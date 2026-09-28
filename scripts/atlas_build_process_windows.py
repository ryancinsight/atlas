"""Contain Windows build commands and all processes they create."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

CREATE_SUSPENDED = 0x00000004
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
THREAD_SUSPEND_RESUME = 0x0002
TH32CS_SNAPTHREAD = 0x00000004
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount",
        "WriteOperationCount",
        "OtherOperationCount",
        "ReadTransferCount",
        "WriteTransferCount",
        "OtherTransferCount",
    )]


class _BasicAccountingInformation(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ThreadEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


def _kernel32() -> ctypes.WinDLL:
    return ctypes.WinDLL("kernel32", use_last_error=True)


def create_job() -> int:
    """Create a kill-on-close job for one build process tree."""
    kernel = _kernel32()
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = _ExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(
        handle,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        error = ctypes.WinError(ctypes.get_last_error())
        kernel.CloseHandle(handle)
        raise error
    return int(handle)


def assign_process(job: int, process_id: int) -> None:
    """Assign a suspended process before its primary thread can spawn children."""
    kernel = _kernel32()
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    process = kernel.OpenProcess(
        PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, process_id
    )
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel.AssignProcessToJobObject(job, process):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(process)


def resume_primary_thread(process_id: int) -> None:
    """Resume the sole primary thread created in the suspended process."""
    kernel = _kernel32()
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
    kernel.Thread32First.restype = wintypes.BOOL
    kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
    kernel.Thread32Next.restype = wintypes.BOOL
    kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    invalid = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = _ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == process_id:
                thread = kernel.OpenThread(THREAD_SUSPEND_RESUME, False, entry.th32ThreadID)
                if not thread:
                    raise ctypes.WinError(ctypes.get_last_error())
                try:
                    if kernel.ResumeThread(thread) == 0xFFFFFFFF:
                        raise ctypes.WinError(ctypes.get_last_error())
                finally:
                    kernel.CloseHandle(thread)
                return
            found = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        raise OSError(f"no primary thread found for suspended process {process_id}")
    finally:
        kernel.CloseHandle(snapshot)


def wait_empty(job: int, timeout_milliseconds: int) -> bool:
    """Return whether the job has no active processes before the deadline."""
    kernel = _kernel32()
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    result = kernel.WaitForSingleObject(job, timeout_milliseconds)
    if result == WAIT_OBJECT_0:
        return True
    if result == WAIT_TIMEOUT:
        return False
    raise ctypes.WinError(ctypes.get_last_error())


def active_processes(job: int) -> int:
    """Return the number of live processes assigned to a job."""
    kernel = _kernel32()
    kernel.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.QueryInformationJobObject.restype = wintypes.BOOL
    information = _BasicAccountingInformation()
    returned_length = wintypes.DWORD()
    if not kernel.QueryInformationJobObject(
        job,
        1,
        ctypes.byref(information),
        ctypes.sizeof(information),
        ctypes.byref(returned_length),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(information.ActiveProcesses)


def terminate_job(job: int, exit_code: int = 1) -> None:
    """Request termination of every process assigned to the job."""
    kernel = _kernel32()
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    if not kernel.TerminateJobObject(job, exit_code):
        raise ctypes.WinError(ctypes.get_last_error())


def close_job(job: int) -> None:
    """Close the job, terminating any remaining member as a final guard."""
    kernel = _kernel32()
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    if not kernel.CloseHandle(job):
        raise ctypes.WinError(ctypes.get_last_error())
