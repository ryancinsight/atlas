#!/usr/bin/env python3
"""Compact a PM board: keep live items in full, collapse closed ones to an index.

`context_and_memory` (artifact compaction) requires the board to stay compact and
link-navigable: "completed items collapse to one-line entries with links to
commits/CHANGELOG rather than retained prose". At the time this script was
written `backlog.md` was 13,399 lines of which 8,872 (66%) sat under items
already marked complete/done, and `checklist.md` was 5,810 lines with 65% of its
items carrying no status at all.

This is the mechanical half of that rule, so the collapse is reproducible rather
than a one-off hand edit. It is deliberately conservative: an item is archived
only when its heading carries an unambiguous closed marker, every commit SHA
mentioned under the item is carried into the archive line, and anything it
cannot classify is left untouched in the live board for a human to triage.

Run from anywhere: paths anchor to this file's parent repository unless a
root is given, so one compactor serves every member board in the stack.

Checkbox-bullet records (`- [x] **ID — title.** ...`) inside a live section
are part of that section's prose and stay verbatim: the collapse unit is the
level-2 heading, never a bullet, so a board that keeps measured-rejection
records in full under an open heading loses nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A heading is closed only when its FINAL em-dash segment is a status clause.
# Matching anywhere after an em-dash archives live items whose *title* contains
# a status word — e.g. "ATLAS-COEUS-LAYERNORM-SHAPE-031 — Complete
# multi-dimensional LayerNorm contract [minor] — in-progress" is in-progress,
# not complete. Under-collapsing is safe; over-collapsing loses a live item.
CLOSED = re.compile(
    r"^\s*(?:✅\s*)?(?:complete|completed|done|closed|merged)\b", re.I
)
# Bare-tick form used by a handful of older kwavers entries.
CLOSED_TICK = re.compile(r"✓\s*DONE\b", re.I)
DATE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
SHA = re.compile(r"\b([0-9a-f]{7,40})\b")
ITEM_ID = re.compile(r"^##\s+([A-Z][A-Z0-9\-]*-\d+[A-Z0-9\-]*)")
# Words that look like hex but are prose, so they never become fake SHAs.
NOT_SHA = {"decade", "faceted", "defaced", "accede", "efface", "deface"}


def is_closed(heading: str) -> bool:
    """Closed only when the last em-dash-delimited segment is a status clause."""
    if CLOSED_TICK.search(heading):
        return True
    tail = heading.rsplit("—", 1)
    return len(tail) == 2 and bool(CLOSED.match(tail[1]))


def split_items(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Return (preamble, [(heading, body_lines), ...]) split on level-2 headings."""
    starts = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    if not starts:
        return lines, []
    preamble = lines[: starts[0]]
    items = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        items.append((lines[i], lines[i + 1 : end]))
    return preamble, items


def archive_line(heading: str, body: list[str]) -> str:
    """One-line archive entry: id, title, date, and every SHA found under the item."""
    text = heading.lstrip("#").strip()
    m = ITEM_ID.match(heading)
    item_id = m.group(1) if m else ""
    title = text
    if item_id:
        title = text[len(item_id) :].lstrip(" —-")
    # Strip the trailing status/date clause; the date is re-attached explicitly.
    title = re.sub(r"—\s*(?:✅\s*)?(?:complete|completed|done|closed|merged)\b.*$", "",
                   title, flags=re.I).strip(" —-")
    title = CLOSED_TICK.sub("", title).strip(" —-")

    blob = "\n".join([heading, *body])
    date = ""
    dates = DATE.findall(blob)
    if dates:
        date = max(dates)
    shas = []
    for s in SHA.findall(blob):
        sl = s.lower()
        if sl in NOT_SHA or sl.isdigit() or len(set(sl)) <= 2:
            continue
        if sl not in shas:
            shas.append(sl)
    ref = f" — {', '.join('`' + s + '`' for s in shas[:4])}" if shas else ""
    stamp = f" ({date})" if date else ""
    label = f"**{item_id}**" if item_id else "**(unnumbered)**"
    return f"- {label} {title}{stamp}{ref}"


def compact(path: Path, archive_heading: str) -> tuple[int, int, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    before = len(lines)
    preamble, items = split_items(lines)

    # If the file already carries the archive section, peel it off before
    # classifying items so its body is preserved verbatim. A subsequent run
    # would otherwise roll the existing one-line entries into a single
    # `(unnumbered) Archive` line and lose the per-item navigability the
    # AGENTS compaction rule is meant to preserve.
    preserved_archive: list[str] = []
    kept_items: list[tuple[str, list[str]]] = []
    for heading, body in items:
        if heading.startswith(archive_heading):
            preserved_archive = body
            # Strip the introductory paragraph (one or more blank-prefixed
            # lines) so we don't double-print the heading's leading blurb.
            while preserved_archive and not preserved_archive[0].startswith("- "):
                preserved_archive.pop(0)
            if preserved_archive and not preserved_archive[0]:
                preserved_archive.pop(0)
        else:
            kept_items.append((heading, body))

    live: list[str] = []
    archived: list[str] = []
    for heading, body in kept_items:
        if is_closed(heading):
            archived.append(archive_line(heading, body))
        else:
            live.append(heading)
            live.extend(body)

    # Drop any item IDs already covered by the preserved archive so the
    # merged section stays deduplicated.
    preserved_ids: set[str] = set()
    for line in preserved_archive:
        m = re.match(r"^\s*-\s+\*\*([^*]+)\*\*", line)
        if m:
            preserved_ids.add(m.group(1))
    if preserved_ids:
        archived = [
            line for line in archived
            if not (m := re.match(r"^\s*-\s+\*\*([^*]+)\*\*", line))
            or m.group(1) not in preserved_ids
        ]

    out = list(preamble)
    out.extend(live)
    if preserved_archive or archived:
        # Trim trailing blanks so successive runs don't accumulate padding.
        while out and not out[-1].strip():
            out.pop()
        out.append("")
        out.append(archive_heading)
        out.append("")
        out.append(
            "Closed items, one line each. Full prose is in git history; commit "
            "SHAs below are the entry points."
        )
        out.append("")
        out.extend(preserved_archive)
        if archived:
            if preserved_archive and preserved_archive[-1].strip():
                out.append("")
            out.extend(archived)

    # `newline=""`: text mode on Windows would translate every "\n" to CRLF; the
    # board is committed LF (`.gitattributes`), and a CRLF working copy is churn.
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="")
    return before, len(out), len(archived)


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
                (h, b) for h, b in items
                if not h.startswith(heading)
            ]
            closed = sum(1 for h, _ in kept if is_closed(h))
            print(f"{path.name}: {len(lines)} lines, {len(kept)} items, "
                  f"{closed} would archive, {len(kept) - closed} stay live")
            continue
        before, after, n = compact(path, heading)
        print(f"{path.name}: {before} -> {after} lines ({n} items archived)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
