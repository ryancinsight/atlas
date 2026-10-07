"""Discover and hash Cargo artifacts for source identity records."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Iterable, Sequence

from atlas_build_lease import BuildIdentityError
from atlas_build_snapshot import _cargo_metadata
from atlas_build_source import _canonical, _is_within

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
    owners: dict[str, frozenset[str]] | None = None,
) -> dict[str, object]:
    _canonical(root, strict=True)
    target_dir = _canonical(target_dir)
    selected = set(validate_artifact_paths(target_dir, paths))

    if not selected:
        return artifact_identities(
            root,
            target_dir,
            {package: related_packages},
            profile,
            target,
            manifest,
            metadata_cwd,
            owners,
        )[package]

    relative = []
    for path in selected:
        try:
            relative.append(path.relative_to(target_dir).as_posix())
        except ValueError as error:
            raise BuildIdentityError(f"artifact is outside the shared target: {path}") from error
    return recorded_artifact_identity(target_dir, relative)


def artifact_identities(
    root: Path,
    target_dir: Path,
    packages: dict[str, Sequence[str]],
    profile: str,
    target: str = "host",
    manifest: Path | None = None,
    metadata_cwd: Path | None = None,
    owners: dict[str, frozenset[str]] | None = None,
) -> dict[str, dict[str, object]]:
    """Discover several packages' overlapping artifact closures in one target census."""

    _canonical(root, strict=True)
    target_dir = _canonical(target_dir)
    if not packages:
        return {}
    if owners is None:
        if manifest is None:
            owners = {
                package: frozenset({_normalize_stem(package)}) for package in packages
            }
        else:
            owners = _workspace_artifact_owners(manifest, metadata_cwd)
    by_owner = _discover_artifacts_by_owner(target_dir, profile, target, owners)
    selected = {
        package: set().union(
            *(by_owner.get(owner, set()) for owner in {package, *related})
        )
        for package, related in packages.items()
    }
    missing = [package for package, paths in selected.items() if not paths]
    if missing:
        raise BuildIdentityError(
            f"no artifact found for {', '.join(sorted(missing))} in {target_dir / profile}"
        )
    digests = {
        path: _file_digest(path)
        for path in sorted(set().union(*(paths for paths in selected.values())))
    }
    results = {}
    for package, paths in selected.items():
        files = {
            path.relative_to(target_dir).as_posix(): digests[path]
            for path in sorted(paths)
        }
        results[package] = {"files": files, "digest": artifact_digest(files)}
    return results


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
    owners: dict[str, frozenset[str]] | None = None,
) -> set[str] | None:
    """The packages owning the artifact files whose digests changed.

    None when a changed file cannot be attributed to exactly one of
    `packages`; the caller then cleans them all. `owners` is the workspace's
    artifact stems when the caller has read them already (`artifact_owners`).
    """
    changed = [relative for relative, digest in recorded.items() if current.get(relative) != digest]
    if owners is None:
        owners = _workspace_artifact_owners(manifest, metadata_cwd)
    owners = {name: stems for name, stems in owners.items() if name in packages}
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


def shared_artifact_identity(
    target_dir: Path,
    package: str,
    profile: str,
    target: str,
    manifest: Path,
    metadata_cwd: Path,
    exclusive_packages: Iterable[str],
    shared_packages: frozenset[str] | set[str],
    named: dict[str, str],
    owners: dict[str, frozenset[str]],
    settled: dict[str, str],
    deadline_ns: int,
    exclusive_artifact: dict[str, object] | None = None,
) -> dict[str, object]:
    """A run's record of `package`'s artifacts when it held some path packages shared.

    Peers read, and their Cargo may rewrite, every path package the run holds
    shared, so those are found by the names a record lists (`named`, with the
    digests read before the command), never by discovery, and each is hashed
    again once two reads agree: the command rebuilt them in place (a fresh
    export has fresh mtimes, and rustc embeds its path in the bytes). A file
    that never settles is recorded unverified, and one that cannot be read at
    all keeps its digest read before the command. Only the path packages held
    exclusive are discovered afresh, and their recorded names are dropped, so a
    name their rebuild retired is not kept. `settled` memoizes each file's
    digest across the run's packages; each file gets up to SETTLE_SECONDS, never
    past `deadline_ns`, and at least two reads are always attempted.
    """
    own = exclusive_artifact
    if own is None:
        own = recorded_artifact_identity(
            target_dir,
            [
                path.relative_to(target_dir).as_posix()
                for path in discover_artifacts(
                    target_dir,
                    package,
                    profile,
                    target,
                    manifest,
                    metadata_cwd,
                    tuple(sorted(exclusive_packages)),
                    owners,
                )
            ],
        )
    files = {}
    for relative, verified in named.items():
        if artifact_package(relative, owners) not in shared_packages:
            continue
        if relative not in settled:
            budget = min(time.monotonic_ns() + int(SETTLE_SECONDS * 1_000_000_000), deadline_ns)
            digest = settled_digest(target_dir / relative, budget)
            settled[relative] = verified if digest is None else digest
        files[relative] = settled[relative]
    files.update(own["files"])
    return {"files": files, "digest": artifact_digest(files)}


def artifact_digest(files: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _normalize_stem(value: str) -> str:
    return value.replace("-", "_")


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
    requested_packages = {package, *related_packages}
    by_owner = _discover_artifacts_by_owner(target_dir, profile, target, owners)
    return tuple(
        sorted(set().union(*(by_owner.get(owner, set()) for owner in requested_packages)))
    )


def _discover_artifacts_by_owner(
    target_dir: Path,
    profile: str,
    target: str,
    owners: dict[str, frozenset[str]],
) -> dict[str, set[Path]]:
    """Enumerate one target directory once and group every artifact by package."""

    selected: dict[str, set[Path]] = {}
    dep_dirs = [target_dir / profile / "deps"]
    if target != "host":
        dep_dirs.append(target_dir / target / profile / "deps")
    for deps in dep_dirs:
        if not deps.is_dir():
            continue
        for path in deps.iterdir():
            owner = _artifact_owner(path.name, owners, "")
            if path.is_file() and path.suffix in ARTIFACT_SUFFIXES and owner is not None:
                selected.setdefault(owner, set()).add(path.resolve())
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
            owner = _artifact_owner(directory.name, owners, "")
            if directory.is_dir() and owner is not None:
                selected.setdefault(owner, set()).update(
                    path.resolve() for path in directory.rglob("*") if path.is_file()
                )
    return selected
