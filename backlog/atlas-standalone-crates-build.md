<a id="atlas-standalone-crates-build"></a>
## ATLAS-STANDALONE-CRATES-BUILD — Make the five unbuildable standalone crates compile [patch] — todo
- Outcome: `atlas_cast_gate.py measure --manifest <crate>` completes at each member's origin/main for the crates below, and each gets its row in `scripts/cast-baseline.json`. Until then the owned hook refuses any push touching them: the cast gate cannot judge them.
- Evidence (stable clippy `--locked`, shared target, baseline bases, 2026-10-02): consus `fuzz/` no committed `Cargo.lock`; gaia `fuzz/` workspace-belief metadata failure; mnemosyne `fuzz/` stale lockfile; moirai `fuzz/` builds `--cfg fuzzing`, measured at 2.
- metis `fuzz/`: stale lockfile + `crates/metis-cli/src/manifest/svg.rs:23` cannot find `crate::bounded_read` via `#[path]`; melinoe `contracts/atlas-device/` path-deps on siblings (`../../../hephaestus/...`), builds only in the stack checkout.
- Oracle: the measure command exits 0 for each crate at its member's origin/main, and its row lands.
- priority: verification
- needs: none
- scope: the five crates and their member boards, then `scripts/cast-baseline.json`.
- Next step: per crate, the fix the evidence names (commit or regenerate the lockfile; an empty `[workspace]` table for gaia's; the `bounded_read` dependency for metis's include; git+version sources for melinoe's contract crate).
