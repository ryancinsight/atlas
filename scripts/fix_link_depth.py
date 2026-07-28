#!/usr/bin/env python3
"""Bulk fix for Patterns A + B from `MDBOOK_LINK_WARNINGS.md`.

Prepends one extra `../` to every link of shape `[](../../(examples|crates)/...)`
inside the `examples/` directory of each book. The off-by-one path-depth
bug surfaces because `examples/*.md` lives at `docs/book/examples/<file>.md`,
so `../../<thing>` resolves at `docs/<thing>` instead of the project root
`<thing>`.

We use a `sub` callback rather than a fixed replacement string. Python's
re-substitution keeps `\X` (any non-letter escape) as the two literal chars
`\X` (per CPython's re module docs), so writing a REPLACE string with
`\\.\\./` produces `\,` `\,`, `` /`` rather than `.` `.` `/`. A callback
side-steps that ambiguity.

CLI:
    fix_link_depth.py [--dry-run] [ROOT ...]

If no `ROOT` is supplied, defaults to `repos/CFDrs/docs/book/examples` and
`repos/helios/docs/book/examples` (the two affected books per the follow-up
plan). Pass additional roots for any other book that adopts the same pattern.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Exactly two `../` segments at the start of the URL portion, immediately
# followed by `examples/` or `crates/`. We deliberately do NOT anchor on what
# precedes the `..` segments; the link text comes after `](`, so we anchor
# on the ASCII `]` + `(` directly. Combined with the substitution callback
# below, idempotency holds: after re-running the script, the new URL is
# `](../../../examples/...)` whose `..` segment at offset 0 is followed by
# `/..` then `/..`  then `/..` then `/examples/` — offset 0 is `..`, offset
# 1 is `.`, offset 2 is `/`. The PATTERN requires `..`/``i.e. `.` + `.` +
# `/` at offsets 0-2. After the match, the next segment would need to be
# `examples` starting at offset 6, but offset 6 is `.`. Failure to match
# here makes the regex fall through to the next try-position, which also
# fails. Confirmed idempotent.
PATTERN = re.compile(r"""\]\(\.\./\.\./(examples|crates)/""")


def rewrite(text: str) -> tuple[str, int]:
    """Return (rewritten_text, replacement_count).

    Replacement is unambiguous: `](../ + '../../../' + <group1> + '/`.
    The full output fragment is `](./../../<group1>/` -- but wait, we
    are *adding* one `../`, so the output should be
    `](../<group1>/` actually `](../../<group1>/` -- the replacement is
    built character-by-character to avoid escape ambiguity.
    """

    def repl(match: re.Match[str]) -> str:
        return "]" + "(" + "../../../" + match.group(1) + "/"

    return PATTERN.subn(repl, text)


def walk(root: Path, dry_run: bool) -> tuple[int, int, list[str]]:
    """Return (files_changed, total_replacements, sample_lines)."""
    files_changed = 0
    total_replacements = 0
    sample_lines: list[str] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        new_text, count = rewrite(text)
        if count == 0:
            continue
        files_changed += 1
        total_replacements += count
        for ln in PATTERN.finditer(text):
            sample_lines.append(f"    {path.name}:  {ln.group(0)}")
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
    return files_changed, total_replacements, sample_lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without modifying any file.",
    )
    ap.add_argument(
        "roots",
        nargs="*",
        default=[
            "repos/CFDrs/docs/book/examples",
            "repos/helios/docs/book/examples",
        ],
        help="Book roots to scan (default: CFDrs + helios examples).",
    )
    args = ap.parse_args()

    print(
        f"Mode: {'DRY-RUN (no writes)' if args.dry_run else 'APPLY (writes to disk)'}"
    )
    grand_files = 0
    grand_subs = 0
    for root in args.roots:
        rp = Path(root)
        if not rp.exists():
            print(f"\nSKIP (missing): {root}")
            continue
        files, subs, samples = walk(rp, args.dry_run)
        grand_files += files
        grand_subs += subs
        print(f"\n{root}")
        print(f"  files affected       : {files}")
        print(f"  replacements applied : {subs}")
        if samples:
            shown = samples[:5]
            print(f"  sample matches       :")
            for line in shown:
                print(line)
            if len(samples) > 5:
                print(f"    (... and {len(samples) - 5} more)")

    print(
        f"\nTOTAL: {grand_files} files affected, {grand_subs} replacements "
        f"({'would-be' if args.dry_run else 'actually applied'})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
