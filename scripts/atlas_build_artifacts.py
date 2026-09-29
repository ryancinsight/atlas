"""Discover and hash Cargo artifacts for source identity records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Iterable, Sequence

from atlas_build_lease import BuildIdentityError

ARTIFACT_SUFFIXES = frozenset(
    {
        ".a",
        ".d",
        ".dll",
        ".dylib",
        ".exe",
        ".json",
        ".lib",
        ".pdb",
        ".rlib",
        ".rmeta",
        ".so",
        ".wasm",
    }
)


def _canonical(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve {path}: {error}") from error


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise BuildIdentityError(f"cannot hash artifact {path}: {error}") from error
    return digest.hexdigest()


def validate_artifact_paths(target_dir: Path, paths: Sequence[Path]) -> tuple[Path, ...]:
    canonical_target = _canonical(target_dir)
    selected: set[Path] = set()
    for path in paths:
        resolved = _canonical(path)
        try:
            resolved.relative_to(canonical_target)
        except ValueError as error:
            raise BuildIdentityError(f"artifact is outside the shared target: {resolved}") from error
        selected.add(resolved)
    return tuple(sorted(selected))


def artifact_identity(
    root: Path,
    target_dir: Path,
    package: str,
    profile: str,
    paths: Sequence[Path],
    target: str = "host",
    manifest: Path | None = None,
    metadata_cwd: Path | None = None,
    related_packages: Sequence[str] = (),
) -> dict[str, object]:
    _canonical(root, strict=True)
    target_dir = _canonical(target_dir)
    selected = set(validate_artifact_paths(target_dir, paths))

    if not selected:
        selected.update(
            discover_artifacts(
                target_dir,
                package,
                profile,
                target,
                manifest,
                metadata_cwd,
                related_packages,
            )
        )

    if not selected:
        raise BuildIdentityError(f"no artifact found for {package} in {target_dir / profile}")
    relative = []
    for path in selected:
        try:
            relative.append(path.relative_to(target_dir).as_posix())
        except ValueError as error:
            raise BuildIdentityError(f"artifact is outside the shared target: {path}") from error
    return recorded_artifact_identity(target_dir, relative)


def recorded_artifact_identity(target_dir: Path, relative_paths: Iterable[str]) -> dict[str, object]:
    """Hash exactly the named artifacts, without discovering others.

    A shared reader compares a dependency against the files its record
    names: a variant another reader's build writes beside them is not part
    of that comparison, so it cannot tear it. A missing or unreadable file
    raises.
    """
    target_dir = _canonical(target_dir)
    files = {}
    for relative in sorted(set(relative_paths)):
        path = target_dir / relative
        if not _is_within(_canonical(path), target_dir):
            raise BuildIdentityError(f"artifact is outside the shared target: {path}")
        files[relative] = _file_digest(path)
    return {"files": files, "digest": artifact_digest(files)}


def changed_packages(
    recorded: dict[str, str],
    current: dict[str, str],
    manifest: Path,
    metadata_cwd: Path | None,
    packages: Sequence[str],
) -> set[str] | None:
    """The packages owning the artifact files whose digests changed.

    None when a changed file cannot be attributed to exactly one of
    `packages`; the caller then cleans them all.
    """
    changed = [relative for relative, digest in recorded.items() if current.get(relative) != digest]
    owners = {
        name: stems
        for name, stems in _workspace_artifact_owners(manifest, metadata_cwd).items()
        if name in packages
    }
    names: set[str] = set()
    for relative in changed:
        owner = artifact_package(relative, owners)
        if owner is None:
            return None
        names.add(owner)
    return names


def artifact_owners(manifest: Path, metadata_cwd: Path | None = None) -> dict[str, frozenset[str]]:
    """Each package's artifact stems, read once for several attributions."""
    return _workspace_artifact_owners(manifest, metadata_cwd)


def artifact_package(relative: str, owners: dict[str, frozenset[str]]) -> str | None:
    """The one package in `owners` that a recorded artifact path belongs to, or None."""
    parts = relative.split("/")
    # `<profile>/deps/<file>` names the file, `.../.fingerprint/<unit>/<file>` the unit.
    unit = parts[parts.index(".fingerprint") + 1] if ".fingerprint" in parts else parts[-1]
    return _artifact_owner(unit, owners, "")


# Recorded in place of a digest when a dependency file never read the same
# twice in a row: it compares unequal to any real digest, so the next run
# cleans that file's package, never the whole closure.
UNVERIFIED = "unverified"
# A dependency file another reader's Cargo is rewriting refuses reads on
# Windows, or changes under them, while rustc writes it; one second outlasts
# a rewrite of the artifacts a gate step reads.
SETTLE_SECONDS = 1.0
_SETTLE_INTERVAL = 0.02


def settled_digest(path: Path, deadline_ns: int) -> str | None:
    """The file's digest once two consecutive reads agree.

    Reads repeat until two in a row succeed with one digest and the file's
    size and modification time unchanged across both, or until `deadline_ns`
    (monotonic) passes after at least two attempts. Returns `UNVERIFIED`
    when reads succeeded but never agreed, and None when none succeeded.
    """
    previous = None
    read = False
    attempts = 0
    while True:
        attempts += 1
        try:
            before = path.stat()
            digest = _file_digest(path)
            after = path.stat()
        except (OSError, BuildIdentityError):
            current = None
        else:
            read = True
            state = (before.st_size, before.st_mtime_ns)
            current = (digest, state) if state == (after.st_size, after.st_mtime_ns) else None
        if current is not None and current == previous:
            return current[0]
        settling = current is not None and previous is None
        previous = current
        if attempts >= 2 and time.monotonic_ns() >= deadline_ns:
            return UNVERIFIED if read else None
        if not settling:
            # The first good read is confirmed at once; anything else waits.
            time.sleep(_SETTLE_INTERVAL)


def artifact_digest(files: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _normalize_stem(value: str) -> str:
    return value.replace("-", "_")


def _cargo_metadata(
    manifest: Path,
    metadata_cwd: Path | None = None,
    *,
    no_deps: bool = True,
) -> dict[str, object]:
    cargo = (os.environ["CARGO"],) if os.environ.get("CARGO") else ("cargo",)
    arguments = [
        *cargo,
        "metadata",
        "--format-version",
        "1",
        "--locked",
        "--manifest-path",
        str(manifest),
    ]
    if no_deps:
        arguments.append("--no-deps")
    try:
        result = subprocess.run(
            arguments,
            cwd=metadata_cwd or manifest.parent,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BuildIdentityError(f"cannot read package metadata from {manifest}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise BuildIdentityError(f"cargo metadata failed for {manifest}: {detail}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise BuildIdentityError(f"malformed cargo metadata for {manifest}") from error
    if not isinstance(value, dict):
        raise BuildIdentityError(f"malformed cargo metadata for {manifest}")
    return value


def _workspace_artifact_owners(
    manifest: Path, metadata_cwd: Path | None = None
) -> dict[str, frozenset[str]]:
    metadata = _cargo_metadata(manifest, metadata_cwd, no_deps=False)
    try:
        owners: dict[str, frozenset[str]] = {}
        for package in metadata["packages"]:
            name = str(package["name"])
            stems = {_normalize_stem(name)}
            for target in package.get("targets", []):
                target_name = target.get("name")
                if isinstance(target_name, str) and target_name:
                    stems.add(_normalize_stem(target_name))
            owners[name] = frozenset(stems)
    except (KeyError, TypeError) as error:
        raise BuildIdentityError(
            f"malformed cargo metadata for {manifest}"
        ) from error
    if not owners:
        raise BuildIdentityError(f"cargo metadata contains no packages for {manifest}")
    return owners


# Cargo writes a 16-digit metadata hash; any hex suffix is accepted so the
# fixture names (`demo-111`) and real ones are read alike.
_METADATA_HASH = re.compile(r"-[0-9a-f]+$")


def _artifact_owner(filename: str, owners: dict[str, frozenset[str]], requested: str) -> str | None:
    """The package whose target the artifact names exactly.

    Cargo names an artifact `<target>-<hex metadata hash>` (a library
    file adds `lib` and an extension), so the name before the hash is the
    target, compared whole. A prefix match let `mnemosyne_build_util-<h>`
    belong to both `mnemosyne-build-util` and `mnemosyne-memory` (whose
    library is `mnemosyne`), and an artifact claimed twice was claimed by
    none: a real mnemosyne gate found no artifact and refused the push.
    """
    base = _METADATA_HASH.sub("", filename.split(".", 1)[0])
    names = {_normalize_stem(base)}
    if base.startswith("lib"):
        names.add(_normalize_stem(base[3:]))
    matches = [owner for owner, stems in owners.items() if names & stems]
    return matches[0] if len(matches) == 1 else None


def _stable_package_ids(
    packages: dict[str, dict], workspace_root: object
) -> dict[str, str]:
    """Path-package IDs relative to the workspace root.

    Cargo names a path package by its absolute manifest directory
    (`path+file:///<dir>#<version>`), so the same workspace exported to two
    directories yields two snapshots of one dependency graph. Packages
    inside the workspace are renamed to their workspace-relative directory;
    anything else keeps cargo's ID.
    """
    if not isinstance(workspace_root, str) or not workspace_root:
        return {}
    base = _canonical(Path(workspace_root))
    stable: dict[str, str] = {}
    for package_id, value in packages.items():
        if value.get("source") is not None:
            continue
        directory = _canonical(Path(str(value["manifest_path"]))).parent
        if not _is_within(directory, base):
            continue
        relative = directory.relative_to(base).as_posix()
        stable[package_id] = f"workspace:{relative}#{value['name']}@{value['version']}"
    return stable


def dependency_snapshot(
    manifest: Path,
    package: str,
    metadata_cwd: Path | None,
    source_identity: Callable[[Path], object],
    content_digest: Callable[[Path], str],
) -> dict[str, object]:
    metadata = _cargo_metadata(manifest, metadata_cwd, no_deps=False)
    try:
        packages = {
            str(value["id"]): value
            for value in metadata["packages"]
            if isinstance(value, dict) and "id" in value
        }
        nodes = {
            str(value["id"]): value
            for value in metadata["resolve"]["nodes"]
            if isinstance(value, dict)
            and "id" in value
            and isinstance(value.get("deps"), list)
        }
    except (KeyError, TypeError) as error:
        raise BuildIdentityError(f"Cargo metadata has no resolved dependency graph for {manifest}") from error
    roots = [
        package_id
        for package_id, value in packages.items()
        if value.get("name") == package
        and (
            not metadata.get("workspace_members")
            or package_id in metadata["workspace_members"]
        )
    ]
    if len(roots) != 1 or roots[0] not in nodes:
        raise BuildIdentityError(f"Cargo metadata has no unique root package {package}")
    stable = _stable_package_ids(packages, metadata.get("workspace_root"))
    reachable: set[str] = set()
    edges: list[dict[str, object]] = []
    pending = [roots[0]]
    while pending:
        package_id = pending.pop()
        if package_id in reachable:
            continue
        reachable.add(package_id)
        node = nodes[package_id]
        for dependency in node["deps"]:
            dependency_id = str(dependency["pkg"])
            edges.append(
                {
                    "from": stable.get(package_id, package_id),
                    "to": stable.get(dependency_id, dependency_id),
                    "dep_kinds": sorted(
                        dependency.get("dep_kinds", []),
                        key=lambda value: json.dumps(value, sort_keys=True),
                    ),
                }
            )
            pending.append(dependency_id)
    records: list[dict[str, object]] = []
    clean_packages: set[str] = set()
    clean_sources: dict[str, str] = {}
    for package_id in sorted(reachable):
        value = packages.get(package_id)
        if value is None:
            raise BuildIdentityError(f"Cargo metadata is missing package {package_id}")
        source = value.get("source")
        manifest_path = Path(str(value["manifest_path"]))
        if source is None:
            identity_value = source_identity(manifest_path.parent)
            record = {
                "id": stable.get(package_id, package_id),
                "name": str(value["name"]),
                "version": str(value["version"]),
                "features": sorted(
                    str(feature) for feature in nodes[package_id].get("features", [])
                ),
                "kind": "path",
                "identity": identity_value,
            }
        else:
            source_text = str(source)
            kind = "git" if source_text.startswith("git+") else "registry"
            record = {
                "id": package_id,
                "name": str(value["name"]),
                "version": str(value["version"]),
                "features": sorted(
                    str(feature) for feature in nodes[package_id].get("features", [])
                ),
                "kind": kind,
                "source": source_text,
                "content_digest": content_digest(manifest_path.parent),
            }
        if record["kind"] != "registry":
            name = str(record["name"])
            previous = clean_sources.get(name)
            if previous is not None and previous != stable.get(package_id, package_id):
                raise BuildIdentityError(
                    f"dependency package name {name} has multiple non-registry sources"
                )
            clean_sources[name] = stable.get(package_id, package_id)
            clean_packages.add(name)
        records.append(record)
    snapshot = {
        "root": stable.get(roots[0], roots[0]),
        "packages": records,
        "edges": sorted(edges, key=lambda value: json.dumps(value, sort_keys=True)),
        "clean_packages": sorted(clean_packages),
    }
    snapshot["digest"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return snapshot


def discover_artifacts(
    target_dir: Path,
    package: str,
    profile: str,
    target: str = "host",
    manifest: Path | None = None,
    metadata_cwd: Path | None = None,
    related_packages: Sequence[str] = (),
    owners: dict[str, frozenset[str]] | None = None,
) -> tuple[Path, ...]:
    target_dir = _canonical(target_dir)
    if owners is None:
        owners = (
            _workspace_artifact_owners(manifest, metadata_cwd)
            if manifest is not None
            else {package: frozenset({_normalize_stem(package)})}
        )
    requested_packages = set((package, *related_packages))
    selected: set[Path] = set()
    dep_dirs = [target_dir / profile / "deps"]
    if target != "host":
        dep_dirs.append(target_dir / target / profile / "deps")
    for deps in dep_dirs:
        if not deps.is_dir():
            continue
        for path in deps.iterdir():
            if (
                path.is_file()
                and path.suffix in ARTIFACT_SUFFIXES
                and _artifact_owner(path.name, owners, package) in requested_packages
            ):
                selected.add(path.resolve())
    fingerprint_dirs = [
        target_dir / profile / ".fingerprint",
        target_dir / ".fingerprint",
    ]
    if target != "host":
        fingerprint_dirs.append(target_dir / target / profile / ".fingerprint")
    for fingerprints in fingerprint_dirs:
        if not fingerprints.is_dir():
            continue
        for directory in fingerprints.iterdir():
            if (
                directory.is_dir()
                and _artifact_owner(directory.name, owners, package) in requested_packages
            ):
                selected.update(
                    path.resolve() for path in directory.rglob("*") if path.is_file()
                )
    return tuple(sorted(selected))
