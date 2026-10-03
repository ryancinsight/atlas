"""Fixtures the root hook tests share.

The tests that run `.githooks/pre-commit`, `.githooks/pre-push` and
`.githooks/stack-root.sh` in throwaway repositories build those repositories
here and run git as a test committer under one deadline.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRE_PUSH = ROOT / ".githooks" / "pre-push"
PRE_COMMIT = ROOT / ".githooks" / "pre-commit"
STACK_ROOT = ROOT / ".githooks" / "stack-root.sh"

# Hang guard for every subprocess a fixture starts: git calls (some run a
# hook that launches a few dozen processes), hook invocations, and `cargo
# build`. It is the 10-minute foreground default of the agent process budget,
# not a speed bound: a call taking 30 s on a loaded host is slow, not hung.
# Hook speed is held by counting what a hook launches, never by timing it.
FIXTURE_PROCESS_TIMEOUT_SECONDS = 600


def fixture_environment() -> dict[str, str]:
    """The process environment without `GIT_*`, and with no user or system git config."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return environment


def git(
    environment: dict[str, str], path: Path, *arguments: str, check: bool = True,
) -> subprocess.CompletedProcess:
    """`git -C path ...` as a test committer, under the fixture deadline."""
    return subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=Test",
         "-c", "user.email=test@example.invalid", *arguments],
        env=environment, check=check, capture_output=True,
        text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
    )


def install_hook(repo: Path) -> None:
    """The pre-commit hook, its resolver and the scripts it runs, copied into `repo`."""
    (repo / "scripts").mkdir()
    for name in (
        "atlas-stale-side-guard.py", "atlas_stale_side_git.py",
        "atlas_stale_side_basis.py", "atlas_git_process.py", "stale-side-waivers.json",
        "atlas-provider-integration-audit.py", "atlas_stack.py", "check_mdbook_links.py",
    ):
        shutil.copyfile(ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / ".githooks").mkdir()
    for hook in (PRE_COMMIT, STACK_ROOT):
        shutil.copyfile(hook, repo / ".githooks" / hook.name)
        (repo / ".githooks" / hook.name).chmod(0o755)


def init_separate_git_dir(
    environment: dict[str, str], worktree: Path, metadata: Path,
) -> None:
    """A repository at `worktree` whose Git metadata is the separate directory `metadata`.

    The worktree's `.git` is then a file naming the metadata, the only marker
    of the canonical worktree from a linked lane. The parents of both are
    created, and nothing is committed.
    """
    worktree.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    git(environment, worktree.parent, "init", "-q", "-b", "main",
        "--separate-git-dir", str(metadata), str(worktree))
