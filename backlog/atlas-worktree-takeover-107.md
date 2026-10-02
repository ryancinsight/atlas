<a id="atlas-worktree-takeover-107"></a>
## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — todo
outcome: every worktree/branch across the stack (30 trees) maps to a measured delivery state — ahead of `origin/main`, pushed, merged — rather than an inference from the branch name; each unmapped branch is either integrated, pushed, or recorded as superseded.
detectors recorded for recurrence: `git rev-list origin/main..<branch>`, `git stash list`, `git ls-files --others docs/adr/`, `git merge-base --is-ancestor` for cited commits.
residual for the next pass: the remaining `worktrees/` lanes (apollo-route, eunomia-debuginfo-budget, hephaestus-host-dense-product, horae-test-harness, kwavers-*, leto-plane-range, ritk-python-ci-red, tyche-core-test-harness, …) still need their per-lane measured state recorded.
