"""Which run last wrote each package's artifacts, so a killed run's progress survives.

A run that is killed after its command rebuilt some packages records nothing,
so the next run reads the older record, finds the rebuilt files changed, and
cleans the packages again. Each package therefore carries a writer mark under
the run's exclusive lease: `cleaning` before a clean, `building` once the
clean has finished and until the command is recorded, `complete` after. A
later run with the same identity resumes the packages still marked
`building` without cleaning them; any other writer replaces the mark, and a
`cleaning` or `complete` mark never resumes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from atlas_build_lease import BuildIdentityError
from atlas_build_records import BuildSpec, _content, _write_atomic
from atlas_build_source import _sha256_bytes

CLEANING = "cleaning"
BUILDING = "building"
COMPLETE = "complete"
_STATES = (CLEANING, BUILDING, COMPLETE)
_VERSION = 1


def writer_path(target_dir: Path, package: str) -> Path:
    return target_dir / ".atlas" / "source-identity" / "writers" / f"{quote(package, safe='')}.json"


def run_identity(spec: BuildSpec, dependency_digests: dict[str, str]) -> str:
    """The digest of everything that decides what a run's command writes.

    The source content, build dimensions and dependency snapshots of every
    package the command builds; the checkout path and the package a record
    is kept for are excluded, as for records.
    """
    build = _content(spec.as_dict())
    if not isinstance(build, dict):
        raise BuildIdentityError("build spec is not a mapping")
    build = {key: value for key, value in build.items() if key not in ("package", "dependency_digest")}
    payload = json.dumps(
        {"build": build, "dependencies": dict(sorted(dependency_digests.items()))},
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_bytes(payload.encode())


def _read(target_dir: Path, package: str) -> dict[str, object] | None:
    try:
        value = json.loads(writer_path(target_dir, package).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # An unreadable mark resumes nothing: the run cleans as it always did.
        return None
    if not isinstance(value, dict) or value.get("version") != _VERSION or value.get("state") not in _STATES:
        return None
    return value


def resumable(target_dir: Path, packages: Iterable[str], identity: str) -> frozenset[str]:
    """The packages whose last writer was an unfinished run of this identity."""
    resumed = set()
    for package in packages:
        mark = _read(target_dir, package)
        if mark is not None and mark["state"] == BUILDING and mark.get("identity") == identity:
            resumed.add(package)
    return frozenset(resumed)


def mark(target_dir: Path, packages: Iterable[str], state: str, identity: str) -> None:
    """Record `state` as the last writer of each package; the caller holds each exclusive."""
    if state not in _STATES:
        raise BuildIdentityError(f"unknown writer state {state}")
    for package in packages:
        _write_atomic(
            writer_path(target_dir, package),
            {"version": _VERSION, "state": state, "identity": identity},
        )

