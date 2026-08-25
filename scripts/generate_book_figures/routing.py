"""Heuristics to analyze titles and dispatch to the correct figure template."""

import re

from generate_book_figures.templates import (
    build_domain_mesh_svg,
    build_dose_svg,
    build_gamma_svg,
    build_gpu_svg,
    build_hub_svg,
    build_imaging_svg,
    build_memory_svg,
    build_migration_svg,
    build_mlc_svg,
    build_physics_stack_svg,
    build_pipeline_svg,
    build_solver_svg,
    build_vessel_flow_svg,
    build_workflow_svg,
)

STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those", "chapter",
    "example", "part", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "overview", "introduction", "reference",
}

# Map domain keywords to the template that should be used for chapter pages.
# Order matters: earlier entries take precedence.
DOMAIN_ROUTING: list[tuple[str, list[str]]] = [
    # GPU hardware/compute should win whenever the title explicitly calls it out,
    # even if the underlying physics term (e.g. "attenuation") would otherwise
    # route elsewhere.
    ("gpu", ["gpu", "hardware", "acceleration", "hephaestus", "coeus"]),
    ("imaging", ["imaging", "ct", "radon", "fbp", "mvct", "hounsfield", "back projection", "filtered back projection", "forward projection"]),
    ("dose", ["dose", "terma", "convolution", "spectra", "hardening", "energy deposition", "attenuation"]),
    ("memory", ["memory", "allocation", "mnemosyne", "themis"]),
    ("mlc", ["mlc", "leaf", "sequencing"]),
    ("gamma", ["gamma", "verification"]),
    ("workflow", ["workflow", "delivery", "tomo", "linac", "adaptive", "clinical workflow"]),
    ("solver", ["pressure", "velocity", "coupling", "time integration", "simple", "pimple", "krylov"]),
    ("migration", ["migration", "eunomia", "leto", "atlas", "hermes", "moirai", "apollo", "ritk"]),
    ("vessel_flow", ["biomedical", "blood", "vascular", "microfluidic", "microfluidics", "cavitation", "turbulence"]),
    ("domain_mesh", ["geometry", "voxel", "meshing", "spatial", "grids", "schematic", "schematics", "csg"]),
    ("physics_stack", ["foundations", "governing", "equations", "numerics", "numeric", "solvers", "physics", "spectral"]),
]


def _keyword_variants(k: str) -> set[str]:
    """Return a small set of likely forms for a single-word keyword (singular/plural)."""
    variants: set[str] = {k}
    if len(k) <= 3:
        return variants
    # If the keyword already ends in a trailing 's', assume it is plural and add the singular.
    if k.endswith("s") and not k.endswith("ss"):
        variants.add(k[:-1])
    else:
        # Otherwise generate regular plural forms.
        variants.add(k + "s")
        if k.endswith("y"):
            variants.add(k[:-1] + "ies")
    return variants


def choose_domain(title: str) -> str:
    """Pick the most appropriate domain template for a chapter title."""
    t = title.lower()
    # Use a word set for single-word keywords to avoid accidental substring matches.
    words = set(re.findall(r"[a-z0-9]+", t))
    for domain, keywords in DOMAIN_ROUTING:
        for k in keywords:
            if " " in k:
                # Multi-word keyword: match the phrase as-is.
                if k in t:
                    return domain
            elif any(var in words for var in _keyword_variants(k)):
                return domain
    return "hub"


def keywords_from_title(title: str, count: int = 6) -> list[str]:
    """Extract interesting keywords from a title for the generic hub template."""
    words = re.findall(r"[A-Za-z0-9]+", title)
    filtered = [w for w in words if w.lower() not in STOP_WORDS and len(w) > 1]
    seen: set[str] = set()
    out: list[str] = []
    for w in filtered:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:count]


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
    if domain == "vessel_flow":
        return build_vessel_flow_svg(title, keywords, caption)
    if domain == "domain_mesh":
        return build_domain_mesh_svg(title, keywords, caption)
    if domain == "physics_stack":
        return build_physics_stack_svg(title, keywords, caption)
    if domain == "memory":
        return build_memory_svg(title, keywords, caption)
    if domain == "mlc":
        return build_mlc_svg(title, keywords, caption)
    if domain == "gamma":
        return build_gamma_svg(title, keywords, caption)
    if domain == "workflow":
        return build_workflow_svg(title, keywords, caption)
    if domain == "solver":
        return build_solver_svg(title, keywords, caption)
    return build_hub_svg(title, keywords, kind, caption)
