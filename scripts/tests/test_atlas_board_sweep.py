#!/usr/bin/env python3
"""Tests for the report-only Atlas backlog sweep."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-board-sweep.py"
_SPEC = importlib.util.spec_from_file_location("atlas_board_sweep", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_sweep = importlib.util.module_from_spec(_SPEC)
# Python 3.14's dataclass resolver expects dynamically loaded modules to be
# present in sys.modules while annotations are evaluated.
sys.modules[_SPEC.name] = _sweep
_SPEC.loader.exec_module(_sweep)


class BacklogSweepTestCase(unittest.TestCase):
    def test_parses_status_variants_owner_and_claim_date(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-board-") as root_text:
            path = Path(root_text) / "backlog.md"
            path.write_text(
                "## ATLAS-HYGIENE-BASELINE-001 — Active work [patch] — in-progress\n"
                "- Owner: Alice (claimed 2026-08-07).\n"
                "\n"
                "## ATLAS-TWO — Another active work [patch] — in-progress\n"
                "- Owner: Bob; last-update: 2026-08-06\n",
                encoding="utf-8",
            )

            items = _sweep.parse_board(path)

        self.assertEqual([item.normalized_status for item in items], ["in progress", "in progress"])
        self.assertEqual(items[0].owner, "Alice (claimed 2026-08-07)")
        self.assertEqual(items[0].claim_dates, ["2026-08-07"])
        self.assertEqual(items[1].claim_dates, ["2026-08-06"])

    def test_ignores_unrelated_title_dates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-board-") as root_text:
            path = Path(root_text) / "backlog.md"
            path.write_text(
                "## ATLAS-DATE — Status note from 2026-08-07 [patch] — in progress\n"
                "- Owner: Alice.\n",
                encoding="utf-8",
            )

            item = _sweep.parse_board(path)[0]

        self.assertEqual(item.claim_dates, [])

    def test_reports_blocked_item_without_trigger_but_does_not_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-board-") as root_text:
            path = Path(root_text) / "backlog.md"
            path.write_text(
                "## ATLAS-BLOCKED — Waiting for provider [minor] — blocked\n"
                "- Owner: Unclaimed.\n",
                encoding="utf-8",
            )

            items = _sweep.parse_board(path)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = _sweep.report(items, str(path))

        self.assertEqual(exit_code, 0)
        self.assertIn("Blocked items missing a re-open trigger (1):", output.getvalue())
        self.assertIn("ATLAS-BLOCKED", output.getvalue())

    def test_reopen_trigger_is_detected_with_hyphen_or_space(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-board-") as root_text:
            path = Path(root_text) / "backlog.md"
            path.write_text(
                "## ATLAS-HYPHEN — Blocked [patch] — blocked\n"
                "- Re-open trigger: provider lands the seam.\n"
                "\n"
                "## ATLAS-SPACE — Blocked [patch] — blocked\n"
                "- Re open trigger: consumer returns to main.\n"
                "\n"
                "## ATLAS-QUALIFIED — Blocked [patch] — blocked\n"
                "- Re-open trigger (for the claiming session): owner returns to main.\n",
                encoding="utf-8",
            )

            items = _sweep.parse_board(path)

        self.assertTrue(all(item.has_reopen_trigger for item in items))

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = _sweep.report(items, str(path))
        self.assertEqual(exit_code, 0)
        self.assertIn("Blocked items missing a re-open trigger (0):", output.getvalue())

    def test_nonexistent_board_returns_invocation_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-board-") as root_text:
            missing = Path(root_text) / "missing.md"
            captured = io.StringIO()
            with contextlib.redirect_stderr(captured):
                exit_code = _sweep.main(["--file", str(missing)])

        self.assertEqual(exit_code, 2)
        self.assertIn("cannot read board file", captured.getvalue())

    def test_empty_board_is_a_successful_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-board-") as root_text:
            path = Path(root_text) / "backlog.md"
            path.write_text("# Empty\n", encoding="utf-8")

            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = _sweep.main(["--file", str(path)])

        self.assertEqual(exit_code, 0)
        self.assertIn("0 items scanned", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
