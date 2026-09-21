<a id="atlas-cross-member-sweep-108"></a>
## ATLAS-CROSS-MEMBER-SWEEP-108 — cross-member staleness and dirt sweep [patch] (2026-08-23) — in-progress
- **outcome:** every stranded/diverged branch and dirty checkout found across the 28-member liveness sweep is rescued, adjudicated (delivered or retired), and its lane/branch reclaimed.
- **next: still diverged, needing per-PR integration** — proteus #17, hephaestus #216, kwavers #439/#440/#617/#620/#622–#624.
- **Filed as its own item:** asclepius's aequitas/coeus first-party deps (^0.1.0/^0.9.0) no longer resolve against current releases (0.2.0/0.10.0) — advance through the 0.9→0.10 API surface.
- **Re-open triggers:** CFDrs PR #360 verdict [collected]; author decisions on remaining rescue branches; moirai re-check once its live peer's commit lands.
