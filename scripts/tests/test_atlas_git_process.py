#!/usr/bin/env python3
"""Tests for bounded subprocess groups and Windows job cleanup."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atlas_git_process import GitProcessError, execute_process


def process_is_running(process_id: int) -> bool:
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.WaitForSingleObject.restype = ctypes.c_ulong
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_int
        handle = kernel.OpenProcess(0x00100000, False, process_id)
        if not handle:
            if ctypes.get_last_error() == 87:
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            if result == 0:
                return False
            if result == 258:
                return True
            raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    if sys.platform.startswith("linux"):
        try:
            stat = Path(f"/proc/{process_id}/stat").read_bytes()
        except FileNotFoundError:
            return False
        return stat[stat.rfind(b")") + 2] != ord("Z")
    return True


class ProcessBoundaryTestCase(unittest.TestCase):
    def test_successful_command_with_no_descendants_returns_its_exit_code(self) -> None:
        result = execute_process(
            (
                sys.executable,
                "-c",
                "import sys; sys.stdout.write('ready'); sys.stderr.write('checked')",
            ),
            timeout=30,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"ready")
        self.assertEqual(result.stderr, b"checked")

    def test_successful_command_terminates_its_remaining_contained_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-process-tree-") as temporary:
            root = Path(temporary)
            pid_path = root / "child.pid"
            script = root / "spawn.py"
            child_code = "import threading; threading.Event().wait()"
            script.write_text(
                "import subprocess, sys\n"
                f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                f"open({str(pid_path)!r}, 'w', encoding='ascii').write(str(child.pid))\n"
                "sys.stdout.write('parent-output')\n"
                "sys.stderr.write('parent-diagnostic')\n",
                encoding="utf-8",
            )

            result = execute_process(
                (sys.executable, str(script)),
                cwd=root,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"parent-output")
            self.assertEqual(result.stderr, b"parent-diagnostic")
            self.assertTrue(pid_path.is_file())
            child_pid = int(pid_path.read_text(encoding="ascii"))
            self.assertGreater(child_pid, 0)
            self.assertFalse(process_is_running(child_pid))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux procfs behavior")
    def test_successful_command_terminates_child_with_non_ascii_process_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-process-non-ascii-") as temporary:
            root = Path(temporary)
            pid_path = root / "child.pid"
            script = root / "spawn.py"
            child_code = (
                "import ctypes, os, threading\n"
                "libc = ctypes.CDLL(None)\n"
                "if libc.prctl(15, ctypes.c_char_p(b'\\xffchild'), 0, 0, 0) != 0: raise OSError('PR_SET_NAME failed')\n"
                "status = open('/proc/self/stat', 'rb').read()\n"
                "if status[status.index(b'(') + 1:status.rfind(b')')] != b'\\xffchild': raise AssertionError('process name was not set')\n"
                "os.write(1, b'ready')\n"
                "threading.Event().wait()\n"
            )
            script.write_text(
                "import subprocess, sys\n"
                f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}], stdout=subprocess.PIPE)\n"
                "if child.stdout.read(5) != b'ready': raise RuntimeError('child process-name check failed')\n"
                f"open({str(pid_path)!r}, 'w', encoding='ascii').write(str(child.pid))\n"
                "sys.stdout.write('parent-output')\n",
                encoding="utf-8",
            )

            result = execute_process(
                (sys.executable, str(script)),
                cwd=root,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b"parent-output")
            child_pid = int(pid_path.read_text(encoding="ascii"))
            self.assertFalse(process_is_running(child_pid))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux subreaper behavior")
    def test_successful_command_reaps_terminated_adopted_zombie(self) -> None:
        libc = ctypes.CDLL(None, use_errno=True)
        prctl = libc.prctl
        prctl.argtypes = [ctypes.c_int]
        prctl.restype = ctypes.c_int
        previous = ctypes.c_int()
        if prctl(37, ctypes.byref(previous), ctypes.c_ulong(0), ctypes.c_ulong(0), ctypes.c_ulong(0)) != 0:
            raise OSError(ctypes.get_errno(), "PR_GET_CHILD_SUBREAPER failed")
        if prctl(36, ctypes.c_ulong(1), ctypes.c_ulong(0), ctypes.c_ulong(0), ctypes.c_ulong(0)) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER failed")
        try:
            with tempfile.TemporaryDirectory(prefix="atlas-process-subreaper-") as temporary:
                root = Path(temporary)
                pid_path = root / "child.pid"
                script = root / "spawn.py"
                child_code = "import threading; threading.Event().wait()"
                script.write_text(
                    "import subprocess, sys\n"
                    f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                    f"open({str(pid_path)!r}, 'w', encoding='ascii').write(str(child.pid))\n"
                    "sys.stdout.write('parent-output')\n"
                    "sys.exit(7)\n",
                    encoding="utf-8",
                )

                result = execute_process(
                    (sys.executable, str(script)),
                    cwd=root,
                    timeout=30,
                )

                self.assertEqual(result.returncode, 7)
                self.assertEqual(result.stdout, b"parent-output")
                child_pid = int(pid_path.read_text(encoding="ascii"))
                self.assertFalse(process_is_running(child_pid))
                with self.assertRaises(ChildProcessError):
                    os.waitpid(child_pid, os.WNOHANG)
        finally:
            if prctl(
                36,
                ctypes.c_ulong(previous.value),
                ctypes.c_ulong(0),
                ctypes.c_ulong(0),
                ctypes.c_ulong(0),
            ) != 0:
                raise OSError(ctypes.get_errno(), "could not restore child subreaper")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux process-group identity")
    def test_capture_failure_after_cleanup_does_not_signal_reused_group_id(self) -> None:
        import atlas_git_process

        capture_close = atlas_git_process.BoundedOutputCapture.close
        real_killpg = os.killpg
        with tempfile.TemporaryDirectory(prefix="atlas-process-capture-error-") as temporary:
            root = Path(temporary)
            pid_path = root / "child.pid"
            script = root / "spawn.py"
            child_code = "import threading; threading.Event().wait()"
            script.write_text(
                "import subprocess, sys\n"
                f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                f"open({str(pid_path)!r}, 'w', encoding='ascii').write(str(child.pid))\n",
                encoding="utf-8",
            )

            close_failed = False

            def fail_capture_close(capture: object) -> OSError | None:
                nonlocal close_failed
                result = capture_close(capture)
                if not close_failed:
                    close_failed = True
                    raise OSError("injected capture close failure")
                return result

            with (
                mock.patch.object(
                    atlas_git_process.BoundedOutputCapture,
                    "close",
                    new=fail_capture_close,
                ),
                mock.patch.object(atlas_git_process.os, "killpg", wraps=real_killpg) as killpg,
            ):
                with self.assertRaisesRegex(GitProcessError, "cannot run"):
                    execute_process((sys.executable, str(script)), cwd=root, timeout=30)

            self.assertEqual(killpg.call_count, 1)
            child_pid = int(pid_path.read_text(encoding="ascii"))
            self.assertFalse(process_is_running(child_pid))

    def test_timed_out_command_terminates_a_contained_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-process-timeout-") as temporary:
            root = Path(temporary)
            pid_path = root / "child.pid"
            script = root / "spawn.py"
            child_code = "import threading; threading.Event().wait()"
            script.write_text(
                "import subprocess, sys, threading\n"
                f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                f"open({str(pid_path)!r}, 'w', encoding='ascii').write(str(child.pid))\n"
                "threading.Event().wait()\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(GitProcessError, "timed out") as raised:
                execute_process(
                    (sys.executable, str(script)),
                    cwd=root,
                    timeout=1,
                )

            self.assertTrue(raised.exception.timed_out)
            self.assertTrue(pid_path.is_file())
            child_pid = int(pid_path.read_text(encoding="ascii"))
            self.assertGreater(child_pid, 0)
            self.assertFalse(process_is_running(child_pid))

    def test_stdin_and_captured_output_keep_their_byte_values(self) -> None:
        payload = b"\x00input\xff"
        result = execute_process(
            (
                sys.executable,
                "-c",
                "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); "
                "sys.stderr.buffer.write(b'diagnostic')",
            ),
            stdin=payload,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, payload)
        self.assertEqual(result.stderr, b"diagnostic")

    @unittest.skipIf(os.name == "nt", "non-Linux POSIX process boundary")
    def test_non_linux_posix_is_rejected_before_process_launch(self) -> None:
        import atlas_git_process

        with (
            mock.patch.object(atlas_git_process.os, "name", "posix"),
            mock.patch.object(atlas_git_process.sys, "platform", "darwin"),
            mock.patch.object(atlas_git_process.subprocess, "Popen") as launch,
            self.assertRaisesRegex(
                GitProcessError, "supported only on Windows and Linux"
            ),
        ):
            execute_process((sys.executable, "-c", "pass"), timeout=30)
        launch.assert_not_called()

    def test_capture_pipes_close_after_success_and_timeout(self) -> None:
        import atlas_git_process

        create_process = atlas_git_process.subprocess.Popen
        processes = []

        def track_process(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
            process = create_process(*args, **kwargs)
            processes.append(process)
            return process

        for timed_out in (False, True):
            with self.subTest(timed_out=timed_out):
                processes.clear()
                command = (
                    (sys.executable, "-c", "import threading; threading.Event().wait()")
                    if timed_out
                    else (sys.executable, "-c", "import sys; sys.stdout.write('ready')")
                )
                with mock.patch.object(
                    atlas_git_process.subprocess, "Popen", side_effect=track_process
                ):
                    if timed_out:
                        with self.assertRaises(GitProcessError) as raised:
                            execute_process(command, timeout=1)
                        self.assertTrue(raised.exception.timed_out)
                    else:
                        result = execute_process(command, timeout=30)
                        self.assertEqual(result.stdout, b"ready")
                self.assertEqual(len(processes), 1)
                self.assertTrue(processes[0].stdout.closed)
                self.assertTrue(processes[0].stderr.closed)

    def test_capture_budget_accepts_exact_limit_and_rejects_one_more_byte(self) -> None:
        exact = execute_process(
            (sys.executable, "-c", "import os; os.write(1, b'x' * 1024)"),
            timeout=30,
            max_capture_bytes=1024,
        )
        self.assertEqual(exact.stdout, b"x" * 1024)
        self.assertEqual(exact.stderr, b"")

        with self.assertRaisesRegex(GitProcessError, "capture limit") as raised:
            execute_process(
                (
                    sys.executable,
                    "-c",
                    "import os;\nwhile True: os.write(1, b'x' * 4096)",
                ),
                timeout=30,
                max_capture_bytes=1024,
            )
        self.assertTrue(raised.exception.output_limit_exceeded)
        self.assertFalse(raised.exception.timed_out)

    @unittest.skipUnless(os.name == "nt", "Windows Job Object cleanup contract")
    def test_timeout_remains_typed_when_job_cleanup_reports_os_error(self) -> None:
        import atlas_build_process_windows as process_windows

        with tempfile.TemporaryDirectory(prefix="atlas-process-job-error-") as temporary:
            root = Path(temporary)
            pid_path = root / "child.pid"
            script = root / "spawn.py"
            child_code = "import threading; threading.Event().wait()"
            script.write_text(
                "import subprocess, sys, threading\n"
                f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
                f"open({str(pid_path)!r}, 'w', encoding='ascii').write(str(child.pid))\n"
                "threading.Event().wait()\n",
                encoding="utf-8",
            )

            close = process_windows.close_job

            def fail_after_close(job: int) -> None:
                close(job)
                raise OSError("injected job close failure")

            real_popen = subprocess.Popen
            for operation in ("terminate_job", "wait_empty", "close_job"):
                with self.subTest(operation=operation):
                    spawned = []

                    def record_process(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
                        process = real_popen(*args, **kwargs)
                        spawned.append(process)
                        return process

                    failure = (
                        OSError("injected job termination failure")
                        if operation == "terminate_job"
                        else (
                            OSError("injected job wait failure")
                            if operation == "wait_empty"
                            else fail_after_close
                        )
                    )
                    with (
                        mock.patch.object(
                            process_windows,
                            operation,
                            side_effect=failure,
                        ),
                        mock.patch("atlas_git_process.subprocess.Popen", side_effect=record_process),
                    ):
                        with self.assertRaisesRegex(
                            GitProcessError, "process timed out"
                        ) as raised:
                            execute_process(
                                (sys.executable, str(script)),
                                cwd=root,
                                timeout=1,
                            )

                    self.assertTrue(raised.exception.timed_out)
                    self.assertIn("cleanup failed", str(raised.exception))
                    self.assertEqual(len(spawned), 1)
                    self.assertIsNotNone(spawned[0].returncode)
                    self.assertTrue(pid_path.is_file())
                    child_pid = int(pid_path.read_text(encoding="ascii"))
                    self.assertGreater(child_pid, 0)
                    self.assertFalse(process_is_running(child_pid))


if __name__ == "__main__":
    unittest.main()
