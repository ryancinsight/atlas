<a id="atlas-adr0033-stages"></a>
## ATLAS-ADR0033-STAGES — Krylov ownership unwind, measured status [arch] — in-progress

Re-measured 2026-08-20 against the trees rather than the board. ADR 0033's
four-stage plan is further along in places and wider in others than recorded.

**Stage A — close Athena's capability gap: DONE.**
`athena-core` ships `Cg<B>`, `BiCgStab<B>`, `Gmres<B, const RESTART>`, and
`Lsqr<B>` (`crates/athena-core/src/solver/*/algorithm.rs`), and `athena-leto`
ships Jacobi, ILU, and SOR/SSOR preconditioners over `LetoBackend`. Residual gap,
not part of stage A but blocking backend-generic solving: **no preconditioner
exists for the Hephaestus backend**, so accelerator PCG is unpreconditioned CG
(`crates/athena-hephaestus/src/lib.rs` versus the three `athena-leto` impls).

**Stage B — migrate CFDrs: substantially done, remainder in flight.**
Production CFDrs already solves through Athena. `cfd-math/src/linear_solver/
krylov.rs` (613 LOC) builds a `LetoBackend` and `BorrowedCsrOperator` and
dispatches Athena's solvers; it is a legitimate adapter, not a shim, because
Athena's `Gmres<B, const RESTART>` is const-generic while CFDrs selects restart
at runtime. There are no `GMRES::new`/`BiCGSTAB::new`/`ConjugateGradient::new`
call sites in `crates/*/src` at all — the single occurrence is inside a doc
comment.

What remains is the re-export shim `pub mod iterative { pub use leto_ops::{...} }`
in `cfd-math/src/lib.rs`, whose own doc calls leto-ops "the SSOT iterative-solver
types" in direct contradiction of this ADR. It keeps the Leto family alive and so
blocks stage D. The concrete duplication it sustains: `DiagJacobi<T>` in
`cfd-1d/src/solver/core/linear_system.rs` implements **both** preconditioner
traits — leto's at line 301 and `athena_core::Preconditioner` at line 311 —
exactly the duplication stage D names. Remaining consumers are five test/bench
files plus `IterativeSolverConfig` (56 references).

**Stage B increment (2026-08-22):** PR
[#363](https://github.com/ryancinsight/CFDrs/pull/363) at head `27338e95`,
rebased onto the merged format-gate default `a70faea6`. The branch deletes the
`pub mod iterative` re-export shim and migrates its callers; the `DiagJacobi`
dual-trait duplication is already resolved on the branch — only the
`athena_core::Preconditioner<LetoBackend>` impl remains. Local evidence:
`cargo fmt --all --check` clean; nextest `-p cfd-math -p cfd-validation`
675/675; warning-denied Clippy clean for cfd-math, cfd-validation, and
cfd-1d (the two `needless_update` warnings in `cfd-3d` are pre-existing
default debt the branch does not touch).

**Rebase and blocker fix (2026-08-23):** hosted run `32590225522` failed on
exactly those two `needless_update` sites — with every other debt class
cleared stack-wide they became the only remaining `-D warnings` errors, i.e.
delivery-blocking. Commit `05c025e8` deletes the two no-effect
`..Default::default()` bases (all three struct fields are specified at both
sites). Local: workspace clippy `-D warnings` reports zero errors, cfd-3d
nextest 400/400, fmt clean.

**Stage B closed (2026-08-23):** replacement gate terminal success at
`05c025e8`; PR #363 merged with the expected-head guard at default `c5f9fa2c`;
post-merge CI `32611718091` collected before further solver work on this
default.

**Stage C scoping confirmed (2026-08-23):** the Leto Krylov family now has
**zero stack-wide consumers** (`linalg::iterative` imports: helios, ritk,
coeus, harmonia, CFDrs, kwavers, moirai, tyche all scan zero), so Stage D's
consumer precondition is met and only ADR 0033's sequencing (C before D)
holds deletion. Stage C scope verified present at kwavers origin/main:
`kwavers-solver/src/forward/bem/gmres.rs` (334 LOC, f64-hardcoded dense
GMRES), `kwavers-solver/src/integration/nonlinear/gmres/` (419 LOC), and the
matrix-free operator whose `jacobian_vector_product`
(`multiphysics/monolithic/residual/jvp.rs:17`) needs the `&mut self` →
`&self` refactor (scratch-buffer cache is its only mutation). Kwavers uses
`leto_ops` only for matvec/dot primitives elsewhere — legitimate array ops,
not Krylov recurrences.

**Stage C claim blocked on lane availability:** all seven registered Kwavers
worktree lanes hold live published PR branches (#598, #590, #602, and peers);
the two-tree bound forbids minting a ninth tree, and the primary checkout is
detached and dirty. This is a genuine contention deferral: re-open when any
lane completes its hosted collection and merges (its tree then re-points),
or when a peer releases a lane. DoR is otherwise complete: outcome (one
Athena-backed Krylov implementation; delete the three Kwavers duplicates),
acceptance oracle (ADR 0033 Stage C/D acceptance — residue scan finds no
Krylov recurrence outside Athena; every consumer suite passes against
Athena), change class `[minor]` breaking internal seam per the ADR.

**Stage C — migrate Kwavers: not started, and wider than the ADR recorded.**
Kwavers declares no `athena` dependency in any manifest. It carries **three**
iterative implementations, where ADR 0033 anticipated one:

- `kwavers-solver/src/forward/bem/gmres.rs` — 334 LOC dense GMRES, `f64`-hardcoded
  (29 `f64` occurrences), Modified Gram-Schmidt Arnoldi with Givens rotations.
- `kwavers-solver/src/integration/nonlinear/gmres/` — 419 LOC (solver 249,
  tests 110).
- The matrix-free operator feeding the monolithic multiphysics residual.

The ADR's stated prerequisite holds exactly as written: `jacobian_vector_product`
at `kwavers-solver/src/multiphysics/monolithic/residual/jvp.rs:17` takes
`&mut self`, and its only mutation is the `jvp_state_scratch` buffer cache, so it
can satisfy `LinearOperator::apply(&self, ...)` once that scratch moves to
caller-owned workspace or interior mutability.

**Stage D — delete `leto-ops/src/application/linalg/iterative/`: blocked on B and
C.** Consumer check across the stack found no other repository importing the Leto
iterative family — helios, ritk, coeus, and harmonia are all clean. CFDrs and
Kwavers are the only two holding it alive.

Sequencing is unchanged from the ADR: B, then C, then D, each converting its
consumers in the same change, with no compatibility layer at any stage.

