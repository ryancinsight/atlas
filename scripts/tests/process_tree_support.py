"""Shared fixtures for the process-tree tests."""

from __future__ import annotations

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
# failure instead of a hang. The longest completing chain any test runs is four
# sequential interpreter starts (the descendant chain reporting readiness; the
# supervisor, command, parent and child chains are no longer). One interpreter
# start takes 0.34-0.57 s idle on this host, and one start took 2.27 s under
# concurrent builds. CI runs on Linux and records no per-test timing, so its
# factor is the recorded CI-to-host slowdown for compile-bound work, 15x,
# applied to the high end of each: a four-start chain at the idle high end,
# 4 x 0.57 s x 15 = 34.2 s, and a single start under load, 2.27 s x 15 = 34.1 s.
# The guard is 35 s, above both.
HANG_GUARD_SECONDS = 35.0

# Deadline of a run whose command never ends and whose clock starts when the
# descendant reports readiness (``budget_from_readiness``). The deadline always
# fires, and everything the test then asserts was produced before the readiness
# report, so the value sets only how long the live tree is held: no machine speed
# changes the outcome. One second is that hold.
EXPIRY_HOLD_SECONDS = 1.0


def budget_from_readiness(listener: socket.socket):
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
