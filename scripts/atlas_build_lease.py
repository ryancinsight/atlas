"""Crash-recoverable ownership leases for shared build scopes."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


class BuildIdentityError(RuntimeError):
    """A source identity cannot be established or safely used."""


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
            try:
                current = json.loads(self.path.read_text(encoding="utf-8"))
                owner = current.get("root", "unknown") if isinstance(current, dict) else "unknown"
                revision = current.get("revision", "unknown") if isinstance(current, dict) else "unknown"
            except (OSError, json.JSONDecodeError):
                owner = revision = "unknown"
            handle.close()
            raise BuildIdentityError(
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
