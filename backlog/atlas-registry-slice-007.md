<a id="atlas-registry-slice-007"></a>
## ATLAS-REGISTRY-SLICE-007 — Read drift through the shared registry policy [patch] — todo
- outcome: the drift and bump-guard tools read the registry through the shared policy; 327 changed lines (exact).
- oracle: scripts/tests/test_atlas_published_drift.py and scripts/tests/test_atlas_bump_guard.py in full (the real-TCP drift tests need the strict reader of ATLAS-REGISTRY-SLICE-009), plus the fast and slow CI runs.
- basis: 2b000c51b; priority: architecture; needs: ATLAS-REGISTRY-SLICE-005, ATLAS-REGISTRY-SLICE-009; pins: none (in no closure); scope: `scripts/atlas-published-drift.py`, `scripts/atlas-bump-guard.py`, `scripts/tests/test_atlas_published_drift.py`, `scripts/tests/test_atlas_bump_guard.py`
- next: the drift tests expect `registry response failed` from `_raise_registry_io` and `incomplete registry HTTP body` retried as `RegistryTransportError`. Open, not in the oracle: verdict F4 (drift reads REGISTRY_POLICY through crates_pending).
- links: slice 7 of the PR 587 verdict (https://github.com/ryancinsight/atlas/pull/587#issuecomment-6866306457); source tree `refs/pull/587/head`; cut from its net diff against main.
