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
    """A live process holds the lease."""


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


def _try_lock(handle: Any) -> bool:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True
    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
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


class OwnerLease:
    def __init__(self, path: Path, owner: dict[str, object], seconds: int) -> None:
        if seconds <= 0:
            raise BuildIdentityError("lease duration must be positive")
        self.path = path
        self.owner = owner
        self.seconds = seconds
        self.handle = None
        self.held = False

    def __enter__(self) -> OwnerLease:
        handle = _open_lease(self.path)
        if not _try_lock(handle):
            handle.close()
            current = peek_owner(self.path) or {}
            owner = current.get("root", "unknown")
            revision = current.get("revision", "unknown")
            raise LeaseHeldError(
                f"source identity is owned by {owner} at {revision}; retry after it releases"
            )
        token = uuid.uuid4().hex
        payload = {
            **self.owner,
            "token": token,
            "expires_ns": time.time_ns() + self.seconds * 1_000_000_000,
        }
        try:
            handle.seek(0)
            handle.truncate()
            handle.write(b" " * RECORD_OFFSET)
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
            handle.flush()
            os.fsync(handle.fileno())
        except OSError as error:
            _unlock(handle)
            handle.close()
            raise BuildIdentityError(f"cannot write source identity lease {self.path}: {error}") from error
        self.handle = handle
        self.owner = {**self.owner, "token": token}
        self.held = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self.held or self.handle is None:
            return
        try:
            _unlock(self.handle)
            self.handle.close()
        except OSError as error:
            raise BuildIdentityError(f"cannot release source identity lease {self.path}") from error
        finally:
            self.held = False
            self.handle = None


class LeaseProbe:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def __enter__(self) -> bool:
        handle = _open_lease(self.path)
        if not _try_lock(handle):
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
    """Enter `lease`, waiting while a live owner holds it.

    The wait ends when the owner releases, when the owner's recorded
    `expires_ns` passes while it still holds the lock, or after `wait_seconds`,
    whichever is first; the last two raise without taking the lease. Callers
    acquire several leases in sorted scope order, so waiting holders never
    form a cycle.
    """
    deadline_ns = time.monotonic_ns() + int(wait_seconds * 1_000_000_000)
    delay = _WAIT_FIRST_SECONDS
    announced = None
    while True:
        try:
            return lease.__enter__()
        except LeaseHeldError:
            if wait_seconds <= 0:
                raise
            current = peek_owner(lease.path) or {}
        owner = current.get("root", "unknown")
        revision = current.get("revision", "unknown")
        remaining_ns = deadline_ns - time.monotonic_ns()
        expires_ns = current.get("expires_ns")
        if type(expires_ns) is int:
            remaining_ns = min(remaining_ns, expires_ns - time.time_ns())
        if remaining_ns <= 0:
            raise BuildIdentityError(
                f"source identity lease {lease.path.name} is still held by {owner} at "
                f"{revision} after waiting up to its expiry; no artifact was touched"
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
