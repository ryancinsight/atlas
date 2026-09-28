"""Check whether shared Cargo artifacts match their recorded source identity."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import atlas_build_record as records
from atlas_build_artifacts import artifact_identity, validate_artifact_paths
from atlas_build_identity import _canonical, _dependency_data, build_spec
from atlas_build_lease import (
    BuildIdentityError,
    LeaseProbe,
    package_target_lease_scopes,
)
from atlas_build_target import TargetDirectory


@dataclass(frozen=True)
class CheckRequest:
    root: Path
    package: str
    profile: str
    target: str
    features: str
    artifact_paths: tuple[Path, ...]
    manifest: Path | None
    command: tuple[str, ...]
    execution_root: Path
    command_key: str | None
    ignore_paths: tuple[Path, ...]


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
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True) if manifest is not None else None
    execution_root = _canonical(command_cwd or root, strict=True)
    request = CheckRequest(
        root=root,
        package=package,
        profile=profile,
        target=target,
        features=features,
        artifact_paths=tuple(artifact_paths),
        manifest=manifest,
        command=tuple(str(argument) for argument in command),
        execution_root=execution_root,
        command_key=command_key,
        ignore_paths=tuple(ignore_paths),
    )
    with TargetDirectory(Path(target_dir)) as target_root:
        return _check_record(request, target_root)


def _check_record(
    request: CheckRequest, target_root: TargetDirectory
) -> tuple[int, dict[str, object]]:
    root = request.root
    package = request.package
    profile = request.profile
    target = request.target
    features = request.features
    artifact_paths = validate_artifact_paths(target_root, request.artifact_paths)
    manifest = request.manifest
    command = request.command
    execution_root = request.execution_root
    command_key = request.command_key
    ignore_paths = request.ignore_paths
    if manifest is None and not artifact_paths:
        raise BuildIdentityError(
            "manifest is required for dependency closure resolution"
        )
    target_dir = target_root.path
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
    record_file = records.record_path(spec)
    with ExitStack() as probes:
        acquired = True
        for lock, _owner in package_target_lease_scopes(
            spec.package,
            target_dir,
            spec.source.root,
            spec.source.revision,
            tuple(str(value) for value in dependencies["clean_packages"]),
        ):
            if not probes.enter_context(LeaseProbe(target_root, lock)):
                acquired = False
        if not acquired:
            return 3, {"status": "owned", "record": record_file.as_posix()}
        locked_dependencies = _dependency_data(
            manifest or Path(),
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
            return 2, {"status": "stale", "record": record_file.as_posix()}
        existing = records.read_record(target_root, record_file)
        if existing is None:
            return 2, {"status": "missing", "record": record_file.as_posix()}
        try:
            current = artifact_identity(
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
            return 2, {"status": "stale", "record": record_file.as_posix()}
        final_dependencies = _dependency_data(
            manifest or Path(),
            package,
            target_dir,
            execution_root,
            ignore_paths,
            bool(artifact_paths),
        )
        final_spec = build_spec(
            root,
            package,
            target_dir,
            profile,
            target,
            features,
            command,
            command_key,
            ignore_paths,
            str(final_dependencies["digest"]),
        )
        if final_dependencies != dependencies or final_spec.as_dict() != spec.as_dict():
            return 2, {"status": "stale", "record": record_file.as_posix()}
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
