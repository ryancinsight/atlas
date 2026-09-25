#!/usr/bin/env python3
"""Regression tests for the shared Atlas stack helpers."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas_stack.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_stack_under_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
atlas_stack = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = atlas_stack
SPEC.loader.exec_module(atlas_stack)
from atlas_git_process import clean_process_env

IDENT = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(repo: Path, *argv: str) -> None:
    subprocess.run(["git", "-C", str(repo), *argv], check=True, env=clean_process_env())


class MemberPinsTestCase(unittest.TestCase):
    def test_reads_gitlinks_from_the_requested_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-stack-pins-") as directory:
            repo = Path(directory)
            _git(repo, "init", "-q", "-b", "main")
            (repo / ".gitmodules").write_text(
                '[submodule "repos/demo"]\n'
                "\tpath = repos/demo\n"
                "\turl = https://github.com/ryancinsight/demo\n",
                encoding="utf-8",
            )
            _git(repo, "add", ".gitmodules")
            revision = "1" * 40
            _git(
                repo,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{revision},repos/demo",
            )
            _git(
                repo,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{'2' * 40},repos/unregistered",
            )
            _git(repo, *IDENT, "commit", "-q", "-m", "pin demo")
            self.assertEqual(atlas_stack.member_pins(repo), {"demo": revision})


class StalenessTestCase(unittest.TestCase):
    """`commits_behind_upstream` and the note built on it.

    Gates report against whichever revision is checked out, and members of
    this stack are routinely behind — eight of twenty-five were the day this
    was written. A stale checkout then manufactures findings that upstream
    already fixed, which is how coeus came to report a drifted ADR index
    whose missing row `origin/main` had carried for six commits.
    """

    def test_git_preserves_configuration_and_clears_repository_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            _git(repo, "init", "-q", "-b", "main")
            (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            _git(repo, "add", "tracked.txt")
            foreign_index = Path(directory) / "foreign-index"
            foreign_index.write_bytes(b"invalid index")
            configuration = {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "atlas.fixture",
                "GIT_CONFIG_VALUE_0": "caller-setting",
                "GIT_CONFIG_GLOBAL": str(repo / "isolated-config"),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_DIR": str(repo / "not-a-repository"),
                "GIT_WORK_TREE": str(repo / "not-a-worktree"),
                "GIT_INDEX_FILE": str(foreign_index),
            }
            with patch.dict(os.environ, configuration):
                before = dict(os.environ)
                self.assertEqual(
                    atlas_stack.git(repo, "config", "--get", "atlas.fixture").strip(),
                    "caller-setting",
                )
                self.assertEqual(atlas_stack.git(repo, "ls-files"), "tracked.txt\n")
                self.assertEqual(
                    Path(atlas_stack.git(repo, "rev-parse", "--show-toplevel").strip()).resolve(),
                    repo.resolve(),
                )
                cleaned = clean_process_env()
                self.assertEqual(cleaned["GIT_CONFIG_GLOBAL"], configuration["GIT_CONFIG_GLOBAL"])
                self.assertEqual(cleaned["GIT_CONFIG_NOSYSTEM"], "1")
                self.assertEqual(dict(os.environ), before)
                self.assertFalse({"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"} & cleaned.keys())

    def _clone_one_behind(self, root: Path) -> Path:
        """A clone whose HEAD is one commit behind its fetched origin."""
        origin, clone = root / "origin", root / "clone"
        origin.mkdir()
        (origin / "a.md").write_text("seed\n", encoding="utf-8")
        _git(origin, "init", "-q", "-b", "main")
        _git(origin, *IDENT, "add", "a.md")
        _git(origin, *IDENT, "commit", "-q", "-m", "one")
        subprocess.run(
            ["git", "clone", "-q", str(origin), str(clone)],
            check=True,
            env=clean_process_env(),
        )
        (origin / "b.md").write_text("second\n", encoding="utf-8")
        _git(origin, *IDENT, "add", "b.md")
        _git(origin, *IDENT, "commit", "-q", "-m", "two")
        _git(clone, "fetch", "-q")
        return clone

    def test_measures_distance_on_a_tracking_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-stack-") as temp:
            clone = self._clone_one_behind(Path(temp))
            self.assertEqual(atlas_stack.commits_behind_upstream(clone), 1)

    def test_measures_distance_from_a_detached_head(self) -> None:
        """A detached HEAD has no `@{upstream}`, so the fallback carries this.

        Detached checkouts are the stale ones in practice, so without the
        `origin/main` fallback the note stays silent exactly where it is
        needed — as it did on coeus.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-stack-") as temp:
            clone = self._clone_one_behind(Path(temp))
            _git(clone, "checkout", "-q", "--detach", "HEAD")
            self.assertEqual(atlas_stack.commits_behind_upstream(clone), 1)

    def test_current_checkout_reports_no_distance_and_no_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-stack-") as temp:
            root = Path(temp)
            clone = self._clone_one_behind(root)
            _git(clone, "merge", "-q", "--ff-only", "origin/main")
            self.assertEqual(atlas_stack.commits_behind_upstream(clone), 0)
            self.assertEqual(atlas_stack.staleness_note(clone), "")

    def test_non_repository_reports_no_distance(self) -> None:
        """Silence beats a violation the tool cannot substantiate."""
        with tempfile.TemporaryDirectory(prefix="atlas-stack-") as temp:
            self.assertEqual(atlas_stack.commits_behind_upstream(Path(temp)), 0)
            self.assertEqual(atlas_stack.staleness_note(Path(temp)), "")

    def test_git_timeout_is_not_an_empty_measurement(self) -> None:
        with patch.object(
            atlas_stack,
            "execute_git",
            side_effect=atlas_stack.GitProcessError("timed out", timed_out=True),
        ):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                atlas_stack.git(Path("unused"), "rev-parse", "HEAD")

    def test_nonzero_git_result_is_not_a_clean_measurement(self) -> None:
        failure = subprocess.CompletedProcess(
            ["git"], 128, stdout=b"", stderr=b"fatal: failed"
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".git").mkdir()
            with patch.object(atlas_stack, "execute_git", return_value=failure):
                with self.assertRaisesRegex(RuntimeError, "failed"):
                    atlas_stack.git(repo, "rev-parse", "HEAD")
            with patch.object(atlas_stack, "execute_git", return_value=failure):
                with self.assertRaisesRegex(RuntimeError, "failed"):
                    atlas_stack.commits_behind_upstream(repo)
        with patch.object(atlas_stack, "execute_git", return_value=failure):
            with self.assertRaisesRegex(RuntimeError, "failed"):
                atlas_stack.is_git_ignored(atlas_stack.ROOT / "artifact")

    def test_note_states_the_distance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-stack-") as temp:
            clone = self._clone_one_behind(Path(temp))
            note = atlas_stack.staleness_note(clone)
            self.assertIn("1 commit(s) behind upstream", note)


class StackRootTestCase(unittest.TestCase):
    """A copy of the scripts extracted elsewhere measures the stack it names."""

    def root_of(self, env: dict[str, str]) -> Path:
        probe = subprocess.run(
            [sys.executable, "-c", "import atlas_stack; print(atlas_stack.ROOT)"],
            cwd=SCRIPT.parent, env=env, capture_output=True, text=True, check=True,
        )
        return Path(probe.stdout.strip())

    def test_the_named_stack_is_the_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-stack-root-") as temp:
            env = dict(os.environ, ATLAS_STACK_ROOT=temp)
            self.assertEqual(self.root_of(env), Path(temp).resolve())

    def test_unset_the_root_is_the_tree_the_scripts_sit_in(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "ATLAS_STACK_ROOT"}
        self.assertEqual(self.root_of(env), SCRIPT.resolve().parent.parent)


if __name__ == "__main__":
    unittest.main()
