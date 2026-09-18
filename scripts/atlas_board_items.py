#!/usr/bin/env python3
"""Shared parsing primitives for Atlas PM-board item headings.

Every board-scanning tool independently re-derived "split a level-two
heading into id / title / status" against the same grammar:

    ## <ID> <sep> <title> <sep> <status>

where `<sep>` is ` — ` (em dash) or ` - ` (hyphen) at bracket/paren depth
zero, and an anchor (`<a id="...">...</a>`) sits either on its own line
immediately above the heading or inline at the heading's tail. Four
scripts (`atlas-board-compact.py`, `atlas-board-lint.py`,
`atlas-board-sweep.py`, `atlas-board-delivery-audit.py`) each carried a
near-duplicate of this grammar before this module existed -- consolidated
here per the pre-write search gate (a second occurrence is the signal;
four was overdue).

This module also carries the per-item-file board layout introduced by the
board-compaction migration: `backlog.md` holds one generated index line per
item (`<a id="..."></a>- [ID](backlog/anchor.md) — title — status`) instead
of the item's full body, with the body living in `backlog/<anchor>.md`.
`expand_board_lines` transparently resolves an index-format board back into
the pre-migration inline shape (heading + body concatenated in the original
positions), so a tool built against "one big file of inline items" keeps
working against either layout without carrying two parsers.
"""
from __future__ import annotations

import re
from pathlib import Path

# A capitalized, hyphenated token -- ids on this board are not required to
# carry digits (`ATLAS-CUDA-DRIVER-BOUNDARY` is a real id), so the marker is
# structural (at least one hyphen, all-caps-and-digits) rather than a
# specific prefix or a trailing numeral.
ITEM_ID = re.compile(r"^##\s+([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)")

ANCHOR_OWN_LINE = re.compile(r'^<a id="([^"]+)"></a>\s*$')
ANCHOR_INLINE = re.compile(r'\s*<a id="([^"]+)"></a>\s*$')

# The new index-line format: an anchor immediately followed (same line, no
# space) by a markdown link to the item's per-item file.
INDEX_LINE = re.compile(
    r'^<a id="(?P<anchor>[^"]+)"></a>-\s*\[(?P<id>[^\]]+)\]'
    r'\((?P<ref>backlog/[^)]+\.md)\)\s*(?:—|-)\s*(?P<title>.*?)\s*(?:—|-)\s*'
    r'(?P<status>[A-Za-z-]+)\s*$'
)


def top_level_separators(text: str) -> list[tuple[int, int]]:
    """Positions of every ' — ' / ' - ' at bracket/paren depth 0.

    A trailing parenthetical can itself contain a dash, so a plain rsplit on
    the last dash anywhere can land inside it. Skipping nested spans finds
    the separator that actually divides one field from the next.
    """
    spans = []
    depth = 0
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "([":
            depth += 1
            i += 1
            continue
        if c in ")]":
            depth = max(0, depth - 1)
            i += 1
            continue
        if depth == 0:
            if text[i : i + 3] == " — ":
                spans.append((i, i + 3))
                i += 3
                continue
            if i + 2 < n and text[i] == " " and text[i + 1] == "-" and text[i + 2] == " ":
                spans.append((i, i + 3))
                i += 3
                continue
        i += 1
    return spans


def split_title_status(tail: str) -> tuple[str, str] | None:
    """Split heading text after the item id into (title, status).

    `tail` is everything following "## ID", so its FIRST top-level
    separator is the id/title divider, not a field boundary to keep in the
    title -- returning it unstripped once left every already-canonical
    title carrying a leading " — "/" - " (visible in a generated index as
    "... — - Some Title ... — status"). A genuine status field is a SECOND
    top-level separator; a heading with only the id/title divider and no
    status field at all (a handful of newest-format items:
    "## ID - title [tags]") returns None rather than mistaking the title
    for a status.
    """
    spans = top_level_separators(tail)
    if len(spans) < 2:
        return None
    return tail[spans[0][1] : spans[-1][0]].strip(), tail[spans[-1][1] :].strip()


def extract_anchor(heading_line: str, prev_nonblank_line: str | None) -> str | None:
    """Anchor from an own-line predecessor, else inline at the heading tail."""
    if prev_nonblank_line is not None:
        m = ANCHOR_OWN_LINE.match(prev_nonblank_line)
        if m:
            return m.group(1)
    m = ANCHOR_INLINE.search(heading_line)
    if m:
        return m.group(1)
    return None


def strip_inline_anchor(heading_line: str) -> str:
    """Remove a trailing inline `<a id="...">` from a heading line, if any."""
    return ANCHOR_INLINE.sub("", heading_line).rstrip()


def expand_board_lines(path: Path) -> list[str]:
    """Return *path*'s lines with any per-item-file index lines expanded
    inline to the referenced file's full content.

    A board with no index lines (the pre-migration inline shape, or a board
    this migration never touched -- checklist.md, gap_audit.md, a member
    repository's own backlog.md) is returned unchanged: expansion is a
    no-op wherever there is nothing to expand.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    root = path.parent
    out: list[str] = []
    for line in lines:
        m = INDEX_LINE.match(line)
        if not m:
            out.append(line)
            continue
        ref = root / m.group("ref")
        if ref.is_file():
            out.extend(ref.read_text(encoding="utf-8").splitlines())
        else:
            out.append(line)
    return out


def expand_board_text(path: Path) -> str:
    return "\n".join(expand_board_lines(path)) + "\n"


def item_file_paths(board: Path) -> list[Path]:
    """Every per-item file referenced by *board*'s index lines, in order."""
    lines = board.read_text(encoding="utf-8").splitlines()
    root = board.parent
    paths: list[Path] = []
    for line in lines:
        m = INDEX_LINE.match(line)
        if m:
            paths.append(root / m.group("ref"))
    return paths
