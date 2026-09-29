"""Own a suspended Windows process through a kill-on-close Job Object."""

from __future__ import annotations

import ctypes
import subprocess
from ctypes import wintypes


CREATE_SUSPENDED = 0x00000004
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_THREAD_SUSPEND_RESUME = 0x0002
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 0x00000102
_WAIT_FAILED = 0xFFFFFFFF


class _LargeInteger(ctypes.Structure):
    _fields_ = [("quad_part", ctypes.c_longlong)]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", _LargeInteger),
        ("per_job_user_time_limit", _LargeInteger),
        ("limit_flags", wintypes.DWORD),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority_class", wintypes.DWORD),
        ("scheduling_class", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _BasicLimitInformation),
        ("io_info", _IoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


def _kernel32():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _ntdll():
    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtGetNextThread.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    ntdll.NtGetNextThread.restype = wintypes.LONG
    ntdll.RtlNtStatusToDosError.argtypes = [wintypes.LONG]
    ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG
    return ntdll


def create_kill_job(process: subprocess.Popen[bytes]) -> int:
    """Assign a suspended process to a kill-on-close Job Object."""
    kernel32 = _kernel32()
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    information = _ExtendedLimitInformation()
    information.basic_limit_information.limit_flags = (
        _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    if not kernel32.SetInformationJobObject(
        job,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(information),
        ctypes.sizeof(information),
    ):
        error = ctypes.WinError(ctypes.get_last_error())
        _close_after_failure(kernel32, job, error)

    process_handle = getattr(process, "_handle", None)
    if process_handle is None or not kernel32.AssignProcessToJobObject(
        job, wintypes.HANDLE(int(process_handle))
    ):
        error = ctypes.WinError(ctypes.get_last_error())
        _close_after_failure(kernel32, job, error)
    return int(job)


def _close_after_failure(kernel32, handle, error: OSError) -> None:
    if kernel32.CloseHandle(handle):
        raise error
    close_error = ctypes.WinError(ctypes.get_last_error())
    raise OSError(f"{error}; handle close failed: {close_error}") from error


def resume(process: subprocess.Popen[bytes]) -> None:
    """Resume the only thread created for a suspended root process."""
    kernel32 = _kernel32()
    ntdll = _ntdll()
    thread = wintypes.HANDLE()
    process_handle = getattr(process, "_handle", None)
    if process_handle is None:
        raise OSError("suspended process has no native process handle")
    # A globally enumerated thread snapshot adds cost proportional to unrelated
    # system load. The suspended root can only own its initial thread, so the
    # native next-thread query obtains that handle directly.
    status = ntdll.NtGetNextThread(
        wintypes.HANDLE(int(process_handle)),
        None,
        _THREAD_SUSPEND_RESUME,
        0,
        0,
        ctypes.byref(thread),
    )
    if status != 0:
        raise ctypes.WinError(ntdll.RtlNtStatusToDosError(status))
    try:
        if kernel32.ResumeThread(thread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if not kernel32.CloseHandle(thread):
            raise ctypes.WinError(ctypes.get_last_error())


def close_job(job: int) -> str | None:
    """Close a Job Object handle, terminating any remaining members."""
    kernel32 = _kernel32()
    if kernel32.CloseHandle(wintypes.HANDLE(job)):
        return None
    return f"job handle close failed: {ctypes.WinError(ctypes.get_last_error())}"


def terminate_job(job: int, timeout_seconds: float) -> str | None:
    """Terminate and wait for every process assigned to a Job Object."""
    kernel32 = _kernel32()
    if not kernel32.TerminateJobObject(wintypes.HANDLE(job), 1):
        return f"job termination failed: {ctypes.WinError(ctypes.get_last_error())}"
    milliseconds = max(0, min(round(timeout_seconds * 1000), 0xFFFFFFFE))
    wait_status = kernel32.WaitForSingleObject(wintypes.HANDLE(job), milliseconds)
    if wait_status == _WAIT_OBJECT_0:
        return None
    if wait_status == _WAIT_TIMEOUT:
        return f"process tree did not exit within {timeout_seconds:g} seconds"
    if wait_status == _WAIT_FAILED:
        return f"job wait failed: {ctypes.WinError(ctypes.get_last_error())}"
    return f"job wait returned unexpected status {wait_status}"
