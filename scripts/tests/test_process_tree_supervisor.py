"""Verify the POSIX supervisor bounds its process group when the caller cannot.

The supervisor is a program, so its two watchers run here in this process on
every host with the group kill replaced by a recording stand-in. The tests that
kill or stall a real caller run on POSIX hosts only, where the supervisor exists.
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import select
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
from process_tree_support import (  # noqa: E402
    EXPIRY_HOLD_SECONDS,
    HANG_GUARD_SECONDS,
    NEVER_ENDS,
)

WATCHERS = ("atlas-supervisor-caller", "atlas-supervisor-deadline")
# Connects to the port in argv[1], reports readiness on its standard output, and
# stays alive.
HOLD = (
    "import socket, sys, threading; "
    "held = socket.create_connection(('127.0.0.1', int(sys.argv[1]))); "
    "print('ready', flush=True); "
    "threading.Event().wait()"
)
# The same, ending when the test closes its end of the connection.
HOLD_UNTIL_RELEASED = (
    "import socket, sys; "
    "socket.create_connection(('127.0.0.1', int(sys.argv[1]))).recv(1)"
)
# A command that starts a holder, waits for its readiness report, and exits
# leaving the holder running: the holder is connected before the command ends.
LEAVE_HOLDER = (
    "import subprocess, sys; "
    "child = subprocess.Popen("
    "[sys.executable, '-I', '-c', sys.argv[2], sys.argv[1]], stdout=subprocess.PIPE); "
    "child.stdout.readline()"
)
# A command that is a holder and also has a holder child.
HOLD_WITH_HOLDER = LEAVE_HOLDER + "; exec(sys.argv[2])"
# A run longer than any wait a test makes, so a retirement that arrives within
# the wait was not the deadline's.
LONG_DEADLINE_SECONDS = 2 * HANG_GUARD_SECONDS


class SupervisorWatcherTests(unittest.TestCase):
    """The supervisor's source, run in this process with a recording group kill."""

    def setUp(self) -> None:
        self.kills: list[tuple[int, int]] = []
        self.reported_at_kill: list[list[bytes]] = []
        self.namespace: dict[str, object] = {"__name__": "__main__"}
        self.killed = threading.Event()
        self.outcome: dict[str, BaseException] = {}
        self.status_read, self.status_write = os.pipe()
        self.guard_read, self.guard_write = os.pipe()
        self.released = threading.Event()
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(HANG_GUARD_SECONDS)
        self.accepted: list[socket.socket] = []
        self.guard_open = True
        self.worker: threading.Thread | None = None
        # The supervisor's process and its group, which it must lead.
        self.process = 4242
        self.group = 4242
        stack = self.enterContext(contextlib.ExitStack())
        stack.enter_context(patch.object(os, "killpg", self.killpg, create=True))
        stack.enter_context(patch.object(os, "getpid", lambda: self.process))
        stack.enter_context(patch.object(os, "getpgrp", lambda: self.group, create=True))
        stack.enter_context(patch.object(signal, "SIGKILL", 9, create=True))
        self.addCleanup(self.shut_down)

    def killpg(self, group: int, signum: int) -> None:
        # What the supervisor had reported when it killed: after the real kill
        # nothing more can be reported.
        self.reported_at_kill.append(list(self.namespace.get("reported", [])))
        self.kills.append((group, signum))
        self.killed.set()

    def close_guard(self) -> None:
        if self.guard_open:
            self.guard_open = False
            os.close(self.guard_write)

    def shut_down(self) -> None:
        """End every supervisor thread before the group kill is restored.

        A watcher still running when the stand-in is removed would call the real
        ``killpg`` on this test run's own process group.
        """
        self.close_guard()
        for connection in self.accepted:
            connection.close()
        self.listener.close()
        if self.worker is not None:
            self.worker.join(HANG_GUARD_SECONDS)
        for thread in threading.enumerate():
            if thread.name in WATCHERS:
                thread.join(HANG_GUARD_SECONDS)
        leftover = [t.name for t in threading.enumerate() if t.name in WATCHERS]
        # A supervisor that ran has closed the status write end itself.
        descriptors = [self.status_read, self.guard_read]
        if self.worker is None:
            descriptors.append(self.status_write)
        for descriptor in descriptors:
            os.close(descriptor)
        self.assertEqual(leftover, [], "a supervisor watcher outlived the test")

    def start(self, deadline_in: float, command: list[str]) -> None:
        arguments = [
            "-c",
            str(self.status_write),
            "0",
            f"{time.monotonic() + deadline_in:.6f}",
            str(self.guard_read),
            *command,
        ]
        source = compile(process_tree._POSIX_PROCESS_SUPERVISOR, "<supervisor>", "exec")

        def supervise() -> None:
            try:
                exec(source, self.namespace)
            except BaseException as error:
                self.outcome["error"] = error

        patcher = patch.object(sys, "argv", arguments)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.worker = threading.Thread(target=supervise, name="supervisor", daemon=True)
        self.worker.start()

    def read_status(self) -> bytes:
        """Read the status message; a pipe cannot be selected on every host."""
        message: list[bytes] = []
        reader = threading.Thread(
            target=lambda: message.append(os.read(self.status_read, 4096)), daemon=True
        )
        reader.start()
        reader.join(HANG_GUARD_SECONDS)
        self.assertTrue(message, "the supervisor never reported a status")
        return message[0]

    def test_caller_end_of_file_retires_the_group_without_waiting_for_the_deadline(self):
        # A deadline past what a wait accepts is clamped, not an overflow.
        self.start(1e12, [sys.executable, "-I", "-c", "pass"])
        self.assertEqual(self.read_status(), b"exit:0")
        self.assertEqual(self.kills, [], "the supervisor retired a live caller's group")
        # After its status the supervisor keeps leading its group until retired:
        # a negative wait, so it bounds only how long an early exit can hide.
        self.worker.join(EXPIRY_HOLD_SECONDS)
        self.assertTrue(self.worker.is_alive(), "the supervisor left its group unled")

        self.close_guard()

        self.assertTrue(self.killed.wait(HANG_GUARD_SECONDS))
        self.assertEqual(self.kills[0], (4242, 9))

    def test_deadline_retires_the_group_while_the_caller_is_alive(self):
        command = [
            sys.executable,
            "-I",
            "-c",
            HOLD_UNTIL_RELEASED,
            str(self.listener.getsockname()[1]),
        ]
        started = time.monotonic()
        self.start(EXPIRY_HOLD_SECONDS, command)
        self.accepted.append(self.listener.accept()[0])

        self.assertTrue(self.killed.wait(HANG_GUARD_SECONDS))

        self.assertGreaterEqual(time.monotonic() - started, EXPIRY_HOLD_SECONDS)
        self.assertEqual(self.kills[0], (4242, 9))
        self.assertTrue(self.guard_open, "the caller's pipe was still open")
        # The report comes before the kill, which ends the supervisor and with it
        # any chance to report: the caller reads the timeout from the pipe.
        self.assertEqual(self.reported_at_kill[0], [b"timeout"])
        self.assertEqual(self.read_status(), b"timeout")

    def test_an_exit_reported_first_is_not_replaced_by_the_deadline(self):
        self.start(EXPIRY_HOLD_SECONDS, [sys.executable, "-I", "-c", "pass"])
        self.assertEqual(self.read_status(), b"exit:0")

        # The caller is alive and never retires the group: the deadline does,
        # without a second report on the closed status pipe.
        self.assertTrue(self.killed.wait(HANG_GUARD_SECONDS))

        self.assertEqual(self.kills[0], (4242, 9))
        self.assertEqual(self.read_status(), b"", "a late report followed the exit")

    def test_a_deadline_already_past_retires_the_group_at_once(self):
        # The caller was descheduled past its own deadline, or the supervisor's
        # start-up took longer than the time left: no wait is negative.
        command = [
            sys.executable,
            "-I",
            "-c",
            HOLD_UNTIL_RELEASED,
            str(self.listener.getsockname()[1]),
        ]
        self.start(-HANG_GUARD_SECONDS, command)
        self.accepted.append(self.listener.accept()[0])

        self.assertEqual(self.read_status(), b"timeout")
        self.assertTrue(self.killed.wait(HANG_GUARD_SECONDS))

    def test_supervisor_refuses_to_run_when_it_does_not_lead_its_group(self):
        # killpg of a group it merely belongs to would kill the caller's.
        self.group = 4243

        self.start(1e12, [sys.executable, "-I", "-c", "pass"])

        message = self.read_status().decode("utf-8")
        self.assertTrue(message.startswith("error:NotGroupLeader:"), message)
        self.worker.join(HANG_GUARD_SECONDS)
        self.assertEqual(self.outcome["error"].code, 1)
        self.assertEqual(self.kills, [])
        self.assertEqual(
            [t.name for t in threading.enumerate() if t.name in WATCHERS],
            [],
            "a watcher started in a group the supervisor does not lead",
        )

    def test_launch_failure_is_reported_before_the_supervisor_ends(self):
        self.start(1e12, ["atlas-no-such-executable-for-the-supervisor"])

        message = self.read_status().decode("utf-8")

        self.assertTrue(message.startswith("error:FileNotFoundError:"), message)
        self.worker.join(HANG_GUARD_SECONDS)
        self.assertIsInstance(self.outcome["error"], FileNotFoundError)

    def test_blocked_status_write_does_not_hold_deadline_watcher(self):
        write_started = threading.Event()
        release_write = threading.Event()
        real_write = os.write

        def blocked_write(descriptor: int, message: bytes) -> int:
            if descriptor == self.status_write:
                write_started.set()
                release_write.wait()
            return real_write(descriptor, message)

        with patch.object(os, "write", side_effect=blocked_write):
            try:
                self.start(
                    EXPIRY_HOLD_SECONDS,
                    ["atlas-no-such-executable-for-the-supervisor"],
                )
                self.assertTrue(write_started.wait(HANG_GUARD_SECONDS))
                self.assertTrue(
                    self.killed.wait(EXPIRY_HOLD_SECONDS + HANG_GUARD_SECONDS),
                    "deadline watcher could not retire while status write was blocked",
                )
            finally:
                release_write.set()

        self.worker.join(HANG_GUARD_SECONDS)
        self.assertFalse(self.worker.is_alive(), "blocked report outlived its supervisor")


def retire_group(group: int) -> None:
    """Kill whatever still runs in ``group``, a leader's identifier."""
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass


@unittest.skipUnless(os.name == "posix", "the supervisor exists only on POSIX")
class PosixCallerDeathTests(unittest.TestCase):
    """A hard-killed caller leaves no process of its group running."""

    HELPER = (
        "import os, signal, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import process_tree\n"
        "mode, port, timeout, script, holder = sys.argv[2:7]\n"
        "class Recording(process_tree.subprocess.Popen):\n"
        "    def __init__(self, *arguments, **options):\n"
        "        super().__init__(*arguments, **options)\n"
        "        print(self.pid, flush=True)\n"
        "process_tree.subprocess.Popen = Recording\n"
        "if mode == 'die-after-status':\n"
        "    def die(*arguments):\n"
        "        os.kill(os.getpid(), signal.SIGKILL)\n"
        "    process_tree._terminate_process_tree = die\n"
        "process_tree.run(\n"
        "    [sys.executable, '-I', '-c', script, port, holder],\n"
        "    timeout=float(timeout),\n"
        ")\n"
    )

    def setUp(self) -> None:
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(HANG_GUARD_SECONDS)
        self.addCleanup(self.listener.close)
        self.held: list[socket.socket] = []
        self.addCleanup(self.release_holders)
        self.log = tempfile.TemporaryFile()
        self.addCleanup(self.log.close)

    def release_holders(self) -> None:
        for connection in self.held:
            connection.close()

    def accept_holders(self, count: int) -> None:
        for _ in range(count):
            try:
                self.held.append(self.listener.accept()[0])
            except TimeoutError:
                self.log.seek(0)
                self.fail(f"a holder never connected: {self.log.read()!r}")

    def start_helper(self, mode: str, script: str) -> subprocess.Popen[bytes]:
        helper = subprocess.Popen(
            [
                sys.executable,
                "-c",
                self.HELPER,
                str(SCRIPTS),
                mode,
                str(self.listener.getsockname()[1]),
                repr(LONG_DEADLINE_SECONDS),
                script,
                HOLD,
            ],
            stdout=subprocess.PIPE,
            stderr=self.log,
        )
        self.addCleanup(helper.stdout.close)
        self.addCleanup(helper.wait, HANG_GUARD_SECONDS)
        self.addCleanup(helper.kill)
        # The helper reports its supervisor's pid, which is the group's leader
        # and its identifier. The group is retired on every exit from the test,
        # so a defect that leaves it running cannot outlive the failure.
        ready, _, _ = select.select([helper.stdout], [], [], HANG_GUARD_SECONDS)
        self.assertTrue(ready, "the helper never launched")
        self.addCleanup(retire_group, int(os.read(helper.stdout.fileno(), 4096)))
        return helper

    def assert_holders_gone(self) -> None:
        """Every holder's connection reaches end of file: its process is dead.

        The helper's run has a deadline of twice this wait, so a group retired
        inside the wait was retired by the supervisor's caller watcher.
        """
        for connection in self.held:
            connection.settimeout(HANG_GUARD_SECONDS)
            try:
                data = connection.recv(1)
            except ConnectionResetError:
                continue
            except TimeoutError:
                self.fail("a group member outlived its hard-killed caller")
            self.assertEqual(data, b"")

    def test_group_is_retired_when_the_caller_is_killed_during_the_wait(self):
        helper = self.start_helper("wait", HOLD_WITH_HOLDER)
        self.accept_holders(2)

        helper.kill()

        self.assertEqual(helper.wait(HANG_GUARD_SECONDS), -signal.SIGKILL)
        self.assert_holders_gone()

    def test_group_is_retired_when_the_caller_is_killed_after_the_status_write(self):
        helper = self.start_helper("die-after-status", LEAVE_HOLDER)
        self.accept_holders(1)

        # The helper kills itself on reading the command's status, before its
        # own group kill: the window the supervisor must not wait out.
        self.assertEqual(helper.wait(HANG_GUARD_SECONDS), -signal.SIGKILL)
        self.assert_holders_gone()


@unittest.skipUnless(os.name == "posix", "the supervisor exists only on POSIX")
class PosixSupervisorProcessTests(unittest.TestCase):
    """The supervisor process, launched as the runner launches it."""

    def launch(
        self,
        deadline_in: float,
        command: list[str],
        stdout=subprocess.DEVNULL,
        new_session: bool = True,
    ) -> subprocess.Popen[bytes]:
        status_read, status_write = os.pipe()
        guard_read, self.guard_write = os.pipe()
        self.status_read = status_read
        self.guard_open = True
        launch_command = process_tree._posix_launch_command(
            status_write, guard_read, "0", time.monotonic() + deadline_in, command
        )
        supervisor = subprocess.Popen(
            launch_command,
            pass_fds=(status_write, guard_read),
            start_new_session=new_session,
            stdout=stdout,
            stderr=subprocess.DEVNULL,
        )
        os.close(status_write)
        os.close(guard_read)
        self.addCleanup(os.close, status_read)
        self.addCleanup(self.close_guard)
        self.addCleanup(self.retire, supervisor)
        return supervisor

    def close_guard(self) -> None:
        if self.guard_open:
            self.guard_open = False
            os.close(self.guard_write)

    @staticmethod
    def retire(supervisor: subprocess.Popen[bytes]) -> None:
        """Kill the supervisor's group even after the supervisor has exited.

        Members outlive their leader, and that is the case a leftover group
        occurs in, so the kill does not depend on the leader being alive.
        """
        retire_group(supervisor.pid)
        supervisor.wait(timeout=HANG_GUARD_SECONDS)

    def test_supervisor_ends_when_the_caller_vanishes_after_its_status_write(self):
        supervisor = self.launch(
            LONG_DEADLINE_SECONDS, [sys.executable, "-I", "-c", "pass"]
        )
        ready, _, _ = select.select([self.status_read], [], [], HANG_GUARD_SECONDS)
        self.assertTrue(ready, "the supervisor never reported a status")
        self.assertEqual(os.read(self.status_read, 4096), b"exit:0")
        self.assertIsNone(
            supervisor.poll(), "the supervisor left before its caller retired the group"
        )

        self.close_guard()

        self.assertEqual(supervisor.wait(HANG_GUARD_SECONDS), -signal.SIGKILL)

    def test_supervisor_ends_at_its_deadline_while_the_caller_is_alive(self):
        started = time.monotonic()
        # The command inherits the standard output pipe, so the pipe reaches end
        # of file only when the supervisor and every member of its group are
        # gone, whenever the command managed to start.
        supervisor = self.launch(
            EXPIRY_HOLD_SECONDS,
            [sys.executable, "-I", "-c", NEVER_ENDS],
            stdout=subprocess.PIPE,
        )
        self.addCleanup(supervisor.stdout.close)

        self.assertEqual(supervisor.wait(HANG_GUARD_SECONDS), -signal.SIGKILL)

        self.assertGreaterEqual(time.monotonic() - started, EXPIRY_HOLD_SECONDS)
        self.assertTrue(self.guard_open, "the caller's pipe was still open")
        self.assertEqual(
            os.read(self.status_read, 4096),
            b"timeout",
            "the supervisor was killed before it reported the timeout",
        )
        ready, _, _ = select.select([supervisor.stdout], [], [], HANG_GUARD_SECONDS)
        self.assertTrue(ready, "a group member outlived the supervisor's deadline")
        self.assertEqual(supervisor.stdout.read(), b"")

    def test_supervisor_refuses_a_group_it_does_not_lead(self):
        # Launched without its own session, the supervisor is a member of this
        # process's group: killing that group would kill the test run.
        supervisor = self.launch(
            LONG_DEADLINE_SECONDS,
            [sys.executable, "-I", "-c", NEVER_ENDS],
            new_session=False,
        )

        self.assertEqual(supervisor.wait(HANG_GUARD_SECONDS), 1)

        message = os.read(self.status_read, 4096).decode("utf-8")
        self.assertTrue(message.startswith("error:NotGroupLeader:"), message)


@unittest.skipUnless(os.name == "posix", "the supervisor exists only on POSIX")
class PosixStalledCallerTests(unittest.TestCase):
    """``run`` with a caller that is alive and never reads, retires nothing itself.

    The caller is stalled inside its wait, as a descheduled or blocked caller
    is, so only the supervisor's deadline, built from the one ``run`` passes it,
    can end the group.
    """

    def test_group_is_retired_at_the_deadline_run_passed_the_supervisor(self):
        launched: list[float] = []
        supervisors: list[subprocess.Popen[bytes]] = []
        stalled = threading.Event()
        released = threading.Event()
        outcome: dict[str, BaseException] = {}
        real_launch = process_tree._posix_launch_command
        real_read = process_tree._read_posix_status

        def record_launch(status_write, guard_read, has_input, deadline, arguments):
            launched.append(deadline)
            return real_launch(status_write, guard_read, has_input, deadline, arguments)

        class Recording(subprocess.Popen):
            def __init__(self, *arguments, **options):
                super().__init__(*arguments, **options)
                supervisors.append(self)

        def stalled_read(status, deadline):
            stalled.set()
            released.wait(HANG_GUARD_SECONDS)
            return real_read(status, deadline)

        def run() -> None:
            try:
                process_tree.run(
                    [sys.executable, "-I", "-c", NEVER_ENDS],
                    timeout=EXPIRY_HOLD_SECONDS,
                )
            except BaseException as error:
                outcome["error"] = error

        before = time.monotonic()
        with (
            patch.object(process_tree, "_posix_launch_command", record_launch),
            patch.object(process_tree, "_read_posix_status", stalled_read),
            patch.object(process_tree.subprocess, "Popen", Recording),
        ):
            worker = threading.Thread(target=run, daemon=True)
            worker.start()
            self.addCleanup(worker.join, HANG_GUARD_SECONDS)
            self.addCleanup(released.set)
            self.assertTrue(
                stalled.wait(HANG_GUARD_SECONDS), "the run never reached its wait"
            )
            self.addCleanup(lambda: retire_group(supervisors[0].pid))
            stalled_at = time.monotonic()

            # The deadline is the caller's own absolute reading: the time it
            # started plus the timeout, never the timeout alone or a duration.
            self.assertEqual(len(launched), 1)
            self.assertGreaterEqual(launched[0], before + EXPIRY_HOLD_SECONDS)
            self.assertLessEqual(launched[0], stalled_at + EXPIRY_HOLD_SECONDS)

            # The supervisor ends at the deadline, or when its own start-up
            # ends if that is later: at most one interpreter start, which is at
            # most the hang guard, past it.
            status = supervisors[0].wait(EXPIRY_HOLD_SECONDS + HANG_GUARD_SECONDS)
            ended = time.monotonic()
            self.assertEqual(status, -signal.SIGKILL)
            self.assertGreaterEqual(ended, launched[0])
            self.assertTrue(worker.is_alive(), "the caller was not stalled")

            # Released, the caller finds the supervisor's report and classifies
            # the end of the command by it.
            released.set()
            worker.join(HANG_GUARD_SECONDS)
            self.assertFalse(worker.is_alive())

        self.assertIsInstance(outcome.get("error"), process_tree.ProcessTreeTimeout)


class CrossProcessClockTests(unittest.TestCase):
    """The deadline is one reading of ``time.monotonic``, valid in the supervisor."""

    @unittest.skipUnless(sys.platform.startswith("linux"), "names the Linux clock")
    def test_the_clock_is_the_system_wide_monotonic_clock_on_linux(self):
        self.assertEqual(
            time.get_clock_info("monotonic").implementation,
            "clock_gettime(CLOCK_MONOTONIC)",
        )

    def test_a_child_process_reads_the_callers_monotonic_clock(self):
        before = time.monotonic()
        completed = subprocess.run(
            [sys.executable, "-I", "-c", "import time; print(repr(time.monotonic()))"],
            capture_output=True,
            text=True,
            check=True,
            timeout=HANG_GUARD_SECONDS,
        )
        after = time.monotonic()

        self.assertLessEqual(before, float(completed.stdout))
        self.assertLessEqual(float(completed.stdout), after)


if __name__ == "__main__":
    unittest.main()
