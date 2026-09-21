<a id="atlas-shared-tree-stale-basis-2026-09-17"></a>
## ATLAS-SHARED-TREE-STALE-BASIS-2026-09-17 — Reconcile the checkout and finish its stale-index guard [patch] — in-progress
- Integrator: codex-root; branch: `foundation-f3-correction-2026-09-10`; scope: stale-side guard, Git subprocess environments, root hook/provider audit, artifact path casing, tests, waivers, Makefile and recovered documentation.
- Acceptance: historical-content and provider checks honor the active commit index; Git errors fail closed; live split indexes pass; subprocess waits are bounded; filesystem board names match Git-tree casing; closed PM history is not a provider invariant.
- Evidence: reconciliation `f82e6d657`; Git routing `159e2c59b`; documentation `2fe880528`; path casing `be977ce6d`. Independent Windows child termination 30.60s; guard/root suite 38 tests and six subtests; artifact/conformance suite 105 tests and three subtests; provider suite 34 tests. Final full gates running.
- Verification: guard and root hook regression suites, then the configured root Python gate. Related: [member stale-basis item](ritk-shared-tree-stale-basis-213.md).
