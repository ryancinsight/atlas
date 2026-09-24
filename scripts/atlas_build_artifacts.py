"""Discover and hash Cargo artifacts for source identity records."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Sequence

from atlas_build_lease import BuildIdentityError

ARTIFACT_SUFFIXES = frozenset(
    {".a", ".d", ".dll", ".dylib", ".exe", ".json", ".lib", ".pdb", ".rlib", ".rmeta", ".so"}
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


def artifact_identity(
    root: Path,
    target_dir: Path,
    package: str,
    profile: str,
    paths: Sequence[Path],
    target: str = "host",
    manifest: Path | None = None,
    metadata_cwd: Path | None = None,
) -> dict[str, object]:
    _canonical(root, strict=True)
    target_dir = _canonical(target_dir)
    selected: set[Path] = set()
    for path in paths:
        resolved = _canonical(path, strict=True)
        try:
            resolved.relative_to(target_dir)
        except ValueError as error:
            raise BuildIdentityError(f"artifact is outside the shared target: {resolved}") from error
        if not resolved.is_file():
            raise BuildIdentityError(f"artifact does not exist: {resolved}")
        selected.add(resolved)

    if not selected:
        selected.update(
            discover_artifacts(target_dir, package, profile, target, manifest, metadata_cwd)
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


def _workspace_package_names(manifest: Path, metadata_cwd: Path | None = None) -> frozenset[str]:
    cargo = (os.environ["CARGO"],) if os.environ.get("CARGO") else ("cargo",)
    try:
        result = subprocess.run(
            [
                *cargo,
                "metadata",
                "--no-deps",
                "--format-version",
                "1",
                "--manifest-path",
                str(manifest),
            ],
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
        packages = json.loads(result.stdout)["packages"]
        names = frozenset(str(package["name"]) for package in packages)
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise BuildIdentityError(f"malformed cargo metadata for {manifest}") from error
    if not names:
        raise BuildIdentityError(f"cargo metadata contains no packages for {manifest}")
    return names


def _artifact_owner(filename: str, package_names: frozenset[str], requested: str) -> str | None:
    stem = filename[3:] if filename.startswith("lib") else filename
    stem = stem.split(".", 1)[0]
    matches = [name for name in package_names if stem == name or stem.startswith(f"{name}-")]
    if not matches:
        return requested if stem == requested or stem.startswith(f"{requested}-") else None
    owner = max(matches, key=len)
    return owner if owner == requested else None


def discover_artifacts(
    target_dir: Path,
    package: str,
    profile: str,
    target: str = "host",
    manifest: Path | None = None,
    metadata_cwd: Path | None = None,
) -> tuple[Path, ...]:
    target_dir = _canonical(target_dir)
    package_names = (
        _workspace_package_names(manifest, metadata_cwd)
        if manifest is not None
        else frozenset({package})
    )
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
                and _artifact_owner(path.name, package_names, package) == package
            ):
                selected.add(path.resolve())
    fingerprints = target_dir / ".fingerprint"
    if fingerprints.is_dir():
        for directory in fingerprints.iterdir():
            if (
                directory.is_dir()
                and _artifact_owner(directory.name, package_names, package) == package
            ):
                selected.update(path.resolve() for path in directory.rglob("*") if path.is_file())
    return tuple(sorted(selected))
