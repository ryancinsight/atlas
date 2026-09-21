<a id="atlas-jfnk-matrix-free-gmres-001"></a>
## ATLAS-JFNK-MATRIX-FREE-GMRES-001 — Converge JFNK onto Athena [minor] — todo
- **outcome:** `cfd-math/src/nonlinear_solver/jfnk.rs`'s inline restarted GMRES migrates onto Athena's `LinearOperator`; `cfd_math::iterative` facade and leto-ops iterative dependency are then deleted.
- **check first:** whether the Jacobian-vector closure needs `&mut self` — if so, solve together with Kwavers stage C (`ATLAS-GMRES-FORK-CONVERGE-001`).
- **blocked:** cfd-3d — peer commit `63e49604` left `projection_solver.rs` mid-migration; re-check later. Also blocked on clippy, itself blocked by `ATLAS-TOOLCHAIN-COHERENCE-001` (poisoned cross-rustc artifacts on `cfd-io`), the largest current drag on verification.
