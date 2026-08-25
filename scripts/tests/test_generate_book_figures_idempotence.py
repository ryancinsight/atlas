#!/usr/bin/env python3
"""Fixed-point tests for figure-block insertion into chapter markdown.

`process_book` must be idempotent: running it twice (with or without
``--force``) yields byte-identical chapter files, and regeneration collapses
blank-line runs leaked by earlier generator versions instead of growing them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from generate_book_figures.core import process_book

CHAPTER = "# Chapter 1 — Governing Equations\n\nBody text follows the heading.\n"

LEAKED = (
    "# Chapter 1 — Governing Equations\n"
    "\n"
    "<!-- generated-figure-start -->\n"
    "![Figure 1.1 — old](figures/ch01/fig01_1_governing_equations.svg)\n"
    "*Figure 1.1 — old*\n"
    "<!-- generated-figure-end -->\n" + "\n" * 30 + "Body text follows the heading.\n"
)


@pytest.fixture()
def book_dir(tmp_path: Path) -> Path:
    book = tmp_path / "docs" / "book"
    book.mkdir(parents=True)
    (book / "SUMMARY.md").write_text(
        "# Summary\n\n- [Governing Equations](governing_equations.md)\n",
        encoding="utf-8",
    )
    return book


def test_force_regeneration_is_a_fixed_point(book_dir: Path) -> None:
    page = book_dir / "governing_equations.md"
    page.write_text(CHAPTER, encoding="utf-8")

    process_book(book_dir, dry_run=False, force=True)
    first = page.read_text(encoding="utf-8")
    assert "<!-- generated-figure-start -->" in first

    process_book(book_dir, dry_run=False, force=True)
    second = page.read_text(encoding="utf-8")
    assert first == second, "second --force run must not change the page"


def test_regeneration_collapses_leaked_blank_runs(book_dir: Path) -> None:
    page = book_dir / "governing_equations.md"
    page.write_text(LEAKED, encoding="utf-8")

    process_book(book_dir, dry_run=False, force=True)
    text = page.read_text(encoding="utf-8")
    assert "\n\n\n" not in text, "blank-line run must collapse on regeneration"
    assert text.endswith("Body text follows the heading.\n")
    assert text.count("<!-- generated-figure-start -->") == 1


if __name__ == "__main__":
    pytest.main([__file__])
