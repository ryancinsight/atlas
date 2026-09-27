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


class LeaseHeldError(BuildIdentityError):
    """A live process holds the lease."""


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

    Only an exclusive holder writes the owner record.
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
        self.held = False

    def __enter__(self) -> OwnerLease:
        handle = _take(self.path, self.mode)
        if handle is None:
            current = peek_owner(self.path) or {}
            owner = current.get("root", "unknown")
            revision = current.get("revision", "unknown")
            raise LeaseHeldError(
                f"source identity is owned by {owner} at {revision}; retry after it releases"
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
    """Enter `lease`, waiting while a live owner holds it.

    The wait ends when the owner releases or after `wait_seconds`; the latter
    raises without taking the lease. The OS lock proves the owner is alive, so
    its recorded `expires_ns` only reports: a build that outlives it is still
    waited out. Callers acquire several leases in sorted scope order, so
    waiting holders never form a cycle.
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
