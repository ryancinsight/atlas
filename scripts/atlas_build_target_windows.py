"""Windows directory-relative access to shared Cargo target files."""

from __future__ import annotations

import ctypes
import ntpath
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from atlas_build_lease import BuildIdentityError
from atlas_build_target_paths import _components
from atlas_build_target_windows_api import (
    ERROR_FILE_NOT_FOUND,
    FILE_ATTRIBUTE_DEVICE,
    FILE_ATTRIBUTE_DIRECTORY,
    FILE_ATTRIBUTE_REPARSE_POINT,
    FILE_CREATE,
    LEASE_FILE_ACCESS,
    FILE_DISPOSITION_INFO,
    FILE_FLAG_BACKUP_SEMANTICS,
    FILE_OPEN_REPARSE_POINT,
    FILE_READ_ATTRIBUTES,
    FILE_SHARE_READ,
    FILE_SHARE_WRITE,
    MOVEFILE_REPLACE_EXISTING,
    MOVEFILE_WRITE_THROUGH,
    OPEN_EXISTING,
    SYNCHRONIZE,
    TARGET_DIRECTORY_ACCESS,
    TEMPORARY_FILE_ACCESS,
    _nt_open_child,
    _windows_absolute,
    _windows_api,
    _windows_error,
    _windows_file_info,
    _windows_final_path,
    _windows_lexical_path,
    _windows_path_from_handle,
)


class WindowsTargetDirectory:
    """A Windows target directory anchored by open directory handles."""

    def __init__(self, path: Path, *, create: bool) -> None:
        self.path = Path(path)
        self._handles: list[int] = []
        self._anchor: str | None = None
        self._target_components: tuple[str, ...] = ()
        self._open_windows(create)

    def close(self) -> None:
        if self._handles:
            close = _windows_api()["CloseHandle"]
            for handle in reversed(self._handles):
                close(ctypes.c_void_p(handle))
            self._handles.clear()

    def relative_path(self, candidate: Path) -> Path:
        if candidate.drive and not candidate.is_absolute():
            raise BuildIdentityError(f"artifact path is drive-relative: {candidate}")
        if candidate.is_absolute():
            return self._windows_relative_path(candidate)
        return candidate

    def open_file(self, path: Path, *, missing_ok: bool) -> BinaryIO | None:
        components = _components(self.relative_path(path))
        return self._open_windows_file(components, missing_ok=missing_ok)

    def open_lock_file(self, path: Path, *, create: bool) -> BinaryIO | None:
        components = _components(self.relative_path(path))
        if not self._handles:
            raise BuildIdentityError("target directory handle is closed")
        opened: list[int] = []
        current = self._handles[-1]
        try:
            for index, component in enumerate(components):
                final = index == len(components) - 1
                try:
                    child = _nt_open_child(
                        current,
                        component,
                        directory=not final,
                        create=create,
                        access=LEASE_FILE_ACCESS if final else None,
                        share_delete=not final,
                    )
                except FileNotFoundError:
                    if not create:
                        return None
                    raise
                transferred = False
                try:
                    info = _windows_file_info(child)
                    if info[0] & FILE_ATTRIBUTE_REPARSE_POINT:
                        raise BuildIdentityError(
                            f"lease path contains a reparse point: {component}"
                        )
                    if final and (
                        info[0] & FILE_ATTRIBUTE_DIRECTORY
                        or info[0] & FILE_ATTRIBUTE_DEVICE
                    ):
                        raise BuildIdentityError(
                            f"lease path is not a regular file: {component}"
                        )
                    if not final and not info[0] & FILE_ATTRIBUTE_DIRECTORY:
                        raise BuildIdentityError(
                            f"lease parent is not a directory: {component}"
                        )
                    if final:
                        descriptor = _windows_api()["open_osfhandle"](
                            child, os.O_RDWR | getattr(os, "O_BINARY", 0)
                        )
                        transferred = True
                        try:
                            return os.fdopen(descriptor, "r+b")
                        except BaseException:
                            os.close(descriptor)
                            raise
                    opened.append(child)
                    current = child
                except BaseException:
                    if not transferred:
                        _windows_api()["CloseHandle"](ctypes.c_void_p(child))
                    raise
        except OSError as error:
            raise BuildIdentityError(f"cannot open lease beneath {self.path}: {error}") from error
        finally:
            close = _windows_api()["CloseHandle"]
            for handle in reversed(opened):
                close(ctypes.c_void_p(handle))
        raise BuildIdentityError("lease path has no file component")

    def validate_path(self, path: Path) -> None:
        components = _components(self.relative_path(path))
        self._validate_windows_path(components, path)

    def atomic_write(self, path: Path, content: bytes) -> None:
        components = _components(self.relative_path(path))
        self._atomic_write_windows(components, content)


    def _open_windows(self, create: bool) -> None:
        absolute = _windows_absolute(self.path)
        drive, tail = ntpath.splitdrive(absolute)
        if not drive or not tail.startswith("\\"):
            raise BuildIdentityError(f"target directory is not absolute: {absolute}")
        anchor = drive + "\\"
        self._anchor = ntpath.normcase(anchor)
        api = _windows_api()
        root = api["CreateFileW"](
            anchor,
            FILE_READ_ATTRIBUTES | SYNCHRONIZE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
        if root in (None, ctypes.c_void_p(-1).value):
            raise _windows_error(f"cannot open target volume root {anchor}")
        current = int(root)
        self._handles.append(current)
        try:
            components = tuple(part for part in tail.split("\\") if part)
            self._target_components = components
            for index, component in enumerate(components):
                access = (
                    TARGET_DIRECTORY_ACCESS
                    if index == len(components) - 1
                    else None
                )
                child = _nt_open_child(
                    current,
                    component,
                    directory=True,
                    create=create,
                    access=access,
                )
                try:
                    self._require_directory(child, component)
                except BaseException:
                    api["CloseHandle"](ctypes.c_void_p(child))
                    raise
                current = child
                self._handles.append(current)
            self.path = _windows_path_from_handle(current)
        except BaseException:
            self.close()
            raise

    def _windows_relative_path(self, candidate: Path) -> Path:
        if self._anchor is None or not self._handles:
            raise BuildIdentityError("target directory handle is closed")
        drive, tail = ntpath.splitdrive(_windows_lexical_path(candidate))
        anchor = ntpath.normcase(drive + "\\")
        components = tuple(part for part in tail.split("\\") if part)
        if anchor != self._anchor or len(components) < len(self._target_components):
            raise BuildIdentityError(f"artifact is outside the shared target: {candidate}")

        opened: list[int] = []
        current = self._handles[0]
        try:
            for index, component in enumerate(components[: len(self._target_components)]):
                child = _nt_open_child(current, component, directory=True, create=False)
                try:
                    self._require_directory(child, component)
                    expected = _windows_file_info(self._handles[index + 1])[1:]
                    actual = _windows_file_info(child)[1:]
                    if actual != expected:
                        raise BuildIdentityError(
                            f"artifact is outside the shared target: {candidate}"
                        )
                except BaseException:
                    _windows_api()["CloseHandle"](ctypes.c_void_p(child))
                    raise
                opened.append(child)
                current = child
        finally:
            close = _windows_api()["CloseHandle"]
            for handle in reversed(opened):
                close(ctypes.c_void_p(handle))
        return Path(*components[len(self._target_components) :])

    def _require_directory(self, handle: int, label: str) -> None:
        info = _windows_file_info(handle)
        if info[0] & FILE_ATTRIBUTE_REPARSE_POINT:
            raise BuildIdentityError(f"target path contains a reparse point: {label}")
        if not info[0] & FILE_ATTRIBUTE_DIRECTORY:
            raise BuildIdentityError(f"target path component is not a directory: {label}")

    def _open_windows_file(
        self, components: tuple[str, ...], *, missing_ok: bool
    ) -> BinaryIO | None:
        if not self._handles:
            raise BuildIdentityError("target directory handle is closed")
        opened: list[int] = []
        current = self._handles[-1]
        try:
            for index, component in enumerate(components):
                final = index == len(components) - 1
                try:
                    child = _nt_open_child(
                        current, component, directory=not final, create=False
                    )
                except FileNotFoundError:
                    if missing_ok:
                        return None
                    raise
                transferred = False
                try:
                    info = _windows_file_info(child)
                    if info[0] & FILE_ATTRIBUTE_REPARSE_POINT:
                        raise BuildIdentityError(
                            f"artifact path contains a reparse point: {component}"
                        )
                    if final and (
                        info[0] & FILE_ATTRIBUTE_DIRECTORY
                        or info[0] & FILE_ATTRIBUTE_DEVICE
                    ):
                        raise BuildIdentityError(
                            f"artifact is not a regular file: {component}"
                        )
                    if not final and not info[0] & FILE_ATTRIBUTE_DIRECTORY:
                        raise BuildIdentityError(
                            f"artifact parent is not a directory: {component}"
                        )
                    if final:
                        descriptor = _windows_api()["open_osfhandle"](
                            child, os.O_RDONLY | getattr(os, "O_BINARY", 0)
                        )
                        transferred = True
                        try:
                            return os.fdopen(descriptor, "rb")
                        except BaseException:
                            os.close(descriptor)
                            raise
                    opened.append(child)
                    current = child
                except BaseException:
                    if not transferred:
                        _windows_api()["CloseHandle"](ctypes.c_void_p(child))
                    raise
        except OSError as error:
            raise BuildIdentityError(f"cannot open artifact beneath {self.path}: {error}") from error
        finally:
            close = _windows_api()["CloseHandle"]
            for handle in reversed(opened):
                close(ctypes.c_void_p(handle))
        raise BuildIdentityError("artifact path has no file component")

    def _validate_windows_path(
        self, components: tuple[str, ...], path: Path
    ) -> None:
        if not self._handles:
            raise BuildIdentityError("target directory handle is closed")
        opened: list[int] = []
        current = self._handles[-1]
        try:
            for index, component in enumerate(components):
                final = index == len(components) - 1
                try:
                    child = _nt_open_child(
                        current, component, directory=not final, create=False
                    )
                except FileNotFoundError:
                    return
                try:
                    attributes = _windows_file_info(child)[0]
                    if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                        raise BuildIdentityError(
                            f"target path contains a reparse point: {component}"
                        )
                    if final and attributes & FILE_ATTRIBUTE_DIRECTORY:
                        raise BuildIdentityError(f"artifact path is a directory: {path}")
                    if not final and not attributes & FILE_ATTRIBUTE_DIRECTORY:
                        raise BuildIdentityError(
                            f"artifact parent is not a directory: {component}"
                        )
                except BaseException:
                    _windows_api()["CloseHandle"](ctypes.c_void_p(child))
                    raise
                if not final:
                    opened.append(child)
                    current = child
                else:
                    _windows_api()["CloseHandle"](ctypes.c_void_p(child))
        except OSError as error:
            raise BuildIdentityError(f"cannot validate target path {path}: {error}") from error
        finally:
            close = _windows_api()["CloseHandle"]
            for handle in reversed(opened):
                close(ctypes.c_void_p(handle))

    def _atomic_write_windows(
        self, components: tuple[str, ...], content: bytes
    ) -> None:
        if not self._handles:
            raise BuildIdentityError("target directory handle is closed")
        api = _windows_api()
        opened: list[int] = []
        parent = self._handles[-1]
        temporary = f".{components[-1]}.{uuid.uuid4().hex}.tmp"
        handle: int | None = None
        try:
            for component in components[:-1]:
                child = _nt_open_child(
                    parent,
                    component,
                    directory=True,
                    create=True,
                    access=TARGET_DIRECTORY_ACCESS,
                )
                try:
                    self._require_directory(child, component)
                except BaseException:
                    api["CloseHandle"](ctypes.c_void_p(child))
                    raise
                opened.append(child)
                parent = child
            handle = _nt_open_child(
                parent,
                temporary,
                directory=False,
                create=True,
                access=TEMPORARY_FILE_ACCESS,
                disposition=FILE_CREATE,
            )
            self._write_windows_file(handle, content)
            api["CloseHandle"](ctypes.c_void_p(handle))
            handle = None
            parent_path = _windows_final_path(parent)
            temporary_path = ntpath.join(parent_path, temporary)
            destination_path = ntpath.join(parent_path, components[-1])
            if not api["MoveFileExW"](
                temporary_path,
                destination_path,
                MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
            ):
                raise _windows_error("cannot replace target record")
            temporary = ""
        except OSError as error:
            raise BuildIdentityError(
                f"cannot write target file {Path(*components)}: {error}"
            ) from error
        finally:
            try:
                if handle is not None:
                    try:
                        self._delete_windows_file(handle)
                    finally:
                        api["CloseHandle"](ctypes.c_void_p(handle))
                elif temporary:
                    path = ntpath.join(_windows_final_path(parent), temporary)
                    if not api["DeleteFileW"](path):
                        error = ctypes.get_last_error()
                        if error != ERROR_FILE_NOT_FOUND:
                            raise _windows_error("cannot remove temporary target record")
            finally:
                close = api["CloseHandle"]
                for directory in reversed(opened):
                    close(ctypes.c_void_p(directory))

    def _write_windows_file(self, handle: int, content: bytes) -> None:
        api = _windows_api()
        offset = 0
        while offset < len(content):
            chunk = content[offset : offset + 1024 * 1024]
            buffer = ctypes.create_string_buffer(chunk)
            written = ctypes.c_ulong()
            if not api["WriteFile"](
                ctypes.c_void_p(handle),
                buffer,
                len(chunk),
                ctypes.byref(written),
                None,
            ):
                raise _windows_error("cannot write target record")
            if not written.value:
                raise BuildIdentityError("Windows wrote zero bytes to a target record")
            offset += written.value
        if not api["FlushFileBuffers"](ctypes.c_void_p(handle)):
            raise _windows_error("cannot flush target record")

    def _delete_windows_file(self, handle: int) -> None:
        delete = ctypes.c_ubyte(1)
        if not _windows_api()["SetFileInformationByHandle"](
            ctypes.c_void_p(handle),
            FILE_DISPOSITION_INFO,
            ctypes.byref(delete),
            ctypes.sizeof(delete),
        ):
            raise _windows_error("cannot remove temporary target record")
