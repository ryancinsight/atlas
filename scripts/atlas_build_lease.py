"""Crash-recoverable ownership leases for shared build scopes."""

from __future__ import annotations

import errno
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
EXCLUSIVE = "exclusive"
SHARED = "shared"
_MODES = (EXCLUSIVE, SHARED)
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
    # The one failure that means another handle holds a conflicting lock.
    _ERROR_LOCK_VIOLATION = 33


def _try_lock(handle: Any, mode: str = EXCLUSIVE) -> bool:
    """Lock byte 0 of `handle` in `mode` without blocking.

    Returns False only when another holder conflicts; any other failure is
    raised. Windows uses `LockFileEx`, which has a shared mode and whose
    byte-range locks conflict with the `msvcrt.locking` exclusive locks of
    earlier holders. POSIX uses `flock`, the call earlier holders used;
    `fcntl` record locks would not see theirs.
    """
    if mode not in _MODES:
        raise BuildIdentityError(f"unknown lease mode {mode}")
    if os.name == "nt":
        flags = _LOCKFILE_FAIL_IMMEDIATELY
        if mode == EXCLUSIVE:
            flags |= _LOCKFILE_EXCLUSIVE_LOCK
        overlapped = _Overlapped()
        if _KERNEL32.LockFileEx(
            msvcrt.get_osfhandle(handle.fileno()), flags, 0, 1, 0, ctypes.byref(overlapped)
        ):
            return True
        code = ctypes.get_last_error()
        if code == _ERROR_LOCK_VIOLATION:
            return False
        raise ctypes.WinError(code)
    import fcntl

    operation = fcntl.LOCK_EX if mode == EXCLUSIVE else fcntl.LOCK_SH
    try:
        fcntl.flock(handle.fileno(), operation | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
            return False
        raise
    return True


def _unlock(handle: Any) -> None:
    if os.name == "nt":
        overlapped = _Overlapped()
        if not _KERNEL32.UnlockFileEx(
            msvcrt.get_osfhandle(handle.fileno()), 0, 1, 0, ctypes.byref(overlapped)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _open_lease(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o644)
    try:
        if os.fstat(descriptor).st_size == 0:
            # A lock is never held on an empty file: an earlier checker that
            # finds one empty writes byte 0 and crashes on the lock. The byte
            # is written before any lock is taken, so the write is refused
            # only when a holder wrote its own byte and locked it meanwhile.
            try:
                os.write(descriptor, b"\0")
            except PermissionError:
                pass
        return os.fdopen(descriptor, "r+b")
    except BaseException:
        os.close(descriptor)
        raise


def _release(handle: Any, locked: bool) -> None:
    try:
        if locked:
            _unlock(handle)
    finally:
        handle.close()


def _take(path: Path, mode: str):
    """Open `path` locked in `mode`, or None when a holder conflicts; never leaks."""
    handle = _open_lease(path)
    try:
        if _try_lock(handle, mode):
            return handle
    except BaseException:
        handle.close()
        raise
    handle.close()
    return None


def _write_record(handle: Any, record: dict[str, object]) -> None:
    # Overwrite, then cut the tail: truncating first left an empty file that
    # a concurrent opener read as never initialized.
    handle.seek(0)
    handle.write(b" " * RECORD_OFFSET)
    handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
    handle.truncate()
    handle.flush()
    os.fsync(handle.fileno())


_TICKET_MODES = {EXCLUSIVE: "x", SHARED: "s"}
_TICKET_ATTEMPTS = 100
_UNLINK_ATTEMPTS = 20
_RETRY_SECONDS = 0.005


def _queue_dir(path: Path) -> Path:
    return path.with_name(f"{path.stem}.queue")


def _unlink(path: Path, attempts: int = 1) -> None:
    # Windows refuses while a peer's liveness check has the file open; that
    # check closes within milliseconds, and an unlocked ticket left behind is
    # collected by the next scan.
    for attempt in range(attempts):
        try:
            path.unlink()
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt + 1 < attempts:
                time.sleep(_RETRY_SECONDS)


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


class _Ticket:
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

    def ahead(self, mode: str) -> list[dict[str, object]]:
        """Live earlier requests this one may not pass, collecting dead tickets.

        An exclusive request waits for every earlier request, a shared one for
        earlier exclusive requests only: readers that arrived together share,
        and a waiting writer holds back every later reader.
        """
        if not _names(self.path, self.handle):
            _release(self.handle, locked=True)
            self._create()
        blockers = []
        for other in sorted(self.directory.glob("*.ticket")):
            if other == self.path or not _ticket_is_live(other):
                continue
            if other.name < self.path.name and (
                mode == EXCLUSIVE or f"-{_TICKET_MODES[EXCLUSIVE]}-" in other.name
            ):
                blockers.append(peek_owner(other) or {})
        return blockers

    def close(self) -> None:
        try:
            _release(self.handle, locked=True)
        finally:
            _unlink(self.path, _UNLINK_ATTEMPTS)


def _names(path: Path, handle: Any) -> bool:
    """Whether `path` still names the file `handle` has open."""
    try:
        return os.path.samestat(os.fstat(handle.fileno()), os.stat(path))
    except FileNotFoundError:
        return False


class OwnerLease:
    """A lease on one build scope, held shared (reading) or exclusive (writing).

    Requests are served in arrival order through `_Ticket`; the OS lock on
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
        self.ticket: _Ticket | None = None
        self.held = False

    def attempt(self) -> OwnerLease:
        """Take the lease if this request's turn has come and no holder conflicts."""
        if self.ticket is None:
            self.ticket = _Ticket(self.path, self.mode, self.owner)
        ahead = self.ticket.ahead(self.mode)
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
