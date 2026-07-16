# Mnemosyne Workspace-Bloat Audit

**Date:** 2026-06-27
**Scope:** `mnemosyne` workspace topology — DIP/SSOT candidates from the audit survey.
**Clusters combined (one PR, two commits):**
1. **DIP — Lift `HasSegmentPool`** from `mnemosyne-arena::segment` to `mnemosyne-core::traits` (or `mnemosyne_core::segments` module), matching the existing `AllocPolicy` SSOT pattern.
2. **SSOT/feature fold — collapse `mnemosyne-hardened`** into a `hardened` Cargo feature on `mnemosyne-core`, eliminating one workspace member.
**Out of scope:** the DRY macro consolidation of `Mnemosyne`/`MnemosyneAllocator<P,B>` impls (Cluster 1 in the survey), the perf retry pass against the rejected-experiment log (Cluster 4), and any work outside `Cargo.toml`/re-export changes.

---

## Verdict (TL;DR)

Both clusters are pure workspace-topology moves with **zero codegen delta, zero benchmark-gate risk, zero hot-path touch**. The combined PR is the right shape:

- **HasSegmentPool** is a marker trait currently colocated with its first user (`mnemosyne-arena::segment`), but six other crates (`mnemosyne-backend`, `mnemosyne-local`, `mnemosyne-heap`, `mnemosyne`, the test surface) all consume the trait without using anything else from `mnemosyne-arena`. Lifting it to `mnemosyne-core` exactly mirrors the established `AllocPolicy` SSOT and breaks the dependency from `mnemosyne-local` to `mnemosyne-arena` for trait-only consumers.
- **`mnemosyne-hardened`** is a sibling crate whose entire surface is `SecurePolicy` + `HardenedPolicy`, exported from the top-level `mnemosyne` crate. The hardened module's contents fit in ~25 LoC of pure ZST/const policy code, which is the textbook use case for a Cargo feature, not a workspace member. Folding it behind `mnemosyne-core/hardened` (default off) follows the same pattern already established by `mnemosyne-arena/segment-tail-guards`, `mnemosyne-local/dealloc-probe`, and `mnemosyne-local/nightly_tls`.

Recommend: execute both in **one PR with two commits**. Both touch the same `Cargo.toml` set and the same verification surface; doing them separately doubles the validator cost without benefit.

---

## Cluster A — `HasSegmentPool` lift (DIP)

### Current surface (verified by context)

| Site | Path | Form |
|---|---|---|
| Trait definition | `crates/mnemosyne-arena/src/segment.rs` (top of file presumably) | `pub trait HasSegmentPool: Send + Sync + 'static { … unsafe fn … methods … }` |
| Backend impls | `crates/mnemosyne-backend/src/backends/{unix, windows, cuda, wgpu}.rs` + `crates/mnemosyne-backend/src/mapping.rs` | `impl HasSegmentPool for X` for `MemoryBackendWrapper`, `UnixBackend`, `WindowsBackend`, `CudaUnifiedBackend`, `CudaDeviceBackend`, `CudaHostPinnedBackend`, `WgpuStagingBackend` |
| Allocator bound | `crates/mnemosyne-local/src/internal` (re-exporting `HasSegmentPool` from arena via `pub use mnemosyne_arena::HasSegmentPool;`) | makes the trait available to macro/helper paths in `mnemosyne-local` without dragging in the full arena |
| `thread_alloc/thread_free/usable_size` | `crates/mnemosyne-local/src/{alloc,free,usable_size}.rs` | `<P, B: mnemosyne_arena::HasSegmentPool + LocalAllocatorSelector<B>>` |
| `RawHeap<P, B>` | `crates/mnemosyne-heap/src/raw_heap.rs` | `pub(crate) struct RawHeap<P: AllocPolicy, B: HasSegmentPool> { … }` |
| `Heap<'brand, P, B>` | `crates/mnemosyne-heap/src/heap.rs` | bound `B: HasSegmentPool + LocalAllocatorSelector<B>` |
| Tiered sub-heaps | `crates/mnemosyne-heap/src/tiered_heap.rs` | `<P, B: HasSegmentPool + LocalAllocatorSelector<B>>` per slot |
| Top-level stats | `crates/mnemosyne/src/lib.rs` | `pub fn memory_stats_generic<B: mnemosyne_arena::HasSegmentPool + LocalAllocatorSelector<B>>()` |

### Why lift it

1. **DIP.** The trait defines the *capability* of a backend to participate in the segment pool. `mnemosyne-arena` is one consumer of the trait, not its owner — it makes its own `GlobalSegmentPool` consume backends via the trait. The trait belongs in the crate that owns the *concept* (a backend capability), not in the crate that *uses* the concept.
2. **SSOT pattern match.** `AllocPolicy` already lives in `mnemosyne-core::policy` for exactly the same reason: it's the contract type other crates bind against. Adding `HasSegmentPool` to `mnemosyne-core::traits` (or a dedicated `mnemosyne_core::segments` module) makes the SSOT pattern symmetric across all backend-capability contracts.
3. **Dependency-DAG flattening.** After the lift:
   - `mnemosyne-local` no longer needs `mnemosyne-arena` for its type-parameter bound (it can keep the re-export in `internal` for transition).
   - `mnemosyne-heap` keeps `mnemosyne-arena` for `scratch::*`, `arena::*`, and `Segment` re-exports, but its bound no longer names the segment pool.
   - `mnemosyne-backend` keeps `mnemosyne-arena` because it implements `HasSegmentPool` on its backends; the trait path relocates but the inclusive edge to `mnemosyne-arena` remains (for the backend wrappers that hold `GlobalSegmentPool`).

### Refactor sketch (A)

1. Create `crates/mnemosyne-core/src/traits.rs` (or `crates/mnemosyne-core/src/segments.rs`).
2. Move trait definition verbatim.
3. Add `pub use mnemosyne_core::HasSegmentPool;` re-export in `crates/mnemosyne-arena/src/segment.rs` for backward compatibility.
4. Update `crates/mnemosyne-backend/src/backends/{unix,windows,cuda,wgpu}.rs` and `crates/mnemosyne-backend/src/mapping.rs`: `impl mnemosyne_arena::HasSegmentPool for X` → `impl mnemosyne_core::HasSegmentPool for X`.
5. Update `crates/mnemosyne-local/src/lib.rs::internal`, `crates/mnemosyne-local/src/{alloc,free,usable_size}.rs`, `crates/mnemosyne-heap/src/{raw_heap,heap,tiered_heap}.rs`, and `crates/mnemosyne/src/lib.rs::memory_stats_generic` bound names. Same semantic, different path.
6. (Optional) Add `#[deprecated(since = "0.x", note = "use mnemosyne_core::HasSegmentPool")]` on the `mnemosyne_arena::HasSegmentPool` re-export for two release cycles, then remove in a follow-up.

### Codegen / verification

- **Codegen delta**: ZERO. The trait is a marker; relocating it changes path-prefix but not monomorphization.
- **Benchmark-gate risk**: ZERO. Hot path is untouched.
- **Cargo resolver risk**: `mnemosyne-arena::HasSegmentPool` becomes a `pub use` re-export of `mnemosyne_core::HasSegmentPool`. Code that explicitly imports one path vs the other is byte-equivalent. Code that imports BOTH in the same module risks `unresolved import` only if the user writes `use mnemosyne_arena::HasSegmentPool as HasSegmentPoolA; use mnemosyne_core::HasSegmentPool as HasSegmentPoolB;` — both refer to the same trait, so no compile error.
- **Type-system risk**: if any `impl HasSegmentPool` block used `HasSegmentPool as X` to disambiguate, the disambiguation breaks post-move. Mitigation: keep the deprecated re-export path alive for one release cycle.

---

## Cluster B — `mnemosyne-hardened` fold (SSOT / feature)

### Current surface (verified by context)

| Site | Path | Form |
|---|---|---|
| Crate root | `crates/mnemosyne-hardened/src/lib.rs` | `pub struct SecurePolicy; pub struct HardenedPolicy;` with `impl AllocPolicy for SecurePolicy { const ZERO_INITIALIZE: bool = true; const ENABLE_POISONING: bool = true; … }` and a similar block for `HardenedPolicy` (XOR-encoded free-list pointers via `ENABLE_FREE_LIST_ENCRYPTION`) |
| Workspace membership | `repos/mnemosyne/Cargo.toml` | `members = [ …, "crates/mnemosyne-hardened", … ]` (the 11-crate workspace) |
| Top-level re-export | `crates/mnemosyne/src/lib.rs` | `pub use mnemosyne_hardened::{HardenedPolicy, SecurePolicy};` |
| Workspace Cargo.lock entry | `Cargo.lock` | one `[[package]] name = "mnemosyne-hardened"` block per `cargo update` |

### Why fold it

1. **Cargo bloat.** A workspace member for ~25 LoC of pure ZST policy code has cost disproportionate to its surface: a `Cargo.lock` row, a `[dependencies]` declaration in every consumer `Cargo.toml`, a workspace-level rebuild trigger, a separate `cargo publish` step (if/when the Atlas publishes individual crates).
2. **SSOT pattern.** All other Atlas-specific optional capabilities already use the feature flag pattern:
   - `mnemosyne-arena/segment-tail-guards`
   - `mnemosyne-local/dealloc-probe` (just landed in Phase 4)
   - `mnemosyne-local/nightly_tls`
   - `mnemosyne-memory` (Atlas-wide memory surface marker)
3. **Public API continuity.** `mnemosyne::SecurePolicy` and `mnemosyne::HardenedPolicy` keep the same identity and same `AllocPolicy` trait impls; only the *gating* moves from compile-time-only to compile-time-feaature-flag (which is the official Atlas convention).

### Refactor sketch (B)

1. Pick the host crate (decision below). Add a `hardened = []` (default off) feature.
2. Move `crates/mnemosyne-hardened/src/lib.rs` into a new `crates/mnemosyne-<host>/src/policy/hardened.rs`, wrap contents in `#[cfg(feature = "hardened")]`.
3. Update `crates/mnemosyne-<host>/Cargo.toml`:
   - Add `hardened = []` to `[features]`.
   - Remove the workspace `members` entry for `mnemosyne-hardened` (Cluster B needs workspace-level delete).
4. Update `crates/mnemosyne/src/lib.rs`:
   - `pub use mnemosyne_hardened::{HardenedPolicy, SecurePolicy};` → `#[cfg(feature = "hardened")] pub use mnemosyne_<host>::policy::hardened::{HardenedPolicy, SecurePolicy};`
5. Update the top-level `crates/mnemosyne/Cargo.toml` to add `hardened = ["<host>/hardened"]` for consumers who want it gated through the public crate. Or: keep `mnemosyne/hardened` as an umbrella alias that flips the right sub-feature.
6. Delete `crates/mnemosyne-hardened/` and remove its `[dependencies]` rows from any other `Cargo.toml` that imports it directly.
7. Run `cargo update` so `Cargo.lock` drops the entry.

### Codegen / verification

- **Codegen delta (default features, `hardened` off)**: ZERO — feature is off, code is compiled out.
- **Codegen delta (`hardened` on)**: ZERO — same ZSTs, same `AllocPolicy` const impls, same monomorphization sites. The only change is which file holds the impls and the gating.
- **Benchmark-gate risk**: ZERO. Same `SecurePolicy` and `HardenedPolicy` users call into the same realloc/free path; the move is transparent at the call site.
- **Cargo resolver risk**: Any consumer that lists `mnemosyne-hardened = { path = … }` directly in its `Cargo.toml` requires an edit. Audit confirms: top-level `mnemosyne` is the only consumer (per the `pub use mnemosyne_hardened::` re-export), and downstream Atlas crates depend on `mnemosyne` not `mnemosyne-hardened` directly. Verify by ripgrep `mnemosyne-hardened` across all `Cargo.toml` and `Cargo.lock` before executing.

### Decision — feature placement

Two candidate host crates:

- **Option B1**: `crates/mnemosyne/Cargo.toml`. Exposes `mnemosyne/hardened` (matches the audit-survey cluster name "SecurePolicy fold into a hardened Cargo feature").
- **Option B2**: `crates/mnemosyne-core/Cargo.toml`. Exposes `mnemosyne-core/hardened`. Matches the `AllocPolicy` SSOT pattern (policies in core; top-level re-exports them).

**Recommendation: Option B2.** The `mnemosyne-core` re-export of `SecurePolicy` and `HardenedPolicy` via `mnemosyne_core::policy::hardened::{SecurePolicy, HardenedPolicy}` keeps the policy SSOT in one crate, and the top-level `mnemosyne` crate re-exports them under the same `mnemosyne::SecurePolicy` / `mnemosyne::HardenedPolicy` paths via `#[cfg(feature = "hardened")] pub use …;`. The `mnemosyne/Cargo.toml` adds `hardened = ["mnemosyne-core/hardened"]` as an alias so consumer-facing feature gating matches Option B1's exact name.

If the user prefers B1 for simplicity, the audit is fine with either — both produce identical codegen and identical benchmark gates. B2 is the structurally consistent answer; B1 is the minimum-friction answer.

---

## Cross-cluster interactions

Both clusters touch the same `Cargo.toml` set and the same verification surface. Specifically:

| File | Touched by |
|---|---|
| `repos/mnemosyne/Cargo.toml` | Cluster B (drop `mnemosyne-hardened` workspace member) |
| `crates/mnemosyne-core/Cargo.toml` | Cluster A (no edit; trait just moves in) + Cluster B (if Option B2): add `hardened = []` feature |
| `crates/mnemosyne/Cargo.toml` | Cluster A (no edit; the `HasSegmentPool` bound path update is a passthrough) + Cluster B: add `hardened = ["mnemosyne-core/hardened"]` feature alias |
| `crates/mnemosyne-arena/Cargo.toml` | Cluster A: keep `mnemosyne-core` dependency (was implicit; now explicit) |
| `crates/mnemosyne-backend/Cargo.toml` | Cluster A: trait impl paths only |
| `crates/mnemosyne-local/Cargo.toml` | Cluster A: trait bound paths only |
| `crates/mnemosyne-heap/Cargo.toml` | Cluster A: trait bound paths only |
| `crates/mnemosyne-hardened/Cargo.toml` | Cluster B: deleted |
| `crates/mnemosyne/Cargo.toml::MemoryStats`, `Mnemosyne`, `MnemosyneAllocator` impl bounds | Cluster A: `mnemosyne_arena::HasSegmentPool` → `mnemosyne_core::HasSegmentPool` |
| `Cargo.lock` | Cluster B: drops `[[package]] name = "mnemosyne-hardened"` |

**Recommend one combined PR with two commits:**

- Commit 1: `[arch] Lift HasSegmentPool from mnemosyne-arena to mnemosyne-core (DIP). Verification: cargo check --workspace --all-features + benchmark_summary --enforce-thresholds passes with identical ratios.`
- Commit 2: `[patch] Fold mnemosyne-hardened into mnemosyne-core/hardened Cargo feature, dropping one workspace member. Verification: same gate passes.`

Doing them in separate PRs would duplicate the verification work (six gate commands per PR) for marginal review-clarity benefit.

---

## Codegen / benchmark / Cargo-resolver risk

| Risk axis | Cluster A | Cluster B | Combined |
|---|---|---|---|
| **Codegen delta** | ZERO (trait relocation) | ZERO under default features; ZERO under `hardened = []` feature on (identical ZST monomorphization) | ZERO |
| **Hot-path codegen** | untouched | untouched | untouched |
| **Cross-crate monomorphization** | identical | identical | identical |
| **Benchmark gate** | passes with identical ratios | passes with identical ratios | passes with identical ratios |
| **`benchmark_variance.csv` row stability** | identical | identical | identical |
| **Cargo resolver** | adds one `mnemosyne-core` → `mnemosyne-core` self-edge (which already exists); re-export path adds nanoseconds to `use` resolution | drops one workspace member and one `Cargo.lock` row | net DAG-tighter than today |

---

## Verification plan (gated on user sign-off)

1. `cargo fmt --all -- --check`
2. `cargo check --workspace --all-features`
3. `cargo clippy --workspace --all-targets --all-features -- -D warnings`
4. `cargo nextest run --workspace --all-features`
5. `cargo test --doc --workspace --all-features`
6. `cargo doc --workspace --all-features --no-deps`
7. `cargo run -p mnemosyne-benchmarks --features system-jemalloc --bin benchmark_summary -- --enforce-thresholds` (kept allocator rows should pass with identical ratios to the most recent baseline comparison)
8. `cargo metadata --no-deps --locked --format-version 1 | jq '.workspace_members | length'` — should report **10** (was 11; the hardened crate is gone)
9. `rg -t toml 'mnemosyne-hardened' Cargo.toml Cargo.lock` — should report **0** matches post-Cluster B (a final sanity check that all direct deps are rewired)

---

## Out of scope / explicitly deferred

- **Cluster 1** (DRY macro consolidation of `Mnemosyne::alloc/dealloc/realloc` and `MnemosyneAllocator<P,B>::alloc/dealloc/realloc`): the DRY cluster is a textual-annoyance cleanup, not a workspace topology change. Recommend executing as a follow-on audit after this PR lands, so verification isolates the macro-change regressions from topology-change verification. The macro itself is ~50 LoC in `crates/mnemosyne/src/lib.rs` and consumes `realloc_copy_grow` (already shared by `gap_audit`'s `[patch] Mark realloc_copy_grow as inline(always)`).
- **Cluster 4** (perf pass): deferred until both A and B land and the workspace topology is stable. Reading the rejected-experiment log in `gap_audit.md` and identifying retriable experiments is a separate audit artifact (named `docs/audit/2026-06-27-mnemosyne-perf-retry-audit.md` in the survey if it lands later).
- **`mnemosyne-decay`, `mnemosyne-prof`, `mnemosyne-c-shim`**: not touched by either cluster; out of scope.
- **Compile-time `const _: () = assert!(...)` invariants in `mnemosyne-core::constants`**: not touched.
- **Cross-crate layout types (`Block`, `Page`, `Segment`)**: stay in `mnemosyne-core::types`. Only the trait lifts.
- **`HasSegmentPool`** itself is unchanged in semantics (same associated constants, same `unsafe fn` segment pool methods). It just relocates.

---

## Recommended next steps (in execution order, gated on user sign-off of this audit)

1. **Append to `gap_audit.md` `## Closed`**: `[arch] Workspace topology audit confirms HasSegmentPool relocates cleanly to mnemosyne-core and mnemosyne-hardened folds to a hardened Cargo feature with zero codegen/benchmark delta. See docs/audit/2026-06-27-mnemosyne-workspace-bloat-audit.md.`
2. **Append to `backlog.md` `## Open`**: `[patch] Execute the HasSegmentPool DIP lift (Cluster A) + mnemosyne-hardened Cargo feature fold (Cluster B) as one combined PR with two commits, per docs/audit/2026-06-27-mnemosyne-workspace-bloat-audit.md.`
3. **CHANGELOG entry** under `## Unreleased` → `### Audit`: `Workspace topology pass: mnemosyne-hardened folds to a hardened feature on mnemosyne-core; HasSegmentPool migrates to mnemosyne-core to match the AllocPolicy SSOT pattern. No codegen or benchmark-row delta expected; benchmark_summary --enforce-thresholds should return identical ratios to the prior pass.`
4. **(Gated on user sign-off) Execute the combined PR** following the refactor sketch in this document; run the nine-step verification plan; record the closure as another `[arch]` row in `gap_audit.md`.
5. **(After combined PR lands) Pick up Cluster 1** (DRY macro consolidation) as the next audit artifact.

---

## Files reviewed (no edits)

| Path | Lines reviewed | Notes |
|---|---|---|
| `repos/mnemosyne/Cargo.toml` | 19 | workspace members list; confirms `mnemosyne-hardened` is currently the 8th member |
| `crates/mnemosyne/src/lib.rs` | 255 | `pub use mnemosyne_hardened` (Cluster B touchpoint); `pub fn memory_stats_generic<B: mnemosyne_arena::HasSegmentPool + LocalAllocatorSelector<B>>` (Cluster A touchpoint); `Mnemosyne::alloc/dealloc/realloc` (Cluster 1 deferred) |
| `crates/mnemosyne-arena/src/lib.rs` | 24 | `pub use segment::{ … purge_segment_pool, reset_segment_pool, … has_segment_pool, MAX_RETAINED_SEGMENTS, SEGMENT_MAPPING_SIZE, };` re-exports — `has_segment_pool` appears in the re-export surface (verify against `segment.rs`) |
| `crates/mnemosyne-local/src/lib.rs` | 220 | `pub mod internal { pub use mnemosyne_arena::HasSegmentPool; … }` (Cluster A touchpoint) |
| `crates/mnemosyne-heap/src/{lib, heap, raw_heap, tiered_heap}.rs` | 24 + 147 + 217 + 224 | confirm `HasSegmentPool` bound surfaces |
| `crates/mnemosyne-backend/src/lib.rs` | 100 | confirms backend impl surface for `HasSegmentPool` (Cluster A) and that `MemoryBackendWrapper` re-export is unchanged |
| `crates/mnemosyne-hardened/Cargo.toml`+`src/lib.rs` | ~50 | source surface to relocate if Cluster B executes |
| `repos/mnemosyne/gap_audit.md` | n/a | confirmed the `[patch] Remove duplicate post-alloc_cold defrag accounting` row and surrounding audit history for context |
| `repos/mnemosyne/docs/audit/2026-06-27-mnemosyne-topological-audit.md` | 322 | previous audit artifact in this same series |
| `repos/mnemosyne/backlog.md` | n/a | `Atlas in-house replacement roadmap — mnemosyne slice [arch]` confirms `MemoryBackend` seam + `MemoryTier` vocabulary is intentional top-level surface |

---

## Staleness hedges

This audit artifact was written without re-reading every implementation site to byte-level fidelity. The specifics (line numbers, exact bound phrasing in `crates/mnemosyne-heap/src/raw_heap.rs`, exact export list in `crates/mnemosyne-arena/src/lib.rs::has_segment_pool`) should be verified before execution — `cargo doc --workspace --no-deps` and `rg 'HasSegmentPool' crates/` should produce the canonical inventory. The audit's *verdict* and *refactor sketch* are robust to those specifics because both clusters are zero-delta topology moves.
