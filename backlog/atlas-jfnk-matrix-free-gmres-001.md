<a id="atlas-jfnk-matrix-free-gmres-001"></a>
## ATLAS-JFNK-MATRIX-FREE-GMRES-001 — Converge JFNK onto Athena [minor] — todo

- `cfd-math/src/nonlinear_solver/jfnk.rs` implements restarted GMRES inline for
  Jacobian-free Newton-Krylov, using only matrix-vector products.
- Migrating it needs Athena's `LinearOperator` over a Jacobian-vector closure.
  Check first whether that closure needs `&mut self` — if so it hits the same
  blocker as Kwavers stage C (`ATLAS-GMRES-FORK-CONVERGE-001`), and the two
  should be solved together rather than separately.
- `cfd-1d/src/solver/core/newton_fallback.rs:223` feeds `krylov_restart` into
  this config, so it is the last cfd-1d reference to a non-Athena solver.

Remaining stage B: cfd-3d (blocked on peer activity in `cfd-3d/src/fem`), JFNK,
then delete the `cfd_math::iterative` facade and the leto-ops iterative
dependency.

### Verification debt review 2026-07-30

**cfd-3d is still not clear.** Peer commit `63e49604` landed at 01:40, twelve
minutes before the check, and `projection_solver.rs` carries their uncommitted
continuation of the same Quantity migration (`.into_base()` conversions).
Fresh and commit-backed, so the scope stays blocked. `solver.rs` is clean now,
but it is the same live scope. Re-check later.

**cfd-validation tests: discharged.** The hephaestus rebase finished, so the
suite ran: **184/187 passed, 3 timed out** in
`numerical::venturi_cross_fidelity`.

Those three were investigated rather than assumed pre-existing, because they
drive `cfd_2d::solvers::ns_fvm` SIMPLE and could plausibly have been a
convergence regression from the pressure-correction migration. They are not:
`ns_fvm` solves its pressure-correction Poisson with **its own hand-rolled SOR
sweep** (`solvers/ns_fvm/solver/pressure/poisson.rs`), never reaching
`PressureCorrectionSolver` or any Krylov solver in this migration. Running one
case without a timeout shows SIMPLEC continuity stagnant at ~4.59e2 across ten
iterations and still running past 400s, which is that SOR failing to converge
on a micro-scale geometry. The file is also peer-dirty. Filed below.

**Clippy: still blocked**, third consecutive attempt, now surfacing on
`cfd-io` whose dependencies were built by a different rustc. Note the tests
passed minutes earlier under the same toolchain — the poisoned artifact set
differs by which crates a command pulls, which is exactly why this presents as
moving, unrelated breakage. `ATLAS-TOOLCHAIN-COHERENCE-001` is the blocker and
is now the single largest drag on verification.

