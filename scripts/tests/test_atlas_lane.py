#!/usr/bin/env python3
"""End-to-end tests for the lane tool against real repositories.

Each test builds a stack-shaped fixture -- a bare origin, a member clone under
`repos/`, and the `worktrees/` lane root -- and drives the CLI as a process
with `ATLAS_STACK_ROOT` pointing at it, so every precondition is checked
against real `git worktree` state.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lane.py"
IDENT = ["-c", "user.email=t@t", "-c", "user.name=t"]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *IDENT, *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def link_directory(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        # Windows without symlink privilege: a junction redirects the same way.
        import _winapi
        _winapi.CreateJunction(str(target), str(link))


class LaneToolTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-lane-")
        base = Path(self.temp.name)
        self.stack = base / "stack"
        origin = base / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        self.member = self.stack / "repos" / "demo"
        subprocess.run(["git", "clone", "-q", str(origin), str(self.member)],
                       check=True, capture_output=True)
        (self.member / "a.txt").write_text("seed\n", encoding="utf-8")
        git(self.member, "add", "a.txt")
        git(self.member, "commit", "-q", "-m", "seed")
        git(self.member, "push", "-q", "origin", "HEAD:main")
        git(self.member, "remote", "set-head", "origin", "main")
        (self.stack / "worktrees").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def lane(self, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "ATLAS_STACK_ROOT": str(self.stack)}
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              capture_output=True, text=True, env=env)

    def trees(self) -> int:
        return git(self.member, "worktree", "list", "--porcelain").count("worktree ")

    def test_create_names_the_lane_and_refuses_a_third_tree(self) -> None:
        made = self.lane("create", "demo", "fix/first")
        self.assertEqual(made.returncode, 0, made.stderr)
        lane = self.stack / "worktrees" / "demo-fix-first"
        self.assertEqual(git(lane, "symbolic-ref", "--short", "HEAD"), "fix/first")
        self.assertEqual(git(lane, "rev-parse", "HEAD"), git(self.member, "rev-parse", "origin/main"))

        refused = self.lane("create", "demo", "fix/second")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("already has 2 trees", refused.stderr)
        self.assertIn("demo-fix-first on refs/heads/fix/first", refused.stderr)
        self.assertFalse((self.stack / "worktrees" / "demo-fix-second").exists())
        self.assertEqual(self.trees(), 2)

    def test_create_refuses_detached_head_and_a_lane_root_outside_the_stack(self) -> None:
        for revision in ("HEAD", git(self.member, "rev-parse", "HEAD")):
            refused = self.lane("create", "demo", revision)
            self.assertEqual(refused.returncode, 1)
            self.assertIn("would be detached HEAD", refused.stderr)

        # A lane root redirected out of the stack would build outside the
        # shared `.cargo` configuration, exactly like `D:/<member>-audit`.
        (self.stack / "worktrees").rmdir()
        elsewhere = Path(self.temp.name) / "elsewhere"
        elsewhere.mkdir()
        link_directory(self.stack / "worktrees", elsewhere)
        refused = self.lane("create", "demo", "fix/away")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("outside the canonical lane root", refused.stderr)
        self.assertEqual(self.trees(), 1)

    def test_close_refuses_dirty_and_unlanded_lanes_and_removes_landed_ones(self) -> None:
        self.assertEqual(self.lane("create", "demo", "fix/work").returncode, 0)
        lane = self.stack / "worktrees" / "demo-fix-work"
        (lane / "b.txt").write_text("work\n", encoding="utf-8")

        dirty = self.lane("close", "demo-fix-work")
        self.assertEqual(dirty.returncode, 1)
        self.assertIn("uncommitted work", dirty.stderr)

        git(lane, "add", "b.txt")
        git(lane, "commit", "-q", "-m", "work")
        unlanded = self.lane("close", "demo-fix-work")
        self.assertEqual(unlanded.returncode, 1)
        self.assertIn("neither on origin/main nor pushed", unlanded.stderr)
        repointed = self.lane("repoint", "demo-fix-work", "fix/next")
        self.assertEqual(repointed.returncode, 1)
        self.assertIn("holds work not on origin/main", repointed.stderr)

        git(lane, "push", "-q", "origin", "HEAD:main")
        repointed = self.lane("repoint", "demo-fix-work", "fix/next")
        self.assertEqual(repointed.returncode, 0, repointed.stderr)
        moved = self.stack / "worktrees" / "demo-fix-next"
        self.assertEqual(git(moved, "symbolic-ref", "--short", "HEAD"), "fix/next")
        self.assertFalse(lane.exists())

        closed = self.lane("close", str(moved))
        self.assertEqual(closed.returncode, 0, closed.stderr)
        self.assertFalse(moved.exists())
        self.assertEqual(self.trees(), 1)

    def test_export_writes_the_tree_without_a_worktree(self) -> None:
        target = Path(self.temp.name) / "baseline"
        exported = self.lane("export", "demo", "origin/main", str(target))
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertEqual((target / "a.txt").read_text(encoding="utf-8"), "seed\n")
        self.assertFalse((target / ".git").exists())
        self.assertEqual(self.trees(), 1)

        inside = self.lane("export", "demo", "origin/main", str(self.stack / "worktrees" / "ab"))
        self.assertEqual(inside.returncode, 1)
        self.assertIn("inside the lane root", inside.stderr)


    def submodule_shape(self) -> Path:
        """Move the member's gitdir under the umbrella's `.git/modules`, as a submodule has it."""
        gitdir = self.stack / ".git" / "modules" / "repos" / "demo"
        gitdir.parent.mkdir(parents=True)
        (self.member / ".git").rename(gitdir)
        (self.member / ".git").write_text("gitdir: ../../.git/modules/repos/demo\n", encoding="utf-8")
        subprocess.run(["git", "config", "-f", str(gitdir / "config"), "core.worktree",
                        "../../../../repos/demo"], check=True)
        return gitdir

    def toplevel(self, tree: Path) -> Path:
        return Path(git(tree, "rev-parse", "--show-toplevel")).resolve()

    def test_a_submodule_lane_resolves_to_its_own_directory(self) -> None:
        gitdir = self.submodule_shape()
        self.assertEqual(self.toplevel(self.member), self.member.resolve())

        made = self.lane("create", "demo", "fix/sub")
        self.assertEqual(made.returncode, 0, made.stderr)
        lane = self.stack / "worktrees" / "demo-fix-sub"
        self.assertEqual(self.toplevel(lane), lane.resolve())
        self.assertEqual(git(lane, "status", "--porcelain"), "")
        # The repair is per worktree: the main tree keeps the shared value.
        self.assertEqual(self.toplevel(self.member), self.member.resolve())
        self.assertEqual(subprocess.run(
            ["git", "config", "-f", str(gitdir / "config"), "core.worktree"],
            check=True, capture_output=True, text=True).stdout.strip(), "../../../../repos/demo")

        # A lane made before the repair inherits the shared value; repoint and
        # close repair it instead of refusing it as thousands of deletions.
        git(lane, "config", "--worktree", "--unset", "core.worktree")
        self.assertNotEqual(self.toplevel(lane), lane.resolve())
        repointed = self.lane("repoint", "demo-fix-sub", "fix/sub-next")
        self.assertEqual(repointed.returncode, 0, repointed.stderr)
        moved = self.stack / "worktrees" / "demo-fix-sub-next"
        self.assertEqual(self.toplevel(moved), moved.resolve())
        self.assertEqual(git(moved, "status", "--porcelain"), "")

        git(moved, "config", "--worktree", "--unset", "core.worktree")
        closed = self.lane("close", "demo-fix-sub-next")
        self.assertEqual(closed.returncode, 0, closed.stderr)
        self.assertFalse(moved.exists())
        self.assertEqual(self.toplevel(self.member), self.member.resolve())

if __name__ == "__main__":
    unittest.main()
