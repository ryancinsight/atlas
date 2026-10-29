"""Exercise bounded subprocess-tree ownership with real descendants."""

from __future__ import annotations

import _thread
import math
import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import ANY, patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import process_tree  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from process_tree_support import (  # noqa: E402
    EXPIRY_HOLD_SECONDS,
    HANG_GUARD_SECONDS,
    NEVER_ENDS,
    budget_from_readiness,
)


CHILD = textwrap.dedent(
    """
    import os
    import pathlib
    import sys
    import threading

    lock = pathlib.Path(sys.argv[1]).open("r+b")
    pathlib.Path(sys.argv[1] + ".pid").write_text(str(os.getpid()))
    if os.name == "nt":
        import msvcrt
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX)
    print(f"child-ready {os.getpid()}", flush=True)
    threading.Event().wait()
    """
)

# The readiness report follows the relayed output, so a deadline that fires after
# the report finds the output already written.
WAITING_PARENT = textwrap.dedent(
    """
    import os
    import socket
    import subprocess
    import sys

    ready_port = int(os.environ.pop("ATLAS_TEST_READY_PORT"))
    child = subprocess.Popen(
        [sys.executable, "-c", sys.argv[2], sys.argv[1]],
        stdout=subprocess.PIPE,
        text=True,
    )
    ready = child.stdout.readline()
    if not ready.startswith("child-ready "):
        raise SystemExit(f"invalid child readiness signal: {ready!r}")
    print(ready, end="", flush=True)
    socket.create_connection(("127.0.0.1", ready_port)).close()
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

READY_SECONDS = HANG_GUARD_SECONDS


def _readline_with_timeout(process: subprocess.Popen, timeout: float) -> bytes:
    """Read one readiness line, terminating a stalled child within the budget."""
    result: list[bytes] = []
    reader = threading.Thread(
        target=lambda: result.append(process.stdout.buffer.readline()),
        daemon=True,
    )
    reader.start()
    reader.join(timeout)
    if reader.is_alive():
        process.kill()
        process.wait(timeout=timeout)
        reader.join(timeout)
        raise AssertionError("child readiness exceeded its deadline")
    return result[0]


def _lock_is_held(path: pathlib.Path) -> bool:
    """Report whether a live process holds the exclusive lock the child takes."""
    with path.open("r+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return True
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            return False
        import fcntl

        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def _assert_lock_released(test: unittest.TestCase, path: pathlib.Path) -> None:
    if _lock_is_held(path):
        test.fail("retired descendant retained its file lock")


def _reap_lock_holder(lock: pathlib.Path) -> None:
    """Kill the child that still holds ``lock``, if a failed assertion left one.

    The child records its pid before taking the lock, so a held lock implies a
    recorded pid, and a released lock means the process is gone and its pid is
    never signalled.
    """
    if not _lock_is_held(lock):
        return
    pid = int(lock.with_name(lock.name + ".pid").read_text())
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            timeout=HANG_GUARD_SECONDS,
            check=False,
        )
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _assert_process_inactive(test: unittest.TestCase, process_id: int) -> None:
    if os.name == "nt":
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process_id}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=HANG_GUARD_SECONDS,
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
        timeout=HANG_GUARD_SECONDS,
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
            timeout=HANG_GUARD_SECONDS,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"standard input\x00")
        self.assertEqual(result.stderr, b"standard error")

    def test_nonzero_exit_preserves_status(self):
        result = process_tree.run(
            [sys.executable, "-c", "raise SystemExit(23)"],
            timeout=HANG_GUARD_SECONDS,
        )

        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout, b"")

    def test_stdout_limit_terminates_the_tree_before_unbounded_capture(self):
        command = (
            "import sys, threading; "
            "sys.stdout.buffer.write(b'x' * 200000); sys.stdout.buffer.flush(); "
            "threading.Event().wait()"
        )

        with self.assertRaises(process_tree.ProcessTreeOutputLimit) as raised:
            process_tree.run(
                [sys.executable, "-c", command],
                timeout=HANG_GUARD_SECONDS,
                stdout_limit=7,
                stderr_limit=7,
            )

        self.assertEqual(raised.exception.stream, "stdout")
        self.assertEqual(raised.exception.limit, 7)
        self.assertEqual(raised.exception.stdout, b"x" * 7)
        self.assertEqual(raised.exception.stderr, b"")

    def test_output_limit_preserves_a_failure_reported_after_real_cleanup(self):
        command = (
            "import os, threading; os.write(1, b'x' * 8); "
            "threading.Event().wait()"
        )
        original_cleanup = process_tree._terminate_process_tree

        def cleanup_then_report(*args, **kwargs):
            self.assertIsNone(original_cleanup(*args, **kwargs))
            return "injected cleanup failure"

        with (
            patch.object(process_tree, "_terminate_process_tree", cleanup_then_report),
            self.assertRaises(process_tree.ProcessTreeOutputLimit) as raised,
        ):
            process_tree.run(
                [sys.executable, "-c", command],
                timeout=HANG_GUARD_SECONDS,
                stdout_limit=7,
            )

        self.assertEqual(raised.exception.stdout, b"x" * 7)
        self.assertEqual(raised.exception.cleanup_error, "injected cleanup failure")
        self.assertIn("process-tree cleanup failed: injected cleanup failure",
                      str(raised.exception))
        self.assertIsInstance(raised.exception.__cause__, process_tree.ProcessTreeCleanupError)
        self.assertEqual(raised.exception.__cause__.cleanup_error, "injected cleanup failure")

    def test_stderr_limit_is_independent_and_default_behavior_is_unchanged(self):
        command = "import sys; sys.stderr.buffer.write(b'abcdef')"

        with self.assertRaises(process_tree.ProcessTreeOutputLimit) as raised:
            process_tree.run(
                [sys.executable, "-c", command],
                timeout=HANG_GUARD_SECONDS,
                stdout_limit=7,
                stderr_limit=5,
            )

        self.assertEqual(raised.exception.stream, "stderr")
        self.assertEqual(raised.exception.stderr, b"abcde")

    def test_output_limits_are_validated_before_launch(self):
        for limit in (-1, True, 1.5, "1"):
            with self.subTest(limit=limit):
                with (
                    patch.object(process_tree.subprocess, "Popen") as launch,
                    self.assertRaisesRegex(ValueError, "nonnegative integer"),
                ):
                    process_tree.run(
                        [sys.executable, "-c", "pass"],
                        timeout=HANG_GUARD_SECONDS,
                        stdout_limit=limit,
                    )
                launch.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX status pipe")
    def test_buffered_exit_status_wins_when_deadline_has_elapsed(self):
        status_read, status_write = os.pipe()
        self.addCleanup(os.close, status_read)
        self.addCleanup(os.close, status_write)
        os.write(status_write, b"exit:7")

        self.assertEqual(
            process_tree._read_posix_status(status_read, time.monotonic() - 1),
            7,
        )

    def test_timeout_must_be_finite_and_positive(self):
        for timeout in (0, -1, math.nan, math.inf, -math.inf):
            with self.subTest(timeout=timeout):
                with (
                    patch.object(process_tree.subprocess, "Popen") as launch,
                    self.assertRaisesRegex(ValueError, "finite and greater than zero"),
                ):
                    process_tree.run([sys.executable, "-c", "pass"], timeout=timeout)

                launch.assert_not_called()

    def test_timeout_that_is_no_number_is_a_type_error_before_any_launch(self):
        for timeout in (None, "5"):
            with self.subTest(timeout=timeout):
                with (
                    patch.object(process_tree.subprocess, "Popen") as launch,
                    self.assertRaises(TypeError),
                ):
                    process_tree.run([sys.executable, "-c", "pass"], timeout=timeout)

                launch.assert_not_called()

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

        def create_job():
            self.assertEqual(events, [])
            events.append("job-created")
            return 17

        def assign(job, process):
            self.assertEqual(job, 17)
            self.assertIs(process, suspended_process)
            self.assertEqual(events, ["job-created", "created-suspended"])
            events.append("assigned")

        def resume(process):
            self.assertIs(process, suspended_process)
            self.assertEqual(events, ["job-created", "created-suspended", "assigned"])
            events.append("resumed")

        def cleanup(process, job, state):
            self.assertIs(process, suspended_process)
            self.assertEqual(job, 17)
            if state.deadline is None:
                state.deadline = (
                    time.monotonic() + process_tree.PROCESS_TREE_CLEANUP_SECONDS
                )
            state.termination_issued = True
            state.launcher_reaped = True
            events.append("cleanup")
            return None

        with (
            patch.object(process_tree.subprocess, "Popen", side_effect=create),
            patch.object(
                process_tree.windows_process,
                "create_kill_job",
                side_effect=create_job,
            ),
            patch.object(
                process_tree.windows_process, "assign_process", side_effect=assign
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
                "job-created",
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

    def test_absent_input_leaves_standard_input_inherited(self):
        payload = b"inherited standard input\x00"
        child = (
            "import sys; "
            "sys.stdout.buffer.write(sys.stdin.buffer.read())"
        )
        guard = READY_SECONDS
        helper = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(SCRIPTS)!r})
            import process_tree

            result = process_tree.run(
                [sys.executable, "-c", {child!r}], timeout={guard!r}
            )
            sys.stdout.buffer.write(result.stdout)
            raise SystemExit(result.returncode)
            """
        )

        inherited = subprocess.run(
            [sys.executable, "-c", helper],
            input=payload,
            capture_output=True,
            timeout=READY_SECONDS + process_tree.PROCESS_TREE_CLEANUP_SECONDS,
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
                    [sys.executable, "-c", {NEVER_ENDS!r}],
                    input=b"x" * (2 * 1024 * 1024),
                    timeout={EXPIRY_HOLD_SECONDS!r},
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
            timeout=HANG_GUARD_SECONDS,
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

    def test_supervisor_and_status_wait_get_the_callers_absolute_deadline(self):
        # The one deadline the caller computes from its clock is the value both
        # sides use: a duration (the time left) would have the supervisor kill
        # at a different instant than the caller waits for. The platform and
        # the launch are replaced, so this runs on every host.
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

        clock = 1_000.0
        timeout = 5.0
        launches: list[tuple] = []

        def record_launch(*arguments):
            launches.append(arguments)
            return ["supervisor"]

        with (
            patch.object(process_tree.sys, "platform", "linux"),
            patch.object(process_tree.time, "monotonic", lambda: clock),
            patch.object(process_tree, "_posix_launch_command", record_launch),
            patch.object(
                process_tree.subprocess, "Popen", return_value=OwnedLauncher()
            ),
            patch.object(
                process_tree, "_read_posix_status", return_value=0
            ) as read_status,
            patch.object(process_tree.os, "killpg", create=True),
            patch.object(process_tree.signal, "SIGKILL", 9, create=True),
            patch.object(
                process_tree, "_posix_group_has_active_members", return_value=False
            ),
        ):
            process_tree.run(["command"], timeout=timeout)

        self.assertEqual(len(launches), 1)
        # (status write, guard read, has input, deadline, command)
        self.assertEqual(launches[0][3], clock + timeout)
        read_status.assert_called_once_with(ANY, clock + timeout)

    def descendant_lock(self, prefix: str) -> pathlib.Path:
        """A lock file in a directory removed after any survivor is killed.

        Cleanups run last-in first-out, so the survivor is reaped before the
        directory that its open lock file would otherwise pin is removed.
        """
        directory = pathlib.Path(
            self.enterContext(tempfile.TemporaryDirectory(prefix=prefix))
        )
        lock = directory / "descendant.lock"
        lock.write_bytes(b"x")
        self.addCleanup(_reap_lock_holder, lock)
        return lock

    def test_normal_exit_retires_live_descendant(self):
        lock = self.descendant_lock("atlas-process-tree-exit-")

        result = process_tree.run(
            [sys.executable, "-c", EXITING_PARENT, str(lock), CHILD],
            timeout=HANG_GUARD_SECONDS,
        )

        self.assertEqual(result.returncode, 0)
        process_id = int(result.stdout.split(b"child-ready ", 1)[1].strip())
        _assert_lock_released(self, lock)
        _assert_process_inactive(self, process_id)

    def test_timeout_retires_live_descendant(self):
        lock = self.descendant_lock("atlas-process-tree-timeout-")
        listener = socket.create_server(("127.0.0.1", 0))
        listener.settimeout(READY_SECONDS)
        environment = os.environ.copy()
        environment["ATLAS_TEST_READY_PORT"] = str(listener.getsockname()[1])

        with listener, budget_from_readiness(listener):
            with self.assertRaises(process_tree.ProcessTreeTimeout) as raised:
                process_tree.run(
                    [sys.executable, "-c", WAITING_PARENT, str(lock), CHILD],
                    env=environment,
                    timeout=EXPIRY_HOLD_SECONDS,
                )

        self.assertEqual(raised.exception.timeout, EXPIRY_HOLD_SECONDS)
        self.assertIsNone(raised.exception.cleanup_error)
        output = raised.exception.output
        self.assertIsInstance(output, bytes)
        process_id = int(output.split(b"child-ready ", 1)[1].splitlines()[0])
        _assert_lock_released(self, lock)
        _assert_process_inactive(self, process_id)

    @unittest.skipUnless(sys.platform == "darwin", "Darwin's zombie-only group errno")
    def test_cleanup_accepts_a_verified_zombie_only_group(self):
        child = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            start_new_session=True,
            stdout=subprocess.PIPE,
        )
        self.addCleanup(child.stdout.close)
        self.addCleanup(child.wait, HANG_GUARD_SECONDS)
        self.addCleanup(child.kill)
        self.assertEqual(child.stdout.read(), b"")
        deadline = time.monotonic() + HANG_GUARD_SECONDS
        while True:
            observed = subprocess.run(
                ["/bin/ps", "-p", str(child.pid), "-o", "stat="],
                capture_output=True, text=True, check=True,
                timeout=HANG_GUARD_SECONDS,
            ).stdout.strip()
            if observed.startswith("Z"):
                break
            self.assertLess(time.monotonic(), deadline, observed)
        with self.assertRaises(PermissionError):
            os.killpg(child.pid, signal.SIGKILL)
        self.assertFalse(process_tree._posix_group_has_active_members(child.pid))
        error = process_tree._terminate_process_tree(
            child, None, process_tree._CleanupState()
        )
        self.assertIsNone(error)
        self.assertEqual(child.returncode, 0)

    def test_darwin_group_probe_uses_native_states_without_a_helper_launch(self):
        for observed in process_tree.darwin_process.GroupState:
            active = observed is not process_tree.darwin_process.GroupState.INACTIVE
            with (
                self.subTest(observed=observed),
                patch.object(process_tree.sys, "platform", "darwin"),
                patch.object(process_tree.subprocess, "Popen") as launch,
                patch.object(
                    process_tree.darwin_process, "group_state", return_value=observed,
                ) as probe,
            ):
                self.assertEqual(process_tree._posix_group_has_active_members(42), active)
                probe.assert_called_once_with(42)
                launch.assert_not_called()

    def test_darwin_snapshot_waits_only_for_transient_changes_within_its_deadline(self):
        states = process_tree.darwin_process.GroupState
        cases = (
            ([states.CHANGING, states.INACTIVE], [0.0, 0.0, 0.0], states.INACTIVE, 1),
            ([states.CHANGING, states.ACTIVE], [0.0, 0.0, 0.0], states.ACTIVE, 1),
            ([states.CHANGING, states.UNKNOWN], [0.0, 0.0, 0.0], states.UNKNOWN, 1),
            ([states.CHANGING], [0.0, 1.0], states.CHANGING, 0),
            ([states.ACTIVE], [0.0], states.ACTIVE, 0),
            ([states.UNKNOWN], [0.0], states.UNKNOWN, 0),
        )
        for readings, times, expected, sleeps in cases:
            with (
                self.subTest(readings=readings),
                patch.object(process_tree.darwin_process, "group_state", side_effect=readings) as probe,
                patch.object(process_tree.time, "monotonic", side_effect=times),
                patch.object(process_tree.time, "sleep") as pause,
                patch.object(process_tree.os, "killpg", create=True) as signal_group,
                patch.object(process_tree.subprocess, "Popen") as launch,
            ):
                self.assertIs(process_tree._darwin_group_snapshot_before(42, 1.0), expected)
                self.assertEqual(probe.call_count, len(readings))
                self.assertEqual(pause.call_count, sleeps)
                for call in pause.call_args_list:
                    self.assertGreater(call.args[0], 0)
                    self.assertLessEqual(call.args[0], process_tree.GROUP_POLL_SECONDS)
                signal_group.assert_not_called()
                launch.assert_not_called()

    def test_darwin_snapshot_never_starts_an_observation_after_expiry(self):
        states = process_tree.darwin_process.GroupState
        for times, readings, expected_reads in (
            ([1.0], [states.INACTIVE], 0),
            ([0.0, 0.0, 1.0], [states.CHANGING, states.INACTIVE], 1),
        ):
            with (
                self.subTest(times=times),
                patch.object(process_tree.darwin_process, "group_state", side_effect=readings) as probe,
                patch.object(process_tree.time, "monotonic", side_effect=times),
                patch.object(process_tree.time, "sleep"),
            ):
                self.assertIs(
                    process_tree._darwin_group_snapshot_before(42, 1.0), states.CHANGING,
                )
                self.assertEqual(probe.call_count, expected_reads)

    @unittest.skipUnless(os.name == "posix", "POSIX group signalling")
    def test_permission_denied_on_a_live_group_remains_a_cleanup_error(self):
        child = subprocess.Popen(
            [sys.executable, "-c", NEVER_ENDS], start_new_session=True,
        )
        self.addCleanup(child.wait, HANG_GUARD_SECONDS)
        self.addCleanup(child.kill)
        with patch.object(
            process_tree.os, "killpg", side_effect=PermissionError("live group denied"),
        ):
            error = process_tree._terminate_process_tree(
                child, None, process_tree._CleanupState()
            )
        self.assertIn("process-group kill failed: live group denied", error)
        self.assertEqual(child.returncode, -signal.SIGKILL)

    def test_survivor_reaper_retires_a_holder_that_outlives_its_run(self):
        lock = self.descendant_lock("atlas-process-tree-reap-")
        holder = subprocess.Popen(
            [sys.executable, "-c", CHILD, str(lock)],
            stdout=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(holder.stdout.close)
        self.addCleanup(holder.kill)
        self.assertTrue(
            _readline_with_timeout(holder, HANG_GUARD_SECONDS).startswith(
                b"child-ready "
            )
        )
        self.assertTrue(_lock_is_held(lock))

        _reap_lock_holder(lock)

        holder.wait(timeout=HANG_GUARD_SECONDS)
        self.assertFalse(_lock_is_held(lock))
        _reap_lock_holder(lock)


if __name__ == "__main__":
    unittest.main()
