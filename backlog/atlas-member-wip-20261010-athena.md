<a id="atlas-member-wip-20261010-athena"></a>
## ATLAS-MEMBER-WIP-20261010-ATHENA — Triage athena's uncommitted checkout work [patch] — todo
outcome: every uncommitted hunk in `repos/athena` is committed on an athena branch or proven landed, and the checkout state is recorded.
background: 2026-10-10 sweep found the athena checkout on `main` (`12d78d08`) with mods to krylov/preconditioner/lib/exports, two example updates, and untracked `preconditioner/multigrid/` + `preconditioner/saddle/` trees; upstream default has moved 18 commits to `ced71f59`.
acceptance: `git -C repos/athena status --porcelain` is empty or cites the preserving branch; no hunk is lost.
priority: correctness
needs: none
scope: repos/athena
next: inspect the diff hunk-by-hunk against `origin/main` and commit or close per fix-forward.
basis: atlas `afbbcd5f1`; athena checkout `12d78d08`, latest `ced71f59`.
