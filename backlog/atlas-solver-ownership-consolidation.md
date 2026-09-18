<a id="atlas-solver-ownership-consolidation"></a>
## ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION — Complete ADR 0033: the Krylov forks and the only multigrid in the stack live in CFDrs [arch][major] — todo

Decision: [ADR 0062](docs/adr/0062-iterative-solver-and-preconditioner-ownership.md),
**Accepted 2026-09-10** — Phase 1 carries a sequencing condition: the relocations
touch `repos/CFDrs` and `repos/kwavers`, both on the forced Moirai 0.6.0 sweep order,
so they execute once that sweep lands. Board opened from the
[2026-09-09 foundation audit](docs/audit/2026-09-09-foundation-layer-next-steps.md)
finding F1.

- **Outcome:** `athena` owns iterative policy and preconditioner composition,
  `leto` owns the sparse kernels, and no integrator keeps a local copy.
- **Measured 2026-09-09.** ADR 0033 is Accepted and its first two legs landed:
  `athena` owns `Cg`, `Gmres<_, RESTART>`, `BiCgStab`, `Lsqr` and the
  `Preconditioner` trait; `leto` has no `Preconditioner` and no iterative
  module. The third leg did not: `cfd-math/src/linear_solver/` still carries
  `krylov.rs`, `preconditioners/{ilu,multigrid}`, `block_preconditioner.rs`,
  `direct_solver.rs`, `chain.rs`, `dense_bridge.rs`, and `kwavers` carries one
  further Krylov file.
- **Why it is worse than ordinary duplication.** `multigrid` occurs **zero**
  times in `athena`, `leto`, and `coeus` — it exists only in `cfd-math`. The
  member chartered to own solver policy cannot offer it to anyone. And the
  forks can drift: ADR 0055's P2-B evidence already records `cfd-core` and
  `kwavers-medium` disagreeing on aluminium (70 GPa against 69 GPa).
- **Scope discipline.** Per ADR 0011 §Leg 2 the source edits are consumer-claim
  work in `repos/CFDrs` and `repos/kwavers`; this row tracks them. Phase 1 is a
  **move with a differential oracle**, not a rewrite — anything that cannot
  reproduce current CFDrs output on existing fixtures was an algorithm change
  and does not belong in it.
- **Acceptance:** `cfd-math/src/linear_solver/` is gone and its callers re-point
  at `athena` + `leto`; the `kwavers` Krylov file is gone; the false doc comment
  at `leto-ops/src/application/linalg/mod.rs` is deleted; every relocated solver
  reproduces its prior output on existing fixtures at `f32` and `f64`.
- **Phase 2** (new construction, gated per ADR 0056 on analytical oracles, not
  on a second consumer): `athena` gains MINRES, FGMRES, Chebyshev,
  deflation/recycling. **Phase 3** deferred: algebraic multigrid needs a
  grid-hierarchy owner, since prolongation/restriction is interpolation and
  ADR 0055 R6 assigns that to geometry.
- **Dependencies:** none on other open items. Not blocked by the Apollo Moirai
  `rev` quarantine, though CI cannot confirm Phase 1 while the stack overlay is
  red.

