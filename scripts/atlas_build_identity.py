"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Iterable, Sequence
from urllib.parse import unquote

from atlas_build_artifacts import (
    artifact_digest,
    artifact_identity,
    changed_packages,
    dependency_snapshot,
    discover_artifacts,
    owned_by,
    SETTLE_SECONDS,
    recorded_artifact_identity,
    settled_digest,
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


def _dimensions(build: object) -> object:
    """A build record's dimensions, without the fields compared on their own.

    `source` is compared against `spec.source` directly. `dependency_digest`
    is `str(dependencies["digest"])`, so it moves in lockstep with the
    dependency snapshot and is redundant with comparing `dependencies`
    itself; keeping it here would fail every narrowing candidate outright,
    since a snapshot that disagrees only in path-record identity still
    hashes to a different digest.
    """
    content = _content(build)
    if not isinstance(content, dict):
        return content
    return {key: value for key, value in content.items() if key not in ("source", "dependency_digest")}


_WORKSPACE_PATH_ID = re.compile(r"^workspace:(?P<relative>.*)#[^#]+@[^#]+$")
_CARGO_PATH_ID = re.compile(r"^path\+file://(?P<path>.+)#[^#]+@[^#]+$")

# A name-only diff is checked for filenames, never TOML sections: a build
# script, a toolchain pin, a Cargo manifest or lockfile, or anything under a
# `.cargo` directory can all reconfigure how a dependency compiles (profile,
# features, patches, linker flags) without the dependency's own recorded
# content moving at all.
_BUILD_CONFIGURATION_NAMES = frozenset({"Cargo.toml", "Cargo.lock", "build.rs"})


def _touches_build_configuration(paths: Iterable[str]) -> bool:
    for relative in paths:
        relative = relative.strip()
        if not relative:
            continue
        parts = relative.split("/")
        name = parts[-1]
        if name in _BUILD_CONFIGURATION_NAMES or name.startswith("rust-toolchain"):
            return True
        if ".cargo" in parts[:-1]:
            return True
    return False


def _path_record_manifest_dir(record_id: str, workspace_root: Path) -> Path | None:
    """The absolute manifest directory a path record's stable id names.

    A workspace-relative id (`workspace:<relative>#<name>@<version>`)
    resolves against `workspace_root`, which this run's own `root` -- the
    workspace `dependency_snapshot` was computed against -- approximates.
    Cargo's own `path+file://` id, kept for a path package outside the
    workspace, embeds the absolute manifest directory directly. Neither
    pattern matching means the id is not one this run can resolve to a
    filesystem path.
    """
    workspace_match = _WORKSPACE_PATH_ID.match(record_id)
    if workspace_match:
        return (workspace_root / workspace_match.group("relative")).resolve()
    path_match = _CARGO_PATH_ID.match(record_id)
    if path_match:
        raw = unquote(path_match.group("path"))
        if len(raw) > 2 and raw[0] == "/" and raw[2] == ":":
            raw = raw[1:]  # `/C:/...` (URL form) -> `C:/...`
        return Path(raw)
    return None


def _path_repository_safe_to_narrow(
    record_id: str,
    existing_identity: object,
    current_identity: object,
    workspace_root: Path,
) -> bool:
    """Whether a path record's identity change is provably a non-build-config edit.

    A path record's identity is the identity of its whole containing
    repository, so a change reconfiguring how dependencies build -- a
    profile, a feature, a build script, a toolchain pin -- moves it exactly
    like an ordinary source edit. Narrowing on identity alone is safe only
    when the actual file-level diff between the two recorded revisions
    touches no such file. A dirty tree on either side means the diff is not
    fully captured by a revision-to-revision comparison (its uncommitted
    files are not on either side's compared range), and a revision this
    repository cannot resolve, or a `git diff` that fails outright, means
    the diff cannot be established at all: both are treated as unsafe, never
    as a reason to search harder.
    """
    if not isinstance(existing_identity, dict) or not isinstance(current_identity, dict):
        return False
    if existing_identity.get("dirty") or current_identity.get("dirty"):
        return False
    existing_revision = existing_identity.get("revision")
    current_revision = current_identity.get("revision")
    if not isinstance(existing_revision, str) or not isinstance(current_revision, str):
        return False
    if existing_revision == current_revision:
        return True
    manifest_dir = _path_record_manifest_dir(record_id, workspace_root)
    if manifest_dir is None or not manifest_dir.is_dir():
        return False
    try:
        top = subprocess.run(
            ["git", "-C", str(manifest_dir), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "-C", top, "diff", "--name-only", existing_revision, current_revision, "--"],
            check=True, capture_output=True, text=True, timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return not _touches_build_configuration(diff.splitlines())


def _path_only_dependency_diff(
    existing: dict[str, object], current: dict[str, object], workspace_root: Path
) -> set[str] | None:
    """The path-record names two dependency snapshots disagree on, or None.

    A path record's identity is `source_identity` of its whole containing
    repository (revision plus diff), not of its own subtree: every path
    package sharing one repository -- the run's own workspace members, and,
    under the development overlay, a sibling first-party crate patched to a
    local checkout -- changes identity together whenever any file in that
    repository changes, whether or not the package itself did. Two snapshots
    may therefore disagree on path records alone while every git and registry
    dependency, every edge, and the clean-package set stay exactly the
    packages they were: nothing reachable through a non-path record could
    have moved. None means the disagreement reaches further than that and the
    whole closure must clean: a real-Cargo counterexample showed a path
    record differing in `features` alone (feature unification from an
    unrelated manifest edit) left a sibling's rebuilt variant unrecorded, so
    every field but `identity` must still agree, and a real-Cargo
    counterexample showed the run's own identity-only change touching its
    Cargo.toml (a profile edit) silently reconfigured a git dependency's
    build, so an identity difference narrows only when
    `_path_repository_safe_to_narrow` proves the underlying diff untouched
    build configuration.
    """
    if existing.get("root") != current.get("root"):
        return None
    if existing.get("edges") != current.get("edges"):
        return None
    if existing.get("clean_packages") != current.get("clean_packages"):
        return None
    existing_packages = existing.get("packages")
    current_packages = current.get("packages")
    if not isinstance(existing_packages, list) or not isinstance(current_packages, list):
        return None
    existing_by_id = {record.get("id"): record for record in existing_packages}
    current_by_id = {record.get("id"): record for record in current_packages}
    if existing_by_id.keys() != current_by_id.keys():
        return None
    changed: set[str] = set()
    for package_id, existing_record in existing_by_id.items():
        current_record = current_by_id[package_id]
        if existing_record == current_record:
            continue
        if existing_record.get("kind") != "path" or current_record.get("kind") != "path":
            return None
        existing_rest = {key: value for key, value in existing_record.items() if key != "identity"}
        current_rest = {key: value for key, value in current_record.items() if key != "identity"}
        if existing_rest != current_rest:
            return None
        if not _path_repository_safe_to_narrow(
            str(package_id),
            existing_record.get("identity"),
            current_record.get("identity"),
            workspace_root,
        ):
            return None
        changed.add(str(current_record.get("name")))
    return changed


def _narrowed_clean(
    existing: dict[str, object] | None,
    current: dict[str, object] | None,
    spec: BuildSpec,
    dependencies: dict[str, object],
    manifest: Path,
    execution_root: Path,
    clean_packages: tuple[str, ...],
    root: Path,
) -> tuple[str, ...] | None:
    """The packages a mismatched record must clean, or None for the whole closure.

    With the build dimensions unchanged and the dependency snapshots equal or
    disagreeing only in path-record identity (`_path_only_dependency_diff`),
    every git and registry dependency's inputs are unchanged: a new source for
    the identified package, or for a sibling repository patched in as a path
    dependency, cannot alter their artifacts. The run then cleans its own
    package when its source changed, each path record whose identity changed
    (its own containing repository moved), and each package whose recorded
    artifact bytes changed (Cargo rebuilds every unit that depends on a unit
    it rebuilds, so dependents follow). Cleaning the closure on every source
    change rebuilt every first-party dependency under exclusive leases on each
    push and serialized every gate sharing them.
    """
    if existing is None or current is None:
        return None
    if _dimensions(existing.get("build")) != _dimensions(spec.as_dict()):
        return None
    existing_dependencies = existing.get("dependencies")
    if existing_dependencies == dependencies:
        path_changed: set[str] = set()
    elif isinstance(existing_dependencies, dict):
        path_changed = _path_only_dependency_diff(existing_dependencies, dependencies, root)
        if path_changed is None:
            return None
    else:
        return None
    changed = changed_packages(
        existing["artifact"]["files"], current["files"], manifest, execution_root, clean_packages
    )
    if changed is None:
        return None
    changed = changed | path_changed
    if _content(existing.get("source")) != _content(spec.source.as_dict()):
        changed.add(spec.package)
    return tuple(sorted(changed)) if changed else None


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

    def acquire(exclusive: frozenset[str]) -> ExitStack:
        # The command writes its own package; a dependency is only read
        # unless the record shows the run must clean or rebuild it.
        stack = ExitStack()
        try:
            for lock, owner in scopes:
                mode = (
                    EXCLUSIVE
                    if owner["package"] == spec.package or owner["package"] in exclusive
                    else SHARED
                )
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

    def clean_targets(
        existing: dict[str, object] | None, current: dict[str, object] | None
    ) -> tuple[str, ...]:
        # A caller's clean command is opaque, so it may touch the whole closure.
        if clean_command is not None:
            return clean_packages
        narrowed = _narrowed_clean(
            existing, current, spec, dependencies, manifest, execution_root, clean_packages, root
        )
        return clean_packages if narrowed is None else narrowed

    with ExitStack() as leases:
        shared = leases.enter_context(acquire(frozenset()))
        existing, matched, current = locked_record()
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
            existing, matched, current = locked_record()
            # The re-read may name packages the first read did not: widen to
            # them and read again, so nothing is cleaned under a shared lease.
            while not matched and not held.issuperset(clean_targets(existing, current)):
                held = held | frozenset(clean_targets(existing, current))
                exclusive.close()
                exclusive = leases.enter_context(acquire(held))
                existing, matched, current = locked_record()
        stale = not matched and (existing is not None or not _sibling_matches(spec))
        if stale:
            if clean_command is not None:
                _run_checked(clean_command, execution_root, environment)
            else:
                # The widen loop's converged set, never recomputed: every
                # package this run cleans was held exclusive by that loop, so
                # cleaning it here can never reach past that set.
                targets = tuple(sorted(held))
                # One invocation for the whole closure: each `cargo clean`
                # walks the entire shared target whatever it deletes, so one
                # call per package held the closure's exclusive leases for
                # minutes per package (about 2.5 min each on the stack
                # target) and a stale metis record stalled every push that
                # shared its dependencies for over an hour.
                _run_checked(
                    [
                        *_cargo_command(),
                        "clean",
                        *(
                            argument
                            for clean_package in targets
                            for argument in ("-p", clean_package)
                        ),
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
        # A narrowed clean held some dependencies only shared: `held` is then
        # a proper subset of the closure, and the packages it names are the
        # only ones this run may have rebuilt. Recording like the matched
        # branch below -- discovering only what was held exclusive, and
        # re-verifying every other named file by settling rather than
        # rediscovering it -- keeps the run from walking a dependency another
        # gate holds only shared (ADR 0064: hash only files the record names,
        # found by name, never by discovery).
        narrowed = (
            not matched
            and stale
            and existing is not None
            and not artifact_paths
            and frozenset(held) != frozenset(clean_packages)
        )
        if (matched or narrowed) and not artifact_paths:
            # The command rebuilt dependency files in place (a fresh export
            # has fresh mtimes, and rustc embeds its path in the bytes), so
            # every file the record names is hashed again once two reads
            # agree. Another reader's Cargo may be rewriting one: a file that
            # never settles is recorded unverified, and one that cannot be
            # read at all keeps its pre-command digest. Only the packages
            # held exclusive -- the run's own package always, plus, for a
            # narrowed clean, every package it cleaned -- are discovered
            # afresh; a package another gate holds shared is never walked.
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
                        tuple(sorted(held - {spec.package})),
                    )
                ],
            )
            # A package this run cleaned but did not rediscover here (a new
            # metadata hash replaced its old filename) had its old file
            # deleted by that clean: keeping its pre-command digest would
            # carry a name-only entry for a file that no longer exists. Only
            # a package this run never cleaned -- genuinely held shared --
            # may fall back to settling its named file's digest.
            cleaned_leftovers = owned_by(
                (relative for relative in existing["artifact"]["files"] if relative not in own["files"]),
                manifest,
                execution_root,
                tuple(held | {spec.package}),
            )
            files = {}
            for relative, verified in existing["artifact"]["files"].items():
                if relative in own["files"] or relative in cleaned_leftovers:
                    continue
                # Each file gets up to SETTLE_SECONDS, never past the run's
                # wait deadline; at least two reads are always attempted.
                budget = min(time.monotonic_ns() + int(SETTLE_SECONDS * 1_000_000_000), deadline_ns)
                settled = settled_digest(target_dir / relative, budget)
                files[relative] = verified if settled is None else settled
            files.update(own["files"])
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
