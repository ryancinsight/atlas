<a id="atlas-coeus-cpu-overlay"></a>
## ATLAS-COEUS-CPU-OVERLAY — Commit the stack overlay's coeus-cpu row [patch] — blocked
- Outcome: the committed `.cargo/config.toml` overlay maps the Coeus git sources to `coeus-cpu` instead of the deleted `coeus-leto` path, so local stack builds resolve again.
- Evidence: coeus PR #608 deleted `crates/coeus-leto`; the committed overlay still patches `coeus-leto = { path = "repos/coeus/crates/coeus-leto" }` (both Coeus sections), which fails every local build beneath the stack root. `atlas-stack-overlay.py generate` is currently unusable for this: version lag makes it drop 164 lines of still-functional rows. A surgical 2-line rename (key + path, both sections) is verified working in the filing checkout but deliberately left uncommitted: the file header reserves edits to the generator.
- Oracle: committed overlay contains `coeus-cpu = { path = "repos/coeus/crates/coeus-cpu" }` in both Coeus sections and no `coeus-leto`; `cargo check -p coeus-cpu --offline` passes with the overlay on.
- priority: tightening
- needs: none
- scope: atlas `.cargo/config.toml` only.
- **Blocked 2026-10-19:** the rename cannot land alone. At the recorded coeus gitlink (3ea49578, pre-rename) a `coeus-cpu` row dangles, so the overlay freshness gate fails; advancing the coeus gitlink in the same commit trips pin drift in every member still locked at 0.10. Re-open after ATLAS-VERSION-COHERENCE-SWEEP advances the full cohort and its locks.
