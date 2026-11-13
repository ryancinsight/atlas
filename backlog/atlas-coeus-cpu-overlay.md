<a id="atlas-coeus-cpu-overlay"></a>
## ATLAS-COEUS-CPU-OVERLAY — Commit the stack overlay's coeus-cpu row [patch] — blocked
- Outcome: the committed `.cargo/config.toml` overlay maps the Coeus git sources to `coeus-cpu` instead of the deleted `coeus-leto` path, so local stack builds resolve again.
- Oracle: committed overlay contains `coeus-cpu = { path = "repos/coeus/crates/coeus-cpu" }` in both Coeus sections and no `coeus-leto`; `cargo check -p coeus-cpu --offline` passes with the overlay on.
- priority: tightening; scope: atlas `.cargo/config.toml` only
- needs: qualify bounded concurrent CI worktree materialization within unchanged budgets (#580's compatible checker is published at11bbccfb), then reconcile closure with the existing Atlas #551 owner; retain the original index's blocked hold. Historical oracle claims below remain historical, not exact-current-revision verification (2026-10-26 parity audit).
