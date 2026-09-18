<a id="atlas-board-closure-canon-001"></a>
## ATLAS-BOARD-CLOSURE-CANON-001 - Canonicalize historical closure markers [pm-hygiene] [patch] [M] — in-progress

- Outcome: every closed item carries the one canonical heading marker so
  atlas-board-compact.py archives at full power and
  atlas-board-lint.py's reference scope stays accurate.
- Measured 2026-08-24: compact dry-run archived only 18 of 236 backlog
  items (8 percent) because closure markers vary by era - heading
  "- closed DATE", body Status lines, checkmark bullets, unmarked.
  Full-power archival would collapse thousands of archive-prose lines;
  today they remain live-scope and feed the 323 reference mentions the
  lint reports.
- Scope: pick the canonical form (heading `- closed YYYY-MM-DD`);
  script a reviewed one-pass normalization; rerun compaction; then flip
  ATLAS-LINT-CALIB's reference report toward enforcing for items that
  stay live after normalization.
- Status: in-progress (integrator: claude session; lease: scripts/atlas-board-canonicalize.py, backlog.md, checklist.md, focused tests)

