<a id="atlas-worktree-takeover-107"></a>
## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in-progress
outcome: every worktree/branch across the stack (30 trees) maps to a measured delivery state — ahead of `origin/main`, pushed, merged — rather than an inference from the branch name; each unmapped branch is either integrated, pushed, or recorded as superseded.
- next: record the remaining per-lane measured state for the `worktrees/` lanes; completed branch mappings remain in git history.
- Detectors recorded for recurrence: `git rev-list origin/main..<branch>`, `git stash list`, `git ls-files --others docs/adr/`, `git merge-base --is-ancestor` for cited commits.
