<a id="atlas-kwavers-swe3d-baseline-regression-2026-08-26"></a>
## ATLAS-KWAVERS-SWE3D-BASELINE-REGRESSION-2026-08-26 — integration oracle regression on main [major] — todo
outcome: kwavers main's Architecture Validation → Test Suite Coverage integration suite is green; any baseline refresh is justified by a diagnosed cause (platform noise vs. a genuine solver-behavior change), never a mechanical `--update`.
open: `pstd_finite_window_born::source_phasing_is_frechet_derivative` fails locally at tip `dddb75c12` — half-resolution Born residual now exceeds full-resolution, violating the convergence-under-refinement assertion. Needs `git bisect` across six recent PSTD solver refactors, not a baseline `--update`.
