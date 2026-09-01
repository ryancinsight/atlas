#!/usr/bin/env python3
"""Normalize closure markers on PM board headings to one canonical form.

The compact pass (`atlas-board-compact.py`) classifies a heading as closed by
matching the last em-dash segment against a regex that accepts several status
words (`done`, `closed`, `complete`, `completed`, `merged`). Variants drift
across eras:

  - ``## ATLAS-... — ... — done 2026-08-25`` (canonical)
  - ``## ATLAS-... — ... — completed`` (no date)
  - ``## ATLAS-... — ... — closed 2026-08-25 (superseded by ADR 0033)`` (note in heading)
  - ``## ATLAS-... — ... — done 2026-08-29; gate corrected 2026-09-01`` (semicolon)

Canonicalization makes every closed heading carry exactly the form

  ``— closed YYYY-MM-DD``

with no trailing parenthetical or semicolon tail. Items that genuinely need a
note (e.g. the supersession remark) move the remark into the first body line
under the heading so the archive step still picks the commit SHAs up.

Date derivation for items missing one:

  1. First ISO date in the heading tail after the status word
  2. First ISO date in the body content (commit dates, audit dates)
  3. Empty (left for human triage; not auto-closed)

Status word selection: ``closed`` is canonical. ``done`` and ``completed`` map
  to it. ``merged`` stays ``merged`` (the closure was a merge, not a fix);
  ``delivered`` and other variants stay as-is but flagged for review.

Scope: per-line, deterministic, mechanical. Anything the script cannot classify
is left untouched for human review, and the diff is reviewable per heading.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CLOSED_STATUSES = ("done", "closed", "complete", "completed", "merged", "delivered")
STATUS_RE = re.compile(r"^\s*(?P<status>done|closed|complete|completed|merged|delivered)\b\s*(?P<rest>.*)$", re.I)
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
ITEM_ID_RE = re.compile(r"^##\s+([A-Z][A-Z0-9\-]*-\d+[A-Z0-9\-]*)")
NOT_SHA = {"decade", "faceted", "defaced", "accede", "efface", "deface"}

# Canonical status choice (lowercased)
CANONICAL = {"done": "closed", "complete": "closed", "completed": "closed"}
KEEP_AS_IS = {"closed", "merged", "delivered"}


def is_closed(heading: str) -> bool:
    """Mirror atlas-board-compact.is_closed: last em-dash segment matches a status word.

    Excludes the Archive section header itself, which starts with the word
    "closed" but is a container, not an item.
    """
    if not heading.startswith("## "):
        return False
    # Skip the Archive section header itself
    body_after_hashes = heading.lstrip("#").strip()
    if body_after_hashes.lower().startswith("archive"):
        return False
    tail = heading.rsplit("—", 1)
    if len(tail) != 2:
        return False
    return bool(STATUS_RE.match(tail[1]))


def canonicalize_heading(heading: str, body: list[str]) -> tuple[str, list[str] | None, bool]:
    """Return (new_heading, new_body, changed).

    ``changed=False`` means the heading was already in canonical form and the
    body is unchanged. ``changed=True`` carries the canonicalized heading and
    possibly a rewritten body (when a note was extracted).
    """
    if not is_closed(heading):
        return heading, None, False

    head_tail = heading.rsplit("—", 1)
    prefix, tail = head_tail[0], head_tail[1].strip()
    m = STATUS_RE.match(tail)
    if not m:
        return heading, None, False
    status = m.group("status").lower()
    rest = m.group("rest").strip()

    # Pick canonical status
    if status in CANONICAL:
        canonical_status = "closed"
    elif status in KEEP_AS_IS:
        canonical_status = status
    else:
        return heading, None, False

    # Strip trailing parenthetical / semicolon tails from the rest
    # Examples: "(superseded by ADR 0033 execution)", "; gate corrected 2026-09-01"
    # We want to keep only the date (if any) in the heading; the rest is body content.
    note = ""
    cleaned_rest = rest

    # Extract parenthetical note
    paren_match = re.search(r"\(([^)]+)\)", cleaned_rest)
    if paren_match:
        note = paren_match.group(1).strip()
        cleaned_rest = cleaned_rest[: paren_match.start()] + cleaned_rest[paren_match.end() :]

    # Extract semicolon-clause note
    if ";" in cleaned_rest:
        before, after = cleaned_rest.split(";", 1)
        extra = after.strip()
        if extra:
            note = (note + "; " + extra) if note else extra
        cleaned_rest = before

    # Find the date: prefer a date in the cleaned_rest; else in the body
    date = ""
    dates = DATE_RE.findall(cleaned_rest)
    if dates:
        date = dates[0]
    else:
        body_blob = "\n".join([heading, *body])
        body_dates = DATE_RE.findall(body_blob)
        if body_dates:
            # Prefer the latest date as the closure date (commit lands after audit)
            date = max(body_dates)

    # Build the new heading; canonical form is `— closed YYYY-MM-DD`
    parts = [prefix.rstrip(), canonical_status]
    if date:
        parts.append(date)
    # The prefix already ends with the title; join with single em-dash+space
    new_heading = f"{parts[0]} — {' '.join(parts[1:])}"

    # If we extracted a note, prepend it to the body
    new_body: list[str] | None = None
    changed = (new_heading != heading) or note
    if note:
        new_body = [f"_Closure note (moved from heading):_ {note}", "", *body]
    return new_heading, new_body, changed


def split_items(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Return (preamble, [(heading, body_lines), ...]) split on level-2 headings."""
    starts = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    if not starts:
        return lines, []
    preamble = lines[: starts[0]]
    items: list[tuple[str, list[str]]] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(lines)
        heading = lines[start]
        body = lines[start + 1 : end]
        items.append((heading, body))
    return preamble, items


def process_board(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Return (new_text, [(item_id, old_heading, new_heading)]).

    The list contains every canonicalized heading pair. Untouched items are
    not in the list.
    """
    lines = text.split("\n")
    preamble, items = split_items(lines)
    changes: list[tuple[str, str, str]] = []
    new_items: list[tuple[str, list[str]]] = []
    for heading, body in items:
        m = ITEM_ID_RE.match(heading)
        item_id = m.group(1) if m else ""
        new_heading, new_body, changed = canonicalize_heading(heading, body)
        if changed:
            changes.append((item_id, heading, new_heading))
            if new_body is not None:
                new_items.append((new_heading, new_body))
            else:
                new_items.append((new_heading, body))
        else:
            new_items.append((heading, body))

    out: list[str] = []
    out.extend(preamble)
    for heading, body in new_items:
        out.append(heading)
        out.extend(body)
    return "\n".join(out), changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--path",
        default=str(ROOT / "backlog.md"),
        help="board file to canonicalize (default: backlog.md)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would change without writing",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="print each canonicalized heading pair (old -> new)",
    )
    args = parser.parse_args()

    text = Path(args.path).read_text(encoding="utf-8")
    new_text, changes = process_board(text)

    if args.show:
        for item_id, old, new in changes:
            print(f"[{item_id}]")
            print(f"  - {old.strip()}")
            print(f"  + {new.strip()}")
            print()

    if args.dry_run:
        print(f"{args.path}: {len(changes)} heading(s) canonicalized (dry run)")
        return 0

    Path(args.path).write_text(new_text, encoding="utf-8")
    print(f"{args.path}: {len(changes)} heading(s) canonicalized")
    return 0


if __name__ == "__main__":
    sys.exit(main())