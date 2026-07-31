#!/usr/bin/env python3
"""List mdBook .md files that look like placeholder chapters."""

import re
import sys
from pathlib import Path

SKIP = {"SUMMARY.md", "README.md", "BOOK_ORGANIZATION.md"}


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


def is_placeholder(text: str, words: int) -> bool:
    if words < 20:
        return True
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
        if is_placeholder(text, words):
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
