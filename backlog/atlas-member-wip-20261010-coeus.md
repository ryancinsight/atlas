<a id="atlas-member-wip-20261010-coeus"></a>
## ATLAS-MEMBER-WIP-20261010-COEUS — Triage coeus's uncommitted checkout work [patch] — todo
outcome: every uncommitted hunk in `repos/coeus` is committed on a coeus branch or proven landed, and the checkout state is recorded.
background: 2026-10-10 sweep found the coeus checkout on `main` (`89cb08b0`) with wide mods (CHANGELOG, Cargo.toml, backlog, autograd/node/ops/nn sources; `gradcheck.rs` and activation `math.rs` deleted, ~1.2 k lines removed) plus untracked content; upstream default has moved to `1a961ed7`.
acceptance: `git -C repos/coeus status --porcelain` is empty or cites the preserving branch; no hunk is lost; deletions are reviewed, not bulk-restored.
priority: correctness
needs: none
scope: repos/coeus
next: inspect the diff hunk-by-hunk against `origin/main` and commit or close per fix-forward.
basis: atlas `afbbcd5f1`; coeus checkout `89cb08b0`, latest `1a961ed7`.
