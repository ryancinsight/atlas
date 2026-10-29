# Documentation-link validator internals

The standalone entry point is `scripts/check_mdbook_links.py`. Keeping its
syntax, filters and heading functions together preserves the existing copied
validator contract and the root-symbol smoke controls. Existing docs workflow
and pre-commit path filters continue to watch the complete implementation.

The October 29 fence repair follows [CommonMark section 4.5](https://spec.commonmark.org/0.31.2/#fenced-code-blocks):
a closer permits zero to three leading ASCII spaces, the opening character
repeated at least as many times, and only ASCII spaces or tabs afterward.
CRLF is supported. Four-space/tab indentation and Unicode padding remain code.
Real destinations outside the closing fence remain subject to the strict gate.

This repair does not change inline-link classification, allowlists, heading
normalization or CLI exit policies. It does not claim complete CommonMark parsing.

## Retained historical rationale

The following notes were moved from the entry point at source revision
`6e495c8246be86bfd4c30613326f77294fd26dc9`; dated/current-state claims in
these historical notes are provenance, not new fleet qualification.

``````text

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


# Patterns C / D / E / F — see docs/mdbook/link-warnings.md.  Order matters in
# classify_pattern(): trailing-slash (D) → src/*.rs (F) → cross-book (C)
# → depth-3 README (E).  First match wins so labels don't collide.
# Forward-defence allow-list — `.check_mdbook_links_allowlist` at the atlas
# repo root (JSON, schema documented in that file).  The detector loads this
# file once at startup; matching FILE_MISSING rows are silently skipped
# (with an `allowlist:` prefix in the per-link section).  See
# `docs/mdbook/detector-parity-kwavers.md` §3 Issue B for the historical pattern
# (FDTD-recurrence `[n+1](x)`) that the SINGLE_CHAR_HREF_RE filter already
# handles detector-wide — entries in `.check_mdbook_links_allowlist` are
# for true per-row exceptions only.
# Pattern G false-positive filter: finite-difference notation
# `p[n+1](x)` matches the inline-link regex as `[n+1](x)` even though it
# is an array-indexed function call, not a markdown link.  Real chapter
# hrefs are always named (multi-char, contain `/` or `.md`); a single
# alphanumeric href is almost always math notation.  Mirrors the
# LATEX_HREF_RE precedent (Pattern G reclassified; see
# docs/mdbook/detector-parity-kwavers.md §3 Issue B).
# Fenced code block (CommonMark): a run of 3+ backticks or tildes,
# indented at most 3 spaces, with an optional info string. The closing
# fence uses the same character and is at least as long. An unterminated
# fence runs to end of document, which is also CommonMark's rule.
# Inline code span: a backtick run, single-line content, closing run.
# CommonMark 4.5 permits at most three leading spaces and
# only ASCII spaces/tabs after the run. strip() admits
# code-indented fences and other Unicode whitespace.
# Code is masked first: a link inside a fenced block or inline span is
# illustrative text, not a link mdBook would resolve.
# Inline form.  `[^)\n]+` (rather than the more permissive `[^)]+`)
# restricts the href to a single line; combined with the LaTeX-
# noise filter (LATEX_HREF_RE, module-level) below, it silences
# kwavers-style single-line `[F(m)](\mathbf{r}_s, t)` math noise.
# See docs/mdbook/detector-parity-kwavers.md § Issue A.
# Skip hrefs whose content starts with a LaTeX command — e.g.
# `[F(m)](\mathbf{r}_s, t)` is a math bracket followed by a
# math parens on the same line; the author wrote LaTeX, not an
# actual link.  Real markdown-link hrefs almost never start
# with a backslash.  See kwavers §7 #1 § Issue A.
# Pattern G filter (mirror of LATEX_HREF_RE above): skip single-
# character hrefs, which overwhelmingly come from finite-
# difference recurrence notation `f[n+1](x)` rather than real
# markdown links.  See docs/mdbook/detector-parity-kwavers.md §3
# Issue B for the kwavers `[n+1](x)` false positive.
# Reference-style shorthand: [foo]: path then [foo] inline.
# We deliberately do NOT walk reference-style — mdBook's link checker
# also primarily covers inline form. Document if needed.
# HTML entity references that can appear in heading text.  mdBook's parser
# decodes these to their literal character (which the char-loop below then
# drops, or turns into a hyphen for &nbsp;).  Mirroring the decode matters:
# e.g. `x &amp; y` renders as `x & y` in mdBook → id `x--y`; without the
# decode the raw letters `amp` would wrongly survive into the slug.
# Trailing heading-attribute group consumed by pulldown-cmark's heading-
# attributes parser (mdBook enables it): `NAV{1}` → text `NAV` (id `nav`),
# `NAV {#x}` → text `NAV` + explicit id `x`.  The group must be the LAST
# thing on the heading line (optional preceding whitespace); mid-heading
# braces like `a {b} c` are literal text (braces dropped, content kept).
# Order matters: replace `---` before `--` so `A --- B` becomes the
# em-dash form (→ `a--b`), not an en-dash plus a stray hyphen.
# Inline code span: keep the content, drop the backticks.
# Underscore emphasis: `__bold__` then non-intraword `_em_`; the
# lookarounds keep intraword underscores (foo_bar) as literal text.
# Star emphasis / strikethrough markers (dropped by the char loop anyway;
# stripping them here mirrors pulldown rendering `*em*` → `em`).
# Trailing heading attribute group (non-id): `NAV{1}` → `NAV`.
# else: dropped (em-dash, en-dash, punctuation, …)
# Pre-compute heading anchor ids of this file once for anchor checks.
# Explicit `{#id}` ids are case-preserved in the parity list, but the
# link side compares through `slugify` (which lowercases); adding the
# lowercased variant here keeps both an exact-case link
# (`#CamelCase-Anchor`) and the historical lowercase-lenient form
# resolving, without disturbing the byte-for-byte parity list.
# Anchor-only links are NOT skipped; they fall through and are validated
# against the local anchor set (mdbook enforces in-page anchors too).
# pure anchor linked to current page
# mdBook resolves a leading `/` against the book root, not
# the filesystem. `Path.__truediv__` silently discards the
# left operand when the right side is absolute, which sent
# `/README.md` to the drive root and reported every
# root-absolute link as missing.
# Forward-defence allow-list: if (origin, href) is in the
# atlas-root allow-list, skip the FILE_MISSING entry (the
# allow-list signals a documented exception — e.g., a
# pattern the detector can't yet filter detector-wide).
# If the target is the same file, use the precomputed set
# Show the allowlist-skipped subset for transparency.
# Backwards-compatible tuple shape: 3-tuple (legacy) or
# 4-tuple with `allowlist` flag at index 3 (current).
# ---- Exit code decision ----
# All books invalid?  Treat as invocation error (exit 2) so a
# typo'd CI step can't silently pass — better to fail loud.
# Print-only: warnings printed above, exit 0 unconditionally so
# the run doesn't block commits while the 12 known misses are
# still being triaged (§7 #5 in docs/mdbook/detector-parity.md).
# Strip allow-listed rows from the gate decision — they're documented
# exceptions, not real bugs.  total_allowlisted was accumulated during
# the main book loop above (no double-scanning required).
# --strict-placeholder with no FILE_MISSING but D/F-specific misses.
# Currently unreachable (Pattern D/F are already counted under
# total_file_missing).  Kept for forward-compat: if a future
# allow-list downgrades D/F from FILE_MISSING to PLACEHOLDER_MISSING,
# --strict-placeholder re-elevates them without double-counting.
``````

## Fence boundary contract

A closing fence allows zero to three leading ASCII spaces, the opener's
character repeated at least as many times, then only ASCII spaces or tabs.
Four-space, tab or Unicode indentation keeps the apparent closing fence inside
the example. Stripping arbitrary whitespace closes such examples too early:
example links and headings become visible, and real destinations after the
actual closing fence can disappear from validation.

[The boundary regressions](../../scripts/tests/test_mdbook_fence_boundaries.py)
cover these cases, CRLF, valid fence controls and real missing-file failures.
An independent mdBook 0.4.40 render of the four-space fixture retains the
example and emits only the real link and heading; that observation does not
qualify a reusable workflow's configured renderer version.

The standalone validator retains its original root symbols and copied-file
runtime contract. Links and headings share its corrected existing mask;
classifications, allowlists, exit policies and gate activation paths remain
unchanged. The historical notes above keep the executable below 500 lines.
This repair does not establish member figure-generation closure or change
dependency, hook, pin or publication policy. Final delivery still requires
ordinary exact-revision tests, independent review and hosted gates.
