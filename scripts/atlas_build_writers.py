"""Which run last wrote each package's artifacts, so a killed run's progress survives.

A run that is killed after its command rebuilt some packages records nothing,
so the next run reads the older record, finds the rebuilt files changed, and
cleans the packages again. Each package therefore carries a writer mark under
the run's exclusive lease: `cleaning` before a clean, `building` once the
clean has finished and until the command is recorded, `complete` after. A
later run with the same identity resumes the packages still marked
`building` without cleaning them; any other writer replaces the mark, and a
`cleaning` or `complete` mark never resumes.

A mark cannot see a peer that writes the package without a lease, and Cargo
trusts artifacts whose sources are older than they are. While the command
runs, a heartbeat refreshes each `building` mark every `HEARTBEAT_SECONDS`;
a rerun resumes a package only if none of its artifact or fingerprint files
is newer than the mark's last heartbeat. The kill stops the heartbeat, so a
peer's later write, and the killed run's own last interval of output, are
newer and clean; progress older than the final heartbeat survives.
"""

from __future__ import annotations

import json
import os
import re
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator
from urllib.parse import quote

from atlas_build_lease import BuildIdentityError
from atlas_build_records import BuildSpec, _content, _write_atomic
from atlas_build_source import _sha256_bytes

CLEANING = "cleaning"
BUILDING = "building"
COMPLETE = "complete"
_STATES = (CLEANING, BUILDING, COMPLETE)
_VERSION = 1
# The most progress a kill can cost: the killed run's files written after the
# last heartbeat are cleaned with a peer's. Short against a cold build of
# minutes, long enough that the heartbeat's writes (one small file per
# package) stay negligible beside Cargo's.
HEARTBEAT_SECONDS = 5.0
_SUBDIRECTORIES = ("deps", ".fingerprint", "build")


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


def _artifact_pattern(package: str) -> re.Pattern[str]:
    names = "|".join(re.escape(name) for name in {package, package.replace("-", "_")})
    return re.compile(rf"^(?:lib)?(?:{names})-[0-9a-f]+(?:\.|$)")


def _raise(error: OSError) -> None:
    raise error


def _subdirectories(directory: Path) -> list[Path]:
    with os.scandir(directory) as scan:
        paths = [entry.path for entry in scan]
    return [Path(path) for path in paths if stat.S_ISDIR(os.stat(path).st_mode)]


def _profile_directories(target_dir: Path) -> Iterator[Path]:
    """Directories that may hold `deps` or `.fingerprint`: `<profile>` and `<triple>/<profile>`.

    A listing or stat error propagates: a scan that cannot see a directory
    cannot vouch for it.
    """
    for first in _subdirectories(target_dir):
        yield first
        yield from _subdirectories(first)


def written_after(target_dir: Path, package: str, since_ns: int) -> bool:
    """Whether any artifact or fingerprint file of `package` is newer than `since_ns`.

    Over-matches by name only (a longer package sharing the prefix and a hash
    suffix), which cleans more, never less. A directory or file that cannot
    be listed or read, or vanishes mid-scan, counts as newer.
    """
    pattern = _artifact_pattern(package)
    try:
        for directory in _profile_directories(target_dir):
            with os.scandir(directory) as scan:
                present = {entry.name for entry in scan}
            for subdirectory in _SUBDIRECTORIES:
                if subdirectory not in present:
                    continue
                with os.scandir(directory / subdirectory) as scan:
                    paths = [entry.path for entry in scan if pattern.match(entry.name)]
                for path in paths:
                    status = os.stat(path)
                    if status.st_mtime_ns > since_ns:
                        return True
                    if stat.S_ISDIR(status.st_mode):
                        for parent, directories, files in os.walk(path, onerror=_raise):
                            for name in (*directories, *files):
                                if os.stat(os.path.join(parent, name)).st_mtime_ns > since_ns:
                                    return True
    except OSError:
        return True
    return False


def resumable(target_dir: Path, packages: Iterable[str], identity: str) -> frozenset[str]:
    """The packages whose last writer was an unfinished run of this identity.

    Only if nothing of theirs was written after that run's last heartbeat.
    """
    resumed = set()
    for package in packages:
        written = _read(target_dir, package)
        heartbeat_ns = written.get("heartbeat_ns") if written is not None else None
        if (
            written is not None
            and written["state"] == BUILDING
            and written.get("identity") == identity
            and type(heartbeat_ns) is int
            and not written_after(target_dir, package, heartbeat_ns)
        ):
            resumed.add(package)
    return frozenset(resumed)


def mark(
    target_dir: Path, packages: Iterable[str], state: str, identity: str, at_ns: int | None = None
) -> None:
    """Record `state` at `at_ns` (default now) for each package; the caller holds each exclusive."""
    if state not in _STATES:
        raise BuildIdentityError(f"unknown writer state {state}")
    for package in packages:
        _write_atomic(
            writer_path(target_dir, package),
            {
                "version": _VERSION,
                "state": state,
                "identity": identity,
                "heartbeat_ns": time.time_ns() if at_ns is None else at_ns,
            },
        )


@contextmanager
def heartbeat(target_dir: Path, packages: Iterable[str], identity: str) -> Iterator[None]:
    """Refresh the `building` marks every `HEARTBEAT_SECONDS` while the caller's command runs."""
    held = tuple(packages)
    stopped = threading.Event()

    def beat() -> None:
        while not stopped.wait(HEARTBEAT_SECONDS):
            # Read before the stop check: no beat is stamped after the command
            # exited, which would vouch for a peer's later write.
            stamp = time.time_ns()
            if stopped.is_set():
                return
            try:
                mark(target_dir, held, BUILDING, identity, stamp)
            except (OSError, BuildIdentityError):
                # A missed beat only ages the mark, so a rerun cleans more.
                continue

    thread = threading.Thread(target=beat, name="writer-heartbeat", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set()
        thread.join()
