"""Individual figure SVG template builders."""

import html

from generate_book_figures.svg import (
    _arrow_marker,
    _render_caption,
    _render_title,
    _svg_canvas,
    render_wrapped_text,
    wrap_text,
)


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

    # Stage box and labels
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
    """Layered physics-to-solver stack diagram with domain-aware labels."""
    width, _height = 800, 340

    title_lower = title.lower()
    if "governing" in title_lower or "equations" in title_lower:
        labels = ["Governing PDEs", "Discretization", "Solver"]
    elif "numeric" in title_lower or "scalar" in title_lower:
        labels = ["Scalar Fields", "Vector/Tensor Ops", "Abstractions"]
    elif "foundation" in title_lower:
        labels = ["Physical Model", "Mathematical Form", "Numerical Form"]
    else:
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


def build_memory_svg(title: str, keywords: list[str], caption: str) -> str:
    """Memory allocator layout with stack/heap/pool/device regions."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    blocks = [
        ("Stack", "#dbeafe", "#2563eb"),
        ("Heap", "#dcfce7", "#16a34a"),
        ("Pool", "#fef3c7", "#d97706"),
        ("Device", "#f3e8ff", "#7e22ce"),
    ]
    box_w, box_h = 130, 70
    spacing = 25
    total_w = len(blocks) * box_w + (len(blocks) - 1) * spacing
    start_x = (800 - total_w) / 2
    y = 150

    for i, (label, fill, stroke) in enumerate(blocks):
        x = start_x + i * (box_w + spacing)
        svg += f'  <rect x="{x}" y="{y - box_h / 2}" width="{box_w}" height="{box_h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        svg += render_wrapped_text(int(x + box_w / 2), y, [label], "middle", 14, "#1f2937") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += svg_footer
    return svg


def build_mlc_svg(title: str, keywords: list[str], caption: str) -> str:
    """Multi-leaf collimator: two banks of leaves with a beam aperture."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Beam arrow from left
    svg += f'  <line x1="60" y1="170" x2="220" y2="170" stroke="#f59e0b" stroke-width="3" marker-end="url(#arrowhead)"/>\n'

    leaf_w, leaf_h = 80, 18
    gap = 6
    # Top leaves descending from center
    for i in range(4):
        y = 90 + i * (leaf_h + gap)
        svg += f'  <rect x="240" y="{y}" width="{leaf_w}" height="{leaf_h}" rx="3" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>\n'
        svg += f'  <rect x="{560 - leaf_w}" y="{y}" width="{leaf_w}" height="{leaf_h}" rx="3" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>\n'

    # Bottom leaves ascending from center
    for i in range(4):
        y = 220 + i * (leaf_h + gap)
        svg += f'  <rect x="240" y="{y}" width="{leaf_w}" height="{leaf_h}" rx="3" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>\n'
        svg += f'  <rect x="{560 - leaf_w}" y="{y}" width="{leaf_w}" height="{leaf_h}" rx="3" fill="#3b82f6" stroke="#1e40af" stroke-width="1"/>\n'

    # Aperture highlight rectangle in the middle (vertical transparent band)
    svg += f'  <rect x="260" y="80" width="280" height="200" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4"/>\n'
    svg += render_wrapped_text(600, 170, ["Aperture"], "middle", 12, "#d97706") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_workflow_svg(title: str, keywords: list[str], caption: str) -> str:
    """Clinical workflow pipeline."""
    stages = ["Plan", "Image", "Treat", "Verify"]
    width, _height = 800, 340
    box_w, box_h = 140, 70
    spacing = 40
    total_w = len(stages) * box_w + (len(stages) - 1) * spacing
    start_x = (width - total_w) / 2
    y = 150

    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    for i, stage in enumerate(stages):
        x = start_x + i * (box_w + spacing)
        fill = ["#dbeafe", "#dcfce7", "#fef3c7", "#f3e8ff"][i]
        stroke = ["#2563eb", "#16a34a", "#d97706", "#7e22ce"][i]
        svg += f'  <rect x="{x}" y="{y - box_h / 2}" width="{box_w}" height="{box_h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        svg += render_wrapped_text(int(x + box_w / 2), y, [stage], "middle", 14, "#1f2937") + "\n"
        if i < len(stages) - 1:
            x1 = x + box_w + 2
            x2 = x + box_w + spacing - 2
            svg += f'  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    svg += _render_caption(caption) + "\n"
    svg += _arrow_marker()
    svg += svg_footer
    return svg


def build_gamma_svg(title: str, keywords: list[str], caption: str) -> str:
    """Gamma index: reference cross, evaluated point, and tolerance circle."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Tolerance circle
    svg += '  <circle cx="400" cy="170" r="70" fill="none" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4"/>\n'
    # Reference cross
    svg += '  <line x1="360" y1="130" x2="440" y2="210" stroke="#2563eb" stroke-width="3"/>\n'
    svg += '  <line x1="440" y1="130" x2="360" y2="210" stroke="#2563eb" stroke-width="3"/>\n'
    # Evaluated point offset
    svg += '  <circle cx="420" cy="155" r="6" fill="#dc2626"/>\n'
    # Labels
    svg += render_wrapped_text(400, 95, ["Tolerance"], "middle", 12, "#64748b") + "\n"
    svg += render_wrapped_text(400, 245, ["Reference"], "middle", 12, "#2563eb") + "\n"
    svg += render_wrapped_text(460, 155, ["Evaluated"], "middle", 12, "#dc2626") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += svg_footer
    return svg


def build_benchmark_svg(title: str, keywords: list[str], caption: str) -> str:
    """Benchmark comparison bars for reference vs computed results."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Axes
    svg += '  <line x1="80" y1="250" x2="720" y2="250" stroke="#111827" stroke-width="2"/>\n'
    svg += '  <line x1="80" y1="250" x2="80" y2="100" stroke="#111827" stroke-width="2"/>\n'

    bar_w = 35
    group_gap = 120
    base_y = 250
    data = [
        ("Lid-Driven Cavity", 180, 175),
        ("Pipe Flow", 220, 215),
        ("Poiseuille", 150, 145),
    ]
    x = 120
    for name, ref_h, comp_h in data:
        svg += f'  <rect x="{x}" y="{base_y - ref_h}" width="{bar_w}" height="{ref_h}" fill="#2563eb" stroke="#1d4ed8" stroke-width="1"/>\n'
        svg += f'  <rect x="{x + bar_w + 5}" y="{base_y - comp_h}" width="{bar_w}" height="{comp_h}" fill="#22c55e" stroke="#16a34a" stroke-width="1"/>\n'
        svg += render_wrapped_text(x + bar_w, base_y + 25, [name], "middle", 11, "#374151") + "\n"
        x += group_gap

    # Legend
    svg += '  <rect x="520" y="120" width="15" height="15" fill="#2563eb"/>\n'
    svg += render_wrapped_text(600, 127, ["Reference"], "middle", 12, "#111827") + "\n"
    svg += '  <rect x="520" y="145" width="15" height="15" fill="#22c55e"/>\n'
    svg += render_wrapped_text(600, 152, ["Computed"], "middle", 12, "#111827") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += svg_footer
    return svg


def build_optimization_svg(title: str, keywords: list[str], caption: str) -> str:
    """Multi-objective optimization Pareto front."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    # Axes
    svg += '  <line x1="80" y1="250" x2="720" y2="250" stroke="#111827" stroke-width="2"/>\n'
    svg += '  <line x1="80" y1="250" x2="80" y2="100" stroke="#111827" stroke-width="2"/>\n'
    # Axis labels
    svg += render_wrapped_text(400, 285, ["Objective 1"], "middle", 12, "#374151") + "\n"
    svg += render_wrapped_text(50, 170, ["Obj 2"], "middle", 12, "#374151") + "\n"

    # Pareto front curve
    svg += '  <path d="M 120,220 Q 250,200 400,150 T 680,110" fill="none" stroke="#7e22ce" stroke-width="3"/>\n'
    # Pareto-optimal points
    for x, y in [(150, 215), (300, 185), (480, 145), (650, 115)]:
        svg += f'  <circle cx="{x}" cy="{y}" r="5" fill="#7e22ce"/>\n'
    # Dominated points
    for x, y in [(200, 225), (350, 205), (550, 165)]:
        svg += f'  <circle cx="{x}" cy="{y}" r="4" fill="#64748b" opacity="0.6"/>\n'

    # Legend
    svg += '  <circle cx="540" cy="120" r="5" fill="#7e22ce"/>\n'
    svg += render_wrapped_text(600, 120, ["Pareto front"], "middle", 12, "#111827") + "\n"
    svg += '  <circle cx="540" cy="140" r="4" fill="#64748b" opacity="0.6"/>\n'
    svg += render_wrapped_text(600, 140, ["Dominated"], "middle", 12, "#111827") + "\n"

    svg += _render_caption(caption) + "\n"
    svg += svg_footer
    return svg


def build_solver_svg(title: str, keywords: list[str], caption: str) -> str:
    """Pressure-velocity coupling loop (SIMPLE/PIMPLE)."""
    svg_header, svg_footer = _svg_canvas(title)
    svg = svg_header
    svg += _render_title(title) + "\n"

    nodes = [
        ("Predict", 400, 90),
        ("Momentum", 560, 170),
        ("Pressure", 400, 250),
        ("Correct", 240, 170),
    ]

    # Arrows behind boxes
    arrows = [
        (400, 115, 500, 170),
        (560, 195, 400, 225),
        (340, 250, 300, 170),
        (240, 145, 400, 90),
    ]
    for x1, y1, x2, y2 in arrows:
        svg += f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#64748b" stroke-width="2" marker-end="url(#arrowhead)"/>\n'

    for label, x, y in nodes:
        svg += f'  <rect x="{x - 60}" y="{y - 25}" width="120" height="50" rx="8" fill="#dbeafe" stroke="#2563eb" stroke-width="2"/>\n'
        svg += render_wrapped_text(x, y, [label], "middle", 14, "#1e3a8a") + "\n"

    svg += render_wrapped_text(400, 170, ["SIMPLE / PIMPLE"], "middle", 12, "#64748b") + "\n"

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
    module = [
        ("Numeric", "#dbeafe", "#2563eb"),
        ("Array", "#dcfce7", "#16a34a"),
        ("Memory", "#fef3c7", "#d97706"),
        ("GPU", "#f3e8ff", "#7e22ce"),
    ]
    box_w, box_h = 100, 50
    start_x = 340
    for i, (label, fill, stroke) in enumerate(module):
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

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">\n'
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
            svg += f'  <text x="{px}" y="{y_off:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#1f2937">{html.escape(line)}</text>\n'

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
