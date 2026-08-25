#!/usr/bin/env python3
"""Regression tests for the shared Atlas stack helpers."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas_stack.py"
SPEC = importlib.util.spec_from_file_location("atlas_stack_under_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
atlas_stack = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = atlas_stack
SPEC.loader.exec_module(atlas_stack)

IDENT = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(repo: Path, *argv: str) -> None:
    subprocess.run(["git", "-C", str(repo), *argv], check=True)


class StalenessTestCase(unittest.TestCase):
    """`commits_behind_upstream` and the note built on it.

    Gates report against whichever revision is checked out, and members of
    this stack are routinely behind — eight of twenty-five were the day this
    was written. A stale checkout then manufactures findings that upstream
    already fixed, which is how coeus came to report a drifted ADR index
    whose missing row `origin/main` had carried for six commits.
    """

    def _clone_one_behind(self, root: Path) -> Path:
        """A clone whose HEAD is one commit behind its fetched origin."""
        origin, clone = root / "origin", root / "clone"
        origin.mkdir()
        (origin / "a.md").write_text("seed\n", encoding="utf-8")
        _git(origin, "init", "-q", "-b", "main")
        _git(origin, *IDENT, "add", "a.md")
        _git(origin, *IDENT, "commit", "-q", "-m", "one")
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
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

    def test_note_states_the_distance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-stack-") as temp:
            clone = self._clone_one_behind(Path(temp))
            note = atlas_stack.staleness_note(clone)
            self.assertIn("1 commit(s) behind upstream", note)


if __name__ == "__main__":
    unittest.main()
