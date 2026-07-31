#!/usr/bin/env python3
"""Smoke tests for the figure generator's domain routing and SVG templates.

The routing tests assert that `choose_domain` maps known chapter titles to the
expected figure template.  The SVG smoke tests ensure every routed (and hub)
template produces a valid `<svg>` output.  Together they guard against routing
regressions and broken figure templates.
"""
from __future__ import annotations

import unittest

import pytest

from generate_book_figures import build_figure_svg, choose_domain
from generate_book_figures.routing import DOMAIN_ROUTING


# (title, expected_domain) -- order-sensitive cases that exercise the
# full routing table and a few ambiguous titles.
ROUTING_CASES: list[tuple[str, str]] = [
    # Hounsfield/CT imaging wins over dose-related "attenuation".
    ("1. Hounsfield Units and Attenuation Maps", "imaging"),
    # Pure imaging keywords.
    ("6. CT Reconstruction with FBP and Iterative Methods", "imaging"),
    # Dose keywords still route to dose when no GPU is present.
    ("5. Energy Deposition and TERMA", "dose"),
    ("Attenuation Map for Dose Calculation", "dose"),
    # GPU is now top priority, so it wins over imaging/dose terms.
    ("GPU Attenuation Map and Forward Projection", "gpu"),
    # Pure GPU keyword.
    ("Hardware Acceleration with Hephaestus", "gpu"),
    # "forward projection" alone routes to imaging (no GPU override).
    ("CT Forward Projection Algorithms", "imaging"),
    # Memory/allocator.
    ("4. Memory and Allocation: Mnemosyne Integration", "memory"),
    # MLC.
    ("13. MLC Models and Leaf Sequencing", "mlc"),
    # Gamma verification.
    ("Gamma Index Verification", "gamma"),
    # Clinical workflow.
    ("Tomotherapy Delivery Workflow", "workflow"),
    # Benchmarks.
    ("Canonical Incompressible Benchmarks", "benchmark"),
    # Optimization.
    ("Multi-Objective Optimization", "optimization"),
    # Pressure-velocity / solver.
    ("Pressure-Velocity Coupling and Time Integration", "solver"),
    # Migration.
    ("Atlas Migration Overview", "migration"),
    # Validation.
    ("Reference Phantoms and Ground Truth", "validation"),
    # Biomedical/microfluidics.
    ("Microfluidics and Millifluidic Networks", "vessel_flow"),
    # Schematic/mesh.
    ("2-D Flows and Schematic Integration", "domain_mesh"),
    # Physics stack.
    ("1. Physics Domain Types and Safety Boundaries", "physics_stack"),
    # Generic fallback.
    ("CFDrs Architecture and Problem Setup", "hub"),
]


# Representative titles used to exercise each routed (and hub) SVG template.
# This list is intentionally separate from ROUTING_CASES so that the SVG smoke
# test is decoupled from routing-case semantics and tests every template once.
SVG_DOMAIN_TITLES: list[tuple[str, str]] = [
    ("gpu", "GPU Attenuation Map and Forward Projection"),
    ("imaging", "1. Hounsfield Units and Attenuation Maps"),
    ("dose", "5. Energy Deposition and TERMA"),
    ("memory", "4. Memory and Allocation: Mnemosyne Integration"),
    ("mlc", "13. MLC Models and Leaf Sequencing"),
    ("gamma", "Gamma Index Verification"),
    ("workflow", "Tomotherapy Delivery Workflow"),
    ("benchmark", "Canonical Incompressible Benchmarks"),
    ("optimization", "Multi-Objective Optimization"),
    ("solver", "Pressure-Velocity Coupling and Time Integration"),
    ("migration", "Atlas Migration Overview"),
    ("validation", "Reference Phantoms and Ground Truth"),
    ("vessel_flow", "Microfluidics and Millifluidic Networks"),
    ("domain_mesh", "2-D Flows and Schematic Integration"),
    ("physics_stack", "1. Physics Domain Types and Safety Boundaries"),
    ("hub", "CFDrs Architecture and Problem Setup"),
]


class RoutingSmokeTestCase(unittest.TestCase):
    """Expected domain for representative chapter titles and SVG coverage."""

    def test_routing_cases(self) -> None:
        for title, expected in ROUTING_CASES:
            with self.subTest(title=title):
                self.assertEqual(
                    choose_domain(title),
                    expected,
                )

    def test_svg_domain_titles_cover_all_routed_domains(self) -> None:
        """SVG_DOMAIN_TITLES must cover every routed domain plus the hub."""
        routed_domains = {domain for domain, _ in DOMAIN_ROUTING}
        expected_domains = routed_domains | {"hub"}
        covered = {domain for domain, _ in SVG_DOMAIN_TITLES}
        self.assertEqual(
            covered,
            expected_domains,
            "SVG_DOMAIN_TITLES must contain one case per routed domain plus hub",
        )


@pytest.mark.slow
@pytest.mark.parametrize("_domain, title", SVG_DOMAIN_TITLES)
def test_build_figure_svg_returns_svg(_domain: str, title: str) -> None:
    """Each routed domain must produce a non-empty SVG string."""
    svg = build_figure_svg(
        title=title,
        keywords=[],
        kind="chapter",
        caption="Smoke-test caption.",
    )
    assert isinstance(svg, str)
    assert svg.startswith("<svg"), "figure must start with <svg tag"


if __name__ == "__main__":
    # Run under pytest so the parametrized SVG smoke tests execute too.
    pytest.main([__file__])
