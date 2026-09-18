<a id="atlas-cfdrs-athena-migration-001"></a>
## ATLAS-CFDRS-ATHENA-MIGRATION-001 — Stage B: CFDrs to Athena [major] [arch] — in-progress

- **outcome:** CFDrs's six linear-solver crates (`cfd-1d/2d/3d`, `cfd-core`, `cfd-math`, `cfd-validation`) run on Athena instead of `leto-ops`; the `cfd_math::iterative` facade and the leto-ops iterative dependency are deleted once every consumer is converted.
- **Scale:** 24 production solver construction sites across 8 files, of 56 files / 242 references total.
- **Decided:** D1 (restart width) — runtime `krylov_restart` is used by real callers, so answered (b): a fixed enum-dispatched restart ladder (8/16/32/64/128/256), not a const generic. D2 (migration shape) — (b) convert crate by crate while the facade still re-exports leto-ops, deleting it last.
- **Done:** cfd-math internals (krylov ladder, `BorrowedCsrOperator`), cfd-2d (momentum `58f6caab`, pressure correction `10fdd86e`) — both off leto-ops.
- **next:** convert `chain.rs` and multigrid in cfd-math, then cfd-3d, cfd-1d, cfd-validation (four sites there need enum dispatch over `Box<dyn LinearSolver<T>>`, per the same standard), then delete the `cfd_math::iterative` facade and the leto-ops dependency.
- **Contention:** `chain.rs` was peer-occupied as of last check (commit `16096fbc`); re-verify liveness before starting there, or start at `cfd-2d/src/physics/momentum/solver.rs`/`pressure_velocity/pressure.rs` if still occupied.
- **Follow-up:** rework the `AlgebraicMultigrid` V-cycle onto borrowed slices; re-run clippy on cfd-2d once the in-flight gaia `cfdrs-integration` feature change settles.
