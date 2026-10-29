"""Verify cleanup retry scope and standard-input delivery reporting."""

from __future__ import annotations

import errno
from contextlib import nullcontext
import pathlib
import sys
import threading
import time
import unittest
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import process_tree  # noqa: E402
from process_tree_support import (  # noqa: E402
    EXPIRY_HOLD_SECONDS,
    HANG_GUARD_SECONDS,
    NEVER_ENDS,
)

WAIT_SECONDS = HANG_GUARD_SECONDS
# A retry loop that swallows defects must end by this deadline, as an assertion
# failure, rather than hang the suite.
RETRY_WINDOW_SECONDS = 1.0


class InterruptedCleanupTests(unittest.TestCase):
    """Only the caller's interrupt is retried; defects keep type and message."""

    def state(self, seconds_left: float) -> process_tree._CleanupState:
        state = process_tree._CleanupState()
        state.deadline = time.monotonic() + seconds_left
        return state

    def test_interrupt_is_retried_until_cleanup_completes(self):
        with patch.object(
            process_tree,
            "_terminate_process_tree",
            side_effect=(KeyboardInterrupt(), None),
        ) as terminate:
            error = process_tree._finish_interrupted_cleanup(
                object(), None, self.state(WAIT_SECONDS)
            )

        self.assertIsNone(error)
        self.assertEqual(terminate.call_count, 2)

    def test_interrupt_past_deadline_reports_instead_of_retrying_forever(self):
        with patch.object(
            process_tree, "_terminate_process_tree", side_effect=KeyboardInterrupt()
        ) as terminate:
            error = process_tree._finish_interrupted_cleanup(
                object(), None, self.state(-1.0)
            )

        self.assertEqual(
            error,
            "process-tree cleanup remained interrupted through its bounded "
            "deadline (1 interruptions)",
        )
        self.assertEqual(terminate.call_count, 1)

    def test_cleanup_defect_propagates_unchanged_without_retry(self):
        defect = ValueError("cleanup defect")
        with patch.object(
            process_tree, "_terminate_process_tree", side_effect=defect
        ) as terminate:
            with self.assertRaises(ValueError) as raised:
                process_tree._finish_interrupted_cleanup(
                    object(), None, self.state(RETRY_WINDOW_SECONDS)
                )

        self.assertIs(raised.exception, defect)
        self.assertEqual(terminate.call_count, 1)

    def test_deferred_signal_keeps_an_existing_cleanup_defect_primary(self):
        defect = ValueError("confirmed cleanup defect")
        handler = unittest.mock.Mock(side_effect=KeyboardInterrupt())
        with (
            patch.object(process_tree.signal, "getsignal", return_value=handler),
            patch.object(process_tree.signal, "signal") as install,
        ):
            try:
                with process_tree._InterruptDeferral("cleanup request"):
                    capture = install.call_args.args[1]
                    capture(process_tree.signal.SIGINT, None)
                    raise defect
            except KeyboardInterrupt:
                self.fail("deferred interrupt replaced the cleanup defect")
            except ValueError as raised:
                self.assertIs(raised, defect)
                self.assertEqual(str(raised), "confirmed cleanup defect")
                self.assertIn("SIGINT received during cleanup request was superseded", raised.__notes__)
            else:
                self.fail("cleanup defect was swallowed")
        handler.assert_not_called()
        self.assertIs(install.call_args.args[1], handler)

    def test_run_surfaces_cleanup_defect_instead_of_hanging(self):
        class Launcher:
            pid = 2_147_483_000
            returncode = None
            stdin = None

        defect = RuntimeError("cleanup defect")

        def failing_cleanup(process, windows_job, state):
            if state.deadline is None:
                state.deadline = time.monotonic() + RETRY_WINDOW_SECONDS
            raise defect

        with (
            patch.object(process_tree.sys, "platform", "linux"),
            patch.object(process_tree.subprocess, "Popen", return_value=Launcher()),
            patch.object(
                process_tree, "_read_posix_status", side_effect=KeyboardInterrupt()
            ),
            patch.object(
                process_tree, "_terminate_process_tree", side_effect=failing_cleanup
            ),
        ):
            # A cleanup that swallows the defect re-raises the caller's
            # interrupt instead; contain it so that regression fails this test
            # by name rather than aborting the whole session.
            try:
                process_tree.run(["command"], timeout=5)
            except KeyboardInterrupt:
                self.fail("the cleanup defect was replaced by the caller's interrupt")
            except RuntimeError as raised:
                self.assertIs(raised, defect)
                self.assertIsInstance(raised.__context__, KeyboardInterrupt)
            else:
                self.fail("run returned although its cleanup raised a defect")


class CleanupFailureReportingTests(unittest.TestCase):
    """A tree that cannot be retired is reported on every outcome, never dropped."""

    FAILURE = "synthetic cleanup failure"

    def failing_cleanup(self):
        retire = process_tree._terminate_process_tree

        def retire_then_fail(process, windows_job, state):
            retire(process, windows_job, state)
            return self.FAILURE

        return patch.object(process_tree, "_terminate_process_tree", retire_then_fail)

    def test_cleanup_failure_after_normal_exit_is_raised(self):
        with self.failing_cleanup(), self.assertRaises(
            process_tree.ProcessTreeCleanupError
        ) as raised:
            process_tree.run(
                [sys.executable, "-I", "-c", "pass"], timeout=HANG_GUARD_SECONDS
            )

        self.assertEqual(raised.exception.cleanup_error, self.FAILURE)
        self.assertEqual(
            str(raised.exception), f"process-tree cleanup failed: {self.FAILURE}"
        )

    def test_cleanup_failure_after_timeout_is_carried_on_the_timeout(self):
        with self.failing_cleanup(), self.assertRaises(
            process_tree.ProcessTreeTimeout
        ) as raised:
            process_tree.run(
                [sys.executable, "-I", "-c", NEVER_ENDS],
                timeout=EXPIRY_HOLD_SECONDS,
            )

        self.assertEqual(raised.exception.cleanup_error, self.FAILURE)
        # A consumer that prints the exception, or reads its cause, sees the
        # failure without knowing the attribute exists.
        self.assertTrue(
            str(raised.exception).endswith(
                f"; process-tree cleanup failed: {self.FAILURE}"
            ),
            str(raised.exception),
        )
        self.assertIsInstance(
            raised.exception.__cause__, process_tree.ProcessTreeCleanupError
        )
        self.assertEqual(raised.exception.__cause__.cleanup_error, self.FAILURE)

    def test_timeout_without_a_cleanup_failure_has_the_plain_message_and_no_cause(self):
        with self.assertRaises(process_tree.ProcessTreeTimeout) as raised:
            process_tree.run(
                [sys.executable, "-I", "-c", NEVER_ENDS],
                timeout=EXPIRY_HOLD_SECONDS,
            )

        self.assertIsNone(raised.exception.cleanup_error)
        self.assertNotIn("cleanup", str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)


class CleanupPhaseStateTests(unittest.TestCase):
    """Confirmed outcomes survive interruption without replaying requests."""

    def exercise(self, phase=None, observed="UNKNOWN", platform="darwin"):
        state = process_tree._CleanupState(deadline=1.0)
        calls = dict(signal=0, proof=0, wait=0, membership=0)
        clock = [0.0]
        owner = self

        class Launcher:
            pid = 2_147_483_000
            returncode = None

            def kill(self):
                owner.assertFalse(state.launcher_reaped)

            def wait(self, timeout):
                calls["wait"] += 1
                owner.assertLessEqual(calls["wait"], 2)
                if phase == "wait" and calls["wait"] == 1:
                    raise KeyboardInterrupt()
                self.returncode = 0
                return 0

        def signal_group(pid, signum):
            self.assertEqual((pid, signum), (Launcher.pid, process_tree.signal.SIGKILL))
            self.assertFalse(state.launcher_reaped)
            calls["signal"] += 1
            self.assertLessEqual(calls["signal"], 2)
            if phase == "syscall":
                if calls["signal"] == 1:
                    raise KeyboardInterrupt()
                return
            raise PermissionError(errno.EPERM, "controlled EPERM")

        def proof(pid, deadline):
            self.assertEqual((pid, deadline), (Launcher.pid, 1.0))
            self.assertFalse(state.launcher_reaped)
            calls["proof"] += 1
            self.assertLessEqual(calls["proof"], 2)
            if phase in ("proof", "proof_deadline") and calls["proof"] == 1:
                if phase == "proof_deadline":
                    clock[0] = 1.0
                raise KeyboardInterrupt()
            result = "INACTIVE" if phase == "proof" else observed
            return getattr(process_tree.darwin_process.GroupState, result)

        def membership(pid):
            self.assertEqual(pid, Launcher.pid)
            self.assertTrue(state.launcher_reaped)
            calls["membership"] += 1
            if phase == "postreap" and calls["membership"] == 1:
                raise KeyboardInterrupt()
            return False

        with (
            patch.object(process_tree.sys, "platform", platform),
            patch.object(process_tree, "_InterruptDeferral", return_value=nullcontext()),
            patch.object(process_tree.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(process_tree.time, "sleep", side_effect=AssertionError("no sleep")),
            patch.object(process_tree.os, "killpg", side_effect=signal_group, create=True),
            patch.object(process_tree.signal, "SIGKILL", 9, create=True),
            patch.object(process_tree, "_darwin_group_snapshot_before", side_effect=proof),
            patch.object(process_tree, "_posix_group_has_active_members", side_effect=membership),
            patch.object(process_tree.windows_process, "terminate_job", return_value="controlled job failure"),
            patch.object(process_tree.subprocess, "Popen", side_effect=AssertionError("no launch")),
            patch.object(process_tree.darwin_process, "_libproc", side_effect=AssertionError("no native")),
        ):
            error = process_tree._finish_interrupted_cleanup(Launcher(), 1, state)
        self.assertEqual(state.deadline, 1.0)
        return error, calls, state

    def test_confirmed_request_and_failures_survive_interrupted_phases(self):
        cases = (
            ("syscall", "UNKNOWN", "darwin", None, 2),
            ("proof", "UNKNOWN", "darwin", None, 1),
            (None, "UNKNOWN", "darwin", "unknown", 1),
            ("wait", "UNKNOWN", "darwin", "unknown", 1),
            ("wait", "ACTIVE", "darwin", "active", 1),
            ("postreap", "UNKNOWN", "darwin", "unknown", 1),
            ("wait", "UNKNOWN", "linux", "controlled EPERM", 1),
            ("wait", "UNKNOWN", "win32", "controlled job failure", 0),
        )
        for phase, observed, platform, failure, expected_signals in cases:
            with self.subTest(phase=phase, observed=observed, platform=platform):
                error, calls, state = self.exercise(phase, observed, platform)
                if failure is None:
                    self.assertIsNone(error)
                else:
                    self.assertIsNotNone(error)
                    self.assertIn(failure, error)
                self.assertEqual(calls["signal"], expected_signals)
                if phase == "proof":
                    self.assertEqual(calls["proof"], 2)
                self.assertTrue(state.termination_issued)
                self.assertTrue(state.launcher_reaped)

    def test_deadline_interrupt_keeps_the_confirmed_failure_without_another_request(self):
        error, calls, state = self.exercise("proof_deadline")
        self.assertIn("controlled EPERM", error)
        self.assertIn("bounded deadline (1 interruptions)", error)
        self.assertEqual(calls["signal"], 1)
        self.assertEqual(calls["proof"], 1)
        self.assertFalse(state.launcher_reaped)
        self.assertEqual(state.failure, error)
        self.assertIsNone(state.pending_permission)


class _GatedStream:
    """A pipe whose write blocks until released, then fails or completes."""

    def __init__(self, failure: BaseException | None = None) -> None:
        self.release = threading.Event()
        self.failure = failure
        self.closed = False

    def write(self, payload: bytes) -> None:
        self.release.wait(WAIT_SECONDS)
        if self.failure is not None:
            raise self.failure

    def close(self) -> None:
        self.closed = True


class _ReleasingThread(threading.Thread):
    """Releases the gated write only when the caller joins the writer."""

    def __init__(self, release: threading.Event, **options) -> None:
        super().__init__(**options)
        self._release = release

    def join(self, timeout: float | None = None) -> None:
        self._release.set()
        super().join(timeout)


class InputWriterTests(unittest.TestCase):
    """Delivery outcome is collected from the writer, never guessed."""

    def writer(self, stream: _GatedStream) -> process_tree._InputWriter:
        self.addCleanup(stream.release.set)
        writer = process_tree._InputWriter(stream, b"payload")
        writer._thread = _ReleasingThread(
            stream.release, target=writer._write, daemon=True
        )
        writer.start()
        return writer

    def test_finish_waits_for_a_writer_still_delivering(self):
        stream = _GatedStream()

        outcome = self.writer(stream).finish(time.monotonic() + WAIT_SECONDS)

        self.assertEqual(outcome, (None, None))
        self.assertTrue(stream.closed)

    def test_finish_returns_the_write_failure(self):
        failure = OSError(errno.EIO, "device failure")
        stream = _GatedStream(failure)

        error, report = self.writer(stream).finish(time.monotonic() + WAIT_SECONDS)

        self.assertIs(error, failure)
        self.assertIsNone(report)

    def test_closed_reader_is_not_a_delivery_failure(self):
        for failure in (BrokenPipeError(), OSError(errno.EINVAL, "closed pipe")):
            with self.subTest(failure=type(failure).__name__, errno=failure.errno):
                stream = _GatedStream(failure)

                outcome = self.writer(stream).finish(
                    time.monotonic() + WAIT_SECONDS
                )

                self.assertEqual(outcome, (None, None))

    def test_finish_reports_a_writer_that_exceeds_the_deadline(self):
        stream = _GatedStream()
        writer = process_tree._InputWriter(stream, b"payload")
        self.addCleanup(stream.release.set)
        writer.start()

        error, report = writer.finish(time.monotonic())

        self.assertIsNone(error)
        self.assertEqual(
            report, "standard-input writer exceeded the cleanup deadline"
        )

    def test_run_raises_the_input_delivery_failure(self):
        failure = OSError(errno.EIO, "device failure")

        class Launcher:
            pid = 2_147_483_000
            returncode = None

            def __init__(self) -> None:
                self.stdin = _GatedStream(failure)
                self.stdin.release.set()

            def kill(self):
                self.returncode = -9

            def wait(self, timeout):
                self.returncode = -9
                return self.returncode

        with (
            patch.object(process_tree.sys, "platform", "linux"),
            patch.object(process_tree.subprocess, "Popen", return_value=Launcher()),
            patch.object(process_tree, "_read_posix_status", return_value=0),
            patch.object(process_tree.os, "killpg", create=True),
            patch.object(process_tree.signal, "SIGKILL", 9, create=True),
            patch.object(
                process_tree, "_posix_group_has_active_members", return_value=False
            ),
        ):
            with self.assertRaises(OSError) as raised:
                process_tree.run(["command"], input=b"payload", timeout=5)

        self.assertIs(raised.exception, failure)


if __name__ == "__main__":
    unittest.main()
