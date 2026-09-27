"""Crash-recoverable ownership leases for shared build scopes."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any


class BuildIdentityError(RuntimeError):
    """A source identity cannot be established or safely used."""


class LeaseHeldError(BuildIdentityError):
    """A live process holds the lease, or an earlier request is queued for it."""

    def __init__(self, message: str, holder: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.holder = holder or {}


# The OS lock covers byte 0 only, and the owner record starts at byte 1: a
# Windows byte-range lock refuses reads of the locked range from every other
# handle, so a record at byte 0 made every live owner read as unknown. Keeping
# the lock on byte 0 keeps exclusion with holders that predate the offset.
RECORD_OFFSET = 1
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


EXCLUSIVE = "exclusive"
SHARED = "shared"
_TICKET_MODES = {EXCLUSIVE: "x", SHARED: "s"}
# A dead ticket is removed only once it is this old: younger, it may belong to
# a requester between creating the file and locking it.
_DEAD_TICKET_SECONDS = 10


if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _Overlapped(ctypes.Structure):
        _fields_ = [
            ("Internal", ctypes.c_void_p),
            ("InternalHigh", ctypes.c_void_p),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        ]

    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _KERNEL32.LockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_Overlapped),
    ]
    _KERNEL32.LockFileEx.restype = wintypes.BOOL
    _KERNEL32.UnlockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_Overlapped),
    ]
    _KERNEL32.UnlockFileEx.restype = wintypes.BOOL
    _LOCKFILE_FAIL_IMMEDIATELY = 0x1
    _LOCKFILE_EXCLUSIVE_LOCK = 0x2


def _try_lock(handle: Any, mode: str = EXCLUSIVE) -> bool:
    """Lock byte 0 of `handle` without blocking.

    Windows uses `LockFileEx`, whose byte-range locks interoperate with the
    `msvcrt.locking` exclusive locks earlier holders take. POSIX uses `flock`,
    which earlier holders also use; `fcntl` record locks would not see them.
    """
    if os.name == "nt":
        flags = _LOCKFILE_FAIL_IMMEDIATELY
        if mode == EXCLUSIVE:
            flags |= _LOCKFILE_EXCLUSIVE_LOCK
        overlapped = _Overlapped()
        return bool(
            _KERNEL32.LockFileEx(
                msvcrt.get_osfhandle(handle.fileno()), flags, 0, 1, 0, ctypes.byref(overlapped)
            )
        )
    import fcntl

    operation = fcntl.LOCK_EX if mode == EXCLUSIVE else fcntl.LOCK_SH
    try:
        fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(handle: Any) -> None:
    if os.name == "nt":
        overlapped = _Overlapped()
        if not _KERNEL32.UnlockFileEx(
            msvcrt.get_osfhandle(handle.fileno()), 0, 1, 0, ctypes.byref(overlapped)
        ):
            raise OSError(ctypes.get_last_error(), "UnlockFileEx failed")
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _open_lease(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    return handle


def _write_record(handle: Any, record: dict[str, object]) -> None:
    handle.seek(0)
    handle.truncate()
    handle.write(b" " * RECORD_OFFSET)
    handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    handle.flush()
    os.fsync(handle.fileno())


def _queue_dir(path: Path) -> Path:
    return path.with_name(f"{path.stem}.queue")


class _Ticket:
    """A requester's place in a lease's arrival order.

    The ticket file is named by a system-wide monotonic arrival time and
    locked by its requester until it releases the lease, so an unlocked ticket
    belongs to a process that has gone.
    """

    def __init__(self, path: Path, mode: str, owner: dict[str, object]) -> None:
        directory = _queue_dir(path)
        directory.mkdir(parents=True, exist_ok=True)
        self.arrival = time.monotonic_ns()
        name = f"{self.arrival:020d}-{_TICKET_MODES[mode]}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.path = directory / f"{name}.ticket"
        self.handle = self.path.open("x+b")
        self.handle.write(b"\0")
        self.handle.flush()
        if not _try_lock(self.handle):
            self.handle.close()
            raise BuildIdentityError(f"cannot lock source identity ticket {self.path}")
        _write_record(self.handle, {**owner, "mode": mode})

    def ahead(self, mode: str) -> list[dict[str, object]]:
        """Live earlier requests this one must not pass.

        An exclusive request waits for every earlier request; a shared one
        only for earlier exclusive requests, so readers that arrived together
        share while a waiting writer holds back later readers.
        """
        blockers = []
        for other in sorted(self.path.parent.glob("*.ticket")):
            if other.name >= self.path.name:
                break
            if mode == SHARED and f"-{_TICKET_MODES[EXCLUSIVE]}-" not in other.name:
                continue
            if _ticket_is_live(other, self.arrival):
                blockers.append(peek_owner(other) or {})
        return blockers

    def close(self) -> None:
        try:
            _unlock(self.handle)
        finally:
            self.handle.close()
        try:
            self.path.unlink()
        except OSError:
            # A peer checking liveness has it open; unlocked, it reads as dead.
            pass


def _ticket_is_live(path: Path, now: int) -> bool:
    try:
        handle = path.open("rb")
    except OSError:
        return False
    try:
        if not _try_lock(handle):
            return True
        _unlock(handle)
    finally:
        handle.close()
    arrival = int(path.name.split("-", 1)[0])
    if now - arrival > _DEAD_TICKET_SECONDS * 1_000_000_000:
        try:
            path.unlink()
        except OSError:
            pass
    return False


class OwnerLease:
    """A lease on one build scope, held shared (reading) or exclusive.

    Requests are served in arrival order through `_Ticket`; the OS lock on
    byte 0 of the lease file remains the authority on who holds it.
    """

    def __init__(
        self, path: Path, owner: dict[str, object], seconds: int, mode: str = EXCLUSIVE
    ) -> None:
        if seconds <= 0:
            raise BuildIdentityError("lease duration must be positive")
        if mode not in _TICKET_MODES:
            raise BuildIdentityError(f"unknown lease mode {mode}")
        self.path = path
        self.owner = owner
        self.seconds = seconds
        self.mode = mode
        self.handle = None
        self.ticket: _Ticket | None = None
        self.held = False

    def enqueue(self) -> None:
        if self.ticket is None:
            self.ticket = _Ticket(self.path, self.mode, self.owner)

    def attempt(self) -> OwnerLease:
        """Take the lease if this request's turn has come and no holder conflicts."""
        self.enqueue()
        assert self.ticket is not None
        ahead = self.ticket.ahead(self.mode)
        handle = _open_lease(self.path)
        if not _try_lock(handle, self.mode):
            handle.close()
            # Earlier tickets name live holders of either mode; the lease
            # record names only the last exclusive one, or a legacy holder.
            current = ahead[0] if ahead else peek_owner(self.path) or {}
            raise LeaseHeldError(
                f"source identity is owned by {current.get('root', 'unknown')} at "
                f"{current.get('revision', 'unknown')}; retry after it releases",
                current,
            )
        if ahead:
            _unlock(handle)
            handle.close()
            raise LeaseHeldError(
                f"source identity is queued behind {ahead[0].get('root', 'unknown')} at "
                f"{ahead[0].get('revision', 'unknown')}; retry after it releases",
                ahead[0],
            )
        token = uuid.uuid4().hex
        if self.mode == EXCLUSIVE:
            try:
                _write_record(
                    handle,
                    {
                        **self.owner,
                        "token": token,
                        "expires_ns": time.time_ns() + self.seconds * 1_000_000_000,
                    },
                )
            except OSError as error:
                _unlock(handle)
                handle.close()
                raise BuildIdentityError(
                    f"cannot write source identity lease {self.path}: {error}"
                ) from error
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
    """A shared, unqueued look at whether a lease can be read now."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def __enter__(self) -> bool:
        handle = _open_lease(self.path)
        if not _try_lock(handle, SHARED):
            handle.close()
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
    deadline_ns = time.monotonic_ns() + int(wait_seconds * 1_000_000_000)
    delay = _WAIT_FIRST_SECONDS
    announced = None
    try:
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
    except BaseException:
        lease.dequeue()
        raise
