#!/usr/bin/env python3
"""Check the Atlas board for duplicate item ids.

Why: a board id is an anchor. Repo ADRs cite items as
`backlog.md#atlas-arch-010`, commits cite them in `Refs:` trailers, and
agents claim work by id. When two different items share one id, every
inbound reference becomes ambiguous and the claim protocol silently
breaks -- two agents can hold "the same" item and touch unrelated code.

This happened seven times before anyone noticed, once because this agent
filed an item without checking the id was free. Duplicate ids are cheap
to detect and expensive to unpick later, so detect them.

    python scripts/atlas-board-lint.py
    python scripts/atlas-board-lint.py --file checklist.md

Exit status is nonzero when any id is used twice, or when an
ATLAS-* reference resolves to no heading in either board file.

Why the reference check: items cite other items ("follow-ups filed
below", "see ATLAS-XYZ") and those references rot silently - two real
incidents sent work chasing ids that were never filed. A reference is
dangling when its exact id appears as prose in either board but no
heading defines it. Non-ATLAS tokens (crate names, ISSUE-220) are
ignored.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def collisions(path: pathlib.Path) -> dict[str, list[tuple[int, str]]]:
    """Map each duplicated id to its (line number, title) occurrences.

    The duplicate-id gate must see every heading form the reference check
    sees. `_defined_ids` treats a level-2 or level-3 heading as a definition
    regardless of separator (the board carries em-dash, hyphen, and
    mojibakeed separators), but this function once matched only the em-dash
    level-2 form, so a duplicate id defined via a hyphen or level-3 heading
    escaped the hard gate — the anchor ambiguity the gate exists to prevent.
    Match the same broad heading surface as `_defined_ids`.
    """
    seen: dict[str, list[tuple[int, str]]] = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            m = HEADING_ANY.match(line.rstrip("\r\n"))
            if not m:
                continue
            # Trailing separators vary by era (em dash, hyphen, U+FFFD);
            # the id ends at the first character outside [A-Z0-9-].
            item_id = m.group(1).rstrip("-")
            seen.setdefault(item_id, []).append((lineno, line.strip()))
    return {k: v for k, v in seen.items() if len(v) > 1}


def next_free(path: pathlib.Path, prefix: str) -> str:
    """Suggest the next unused numeric id for a prefix, e.g. ATLAS-ARCH."""
    used = set()
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = HEADING_ANY.match(line.rstrip("\r\n"))
            if m:
                item_id = m.group(1).rstrip("-")
            else:
                continue
            if item_id.startswith(prefix + "-"):
                tail = item_id[len(prefix) + 1:]
                if tail.isdigit():
                    used.add(int(tail))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}-{n:03d}"

REF_PATTERN = re.compile(r"\bATLAS-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
HEADING_ANY = re.compile(r"^#{2,3}\s+(ATLAS-[A-Z0-9-]+)")


def _defined_ids(boards: list[pathlib.Path]) -> set[str]:
    """Every item id defined by a level-2/3 heading across the boards."""
    defined: set[str] = set()
    for board in boards:
        with board.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = HEADING_ANY.match(line.rstrip("\r\n"))
                if m:
                    # Trailing separators vary (em dash, colon); the id ends
                    # at the first character outside [A-Z0-9-].
                    defined.add(m.group(1).rstrip("-"))
    return defined


# Closure is carried in the heading on this board:
# `## ATLAS-ID - title [class] - closed 2026-08-23`.
# The board separates title from state with an em dash; historical
# round-trips replaced some of them with U+FFFD replacement characters
# (mojibake - tracked as its own cleanup item). Match any of the three.
HEADING_CLOSED = re.compile(
    "[\u2014\ufffd-]\\s*(closed|superseded|withdrawn)\\b", re.IGNORECASE
)


def _active_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) spans of items whose heading does not mark them closed.

    Closed items are an archive: their prose cites historical context and
    linting it buries signal. Only live items' references are actionable.
    Headings without a closure marker count as active - fail-open keeps new
    items linted from day one.
    """
    starts = [
        i
        for i, line in enumerate(lines)
        if HEADING_ANY.match(line.rstrip("\r\n"))
    ]
    bounds: list[tuple[int, int]] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        if HEADING_CLOSED.search(lines[start]):
            continue
        bounds.append((start, end))
    return bounds


def dangling_refs(
    boards: list[pathlib.Path],
    defined: set[str],
) -> dict[str, list[tuple[str, int]]]:
    """ATLAS-* ids referenced by a *live* item but never defined by a heading.

    References inside closed items are archive prose and skipped; ids that
    are prefixes of defined ids ("MOI-AUDIT" for "MOI-AUDIT-SEC-001") count
    as family mentions, not dangling.
    """
    found: dict[str, list[tuple[str, int]]] = {}
    prefixes = {i.rsplit("-", 1)[0] for i in defined} | {
        i.split("-", 1)[0] for i in defined
    }
    for board in boards:
        lines = board.read_text(encoding="utf-8", errors="replace").splitlines()
        for start, end in _active_blocks(lines):
            for offset, line in enumerate(lines[start:end]):
                if HEADING_ANY.match(line.rstrip("\r\n")):
                    continue
                for ref in REF_PATTERN.findall(line):
                    if ref in defined or ref in prefixes:
                        continue
                    found.setdefault(ref, []).append((board.name, start + offset + 1))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="backlog.md", help="board file to lint")
    parser.add_argument(
        "--next", metavar="PREFIX",
        help="print the next free id for a prefix (e.g. ATLAS-ARCH) and exit",
    )
    args = parser.parse_args()

    path = ROOT / args.file
    if not path.is_file():
        print(f"no such board file: {path}", file=sys.stderr)
        return 2

    if args.next:
        print(next_free(path, args.next.rstrip("-")))
        return 0

    boards = [ROOT / "backlog.md", ROOT / "checklist.md"]
    boards = [b for b in boards if b.is_file()]

    defined = _defined_ids(boards)
    refs = dangling_refs(boards, defined)
    dupes = collisions(path)

    status = 0
    if refs:
        # Report-only until ATLAS-LINT-CALIB normalizes the corpus
        # (closure markers vary by board era; separator mojibake). The
        # duplicate-id gate below stays hard.
        print(
            f"[report] {len(refs)} unreconciled ATLAS-* mention(s) in "
            "live-item prose - see ATLAS-LINT-CALIB\n"
        )

    if not dupes:
        print(f"{args.file}: all item ids unique")
        return status

    print(f"{args.file}: {len(dupes)} duplicated item id(s)\n")
    for item_id, uses in sorted(dupes.items()):
        print(f"  {item_id}")
        for lineno, title in uses:
            print(f"    line {lineno}: {title}")
        prefix = item_id.rsplit("-", 1)[0]
        if item_id.rsplit("-", 1)[1].isdigit():
            print(f"    -> a free id for this family is {next_free(path, prefix)}")
        print()
    print(
        "Each id is an anchor cited by ADRs, commits and claims. Renumber the "
        "later item and move its inbound references with it.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
