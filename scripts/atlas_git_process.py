"""Bounded subprocess execution with process-group and Windows Job cleanup."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from atlas_build_process_capture import (
    CAPTURE_POLL_SECONDS,
    DEFAULT_CAPTURE_LIMIT_BYTES,
    BoundedOutputCapture,
    CaptureLimitExceeded,
)
from atlas_build_process_group import (
    linux_process_group_has_live_members,
    terminate_process_group,
    wait_for_process_exit_without_reaping,
)

CLEANUP_TIMEOUT_SECONDS = 5
PROCESS_GROUP_PROBE_COUNT = 100
PROCESS_GROUP_POLL_INTERVAL_SECONDS = CLEANUP_TIMEOUT_SECONDS / PROCESS_GROUP_PROBE_COUNT


class GitProcessError(RuntimeError):
    """A process could not launch, exceeded its deadline, or could not be stopped."""

    def __init__(
        self,
        message: str,
        *,
        timed_out: bool = False,
        output_limit_exceeded: bool = False,
    ) -> None:
        super().__init__(message)
        self.timed_out = timed_out
        self.output_limit_exceeded = output_limit_exceeded


@dataclass(frozen=True)
class GitProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes


def _terminate_process_boundary(
    proc: subprocess.Popen[bytes],
    windows_job: int | None = None,
    *,
    command_timed_out: bool = False,
) -> None:
    if os.name == "nt":
        if windows_job is None:
            proc.kill()
        else:
            from atlas_build_process_windows import terminate_job, wait_empty

            terminate_job(windows_job)
            if not wait_empty(windows_job, CLEANUP_TIMEOUT_SECONDS * 1000):
                raise GitProcessError(
                    "process job did not terminate before cleanup deadline",
                    timed_out=command_timed_out,
                )
    else:
        if not sys.platform.startswith("linux"):
            raise GitProcessError(
                "bounded descendant cleanup is supported only on Windows and Linux"
            )
        try:
            terminate_process_group(
                proc,
                CLEANUP_TIMEOUT_SECONDS,
                PROCESS_GROUP_POLL_INTERVAL_SECONDS,
            )
        except OSError as exc:
            raise GitProcessError(
                str(exc), timed_out=command_timed_out
            ) from exc
        return
    try:
        proc.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        raise GitProcessError(
            "timed-out process job did not terminate", timed_out=True
        ) from exc


def _wait_for_windows_process(
    proc: subprocess.Popen[bytes],
    timeout: int,
    capture: BoundedOutputCapture | None,
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        if capture is not None:
            capture.check()
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            raise subprocess.TimeoutExpired(proc.args, timeout)
        try:
            proc.wait(timeout=min(CAPTURE_POLL_SECONDS, remaining))
            if capture is not None:
                capture.check()
            return
        except subprocess.TimeoutExpired:
            continue


def _stop_after_failure(
    proc: subprocess.Popen[bytes] | None,
    windows_job: int | None,
    *,
    command_timed_out: bool,
) -> BaseException | None:
    if proc is None:
        return None
    if os.name != "nt" and proc.returncode is not None:
        return None
    try:
        _terminate_process_boundary(
            proc, windows_job, command_timed_out=command_timed_out
        )
    except (GitProcessError, OSError) as exc:
        return exc
    return None


def _close_process_job(windows_job: int | None) -> OSError | None:
    if windows_job is None:
        return None
    from atlas_build_process_windows import close_job

    try:
        close_job(windows_job)
    except OSError as exc:
        return exc
    return None


def _close_stdin(stream: object | None) -> OSError | None:
    if stream is None:
        return None
    try:
        stream.close()
    except OSError as exc:
        return exc
    return None


def _finish_capture_after_failure(
    capture: BoundedOutputCapture | None,
    proc: subprocess.Popen[bytes] | None,
) -> OSError | None:
    if capture is not None:
        try:
            capture.finish(CLEANUP_TIMEOUT_SECONDS, tolerate_limit=True)
        except OSError as exc:
            return exc
        return None
    if proc is None:
        return None
    failure: OSError | None = None
    for stream in (proc.stdout, proc.stderr):
        if stream is None:
            continue
        try:
            stream.close()
        except OSError as exc:
            failure = failure or exc
    return failure


def _cleanup_detail(*errors: BaseException | None) -> str:
    failures = [str(error) for error in errors if error is not None]
    return f"; process cleanup failed: {'; '.join(failures)}" if failures else ""


def _reap_direct_process(
    proc: subprocess.Popen[bytes] | None,
) -> BaseException | None:
    if proc is None:
        return None
    try:
        proc.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return exc
    return None


def clean_process_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Remove inherited Git repository-selection variables."""
    cleaned = os.environ.copy() if env is None else env.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        cleaned.pop(key, None)
    return cleaned


def execute_process(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
    timeout: int,
    capture_output: bool = True,
    max_capture_bytes: int = DEFAULT_CAPTURE_LIMIT_BYTES,
    pass_fds: Sequence[int] = (),
) -> GitProcessResult:
    """Run within a deadline, capture output, and clean contained processes."""
    arguments = tuple(command)
    if os.name != "nt" and not sys.platform.startswith("linux"):
        raise GitProcessError(
            "bounded descendant cleanup is supported only on Windows and Linux"
        )
    if capture_output and max_capture_bytes <= 0:
        raise ValueError("capture limit must be positive")
    options: dict[str, object] = {}
    inherited_fds = tuple(pass_fds)
    windows_job: int | None = None
    if os.name == "nt":
        if inherited_fds:
            raise ValueError("inherited file descriptors are not supported on Windows")
        from atlas_build_process_windows import (
            CREATE_SUSPENDED,
            active_processes,
            assign_process,
            create_job,
            resume_primary_thread,
        )

        options["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED
        )
    else:
        options["start_new_session"] = True
        options["pass_fds"] = inherited_fds
    environment = clean_process_env(env)
    if env is not None and "GIT_INDEX_FILE" in env:
        environment["GIT_INDEX_FILE"] = env["GIT_INDEX_FILE"]
    assigned = False
    proc: subprocess.Popen[bytes] | None = None
    capture: BoundedOutputCapture | None = None
    stdin_capture = None
    try:
        if os.name == "nt":
            windows_job = create_job()
        if stdin is not None:
            stdin_capture = tempfile.TemporaryFile(mode="w+b")
            stdin_capture.write(stdin)
            stdin_capture.seek(0)
        proc = subprocess.Popen(
            arguments,
            cwd=cwd,
            stdin=stdin_capture,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            env=environment,
            **options,
        )
        if windows_job is not None:
            assign_process(windows_job, proc.pid)
            assigned = True
            resume_primary_thread(proc.pid)
        if capture_output:
            if proc.stdout is None or proc.stderr is None:
                raise OSError("subprocess output pipes were not created")
            capture = BoundedOutputCapture(
                proc.stdout, proc.stderr, max_capture_bytes
            )
        if os.name == "nt":
            _wait_for_windows_process(proc, timeout, capture)
            if windows_job is not None and active_processes(windows_job) != 0:
                _terminate_process_boundary(proc, windows_job)
        else:
            if not wait_for_process_exit_without_reaping(
                proc, timeout, PROCESS_GROUP_POLL_INTERVAL_SECONDS, capture
            ):
                raise subprocess.TimeoutExpired(arguments, timeout)
            if capture is not None:
                capture.wait(0.0)
            if linux_process_group_has_live_members(proc.pid, proc.pid):
                _terminate_process_boundary(proc)
            else:
                proc.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
        if capture is not None:
            stdout, stderr = capture.finish(CLEANUP_TIMEOUT_SECONDS)
            capture = None
        else:
            stdout = b""
            stderr = b""
    except CaptureLimitExceeded as exc:
        cleanup_error = _stop_after_failure(
            proc, windows_job if assigned else None, command_timed_out=False
        )
        close_error = _close_process_job(windows_job)
        reap_error = _reap_direct_process(proc)
        capture_error = _finish_capture_after_failure(capture, proc)
        stdin_error = _close_stdin(stdin_capture)
        detail = _cleanup_detail(
            cleanup_error, close_error, reap_error, capture_error, stdin_error
        )
        raise GitProcessError(
            f"{exc}{detail}", output_limit_exceeded=True
        ) from (cleanup_error or capture_error or stdin_error or exc)
    except subprocess.TimeoutExpired as exc:
        cleanup_error = _stop_after_failure(
            proc,
            windows_job if assigned else None,
            command_timed_out=True,
        )
        close_error = _close_process_job(windows_job)
        reap_error = _reap_direct_process(proc)
        capture_error = _finish_capture_after_failure(capture, proc)
        stdin_error = _close_stdin(stdin_capture)
        detail = _cleanup_detail(
            cleanup_error, close_error, reap_error, capture_error, stdin_error
        )
        raise GitProcessError(
            f"process timed out after {timeout}s: {' '.join(arguments)}{detail}",
            timed_out=True,
        ) from (cleanup_error or close_error or reap_error or capture_error or stdin_error or exc)
    except OSError as exc:
        cleanup_error = _stop_after_failure(
            proc,
            windows_job if assigned else None,
            command_timed_out=False,
        )
        close_error = _close_process_job(windows_job)
        reap_error = _reap_direct_process(proc)
        capture_error = _finish_capture_after_failure(capture, proc)
        stdin_error = _close_stdin(stdin_capture)
        detail = _cleanup_detail(
            cleanup_error, close_error, reap_error, capture_error, stdin_error
        )
        raise GitProcessError(
            f"cannot run {arguments[0]}: {exc}{detail}"
        ) from (cleanup_error or capture_error or stdin_error or exc)
    except BaseException as exc:
        cleanup_error = _stop_after_failure(
            proc,
            windows_job if assigned else None,
            command_timed_out=False,
        )
        close_error = _close_process_job(windows_job)
        reap_error = _reap_direct_process(proc)
        capture_error = _finish_capture_after_failure(capture, proc)
        stdin_error = _close_stdin(stdin_capture)
        if any(
            error is not None
            for error in (
                cleanup_error,
                close_error,
                reap_error,
                capture_error,
                stdin_error,
            )
        ):
            raise exc from (
                cleanup_error or close_error or reap_error or capture_error or stdin_error
            )
        raise
    else:
        close_error = _close_process_job(windows_job)
        stdin_error = _close_stdin(stdin_capture)
        if proc is None:
            raise GitProcessError("process did not start")
        if close_error is not None or stdin_error is not None:
            failure = close_error or stdin_error
            raise GitProcessError("failed to close subprocess resources") from failure
        return GitProcessResult(arguments, proc.returncode, stdout, stderr)


def execute(
    repo: Path,
    args: tuple[str, ...],
    *,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
    timeout: int,
) -> GitProcessResult:
    """Run Git against one repository with a bounded process lifetime."""
    return execute_process(
        ("git", "-C", str(repo), *args),
        stdin=stdin,
        env=env,
        timeout=timeout,
    )


def archive(
    repo: Path,
    revision: str,
    *,
    paths: Sequence[str] = (),
    timeout: int,
) -> bytes:
    """Return a Git tree archive with a bounded process lifetime."""
    arguments = ["archive", "--format=tar", revision]
    if paths:
        arguments.extend(("--", *paths))
    result = execute(repo, tuple(arguments), timeout=timeout)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitProcessError(detail or f"git archive failed for {revision}")
    return result.stdout


def extract_archive(payload: bytes, destination: Path) -> None:
    """Extract a Git archive while rejecting unsafe member paths."""
    with tarfile.open(fileobj=io.BytesIO(payload)) as tree:
        if hasattr(tarfile, "data_filter"):
            tree.extractall(destination, filter="data")
            return
        root = destination.resolve()
        for member in tree.getmembers():
            relative = PurePosixPath(member.name)
            target = destination.joinpath(*relative.parts).resolve()
            if relative.is_absolute() or ".." in relative.parts or root not in target.parents:
                raise tarfile.ExtractError(f"archive path escapes snapshot: {member.name}")
            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise tarfile.ExtractError(f"unsupported archive entry: {member.name}")
            tree.extract(member, path=destination)
