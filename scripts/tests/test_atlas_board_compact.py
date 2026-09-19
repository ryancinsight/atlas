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


class IndexedLayoutTestCase(unittest.TestCase):
    """Past about forty open items a board moves bodies to
    `backlog/<anchor>.md` with `backlog.md` as their generated index
    (`atlas-board-index.py`). Compaction there deletes a closed item's file
    outright and regenerates the index, rather than deleting a line range."""

    def _indexed_root(self, index_lines: str, items: dict[str, str], preamble: str = "# atlas — backlog") -> Path:
        tmp = tempfile.TemporaryDirectory(prefix="atlas-compact-indexed-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        item_dir = root / "backlog"
        item_dir.mkdir()
        for name, text in items.items():
            (item_dir / name).write_text(text, encoding="utf-8")
        (root / "backlog.md").write_text(
            preamble + "\n\n" + index_lines, encoding="utf-8"
        )
        return root

    def test_is_indexed_board_requires_sibling_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-compact-plain-") as root:
            board = Path(root) / "backlog.md"
            board.write_text("# atlas\n", encoding="utf-8")
            self.assertFalse(_compact.is_indexed_board(board))
            (Path(root) / "backlog").mkdir()
            self.assertTrue(_compact.is_indexed_board(board))

    def test_closed_item_file_is_deleted_and_index_regenerated(self) -> None:
        root = self._indexed_root(
            index_lines=(
                '<a id="done-one"></a>- [ATLAS-DONE-070](backlog/done-one.md) — closed one [patch] — done\n'
                '<a id="live-one"></a>- [ATLAS-LIVE-070](backlog/live-one.md) — open one [patch] — todo\n'
            ),
            items={
                "done-one.md": '<a id="done-one"></a>\n## ATLAS-DONE-070 — closed one [patch] — done\n\n- delivered\n',
                "live-one.md": '<a id="live-one"></a>\n## ATLAS-LIVE-070 — open one [patch] — todo\n\n- body\n',
            },
        )
        board = root / "backlog.md"
        before, after, n_items, n_narr = _compact.compact_indexed(board, "## Archive — closed items")
        self.assertEqual(n_items, 1)
        self.assertEqual(n_narr, 0)
        self.assertLess(after, before)
        self.assertFalse((root / "backlog" / "done-one.md").exists())
        self.assertTrue((root / "backlog" / "live-one.md").exists())
        index_text = board.read_text(encoding="utf-8")
        self.assertNotIn("ATLAS-DONE-070", index_text)
        self.assertIn("ATLAS-LIVE-070", index_text)

    def test_index_stays_fresh_after_compaction(self) -> None:
        """The regenerated backlog.md must already be what
        `atlas-board-index.py generate` would produce -- a `check` right
        after compaction passes with no further edit."""
        root = self._indexed_root(
            index_lines=(
                '<a id="done-two"></a>- [ATLAS-DONE-071](backlog/done-two.md) — closed two [patch] — done\n'
                '<a id="live-two"></a>- [ATLAS-LIVE-071](backlog/live-two.md) — open two [patch] — todo\n'
            ),
            items={
                "done-two.md": '<a id="done-two"></a>\n## ATLAS-DONE-071 — closed two [patch] — done\n\n- delivered\n',
                "live-two.md": '<a id="live-two"></a>\n## ATLAS-LIVE-071 — open two [patch] — todo\n\n- body\n',
            },
        )
        board = root / "backlog.md"
        _compact.compact_indexed(board, "## Archive — closed items")

        index_mod = _compact._load_index_module()
        self.assertEqual(
            board.read_text(encoding="utf-8"), index_mod.generate_text(root)
        )

    def test_no_closed_items_is_a_no_op(self) -> None:
        root = self._indexed_root(
            index_lines='<a id="live-three"></a>- [ATLAS-LIVE-072](backlog/live-three.md) — open three [patch] — in-progress\n',
            items={
                "live-three.md": '<a id="live-three"></a>\n## ATLAS-LIVE-072 — open three [patch] — in-progress\n\n- body\n',
            },
        )
        board = root / "backlog.md"
        before_text = board.read_text(encoding="utf-8")
        before, after, n_items, n_narr = _compact.compact_indexed(board, "## Archive — closed items")
        self.assertEqual((n_items, n_narr), (0, 0))
        self.assertEqual(before, after)
        self.assertEqual(board.read_text(encoding="utf-8"), before_text)

    def test_preamble_narrative_section_without_signal_is_deleted(self) -> None:
        root = self._indexed_root(
            preamble=(
                "# atlas — backlog\n\n"
                "## Tier 0 — unsoundness and wrong numbers shipping\n\n"
                "Plain prose, no checkbox, no id reference."
            ),
            index_lines='<a id="live-four"></a>- [ATLAS-LIVE-073](backlog/live-four.md) — open four [patch] — todo\n',
            items={
                "live-four.md": '<a id="live-four"></a>\n## ATLAS-LIVE-073 — open four [patch] — todo\n\n- body\n',
            },
        )
        board = root / "backlog.md"
        _, _, n_items, n_narr = _compact.compact_indexed(board, "## Archive — closed items")
        self.assertEqual(n_narr, 1)
        self.assertNotIn("Tier 0", board.read_text(encoding="utf-8"))

    def test_preamble_narrative_section_referencing_open_id_is_kept(self) -> None:
        root = self._indexed_root(
            preamble=(
                "# atlas — backlog\n\n"
                "## Session 17 closure — notes\n\n"
                "See ATLAS-LIVE-074 for the residual."
            ),
            index_lines='<a id="live-five"></a>- [ATLAS-LIVE-074](backlog/live-five.md) — open five [patch] — todo\n',
            items={
                "live-five.md": '<a id="live-five"></a>\n## ATLAS-LIVE-074 — open five [patch] — todo\n\n- body\n',
            },
        )
        board = root / "backlog.md"
        _, _, _, n_narr = _compact.compact_indexed(board, "## Archive — closed items")
        self.assertEqual(n_narr, 0)
        self.assertIn("## Session 17 closure", board.read_text(encoding="utf-8"))

    def test_main_dispatches_to_indexed_layout(self) -> None:
        root = self._indexed_root(
            index_lines='<a id="done-eighty"></a>- [ATLAS-DONE-080](backlog/done-eighty.md) — closed [patch] — done\n',
            items={
                "done-eighty.md": '<a id="done-eighty"></a>\n## ATLAS-DONE-080 — closed [patch] — done\n\n- delivered\n',
            },
        )
        self.assertEqual(_compact.main([str(root)]), 0)
        self.assertFalse((root / "backlog" / "done-eighty.md").exists())

    def test_dry_run_does_not_write(self) -> None:
        root = self._indexed_root(
            index_lines='<a id="done-ninety"></a>- [ATLAS-DONE-090](backlog/done-ninety.md) — closed [patch] — done\n',
            items={
                "done-ninety.md": '<a id="done-ninety"></a>\n## ATLAS-DONE-090 — closed [patch] — done\n\n- delivered\n',
            },
        )
        before_text = (root / "backlog.md").read_text(encoding="utf-8")
        self.assertEqual(_compact.main(["--dry-run", str(root)]), 0)
        self.assertEqual((root / "backlog.md").read_text(encoding="utf-8"), before_text)
        self.assertTrue((root / "backlog" / "done-ninety.md").exists())


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
