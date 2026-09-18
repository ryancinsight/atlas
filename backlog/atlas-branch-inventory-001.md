<a id="atlas-branch-inventory-001"></a>
## ATLAS-BRANCH-INVENTORY-001 - Burn down stack branch inventories [git-hygiene] [patch] — in-progress

- Outcome: every member's local branches map to an open item or enqueued
  PR (orient rule); measured 2026-08-26: kwavers 65 (12 merged, 6 gone),
  moirai 30 (24 merged, 15 gone), coeus 21, apollo 17, hermes 14,
  helios 16. Merged/gone prune mechanically; the unmerged remainder
  classifies by patch-id against origin default (rebase/squash-landed
  deletes as landed; unique deltas salvage per takeover) — one
  mechanical sweep per member, proportionate triage.
- Sweep done 2026-08-26 — 125 branches deleted across 26 members (merged
  into origin default, or gone-upstream with cherry-verified empty delta);
  kwavers stashes cleared by peer.
- kwavers classified 2026-08-26: 56 -> 35 refs (21 more landed branches
  deleted; every survivor verified to hold real content deltas vs main —
  content-supersession test on touched files, not just patch-id).
  Survivor families, takeover material closest-to-done-first: 8
  PR-scratch (pr-622/623/624/633/646, fix622/fix622-work/fix622b, small
  deltas); 5 merged-PR leftovers (+1..+8 past merged tips: #364 #434
  #443 #609, remove-simulated-gpu-swe); 7 recent seams/docs/ci (Aug
  19-25); 12 July-era codex/* WIP (aequitas family, +3..+138 commits —
  largest recoverable value, oldest basis, naming-rule renames due at
  takeover).
- ritk classified 2026-08-26: 33 -> 19 refs (15 deleted: merged tips,
  cherry-landed, merged). 17 survivors with real deltas: 5 merged-PR
  tails (+1..+3 past #54 #80 #116 #154 #166); 4 large Aug 1-7 WIP
  (release-workflow-caller +35, coeus-publishability +29,
  reconcile-model-coeus +26, gradient-reorientation +20); 8 small
  recent fixes/docs (Aug 11-19, +1..+3).
- Mechanical phase closed 2026-08-26, stack-wide: coeus 21->17 (note the
  coeus-frobenius provider/cherry/rebase/v2 sibling family — consolidate
  at takeover), gaia 19->2 (cascade/provider-042 held by the tree's
  checkout bookkeeping), apollo 16->12, and 50 more deletions across the
  other 21 members (consus 13->5, helios 14->7, moirai 7->4, ...).
  Session total: ~236 branches deleted, every deletion evidence-backed
  (merged / cherry-landed / merged-PR tip / content-superseded).
  Remaining work: ~98 survivor branches with real deltas are takeover
  material, familied above for kwavers/ritk/coeus/apollo; per-item
  takeover increments, not a sweep.
- Settings done 2026-08-26 (user-authorized): delete_branch_on_merge=true
  on all 26 members; allow_auto_merge=true on 25/26 — leoneuro-rs
  declines auto-merge (plan/visibility limit), enqueue falls back to
  merge-on-green there.
- Status: in-progress (mechanical phase done stack-wide; survivor takeovers unclaimed, closest-to-done-first)

