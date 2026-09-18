<a id="atlas-worktree-clones-001"></a>
## ATLAS-WORKTREE-CLONES-001 — Reconcile standalone clones under `worktrees/` [patch] — in-progress

- **outcome:** no standalone clone remains under `worktrees/`; every member stays at or under the two-tree bound.
- **Status 2026-09-02:** delivered except one residual — `worktrees/kwavers-log` is an empty folder skeleton (0 files) left by a removed lane; its `crates/kwavers-python/.pytest_cache` is held open by five live peer processes and refuses deletion.
- **next:** once those handles release (or the peer session ends), `rm -rf worktrees/kwavers-log`; the lane audit then reads 0, closing this item and `ATLAS-LANE-AUDIT-001`.
- **Non-goal:** touching genuine linked worktrees.
