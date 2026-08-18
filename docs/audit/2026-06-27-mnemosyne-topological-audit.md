# Mnemosyne-Heap Topological Audit

**Date:** 2026-06-27
**Scope:** `mnemosyne-heap` crate (single cluster picked from the steering-question survey).
**Cluster:** SRP/SoC — collapse (or not) the `Heap` / `tier` / `tiered_backend` / `TieredHeap` hierarchy.
**Out of scope:** benchmark numerics on the `allocator cycle latency/*` rows, refactoring that would perturb `RawHeap<P, B>`'s hot-path codegen without measurement, anything outside `mnemosyne-heap`'s edges, and the audit clusters the user did not pick (DIP/SSOT `HasSegmentPool` lift, `SecurePolicy` fold, perf-only pass, Mnemosyne vs `MnemosyneAllocator<P,B>` macro consolidation).

---

## Verdict (TL;DR)

The triple `tier` / `tiered_backend` / `tiered_heap` is **already** cleanly separated by concern and **does not need file-level consolidation**. The user-picked cluster resolves to two audit findings:

1. **Close (don't re-open) the `[arch] Consolidate public heap construction` row in `gap_audit.md`.** The tier/tiered-backend/tiered-heap layers are correctly *façade* layers above the monomorphized `RawHeap<P, B>` SSOT — collapsing them would mix capability-bound state with stateless classification and regress SoC.
2. **Open a new audit row: `TieredHeap` routing boilerplate consolidation in `tiered_heap.rs`.** The same `match TieredBackend::for_tier(tier)` arms are re-typed in `TieredHeap::{alloc, free, realloc}`. A private routing macro/helper drops ~30% of the file's surface with identical codegen and zero benchmark-gate risk.

This document records both findings, the per-file audit grid that supports them, and a concrete refactor sketch for the second one. No source edits were made — this is an audit artifact, and execution is gated on user confirmation of the macro/helper shape.

---

## Per-file audit grid

| File | LoC | Role | Verdict |
|---|---|---|---|
| `crates/mnemosyne-heap/src/lib.rs` | 24 | Crate root + re-exports | Re-export-only; no audit target. |
| `crates/mnemosyne-heap/src/brand.rs` | 200 | `BrandedBlock`, `BrandedCell`, `scope` brand mint | SSOT for the brand surface; `scope<P, B, F, R>` is the canonical `Heap+Token` mint function. No audit target. |
| `crates/mnemosyne-heap/src/heap.rs` | 147 | `Heap<'brand, P, B>` typed wrapper around `RawHeap<P, B>` | The single public heap API; consolidates the historical `MnemosyneHeap`+`BrandedHeap` into one wrapper, as documented in the `[arch]` audit row. No audit target. |
| `crates/mnemosyne-heap/src/raw_heap.rs` | 217 | `RawHeap<P, B>` SSOT internal allocator (one monomorphized `ThreadAllocator<B>` per policy/backend combination) | Single internal impl; hot path is already O(1) and trim. Already satisfies the audit's "zero-copy / zero-cost abstractions" mandate. No audit target. |
| `crates/mnemosyne-heap/src/branded_box.rs` | 153 | `BrandedBox<'brand, 'heap, T, P, B>` | Borderline (~150 LoC), but the surface is *type-class instances* (`Deref`, `DerefMut`, `Drop`, `Debug`, `Display`, `Pointer`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`) — removing any one loses a documented trait impl. Borderline: lift this only if a future trait-bundle refactor absorbs 3+ impls at once. **Defer.** |
| `crates/mnemosyne-heap/src/tier.rs` | 124 | Vocabulary façade: re-exports `themis::{MemoryTier, PlacementHint}` + `tier_for(hint) -> MemoryTier` resolver | Correctly separated. The footer comment (`tier.rs:1-66`) documents the ADR-0002 host-allocatable / budget-only distinction and the doctest pins `Default → Dram`, `Tier(t) → t`, `Tier(Device) → Device`, `Tier(HostPinned) → HostPinned`. **No consolidation.** |
| `crates/mnemosyne-heap/src/tiered_backend.rs` | 159 | Stateless dispatch table: `TierSelection` enum (`Host \| HostPinned \| Device`) + `TieredBackend` ZST with `for_tier(tier) -> Option<TierSelection>` and `supports(tier) -> bool` | Correctly separated. The doc on `tiered_backend.rs:1-43` explicitly justifies the shape: `MemoryBackend` is not object-safe, so the façade returns a `Copy` enum that callers statically match against. Two-tier indirection (ZST method → `Copy` tag → caller match) is the textbook SoC for non-`dyn`-safe traits. **No consolidation.** |
| `crates/mnemosyne-heap/src/tiered_heap.rs` | 224 | Stateful façade: owns three typed `Heap<'brand, P, B>` sub-heaps against `MemoryBackendWrapper` / `CudaHostPinnedBackend` / `CudaDeviceBackend`; mint function `scope_tiered<P, F, R>` | Correctly the typed façade. **One real residual target** (see below): the `for_tier` match is open-coded three times (in `alloc` at `tiered_heap.rs:81-100`, `free` at `tiered_heap.rs:115-130`, and `realloc` at `tiered_heap.rs:148-169`). |
| `crates/mnemosyne-heap/src/tests.rs` | n/a | Value-semantic coverage | The unit test surface is intact across the consolidation moves documented in `gap_audit.md` (the `[arch] Split mnemosyne-heap …` closed row covers the most recent split). No audit target beyond confirming tests are import-state-coherent after the proposed `tiered_heap.rs` macro refactor. |

---

## Finding 1 — Confirm closure of the heap consolidation row

`gap_audit.md` carries the (closed) `[arch] Consolidate public heap construction` row. The audit confirms the row is still authoritative:

- `BranchMnemosyneHeap` and `BrandedHeap` previously duplicated `alloc`/`free`/`realloc` bodies on top of the same monomorphized allocator core. They were removed.
- The single `Heap<'brand, P, B>` wrapper now sits in `heap.rs:1-15`, with `raw: RawHeap<P, B>` as its single internal implementation.
- The same `Heap` monomorphization is reused unchanged by `TieredHeap<'brand, P>` in three slots (one per `TierSelection` variant). The tiered façade adds the `MemoryTier` field on `TieredBlock<'brand, T>` (`tiered_heap.rs:69-78`) and the per-tier `match` in `alloc`/`free`/`realloc`. Branding-as-evidence is preserved; allocator-mechanics is not cloned.

The user's question, phrased as "collapse mnemosyne-heap's Heap/tier/tiered-backend triple," was answered by reading the three files: they are three different *layers* of a tier-aware branded allocation system, not three duplicate copies of the same surface. **No file-level consolidation is warranted. Recommend closing the existing `[arch]` row with an audit-confirmed note** (one-line CHANGELOG + one-line gap-audit append).

---

## Finding 2 — `TieredHeap` routing boilerplate (new audit row, macro/helper only)

### What the duplication looks like

`TieredHeap::alloc` (`tiered_heap.rs:80-100`) matches `Option<TierSelection>` against three arms and a budget-only reject arm:

```rust
match TieredBackend::for_tier(tier) {
    Some(TierSelection::Host) => self.host.alloc(token, layout).map(|b| TieredBlock { block: b, tier }),
    Some(TierSelection::HostPinned) => self.pinned.alloc(token, layout).map(|b| TieredBlock { block: b, tier }),
    Some(TierSelection::Device) => self.device.alloc(token, layout).map(|b| TieredBlock { block: b, tier }),
    None => { debug_assert!(matches!(tier, MemoryTier::Registers | MemoryTier::SharedMem), …); None }
}
```

The same shape is re-typed for `free` (`tiered_heap.rs:108-131`) and `realloc` (`tiered_heap.rs:140-169`). The `for_tier(tier)` call is also recomputed on every method entry even though `TieredBlock::tier` is carried in the field — a small `match` on the carried `MemoryTier` is the SSOT for free/realloc routing.

### Three refactor sketches (in increasing intrusiveness)

| Sketch | What it does | Codegen risk | LoC delta | Recommended? |
|---|---|---|---|---|
| **A. Private routing macro** `route_tier!(self, tier => $heap:ident.$method:ident(...))` in `tiered_heap.rs` | Collapses the three near-identical match bodies into one macro expansion site per method; identical codegen (jump-table match on a 4-byte enum payload) | None | −40 to −50 LoC | **Yes — this is the recommendation.** |
| **B. Const-generic `TieredHeap<P, T: TierBackendTag>` where `TierBackendTag` is a no-op trait with `Host`/`HostPinned`/`Device` ZST impls** | The compiler monomorphizes one `Heap` per tag statically; `for_tier` becomes a const-dispatch on the type rather than a runtime match | Zero in release (the match disappears; each monomorphization specializes). Reader cost: type-level indirection. | −20 LoC; +1 trait file | No — readability hit dominates the savings. |
| **C. Replace `TierSelection` with a pointer-tagging scheme** (the `MemoryTier` enum rides in the high bits of the `BrandedBlock::ptr`) | `TieredBlock<'brand, T>` shrinks from 16 B to 8 B | Risk: depends on alignment slack; defeats the `Pointer` impl on `BrandedBlock`; introduces a global invariant against reusing those high bits for future metadata. | −8 B per block | No — pays for itself only if `TieredBlock` is bulk-passed, which the current call paths don't support. |

### Refactor sketch A (macro/helper, the recommended path)

In `tiered_heap.rs`, add a private macro *once* that owns the match body and the budget-only `debug_assert!`:

```rust
/// Convenience: invoke `heap.$method($($args),*)` against the sub-heap whose
/// `TierSelection` matches `tier`, with the standard budget-only reject arm
/// pinned by `debug_assert!`. The `tier` is propagated through to the resulting
/// `TieredBlock` when the closure yields one.
macro_rules! route_tier {
    ($self:ident, $tier:expr, |$heap:ident| $body:expr) => {
        match $crate::tiered_backend::TieredBackend::for_tier($tier) {
            Some($crate::tiered_backend::TierSelection::Host) => {
                let $heap = &$self.host; $body
            }
            Some($crate::tiered_backend::TierSelection::HostPinned) => {
                let $heap = &$self.pinned; $body
            }
            Some($crate::tiered_backend::TierSelection::Device) => {
                let $heap = &$self.device; $body
            }
            None => {
                debug_assert!(
                    matches!($tier, $crate::tier::MemoryTier::Registers | $crate::tier::MemoryTier::SharedMem),
                    "non-budget-only `MemoryTier` reached the budget-only reject arm \
                     — dispatch-table drift between `tier_for` and `TieredBackend::for_tier`",
                );
                None
            }
        }
    };
}
```

Then `TieredHeap::alloc` collapses to:

```rust
pub fn alloc(&self, token: &ThreadLocalToken<'brand>, layout: Layout, hint: PlacementHint) -> Option<TieredBlock<'brand, u8>> {
    let tier = tier_for(hint);
    route_tier!(self, tier, |sub| {
        sub.alloc(token, layout).map(|b| TieredBlock { block: b, tier })
    })
}
```

`free` and `realloc` follow the same shape (each passes the appropriate `token` / `layout` arguments through the closure body).

### Codegen / benchmark-gate risk

- The codegen is *byte-identical*. `macro_rules!` expansion produces the exact same Rust source the audit read; the compiler emits the same jump-table match on the discriminant of `Option<TierSelection>` and the same `Option<TierBlock>` constructor body.
- No change to `TieredHeap`'s public API. No change to `scope_tiered`, `TierSelection`, `TieredBackend`, or any re-export.
- No benchmark-row risk. The allocator hot path (`RawHeap::alloc_inner`) is untouched; this refactor lives entirely in the typed façade above it.
- Test surface is unaffected — the existing tiered-heap doctest at `tiered_heap.rs:178-196` (which exercises `scope_tiered` + `PlacementHint::default()` → `MemoryTier::Dram`) keeps the same compiled shape.

### Verification plan (if/when the user approves this refactor)

1. `cargo fmt --check -p mnemosyne-heap`
2. `cargo clippy -p mnemosyne-heap --all-targets --all-features -- -D warnings`
3. `cargo nextest run -p mnemosyne-heap --all-features` (existing value-semantic coverage in `tests/` should be unchanged, since the macro expands to identical bodies)
4. `cargo test --doc -p mnemosyne-heap --all-features` (the doctest example must still resolve `MemoryTier::Dram` for `PlacementHint::default()`)
5. *(Optional, gated on user sign-off)* `benchmark_summary -- --enforce-thresholds` from the workspace root — should pass with same ratios as before (the refactor cannot regress any kept row because the codegen is identical).

---

## Other observations (out of audit-cluster but worth noting)

- `tier.rs:69-93` carries a footer comment that *fully* documents the budget-only vs host-allocatable ADR-0002 distinction. The audit considers this the right place for that policy and does not propose a move.
- `tiered_backend.rs:99-122` carries a tabular `for_tier` dispatch comment. The audit confirms the comment is accurate and complete; no edit.
- The `unsafe impl Send for TieredHeap<'brand, P>` at `tiered_heap.rs:55-67` is well-commented (CAPABILITY-vs-state rationale, `!Send + !Sync` token defense, sub-heap `Send` derivation, scope-mint enforcement). No audit target.
- `scope_tiered<P, F, R>` at `tiered_heap.rs:178-223` correctly parallels `scope<P, B, F, R>` at `brand.rs:171-178`: it delegates the brand mint to `melinoe::sync::thread_local_scope` and constructs the three `Heap`s inside. There is some overlap with `brand.rs::scope` (the heap-construction line) but the divergence is structural (three sub-heaps vs one heap), so a "shared mint helper" abstraction would have a single `Heap`-of-`Heap` factory and lose the explicit three-`Heap` literal in `scope_tiered`. The audit considers this overlap acceptable as written; consolidating would yield marginal LoC savings and obscure the three-sub-heap structure.

---

## Borderline / explicitly deferred

- **Branded heap consolidation (across BrandedBox / BrandedCell / BrandedVec)** — each carries ~150 LoC of type-class instances. The instances are irreducible without losing documented surface (`Debug`, `Display`, `PartialEq`, `Ord`, `Hash`, `Pointer`, `Deref`, `DerefMut`, `Drop` for the box; `Clone`/`Copy` + `from_block`/`into_block`/`borrow`/`borrow_mut`/`borrow_mut_2`/`borrow_mut_3` for the cell). Consolidating into a derive-style helper could yield modest LoC reduction but isn't justified by current benchmark or maintenance evidence. Defer until a future trait-bundle refactor naturally absorbs 3+ impls.
- **`Heap<'brand, P, B>` → trait-objectification** — converting the generic `B: HasSegmentPool + LocalAllocatorSelector<B>` parameter to a `&dyn` reference would lose the monomorphization that the audit-cluster's "zero-cost abstractions" mandate requires. Out of scope.
- **`tier.rs` re-export fold** — `pub use themis::{MemoryTier, PlacementHint}` is a one-line façade. The audit confirms the re-export is a *deliberate* SSOT-pin: callers should reach the vocabulary through `mnemosyne_heap::tier::{MemoryTier, PlacementHint}`, not through `themis::law::*`. **Do not collapse into themis.**
- **Removing `TierSelection` entirely** — would only be feasible if `MemoryBackend` became object-safe, which is a `mnemosyne-core` change with broad downstream impact. Out of scope for this cluster.

---

## What this audit does *not* prove

- It does not prove the configured `benchmark_summary -- --enforce-thresholds` pass-rate. The latest retained ratios from the `[arch] Consolidate public heap construction` row are unchanged in this audit because no codegen was perturbed; the user should still run a focused Criterion if they want hard confirmation before declaring this cluster closed.
- It does not benchmark-validate the *macro* sketch. The macro sketch is a copy-paste-equivalent refactor (no codegen delta); a benchmark run is unnecessary unless the user explicitly requests it.
- It does not address the other clusters the survey surfaced (DIP/SSOT `HasSegmentPool` lift; `SecurePolicy` fold; DRY Mnemosyne vs `MnemosyneAllocator<P,B>` macro; perf-only pass). Those remain live audit rows in the steering-question survey response; each would warrant its own document if picked next.

---

## Recommended next steps (in execution order)

1. **Append to `gap_audit.md`** — one `[arch]` line under `## Closed`: "`tier` / `tiered_backend` / `tiered_heap` confirmed already SoC-separated by the topological audit; `tiered_heap.rs::for_tier` match remains the only realistic residual target, addressed in the new `[patch] Consolidate TieredHeap routing boilerplate` row below."
2. **Add a new audit row** to `gap_audit.md` and (optionally) `backlog.md`: `[patch] Collapse TieredHeap::alloc/free/realloc's 3× `for_tier` match into one routed macro at `tiered_heap.rs` to remove duplicated budget-only `debug_assert!` arms and per-method closure construction without changing codegen.`
3. **CHANGELOG entry** under `## Unreleased` → `### Audit`: "`docs/audit/2026-06-27-mnemosyne-topological-audit.md` written; the Heap/tier/tiered-backend triple is already SoC-separated; the residual `for_tier` match consolidation in `tiered_heap.rs` is the actionable cluster."
4. **(Gated on user sign-off) Execute the macro refactor** following the sketch in Finding 2; run the five-step verification plan; record the closure as another `[patch]` row in `gap_audit.md`.

---

## Appendix — Files reviewed (no edits)

| Path | Lines reviewed | Lines quoted |
|---|---|---|
| `crates/mnemosyne-heap/Cargo.toml` | 32 | full file (dependency graph only) |
| `crates/mnemosyne-heap/src/lib.rs` | 24 | full file |
| `crates/mnemosyne-heap/src/brand.rs` | 200 | `BrandedBlock`, `BrandedCell`, `scope` definition at lines 12-91, 96-167, 171-178 |
| `crates/mnemosyne-heap/src/heap.rs` | 147 | `Heap<'brand, P, B>` struct, `Send` impl, `alloc`/`free`/`realloc`/`alloc_init` bodies |
| `crates/mnemosyne-heap/src/raw_heap.rs` | 217 | full file (`alloc_inner`, `free_owned_unchecked`, `realloc_owned_unchecked`, `free_large_or_huge`) |
| `crates/mnemosyne-heap/src/tier.rs` | 124 | footer comment (lines 1-66), `tier_for` body (lines 73-89) |
| `crates/mnemosyne-heap/src/tiered_backend.rs` | 159 | dispatched-table comment (lines 1-43), `TierSelection` enum, `TieredBackend::for_tier` body |
| `crates/mnemosyne-heap/src/tiered_heap.rs` | 224 | `TieredHeap<'brand, P>` struct, `Send` impl rationale, `TieredBlock<'brand, T>` definition, `alloc`/`free`/`realloc` bodies, `scope_tiered` mint function |
| `crates/mnemosyne-heap/src/branded_box.rs` | 153 | full file (deferred — see "Borderline" above) |
| `gap_audit.md` | n/a | the closed `[arch] Consolidate public heap construction` row context |
| `complexity_audit.md` | n/a | the workspace map (10 crates, updated for the heap consolidation) |
| `checklist.md` | n/a | confirm the heap rows close to the audit-grain baseline |
| `gap_analysis_external.md` | n/a | ADR-0002 reference cross-check |
| `backlog.md` | n/a | Stage-D1 GPU slice — confirms `tier`/`MemoryBackend` are the deliberate surfaces |
| `crates/mnemosyne-backend/src/lib.rs`, `crates/mnemosyne-backend/src/recorders.rs`, `crates/mnemosyne-arena/src/lib.rs`, `crates/mnemosyne-local/src/lib.rs` | n/a | cross-crate import-graph check to confirm no audit surface crosses crate boundaries other than through the SSOT imports in `Cargo.toml` |
