"""Portable mdBook dead-link detector with heading checks.

Checks inline local destinations and headings while ignoring code examples.
Existing classifications, allowlists and CLI exit policies remain unchanged.
Historical parsing rationale and supported syntax live in
docs/mdbook/link-detector-internals.md.

Usage: check_mdbook_links.py [--advisory] [--strict-placeholder] BOOK ...
"""

import sys
import re
import json
import argparse
from pathlib import Path
from urllib.parse import unquote, urlparse


PATTERN_F_RE = re.compile(r"^(?:\.\./)+crates/[^/]+/src/[^/]+(?:/[^/]+)*\.rs$")
PATTERN_C_RE = re.compile(r"^(?:\.\./)+(?:[\w-]+)/docs/book/")
PATTERN_E_RE = re.compile(r"^(?:\.\./){3,}README\.md$")
LATEX_HREF_RE = re.compile(r"^\\[A-Za-z]+")


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


FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})\s*(?P<info>[^`]*)$")
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")


def _mask_fenced(content: str) -> str:
    """Blank out FENCED code regions only, preserving line structure.

    Used where code-block content must not be seen but inline code spans
    must survive (heading extraction: mdBook keeps inline-code content in
    heading text, so ``The `AllocPolicy` trait`` → `the-allocpolicy-trait`).
    """
    out: list[str] = []
    closing: re.Pattern[str] | None = None
    for line in content.split("\n"):
        if closing is None:
            opened = FENCE_OPEN_RE.match(line)
            if opened:
                run = opened.group("fence")
                closing = re.compile(
                    r" {0,3}" + re.escape(run[0])
                    + "{" + str(len(run)) + r",}[ \t]*\r?"
                )
                out.append("")
                continue
            out.append(line)
            continue
        if closing.fullmatch(line):
            closing = None
        out.append("")
    return "\n".join(out)


def mask_code(content: str) -> str:
    """Blank out code regions so link syntax inside them is not checked.

    mdBook does not resolve links inside code, and book prose routinely
    shows markdown, shell, or TOML snippets containing bracket-paren
    text that is not a link (``[dependencies]``, ``[foo](bar)`` in a
    markdown example). Fenced blocks and inline spans are replaced with
    blanks. Line structure is preserved so the masked text stays
    positionally aligned with the original.
    """
    return INLINE_CODE_RE.sub(" ", _mask_fenced(content))


def extract_links(content: str):
    """Yield raw href strings from inline `[text](href)` and reference-style"""
    content = mask_code(content)
    for m in re.finditer(r"\[[^\]]*\]\(([^)\n]+)\)", content):
        href = m.group(1).strip()
        if LATEX_HREF_RE.match(href):
            continue
        if SINGLE_CHAR_HREF_RE.match(href):
            continue
        yield href


HTML_ENTITY_RE = re.compile(r"&(?:#(\d+)|#x([0-9a-fA-F]+)|(amp|lt|gt|quot|apos|nbsp));")
HTML_ENTITY_NAMED = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": "\"",
    "apos": "'",
    "nbsp": " ",
}

HEADING_ATTR_RE = re.compile(r"\s*\{[^}]*\}\s*$")


def _decode_entities(s: str) -> str:
    def _sub(m):
        dec, hexd, named = m.group(1), m.group(2), m.group(3)
        if dec:
            try:
                return chr(int(dec))
            except ValueError:
                return m.group(0)
        if hexd:
            try:
                return chr(int(hexd, 16))
            except ValueError:
                return m.group(0)
        return HTML_ENTITY_NAMED[named]

    return HTML_ENTITY_RE.sub(_sub, s)


def _render_heading_text(title: str) -> str:
    """Approximate pulldown-cmark's rendered Text for an ATX heading line.

    Empirical parity against the mdBook v0.5.4 binary (see the battery of
    probes in the ATLAS-BOOK-ANCHOR-PARITY-001 record):
      - `[text](url)` → `text` (link text survives, url does not)
      - inline code `` `x` `` → `x` (content survives, backticks don't)
      - `*em*` / `**bold**` / `~strike~` → text; underscore emphasis
        `_em_` / `__bold__` strips the delimiters, but INTRaword underscores
        (`foo_bar`, `a_b c`) are literal and must survive into the id
      - smart punctuation `---` → em-dash, `--` → en-dash (dropped later)
      - a TRAILING `{...}` group is a heading attribute: stripped entirely
        (its `{#id}` becomes the explicit id — handled by heading_ids)
      - HTML entities decode to their literal character
    """
    s = title
    s = s.replace("---", "\u2014").replace("--", "\u2013")
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"`+([^`\n]*)`+", r"\1", s)
    s = re.sub(r"__([^_\s]+)__", r"\1", s)
    s = re.sub(r"(?<!\w)_([^_\s]+)_(?!\w)", r"\1", s)
    s = re.sub(r"[*~]+", "", s)
    s = HEADING_ATTR_RE.sub("", s)
    return _decode_entities(s)


def heading_slug(title: str) -> str:
    """mdBook v0.5.4 heading-id rule, applied to RAW markdown title text.

    Mirrors the pipeline mdBook applies to the RENDERED heading text before
    slugging (empirically verified against the v0.5.4 binary):

      1. `_render_heading_text` approximates pulldown-cmark's Text events:
         link text, inline-code content, emphasis markers, smart
         punctuation (`--`/`---` → en/em-dash), trailing attribute groups,
         and HTML entities are all resolved.
      2. char loop (mdBook `normalize_id`): EACH whitespace char → `-`
         (runs are NOT collapsed — `A  B` → `a--b`); Unicode alphanumeric →
         lowercased; `-` and `_` are KEPT as-is; every other character
         (em/en-dash, punctuation, …) is dropped.  No leading/trailing
         trimming: `- leading hyphen` → `--leading-hyphen`.  This is why
         `CSD — Constrained ...` → `csd--constrained-...`: the em-dash
         vanishes but each surrounding space still yields its own hyphen.
    """
    out = []
    for ch in _render_heading_text(title):
        if ch.isspace():
            out.append("-")
        elif ch.isalnum():
            out.append(ch.lower())
        elif ch in "-_":
            out.append(ch)
    return "".join(out)


def slugify(anchor: str) -> str:
    """Normalize a LINK anchor for set membership.

    This is the pure char loop of `heading_slug` WITHOUT the markdown/
    smart-punctuation pre-steps: a link fragment is already the author's
    intended id (e.g. `#csd--constrained-...`), so `--` must survive as
    two literal hyphens.  Lowercasing keeps the historical leniency
    (`#Intro` matches heading `Intro`).
    """
    out = []
    for ch in anchor:
        if ch.isspace():
            out.append("-")
        elif ch.isalnum():
            out.append(ch.lower())
        elif ch in "-_":
            out.append(ch)
    return "".join(out)


def heading_ids(content: str) -> list[str]:
    """All heading anchor ids mdBook would emit for a file, in document order.

    Auto-generated slugs collide → mdBook appends `-1`, `-2`, … suffixes in
    order of appearance (verified: three `a--b`-producing headings yield
    `a--b`, `a--b-1`, `a--b-2`).  A TRAILING `{#id}` attribute overrides the
    slug verbatim, case-preserved, and is exempt from the dedup counter
    (verified: two `{#same-anchor}` headings both emit `same-anchor`;
    `{#CamelCase-Anchor}` keeps its case).

    Fenced code blocks are masked first: `#`-prefixed lines inside a fence
    (e.g. rustdoc/doctest markers like `# Ok::<()>(())` inside a ```rust
    block) are code, not headings — mdBook emits no heading id for them.
    Inline code spans are intentionally NOT masked: mdBook keeps inline-code
    content in the rendered heading text (`The `AllocPolicy` trait` →
    `the-allocpolicy-trait`).
    """
    content = _mask_fenced(content)
    ids: list[str] = []
    auto_seen: dict[str, int] = {}
    for _h, title in re.findall(r"^(#{1,6})\s+(.*?)\s*$", content, re.MULTILINE):
        am = re.search(r"\{#([\w-]+)\}\s*$", title)
        if am is not None:
            ids.append(am.group(1))
            continue
        base = heading_slug(title)
        n = auto_seen.get(base, 0)
        if n == 0:
            ids.append(base)
            auto_seen[base] = 1
        else:
            ids.append(f"{base}-{n}")
            auto_seen[base] = n + 1
    return ids


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
        local_anchor_set = set()
        for hid in heading_ids(content):
            local_anchor_set.add(hid)
            local_anchor_set.add(hid.lower())

        for href in extract_links(content):
            if not href or is_external(href):
                continue
            anchor = None
            path_part = href
            if "#" in href:
                path_part, anchor = href.split("#", 1)
                anchor = unquote(anchor)
            path_part = unquote(path_part)
            if not path_part:
                if anchor and slugify(anchor) not in local_anchor_set:
                    anchor_missing.append((origin, href, anchor))
                continue
            if path_part.startswith("/"):
                target = (root / path_part.lstrip("/")).resolve()
            else:
                target = (md.parent / path_part).resolve()
            links_checked += 1
            if not target.exists():
                if allowlist and (origin, href) in allowlist:
                    file_missing.append((origin, href, str(target), "allowlisted"))
                else:
                    file_missing.append((origin, href, str(target), None))
                continue
            if anchor:
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
                for hid in heading_ids(tc):
                    t_anchors.add(hid)
                    t_anchors.add(hid.lower())
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
        allow_count = _file_missing_allowlisted_count(fm)
        if allow_count:
            print(f"  FILE_MISSING (allow-listed): {allow_count}")
        if fm:
            seen_pairs = set()
            for row in fm:
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

    if len(args.books) > 0 and bad_paths == len(args.books):
        return 2
    if args.advisory:
        return 0
    real_file_missing = total_file_missing - total_allowlisted
    if real_file_missing > 0:
        return 1
    if args.strict_placeholder and placeholder_errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
