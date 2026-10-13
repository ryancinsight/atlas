<a id="atlas-hook-gate-convergence-20261010"></a>
## ATLAS-HOOK-GATE-CONVERGENCE-20261010 — Converge the hook-gate rollout, then sweep gitlinks [arch] — todo
outcome: one hook version stack-wide, hephaestus tip debt cleared, and every member gitlink at its default tip with a green atlas gate.
state 2026-10-12: members merged the cast-gate `.githooks/pre-push` from the unlanded `fix/cast-gate-takeover` branch while atlas main owned the older gate, so any gitlink bump read `member_gate_versions` 1->2. [atlas #537](https://github.com/ryancinsight/atlas/pull/537) lands that gate plus the gitlink sweep to fetched default tips in one revision (193 hook tests + 82 subtests pass locally); apollo/hephaestus pin rows are re-probed at the refreshed tips in that PR.
acceptance: `member_gate_versions` = 1 at the sweep revision; hephaestus/apollo rows at or below baseline; atlas PR CI green; gitlinks = fetched default tips. priority: correctness; needs: none; scope: scripts/git-hooks, atlas gitlinks.
next: merge [atlas #537](https://github.com/ryancinsight/atlas/pull/537), then delete this item. basis: atlas origin/main at #536, 2026-10-12.
