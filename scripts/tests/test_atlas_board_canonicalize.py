"""Tests for atlas-board-canonicalize.py.

Each test exercises a single canonicalization rule and asserts the new heading
plus body match the canonical form (heading) plus moved-note form (body).

The expected status word changed from `closed` to `done` because the original
assertions encoded a wrong spec, not because they were hard to satisfy: the
board's status set is todo / in-progress / blocked / review / done (AGENTS.md
`context_and_memory`), so canonicalizing onto `closed` — and preserving
`merged` and `delivered` besides — moved the corpus off the vocabulary the
board lint exists to enforce.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

spec = importlib.util.spec_from_file_location(
    "atlas_board_canonicalize",
    Path(__file__).resolve().parent.parent / "atlas-board-canonicalize.py",
)
abc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abc)


def test_canonical_done_with_date_is_already_canonical() -> None:
    """`done` plus a date is the canonical form, so the pass is a no-op."""
    heading = "## ATLAS-X-001 — Title [patch] — done 2026-08-29"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert not changed
    assert new_h == "## ATLAS-X-001 — Title [patch] — done 2026-08-29"
    assert new_b is None


def test_canonical_completed_no_date_uses_body_date() -> None:
    heading = "## ATLAS-X-002 [integration][perf] — completed"
    body = ["Done on 2026-08-26 by `abcd123`.", "Some prose."]
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert changed
    assert new_h == "## ATLAS-X-002 [integration][perf] — done 2026-08-26"
    assert new_b is None


def test_canonical_parens_extract_to_body() -> None:
    heading = "## ATLAS-X-003 — Title [patch] — closed 2026-08-25 (resolved upstream)"
    body = ["Original prose."]
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert changed
    assert new_h == "## ATLAS-X-003 — Title [patch] — done 2026-08-25"
    assert new_b is not None
    assert new_b[0] == "_Closure note (moved from heading):_ resolved upstream"
    assert new_b[2] == "Original prose."


def test_canonical_semicolon_extract_to_body() -> None:
    heading = "## ATLAS-X-004 — Title [patch] — done 2026-08-29; gate corrected 2026-09-01"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert changed
    assert new_h == "## ATLAS-X-004 — Title [patch] — done 2026-08-29"
    assert new_b is not None
    assert new_b[0] == "_Closure note (moved from heading):_ gate corrected 2026-09-01"


def test_archive_section_header_not_treated_as_item() -> None:
    heading = "## Archive — closed items"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert not changed
    assert new_h == heading


def test_in_progress_not_canonicalized() -> None:
    heading = "## ATLAS-X-005 — Title [patch] — in-progress (2026-08-25)"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert not changed
    assert new_h == heading


def test_todo_not_canonicalized() -> None:
    heading = "## ATLAS-X-006 — Title [patch] — todo"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert not changed


def test_already_canonical_no_change() -> None:
    heading = "## ATLAS-X-007 — Title [patch] — done 2026-08-25"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert not changed


def test_merged_normalizes_to_done() -> None:
    heading = "## ATLAS-X-008 — Title [patch] — merged 2026-08-25"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    # `merged` is a closure synonym, not a status: the set has one closed word.
    assert changed
    assert new_h == "## ATLAS-X-008 — Title [patch] — done 2026-08-25"


def test_delivered_normalizes_to_done() -> None:
    heading = "## ATLAS-X-009 — Title [patch] — delivered 2026-08-27"
    body: list[str] = []
    new_h, new_b, changed = abc.canonicalize_heading(heading, body)
    assert changed
    assert new_h == "## ATLAS-X-009 — Title [patch] — done 2026-08-27"


def test_trailing_anchor_survives_canonicalization() -> None:
    """The anchor is how ADRs, `Refs:` trailers and cross-board links address
    the item; dropping it while rewriting the status is exactly the edit that
    breaks every inbound reference."""
    heading = (
        "## ATLAS-X-020 — Title [patch] — closed 2026-08-25 "
        '<a id="atlas-x-020"></a>'
    )
    body: list[str] = []
    new_h, _, changed = abc.canonicalize_heading(heading, body)
    assert changed
    assert new_h == (
        '## ATLAS-X-020 — Title [patch] — done 2026-08-25 <a id="atlas-x-020"></a>'
    )


def test_anchor_survives_when_a_note_moves_to_the_body() -> None:
    heading = (
        "## ATLAS-X-021 — Title [patch] — closed 2026-08-25 (superseded) "
        '<a id="atlas-x-021"></a>'
    )
    new_h, new_b, changed = abc.canonicalize_heading(heading, [])
    assert changed
    assert new_h == (
        '## ATLAS-X-021 — Title [patch] — done 2026-08-25 <a id="atlas-x-021"></a>'
    )
    assert new_b is not None and "superseded" in new_b[0]


def test_split_items_handles_archive_preamble() -> None:
    text = (
        "# atlas backlog\n\n"
        "Some preamble text\n\n"
        "## Archive — closed items\n\n"
        "- **ATLAS-X-OLD** thing [patch] (2026-08-01) — `abc1234`\n\n"
    )
    lines = text.split("\n")
    preamble, items = abc.split_items(lines)
    # Preamble contains everything before the first ## heading
    assert preamble[0] == "# atlas backlog"
    assert "atlas backlog" in "\n".join(preamble)
    # Archive is a heading but is_closed(Archive) returns False, so the
    # canonicalization pass leaves it untouched in the items list.
    assert len(items) == 1
    assert items[0][0] == "## Archive — closed items"
    # Canonicalization leaves the Archive heading unchanged.
    new_h, new_b, changed = abc.canonicalize_heading(items[0][0], items[0][1])
    assert not changed


def test_full_board_processing_smoke() -> None:
    text = (
        "# board\n\n"
        "## ATLAS-X-001 — T1 [patch] — merged 2026-08-29\n\n"
        "Prose.\n\n"
        "## ATLAS-X-002 — T2 [patch] — completed\n\n"
        "Done 2026-08-26.\n\n"
        "## ATLAS-X-003 — T3 [patch] — in-progress\n\n"
        "Status: in-progress\n\n"
    )
    new_text, changes = abc.process_board(text)
    assert len(changes) == 2
    ids = [c[0] for c in changes]
    assert ids == ["ATLAS-X-001", "ATLAS-X-002"]
    assert "ATLAS-X-003" not in new_text or "in-progress" in new_text.split("ATLAS-X-003")[1].split("## ")[0]
    assert "done 2026-08-29" in new_text
    assert "done 2026-08-26" in new_text


def test_no_date_anywhere_leaves_the_status_word_bare() -> None:
    """A closure synonym still normalizes; the date is simply not invented."""
    heading = "## ATLAS-X-010 — Title [patch] — completed"
    body: list[str] = []
    new_h, _, changed = abc.canonicalize_heading(heading, body)
    assert changed
    assert new_h == "## ATLAS-X-010 — Title [patch] — done"


if __name__ == "__main__":
    import unittest

    unittest.main()