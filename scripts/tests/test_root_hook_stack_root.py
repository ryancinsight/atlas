"""Pin `canonical_stack_root` in `.githooks/stack-root.sh`, which both root hooks source."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from root_hook_support import (
    FIXTURE_PROCESS_TIMEOUT_SECONDS, STACK_ROOT, fixture_environment, git, init_separate_git_dir,
)


def separate_git_dir_repository(
    environment: dict[str, str], worktree: Path, metadata: Path,
) -> None:
    """`init_separate_git_dir` with an empty root commit, so a lane can branch from it."""
    init_separate_git_dir(environment, worktree, metadata)
    git(environment, worktree, "commit", "-q", "--allow-empty", "-m", "root")


def canonical_root(
    environment: dict[str, str], directory: Path, scratch: Path, **extra: str,
) -> subprocess.CompletedProcess:
    """`canonical_stack_root` from `.githooks/stack-root.sh`, as a hook calls it.

    The hook passes Git's top level for its own directory, so this does too.
    The driver is a script file: `bash -c` halves the backslashes of its
    argument on Windows, which breaks the resolver's own path handling.
    """
    toplevel = git(environment, directory, "rev-parse", "--show-toplevel").stdout.strip()
    driver = scratch / "resolve.sh"
    driver.write_bytes(b'. "$1"\ncanonical_stack_root "$2"\n')
    return subprocess.run(
        ["bash", str(driver), STACK_ROOT.as_posix(), toplevel],
        cwd=toplevel, env=dict(environment, **extra), capture_output=True, text=True,
        timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
    )


class StackRootTests(unittest.TestCase):
    def assertResolves(self, result: subprocess.CompletedProcess, expected: Path) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(os.path.samefile(result.stdout.strip(), expected), result.stdout)

    def test_a_checkout_is_its_own_canonical_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            repo = root / "atlas"
            repo.mkdir()
            git(environment, repo, "init", "-q", "-b", "main")

            self.assertResolves(canonical_root(environment, repo, root), repo)

    def test_a_linked_lane_resolves_to_the_main_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            repo = root / "atlas"
            repo.mkdir()
            git(environment, repo, "init", "-q", "-b", "main")
            git(environment, repo, "commit", "-q", "--allow-empty", "-m", "root")
            lane = root / "lane"
            git(environment, repo, "worktree", "add", "-q", "-b", "lane", str(lane))

            self.assertResolves(canonical_root(environment, lane, root), repo)

    def test_a_separate_git_dir_lane_resolves_to_the_canonical_worktree(self) -> None:
        """Only a scan of the ancestors can name the worktree, as its `.git` is a file."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root / "checkouts" / "canonical"
            separate_git_dir_repository(environment, worktree, root / "metadata" / "repo.git")
            lane = root / "lane"
            git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
            configured = git(
                environment, worktree, "config", "--get", "core.worktree", check=False,
            )
            self.assertEqual(configured.stdout, "", "the layout must leave `core.worktree` unset")

            self.assertResolves(canonical_root(environment, lane, root), worktree)

    def test_core_worktree_names_a_canonical_root_no_scan_reaches(self) -> None:
        """The scan looks six directories down; a configured worktree needs no scan."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = fixture_environment()
            worktree = root.joinpath(*"abcdefgh") / "canonical"
            metadata = root / "metadata" / "repo.git"
            separate_git_dir_repository(environment, worktree, metadata)
            lane = root / "lane"
            git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
            git(environment, lane, "--git-dir", str(metadata), "config", "core.worktree", str(worktree))

            self.assertResolves(canonical_root(environment, lane, root), worktree)


if __name__ == "__main__":
    unittest.main()
