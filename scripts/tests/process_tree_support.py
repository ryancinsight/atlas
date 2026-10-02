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
