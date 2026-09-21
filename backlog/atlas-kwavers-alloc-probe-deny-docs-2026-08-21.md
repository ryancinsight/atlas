<a id="atlas-kwavers-alloc-probe-deny-docs-2026-08-21"></a>
## ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 — Pilot deny(missing_docs) [patch] — in-progress
- **outcome:** `kwavers-alloc-probe` compiles with `#![deny(missing_docs)]`, the first of 118 flagged crates to adopt it, demonstrating the pattern for the remaining 117 (114 of which need per-crate doc work first).
- **next:** merge [kwavers PR #598](https://github.com/ryancinsight/kwavers/pull/598) at exact head `aa5ab2bc94ba31dbd5f7438aaef41195e9bf5c8e` once its hosted checks (CI/CD, Architecture Validation, benchmark regression, Legacy Migration Audit, Deploy mdBook) go terminal — all were still `queued` after 56 min of observation, no runner had picked up a job.
- **Acceptance:** hosted checks green at the exact PR head; no pointer advance or bypass until then.
