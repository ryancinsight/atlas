"""Bounded process execution with sanitized Git selection and descendant cleanup."""

from __future__ import annotations

import io
import math
import os
import tarfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import process_tree


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


def clean_process_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Remove inherited Git repository-selection variables."""
    cleaned = os.environ.copy() if env is None else env.copy()
    for key in REPOSITORY_ENVIRONMENT:
        cleaned.pop(key, None)
    return cleaned


def _timeout_error(
    arguments: Sequence[str], timeout: float, cleanup_error: str | None = None
) -> GitProcessError:
    message = f"process timed out after {timeout}s: {' '.join(arguments)}"
    if cleanup_error is not None:
        message += f"; process-tree cleanup failed: {cleanup_error}"
    return GitProcessError(message, timed_out=True)


# The variables `git rev-parse --local-env-vars` lists as describing one
# repository, which a command run in another must not inherit. The two
# per-setting entries that list also names (`GIT_CONFIG_PARAMETERS`,
# `GIT_CONFIG_COUNT` with its `KEY_n`/`VALUE_n`) are the caller's settings and
# pass through; `GIT_CONFIG` redirects the repository's own configuration
# file, so it goes.
REPOSITORY_ENVIRONMENT = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
)


def execute_process(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
    timeout: int,
) -> GitProcessResult:
    """Run a process with a deadline and descendant cleanup.

    A deadline that is zero or negative has already passed: the command is not
    launched and the outcome is the typed timeout every expired deadline has. A
    deadline that is not a finite number (NaN, an infinity, ``None``, a string)
    names no instant, so it is a typed error that is not a timeout.
    """
    arguments = tuple(command)
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
    ):
        raise GitProcessError(
            f"process deadline must be a finite number of seconds, got {timeout!r}: "
            f"{' '.join(arguments)}"
        )
    if timeout <= 0:
        raise _timeout_error(arguments, timeout)
    environment = clean_process_env(env)
    if env is not None and "GIT_INDEX_FILE" in env:
        environment["GIT_INDEX_FILE"] = env["GIT_INDEX_FILE"]
    try:
        completed = process_tree.run(
            arguments,
            cwd=cwd,
            env=environment,
            input=stdin,
            timeout=timeout,
        )
    except process_tree.ProcessTreeTimeout as exc:
        raise _timeout_error(arguments, timeout, exc.cleanup_error) from exc
    except process_tree.ProcessTreeCleanupError as exc:
        raise GitProcessError(
            f"{arguments[0]} ran but its process-tree cleanup failed: {exc.cleanup_error}"
        ) from exc
    except (OSError, RuntimeError) as exc:
        raise GitProcessError(f"cannot run {arguments[0]}: {exc}") from exc
    return GitProcessResult(
        arguments,
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


# The variables `git rev-parse --local-env-vars` lists as describing one
# repository, which a command run in another must not inherit. The two
# per-setting entries that list also names (`GIT_CONFIG_PARAMETERS`,
# `GIT_CONFIG_COUNT` with its `KEY_n`/`VALUE_n`) are the caller's settings and
# pass through; `GIT_CONFIG` redirects the repository's own configuration
# file, so it goes.
REPOSITORY_ENVIRONMENT = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
)



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
