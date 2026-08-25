"""Low-level SVG canvas handling, text formatting, and primitives."""

import html
import textwrap


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
    out = [
        f'<text x="{x}" y="{start_y:.1f}" text-anchor="{anchor}" '
        f'font-family="Arial, sans-serif" font-size="{font_size}" fill="{fill}">'
    ]
    for i, line in enumerate(lines):
        if i == 0:
            out.append(f'  <tspan x="{x}" dy="0">{html.escape(line)}</tspan>')
        else:
            out.append(f'  <tspan x="{x}" dy="{dy:.1f}">{html.escape(line)}</tspan>')
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
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">\n'
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
