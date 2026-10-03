"""Arrival-order queue of requests for one build-scope lease."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

from atlas_build_lock import (
    EXCLUSIVE,
    SHARED,
    BuildIdentityError,
    SHARING_RETRY_ATTEMPTS,
    _release,
    _try_lock,
    _unlock,
    _write_record,
    retry_sharing_violation,
)

_TICKET_MODES = {EXCLUSIVE: "x", SHARED: "s"}
_TICKET_ATTEMPTS = 100
_RETRY_SECONDS = 0.005


def _queue_dir(path: Path) -> Path:
    return path.with_name(f"{path.stem}.queue")


def _unlink(path: Path, attempts: int = 1) -> None:
    # Windows refuses while a peer's liveness check has the file open, and
    # that check closes within the sharing-violation bound. A ticket left
    # behind when the refusal outlasts `attempts` is unlocked, and the next
    # scan collects it, so the release that called this must not fail on it.
    try:
        retry_sharing_violation(path.unlink, path, attempts)
    except FileNotFoundError:
        return
    except BuildIdentityError:
        return


def _ticket_is_live(path: Path) -> bool:
    """A ticket is live while its requester holds its lock; a dead one is removed."""
    try:
        handle = path.open("rb")
    except (FileNotFoundError, PermissionError):
        # Gone, or on Windows pending deletion by its requester's release.
        return False
    try:
        # Shared, against the requester's exclusive lock: concurrent checks
        # then never make a dead ticket look held to one another.
        if not _try_lock(handle, SHARED):
            return True
        _unlock(handle)
    finally:
        handle.close()
    _unlink(path)
    return False


class Ticket:
    """A request's place in a lease's arrival order.

    The file is named by the system-wide monotonic clock at arrival and locked
    by its requester until it releases the lease. A requester that loses the
    race between creating and locking its file, to a peer's liveness check
    or collection, retries under a new name with the same arrival; one whose
    locked file a peer's collection removed anyway (POSIX unlinks open files)
    re-creates it with the same arrival at its next attempt.
    """

    def __init__(self, path: Path, mode: str, owner: dict[str, object]) -> None:
        self.directory = _queue_dir(path)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lease = path
        self.mode = mode
        self.record = {**owner, "mode": mode}
        self.arrival = time.monotonic_ns()
        self._create()

    def _create(self) -> None:
        for _ in range(_TICKET_ATTEMPTS):
            name = f"{self.arrival:020d}-{_TICKET_MODES[self.mode]}-{os.getpid()}-{uuid.uuid4().hex}"
            candidate = self.directory / f"{name}.ticket"
            handle = candidate.open("x+b")
            locked = False
            try:
                locked = _try_lock(handle)
                if locked and _names(candidate, handle):
                    _write_record(handle, self.record)
                    self.path, self.handle = candidate, handle
                    return
            except BaseException:
                _release(handle, locked)
                _unlink(candidate)
                raise
            _release(handle, locked)
            _unlink(candidate)
            time.sleep(_RETRY_SECONDS)
        raise BuildIdentityError(f"cannot queue for source identity lease {self.lease}")

    def ahead(self, mode: str) -> list[Path]:
        """Live earlier requests this one may not pass, collecting dead tickets.

        An exclusive request waits for every earlier request, a shared one for
        earlier exclusive requests only: readers that arrived together share,
        and a waiting writer holds back every later reader.
        """
        self.refile()
        blockers = []
        for other in sorted(self.directory.glob("*.ticket")):
            if other == self.path or not _ticket_is_live(other):
                continue
            if other.name < self.path.name and (
                mode == EXCLUSIVE or f"-{_TICKET_MODES[EXCLUSIVE]}-" in other.name
            ):
                blockers.append(other)
        return blockers

    def refile(self) -> None:
        """Re-create this ticket, with its arrival, if a peer's collection removed it."""
        if not _names(self.path, self.handle):
            _release(self.handle, locked=True)
            self._create()

    def downgrade(self) -> None:
        """Re-file this request as shared, keeping its arrival and so its place.

        The shared ticket is created before the exclusive one is removed, so
        a later request always sees an earlier ticket of this requester.
        """
        if self.mode == SHARED:
            return
        previous_path, previous_handle = self.path, self.handle
        self.mode = SHARED
        self.record = {**self.record, "mode": SHARED}
        self._create()
        try:
            _release(previous_handle, locked=True)
        finally:
            _unlink(previous_path, SHARING_RETRY_ATTEMPTS)

    def close(self) -> None:
        try:
            _release(self.handle, locked=True)
        finally:
            _unlink(self.path, SHARING_RETRY_ATTEMPTS)


def _names(path: Path, handle: Any) -> bool:
    """Whether `path` still names the file `handle` has open."""
    try:
        return os.path.samestat(os.fstat(handle.fileno()), os.stat(path))
    except FileNotFoundError:
        return False
