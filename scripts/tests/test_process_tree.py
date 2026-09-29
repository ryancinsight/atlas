"""Exercise bounded subprocess-tree ownership with real descendants."""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import process_tree  # noqa: E402


CHILD = textwrap.dedent(
    """
    import os
    import pathlib
    import sys
    import threading

    lock = pathlib.Path(sys.argv[1]).open("r+b")
    if os.name == "nt":
        import msvcrt
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX)
    ready_port = os.environ.get("ATLAS_TEST_READY_PORT")
    if ready_port:
        import socket
        socket.create_connection(("127.0.0.1", int(ready_port))).close()
    print(f"child-ready {os.getpid()}", flush=True)
    threading.Event().wait()
    """
)

WAITING_PARENT = textwrap.dedent(
    """
    import subprocess
    import sys

    child = subprocess.Popen(
        [sys.executable, "-c", sys.argv[2], sys.argv[1]],
        stdout=subprocess.PIPE,
        text=True,
    )
    ready = child.stdout.readline()
    if not ready.startswith("child-ready "):
        raise SystemExit(f"invalid child readiness signal: {ready!r}")
    print(ready, end="", flush=True)
    raise SystemExit(child.wait())
    """
)

EXITING_PARENT = textwrap.dedent(
    """
    import subprocess
    import sys

    child = subprocess.Popen(
        [sys.executable, "-c", sys.argv[2], sys.argv[1]],
        stdout=subprocess.PIPE,
        text=True,
    )
    ready = child.stdout.readline()
    if not ready.startswith("child-ready "):
        raise SystemExit(f"invalid child readiness signal: {ready!r}")
    print(ready, end="", flush=True)
    """
)

READY_SECONDS = 60


def _budget_from_readiness(listener: socket.socket):
    """Start the timeout clock only after the descendant is live."""
    ready = threading.Event()
    real_monotonic = time.monotonic
    frozen: list[float] = []

    def clock() -> float:
        if ready.is_set():
            return real_monotonic()
        if not frozen:
            frozen.append(real_monotonic())
        return frozen[0]

    def after_ready(wait):
        def supervised(*args, **kwargs):
            if not ready.is_set():
                connection, _ = listener.accept()
                connection.close()
                ready.set()
            return wait(*args, **kwargs)

        return supervised

    return (
        patch.object(process_tree.time, "monotonic", clock),
        patch.object(
            process_tree.subprocess.Popen,
            "wait",
            after_ready(subprocess.Popen.wait),
        ),
        patch.object(
            process_tree,
            "_read_posix_status",
            after_ready(process_tree._read_posix_status),
        ),
    )


def _assert_lock_released(test: unittest.TestCase, path: pathlib.Path) -> None:
    with path.open("r+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                test.fail(f"retired descendant retained its file lock: {error}")
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                test.fail("retired descendant retained its file lock")


def _assert_process_inactive(test: unittest.TestCase, process_id: int) -> None:
    if os.name == "nt":
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process_id}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
        test.assertNotIn(f'"{process_id}"', listing.stdout)
        return
    status = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(process_id)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    test.assertTrue(
        status.returncode != 0
        or not status.stdout.strip()
        or status.stdout.lstrip().startswith("Z"),
        f"descendant {process_id} remains active with state {status.stdout.strip()!r}",
    )


class ProcessTreeTests(unittest.TestCase):
    """Keep command semantics while containing every descendant."""

    def test_normal_exit_preserves_status_output_and_input(self):
        command = (
            "import sys; payload=sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(payload); "
            "sys.stderr.buffer.write(b'standard error')"
        )

        result = process_tree.run(
            [sys.executable, "-c", command],
            input=b"standard input\x00",
            timeout=5,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"standard input\x00")
        self.assertEqual(result.stderr, b"standard error")

    def test_nonzero_exit_preserves_status(self):
        result = process_tree.run(
            [sys.executable, "-c", "raise SystemExit(23)"], timeout=5
        )

        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout, b"")

    def test_timeout_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            process_tree.run([sys.executable, "-c", "pass"], timeout=0)

    @unittest.skipUnless(os.name == "nt", "Windows Job Object ordering")
    def test_windows_creates_suspended_assigns_job_then_resumes(self):
        events: list[str] = []
        input_closed = threading.Event()

        class ControlPipe:
            closed = False

            def write(self, payload):
                events.append(f"write:{payload!r}")

            def close(self):
                self.closed = True
                events.append("control-close")
                input_closed.set()

        class SuspendedProcess:
            pid = 123
            returncode = 0
            stdin = ControlPipe()

            def wait(self, timeout):
                if not input_closed.wait(timeout):
                    raise AssertionError("input writer did not close the pipe")
                events.append("wait")
                return self.returncode

        suspended_process = SuspendedProcess()

        def create(command, **options):
            self.assertEqual(command, ["command"])
            self.assertEqual(
                options["creationflags"],
                process_tree.subprocess.CREATE_NEW_PROCESS_GROUP
                | process_tree.windows_process.CREATE_SUSPENDED,
            )
            self.assertIs(options["stdin"], process_tree.subprocess.PIPE)
            events.append("created-suspended")
            return suspended_process

        def assign(process):
            self.assertIs(process, suspended_process)
            self.assertEqual(events, ["created-suspended"])
            events.append("assigned")
            return 17

        def resume(process):
            self.assertIs(process, suspended_process)
            self.assertEqual(events, ["created-suspended", "assigned"])
            events.append("resumed")

        def cleanup(process, job, state):
            self.assertIs(process, suspended_process)
            self.assertEqual(job, 17)
            state.termination_issued = True
            state.launcher_reaped = True
            events.append("cleanup")
            return None

        with (
            patch.object(process_tree.subprocess, "Popen", side_effect=create),
            patch.object(
                process_tree.windows_process,
                "create_kill_job",
                side_effect=assign,
            ),
            patch.object(process_tree.windows_process, "resume", side_effect=resume),
            patch.object(process_tree, "_terminate_process_tree", side_effect=cleanup),
            patch.object(
                process_tree.windows_process,
                "close_job",
                side_effect=lambda job: events.append(f"close-job:{job}"),
            ),
        ):
            result = process_tree.run(["command"], input=b"payload", timeout=5)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            events,
            [
                "created-suspended",
                "assigned",
                "resumed",
                "write:b'payload'",
                "control-close",
                "wait",
                "cleanup",
                "close-job:17",
            ],
        )

    @unittest.skipUnless(os.name == "nt", "Windows inherited standard input")
    def test_windows_without_input_inherits_callers_standard_input(self):
        payload = b"inherited standard input\x00"
        child = (
            "import sys; "
            "sys.stdout.buffer.write(sys.stdin.buffer.read())"
        )
        helper = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(SCRIPTS)!r})
            import process_tree

            result = process_tree.run(
                [sys.executable, "-c", {child!r}], timeout=5
            )
            sys.stdout.buffer.write(result.stdout)
            raise SystemExit(result.returncode)
            """
        )

        inherited = subprocess.run(
            [sys.executable, "-c", helper],
            input=payload,
            capture_output=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(
            inherited.returncode,
            0,
            inherited.stderr.decode(errors="replace"),
        )
        self.assertEqual(inherited.stdout, payload)

    @unittest.skipUnless(os.name == "nt", "Windows pipe backpressure")
    def test_windows_input_backpressure_obeys_timeout(self):
        helper = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(SCRIPTS)!r})
            import process_tree

            try:
                process_tree.run(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    input=b"x" * (2 * 1024 * 1024),
                    timeout=0.2,
                )
            except process_tree.ProcessTreeTimeout as error:
                if error.cleanup_error is not None:
                    raise SystemExit(error.cleanup_error)
                print("bounded")
            else:
                raise SystemExit("backpressured command did not time out")
            """
        )

        bounded = subprocess.run(
            [sys.executable, "-c", helper],
            capture_output=True,
            timeout=process_tree.PROCESS_TREE_CLEANUP_SECONDS + 2,
            check=False,
        )

        self.assertEqual(
            bounded.returncode,
            0,
            bounded.stderr.decode(errors="replace"),
        )
        self.assertEqual(bounded.stdout.splitlines(), [b"bounded"])

    def test_cleanup_does_not_resignal_after_launcher_reap(self):
        class OwnedLauncher:
            pid = 2_147_483_000
            returncode = None

            def kill(self):
                self.returncode = -9

            def wait(self, timeout):
                del timeout
                self.returncode = -9
                return self.returncode

        launcher = OwnedLauncher()
        state = process_tree._CleanupState()
        with (
            patch.object(process_tree.sys, "platform", "linux"),
            patch.object(process_tree.os, "killpg", create=True) as kill_group,
            patch.object(process_tree.signal, "SIGKILL", 9, create=True),
            patch.object(
                process_tree,
                "_posix_group_has_active_members",
                return_value=False,
            ),
        ):
            first = process_tree._terminate_process_tree(launcher, None, state)
            second = process_tree._terminate_process_tree(launcher, None, state)

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertTrue(state.launcher_reaped)
        kill_group.assert_called_once_with(launcher.pid, 9)

    def test_cleanup_retries_interrupted_signal_while_group_is_owned(self):
        class OwnedLauncher:
            pid = 2_147_483_000
            returncode = None

            def kill(self):
                self.returncode = -9

            def wait(self, timeout):
                del timeout
                self.returncode = -9
                return self.returncode

        launcher = OwnedLauncher()
        state = process_tree._CleanupState()
        with (
            patch.object(process_tree.sys, "platform", "linux"),
            patch.object(
                process_tree.os,
                "killpg",
                side_effect=(KeyboardInterrupt(), None),
                create=True,
            ) as kill_group,
            patch.object(process_tree.signal, "SIGKILL", 9, create=True),
            patch.object(
                process_tree,
                "_posix_group_has_active_members",
                return_value=False,
            ),
        ):
            with self.assertRaises(KeyboardInterrupt):
                process_tree._terminate_process_tree(launcher, None, state)
            self.assertFalse(state.termination_issued)
            self.assertFalse(state.launcher_reaped)
            cleanup_error = process_tree._terminate_process_tree(launcher, None, state)

        self.assertIsNone(cleanup_error)
        self.assertTrue(state.termination_issued)
        self.assertTrue(state.launcher_reaped)
        self.assertEqual(kill_group.call_count, 2)

    def test_caller_interrupt_retires_owned_group_before_propagating(self):
        class OwnedLauncher:
            pid = 2_147_483_000
            returncode = None
            stdin = None

            def kill(self):
                self.returncode = -9

            def wait(self, timeout):
                del timeout
                self.returncode = -9
                return self.returncode

        launcher = OwnedLauncher()
        with (
            patch.object(process_tree.sys, "platform", "linux"),
            patch.object(process_tree.subprocess, "Popen", return_value=launcher),
            patch.object(
                process_tree,
                "_read_posix_status",
                side_effect=KeyboardInterrupt(),
            ),
            patch.object(
                process_tree.os,
                "killpg",
                side_effect=(KeyboardInterrupt(), None),
                create=True,
            ) as kill_group,
            patch.object(process_tree.signal, "SIGKILL", 9, create=True),
            patch.object(
                process_tree,
                "_posix_group_has_active_members",
                return_value=False,
            ),
        ):
            with self.assertRaises(KeyboardInterrupt):
                process_tree.run(["command"], timeout=5)

        self.assertEqual(launcher.returncode, -9)
        self.assertEqual(kill_group.call_count, 2)
        kill_group.assert_called_with(launcher.pid, 9)

    def test_normal_exit_retires_live_descendant(self):
        with tempfile.TemporaryDirectory(prefix="atlas-process-tree-exit-") as directory:
            lock = pathlib.Path(directory) / "descendant.lock"
            lock.write_bytes(b"x")

            result = process_tree.run(
                [sys.executable, "-c", EXITING_PARENT, str(lock), CHILD], timeout=5
            )

            self.assertEqual(result.returncode, 0)
            process_id = int(result.stdout.split(b"child-ready ", 1)[1].strip())
            _assert_lock_released(self, lock)
            _assert_process_inactive(self, process_id)

    def test_timeout_retires_live_descendant(self):
        with tempfile.TemporaryDirectory(prefix="atlas-process-tree-timeout-") as directory:
            lock = pathlib.Path(directory) / "descendant.lock"
            lock.write_bytes(b"x")
            listener = socket.create_server(("127.0.0.1", 0))
            listener.settimeout(READY_SECONDS)
            environment = os.environ.copy()
            environment["ATLAS_TEST_READY_PORT"] = str(listener.getsockname()[1])
            clock, windows_wait, posix_wait = _budget_from_readiness(listener)

            with listener, clock, windows_wait, posix_wait:
                with self.assertRaises(process_tree.ProcessTreeTimeout) as raised:
                    process_tree.run(
                        [sys.executable, "-c", WAITING_PARENT, str(lock), CHILD],
                        env=environment,
                        timeout=1,
                    )

            self.assertEqual(raised.exception.timeout, 1)
            self.assertIsNone(raised.exception.cleanup_error)
            output = raised.exception.output
            self.assertIsInstance(output, bytes)
            process_id = int(output.split(b"child-ready ", 1)[1].splitlines()[0])
            _assert_lock_released(self, lock)
            _assert_process_inactive(self, process_id)


if __name__ == "__main__":
    unittest.main()
