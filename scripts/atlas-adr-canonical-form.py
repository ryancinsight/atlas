#!/usr/bin/env python3
"""Rewrite ADR headings to the canonical form `# ADR NNNN: Title`.

ADR governance names one heading form; twelve members carry six others
(`ADR-NNNN:`, `ADR NNNN —`, `ADR NNNN (repo):`, `NNN.`, bare titles), which is
why the shared index guard (`adr-index-guard.yml`) cannot yet run strict on
them (ATLAS-ADR-FORM-NORMALIZATION-2026-09-02). This tool is the mechanical
half of that campaign: it rewrites only the first heading line of each
numbered ADR file, taking the number from the filename — the strict check
requires the two to agree — and leaves every other byte alone.

    atlas-adr-canonical-form.py --check DIR...   # exit 1 and list nonconforming files
    atlas-adr-canonical-form.py --write DIR...   # rewrite them in place

Unnumbered files (no leading digits in the name) are reported, never
rewritten: an ADR without a number needs a claimed number, a governance
decision this tool does not make.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILENAME_NUMBER = re.compile(r"^(\d+)-")
# Every heading shape observed across the stack's ADR directories. The
# optional `(repo)` tag is a repository marker inside that repository's own
# tree and carries no information; it is dropped with the rest of the prefix.
HEADING = re.compile(
    r"^#\s+(?:ADR[- ]?)?(?P<number>\d+)\s*(?:\([^)]*\))?\s*(?:[:.\-]|–|—)\s*(?P<title>.+?)\s*$"
)
CANONICAL = re.compile(r"^# ADR (?P<number>\d+): (?P<title>\S.*\S|\S)$")
BARE_TITLE = re.compile(r"^#\s+(?P<title>.+?)\s*$")


def canonical_heading(line: str, number: str) -> str | None:
    """Return the canonical form of a first-heading line, or None if it is
    not a heading at all. The filename's number wins over the heading's; a
    CRLF file keeps its carriage return."""
    ending = "\r" if line.endswith("\r") else ""
    line = line.rstrip("\r")
    canonical = CANONICAL.match(line)
    if canonical and canonical.group("number") == number:
        return line + ending
    match = HEADING.match(line) or BARE_TITLE.match(line)
    if match is None:
        return None
    return f"# ADR {number}: {match.group('title')}{ending}"


def first_heading_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.startswith("#"):
            return index
        if line.strip():
            return None
    return None


def normalize(text: str, number: str) -> str:
    """Rewrite the first heading of `text`; everything else is byte-identical."""
    lines = text.split("\n")
    index = first_heading_index(lines)
    if index is None:
        return text
    heading = canonical_heading(lines[index], number)
    if heading is None:
        return text
    lines[index] = heading
    return "\n".join(lines)


def adr_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.md") if p.name != "README.md")


def run(directories: list[Path], write: bool) -> int:
    nonconforming = 0
    for directory in directories:
        for path in adr_files(directory):
            number_match = FILENAME_NUMBER.match(path.name)
            if number_match is None:
                print(f"unnumbered (not rewritten): {path}")
                nonconforming += 1
                continue
            # Bytes in, bytes out: text-mode I/O would translate CRLF and the
            # rewrite must change exactly one line.
            original = path.read_bytes().decode("utf-8")
            rewritten = normalize(original, number_match.group(1))
            if rewritten == original:
                continue
            nonconforming += 1
            if write:
                path.write_bytes(rewritten.encode("utf-8"))
                print(f"rewritten: {path}")
            else:
                print(f"nonconforming heading: {path}")
    if nonconforming and not write:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report nonconforming files")
    mode.add_argument("--write", action="store_true", help="rewrite nonconforming headings")
    parser.add_argument("directories", nargs="+", type=Path)
    arguments = parser.parse_args()
    for directory in arguments.directories:
        if not directory.is_dir():
            print(f"error: {directory} is not a directory", file=sys.stderr)
            return 2
    return run(arguments.directories, write=arguments.write)


if __name__ == "__main__":
    raise SystemExit(main())
