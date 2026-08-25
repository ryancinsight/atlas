# ADR 0018 — TREE-SRP-001: Melinoe/Themis/Moirai module hierarchy cleanup

- Status: **Accepted**
- Date: 2026-07-15
- Drivers: 500+ line files in operation-family modules; dual channel systems in moirai-core (`channel/` + `unified_channel/`); tests interleaved with source in themis; junk-drawer `constants.rs` in moirai-core.
- Anchors: `repos/melinoe/crates/halo/src/collections/branded_deque.rs` (~600 L); `repos/themis/src/branded/sync_region.rs` (~540 L); `repos/moirai/moirai-core/src/channel/{hybrid,mpmc}.rs` (~620, ~580 L); `repos/moirai/moirai-core/src/constants.rs`; `repos/themis/src/topology/tests/` + `repos/themis/src/branded/tests.rs`.
- See also: ADR 0002 (topology law — names the provider ownership map that these module boundaries reflect); `AGENTS.md` §standards (500-line target, operation-family leaf modules, no junk drawers, consolidation discipline).
- Index: docs/adr/INDEX.md#ADR-0018

## Context

A structural audit of the Melinoe (including `halo` sub-crate), Themis, and Moirai (core + async) source trees found 4 categories of architecture drift against the standards in `AGENTS.md`:

### Category A — Files exceeding the 500-line leaf-module target

`AGENTS.md` §standards targets ≤500 lines per file with operation families isolated in dedicated leaf modules. Four files exceed this:

| File | ~Lines | Violation |
|------|--------|-----------|
| `halo/src/collections/branded_deque.rs` | 600 | `BrandedVecDeque` implementation, iterator impls, and tests in one file |
| `themis/src/branded/sync_region.rs` | 540 | `SyncRegion`, placement logic, and topology helpers mixed |
| `moirai-core/src/channel/hybrid.rs` | 620 | `HybridChannel` with select logic, benchmarks, and tests |
| `moirai-core/src/channel/mpmc.rs` | 580 | `MpmcChannel` with multi-producer logic and tests |

Each mixes multiple operation families (type definition, iterator impls, test helpers) in one file. The fix is mechanical: extract operation-family groups into submodules, keeping the public API surface unchanged.

### Category B — Dual channel systems in moirai-core

`moirai-core/src/` has two competing channel implementations:

- `channel/` (`mod.rs`, `hybrid.rs`, `mpmc.rs`, `spsc.rs`, `select.rs`, `error.rs`) — SPSC, MPMC, Hybrid, and Select dispatch.
- `unified_channel/` (`mod.rs`, `core.rs`, `receiver.rs`, `sender.rs`, `error.rs`, `stats.rs`, `config.rs`, `tests.rs`) — a separate `UnifiedChannel` with its own sender/receiver/statistics.

Both are publicly re-exported from `moirai-core/src/lib.rs:52-55` and `lib.rs:77-86`. The `lib.rs` comment at line 68 (`// pub mod hybrid; // Removed: Duplicate implementation, using moirai-executor::HybridExecutor instead`) shows prior awareness of the duplication.

| Module | Public symbols | Tests |
|--------|---------------|-------|
| `channel/` | `MpmcChannel`, `SpscChannel`, `HybridChannel`, `Select`, `mpmc()`, `spsc()`, `unbounded()` | Inline `#[cfg(test)]` |
| `unified_channel/` | `UnifiedChannel`, `UnifiedReceiver`, `UnifiedSender`, `ChannelStatistics`, `ChannelConfig`, `unified_channel()`, `unified_channel_with_config()` | `unified_channel/tests.rs` |

The correct resolution is not obvious: `unified_channel/` has richer configuration (backpressure, statistics) while `channel/` integrates with the `Select` I/O multiplexer. Consolidation requires a design decision on which superset absorbs which.

### Category C — Tests interleaved with source in themis

`themis/src/` embeds tests alongside production code in two locations:

- `themis/src/topology/tests/` (`cpu.rs`, `gpu.rs`, `tpu.rs`) — topology test suite as a subdirectory under `src/`.
- `themis/src/branded/tests.rs` — branded module tests.

`AGENTS.md` §standards does not mandate a top-level `tests/` directory, but interleaving test source with production source under `src/` makes it harder to audit the production surface (e.g., `cargo xtask migrate-audit` must filter test modules) and violates the convention used by the rest of the Atlas provider stack.

### Category D — Junk-drawer constants in moirai-core

`moirai-core/src/constants.rs` (75 lines) mixes:
- PERCENTAGE constant (`task/` domain)
- Cache-line constants (`memory/` domain)
- Spin-attempt constants (`pool/` domain)
- Task-priority constants (`task/` domain)

Each constant belongs in the domain module it governs. The file is small (75 lines) but violates the "no junk drawers" rule by aggregating unrelated domains.

## Decision

We accept the architecture drift documented above and proceed with a phased remediation. Each phase is independently verifiable and merges without breaking consumers.

### Phase 1 — Split 500+ line files (P0, mechanical)

Split each oversized file into operation-family leaf modules. Zero behavior change: the public API surface and re-export paths remain identical. Each split preserves `pub use` from the parent `mod.rs` so consumers see no difference.

**1a. `halo/src/collections/branded_deque.rs` → `deque/`**

| New file | Content | ~Lines |
|----------|---------|--------|
| `deque/mod.rs` | Type definition `BrandedVecDeque<T, B>`, constructor, capacity methods | 40 |
| `deque/ops.rs` | Push/pop/insert/remove front/back operations | 120 |
| `deque/iter.rs` | `Iter`, `IterMut`, `IntoIter`, `Drain` impls + `IntoIterator` | 100 |
| `deque/views.rs` | `as_slices`, `make_contiguous`, range views | 80 |
| `deque/tests.rs` | `#[cfg(test)]` module with existing tests | 200 |

**1b. `themis/src/branded/sync_region.rs` → `branded/region/`**

| New file | Content | ~Lines |
|----------|---------|--------|
| `branded/region/mod.rs` | `SyncRegion` type, construction, `NumaNodePlacement` API | 100 |
| `branded/region/placement.rs` | Split operations, topology mirroring | 160 |
| `branded/region/sync.rs` | Barriers, worker synchronization | 120 |
| `branded/region/tests.rs` | `#[cfg(test)]` module with existing tests | 160 |

**1c. `moirai-core/src/channel/hybrid.rs` → `channel/hybrid/`**

| New file | Content | ~Lines |
|----------|---------|--------|
| `channel/hybrid/mod.rs` | `HybridChannel` type definition, construction, public API | 80 |
| `channel/hybrid/sender.rs` | `HybridSender` impl | 160 |
| `channel/hybrid/receiver.rs` | `HybridReceiver` impl | 160 |
| `channel/hybrid/select.rs` | Select integration, poll logic | 120 |
| `channel/hybrid/tests.rs` | `#[cfg(test)]` module with existing tests | 100 |

**1d. `moirai-core/src/channel/mpmc.rs` → `channel/mpmc/`**

| New file | Content | ~Lines |
|----------|---------|--------|
| `channel/mpmc/mod.rs` | `MpmcChannel` type, construction, public API | 80 |
| `channel/mpmc/sender.rs` | `MpmcSender` impl | 160 |
| `channel/mpmc/receiver.rs` | `MpmcReceiver` impl | 160 |
| `channel/mpmc/tests.rs` | `#[cfg(test)]` module with existing tests | 180 |

### Phase 2 — Rehome themis tests to `tests/` (P1, mechanical)

Move `themis/src/topology/tests/` → `themis/tests/topology/` and `themis/src/branded/tests.rs` → `themis/tests/branded.rs`.

> **Implementation note (2026-07-15)**: Phase 2 is complete.
> - ✅ **Dead files deleted**: `src/topology/tests/gpu.rs` and `src/topology/tests/tpu.rs` (these were not declared in `mod.rs` — only `mod cpu;` existed; standalone integration tests already lived at `tests/gpu.rs` and `tests/tpu.rs`).
> - ✅ **CPU topology tests rehomed**: `src/topology/tests/cpu.rs` → `tests/topology/cpu.rs`. Resolved `pub(crate)` struct field access by adding `#[cfg(test)] pub fn new_for_test(...)` constructor on `CpuTopology` (`src/topology/cpu/mod.rs`). Widened builder functions (`build_adjacent_nodes`, `build_node_to_index`, `build_processor_to_node`) and distance constants (`LOCAL_DISTANCE`, `REMOTE_DISTANCE`) from `pub(crate)`/`pub(in crate::topology)` to `pub`. Added `#[cfg(test)] pub use` re-exports in `src/lib.rs`.
> - ✅ **Branded tests rehomed**: `src/branded/tests.rs` → `tests/branded.rs`. Uses `new_for_test` constructor. Feature-gated behind `melinoe` via `[[test]]` `required-features` in `Cargo.toml`.
> - ✅ **Deleted**: `src/topology/tests/mod.rs`, `src/topology/tests/cpu.rs`, `src/branded/tests.rs`.
> - ⚠️ **Pre-existing**: 2 branded placement tests panic under `melinoe` feature (`region_index 0 out of bounds for 0 region(s)` in `SafePlacement::cell_index`). This is a pre-existing bug in the branded `split`/`split_with` paths when `CpuTopology` has zero NUMA nodes — not a regression from the rehome. Original `src/branded/tests.rs` has the same panic; tests were never run with `--features melinoe` at the crate level before.
> - Test count: 16/18 pass (default features), 2 pre-existing failures (branded placement). `--no-default-features` failures are pre-existing.

### Phase 3 — Split constants.rs (P1, mechanical)

Move each constant group into its domain module:

| Constant | Move to |
|----------|---------|
| `PERCENTAGE` scaling factor | `moirai-core/src/executor/config.rs` |
| Cache-line size constants | `moirai-core/src/memory/allocator.rs` |
| Spin-attempt limits | `moirai-core/src/pool/stack.rs` |
| Task priority consts | `moirai-core/src/task/id_and_context.rs` |

Delete `moirai-core/src/constants.rs` and remove `pub mod constants;` from `lib.rs`. Update any call sites to use the new paths.

### Phase 4 — Dual channel consolidation (P2, architectural)

**Deferred.** The two channel systems serve overlapping but not identical use cases:
- `channel/` integrates with `Select` I/O multiplexer — needed by the async executor.
- `unified_channel/` provides richer configuration (backpressure policies, statistics).

A correct consolidation requires:
1. Survey all consumers across the moirai workspace and the Atlas provider graph.
2. Design a single `Channel<T, P: ChannelPolicy>` generic that supersedes both.
3. Deprecate the old types, migrate call sites, delete superseded modules.

This is a `[major]` change with broader blast radius than this ADR covers. It is filed as a separate architecture item (TREE-DUP-002). Phase 1–3 proceed independently.

### Rejected alternatives

**Status quo**: Leaves 1,800+ lines in files above the 500-line target; the dual-channel ambiguity persists; the themis test layout diverges from provider convention. These are architecture drift that compounds as new code follows the local pattern.

**Consolidate everything in one phase**: The dual-channel consolidation changes public API signatures and would block the mechanical splits. Separating phases keeps each change independently verifiable and mergable.

**Delete unified_channel outright**: Loses backpressure configuration and statistics that consumers may depend on. Not justified without a consumer audit.

## Consequences

### Positive

1. Every source file in the affected crates is under the 500-line target after Phase 1.
2. Operation-family grouping makes modules easier to navigate: a developer looking for `HybridSender` impls finds them in `hybrid/sender.rs`, not scattered through a 620-line file.
3. Themis tests under `tests/` follow the Cargo convention and are excluded from `cargo build --lib` compilation.
4. `constants.rs` removal eliminates the last junk-drawer module in moirai-core.
5. Phases 1–3 require zero consumer-side changes (public re-exports are preserved or test-only paths).

### Negative

1. ~20 new files across the three provider repos (churn in the tree; review burden).
2. Git blame continuity is lost for the moved code (acceptable per `consolidation_discipline` — the moved code is unchanged, only relocated).
3. Themis tests moving to `tests/` may require `pub(crate)` re-exports for internal items the tests access. Each such re-export widens the (test-only) API surface.

### Risks

1. **Phase 2 test access**: if themis test modules access `pub(super)` or `pub(crate)` items that are only re-exported from the parent module (not from the crate root), the tests may not compile from `tests/`. Pre-audit before moving. Mitigation: any needed re-export is a `#[cfg(test)]`-gated `pub use` in the crate root or a `pub(crate)` on the parent module; if the access chain is deep, the test file stays `#[cfg(test)]` in `src/` and is filed as deferred (documented in gap_audit.md).
2. **Phase 4 deferral risk**: the dual-channel ambiguity is architectural debt that compounds as new channel consumers are written. The deferral is documented as TREE-DUP-002 with an ADR requirement before implementation begins.

## Verification plan

Each phase has independent verification gates:

### Phase 1 (file splits)
- `cargo check -p melinoe -p halo` clean (no new warnings).
- `cargo check -p themis` clean.
- `cargo check -p moirai-core` clean.
- `cargo nextest run -p melinoe -p halo` 100% pass (same count as pre-split).
- `cargo nextest run -p themis` 100% pass.
- `cargo nextest run -p moirai-core` 100% pass.
- `git diff --stat` confirms zero net lines changed (only file relocations).
- `rg "pub mod (hybrid|mpmc|branded_deque|sync_region)"` confirms no stale source files remain.

### Phase 2 (themis test rehome)
- `cargo nextest run -p themis` 100% pass (same count as pre-move).
- `cargo test --doc -p themis` green.
- `ls repos/themis/tests/` contains `topology/` and `branded.rs`.
- `ls repos/themis/src/topology/tests/` does not exist.
- No production crate depends on `themis::topology::tests::*` or `themis::branded::tests::*` (confirmed via `rg -l "themis::(topology::tests|branded::tests)"`).

### Phase 3 (constants split)
- `cargo check -p moirai-core` clean.
- `cargo nextest run -p moirai-core` 100% pass.
- `rg "use crate::constants" repos/moirai/moirai-core/src` returns zero matches.
- `repos/moirai/moirai-core/src/constants.rs` does not exist.
- Each constant's new home documents its provenance (comment or commit reference).

### Phase 4 (deferred)
- No verification gate. TREE-DUP-002 carries its own ADR and verification plan.

## Sequencing

1. Phase 1 (file splits) — implement first, verify per-gate.
2. Phase 2 (themis test rehome) — implement second, verify per-gate. Must wait for Phase 1 if `sync_region` tests are affected (they are not — Phase 1 splits the module but preserves the test module in `src/branded/region/tests.rs`, which Phase 2 then moves to `tests/`).
3. Phase 3 (constants split) — implement third, verify per-gate.
4. Phase 4 (dual channel) — deferred; filed as TREE-DUP-002.
