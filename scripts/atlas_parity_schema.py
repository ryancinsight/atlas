"""Protocol 1 structural contracts shared by the parity gate.

Schema violations fail closed. These are checks on supplied evidence, not a
claim that the gate independently proves a numerical theorem or remote result.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse


class ParityError(ValueError):
    """A parity artifact violates a required schema or traceability invariant."""


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ParityError(message)


def fields(record: dict, required: dict[str, type], context: str) -> None:
    need(isinstance(record, dict), f"{context}: expected object")
    for key, kind in required.items():
        need(key in record and type(record[key]) is kind,
             f"{context}.{key}: expected {kind.__name__}")


def source_selector(path: object, context: str) -> None:
    """JSON source paths use string keys and exact nonnegative integer offsets."""
    need(type(path) is list, f"{context}: source selector must be a list")
    for key in path:
        need(type(key) is str or (type(key) is int and key >= 0),
             f"{context}: invalid source selector component {key!r}")


def source_entry_at(document: object, path: object, context: str) -> object:
    """Resolve a typed JSON path without Python's bool/int or negative-index aliases."""
    source_selector(path, context)
    for key in path:
        if type(document) is dict:
            need(type(key) is str and key in document,
                 f"{context}: source selector object key absent or not a string")
        elif type(document) is list:
            need(type(key) is int and key < len(document),
                 f"{context}: source selector list offset absent or not an integer")
        else:
            need(False, f"{context}: source selector traverses a scalar")
        document = document[key]
    return document


def nonempty(value: object, context: str) -> None:
    need(isinstance(value, str) and bool(value.strip()), f"{context}: empty text")


def finite_number(value: object) -> bool:
    """Bounded estimates exclude booleans and nonfinite floating values."""
    return type(value) is int or (type(value) is float and math.isfinite(value))


def revision(value: object, context: str) -> None:
    need(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None,
         f"{context}: expected exact 40-character Git revision")


def digest(value: object, context: str) -> None:
    need(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
         f"{context}: expected SHA-256")


def https(value: object, context: str) -> None:
    need(isinstance(value, str), f"{context}: expected HTTPS URL")
    parsed = urlparse(value)
    need(parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username,
         f"{context}: expected durable HTTPS URL without credentials")


def unique(rows: list[dict], key: str, context: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        fields(row, {key: str}, context)
        nonempty(row[key], context)
        need(row[key] not in result, f"{context}: duplicate {key} {row[key]}")
        result[row[key]] = row
    return result


def dag(rows: dict[str, dict], key: str, context: str) -> None:
    visiting, visited = set(), set()

    def visit(identity: str) -> None:
        need(identity not in visiting, f"{context}: dependency cycle at {identity}")
        if identity in visited:
            return
        visiting.add(identity)
        fields(rows[identity], {key: list}, identity)
        for dependency in rows[identity][key]:
            need(isinstance(dependency, str) and dependency in rows,
                 f"{context}: unknown dependency {dependency!r} in {identity}")
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in rows:
        visit(identity)


def read_json(path: Path) -> object:
    def no_duplicates(pairs: list[tuple]) -> dict:
        result = {}
        for key, value in pairs:
            need(key not in result, f"{path}: duplicate JSON key {key}")
            result[key] = value
        return result

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ParityError(f"{path}: {error}") from error


def local_path(root: Path, relative: str) -> Path:
    need(isinstance(relative, str), "artifact path must be text")
    path = (root / relative).resolve()
    need(path.is_relative_to(root.resolve()), f"artifact escapes program directory: {relative}")
    need(path.is_file(), f"artifact does not exist: {relative}")
    return path


def api_identity(framework: str, version: str, row: dict) -> str:
    """Keep declarations from different sources/versions; never dedupe by name."""
    fields(row, {"symbol": str, "kind": str, "source": str}, framework)
    provenance = hashlib.sha256(row["source"].encode()).hexdigest()[:16]
    return f"{framework}@{version}|{row['kind']}|{row['symbol']}|{provenance}"
