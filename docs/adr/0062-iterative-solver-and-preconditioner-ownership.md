# ADR 0062: Iterative solvers and preconditioners are Athena policy over Leto kernels

- Status: **Accepted** — 2026-09-10 (proposed and accepted same day; acceptance
  directed by the architect on "proceed with the next phase").
- Date: 2026-09-10
- **Sequencing condition on Phase 1:** accepted as doctrine now, but the Phase 1
  source relocations touch `repos/CFDrs` and `repos/kwavers`, and both sit on the
  forced Moirai 0.6.0 sweep order — kwavers' `main` is currently unresolvable and
  CFDrs is peer-held at `build/cfdrs-moirai-06`. Relocations execute once that
  sweep lands, not before; nothing in this ADR authorises a cross-repo move into
  a tree that cannot compile.
- Class: `[arch]` `[major]`
- Relates to: [ADR 0033](0033-krylov-ownership-reaffirmation.md) (the
  ownership this closes), [ADR 0022](0022-horae-athena-simulation-providers.md)
  (Athena's charter), [ADR 0034](0034-athena-single-accelerator-backend.md),
  [ADR 0055](0055-continuum-domain-decomposition.md) (R6, geometry owns
  interpolation), [ADR 0056](0056-new-construction-promotion-path.md) (the
  oracle rule for Phase 2)
- Board: [ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION](../../backlog.md#atlas-solver-ownership-consolidation)

## Context

ADR 0033 reaffirmed `athena` as the Krylov owner and unwound the `leto`
regression. That decision is Accepted. Measuring the stack at this revision
shows the reassignment was executed on only one of its three legs, and the
leg that was skipped is the one holding the most valuable code.

**Leg 1, done.** `athena` owns the iteration policy: `Cg`,
`Gmres<_, RESTART>` (restarted, right-preconditioned), `BiCgStab`, `Lsqr`, the
`Preconditioner` trait at `athena-core/src/preconditioner/traits.rs`, and
`Jacobi`, `IncompleteLu`, `SuccessiveOverRelaxation`, and triangular impls in
`athena-leto/src/preconditioner/`.

**Leg 2, done and then left inconsistent.** `leto` lost its duplicate
recurrences and now has **no `Preconditioner` type and no iterative module at
all**. `crates/leto-ops/src/application/linalg/` contains only direct and dense
decompositions. This is correct — but `application/linalg/mod.rs` still
documents "Iterative solvers (CG, BiCGSTAB, GMRES, LSQR) and preconditioners"
directly above `pub mod lu;`, so the crate advertises a capability ADR 0033
removed, and `docs/audit/math-ssot-ledger.md` §3 repeated the claim into an
audit artifact that later planning reads.

**Leg 3, not done.** The consumer forks were never deleted.
`CFDrs/crates/cfd-math/src/linear_solver/` still carries `krylov.rs`,
`preconditioners/{ilu, multigrid}`, `block_preconditioner.rs`,
`direct_solver.rs`, `chain.rs`, and `dense_bridge.rs`. `kwavers` carries one
further Krylov file. `ATLAS-GMRES-FORK-DEFECTS-001` closed on 2026-08-03 having
*ported corrections into* those forks rather than removing them, so the
duplication was known and preserved deliberately.

Two consequences follow from leg 3 that are worse than ordinary duplication:

- **Multigrid exists only inside `CFDrs`.** Zero occurrences in `athena`,
  `leto`, or `coeus`. The preconditioner family that makes large multiphysics
  solves tractable sits in an integrator's math crate, and the member chartered
  to own solver policy cannot see or offer it to anyone else.
- **The forks can drift, and this stack has already paid that tax.** The
  ADR 0055 P2-B evidence records `cfd-core::ElasticSolid` and
  `kwavers-medium::ElasticPropertyData` agreeing exactly on steel and
  disagreeing on aluminium (70 GPa against 69 GPa). Two copies of one physical
  law is how that happens.

`athena` additionally has no MINRES (symmetric indefinite), no FGMRES (variable
preconditioner), no deflation or recycling, no Chebyshev, no QMR/TFQMR/IDR, no
LSMR, and no Arnoldi/Lanczos machinery.

## Decision

Preconditioning and iterative solution are **Athena policy composed over Leto
kernels**, and no integrator keeps a local copy of either.

| Concern | Owner | Rationale |
| --- | --- | --- |
| Iteration policy: method, restart, convergence, residual bookkeeping | `athena` | ADR 0022 and ADR 0033 |
| Preconditioner *policy and composition*: block, chain, cycle, relaxation schedule | `athena` | Composition is policy; it decides how kernels are sequenced, not how they compute |
| Preconditioner *kernels*: sparse triangular solve, ILU numeric factorization, SpMV, Jacobi scaling | `leto` | `leto` owns host arrays and the sparse formats (`CsrMatrix`, `CscMatrix`, `CooMatrix`) these operate on |
| Direct sparse solve | `leto` | Already owned: `application/sparse/` with AMD ordering (`amd.rs`, wired at `lu_symbolic.rs:45`) |
| Multigrid as a preconditioner family | `athena` | It is a `Preconditioner` impl, not a solver API of its own |

### Phase 1 — relocate, no new algorithms

Move `cfd-math/src/linear_solver/` into the two owners and delete the consumer
copies:

- `krylov.rs`, `block_preconditioner.rs`, `chain.rs` → `athena` (policy and
  composition).
- `preconditioners/ilu`, `preconditioners/ssor*`, `dense_bridge.rs` kernels →
  `leto` (`application/sparse/`) where the sparse formats already live.
- `direct_solver.rs` → `leto`, which already owns `SparseLuSolver`.
- `preconditioners/multigrid` → `athena` as a `Preconditioner` impl.
- Delete the remaining `kwavers` Krylov file against the same surface.
- Delete the false doc comment at `leto-ops/src/application/linalg/mod.rs`.

No algorithm changes in this phase. Callers re-point; nothing is rewritten.

### Phase 2 — fill the gaps, gated on oracles

`athena` gains MINRES, FGMRES, Chebyshev, and deflation/recycling. Under
[ADR 0056](0056-new-construction-promotion-path.md) these are new construction,
so they are gated on analytical oracles rather than on a second consumer:
closed-form solutions, manufactured solutions, and conservation identities,
each at `f32` and `f64`.

### Phase 3 — deferred, with a named trigger

Algebraic multigrid, and any coarse-grid transfer over unstructured meshes,
needs a grid-hierarchy owner. Prolongation and restriction are interpolation,
which ADR 0055 R6 assigns to geometry and ADR 0050 denies to `harmonia`.
Phase 1 delivers **geometric** multigrid on structured grids, where the
hierarchy is a property of the `leto` grid and no geometry package is involved.
Reopen AMG when `gaia` owns a mesh-hierarchy or coarsening seam, or when a
second consumer needs unstructured coarsening.

## Non-goals

- **Eigenvalue machinery.** Arnoldi, Lanczos, and eigensolvers are a separate
  capability with their own ownership question. Not moved here.
- **Changes to `harmonia`.** It calls solvers; it does not own them.
- **Changes to Athena's backend story.** ADR 0034 stands: one accelerator
  backend through `hephaestus`.
- **A multigrid or solver package.** Rejected below.

## Verification

Phase 1 is a move, so its oracle is differential: every relocated solver and
preconditioner reproduces its current CFDrs output on the existing CFDrs
fixtures to the recorded convergence tolerance, at `f32` and `f64`. Anything
that cannot be reproduced this way was an algorithm change and does not belong
in Phase 1.

Phase 2 oracles, per ADR 0056:

| Oracle | Statement |
| --- | --- |
| MINRES on a symmetric indefinite system | Recovers the closed-form solution of a constructed indefinite system where CG must fail |
| FGMRES with a varying preconditioner | Converges where restarted GMRES with a fixed preconditioner stalls, on a constructed varying-preconditioner case |
| Chebyshev | Smoothing property on a high-frequency residual, against the analytic damping bound |
| Multigrid | Mesh-independent convergence: iteration count is flat as the grid refines, against the two-grid analytic estimate |
| Preconditioner round trip | `apply` then `solve` on an identity preconditioner reproduces the input exactly, so marshalling adds nothing |
| Zero null case | A zero right-hand side produces exactly zero solution and zero iterations, so the composition adds no spurious forcing |

## Consequences

- `CFDrs` loses a solver surface it exercises daily. That is real migration
  cost, and it is the point: the surface was doing the stack's job locally.
- One solver stack becomes visible to every integrator instead of one. In
  particular multigrid stops being a CFDrs-only capability.
- The `leto` linalg doc comment and the ledger §3 row must both be corrected as
  part of this work — they are the reason the inconsistency survived a year of
  audits. The ledger correction is already applied; the doc comment is Phase 1.
- Nothing in this ADR changes ADR 0033. It completes it.

## Alternatives considered

1. **Leave the forks in place.** Rejected: multigrid stays invisible to the
   owner, and two Krylov implementations drift. This stack has already measured
   that failure mode in the elastic catalogs.
2. **Promote multigrid to its own package.** Rejected: gate conditions 1 and 6
   are unmet — `CFDrs` is the only consumer and nothing crosses a repository
   boundary. Multigrid is a preconditioner family, not a bounded context.
3. **Put the whole solver stack in `leto`.** Rejected by ADR 0033, which exists
   precisely to stop `leto` carrying duplicate recurrences.
4. **Put everything, including sparse kernels, in `athena`.** Rejected: `leto`
   owns host arrays and sparse formats; `athena` would have to re-own SpMV and
   sparse triangular solve to do this, duplicating the substrate it composes.
5. **Rewrite the solvers against a new unified API during the move.** Rejected:
   it makes the first integration the largest one, and it destroys the
   differential oracle — a move and a rewrite cannot be told apart in review.
