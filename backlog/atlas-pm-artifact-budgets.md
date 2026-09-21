<a id="atlas-pm-artifact-budgets"></a>
## ATLAS-PM-ARTIFACT-BUDGETS — The stack's PM artifacts are eight to sixteen times their budget [patch] — in-progress

outcome: every board, checklist and gap audit in the stack sits inside the
1,000-line budget, and the ratchet that measures them has nothing left to
hold down.

- Done. atlas `checklist.md` 7,911 to 2,312: every section whose boxes were
  all checked has no next step left, so 194 went and the 58 carrying an
  unchecked box stayed. kwavers `backlog.md` 14,181 to 5,685 (kwavers #809):
  397 finished items deleted, the five ADRs that linked them by anchor now
  name the ID the way the other ADRs do.
- Next, in order. atlas `gap_audit.md` (16,338 lines, 420 findings): unlike a
  board this needs a verdict per finding — a closed one's residue belongs in a
  lint, an ADR or the slop-pattern library, and only open risks with a live
  re-open trigger stay — so it is a read pass, not a mechanical filter. atlas
  `backlog.md` (965) is inside budget but is mostly a "Landed from this sweep"
  table, the ledger genre the board rule deletes. kwavers `gap_audit.md`
  (7,891) and `checklist.md` follow, then the remaining members by the scan's
  `pm_lines_over_budget` count.
- Acceptance: `python scripts/atlas-conformance.py report --worktree` shows
  `pm_lines_over_budget` at zero for each member as it is worked, and no
  deleted entry's ID is unrecoverable — `git log --grep='^Item: <id>'` finds
  its delivery.
- Non-goals: rewriting live items, and any member whose board is already
  inside budget.
