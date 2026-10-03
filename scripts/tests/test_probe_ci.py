"""Measurements of the process-tree paths on one host class (probe, not committed)."""

from __future__ import annotations

import os
import pathlib
import socket
import statistics
import subprocess
import sys
import threading
import time

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import process_tree  # noqa: E402

NEVER = "import threading; threading.Event().wait()"
CONNECT_THEN_WAIT = (
    "import socket, sys, threading; "
    "socket.create_connection(('127.0.0.1', int(sys.argv[1]))).close(); "
    "threading.Event().wait()"
)
TREE = (
    "import subprocess, sys; "
    "subprocess.Popen([sys.executable, '-I', '-c', sys.argv[1]]); "
    "subprocess.run([sys.executable, '-I', '-c', sys.argv[1]])"
)


def stats(label: str, values: list[float]) -> str:
    values = sorted(values)
    return (
        f"{label}: n={len(values)} min={values[0]:.4f} med={statistics.median(values):.4f} "
        f"p90={values[int(0.9 * (len(values) - 1))]:.4f} max={values[-1]:.4f}"
    )


def interpreter_start(n: int) -> list[float]:
    out = []
    for _ in range(n):
        t = time.monotonic()
        subprocess.run([sys.executable, "-I", "-c", "pass"], check=True)
        out.append(time.monotonic() - t)
    return out


def start_chain(n: int, depth: int) -> list[float]:
    code = (
        "import subprocess,sys; d=int(sys.argv[1]); "
        "d>1 and subprocess.run([sys.executable,'-I','-c',sys.argv[2],str(d-1),sys.argv[2]])"
    )
    out = []
    for _ in range(n):
        t = time.monotonic()
        subprocess.run([sys.executable, "-I", "-c", code, str(depth), code], check=True)
        out.append(time.monotonic() - t)
    return out


def run_pass(n: int) -> list[float]:
    out = []
    for _ in range(n):
        t = time.monotonic()
        process_tree.run([sys.executable, "-I", "-c", "pass"], timeout=60)
        out.append(time.monotonic() - t)
    return out


def event_wake(n: int, wait: float) -> list[float]:
    out = []
    for _ in range(n):
        event = threading.Event()
        t = time.monotonic()
        event.wait(wait)
        out.append(time.monotonic() - t - wait)
    return out


def select_wake(n: int, wait: float) -> list[float]:
    import selectors

    out = []
    reader, writer = (socket.socketpair() if os.name == "nt" else (None, None))
    if reader is None:
        read_fd, write_fd = os.pipe()
        source = read_fd
    else:
        source = reader
    with selectors.DefaultSelector() as selector:
        selector.register(source, selectors.EVENT_READ)
        for _ in range(n):
            t = time.monotonic()
            selector.select(wait)
            out.append(time.monotonic() - t - wait)
    return out


def cleanup(n: int, hold: float) -> list[float]:
    out = []
    for _ in range(n):
        t = time.monotonic()
        try:
            process_tree.run([sys.executable, "-I", "-c", TREE, NEVER], timeout=hold)
        except process_tree.ProcessTreeTimeout:
            pass
        out.append(time.monotonic() - t - hold)
    return out


def group_scan(n: int) -> list[float]:
    out = []
    for _ in range(n):
        t = time.monotonic()
        process_tree._posix_group_has_active_members(2_147_483_000)
        out.append(time.monotonic() - t)
    return out


def supervisor_lateness(n: int, deadline_in: float) -> list[float]:
    """Death time of a real supervisor past its deadline, gated on command readiness."""
    out = []
    for _ in range(n):
        listener = socket.create_server(("127.0.0.1", 0))
        listener.settimeout(30)
        status_read, status_write = os.pipe()
        guard_read, guard_write = os.pipe()
        deadline = time.monotonic() + deadline_in
        command = process_tree._posix_launch_command(
            status_write,
            guard_read,
            "0",
            deadline,
            [sys.executable, "-I", "-c", CONNECT_THEN_WAIT, str(listener.getsockname()[1])],
        )
        supervisor = subprocess.Popen(
            command,
            pass_fds=(status_write, guard_read),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.close(status_write)
        os.close(guard_read)
        try:
            listener.accept()[0].close()
            ready = time.monotonic()
            supervisor.wait(deadline_in + 30)
            died = time.monotonic()
            if ready < deadline:
                out.append(died - deadline)
            else:
                out.append(float("nan"))
        finally:
            try:
                os.killpg(supervisor.pid, 9)
            except ProcessLookupError:
                pass
            supervisor.wait()
            os.close(status_read)
            os.close(guard_write)
            listener.close()
    return [v for v in out if v == v]


def report(quick: bool = False) -> str:
    n = 10 if quick else 40
    lines = [
        f"host: {sys.platform} cpus={os.cpu_count()} "
        f"load={os.getloadavg() if hasattr(os, 'getloadavg') else 'n/a'}",
        stats("interpreter start (-I -c pass)", interpreter_start(n)),
        stats("3-start chain", start_chain(n, 3)),
        stats("5-start chain", start_chain(n, 5)),
        stats("run(pass) = supervisor/root + command", run_pass(n)),
        stats("Event.wait(0.05) overshoot", event_wake(100, 0.05)),
        stats("select(0.1) overshoot", select_wake(30, 0.1)),
        stats("cleanup (3-process tree) after hold 1.0", cleanup(max(10, n // 2), 1.0)),
    ]
    if os.name == "posix":
        lines.append(stats("group scan", group_scan(100)))
        lines.append(
            stats("supervisor death - deadline (ready first)", supervisor_lateness(10 if not quick else 3, 2.0))
        )
    return "\n".join(lines)


def loaded_report() -> str:
    """The same measurements with two busy processes per core, as the Windows runs had."""
    busy = [
        subprocess.Popen([sys.executable, "-I", "-c", "while True: pass"])
        for _ in range(2 * (os.cpu_count() or 1))
    ]
    try:
        return "LOADED (2 busy processes per core)" + chr(10) + report()
    finally:
        for process in busy:
            process.kill()
        for process in busy:
            process.wait()


if __name__ == "__main__":
    print(report(quick="--quick" in sys.argv))



import unittest  # noqa: E402


class ProbeTests(unittest.TestCase):
    def test_probe_reports_measurements(self):
        self.fail("PROBE" + chr(10) + report() + chr(10) + loaded_report())
