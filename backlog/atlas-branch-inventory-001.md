<a id="atlas-branch-inventory-001"></a>
## ATLAS-BRANCH-INVENTORY-001 - Burn down stack branch inventories [git-hygiene] [patch] — in-progress

outcome: every member's local branches map to an open item or enqueued PR (orient rule); merged/gone-upstream branches prune mechanically, unmerged survivors salvage via takeover per content-supersession (not just patch-id).

Mechanical phase closed stack-wide 2026-08-26: ~236 branches deleted across 26 members, each evidence-backed (merged / cherry-landed / merged-PR tip / content-superseded). `delete_branch_on_merge=true` set on all 26 members; `allow_auto_merge=true` on 25/26 (leoneuro-rs declines: plan/visibility limit, falls back to merge-on-green).

next: ~98 survivor branches with real deltas remain takeover material, closest-to-done-first — kwavers (35 refs: 8 PR-scratch, 5 merged-PR leftovers, 7 recent seams/docs/ci, 12 codex/* WIP incl. aequitas family), ritk (17 refs: 5 merged-PR tails, 4 large Aug WIP, 8 small fixes), coeus (17, incl. coeus-frobenius provider/cherry/rebase/v2 family to consolidate), apollo (12), and ~21 other members. Per-item takeover increments, not a sweep.
