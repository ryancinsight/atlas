#!/usr/bin/env python3
"""Tests for atlas-board-compact.py delete semantics.

2026-09-18: the board policy changed from "collapse a closed item to a
one-line archive entry" to "delete it outright" — a board is a queue, not a
ledger, and a closed item's record is its merging PR plus `Item:` trailer,
not a board line. Report-genre narrative sections (Tier/Wave/Session/
Watchpoints/ledger prose, and the `## Archive — closed items` section
itself) delete the same way, with one exception: a narrative section that
still carries live signal (an open checkbox, or a reference to an item id
that is still open elsewhere) is kept and reported.

This file replaces the prior archive-preservation suite (which asserted the
opposite: that closed items' one-line entries and the old `## Archive`
section's body survived). It also adds regression coverage for the
classifier's structural fixes made alongside the delete-semantics change:
anchor attribution across a deleted predecessor, digit-free item ids, and
the paren-aware separator search that catches a status word sitting before
a trailing parenthetical.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-board-compact.py"
_SPEC = importlib.util.spec_from_file_location("atlas_board_compact", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_compact = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _compact
_SPEC.loader.exec_module(_compact)


ARCHIVE_HEADING = "## Archive — closed items"


def _run(text: str, heading: str = ARCHIVE_HEADING):
    with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
        path = Path(root) / "backlog.md"
        path.write_text(text, encoding="utf-8")
        result = _compact.compact(path, heading)
        out = path.read_text(encoding="utf-8")
    return out, result


class ClosedItemDeletionTestCase(unittest.TestCase):
    def test_closed_item_is_deleted_entirely(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            <a id="closed-one"></a>
            ## ATLAS-DONE-001 — a finished item [patch] — done 2026-09-01

            - Delivered in `deadbee`.

            ## ATLAS-LIVE-001 — active work [patch] — in-progress

            - Some live prose.
            """
        )
        out, (before, after, n_items, n_narr) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertEqual(n_narr, 0)
        self.assertNotIn("ATLAS-DONE-001", out)
        self.assertNotIn("closed-one", out)
        self.assertNotIn("deadbee", out)
        self.assertIn("## ATLAS-LIVE-001", out)
        self.assertIn("Some live prose.", out)
        self.assertLess(after, before)

    def test_open_item_survives_byte_identical(self) -> None:
        block = (
            "## ATLAS-LIVE-002 — still open [minor] — blocked (waiting on peer)\n"
            "\n"
            "- checkbox record: [x] and [ ] both stay, this is item prose.\n"
        )
        text = "# atlas — backlog\n\n" + block
        out, (_, _, n_items, n_narr) = _run(text)
        self.assertEqual((n_items, n_narr), (0, 0))
        self.assertIn(block.rstrip("\n"), out)

    def test_hyphen_style_closed_item_is_deleted(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-OLD-002 - Prerequisite status [minor] - done 2026-09-04 <a id="old-002"></a>

            - body text
            """
        )
        out, (_, _, n_items, _) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertNotIn("ATLAS-OLD-002", out)
        self.assertNotIn("old-002", out)

    def test_nested_parenthetical_closed_status_is_deleted(self) -> None:
        """A status word before a trailing parenthetical that itself
        contains a dash (`"... — ✅ closed (2026-07-23 Session 17 —
        migrated from peer draft)"`) must not be missed by a naive
        last-dash-anywhere split, which would land inside the parenthetical
        and see "migrated from peer draft)" instead of the real status."""
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-NESTED-001 — Some real sparse solver work [arch] — ✅ closed (2026-07-23 Session 17 — migrated from peer draft)

            - body
            """
        )
        out, (_, _, n_items, _) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertNotIn("ATLAS-NESTED-001", out)

    def test_status_word_only_in_title_is_not_deleted(self) -> None:
        """Conservative-direction regression: a title that merely contains
        a closed-vocabulary word, with no actual trailing status clause,
        must stay live."""
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-COEUS-LAYERNORM-SHAPE-031 — Complete multi-dimensional LayerNorm contract [minor] — in-progress

            - body
            """
        )
        out, (_, _, n_items, _) = _run(text)
        self.assertEqual(n_items, 0)
        self.assertIn("## ATLAS-COEUS-LAYERNORM-SHAPE-031", out)


class AnchorAttributionRegressionTestCase(unittest.TestCase):
    """split_items must attribute a preceding own-line anchor to the
    heading it precedes, not to the previous item's body — otherwise
    deleting the previous item silently drops the next item's anchor too,
    and deleting the *next* item while the previous one survives would
    otherwise leave the anchor stranded as orphaned text in a live item."""

    def test_anchor_of_a_surviving_item_is_not_lost_when_predecessor_is_deleted(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-DONE-010 — closed predecessor [patch] — done 2026-09-01

            - closed body

            <a id="live-011"></a>
            ## ATLAS-LIVE-011 — open successor [patch] — todo

            - open body
            """
        )
        out, (_, _, n_items, _) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertNotIn("ATLAS-DONE-010", out)
        self.assertIn('<a id="live-011"></a>', out)
        self.assertIn("## ATLAS-LIVE-011", out)

    def test_anchor_of_a_deleted_item_does_not_leak_into_the_predecessor(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-LIVE-020 — open predecessor [patch] — todo

            - open body

            <a id="done-021"></a>
            ## ATLAS-DONE-021 — closed successor [patch] — done 2026-09-01

            - closed body
            """
        )
        out, (_, _, n_items, _) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertIn("## ATLAS-LIVE-020", out)
        self.assertNotIn("done-021", out)
        self.assertNotIn("ATLAS-DONE-021", out)

    def test_inline_anchor_on_a_deleted_item_is_removed(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-DONE-030 - closed item [patch] - done 2026-09-01 <a id="done-030"></a>

            - body
            """
        )
        out, (_, _, n_items, _) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertNotIn("done-030", out)


class DigitFreeIdRegressionTestCase(unittest.TestCase):
    """ITEM_ID must recognize purely-alphabetic hyphenated ids
    (`ATLAS-CUDA-DRIVER-BOUNDARY`) as items, not fall through to narrative
    handling — a digit requirement previously misrouted these."""

    def test_digit_free_closed_id_is_recognized_and_deleted(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-CUDA-DRIVER-BOUNDARY — Own a correct dynamically loaded CUDA ABI — done 2026-09-09

            - body
            """
        )
        out, (_, _, n_items, n_narr) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertEqual(n_narr, 0)
        self.assertNotIn("ATLAS-CUDA-DRIVER-BOUNDARY", out)

    def test_digit_free_open_id_survives_and_registers_as_open(self) -> None:
        """A digit-free open id must count toward open_ids so a narrative
        section referencing it is kept, proving ITEM_ID (not some other
        path) is what makes it an item."""
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## Watchpoints — 2026-09-18 (coordinator view)

            still tracking ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION

            ## ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION — Complete ADR 0033 [arch][major] — todo

            - body
            """
        )
        out, (_, _, n_items, n_narr) = _run(text)
        self.assertEqual((n_items, n_narr), (0, 0))
        self.assertIn("## Watchpoints", out)
        self.assertIn("## ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION", out)


class OldArchiveSectionDeletionTestCase(unittest.TestCase):
    """The pre-existing `## Archive — closed items` ledger is report genre
    and is now deleted whole, never merged/preserved — including entries
    that used to collide on the shared "(unnumbered)" dedup label."""

    def test_prior_archive_section_is_deleted_entirely(self) -> None:
        text = textwrap.dedent(
            f"""\
            # atlas — backlog

            ## ATLAS-LIVE-040 — active work [patch] — in-progress

            - live prose

            {ARCHIVE_HEADING}

            Closed items, one line each. Full prose is in git history; commit
            SHAs below are the entry points.

            - **ATLAS-OLD-001** item one [patch] (2026-08-01) — `aaaaaaa`
            - **(unnumbered)** some old digit-free entry [patch] (2026-08-02) — `bbbbbbb`
            """
        )
        out, (_, _, n_items, n_narr) = _run(text)
        self.assertNotIn(ARCHIVE_HEADING, out)
        self.assertNotIn("ATLAS-OLD-001", out)
        self.assertNotIn("aaaaaaa", out)
        self.assertNotIn("bbbbbbb", out)
        self.assertIn("## ATLAS-LIVE-040", out)


class NarrativeSectionRuleTestCase(unittest.TestCase):
    def test_narrative_section_without_signal_is_deleted(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## Tier 0 — unsoundness and wrong numbers shipping

            Plain prose, no checkbox, no id reference.

            ## ATLAS-LIVE-050 — open item [patch] — todo

            - body
            """
        )
        out, (_, _, n_items, n_narr) = _run(text)
        self.assertEqual(n_narr, 1)
        self.assertNotIn("Tier 0", out)
        self.assertIn("## ATLAS-LIVE-050", out)

    def test_narrative_section_with_open_checkbox_is_kept(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## Watchpoints — 2026-07-19 (atlas-meta coordinator view)

            - [ ] confirm the runner capacity fix landed
            """
        )
        out, (_, _, _, n_narr) = _run(text)
        self.assertEqual(n_narr, 0)
        self.assertIn("## Watchpoints", out)
        self.assertIn("- [ ] confirm", out)

    def test_narrative_section_referencing_open_id_is_kept(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## Session 17 closure (2026-07-23) — notes

            See ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 for the residual.

            ## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — migrate direct_solver [minor] — todo

            - body
            """
        )
        out, (_, _, _, n_narr) = _run(text)
        self.assertEqual(n_narr, 0)
        self.assertIn("## Session 17 closure", out)

    def test_narrative_section_referencing_only_a_closed_id_is_deleted(self) -> None:
        """The exception is scoped to ids that are still OPEN; a narrative
        section whose only id reference is to an item that closed (and is
        therefore itself deleted) carries no live signal and deletes too."""
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## Session 18 closure (2026-07-24) — notes

            See ATLAS-HELIOS-BOOK-001 for detail.

            ## ATLAS-HELIOS-BOOK-001 — Helios book [minor] — done 2026-07-24

            - body
            """
        )
        out, (_, _, n_items, n_narr) = _run(text)
        self.assertEqual(n_items, 1)
        self.assertEqual(n_narr, 1)
        self.assertNotIn("Session 18 closure", out)
        self.assertNotIn("ATLAS-HELIOS-BOOK-001", out)


class IdempotenceTestCase(unittest.TestCase):
    def test_second_run_is_a_no_op(self) -> None:
        text = textwrap.dedent(
            """\
            # atlas — backlog

            ## ATLAS-DONE-060 — closed [patch] — done 2026-09-01

            - body

            ## Tier 0 — narrative, no signal

            prose

            ## ATLAS-LIVE-061 — open [patch] — todo

            - body
            """
        )
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            path = Path(root) / "backlog.md"
            path.write_text(text, encoding="utf-8")
            _compact.compact(path, ARCHIVE_HEADING)
            first = path.read_text(encoding="utf-8")
            before, after, n_items, n_narr = _compact.compact(path, ARCHIVE_HEADING)
            second = path.read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual((before, n_items, n_narr), (after, 0, 0))


class RootArgumentTestCase(unittest.TestCase):
    def test_root_argument_selects_another_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            board = Path(root) / "backlog.md"
            board.write_text(
                "# member — backlog\n\n"
                "## M-1 — closed [patch] — done 2026-09-02\n\n- `abc1234`\n",
                encoding="utf-8",
            )
            self.assertEqual(_compact.main([root]), 0)
            text = board.read_text(encoding="utf-8")
        self.assertNotIn("M-1", text)

    def test_missing_root_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            self.assertEqual(_compact.main([str(Path(root) / "absent")]), 2)


if __name__ == "__main__":
    unittest.main()
