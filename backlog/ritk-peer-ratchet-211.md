<a id="ritk-peer-ratchet-211"></a>
## RITK-PEER-RATCHET-211 — Peer commits regressed three ratchet classes on ritk [patch] — todo
- STALE as written (re-measured 2026-09-21 via the committed scanner, ritk worktree): `print_dbg` reads 0 and `manifest_implementation` 104 (baseline), so do NOT execute the old prescription; the only live remainder is `oversized_files` at 45 against baseline 43, which needs a fresh triage. The ritk tree held live peer dirt (ritk-snap dicom work).
- Acceptance: each class back at or below baseline, or the baseline regenerated with a recorded justification per the generator contract.
