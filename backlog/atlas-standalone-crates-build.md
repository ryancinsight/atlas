<a id="atlas-standalone-crates-build"></a>
## ATLAS-STANDALONE-CRATES-BUILD — Make the five unbuildable standalone crates compile [patch] — todo
- Outcome: `atlas_cast_gate.py measure --manifest <crate>` completes at each member's origin/main for the crates below, and each gets its row in `scripts/cast-baseline.json`; until then the owned hook refuses any push touching them.
- Evidence (stable clippy, `--locked`, shared target, at each member's basis in the baseline, 2026-10-02): consus `fuzz/` has no committed `Cargo.lock`; gaia `fuzz/` fails `cargo metadata` ("current package believes it's in a workspace when it's not"); metis `fuzz/` has a stale lockfile and `crates/metis-cli/src/manifest/svg.rs:23` cannot find `crate::bounded_read` through `#[path]`; mnemosyne `fuzz/` has a stale lockfile; melinoe `contracts/atlas-device/` path-depends on sibling repositories (`../../../hephaestus/...`), so it builds only inside the stack checkout; moirai `fuzz/` builds with `--cfg fuzzing` and measures 2.
- Oracle: the measure command exits 0 for each crate at its member's origin/main, and its row lands.
- priority: verification
- needs: none
- scope: the five crates and their member boards, then `scripts/cast-baseline.json`.
- Next step: per crate, the fix the evidence names (commit or regenerate the lockfile; an empty `[workspace]` table for gaia's; the `bounded_read` dependency for metis's include; git+version sources for melinoe's contract crate).
