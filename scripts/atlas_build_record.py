"""Read and atomically write shared build identity records."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from atlas_build_lease import BuildIdentityError
from atlas_build_target import TargetDirectory

if TYPE_CHECKING:
    from atlas_build_identity import BuildSpec

RECORD_VERSION = 6
STALE_RECORD_VERSIONS = frozenset({1, 2, 3, 4, 5})


def _spec_key(spec: BuildSpec) -> str:
    scope = spec.as_dict()
    scope.pop("source")
    scope.pop("dependency_digest")
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def record_path(spec: BuildSpec) -> Path:
    return Path(spec.target_dir) / ".atlas" / "source-identity" / f"{_spec_key(spec)}.json"


def _keys(value: dict[str, object], expected: set[str]) -> bool:
    return value.keys() == expected


def _sha256(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _absolute_path(value: str) -> bool:
    return (
        Path(value).is_absolute()
        or value.startswith("\\\\")
        or (
            len(value) >= 3
            and value[1] == ":"
            and value[2] in "/\\"
        )
    )


def _source_record(value: object) -> bool:
    if type(value) is not dict or not _keys(
        value, {"root", "revision", "tree_digest", "dirty"}
    ):
        return False
    revision = value["revision"]
    return (
        type(value["root"]) is str
        and bool(value["root"])
        and _absolute_path(value["root"])
        and type(revision) is str
        and len(revision) in {40, 64}
        and re.fullmatch(r"[0-9a-f]+", revision) is not None
        and _sha256(value["tree_digest"])
        and type(value["dirty"]) is bool
    )


def _dependency_record(value: object) -> bool:
    if type(value) is not dict or not _keys(
        value, {"root", "packages", "edges", "clean_packages", "digest"}
    ):
        return False
    if (
        type(value["root"]) is not str
        or not value["root"]
        or type(value["packages"]) is not list
        or type(value["edges"]) is not list
        or type(value["clean_packages"]) is not list
        or any(type(name) is not str or not name for name in value["clean_packages"])
        or value["clean_packages"] != sorted(set(value["clean_packages"]))
        or not _sha256(value["digest"])
    ):
        return False
    for package in value["packages"]:
        if type(package) is not dict:
            return False
        kind = package.get("kind")
        common = {"id", "name", "version", "features", "kind"}
        if (
            type(package.get("id")) is not str
            or not package["id"]
            or type(package.get("name")) is not str
            or not package["name"]
            or type(package.get("version")) is not str
            or not package["version"]
            or type(package.get("features")) is not list
            or any(type(feature) is not str for feature in package["features"])
            or package["features"] != sorted(set(package["features"]))
        ):
            return False
        if kind == "path":
            if not _keys(package, common | {"identity"}) or not _source_record(
                package["identity"]
            ):
                return False
        elif kind == "git":
            if (
                not _keys(package, common | {"source", "identity"})
                or type(package["source"]) is not str
                or not package["source"]
                or not _source_record(package["identity"])
            ):
                return False
        elif kind == "registry":
            if (
                not _keys(package, common | {"source", "content_digest"})
                or type(package["source"]) is not str
                or not package["source"]
                or not _sha256(package["content_digest"])
            ):
                return False
        else:
            return False
    for edge in value["edges"]:
        if (
            type(edge) is not dict
            or not _keys(edge, {"from", "to", "dep_kinds"})
            or type(edge["from"]) is not str
            or type(edge["to"]) is not str
            or type(edge["dep_kinds"]) is not list
            or any(
                type(kind) is not dict
                or not _keys(kind, {"kind", "target"})
                or kind["kind"] is not None
                and type(kind["kind"]) is not str
                or kind["target"] is not None
                and type(kind["target"]) is not str
                for kind in edge["dep_kinds"]
            )
        ):
            return False
    expected_digest = dict(value)
    expected_digest.pop("digest")
    digest = hashlib.sha256(
        json.dumps(expected_digest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return value["digest"] == digest


def _artifact_record(value: object) -> bool:
    if type(value) is not dict or not _keys(value, {"files", "digest"}):
        return False
    files = value["files"]
    if type(files) is not dict or not files:
        return False
    for path, digest in files.items():
        relative = PurePosixPath(path) if type(path) is str else None
        if (
            relative is None
            or not path
            or relative.is_absolute()
            or "\\" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or not _sha256(digest)
        ):
            return False
    expected_digest = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return value["digest"] == expected_digest


def _build_record(value: object, source: object, dependencies: object) -> bool:
    if type(value) is not dict or not _keys(
        value,
        {
            "source",
            "package",
            "profile",
            "target",
            "features",
            "toolchain",
            "target_dir",
            "command_key",
            "environment_digest",
            "dependency_digest",
        },
    ):
        return False
    return (
        value["source"] == source
        and all(
            type(value[key]) is str
            for key in (
                "package",
                "profile",
                "target",
                "features",
                "toolchain",
                "target_dir",
                "command_key",
            )
        )
        and all(
            value[key]
            for key in ("package", "profile", "target", "toolchain", "target_dir", "command_key")
        )
        and _absolute_path(value["target_dir"])
        and _sha256(value["environment_digest"])
        and _sha256(value["dependency_digest"])
        and type(dependencies) is dict
        and value["dependency_digest"] == dependencies.get("digest")
    )


def read_record(target: TargetDirectory, path: Path) -> dict[str, object] | None:
    payload = target.read_file(path)
    if payload is None:
        return None
    try:
        value = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BuildIdentityError(f"malformed source identity record {path}: {error}") from error
    version = value.get("version") if isinstance(value, dict) else None
    if type(version) is int and version in STALE_RECORD_VERSIONS:
        return None
    if not isinstance(value, dict) or type(version) is not int or version != RECORD_VERSION:
        raise BuildIdentityError(f"unsupported source identity record: {path}")
    if not _keys(value, {"version", "source", "build", "dependencies", "artifact"}):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    source = value["source"]
    if (
        not _source_record(source)
        or not _dependency_record(value["dependencies"])
        or not _artifact_record(value["artifact"])
        or not _build_record(value["build"], source, value["dependencies"])
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    return value


def write_record(
    target: TargetDirectory, path: Path, value: dict[str, object]
) -> None:
    _validate_record(value, path)
    payload = json.dumps(value, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    target.atomic_write(path, payload)


def _validate_record(value: object, path: Path) -> None:
    try:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
        parsed = json.loads(payload)
    except (TypeError, ValueError) as error:
        raise BuildIdentityError(f"malformed source identity record for {path}: {error}") from error
    if (
        type(parsed) is not dict
        or type(parsed.get("version")) is not int
        or parsed["version"] != RECORD_VERSION
        or not _keys(parsed, {"version", "source", "build", "dependencies", "artifact"})
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
    source = parsed["source"]
    if (
        not _source_record(source)
        or not _dependency_record(parsed["dependencies"])
        or not _artifact_record(parsed["artifact"])
        or not _build_record(parsed["build"], source, parsed["dependencies"])
    ):
        raise BuildIdentityError(f"malformed source identity record: {path}")
