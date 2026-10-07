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
sys.path.insert(0, str(SCRIPT.parent))
from atlas_target_dir import TARGET_ENVIRONMENT  # noqa: E402
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
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.stack)], check=True)
        git(self.stack, "config", "user.email", "t@t")
        git(self.stack, "config", "user.name", "t")
        (self.stack / "README.md").write_text("stack\n", encoding="utf-8")
        git(self.stack, "add", "README.md")
        git(self.stack, "commit", "-q", "-m", "stack")
        self.member = self.stack / "repos" / "demo"
        subprocess.run(["git", "clone", "-q", str(origin), str(self.member)],
                       check=True, capture_output=True)
        (self.member / "a.txt").write_text("seed\n", encoding="utf-8")
        (self.member / "Cargo.toml").write_text(
            "[package]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
            encoding="utf-8",
        )
        (self.member / "src").mkdir()
        (self.member / "src" / "lib.rs").write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
        git(self.member, "add", "a.txt")
        git(self.member, "add", "Cargo.toml", "src/lib.rs")
        git(self.member, "commit", "-q", "-m", "seed")
        git(self.member, "push", "-q", "origin", "HEAD:main")
        git(self.member, "remote", "set-head", "origin", "main")
        (self.stack / "worktrees").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def cargo_environment() -> dict[str, str]:
        """The process environment without any Cargo output-directory variable."""
        return {k: v for k, v in os.environ.items() if k not in TARGET_ENVIRONMENT}

    def lane(self, *args: str) -> subprocess.CompletedProcess:
        env = {**self.cargo_environment(), "ATLAS_STACK_ROOT": str(self.stack)}
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
        config = self.stack / "worktrees" / ".cargo" / "config.toml"
        self.assertIn(
            f'target-dir = "{(self.stack / "target").resolve().as_posix()}"',
            config.read_text(encoding="utf-8"),
        )
        built = subprocess.run(
            ["cargo", "check", "--quiet", "--offline"],
            cwd=lane,
            capture_output=True,
            text=True,
            env=self.cargo_environment(),
        )
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertTrue((self.stack / "target").is_dir())
        self.assertFalse((lane / "target").exists())

        refused = self.lane("create", "demo", "fix/second")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("already has 2 trees", refused.stderr)
        self.assertIn("demo-fix-first on refs/heads/fix/first", refused.stderr)
        self.assertFalse((self.stack / "worktrees" / "demo-fix-second").exists())
        self.assertEqual(self.trees(), 2)

    def test_create_writes_both_generated_configs_only_once_it_will_proceed(self) -> None:
        member_config = self.stack / "repos" / ".cargo" / "config.toml"
        lane_config = self.stack / "worktrees" / ".cargo" / "config.toml"
        (self.stack / "worktrees" / "demo-fix-here").mkdir()
        refused = self.lane("create", "demo", "fix/here")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("already exists", refused.stderr)
        git(self.member, "branch", "fix/existing")
        refused = self.lane("create", "demo", "fix/existing", "--from", "main")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("--from applies only to a new branch", refused.stderr)
        self.assertFalse(member_config.exists())
        self.assertFalse(lane_config.exists())
        made = self.lane("create", "demo", "fix/existing")
        self.assertEqual(made.returncode, 0, made.stderr)
        self.assertTrue(member_config.is_file())
        self.assertTrue(lane_config.is_file())
        target = f'target-dir = "{(self.stack / "target").resolve().as_posix()}"'
        self.assertIn(target, member_config.read_text(encoding="utf-8"))
        self.assertIn(target, lane_config.read_text(encoding="utf-8"))

    def test_create_refuses_before_writing_when_a_generated_path_is_foreign(self) -> None:
        member_config = self.stack / "repos" / ".cargo" / "config.toml"
        lane_config = self.stack / "worktrees" / ".cargo" / "config.toml"
        lane_config.parent.mkdir()
        lane_config.write_text("[net]\noffline = true\n", encoding="utf-8")
        refused = self.lane("create", "demo", "fix/foreign")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("left alone", refused.stderr)
        self.assertFalse(member_config.exists())
        self.assertEqual(lane_config.read_text(encoding="utf-8"), "[net]\noffline = true\n")
        self.assertEqual(self.trees(), 1)

    def test_create_writes_no_config_when_the_worktree_cannot_be_added(self) -> None:
        # `main` is checked out in the member's own tree, so git refuses a lane on it.
        refused = self.lane("create", "demo", "main")
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertFalse((self.stack / "repos" / ".cargo" / "config.toml").exists())
        self.assertFalse((self.stack / "worktrees" / ".cargo" / "config.toml").exists())
        self.assertFalse((self.stack / "worktrees" / "demo-main").exists())
        self.assertEqual(self.trees(), 1)

    def test_create_refuses_the_umbrella_and_paths_outside_repos(self) -> None:
        for member in ("..", ".", "", "../stack"):
            refused = self.lane("create", member, "fix/up")
            self.assertEqual(refused.returncode, 1, member)
            self.assertIn("not a member checkout", refused.stderr)
        self.assertEqual(
            git(self.stack, "worktree", "list", "--porcelain").count("worktree "), 1
        )
        self.assertEqual(
            [path.name for path in (self.stack / "worktrees").iterdir()], []
        )

    def test_create_refuses_before_writing_when_the_member_config_is_foreign(self) -> None:
        member_config = self.stack / "repos" / ".cargo" / "config.toml"
        member_config.parent.mkdir()
        member_config.write_text("[net]\noffline = true\n", encoding="utf-8")
        refused = self.lane("create", "demo", "fix/foreign-member")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("left alone", refused.stderr)
        self.assertEqual(member_config.read_text(encoding="utf-8"), "[net]\noffline = true\n")
        self.assertFalse((self.stack / "worktrees" / ".cargo" / "config.toml").exists())
        self.assertFalse((self.stack / "worktrees" / "demo-fix-foreign-member").exists())
        self.assertEqual(self.trees(), 1)

    def test_create_refuses_before_adding_when_the_shared_target_cannot_be_resolved(self) -> None:
        # A separate git directory is not named `.git`, so no shared target resolves.
        subprocess.run(
            ["git", "-C", str(self.stack), "init", "-q", "--separate-git-dir",
             str(Path(self.temp.name) / "gitdata")],
            check=True, capture_output=True,
        )
        refused = self.lane("create", "demo", "fix/unresolved")
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertIn("unexpected Git common directory", refused.stderr)
        self.assertFalse((self.stack / "repos" / ".cargo" / "config.toml").exists())
        self.assertFalse((self.stack / "worktrees" / ".cargo" / "config.toml").exists())
        self.assertFalse((self.stack / "worktrees" / "demo-fix-unresolved").exists())
        self.assertEqual(self.trees(), 1)

    def test_create_refuses_a_link_that_leaves_repos(self) -> None:
        outside = Path(self.temp.name) / "outside"
        subprocess.run(["git", "init", "-q", "-b", "main", str(outside)], check=True)
        link = self.stack / "repos" / "evil"
        link_directory(link, outside)
        try:
            refused = self.lane("create", "evil", "fix/up")
        finally:
            # A directory link is removed as a directory on Windows, as a file elsewhere.
            os.rmdir(link) if os.name == "nt" else link.unlink()
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertIn("not a member checkout", refused.stderr)
        self.assertEqual(
            git(outside, "worktree", "list", "--porcelain").count("worktree "), 1
        )
        self.assertEqual([path.name for path in (self.stack / "worktrees").iterdir()], [])

    @unittest.skipUnless(os.name == "nt", "a drive-relative name exists only on Windows")
    def test_create_refuses_a_drive_relative_name_that_reaches_the_umbrella(self) -> None:
        # `<drive>:..` joins onto repos/ as `repos/..`, the umbrella checkout.
        drive = os.path.splitdrive(str(self.stack.resolve()))[0]
        refused = self.lane("create", f"{drive}..", "fix/up")
        self.assertEqual(refused.returncode, 1, refused.stderr)
        self.assertIn("not a member checkout", refused.stderr)
        self.assertEqual(
            git(self.stack, "worktree", "list", "--porcelain").count("worktree "), 1
        )
        self.assertEqual([path.name for path in (self.stack / "worktrees").iterdir()], [])

    def test_create_refuses_while_a_lane_config_redirects_the_output(self) -> None:
        elsewhere = self.stack / "worktrees" / "demo-other"
        (elsewhere / ".cargo").mkdir(parents=True)
        (elsewhere / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        (elsewhere / ".cargo" / "config.toml").write_text(
            "[build]\nbuild-dir = 'private'\n", encoding="utf-8"
        )
        refused = self.lane("create", "demo", "fix/blocked")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("fork the shared cache", refused.stderr)
        self.assertIn("demo-other", refused.stderr)
        self.assertEqual(self.trees(), 1)

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
        """Register the member as a submodule and let Git absorb its gitdir."""
        gitmodules = self.stack / ".gitmodules"
        subprocess.run(
            ["git", "config", "-f", str(gitmodules),
             "submodule.repos/demo.path", "repos/demo"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "config", "-f", str(gitmodules),
             "submodule.repos/demo.url", git(self.member, "remote", "get-url", "origin")],
            check=True, capture_output=True, text=True,
        )
        git(self.stack, "add", ".gitmodules", "repos/demo")
        git(self.stack, "commit", "-q", "-m", "register demo")
        subprocess.run(
            ["git", "-C", str(self.stack), "submodule", "absorbgitdirs", "repos/demo"],
            check=True, capture_output=True, text=True,
        )
        return Path(git(self.member, "rev-parse", "--absolute-git-dir")).resolve()

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
