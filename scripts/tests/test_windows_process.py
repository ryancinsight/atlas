"""Verify Job Object ownership of a process tree against real descendants."""

from __future__ import annotations

import ctypes
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import textwrap
import types
import unittest
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import process_tree  # noqa: E402
import windows_process  # noqa: E402
from process_tree_support import (  # noqa: E402
    EXPIRY_HOLD_SECONDS,
    HANG_GUARD_SECONDS,
    budget_from_readiness,
)

READY_SECONDS = HANG_GUARD_SECONDS
WINDOWS_ONLY = "Job Objects exist only on Windows"

# Each node records its pid after every child it launched reported readiness, so
# when the root reports readiness (socket connect or exit) every pid file exists.
# A detached child runs without a console and in its own process group; it still
# inherits job membership because the job permits no breakaway.
NODE = textwrap.dedent(
    """
    import json
    import os
    import pathlib
    import socket
    import subprocess
    import sys
    import threading

    directory, spec = sys.argv[1], json.loads(sys.argv[2])
    for child in spec.get("children", ()):
        options = {}
        if child.get("detached"):
            options["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        launched = subprocess.Popen(
            [sys.executable, __file__, directory, json.dumps(child)],
            stdout=subprocess.PIPE,
            text=True,
            **options,
        )
        if launched.stdout.readline().strip() != "ready":
            raise SystemExit(f"{child['name']} did not become ready")
    pathlib.Path(directory, "pids", spec["name"]).write_text(str(os.getpid()))
    print("ready", flush=True)
    port = spec.get("ready_port")
    if port:
        socket.create_connection(("127.0.0.1", port)).close()
    if not spec.get("exit"):
        threading.Event().wait()
    """
)

HELPER = textwrap.dedent(
    """
    import sys

    sys.path.insert(0, {scripts!r})
    import process_tree

    process_tree.run(
        [sys.executable, {node!r}, {directory!r}, {spec!r}], timeout={timeout}
    )
    """
)

TREE = {
    "name": "root",
    "children": [
        {"name": "middle", "children": [{"name": "grandchild"}]},
        {"name": "detached", "detached": True},
    ],
}
NAMES = {"root", "middle", "grandchild", "detached"}

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    _SYNCHRONIZE = 0x00100000
    _PROCESS_TERMINATE = 0x0001
    _WAIT_OBJECT_0 = 0
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _kernel32.WaitForSingleObject.restype = wintypes.DWORD
    _kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.TerminateProcess.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL


class _Descendants:
    """Handles to recorded processes, opened while they are alive."""

    def __init__(self) -> None:
        self._handles: dict[str, int] = {}
        self.pids: dict[str, int] = {}

    def open_recorded(self, directory: pathlib.Path) -> None:
        """Open every pid a node recorded, before any termination request."""
        for entry in (directory / "pids").iterdir():
            pid = int(entry.read_text())
            handle = _kernel32.OpenProcess(
                _SYNCHRONIZE | _PROCESS_TERMINATE, False, pid
            )
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            self._handles[entry.name] = handle
            self.pids[entry.name] = pid

    def assert_signalled(
        self, test: unittest.TestCase, milliseconds: int
    ) -> None:
        """Assert each opened process has exited within the stated wait."""
        test.assertEqual(set(self._handles), NAMES)
        for name, handle in sorted(self._handles.items()):
            status = _kernel32.WaitForSingleObject(handle, milliseconds)
            test.assertEqual(
                status,
                _WAIT_OBJECT_0,
                f"descendant {name} (pid {self.pids[name]}) is still running",
            )

    def reap(self) -> None:
        """Terminate any survivor of a failed assertion, then release handles."""
        for handle in self._handles.values():
            if _kernel32.WaitForSingleObject(handle, 0) != _WAIT_OBJECT_0:
                _kernel32.TerminateProcess(handle, 1)
                _kernel32.WaitForSingleObject(handle, 10_000)
            _kernel32.CloseHandle(handle)
        self._handles.clear()


@unittest.skipUnless(os.name == "nt", WINDOWS_ONLY)
class WindowsTreeOwnershipTests(unittest.TestCase):
    """The tree is dead when ``run`` returns or when the caller is."""

    def setUp(self) -> None:
        self.directory = pathlib.Path(
            self.enterContext(tempfile.TemporaryDirectory(prefix="atlas-job-tree-"))
        )
        (self.directory / "pids").mkdir()
        self.node = self.directory / "node.py"
        self.node.write_text(NODE, encoding="utf-8")
        self.tree = _Descendants()
        self.addCleanup(self.tree.reap)

    def command(self, spec: dict) -> list[str]:
        return [sys.executable, str(self.node), str(self.directory), json.dumps(spec)]

    def open_before_termination(self):
        """Open handles when termination is requested, while descendants live."""
        terminate = windows_process.terminate_job

        def opened(job: int, timeout_seconds: float):
            self.tree.open_recorded(self.directory)
            return terminate(job, timeout_seconds)

        return patch.object(process_tree.windows_process, "terminate_job", opened)

    def test_normal_exit_signals_every_descendant_on_return(self):
        with self.open_before_termination():
            result = process_tree.run(
                self.command(dict(TREE, exit=True)), timeout=READY_SECONDS
            )

        self.assertEqual(result.returncode, 0)
        # Zero wait: signalled state must hold at the instant ``run`` returns,
        # because termination is asynchronous until the job itself is waited on.
        self.tree.assert_signalled(self, 0)

    def test_timeout_signals_every_descendant_on_return(self):
        listener = socket.create_server(("127.0.0.1", 0))
        listener.settimeout(READY_SECONDS)
        spec = dict(TREE, ready_port=listener.getsockname()[1])
        clock, windows_wait, posix_wait = budget_from_readiness(listener)

        with listener, clock, windows_wait, posix_wait, self.open_before_termination():
            with self.assertRaises(process_tree.ProcessTreeTimeout) as raised:
                process_tree.run(self.command(spec), timeout=EXPIRY_HOLD_SECONDS)

        self.assertIsNone(raised.exception.cleanup_error)
        self.tree.assert_signalled(self, 0)

    def test_hard_killed_caller_retires_the_tree(self):
        listener = socket.create_server(("127.0.0.1", 0))
        listener.settimeout(READY_SECONDS)
        spec = dict(TREE, ready_port=listener.getsockname()[1])
        helper_log = self.directory / "helper.log"
        with helper_log.open("wb") as log:
            helper = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    HELPER.format(
                        scripts=str(SCRIPTS),
                        node=str(self.node),
                        directory=str(self.directory),
                        spec=json.dumps(spec),
                        timeout=READY_SECONDS,
                    ),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        self.addCleanup(helper.wait)
        self.addCleanup(helper.kill)
        with listener:
            try:
                listener.accept()[0].close()
            except TimeoutError:
                self.fail(f"tree never became ready: {helper_log.read_text()}")
        self.tree.open_recorded(self.directory)

        helper.kill()
        helper.wait(timeout=READY_SECONDS)

        # No runner code executes after the kill, so only the kernel's
        # kill-on-close teardown can end the tree. It terminates members as the
        # dying helper's job handle closes; the only latency is process
        # teardown, the event terminate_job waits on under the same cleanup
        # budget, so that committed budget bounds each wait.
        self.tree.assert_signalled(
            self, round(process_tree.PROCESS_TREE_CLEANUP_SECONDS * 1000)
        )


@unittest.skipUnless(os.name == "nt", WINDOWS_ONLY)
class WindowsApiFailureTests(unittest.TestCase):
    """Failures keep the primary cause and never read a stale last error."""

    def kernel32(self, **functions):
        return patch.object(
            windows_process, "_kernel32", return_value=types.SimpleNamespace(**functions)
        )

    def resume(self, resume_status: int, close_status: int, last_errors: list[int]):
        ntdll = types.SimpleNamespace(NtGetNextThread=lambda *arguments: 0)
        with (
            self.kernel32(
                ResumeThread=lambda handle: resume_status,
                CloseHandle=lambda handle: close_status,
            ),
            patch.object(windows_process, "_ntdll", return_value=ntdll),
            patch.object(
                windows_process.ctypes, "get_last_error", side_effect=last_errors
            ),
        ):
            windows_process.resume(types.SimpleNamespace(_handle=1))

    def test_resume_failure_survives_thread_handle_close_failure(self):
        access_denied, invalid_handle = 5, 6

        with self.assertRaises(OSError) as raised:
            self.resume(0xFFFFFFFF, 0, [access_denied, invalid_handle])

        self.assertEqual(raised.exception.winerror, access_denied)
        self.assertTrue(
            any(
                "thread handle close failed" in note
                for note in raised.exception.__notes__
            ),
            raised.exception.__notes__,
        )

    def test_thread_handle_close_failure_surfaces_after_successful_resume(self):
        invalid_handle = 6

        with self.assertRaises(OSError) as raised:
            self.resume(1, 0, [invalid_handle])

        self.assertEqual(raised.exception.winerror, invalid_handle)

    def test_resume_with_closed_handle_returns(self):
        self.assertIsNone(self.resume(1, 1, []))

    def test_job_assignment_without_process_handle_closes_job_and_names_cause(self):
        closed: list[int] = []
        job = 7

        with (
            self.kernel32(
                CreateJobObjectW=lambda attributes, name: job,
                SetInformationJobObject=lambda *arguments: 1,
                CloseHandle=lambda handle: closed.append(handle) or 1,
            ),
            patch.object(
                windows_process.ctypes,
                "get_last_error",
                side_effect=AssertionError("a stale last error was consulted"),
            ),
            self.assertRaisesRegex(OSError, "no native process handle") as raised,
        ):
            windows_process.create_kill_job(types.SimpleNamespace(_handle=None))

        self.assertIsNone(raised.exception.winerror)
        self.assertEqual(closed, [job])


@unittest.skipUnless(os.name == "nt", WINDOWS_ONLY)
class WindowsJobLifecycleTests(unittest.TestCase):
    """The job handle is released and a failed or slow termination is reported as such."""

    JOB = 7
    ACCESS_DENIED = 5
    INVALID_HANDLE = 6

    def kernel32(self, **functions):
        return patch.object(
            windows_process, "_kernel32", return_value=types.SimpleNamespace(**functions)
        )

    def last_error(self, code: int):
        return patch.object(windows_process.ctypes, "get_last_error", return_value=code)

    def test_close_job_releases_the_handle(self):
        closed: list[int] = []

        with self.kernel32(CloseHandle=lambda handle: closed.append(handle.value) or 1):
            error = windows_process.close_job(self.JOB)

        self.assertIsNone(error)
        self.assertEqual(closed, [self.JOB])

    def test_close_job_failure_names_the_system_error(self):
        with self.kernel32(CloseHandle=lambda handle: 0), self.last_error(
            self.INVALID_HANDLE
        ):
            error = windows_process.close_job(self.JOB)

        self.assertEqual(
            error,
            f"job handle close failed: {ctypes.WinError(self.INVALID_HANDLE)}",
        )

    def terminate(self, terminate_status: int, wait_status: int, timeout: float):
        waits: list[tuple[int, int]] = []

        def wait(handle, milliseconds):
            waits.append((handle.value, milliseconds))
            return wait_status

        with (
            self.kernel32(
                TerminateJobObject=lambda handle, code: terminate_status,
                WaitForSingleObject=wait,
            ),
            self.last_error(self.ACCESS_DENIED),
        ):
            return windows_process.terminate_job(self.JOB, timeout), waits

    def test_failed_termination_is_reported_and_never_waited_on(self):
        error, waits = self.terminate(0, 0, 2.5)

        self.assertEqual(
            error, f"job termination failed: {ctypes.WinError(self.ACCESS_DENIED)}"
        )
        self.assertEqual(waits, [])

    def test_terminated_job_is_waited_on_for_the_stated_budget(self):
        error, waits = self.terminate(1, windows_process._WAIT_OBJECT_0, 2.5)

        self.assertIsNone(error)
        self.assertEqual(waits, [(self.JOB, 2500)])

    def test_job_that_outlives_the_budget_is_reported(self):
        error, _ = self.terminate(1, windows_process._WAIT_TIMEOUT, 2.5)

        self.assertEqual(error, "process tree did not exit within 2.5 seconds")

    def test_failed_wait_is_reported_with_the_system_error(self):
        error, _ = self.terminate(1, windows_process._WAIT_FAILED, 2.5)

        self.assertEqual(
            error, f"job wait failed: {ctypes.WinError(self.ACCESS_DENIED)}"
        )

    def test_unexpected_wait_status_is_reported(self):
        error, _ = self.terminate(1, 0x80, 2.5)

        self.assertEqual(error, "job wait returned unexpected status 128")


if __name__ == "__main__":
    unittest.main()
