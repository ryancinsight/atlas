#!/usr/bin/env python3
"""Generate conceptual SVG figure assets for an mdBook and embed them.

Mirrors the kwavers pattern of keeping figures under docs/book/figures/chXX/
and referencing them with markdown image syntax. Each generated figure now
includes a caption (e.g. ``Figure 1.2 — Title'') and wraps long SVG text so
it stays within the artboard.

Usage:
    python scripts/generate_book_figures.py <book_dir> [--dry-run] [--force]
"""

import argparse
import html as html_mod
import os
import re
import textwrap
from pathlib import Path

STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those", "chapter",
    "example", "part", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "overview", "introduction", "reference",
}

SKIP_FILES = {"SUMMARY.md", "README.md", "BOOK_ORGANIZATION.md"}

# Map domain keywords to the template that should be used for chapter pages.
# Order matters: earlier entries take precedence.
DOMAIN_ROUTING: list[tuple[str, list[str]]] = [
    ("imaging", ["imaging", "ct", "radon", "fbp", "mvct", "hounsfield"]),
    ("dose", ["dose", "terma", "convolution", "spectra", "hardening", "energy deposition", "attenuation"]),
    ("gpu", ["gpu", "hardware", "acceleration", "hephaestus", "coeus"]),
    ("migration", ["migration", "eunomia", "leto", "mnemosyne", "atlas", "themis"]),
    ("validation", ["validation", "benchmark", "clinical", "phantom", "regression"]),
    ("vessel_flow", ["biomedical", "blood", "vascular", "microfluidic", "cavitation", "turbulence"]),
    ("domain_mesh", ["geometry", "voxel", "meshing", "spatial", "grids", "schematic", "csg"]),
    ("physics_stack", ["foundations", "governing", "equations", "numerics", "solvers", "physics"]),
]


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


def keywords_from_title(title: str, count: int = 6) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", title)
    filtered = [w for w in words if w.lower() not in STOP_WORDS and len(w) > 1]
    seen: set[str] = set()
    out: list[str] = []
    for w in filtered:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:count]


def wrap_text(text: str, max_width: int, font_size: int) -> list[str]:
    """Wrap arbitrary text to a pixel width using a simple character estimate."""
    avg_char_width = font_size * 0.58
    max_chars = max(1, int(max_width / avg_char_width))
    return textwrap.wrap(text, width=max_chars)


def render_wrapped_text(
    x: int,
    y: int,
    lines: list[str],
    anchor: str,
    font_size: int,
    fill: str,
    line_height: float = 1.25,
) -> str:
    """Render a block of wrapped SVG text centered vertically around (x, y)."""
    if not lines:
        lines = ["..."]
    dy = font_size * line_height
    total_height = (len(lines) - 1) * dy
    start_y = y - total_height / 2 + font_size / 4
    out = [f'<text x="{x}" y="{start_y:.1f}" text-anchor="{anchor}" font-family="Arial, sans-serif" font-size="{font_size}" fill="{fill}">']
    for i, line in enumerate(lines):
        if i == 0:
            out.append(f'  <tspan x="{x}" dy="0">{html_mod.escape(line)}</tspan>')
        else:
            out.append(f'  <tspan x="{x}" dy="{dy:.1f}">{html_mod.escape(line)}</tspan>')
    out.append("</text>")
    return "\n".join(out)


def _arrow_marker() -> str:
    return '''  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6 Z" fill="#64748b"/>
    </marker>
  </defs>
'''


def _svg_canvas(title: str) -> tuple[str, str]:
    """Return the opening SVG tag (with aria-label) and background rect."""
    width, height = 800, 340
    header = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{html_mod.escape(title)}">\n'
        f'  <rect width="{width}" height="{height}" fill="#f8fafc"/>\n'
    )
    return header, "</svg>\n"


def _render_title(title: str) -> str:
    title_lines = wrap_text(title, 760, 20)
    title_y = 25 + len(title_lines) * 10
    return render_wrapped_text(400, title_y, title_lines, "middle", 20, "#111827")


def _render_caption(caption: str) -> str:
    caption_lines = wrap_text(caption, 760, 14)
    caption_y = 300 + len(caption_lines) * 7
    return render_wrapped_text(400, min(caption_y, 325), caption_lines, "middle", 14, "#374151")


def build_pipeline_svg(title: str, keywords: list[str], caption: str) -> str:
    """Generate a horizontal pipeline-style SVG for example pages."""
    width, height = 800, 340
    fill, stroke = "#dcfce7", "#16a34a"

    # Build a short list of pipeline stages from keywords, falling back to generic labels.
    stages = list(dict.fromkeys(keywords))[:4]
    generic = ["Input", "Process", "Output", "Results"]
    seen_lower = {s.lower() for s in stages}
    for g in generic:
        if len(stages) >= 4:
            break
        if g.lower() not in seen_lower:
            seen_lower.add(g.lower())
            stages.append(g)
    stages = stages[:4]
    n = len(stages)

    # Compute stage box geometry so the pipeline is centered.
    box_w = 140
    spacing = 40
    total_w = n * box_w + (n - 1) * spacing
    start_x = (width - total_w) / 2
    y = 150

    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Arrows between stages
    for i in range(n - 1):
        x1 = start_x + (i + 1) * box_w + i * spacing - 2
        x2 = start_x + (i + 1) * (box_w + spacing) + 2
        svg += f'  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    # Stage boxes and labels
    for i, stage in enumerate(stages):
        cx = start_x + i * (box_w + spacing) + box_w / 2
        svg += f'  <rect x="{cx - box_w / 2}" y="{y - 35}" width="{box_w}" height="70" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        label_lines = wrap_text(str(stage), box_w - 16, 14)
        svg += render_wrapped_text(int(cx), y, label_lines, "middle", 14, "#1f2937") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_physics_stack_svg(title: str, keywords: list[str], caption: str) -> str:
    """Layered physics-to-solver stack diagram."""
    width, _height = 800, 340
    labels = ["Continuous PDEs", "Discretization", "Solver"]
    box_w, box_h = 260, 56
    x = (width - box_w) / 2
    y_positions = [120, 180, 240]

    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    for i, (y, label) in enumerate(zip(y_positions, labels)):
        fill = ["#dbeafe", "#bfdbfe", "#93c5fd"][i]
        stroke = "#2563eb"
        svg += f'  <rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        label_lines = wrap_text(str(label), box_w - 20, 14)
        svg += render_wrapped_text(400, y + box_h / 2, label_lines, "middle", 14, "#1e3a8a") + "\n"
        if i < len(y_positions) - 1:
            svg += f'  <line x1="{400}" y1="{y + box_h + 4}" x2="{400}" y2="{y_positions[i + 1] - 4}" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_domain_mesh_svg(title: str, keywords: list[str], caption: str) -> str:
    """Voxel/mesh grid with a few highlighted cells."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Draw a 5x3 grid of cells centered in the canvas.
    cols, rows = 5, 3
    cell = 44
    total_w = cols * cell
    total_h = rows * cell
    start_x = (800 - total_w) / 2
    start_y = 130

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * cell
            y = start_y + r * cell
            fill = "#e2e8f0"
            stroke = "#94a3b8"
            # Highlight a simple pattern
            if (r + c) % 3 == 0:
                fill = "#dbeafe"
                stroke = "#2563eb"
            svg += f'  <rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>\n'

    # Axis labels
    svg += f'  <text x="{start_x - 10}" y="{start_y + total_h / 2}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">j</text>\n'
    svg += f'  <text x="{start_x + total_w / 2}" y="{start_y + total_h + 18}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#64748b">i</text>\n'

    svg += _render_caption(caption) + "\n"
    svg += svg_footer
    return svg


def build_imaging_svg(title: str, keywords: list[str], caption: str) -> str:
    """CT/Radon imaging pipeline: source -> object -> detector -> image."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    stages = ["Source", "Object", "Detector", "Image"]
    box_w, box_h = 120, 50
    total_w = len(stages) * box_w + (len(stages) - 1) * 40
    start_x = (800 - total_w) / 2
    y = 150

    for i, stage in enumerate(stages):
        x = start_x + i * (box_w + 40)
        fill = "#fef3c7" if i == 0 else "#dbeafe"
        stroke = "#d97706" if i == 0 else "#2563eb"
        svg += f'  <rect x="{x}" y="{y - box_h / 2}" width="{box_w}" height="{box_h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        svg += render_wrapped_text(int(x + box_w / 2), y, [stage], "middle", 14, "#1f2937") + "\n"
        if i < len(stages) - 1:
            x1 = x + box_w + 2
            x2 = x + box_w + 38
            svg += f'  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_dose_svg(title: str, keywords: list[str], caption: str) -> str:
    """Dose deposition cascade: beams through layers."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    layers = ["Beam", "TERMA", "Dose"]
    y_positions = [115, 165, 215]
    for i, (y, label) in enumerate(zip(y_positions, layers)):
        fill = ["#fee2e2", "#fecaca", "#fca5a5"][i]
        stroke = "#dc2626"
        svg += f'  <rect x="250" y="{y}" width="300" height="40" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1"/>\n'
        svg += render_wrapped_text(400, y + 20, [label], "middle", 14, "#7f1d1d") + "\n"

    # Vertical arrows through layers
    for x in [320, 400, 480]:
        svg += f'  <line x1="{x}" y1="110" x2="{x}" y2="250" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="4"/>\n'

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_gpu_svg(title: str, keywords: list[str], caption: str) -> str:
    """Host CPU sending work to GPU compute cores."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Host
    svg += f'  <rect x="80" y="130" width="120" height="80" rx="6" fill="#e0e7ff" stroke="#4f46e5" stroke-width="2"/>\n'
    svg += render_wrapped_text(140, 170, ["Host CPU"], "middle", 14, "#1e1b4b") + "\n"

    # Arrow to GPU grid
    svg += f'  <line x1="202" y1="170" x2="278" y2="170" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    # GPU cores
    core_w, core_h, gap = 70, 50, 15
    core_idx = 0
    for row in range(2):
        for col in range(4):
            x = 290 + col * (core_w + gap)
            y = 125 + row * (core_h + gap)
            svg += f'  <rect x="{x}" y="{y}" width="{core_w}" height="{core_h}" rx="4" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>\n'
            core_idx += 1
            svg += render_wrapped_text(x + core_w / 2, y + core_h / 2, [f"C{core_idx}"], "middle", 10, "#1e3a8a") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_vessel_flow_svg(title: str, keywords: list[str], caption: str) -> str:
    """Bifurcating vessel/channel with flow direction."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Main channel path using a thick stroke.
    svg += (
        '  <path d="M 120,170 Q 220,170 260,150 T 400,130" fill="none" '
        'stroke="#3b82f6" stroke-width="14" stroke-linecap="round" opacity="0.6"/>\n'
    )
    svg += (
        '  <path d="M 260,150 Q 300,190 400,210" fill="none" '
        'stroke="#3b82f6" stroke-width="10" stroke-linecap="round" opacity="0.6"/>\n'
    )

    # Flow arrow along main branch
    svg += f'  <line x1="190" y1="165" x2="230" y2="158" stroke="#1e3a8a" stroke-width="2" marker-end="url(#arrowhead)"/>\n'
    svg += f'  <line x1="300" y1="185" x2="340" y2="205" stroke="#1e3a8a" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    # Labels
    svg += render_wrapped_text(160, 200, ["Inlet"], "middle", 12, "#1e3a8a") + "\n"
    svg += render_wrapped_text(430, 130, ["Branch A"], "middle", 12, "#1e3a8a") + "\n"
    svg += render_wrapped_text(430, 220, ["Branch B"], "middle", 12, "#1e3a8a") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_validation_svg(title: str, keywords: list[str], caption: str) -> str:
    """Simple benchmark chart: analytical vs simulated."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Axes
    svg += '  <line x1="80" y1="250" x2="720" y2="250" stroke="#111827" stroke-width="2"/>\n'
    svg += '  <line x1="80" y1="250" x2="80" y2="100" stroke="#111827" stroke-width="2"/>\n'

    # Analytical line
    svg += '  <polyline points="120,200 250,180 400,160 550,140 680,120" fill="none" stroke="#2563eb" stroke-width="3"/>\n'

    # Simulated scatter points
    points = [(140, 205), (270, 185), (420, 155), (570, 145), (690, 118)]
    for x, y in points:
        svg += f'  <circle cx="{x}" cy="{y}" r="5" fill="#dc2626"/>\n'

    # Legend
    svg += '  <line x1="520" y1="90" x2="560" y2="90" stroke="#2563eb" stroke-width="3"/>\n'
    svg += render_wrapped_text(600, 90, ["Analytical"], "middle", 12, "#111827") + "\n"
    svg += '  <circle cx="540" cy="110" r="5" fill="#dc2626"/>\n'
    svg += render_wrapped_text(600, 110, ["Simulated"], "middle", 12, "#111827") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += svg_footer
    return svg


def build_migration_svg(title: str, keywords: list[str], caption: str) -> str:
    """Legacy monolith transitioning to Atlas stack modules."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Legacy box
    svg += f'  <rect x="80" y="140" width="160" height="80" rx="6" fill="#fee2e2" stroke="#dc2626" stroke-width="2"/>\n'
    svg += render_wrapped_text(160, 180, ["Legacy"], "middle", 14, "#7f1d1d") + "\n"

    # Arrow
    svg += f'  <line x1="244" y1="180" x2="316" y2="180" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    # Atlas stack modules
    modules = [
        ("Numeric", "#dbeafe", "#2563eb"),
        ("Array", "#dcfce7", "#16a34a"),
        ("Memory", "#fef3c7", "#d97706"),
        ("GPU", "#f3e8ff", "#7e22ce"),
    ]
    box_w, box_h = 100, 50
    start_x = 340
    for i, (label, fill, stroke) in enumerate(modules):
        x = start_x + i * (box_w + 10)
        y = 130 if i % 2 == 0 else 190
        svg += f'  <rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        svg += render_wrapped_text(x + box_w / 2, y + box_h / 2, [label], "middle", 12, "#111827") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_hub_svg(title: str, keywords: list[str], kind: str, caption: str) -> str:
    width, height = 800, 340
    fill, stroke = _colors_for_kind(kind)

    # Central label uses the first few keywords/title fragment
    center_text = " ".join(keywords[:3]) or title
    if len(center_text) > 28:
        center_text = center_text[:25] + "…"

    satellite_labels = keywords[3:7] if len(keywords) >= 7 else keywords[:4]
    while len(satellite_labels) < 3:
        satellite_labels.append("...")
    satellite_labels = satellite_labels[:4]

    positions = [(180, 80), (180, 240), (620, 80), (620, 240)]

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html_mod.escape(title)}">\n'
    svg += f'  <rect width="{width}" height="{height}" fill="#f8fafc"/>\n'
    svg += _render_title(title) + "\n"

    # Arrows behind boxes
    for px, py in positions[: len(satellite_labels)]:
        svg += f'  <line x1="400" y1="160" x2="{px}" y2="{py}" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    # Satellite boxes with wrapped labels
    for (px, py), label in zip(positions[: len(satellite_labels)], satellite_labels):
        svg += f'  <rect x="{px - 80}" y="{py - 25}" width="160" height="50" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        sat_lines = wrap_text(str(label), 150, 14)
        # Estimate line height to keep text inside the 50 px box
        sat_line_height = 1.2
        block_h = len(sat_lines) * 14 * sat_line_height
        start_y = py - block_h / 2 + 14 / 2
        for i, line in enumerate(sat_lines):
            y_off = start_y + i * 14 * sat_line_height
            svg += f'  <text x="{px}" y="{y_off:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#1f2937">{html_mod.escape(line)}</text>\n'

    # Central box with wrapped text
    svg += f'  <rect x="320" y="130" width="160" height="60" rx="8" fill="#ffffff" stroke="{stroke}" stroke-width="3"/>\n'
    center_lines = wrap_text(center_text, 140, 14)
    svg += render_wrapped_text(400, 160, center_lines, "middle", 14, "#111827") + "\n"

    svg += _render_caption(caption) + "\n"

    svg += _arrow_marker()
    svg += "</svg>\n"
    return svg


def _colors_for_kind(kind: str) -> tuple[str, str]:
    if kind == "example":
        return "#dcfce7", "#16a34a"
    if kind == "appendix":
        return "#fef3c7", "#d97706"
    if kind == "migration":
        return "#f3e8ff", "#7e22ce"
    return "#dbeafe", "#2563eb"


def choose_domain(title: str) -> str:
    t = title.lower()
    for domain, keywords in DOMAIN_ROUTING:
        if any(k in t for k in keywords):
            return domain
    return "hub"


def build_figure_svg(
    title: str,
    keywords: list[str],
    kind: str,
    caption: str,
) -> str:
    """Dispatch to the appropriate figure template."""
    if kind == "example":
        return build_pipeline_svg(title, keywords, caption)

    domain = choose_domain(title)
    if domain == "imaging":
        return build_imaging_svg(title, keywords, caption)
    if domain == "dose":
        return build_dose_svg(title, keywords, caption)
    if domain == "gpu":
        return build_gpu_svg(title, keywords, caption)
    if domain == "migration":
        return build_migration_svg(title, keywords, caption)
    if domain == "validation":
        return build_validation_svg(title, keywords, caption)
    if domain == "vessel_flow":
        return build_vessel_flow_svg(title, keywords, caption)
    if domain == "domain_mesh":
        return build_domain_mesh_svg(title, keywords, caption)
    if domain == "physics_stack":
        return build_physics_stack_svg(title, keywords, caption)
    return build_hub_svg(title, keywords, kind, caption)


def process_book(book_dir: Path, dry_run: bool = False, force: bool = False):
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
        caption = f"Figure {fig_label} — {title}"

        # Stricter detection: an exact markdown image reference produced by this script.
        figure_img_re = re.compile(
            r"!\[Figure [^\]]+\]\(" + re.escape(rel_svg) + r"\)"
        )
        has_figure = bool(figure_img_re.search(md_text))
        if not force and has_figure:
            print(f"  skip (already has figure): {rel_path}")
            continue

        if has_figure:
            # Remove previously inserted figure block so we can regenerate it.
            md_text = re.sub(
                r"\n<!-- generated-figure-start -->.*?<!-- generated-figure-end -->\n",
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

        figure_md = f"\n<!-- generated-figure-start -->\n![{caption}]({rel_svg})\n*{caption}*\n<!-- generated-figure-end -->\n"
        new_lines = lines[: insert_after + 1] + [figure_md] + lines[insert_after + 1 :]
        # Preserve trailing newline behaviour
        if md_text.endswith("\n"):
            new_lines.append("")
        if not dry_run:
            md_file.write_text("\n".join(new_lines), encoding="utf-8")
            generated += 1
            updated += 1
        else:
            print(f"  would generate {rel_svg} for {rel_path}")

    if dry_run:
        print(f"{book_dir}: dry-run complete")
    else:
        print(f"{book_dir}: generated {generated} figures and wired into {updated} pages")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate mdBook figure assets")
    parser.add_argument("book_dir", type=Path, help="Path to docs/book directory")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be generated without writing files")
    parser.add_argument("--force", action="store_true", help="Regenerate figures even if pages already contain them")
    args = parser.parse_args()
    process_book(args.book_dir, dry_run=args.dry_run, force=args.force)
