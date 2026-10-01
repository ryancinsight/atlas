<a id="atlas-gate-step-batch"></a>
## ATLAS-GATE-STEP-BATCH — One identity run per gate step, not per package [patch] — todo
- Outcome: a member push gates its changed packages in one identity run per step (clippy, tests, docs), so the closure is snapshotted, leased and hashed once per step instead of once per package.
- Evidence: the owned hook runs `run_identity_step` once per package per step (`scripts/git-hooks/pre-push`, the clippy, nextest and doc loops). A 12-package metis push is therefore 36 identity runs. Each run takes the dependency snapshot up to four times and waits up to 900 s per lease. A push of metis perf/metis-image-decode-single-buffer, with the checker at 8e01dbaf8, gated from 00:17 to 01:53 on 2026-10-01. It had finished clippy on all 12 packages and was in the tests step of the first when it was stopped.
- Oracle: wall time of a 12-package metis push on a warm shared target, measured before and after with the same revision and no peer gate. Every gated package stays covered: the per-package record, or its replacement, still detects a stand-in for each package's artifacts (the existing identity suites, plus a test naming several packages in one run).
- priority: tightening
- needs: ATLAS-IDENTITY-NARROW-ADDED-DEPS (ryancinsight/atlas#422), so the baseline is measured with the narrowed cleans.
- scope: scripts/git-hooks/pre-push, scripts/atlas_build_identity.py, scripts/tests/test_atlas_pre_push_gate.py, scripts/tests/test_atlas_build_identity.py, docs/adr/0064-shared-build-source-identity.md
- Links: [ATLAS-IDENTITY-LEASE-STARVATION](atlas-identity-lease-starvation.md) covers the lease waits between gates. This item covers the run count within one gate; fewer runs per push shorten every hold that item measures.
- Next step: measure one no-op identity run (record matches, cargo fresh) per phase — snapshot, leases, re-hash — to attribute the per-run cost before choosing between a multi-package run and cutting the per-run overhead.
