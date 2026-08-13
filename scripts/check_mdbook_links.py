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

Pattern classification (Patterns C / D / E / F from docs/mdbook/link-warnings.md)
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


# Patterns C / D / E / F — see docs/mdbook/link-warnings.md.  Order matters in
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
# `docs/mdbook/detector-parity-kwavers.md` §3 Issue B for the historical pattern
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
# docs/mdbook/detector-parity-kwavers.md §3 Issue B).
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


# Fenced code block (CommonMark): a run of 3+ backticks or tildes,
# indented at most 3 spaces, with an optional info string. The closing
# fence uses the same character and is at least as long. An unterminated
# fence runs to end of document, which is also CommonMark's rule.
FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})\s*(?P<info>[^`]*)$")
# Inline code span: a backtick run, single-line content, closing run.
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")


def _mask_fenced(content: str) -> str:
    """Blank out FENCED code regions only, preserving line structure.

    Used where code-block content must not be seen but inline code spans
    must survive (heading extraction: mdBook keeps inline-code content in
    heading text, so ``The `AllocPolicy` trait`` → `the-allocpolicy-trait`).
    """
    out: list[str] = []
    fence: tuple[str, int] | None = None
    for line in content.split("\n"):
        if fence is None:
            opened = FENCE_OPEN_RE.match(line)
            if opened:
                run = opened.group("fence")
                fence = (run[0], len(run))
                out.append("")
                continue
            out.append(line)
            continue
        char, length = fence
        closing = line.strip()
        if closing and set(closing) == {char} and len(closing) >= length:
            fence = None
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
    # Code is masked first: a link inside a fenced block or inline span is
    # illustrative text, not a link mdBook would resolve.
    content = mask_code(content)
    # Inline form.  `[^)\n]+` (rather than the more permissive `[^)]+`)
    # restricts the href to a single line; combined with the LaTeX-
    # noise filter (LATEX_HREF_RE, module-level) below, it silences
    # kwavers-style single-line `[F(m)](\mathbf{r}_s, t)` math noise.
    # See docs/mdbook/detector-parity-kwavers.md § Issue A.
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
        # markdown links.  See docs/mdbook/detector-parity-kwavers.md §3
        # Issue B for the kwavers `[n+1](x)` false positive.
        if SINGLE_CHAR_HREF_RE.match(href):
            continue
        yield href
    # Reference-style shorthand: [foo]: path then [foo] inline.
    # We deliberately do NOT walk reference-style — mdBook's link checker
    # also primarily covers inline form. Document if needed.


# HTML entity references that can appear in heading text.  mdBook's parser
# decodes these to their literal character (which the char-loop below then
# drops, or turns into a hyphen for &nbsp;).  Mirroring the decode matters:
# e.g. `x &amp; y` renders as `x & y` in mdBook → id `x--y`; without the
# decode the raw letters `amp` would wrongly survive into the slug.
HTML_ENTITY_RE = re.compile(r"&(?:#(\d+)|#x([0-9a-fA-F]+)|(amp|lt|gt|quot|apos|nbsp));")
HTML_ENTITY_NAMED = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": "\"",
    "apos": "'",
    "nbsp": " ",
}

# Trailing heading-attribute group consumed by pulldown-cmark's heading-
# attributes parser (mdBook enables it): `NAV{1}` → text `NAV` (id `nav`),
# `NAV {#x}` → text `NAV` + explicit id `x`.  The group must be the LAST
# thing on the heading line (optional preceding whitespace); mid-heading
# braces like `a {b} c` are literal text (braces dropped, content kept).
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
    # Order matters: replace `---` before `--` so `A --- B` becomes the
    # em-dash form (→ `a--b`), not an en-dash plus a stray hyphen.
    s = s.replace("---", "\u2014").replace("--", "\u2013")
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    # Inline code span: keep the content, drop the backticks.
    s = re.sub(r"`+([^`\n]*)`+", r"\1", s)
    # Underscore emphasis: `__bold__` then non-intraword `_em_`; the
    # lookarounds keep intraword underscores (foo_bar) as literal text.
    s = re.sub(r"__([^_\s]+)__", r"\1", s)
    s = re.sub(r"(?<!\w)_([^_\s]+)_(?!\w)", r"\1", s)
    # Star emphasis / strikethrough markers (dropped by the char loop anyway;
    # stripping them here mirrors pulldown rendering `*em*` → `em`).
    s = re.sub(r"[*~]+", "", s)
    # Trailing heading attribute group (non-id): `NAV{1}` → `NAV`.
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
        # else: dropped (em-dash, en-dash, punctuation, …)
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
        # Pre-compute heading anchor ids of this file once for anchor checks.
        # Explicit `{#id}` ids are case-preserved in the parity list, but the
        # link side compares through `slugify` (which lowercases); adding the
        # lowercased variant here keeps both an exact-case link
        # (`#CamelCase-Anchor`) and the historical lowercase-lenient form
        # resolving, without disturbing the byte-for-byte parity list.
        local_anchor_set = set()
        for hid in heading_ids(content):
            local_anchor_set.add(hid)
            local_anchor_set.add(hid.lower())

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
            if path_part.startswith("/"):
                # mdBook resolves a leading `/` against the book root, not
                # the filesystem. `Path.__truediv__` silently discards the
                # left operand when the right side is absolute, which sent
                # `/README.md` to the drive root and reported every
                # root-absolute link as missing.
                target = (root / path_part.lstrip("/")).resolve()
            else:
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
        # still being triaged (§7 #5 in docs/mdbook/detector-parity.md).
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
