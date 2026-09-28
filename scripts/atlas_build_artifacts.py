"""Discover and hash Cargo artifacts for source identity records."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable, Sequence

from atlas_git_process import GitProcessError, execute_process
from atlas_build_lease import BuildIdentityError
from atlas_build_target import TargetDirectory

def _canonical(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve {path}: {error}") from error


def _feed_framed(digest: "hashlib._Hash", data: bytes) -> None:
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)


def _file_digest(target: TargetDirectory, path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with target.open_file(path) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise BuildIdentityError(f"cannot hash artifact {path}: {error}") from error
    return digest.hexdigest()


def _validated_paths(
    target: TargetDirectory, paths: Sequence[Path]
) -> tuple[Path, ...]:
    selected: set[Path] = set()
    for path in paths:
        target.validate_path(path)
        relative = target.relative_path(path)
        selected.add(target.path / relative)
    return tuple(sorted(selected))


def validate_artifact_paths(
    target: TargetDirectory, paths: Sequence[Path]
) -> tuple[Path, ...]:
    return _validated_paths(target, paths)


def artifact_identity(
    root: Path,
    target_root: TargetDirectory,
    package: str,
    profile: str,
    paths: Sequence[Path],
    target: str = "host",
    manifest: Path | None = None,
    metadata_cwd: Path | None = None,
    related_packages: Sequence[str] = (),
) -> dict[str, object]:
    _canonical(root, strict=True)
    target_dir = target_root.path
    selected = set(_validated_paths(target_root, paths))
    if not selected:
        selected.update(
            discover_artifacts(
                target_root.command_path,
                package,
                profile,
                target,
                manifest,
                metadata_cwd,
                related_packages,
            )
        )
        selected = set(_validated_paths(target_root, tuple(selected)))

    if not selected:
        raise BuildIdentityError(
            f"no artifact found for {package} in {target_dir / profile}"
        )
    files = {}
    for path in sorted(selected):
        relative = target_root.relative_path(path).as_posix()
        files[relative] = _file_digest(target_root, path)
    digest = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"files": files, "digest": digest}


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _package_source_digest(root: Path) -> str:
    canonical_root = _canonical(root, strict=True)
    if not canonical_root.is_dir():
        raise BuildIdentityError(f"package source is not a directory: {canonical_root}")
    digest = hashlib.sha256()
    paths = sorted(
        (
            path
            for path in canonical_root.rglob("*")
            if ".git" not in path.relative_to(canonical_root).parts
        ),
        key=lambda path: path.relative_to(canonical_root).as_posix(),
    )
    for path in paths:
        relative = path.relative_to(canonical_root).as_posix()
        if path.is_symlink():
            try:
                target = path.readlink().as_posix()
                resolved = path.resolve(strict=True)
            except OSError as error:
                raise BuildIdentityError(
                    f"cannot resolve package source symlink {path}: {error}"
                ) from error
            if not _is_within(resolved, canonical_root):
                raise BuildIdentityError(
                    f"package source symlink escapes its package root: {path}"
                )
            _feed_framed(digest, b"symlink")
            _feed_framed(digest, relative.encode("utf-8"))
            _feed_framed(digest, target.encode("utf-8"))
            continue
        if not path.is_file():
            continue
        _feed_framed(digest, b"file")
        _feed_framed(digest, relative.encode("utf-8"))
        try:
            _feed_framed(digest, path.read_bytes())
        except OSError as error:
            raise BuildIdentityError(f"cannot read package source {path}: {error}") from error
    return digest.hexdigest()


def _normalize_stem(value: str) -> str:
    return value.replace("-", "_")


_CARGO_HASH_SUFFIX = re.compile(r"-[0-9a-f]{16}\Z")
_VERSIONED_SHARED_LIBRARY = re.compile(r"\.so(?:\.\d+(?:\.\d+)*)?\Z", re.IGNORECASE)


def _artifact_stem(filename: str) -> str | None:
    name = filename.casefold()
    prefixed_extensions = (".rlib", ".rmeta", ".so", ".dylib", ".a")
    plain_extensions = (".dll.lib", ".dll", ".lib", ".exe", ".wasm", ".d", ".pdb")
    for extension in prefixed_extensions:
        if name.endswith(extension):
            return filename[: -len(extension)].removeprefix("lib")
    if _VERSIONED_SHARED_LIBRARY.search(name):
        suffix = _VERSIONED_SHARED_LIBRARY.search(name)
        if suffix is None:
            return None
        return filename[: suffix.start()].removeprefix("lib")
    for extension in plain_extensions:
        if name.endswith(extension):
            return filename[: -len(extension)]
    if "." in filename:
        return None
    return filename


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
        result = execute_process(
            arguments,
            cwd=metadata_cwd or manifest.parent,
            timeout=60,
        )
    except GitProcessError as error:
        raise BuildIdentityError(f"cannot read package metadata from {manifest}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BuildIdentityError(f"cargo metadata failed for {manifest}: {detail}")
    try:
        value = json.loads(result.stdout.decode("utf-8", errors="replace"))
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


def _artifact_owner(filename: str, owners: dict[str, frozenset[str]], requested: str) -> str | None:
    stem = _artifact_stem(filename)
    if stem is None:
        return None
    if _CARGO_HASH_SUFFIX.search(stem):
        stem = stem[:-17]
    stem = _normalize_stem(stem)
    matches = [
        (owner, candidate)
        for owner, stems in owners.items()
        for candidate in stems
        if stem == candidate
    ]
    requested_matches = [match for match in matches if match[0] == requested]
    if not requested_matches:
        return None
    longest = max(len(candidate) for _, candidate in matches)
    best = {owner for owner, candidate in matches if len(candidate) == longest}
    if len(best) != 1:
        raise BuildIdentityError(
            f"artifact {filename} has ambiguous Cargo owners: {', '.join(sorted(best))}"
        )
    return next(iter(best))


def _belongs_to_requested(
    filename: str, owners: dict[str, frozenset[str]], requested: set[str]
) -> bool:
    return any(
        _artifact_owner(filename, owners, package) == package
        for package in sorted(requested)
    )


def dependency_snapshot(
    manifest: Path,
    package: str,
    metadata_cwd: Path | None,
    source_identity: Callable[[Path], object],
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
                    "from": package_id,
                    "to": dependency_id,
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
    git_source_identities: dict[str, object] = {}
    for package_id in sorted(reachable):
        value = packages.get(package_id)
        if value is None:
            raise BuildIdentityError(f"Cargo metadata is missing package {package_id}")
        source = value.get("source")
        manifest_path = Path(str(value["manifest_path"]))
        if source is None:
            identity_value = source_identity(manifest_path.parent)
            record = {
                "id": package_id,
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
            source_record: dict[str, object] = {
                "id": package_id,
                "name": str(value["name"]),
                "version": str(value["version"]),
                "features": sorted(
                    str(feature) for feature in nodes[package_id].get("features", [])
                ),
                "kind": kind,
                "source": source_text,
            }
            if kind == "git":
                identity_value = git_source_identities.get(source_text)
                if identity_value is None:
                    identity_value = source_identity(manifest_path.parent)
                    git_source_identities[source_text] = identity_value
                source_record["identity"] = identity_value
            else:
                source_record["content_digest"] = _package_source_digest(
                    manifest_path.parent
                )
            record = source_record
        if record["kind"] != "registry":
            name = str(record["name"])
            previous = clean_sources.get(name)
            if previous is not None and previous != package_id:
                raise BuildIdentityError(
                    f"dependency package name {name} has multiple non-registry sources"
                )
            clean_sources[name] = package_id
            clean_packages.add(name)
        records.append(record)
    snapshot = {
        "root": roots[0],
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
) -> tuple[Path, ...]:
    target_dir = Path(target_dir)
    if not target_dir.is_absolute():
        target_dir = Path.cwd() / target_dir
    owners = (
        _workspace_artifact_owners(manifest, metadata_cwd)
        if manifest is not None
        else {package: frozenset({_normalize_stem(package)})}
    )
    requested_packages = set((package, *related_packages))
    selected: set[Path] = set()
    profile_dirs = [target_dir / profile]
    if target != "host":
        profile_dirs.append(target_dir / target / profile)
    for profile_dir in profile_dirs:
        if not profile_dir.is_dir():
            continue
        for path in profile_dir.iterdir():
            if (
                path.is_file()
                and _belongs_to_requested(path.name, owners, requested_packages)
            ):
                selected.add(path)
    dep_dirs = [target_dir / profile / "deps"]
    if target != "host":
        dep_dirs.append(target_dir / target / profile / "deps")
    for deps in dep_dirs:
        if not deps.is_dir():
            continue
        for path in deps.iterdir():
            if (
                path.is_file()
                and _belongs_to_requested(path.name, owners, requested_packages)
            ):
                selected.add(path)

    example_dirs = [target_dir / profile / "examples"]
    if target != "host":
        example_dirs.append(target_dir / target / profile / "examples")
    for examples in example_dirs:
        if not examples.is_dir():
            continue
        for path in examples.iterdir():
            if (
                path.is_file()
                and _belongs_to_requested(path.name, owners, requested_packages)
            ):
                selected.add(path)
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
                and _belongs_to_requested(directory.name, owners, requested_packages)
            ):
                selected.update(
                    path for path in directory.rglob("*") if path.is_file()
                )
    build_dirs = [target_dir / profile / "build"]
    if target != "host":
        build_dirs.append(target_dir / target / profile / "build")
    for builds in build_dirs:
        if not builds.is_dir():
            continue
        for directory in builds.iterdir():
            if (
                directory.is_dir()
                and _belongs_to_requested(directory.name, owners, requested_packages)
            ):
                selected.update(
                    path for path in directory.rglob("*") if path.is_file()
                )
    return tuple(sorted(selected))
