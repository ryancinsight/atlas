<a id="atlas-cwd-config-cost-2026-09-16"></a>
## ATLAS-CWD-CONFIG-COST-2026-09-16 — Cargo config discovery is all-or-nothing: the shared `target-dir` arrives with the whole-stack `[patch]` overlay [patch] — in-progress

delivered: `CargoOverlayFixture` no longer resolves/checks from the Atlas root, so the 46-table/136-row stack `[patch]` overlay never applies to its two-package fixture graph; resolution and compile budgets are split (30s/120s) and the fixture now owns its own `CARGO_TARGET_DIR` inside its tempdir rather than inheriting the shared stack cache, closing the underlying contention-reported-as-hang failure mode.
- Acceptance: no fixture/test invocation depends on `cwd` for a stack config key it needs; a cargo command in this suite either owns its target directory or sizes its bound as a hang guard, not a performance assertion.
- Verified 2026-09-16: `pytest scripts/tests/test_atlas_stack_overlay.py` → 20 passed; `pytest scripts/tests` → 702 passed, 3 skipped, 89 subtests. Regression test `test_fixture_builds_in_its_own_target_not_the_shared_stack_cache` guards against reverting to the shared cache.
