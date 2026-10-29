"""Code-region masking and inline destination extraction for book validation."""

import re

LATEX_HREF_RE = re.compile(r"^\\[A-Za-z]+")

# Pattern G false-positive filter: finite-difference notation
# `p[n+1](x)` matches the inline-link regex as `[n+1](x)` even though it
# is an array-indexed function call, not a markdown link.  Real chapter
# hrefs are always named (multi-char, contain `/` or `.md`); a single
# alphanumeric href is almost always math notation.  Mirrors the
# LATEX_HREF_RE precedent (Pattern G reclassified; see
# docs/mdbook/detector-parity-kwavers.md §3 Issue B).
SINGLE_CHAR_HREF_RE = re.compile(r"^[a-zA-Z]$")


# Fenced code block (CommonMark): a run of 3+ backticks or tildes,
# indented at most 3 spaces, with an optional info string. The closing
# fence uses the same character and is at least as long. An unterminated
# fence runs to end of document, which is also CommonMark's rule.
FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})\s*(?P<info>[^`]*)$")
# Inline code span: a backtick run, single-line content, closing run.
INLINE_CODE_RE = re.compile(r"`+[^`\n]*`+")


def mask_fenced(content: str) -> str:
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
                # CommonMark 4.5 permits at most three leading spaces and
                # only ASCII spaces/tabs after the run. strip() admits
                # code-indented fences and other Unicode whitespace.
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
    return INLINE_CODE_RE.sub(" ", mask_fenced(content))


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


