#!/usr/bin/env python3
"""Tests for atlas-board-lint.py duplicate-id and reference gates.

The duplicate-id gate is the hard gate: an item id is an anchor cited by
ADRs, commits, and claims, so two headings sharing one id make every
inbound reference ambiguous. The gate must recognize every heading form the
board carries — level-2 and level-3, em-dash and hyphen separators — or a
duplicate defined via a form the reference scanner sees but the collision
scanner does not escapes the hard gate.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-board-lint.py"
_SPEC = importlib.util.spec_from_file_location("atlas_board_lint", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_lint = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _lint
_SPEC.loader.exec_module(_lint)


class BoardLintUtilTestCase(unittest.TestCase):
    """Base with a per-test temp directory that lives for the test's lifetime."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-board-lint-")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _board(self, text: str) -> Path:
        path = Path(self._tmp.name) / "backlog.md"
        path.write_text(text, encoding="utf-8", errors="replace")
        return path


class CollisionsTestCase(BoardLintUtilTestCase):
    def test_duplicate_em_dash_heading_is_flagged(self) -> None:
        board = self._board(
            "## ATLAS-AUDIT-001 — first [patch] — in-progress\n"
            "## ATLAS-AUDIT-001 — second [minor] — done\n"
        )
        dupes = _lint.collisions(board)
        self.assertIn("ATLAS-AUDIT-001", dupes)
        self.assertEqual(len(dupes["ATLAS-AUDIT-001"]), 2)

    def test_duplicate_hyphen_separated_heading_is_flagged(self) -> None:
        # A hyphen separator (older board era) must not escape the gate.
        board = self._board(
            "## ATLAS-AUDIT-001 - first [patch] - in-progress\n"
            "## ATLAS-AUDIT-001 - second [patch] - done\n"
        )
        dupes = _lint.collisions(board)
        self.assertIn("ATLAS-AUDIT-001", dupes)
        self.assertEqual(len(dupes["ATLAS-AUDIT-001"]), 2)

    def test_duplicate_level_three_heading_is_flagged(self) -> None:
        # A `###` sub-heading that defines a duplicate id is invisible to an
        # em-dash-only level-2 match; the gate must still catch it.
        board = self._board(
            "## ATLAS-GMRES-001 — consolidate [major] — closed\n"
            "### ATLAS-GMRES-001 — CORRECTED: owner is athena\n"
        )
        dupes = _lint.collisions(board)
        self.assertIn("ATLAS-GMRES-001", dupes)
        self.assertEqual(len(dupes["ATLAS-GMRES-001"]), 2)

    def test_unique_ids_are_not_flagged(self) -> None:
        board = self._board(
            "## ATLAS-AUDIT-001 — first [patch] — in-progress\n"
            "## ATLAS-AUDIT-002 — second [patch] — done\n"
            "### ATLAS-AUDIT-003 — sub-note\n"
        )
        dupes = _lint.collisions(board)
        self.assertEqual(dupes, {})

    def test_headings_without_atlas_id_are_ignored(self) -> None:
        board = self._board("## Not an item — prose\n## ATLAS-AUDIT-001 — one\n")
        dupes = _lint.collisions(board)
        self.assertEqual(dupes, {})

    def test_original_specification_appendix_does_not_collide(self) -> None:
        # The board attaches an item's original specification as a second
        # heading under the SAME id. The id still resolves to one item, so
        # this is an appendix, not the anchor ambiguity the gate exists for.
        board = self._board(
            "## ATLAS-DMRI-IO-001 — Rank-generic acquisition-series I/O [minor] — in-progress\n"
            "## ATLAS-DMRI-IO-001 original specification\n"
        )
        dupes = _lint.collisions(board)
        self.assertEqual(dupes, {})

    def test_appendix_suffix_must_be_exact(self) -> None:
        # Only the exact `original specification` suffix is exempt; any other
        # trailing text keeps the heading a full item definition.
        board = self._board(
            "## ATLAS-AUDIT-001 — first — in-progress\n"
            "## ATLAS-AUDIT-001 original specification and other matter\n"
        )
        dupes = _lint.collisions(board)
        self.assertIn("ATLAS-AUDIT-001", dupes)
        self.assertEqual(len(dupes["ATLAS-AUDIT-001"]), 2)

    def test_appendix_exempt_id_still_collides_with_a_real_duplicate(self) -> None:
        # Exempting the appendix must not blind the gate to a genuine second
        # item reusing the id elsewhere in the board.
        board = self._board(
            "## ATLAS-AUDIT-001 — first — in-progress\n"
            "## ATLAS-AUDIT-001 original specification\n"
            "## ATLAS-AUDIT-001 — a different item — done\n"
        )
        dupes = _lint.collisions(board)
        self.assertIn("ATLAS-AUDIT-001", dupes)
        self.assertEqual(len(dupes["ATLAS-AUDIT-001"]), 2)


class NextFreeTestCase(BoardLintUtilTestCase):
    def test_next_free_skips_hyphen_and_level_three_forms(self) -> None:
        board = self._board(
            "## ATLAS-ARCH-001 - first [patch]\n"
            "### ATLAS-ARCH-002 — sub-heading\n"
            "## ATLAS-ARCH-004 — fourth\n"
        )
        suggestion = _lint.next_free(board, "ATLAS-ARCH")
        self.assertEqual(suggestion, "ATLAS-ARCH-003")


class IndexedLayoutTestCase(BoardLintUtilTestCase):
    """Past about forty open items a board moves bodies to
    `backlog/<anchor>.md` with `backlog.md` as their generated index
    (`atlas-board-index.py`); every check must see ids and control
    characters wherever the migration put them."""

    def _item_dir(self) -> Path:
        item_dir = Path(self._tmp.name) / "backlog"
        item_dir.mkdir(exist_ok=True)
        return item_dir

    def test_collisions_across_finds_a_duplicate_id_in_two_item_files(self) -> None:
        item_dir = self._item_dir()
        (item_dir / "a.md").write_text(
            '<a id="a"></a>\n## ATLAS-DUP-100 — first [patch] — todo\n', encoding="utf-8"
        )
        (item_dir / "b.md").write_text(
            '<a id="b"></a>\n## ATLAS-DUP-100 — second [patch] — done\n', encoding="utf-8"
        )
        dupes = _lint.collisions_across([item_dir / "a.md", item_dir / "b.md"])
        self.assertIn("ATLAS-DUP-100", dupes)
        self.assertEqual(len(dupes["ATLAS-DUP-100"]), 2)

    def test_collisions_across_unique_ids_across_files_are_not_flagged(self) -> None:
        item_dir = self._item_dir()
        (item_dir / "a.md").write_text(
            '<a id="a"></a>\n## ATLAS-UNIQ-100 — first [patch] — todo\n', encoding="utf-8"
        )
        (item_dir / "b.md").write_text(
            '<a id="b"></a>\n## ATLAS-UNIQ-101 — second [patch] — todo\n', encoding="utf-8"
        )
        dupes = _lint.collisions_across([item_dir / "a.md", item_dir / "b.md"])
        self.assertEqual(dupes, {})

    def test_next_free_across_scans_every_item_file(self) -> None:
        item_dir = self._item_dir()
        (item_dir / "a.md").write_text("## ATLAS-FAM-001 — one\n", encoding="utf-8")
        (item_dir / "b.md").write_text("## ATLAS-FAM-002 — two\n", encoding="utf-8")
        suggestion = _lint.next_free_across([item_dir / "a.md", item_dir / "b.md"], "ATLAS-FAM")
        self.assertEqual(suggestion, "ATLAS-FAM-003")

    def test_main_finds_duplicate_id_across_item_files(self) -> None:
        item_dir = self._item_dir()
        (item_dir / "a.md").write_text(
            '<a id="a"></a>\n## ATLAS-DUP-200 — first [patch] — todo\n', encoding="utf-8"
        )
        (item_dir / "b.md").write_text(
            '<a id="b"></a>\n## ATLAS-DUP-200 — second [patch] — done\n', encoding="utf-8"
        )
        board = Path(self._tmp.name) / "backlog.md"
        board.write_text(
            '<a id="a"></a>- [ATLAS-DUP-200](backlog/a.md) — first [patch] — todo\n'
            '<a id="b"></a>- [ATLAS-DUP-200](backlog/b.md) — second [patch] — done\n',
            encoding="utf-8",
        )
        old_argv = sys.argv
        old_root = _lint.ROOT
        sys.argv = ["atlas-board-lint.py", "--file", "backlog.md"]
        _lint.ROOT = Path(self._tmp.name)
        try:
            rc = _lint.main()
        finally:
            sys.argv = old_argv
            _lint.ROOT = old_root
        self.assertEqual(rc, 1)

    def test_main_reports_unique_ids_for_a_clean_indexed_board(self) -> None:
        item_dir = self._item_dir()
        (item_dir / "a.md").write_text(
            '<a id="a"></a>\n## ATLAS-CLEAN-100 — first [patch] — todo\n', encoding="utf-8"
        )
        board = Path(self._tmp.name) / "backlog.md"
        board.write_text(
            '<a id="a"></a>- [ATLAS-CLEAN-100](backlog/a.md) — first [patch] — todo\n',
            encoding="utf-8",
        )
        old_argv = sys.argv
        old_root = _lint.ROOT
        sys.argv = ["atlas-board-lint.py", "--file", "backlog.md"]
        _lint.ROOT = Path(self._tmp.name)
        try:
            rc = _lint.main()
        finally:
            sys.argv = old_argv
            _lint.ROOT = old_root
        self.assertEqual(rc, 0)

    def test_main_reports_control_characters_in_an_item_file(self) -> None:
        item_dir = self._item_dir()
        (item_dir / "a.md").write_bytes(
            b'<a id="a"></a>\n## ATLAS-CTRL-100 \xe2\x80\x94 item [patch] \xe2\x80\x94 todo\n'
            b"- Path D:\x07tlas\\repos\n"
        )
        board = Path(self._tmp.name) / "backlog.md"
        board.write_text(
            '<a id="a"></a>- [ATLAS-CTRL-100](backlog/a.md) \u2014 item [patch] \u2014 todo\n',
            encoding="utf-8",
        )
        old_argv = sys.argv
        old_root = _lint.ROOT
        sys.argv = ["atlas-board-lint.py", "--file", "backlog.md"]
        _lint.ROOT = Path(self._tmp.name)
        try:
            rc = _lint.main()
        finally:
            sys.argv = old_argv
            _lint.ROOT = old_root
        self.assertEqual(rc, 1)


class ControlCharacterTestCase(unittest.TestCase):
    """A board line carrying an interpreted escape fails the lint."""

    def test_a_bel_from_an_escaped_windows_path_is_named_by_line(self) -> None:
        with tempfile.TemporaryDirectory(prefix="board-lint-") as temp:
            board = Path(temp) / "backlog.md"
            board.write_bytes(
                b"# Backlog\n\n## ATLAS-X-1 \xe2\x80\x94 Item [patch] \xe2\x80\x94 todo\n"
                b"- Path D:\x07tlas\\repos\r\n"
            )
            found = _lint.control_characters(board)
        self.assertEqual([lineno for lineno, _ in found], [4])
        self.assertIn("\\x07", found[0][1])

    def test_line_endings_and_plain_text_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="board-lint-") as temp:
            board = Path(temp) / "backlog.md"
            board.write_bytes(b"# Backlog\r\n\r\n- D:\\atlas\\repos\n")
            self.assertEqual(_lint.control_characters(board), [])

    def test_a_tab_is_an_interpreted_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="board-lint-") as temp:
            board = Path(temp) / "backlog.md"
            board.write_bytes(b"- D:\\atlas\target\n")
            self.assertEqual([lineno for lineno, _ in _lint.control_characters(board)], [1])


if __name__ == "__main__":
    unittest.main()
