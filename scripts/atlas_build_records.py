"""A build's identity record: its dimensions, the record file, and what makes two records match."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from atlas_build_artifacts import UNVERIFIED, recorded_artifact_identity
from atlas_build_lease import BuildIdentityError
from atlas_build_lock import retry_sharing_violation
from atlas_build_source import SourceIdentity, _sha256_bytes

VERSION = 7
INDEX_SCHEMA = 1
_INDEX_SCOPE_FIELDS = (
    "package",
    "profile",
    "target",
    "features",
    "toolchain",
    "target_dir",
    "command_key",
    "selection",
    "environment_digest",
    "cargo_config_digest",
)


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
    # The packages the command builds, comma-joined in name order. Cargo
    # unifies features across one invocation's packages, so a shared
    # dependency's variant (its file name) depends on the whole set: a
    # record names the variants of the set that built it, never another's.
    selection: str
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
            "selection": self.selection,
            "environment_digest": self.environment_digest,
            "cargo_config_digest": self.cargo_config_digest,
            "dependency_digest": self.dependency_digest,
        }


@dataclass(frozen=True)
class _SiblingRecord:
    record: dict[str, object]
    artifact: dict[str, object]


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


def _identified_by_files(dependencies: dict[str, object]) -> bool:
    """Whether the snapshot holds the root's own path record.

    That record identifies the root by its own files, and the `inputs`
    field names the files outside them, so the repository's revision and
    tree digest decide nothing: a commit to another member moved them. A
    run of declared artifact paths has no snapshot, and a snapshot whose
    root names no record of its own, so both still compare the repository.
    """
    root = dependencies.get("root")
    return any(
        isinstance(record, dict) and record.get("id") == root and record.get("kind") == "path"
        for record in dependencies.get("packages", [])
    )


def _build_content(build: object, by_files: bool) -> object:
    """A build record's content, without the repository identity when `by_files`."""
    content = _content(build)
    if by_files and isinstance(content, dict):
        content = {key: value for key, value in content.items() if key != "source"}
    return content


def _record_matches(
    existing: dict[str, object],
    spec: BuildSpec,
    dependencies: dict[str, object],
    artifact: dict[str, object],
    inputs: dict[str, object],
) -> bool:
    """`inputs` is `current_inputs` of the record's own `inputs`."""
    return not _record_mismatch_reasons(existing, spec, dependencies, artifact, inputs)


def _record_mismatch_reasons(
    existing: dict[str, object],
    spec: BuildSpec,
    dependencies: dict[str, object],
    artifact: dict[str, object],
    inputs: dict[str, object],
) -> tuple[str, ...]:
    """Name each record component that differs from the current build input."""
    by_files = _identified_by_files(dependencies)
    comparisons = (
        (
            "source",
            by_files or _content(existing.get("source")) == _content(spec.source.as_dict()),
        ),
        (
            "build",
            _build_content(existing.get("build"), by_files)
            == _build_content(spec.as_dict(), by_files),
        ),
        ("dependencies", existing.get("dependencies") == dependencies),
        ("artifact", existing.get("artifact") == artifact),
        ("inputs", existing.get("inputs") == inputs),
    )
    return tuple(name for name, matches in comparisons if not matches)


def _spec_key(spec: BuildSpec) -> str:
    scope = {key: spec.as_dict()[key] for key in _INDEX_SCOPE_FIELDS}
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def record_path(spec: BuildSpec) -> Path:
    return Path(spec.target_dir) / ".atlas" / "source-identity" / f"{_spec_key(spec)}.json"


def _record_index_path(directory: Path) -> Path:
    return directory / "index" / "records.json"


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key {key!r}")
        value[key] = item
    return value


def _scope_key(scope: dict[str, object]) -> str:
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def _validated_index_scope(key: object, value: object, path: Path) -> dict[str, object]:
    if (
        type(key) is not str
        or len(key) != 64
        or any(character not in "0123456789abcdef" for character in key)
        or type(value) is not dict
        or set(value) != set(_INDEX_SCOPE_FIELDS)
        or any(type(value[field]) is not str for field in _INDEX_SCOPE_FIELDS)
        or _scope_key(value) != key
    ):
        raise BuildIdentityError(f"malformed source identity record index: {path}")
    return value


def _read_record_index(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        value = json.loads(read_record_text(path), object_pairs_hook=_unique_object)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise BuildIdentityError(
            f"malformed source identity record index {path}: {error}"
        ) from error
    if type(value) is not dict or set(value) != {"schema", "records"}:
        raise BuildIdentityError(f"malformed source identity record index: {path}")
    if type(value["schema"]) is not int or value["schema"] != INDEX_SCHEMA:
        raise BuildIdentityError(f"unsupported source identity record index: {path}")
    records = value["records"]
    if type(records) is not dict:
        raise BuildIdentityError(f"malformed source identity record index: {path}")
    return {
        key: _validated_index_scope(key, scope, path)
        for key, scope in records.items()
    }


def _canonical_record_scope(path: Path, record: dict[str, object]) -> dict[str, object] | None:
    build = record.get("build")
    if type(build) is not dict:
        return None
    scope = {key: build.get(key) for key in _INDEX_SCOPE_FIELDS}
    if any(type(value) is not str for value in scope.values()) or _scope_key(scope) != path.stem:
        return None
    return scope


def _record_family(scope: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in scope.items() if key != "command_key"}


def _indexed_record_scopes(
    directory: Path, candidates: Sequence[Path]
) -> dict[str, dict[str, object]]:
    index_path = _record_index_path(directory)
    prior = _read_record_index(index_path)
    present = {candidate.stem for candidate in candidates}
    scopes = {key: scope for key, scope in prior.items() if key in present}
    for candidate in candidates:
        if candidate.stem in scopes:
            continue
        try:
            record = read_record(candidate)
        except BuildIdentityError:
            continue
        if record is None:
            continue
        scope = _canonical_record_scope(candidate, record)
        if scope is not None:
            scopes[candidate.stem] = scope
    if not index_path.exists() or scopes != prior:
        _write_atomic(index_path, {"schema": INDEX_SCHEMA, "records": scopes})
    return scopes


def _sibling_record(
    spec: BuildSpec,
    dependencies: dict[str, object],
    inputs_hold: Callable[[dict[str, object]], bool],
) -> _SiblingRecord | None:
    """A record of the same build and source under another command key.

    Its artifact names cover the dependency closure this run reads, so a run
    that holds the dependencies shared hashes them by those names. The
    dependency snapshot, recorded inputs, and current artifact bytes must
    still equal the successful record.
    """
    build = spec.as_dict()
    build.pop("command_key")
    directory = record_path(spec).parent
    if not directory.is_dir():
        return None
    candidates = list(directory.glob("*.json"))
    scopes = _indexed_record_scopes(directory, candidates)
    family = _record_family(
        {key: value for key, value in spec.as_dict().items() if key in _INDEX_SCOPE_FIELDS}
    )
    for candidate in candidates:
        scope = scopes.get(candidate.stem)
        if (
            scope is None
            or scope["command_key"] == spec.command_key
            or _record_family(scope) != family
        ):
            continue
        try:
            record = read_record(candidate)
        except BuildIdentityError:
            continue
        if record is None:
            continue
        if _canonical_record_scope(candidate, record) != scope:
            continue
        other = record.get("build")
        if not isinstance(other, dict):
            continue
        other = dict(other)
        other.pop("command_key", None)
        if (
            _build_content(other, False) == _build_content(build, False)
            and _content(record.get("source")) == _content(spec.source.as_dict())
            and record.get("dependencies") == dependencies
            and inputs_hold(record)
        ):
            artifact = _recorded_artifact(record, Path(spec.target_dir), ())
            if artifact == record.get("artifact"):
                return _SiblingRecord(record, artifact)
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
    except BuildIdentityError:
        return None


def read_record_text(path: Path) -> str:
    """The text of a record or stamp, waiting out a peer's replace of it.

    A replace in flight makes Windows refuse the read; the refusal ends with
    the replace, so it is retried (`retry_sharing_violation`) rather than
    reported as a damaged record.
    """
    return retry_sharing_violation(lambda: path.read_text(encoding="utf-8"), path)


def read_record(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(read_record_text(path))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildIdentityError(f"malformed source identity record {path}: {error}") from error
    version = value.get("version") if isinstance(value, dict) else None
    if type(version) is int and version in {1, 2, 3, 4, 5, 6}:
        return None
    if not isinstance(value, dict) or type(version) is not int or version != VERSION:
        raise BuildIdentityError(f"unsupported source identity record: {path}")
    source = value.get("source")
    build = value.get("build")
    artifact = value.get("artifact")
    dependencies = value.get("dependencies")
    inputs = value.get("inputs")
    if type(inputs) is not dict or any(
        type(package) is not str
        or not (
            files == UNVERIFIED
            or type(files) is dict
            and all(type(key) is str and type(digest) is str for key, digest in files.items())
        )
        for package, files in inputs.items()
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    if (
        not isinstance(source, dict)
        or not isinstance(build, dict)
        or not isinstance(artifact, dict)
        or not isinstance(dependencies, dict)
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    if any(type(source.get(key)) is not str for key in ("root", "revision", "tree_digest")):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    if type(source.get("dirty")) is not bool:
        raise BuildIdentityError(f"malformed source identity record: {path}")
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
            "selection",
            "environment_digest",
            "cargo_config_digest",
            "dependency_digest",
        )
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    files = artifact.get("files")
    if type(files) is not dict or any(type(key) is not str or type(value) is not str for key, value in files.items()):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    if type(artifact.get("digest")) is not str:
        raise BuildIdentityError(f"malformed source identity record: {path}")
    if (
        type(dependencies.get("root")) is not str
        or type(dependencies.get("digest")) is not str
        or type(dependencies.get("packages")) is not list
        or type(dependencies.get("edges")) is not list
        or type(dependencies.get("clean_packages")) is not list
        or any(type(value) is not str for value in dependencies["clean_packages"])
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    return value


def _write_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(value, sort_keys=True, indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        retry_sharing_violation(lambda: os.replace(temporary, path), path)
    except (OSError, BuildIdentityError) as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as cleanup_error:
            raise BuildIdentityError(
                f"cannot write source identity record {path}: {error}; cleanup failed: {cleanup_error}"
            ) from error
        raise BuildIdentityError(f"cannot write source identity record {path}: {error}") from error
