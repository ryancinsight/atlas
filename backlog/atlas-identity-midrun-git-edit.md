<a id="atlas-identity-midrun-git-edit"></a>
## ATLAS-IDENTITY-MIDRUN-GIT-EDIT — Stamp a trusted Git package whose checkout moved during a failed run [patch] — todo
- Outcome: a run that fails after a trusted Git package's checkout was edited mid-build leaves that package stale, so the next run cleans it instead of reusing what the failed build wrote from the edit.
- Evidence: the fifth soundness judge on ryancinsight/atlas#422 (its `midrun_edit.py`). A run trusts `g` (stamp current). The checkout is edited after the snapshot and before Cargo builds a variant the target lacks (the check-mode rmeta). The run fails, and the checkout is restored. The next `cargo check` reuses the rmeta built from the edit and fails while the checkout holds the original. The parent commit 8e01dbaf8 behaves the same way. The `building` sentinel covers only packages a run cleans or finds unstamped (`scripts/atlas_build_identity.py`, `_BUILDING`).
- Oracle: the judge's scenario as a real-Cargo test: after the failed run the stamp reads `building`, and the next run cleans `g` and builds the original.
- priority: correctness
- needs: ATLAS-IDENTITY-NARROW-ADDED-DEPS (ryancinsight/atlas#422)
- scope: scripts/atlas_build_identity.py, scripts/tests/test_atlas_build_identity.py, docs/adr/0064-shared-build-source-identity.md
- Next step: on any failure after the command started, re-read the content digests of the trusted Git packages and stamp each that moved as `building`. An edit that lands and is reverted within one build stays out of reach; record that bound.
