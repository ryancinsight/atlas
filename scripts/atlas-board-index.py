#!/usr/bin/env python3
"""Generate and check the `backlog.md` per-item-file index.

Past about forty open items, item bodies move to per-item files
(`backlog/<anchor>.md`, each within the per-item line budget) and
`backlog.md` becomes their generated one-line-per-item index: the scannable
surface and the lease file (`context_and_memory`, Boards). This script is
that generator.

Layout::

    backlog.md
        <preamble: title and any policy/narrative text>

        <a id="<anchor>"></a>- [<ID>](backlog/<anchor>.md) — <title> — <status>
        ...one line per item, in order...

    backlog/<anchor>.md
        <a id="<anchor>"></a>
        ## <ID> ... — <title> — <status>
        <body, verbatim>

The anchor stays in `backlog.md` (on the same line as the index entry), so
every existing inbound link of the form `backlog.md#<anchor>` keeps
resolving exactly as it did when the anchor sat on the heading itself.

Ordering is regenerate-and-diff stable: an item whose anchor already has an
index line keeps its current position (so a plain re-run is a no-op); an
item file with no existing index line (newly added since the last generate)
is appended at the end, ordered by id. An index line whose file has been
removed (the item closed and its file deleted, per `atlas-board-compact.py`)
drops out.

    python scripts/atlas-board-index.py generate
    python scripts/atlas-board-index.py check

`check` exits 1 when `backlog.md` differs from what `generate` would write
-- the freshness gate for CI and pre-push.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_board_items import (  # noqa: E402
    ANCHOR_OWN_LINE,
    INDEX_LINE,
    ITEM_ID,
    split_title_status,
    strip_inline_anchor,
)

ROOT = Path(__file__).resolve().parent.parent

# The index line's status field is the bare canonical word (schema: todo,
# in-progress, blocked, review, done). A per-item file's own heading may
# carry a decorated status ("in-progress (enforcement merged; sweep
# unclaimed)", "blocked (peer-owned)", "in-progress 2026-08-18") -- that
# decoration is the item's own prose and stays in the file untouched, but
# the generated index line surfaces only the leading status word so the
# index stays a clean, closed-vocabulary scan surface.
STATUS_WORD = re.compile(r"^[A-Za-z-]+")


def item_fields_from_file(path: Path) -> tuple[str, str, str, str]:
    """Return (anchor, item_id, title, status) parsed from a per-item file.

    The anchor is read from the file's own leading `<a id="...">` line when
    present, falling back to the item id lowercased (matching the migration
    rule: "the item's `<a id>` value or, if it has none, its ID lowercased").
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    anchor: str | None = None
    heading_idx: int | None = None
    for i, line in enumerate(lines):
        if heading_idx is None and line.startswith("## "):
            heading_idx = i
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            if j >= 0:
                m = ANCHOR_OWN_LINE.match(lines[j])
                if m:
                    anchor = m.group(1)
            break
    if heading_idx is None:
        raise ValueError(f"{path}: no '## ' heading found")
    heading = lines[heading_idx]
    id_match = ITEM_ID.match(heading)
    if id_match is None:
        raise ValueError(f"{path}: heading carries no item id: {heading!r}")
    item_id = id_match.group(1)
    # Not `.strip()`-ed: the tail's leading space is part of the id/title
    # separator (" — "/" - ") that `split_title_status` matches on.
    split = split_title_status(heading[id_match.end():])
    if split is None:
        raise ValueError(f"{path}: heading has no title/status separator: {heading!r}")
    title, status = split
    title = strip_inline_anchor(title.strip()).strip()
    status = strip_inline_anchor(status.strip()).strip()
    status_match = STATUS_WORD.match(status)
    status = status_match.group(0) if status_match else status
    if anchor is None:
        anchor = item_id.lower()
    return anchor, item_id, title, status


def _format_index_line(anchor: str, item_id: str, ref: str, title: str, status: str) -> str:
    return f'<a id="{anchor}"></a>- [{item_id}]({ref}) — {title} — {status}'


def _split_preamble_and_index(lines: list[str]) -> tuple[list[str], list[str]]:
    """(preamble_lines, existing_anchor_order) from the CURRENT board text.

    A board with no index lines yet (freshly seeded, or never migrated)
    yields the whole file as preamble and an empty order.
    """
    order: list[str] = []
    first_index_at: int | None = None
    for i, line in enumerate(lines):
        m = INDEX_LINE.match(line)
        if m:
            if first_index_at is None:
                first_index_at = i
            order.append(m.group("anchor"))
    if first_index_at is None:
        return lines, []
    return lines[:first_index_at], order


def generate_text(root: Path) -> str:
    board = root / "backlog.md"
    item_dir = root / "backlog"
    lines = board.read_text(encoding="utf-8").split("\n") if board.is_file() else [""]
    preamble, existing_order = _split_preamble_and_index(lines)

    files = sorted(item_dir.glob("*.md")) if item_dir.is_dir() else []
    fields_by_anchor: dict[str, tuple[str, str, str, str]] = {}
    for f in files:
        anchor, item_id, title, status = item_fields_from_file(f)
        fields_by_anchor[anchor] = (item_id, f"backlog/{f.name}", title, status)

    existing_set = set(existing_order)
    ordered_anchors = [a for a in existing_order if a in fields_by_anchor]
    new_anchors = sorted(
        (a for a in fields_by_anchor if a not in existing_set),
        key=lambda a: fields_by_anchor[a][0],
    )
    ordered_anchors.extend(new_anchors)

    index_lines = [
        _format_index_line(anchor, *fields_by_anchor[anchor])
        for anchor in ordered_anchors
    ]

    while preamble and preamble[-1].strip() == "":
        preamble.pop()
    out = list(preamble)
    if out and index_lines:
        out.append("")
    out.extend(index_lines)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "check"))
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    board = root / "backlog.md"

    new_text = generate_text(root)

    if args.mode == "check":
        current = board.read_text(encoding="utf-8") if board.is_file() else ""
        if current == new_text:
            print(f"{board}: up to date")
            return 0
        print(f"{board}: stale -- run `atlas-board-index.py generate` and commit the result",
              file=sys.stderr)
        return 1

    # `newline=""`: the board is committed LF; `write_text` would otherwise
    # translate every line ending to the platform's on Windows.
    with board.open("w", encoding="utf-8", newline="") as handle:
        handle.write(new_text)
    n_items = sum(1 for line in new_text.splitlines() if INDEX_LINE.match(line))
    print(f"{board}: {n_items} item(s) indexed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
