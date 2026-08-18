#!/usr/bin/env python3
"""Populate empty mdBook chapter/example .md files with short intros."""

import os
import re
import sys
from pathlib import Path


def extract_links(summary_text: str):
    """Return a dict mapping relative md path -> link title."""
    links = {}
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", summary_text):
        title = match.group(1).strip()
        path = match.group(2).strip()
        if path.endswith(".md") and path not in links:
            links[path] = title
    return links


def title_from_filename(filename: str) -> str:
    """Convert a filename like 'foo_bar_baz.md' -> 'Foo Bar Baz'."""
    name = Path(filename).stem
    return " ".join(word.capitalize() for word in name.split("_"))


def generate_content(title: str, rel_path: str, repo: str) -> str:
    rel = rel_path.replace("\\", "/")
    if title.lower().startswith("example:"):
        topic = re.sub(r"^Example:\s*", "", title, flags=re.IGNORECASE)
        return f"""# {title}

This example demonstrates **{topic}** in the {repo} pipeline.

It walks through the key setup steps, shows how the Atlas stack primitives are
composed, and points out validation checks you can use to verify the result.

<!-- TODO: add runnable source, expected output, and diagrams -->
"""
    if "migration" in rel.lower():
        return f"""# {title}

This chapter tracks the Atlas stack migration for **{title}**. It explains the
mapping from legacy crates (nalgebra/ndarray/burn) to Atlas primitives, calls
out zero-cost abstraction patterns, and highlights parity validation
checkpoints.

<!-- TODO: expand with before/after code snippets and parity notes -->
"""
    if "appendix" in rel.lower():
        return f"""# {title}

This appendix provides supplementary reference material for **{title}**. It is
designed to be consulted alongside the main chapters rather than read linearly.

<!-- TODO: fill in tables, glossary entries, or API links -->
"""
    return f"""# {title}

This chapter introduces **{title}**. It covers the core concepts, design choices,
and how they fit into the broader {repo} architecture.

<!-- TODO: expand with runnable examples and diagrams -->
"""


def process_book(root: Path):
    repo = root.parent.parent.name.capitalize()
    summary = root / "SUMMARY.md"
    if not summary.exists():
        print(f"No SUMMARY.md in {root}")
        return

    links = extract_links(summary.read_text(encoding="utf-8"))
    skipped = {"SUMMARY.md", "README.md", "BOOK_ORGANIZATION.md"}

    updated = 0
    for md_file in root.rglob("*.md"):
        if md_file.name in skipped:
            continue
        rel = md_file.relative_to(root).as_posix()
        if md_file.stat().st_size == 0:
            title = links.get(rel) or title_from_filename(md_file.name)
            content = generate_content(title, rel, repo)
            md_file.write_text(content, encoding="utf-8")
            updated += 1
            print(f"  wrote {rel}")

    print(f"{root}: populated {updated} empty markdown files")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.exists():
            process_book(path)
        else:
            print(f"Path does not exist: {path}")
