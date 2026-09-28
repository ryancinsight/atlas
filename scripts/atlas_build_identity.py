"""Describe source and build dimensions for shared Cargo artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from atlas_build_artifacts import dependency_snapshot
from atlas_build_lease import BuildIdentityError, package_target_lease_path
from atlas_build_source import (
    SourceIdentity,
    environment_digest,
    source_identity,
    toolchain_identity,
)

DEFAULT_LEASE_SECONDS = 900


@dataclass(frozen=True)
class BuildSpec:
    source: SourceIdentity
    package: str
    profile: str
    target: str
    features: str
    toolchain: str
    target_dir: str
    command_key: str
    environment_digest: str
    dependency_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source.as_dict(),
            "package": self.package,
            "profile": self.profile,
            "target": self.target,
            "features": self.features,
            "toolchain": self.toolchain,
            "target_dir": self.target_dir,
            "command_key": self.command_key,
            "environment_digest": self.environment_digest,
            "dependency_digest": self.dependency_digest,
        }


def _cargo_command() -> tuple[str, ...]:
    configured = os.environ.get("CARGO")
    return (configured,) if configured else ("cargo",)


def _resolve_command(command: Sequence[str]) -> list[str]:
    cargo = _cargo_command()
    resolved: list[str] = []
    for argument in command:
        if argument == "cargo":
            resolved.extend(cargo)
        else:
            resolved.append(str(argument))
    return resolved


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve {path}: {error}") from error


def build_spec(
    root: Path,
    package: str,
    target_dir: Path,
    profile: str,
    target: str,
    features: str,
    command: Sequence[str] = (),
    command_key: str | None = None,
    ignore_paths: Sequence[Path] = (),
    dependency_digest: str = "",
) -> BuildSpec:
    if not package:
        raise BuildIdentityError("package must not be empty")
    canonical_root = _canonical(root, strict=True)
    canonical_target = _canonical(target_dir)
    if canonical_target == canonical_root:
        raise BuildIdentityError("target directory must differ from the source root")
    normalized_command = [str(argument) for argument in command]
    normalized_key = command_key if command_key is not None else json.dumps(
        normalized_command, separators=(",", ":")
    )
    return BuildSpec(
        source=source_identity(canonical_root, (canonical_target,), ignore_paths),
        package=package,
        profile=profile,
        target=target,
        features=features,
        toolchain=toolchain_identity(root),
        target_dir=canonical_target.as_posix(),
        command_key=normalized_key,
        environment_digest=environment_digest(),
        dependency_digest=dependency_digest,
    )


def _dependency_data(
    manifest: Path,
    package: str,
    target_dir: Path,
    metadata_cwd: Path,
    ignore_paths: Sequence[Path],
    has_explicit_artifacts: bool,
) -> dict[str, object]:
    if has_explicit_artifacts:
        snapshot: dict[str, object] = {
            "root": package,
            "packages": [],
            "edges": [],
            "clean_packages": [package],
        }
    else:
        source_cache: dict[Path, dict[str, object]] = {}

        def identify_source(path: Path) -> dict[str, object]:
            canonical_path = _canonical(path)
            if canonical_path not in source_cache:
                source_cache[canonical_path] = source_identity(
                    canonical_path, (target_dir,), ignore_paths
                ).as_dict()
            return source_cache[canonical_path]

        snapshot = dependency_snapshot(
            manifest,
            package,
            metadata_cwd,
            identify_source,
        )
    snapshot = dict(snapshot)
    snapshot.pop("digest", None)
    snapshot["digest"] = _sha256_bytes(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    )
    return snapshot


def lease_path(spec: BuildSpec) -> Path:
    return package_target_lease_path(spec.package, Path(spec.target_dir))
