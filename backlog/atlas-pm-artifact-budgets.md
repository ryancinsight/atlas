<a id="atlas-pm-artifact-budgets"></a>
## ATLAS-PM-ARTIFACT-BUDGETS — Stack PM artifacts run eight to sixteen times their budget [patch] — in-progress

- Outcome: every board, checklist and gap audit inside the 1,000-line budget.
- Done: atlas `checklist.md` 7,911 to 2,312 (194 sections with every box
  checked have no next step left); atlas `backlog.md` 967 to 226 (the landed
  table and nine session closures go, all 148 item links stay); kwavers
  `backlog.md` 14,181 to 5,685 with its five anchor-linking ADRs renamed to
  the ID form (kwavers #809).
- Next, in order: atlas `gap_audit.md` (16,338 lines, 420 findings) needs a
  verdict per finding, not a filter — a closed one's residue belongs in a
  lint, an ADR or the slop-pattern library; then kwavers `gap_audit.md`
  (7,891) and the remaining members by scan count.
- Acceptance: `pm_lines_over_budget` at zero per member as it is worked,
  every deleted ID still recoverable by `git log --grep='^Item: <id>'`.
