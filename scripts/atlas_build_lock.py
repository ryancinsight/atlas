"""OS byte-range locks and the record they guard, for shared build scopes."""

from __future__ import annotations

import errno
import json
import os
from pathlib import Path
from typing import Any


class BuildIdentityError(RuntimeError):
    """A source identity cannot be established or safely used."""


# The OS lock covers byte 0 only, and the owner record starts at byte 1: a
# Windows byte-range lock refuses reads of the locked range from every other
# handle, so a record at byte 0 made every live owner read as unknown. Keeping
# the lock on byte 0 keeps exclusion with holders that predate the offset.
RECORD_OFFSET = 1
EXCLUSIVE = "exclusive"
SHARED = "shared"
_MODES = (EXCLUSIVE, SHARED)


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


def _downgrade(handle: Any) -> None:
    """Hold `handle`'s exclusive lock on byte 0 as shared from now on.

    Windows adds a shared lock over the exclusive one and unlocks once:
    `LockFileEx` lets a shared lock overlap an exclusive lock taken through
    the same handle, and the first unlock releases the exclusive one, so the
    byte is never unlocked. `flock` may convert by unlocking and then
    locking, so on POSIX another process can take the lock in between; that
    one attempt failing raises holding nothing, never retries: a retry that
    succeeded later could not tell whether the taker had cleaned the scope
    meanwhile.
    """
    if os.name == "nt":
        if not _try_lock(handle, SHARED):
            raise BuildIdentityError("cannot add a shared lock over the held exclusive lock")
        _unlock(handle)
        return
    if not _try_lock(handle, SHARED):
        raise BuildIdentityError("lost the lease while converting it to shared")


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
