"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Sequence

from atlas_build_artifacts import (
    artifact_digest,
    artifact_identity,
    changed_packages,
    dependency_snapshot,
    discover_artifacts,
    recorded_artifact_identity,
    validate_artifact_paths,
)
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    BuildIdentityError,
    LeaseProbe,
    OwnerLease,
    acquire_waiting,
    lease_is_held,
    package_target_lease_path,
    package_target_lease_scopes,
)
from atlas_build_source import (
    SourceIdentity,
    environment_digest,
    source_identity,
    toolchain_identity,
)

VERSION = 3
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


def _content(record: object) -> object:
    """A source or build record without the checkout path it was read from.

    The pre-push gate builds a fresh export of the pushed revision at a new
    temporary path on every run, so a record keyed on that path was stale on
    every push and cleaned the whole non-registry closure. Content -- the
    revision, the tree digest, the build dimensions -- decides staleness; the
    root stays in the record for diagnostics and lease ownership only.
    """
    if not isinstance(record, dict):
        return record
    value = {key: item for key, item in record.items() if key != "root"}
    if isinstance(value.get("source"), dict):
        value["source"] = _content(value["source"])
    return value


def _record_matches(
    existing: dict[str, object],
    spec: BuildSpec,
    dependencies: dict[str, object],
    artifact: dict[str, object],
) -> bool:
    return (
        _content(existing.get("source")) == _content(spec.source.as_dict())
        and _content(existing.get("build")) == _content(spec.as_dict())
        and existing.get("dependencies") == dependencies
        and existing.get("artifact") == artifact
    )


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
    canonical_target = _canonical(target_dir)
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
            "clean_packages": [package],
        }
    else:
        source_cache: dict[Path, dict[str, object]] = {}

        def identify_source(path: Path) -> dict[str, object]:
            canonical_path = _canonical(path)
            if canonical_path not in source_cache:
                identified = source_identity(canonical_path, (target_dir,), ignore_paths)
                source_cache[canonical_path] = _content(identified.as_dict())
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


def _spec_key(spec: BuildSpec) -> str:
    scope = spec.as_dict()
    scope.pop("source")
    scope.pop("dependency_digest")
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def record_path(spec: BuildSpec) -> Path:
    return Path(spec.target_dir) / ".atlas" / "source-identity" / f"{_spec_key(spec)}.json"


def _sibling_matches(spec: BuildSpec) -> bool:
    build = spec.as_dict()
    build.pop("command_key")
    directory = record_path(spec).parent
    if not directory.is_dir():
        return False
    for candidate in directory.glob("*.json"):
        try:
            record = read_record(candidate)
        except IdentityError:
            continue
        if record is None:
            continue
        other = record.get("build")
        if not isinstance(other, dict):
            continue
        other = dict(other)
        other.pop("command_key", None)
        if _content(other) == _content(build) and _content(record.get("source")) == _content(
            spec.source.as_dict()
        ):
            return True
    return False


def _recorded_artifact(
    existing: dict[str, object], target_dir: Path, artifact_paths: Sequence[Path]
) -> dict[str, object] | None:
    """The record's artifacts as they are now, or None when one cannot be read.

    Only the files the record names are hashed, so a variant another build
    writes beside them does not change the result.
    """
    recorded = existing.get("artifact")
    if not isinstance(recorded, dict) or not isinstance(recorded.get("files"), dict):
        return None
    names = recorded["files"].keys()
    if artifact_paths and set(names) != {
        path.relative_to(target_dir).as_posix() for path in artifact_paths
    }:
        return None
    try:
        return recorded_artifact_identity(target_dir, names)
    except IdentityError:
        return None


def lease_path(spec: BuildSpec) -> Path:
    return package_target_lease_path(spec.package, Path(spec.target_dir))


def read_record(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityError(f"malformed source identity record {path}: {error}") from error
    version = value.get("version") if isinstance(value, dict) else None
    if type(version) is int and version in {1, 2}:
        return None
    if not isinstance(value, dict) or type(version) is not int or version != VERSION:
        raise IdentityError(f"unsupported source identity record: {path}")
    source = value.get("source")
    build = value.get("build")
    artifact = value.get("artifact")
    dependencies = value.get("dependencies")
    if (
        not isinstance(source, dict)
        or not isinstance(build, dict)
        or not isinstance(artifact, dict)
        or not isinstance(dependencies, dict)
    ):
        raise IdentityError(f"malformed source identity record: {path}")
    if any(type(source.get(key)) is not str for key in ("root", "revision", "tree_digest")):
        raise IdentityError(f"malformed source identity record: {path}")
    if type(source.get("dirty")) is not bool:
        raise IdentityError(f"malformed source identity record: {path}")
    if any(
        type(build.get(key)) is not str
        for key in (
            "package",
            "profile",
            "target",
            "features",
            "toolchain",
            "target_dir",
            "command_key",
            "environment_digest",
            "dependency_digest",
        )
    ):
        raise IdentityError(f"malformed source identity record: {path}")
    files = artifact.get("files")
    if type(files) is not dict or any(type(key) is not str or type(value) is not str for key, value in files.items()):
        raise IdentityError(f"malformed source identity record: {path}")
    if type(artifact.get("digest")) is not str:
        raise IdentityError(f"malformed source identity record: {path}")
    if (
        type(dependencies.get("root")) is not str
        or type(dependencies.get("digest")) is not str
        or type(dependencies.get("packages")) is not list
        or type(dependencies.get("edges")) is not list
        or type(dependencies.get("clean_packages")) is not list
        or any(type(value) is not str for value in dependencies["clean_packages"])
    ):
        raise IdentityError(f"malformed source identity record: {path}")
    return value


def _write_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(value, sort_keys=True, indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as cleanup_error:
            raise IdentityError(
                f"cannot write source identity record {path}: {error}; cleanup failed: {cleanup_error}"
            ) from error
        raise IdentityError(f"cannot write source identity record {path}: {error}") from error


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
    lease_wait_seconds: float = 0,
) -> BuildResult:
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = _canonical(target_dir)
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
    clean_packages = tuple(str(value) for value in dependencies["clean_packages"])
    scopes = package_target_lease_scopes(
        spec.package, target_dir, spec.source.root, spec.source.revision, clean_packages
    )
    # One bound for the whole run, across every lease and both phases.
    deadline_ns = time.monotonic_ns() + int(lease_wait_seconds * 1_000_000_000)

    def acquire(exclusive: bool) -> ExitStack:
        # The command writes its own package; dependencies are only read
        # unless the record shows the run must clean or rebuild them.
        stack = ExitStack()
        try:
            for lock, owner in scopes:
                mode = EXCLUSIVE if exclusive or owner["package"] == spec.package else SHARED
                stack.push(
                    acquire_waiting(
                        OwnerLease(lock, owner, lease_seconds, mode),
                        lease_wait_seconds,
                        deadline_ns,
                    )
                )
        except BaseException:
            stack.close()
            raise
        return stack

    def locked_record() -> tuple[dict[str, object] | None, bool, dict[str, object] | None]:
        locked_dependencies = _dependency_data(
            manifest, package, target_dir, execution_root, ignore_paths, bool(artifact_paths)
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
        if existing is None:
            return None, False, None
        current = _recorded_artifact(existing, target_dir, artifact_paths)
        return existing, _record_matches(existing, spec, dependencies, current), current

    with ExitStack() as leases:
        shared = leases.enter_context(acquire(exclusive=False))
        existing, matched, current = locked_record()
        if not matched:
            # Anything but an exact match may write dependency artifacts, so
            # it runs exclusive. Releasing before asking again, rather than
            # upgrading in place, keeps two upgraders from each holding the
            # shared lease the other waits for; the record is read again
            # because a holder may have rebuilt it meanwhile.
            shared.close()
            leases.enter_context(acquire(exclusive=True))
            existing, matched, current = locked_record()
        stale = not matched and (existing is not None or not _sibling_matches(spec))
        if stale:
            if clean_command is not None:
                _run_checked(clean_command, execution_root, environment)
            else:
                targets = clean_packages
                if (
                    existing is not None
                    and current is not None
                    and _record_matches(existing, spec, dependencies, existing.get("artifact"))
                ):
                    # Only artifact bytes changed. Cleaning the packages that
                    # own them is enough: Cargo rebuilds every unit whose
                    # dependency it rebuilds, so their dependents follow.
                    narrowed = changed_packages(
                        existing["artifact"]["files"],
                        current["files"],
                        manifest,
                        execution_root,
                        clean_packages,
                    )
                    if narrowed:
                        targets = tuple(sorted(narrowed))
                for clean_package in targets:
                    _run_checked(
                        [
                            *_cargo_command(),
                            "clean",
                            "-p",
                            clean_package,
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
            manifest, package, target_dir, execution_root, ignore_paths, bool(artifact_paths)
        )
        if final_dependencies != dependencies:
            raise IdentityError("dependency graph changed while the build was running")
        if matched and not artifact_paths:
            # Only the package held exclusive is hashed again. Another
            # reader's Cargo may be rewriting a dependency's files in place
            # right now, so they keep the digests verified before the
            # command; the next run's comparison re-hashes them.
            own = recorded_artifact_identity(
                target_dir,
                [
                    path.relative_to(target_dir).as_posix()
                    for path in discover_artifacts(
                        target_dir, package, profile, target, manifest, execution_root
                    )
                ],
            )
            files = {**existing["artifact"]["files"], **own["files"]}
            artifact = {"files": files, "digest": artifact_digest(files)}
        else:
            artifact = artifact_identity(
                root,
                target_dir,
                package,
                profile,
                artifact_paths,
                target,
                manifest,
                execution_root,
                clean_packages,
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
    target_dir = _canonical(target_dir)
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
