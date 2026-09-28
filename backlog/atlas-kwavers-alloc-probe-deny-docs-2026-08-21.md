<a id="atlas-kwavers-alloc-probe-deny-docs-2026-08-21"></a>
## ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 — Pilot deny(missing_docs) [patch] — in-progress
- **outcome:** `kwavers-alloc-probe` compiles with `#![deny(missing_docs)]`, the first of 118 flagged crates to adopt it, demonstrating the pattern for the remaining 117 (114 of which need per-crate doc work first).
- **delivered:** kwavers PR #598 merged (extended to `kwavers-alloc-probe`, `kwavers-mesh`, `kwavers-field`; 3 of 118 flagged crates).
- **next:** extend `#![deny(missing_docs)]` to the remaining 114 flagged crates that still need per-crate doc work (tracked by the `missing_deny_docs` class in ATLAS-HYGIENE-BASELINE-001; not a safe mechanical sweep — see gap_audit history).
- **Acceptance:** each migrated crate compiles under the directive with focused gates green at its exact head.
