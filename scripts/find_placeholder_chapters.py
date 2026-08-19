#!/usr/bin/env python3
"""List mdBook .md files that look like placeholder chapters."""

import re
import sys
from pathlib import Path

SKIP = {"SUMMARY.md", "README.md", "BOOK_ORGANIZATION.md"}
INCLUDE_DIRECTIVE = re.compile(r"\{\{#include\s+([^}\s]+)\s*\}\}")


def body_word_count(text: str) -> int:
    lines = text.splitlines()
    if not lines:
        return 0
    # Drop first heading if present
    if lines[0].startswith("#"):
        lines = lines[1:]
    body = "\n".join(lines)
    # Remove HTML/Markdown comments
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    # Remove code blocks
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    # Remove inline code and markdown links/images, headings
    body = re.sub(r"`[^`]*`", "", body)
    body = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"#+", "", body)
    return len(body.split())


def has_source_include(text: str, source_file: Path | None) -> bool:
    """Return whether a short page includes an existing source file.

    Source-backed examples intentionally keep their prose compact because the
    executable example is the canonical content.  Counting only prose turns
    those pages into false placeholder findings, while a missing include must
    remain visible to the book/link gates.
    """
    if source_file is None:
        return False
    for target in INCLUDE_DIRECTIVE.findall(text):
        include_path = Path(target)
        if not include_path.is_absolute():
            include_path = source_file.parent / include_path
        if include_path.is_file():
            return True
    return False


def is_placeholder(
    text: str, words: int, source_file: Path | None = None
) -> bool:
    if words < 20:
        return not has_source_include(text, source_file)
    # If body is only TODO/placeholder comments, treat as placeholder
    body = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    body = re.sub(r"#.*", "", body)
    if not body.strip():
        return True
    return False


def scan(book_dir: Path):
    results = []
    for md_file in sorted(book_dir.rglob("*.md")):
        if md_file.name in SKIP:
            continue
        text = md_file.read_text(encoding="utf-8")
        words = body_word_count(text)
        if is_placeholder(text, words, md_file):
            rel = md_file.relative_to(book_dir).as_posix()
            results.append((rel, words))
    return results


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"Missing: {path}")
            continue
        print(f"\n# {path}\n")
        placeholders = scan(path)
        print(f"{'file':<60} {'words'}")
        print("-" * 66)
        for rel, words in placeholders:
            print(f"{rel:<60} {words}")
        print(f"\nTotal placeholders: {len(placeholders)}")
