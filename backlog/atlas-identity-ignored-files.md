<a id="atlas-identity-ignored-files"></a>
## ATLAS-IDENTITY-IGNORED-FILES — Keep gitignored run output out of a path package's identity [patch] — todo
- Outcome: a gitignored file appearing in a path dependency's tree (run output, logs) no longer moves that package's source identity, so it does not clean it.
- Evidence: a judge on ryancinsight/atlas#422 wrote `out/run.log` under a gitignored `/out` in an overlay member `d`, and the next run cleaned `d`. Source identity hashes ignored files outside `target/`. Cargo reads only files a build names (sources, `include_*!`, build-script `rerun-if-changed` paths), and those can be ignored too, so dropping ignored files needs a bound, not a blanket exclusion.
- Oracle: a real-Cargo test where an ignored, unread file appears in a path dependency cleans nothing, and an ignored file the build reads (`include_str!`) still cleans its package.
- priority: tightening
- needs: ATLAS-IDENTITY-NARROW-ADDED-DEPS (ryancinsight/atlas#422)
- scope: scripts/atlas_build_source.py, scripts/atlas_build_identity.py, scripts/tests/test_atlas_build_identity.py, docs/adr/0064-shared-build-source-identity.md
- Next step: measure how often ignored files move a stack member's identity across a day of pushes, from the records under `target/.atlas/source-identity`.
