"""Open shared target files beneath a held directory handle."""

from __future__ import annotations

import os
import stat
import uuid
from pathlib import Path, PurePath
from typing import BinaryIO

from atlas_build_lease import BuildIdentityError
from atlas_build_target_paths import _components
from atlas_build_target_windows import WindowsTargetDirectory


class TargetDirectory:
    """A target directory whose child opens remain anchored to its handle."""

    def __init__(self, path: Path, *, create: bool = False) -> None:
        self.path = Path(path)
        self._fd: int | None = None
        self._windows: WindowsTargetDirectory | None = None
        if os.name == "nt":
            self._windows = WindowsTargetDirectory(path, create=create)
            self.path = self._windows.path
        else:
            self._open_posix(create)

    def __enter__(self) -> TargetDirectory:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self._windows is not None:
            self._windows.close()
            self._windows = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    @property
    def command_path(self) -> str:
        """Return a subprocess path resolved through the held directory handle."""
        if self._windows is not None:
            return str(self.path)
        if self._fd is None:
            raise BuildIdentityError("target directory handle is closed")
        for descriptor_root in (Path("/proc/self/fd"), Path("/dev/fd")):
            descriptor_path = descriptor_root / str(self._fd)
            if descriptor_path.is_dir():
                return str(descriptor_path)
        raise BuildIdentityError(
            "the host does not expose directory handles to subprocess paths"
        )

    @property
    def command_fds(self) -> tuple[int, ...]:
        """Return descriptors that subprocesses must inherit for ``command_path``."""
        if self._windows is not None:
            return ()
        if self._fd is None:
            raise BuildIdentityError("target directory handle is closed")
        return (self._fd,)

    def open_file(self, path: Path) -> BinaryIO:
        stream = self._open_file(path, missing_ok=False)
        if stream is None:
            raise BuildIdentityError(f"target file does not exist: {path}")
        return stream

    def open_lock_file(self, path: Path, *, create: bool = True) -> BinaryIO | None:
        if self._windows is not None:
            return self._windows.open_lock_file(path, create=create)
        components = _components(self.relative_path(path))
        return self._open_posix_lock_file(components, create=create)

    def read_file(self, path: Path) -> bytes | None:
        stream = self._open_file(path, missing_ok=True)
        if stream is None:
            return None
        with stream:
            return stream.read()

    def _open_file(self, path: Path, *, missing_ok: bool) -> BinaryIO | None:
        if self._windows is not None:
            return self._windows.open_file(path, missing_ok=missing_ok)
        components = _components(self.relative_path(path))
        return self._open_posix_file(components, missing_ok=missing_ok)

    def atomic_write(self, path: Path, content: bytes) -> None:
        if self._windows is not None:
            self._windows.atomic_write(path, content)
            return
        components = _components(self.relative_path(path))
        self._atomic_write_posix(components, content)

    def validate_path(self, path: Path) -> None:
        if self._windows is not None:
            self._windows.validate_path(path)
            return
        components = _components(self.relative_path(path))
        self._validate_posix_path(components, path)

    def relative_path(self, path: Path) -> Path:
        candidate = Path(path)
        if ".." in candidate.parts:
            raise BuildIdentityError(f"artifact path contains parent traversal: {path}")
        if self._windows is not None:
            return self._windows.relative_path(candidate)
        if candidate.is_absolute():
            try:
                return candidate.relative_to(self.path)
            except ValueError:
                try:
                    return candidate.relative_to(Path(self.command_path))
                except ValueError as error:
                    raise BuildIdentityError(
                        f"artifact is outside the shared target: {path}"
                    ) from error
        return candidate


    def _open_posix(self, create: bool) -> None:
        raw = os.fspath(self.path)
        if ".." in PurePath(raw).parts:
            raise BuildIdentityError(f"target directory contains a parent traversal: {raw}")
        absolute = Path(os.path.abspath(raw))
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0)
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        if not nofollow:
            raise BuildIdentityError("the host does not support no-follow directory opens")
        try:
            current = os.open(absolute.anchor, flags | nofollow)
            for component in absolute.parts[1:]:
                if create:
                    try:
                        os.mkdir(component, dir_fd=current)
                    except FileExistsError:
                        pass
                child = os.open(component, flags | nofollow, dir_fd=current)
                os.close(current)
                current = child
            if not stat.S_ISDIR(os.fstat(current).st_mode):
                raise BuildIdentityError(f"target is not a directory: {absolute}")
        except BaseException as error:
            if "current" in locals():
                os.close(current)
            if isinstance(error, OSError):
                raise BuildIdentityError(
                    f"cannot open target directory {absolute}: {error}"
                ) from error
            raise
        self._fd = current
        self.path = absolute

    def _open_posix_file(
        self, components: tuple[str, ...], *, missing_ok: bool
    ) -> BinaryIO | None:
        if self._fd is None:
            raise BuildIdentityError("target directory handle is closed")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        current = os.dup(self._fd)
        try:
            for index, component in enumerate(components):
                try:
                    child = os.open(component, flags, dir_fd=current)
                except FileNotFoundError:
                    if missing_ok:
                        return None
                    raise
                try:
                    metadata = os.fstat(child)
                    final = index == len(components) - 1
                    if final and not stat.S_ISREG(metadata.st_mode):
                        raise BuildIdentityError(
                            f"artifact is not a regular file: {component}"
                        )
                    if not final and not stat.S_ISDIR(metadata.st_mode):
                        raise BuildIdentityError(
                            f"artifact parent is not a directory: {component}"
                        )
                except BaseException:
                    os.close(child)
                    raise
                os.close(current)
                current = child
            stream = os.fdopen(current, "rb")
            current = -1
            return stream
        except OSError as error:
            raise BuildIdentityError(
                f"cannot open artifact beneath {self.path}: {error}"
            ) from error
        finally:
            if current >= 0:
                os.close(current)

    def _open_posix_lock_file(
        self, components: tuple[str, ...], *, create: bool
    ) -> BinaryIO | None:
        if self._fd is None:
            raise BuildIdentityError("target directory handle is closed")
        current = os.dup(self._fd)
        descriptor = -1
        try:
            for component in components[:-1]:
                if create:
                    try:
                        os.mkdir(component, dir_fd=current)
                    except FileExistsError:
                        pass
                try:
                    child = os.open(
                        component,
                        os.O_RDONLY
                        | getattr(os, "O_CLOEXEC", 0)
                        | getattr(os, "O_DIRECTORY", 0)
                        | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=current,
                    )
                except FileNotFoundError:
                    if not create:
                        return None
                    raise
                if not stat.S_ISDIR(os.fstat(child).st_mode):
                    os.close(child)
                    raise BuildIdentityError(f"lock parent is not a directory: {component}")
                os.close(current)
                current = child
            flags = (
                os.O_RDWR
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0)
            )
            if create:
                flags |= os.O_CREAT
            try:
                descriptor = os.open(components[-1], flags, 0o600, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    return None
                raise
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise BuildIdentityError(f"lease path is not a regular file: {components[-1]}")
            stream = os.fdopen(descriptor, "r+b")
            descriptor = -1
            return stream
        except OSError as error:
            raise BuildIdentityError(f"cannot open lease beneath {self.path}: {error}") from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(current)

    def _validate_posix_path(self, components: tuple[str, ...], path: Path) -> None:
        if self._fd is None:
            raise BuildIdentityError("target directory handle is closed")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        current = os.dup(self._fd)
        try:
            for index, component in enumerate(components):
                final = index == len(components) - 1
                component_flags = flags
                if not final:
                    component_flags |= getattr(os, "O_DIRECTORY", 0)
                try:
                    child = os.open(component, component_flags, dir_fd=current)
                except FileNotFoundError:
                    return
                try:
                    metadata = os.fstat(child)
                    is_expected_type = (
                        stat.S_ISREG(metadata.st_mode)
                        if final
                        else stat.S_ISDIR(metadata.st_mode)
                    )
                    if not is_expected_type:
                        raise BuildIdentityError(
                            f"invalid target path component: {path}"
                        )
                except BaseException:
                    os.close(child)
                    raise
                os.close(current)
                current = child
        except OSError as error:
            raise BuildIdentityError(f"cannot validate target path {path}: {error}") from error
        finally:
            os.close(current)

    def _atomic_write_posix(
        self, components: tuple[str, ...], content: bytes
    ) -> None:
        if self._fd is None:
            raise BuildIdentityError("target directory handle is closed")
        parent = os.dup(self._fd)
        temporary = f".{components[-1]}.{uuid.uuid4().hex}.tmp"
        descriptor = -1
        try:
            for component in components[:-1]:
                try:
                    os.mkdir(component, dir_fd=parent)
                except FileExistsError:
                    pass
                child = os.open(
                    component,
                    os.O_RDONLY
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent,
                )
                if not stat.S_ISDIR(os.fstat(child).st_mode):
                    os.close(child)
                    raise BuildIdentityError(
                        f"record parent is not a directory: {component}"
                    )
                os.close(parent)
                parent = child
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent,
            )
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary,
                components[-1],
                src_dir_fd=parent,
                dst_dir_fd=parent,
            )
            os.fsync(parent)
        except OSError as error:
            raise BuildIdentityError(
                f"cannot write target file {Path(*components)}: {error}"
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            finally:
                os.close(parent)
