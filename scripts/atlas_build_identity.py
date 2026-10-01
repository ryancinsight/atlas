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
import tomllib
from typing import Iterable, Sequence
from urllib.parse import unquote

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

VERSION = 4
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
    if type(version) is int and version in {1, 2, 3}:
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

# A name-only diff is checked for filenames: a build script, a toolchain pin,
# or anything under a `.cargo` directory can reconfigure how a package
# compiles without any snapshot record moving, so a repository diff touching
# one never narrows.
_BUILD_CONFIGURATION_NAMES = frozenset({"build.rs"})
# A manifest or lockfile edit narrows, but as a rehash: it can rename the
# package's artifacts (features, dependencies, target kinds feed Cargo's
# metadata hash, which every dependent's hash includes), so the package and
# its dependents inside the closure are cleaned and rediscovered. Cargo reads
# `[profile]`, `[patch]` and `[replace]` from the workspace root manifest
# alone, which `_root_manifest_build_tables` compares on its own.
_MANIFEST_NAMES = frozenset({"Cargo.toml", "Cargo.lock"})

# The root-manifest tables that reconfigure every unit without moving any
# snapshot record. Cargo ignores them in every other manifest (Cargo
# reference: Profiles; Overriding Dependencies).
_ROOT_BUILD_TABLES = ("profile", "patch", "replace", "cargo-features")
_ROOT_RESOLVER_TABLES = ("workspace", "package")


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


def _touches_manifest(paths: Iterable[str]) -> bool:
    return any(relative.strip().split("/")[-1] in _MANIFEST_NAMES for relative in paths if relative.strip())


def _root_build_tables(text: str) -> dict[str, object] | None:
    try:
        manifest = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    tables: dict[str, object] = {key: manifest.get(key) for key in _ROOT_BUILD_TABLES}
    for key in _ROOT_RESOLVER_TABLES:
        section = manifest.get(key)
        tables[f"{key}.resolver"] = section.get("resolver") if isinstance(section, dict) else None
    return tables


def _root_manifest_build_tables_unchanged(
    manifest: Path, existing_source: object, current_source: object
) -> bool:
    """Whether the run's root manifest keeps every root-only build table.

    The recorded side is read at the recorded revision; the current side is
    the file Cargo is about to read. A dirty recorded tree, a revision this
    repository cannot resolve, or a manifest either side cannot parse means
    the comparison cannot be established, and the whole closure cleans.
    """
    existing = _content(existing_source)
    current = _content(current_source)
    if not isinstance(existing, dict) or not isinstance(current, dict):
        return False
    if existing.get("dirty"):
        return False
    existing_revision = existing.get("revision")
    if not isinstance(existing_revision, str):
        return False
    if existing_revision == current.get("revision") and not current.get("dirty"):
        return True
    try:
        top = subprocess.run(
            ["git", "-C", str(manifest.parent), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=60,
        ).stdout.strip()
        relative = manifest.resolve().relative_to(Path(top).resolve()).as_posix()
        recorded = subprocess.run(
            ["git", "-C", top, "show", f"{existing_revision}:{relative}"],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=60,
        ).stdout
        present = manifest.read_text(encoding="utf-8")
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    recorded_tables = _root_build_tables(recorded)
    return recorded_tables is not None and recorded_tables == _root_build_tables(present)


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


_SOURCE_EDIT = "source"
_MANIFEST_EDIT = "manifest"


def _path_repository_change(
    record_id: str,
    existing_identity: object,
    current_identity: object,
    workspace_root: Path,
) -> str | None:
    """How a path record's identity change may narrow, or None if it cannot.

    A path record's identity is the identity of its whole containing
    repository, so the actual file-level diff between the two recorded
    revisions decides: one touching a build script, a toolchain pin, or
    `.cargo` configuration cannot narrow; one touching a manifest or
    lockfile is a `_MANIFEST_EDIT`, whose packages and their dependents are
    rehashed; any other is a `_SOURCE_EDIT`, rebuilt in place under its
    recorded names. A dirty tree on either side means the diff is not fully
    captured by a revision-to-revision comparison, and a revision this
    repository cannot resolve, or a `git diff` that fails outright, means
    the diff cannot be established at all: both are treated as unsafe, never
    as a reason to search harder.
    """
    if not isinstance(existing_identity, dict) or not isinstance(current_identity, dict):
        return None
    if existing_identity.get("dirty") or current_identity.get("dirty"):
        return None
    existing_revision = existing_identity.get("revision")
    current_revision = current_identity.get("revision")
    if not isinstance(existing_revision, str) or not isinstance(current_revision, str):
        return None
    if existing_revision == current_revision:
        return _SOURCE_EDIT
    manifest_dir = _path_record_manifest_dir(record_id, workspace_root)
    if manifest_dir is None or not manifest_dir.is_dir():
        return None
    try:
        top = subprocess.run(
            ["git", "-C", str(manifest_dir), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=60,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "-C", top, "diff", "--name-only", existing_revision, current_revision, "--"],
            check=True, capture_output=True, text=True, encoding="utf-8", timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    paths = diff.splitlines()
    if _touches_build_configuration(paths):
        return None
    return _MANIFEST_EDIT if _touches_manifest(paths) else _SOURCE_EDIT


def _outgoing_edges(snapshot: dict[str, object]) -> dict[str, list[str]] | None:
    edges = snapshot.get("edges")
    if not isinstance(edges, list):
        return None
    outgoing: dict[str, list[str]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            return None
        outgoing.setdefault(str(edge.get("from")), []).append(
            json.dumps([edge.get("to"), edge.get("dep_kinds")], sort_keys=True)
        )
    return {key: sorted(value) for key, value in outgoing.items()}


def _dependency_diff(
    existing: dict[str, object], current: dict[str, object], workspace_root: Path
) -> tuple[set[str], set[str]] | None:
    """The packages two dependency snapshots disagree on, or None.

    Returns `(rebuilt, rehashed)` by package name. `rebuilt` holds path
    packages whose containing repository changed only in source: Cargo
    rebuilds them, and every unit depending on them, in place under the
    names the record already lists. `rehashed` holds packages whose
    artifact names can move: a record differing in anything but `identity`
    (features, version, kind, content), a package whose own dependency edges
    changed (Cargo's metadata hash of a unit covers its dependencies'), and
    path packages whose repository diff touched a manifest or lockfile. The
    caller cleans those together with their dependents inside the closure.

    A package present only in the current snapshot is new to this closure:
    it is not cleaned (its artifacts, if any, belong to other runs) and is
    held shared and left unrecorded; the packages depending on it changed
    their edges and are rehashed. A package present only in the existing
    snapshot left the closure and needs nothing.

    None means the disagreement cannot be attributed: a different root, a
    malformed snapshot, or a path identity change whose diff touched a build
    script, a toolchain pin, or `.cargo` configuration, or could not be read.
    """
    if existing.get("root") != current.get("root"):
        return None
    existing_packages = existing.get("packages")
    current_packages = current.get("packages")
    if not isinstance(existing_packages, list) or not isinstance(current_packages, list):
        return None
    existing_by_id = {str(record.get("id")): record for record in existing_packages if isinstance(record, dict)}
    current_by_id = {str(record.get("id")): record for record in current_packages if isinstance(record, dict)}
    if len(existing_by_id) != len(existing_packages) or len(current_by_id) != len(current_packages):
        return None
    # `clean_packages` is derived from the records; a set naming a package no
    # record describes cannot be attributed to any package's change.
    for snapshot, by_id in ((existing, existing_by_id), (current, current_by_id)):
        derived = sorted(
            {str(record.get("name")) for record in by_id.values() if record.get("kind") != "registry"}
        )
        if snapshot.get("clean_packages") != derived:
            return None
    existing_edges = _outgoing_edges(existing)
    current_edges = _outgoing_edges(current)
    if existing_edges is None or current_edges is None:
        return None
    rebuilt: set[str] = set()
    rehashed: set[str] = set()
    for package_id, current_record in current_by_id.items():
        existing_record = existing_by_id.get(package_id)
        if existing_record is None:
            continue
        name = str(current_record.get("name"))
        if existing_edges.get(package_id, []) != current_edges.get(package_id, []):
            rehashed.add(name)
        if existing_record == current_record:
            continue
        existing_rest = {key: value for key, value in existing_record.items() if key != "identity"}
        current_rest = {key: value for key, value in current_record.items() if key != "identity"}
        if existing_rest != current_rest:
            rehashed.add(name)
            continue
        if current_record.get("kind") != "path":
            return None
        change = _path_repository_change(
            package_id,
            existing_record.get("identity"),
            current_record.get("identity"),
            workspace_root,
        )
        if change is None:
            return None
        (rehashed if change == _MANIFEST_EDIT else rebuilt).add(name)
    return rebuilt, rehashed


def _dependents_within(snapshot: dict[str, object], names: set[str]) -> set[str]:
    """`names` and every package in `snapshot` that reaches one of them."""
    id_to_name = {
        str(record.get("id")): str(record.get("name"))
        for record in snapshot.get("packages", [])
        if isinstance(record, dict)
    }
    depending: dict[str, set[str]] = {}
    for edge in snapshot.get("edges", []):
        if isinstance(edge, dict):
            depending.setdefault(id_to_name.get(str(edge.get("to")), ""), set()).add(
                id_to_name.get(str(edge.get("from")), "")
            )
    reached = set(names)
    pending = list(names)
    while pending:
        for dependent in depending.get(pending.pop(), ()):
            if dependent and dependent not in reached:
                reached.add(dependent)
                pending.append(dependent)
    return reached


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

    With the build dimensions and the run's root-only manifest tables
    unchanged, the dependency snapshots are compared package by package
    (`_dependency_diff`). The run cleans its own package when its source
    changed, each path package whose repository changed only in source
    (rebuilt in place, as are its dependents), each rehashed package together
    with every package inside the closure that reaches it, and each package
    whose recorded artifact bytes changed. A package new to the closure is
    never cleaned. Cleaning the whole closure on any of these rebuilt every
    first-party dependency under exclusive leases and serialized every gate
    sharing them; a two-dependency addition held 35 scopes through a command.
    """
    if existing is None or current is None:
        return None
    if _dimensions(existing.get("build")) != _dimensions(spec.as_dict()):
        return None
    if _content(existing.get("source")) != _content(spec.source.as_dict()) and not (
        _root_manifest_build_tables_unchanged(manifest, existing.get("source"), spec.source.as_dict())
    ):
        return None
    existing_dependencies = existing.get("dependencies")
    if existing_dependencies == dependencies:
        rebuilt: set[str] = set()
        rehashed: set[str] = set()
    elif isinstance(existing_dependencies, dict):
        diff = _dependency_diff(existing_dependencies, dependencies, root)
        if diff is None:
            return None
        rebuilt, rehashed = diff
    else:
        return None
    changed = changed_packages(
        existing["artifact"]["files"], current["files"], manifest, execution_root, clean_packages
    )
    if changed is None:
        return None
    # Only packages both snapshots hold are cleaned: one new to the closure
    # owns no artifact this run recorded, and its files may be a peer's.
    known = {
        str(record.get("name"))
        for record in existing_dependencies.get("packages", [])
        if isinstance(record, dict)
    }
    rehashed_closure = _dependents_within(dependencies, rehashed) & known
    changed = (changed | rebuilt | rehashed_closure) & set(clean_packages)
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
        execution_root,
    )
    record = record_path(spec)
    environment = dict(os.environ)
    environment["CARGO_TARGET_DIR"] = target_dir.as_posix()
    cleaned = False
    clean_packages = tuple(str(value) for value in dependencies["clean_packages"])
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
            execution_root,
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
        sibling = None if matched or existing is not None else _sibling_record(spec)
        stale = not matched and (existing is not None or sibling is None)
        # The packages the clean left for the command to rebuild, and the
        # closure's files as read under this run's leases, by the names a
        # record lists. A stale run has neither a match nor a sibling, so
        # only a narrowed clean names them (the widen loop converges only on
        # a readable record, so `current` is set whenever `held` is a proper
        # subset of the closure); a sibling whose files cannot all be read
        # names none, and without them every scope stays exclusive.
        rebuilt: tuple[str, ...] = ()
        named = current if matched else None
        if sibling is not None:
            named = _recorded_artifact(sibling, target_dir, ())
        if stale:
            if clean_command is not None:
                _run_checked(clean_command, execution_root, environment)
            else:
                # The widen loop's converged set, never recomputed: every
                # package this run cleans was held exclusive by that loop, so
                # cleaning it here can never reach past that set.
                targets = tuple(sorted(held))
                if held != frozenset(clean_packages):
                    named = current
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
                rebuilt = targets
            cleaned = True
        # The packages whose artifacts this run writes and discovers afresh.
        fresh = {spec.package, *rebuilt}
        if named is not None and not artifact_paths:
            # The command rebuilds what was cleaned, so those scopes stay
            # exclusive; every other scope is only read from here on, as on a
            # matched run, and peers sharing it enter while the command runs.
            # The downgrade keeps each lease's place in the queue, so no
            # writer queued meanwhile can clean between the clean and the
            # command.
            for lease in taken:
                if lease.owner["package"] not in fresh and lease.mode == EXCLUSIVE:
                    lease.downgrade()
        read_shared = any(lease.mode == SHARED for lease in taken)
        if read_shared and named is None and not artifact_paths:
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
        if read_shared and not artifact_paths:
            # Peers read, and their Cargo may rewrite, every package this run
            # holds shared, so those are found by the names `named` lists,
            # never by discovery, and each is hashed again once two reads
            # agree: the command rebuilt them in place (a fresh export has
            # fresh mtimes, and rustc embeds its path in the bytes). A file
            # that never settles is recorded unverified, and one that cannot
            # be read at all keeps its digest read before the command. Only
            # the packages held exclusive are discovered afresh, and their
            # recorded names are dropped, so a name their rebuild retired is
            # not kept.
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
                        tuple(sorted(fresh)),
                        owners,
                    )
                ],
            )
            files = {}
            for relative, verified in named["files"].items():
                if artifact_package(relative, owners) in fresh:
                    continue
                # Each file gets up to SETTLE_SECONDS, never past the run's
                # wait deadline; at least two reads are always attempted.
                budget = min(time.monotonic_ns() + int(SETTLE_SECONDS * 1_000_000_000), deadline_ns)
                settled = settled_digest(target_dir / relative, budget)
                files[relative] = verified if settled is None else settled
            files.update(own["files"])
            artifact = {"files": files, "digest": artifact_digest(files)}
        else:
            # Declared paths are hashed as named; otherwise every scope is
            # still exclusive, so the closure is discovered.
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
