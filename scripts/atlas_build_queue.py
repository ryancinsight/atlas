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
_TICKET_SUFFIX = ".ticket"
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


def _fields(name: str) -> tuple[int, str, str]:
    """A ticket name's arrival, mode letter and run.

    The name is `arrival-mode-run-pid-uuid`. A ticket of a checker that
    predates runs is `arrival-mode-pid-uuid`; its pid and uuid stand in for
    the run, which is unique to that ticket, so it ties with nothing.
    """
    arrival, mode, *rest = name.removesuffix(_TICKET_SUFFIX).split("-")
    return int(arrival), mode, rest[0] if len(rest) == 3 else "-".join(rest)


def place_of(name: str) -> tuple[int, str]:
    """A ticket's place in the arrival order: `(arrival, run)`.

    The order is strict and total across the runs that queue at one lease,
    and it is the same at every lease: a run's tickets all carry its arrival
    and its run, and two runs never share a run. The mode is not part of it,
    since it differs from lease to lease for one run.
    """
    arrival, _, run = _fields(name)
    return arrival, run


def _is_exclusive(name: str) -> bool:
    return _fields(name)[1] == _TICKET_MODES[EXCLUSIVE]


class Ticket:
    """A request's place in a lease's arrival order.

    The file is named by the system-wide monotonic clock at arrival, then the
    mode and the run (one identifier for every ticket of a run, whatever the
    lease), and locked by its requester until it releases the lease. A
    requester that loses the race between creating and locking its file, to a
    peer's liveness check or collection, retries under a new name with the
    same arrival; one whose locked file a peer's collection removed anyway
    (POSIX unlinks open files) re-creates it with the same arrival at its next
    attempt.
    """

    def __init__(
        self,
        path: Path,
        mode: str,
        owner: dict[str, object],
        arrival: int | None = None,
        run: str | None = None,
    ) -> None:
        self.directory = _queue_dir(path)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lease = path
        self.mode = mode
        self.record = {**owner, "mode": mode}
        self.arrival = time.monotonic_ns() if arrival is None else arrival
        self.run = uuid.uuid4().hex if run is None else run
        self._create()

    @property
    def place(self) -> tuple[int, str]:
        """This ticket's place in the arrival order."""
        return self.arrival, self.run

    def _create(self) -> None:
        for _ in range(_TICKET_ATTEMPTS):
            name = (
                f"{self.arrival:020d}-{_TICKET_MODES[self.mode]}-{self.run}"
                f"-{os.getpid()}-{uuid.uuid4().hex}"
            )
            candidate = self.directory / f"{name}{_TICKET_SUFFIX}"
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
            if place_of(other.name) < self.place and (mode == EXCLUSIVE or _is_exclusive(other.name)):
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


def conflicting(
    path: Path, mode: str, place: tuple[int, str], own: Path | None = None
) -> tuple[list[Path], list[Path]]:
    """Live tickets of the lease at `path` that a `mode` request at `place` conflicts with.

    Returns the tickets whose place is before the request's and those whose
    place is after it, collecting dead ones. Places are `(arrival, run)`, the
    order `Ticket.ahead` uses, so the two agree on every pair, ties included.
    A shared request conflicts with exclusive tickets only; an exclusive one
    with every ticket. `own` is the requester's ticket, and any ticket of the
    request's own run, which never conflicts with itself.
    """
    before: list[Path] = []
    after: list[Path] = []
    for other in sorted(_queue_dir(path).glob(f"*{_TICKET_SUFFIX}")):
        if other == own:
            continue
        other_place = place_of(other.name)
        if other_place == place:
            continue
        if mode != EXCLUSIVE and not _is_exclusive(other.name):
            continue
        if not _ticket_is_live(other):
            continue
        (before if other_place < place else after).append(other)
    return before, after


def _names(path: Path, handle: Any) -> bool:
    """Whether `path` still names the file `handle` has open."""
    try:
        return os.path.samestat(os.fstat(handle.fileno()), os.stat(path))
    except FileNotFoundError:
        return False
