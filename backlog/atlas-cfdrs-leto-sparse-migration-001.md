<a id="atlas-cfdrs-leto-sparse-migration-001"></a>
## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — todo
outcome: replace `crates/cfd-math/src/linear_solver/direct_solver.rs` body with calls to `leto_ops::application::sparse::SparseLuSolver::solve_view` on real CSC-typed inputs; remove any `with_direct_threshold(512)` regime that exists only to route medium saddle-point FEM matrices to GMRES.
- Acceptance: (1) direct_solver.rs no longer documents itself as "atlas-native sparse direct solver backed by dense partial-pivoting LU"; (2) CFDrs cfd-3d suite verifies end-to-end (`validate_poiseuille_flow` stays PASS, re-profile <1s); (3) `direct_threshold` removed or re-evaluated (filed separately against CFDrs perf).
- Dependencies: CFDrs leto version bump (currently path-pinned at atlas-meta level); aequitas pin coherence across atlas consumers (URL-only form).
- Refs: backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed), leto origin/main `687b670`.
