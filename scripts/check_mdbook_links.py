"""
Portable mdbook-equivalent dead-link detector.

Walks every chapter file in a book, parses inline links `[text](href)`,
validates:
  - File paths resolve to existing files (FILE_MISSING)
  - Anchor references (#slug) correspond to a heading in the target file (ANCHOR_MISSING)
  - External URLs / mailto / anchors-only are skipped

Exit codes:
  0   clean (no FILE_MISSING)
  1   FILE_MISSING > 0 (default gate; relaxed by --advisory, tightened by --strict-placeholder)
  2   invocation error (no books supplied)

Pattern classification (Patterns C / D / E / F from MDBOOK_LINK_WARNINGS.md)
is appended to each FILE_MISSING row to aid triage.  --strict-placeholder
elevates Pattern D / F rows so an explicit allow-list can be maintained
per-target once the responsible chapters materialise.

Forward-defence allow-list: `.check_mdbook_links_allowlist` at the atlas
repo root (JSON, schema documented in that file).  If a FILE_MISSING
row's `(source, href)` matches an entry, the row is silently skipped
(and prefixed with `allowlist:` in the per-link section) so the strict-
mode CI gate does not block legitimate commits.  Today's allow-list is
empty — the gate is green across all 3 atlases — but the scaffold lets
future contributors quickly silence a new false-positive pattern
without re-running detector analysis.

Architectural note (latent bug, masked by FILE_MISSING : 0 on all 3 atlases):
`check_book()` previously referenced `allowlist` as a free variable that was
only defined locally inside `main()`.  This worked by accident — every atlas
had FILE_MISSING : 0 post-§7-#5, so the `if allowlist and ...` line was
unreachable.  The first time FILE_MISSING > 0 occurred (e.g., the new
`docs-link-smoke-test` fixture with the SINGLE_CHAR_HREF_RE filter disabled
during the negative test), the detector raised `NameError: name 'allowlist'
is not defined`.  Fix: `allowlist` is now an explicit parameter on
`check_book()` (defaulting to `frozenset()` for backward-compat).  This
unifies `check_book` as a pure function over its inputs — no implicit
free-variable dependency on `main`'s scope.

Usage:
    check_mdbook_links.py [--advisory] [--strict-placeholder] <book-root> [<book-root> ...]
"""

import sys
import re
import json
import argparse
from pathlib import Path
from urllib.parse import unquote, urlparse


# Patterns C / D / E / F — see MDBOOK_LINK_WARNINGS.md.  Order matters in
# classify_pattern(): trailing-slash (D) → src/*.rs (F) → cross-book (C)
# → depth-3 README (E).  First match wins so labels don't collide.
PATTERN_F_RE = re.compile(r"^(?:\.\./)+crates/[^/]+/src/[^/]+(?:/[^/]+)*\.rs$")
PATTERN_C_RE = re.compile(r"^(?:\.\./)+(?:[\w-]+)/docs/book/")
PATTERN_E_RE = re.compile(r"^(?:\.\./){3,}README\.md$")
LATEX_HREF_RE = re.compile(r"^\\[A-Za-z]+")


# Forward-defence allow-list — `.check_mdbook_links_allowlist` at the atlas
# repo root (JSON, schema documented in that file).  The detector loads this
# file once at startup; matching FILE_MISSING rows are silently skipped
# (with an `allowlist:` prefix in the per-link section).  See
# `MDBOOK_DETECTOR_PARITY_KWAVERS.md` §3 Issue B for the historical pattern
# (FDTD-recurrence `[n+1](x)`) that the SINGLE_CHAR_HREF_RE filter already
# handles detector-wide — entries in `.check_mdbook_links_allowlist` are
# for true per-row exceptions only.
ALLOWLIST_PATH = Path(__file__).resolve().parent.parent / ".check_mdbook_links_allowlist"


def load_allowlist(path: Path = ALLOWLIST_PATH) -> set:
    """Load the forward-defence allow-list from JSON.  Returns a set of
    `(source, href)` tuples.  Missing file → empty set (no error)."""
    if not path.exists():
        return set()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"  WARNING: allow-list at {path} unreadable: {e}", file=sys.stderr)
        return set()
    allow = doc.get("allow", []) if isinstance(doc, dict) else []
    out = set()
    for entry in allow:
        if not isinstance(entry, dict):
            continue
        src = entry.get("source")
        href = entry.get("href")
        if isinstance(src, str) and isinstance(href, str):
            out.add((src, href))
    return out
# Pattern G false-positive filter: finite-difference notation
# `p[n+1](x)` matches the inline-link regex as `[n+1](x)` even though it
# is an array-indexed function call, not a markdown link.  Real chapter
# hrefs are always named (multi-char, contain `/` or `.md`); a single
# alphanumeric href is almost always math notation.  Mirrors the
# LATEX_HREF_RE precedent (Pattern G reclassified; see
# MDBOOK_DETECTOR_PARITY_KWAVERS.md §3 Issue B).
SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")


def classify_pattern(href: str) -> str:
    """Return a single-letter Pattern label for a missing-file href, or '' if unclassified."""
    if href.endswith("/"):
        return "D"
    if PATTERN_F_RE.match(href):
        return "F"
    if PATTERN_C_RE.match(href):
        return "C"
    if PATTERN_E_RE.match(href):
        return "E"
    return ""


def is_external(href: str) -> bool:
    if href.startswith(("http://", "https://", "mailto:", "//")):
        return True
    p = urlparse(href)
    return bool(p.scheme)


def extract_links(content: str):
    """Yield raw href strings from inline `[text](href)` and reference-style"""
    # Inline form.  `[^)\n]+` (rather than the more permissive `[^)]+`)
    # restricts the href to a single line; combined with the LaTeX-
    # noise filter (LATEX_HREF_RE, module-level) below, it silences
    # kwavers-style single-line `[F(m)](\mathbf{r}_s, t)` math noise.
    # See MDBOOK_DETECTOR_PARITY_KWAVERS.md § Issue A.
    for m in re.finditer(r"\[[^\]]*\]\(([^)\n]+)\)", content):
        href = m.group(1).strip()
        # Skip hrefs whose content starts with a LaTeX command — e.g.
        # `[F(m)](\mathbf{r}_s, t)` is a math bracket followed by a
        # math parens on the same line; the author wrote LaTeX, not an
        # actual link.  Real markdown-link hrefs almost never start
        # with a backslash.  See kwavers §7 #1 § Issue A.
        if LATEX_HREF_RE.match(href):
            continue
        # Pattern G filter (mirror of LATEX_HREF_RE above): skip single-
        # character hrefs, which overwhelmingly come from finite-
        # difference recurrence notation `f[n+1](x)` rather than real
        # markdown links.  See MDBOOK_DETECTOR_PARITY_KWAVERS.md §3
        # Issue B for the kwavers `[n+1](x)` false positive.
        if SINGLE_CHAR_HREF_RE.match(href):
            continue
        yield href
    # Reference-style shorthand: [foo]: path then [foo] inline.
    # We deliberately do NOT walk reference-style — mdBook's link checker
    # also primarily covers inline form. Document if needed.


def slugify(heading: str) -> str:
    """Replicate mdbook's heading slug rule."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", heading)
    s = re.sub(r"[`*_~]", "", s)
    s = s.lower()
    # mdbook keeps Unicode word chars and replaces non-word, non-em-dash, non-space, non-hyphen
    # NOTE: em-dash (U+2014) is intentionally NOT in the keep-set; mdbook strips it.
    # Anything outside [a-zA-Z0-9_\s-] is dropped to match mdbook's slug rule.
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s


def check_book(book_root: str, name: str, allowlist: frozenset = frozenset()):
    root = Path(book_root).resolve()
    if not root.exists():
        return {"name": name, "error": f"directory not found: {root}"}

    files_checked = 0
    links_checked = 0
    file_missing = []
    anchor_missing = []
    read_fail = []
    md_files = sorted(root.rglob("*.md"))
    for md in md_files:
        files_checked += 1
        try:
            content = md.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # pragma: no cover
            read_fail.append((md.relative_to(root).as_posix(), str(e)))
            continue
        origin = md.relative_to(root).as_posix()
        # Pre-compute heading slugs of this file once for anchor checks
        local_anchor_set = set()
        for _h, title in re.findall(r"^(#{1,6})\s+(.*?)\s*$", content, re.MULTILINE):
            slug = slugify(title)
            local_anchor_set.add(slug)
            # explicit {#id} attr
            for am in re.finditer(r"\{#([\w-]+)\}", title):
                local_anchor_set.add(am.group(1).lower())

        for href in extract_links(content):
            # Anchor-only links are NOT skipped; they fall through and are validated
            # against the local anchor set (mdbook enforces in-page anchors too).
            if not href or is_external(href):
                continue
            anchor = None
            path_part = href
            if "#" in href:
                path_part, anchor = href.split("#", 1)
                anchor = unquote(anchor)
            path_part = unquote(path_part)
            if not path_part:
                # pure anchor linked to current page
                if anchor and slugify(anchor) not in local_anchor_set:
                    anchor_missing.append((origin, href, anchor))
                continue
            target = (md.parent / path_part).resolve()
            links_checked += 1
            if not target.exists():
                # Forward-defence allow-list: if (origin, href) is in the
                # atlas-root allow-list, skip the FILE_MISSING entry (the
                # allow-list signals a documented exception — e.g., a
                # pattern the detector can't yet filter detector-wide).
                if allowlist and (origin, href) in allowlist:
                    file_missing.append((origin, href, str(target), "allowlisted"))
                else:
                    file_missing.append((origin, href, str(target), None))
                continue
            if anchor:
                # If the target is the same file, use the precomputed set
                if target.resolve() == md.resolve():
                    if slugify(anchor) not in local_anchor_set:
                        anchor_missing.append((origin, href, anchor))
                    continue
                try:
                    tc = target.read_text(encoding="utf-8", errors="replace")
                except Exception as e:  # pragma: no cover
                    read_fail.append((origin, href, str(e)))
                    continue
                t_anchors = set()
                for _h, title in re.findall(
                    r"^(#{1,6})\s+(.*?)\s*$", tc, re.MULTILINE
                ):
                    t_anchors.add(slugify(title))
                    for am in re.finditer(r"\{#([\w-]+)\}", title):
                        t_anchors.add(am.group(1).lower())
                if slugify(anchor) not in t_anchors:
                    anchor_missing.append((origin, href, anchor))

    return {
        "name": name,
        "files_checked": files_checked,
        "links_checked": links_checked,
        "file_missing": file_missing,
        "anchor_missing": anchor_missing,
        "read_fail": read_fail,
    }


def _file_missing_allowlisted_count(file_missing):
    """Return the count of FILE_MISSING rows that were allow-list-skipped."""
    return sum(1 for row in file_missing if len(row) >= 4 and row[3] == "allowlisted")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Portable mdbook-equivalent dead-link detector.",
        epilog=(
            "Exit codes: 0=clean, 1=FILE_MISSING (default; relaxed by "
            "--advisory, tightened by --strict-placeholder), 2=invocation error."
        ),
    )
    parser.add_argument(
        "books",
        nargs="+",
        help="book-root directories to scan (e.g. repos/CFDrs/docs/book).",
    )
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="print warnings but always exit 0 (print-only CI mode).",
    )
    parser.add_argument(
        "--strict-placeholder",
        action="store_true",
        help=(
            "escalate Pattern D / F FILE_MISSING rows to gate-failure so "
            "per-target placeholder allow-lists can be made explicit."
        ),
    )
    args = parser.parse_args(argv)

    total_file_missing = 0
    total_allowlisted = 0    # subset of FILE_MISSING that the allow-list silenced
    total_anchor_missing = 0
    placeholder_errors = 0  # Pattern D or F under --strict-placeholder
    bad_paths = 0           # paths that failed existence check (exit 2 if all bad)

    allowlist = load_allowlist()
    if allowlist:
        print(f"# allow-list loaded: {len(allowlist)} entries from {ALLOWLIST_PATH}", file=sys.stderr)

    for root in args.books:
        rp = Path(root).resolve()
        if not rp.exists():
            print(f"\n== {root} ==", file=sys.stderr)
            print(f"  ERROR: directory not found: {rp}", file=sys.stderr)
            bad_paths += 1
            continue
        name = rp.parent.parent.name if rp.name == "book" else rp.name
        r = check_book(root, name, allowlist)
        print(f"\n== {r['name']} ==")
        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue
        print(f"  files scanned : {r['files_checked']}")
        print(f"  links scanned : {r['links_checked']}")
        fm = r["file_missing"]
        am = r["anchor_missing"]
        rf = r["read_fail"]
        total_file_missing += len(fm)
        total_allowlisted += _file_missing_allowlisted_count(fm)
        total_anchor_missing += len(am)
        print(f"  FILE_MISSING  : {len(fm)}")
        # Show the allowlist-skipped subset for transparency.
        allow_count = _file_missing_allowlisted_count(fm)
        if allow_count:
            print(f"  FILE_MISSING (allow-listed): {allow_count}")
        if fm:
            seen_pairs = set()
            for row in fm:
                # Backwards-compatible tuple shape: 3-tuple (legacy) or
                # 4-tuple with `allowlist` flag at index 3 (current).
                if len(row) >= 4:
                    origin, href, tgt, allow_flag = row
                else:
                    origin, href, tgt = row
                    allow_flag = None
                key = (origin, href)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                pat = classify_pattern(href)
                prefix = "allowlist: " if allow_flag == "allowlisted" else ""
                suffix = f" [Pattern {pat}]" if pat else ""
                print(f"    - {prefix}in {origin}: link [{href}] -> {tgt}{suffix}")
                if args.strict_placeholder and pat in ("D", "F"):
                    placeholder_errors += 1
        print(f"  ANCHOR_MISSING: {len(am)}")
        if am:
            for origin, href, anchor in am:
                print(f"    - in {origin}: link [{href}] misses anchor #{anchor}")
        print(f"  READ_FAIL     : {len(rf)}")
        if rf:
            for item in rf:
                print(f"    - {item}")

    # ---- Exit code decision ----
    # All books invalid?  Treat as invocation error (exit 2) so a
    # typo'd CI step can't silently pass — better to fail loud.
    if len(args.books) > 0 and bad_paths == len(args.books):
        return 2
    if args.advisory:
        # Print-only: warnings printed above, exit 0 unconditionally so
        # the run doesn't block commits while the 12 known misses are
        # still being triaged (§7 #5 in MDBOOK_DETECTOR_PARITY.md).
        return 0
    # Strip allow-listed rows from the gate decision — they're documented
    # exceptions, not real bugs.  total_allowlisted was accumulated during
    # the main book loop above (no double-scanning required).
    real_file_missing = total_file_missing - total_allowlisted
    if real_file_missing > 0:
        return 1
    # --strict-placeholder with no FILE_MISSING but D/F-specific misses.
    # Currently unreachable (Pattern D/F are already counted under
    # total_file_missing).  Kept for forward-compat: if a future
    # allow-list downgrades D/F from FILE_MISSING to PLACEHOLDER_MISSING,
    # --strict-placeholder re-elevates them without double-counting.
    if args.strict_placeholder and placeholder_errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
