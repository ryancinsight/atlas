<a id="atlas-hook-fleet-blob-drift"></a>
## ATLAS-HOOK-FLEET-BLOB-DRIFT — Member pre-push hooks carry a blob that is not on atlas main [patch] — todo
- Outcome: every member's default-branch `.githooks/pre-push` is byte-identical to atlas's default-branch `scripts/git-hooks/pre-push`, and the one blob they share is either landed on atlas main or replaced.
- Evidence (2026-11-13, fetched origin of each member, atlas origin/main 12708acf3ae4892d4443627f0d6d5016ddeb29d7): 28 of 29 member default branches hold one `.githooks/pre-push` blob (`leoneuro-rs` has none), and it differs from atlas main's `scripts/git-hooks/pre-push`. That blob is in none of the 84 atlas-main commits touching the file. It equals `git rev-parse refs/pull/647/head:scripts/git-hooks/pre-push` of open draft atlas#647 (`rescue/atlas-root-cast-base-owner`, label `judge-required`, last commit 2026-11-10); the hook diff of #647 against main is +51/-11.
- Consequence: a fix to atlas's hook ([ATLAS-HOOK-MERGE-RANGE](../backlog.md#atlas-hook-merge-range), [ATLAS-HOOK-NEXTEST-CONFIG-OWNER](../backlog.md#atlas-hook-nextest-config-owner)) reaches no member until the drift is resolved, and the fleet runs hook code that atlas main never reviewed.
- Oracle: for every member, `git rev-parse origin/<default>:.githooks/pre-push` equals `git rev-parse origin/main:scripts/git-hooks/pre-push` of atlas; the closing PR lists the 29-member loop output.
- basis: 12708acf3ae4892d4443627f0d6d5016ddeb29d7; priority: verification; needs: none
- scope: `scripts/git-hooks/pre-push`, member `.githooks/pre-push` copies, atlas#647
- Links: [ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06](../backlog.md#hook-fleet-duplication), [ATLAS-HOOK-DIRECT-PATH-RETIRE](../backlog.md#ATLAS-HOOK-DIRECT-PATH-RETIRE). Widens the filed metis-only finding: metis holds the same blob as the other 27.
- Next step: judge #647, the source of the shared blob: land it, or close it and republish main's blob to the 28 copies through the sync PRs.
