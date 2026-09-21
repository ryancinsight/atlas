<a id="atlas-worktree-takeover-107"></a>
## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in-progress
outcome: every worktree/branch across the stack (30 trees) maps to a measured delivery state — ahead of `origin/main`, pushed, merged — rather than an inference from the branch name; each unmapped branch is either integrated, pushed, or recorded as superseded.
- next: triage pushed-but-unmerged branches with real divergence, each needing its owner or a PR check rather than a takeover — CFDrs `codex/cfdrs-backward-step-108` (99 ahead), helios & asclepius `fix/apollo-lock-0.27` (3/2 ahead, coordinated cross-repo lock sweep), hephaestus `codex/hephaestus-fdtd-107`, hermes `codex/hermes-orphan-closure`.
- Detectors recorded for recurrence: `git rev-list origin/main..<branch>`, `git stash list`, `git ls-files --others docs/adr/`, `git merge-base --is-ancestor` for cited commits.
