"""Observe and terminate Linux process groups without reusing their leader ID."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_build_process_capture import BoundedOutputCapture

def terminate_process_group(
    process: subprocess.Popen[bytes],
    timeout_seconds: float,
    probe_interval_seconds: float,
) -> None:
    """Kill the initial group, drain it, then reap its still-reserved leader."""
    if not sys.platform.startswith("linux"):
        raise OSError("process-group cleanup requires Linux procfs")
    deadline = time.monotonic() + timeout_seconds
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if not wait_for_process_exit_without_reaping(
        process,
        max(0.0, deadline - time.monotonic()),
        probe_interval_seconds,
    ):
        raise OSError("direct process did not terminate before cleanup deadline")
    if not wait_process_group_terminated(
        process.pid, deadline, process.pid, probe_interval_seconds
    ):
        raise OSError("process group did not terminate before cleanup deadline")
    try:
        process.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired as error:
        raise OSError("direct process did not reap before cleanup deadline") from error


def wait_process_group_terminated(
    process_group_id: int,
    deadline: float,
    direct_process_id: int,
    probe_interval_seconds: float,
) -> bool:
    """Wait until the initial group has no live processes or the bound expires."""
    if not sys.platform.startswith("linux"):
        raise OSError("process-group inspection requires Linux procfs")
    while True:
        if not linux_process_group_has_live_members(
            process_group_id, direct_process_id
        ):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            return False
        time.sleep(min(remaining, probe_interval_seconds))


def wait_for_process_exit_without_reaping(
    process: subprocess.Popen[bytes],
    timeout: float,
    probe_interval_seconds: float,
    capture: BoundedOutputCapture | None = None,
) -> bool:
    """Observe direct-child exit while reserving its PID as the group ID."""
    if not all(
        hasattr(os, name)
        for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")
    ):
        raise OSError("POSIX process cleanup requires waitid with WNOWAIT")
    deadline = time.monotonic() + timeout
    while True:
        try:
            status = os.waitid(
                os.P_PID,
                process.pid,
                os.WEXITED | os.WNOHANG | os.WNOWAIT,
            )
        except InterruptedError:
            continue
        if status is not None and status.si_pid == process.pid:
            if capture is not None:
                capture.check()
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            return False
        interval = min(remaining, probe_interval_seconds)
        if capture is None:
            time.sleep(interval)
        else:
            capture.wait(interval)


def linux_process_group_has_live_members(
    process_group_id: int, direct_process_id: int
) -> bool:
    """Reap adopted zombies and detect live members through Linux procfs."""
    with os.scandir("/proc") as entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            process_id = int(entry.name)
            try:
                status = Path(entry.path, "stat").read_bytes()
            except FileNotFoundError:
                continue
            except PermissionError as error:
                raise OSError(
                    f"cannot inspect process {process_id} during process-group cleanup"
                ) from error
            fields = status[status.rfind(b")") + 2 :].split()
            if len(fields) < 4:
                raise OSError(f"invalid proc stat for process {process_id}")
            if (
                int(fields[2]) != process_group_id
                or int(fields[3]) != process_group_id
            ):
                continue
            if fields[0] in {b"Z", b"X"}:
                if process_id != direct_process_id:
                    try:
                        os.waitpid(process_id, os.WNOHANG)
                    except ChildProcessError:
                        pass
                continue
            return True
    return False
