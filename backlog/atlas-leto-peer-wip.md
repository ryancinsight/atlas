<a id="atlas-leto-peer-wip"></a>
## ATLAS-LETO-PEER-WIP — Leto uncommitted peer WIP [patch] — blocked (peer-owned)

- Owner: peer session (codex); scope: `repos/leto/crates/leto-ops/`, `repos/leto/Cargo.toml`, branch `codex/leto-real-sparse-lu`.
- Contains a new Legendre polynomial module (`special_legendre.rs`, 3 tests), a `Cargo.toml` path-dep overlay patch, `special.rs` formatting, module-tree updates, and a `bessel_k0` tolerance fix; 425 leto-ops tests pass.
- **Blocker:** peer-owned; not committed by this session per concurrent_agents policy.
- **Re-open trigger:** the peer lands the branch, or the one-hour stale-claim sweep finds no board/commit update — then reclaim the scope and complete the integration from the committed branch state.
