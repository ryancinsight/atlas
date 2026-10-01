<a id="atlas-build-identity-split"></a>
## ATLAS-BUILD-IDENTITY-SPLIT — Split the build-identity scripts by operation family [patch] — todo
- Outcome: `scripts/atlas_build_identity.py` (1,057 lines after ryancinsight/atlas#422) and `scripts/atlas_build_artifacts.py` (553) split into modules under the 500-line target, one operation family each: the dependency snapshot and its digests, artifact discovery and hashing, Git build stamps, the stale-package rule, and the `run_build` lease protocol.
- Evidence: `wc -l` at ryancinsight/atlas#422's head. The identity module was 1,015 lines on main before it; #422 added the snapshot's manifest digests to the artifacts module (taking it past 500) and a build-directory type to the identity module. The conformance scan's `oversized_files` class counts Rust files only, so neither is measured.
- Oracle: every module under 500 lines; the identity, package-source and pre-push gate suites pass unchanged, test names diffed by `pytest --collect-only -q` before and after; tests patch each function at its new home, never through a re-export.
- priority: tightening
- needs: ATLAS-IDENTITY-NARROW-ADDED-DEPS (ryancinsight/atlas#422)
- scope: scripts/atlas_build_identity.py, scripts/atlas_build_artifacts.py, scripts/tests/test_atlas_build_identity.py, docs/adr/0064-shared-build-source-identity.md
- Next step: map each function to its family and its test patch sites (`patch.object(identity, ...)`, `patch.object(artifacts, ...)`), then move the snapshot family first.
