<a id="atlas-branch-inventory-001"></a>
## ATLAS-BRANCH-INVENTORY-001 - Burn down stack branch inventories [git-hygiene] [patch] — in-progress

outcome: every member's local branches map to an open item or enqueued PR (orient rule); merged/gone-upstream branches prune mechanically, unmerged survivors salvage via takeover per content-supersession (not just patch-id).

Mechanical phase closed stack-wide 2026-08-26: ~236 branches deleted across 26 members, each evidence-backed (merged / cherry-landed / merged-PR tip / content-superseded). `delete_branch_on_merge=true` set on all 26 members; `allow_auto_merge=true` on 25/26 (leoneuro-rs declines: plan/visibility limit, falls back to merge-on-green).

next: ~98 survivor branches with real deltas remain takeover material, closest-to-done-first — kwavers (35 refs: 8 PR-scratch, 5 merged-PR leftovers, 7 recent seams/docs/ci, 12 codex/* WIP incl. aequitas family), ritk (17 refs: 5 merged-PR tails, 4 large Aug WIP, 8 small fixes), coeus (17, incl. coeus-frobenius provider/cherry/rebase/v2 family to consolidate), apollo (12), and ~21 other members. Per-item takeover increments, not a sweep.

apollo classified 2026-09-20 (11 remote branches with no open PR). Verified
here, deletable, pending the remote-delete permission: `ci/sync-stack-hooks-0918`
(`main`'s `.githooks/pre-push` is a strict superset of it -- every line the
branch adds plus the deny, artifact-budget and rustdoc sections) and
`codex/apollo-fft-hephaestus-cutover` (`7e56b332`, a board claim touching only
`backlog.md` and `checklist.md`). A sweep classifier called five more
superseded -- `cascade/hermes-07`, `fix/apollo-large-composite-wiring` (both
claimed landed as `d585e0f5`), `codex/apollo-arch-006-junk-drawer-rename`,
`perf/apollo-batched-parallel`, `perf/apollo-planar-staged-transpose` -- but
its stated reason for `perf/apollo-batched-parallel` (a revert of nextest
config) does not match that branch's diff at all, which is a board and bench
change, so none of the five is deletable on that evidence. Four were called
unique and are takeover material closest-to-done-first:
`perf/apollo-f32-rader-narrowing` (5 commits, a breaking `dft_inverse`
accumulation fix in `T`), `codex/fix-apollo-package-sources` (8),
`feat/apollo-benchmark-generator` (2, restores dropped lint floors),
`style/apollo-butterfly-lint-consolidation-217` (1). Three local branches
whose content had landed under new SHAs were deleted: `feat/apollo-fft-2d-axis`
(`f942140b`, landed as `4ffb3d4a`; `git range-diff` shows only context drift),
`feat/apollo-fft-normalization` (`6674f1dd`) and
`perf/apollo-mem-radix2-split-conj` (`94ff56ca`), the last two all-`-` under
`git cherry origin/main`.

