<a id="atlas-identity-overlay-locked-metadata"></a>
## ATLAS-IDENTITY-OVERLAY-LOCKED-METADATA — Read the overlay's dependency graph without refusing its lock [patch] — todo
- Outcome: an identity run on a fresh stack tree under the development overlay reads its dependency snapshot from the committed lock form, instead of failing before its first build.
- Evidence: `_cargo_metadata` runs `cargo metadata --locked` (`scripts/atlas_build_artifacts.py`, added by 03aee53b0). Under the overlay's `[patch]`, Cargo must rewrite the committed lock (patched packages lose their `source` line, `[[patch.unused]]` appears), which `--locked` refuses. So `run_build` cannot start until some other Cargo command rewrites the working lock. A judge reproduced this on ryancinsight/atlas#422, with a fresh overlay tree and `cargo metadata --locked` exiting nonzero.
- Oracle: a real-Cargo test with a stack root `.cargo/config.toml` patching a Git dependency to a local path tree runs `run_build` on the committed lock and records. The same test with a lock that resolves differently outside the overlay is still refused.
- priority: correctness
- needs: ATLAS-IDENTITY-NARROW-ADDED-DEPS (ryancinsight/atlas#422)
- scope: scripts/atlas_build_artifacts.py, scripts/tests/test_atlas_build_identity.py, docs/adr/0064-shared-build-source-identity.md
- Next step: decide whether the snapshot reads the overlay's rewrite (the build's actual resolution) or the committed lock, from what `run_build`'s command itself resolves.
