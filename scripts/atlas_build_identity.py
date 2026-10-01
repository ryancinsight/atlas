"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import os
import subprocess
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from atlas_build_artifacts import (
    artifact_digest,
    artifact_identity,
    artifact_owners,
    artifact_package,
    discover_artifacts,
    SETTLE_SECONDS,
    recorded_artifact_identity,
    settled_digest,
    validate_artifact_paths,
)
from atlas_build_inputs import _dependency_data, build_spec
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    BuildIdentityError,
    LeaseProbe,
    OwnerLease,
    acquire_waiting,
    package_target_lease_path,
    package_target_lease_scopes,
)
from atlas_build_records import (
    VERSION,
    BuildSpec,
    _record_matches,
    _recorded_artifact,
    _sibling_record,
    _write_atomic,
    read_record,
    record_path,
)
from atlas_build_source import _canonical, source_identity
from atlas_build_stale_packages import _path_packages, _stale_packages
from atlas_build_stamps import (
    BuildDirectory,
    _git_names,
    _stale_git,
    _unstamped_git,
    _write_git_stamps,
)

DEFAULT_LEASE_SECONDS = 900


IdentityError = BuildIdentityError


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
    lease_wait_seconds: float = 0,
) -> BuildResult:
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = _canonical(target_dir)
    directory = BuildDirectory(target_dir, profile, target)
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
        execution_root,
    )
    record = record_path(spec)
    environment = dict(os.environ)
    environment["CARGO_TARGET_DIR"] = target_dir.as_posix()
    cleaned = False
    clean_packages = tuple(str(value) for value in dependencies["clean_packages"])
    recorded_packages = {*_path_packages(dependencies), spec.package}
    scopes = package_target_lease_scopes(
        spec.package, target_dir, spec.source.root, spec.source.revision, clean_packages
    )
    # One bound for acquiring every lease, across both phases.
    deadline_ns = time.monotonic_ns() + int(lease_wait_seconds * 1_000_000_000)

    taken: list[OwnerLease] = []

    def acquire(exclusive: frozenset[str]) -> ExitStack:
        # The command writes its own package; a dependency is only read
        # unless the record shows the run must clean or rebuild it.
        stack = ExitStack()
        taken.clear()
        try:
            for lock, owner in scopes:
                mode = (
                    EXCLUSIVE
                    if owner["package"] == spec.package or owner["package"] in exclusive
                    else SHARED
                )
                lease = acquire_waiting(
                    OwnerLease(lock, owner, lease_seconds, mode),
                    lease_wait_seconds,
                    deadline_ns,
                )
                stack.push(lease)
                taken.append(lease)
        except BaseException:
            stack.close()
            raise
        return stack

    def locked_record() -> tuple[
        dict[str, object] | None, bool, dict[str, object] | None, set[str]
    ]:
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
            execution_root,
        )
        if locked_dependencies != dependencies or locked_spec.as_dict() != spec.as_dict():
            raise IdentityError(
                "source or dependency inputs changed while acquiring the package leases"
            )
        stale_git = _stale_git(dependencies, directory)
        existing = read_record(record)
        if existing is None:
            return None, False, None, stale_git
        current = _recorded_artifact(existing, target_dir, artifact_paths)
        matched = _record_matches(existing, spec, dependencies, current) and not stale_git
        return existing, matched, current, stale_git

    def clean_targets(
        existing: dict[str, object] | None, current: dict[str, object] | None
    ) -> tuple[str, ...]:
        # A caller's clean command is opaque, so it may touch the whole closure.
        if clean_command is not None:
            return clean_packages
        return _stale_packages(existing, current, spec, dependencies, manifest, execution_root)

    with ExitStack() as leases:
        shared = leases.enter_context(acquire(frozenset()))
        existing, matched, current, stale_git = locked_record()
        held: frozenset[str] = frozenset()
        if not matched:
            # A mismatch may write the artifacts of the packages it cleans, so
            # those run exclusive; every other dependency stays shared. Releasing
            # before asking again, rather than upgrading in place, keeps two
            # upgraders from each holding the shared lease the other waits
            # for; the record is read again because a holder may have rebuilt
            # it meanwhile.
            held = frozenset(clean_targets(existing, current))
            shared.close()
            exclusive = leases.enter_context(acquire(held))
            existing, matched, current, stale_git = locked_record()
            # The re-read may name packages the first read did not: widen to
            # them and read again, so nothing is cleaned under a shared lease.
            while not matched and not held.issuperset(clean_targets(existing, current)):
                held = held | frozenset(clean_targets(existing, current))
                exclusive.close()
                exclusive = leases.enter_context(acquire(held))
                existing, matched, current, stale_git = locked_record()
        sibling = None if matched or existing is not None else _sibling_record(spec)
        # A sibling's record stands in for this run's path packages, never
        # for the target's stale Git packages, which are cleaned regardless.
        stale = not matched and (existing is not None or sibling is None or bool(stale_git))
        # The packages the clean left for the command to rebuild, and the
        # recorded files as read under this run's leases, by the names a
        # record lists: this run's own when it has one, else a sibling's. A
        # path package the clean left alone always has a readable record
        # naming it (`_stale_packages` cleans every one otherwise), and a
        # sibling whose files cannot all be read names none.
        rebuilt: tuple[str, ...] = ()
        named = current if matched else None
        if sibling is not None:
            named = _recorded_artifact(sibling, target_dir, ())
        # Git packages this run builds: the stale ones it cleans, and the
        # unstamped ones it trusts. Each is stamped as building before the
        # clean and the command, and with its content only after both.
        git_built = _unstamped_git(dependencies, directory)
        if stale:
            if clean_command is not None:
                _run_checked(clean_command, execution_root, environment)
                # Opaque, so it may have cleaned everything it held; only the
                # stale Git packages are certainly cleaned, by Cargo below.
                rebuilt = tuple(sorted(held))
                targets = tuple(sorted(held & stale_git))
            else:
                # The widen loop's converged set, never recomputed: every
                # package this run cleans was held exclusive by that loop, so
                # cleaning it here can never reach past that set. A sibling's
                # record stands in for the path packages, never for the
                # stale Git packages.
                targets = tuple(sorted(held if sibling is None else held & stale_git))
                rebuilt = targets
                if sibling is None:
                    named = current
            git_built |= set(targets) & _git_names(dependencies)
            _write_git_stamps(dependencies, directory, git_built, building=True)
            # One invocation for the whole closure: each `cargo clean` walks
            # the entire shared target whatever it deletes, so one call per
            # package held the closure's exclusive leases for minutes per
            # package (about 2.5 min each on the stack target) and a stale
            # metis record stalled every push that shared its dependencies
            # for over an hour. A `cargo clean` naming no package would clean
            # everything.
            if targets:
                _run_checked(
                    [
                        *_cargo_command(),
                        "clean",
                        *(argument for clean_package in targets for argument in ("-p", clean_package)),
                        *directory.clean_arguments(),
                        "--manifest-path",
                        str(manifest),
                    ],
                    execution_root,
                    environment,
                )
            cleaned = True
        else:
            _write_git_stamps(dependencies, directory, git_built, building=True)
        # The packages whose artifacts this run writes and discovers afresh.
        fresh = {spec.package, *rebuilt}
        if (named is not None or recorded_packages <= fresh) and not artifact_paths:
            # The command rebuilds what was cleaned, so those scopes stay
            # exclusive; every other scope is only read from here on, as on a
            # matched run, and peers sharing it enter while the command runs.
            # The downgrade keeps each lease's place in the queue, so no
            # writer queued meanwhile can clean between the clean and the
            # command.
            for lease in taken:
                if lease.owner["package"] not in fresh and lease.mode == EXCLUSIVE:
                    lease.downgrade()
        # Path packages read shared, whose files are hashed by the names a
        # record lists rather than discovered.
        shared_recorded = recorded_packages & {
            str(lease.owner["package"]) for lease in taken if lease.mode == SHARED
        }
        if shared_recorded and named is None and not artifact_paths:
            raise IdentityError(
                "a dependency is held shared but no record names its artifacts"
            )
        _run_checked(command, execution_root, environment)
        final_source = source_identity(root, (target_dir,), ignore_paths)
        if final_source.as_dict() != spec.source.as_dict():
            raise IdentityError("source tree changed while the build was running")
        final_dependencies = _dependency_data(
            manifest, package, target_dir, execution_root, ignore_paths, bool(artifact_paths)
        )
        if final_dependencies != dependencies:
            raise IdentityError("dependency graph changed while the build was running")
        # The checkout content is the snapshot's, unchanged across the build.
        _write_git_stamps(dependencies, directory, git_built, building=False)
        if shared_recorded and not artifact_paths:
            # Peers read, and their Cargo may rewrite, every path package this
            # run holds shared, so those are found by the names `named` lists,
            # never by discovery, and each is hashed again once two reads
            # agree: the command rebuilt them in place (a fresh export has
            # fresh mtimes, and rustc embeds its path in the bytes). A file
            # that never settles is recorded unverified, and one that cannot
            # be read at all keeps its digest read before the command. Only
            # the path packages held exclusive are discovered afresh, and
            # their recorded names are dropped, so a name their rebuild
            # retired is not kept.
            owners = artifact_owners(manifest, execution_root)
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
                        execution_root,
                        tuple(sorted(recorded_packages - shared_recorded)),
                        owners,
                    )
                ],
            )
            files = {}
            for relative, verified in named["files"].items():
                if artifact_package(relative, owners) not in shared_recorded:
                    continue
                # Each file gets up to SETTLE_SECONDS, never past the run's
                # wait deadline; at least two reads are always attempted.
                budget = min(time.monotonic_ns() + int(SETTLE_SECONDS * 1_000_000_000), deadline_ns)
                settled = settled_digest(target_dir / relative, budget)
                files[relative] = verified if settled is None else settled
            files.update(own["files"])
            artifact = {"files": files, "digest": artifact_digest(files)}
        else:
            # Declared paths are hashed as named; otherwise every recorded
            # package is held exclusive, so each is discovered.
            artifact = artifact_identity(
                root,
                target_dir,
                package,
                profile,
                artifact_paths,
                target,
                manifest,
                execution_root,
                tuple(sorted(recorded_packages)),
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
