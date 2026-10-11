<a id="atlas-member-wip-20261010-metis"></a>
## ATLAS-MEMBER-WIP-20261010-METIS — Triage metis's uncommitted checkout work [patch] — todo
outcome: every uncommitted hunk in `repos/metis` is committed on a metis branch or proven landed, and the checkout state is recorded.
background: 2026-10-10 sweep found the metis checkout on `build/metis-deps-20261007` (`45cbe2bd`) with +686/−16 to `scripts/python_native_capture.py`, `scripts/python_native_input_capture.py`, and its test; upstream default has moved to `ce47b2b2`. Moirai's untracked PRD/WASM docs were relocated to session scratch, not deleted.
acceptance: `git -C repos/metis status --porcelain` is empty or cites the preserving branch; no hunk is lost.
priority: correctness
needs: none
scope: repos/metis
next: inspect the diff hunk-by-hunk against `origin/main` and commit or close per fix-forward.
basis: atlas `afbbcd5f1`; metis checkout `45cbe2bd`, latest `ce47b2b2`.
