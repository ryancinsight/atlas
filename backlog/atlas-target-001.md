<a id="atlas-target-001"></a>
## ATLAS-TARGET-001 — One build cache, one debug budget [patch] — in-progress (residual)

- owner: Codex `/root`. scope: cache trees/profile sections only, no
  simulation logic. outcome: one shared `target/` cache stack-wide,
  dev/test debuginfo aligned to line-tables-only/deps-none, no wildcard dev
  opt-level overrides — delivered for root config, moirai, kwavers (PR #307).
- residual: audit remaining `[profile.*]`/`.cargo` sections (helios,
  hermes, CFDrs, coeus, ritk, mnemosyne). CFDrs's `opt-level = 2` test
  profile is under a dirty peer workspace — re-open once peer work lands.
- next: atlas-meta root worktrees copy `.cargo/config.toml`, resolving a
  lane-local target — run meta-tool verification from the primary root
  until a portable route exists; a jobs cap needs single- vs
  concurrent-build comparison (23 concurrent `rustc` seen on a 24-thread
  host — oversubscription exposure, not a cap yet).
