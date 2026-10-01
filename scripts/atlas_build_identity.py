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
from typing import Iterable, Sequence

from atlas_build_artifacts import (
    artifact_digest,
    artifact_identity,
    artifact_owners,
    artifact_package,
    changed_packages,
    dependency_snapshot,
    discover_artifacts,
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
from atlas_build_package_source import cached_package_source_digest
from atlas_build_source import (
    SourceIdentity,
    cargo_config_digest,
    environment_digest,
    source_identity,
    toolchain_identity,
)

VERSION = 5
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
    cargo_config_digest: str
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
            "cargo_config_digest": self.cargo_config_digest,
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


def _config_arguments(command: Sequence[str]) -> tuple[str, ...]:
    """The literal `--config` argument values a command line carries.

    Each names or inlines a Cargo configuration source the discovery walk
    in `cargo_config_digest` cannot find by directory alone.
    """
    arguments: list[str] = []
    iterator = iter(command)
    for token in iterator:
        text = str(token)
        if text == "--config":
            value = next(iterator, None)
            if value is not None:
                arguments.append(str(value))
        elif text.startswith("--config="):
            arguments.append(text[len("--config=") :])
    return tuple(arguments)


def _inline_environment(command: Sequence[str]) -> dict[str, str]:
    """The `NAME=VALUE` assignments a leading `env` prefix sets for this command.

    `env RUSTDOCFLAGS=... cargo doc` sets an environment variable no ambient
    `os.environ` snapshot carries, so `environment_digest` alone cannot see
    it move; only a leading run of `NAME=VALUE` tokens right after `env` is
    parsed, matching the `env` program's own simple form (`env` is an
    external program, not a shell builtin, so this command list -- already
    a `Sequence[str]` with no shell involved -- names it as an ordinary
    argument; the parse still stops at `-u`/`-i`/`-C` and any other option,
    since anything past a leading run of assignments is not something this
    identity check can attribute to a specific variable without invoking
    `env` itself).
    """
    values: dict[str, str] = {}
    iterator = iter(command)
    first = next(iterator, None)
    if first != "env":
        return values
    for token in iterator:
        text = str(token)
        if "=" not in text or text.startswith("-"):
            break
        name, _, value = text.partition("=")
        if not name:
            break
        values[name] = value
    return values


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
    execution_root: Path | None = None,
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
    resolved_execution_root = _canonical(execution_root if execution_root is not None else root)
    # Computed once and shared: a leading `env NAME=VALUE ...` prefix (e.g.
    # `env CARGO_HOME=<h> cargo ...`) must be visible to both digests, not
    # only to `environment_digest` -- `cargo_config_digest` resolves
    # `$CARGO_HOME` through this same merged mapping, never `os.environ`
    # alone, or a build's own `CARGO_HOME` override would look for its
    # config at the ambient `CARGO_HOME` instead.
    merged_environment = {**os.environ, **_inline_environment(normalized_command)}
    return BuildSpec(
        source=source_identity(canonical_root, (canonical_target,), ignore_paths),
        package=package,
        profile=profile,
        target=target,
        features=features,
        toolchain=toolchain_identity(root),
        target_dir=canonical_target.as_posix(),
        command_key=normalized_key,
        environment_digest=environment_digest(merged_environment),
        cargo_config_digest=cargo_config_digest(
            resolved_execution_root, _config_arguments(normalized_command), merged_environment
        ),
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
        package_source_cache = target_dir / ".atlas" / "source-identity" / "package-source"

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
            lambda path: cached_package_source_digest(path, package_source_cache),
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


def _sibling_record(spec: BuildSpec) -> dict[str, object] | None:
    """A record of the same build and source under another command key.

    Its artifact names cover the dependency closure this run reads, so a run
    that holds the dependencies shared hashes them by those names.
    """
    build = spec.as_dict()
    build.pop("command_key")
    directory = record_path(spec).parent
    if not directory.is_dir():
        return None
    for candidate in directory.glob("*.json"):
        try:
            record = read_record(candidate)
        except IdentityError:
            continue
        if record is None:
            continue
        artifact = record.get("artifact")
        if not isinstance(artifact, dict) or not isinstance(artifact.get("files"), dict):
            continue
        other = record.get("build")
        if not isinstance(other, dict):
            continue
        other = dict(other)
        other.pop("command_key", None)
        if _content(other) == _content(build) and _content(record.get("source")) == _content(
            spec.source.as_dict()
        ):
            return record
    return None


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
    if type(version) is int and version in {1, 2, 3, 4}:
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
            "cargo_config_digest",
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

    `source` is compared against `spec.source` directly, and
    `dependency_digest` restates the dependency snapshot, which
    `_stale_packages` compares record by record.
    """
    content = _content(build)
    if not isinstance(content, dict):
        return content
    return {key: value for key, value in content.items() if key not in ("source", "dependency_digest")}


def _path_packages(dependencies: dict[str, object]) -> tuple[str, ...]:
    """The closure's path packages, the only ones whose files a record names.

    Cargo trusts a path package's artifact while its sources are older, so
    another tree's build of the same workspace-relative package can stand in
    for this one; the record's file digests detect that. A Git or registry
    package's artifact is named after its locked revision or version and
    built from that checkout, so recording it detects nothing, and hashing
    every variant of every one in the shared target cost each run minutes.
    """
    return tuple(
        sorted(
            {
                str(record.get("name"))
                for record in dependencies.get("packages", [])
                if isinstance(record, dict) and record.get("kind") == "path"
            }
        )
    )


# Cargo's profile name for each profile directory that differs from it.
_CARGO_PROFILE_NAMES = {"debug": "dev"}


@dataclass(frozen=True)
class BuildDirectory:
    """One profile directory of the shared target, where a build writes its artifacts.

    `profile` is the directory's name (`debug`, `release`, a custom
    profile's) and `target` a triple or `host`. A Git package's stamp and
    the clean that invalidates it both cover exactly this directory: `cargo
    clean -p` without `--profile` leaves every other profile's variants, so
    a stamp spanning the target would vouch for artifacts no clean reached.
    """

    target_dir: Path
    profile: str
    target: str

    def stamp(self, record: dict[str, object]) -> Path:
        """Where the content this directory's artifacts of `record` were built from is named."""
        key = _sha256_bytes(
            f"{record.get('name')}\0{record.get('source')}\0{self.profile}\0{self.target}".encode()
        )
        return self.target_dir / ".atlas" / "source-identity" / "git-build" / key

    def clean_arguments(self) -> list[str]:
        """`cargo clean` arguments confining it to this directory, every variant in it."""
        arguments = ["--profile", _CARGO_PROFILE_NAMES.get(self.profile, self.profile)]
        if self.target != "host":
            arguments += ["--target", self.target]
        return arguments


# The stamp a run writes before building a Git package it cleans or finds
# unstamped, replaced by the content digest only once the command and the
# final snapshot succeed. It equals no digest, so a run that fails or is
# killed in between leaves that package stale for the next one: the target
# may already hold what it built. A package whose stamp already matched
# gets no sentinel, so an edit to its checkout during the build, reverted
# before the next run, is not seen (ATLAS-IDENTITY-MIDRUN-GIT-EDIT).
_BUILDING = "building"


def _git_records(dependencies: dict[str, object], names: Iterable[str]) -> list[dict[str, object]]:
    wanted = set(names)
    return [
        record
        for record in dependencies.get("packages", [])
        if isinstance(record, dict) and record.get("kind") == "git" and record.get("name") in wanted
    ]


def _git_names(dependencies: dict[str, object]) -> set[str]:
    return {
        str(record.get("name"))
        for record in dependencies.get("packages", [])
        if isinstance(record, dict) and record.get("kind") == "git"
    }


def _git_stamp(directory: BuildDirectory, record: dict[str, object]) -> str | None:
    """The content digest the stamp names, or `_BUILDING`; None without a stamp."""
    try:
        value = json.loads(directory.stamp(record).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IdentityError(
            f"cannot read the Git build stamp of {record.get('name')}: {error}"
        ) from error
    digest = value.get("content_digest") if isinstance(value, dict) else None
    if not isinstance(digest, str):
        raise IdentityError(f"malformed Git build stamp for {record.get('name')}")
    return digest


def _stale_git(dependencies: dict[str, object], directory: BuildDirectory) -> set[str]:
    """Git packages whose artifacts in the build directory may be from other content.

    Cargo never re-reads a Git checkout, and a record describes only its own
    runs' builds, so the target itself carries one stamp per Git package,
    source and build directory: the content digest of the checkout its
    artifacts there were last built from. A stamp naming other content than the checkout holds now, or a
    build that never finished, means the artifacts may predate an edit or
    its revert, whichever record's run built them. A package with no stamp
    was never built by a run of this checker since stamps began; its
    artifacts are trusted, the bound already accepted for builds outside
    this checker.
    """
    return {
        str(record.get("name"))
        for record in _git_records(dependencies, _git_names(dependencies))
        if (stamp := _git_stamp(directory, record)) is not None
        and stamp != record.get("content_digest")
    }


def _unstamped_git(dependencies: dict[str, object], directory: BuildDirectory) -> set[str]:
    return {
        str(record.get("name"))
        for record in _git_records(dependencies, _git_names(dependencies))
        if _git_stamp(directory, record) is None
    }


def _write_git_stamps(
    dependencies: dict[str, object], directory: BuildDirectory, names: Iterable[str], building: bool
) -> None:
    """Stamp `names`' Git packages as building, or with the content they were built from.

    A refused write raises. The stamp is then `_BUILDING` (or absent, if the
    first write failed), so the next run cleans the package instead of
    trusting it: a failure costs a rebuild, never a stale reuse. Two runs
    stamping one unstamped package concurrently hold it shared and checked
    the same content unchanged across their builds, so either value is true.
    """
    for record in _git_records(dependencies, names):
        value = _BUILDING if building else record.get("content_digest")
        _write_atomic(directory.stamp(record), {"content_digest": value})


def _stale_packages(
    existing: dict[str, object] | None,
    current: dict[str, object] | None,
    spec: BuildSpec,
    dependencies: dict[str, object],
    manifest: Path,
    execution_root: Path,
) -> tuple[str, ...]:
    """The packages a mismatched record must clean before its command runs.

    Cargo rebuilds a unit whose features, profile, dependencies, edition or
    toolchain changed, under a new metadata hash or in place, so none of
    those leave a stale artifact; only source content can, and the record
    must still name the variant the build uses. A variant is renamed only
    by the build dimensions or by the snapshot's shape: its records without
    their content fields -- each path package's resolved manifest among
    them -- its edges, and the workspace manifest, whose `[profile]` tables
    enter every unit's hash. A source edit renames nothing. `cargo
    metadata` unifies features across `cfg` tables and dependency kinds, so
    which variants a shape change renamed cannot be read from it: a shape
    or dimension change cleans every path package. Otherwise only content
    moved, and the run cleans each path package whose source identity
    moved, its own package when its source moved, and the owners of changed
    recorded files, or every path package when a changed file cannot be
    attributed to exactly one. A Git package is cleaned when its stamp is
    stale (`_stale_git`). Registry packages are never cleaned. Cleaning the
    whole non-registry closure on any snapshot difference held a
    two-dependency addition's 35 packages exclusive through its command; 34
    were unedited Git checkouts. Cleaning every path package on any source
    move cleaned each separate-repository path dependency, every stack
    member under the development overlay, on every push of its consumer.
    """
    scope = {*_path_packages(dependencies), spec.package}
    stale = _stale_git(dependencies, BuildDirectory(Path(spec.target_dir), spec.profile, spec.target))
    if (
        existing is None
        or current is None
        or _dimensions(existing.get("build")) != _dimensions(spec.as_dict())
        or _shape(existing["dependencies"]) != _shape(dependencies)
    ):
        return tuple(sorted(scope | stale))
    recorded = {
        record.get("id"): record
        for record in existing["dependencies"].get("packages", [])
        if isinstance(record, dict)
    }
    for record in dependencies.get("packages", []):
        if (
            isinstance(record, dict)
            and record.get("kind") == "path"
            and recorded.get(record.get("id")) != record
        ):
            stale.add(str(record.get("name")))
    if _content(existing.get("source")) != _content(spec.source.as_dict()):
        stale.add(spec.package)
    changed = changed_packages(
        existing["artifact"]["files"],
        current["files"],
        manifest,
        execution_root,
        tuple(sorted(scope)),
    )
    stale |= scope if changed is None else changed
    return tuple(sorted(stale))


# The record fields that carry source content: a path package's repository
# identity and a Git or registry checkout's digest. Neither renames a variant.
_CONTENT_FIELDS = ("identity", "content_digest")


def _shape(snapshot: dict[str, object]) -> str:
    """The snapshot without its content fields: every input of a variant name it holds."""
    shape = {
        "workspace_manifest": snapshot.get("workspace_manifest"),
        "packages": sorted(
            (
                {key: value for key, value in record.items() if key not in _CONTENT_FIELDS}
                for record in snapshot.get("packages", [])
                if isinstance(record, dict)
            ),
            key=lambda record: json.dumps(record, sort_keys=True),
        ),
        "edges": snapshot.get("edges"),
    }
    return json.dumps(shape, sort_keys=True)


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
