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

Per-item-file layout (`backlog.md` + `backlog/<anchor>.md`, past the
forty-item threshold, `atlas-board-index.py`): a `backlog.md` with a
sibling `backlog/` directory is in this layout, and compaction there works
at file granularity instead of line ranges -- a closed item's
`backlog/<anchor>.md` is deleted outright and the index is regenerated to
drop its line, while narrative sections (which stay inline in `backlog.md`'s
preamble under this layout, per the migration) are classified exactly as
above. A board with no sibling `backlog/` directory (checklist.md,
gap_audit.md, a member repository's own backlog.md) compacts by the
original inline logic, unchanged.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas_board_items import (  # noqa: E402
    ANCHOR_OWN_LINE,
    INDEX_LINE,
    ITEM_ID,
    top_level_separators as _top_level_separators,
)

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
# Narrative-section keep exception: an unfiled open TODO, or a reference to
# an item id that is still open elsewhere on the board.
CHECKBOX_OPEN = re.compile(r"^\s*-\s*\[ \]", re.M)
# Risk-artifact (gap_audit) classification. A finding records its status in
# its prose, so the heading clause `is_closed` reads never fires there. Both
# halves are required: an explicit closure signal, and no open signal
# anywhere in the body -- a finding whose prose carries one fixed half and
# one open half is exactly the case that must survive whole.
BODY_CLOSED = re.compile(
    r"\b(?:closed|resolved|fixed in|landed|superseded|no action needed|"
    r"completed?)\b",
    re.I,
)
BODY_OPEN = re.compile(
    r"^\s*-\s*\[ \]|re-?open trigger|\*\*open\b|still open|remains? open|"
    r"\bnot yet\b|\btodo\b|\bblocked\b|\bawaiting\b",
    re.I | re.M,
)
ID_TOKEN = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b")


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


def body_is_closed(body: list[str], heading: str = "") -> bool:
    """Whether a risk-artifact finding records itself as closed.

    Closure must be stated and nothing may contradict it. The open half is
    checked first because a finding that says both is live: `**Fixed** ...
    **Open** ...` is one finding with work left, not two. The heading joins
    the text under test because a finding can carry its open half there and
    nowhere else -- "Provider PR hosted closure remains open" was deleted by
    a body-only read.
    """
    text = "\n".join([heading, *body])
    if BODY_OPEN.search(text):
        return False
    return BODY_CLOSED.search(text) is not None


def compact(
    path: Path, archive_heading: str, body_status: bool = False
) -> tuple[int, int, int, int]:
    """Rewrite `path` in place (inline-item layout). Returns (lines_before,
    lines_after, items_deleted, narrative_sections_deleted)."""
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
        if body_status and is_item:
            # One law per board: a risk artifact's finding states its status
            # in prose whether or not its heading happens to carry an id, and
            # the prose outranks the heading. Two atlas findings headed as
            # merged/closed recorded a still-open half in their bodies ("RITK
            # #132 remains open"); trusting the heading there would delete the
            # live residual the finding exists to carry.
            closed = body_is_closed(body, heading)
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
        elif body_status:
            # Risk artifact: a section IS a finding, so the report-genre
            # default inverts -- delete only what its prose records as
            # closed, keep everything else for a human at its next touch.
            if body_is_closed(body, heading):
                narrative_deleted += 1
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


def is_indexed_board(path: Path) -> bool:
    """True when `path` is a per-item-file board (a sibling `backlog/` dir)."""
    return path.name == "backlog.md" and (path.parent / "backlog").is_dir()


def _load_index_module():
    """Import `atlas-board-index.py` (hyphenated: not a plain `import`)."""
    import importlib.util

    script = Path(__file__).resolve().parent / "atlas-board-index.py"
    spec = importlib.util.spec_from_file_location("atlas_board_index", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _total_lines(board: Path, item_dir: Path) -> int:
    total = len(board.read_text(encoding="utf-8").splitlines()) if board.is_file() else 0
    if item_dir.is_dir():
        total += sum(
            len(p.read_text(encoding="utf-8").splitlines()) for p in item_dir.glob("*.md")
        )
    return total


# An item-file heading ends in its status; the index generator reads it there.
STATUS_TAIL = re.compile(
    r"\s[-\u2013\u2014]\s*(todo|in-progress|blocked|review|done)\s*$", re.I
)
# Inline items written before the per-item migration keep it in the body.
BODY_STATUS_LINE = re.compile(
    r"^\s*[-*]\s*\**status\**\s*:\s*(todo|in-progress|blocked|review|done)\b",
    re.I | re.M,
)


def _status_from_body(body: list[str]) -> str | None:
    """The item's recorded status, or None when it states none."""
    found = BODY_STATUS_LINE.search("\n".join(body))
    return found.group(1).lower() if found else None


def _block(
    anchor_line: str | None, prefix_blanks: list[str], heading: str,
    body: list[str],
) -> list[str]:
    """Reassemble a section exactly as it was read."""
    out: list[str] = []
    if anchor_line is not None:
        out.append(anchor_line)
    out.extend(prefix_blanks)
    out.append(heading)
    out.extend(body)
    return out


def _migrate_preamble_item(
    item_dir: Path, anchor_line: str | None, heading: str, body: list[str]
) -> str | None:
    """Write an inline preamble item to its `backlog/<anchor>.md` file.

    The anchor is the file's identity, so it is taken from the item's own
    `<a id="...">` line when it has one and derived from the id otherwise --
    a regenerated index links to the anchor, and inventing a different one
    would break every existing reference to the item.
    """
    anchor = None
    if anchor_line is not None:
        found = ANCHOR_OWN_LINE.match(anchor_line)
        if found:
            anchor = found.group(1)
    if anchor is None:
        anchor = ITEM_ID.match(heading).group(1).lower()
    target = item_dir / f"{anchor}.md"
    if _status_split(heading) is None and STATUS_TAIL.search(heading) is None:
        status = _status_from_body(body)
        if status is None:
            return None
        heading = f"{heading.rstrip()} - {status}"
    block = [f'<a id="{anchor}"></a>', heading, *body]
    while block and not block[-1].strip():
        block.pop()
    target.write_text("\n".join(block) + "\n", encoding="utf-8", newline="")
    return target.name


def compact_indexed(path: Path, archive_heading: str) -> tuple[int, int, int, int]:
    """Rewrite the per-item-file board rooted at `path` in place.

    Returns (lines_before, lines_after, items_deleted,
    narrative_sections_deleted), counted across `backlog.md` and every
    `backlog/*.md` file combined -- the same "board total" the artifact
    budget gate measures.
    """
    item_dir = path.parent / "backlog"
    before = _total_lines(path, item_dir)

    lines = path.read_text(encoding="utf-8").splitlines()
    first_index_at = next(
        (i for i, ln in enumerate(lines) if INDEX_LINE.match(ln)), len(lines)
    )
    preamble_lines = lines[:first_index_at]

    # Pass 1: delete closed item files, collecting which ids stay open (for
    # the preamble's narrative-section cross-reference exception below).
    items_deleted = 0
    open_ids: set[str] = set()
    for item_path in sorted(item_dir.glob("*.md")):
        text = item_path.read_text(encoding="utf-8")
        heading = next((ln for ln in text.splitlines() if ln.startswith("## ")), "")
        m = ITEM_ID.match(heading)
        if not m:
            continue
        if is_closed(heading):
            item_path.unlink()
            items_deleted += 1
        else:
            open_ids.add(m.group(1))

    # Pass 2: narrative sections stay inline in the preamble under this
    # layout (the migration moved only id-bearing items to files) -- same
    # keep/delete rule as the inline board.
    pre_preamble, narrative_items = split_items(preamble_lines)
    kept_narrative_blocks: list[list[str]] = []
    narrative_deleted = 0
    items_migrated: list[str] = []
    unmigrated: list[str] = []
    for anchor_line, prefix_blanks, heading, body in narrative_items:
        if heading.startswith(archive_heading):
            narrative_deleted += 1
            continue
        item_match = ITEM_ID.match(heading)
        if item_match is not None:
            # An id-bearing preamble section is an item that never got its
            # file, not narrative. The index regenerates from the item
            # directory, so leaving it inline deletes it; the narrative rule
            # would too, since its cross-references are other repositories'
            # ids and can never be in this board's open set.
            if is_closed(heading):
                items_deleted += 1
                continue
            migrated = _migrate_preamble_item(
                item_dir, anchor_line, heading, body
            )
            open_ids.add(item_match.group(1))
            if migrated is None:
                # No readable status: keep it inline rather than write an
                # invented one into the board, and never fall through to the
                # narrative rule, which would delete it.
                unmigrated.append(item_match.group(1))
                kept_narrative_blocks.append(
                    _block(anchor_line, prefix_blanks, heading, body)
                )
            else:
                items_migrated.append(migrated)
            continue
        reason = narrative_keep_reason(body, open_ids)
        if reason is None:
            narrative_deleted += 1
            continue
        kept_narrative_blocks.append(
            _block(anchor_line, prefix_blanks, heading, body)
        )

    new_preamble = list(pre_preamble)
    for block in kept_narrative_blocks:
        new_preamble.extend(block)
    while len(new_preamble) > 1 and not new_preamble[-1].strip() and not new_preamble[-2].strip():
        new_preamble.pop()
    path.write_text("\n".join(new_preamble) + "\n", encoding="utf-8", newline="")

    # Regenerate the index over whichever item files survived.
    index_mod = _load_index_module()
    new_text = index_mod.generate_text(path.parent)
    path.write_text(new_text, encoding="utf-8", newline="")

    after = _total_lines(path, item_dir)
    return before, after, items_deleted, narrative_deleted


def _dry_run_indexed(path: Path, archive_heading: str) -> None:
    item_dir = path.parent / "backlog"
    lines = path.read_text(encoding="utf-8").splitlines()
    before = _total_lines(path, item_dir)
    item_count = 0
    closed = 0
    for item_path in sorted(item_dir.glob("*.md")):
        text = item_path.read_text(encoding="utf-8")
        heading = next((ln for ln in text.splitlines() if ln.startswith("## ")), "")
        if not ITEM_ID.match(heading):
            continue
        item_count += 1
        if is_closed(heading):
            closed += 1
    first_index_at = next(
        (i for i, ln in enumerate(lines) if INDEX_LINE.match(ln)), len(lines)
    )
    _, narrative_items = split_items(lines[:first_index_at])
    narrative = len(narrative_items)
    print(f"{path.name}: {before} lines (index + {len(list(item_dir.glob('*.md')))} item "
          f"files), {item_count} items ({closed} would delete), "
          f"{narrative} narrative sections")


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

    # gap_audit is a board under the same budget and the same rule; it
    # classifies by body because a finding states its status in prose.
    targets = [
        (root / "backlog.md", "## Archive — closed items", False),
        (root / "checklist.md", "## Archive — closed checklists", False),
        (root / "gap_audit.md", "## Archive — closed findings", True),
    ]
    for path, heading, body_status in targets:
        if not path.is_file():
            print(f"skip (absent): {path.name}")
            continue
        indexed = is_indexed_board(path)
        if args.dry_run:
            if indexed:
                _dry_run_indexed(path, heading)
            else:
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
                if body_status:
                    # Reporting the report-genre default here would promise a
                    # sweep this board never performs.
                    closed = sum(
                        1 for _, _, h, b in kept
                        if body_is_closed(b, h)
                    )
                    item_count = len(kept)
                    narrative = 0
                print(f"{path.name}: {len(lines)} lines, {item_count} items "
                      f"({closed} would delete), {narrative} narrative sections")
            continue
        if indexed:
            before, after, n_items, n_narrative = compact_indexed(path, heading)
        else:
            before, after, n_items, n_narrative = compact(
                path, heading, body_status=body_status
            )
        print(f"{path.name}: {before} -> {after} lines "
              f"({n_items} items deleted, {n_narrative} narrative sections deleted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
