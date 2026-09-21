"""Materializable stale-basis inspection for the Atlas guard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import atlas_git_process as process
from atlas_stale_side_git import (
    FILE_MODES,
    git_env,
    head_blobs,
    index_entries,
    run,
    run_bytes,
)

INDEX_MAGIC = b"DIRC"


@dataclass(frozen=True)
class IndexBasis:
    path: Path
    total: int
    differing: int
    examples: tuple[str, ...]


def git_dir(repo: Path) -> Path:
    _code, out = run(repo, "rev-parse", "--absolute-git-dir")
    value = out.strip()
    if not value:
        raise process.GitProcessError("Git returned an empty repository directory")
    return Path(value)


def selected_index(repo: Path, directory: Path) -> Path:
    configured = os.environ.get("GIT_INDEX_FILE")
    if not configured:
        return (directory / "index").resolve()
    path = Path(configured)
    return (repo / path).resolve() if not path.is_absolute() else path.resolve()


def shared_index(repo: Path, index: Path | None = None) -> Path | None:
    env = None if index is None else git_env(index)
    _code, out = run(repo, "rev-parse", "--shared-index-path", env=env)
    value = out.strip()
    if not value:
        return None
    path = Path(value)
    return (repo / path).resolve() if not path.is_absolute() else path.resolve()


def protocol_lock(entry: Path, active_index: Path, directory: Path) -> bool:
    resolved = entry.resolve()
    return resolved == (directory / "index.lock").resolve() or resolved in {
        active_index,
        active_index.with_name(f"{active_index.name}.lock"),
    }


def alternate_indexes(repo: Path) -> list[Path]:
    directory = git_dir(repo)
    if not directory.is_dir():
        raise process.GitProcessError(
            f"repository directory is not readable: {directory}"
        )
    active_index = selected_index(repo, directory)
    active_shared = shared_index(repo)
    ordinary_shared = shared_index(repo, directory / "index")
    live_shared = {path for path in (active_shared, ordinary_shared) if path is not None}
    found = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        resolved = entry.resolve()
        if resolved in {(directory / "index").resolve(), active_index}:
            continue
        if resolved in live_shared:
            continue
        if protocol_lock(entry, active_index, directory):
            continue
        try:
            with entry.open("rb") as handle:
                if handle.read(4) == INDEX_MAGIC:
                    found.append(entry)
        except OSError as exc:
            raise process.GitProcessError(
                f"cannot read possible alternate index {entry}: {exc}"
            ) from exc
    return found


def head_basis(repo: Path) -> str:
    exists, _ = run(
        repo,
        "show-ref",
        "--verify",
        "--quiet",
        "refs/remotes/origin/main",
        allowed=(0, 1),
    )
    _code, name = run(repo, "branch", "--show-current")
    branch = name.strip() or "(detached HEAD)"
    if exists != 0:
        return f"{branch}: origin/main unavailable, distance unknown"
    _code, out = run(
        repo, "rev-list", "--left-right", "--count", "origin/main...HEAD"
    )
    parts = out.split()
    if len(parts) != 2:
        raise process.GitProcessError(
            "malformed `git rev-list --left-right --count` output"
        )
    behind, ahead = parts
    return f"{branch}: {ahead} ahead / {behind} behind origin/main"


def index_summary(repo: Path, index: Path, examples: int = 3) -> IndexBasis:
    entries = index_entries(repo, index)
    heads = head_blobs(repo)
    differing = sorted(
        path
        for path, (mode, blob) in entries.items()
        if mode in FILE_MODES and heads.get(path) != blob
    )
    return IndexBasis(index, len(entries), len(differing), tuple(differing[:examples]))


def ancestor_branches(repo: Path) -> list[tuple[str, int]]:
    _code, out = run(
        repo, "for-each-ref", "--format=%(refname:short)", "refs/heads"
    )
    _code, current_out = run(repo, "branch", "--show-current")
    current = current_out.strip()
    rows = []
    for ref in (line.strip() for line in out.splitlines()):
        if not ref or ref == current:
            continue
        ancestor, _ = run(
            repo, "merge-base", "--is-ancestor", ref, "HEAD", allowed=(0, 1)
        )
        if ancestor != 0:
            continue
        _code, diff = run_bytes(repo, "diff", "--name-only", "-z", ref, "HEAD")
        rows.append((ref, len([item for item in diff.split(b"\0") if item])))
    return sorted(rows, key=lambda row: -row[1])


def inspect_indexes(repo: Path) -> list[IndexBasis]:
    return [index_summary(repo, path) for path in alternate_indexes(repo)]
