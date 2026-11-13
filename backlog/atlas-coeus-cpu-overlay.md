<a id="atlas-coeus-cpu-overlay"></a>
## ATLAS-COEUS-CPU-OVERLAY — Commit the stack overlay's coeus-cpu row [patch] — blocked
- Outcome: the committed `.cargo/config.toml` overlay maps the Coeus git sources to `coeus-cpu` instead of the deleted `coeus-leto` path, so local stack builds resolve again.
- Oracle: committed overlay contains `coeus-cpu = { path = "repos/coeus/crates/coeus-cpu" }` in both Coeus sections and no `coeus-leto`; `cargo check -p coeus-cpu --offline` passes with the overlay on.
- priority: tightening; scope: atlas `.cargo/config.toml` only
- needs: qualify bounded concurrent CI worktree materialization within unchanged budgets (#580's compatible checker is published at11bbccfb), then reconcile closure with the existing Atlas #551 owner; retain the original index's blocked hold. Measured 2026-11-13 at e0f893530: `.cargo/config.toml` holds 2 `coeus-cpu` rows (lines 189, 198) and no `coeus-leto`; the `cargo check -p coeus-cpu --offline` clause is not re-measured, so the item stays blocked until its `needs:` close (2026-10-26 parity audit).
