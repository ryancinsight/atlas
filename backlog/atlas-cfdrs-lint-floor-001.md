<a id="atlas-cfdrs-lint-floor-001"></a>
## ATLAS-CFDRS-LINT-FLOOR-001 — Adopt canonical Atlas lint floor in CFDrs workspace [patch] — in-progress

- Owner: current session; scope: `repos/CFDrs/Cargo.toml` top-level
  `[workspace.lints]` block and per-site `#[expect]` ratchet insertions
  across `crates/cfd-*/src/**` and `xtask/src/**`.  Claimed 2026-08-06.
- Outcome: CFDrs `Cargo.toml` carries the canonical Atlas `[workspace.lints]`
  floor matching `repos/apollo/Cargo.toml` L88-L107 (template SSOT):
  `[workspace.lints.rust] missing_docs = "warn"` (warn floor; `#![deny(missing_docs)]`
  is the per-crate strict escalation choice, not set workspace-wide so existing
  crates without missing-docs discipline stay warning-only until per-crate
  promotion). `[workspace.lints.clippy]` adopts apollo's `all = warn, prio -1` +
  `pedantic = warn, prio -1` and the same `allow` set (`module_name_repetitions`,
  `must_use_candidate`, `similar_names`, `too_many_lines`,
  `default_constructed_unit_structs`, `doc_lazy_continuation`,
  `needless_range_loop`, `too_many_arguments`, `manual_is_multiple_of`,
  `manual_div_ceil`, `manual_slice_size_calculation`, `len_zero`,
  `cast_possible_truncation`, `cast_precision_loss`, `cast_sign_loss`,
  `cast_possible_wrap`, `items_after_statements`, `range_minus_one`,
  `default_trait_access`, `useless_conversion`). Adds the Atlas-canonical library
  hygiene `deny` tier (`unwrap_used`, `print_stderr`, `print_stdout`,
  `dbg_macro`) so consumer-tree library and CLI crates enforce the same floor
  kwavers/helios/apollo already carry — `#[expect]` permitting pre-existing
  sites to remain on a non-increasing ratchet baseline, not silent `allow`.
- Scope: idempotent bulk `#[expect(lint, reason="ratchet cfd-<crate>-<count>")]`
  insertion per violation emitted by `cargo clippy --all-targets
  --workspace --json -- -D warnings -W clippy::pedantic
  -W clippy::unwrap_used -W clippy::print_stderr -W clippy::print_stdout
  -W clippy::dbg_macro`. **Mechanical transform only** per `git_discipline`:
  no logic edits, no refactor, no removed `println!` from `xtask` at large —
  per-site `#[expect]` carries the ratchet signal for future root-cause work.
- Non-goals: no public-API rewrites, no `print!` removal from `xtask` source
  (xtask is a build tool, not a library; per-site `#[expect]` preserves the
  ratchet signal per `engineering_gates` brownfield rule), no logic fixes for
  surfaced `unwrap_used` (the ratchet baseline only decreases — a future
  root-cause slice removes the offending `unwrap` and its `#[expect]` together).
- Disjoint from peer's `ATLAS-CFDRS-ATHENA-MIGRATION-001` chain.rs scope:
  peer's last chain.rs touch was 2026-07-30 (`63e49604`); 7+ days stale,
  reclaimable takeover material. Converge-friendly by construction — `#[expect]`
  is semantics-preserving against any in-flight peer chain.rs work; if peer
  pushes new chain.rs commits during this slice, fall through `concurrent_agents`
  Detect-and-reconcile (compose around peer's diff).
- Lane: reclaimed per-repo 2-tree cap slot by removing the post-merge
  `codex/cfdrs-audit-refresh` worktree lane (peer's PR #327 fully merged at
  `50fa243b`, lane = `D:/atlas/worktrees/CFDrs-audit-refresh` exactly at peer's
  merged tip, tree clean) and adding `feat/cfdrs-lint-floor` lane off
  `origin/main 50fa243b`.
- Acceptance: `cargo clippy --all-targets --workspace -- -D warnings
  -W clippy::pedantic -W clippy::unwrap_used -W clippy::print_stderr
  -W clippy::print_stdout -W clippy::dbg_macro` rc=0; `cargo nextest run
  --workspace` rc=0 (or reduced focused subset if workspace test suite
  budget blocked per `engineering_gates` runtime budgets — root-cause
  any hang, never bypass); `cargo test --doc --workspace` rc=0; `cargo fmt
  --all --check` rc=0.
- Re-open trigger: a new lint violation reaches `repos/CFDrs/origin/main`
  past the floor without an accompanying `#[expect]` carrying its ratchet
  rationale; or the floor is removed/relaxed in `Cargo.toml`.
- Residual recorded, NOT closed in this slice: per-repo `backlog.md` and
  `gap_audit.md` entries for CFDrs lint-floor closure; CFDrs-level
  per-crate `#![deny(missing_docs)]` promotion is deferred to a later
  per-crate slice (each crate's surface decides its own missing-docs tier).
- Current CFDrs increment: commit `cd9580fc` on pushed branch
  `feat/cfdrs-lint-floor` wires every workspace package and `xtask` to the
  floor, removes the cfd-core plugin resolver unwrap, and records the local
  PM state. Evidence: focused `xtask` and cfd-core library Clippy pass;
  cfd-core Nextest 246/246; cfd-core doctests 3/3; explicit migration audit
  reports zero legacy dependencies, zero legacy source tokens, and a clean
  allowlist. Full workspace acceptance remains open on the recorded
  cfd-math, cfd-schematics, cfd-core test/bench, and format debt.
- Follow-up CFDrs commit `e3e88a60` is pushed on the same branch: multigrid
  coarsening now uses deterministic NaN-safe ordering, with a value-semantic
  regression test. cfd-math Nextest passes 198/198; focused cfd-math library
  Clippy residue decreases from 51 to 48 diagnostics.
- Follow-up CFDrs commit `f31176b1` is pushed: multigrid hierarchy and
  interpolation state use invariant-checked expectations, while JFNK and
  spectral kernels centralize C-contiguous storage assumptions. cfd-math
  Nextest remains 198/198; focused library Clippy residue is 22 diagnostics.
- Follow-up CFDrs commit `9e52454a` is pushed: performance-monitor mutex and
  calibration output now use invariant diagnostics and tracing, and DG progress
  output is structured tracing. cfd-math library Clippy and Nextest pass;
  workspace closure still has cfd-schematics, cfd-core test/bench, and format
  debt.
- Follow-up CFDrs commit `c83affee` is pushed: the exported
  `cfd-schematics::topology::model` contract now documents its types, fields,
  variants, aliases, and lookup methods. cfd-schematics library Nextest passes
  164/164 and doctests 16/16; package Clippy residue decreases 712 to 611.
- Follow-up CFDrs commits `ddc04a32` and `8584dd26` are pushed: configuration
  constants, public config manifests, and the route-spec contract now carry
  API documentation. cfd-schematics library Nextest remains 164/164 and
  doctests 16/16; package Clippy residue decreases 611 to 534.
- Follow-up CFDrs commit `322787ae` is pushed: the public node and channel
  geometry-builder setters now carry API documentation. cfd-schematics library
  Nextest remains 164/164 and doctests 16/16; package Clippy residue decreases
  534 to 524.
- Follow-up CFDrs commit `eae43768` is pushed: geometry-generator metadata,
  entry points, and builder methods now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; package Clippy residue
  decreases 524 to 508.
- Follow-up CFDrs commit `c0d53bd5` is pushed: series and parallel geometry
  generators now carry API documentation. cfd-schematics library Nextest
  remains 164/164 and doctests 16/16; this slice reduces its package Clippy
  residual from 508 to 506. The working tree reports 492 with peer-owned
  `analysis_impl.rs` documentation changes also present and uncommitted.
- Follow-up CFDrs commit `f27f86dd` is pushed: selective-tree path, topology,
  request, and generator contracts now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; this slice reduces the
  package Clippy residual from 506 to 468. The working tree reports 454 with
  the peer-owned `analysis_impl.rs` documentation changes still uncommitted.
- Follow-up CFDrs commit `468cc617` is pushed: the `NetworkBlueprint` analysis
  impl (`crates/cfd-schematics/src/domain/model/blueprint/analysis_impl.rs`)
  now carries inline Rustdoc for its 14 undocumented pub methods (node/pipe
  counters, length aggregates, Venturi lookup, overlap analysis/resolution,
  validate, describe). cfd-schematics library Nextest remains 164/164 and
  doctests 16/16. File-disjoint from peer commits on the same branch per
  `concurrent_agents` disjoint-scope rule; peer's prior bullet had already
  flagged this `analysis_impl.rs` work as the uncommitted peer residual, and
  the slice now closes that residual. cfd-schematics distinct missing_docs
  sites in `analysis_impl.rs` fall from 14 to 0; crate-wide distinct
  sites fall from 468 to 454.
- Follow-up CFDrs commit `357debf3` is pushed: the `NetworkBlueprint`
  metadata impl (`crates/cfd-schematics/src/domain/model/blueprint/metadata_impl.rs`)
  now carries inline Rustdoc for its 19 undocumented pub methods/associated
  functions covering the deprecated default constructor, the
  explicit-position constructor, render-hint and metadata builders/accessors,
  topology and lineage attachments, JSON (de)serialization, and
  node/channel addition methods. cfd-schematics library Nextest remains
  164/164 and doctests 16/16. File-disjoint sibling of the just-merged
  analysis_impl.rs closure in the same `domain/model/blueprint/` subtree,
  owned by this session; no peer commits touched this file.
  cfd-schematics distinct missing_docs sites in `metadata_impl.rs` fall
  from 19 to 0; crate-wide distinct sites fall from 454 to 435.

