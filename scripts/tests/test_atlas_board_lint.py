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


class NextFreeTestCase(BoardLintUtilTestCase):
    def test_next_free_skips_hyphen_and_level_three_forms(self) -> None:
        board = self._board(
            "## ATLAS-ARCH-001 - first [patch]\n"
            "### ATLAS-ARCH-002 — sub-heading\n"
            "## ATLAS-ARCH-004 — fourth\n"
        )
        suggestion = _lint.next_free(board, "ATLAS-ARCH")
        self.assertEqual(suggestion, "ATLAS-ARCH-003")


if __name__ == "__main__":
    unittest.main()
