"""High-level mdBook interaction, parsing, file I/O, and orchestration."""

import os
import re
from pathlib import Path

from generate_book_figures.routing import build_figure_svg, keywords_from_title

SKIP_FILES = {"SUMMARY.md", "README.md", "BOOK_ORGANIZATION.md"}


def slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", title.lower()).strip("_")
    return s[:60]


def extract_chapter_label(title: str) -> str | None:
    t = title.strip()
    if m := re.match(r"(\d+)\.", t):
        return m.group(1)
    if m := re.match(r"([A-Z])\.", t):
        return m.group(1)
    return None


def parse_summary(summary_path: Path) -> list[tuple[str | None, str, str, int]]:
    text = summary_path.read_text(encoding="utf-8")
    links = []
    current_label: dict[int, str | None] = {0: None}
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("-"):
            continue
        indent = (len(line) - len(stripped)) // 2
        m = re.search(r"\[([^\]]+)\]\(([^)]+)\)", stripped)
        if not m:
            continue
        title = m.group(1).strip()
        path = m.group(2).strip()
        label = extract_chapter_label(title)
        if indent == 0:
            current_label[0] = label
        parent = current_label.get(0)
        links.append((parent, title, path, indent))
    return links


def page_type(path: str, _indent: int) -> str:
    p = path.replace("\\", "/")
    if "examples/" in p:
        return "example"
    if p.startswith("appendix_") or p.startswith("migration_"):
        if p.startswith("appendix_"):
            return "appendix"
        return "migration"
    return "chapter"


def process_book(book_dir: Path, dry_run: bool = False, force: bool = False) -> None:
    summary = book_dir / "SUMMARY.md"
    if not summary.exists():
        print(f"No SUMMARY.md in {book_dir}")
        return

    links = parse_summary(summary)
    counters: dict[str, int] = {}
    generated = 0
    updated = 0

    for label, title, rel_path, indent in links:
        if not rel_path.endswith(".md"):
            continue
        if Path(rel_path).name in SKIP_FILES:
            continue

        md_file = book_dir / rel_path
        if not md_file.exists():
            continue

        kind = page_type(rel_path, indent)

        # Determine figure directory
        if label is None:
            ch_dir = book_dir / "figures" / "misc"
        elif label.isdigit():
            ch_dir = book_dir / "figures" / f"ch{int(label):02d}"
        else:
            ch_dir = book_dir / "figures" / "appendix"

        if not dry_run:
            ch_dir.mkdir(parents=True, exist_ok=True)

        key = str(ch_dir.relative_to(book_dir))
        counters[key] = counters.get(key, 0) + 1
        idx = counters[key]

        slug = slugify(title)
        svg_name = f"fig{idx:02d}_{slug}.svg"
        svg_path = ch_dir / svg_name
        rel_svg = os.path.relpath(svg_path, md_file.parent).replace(os.sep, "/")

        md_text = md_file.read_text(encoding="utf-8")

        fig_label = f"{label}.{idx}" if label else str(idx)
        # The figure label already carries the chapter number; drop a leading
        # "NN." from the title so captions do not read "Figure 18.1 — 18. …".
        caption_title = re.sub(r"^\d+\.\s*", "", title)
        caption = f"Figure {fig_label} — {caption_title}"

        # Marker-based detection: the comment fences delimit generated content,
        # so a retitled chapter (different SVG path) is still recognized and
        # replaced instead of accumulating a second block.
        has_figure = "<!-- generated-figure-start -->" in md_text
        if not force and has_figure:
            print(f"  skip (already has figure): {rel_path}")
            continue

        if has_figure:
            # Remove previously inserted figure blocks so we can regenerate,
            # consuming the surrounding blank run so repeated regeneration is a
            # fixed point rather than a blank-line leak.
            md_text = re.sub(
                r"\n*<!-- generated-figure-start -->.*?<!-- generated-figure-end -->\n*",
                "\n",
                md_text,
                flags=re.DOTALL,
            )

        keywords = keywords_from_title(title)
        svg = build_figure_svg(title, keywords, kind, caption)
        if not dry_run:
            svg_path.write_text(svg, encoding="utf-8")

        lines = md_text.splitlines()
        heading_idx = next(
            (i for i, line in enumerate(lines) if line.startswith("#")),
            -1,
        )
        insert_after = heading_idx if heading_idx != -1 else 0

        # Collapse any blank run at the insertion point (including runs leaked
        # by earlier generator versions) so the block always sits between
        # exactly one blank line on each side.
        content_start = insert_after + 1
        while content_start < len(lines) and not lines[content_start].strip():
            del lines[content_start]

        figure_md = (
            "\n<!-- generated-figure-start -->\n"
            f"![{caption}]({rel_svg})\n"
            f"*{caption}*\n"
            "<!-- generated-figure-end -->\n"
        )
        new_lines = lines[:content_start] + [figure_md] + lines[content_start:]
        new_text = "\n".join(new_lines).rstrip("\n") + "\n"
        if not dry_run:
            md_file.write_text(new_text, encoding="utf-8")
            generated += 1
            updated += 1
        else:
            print(f"  would generate {rel_svg} for {rel_path}")

    if dry_run:
        print(f"{book_dir}: dry-run complete")
    else:
        print(f"{book_dir}: generated {generated} figures and wired into {updated} pages")
