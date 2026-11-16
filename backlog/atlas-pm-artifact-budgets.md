<a id="atlas-pm-artifact-budgets"></a>
## ATLAS-PM-ARTIFACT-BUDGETS — Stack PM artifacts run eight to sixteen times their budget [patch] — todo
- Outcome: every board, checklist and gap audit inside the 1,000-line budget.
- Next, in order: atlas `gap_audit.md` (16,338 lines, 420 findings) needs a verdict per finding, not a filter — a closed one's residue belongs in a lint, an ADR or the slop-pattern library; then kwavers `gap_audit.md` (7,891) and the remaining members by scan count.
- Item byte budget (judge /865): the 15-line item budget is met by single lines of 2,200-2,900 characters in eunomia, and atlas's own items run longer (ATLAS-EXPORT-TREE-FRESHNESS-RESIDUALS is one bullet of about 5,000 characters). Oracle: `atlas-artifact-budget.py check` reports an item over a byte bound derived from the line budget and the repository's line width, as a non-increasing baselined class (first step: measure the item-size distribution per board and state the derivation).
- Acceptance: `pm_lines_over_budget` at zero per member as it is worked, every deleted ID still recoverable by `git log --grep='^Item: <id>'`.
