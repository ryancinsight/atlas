#!/usr/bin/env python3
"""Report claim and re-open-trigger hygiene on the Atlas backlog.

The sweep is deliberately report-only. It makes the inputs to stale-claim
triage mechanical without deciding whether a claim is stale or reclaimable:
claim-freshness thresholds remain an operator decision under the lane rules.

The board uses both ``in progress`` and ``in-progress`` spellings. Status is
read from the final em-dash segment of each level-two item heading, while the
item body supplies owner and trigger context.

    python scripts/atlas-board-sweep.py
    python scripts/atlas-board-sweep.py --file repos/kwavers/backlog.md

Exit status is 0 for a completed report, including when findings are present;
2 means that the requested board file does not exist or cannot be read.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# IDs are intentionally generic: provider boards use names such as H-100 and
# TYCHE-004 alongside the ATLAS-* IDs in the root board.
HEADING = re.compile(
    r"^##\s+(?P<item_id>[A-Za-z][A-Za-z0-9-]*)\s+—\s+(?P<rest>.+?)\s*$"
)
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
OWNER = re.compile(r"\bOwner\s*:\s*(?P<owner>[^\r\n]+)", re.IGNORECASE)
CLAIM_CONTEXT = re.compile(
    r"\b(?:claim(?:ed|s|ing)?|owner|last-update|status)\b", re.IGNORECASE
)
TRIGGER = re.compile(
    r"\bre[- ]?open\s+trigger(?:\s*\([^)]*\))?\s*:", re.IGNORECASE
)


@dataclass
class BacklogItem:
    """A parsed level-two backlog item and the evidence needed for triage."""

    item_id: str
    title: str
    status: str
    line: int
    body: list[str] = field(default_factory=list)

    @property
    def normalized_status(self) -> str:
        """Return the status prefix in a spelling-independent form."""
        return self.status.casefold().replace("-", " ").strip()

    @property
    def owner(self) -> str | None:
        """Return the first explicit owner clause, if present."""
        for line in self.body:
            match = OWNER.search(line)
            if match:
                return match.group("owner").strip().rstrip(".")
        return None

    @property
    def claim_dates(self) -> list[str]:
        """Return dates attached to heading/claim context, preserving order."""
        candidates = [line for line in self.body if CLAIM_CONTEXT.search(line)]
        dates: list[str] = []
        for text in candidates:
            for value in DATE.findall(text):
                if value not in dates:
                    dates.append(value)
        return dates

    @property
    def has_reopen_trigger(self) -> bool:
        """Whether the item documents a re-open trigger."""
        return any(TRIGGER.search(line) for line in self.body)


def _finish_item(items: list[BacklogItem], current: BacklogItem | None) -> None:
    if current is not None:
        items.append(current)


def parse_board(path: Path) -> list[BacklogItem]:
    """Parse level-two item headings and their bodies from *path*.

    Unknown headings and prose are retained as part of the current item rather
    than rejected. This is intentional: the board is human-authored and the
    sweep must tolerate new tags and status annotations.
    """
    items: list[BacklogItem] = []
    current: BacklogItem | None = None
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.rstrip("\r\n")
            match = HEADING.match(line)
            if match:
                _finish_item(items, current)
                rest = match.group("rest")
                if " — " in rest:
                    title, status = rest.rsplit(" — ", 1)
                else:
                    title, status = rest, ""
                current = BacklogItem(
                    item_id=match.group("item_id"),
                    title=title.strip(),
                    status=status.strip(),
                    line=line_number,
                )
            elif current is not None:
                current.body.append(line)
    _finish_item(items, current)
    return items


def report(items: list[BacklogItem], display_path: str) -> int:
    """Print the sweep report and return the report-only exit status."""
    active = [
        item
        for item in items
        if item.normalized_status.startswith("in progress")
    ]
    blocked_without_trigger = [
        item
        for item in items
        if item.normalized_status.startswith("blocked")
        and not item.has_reopen_trigger
    ]

    print(f"Backlog sweep: {display_path}")
    print(f"In-progress claims ({len(active)}):")
    if active:
        for item in active:
            owner = item.owner or "<missing>"
            dates = ", ".join(item.claim_dates) or "<no explicit date>"
            print(
                f"  {item.item_id} (line {item.line}): "
                f"owner={owner}; claim_dates={dates}"
            )
    else:
        print("  none")

    print(
        "Blocked items missing a re-open trigger "
        f"({len(blocked_without_trigger)}):"
    )
    if blocked_without_trigger:
        for item in blocked_without_trigger:
            print(f"  {item.item_id} (line {item.line}): {item.title}")
    else:
        print("  none")

    print(
        "Summary: "
        f"{len(items)} items scanned; "
        f"{len(active)} in progress; "
        f"{len(blocked_without_trigger)} blocked without a re-open trigger."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the report-only command-line sweep."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="backlog.md", help="board file to sweep")
    args = parser.parse_args(argv)

    path = Path(args.file)
    if not path.is_absolute():
        path = ROOT / path
    try:
        items = parse_board(path)
    except OSError as error:
        print(f"cannot read board file {path}: {error}", file=sys.stderr)
        return 2
    return report(items, args.file)


if __name__ == "__main__":
    raise SystemExit(main())
