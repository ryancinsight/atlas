"""Verify cleanup retry scope and standard-input delivery reporting."""

from __future__ import annotations

import errno
import pathlib
import sys
import threading
import time
import unittest
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import process_tree  # noqa: E402

WAIT_SECONDS = 60
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
            with self.assertRaises(RuntimeError) as raised:
                process_tree.run(["command"], timeout=5)

        self.assertIs(raised.exception, defect)
        self.assertIsInstance(raised.exception.__context__, KeyboardInterrupt)


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
