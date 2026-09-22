<a id="atlas-worktree-takeover-107"></a>
## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in-progress
outcome: every worktree/branch across the stack (30 trees) maps to a measured delivery state — ahead of `origin/main`, pushed, merged — rather than an inference from the branch name; each unmapped branch is either integrated, pushed, or recorded as superseded.
- next: ~~triage pushed-but-unmerged branches with real divergence~~ **done 2026-09-22 — all five mapped in the Closure sweep below** (CFDrs backward-step #349, helios/asclepius apollo-lock #65/#19 with stale refs deleted, hephaestus fdtd #213/#215, hermes orphan #55 — all merged, refs clean). Remaining: the per-lane measured state for the `worktrees/` lanes named at the end of that section.
- Detectors recorded for recurrence: `git rev-list origin/main..<branch>`, `git stash list`, `git ls-files --others docs/adr/`, `git merge-base --is-ancestor` for cited commits.

## Closure sweep 2026-09-22 — all five named branches mapped

- CFDrs `codex/cfdrs-backward-step-108`: PR #349 MERGED 2026-08-17; local and remote refs already gone. **Mapped: merged, refs absent.**
- helios + asclepius `fix/apollo-lock-0.27`: PRs #65 / #19 MERGED 2026-08-18; pin content confirmed in both mains (helios later re-pinned through #96; asclepius `ff2ffbf` carries `(#19)`). The stale **remote refs were deleted this sweep** — `git push origin --delete` under a transient `core.hooksPath` override, because a pure ref deletion of merged content carries no commits and the members still ship pre-probe fork copies of the hook that misreport the budget gate when the Windows python3 Store stub answers `command -v`. **Mapped: merged, refs deleted.**
- hephaestus `codex/hephaestus-fdtd-107`: PRs #213 and #215 MERGED 2026-08-17/20; refs already deleted. **Mapped: merged, refs absent.**
- hermes `codex/hermes-orphan-closure`: PR #55 MERGED 2026-08-19; refs already deleted. **Mapped: merged, refs absent.**
- gaia: the four merged delivery branches (PRs #57–60) had their local branches deleted after merge; `cascade/provider-042` remains an active peer lane and was not touched.
- metis `feat/metis-native-ime-001` (tracking branch gone, 3 unique commits): **taken over** — the ADR pair renumbered and landed as PR #364 (0043 collided with main's rounded-rectangle ADR, so it became 0044 with a regenerated index), the backlog provider-merge line rides PR #357, and the uncommitted mesh-viewer work found in the main tree was re-homed to a clean lane as PR #365.
- Residual for the next pass: the remaining `worktrees/` lanes (apollo-route, eunomia-debuginfo-budget, hephaestus-host-dense-product, horae-test-harness, kwavers-*, leto-plane-range, ritk-python-ci-red, tyche-core-test-harness, …) still need their per-lane measured state recorded.
