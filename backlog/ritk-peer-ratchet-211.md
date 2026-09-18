<a id="ritk-peer-ratchet-211"></a>
## RITK-PEER-RATCHET-211 — Peer commits regressed three ratchet classes on ritk [patch] — todo

- `print_dbg 12 → 17`, `oversized_files 43 → 44`,
  `manifest_implementation 104 → 105`.
- Attribution is unambiguous: the counts are **identical at HEAD and in the
  dirty worktree**, so they came from the peer commits (#171–#173) that moved
  ritk's HEAD from `bacfe1f6` to `0f0b5c56` mid-session, not from the
  accessor work, which is ratchet-neutral.
- `print_dbg +5` is the one to look at first — five new print/`dbg!` sites in
  library code is a lint-floor breach, not drift.
- Acceptance: each class back at or below baseline, or the baseline
  regenerated with a recorded justification per the generator contract.

