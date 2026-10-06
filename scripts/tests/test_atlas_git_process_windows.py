"""Verify the Git wrapper owns real Git-for-Windows descendant processes."""

from __future__ import annotations

import ctypes
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest
from ctypes import wintypes
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import atlas_git_process  # noqa: E402
import process_tree  # noqa: E402
from process_tree_support import (  # noqa: E402
    EXPIRY_HOLD_SECONDS,
    HANG_GUARD_SECONDS,
    budget_from_readiness,
)


GIT_BASH = pathlib.Path("D:/Git/usr/bin/bash.exe")
PYTHON = pathlib.Path("D:/miniforge3/python.exe")
WINDOWS_ONLY = "Windows Job Objects and Git-for-Windows Bash are required"
_PROCESS_TERMINATE = 0x0001
_SYNCHRONIZE = 0x00100000
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 0x00000102

DETACHED_CHILD = textwrap.dedent(
    """
    import os
    import pathlib
    import socket
    import sys
    import threading

    pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding="ascii")
    socket.create_connection(("127.0.0.1", int(sys.argv[2]))).close()
    threading.Event().wait()
    """
)

LAUNCH_DETACHED_CHILD = textwrap.dedent(
    f"""
    import subprocess
    import sys

    subprocess.Popen(
        [sys.executable, "-I", "-c", {DETACHED_CHILD!r}, *sys.argv[1:]],
        creationflags=(
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        ),
        close_fds=True,
    )
    """
)

BASH_TREE = textwrap.dedent(
    f"""\
    set -eu
    "{PYTHON.as_posix()}" -I "$1" "$2" "$3"
    printf 'bash-ready\\n'
    "{PYTHON.as_posix()}" -I -c 'import threading; threading.Event().wait()'
    """
)


@unittest.skipUnless(
    os.name == "nt" and GIT_BASH.is_file() and PYTHON.is_file(),
    WINDOWS_ONLY,
)
class GitBashProcessTests(unittest.TestCase):
    """A timed-out Bash tree has no live reparented native descendant."""

    def setUp(self) -> None:
        self.directory = pathlib.Path(
            self.enterContext(tempfile.TemporaryDirectory(prefix="atlas-git-bash-"))
        )
        self.launcher = self.directory / "launch.py"
        self.launcher.write_text(LAUNCH_DETACHED_CHILD, encoding="utf-8")
        self.pid_file = self.directory / "detached.pid"
        self.process_handle: int | None = None
        self.addCleanup(self._close_process_handle)

    def _open_descendant_before_termination(self):
        terminate = process_tree.windows_process.terminate_job

        def open_then_terminate(job: int, timeout_seconds: float):
            self._open_process_handle()
            return terminate(job, timeout_seconds)

        return patch.object(
            process_tree.windows_process, "terminate_job", open_then_terminate
        )

    def _open_process_handle(self) -> None:
        pid = int(self.pid_file.read_text(encoding="ascii"))
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        self.process_handle = int(
            kernel32.OpenProcess(
                _SYNCHRONIZE | _PROCESS_TERMINATE,
                False,
                pid,
            )
        )
        if not self.process_handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def _close_process_handle(self) -> None:
        if self.process_handle is None:
            if not self.pid_file.exists():
                return
            self._open_process_handle()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = wintypes.HANDLE(self.process_handle)
        wait_status = kernel32.WaitForSingleObject(handle, 0)
        if wait_status == _WAIT_TIMEOUT:
            if not kernel32.TerminateProcess(handle, 1):
                raise ctypes.WinError(ctypes.get_last_error())
            wait_status = kernel32.WaitForSingleObject(
                handle,
                round(process_tree.PROCESS_TREE_CLEANUP_SECONDS * 1000),
            )
        if wait_status != _WAIT_OBJECT_0:
            raise RuntimeError(f"descendant cleanup wait returned {wait_status}")
        if not kernel32.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())
        self.process_handle = None

    def _assert_descendant_exited(self) -> None:
        if self.process_handle is None:
            self._open_process_handle()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        status = kernel32.WaitForSingleObject(
            wintypes.HANDLE(self.process_handle), 0
        )
        self.assertEqual(
            status,
            _WAIT_OBJECT_0,
            "the detached Bash descendant outlived the timeout",
        )

    def test_timeout_retires_reparented_detached_descendant(self):
        listener = socket.create_server(("127.0.0.1", 0))
        listener.settimeout(HANG_GUARD_SECONDS)
        command = [
            str(GIT_BASH),
            "-c",
            BASH_TREE,
            "atlas-git-bash",
            str(self.launcher),
            str(self.pid_file),
            str(listener.getsockname()[1]),
        ]

        with (
            listener,
            budget_from_readiness(listener),
            self._open_descendant_before_termination(),
            self.assertRaises(atlas_git_process.GitProcessError) as raised,
        ):
            atlas_git_process.execute_process(
                command,
                timeout=EXPIRY_HOLD_SECONDS,
            )

        error = raised.exception
        self.assertTrue(error.timed_out)
        self.assertEqual(
            str(error),
            f"process timed out after {EXPIRY_HOLD_SECONDS}s: {' '.join(command)}",
        )
        self._assert_descendant_exited()
        self.assertIsInstance(error.__cause__, process_tree.ProcessTreeTimeout)
        self.assertIsNone(error.__cause__.cleanup_error)
        self.assertEqual(error.__cause__.stdout, b"bash-ready\n")
        self.assertEqual(error.__cause__.stderr, b"")

    def test_ordinary_bash_command_preserves_status_and_output(self):
        command = [
            str(GIT_BASH),
            "-c",
            "printf 'ordinary-output\\n'; printf 'ordinary-error\\n' >&2; exit 23",
        ]

        result = atlas_git_process.execute_process(
            command,
            timeout=HANG_GUARD_SECONDS,
        )

        self.assertEqual(result.command, tuple(command))
        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout, b"ordinary-output\n")
        self.assertEqual(result.stderr, b"ordinary-error\n")


if __name__ == "__main__":
    unittest.main()
