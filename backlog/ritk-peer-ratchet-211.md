<a id="ritk-peer-ratchet-211"></a>
## RITK-PEER-RATCHET-211 — Peer commits regressed three ratchet classes on ritk [patch] — todo
- STALE as written (re-measured 2026-09-21 via the committed scanner, ritk worktree): `print_dbg` reads 0, not 17 — the item predates the `build.rs` cargo-protocol exemption and subsequent cleanup; `manifest_implementation` reads 104, back at baseline; `oversized_files` reads 45 (baseline 43) — still drifting, the only live remainder.
- Do NOT execute the old prescription (print/manifest halves already resolved); the actionable residue is a fresh oversized-files triage against the current 45. Ritk tree holds live peer dirt (ritk-snap dicom work); coordinate there.
- Acceptance: each class back at or below baseline, or the baseline regenerated with a recorded justification per the generator contract.
