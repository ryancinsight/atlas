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

Exit status is nonzero when any id is used twice.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# `## ATLAS-<ID> — <title> — <status>`; the em dash is the board's own
# separator, and the title may itself contain one, so only the id is parsed.
HEADING = re.compile(r"^##\s+(ATLAS-[A-Z0-9-]+?)\s+—\s+(.*)$")


def collisions(path: pathlib.Path) -> dict[str, list[tuple[int, str]]]:
    """Map each duplicated id to its (line number, title) occurrences."""
    seen: dict[str, list[tuple[int, str]]] = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            m = HEADING.match(line.rstrip("\r\n"))
            if not m:
                continue
            item_id, rest = m.group(1), m.group(2).strip()
            seen.setdefault(item_id, []).append((lineno, rest))
    return {k: v for k, v in seen.items() if len(v) > 1}


def next_free(path: pathlib.Path, prefix: str) -> str:
    """Suggest the next unused numeric id for a prefix, e.g. ATLAS-ARCH."""
    used = set()
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = HEADING.match(line.rstrip("\r\n"))
            if m and m.group(1).startswith(prefix + "-"):
                tail = m.group(1)[len(prefix) + 1:]
                if tail.isdigit():
                    used.add(int(tail))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}-{n:03d}"


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

    dupes = collisions(path)
    if not dupes:
        print(f"{args.file}: all item ids unique")
        return 0

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
