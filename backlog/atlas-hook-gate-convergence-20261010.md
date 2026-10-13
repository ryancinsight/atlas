<a id="atlas-hook-gate-convergence-20261010"></a>
## ATLAS-HOOK-GATE-CONVERGENCE-20261010 — Converge the hook-gate rollout, then sweep gitlinks [arch] — todo
outcome: one hook version stack-wide, hephaestus tip debt cleared, and every member gitlink at its default tip with a green atlas gate.
state 2026-10-12: members run `.githooks/pre-push` blob `a15f2cb365` from `83cb58595` (cast gate); atlas main owned `99aa412490`, so any gitlink bump read `member_gate_versions` 1->2. [atlas #537](https://github.com/ryancinsight/atlas/pull/537) lands `83cb58595` (193 hook tests + 82 subtests pass locally). hephaestus tip: oversized 36->37 and apollo pin manifest_implementation 6->7 also blocked probe `f8fac04f`.
acceptance: `member_gate_versions` = 1 at the sweep revision; hephaestus/apollo rows at or below baseline; atlas PR CI green; gitlinks = fetched default tips. priority: correctness; needs: #537 merged; scope: scripts/git-hooks, atlas gitlinks.
next: on #537 landing, push the gitlink sweep refreshed to fetched tips (preserved branch `chore/gitlinks-green-20261012`), fixing apollo/hephaestus pin rows first if still raised; then delete this item. basis: atlas `714bdd169` 2026-10-12.
