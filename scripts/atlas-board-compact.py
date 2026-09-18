#!/usr/bin/env python3
"""Compact a PM board: keep live items in full, delete closed ones outright.

`context_and_memory` (Boards) states the board's own law: "a board is a
queue, never a ledger". A closed item's record is the PR that closed it plus
its `Item:` trailer (`git log --grep='^Item: <id>'` recovers it) — the board
entry is not the record, so once an item closes it deletes, not archives.
Report genre (an `## Archive — closed items` ledger, session/wave/tier/batch
narratives, coordination and watchpoint logs) is the same kind of stale
duplicate state and deletes with it: it duplicates what git history already
holds and rots the moment nothing regenerates it.

Closed items and non-item narrative sections delete outright: heading,
its anchor (own-line or inline), and its body. The one exception is a
narrative section whose body still carries live signal a plain `git log`
search would not surface as directly: an open checkbox (`- [ ]`) or a
reference to an item id that is still open elsewhere on the board. That
section is kept verbatim and reported for triage at its next touch.

This is the mechanical half of that rule, so the deletion is reproducible
rather than a one-off hand edit. It is deliberately conservative on
classification: an item deletes only when its heading carries an
unambiguous closed marker, and anything the classifier cannot place is left
untouched in the live board for a human to triage. Conservative and
irreversible are different axes — under-classifying a closed item as "leave
it" costs a stale line; over-classifying a live item as "delete it" costs
the item, so the classifier only ever loosens what counts as a *separator*
between title and status (em-dash, hyphen, or one nested inside a trailing
parenthetical), never what counts as a *status word* once split from it.

Run from anywhere: paths anchor to this file's parent repository unless a
root is given, so one compactor serves every member board in the stack.

Checkbox-bullet records (`- [x] **ID — title.** ...`) inside a *live,
id-bearing* item's body are part of that item's prose, not a narrative
section, and stay verbatim regardless of checkbox state: the collapse unit
is the level-2 heading, so an open item that keeps measured-rejection
records in full loses nothing. The open-checkbox exception above applies
only to narrative (non-id) sections, which have no other record of their
own.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A heading is closed only when its FINAL separator's segment is a status
# clause. Matching anywhere after a separator would archive live items whose
# *title* merely contains a status word — e.g. "ATLAS-COEUS-LAYERNORM-
# SHAPE-031 — Complete multi-dimensional LayerNorm contract [minor] —
# in-progress" is in-progress, not complete. Under-classifying (leaving a
# closed item live) is safe; over-classifying (deleting a live item) is not.
#
# 2026-09-18 extension: this board also carries delivered/resolved/superseded/
# landed/fixed/implemented/adopted/rejected as terminal statuses, and a large
# older stratum separates the status with " - " (hyphen) instead of an em-dash
# (`ATLAS-PREREQ-EXECUTION-2026-09-03 - ... [minor] - done 2026-09-04`). Both
# gaps under-classified real closed items rather than over-classifying
# anything, so widening them keeps the conservative direction: a heading only
# closes when its final separator segment STARTS WITH one of these words,
# never when the word merely appears inside the title.
CLOSED = re.compile(
    r"^\s*(?:✅\s*)?(?:complete|completed|done|closed|merged|delivered|"
    r"resolved|superseded|landed|fixed|implemented|adopted|rejected)\b",
    re.I,
)
# Bare-tick form used by a handful of older kwavers entries.
CLOSED_TICK = re.compile(r"✓\s*DONE\b", re.I)
# 2026-09-18: no digit requirement — several genuine ids on this board are
# purely alphabetic (`ATLAS-CUDA-DRIVER-BOUNDARY`,
# `ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION`). The digit requirement forced every
# such id to a shared empty label, and since MULTIPLE distinct no-digit ids
# then collided on that one literal key, an id-matching step keyed on the
# label (as the prior archive-dedup step was) silently conflated unrelated
# items. Requiring only "id-like" (a capitalized token with at least one
# hyphen) keeps narrative, non-item headings (`## Tier 0 — ...`, `## Session
# 17 closure ...`) out, since those start with a plain word, not a
# hyphenated all-caps token.
ITEM_ID = re.compile(r"^##\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)")
# An anchor on its own line immediately (blank lines aside) above a heading,
# or inline at the tail of the heading itself.
ANCHOR_OWN_LINE = re.compile(r'^<a id="[^"]+"></a>\s*$')
ANCHOR_INLINE = re.compile(r'\s*(<a id="[^"]+"></a>)\s*')
# Narrative-section keep exception: an unfiled open TODO, or a reference to
# an item id that is still open elsewhere on the board.
CHECKBOX_OPEN = re.compile(r"^\s*-\s*\[ \]", re.M)
ID_TOKEN = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b")


def _top_level_separators(heading: str) -> list[tuple[int, int]]:
    """Positions of every ' — ' / ' - ' at parenthesis/bracket depth 0.

    A trailing parenthetical can itself contain a dash — `"✅ closed
    (2026-07-23 Session 17 — migrated from peer draft)"` — and a plain
    rsplit on the last dash anywhere lands inside it, missing the real
    status clause that precedes the parenthetical. Skipping nested spans
    finds the separator that actually divides title from status.
    """
    spans = []
    depth = 0
    i, n = 0, len(heading)
    while i < n:
        c = heading[i]
        if c in "([":
            depth += 1
            i += 1
            continue
        if c in ")]":
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0:
            if heading[i : i + 3] == " — ":
                spans.append((i, i + 3))
                i += 3
                continue
            if i + 2 < n and heading[i] == " " and heading[i + 1] == "-" and heading[i + 2] == " ":
                spans.append((i, i + 3))
                i += 3
                continue
        i += 1
    return spans


def _status_split(heading: str) -> tuple[str, str] | None:
    """Split on the LAST top-level separator, if that tail is a status
    clause. Returns (before, status_tail) or None when it is not."""
    spans = _top_level_separators(heading)
    if not spans:
        return None
    before, tail = heading[: spans[-1][0]], heading[spans[-1][1] :]
    if CLOSED.match(tail.strip()):
        return before, tail
    return None


def is_closed(heading: str) -> bool:
    """Closed only when the last top-level separator's segment is a status clause."""
    if CLOSED_TICK.search(heading):
        return True
    return _status_split(heading) is not None


def split_items(
    lines: list[str],
) -> tuple[list[str], list[tuple[str | None, list[str], str, list[str]]]]:
    """Return (preamble, [(anchor_line, prefix_blanks, heading, body_lines), ...])
    split on level-2 headings.

    An `<a id="...">` line directly above a heading (blank lines permitted
    between them) belongs to THAT heading's item, not to the previous one's
    body — otherwise deleting the predecessor silently drops the
    successor's anchor along with it (a deleted item contributes nothing to
    the output, so any line misattributed to it vanishes too).
    """
    starts = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    if not starts:
        return lines, []
    block_starts = []
    for s in starts:
        j = s - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        if j >= 0 and ANCHOR_OWN_LINE.match(lines[j]):
            block_starts.append(j)
        else:
            block_starts.append(s)
    preamble = lines[: block_starts[0]]
    items = []
    for n, bstart in enumerate(block_starts):
        bend = block_starts[n + 1] if n + 1 < len(block_starts) else len(lines)
        heading_idx = starts[n]
        anchor_line = lines[bstart] if bstart != heading_idx else None
        prefix_blanks = lines[bstart + 1 : heading_idx] if anchor_line else []
        body = lines[heading_idx + 1 : bend]
        items.append((anchor_line, prefix_blanks, lines[heading_idx], body))
    return preamble, items


def narrative_keep_reason(body: list[str], open_ids: set[str]) -> str | None:
    """Why a narrative (non-id) section survives deletion, or None to delete it.

    A narrative section is report genre by default (Tier/Wave/Session/
    Watchpoints/ledger prose): it duplicates git history and rots. It stays
    only when it carries signal nothing else holds — an open checkbox, or a
    mention of an item id that is still open elsewhere on the board (a
    cross-reference a human should see before the section is dropped).
    """
    text = "\n".join(body)
    if CHECKBOX_OPEN.search(text):
        return "open checkbox"
    for tok in ID_TOKEN.findall(text):
        if tok in open_ids:
            return f"references open {tok}"
    return None


def compact(path: Path, archive_heading: str) -> tuple[int, int, int, int]:
    """Rewrite `path` in place. Returns (lines_before, lines_after,
    items_deleted, narrative_sections_deleted)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    before = len(lines)
    preamble, items = split_items(lines)

    # The old archive/ledger section is report genre like any other
    # narrative section — delete it outright rather than special-casing its
    # preservation. Its per-item lines carried no id git can't already
    # resolve, and it is exactly the growing-ledger shape the board-is-a-
    # queue rule now forbids.
    kept_items = [it for it in items if not it[2].startswith(archive_heading)]

    # Pass 1: classify every id-bearing heading and collect which ids stay
    # open, so pass 2's narrative exception can check cross-references.
    classified: list[tuple[str | None, list[str], str, list[str], bool, bool]] = []
    open_ids: set[str] = set()
    for anchor_line, prefix_blanks, heading, body in kept_items:
        m = ITEM_ID.match(heading)
        is_item = m is not None
        closed = is_item and is_closed(heading)
        if is_item and not closed:
            open_ids.add(m.group(1))
        classified.append((anchor_line, prefix_blanks, heading, body, is_item, closed))

    # Pass 2: assemble the surviving blocks in original order.
    out_blocks: list[list[str]] = []
    items_deleted = 0
    narrative_deleted = 0
    kept_narrative: list[tuple[str, str]] = []
    for anchor_line, prefix_blanks, heading, body, is_item, closed in classified:
        if is_item:
            if closed:
                items_deleted += 1
                continue
            keep = True
        else:
            reason = narrative_keep_reason(body, open_ids)
            if reason is None:
                narrative_deleted += 1
                continue
            kept_narrative.append((heading, reason))
            keep = True
        if keep:
            block = []
            if anchor_line is not None:
                block.append(anchor_line)
            block.extend(prefix_blanks)
            block.append(heading)
            block.extend(body)
            out_blocks.append(block)

    out = list(preamble)
    for block in out_blocks:
        out.extend(block)
    # Trim trailing blanks the deleted tail may have left behind.
    while len(out) > 1 and not out[-1].strip() and not out[-2].strip():
        out.pop()

    # `newline=""`: text mode on Windows would translate every "\n" to CRLF; the
    # board is committed LF (`.gitattributes`), and a CRLF working copy is churn.
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="")
    return before, len(out), items_deleted, narrative_deleted


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report the counts without writing")
    ap.add_argument("root", nargs="?", type=Path, default=ROOT,
                    help="repository root whose backlog.md/checklist.md to "
                         "compact (default: the repository holding this script)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 2

    targets = [
        (root / "backlog.md", "## Archive — closed items"),
        (root / "checklist.md", "## Archive — closed checklists"),
    ]
    for path, heading in targets:
        if not path.is_file():
            print(f"skip (absent): {path.name}")
            continue
        if args.dry_run:
            lines = path.read_text(encoding="utf-8").splitlines()
            _, items = split_items(lines)
            kept = [
                (a, p, h, b) for a, p, h, b in items
                if not h.startswith(heading)
            ]
            item_count = sum(1 for _, _, h, _ in kept if ITEM_ID.match(h))
            closed = sum(
                1 for _, _, h, _ in kept if ITEM_ID.match(h) and is_closed(h)
            )
            narrative = len(kept) - item_count
            print(f"{path.name}: {len(lines)} lines, {item_count} items "
                  f"({closed} would delete), {narrative} narrative sections")
            continue
        before, after, n_items, n_narrative = compact(path, heading)
        print(f"{path.name}: {before} -> {after} lines "
              f"({n_items} items deleted, {n_narrative} narrative sections deleted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
