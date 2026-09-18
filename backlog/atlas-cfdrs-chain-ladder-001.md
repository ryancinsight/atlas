<a id="atlas-cfdrs-chain-ladder-001"></a>
## ATLAS-CFDRS-CHAIN-LADDER-001 — Consolidate the two tiered ladders [patch] — in-progress

`LinearSolverChain::solve` and `solve_with_state` run the same five tiers with
three deliberate differences: log prefix, an iterate reset between tiers, and
the warm path skipping the unpreconditioned tier once a block preconditioner
was built but stalled. Express the ladder once with those as parameters, and
decide explicitly whether the cold path should adopt the skip policy — it is
an improvement the warm path received and the cold one did not, and adopting
it changes which solver answers a given system.

Remaining stage B: cfd-3d, cfd-1d, cfd-validation, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (evening) — cfd-3d deferred, cfd-validation converted

**cfd-3d was not attempted.** Both its solver files were being edited live:
`crates/cfd-3d/src/fem/solver.rs` had a modification timestamp one minute
before I began, alongside 17 other dirty cfd-3d files from a peer's Quantity
migration. Editing there would have collided destructively, so the scope was
skipped rather than taken. **Re-open trigger: cfd-3d/src/fem goes quiet.**

Its two sites when it does: `projection_solver.rs` holds a `GMRES` and a
`ConjugateGradient` field, and `solver.rs` holds `_linear_solver: GMRES<T>` —
note the underscore, it is already dead and should be deleted rather than
converted. `solver.rs` also drives `LinearSolverChain`, which is already on
Athena.

**cfd-validation converted instead**, `f8634e43` — a clean, disjoint file.

- `Vec<(&str, Box<dyn LinearSolver<T>>)>` becomes `SolverKind`, the closed-set
  enum dispatch decided earlier. Athena's markers carry const generics and
  backend GATs and are not object-safe, so this was the one site that could
  not be a mechanical swap.
- Same correction `chain.rs` needed: Athena reports a stalled or broken-down
  solve in the report, not as `Err`, so a bare match would have **recorded a
  non-converged iterate as a validation result**.
- The split between fatal and tolerated failure is preserved deliberately: the
  ill-conditioned Hilbert case is expected to break down; the diagonal and
  Poisson cases are not.
- `SolverKind` lives in cfd-math beside the other entry points so the
  pressure-velocity dispatch can adopt it rather than keep its own match —
  **follow-up**.

Verification: `cargo check` clean for cfd-validation and cfd-math. Tests could
not run — `repos/hephaestus` is mid-rebase onto a branch four commits behind
master, so `hephaestus-core` does not compile in the shared tree. **Re-run the
cfd-validation suite once that settles.**

Note the compounding cost: three consecutive increments have now had a gate
blocked by shared-tree churn — clippy twice by `ATLAS-TOOLCHAIN-COHERENCE-001`,
tests once by a mid-rebase hephaestus. The verification debt is tracked, not
silently absorbed.

Remaining stage B: cfd-3d (blocked), cfd-1d, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (late) — cfd-1d converted

`4ca6518d`. The network solver's iterative tier is on Athena.

- The CG and BiCGSTAB arms were identical apart from the recurrence, so they
  collapse onto `SolverKind`. `LinearSolverMethod` stays as the domain-facing
  choice and maps onto it.
- `DiagJacobi` gained an Athena implementation that applies straight over the
  borrowed views — elementwise, so no scratch and no copy, unlike the AMG
  boundary which must buffer.
- The post-solve residual check is kept, with its reason now explicit: the
  solve runs on the **row-equilibrated** matrix, so meeting the tolerance
  there does not bound the residual of the original system. Athena reporting
  convergence is one of two acceptance conditions, not the only one.

Verification: cfd-1d **736/736** nextest including the primary-solve
reliability cases that exercise this path, `cargo check` clean.

### Correction to an earlier claim

I recorded after `40ef080c` that "cfd-math is fully off the leto-ops iterative
family". True as stated, but incomplete as an impression: `cfd-math`
`nonlinear_solver/jfnk.rs` carries its **own hand-rolled matrix-free
restarted GMRES** (`gmres_matrix_free`), which never used leto-ops. It is a
fifth GMRES in the stack after leto-ops, the deleted CFDrs copy, kwavers, and
Athena. Filed below.

