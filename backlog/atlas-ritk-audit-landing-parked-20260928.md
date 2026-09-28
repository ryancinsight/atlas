<a id="atlas-ritk-audit-landing-parked-20260928"></a>
## ATLAS-RITK-AUDIT-LANDING-PARKED-20260928 — Land the verified ritk audit commit [patch] — blocked
- priority: tightening
- outcome: the audit's verified-clean ritk commit (bb8b2596 on `audit-ritk-20260926`, base de32e111: unwrap 61 → 22 expect-migration, seven classes reduced, 37 files) rebases onto ritk main and merges — rebase, gate per changed crate, PR.
- blocker: ritk's live snap-lane peer (PRs #669/#676, two-tree cap) holds the exact region the diff conflicts in (ritk-snap render/reslice/orientation); re-open when its PRs merge and a tree frees.
