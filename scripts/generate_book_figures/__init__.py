"""Generate conceptual SVG figure assets for an mdBook."""

from generate_book_figures.core import process_book
from generate_book_figures.routing import build_figure_svg, choose_domain

__all__ = ["process_book", "build_figure_svg", "choose_domain"]
