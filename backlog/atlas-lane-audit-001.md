<a id="atlas-lane-audit-001"></a>
## ATLAS-LANE-AUDIT-001 — Lane-root sweep results and residuals [patch] — in-progress (residual)
- outcome: `D:\atlas\worktrees` holds only compliant lanes (created by `git worktree add`, canonical root, two-tree bound per repo); no gitdir-mirror checkouts, standalone clones, or stale lanes remain.
- policy: AGENTS.md git_discipline Worktrees + concurrent_agents (gitdir-mirror checkouts prohibited — a `.git` file pointing at another tree's gitdir shares its index and corrupts both trees' status).
- state (2026-08-17): the completed CFDrs Fourier/SSOR and Apollo public-plan lanes were removed after their PRs merged. The only remaining violation is `worktrees/kwavers-doc557`, detached at commit `df818b9a1` — clean but not on a named branch.
- next: no branch switch or lane deletion is authorized until the lane's owner reconciles the documentation run; re-audit after that lands.
