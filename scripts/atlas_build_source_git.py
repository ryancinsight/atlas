"""Read Git metadata used to identify a source checkout."""

from __future__ import annotations

import os
from pathlib import Path

from atlas_build_lease import BuildIdentityError
from atlas_git_process import GitProcessError, execute_process


def _git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    environment = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_COMMON_DIR",
    ):
        environment.pop(key, None)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = execute_process(
            ("git", *arguments),
            cwd=root,
            stdin=input_bytes,
            env=environment,
            timeout=60,
        )
    except GitProcessError as error:
        raise BuildIdentityError(f"cannot run git in {root}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BuildIdentityError(f"git {' '.join(arguments)} failed in {root}: {detail}")
    return result.stdout


def _tree_entries(top: Path) -> dict[bytes, tuple[bytes, bytes, bytes]]:
    entries: dict[bytes, tuple[bytes, bytes, bytes]] = {}
    for entry in _git(top, "ls-tree", "-r", "-z", "HEAD").split(b"\0"):
        if not entry:
            continue
        metadata, separator, raw_path = entry.partition(b"\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise BuildIdentityError(f"malformed Git tree entry in {top}")
        entries[raw_path] = (fields[0], fields[1], fields[2])
    return entries


def _index_entries(top: Path) -> dict[bytes, list[tuple[bytes, bytes, bytes]]]:
    entries: dict[bytes, list[tuple[bytes, bytes, bytes]]] = {}
    for entry in _git(top, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, separator, raw_path = entry.partition(b"\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise BuildIdentityError(f"malformed Git index entry in {top}")
        entries.setdefault(raw_path, []).append((fields[0], fields[1], fields[2]))
    return entries


