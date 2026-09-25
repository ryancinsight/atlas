"""Discover and hash Cargo artifacts for source identity records."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Sequence

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
    files = {}
    for path in sorted(selected):
        try:
            relative = path.relative_to(target_dir).as_posix()
        except ValueError as error:
            raise BuildIdentityError(f"artifact is outside the shared target: {path}") from error
        files[relative] = _file_digest(path)
    digest = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"files": files, "digest": digest}


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


def _artifact_owner(filename: str, owners: dict[str, frozenset[str]], requested: str) -> str | None:
    stem = filename[3:] if filename.startswith("lib") else filename
    stem = _normalize_stem(stem.split(".", 1)[0])
    matches = [
        owner
        for owner, stems in owners.items()
        if any(
            stem == candidate
            or stem.startswith(f"{candidate}_")
            or stem.startswith(f"{candidate}-")
            for candidate in stems
        )
    ]
    return matches[0] if len(matches) == 1 else None


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
            if isinstance(value, dict) and "id" in value
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
        for dependency in node.get("dependencies", []):
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
    for package_id in sorted(reachable):
        value = packages.get(package_id)
        if value is None:
            raise BuildIdentityError(f"Cargo metadata is missing package {package_id}")
        source = value.get("source")
        if source is None:
            manifest_path = Path(str(value["manifest_path"]))
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
            record = {
                "id": package_id,
                "name": str(value["name"]),
                "version": str(value["version"]),
                "features": sorted(
                    str(feature) for feature in nodes[package_id].get("features", [])
                ),
                "kind": kind,
                "source": source_text,
            }
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
    target_dir = _canonical(target_dir)
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
