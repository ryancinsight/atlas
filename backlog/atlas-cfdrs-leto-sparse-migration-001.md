<a id="atlas-cfdrs-leto-sparse-migration-001"></a>
## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — todo

Filed as follow-up per Session 17 closure of `ATLAS-LETO-OPS-SPARSE-LU-001`.
Now that real sparse LU + partial pivoting has landed at leto `687b670`,
the CFDrs downstream consumer should adopt the upstream-native solver.

- Owner: unclaimed. Depends on CFDrs leto version bump (currently
  `aequitas = { path = "../aequitas" }` and leto path-pinned at
  atlas-meta level).
- Outcome: replace `crates/cfd-math/src/linear_solver/direct_solver.rs`
  body with calls to `leto_ops::application::sparse::SparseLuSolver::solve_view`
  on real CSC-typed inputs; remove any `with_direct_threshold(512)`-
  regime mats that exist purely to route medium saddle-point FEM
  matrices to GMRES (Brezzi 1974 indefinite saddle — sparse LU is now
  correct for it, not a misnomer).
- Acceptance: (1) CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs`
  no longer documents itself as "atlas-native sparse direct solver backed
  by dense partial-pivoting LU" (cf. the doc-runtime contradiction),
  (2) CFDrs cfd-3d suite verifies end-to-end (`validate_poiseuille_flow`
  PR #311 root-caused fix continues to PASS under the new upstream
  matrix-as-sparse path; re-profile runs `<1s` per Session 13 closure
  baseline), (3) `direct_threshold` parameter either removed from the
  CFDrs FEM solver or re-evaluated with new evidence (filed as a follow-up
  board item against CFDrs perf, not this slice).
- Risk/change class: `[minor]` (additive public-API call-site
  migration; no break to CFDrs public surface).
- Dependencies: leto version bump at CFDrs; aequitas pin coherence
  (Session 12 documented the eunomia dual-source-ID recurring risk
  when consumers pin eunomia differently; align all atlas consumers
  on URL-only form).
- Refs: backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed),
  leto origin/main `687b670`.

