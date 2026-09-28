"""Windows native calls used by the held target-directory implementation."""

from __future__ import annotations

import ctypes
import ntpath
import os
from functools import lru_cache
from pathlib import Path, PurePath

from atlas_build_lease import BuildIdentityError

FILE_READ_DATA = 0x00000001
FILE_WRITE_DATA = 0x00000002
FILE_APPEND_DATA = 0x00000004
FILE_READ_EA = 0x00000008
FILE_READ_ATTRIBUTES = 0x00000080
FILE_WRITE_ATTRIBUTES = 0x00000100
DELETE = 0x00010000
READ_CONTROL = 0x00020000
SYNCHRONIZE = 0x00100000
READ_ACCESS = (
    FILE_READ_DATA | FILE_READ_EA | FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE
)
TARGET_DIRECTORY_ACCESS = READ_ACCESS | FILE_WRITE_DATA | FILE_APPEND_DATA
LEASE_FILE_ACCESS = READ_ACCESS | FILE_WRITE_DATA | FILE_APPEND_DATA
TEMPORARY_FILE_ACCESS = (
    FILE_WRITE_DATA | FILE_READ_ATTRIBUTES | FILE_WRITE_ATTRIBUTES | DELETE | SYNCHRONIZE
)

FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_DEVICE = 0x00000040
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400

OPEN_EXISTING = 3
FILE_OPEN = 1
FILE_CREATE = 2
FILE_OPEN_IF = 3
FILE_DIRECTORY_FILE = 0x00000001
FILE_NON_DIRECTORY_FILE = 0x00000040
FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
FILE_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
OBJ_CASE_INSENSITIVE = 0x00000040
FILE_DISPOSITION_INFO = 4
MOVEFILE_REPLACE_EXISTING = 0x00000001
MOVEFILE_WRITE_THROUGH = 0x00000008

ERROR_FILE_NOT_FOUND = 2
NTSTATUS_MASK = 0xFFFFFFFF
STATUS_OBJECT_NAME_NOT_FOUND = 0xC0000034
STATUS_OBJECT_PATH_NOT_FOUND = 0xC000003A

def _windows_absolute(path: Path) -> str:
    raw = os.fspath(path).replace("/", "\\")
    if ".." in PurePath(raw).parts:
        raise BuildIdentityError(f"target directory contains a parent traversal: {raw}")
    drive, tail = ntpath.splitdrive(raw)
    if drive and not tail.startswith("\\"):
        raise BuildIdentityError(f"target directory is drive-relative: {raw}")
    if not ntpath.isabs(raw):
        raw = ntpath.join(os.getcwd(), raw)
    absolute = ntpath.normpath(raw)
    drive, tail = ntpath.splitdrive(absolute)
    if not drive or not tail.startswith("\\"):
        raise BuildIdentityError(f"target directory is not absolute: {absolute}")
    return absolute

def _windows_lexical_path(path: Path) -> str:
    absolute = _windows_absolute(path)
    if absolute.casefold().startswith("\\\\?\\unc\\"):
        return ntpath.normpath("\\\\" + absolute[8:])
    if absolute.startswith("\\\\?\\"):
        return ntpath.normpath(absolute[4:])
    return ntpath.normpath(absolute)

@lru_cache(maxsize=1)
def _windows_api() -> dict[str, object]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll")
    import msvcrt

    class UnicodeString(ctypes.Structure):
        _fields_ = [
            ("Length", ctypes.c_ushort),
            ("MaximumLength", ctypes.c_ushort),
            ("Buffer", ctypes.c_void_p),
        ]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("Length", ctypes.c_ulong),
            ("RootDirectory", ctypes.c_void_p),
            ("ObjectName", ctypes.POINTER(UnicodeString)),
            ("Attributes", ctypes.c_ulong),
            ("SecurityDescriptor", ctypes.c_void_p),
            ("SecurityQualityOfService", ctypes.c_void_p),
        ]

    class IoStatusBlock(ctypes.Structure):
        _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]

    class FileTime(ctypes.Structure):
        _fields_ = [("LowDateTime", ctypes.c_ulong), ("HighDateTime", ctypes.c_ulong)]

    class ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("FileAttributes", ctypes.c_ulong),
            ("CreationTime", FileTime),
            ("LastAccessTime", FileTime),
            ("LastWriteTime", FileTime),
            ("VolumeSerialNumber", ctypes.c_ulong),
            ("FileSizeHigh", ctypes.c_ulong),
            ("FileSizeLow", ctypes.c_ulong),
            ("NumberOfLinks", ctypes.c_ulong),
            ("FileIndexHigh", ctypes.c_ulong),
            ("FileIndexLow", ctypes.c_ulong),
        ]

    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.GetFileInformationByHandle.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ByHandleFileInformation),
    ]
    kernel32.GetFileInformationByHandle.restype = ctypes.c_int
    kernel32.GetFinalPathNameByHandleW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    kernel32.GetFinalPathNameByHandleW.restype = ctypes.c_ulong
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.MoveFileExW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulong]
    kernel32.MoveFileExW.restype = ctypes.c_int
    kernel32.DeleteFileW.argtypes = [ctypes.c_wchar_p]
    kernel32.DeleteFileW.restype = ctypes.c_int
    kernel32.WriteFile.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
        ctypes.c_void_p,
    ]
    kernel32.WriteFile.restype = ctypes.c_int
    kernel32.FlushFileBuffers.argtypes = [ctypes.c_void_p]
    kernel32.FlushFileBuffers.restype = ctypes.c_int
    kernel32.SetFileInformationByHandle.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    kernel32.SetFileInformationByHandle.restype = ctypes.c_int
    ntdll.NtCreateFile.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_ulong,
        ctypes.POINTER(ObjectAttributes),
        ctypes.POINTER(IoStatusBlock),
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    ntdll.NtCreateFile.restype = ctypes.c_long

    return {
        "CreateFileW": kernel32.CreateFileW,
        "GetFileInformationByHandle": kernel32.GetFileInformationByHandle,
        "GetFinalPathNameByHandleW": kernel32.GetFinalPathNameByHandleW,
        "CloseHandle": kernel32.CloseHandle,
        "MoveFileExW": kernel32.MoveFileExW,
        "DeleteFileW": kernel32.DeleteFileW,
        "WriteFile": kernel32.WriteFile,
        "FlushFileBuffers": kernel32.FlushFileBuffers,
        "SetFileInformationByHandle": kernel32.SetFileInformationByHandle,
        "NtCreateFile": ntdll.NtCreateFile,
        "UnicodeString": UnicodeString,
        "ObjectAttributes": ObjectAttributes,
        "IoStatusBlock": IoStatusBlock,
        "ByHandleFileInformation": ByHandleFileInformation,
        "open_osfhandle": msvcrt.open_osfhandle,
    }

def _windows_error(context: str) -> BuildIdentityError:
    return BuildIdentityError(f"{context}: {ctypes.WinError(ctypes.get_last_error())}")

def _windows_file_info(handle: int) -> tuple[int, int, int, int]:
    api = _windows_api()
    info = api["ByHandleFileInformation"]()
    if not api["GetFileInformationByHandle"](ctypes.c_void_p(handle), ctypes.byref(info)):
        raise _windows_error("cannot inspect target handle")
    return (
        info.FileAttributes,
        info.VolumeSerialNumber,
        info.FileIndexHigh,
        info.FileIndexLow,
    )

def _windows_final_path(handle: int) -> str:
    function = _windows_api()["GetFinalPathNameByHandleW"]
    capacity = 512
    while capacity <= 32768:
        buffer = ctypes.create_unicode_buffer(capacity)
        length = function(ctypes.c_void_p(handle), buffer, capacity, 0)
        if not length:
            raise _windows_error("cannot obtain normalized target path")
        if length < capacity:
            return buffer.value.rstrip("\\") or buffer.value
        capacity = length + 1
    raise BuildIdentityError("normalized target path exceeds the Windows path limit")

def _windows_path_from_handle(handle: int) -> Path:
    value = _windows_final_path(handle)
    if value.casefold().startswith("\\\\?\\unc\\"):
        return Path("\\\\" + value[8:])
    if value.startswith("\\\\?\\"):
        return Path(value[4:])
    return Path(value)


def _windows_directory_path(path: Path) -> Path:
    missing: list[str] = []
    existing = path
    while not existing.exists():
        if existing.parent == existing:
            raise BuildIdentityError(f"target directory has no existing ancestor: {path}")
        missing.append(existing.name)
        existing = existing.parent
    if not existing.is_dir():
        raise BuildIdentityError(f"target directory ancestor is not a directory: {existing}")

    api = _windows_api()
    handle = api["CreateFileW"](
        str(existing),
        FILE_READ_ATTRIBUTES,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_OPEN_REPARSE_POINT,
        None,
    )
    if handle in (None, ctypes.c_void_p(-1).value):
        raise _windows_error(f"cannot open target directory ancestor {existing}")
    try:
        resolved = _windows_path_from_handle(int(handle))
    finally:
        api["CloseHandle"](ctypes.c_void_p(handle))
    for component in reversed(missing):
        resolved /= component
    return resolved

def _nt_open_child(
    parent: int,
    name: str,
    *,
    directory: bool,
    create: bool,
    access: int | None = None,
    disposition: int | None = None,
    share_delete: bool | None = None,
) -> int:
    """Open a child relative to its held parent without resolving reparse points."""
    api = _windows_api()
    encoded_name = name.encode("utf-16-le", errors="surrogatepass")
    buffer = ctypes.create_string_buffer(encoded_name, len(encoded_name) + 2)
    byte_length = len(encoded_name)
    unicode_name = api["UnicodeString"](
        byte_length,
        byte_length,
        ctypes.cast(buffer, ctypes.c_void_p),
    )
    attributes = api["ObjectAttributes"](
        ctypes.sizeof(api["ObjectAttributes"]),
        ctypes.c_void_p(parent),
        ctypes.pointer(unicode_name),
        OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    status_block = api["IoStatusBlock"]()
    handle = ctypes.c_void_p()
    allow_delete = not directory if share_delete is None else share_delete
    status = api["NtCreateFile"](
        ctypes.byref(handle),
        READ_ACCESS if access is None else access,
        ctypes.byref(attributes),
        ctypes.byref(status_block),
        None,
        FILE_ATTRIBUTE_DIRECTORY if directory else FILE_ATTRIBUTE_NORMAL,
        FILE_SHARE_READ | FILE_SHARE_WRITE | (FILE_SHARE_DELETE if allow_delete else 0),
        (FILE_OPEN_IF if create else FILE_OPEN) if disposition is None else disposition,
        FILE_OPEN_REPARSE_POINT
        | FILE_SYNCHRONOUS_IO_NONALERT
        | (FILE_DIRECTORY_FILE if directory else FILE_NON_DIRECTORY_FILE),
        None,
        0,
    )
    if status < 0:
        if status & NTSTATUS_MASK in {
            STATUS_OBJECT_NAME_NOT_FOUND,
            STATUS_OBJECT_PATH_NOT_FOUND,
        }:
            raise FileNotFoundError(name)
        raise BuildIdentityError(f"cannot open target path component {name}: NTSTATUS {status:#x}")
    if not handle.value:
        raise BuildIdentityError(f"Windows returned an empty handle for {name}")
    return int(handle.value)
