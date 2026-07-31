#!/usr/bin/env python3
"""Generate conceptual SVG figure assets for an mdBook and embed them.

Mirrors the kwavers pattern of keeping figures under docs/book/figures/chXX/
and referencing them with markdown image syntax.

Usage:
    python scripts/generate_book_figures.py <book_dir> [--dry-run] [--force]
"""

import argparse
from pathlib import Path

from generate_book_figures.core import process_book


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate mdBook figure assets")
    parser.add_argument("book_dir", type=Path, help="Path to docs/book directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without writing files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate figures even if pages already contain them",
    )
    args = parser.parse_args()
    process_book(args.book_dir, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
