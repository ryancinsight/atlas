<a id="atlas-conformance-workflow-overlay-2026-09-21"></a>
## ATLAS-CONFORMANCE-WORKFLOW-OVERLAY-2026-09-21 — exclude the checked-out Atlas overlay from member scans [patch] — in-progress

- Status: in-progress; priority: P1; owner: Atlas verification; integrator: root; last-update: 2026-09-21.
- Scope: the reusable conformance workflow's `_atlas` checkout and the scanner's source traversal; no debt baseline changes.
- Acceptance: the exact workflow checkout no longer scans `_atlas` as member content; a focused regression test proves the exclusion; the member guard passes against the committed baseline without raising debt counts.
- Basis: hosted Metis run `35648065340` failed because `--member-path .` traversed the nested `_atlas` checkout, reporting `oversized_files 0 -> 3`, `manifest_implementation 0 -> 2` and `existence_only_assertions 0 -> 4` after PR #330. Reproduction uses the reusable workflow layout and the exact scanner revision `02a304f519c27b95169b87b732e6e631d51c205d`.
- Re-open trigger: a future reusable member workflow changes the overlay directory or the scanner's traversal skips a checked-in source tree.
