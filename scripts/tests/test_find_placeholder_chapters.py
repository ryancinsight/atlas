"""Regression tests for the mdBook placeholder detector."""

from __future__ import annotations

from pathlib import Path

from find_placeholder_chapters import scan


def test_source_backed_short_example_is_not_a_placeholder(tmp_path: Path) -> None:
    book = tmp_path / "book"
    source = tmp_path / "crate" / "examples" / "book_example.rs"
    source.parent.mkdir(parents=True)
    book.mkdir()
    source.write_text("fn main() {}\n", encoding="utf-8")
    (book / "example.md").write_text(
        "# Example\n\nShort description.\n\n"
        "```rust\n{{#include ../crate/examples/book_example.rs}}\n```\n",
        encoding="utf-8",
    )

    assert scan(book) == []


def test_missing_source_include_remains_a_placeholder(tmp_path: Path) -> None:
    book = tmp_path / "book"
    book.mkdir()
    (book / "example.md").write_text(
        "# Example\n\nShort description.\n\n"
        "```rust\n{{#include ../missing/example.rs}}\n```\n",
        encoding="utf-8",
    )

    assert scan(book) == [("example.md", 2)]
