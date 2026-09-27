"""Crash-recoverable ownership leases for shared build scopes."""

from __future__ import annotations

import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from atlas_build_lock import (
    BuildIdentityError,
    EXCLUSIVE,
    SHARED,
    RECORD_OFFSET,
    _MODES,
    _open_lease,
    _release,
    _take,
    _try_lock,
    _unlock,
    _write_record,
)
from atlas_build_queue import Ticket


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
        self, path: Path, owner: dict[str, object], seconds: int, mode: str = EXCLUSIVE
    ) -> None:
        if seconds <= 0:
            raise BuildIdentityError("lease duration must be positive")
        if mode not in _MODES:
            raise BuildIdentityError(f"unknown lease mode {mode}")
        self.path = path
        self.owner = owner
        self.seconds = seconds
        self.mode = mode
        self.handle = None
        self.ticket: Ticket | None = None
        self.held = False

    def attempt(self) -> OwnerLease:
        """Take the lease if this request's turn has come and no holder conflicts."""
        if self.ticket is None:
            self.ticket = Ticket(self.path, self.mode, self.owner)
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
            if self.held and self.handle is not None:
                try:
                    _unlock(self.handle)
                    self.handle.close()
                except OSError as error:
                    raise BuildIdentityError(
                        f"cannot release source identity lease {self.path}"
                    ) from error
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
            _unlock(self.handle)
            self.handle.close()
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


def acquire_waiting(lease: OwnerLease, wait_seconds: float) -> OwnerLease:
    """Enter `lease`, waiting while a live owner holds it or an earlier request is queued.

    The request keeps one ticket for the whole wait, so a holder that releases
    and asks again queues behind it. The wait ends when the lease is taken or
    after `wait_seconds`; the latter raises without taking the lease. The OS
    lock proves the owner is alive, so its recorded `expires_ns` only reports.
    Callers acquire several leases in sorted scope order: a request waits only
    on holders of its own lease, which wait only on later leases, or on
    earlier requests for the same lease, so no wait forms a cycle.
    """
    try:
        return _wait_for(lease, wait_seconds)
    except BaseException:
        lease.dequeue()
        raise


def _wait_for(lease: OwnerLease, wait_seconds: float) -> OwnerLease:
    deadline_ns = time.monotonic_ns() + int(wait_seconds * 1_000_000_000)
    delay = _WAIT_FIRST_SECONDS
    announced = None
    while True:
        try:
            return lease.attempt()
        except LeaseHeldError as error:
            if wait_seconds <= 0:
                raise
            current = error.holder
        owner = current.get("root", "unknown")
        revision = current.get("revision", "unknown")
        remaining_ns = deadline_ns - time.monotonic_ns()
        if remaining_ns <= 0:
            raise BuildIdentityError(
                f"source identity lease {lease.path.name} is still held by {owner} at "
                f"{revision} after waiting {wait_seconds:g} s (--lease-wait-seconds); "
                "no artifact was touched"
            )
        if announced != (owner, revision):
            print(
                f"atlas-build-identity waiting: lease {lease.path.name} held by {owner} at "
                f"{revision}; waiting up to {remaining_ns / 1e9:.0f} s",
                file=sys.stderr,
                flush=True,
            )
            announced = (owner, revision)
        time.sleep(min(delay, remaining_ns / 1e9))
        delay = min(delay * 2, _WAIT_MAX_SECONDS)
