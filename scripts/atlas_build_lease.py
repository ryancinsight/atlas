"""Crash-recoverable ownership leases for shared build scopes."""

from __future__ import annotations

import hashlib
import json
import sys
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import Sequence

from atlas_build_lock import (
    BuildIdentityError,
    EXCLUSIVE,
    SHARED,
    RECORD_OFFSET,
    _MODES,
    _downgrade,
    _open_lease,
    _release,
    _take,
    _try_lock,
    _unlock,
    _write_record,
)
from atlas_build_queue import Ticket, conflicting


class LeaseHeldError(BuildIdentityError):
    """A live process holds the lease, or an earlier request is queued for it."""

    def __init__(self, message: str, holder: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.holder = holder or {}


_WAIT_FIRST_SECONDS = 0.1
_WAIT_MAX_SECONDS = 5.0


def package_target_lease_path(package: str, target_dir: Path) -> Path:
    scope = {"package": package, "target_dir": target_dir.as_posix()}
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    key = hashlib.sha256(encoded).hexdigest()
    return target_dir / ".atlas" / "source-identity" / f"{key}.lock"


def package_target_lease_scopes(
    package: str,
    target_dir: Path,
    root: str,
    revision: str,
    clean_packages: list[str] | tuple[str, ...] | set[str],
) -> list[tuple[Path, dict[str, object]]]:
    packages = {str(value) for value in clean_packages}
    packages.add(package)
    return [
        (
            package_target_lease_path(name, target_dir),
            {
                "root": root,
                "revision": revision,
                "package": name,
                "target_dir": target_dir.as_posix(),
            },
        )
        for name in sorted(packages)
    ]


class OwnerLease:
    """A lease on one build scope, held shared (reading) or exclusive (writing).

    Requests are served in arrival order through `Ticket`; the OS lock on
    byte 0 of the lease file stays the authority on who holds it. Only an
    exclusive holder writes the owner record.
    """

    def __init__(
        self,
        path: Path,
        owner: dict[str, object],
        seconds: int,
        mode: str = EXCLUSIVE,
        arrival: int | None = None,
        run: str | None = None,
    ) -> None:
        if seconds <= 0:
            raise BuildIdentityError("lease duration must be positive")
        if mode not in _MODES:
            raise BuildIdentityError(f"unknown lease mode {mode}")
        self.path = path
        self.owner = owner
        self.seconds = seconds
        self.mode = mode
        self.arrival = arrival
        self.run = run
        self.handle = None
        self.ticket: Ticket | None = None
        self.held = False

    def reserve(self) -> None:
        """Take this request's place in the lease's queue, without taking the lease."""
        if self.ticket is None:
            self.ticket = Ticket(self.path, self.mode, self.owner, self.arrival, self.run)

    def attempt(self) -> OwnerLease:
        """Take the lease if this request's turn has come and no holder conflicts."""
        self.reserve()
        ahead = [peek_owner(path) or {} for path in self.ticket.ahead(self.mode)]
        handle = _take(self.path, self.mode)
        if handle is None:
            # Earlier tickets name live holders of either mode; the record
            # names only the last exclusive holder, or one without a ticket.
            current = ahead[0] if ahead else peek_owner(self.path) or {}
            raise LeaseHeldError(
                f"source identity is owned by {current.get('root', 'unknown')} at "
                f"{current.get('revision', 'unknown')}; retry after it releases",
                current,
            )
        if ahead:
            _release(handle, locked=True)
            raise LeaseHeldError(
                f"source identity is queued behind {ahead[0].get('root', 'unknown')} at "
                f"{ahead[0].get('revision', 'unknown')}; retry after it releases",
                ahead[0],
            )
        token = uuid.uuid4().hex
        try:
            if self.mode == EXCLUSIVE:
                _write_record(
                    handle,
                    {
                        **self.owner,
                        "token": token,
                        "expires_ns": time.time_ns() + self.seconds * 1_000_000_000,
                    },
                )
        except OSError as error:
            _release(handle, locked=True)
            raise BuildIdentityError(f"cannot write source identity lease {self.path}: {error}") from error
        self.handle = handle
        self.owner = {**self.owner, "token": token}
        self.held = True
        return self

    def downgrade(self) -> None:
        """Hold this lease shared from now on, without leaving its place in the queue.

        Later exclusive requests keep waiting and later shared ones may now
        enter. The owner record, written only by exclusive holders, still
        names this holder until another exclusive holder replaces it.
        """
        if not self.held or self.mode == SHARED:
            return
        if self.ticket is not None:
            # The ticket is what makes a POSIX racer back off, so it must
            # exist while the lock is converted.
            self.ticket.refile()
        try:
            _downgrade(self.handle)
        except BuildIdentityError:
            # A failed POSIX conversion has already unlocked the handle, and
            # a second `flock` unlock is a no-op; a failed Windows one still
            # holds the exclusive lock, which closing the handle frees only
            # at some later time, so it is unlocked here.
            handle, self.handle, self.held = self.handle, None, False
            _release(handle, locked=True)
            raise
        self.mode = SHARED
        if self.ticket is not None:
            self.ticket.downgrade()

    def unhold(self) -> None:
        """Give the lock back and keep this request's place in the queue."""
        if self.held and self.handle is not None:
            handle, self.handle, self.held = self.handle, None, False
            try:
                _release(handle, locked=True)
            except OSError as error:
                raise BuildIdentityError(
                    f"cannot release source identity lease {self.path}"
                ) from error

    def dequeue(self) -> None:
        if self.ticket is not None:
            ticket, self.ticket = self.ticket, None
            ticket.close()

    def __enter__(self) -> OwnerLease:
        try:
            return self.attempt()
        except BaseException:
            self.dequeue()
            raise

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            self.unhold()
        finally:
            self.held = False
            self.handle = None
            self.dequeue()


class LeaseProbe:
    """A shared look at a lease: a check only reads the artifacts."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def __enter__(self) -> bool:
        handle = _take(self.path, SHARED)
        if handle is None:
            return False
        self.handle = handle
        return True

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.handle is None:
            return
        try:
            _release(self.handle, locked=True)
        except OSError as error:
            raise BuildIdentityError(f"cannot release source identity lease {self.path}") from error
        finally:
            self.handle = None


def lease_is_held(path: Path) -> bool:
    if not path.exists():
        return False
    handle = _open_lease(path)
    try:
        if _try_lock(handle):
            _unlock(handle)
            return False
        return True
    finally:
        handle.close()


def peek_owner(path: Path) -> dict[str, object] | None:
    """Read a lease's owner record without taking its lock.

    Diagnostic only: `None` when the record is absent, partial, or malformed.
    A holder that predates `RECORD_OFFSET` wrote its record at byte 0, so the
    byte past the lock is its `{`.
    """
    try:
        with path.open("rb") as handle:
            handle.seek(RECORD_OFFSET)
            raw = handle.read()
    except OSError:
        return None
    for candidate in (raw, b"{" + raw):
        try:
            value = json.loads(candidate)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _pause(seconds: float) -> None:
    time.sleep(seconds)


def _held(path: Path, mode: str) -> bool:
    """Whether a holder conflicts with a `mode` request for the lease at `path` right now."""
    handle = _take(path, mode)
    if handle is None:
        return True
    _release(handle, locked=True)
    return False


def _blocker(lease: OwnerLease) -> LeaseHeldError | None:
    """What stops `lease`'s request from being taken now, or None.

    A request waits for every conflicting request that arrived before it,
    whether that one holds the lease or only waits for it. A request that
    arrived after it conflicts only as a holder, which the lock decides.
    """
    ticket = lease.ticket
    before, after = conflicting(lease.path, lease.mode, ticket.place, ticket.path)
    if before:
        peer = peek_owner(before[0]) or {}
        return LeaseHeldError(
            f"source identity is queued behind {peer.get('root', 'unknown')} at "
            f"{peer.get('revision', 'unknown')}; retry after it releases",
            peer,
        )
    if after and _held(lease.path, lease.mode):
        peer = peek_owner(lease.path) or peek_owner(after[0]) or {}
        return LeaseHeldError(
            f"source identity is owned by {peer.get('root', 'unknown')} at "
            f"{peer.get('revision', 'unknown')}; retry after it releases",
            peer,
        )
    return None


def _release_all(leases: Sequence[OwnerLease]) -> None:
    for lease in reversed(leases):
        lease.__exit__(None, None, None)


def _try_claim(leases: Sequence[OwnerLease]) -> tuple[OwnerLease, LeaseHeldError] | None:
    """Take every lease or none; the first obstacle, or None when all are taken.

    The request keeps its ticket at every lease of the claim from the first
    look until the claim is released or refused, held or not, so a later
    request cannot overtake it at any of them. It takes the locks only when no
    earlier request conflicts at any lease and no holder does, and gives the
    locks back, not the places, when a peer takes one between the look and the
    take.
    """
    for lease in leases:
        lease.reserve()
    blocked = []
    for lease in leases:
        found = _blocker(lease)
        if found is not None:
            blocked.append((lease, found))
    if blocked:
        return blocked[0]
    taken: list[OwnerLease] = []
    try:
        for lease in leases:
            lease.attempt()
            taken.append(lease)
    except LeaseHeldError as error:
        for held in reversed(taken):
            held.unhold()
        return lease, error
    except BaseException:
        _release_all(taken)
        raise
    return None


def acquire_claim(
    leases: Sequence[OwnerLease],
    wait_seconds: float,
    deadline_ns: int | None = None,
    arrival_ns: int | None = None,
    run_id: str | None = None,
) -> ExitStack:
    """Take every lease at once, waiting while a live owner holds one or an earlier request is queued.

    The leases are taken together or not at all, and a request that cannot
    take them holds no lock while it waits: it keeps only its place, a ticket,
    at every lease it needs, so no later request overtakes it at any of them
    and the earliest request can always proceed. A run therefore waits for the
    requests that arrived before it and conflict, and for nothing a peer holds
    only while it waits for something else. Every lease of the claim is queued
    under one `arrival_ns` (the call's own time when omitted) and one `run_id`
    (a fresh one when omitted), so the places, `(arrival, run)`, are ordered
    the same in every queue and never tie, and a request that releases and
    asks again with a later arrival queues behind the ones already waiting. The wait
    ends when the leases are taken or at `deadline_ns` (`wait_seconds` from now
    when omitted); the latter raises without taking any. The OS lock proves the
    owner is alive, so its recorded `expires_ns` only reports.
    """
    leases = tuple(leases)
    arrival = time.monotonic_ns() if arrival_ns is None else arrival_ns
    if deadline_ns is None:
        deadline_ns = time.monotonic_ns() + int(wait_seconds * 1_000_000_000)
    run = uuid.uuid4().hex if run_id is None else run_id
    for lease in leases:
        lease.arrival = arrival
        lease.run = run
    delay = _WAIT_FIRST_SECONDS
    announced = None
    try:
        while True:
            refusal = _try_claim(leases)
            if refusal is None:
                stack = ExitStack()
                for lease in leases:
                    stack.push(lease)
                return stack
            blocked, error = refusal
            if wait_seconds <= 0:
                raise error
            owner = error.holder.get("root", "unknown")
            revision = error.holder.get("revision", "unknown")
            remaining_ns = deadline_ns - time.monotonic_ns()
            if remaining_ns <= 0:
                raise BuildIdentityError(
                    f"source identity lease {blocked.path.name} is still held by {owner} at "
                    f"{revision} after waiting {wait_seconds:g} s (--lease-wait-seconds); "
                    "no artifact was touched"
                )
            if announced != (blocked.path, owner, revision):
                print(
                    f"atlas-build-identity waiting: lease {blocked.path.name} held by {owner} at "
                    f"{revision}; waiting up to {remaining_ns / 1e9:.0f} s",
                    file=sys.stderr,
                    flush=True,
                )
                announced = (blocked.path, owner, revision)
            _pause(min(delay, remaining_ns / 1e9))
            delay = min(delay * 2, _WAIT_MAX_SECONDS)
    except BaseException:
        for lease in leases:
            lease.dequeue()
        raise
