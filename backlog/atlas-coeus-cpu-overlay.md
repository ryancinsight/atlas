<a id="atlas-coeus-cpu-overlay"></a>
## ATLAS-COEUS-CPU-OVERLAY — Commit the stack overlay's coeus-cpu row [patch] — blocked
- Outcome: the committed `.cargo/config.toml` overlay maps the Coeus git sources to `coeus-cpu` instead of the deleted `coeus-leto` path, so local stack builds resolve again.
- Evidence: coeus PR #608 deleted `crates/coeus-leto`; the committed overlay still patches `coeus-leto = { path = "repos/coeus/crates/coeus-leto" }` (both Coeus sections), which fails every local build beneath the stack root. `atlas-stack-overlay.py generate` is currently unusable for this: version lag makes it drop 164 lines of still-functional rows. A surgical 2-line rename (key + path, both sections) is verified working in the filing checkout but deliberately left uncommitted: the file header reserves edits to the generator.
- Oracle: committed overlay contains `coeus-cpu = { path = "repos/coeus/crates/coeus-cpu" }` in both Coeus sections and no `coeus-leto`; `cargo check -p coeus-cpu --offline` passes with the overlay on.
- priority: tightening
- needs: none
- scope: atlas `.cargo/config.toml` only.
- **Re-opened 2026-10-20:** the recorded blocker is gone. The coeus pin advanced to `e8b429ffd8` (post-rename) in [atlas#550](https://github.com/ryancinsight/atlas/pull/550), so a `coeus-cpu` row no longer dangles. The dead `coeus-leto` mapping is what fails every cargo command beneath the stack root, and [atlas#551](https://github.com/ryancinsight/atlas/pull/551) regenerates the overlay so the dead row is gone. The generator still drops the rows whose local tree cannot satisfy a lagging consumer's requirement, so the `coeus-cpu` row this item's oracle asks for waits on ATLAS-VERSION-COHERENCE-SWEEP advancing the consumers and their locks.
