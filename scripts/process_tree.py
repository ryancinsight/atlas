"""Run one command with bounded ownership of its process tree.

Ownership is membership in a kernel container, not parentage:

* Windows: every descendant belongs to a kill-on-close Job Object that permits
  no breakaway, so the tree is complete, and the job handle closing with a
  hard-killed caller retires it. The job exists before the root does. The root
  is created suspended and belongs to no job until ``AssignProcessToJobObject``
  returns, so a caller hard-killed after ``CreateProcessW`` returns inside
  ``subprocess.Popen`` and before that call returns leaves the suspended root
  running. Only the rest of ``Popen`` after the creation call, the entry of the
  launch block and the assignment call run in that window.
* POSIX: every descendant belongs to the supervisor's process group, retired by
  ``killpg``. The supervisor bounds that group itself, whether or not the caller
  survives, and the two cases differ in when it acts. A dead caller (killed by
  any signal) closes the pipe the caller holds, and the supervisor retires the
  group at once, whatever the deadline. A caller that is alive but stalled past
  the deadline is retired at the deadline: the caller passes the supervisor one
  absolute ``time.monotonic()`` deadline, the same value its own wait uses, so
  the two sides cannot disagree about when it falls whatever the scheduling or the
  supervisor's start-up time. ``time.monotonic()`` reads ``CLOCK_MONOTONIC`` on
  Linux, which every process on the host shares (the supervisor is a child
  process of the caller); ``CrossProcessClockTests`` pins that a child reads
  the caller's clock. Before it kills the group at the deadline the supervisor
  writes a ``timeout`` status, so the caller classifies the end of the command by
  what the supervisor reported and never by comparing clocks.
  A descendant that calls ``setsid`` or ``setpgid`` leaves the group and escapes
  cleanup and the supervisor's kill alike; git's detached auto-gc is one such
  process, and the runner cannot reach it.

On both hosts a ``SIGINT`` in the main thread is held over the launch window,
from creating the root until it is owned, and then delivered, so the interrupt
retires the owned tree. Any other ``BaseException`` raised once the launch call
has returned retires the owned tree (the POSIX group or the Windows job) and,
on Windows while the root is not yet in the job, terminates the root through its
process handle. An asynchronous exception raised inside the launch call itself
leaves a Windows root running; on POSIX the caller's pipe closes as the run
unwinds, and the supervisor retires its group. A held ``SIGINT`` is dropped, with
a note on the exception, when the launch fails, and is not held off the main
thread.

On both hosts the wait for the command proceeds in slices of
``WAIT_SLICE_SECONDS``, so a caller's interrupt is observed within one slice.

The POSIX supervisor is an interpreter started in isolated mode (``-I``): the
command's working directory and ``PYTHONPATH`` are the command's to choose, and
neither may substitute a module the supervisor imports.
"""

from __future__ import annotations

import errno
import math
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import windows_process

# Longest the runner spends retiring a tree and collecting its launcher. The
# slowest cleanup measured (kill to launcher reaped, a three-process tree, 40 runs
# on Windows 11 with two busy processes per core) is 0.314 s; the recorded
# CI-to-host slowdown is 15x, and the budget doubles that: 0.314 s x 15 x 2 =
# 9.4 s, rounded up to 10 s. Reaching it is a reported cleanup failure, never a
# silent wait.
PROCESS_TREE_CLEANUP_SECONDS = 10.0
# A Windows process wait and a POSIX selector wait are each one kernel call that
# an interrupt flagged without an operating-system signal (the interpreter's
# signal flag, as ``_thread.interrupt_main`` sets it) does not end, so the
# caller's interrupt is delivered only when the call returns. Waiting in slices
# bounds that latency to one slice on both hosts; a command that exits ends its
# wait at once, so a slice adds no latency to a normal return and costs one wake
# per slice otherwise.
WAIT_SLICE_SECONDS = 0.1
# Pause between scans for a retired POSIX group's last active member. A
# ``time.sleep`` is not ended by an interrupt flagged without an operating-system
# signal either, so the pause is a tenth of the slice that bounds interrupt
# latency, and an exiting group is noticed within it.
GROUP_POLL_SECONDS = WAIT_SLICE_SECONDS / 10
# The supervisor leads the command's process group and bounds it on its own: a
# watcher thread retires the whole group, itself included, when the pipe the
# caller holds reaches end of file (the caller exited or was killed) and another
# does so at the absolute deadline the caller passed, so neither a dead caller nor
# a stalled one leaves the group running. The deadline watcher reports ``timeout``
# on the status pipe before it kills, and the first report wins: a command that
# exited first stays an exit. After the command exits the supervisor stays, still
# leading the group, until the caller retires the group or a watcher does. It
# refuses to start unless it leads its group, since ``killpg`` of a group it
# merely belongs to would kill the caller's.
_POSIX_PROCESS_SUPERVISOR = r"""
import os
import signal
import subprocess
import sys
import threading
import time

status = int(sys.argv[1])
has_input = sys.argv[2] == "1"
deadline = float(sys.argv[3])
guard = int(sys.argv[4])
command = sys.argv[5:]
retired = threading.Event()
report_lock = threading.Lock()
reported = []


def report(message):
    with report_lock:
        if reported:
            return
        reported.append(message)
    # Claim the single status before entering a potentially blocking write. A
    # launch error can be larger than the pipe buffer; the deadline watcher
    # must still be able to retire the process group while this report drains.
    os.write(status, message)
    os.close(status)


if os.getpgrp() != os.getpid():
    report(b"error:NotGroupLeader:the supervisor does not lead its process group")
    raise SystemExit(1)


def retire_group():
    try:
        os.killpg(os.getpgrp(), signal.SIGKILL)
    finally:
        retired.set()


def retire_when_caller_is_gone():
    try:
        while os.read(guard, 4096):
            pass
    except OSError:
        pass
    retire_group()


def retire_at_deadline():
    remaining = min(max(deadline - time.monotonic(), 0.0), threading.TIMEOUT_MAX)
    if not retired.wait(remaining):
        report(b"timeout")
        retire_group()


threading.Thread(
    target=retire_when_caller_is_gone, name="atlas-supervisor-caller", daemon=True
).start()
threading.Thread(
    target=retire_at_deadline, name="atlas-supervisor-deadline", daemon=True
).start()
payload = sys.stdin.buffer.read() if has_input else None
options = {"input": payload} if has_input else {}
try:
    result = subprocess.run(command, check=False, **options)
except BaseException as error:
    report(f"error:{type(error).__name__}:{error}".encode("utf-8", errors="replace"))
    raise
report(f"exit:{result.returncode}".encode("ascii"))
retired.wait()
"""


class ProcessTreeCleanupError(RuntimeError):
    """A command ran to completion but its process tree could not be retired."""

    def __init__(self, cleanup_error: str) -> None:
        super().__init__(f"process-tree cleanup failed: {cleanup_error}")
        self.cleanup_error = cleanup_error


class ProcessTreeTimeout(subprocess.TimeoutExpired):
    """A command exceeded its deadline after bounded process-tree cleanup.

    A cleanup failure is part of the message and the ``__cause__`` as well as
    ``cleanup_error``, so a consumer that only prints the exception sees it.
    """

    def __init__(
        self,
        command: Sequence[str],
        timeout: float,
        stdout: bytes,
        stderr: bytes,
        cleanup_error: str | None,
    ) -> None:
        super().__init__(command, timeout, output=stdout, stderr=stderr)
        self.cleanup_error = cleanup_error

    def __str__(self) -> str:
        message = super().__str__()
        if self.cleanup_error is None:
            return message
        return f"{message}; process-tree cleanup failed: {self.cleanup_error}"


class _InterruptDeferral:
    """Hold a main-thread ``SIGINT`` across the launch window.

    A launched root is retired only once the caller holds its handle, so an
    interrupt raised between creating the process and recording it would
    orphan it. The held signal is delivered on exit to the handler that was
    installed before, after ownership exists. Off the main thread, or where
    ``SIGINT`` is ignored or default-disposed, nothing is held.
    """

    def __init__(self) -> None:
        self._previous = None
        self._held: tuple[int, object] | None = None

    def __enter__(self) -> _InterruptDeferral:
        if threading.current_thread() is not threading.main_thread():
            return self
        previous = signal.getsignal(signal.SIGINT)
        if callable(previous):
            self._previous = previous
            signal.signal(signal.SIGINT, self._hold)
        return self

    def _hold(self, signum: int, frame: object) -> None:
        self._held = (signum, frame)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._previous is None:
            return
        signal.signal(signal.SIGINT, self._previous)
        if self._held is None:
            return
        signum, frame = self._held
        if exc is not None:
            exc.add_note("SIGINT received during process launch was superseded")
            return
        self._previous(signum, frame)


@dataclass
class _CleanupState:
    """Track destructive cleanup so interruption cannot repeat it after reap."""

    termination_issued: bool = False
    launcher_reaped: bool = False
    deadline: float | None = None


class _InputWriter:
    """Deliver bytes without placing pipe backpressure outside the deadline."""

    def __init__(self, stream, payload: bytes) -> None:
        self._stream = stream
        self._payload = payload
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._write,
            name="atlas-process-input",
            daemon=True,
        )

    def start(self) -> None:
        """Begin delivery after process-tree ownership is established."""
        self._thread.start()

    def finish(self, deadline: float) -> tuple[BaseException | None, str | None]:
        """Collect delivery within the process-tree cleanup deadline."""
        self._thread.join(max(0.0, deadline - time.monotonic()))
        if self._thread.is_alive():
            return None, "standard-input writer exceeded the cleanup deadline"
        return self._error, None

    def _write(self) -> None:
        try:
            if self._payload:
                self._stream.write(self._payload)
        except BrokenPipeError:
            pass
        except OSError as caught:
            if caught.errno != errno.EINVAL:
                self._error = caught
        finally:
            try:
                self._stream.close()
            except BrokenPipeError:
                pass
            except OSError as caught:
                if caught.errno != errno.EINVAL and self._error is None:
                    self._error = caught


def _merge_errors(*errors: str | None) -> str | None:
    messages = [error for error in errors if error]
    return "; ".join(messages) if messages else None


def _terminate_process_tree(
    process: subprocess.Popen[bytes], windows_job: int | None, state: _CleanupState
) -> str | None:
    """Stop the owned tree and bound collection of its launcher."""
    if state.deadline is None:
        state.deadline = time.monotonic() + PROCESS_TREE_CLEANUP_SECONDS
    cleanup_deadline = state.deadline
    error: str | None = None
    if not state.termination_issued:
        # The unreaped supervisor pins its POSIX process-group identity. An
        # interrupted syscall may therefore retry safely; confirmation is
        # recorded only after the destructive request returns.
        if sys.platform == "win32":
            if windows_job is None:
                error = "process was not assigned to a Windows kill-on-close job"
            else:
                remaining = max(0.0, cleanup_deadline - time.monotonic())
                error = windows_process.terminate_job(windows_job, remaining)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as caught:
                error = f"process-group kill failed: {caught}"
        state.termination_issued = True

    if error is not None and not state.launcher_reaped:
        process.kill()
    if not state.launcher_reaped:
        remaining = max(0.0, cleanup_deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()
            remaining = max(0.0, cleanup_deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                direct_error = "launcher did not exit within the process-tree cleanup budget"
                error = _merge_errors(error, direct_error)
        if process.returncode is not None:
            state.launcher_reaped = True
    if sys.platform != "win32" and state.launcher_reaped:
        while True:
            if not _posix_group_has_active_members(process.pid):
                break
            remaining = cleanup_deadline - time.monotonic()
            if remaining <= 0:
                error = _merge_errors(
                    error, "process group remained active after the cleanup budget"
                )
                break
            time.sleep(min(GROUP_POLL_SECONDS, remaining))
    return error


def _finish_interrupted_cleanup(
    process: subprocess.Popen[bytes], windows_job: int | None, state: _CleanupState
) -> str | None:
    """Retry cleanup interrupted by ``KeyboardInterrupt`` within its deadline.

    The held launcher pins tree identity, so repeating the destructive request
    is safe. Any other exception is a defect in cleanup itself and propagates
    unchanged.
    """
    interruptions = 0
    while True:
        try:
            return _terminate_process_tree(process, windows_job, state)
        except KeyboardInterrupt:
            interruptions += 1
            deadline = state.deadline
            if deadline is not None and time.monotonic() >= deadline:
                return (
                    "process-tree cleanup remained interrupted through its "
                    f"bounded deadline ({interruptions} interruptions)"
                )


def _posix_group_has_active_members(process_group: int) -> bool:
    """Report executable group members while treating Linux zombies as inactive."""
    if sys.platform.startswith("linux") and os.path.isdir("/proc"):
        with os.scandir("/proc") as entries:
            for entry in entries:
                if not entry.name.isdecimal():
                    continue
                try:
                    with open(entry.path + "/stat", encoding="utf-8") as status:
                        stat = status.read()
                except (FileNotFoundError, ProcessLookupError):
                    continue
                except OSError:
                    return True
                fields = stat[stat.rfind(")") + 1 :].split()
                if len(fields) >= 3 and fields[2].isdecimal():
                    active = fields[0] not in {"Z", "X", "x"}
                    if int(fields[2]) == process_group and active:
                        return True
        return False
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _posix_launch_command(
    status_write: int,
    guard_read: int,
    has_input: str,
    deadline: float,
    arguments: Sequence[str],
) -> list[str]:
    """Return the supervisor invocation, isolated from the command's environment.

    ``deadline`` is an absolute ``time.monotonic()`` reading, the caller's own.

    ``-c`` alone puts the working directory first on ``sys.path`` and honours
    ``PYTHONPATH`` and ``PYTHONHOME``, all of which belong to the command; a
    ``subprocess.py`` there would replace the module the supervisor runs the
    command with. Isolated mode (``-I``) closes both routes.
    """
    return [
        sys.executable,
        "-I",
        "-c",
        _POSIX_PROCESS_SUPERVISOR,
        str(status_write),
        has_input,
        f"{deadline:.6f}",
        str(guard_read),
        *arguments,
    ]


def _wait_for_exit(process: subprocess.Popen[bytes], deadline: float) -> bool:
    """Wait for ``process`` in bounded slices; ``False`` means the deadline passed."""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        try:
            process.wait(timeout=min(remaining, WAIT_SLICE_SECONDS))
        except subprocess.TimeoutExpired:
            continue
        return True


def _read_output(stream) -> bytes:
    stream.seek(0)
    return stream.read()


def _read_posix_status(status: int, deadline: float) -> int | None:
    """Return the supervised command status, or ``None`` once it timed out.

    ``deadline`` is the absolute ``time.monotonic()`` reading the supervisor was
    given. The supervisor reports ``timeout`` before it kills the group at that
    deadline, so a command that timed out is read from the status pipe whenever
    the caller gets to it; the caller's own clock ends the wait only when the
    supervisor has not reported by then. The wait is sliced like
    ``_wait_for_exit``. The command's output goes to files, so no pipe fills while
    the status pipe is waited on.
    """
    with selectors.DefaultSelector() as selector:
        selector.register(status, selectors.EVENT_READ)
        while True:
            if selector.select(0):
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            if selector.select(min(remaining, WAIT_SLICE_SECONDS)):
                break
    message = os.read(status, 4096).decode("utf-8", errors="replace")
    if message == "timeout":
        return None
    if message.startswith("exit:"):
        try:
            return int(message.removeprefix("exit:"))
        except ValueError as error:
            raise RuntimeError(f"invalid process supervisor status: {message!r}") from error
    if message.startswith("error:"):
        raise RuntimeError(f"process supervisor could not launch command: {message[6:]}")
    raise RuntimeError(f"process supervisor returned invalid status: {message!r}")


def run(
    command: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    input: bytes | None = None,
    timeout: float,
) -> subprocess.CompletedProcess[bytes]:
    """Run ``command`` and retire its owned process tree within finite bounds."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("process timeout must be finite and greater than zero")
    arguments = list(command)
    deadline = time.monotonic() + timeout
    job_handle: int | None = None
    windows_job: int | None = None
    process: subprocess.Popen[bytes] | None = None
    command_returncode: int | None = None
    status_read: int | None = None
    status_write: int | None = None
    guard_read: int | None = None
    guard_write: int | None = None
    timed_out = False
    cleanup_error: str | None = None
    input_error: BaseException | None = None
    input_writer: _InputWriter | None = None
    caught_error: BaseException | None = None
    cleanup_state = _CleanupState()
    with tempfile.TemporaryFile(mode="w+b") as stdout, tempfile.TemporaryFile(
        mode="w+b"
    ) as stderr:
        has_input = "1" if input is not None else "0"
        if sys.platform == "win32":
            launch_command = arguments
            process_options = {
                "creationflags": (
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    | windows_process.CREATE_SUSPENDED
                ),
                "stdin": subprocess.PIPE if input is not None else None,
            }
        else:
            status_read, status_write = os.pipe()
            guard_read, guard_write = os.pipe()
            launch_command = _posix_launch_command(
                status_write,
                guard_read,
                has_input,
                deadline,
                arguments,
            )
            process_options = {
                "pass_fds": (status_write, guard_read),
                "start_new_session": True,
                "stdin": subprocess.PIPE if input is not None else None,
            }
        try:
            if sys.platform == "win32":
                try:
                    job_handle = windows_process.create_kill_job()
                except OSError as caught:
                    raise RuntimeError(
                        f"failed to establish process-tree ownership: {caught}"
                    ) from caught
            with _InterruptDeferral():
                process = subprocess.Popen(
                    launch_command,
                    cwd=cwd,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    **process_options,
                )
                if status_write is not None:
                    os.close(status_write)
                    status_write = None
                if guard_read is not None:
                    os.close(guard_read)
                    guard_read = None
                if sys.platform == "win32":
                    try:
                        windows_process.assign_process(job_handle, process)
                        windows_job = job_handle
                        windows_process.resume(process)
                    except OSError as caught:
                        raise RuntimeError(
                            f"failed to establish process-tree ownership: {caught}"
                        ) from caught
            if input is not None:
                if process.stdin is None:
                    raise RuntimeError("process-tree launcher has no input pipe")
                input_writer = _InputWriter(process.stdin, input)
                input_writer.start()
            if sys.platform != "win32":
                command_returncode = _read_posix_status(status_read, deadline)
                timed_out = command_returncode is None
            else:
                timed_out = not _wait_for_exit(process, deadline)
                if not timed_out:
                    command_returncode = process.returncode
            cleanup_error = _terminate_process_tree(process, windows_job, cleanup_state)
        except BaseException as caught:
            caught_error = caught
            if process is not None:
                cleanup_error = _finish_interrupted_cleanup(
                    process, windows_job, cleanup_state
                )
            if cleanup_error is not None:
                caught.add_note(f"process-tree cleanup failed: {cleanup_error}")
            raise
        finally:
            if input_writer is not None:
                input_deadline = cleanup_state.deadline
                if input_deadline is None:
                    input_deadline = time.monotonic() + PROCESS_TREE_CLEANUP_SECONDS
                input_error, input_cleanup_error = input_writer.finish(input_deadline)
                cleanup_error = _merge_errors(cleanup_error, input_cleanup_error)
                if input_cleanup_error is not None and caught_error is not None:
                    caught_error.add_note(
                        f"process-tree cleanup failed: {input_cleanup_error}"
                    )
            if (
                input_writer is None
                and process is not None
                and process.stdin is not None
                and not process.stdin.closed
            ):
                process.stdin.close()
            if status_write is not None:
                os.close(status_write)
            if guard_read is not None:
                os.close(guard_read)
            if status_read is not None:
                os.close(status_read)
            if guard_write is not None:
                os.close(guard_write)
            if job_handle is not None:
                close_error = windows_process.close_job(job_handle)
                cleanup_error = _merge_errors(cleanup_error, close_error)
                if close_error is not None and caught_error is not None:
                    caught_error.add_note(f"process-tree cleanup failed: {close_error}")

        captured_stdout = _read_output(stdout)
        captured_stderr = _read_output(stderr)
        if timed_out:
            raise ProcessTreeTimeout(
                arguments,
                timeout,
                captured_stdout,
                captured_stderr,
                cleanup_error,
            ) from (
                None if cleanup_error is None else ProcessTreeCleanupError(cleanup_error)
            )
        if cleanup_error is not None:
            raise ProcessTreeCleanupError(cleanup_error)
        if input_error is not None:
            raise input_error
        return subprocess.CompletedProcess(
            arguments,
            command_returncode,
            captured_stdout,
            captured_stderr,
        )
