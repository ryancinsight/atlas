<a id="atlas-member-wip-20261010-leto"></a>
## ATLAS-MEMBER-WIP-20261010-LETO — Triage leto's uncommitted checkout work [patch] — todo
outcome: every uncommitted hunk in `repos/leto` is committed on a leto branch or proven landed, and the checkout state is recorded.
background: 2026-10-10 sweep found the leto checkout on `main` (`9c9e779d`, = origin/main) with mods to ci.yml, CHANGELOG, backlog, linalg kernels (eigen/lu/matrix/svd/symmetric_qr), volume, cache, and a volume test plus untracked content.
acceptance: `git -C repos/leto status --porcelain` is empty or cites the preserving branch; no hunk is lost.
priority: correctness
needs: none
scope: repos/leto
next: inspect the diff hunk-by-hunk against `origin/main` and commit or close per fix-forward.
basis: atlas `afbbcd5f1`; leto checkout `9c9e779d` (= latest).
