"""Shared fixtures for the process-tree tests."""

from __future__ import annotations

import contextlib
import pathlib
import socket
import subprocess
import sys
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import process_tree  # noqa: E402


# Hang guard, not a measurement: the longest a test lets an event it is waiting
# for stay pending before failing, and the deadline of every command that must
# run to completion, so a defect that stops the event ends the test as a named
# failure instead of a hang. The longest completing chain on each host:
#
# * Windows runs five sequential interpreter starts: the helper the hard-killed
#   caller tests run ``process_tree.run`` in, then the root, middle, grandchild
#   and detached nodes of the tree (each launches the next and waits for its
#   readiness). Measured on this host (Windows 11, Python 3.13, 24 logical
#   cores, 20 runs of a five-deep chain): 0.589 s at most idle, 2.108 s at most
#   with two busy processes per core.
# * POSIX runs three: the helper, the supervisor and the command, below the
#   Windows chain.
#
# No Windows verification job exists, so the 15x CI-to-host slowdown recorded for
# compile-bound work is applied as the safety multiple on the loaded chain, the
# larger of the two: 2.108 s x 15 = 31.6 s, rounded up to 32 s. The POSIX chain
# at that multiple, 3 x 0.118 s idle per start x 15 = 5.3 s, is below it.
HANG_GUARD_SECONDS = 32.0

# Deadline of a run whose command never ends, so the deadline always fires and
# every assertion concerns what follows it, never how long the command took.
# Where the clock starts at the descendant's readiness report
# (``budget_from_readiness``), everything the test asserts was produced before
# that report, so the value sets only how long the live tree is held: no machine
# speed changes the outcome. One second is that hold.
EXPIRY_HOLD_SECONDS = 1.0

# A command that never ends and holds no resources.
NEVER_ENDS = "import threading; threading.Event().wait()"


@contextlib.contextmanager
def budget_from_readiness(listener: socket.socket):
    """Start the timeout clock only after the descendant is live.

    The caller's clock is frozen until a descendant reports readiness, so the
    deadline the caller waits for begins at the report. The supervisor reads the
    real clock and cannot be told to start counting later, so it is given its
    deadline a hang guard past the caller's: its own deadline is the backstop for
    a stalled caller, which these tests do not exercise
    (``PosixStalledCallerTests`` and ``SupervisorWatcherTests`` do), and it would
    otherwise end the tree before the descendant is live.
    """
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

    def with_backstop_deadline(launch):
        def launched(status_write, guard_read, has_input, deadline, arguments):
            return launch(
                status_write,
                guard_read,
                has_input,
                deadline + HANG_GUARD_SECONDS,
                arguments,
            )

        return launched

    with contextlib.ExitStack() as patches:
        patches.enter_context(patch.object(process_tree.time, "monotonic", clock))
        patches.enter_context(
            patch.object(
                process_tree.subprocess.Popen,
                "wait",
                after_ready(subprocess.Popen.wait),
            )
        )
        patches.enter_context(
            patch.object(
                process_tree,
                "_read_posix_status",
                after_ready(process_tree._read_posix_status),
            )
        )
        patches.enter_context(
            patch.object(
                process_tree,
                "_posix_launch_command",
                with_backstop_deadline(process_tree._posix_launch_command),
            )
        )
        yield
