<a id="atlas-worktree-takeover-107"></a>
## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in-progress
outcome: every worktree/branch across the stack (30 trees) maps to a measured delivery state — ahead of `origin/main`, pushed, merged — rather than an inference from the branch name; each unmapped branch is either integrated, pushed, or recorded as superseded.
- Detectors recorded for recurrence: `git rev-list origin/main..<branch>`, `git stash list`, `git ls-files --others docs/adr/`, `git merge-base --is-ancestor` for cited commits.
- gaia: the four merged delivery branches (PRs #57–60) had their local branches deleted after merge; `cascade/provider-042` remains an active peer lane and was not touched.
- metis `feat/metis-native-ime-001` (tracking branch gone, 3 unique commits): **taken over** — the ADR pair renumbered and landed as PR #364 (0043 collided with main's rounded-rectangle ADR, so it became 0044 with a regenerated index), the backlog provider-merge line rides PR #357, and the uncommitted mesh-viewer work found in the main tree was re-homed to a clean lane as PR #365.
- next: the remaining `worktrees/` lanes (apollo-route, eunomia-debuginfo-budget, hephaestus-host-dense-product, horae-test-harness, kwavers-*, leto-plane-range, ritk-python-ci-red, tyche-core-test-harness, …) still need their per-lane measured state recorded.
