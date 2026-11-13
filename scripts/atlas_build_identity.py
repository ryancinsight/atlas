"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

from atlas_build_artifacts import (
    ARTIFACT_CENSUS_SECONDS,
    changed_packages,
    artifact_identities,
    artifact_identity,
    artifact_owners,
    prune_plan,
    prune_units,
    recorded_artifact_identity,
    shared_artifact_identity,
    validate_artifact_paths,
)
from atlas_build_dep_info import current_inputs, package_layout, record_inputs
from atlas_build_inputs import (
    _config_arguments,
    _dependency_data,
    build_spec,
    compiler_environment,
    effective_compiler_command,
    effective_compiler_environment,
)
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    BuildIdentityError,
    OwnerLease,
    acquire_claim,
    package_target_lease_path,
    package_target_lease_scopes,
)
from atlas_build_records import (
    VERSION,
    BuildSpec,
    _record_matches,
    _record_mismatch_reasons,
    _recorded_artifact,
    _sibling_records,
    _write_atomic,
    read_record,
    record_path,
)
from atlas_build_source import _canonical, overlay_stripped_configs, source_identity
from atlas_build_stale_packages import (
    PackageState,
    _artifact_only_packages,
    _path_packages,
    _stale_packages,
)
from atlas_build_stamps import (
    BuildDirectory,
    _git_names,
    _stale_git,
    _unstamped_git,
    _write_git_stamps,
)
from atlas_build_writers import (
    BUILDING,
    CLEANING,
    COMPLETE,
    heartbeat,
    mark,
    mark_broad_clean,
    resumable,
    run_identity,
)

DEFAULT_LEASE_SECONDS = 900
_CLEAN_PLAN_PREFIX = "atlas-build-clean-plan: "
_PROGRESS_DIR_ENV = "ATLAS_GATE_PROGRESS_DIR"
_PROGRESS_STAGES = (
    "pre-command",
    "cleanup",
    "command",
    "source-dependencies",
    "git-stamps",
    "census-inputs",
    "publication",
)


IdentityError = BuildIdentityError


def _progress_directory() -> Path | None:
    value = os.environ.get(_PROGRESS_DIR_ENV)
    if value is None:
        return None
    progress = Path(value)
    if not progress.is_absolute() or not progress.is_dir():
        raise IdentityError(f"{_PROGRESS_DIR_ENV} must name an existing absolute directory")
    return progress


def _progress_now_ns() -> int:
    """Read the monotonic clock used by every progress-stage boundary."""
    return time.monotonic_ns()


class _ProgressSidecar:
    """Atomically retain diagnostic stage timing without certifying artifacts."""

    def __init__(self, run_id: str) -> None:
        self._path: Path | None = None
        self._run_id = run_id
        self._origin_ns: int | None = None
        self._stages: list[dict[str, object]] = []
        try:
            progress = _progress_directory()
            if progress is None:
                return
            self._path = progress / f"identity-progress-{run_id}.json"
            self._origin_ns = _progress_now_ns()
            self._stages.append(
                {"name": _PROGRESS_STAGES[0], "started_after_ns": 0, "status": "running"}
            )
            self._publish("incomplete")
        except Exception:
            self._path = None

    def advance(self, stage: str) -> None:
        """Complete the current stage and start `stage` at one clock reading."""
        if self._path is None:
            return
        try:
            if stage != _PROGRESS_STAGES[len(self._stages)]:
                raise IdentityError(f"unexpected build progress stage: {stage}")
            elapsed = self._elapsed_ns()
            current = self._stages[-1]
            current["completed_after_ns"] = elapsed
            current["status"] = "completed"
            self._stages.append(
                {"name": stage, "started_after_ns": elapsed, "status": "running"}
            )
            self._publish("incomplete")
        except Exception:
            self._path = None

    def fail(self, error: BaseException) -> None:
        """Retain the incomplete stage when the identity run raises."""
        if self._path is None:
            return
        try:
            current = self._stages[-1]
            current["completed_after_ns"] = self._elapsed_ns()
            current["status"] = "failed"
            self._publish("incomplete", type(error).__name__)
        except Exception:
            self._path = None

    def finish(self) -> None:
        """Complete publication while keeping the sidecar diagnostic-only."""
        if self._path is None:
            return
        try:
            current = self._stages[-1]
            current["completed_after_ns"] = self._elapsed_ns()
            current["status"] = "completed"
            self._publish("complete")
        except Exception:
            self._path = None

    def _elapsed_ns(self) -> int:
        if self._origin_ns is None:
            raise IdentityError("build progress clock has no origin")
        return _progress_now_ns() - self._origin_ns

    def _publish(self, disposition: str, failure: str | None = None) -> None:
        if self._path is None or self._origin_ns is None:
            return
        payload: dict[str, object] = {
            "certifies_artifacts": False,
            "clock": "monotonic_ns",
            "disposition": disposition,
            "origin_ns": self._origin_ns,
            "run": self._run_id,
            "schema": 1,
            "stages": self._stages,
        }
        if failure is not None:
            payload["failure"] = failure
        _write_atomic(self._path, payload, replace_attempts=1)


def _emit_clean_plan(payload: dict[str, object], run_id: str) -> None:
    """Emit one decision and retain it atomically when the gate owns progress."""
    progress = _progress_directory()
    if progress is not None:
        _write_atomic(progress / f"clean-plan-{run_id}.json", payload)
    print(
        _CLEAN_PLAN_PREFIX
        + json.dumps(payload, sort_keys=True, separators=(",", ":")),
        file=sys.stderr,
        flush=True,
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
    packages: Sequence[str],
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
    selection: Sequence[str] = (),
    *,
    clean_config: Sequence[str] = (),
) -> tuple[BuildResult, ...]:
    """Run a build under the manifest's effective compiler environment."""
    if clean_config and (clean_command is not None or tuple(clean_config) != _config_arguments(command)):
        raise IdentityError("cleanup Cargo config differs from the bound command")
    run_id = uuid.uuid4().hex
    progress = _ProgressSidecar(run_id)
    try:
        execution_root = _canonical(command_cwd or root, strict=True)
        environment = effective_compiler_environment(manifest, execution_root, command)
        command = effective_compiler_command(command, environment)
        environment["CARGO_TARGET_DIR"] = _canonical(target_dir).as_posix()
        with compiler_environment(environment):
            with overlay_stripped_configs(execution_root):
                result = _run_build(
                    root,
                    manifest,
                    packages,
                    target_dir,
                    command,
                    profile,
                    target,
                    features,
                    artifact_paths,
                    clean_command,
                    lease_seconds,
                    command_cwd,
                    command_key,
                    ignore_paths,
                    lease_wait_seconds,
                    selection,
                    clean_config=clean_config,
                    run_id=run_id,
                    progress=progress,
                )
    except BaseException as error:
        progress.fail(error)
        raise
    progress.finish()
    return result


def _run_build(
    root: Path,
    manifest: Path,
    packages: Sequence[str],
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
    selection: Sequence[str] = (),
    *,
    run_id: str,
    progress: _ProgressSidecar,
    clean_config: Sequence[str],
) -> tuple[BuildResult, ...]:
    """Run `command` once for `packages`, binding each one's record to it.

    The command builds every package in one invocation (`cargo clippy -p a
    -p b`), so the run reads its inputs, takes its leases and waits for
    cargo once, not once per package. Each package keeps its own record and
    the clean rule applies per package: one stale record cleans what that
    package's rule names, never the others' closures. Results are in
    `packages` order.

    `packages` are the packages whose artifacts the run records. `selection`
    is every package the command builds (default: `packages`), and a record
    is keyed on it, since Cargo unifies features across an invocation's
    packages and so names a shared dependency's variant by the whole set.
    The steps of one push name one selection, so they share their records;
    a step whose command builds a package that writes no artifact of its own
    (no test target, no documented target) lists it in `selection` only.
    """
    if isinstance(packages, str):
        raise IdentityError("packages must be a sequence of package names, not one string")
    packages = tuple(dict.fromkeys(packages))
    if not packages:
        raise IdentityError("at least one package is required")
    selection = tuple(dict.fromkeys(selection)) or packages
    if not set(packages) <= set(selection):
        raise IdentityError(f"packages {packages} are not all in the selection {selection}")
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = _canonical(target_dir)
    directory = BuildDirectory(target_dir, profile, target)
    artifact_paths = validate_artifact_paths(target_dir, artifact_paths)
    if artifact_paths and len(packages) != 1:
        # Declared paths are one package's artifacts; a record per package
        # could not say which of them each package owns.
        raise IdentityError("declared artifact paths need exactly one package")
    execution_root = _canonical(command_cwd or root, strict=True)

    def read_inputs() -> dict[str, tuple[dict[str, object], BuildSpec]]:
        # One `cargo metadata` and one root source identity for the whole
        # package set; only the package and its closure digest differ.
        snapshots = _dependency_data(
            manifest, packages, target_dir, execution_root, ignore_paths, bool(artifact_paths)
        )
        first = build_spec(
            root,
            packages[0],
            target_dir,
            profile,
            target,
            features,
            command,
            command_key,
            ignore_paths,
            str(snapshots[packages[0]]["digest"]),
            execution_root,
            selection,
        )
        return {
            package: (
                snapshots[package],
                replace(first, package=package, dependency_digest=str(snapshots[package]["digest"])),
            )
            for package in packages
        }

    inputs = read_inputs()
    first_spec = inputs[packages[0]][1]
    writer_identity = run_identity(
        first_spec, {package: str(inputs[package][0]["digest"]) for package in packages}
    )
    records = {package: record_path(spec) for package, (_, spec) in inputs.items()}
    environment = dict(os.environ)
    environment["CARGO_TARGET_DIR"] = target_dir.as_posix()
    clean_packages = {
        package: tuple(str(value) for value in dependencies["clean_packages"])
        for package, (dependencies, _) in inputs.items()
    }
    recorded_packages = {
        package: {*_path_packages(dependencies), package}
        for package, (dependencies, _) in inputs.items()
    }
    scopes = {
        lock: owner
        for package in packages
        for lock, owner in package_target_lease_scopes(
            package,
            target_dir,
            first_spec.source.root,
            first_spec.source.revision,
            clean_packages[package],
        )
    }
    # Read once, and only when a record lists a unit's dep-info or an input.
    layout = functools.cache(lambda: package_layout(manifest, execution_root, target_dir))
    # One bound for acquiring every lease, across both phases, and the run's
    # place in every queue, fixed by the same clock read: `(arrival, run)`.
    arrival_ns = time.monotonic_ns()
    deadline_ns = arrival_ns + int(lease_wait_seconds * 1_000_000_000)

    taken: list[OwnerLease] = []
    phases = [0]

    def acquire(exclusive: frozenset[str]) -> ExitStack:
        # The command writes its own packages; a dependency is only read
        # unless a record shows the run must clean or rebuild it. Every lease
        # is taken at once, under the run's arrival, so a run that cannot take
        # them waits holding none and each phase keeps the run's place.
        leases = [
            OwnerLease(
                lock,
                owner,
                lease_seconds,
                EXCLUSIVE if owner["package"] in packages or owner["package"] in exclusive else SHARED,
            )
            for lock, owner in sorted(scopes.items(), key=lambda item: str(item[1]["package"]))
        ]
        phases[0] += 1
        stack = acquire_claim(
            leases, lease_wait_seconds, deadline_ns, arrival_ns, run_id, phases[0]
        )
        taken[:] = leases
        return stack

    def locked_records() -> dict[str, PackageState]:
        if read_inputs() != inputs:
            raise IdentityError(
                "source or dependency inputs changed while acquiring the package leases"
            )
        states = {}
        for package, (dependencies, spec) in inputs.items():
            stale_git = _stale_git(dependencies, directory)
            existing = read_record(records[package])
            if existing is None:
                states[package] = PackageState(None, False, None, stale_git, {})
                continue
            current = _recorded_artifact(existing, target_dir, artifact_paths)
            now = current_inputs(existing.get("inputs"), layout)
            matched = _record_matches(existing, spec, dependencies, current, now) and not stale_git
            states[package] = PackageState(existing, matched, current, stale_git, now)
        return states

    owners_read: list[dict[str, frozenset[str]]] = []

    def workspace_owners() -> dict[str, frozenset[str]]:
        # One `cargo metadata` serves every attribution of the run: the graph
        # is checked unchanged across it.
        if not owners_read:
            owners_read.append(artifact_owners(manifest, execution_root))
        return owners_read[0]

    def clean_targets(package: str, state: PackageState) -> frozenset[str]:
        # A caller's clean command is opaque, so it may touch the whole closure.
        if clean_command is not None:
            return frozenset(clean_packages[package])
        dependencies, spec = inputs[package]
        return frozenset(
            _stale_packages(
                state.existing,
                state.current,
                spec,
                dependencies,
                manifest,
                execution_root,
                state.inputs,
                workspace_owners() if not artifact_paths else None,
            )
        )

    # What each package's rule has asked to clean across every read: a read
    # only ever adds, so the leases never narrow below an earlier answer.
    asked: dict[str, frozenset[str]] = {package: frozenset() for package in packages}

    def widen(states: dict[str, PackageState]) -> frozenset[str]:
        for package, state in states.items():
            if not state.matched:
                asked[package] |= clean_targets(package, state)
        return frozenset().union(*asked.values())

    with ExitStack() as leases:
        shared = leases.enter_context(acquire(frozenset()))
        states = locked_records()
        held: frozenset[str] = frozenset()
        if not all(state.matched for state in states.values()):
            # A mismatch may write the artifacts of the packages it cleans, so
            # those run exclusive; every other dependency stays shared. Releasing
            # before asking again, rather than upgrading in place, keeps two
            # upgraders from each holding the shared lease the other waits
            # for; the records are read again because a holder may have
            # rebuilt them meanwhile.
            held = widen(states)
            shared.close()
            exclusive = leases.enter_context(acquire(held))
            states = locked_records()
            # The re-read may name packages the first read did not: widen to
            # them and read again, so nothing is cleaned under a shared lease.
            while not held.issuperset(widen(states)):
                held = held | widen(states)
                exclusive.close()
                exclusive = leases.enter_context(acquire(held))
                states = locked_records()
        # Every verifying sibling, since units one lists alone are not another's to prune.
        found = {
            package: []
            if state.matched
            else list(
                _sibling_records(
                    inputs[package][1], inputs[package][0],
                    lambda record: current_inputs(record["inputs"], layout) == record["inputs"],
                )
            )
            for package, state in states.items()
        }
        siblings = {
            package: next((record for record in records if record.verified), None)
            for package, records in found.items()
        }
        # A sibling's record stands in for a package's path packages, never
        # for the target's stale Git packages, which are cleaned regardless.
        stale = {
            package: not state.matched
            and (siblings[package] is None or bool(state.stale_git))
            for package, state in states.items()
        }
        # The files each record lists, as read under this run's leases: its
        # own when it has one, else a sibling's. A path package the clean
        # leaves alone always has a readable record naming it
        # (`_stale_packages` cleans every one otherwise), and a sibling whose
        # files cannot all be read names none.
        named: dict[str, dict[str, object] | None] = {
            package: state.current if state.matched else None for package, state in states.items()
        }
        for package, sibling in siblings.items():
            if sibling is not None:
                named[package] = sibling.artifact
        # Git packages this run builds: the stale ones it cleans, and the
        # unstamped ones it trusts. Each is stamped as building before the
        # clean and the command, and with its content only after both.
        git_built = {
            package: _unstamped_git(dependencies, directory)
            for package, (dependencies, _) in inputs.items()
        }
        rebuilt: frozenset[str] = frozenset()
        # Packages an earlier run of this identity cleaned and was killed
        # while rebuilding: held exclusive and discovered afresh like the
        # cleaned ones, but not cleaned again. A stale Git stamp still cleans.
        resumed: frozenset[str] = frozenset()
        targets: frozenset[str] = frozenset()
        owned: dict[str, frozenset[str]] = {}
        prune_paths: list[Path] = []
        marked: frozenset[str] = frozenset()
        custom_clean = False
        if any(stale.values()):
            marked = resumable(directory, held, writer_identity) - frozenset().union(
                *(state.stale_git for state in states.values())
            )
            if clean_command is not None:
                # Opaque, so it may have cleaned everything it held; only the
                # stale Git packages are certainly cleaned, by Cargo below.
                targets = held & frozenset().union(
                    *(states[package].stale_git for package in packages if stale[package])
                )
                if held <= marked and not targets:
                    resumed = held
                else:
                    custom_clean = True
                    rebuilt = held
            else:
                # Each stale package cleans what its own rule asked for in the
                # widen loop, never recomputed: every package cleaned here was
                # held exclusive by that loop. A sibling's record stands in for
                # the path packages, never for the stale Git packages.
                for package in packages:
                    if not stale[package]:
                        continue
                    own = asked[package]
                    if siblings[package] is None:
                        named[package] = states[package].current
                    else:
                        own &= states[package].stale_git
                    owned[package] = own
                    resumed |= own & marked
                    targets |= own - marked
                rebuilt = targets
        # A package whose record fails only in the bytes of some listed
        # artifacts, or for which a sibling stands in, loses the units no
        # record vouches for in place of a clean: Cargo rebuilds a unit whose
        # files are gone, and dirties its dependents.
        hit: dict[str, frozenset[str]] = {}

        def present(files: dict[str, str]) -> dict[str, str]:
            # A listed file now missing leaves no record-wide identity, yet
            # the files still present keep vouching for their units.
            try:
                return recorded_artifact_identity(
                    target_dir, [name for name in files if (target_dir / name).is_file()]
                )["files"]
            except BuildIdentityError:
                return {}

        pairs: list[tuple[dict[str, str], dict[str, str]]] = []
        if clean_command is None and not artifact_paths:
            for package, state in states.items():
                if state.matched or state.existing is None or state.stale_git:
                    continue
                dependencies, spec = inputs[package]
                args = (state.existing, state.current, spec, dependencies, manifest, execution_root)
                if siblings[package] is None:
                    hit[package] = _artifact_only_packages(*args, state.inputs, workspace_owners())
                else:
                    changed = state.current is None or changed_packages(
                        state.existing["artifact"]["files"], state.current["files"], manifest,
                        execution_root, tuple(sorted({*_path_packages(dependencies), spec.package})),
                        workspace_owners(),
                    )
                    hit[package] = asked[package] if changed is True else frozenset(changed or ()) & asked[package]
                    pairs.extend(
                        (record.record["artifact"]["files"], present(record.record["artifact"]["files"]))
                        for record in found[package]
                    )
                # A listed file now missing leaves no current identity, yet
                # the files still present keep vouching for their units.
                files = state.existing["artifact"]["files"]
                pairs.append((files, present(files)))
        pruned = frozenset(
            owner
            for owner in targets
            if hit and all(owner in hit.get(package, ()) for package, own in owned.items() if owner in own)
        )
        standing = frozenset().union(*(hit[p] for p in hit if siblings[p] is not None), frozenset())
        candidates = pruned | (standing - targets - resumed)
        if candidates:
            doomed = prune_plan(target_dir, profile, target, workspace_owners(), candidates, pairs)
            pruned |= frozenset(owner for owner, paths in doomed.items() if paths)
            prune_paths = sum(doomed.values(), [])
            targets -= pruned
            rebuilt = targets | pruned
        package_decisions = {}
        for package, state in states.items():
            if state.existing is None:
                reasons = ["record-absent"]
            else:
                dependencies, spec = inputs[package]
                reasons = list(
                    _record_mismatch_reasons(
                        state.existing, spec, dependencies, state.current, state.inputs
                    )
                )
            if state.stale_git:
                reasons.append("stale-git")
            if package in marked:
                reasons.append("resumable-build")
            if siblings[package] is not None:
                reasons.append("sibling-record")
            package_decisions[package] = {
                "matched": state.matched,
                "reasons": reasons,
                "record_present": state.existing is not None,
                "requested": sorted(asked[package]),
                "sibling": siblings[package] is not None,
                "stale_git": sorted(state.stale_git),
            }
        requested = frozenset().union(*asked.values())
        clean_plan = {
            "clean": sorted(rebuilt - pruned),
            "prune": sorted(pruned),
            "packages": package_decisions,
            "phase": phases[0],
            "profile": profile,
            "requested": sorted(requested),
            "resume": sorted(resumed),
            "run": run_id,
            "schema": 1,
            "target": target,
        }
        _emit_clean_plan(clean_plan, run_id)
        progress.advance("cleanup")
        if custom_clean:
            mark_broad_clean(directory, held, writer_identity)
            _run_checked(clean_command, execution_root, environment)
        for package, (dependencies, _) in inputs.items():
            git_built[package] |= set(targets) & _git_names(dependencies)
            _write_git_stamps(dependencies, directory, git_built[package], building=True)
        # One invocation for every package's targets: each `cargo clean` walks
        # the entire shared target whatever it deletes, so one call per
        # package held the closure's exclusive leases for minutes per package
        # (about 2.5 min each on the stack target) and a stale metis record
        # stalled every push that shared its dependencies for over an hour. A
        # `cargo clean` naming no package would clean everything.
        if pruned:
            mark(directory, pruned, CLEANING, writer_identity)
            prune_units(prune_paths)
        if targets:
            mark(directory, targets, CLEANING, writer_identity)
            _run_checked(
                [
                    *_cargo_command(),
                    *(argument for value in clean_config for argument in ("--config", value)),
                    "clean",
                    *(argument for clean_package in sorted(targets) for argument in ("-p", clean_package)),
                    *directory.clean_arguments(),
                    "--manifest-path",
                    str(manifest),
                ],
                execution_root,
                environment,
            )
        # The packages whose artifacts this run writes and discovers afresh.
        fresh = {*packages, *rebuilt, *resumed}
        # The last writer of every package the command writes, from here until
        # its record lands: a kill leaves this identity's mark for a rerun.
        mark(directory, fresh, BUILDING, writer_identity)
        if not artifact_paths and all(
            named[package] is not None or recorded_packages[package] <= fresh
            for package in packages
        ):
            # The command rebuilds what was cleaned, so those scopes stay
            # exclusive; every other scope is only read from here on, as on a
            # matched run, and peers sharing it enter while the command runs.
            # The downgrade keeps each lease's place in the queue, so no
            # writer queued meanwhile can clean between the clean and the
            # command.
            for lease in taken:
                if lease.owner["package"] not in fresh and lease.mode == EXCLUSIVE:
                    lease.downgrade()
        held_shared = {str(lease.owner["package"]) for lease in taken if lease.mode == SHARED}
        # Path packages read shared, whose files are hashed by the names a
        # record lists rather than discovered.
        shared_recorded = {
            package: recorded_packages[package] & held_shared for package in packages
        }
        for package in packages:
            if shared_recorded[package] and named[package] is None and not artifact_paths:
                raise IdentityError(
                    "a dependency is held shared but no record names its artifacts"
                )
        progress.advance("command")
        with heartbeat(directory, fresh, writer_identity):
            _run_checked(command, execution_root, environment)
        progress.advance("source-dependencies")
        final_source = source_identity(root, (target_dir,), ignore_paths)
        if final_source.as_dict() != first_spec.source.as_dict():
            raise IdentityError("source tree changed while the build was running")
        final_snapshots = _dependency_data(
            manifest, packages, target_dir, execution_root, ignore_paths, bool(artifact_paths)
        )
        if any(final_snapshots[package] != inputs[package][0] for package in packages):
            raise IdentityError("dependency graph changed while the build was running")
        progress.advance("git-stamps")
        # The checkout content is the snapshot's, unchanged across the build.
        for package, (dependencies, _) in inputs.items():
            _write_git_stamps(dependencies, directory, git_built[package], building=False)
        progress.advance("census-inputs")
        # A file several packages' records list is read once per run.
        settled: dict[str, str] = {}
        census_deadline_ns = time.monotonic_ns() + int(
            ARTIFACT_CENSUS_SECONDS * 1_000_000_000
        )
        discovered = {}
        if not artifact_paths:
            discovered = artifact_identities(
                root,
                target_dir,
                {
                    package: tuple(
                        sorted(recorded_packages[package] - shared_recorded[package])
                    )
                    for package in packages
                },
                profile,
                target,
                manifest,
                execution_root,
                workspace_owners(),
                deadline_ns=census_deadline_ns,
                listed={
                    package: tuple(state.current["files"])
                    for package, state in states.items()
                    if state.matched
                },
            )
        prepared = []
        for package in packages:
            dependencies, spec = inputs[package]
            if shared_recorded[package] and not artifact_paths:
                # Peers read, and their Cargo may rewrite, every path package
                # this run holds shared, so those are found by the names
                # `named` lists, never by discovery, and each is hashed again
                # once two reads agree: the command rebuilt them in place (a
                # fresh export has fresh mtimes, and rustc embeds its path in
                # the bytes). A file that never settles is recorded unverified,
                # and one that cannot be read at all keeps its digest read
                # before the command. Only the path packages held exclusive are
                # discovered afresh, and their recorded names are dropped, so a
                # name their rebuild retired is not kept.
                artifact = shared_artifact_identity(
                    target_dir,
                    package,
                    profile,
                    target,
                    manifest,
                    execution_root,
                    recorded_packages[package] - shared_recorded[package],
                    shared_recorded[package],
                    named[package]["files"],
                    workspace_owners(),
                    settled,
                    census_deadline_ns,
                    discovered[package],
                )
            else:
                # Declared paths are hashed as named; otherwise every recorded
                # package is held exclusive, so each is discovered.
                artifact = (
                    artifact_identity(
                        root,
                        target_dir,
                        package,
                        profile,
                        artifact_paths,
                        target,
                        manifest,
                        execution_root,
                        tuple(sorted(recorded_packages[package])),
                        None,
                    )
                    if artifact_paths
                    else discovered[package]
                )
            prepared.append(
                (
                    package,
                    spec,
                    artifact,
                    {
                        "version": VERSION,
                        "source": spec.source.as_dict(),
                        "build": spec.as_dict(),
                        "dependencies": dependencies,
                        "artifact": artifact,
                        # Declared paths are not a closure: the repository decides.
                        "inputs": {}
                        if artifact_paths
                        else record_inputs(
                            target_dir, artifact["files"], recorded_packages[package], layout
                        ),
                    },
                )
            )
        if time.monotonic_ns() >= census_deadline_ns:
            raise IdentityError("artifact census did not converge before its deadline")
        progress.advance("publication")
        results = []
        for package, spec, artifact, record in prepared:
            _write_atomic(records[package], record)
            # Cleaned by its own rule or by another package's in this run.
            cleaned = stale[package] or package in rebuilt
            results.append(
                BuildResult(
                    "rebuilt" if cleaned else "reused",
                    records[package],
                    cleaned,
                    tuple(target_dir / relative for relative in artifact["files"]),
                )
            )
        mark(directory, fresh, COMPLETE, writer_identity)
    return tuple(results)
