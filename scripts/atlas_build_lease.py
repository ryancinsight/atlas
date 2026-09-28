"""Crash-recoverable ownership leases for shared build scopes."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas_build_target import TargetDirectory


class BuildIdentityError(RuntimeError):
    """A source identity cannot be established or safely used."""


def _windows_directory_path(path: Path) -> Path:
    from atlas_build_target_windows_api import _windows_directory_path as resolve

    return resolve(path)


def _canonical_target_dir(target_dir: Path) -> Path:
    try:
        resolved = Path(target_dir).resolve(strict=False)
        if os.name == "nt":
            return _windows_directory_path(resolved)
        return resolved
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve target directory {target_dir}: {error}") from error


def package_target_lease_path(package: str, target_dir: Path) -> Path:
    canonical_target = _canonical_target_dir(target_dir)
    target_key = canonical_target.as_posix()
    if os.name == "nt":
        target_key = target_key.casefold()
    scope = {"package": package, "target_dir": target_key}
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    key = hashlib.sha256(encoded).hexdigest()
    return canonical_target / ".atlas" / "source-identity" / f"{key}.lock"


def package_target_lease_scopes(
    package: str,
    target_dir: Path,
    root: str,
    revision: str,
    clean_packages: list[str] | tuple[str, ...] | set[str],
) -> list[tuple[Path, dict[str, object]]]:
    target_dir = _canonical_target_dir(target_dir)
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


def _open_lease(target: TargetDirectory, path: Path):
    handle = target.open_lock_file(path)
    if handle is None:
        raise BuildIdentityError(f"cannot create source identity lease {path}")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0L")
        handle.flush()
    handle.seek(0)
    return handle


def _read_owner(handle: Any, path: Path) -> dict[str, object] | None:
    try:
        handle.seek(1)
        prefixed = handle.read()
        if prefixed == b"L":
            return None
        if prefixed.startswith(b"L"):
            return _validated_owner(prefixed[1:], path)
        if prefixed in (b"", b"\0"):
            handle.seek(0)
            legacy = handle.read()
            if legacy in (b"", b"\0"):
                return None
            raw = legacy
        else:
            handle.seek(0)
            raw = handle.read()
    except OSError as error:
        raise BuildIdentityError(f"cannot read source identity lease {path}: {error}") from error
    if raw in (b"", b"\0"):
        return None

    return _validated_owner(raw, path)


def _validated_owner(raw: bytes, path: Path) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BuildIdentityError(f"malformed source identity lease {path}") from error
    if not isinstance(value, dict):
        raise BuildIdentityError(f"malformed source identity lease {path}")
    required = {
        "root": str,
        "revision": str,
        "package": str,
        "target_dir": str,
        "token": str,
        "expires_ns": int,
    }
    for key, expected in required.items():
        if type(value.get(key)) is not expected:
            raise BuildIdentityError(f"malformed source identity lease {path}")
    return value


class OwnerLease:
    def __init__(
        self, target: TargetDirectory, path: Path, owner: dict[str, object], seconds: int
    ) -> None:
        if seconds <= 0:
            raise BuildIdentityError("lease duration must be positive")
        self.target = target
        self.path = path
        self.owner = owner
        self.seconds = seconds
        self.handle = None
        self.held = False

    def __enter__(self) -> OwnerLease:
        handle = _open_lease(self.target, self.path)
        if not _try_lock(handle):
            try:
                current = _read_owner(handle, self.path)
                owner = current.get("root", "unknown") if current else "unknown"
                revision = current.get("revision", "unknown") if current else "unknown"
            except BuildIdentityError:
                owner = revision = "unknown"
            handle.close()
            raise BuildIdentityError(
                f"source identity is owned by {owner} at {revision}; retry after it releases"
            )
        try:
            current = _read_owner(handle, self.path)
        except BuildIdentityError:
            _unlock(handle)
            handle.close()
            raise
        if current is not None and current["expires_ns"] > time.time_ns():
            owner = current["root"]
            revision = current["revision"]
            _unlock(handle)
            handle.close()
            raise BuildIdentityError(
                f"source identity is owned by {owner} at {revision} until its lease expires"
            )
        token = uuid.uuid4().hex
        payload = {
            **self.owner,
            "token": token,
            "expires_ns": time.time_ns() + self.seconds * 1_000_000_000,
        }
        try:
            handle.seek(0)
            handle.write(b"\0L")
            handle.seek(2)
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
        failure: OSError | None = None
        try:
            self.handle.seek(0)
            self.handle.write(b"\0L")
            self.handle.seek(2)
            self.handle.truncate()
            self.handle.flush()
            os.fsync(self.handle.fileno())
        except OSError as error:
            failure = error
        try:
            _unlock(self.handle)
        except OSError as error:
            failure = failure or error
        finally:
            try:
                self.handle.close()
            except OSError as error:
                failure = failure or error
            self.held = False
            self.handle = None
        if failure is not None:
            raise BuildIdentityError(
                f"cannot release source identity lease {self.path}"
            ) from failure


class LeaseProbe:
    def __init__(self, target: TargetDirectory, path: Path) -> None:
        self.target = target
        self.path = path
        self.handle = None

    def __enter__(self) -> bool:
        handle = _open_lease(self.target, self.path)
        if not _try_lock(handle):
            handle.close()
            return False
        try:
            current = _read_owner(handle, self.path)
        except BuildIdentityError:
            _unlock(handle)
            handle.close()
            raise
        if current is not None and current["expires_ns"] > time.time_ns():
            _unlock(handle)
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
    from atlas_build_target import TargetDirectory

    if len(path.parents) < 3:
        raise BuildIdentityError(f"invalid source identity lease path: {path}")
    with TargetDirectory(path.parents[2]) as target:
        handle = target.open_lock_file(path, create=False)
        if handle is None:
            return False
        try:
            if _try_lock(handle):
                _unlock(handle)
                _read_owner(handle, path)
                return False
            return True
        finally:
            handle.close()
