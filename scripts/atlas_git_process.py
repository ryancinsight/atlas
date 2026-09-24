"""Bounded process execution with sanitized Git selection and descendant cleanup."""

from __future__ import annotations

import io
import os
import signal
import subprocess
import tarfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CLEANUP_TIMEOUT_SECONDS = 5


class GitProcessError(RuntimeError):
    """A process could not launch, exceeded its deadline, or could not be stopped."""

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
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=CLEANUP_TIMEOUT_SECONDS,
                check=False,
            )
            if result.returncode != 0:
                try:
                    proc.kill()
                except OSError:
                    pass
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except OSError:
                pass
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
            "timed-out process tree did not terminate", timed_out=True
        ) from exc


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
) -> GitProcessResult:
    """Run a process with a deadline and descendant cleanup."""
    arguments = tuple(command)
    options: dict[str, object] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    environment = clean_process_env(env)
    if env is not None and "GIT_INDEX_FILE" in env:
        environment["GIT_INDEX_FILE"] = env["GIT_INDEX_FILE"]
    try:
        proc = subprocess.Popen(
            arguments,
            cwd=cwd,
            stdin=subprocess.PIPE if stdin is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            **options,
        )
        stdout, stderr = proc.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(proc)
        raise GitProcessError(
            f"process timed out after {timeout}s: {' '.join(arguments)}",
            timed_out=True,
        ) from exc
    except OSError as exc:
        raise GitProcessError(f"cannot run {arguments[0]}: {exc}") from exc
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
