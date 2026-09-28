"""Run builds while preserving source identity in the shared target directory."""

from __future__ import annotations

import os
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import atlas_build_record as records
from atlas_git_process import GitProcessError, execute_process
from atlas_build_artifacts import artifact_identity, validate_artifact_paths
from atlas_build_identity import (
    DEFAULT_LEASE_SECONDS,
    BuildSpec,
    _canonical,
    _cargo_command,
    _dependency_data,
    _resolve_command,
    build_spec,
)
from atlas_build_lease import (
    BuildIdentityError,
    OwnerLease,
    package_target_lease_scopes,
)
from atlas_build_source import source_identity
from atlas_build_target import TargetDirectory

# A build command is bounded by the five-minute verification-stage target.
BUILD_COMMAND_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class BuildResult:
    status: str
    record_path: Path
    cleaned: bool
    artifact_files: tuple[Path, ...]


@dataclass(frozen=True)
class BuildRequest:
    root: Path
    manifest: Path
    package: str
    command: tuple[str, ...]
    profile: str
    target: str
    features: str
    artifact_paths: tuple[Path, ...]
    clean_command: tuple[str, ...] | None
    lease_seconds: int
    execution_root: Path
    command_key: str | None
    ignore_paths: tuple[Path, ...]


def _sibling_matches(
    spec: BuildSpec,
    dependencies: dict[str, object],
    manifest: Path,
    execution_root: Path,
    artifact_paths: Sequence[Path],
    target_root: TargetDirectory,
) -> bool:
    build = spec.as_dict()
    build.pop("command_key")
    record_directory = records.record_path(spec).parent
    directory = target_root.command_path / target_root.relative_path(record_directory)
    if not directory.is_dir():
        return False
    current_artifact: dict[str, object] | None = None
    for candidate in directory.glob("*.json"):
        try:
            record = records.read_record(target_root, candidate)
        except BuildIdentityError:
            continue
        if record is None:
            continue
        other = record.get("build")
        if not isinstance(other, dict):
            continue
        other = dict(other)
        other.pop("command_key", None)
        if (
            other != build
            or record.get("source") != spec.source.as_dict()
            or record.get("dependencies") != dependencies
        ):
            continue
        if current_artifact is None:
            try:
                current_artifact = artifact_identity(
                    Path(spec.source.root),
                    target_root,
                    spec.package,
                    spec.profile,
                    artifact_paths,
                    spec.target,
                    manifest,
                    execution_root,
                    tuple(str(value) for value in dependencies["clean_packages"]),
                )
            except BuildIdentityError:
                return False
        if record.get("artifact") == current_artifact:
            return True
    return False


def _run_checked(
    command: Sequence[str],
    root: Path,
    environment: dict[str, str],
    target_root: TargetDirectory,
) -> None:
    try:
        result = execute_process(
            _resolve_command(command),
            cwd=root,
            env=environment,
            timeout=BUILD_COMMAND_TIMEOUT_SECONDS,
            capture_output=False,
            pass_fds=target_root.command_fds,
        )
    except GitProcessError as error:
        raise BuildIdentityError(f"cannot run build command: {error}") from error
    if result.returncode != 0:
        raise BuildIdentityError(
            f"command failed with exit code {result.returncode}: {' '.join(command)}"
        )


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
        raise BuildIdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    execution_root = _canonical(command_cwd or root, strict=True)
    request = BuildRequest(
        root=root,
        manifest=manifest,
        package=package,
        command=tuple(str(argument) for argument in command),
        profile=profile,
        target=target,
        features=features,
        artifact_paths=tuple(artifact_paths),
        clean_command=(
            tuple(str(argument) for argument in clean_command)
            if clean_command is not None
            else None
        ),
        lease_seconds=lease_seconds,
        execution_root=execution_root,
        command_key=command_key,
        ignore_paths=tuple(ignore_paths),
    )
    with TargetDirectory(Path(target_dir), create=True) as target_root:
        return _execute_build(request, target_root)


def _execute_build(
    request: BuildRequest, target_root: TargetDirectory
) -> BuildResult:
    root = request.root
    manifest = request.manifest
    package = request.package
    command = request.command
    profile = request.profile
    target = request.target
    features = request.features
    artifact_paths = validate_artifact_paths(target_root, request.artifact_paths)
    clean_command = request.clean_command
    lease_seconds = request.lease_seconds
    execution_root = request.execution_root
    command_key = request.command_key
    ignore_paths = request.ignore_paths
    target_dir = target_root.path
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
    record = records.record_path(spec)
    environment = dict(os.environ)
    environment["CARGO_TARGET_DIR"] = target_root.command_path
    cleaned = False
    with ExitStack() as leases:
        for lock, owner in package_target_lease_scopes(
            spec.package,
            target_dir,
            spec.source.root,
            spec.source.revision,
            tuple(str(value) for value in dependencies["clean_packages"]),
        ):
            leases.enter_context(OwnerLease(target_root, lock, owner, lease_seconds))
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
        if (
            locked_dependencies != dependencies
            or locked_spec.as_dict() != spec.as_dict()
        ):
            raise BuildIdentityError(
                "source or dependency inputs changed while acquiring the package leases"
            )
        existing = records.read_record(target_root, record)
        stale = existing is None and not _sibling_matches(
            spec, dependencies, manifest, execution_root, artifact_paths, target_root
        )
        if existing is not None:
            try:
                current_artifact = artifact_identity(
                    root,
                    target_root,
                    package,
                    profile,
                    artifact_paths,
                    target,
                    manifest,
                    execution_root,
                    tuple(str(value) for value in dependencies["clean_packages"]),
                )
            except BuildIdentityError:
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
                _run_checked(clean_command, execution_root, environment, target_root)
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
                        target_root,
                    )
            cleaned = True
        _run_checked(command, execution_root, environment, target_root)
        final_source = source_identity(root, (target_dir,), ignore_paths)
        if final_source.as_dict() != spec.source.as_dict():
            raise BuildIdentityError("source tree changed while the build was running")
        final_dependencies = _dependency_data(
            manifest,
            package,
            target_dir,
            execution_root,
            ignore_paths,
            bool(artifact_paths),
        )
        if final_dependencies != dependencies:
            raise BuildIdentityError(
                "dependency graph changed while the build was running"
            )
        artifact = artifact_identity(
            root,
            target_root,
            package,
            profile,
            artifact_paths,
            target,
            manifest,
            execution_root,
            tuple(str(value) for value in dependencies["clean_packages"]),
        )
        post_hash_source = source_identity(root, (target_dir,), ignore_paths)
        post_hash_dependencies = _dependency_data(
            manifest,
            package,
            target_dir,
            execution_root,
            ignore_paths,
            bool(artifact_paths),
        )
        if post_hash_source.as_dict() != spec.source.as_dict():
            raise BuildIdentityError(
                "source tree changed while artifacts were being hashed"
            )
        if post_hash_dependencies != dependencies:
            raise BuildIdentityError(
                "dependency graph changed while artifacts were being hashed"
            )
        paths = tuple(
            target_dir / relative for relative in artifact["files"]
        )
        records.write_record(
            target_root,
            record,
            {
                "version": records.RECORD_VERSION,
                "source": spec.source.as_dict(),
                "build": spec.as_dict(),
                "dependencies": dependencies,
                "artifact": artifact,
            },
        )
    return BuildResult(
        "rebuilt" if cleaned else "reused", record, cleaned, tuple(paths)
    )
