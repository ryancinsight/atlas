<a id="atlas-branch-inventory-001"></a>
## ATLAS-BRANCH-INVENTORY-001 - Burn down stack branch inventories [git-hygiene] [patch] — in-progress

outcome: every member's local branches map to an open item or enqueued PR (orient rule); merged/gone-upstream branches prune mechanically, unmerged survivors salvage via takeover per content-supersession (not just patch-id).

Mechanical phase closed stack-wide 2026-08-26: ~236 branches deleted across 26 members, each evidence-backed (merged / cherry-landed / merged-PR tip / content-superseded). `delete_branch_on_merge=true` set on all 26 members; `allow_auto_merge=true` on 25/26 (leoneuro-rs declines: plan/visibility limit, falls back to merge-on-green).

next: ~98 survivor branches with real deltas remain takeover material, closest-to-done-first — kwavers (35 refs), ritk (17), coeus (17, incl. the coeus-frobenius family to consolidate), apollo (11, classified below), and ~21 other members. Per-item takeover increments, not a sweep.

apollo, 2026-09-20: of 11 remote branches with no open PR, two are verified
deletable and await the remote-delete permission — `ci/sync-stack-hooks-0918`
(main's hook is a strict superset) and `codex/apollo-fft-hephaestus-cutover`
(a board claim only). A sweep called five more superseded on a rationale that
does not match one of their diffs, so those stay. Four are takeover material,
closest to done first: `perf/apollo-f32-rader-narrowing` (5 commits, breaking
`dft_inverse` accumulation in `T`), `codex/fix-apollo-package-sources` (8),
`feat/apollo-benchmark-generator` (2), `style/apollo-butterfly-lint-consolidation-217` (1).
