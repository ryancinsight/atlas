<a id="atlas-member-wip-20261010-apollo"></a>
## ATLAS-MEMBER-WIP-20261010-APOLLO — Triage apollo's uncommitted checkout work [patch] — todo
outcome: every uncommitted hunk in `repos/apollo` is committed on an apollo branch or proven landed, and the checkout state is recorded.
background: 2026-10-10 sweep found the apollo checkout on `build/deps-20261008` (`f213a24e8`) with staged/unstaged mods to CHANGELOG.md, backlog.md, and 8 source files (czt/dctdst/dht typed plans, fft contracts/metadata) plus untracked content; upstream default has since moved to `87932df4`.
acceptance: `git -C repos/apollo status --porcelain` is empty or cites the preserving branch; no hunk is lost.
priority: correctness
needs: none
scope: repos/apollo
next: inspect the diff hunk-by-hunk against `origin/main` and commit or close per fix-forward.
basis: atlas `afbbcd5f1`; apollo checkout `f213a24e8`, latest `87932df4`.
