"""Whether a build's identity record matches its source, without building."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Sequence

from atlas_build_artifacts import validate_artifact_paths
from atlas_build_inputs import _dependency_data, build_spec
from atlas_build_lease import BuildIdentityError as IdentityError
from atlas_build_lease import LeaseProbe, package_target_lease_scopes
from atlas_build_records import _record_matches, _recorded_artifact, read_record, record_path
from atlas_build_source import _canonical


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
    target_dir = _canonical(target_dir)
    artifact_paths = validate_artifact_paths(target_dir, artifact_paths)
    if manifest is None and not artifact_paths:
        raise IdentityError("manifest is required for dependency closure resolution")
    execution_root = _canonical(command_cwd or root, strict=True)
    dependencies = _dependency_data(
        manifest or Path(),
        (package,),
        target_dir,
        execution_root,
        ignore_paths,
        bool(artifact_paths),
    )[package]
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
        execution_root,
    )
    record_file = record_path(spec)
    with ExitStack() as probes:
        acquired = True
        for lock, _owner in package_target_lease_scopes(
            spec.package,
            target_dir,
            spec.source.root,
            spec.source.revision,
            tuple(str(value) for value in dependencies["clean_packages"]),
        ):
            if not probes.enter_context(LeaseProbe(lock)):
                acquired = False
        if not acquired:
            return 3, {"status": "owned", "record": record_file.as_posix()}
        existing = read_record(record_file)
        if existing is None:
            return 2, {"status": "missing", "record": record_file.as_posix()}
        matches = _record_matches(
            existing, spec, dependencies, _recorded_artifact(existing, target_dir, artifact_paths)
        )
        return (0 if matches else 2), {
            "status": "match" if matches else "stale",
            "record": record_file.as_posix(),
        }
