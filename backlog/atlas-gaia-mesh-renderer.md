<a id="atlas-gaia-mesh-renderer"></a>
## ATLAS-GAIA-MESH-RENDERER — Gaia renders meshes; metis hosts the window and the input — in-progress
- Outcome: gaia `application::render` (orbit camera, z-buffered software rasteriser); metis `examples/mesh_viewer.rs` proof of use. Full design, defect narrative, and evidence in gaia/metis PR bodies #57–#60 and metis #364/#365.
- Delivered: gaia merged #57 `a4c22bf`, #58 `b34419bc`, #59 `299e414`, #60 `d0ddbaa`; gaia main `40a3b7c → c213257` (PR #61 test split). Metis PRs #364 (ADR 0044) and #365 (viewer) open pending checks.
- Residuals: collect metis #364/#365, then advance Atlas gaia + metis gitlinks. Open code findings ride gaia's own backlog: `propagate.rs` 1059-line split, `min_det` dimension note, `fit_sphere` companion, `VecDeque` ARCH-008 pattern widen, `VertexPool` `as u32`.
