#!/usr/bin/env python3
"""Tests for the PM-board and tracked-image budget gate."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-artifact-budget.py"
SPEC = importlib.util.spec_from_file_location("atlas_artifact_budget", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
budget = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = budget
SPEC.loader.exec_module(budget)

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}

PNG_HEADER = bytes([0x89]) + b"PNG"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        text=True, env=GIT_ENV,
    ).stdout


def _repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD").strip()


def _lines(n: int) -> str:
    return "".join(f"- line {i}\n" for i in range(n))


def _image(size: int) -> bytes:
    return PNG_HEADER + bytes(size)


class BoardBudgetTest(unittest.TestCase):
    def test_under_budget_board_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(50), encoding="utf-8")
            _commit(root, "board")
            failures, warnings = budget.evaluate(root, None, line_budget=100)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_over_budget_without_base_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "gap_audit.md").write_text(_lines(120), encoding="utf-8")
            _commit(root, "board")
            failures, _ = budget.evaluate(root, None, line_budget=100)
            self.assertEqual(len(failures), 1)
            self.assertIn("gap_audit.md: 120 lines, 20 over", failures[0])

    def test_over_budget_board_that_grew_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(120), encoding="utf-8")
            base = _commit(root, "board")
            (root / "backlog.md").write_text(_lines(125), encoding="utf-8")
            failures, _ = budget.evaluate(root, base, line_budget=100)
            self.assertEqual(len(failures), 1)
            self.assertIn("grew from 120", failures[0])

    def test_over_budget_board_that_shrank_passes_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "checklist.md").write_text(_lines(120), encoding="utf-8")
            base = _commit(root, "board")
            (root / "checklist.md").write_text(_lines(110), encoding="utf-8")
            failures, warnings = budget.evaluate(root, base, line_budget=100)
            self.assertEqual(failures, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("held or shrank from 120", warnings[0])

    def test_board_crossing_the_budget_fails_even_against_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(90), encoding="utf-8")
            base = _commit(root, "board")
            (root / "backlog.md").write_text(_lines(101), encoding="utf-8")
            failures, _ = budget.evaluate(root, base, line_budget=100)
            self.assertEqual(len(failures), 1)


class ImageBudgetTest(unittest.TestCase):
    def test_added_oversized_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "README.md").write_text("x\n", encoding="utf-8")
            base = _commit(root, "init")
            (root / "docs").mkdir()
            (root / "docs" / "shot.png").write_bytes(_image(5000))
            _commit(root, "image")
            failures, _ = budget.evaluate(root, base, image_budget=1024)
            self.assertEqual(len(failures), 1)
            self.assertIn("docs/shot.png", failures[0])

    def test_untouched_oversized_image_passes_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "docs").mkdir()
            (root / "docs" / "old.png").write_bytes(_image(5000))
            base = _commit(root, "image")
            (root / "README.md").write_text("x\n", encoding="utf-8")
            _commit(root, "docs")
            failures, warnings = budget.evaluate(root, base, image_budget=1024)
            self.assertEqual(failures, [])
            self.assertEqual(len(warnings), 1)

    def test_modified_oversized_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "docs").mkdir()
            (root / "docs" / "fig.png").write_bytes(_image(5000))
            base = _commit(root, "image")
            (root / "docs" / "fig.png").write_bytes(_image(6000))
            _commit(root, "image again")
            failures, _ = budget.evaluate(root, base, image_budget=1024)
            self.assertEqual(len(failures), 1)

    def test_snapshot_without_git_is_walked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            (root / "docs" / "fig.jpg").write_bytes(bytes([0xFF, 0xD8]) + bytes(3000))
            (root / "docs" / "note.md").write_text("x\n", encoding="utf-8")
            sizes = budget.tracked_images(root)
            self.assertEqual(list(sizes), ["docs/fig.jpg"])
            self.assertEqual(sizes["docs/fig.jpg"], 3002)

    def test_archived_snapshot_marker_is_walked_not_queried(self) -> None:
        """The conformance scanner's `.git` marker names no gitdir."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").write_text("gitdir: archived 0123abcd\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "shot.png").write_bytes(_image(4000))
            (root / "backlog.md").write_text(_lines(3), encoding="utf-8")
            self.assertFalse(budget._is_git_checkout(root))
            got = budget.counts(root, line_budget=100, image_budget=1024)
            self.assertEqual(got["oversized_tracked_images"], 1)


class RevisionTest(unittest.TestCase):
    def test_rev_judges_the_commit_not_the_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(50), encoding="utf-8")
            head = _commit(root, "board")
            # A peer's uncommitted growth in the shared tree is not the push.
            (root / "backlog.md").write_text(_lines(150), encoding="utf-8")
            failures, _ = budget.evaluate(root, None, line_budget=100, rev=head)
            self.assertEqual(failures, [])
            failures, _ = budget.evaluate(root, None, line_budget=100)
            self.assertEqual(len(failures), 1)


class ReportTest(unittest.TestCase):
    def test_counts_sum_overage_and_count_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(130), encoding="utf-8")
            (root / "gap_audit.md").write_text(_lines(110), encoding="utf-8")
            (root / "big.png").write_bytes(bytes(4096))
            (root / "small.png").write_bytes(bytes(16))
            _commit(root, "fixture")
            got = budget.counts(root, line_budget=100, image_budget=1024)
            self.assertEqual(
                got, {"pm_lines_over_budget": 40, "oversized_tracked_images": 1}
            )

    def test_cli_check_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(5), encoding="utf-8")
            _commit(root, "fixture")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--root", str(root),
                 "--line-budget", "100"],
                capture_output=True, text=True, env=GIT_ENV,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("within budget", proc.stdout)


if __name__ == "__main__":
    unittest.main()
