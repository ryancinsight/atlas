"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from atlas_build_artifacts import (
    artifact_identity,
    dependency_snapshot,
    discover_artifacts,
    resolve_target_root,
    validate_artifact_paths,
)
from atlas_build_lease import (
    BuildIdentityError,
    LeaseProbe,
    OwnerLease,
    lease_is_held,
    package_target_lease_path,
    package_target_lease_scopes,
)
import atlas_build_record as records
from atlas_build_source import (
    SourceIdentity,
    environment_digest,
    source_identity,
    toolchain_identity,
)

DEFAULT_LEASE_SECONDS = 900


IdentityError = BuildIdentityError


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


@dataclass(frozen=True)
class BuildResult:
    status: str
    record_path: Path
    cleaned: bool
    artifact_files: tuple[Path, ...]


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
        raise IdentityError(f"cannot resolve {path}: {error}") from error


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
        raise IdentityError("package must not be empty")
    canonical_root = _canonical(root, strict=True)
    canonical_target = resolve_target_root(target_dir)
    if canonical_target == canonical_root:
        raise IdentityError("target directory must differ from the source root")
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
            "artifact_packages": [package],
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
def _run_checked(command: Sequence[str], root: Path, environment: dict[str, str]) -> None:
    try:
        result = subprocess.run(_resolve_command(command), cwd=root, env=environment, check=False)
    except OSError as error:
        raise IdentityError(f"cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise IdentityError(f"command failed with exit code {result.returncode}: {' '.join(command)}")


def run_build(
    root: Path,
    manifest: Path,
    package: str,
    target_dir: Path,
    command: Sequence[str],
    profile: str = "debug",
    target: str = "host",
    features: str = "",
    artifact_paths: Sequence[Path] = (),
    clean_command: Sequence[str] | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    command_cwd: Path | None = None,
    command_key: str | None = None,
    ignore_paths: Sequence[Path] = (),
) -> BuildResult:
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = resolve_target_root(target_dir)
    artifact_paths = validate_artifact_paths(target_dir, artifact_paths)
    execution_root = _canonical(command_cwd or root, strict=True)
    dependencies = _dependency_data(
        manifest,
        package,
        target_dir,
        execution_root,
        ignore_paths,
        bool(artifact_paths),
    )
    spec = build_spec(
        root,
        package,
        target_dir,
        profile,
        target,
        features,
        command,
        command_key,
        ignore_paths,
        str(dependencies["digest"]),
    )
    record = record_path(spec)
    environment = dict(os.environ)
    environment["CARGO_TARGET_DIR"] = target_dir.as_posix()
    cleaned = False
    with ExitStack() as leases:
        for lock, owner in package_target_lease_scopes(
            spec.package,
            target_dir,
            spec.source.root,
            spec.source.revision,
            tuple(str(value) for value in dependencies["clean_packages"]),
        ):
            leases.enter_context(OwnerLease(lock, owner, lease_seconds))
        locked_dependencies = _dependency_data(
            manifest,
            package,
            target_dir,
            execution_root,
            ignore_paths,
            bool(artifact_paths),
        )
        locked_spec = build_spec(
            root,
            package,
            target_dir,
            profile,
            target,
            features,
            command,
            command_key,
            ignore_paths,
            str(locked_dependencies["digest"]),
        )
        if locked_dependencies != dependencies or locked_spec.as_dict() != spec.as_dict():
            raise IdentityError(
                "source or dependency inputs changed while acquiring the package leases"
            )
        existing = read_record(record)
        stale = existing is None and not _sibling_matches(spec)
        if existing is not None:
            try:
                current_artifact = artifact_identity(
                    root,
                    target_dir,
                    package,
                    profile,
                    artifact_paths,
                    target,
                    manifest,
                    execution_root,
                    tuple(str(value) for value in dependencies["artifact_packages"]),
                )
            except IdentityError:
                stale = True
            else:
                stale = (
                    existing.get("source") != spec.source.as_dict()
                    or existing.get("build") != spec.as_dict()
                    or existing.get("dependencies") != dependencies
                    or existing.get("artifact") != current_artifact
                )
        if stale:
            if clean_command is not None:
                _run_checked(clean_command, execution_root, environment)
            else:
                for clean_package in dependencies["clean_packages"]:
                    _run_checked(
                        [
                            *_cargo_command(),
                            "clean",
                            "-p",
                            str(clean_package),
                            "--manifest-path",
                            str(manifest),
                        ],
                        execution_root,
                        environment,
                    )
            cleaned = True
        _run_checked(command, execution_root, environment)
        final_source = source_identity(root, (target_dir,), ignore_paths)
        if final_source.as_dict() != spec.source.as_dict():
            raise IdentityError("source tree changed while the build was running")
        final_dependencies = _dependency_data(
            manifest,
            package,
            target_dir,
            execution_root,
            ignore_paths,
            bool(artifact_paths),
        )
        if final_dependencies != dependencies:
            raise IdentityError("dependency graph changed while the build was running")
        artifact = artifact_identity(
            root,
            target_dir,
            package,
            profile,
            artifact_paths,
            target,
            manifest,
            execution_root,
            tuple(str(value) for value in dependencies["artifact_packages"]),
        )
        paths = tuple(
            target_dir / relative for relative in artifact["files"]
        )
        _write_atomic(
            record,
            {
                "version": VERSION,
                "source": spec.source.as_dict(),
                "build": spec.as_dict(),
                "dependencies": dependencies,
                "artifact": artifact,
            },
        )
    return BuildResult("rebuilt" if cleaned else "reused", record, cleaned, tuple(paths))


def check_record(
    root: Path,
    package: str,
    target_dir: Path,
    profile: str = "debug",
    target: str = "host",
    features: str = "",
    artifact_paths: Sequence[Path] = (),
    manifest: Path | None = None,
    command: Sequence[str] = (),
    command_cwd: Path | None = None,
    command_key: str | None = None,
    ignore_paths: Sequence[Path] = (),
) -> tuple[int, dict[str, object]]:
    target_dir = resolve_target_root(target_dir)
    artifact_paths = validate_artifact_paths(target_dir, artifact_paths)
    if manifest is None and not artifact_paths:
        raise IdentityError("manifest is required for dependency closure resolution")
    execution_root = _canonical(command_cwd or root, strict=True)
    dependencies = _dependency_data(
        manifest or Path(),
        package,
        target_dir,
        execution_root,
        ignore_paths,
        bool(artifact_paths),
    )
    spec = build_spec(
        root,
        package,
        target_dir,
        profile,
        target,
        features,
        command,
        command_key,
        ignore_paths,
        str(dependencies["digest"]),
    )
    record_file = record_path(spec)
    with ExitStack() as probes:
        acquired = True
        for lock, _owner in package_target_lease_scopes(
            spec.package,
            target_dir,
            spec.source.root,
            spec.source.revision,
            tuple(str(value) for value in dependencies["artifact_packages"]),
        ):
            if not probes.enter_context(LeaseProbe(lock)):
                acquired = False
        if not acquired:
            return 3, {"status": "owned", "record": record_file.as_posix()}
        existing = read_record(record_file)
        if existing is None:
            return 2, {"status": "missing", "record": record_file.as_posix()}
        current = artifact_identity(
            root,
            target_dir,
            package,
            profile,
            artifact_paths,
            target,
            manifest,
            execution_root,
            tuple(str(value) for value in dependencies["clean_packages"]),
        )
        matches = (
            existing.get("source") == spec.source.as_dict()
            and existing.get("build") == spec.as_dict()
            and existing.get("dependencies") == dependencies
            and existing.get("artifact") == current
        )
        return (0 if matches else 2), {
            "status": "match" if matches else "stale",
            "record": record_file.as_posix(),
        }
