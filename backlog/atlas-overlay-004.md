<a id="atlas-overlay-004"></a>
## ATLAS-OVERLAY-004 — Worktree sprawl breaks stack dependency resolution [patch] — in-progress

- owner: unclaimed. scope: `worktrees/`, root and 13 lane-local
  `.cargo/config.toml` files — not the lane branches' source.
- outcome/acceptance: `cargo check -p kwavers-physics` resolves; `git
  worktree list` per repo within the one-main-plus-one-lane bound; no
  lane-local config re-declares `target-dir`/`[patch]`.
- resolved 2026-07-28: orphaned `worktrees/aequitas` linked worktree removed
  (byte-identical to `repos/aequitas`), clearing a `smallvec` collision.
- next: 13 lane-local configs still fork resolution by re-declaring
  `target-dir`/`[patch]` (stack root is sole owner, performance_engineering);
  `worktrees/` holds 28 entries over-bound (5 repos have two-plus).
- Ask-User gate: deleting other agents' lane directories needs confirmation
  first — possibly-live peer setups.
