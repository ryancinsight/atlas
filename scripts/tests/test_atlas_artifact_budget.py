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
    def test_board_names_resolve_by_canonical_name_not_spelling(self) -> None:
        """Four members track `CHECKLIST.md`; that file is their checklist board.

        Matching the path case-sensitively bounded none of them -- they carried
        1,156 to 4,328 lines and still reported `pm_lines_over_budget: 0`, so the
        gate could not see the largest boards in the stack.
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(5), encoding="utf-8")
            (root / "CHECKLIST.md").write_text(_lines(120), encoding="utf-8")
            _commit(root, "case-distinct board path")
            expected = {"CHECKLIST.md": 120, "backlog.md": 5}
            self.assertEqual(budget.board_lines(root, "HEAD"), expected)
            self.assertEqual(budget.board_lines(root), expected)

    def test_uppercase_checklist_is_bounded_by_the_line_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "CHECKLIST.md").write_text(_lines(120), encoding="utf-8")
            _commit(root, "board")
            failures, _ = budget.evaluate(root, None, line_budget=100)
            self.assertEqual(len(failures), 1)
            self.assertIn("CHECKLIST.md: 120 lines, 20 over", failures[0])
            counts = budget.counts(root, line_budget=100)
            self.assertEqual(counts["pm_lines_over_budget"], 20)

    def test_uppercase_checklist_ratchets_like_any_other_board(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "CHECKLIST.md").write_text(_lines(120), encoding="utf-8")
            base = _commit(root, "board")
            (root / "CHECKLIST.md").write_text(_lines(130), encoding="utf-8")
            failures, _ = budget.evaluate(root, base, line_budget=100)
            self.assertEqual(len(failures), 1)
            self.assertIn("grew from 120", failures[0])
            (root / "CHECKLIST.md").write_text(_lines(110), encoding="utf-8")
            failures, warnings = budget.evaluate(root, base, line_budget=100)
            self.assertEqual(failures, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("held or shrank from 120", warnings[0])

    def test_case_only_rename_ratchets_against_the_same_board(self) -> None:
        """A board ratchets by canonical identity, so respelling it is not one
        board vanishing and another appearing between `--base` and the push."""
        self.assertEqual(
            budget._ratchet_previous({"CHECKLIST.md": 120}, "checklist.md"), 120
        )
        self.assertEqual(
            budget._ratchet_previous({"checklist.md": 90}, "CHECKLIST.md"), 90
        )
        self.assertIsNone(budget._ratchet_previous({"backlog.md": 1}, "gap_audit.md"))

    def test_item_file_paths_stay_case_sensitive(self) -> None:
        """Board names resolve by canonical name; item files do not.

        `BACKLOG/` is not the `backlog/` item directory and `item.MD` is not an
        item file, so neither folds into `backlog.md`'s budgeted total.
        """
        for relative in ("BACKLOG/item.md", "backlog/item.MD"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _repo(root)
                (root / "backlog.md").write_text(_lines(5), encoding="utf-8")
                other = root / relative
                other.parent.mkdir(exist_ok=True)
                other.write_text(_lines(120), encoding="utf-8")
                _commit(root, "case-distinct item path")
                expected = {"backlog.md": 5}
                self.assertEqual(budget.board_lines(root, "HEAD"), expected)
                self.assertEqual(budget.board_lines(root), expected)
                self.assertEqual(budget.oversized_item_files(root), {})
                self.assertEqual(budget.counts(root)["pm_lines_over_budget"], 0)

    def test_cli_check_fails_on_an_uppercase_board_over_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "CHECKLIST.md").write_text(_lines(120), encoding="utf-8")
            _commit(root, "board")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--root", str(root),
                 "--line-budget", "100"],
                capture_output=True, text=True, env=GIT_ENV,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertIn("CHECKLIST.md: 120 lines, 20 over", proc.stdout)

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
                got,
                {
                    "pm_lines_over_budget": 40,
                    "oversized_tracked_images": 1,
                    "items_over_budget": 0,
                },
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


class PerItemFileLayoutTest(unittest.TestCase):
    """Past about forty open items a board moves bodies to `backlog/<anchor>.md`
    with `backlog.md` as their generated index (`atlas-board-index.py`); the
    1,000-line board budget must still bound the whole board, and each item
    file carries its own report-only fifteen-line budget."""

    def test_board_lines_folds_in_item_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(10), encoding="utf-8")
            item_dir = root / "backlog"
            item_dir.mkdir()
            (item_dir / "one.md").write_text(_lines(20), encoding="utf-8")
            (item_dir / "two.md").write_text(_lines(30), encoding="utf-8")
            _commit(root, "fixture")
            lines = budget.board_lines(root)
            self.assertEqual(lines["backlog.md"], 60)  # 10 + 20 + 30

    def test_board_lines_without_item_dir_is_unaffected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(10), encoding="utf-8")
            _commit(root, "fixture")
            lines = budget.board_lines(root)
            self.assertEqual(lines["backlog.md"], 10)

    def test_board_lines_at_a_revision_reads_item_files_from_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(5), encoding="utf-8")
            item_dir = root / "backlog"
            item_dir.mkdir()
            (item_dir / "one.md").write_text(_lines(7), encoding="utf-8")
            rev = _commit(root, "fixture")
            self.assertEqual(budget.board_lines(root, rev)["backlog.md"], 12)

    def test_oversized_item_files_reports_over_budget_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(2), encoding="utf-8")
            item_dir = root / "backlog"
            item_dir.mkdir()
            (item_dir / "small.md").write_text(_lines(5), encoding="utf-8")
            (item_dir / "big.md").write_text(_lines(20), encoding="utf-8")
            _commit(root, "fixture")
            over = budget.oversized_item_files(root, item_budget=15)
            self.assertEqual(over, {"backlog/big.md": 20})

    def test_counts_reports_items_over_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(2), encoding="utf-8")
            item_dir = root / "backlog"
            item_dir.mkdir()
            (item_dir / "big-one.md").write_text(_lines(16), encoding="utf-8")
            (item_dir / "big-two.md").write_text(_lines(30), encoding="utf-8")
            _commit(root, "fixture")
            got = budget.counts(root, line_budget=1000, image_budget=1024)
            self.assertEqual(got["items_over_budget"], 2)

    def test_oversized_item_files_never_fails_check(self) -> None:
        # The per-item budget is a report, not a gate (context_and_memory:
        # Boards) -- an over-budget item file must never fail `check` on its
        # own, unlike the board-total line budget.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _repo(root)
            (root / "backlog.md").write_text(_lines(2), encoding="utf-8")
            item_dir = root / "backlog"
            item_dir.mkdir()
            (item_dir / "huge.md").write_text(_lines(500), encoding="utf-8")
            _commit(root, "fixture")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--root", str(root),
                 "--line-budget", "1000"],
                capture_output=True, text=True, env=GIT_ENV,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("INFO", proc.stdout)
            self.assertIn("backlog/huge.md", proc.stdout)


if __name__ == "__main__":
    unittest.main()
