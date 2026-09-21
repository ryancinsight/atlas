<a id="atlas-worktree-001"></a>
## ATLAS-WORKTREE-001 — Canonical lane root consolidation [patch] — in-progress
- **outcome:** every repo's worktree lanes sit under the canonical `D:\atlas\worktrees/` root, within the main-tree-plus-one-lane bound.
- **open:** `scripts/atlas-lane-audit.py` (2026-08-19) reports four topology violations outstanding — Consus (4 trees + 1 lane outside canonical root), Kwavers (4 trees), RITK (4 trees); extra lanes are active peer scopes or dirty, waiting on those streams completing.
- **owner:** Codex `/root` (stale-claim takeover 2026-07-22).
