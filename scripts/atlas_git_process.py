"""Bounded Git process execution with descendant cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path

CLEANUP_TIMEOUT_SECONDS = 5


class GitProcessError(RuntimeError):
    """Git could not launch, exceeded its deadline, or could not be stopped."""

    def __init__(self, message: str, *, timed_out: bool = False) -> None:
        super().__init__(message)
        self.timed_out = timed_out


@dataclass(frozen=True)
class GitProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes


def _terminate_process_tree(proc: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=CLEANUP_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        proc.communicate(timeout=CLEANUP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        raise GitProcessError(
            "timed-out Git process tree did not terminate", timed_out=True
        ) from exc


def execute(
    repo: Path,
    args: tuple[str, ...],
    *,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
    timeout: int,
) -> GitProcessResult:
    """Run Git with a deadline and terminate its process tree on expiry."""
    command = ("git", "-C", str(repo), *args)
    options: dict[str, object] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if stdin is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy() if env is None else env,
            **options,
        )
        stdout, stderr = proc.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(proc)
        raise GitProcessError(
            f"git command timed out after {timeout}s: {' '.join(command)}",
            timed_out=True,
        ) from exc
    except OSError as exc:
        raise GitProcessError(f"cannot run git: {exc}") from exc
    return GitProcessResult(command, proc.returncode, stdout, stderr)
