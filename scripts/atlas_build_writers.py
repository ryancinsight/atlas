"""Which run last wrote each package's artifacts, so a killed run's progress survives.

A run that is killed after its command rebuilt some packages records nothing,
so the next run reads the older record, finds the rebuilt files changed, and
cleans the packages again. Each package therefore carries a writer mark under
the run's exclusive lease: `cleaning` before a clean, `building` once the
clean has finished and until the command is recorded, `complete` after. A
later run with the same identity resumes the packages still marked
`building` without cleaning them; any other writer replaces the mark, and a
`cleaning` or `complete` mark never resumes.

Marks are per physical Cargo profile and shared by its host and target-triple
directories, because host artifacts can overlap every target build.

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
from urllib.parse import quote, unquote

from atlas_build_lease import BuildIdentityError
from atlas_build_records import BuildSpec, _content, _write_atomic
from atlas_build_source import _sha256_bytes
from atlas_build_stamps import BuildDirectory

CLEANING = "cleaning"
BUILDING = "building"
COMPLETE = "complete"
_STATES = (CLEANING, BUILDING, COMPLETE)
_VERSION = 2
# The most progress a kill can cost: the killed run's files written after the
# last heartbeat are cleaned with a peer's. Short against a cold build of
# minutes, long enough that the heartbeat's writes (one small file per
# package) stay negligible beside Cargo's.
HEARTBEAT_SECONDS = 5.0
_SUBDIRECTORIES = ("deps", ".fingerprint", "build")


def _writer_root(target_dir: Path) -> Path:
    return target_dir / ".atlas" / "source-identity" / "writers"


def _profile_key(profile: str) -> str:
    key = quote(profile, safe="")
    if not key or key in (".", ".."):
        raise BuildIdentityError(f"invalid writer profile {profile!r}")
    return key


def writer_path(directory: BuildDirectory, package: str) -> Path:
    """The package writer for one physical profile, shared across target triples."""
    return _writer_root(directory.target_dir) / _profile_key(directory.profile) / (
        f"{quote(package, safe='')}.json"
    )


def _legacy_writer_path(target_dir: Path, package: str) -> Path:
    return _writer_root(target_dir) / f"{quote(package, safe='')}.json"


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


def _read(directory: BuildDirectory, package: str) -> dict[str, object] | None:
    try:
        value = json.loads(writer_path(directory, package).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # An unreadable mark resumes nothing: the run cleans as it always did.
        return None
    if not isinstance(value, dict) or value.get("version") != _VERSION or value.get("state") not in _STATES:
        return None
    return value


def _legacy_fingerprint(target_dir: Path, package: str) -> dict[str, object]:
    """The old target-wide marker state; any later old-tool action disables resume."""
    path = _legacy_writer_path(target_dir, package)
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except FileNotFoundError:
        return {"status": "absent"}
    except OSError as error:
        raise BuildIdentityError(f"cannot read legacy writer mark {path}: {error}") from error
    first = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    second = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if first != second:
        raise BuildIdentityError(f"legacy writer mark changed while reading {path}")
    return {
        "status": "present",
        "device": before.st_dev,
        "inode": before.st_ino,
        "size": before.st_size,
        "modified_ns": before.st_mtime_ns,
        "sha256": _sha256_bytes(content),
    }


def _artifact_pattern(package: str) -> re.Pattern[str]:
    names = "|".join(re.escape(name) for name in {package, package.replace("-", "_")})
    return re.compile(rf"^(?:lib)?(?:{names})-[0-9a-f]+(?:\.|$)")


def _raise(error: OSError) -> None:
    raise error


def _subdirectories(directory: Path) -> list[Path]:
    with os.scandir(directory) as scan:
        paths = [entry.path for entry in scan]
    return [Path(path) for path in paths if stat.S_ISDIR(os.stat(path).st_mode)]


def _profile_directories(directory: BuildDirectory) -> Iterator[Path]:
    """The host and target-triple directories for one physical profile.

    A listing or stat error propagates: a scan that cannot see a directory
    cannot vouch for it.
    """
    for first in _subdirectories(directory.target_dir):
        if first.name == directory.profile:
            yield first
            continue
        profile = first / directory.profile
        try:
            status = profile.stat()
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(status.st_mode):
            raise NotADirectoryError(profile)
        yield profile


def written_after(directory: BuildDirectory, package: str, since_ns: int) -> bool:
    """Whether any artifact or fingerprint file of `package` is newer than `since_ns`.

    Over-matches by name only (a longer package sharing the prefix and a hash
    suffix), which cleans more, never less. A directory or file that cannot
    be listed or read, or vanishes mid-scan, counts as newer.
    """
    pattern = _artifact_pattern(package)
    try:
        for profile in _profile_directories(directory):
            with os.scandir(profile) as scan:
                present = {entry.name for entry in scan}
            for subdirectory in _SUBDIRECTORIES:
                if subdirectory not in present:
                    continue
                with os.scandir(profile / subdirectory) as scan:
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


def resumable(
    directory: BuildDirectory, packages: Iterable[str], identity: str
) -> frozenset[str]:
    """The packages whose last writer was an unfinished run of this identity.

    Only if nothing of theirs was written after that run's last heartbeat.
    """
    resumed = set()
    for package in packages:
        written = _read(directory, package)
        heartbeat_ns = written.get("heartbeat_ns") if written is not None else None
        try:
            legacy_unchanged = (
                written is not None
                and written.get("legacy") == _legacy_fingerprint(directory.target_dir, package)
            )
        except BuildIdentityError:
            legacy_unchanged = False
        if (
            written is not None
            and written["state"] == BUILDING
            and written.get("identity") == identity
            and type(heartbeat_ns) is int
            and legacy_unchanged
            and not written_after(directory, package, heartbeat_ns)
        ):
            resumed.add(package)
    return frozenset(resumed)


def mark(
    directory: BuildDirectory,
    packages: Iterable[str],
    state: str,
    identity: str,
    at_ns: int | None = None,
) -> None:
    """Record `state` at `at_ns` (default now) for each package; the caller holds each exclusive."""
    if state not in _STATES:
        raise BuildIdentityError(f"unknown writer state {state}")
    for package in packages:
        existing = _read(directory, package)
        legacy = (
            existing["legacy"]
            if existing is not None and isinstance(existing.get("legacy"), dict)
            else _legacy_fingerprint(directory.target_dir, package)
        )
        _write_atomic(
            writer_path(directory, package),
            {
                "version": _VERSION,
                "state": state,
                "identity": identity,
                "heartbeat_ns": time.time_ns() if at_ns is None else at_ns,
                "legacy": legacy,
            },
        )


def _marked_profiles(directory: BuildDirectory) -> set[str]:
    """Physical profiles with new writer marks; legacy files are not profiles."""
    root = _writer_root(directory.target_dir)
    try:
        with os.scandir(root) as scan:
            entries = list(scan)
    except FileNotFoundError:
        return {directory.profile}
    except OSError as error:
        raise BuildIdentityError(f"cannot list writer profiles {root}: {error}") from error
    profiles = {directory.profile}
    for entry in entries:
        try:
            if entry.is_file(follow_symlinks=False) and entry.name.endswith(".json"):
                continue
            if not entry.is_dir(follow_symlinks=False):
                raise BuildIdentityError(f"ambiguous writer profile entry {entry.path}")
        except OSError as error:
            raise BuildIdentityError(f"cannot inspect writer profile {entry.path}: {error}") from error
        profile = unquote(entry.name)
        if _profile_key(profile) != entry.name:
            raise BuildIdentityError(f"invalid writer profile path {entry.path}")
        profiles.add(profile)
    return profiles


def mark_broad_clean(
    directory: BuildDirectory, packages: Iterable[str], identity: str
) -> None:
    """Invalidate every marked physical profile before an opaque clean."""
    held = tuple(packages)
    for profile in _marked_profiles(directory):
        mark(
            BuildDirectory(directory.target_dir, profile, directory.target),
            held,
            CLEANING,
            identity,
        )


@contextmanager
def heartbeat(
    directory: BuildDirectory, packages: Iterable[str], identity: str
) -> Iterator[None]:
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
                mark(directory, held, BUILDING, identity, stamp)
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
