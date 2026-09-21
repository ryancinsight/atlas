<a id="atlas-board-closure-canon-001"></a>
## ATLAS-BOARD-CLOSURE-CANON-001 - Canonicalize historical closure markers [pm-hygiene] [patch] [M] — in-progress
- **outcome:** every closed item carries one canonical heading marker (`- closed YYYY-MM-DD`) so `atlas-board-compact.py` archives at full power and `atlas-board-lint.py`'s reference scope stays accurate.
- **why:** measured 2026-08-24, compact dry-run archived only 18/236 items (8%) because closure markers vary by era (heading, body Status line, checkmark bullet, unmarked).
- **next:** script a reviewed one-pass normalization to the canonical form, rerun compaction, then flip ATLAS-LINT-CALIB's reference report toward enforcing for items that stay live after normalization.
