<a id="atlas-cfdrs-athena-migration-001"></a>
## ATLAS-CFDRS-ATHENA-MIGRATION-001 — Stage B: CFDrs to Athena [major] [arch] — in-progress

Surveyed 2026-07-28 before starting. This is a redesign of the CFDrs
linear-solver architecture, not a port, and two of the mismatches change a
public CFDrs API — recording them rather than deciding unilaterally.

### Scale

56 files and 242 references across six crates (`cfd-1d`, `cfd-2d`, `cfd-3d`,
`cfd-core`, `cfd-math`, `cfd-validation`), of which **24 are production solver
construction sites** in 8 files; the rest are tests, benches, and re-exports.

`cfd_math::iterative` is currently a pure re-export of the `leto-ops` family
(`lib.rs:179`), so every consumer reaches the solvers through one facade.

### Structural mismatches

1. **Const-generic restart vs runtime config.** `Gmres<B, RESTART>` fixes the
   restart width at compile time. `LinearSolverChain` carries
   `krylov_restart: usize` as a runtime field with a builder
   (`with_krylov_restart`) and clamps it per solve:
   `min(self.krylov_restart, n_total_dof.max(1))`. A const generic cannot take
   that value. **Decision needed** (see below).
2. **Dynamic solver selection.** Four sites hold `Box<dyn LinearSolver<T>>`,
   including `cfd-validation` which builds a `Vec` of boxed solvers to compare
   CG against BiCGSTAB on the same system. Athena's solvers are ZST markers
   with static `solve_into`; `KrylovBackend` has GATs and `Gmres` a const
   generic, so none of it is dyn-compatible. The sanctioned replacement is
   enum dispatch over the closed solver set — I can decide this one, it is
   what the standards prescribe before reaching for `dyn`.
3. **Preconditioner trait.** CFDrs preconditioners — `AlgebraicMultigrid`,
   `BlockDiagonalPreconditioner`, `SimplePreconditioner`, `IncompleteLU`,
   `DiagJacobi` — implement `leto_ops::Preconditioner<T>`. Each needs an
   `athena_core::Preconditioner<LetoBackend<T>>` implementation instead.
   Mechanical, but touches every preconditioner.
4. **Caller-owned workspaces.** CFDrs solvers allocate internally per call;
   Athena requires a workspace owned by the caller and sized to the system, so
   every call site gains workspace lifetime management. This is the property
   that makes Athena allocation-free, so it is a real improvement rather than
   friction to work around — but it is a call-site change everywhere.
5. **Config to policy.** `IterativeSolverConfig { max_iterations, tolerance,
   relative_tolerance }` maps onto the validated `ConvergencePolicy`, which
   also carries a check interval and rejects invalid tolerances at
   construction. Mechanical.

### Decisions needed

**D1 — restart width.** Either (a) make `krylov_restart` a const parameter on
`LinearSolverChain`, a breaking change to a public CFDrs API; or (b) keep the
runtime field and dispatch across a small fixed set of `RESTART` instantiations
by enum, paying monomorphisation for each; or (c) fix one restart width and
delete the knob, checking first whether any caller sets it to a non-default
value. Recommend (c) if the knob is unused in practice, else (b).

**D2 — migration shape.** Either (a) convert all six crates in one change,
green only at the end; or (b) convert crate by crate while `cfd_math::iterative`
still re-exports `leto-ops`, deleting the facade last. (b) keeps the tree green
per commit and is not a shim — the old path stays only until its last consumer
is gone, which is what the anti-shim rule prescribes for a migration of this
size. Recommend (b), ordered `cfd-math` internals, then `cfd-2d`, `cfd-3d`,
`cfd-1d`, `cfd-validation`, then facade deletion.

### Not started

No CFDrs code changed. Nothing was added that would sit unused pending the
decisions above.

### Stage B progress 2026-07-28 — foundation landed, D1 corrected

**D1 was answered (c), and the check that answer depended on disproved it.**
`krylov_restart` is not an unused knob: `cfd-3d/fem/solver.rs` sets
`min(200, n)` at two sites, `cfd-1d/newton_fallback.rs` derives it from
`max_krylov_iterations`, and `cfd-math/nonlinear_solver/jfnk.rs` carries it in
its own config with 30 and 10 in tests and `min(n)` at runtime; the direct
`GMRES::new` sites use 30 and 100. Fixing one width would have silently
changed four solver configurations, so I took the fallback named in the same
decision — **(b), a fixed ladder with dispatch**.

- athena `f24dded`: `BorrowedCsrOperator`. `CsrOperator` takes ownership,
  which would force a per-solve `O(nnz)` sparse clone in a chain that tries
  several preconditioners against one system. Mirrors `BorrowedDenseOperator`.
- CFDrs `6a13a672`: `cfd_math::linear_solver::krylov` — the restart ladder
  (8/16/32/64/128/256, smallest covering width), `ConvergencePolicy`
  translation, and `gmres`/`gmres_preconditioned`/`bicgstab` entry points over
  Athena. Additive per D2(b): the `iterative` facade still re-exports leto-ops,
  so no consumer changed and the tree stays green per commit.
- Also repaired two cfd-math benches that had not compiled since `8aee5e59`
  left a stray brace in their imports.

Verification: cfd-math library compiles, clippy clean on the library, both
ladder cases pass, fmt clean. The package `--all-targets` gate is red for
reasons predating this change — unused imports and a dead struct in cfd-math
tests from the in-flight SSOT migration.

### Contention on the next increment

`chain.rs` is the next conversion target and a peer is **actively working in
it**: commit `16096fbc` ("resolve Quantity type mismatches in cfd-1d examples
and chain.rs") landed at 19:05 today and its rewrite of
`linear_solver/mod.rs` dropped the `pub mod krylov;` registration I had added,
leaving my file an orphan until I restored it. Converting `chain.rs` now would
collide directly.

Next increment should either wait for that scope to go quiet, or start at a
crate the peer is not in — `cfd-2d/src/physics/momentum/solver.rs` and
`cfd-2d/src/pressure_velocity/pressure.rs` are independent of `chain.rs` and
carry four of the twenty-four construction sites.

Remaining conversion order: `cfd-math` internals (`chain.rs`, multigrid),
`cfd-2d`, `cfd-3d`, `cfd-1d`, `cfd-validation`, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

Note for `cfd-validation`: four sites hold `Box<dyn LinearSolver<T>>` to
compare solvers on one system. Athena's markers are not dyn-compatible, so
that becomes enum dispatch over the closed solver set, per the standards.

### Stage B progress 2026-07-29 — cfd-2d converted

`58f6caab` momentum, `10fdd86e` pressure correction. cfd-2d is off the leto-ops
iterative family; the `cfd_math::iterative` facade still serves the other
crates, per D2(b).

- **Stateful solver objects removed.** Both consumers stored solver instances —
  `MomentumSolver` one GMRES, `PressureCorrectionSolver` three of which at most
  one was ever used, since `solver_type` already selected the recurrence.
  Athena solvers are stateless markers with caller-owned workspaces, so each
  collapses to the configuration it carried.
- **Triplicated policy consolidated.** `correction.rs` repeated the same
  solve-then-retry block verbatim per recurrence: solve with AMG, and on
  breakdown retry unpreconditioned, because a hierarchy built for a stale
  stencil can break the recurrence while the bare operator stays solvable.
  Written once now, with one dispatch over the closed solver set.
- **A real regression, caught and fixed at the right level.** Momentum assembly
  omits the diagonal of rows with no self-coupling. Athena's SOR rejects that;
  the leto-ops one had been *silently* defaulting those rows to a unit pivot.
  Rather than loosen the default, athena `461cdd5` added
  `from_csr_with_identity_rows` — same behaviour, opted into visibly at the
  call site, with a test pinning it.
- athena `f24dded` `BorrowedCsrOperator` removes a per-solve `O(nnz)` clone;
  the Athena SOR likewise borrows where the previous one took ownership, which
  matters because momentum rebuilds it after every coefficient update.
- `AlgebraicMultigrid` gained an Athena preconditioner implementation. Its
  V-cycle recurses over owned vectors while Athena passes borrowed views, so
  the boundary copies through cached buffers rather than allocating per
  application. Two `O(n)` passes against the cycle's `O(nnz)` sweeps.
  **Follow-up: rework the V-cycle onto slices to remove them.**

Verification: cfd-2d 570/571 nextest at both increments; the timeout is a
cross-fidelity tree test with no solver involvement that times out identically
without these changes. Clippy ran clean on the libraries for the first
increment; for the second it could not run — an in-flight `gaia` change removed
the `cfdrs-integration` feature cfd-2d depends on, breaking resolution for
unrelated reasons. **Re-run clippy on cfd-2d once gaia settles.**

