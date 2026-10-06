"""Verify what the command's environment cannot change and what an interrupt retires."""

from __future__ import annotations

import _thread
import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import process_tree  # noqa: E402
from process_tree_support import HANG_GUARD_SECONDS, NEVER_ENDS  # noqa: E402

# Modules the POSIX supervisor imports. A planted module exits with a status no
# interpreter start-up or command produces, so a hijack is unmistakable.
SHADOWED_MODULES = ("subprocess", "signal", "selectors", "threading")
HIJACKED = 97
LONG_COMMAND = [sys.executable, "-I", "-c", NEVER_ENDS]

# The interrupt is raised once the command reports it is running, so the launch
# window is over and the runner is waiting. The command runs until killed, so
# the run ends at its deadline unless the interrupt ends it. The deadline must
# outlast the start-up that precedes the report (supervisor and command, two
# interpreter starts, at most the hang guard), or the run ends in a timeout
# instead of the interrupt. An observed interrupt costs one wait slice plus tree
# cleanup, at most the cleanup budget; a deadline-only observation takes the
# deadline less the start-up, at least half the hang guard. The bound sits
# between: half the deadline is above the first and below the second.
INTERRUPT_RUN_DEADLINE_SECONDS = HANG_GUARD_SECONDS
INTERRUPT_LATENCY_BOUND_SECONDS = INTERRUPT_RUN_DEADLINE_SECONDS / 2
REPORT_THEN_WAIT = (
    "import socket, sys, threading; "
    "socket.create_connection(('127.0.0.1', int(sys.argv[1]))).close(); "
    "threading.Event().wait()"
)


def plant_shadows(directory: pathlib.Path) -> pathlib.Path:
    directory.mkdir(parents=True, exist_ok=True)
    for module in SHADOWED_MODULES:
        (directory / f"{module}.py").write_text(
            f"raise SystemExit({HIJACKED})\n", encoding="utf-8"
        )
    return directory


class SupervisorIsolationTests(unittest.TestCase):
    """The command chooses its working directory and ``PYTHONPATH``, not the supervisor's code."""

    def setUp(self) -> None:
        self.root = pathlib.Path(
            self.enterContext(tempfile.TemporaryDirectory(prefix="atlas-isolation-"))
        )
        self.cwd = plant_shadows(self.root / "cwd")
        self.path_entry = plant_shadows(self.root / "path")
        self.environment = {**os.environ, "PYTHONPATH": str(self.path_entry)}

    def import_supervisor_modules(self, *flags: str, cwd: pathlib.Path | None):
        return subprocess.run(
            [sys.executable, *flags, "-c", "import " + ", ".join(SHADOWED_MODULES)],
            cwd=cwd,
            env=self.environment,
            capture_output=True,
            timeout=HANG_GUARD_SECONDS,
            check=False,
        ).returncode

    def test_unisolated_interpreter_is_hijacked_by_cwd_and_pythonpath(self):
        # The control: without it the isolation assertions prove nothing.
        self.assertEqual(self.import_supervisor_modules(cwd=self.cwd), HIJACKED)
        self.assertEqual(self.import_supervisor_modules(cwd=self.root), HIJACKED)

    def test_isolated_interpreter_ignores_cwd_and_pythonpath(self):
        self.assertEqual(self.import_supervisor_modules("-I", cwd=self.cwd), 0)
        self.assertEqual(self.import_supervisor_modules("-I", cwd=self.root), 0)

    def test_supervisor_is_launched_in_isolated_mode(self):
        command = process_tree._posix_launch_command(
            7, 9, "1", 1.5, ["first", "second"]
        )

        self.assertEqual(
            command,
            [
                sys.executable,
                "-I",
                "-c",
                process_tree._POSIX_PROCESS_SUPERVISOR,
                "7",
                "1",
                "1.500000",
                "9",
                "first",
                "second",
            ],
        )

    def test_command_runs_when_cwd_and_pythonpath_shadow_the_supervisors_imports(self):
        # POSIX launches a supervisor here; Windows launches the command alone.
        result = process_tree.run(
            [sys.executable, "-I", "-c", "print('ran')"],
            cwd=self.cwd,
            env=self.environment,
            timeout=HANG_GUARD_SECONDS,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"ran" + os.linesep.encode())


class InterruptTests(unittest.TestCase):
    """A caller's interrupt retires the tree and is observed promptly."""

    def setUp(self) -> None:
        previous = signal.signal(signal.SIGINT, signal.default_int_handler)
        self.addCleanup(signal.signal, signal.SIGINT, previous)
        self.launched: list[subprocess.Popen[bytes]] = []
        self.addCleanup(self.reap_survivors)

    def reap_survivors(self) -> None:
        for process in self.launched:
            if process.poll() is None:
                if os.name != "nt":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.kill()
                process.wait(timeout=process_tree.PROCESS_TREE_CLEANUP_SECONDS)

    def spy_on_launch(self, after_launch):
        real_popen = subprocess.Popen

        def launching(*arguments, **options):
            process = real_popen(*arguments, **options)
            self.launched.append(process)
            after_launch()
            return process

        return patch.object(process_tree.subprocess, "Popen", side_effect=launching)

    def test_interrupt_in_the_launch_window_does_not_orphan_the_root(self):
        with self.spy_on_launch(lambda: signal.raise_signal(signal.SIGINT)):
            with self.assertRaises(KeyboardInterrupt):
                process_tree.run(LONG_COMMAND, timeout=HANG_GUARD_SECONDS)

        self.assertEqual(len(self.launched), 1)
        self.assertIsNotNone(
            self.launched[0].poll(), "the launched root outlived the interrupted run"
        )

    @unittest.skipUnless(os.name == "nt", "a root created suspended exists only on Windows")
    def test_exception_after_the_launch_call_terminates_the_suspended_root(self):
        started = time.monotonic()
        with (
            self.spy_on_launch(lambda: None),
            patch.object(
                process_tree.windows_process,
                "assign_process",
                side_effect=KeyboardInterrupt(),
            ),
        ):
            with self.assertRaises(KeyboardInterrupt):
                process_tree.run(LONG_COMMAND, timeout=HANG_GUARD_SECONDS)

        self.assertEqual(len(self.launched), 1)
        self.assertIsNotNone(
            self.launched[0].poll(), "the suspended root outlived the failed launch"
        )
        # Termination through the handle is immediate. A root that merely died
        # inside the cleanup budget was retired by the budget, not by the handle.
        self.assertLess(
            time.monotonic() - started,
            process_tree.PROCESS_TREE_CLEANUP_SECONDS / 2,
            "the suspended root was retired only when the cleanup budget ran out",
        )

    def test_interrupt_is_observed_long_before_the_deadline(self):
        listener = socket.create_server(("127.0.0.1", 0))
        listener.settimeout(HANG_GUARD_SECONDS)
        self.addCleanup(listener.close)
        interrupted_at: list[float] = []

        def interrupt_once_running() -> None:
            try:
                listener.accept()[0].close()
            except OSError:
                return
            interrupted_at.append(time.monotonic())
            _thread.interrupt_main()

        interrupter = threading.Thread(target=interrupt_once_running, daemon=True)
        interrupter.start()
        command = [
            sys.executable,
            "-I",
            "-c",
            REPORT_THEN_WAIT,
            str(listener.getsockname()[1]),
        ]

        with self.spy_on_launch(lambda: None):
            with self.assertRaises(KeyboardInterrupt):
                process_tree.run(command, timeout=INTERRUPT_RUN_DEADLINE_SECONDS)

        observed_after = time.monotonic() - interrupted_at[0]
        self.assertLess(
            observed_after,
            INTERRUPT_LATENCY_BOUND_SECONDS,
            "the interrupt was not observed until the command deadline",
        )
        self.assertIsNotNone(self.launched[0].poll())


class _RecordingSelector:
    """Stands in for the POSIX selector: records each wait, never blocks on a pipe."""

    def __init__(self, timeouts: list[float], ready_on: int | None) -> None:
        self.timeouts = timeouts
        self.ready_on = ready_on

    def __enter__(self) -> _RecordingSelector:
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def register(self, fileobj, events) -> None:
        del fileobj, events

    def select(self, timeout: float) -> list[tuple[str, int]]:
        self.timeouts.append(timeout)
        if self.ready_on is not None and len(self.timeouts) >= self.ready_on:
            return [("status", 1)]
        time.sleep(timeout)
        return []


class WaitSliceTests(unittest.TestCase):
    """The POSIX status wait is sliced, so an interrupt waits at most one slice.

    The selector is replaced, so these run on every host. An interrupt flagged
    without an operating-system signal ends no kernel wait: it is observed when
    the wait returns, which a single wait to the deadline delays until then.
    """

    def wait_for_status(self, timeout: float, ready_on: int | None, message: bytes = b"exit:7"):
        timeouts: list[float] = []
        with (
            patch.object(
                process_tree.selectors,
                "DefaultSelector",
                lambda: _RecordingSelector(timeouts, ready_on),
            ),
            patch.object(process_tree.os, "read", return_value=message),
        ):
            status = process_tree._read_posix_status(-1, time.monotonic() + timeout)
        return status, timeouts

    def test_every_wait_is_at_most_one_slice_long(self):
        status, timeouts = self.wait_for_status(HANG_GUARD_SECONDS, ready_on=4)

        self.assertEqual(status, 7)
        self.assertEqual(len(timeouts), 4)
        self.assertLessEqual(max(timeouts), process_tree.WAIT_SLICE_SECONDS)

    def test_the_supervisors_timeout_report_is_a_timeout_whatever_the_callers_clock_says(self):
        # The supervisor kills at the deadline on its own clock, which can pass
        # while the caller is descheduled or, as under a frozen test clock, has
        # not reached it: the report decides, the clock does not.
        for timeout in (0.0, HANG_GUARD_SECONDS):
            with self.subTest(deadline_in=timeout):
                status, _ = self.wait_for_status(timeout, ready_on=1, message=b"timeout")

                self.assertIsNone(status)

    def test_end_of_file_without_a_report_is_an_invalid_status_before_and_after_the_deadline(self):
        # A supervisor killed from outside reports nothing; no clock turns that
        # into a timeout.
        for timeout in (0.0, HANG_GUARD_SECONDS):
            with self.subTest(deadline_in=timeout):
                with self.assertRaisesRegex(RuntimeError, "invalid status"):
                    self.wait_for_status(timeout, ready_on=1, message=b"")

    def test_deadline_without_status_returns_none_after_sliced_waits(self):
        timeout = 3.5 * process_tree.WAIT_SLICE_SECONDS

        status, timeouts = self.wait_for_status(timeout, ready_on=None)

        self.assertIsNone(status)
        self.assertGreaterEqual(len(timeouts), 4)
        self.assertLessEqual(max(timeouts), process_tree.WAIT_SLICE_SECONDS)
        self.assertGreaterEqual(min(timeouts), 0.0)


class _SlicedProcess:
    """Stands in for a launched process: every wait is recorded and ends by timeout."""

    def __init__(self, timeouts: list[float], exits_on: int | None) -> None:
        self.timeouts = timeouts
        self.exits_on = exits_on

    def wait(self, timeout: float) -> int:
        self.timeouts.append(timeout)
        if self.exits_on is not None and len(self.timeouts) >= self.exits_on:
            return 0
        time.sleep(timeout)
        raise subprocess.TimeoutExpired("command", timeout)


class ExitWaitSliceTests(unittest.TestCase):
    """The wait for the command's exit, which Windows uses, is sliced too.

    A Windows process wait is one kernel call that an interrupt flagged without
    an operating-system signal does not end, so a wait to the deadline delays
    that interrupt until the deadline. The process is replaced, so these run on
    every host.
    """

    def wait_for_exit(self, timeout: float, exits_on: int | None):
        timeouts: list[float] = []
        exited = process_tree._wait_for_exit(
            _SlicedProcess(timeouts, exits_on), time.monotonic() + timeout
        )
        return exited, timeouts

    def test_every_wait_is_at_most_one_slice_long(self):
        exited, timeouts = self.wait_for_exit(HANG_GUARD_SECONDS, exits_on=4)

        self.assertTrue(exited)
        self.assertEqual(len(timeouts), 4)
        self.assertLessEqual(max(timeouts), process_tree.WAIT_SLICE_SECONDS)

    def test_deadline_without_an_exit_returns_false_after_sliced_waits(self):
        exited, timeouts = self.wait_for_exit(
            3.5 * process_tree.WAIT_SLICE_SECONDS, exits_on=None
        )

        self.assertFalse(exited)
        self.assertGreaterEqual(len(timeouts), 4)
        self.assertLessEqual(max(timeouts), process_tree.WAIT_SLICE_SECONDS)
        self.assertGreater(min(timeouts), 0.0)

    def test_an_expired_deadline_waits_for_nothing(self):
        exited, timeouts = self.wait_for_exit(0.0, exits_on=None)

        self.assertFalse(exited)
        self.assertEqual(timeouts, [])


class InterruptDeferralTests(unittest.TestCase):
    """The held signal reaches the prior handler once, after the window."""

    def test_signal_is_held_inside_and_delivered_after_the_window(self):
        delivered: list[int] = []
        previous = signal.signal(
            signal.SIGINT, lambda signum, frame: delivered.append(signum)
        )
        self.addCleanup(signal.signal, signal.SIGINT, previous)

        with process_tree._InterruptDeferral():
            signal.raise_signal(signal.SIGINT)
            self.assertEqual(delivered, [])

        self.assertEqual(delivered, [signal.SIGINT])
        signal.raise_signal(signal.SIGINT)
        self.assertEqual(delivered, [signal.SIGINT, signal.SIGINT])

    def test_signal_ignored_by_the_caller_stays_ignored(self):
        previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.addCleanup(signal.signal, signal.SIGINT, previous)

        with process_tree._InterruptDeferral():
            signal.raise_signal(signal.SIGINT)

        self.assertEqual(signal.getsignal(signal.SIGINT), signal.SIG_IGN)

    def test_failure_in_the_window_is_not_replaced_by_the_held_signal(self):
        delivered: list[int] = []

        def handler(signum, frame):
            delivered.append(signum)

        previous = signal.signal(signal.SIGINT, handler)
        self.addCleanup(signal.signal, signal.SIGINT, previous)

        with self.assertRaises(OSError) as raised:
            with process_tree._InterruptDeferral():
                signal.raise_signal(signal.SIGINT)
                raise OSError("launch failed")

        self.assertEqual(
            raised.exception.__notes__,
            ["SIGINT received during process launch was superseded"],
        )
        self.assertEqual(delivered, [])
        self.assertIs(signal.getsignal(signal.SIGINT), handler)


if __name__ == "__main__":
    unittest.main()
