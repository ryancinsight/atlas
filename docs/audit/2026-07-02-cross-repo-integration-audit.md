# 2026-07-02 cross-repo integration audit (7-repo core + stack-wide seams)

Six-agent read-only fan-out over eunomia, melinoe, themis, mnemosyne, hermes,
moirai, leto, hephaestus (+ apollo/coeus/gaia/consus/ritk/kwavers/helios where
they touch these). Focus: the **cross-acyclic integration graph** and SSOT
boundaries, plus per-repo quality. mnemosyne and moirai were deeply audited
earlier this session (see the 07-01 and 07-02 audit docs); this pass adds the
foundation/domain/integrator crates and the inter-repo seams.

## HEADLINE: the dependency graph is a proven DAG

Every atlas-sibling edge (normal + build + optional + dev) was parsed across all
repos. Edge list (crate-level, `→` = depends on):

```
eunomia   → ∅            melinoe → ∅            (foundation leaves)
themis    → melinoe(opt)                        (lateral, foundation)
mnemosyne → eunomia(opt), melinoe, themis
hermes    → eunomia, melinoe, mnemosyne(opt), themis      (⊥ moirai)
moirai    → melinoe, mnemosyne(opt), themis               (NO eunomia edge)
leto      → eunomia, hermes, melinoe, mnemosyne(opt), moirai(opt), themis(opt)
hephaestus→ eunomia, hermes, leto, melinoe, mnemosyne, moirai, themis
```

No back-edge from any foundation/infra crate to a crate above it. The only
foundation→foundation edge (themis→melinoe) is lateral and does not close a
cycle (melinoe→∅). No dev-dependency cycles. **Verdict: acyclic. Cross-acyclic
integration holds at the crate level.** The suspected mnemosyne↔themis and
mnemosyne↔melinoe cycles were phantom features (see below), not real edges.

## Per-repo verdicts (the 7 core)

- **eunomia** — clean foundation leaf (RealField/Scalar SSOT); no atlas deps, no
  arena/pool slop. Phantom `parallel`/`mnemosyne-memory` features (below).
- **melinoe** — FULLY SOUND (every branded/cell/token/atomic type's variance
  traced clean; no covariant-Copy-interior-mut GhostCell hole). FIXED this
  session: phantom features removed, nextest budget committed (commit `e39c261`,
  branch `fix/phantom-features`). Follow-ups: indexed disjoint-shard API for
  moirai-parallel (below); `GuardedCell`/`ReentrancyCell`/`BrandedAtomic` are
  sound but unconsumed seams — file in mnemosyne to close the seam→consumer
  trace or mark for removal.
- **themis** — clean topology SSOT; no melinoe re-derivation (consumes it), and
  it exposes borrowed accessors so consumers need not copy. FIXED: phantom
  features removed + synthetic-cache/distance provenance documented (commit
  `b3b12b7`, branch `fix/phantom-features-provenance`).
- **hermes** — SIMD SSOT; eunomia migration COMPLETE (hermes-numeric deleted,
  imports re-pointed, no residual). No fake generics, correct runtime ISA
  gating, native-precision kernels, zero-copy TensorView. IN PROGRESS this
  session (agent, branch `fix/simd-safety-and-hygiene`): phantom-feature
  removal + `// SAFETY:` on the ~50 target_feature intrinsic fns + edition
  decision.
- **leto** — geometry/ndarray-replacement domain crate; clean core (no fake
  generics, zero-copy well applied, SIMD→hermes and parallelism→moirai both
  correctly delegated). UNDER CONCURRENT EDIT (24 files, geometry primitives
  landing) — read-only. Headline finding filed below (eunomia Scalar rebase).
- **hephaestus** — clean GPU integrator; moirai-gpu consumed PLANNER-ONLY
  (confirmed — its wgpu-0.19 backend is never compiled in), no capability
  duplication, no dependency bloat, honest CUDA-off stubs. `[patch]` hygiene
  only (3 missing SAFETY comments, nextest slow-timeout gap, phantom features,
  a 3302-line python god-file) — filed for its owner (1 file under concurrent
  edit).

## Cross-repo [arch]/[major] items — FILED (coordination-gated, not deferrable-away)

These are genuine required enhancements, but each spans repos under concurrent
edit or outside the 7-repo core, and each requires the co-evolution protocol
(upstream-first, coordinated consumer update, contract test). Per
architecture_scoping + concurrent_agents they are filed Definition-of-Ready with
owner/driver, NOT done piecemeal mid-flight.

- **CR-1 [arch] apollo-ghostcell duplicates melinoe branding.**
  `apollo/crates/apollo-ghostcell/src/lib.rs` is a full standalone GhostCell
  re-impl (`GhostToken<'brand>`, `GhostCell<'brand,T>`, invariant brand) with
  ZERO melinoe dep, while melinoe ships exactly this. Delete apollo-ghostcell;
  consume `melinoe::MelinoeCell`/token API. Owner: apollo; driver: melinoe SSOT.
- **CR-2 [arch] three LIBRARIES register `#[global_allocator]`.** moirai (lib),
  ritk-core, cfd-core each set a `#[global_allocator]` behind a
  `mnemosyne`/`mnemosyne-alloc` feature. Only binaries may register a global
  allocator. Move the static to each workspace's `-cli`/`-py`/binary crate;
  keep the library feature as "link mnemosyne as allocator type" only. leto and
  hermes already do this correctly (link, do not register).
- **CR-3 [major] kwavers is the sole rayon holdout.** rayon→moirai is COMPLETE
  everywhere except kwavers (13 crates declare rayon, ~40 src files use
  `par_iter`/`ThreadPoolBuilder`/`current_num_threads`; `kwavers-gpu` also uses
  raw `std::thread::spawn`). Migrate to moirai `par_*`/`for_each_index_with`.
  (CFDrs/consus rayon mentions are doc-comments only — no live dep. ndarray's
  internal `rayon` feature is the sanctioned exception.) Owner: kwavers.
- **CR-4 [major] standalone Scalar traits bypass eunomia.**
  `coeus-core/src/dtype/traits.rs` (`Scalar`/`Float`/`FloatOps`, ~50 widen-to-f64
  seams) and `leto-ops/src/domain/scalar.rs` (`Scalar`/`RealScalar`, and
  leto-ops does not even depend on eunomia) re-declare eunomia's
  `NumericElement`/`RealField`. Rebase onto `eunomia::{Scalar,RealField}` as
  supertraits, keeping only the BLAS/kernel methods eunomia does not own. gaia
  already does this correctly (`Scalar: eunomia::RealField`). Owner: coeus, leto;
  driver: eunomia SSOT. NOTE: moirai-core's `FloatDtype` is a separate decision —
  moirai has no eunomia edge; adding one is layering-valid but is an
  execution⊥numeric design call, not a trivial swap.
- **CR-5 [major] hand-rolled arenas duplicate mnemosyne.** apollo `ComposeArena`
  (thread-local bump allocator for FFT scratch) and kwavers `PerfMemoryPool` +
  `MemoryOptimizer` (frame-local bump + custom-aligned `std::alloc`) duplicate
  mnemosyne's arena/aligned-alloc. Migrate to mnemosyne's arena API or formalize
  a documented sub-SSOT delegation. (No bumpalo/typed-arena/slab anywhere;
  gaia `VertexPool` is Vec-backed object cache — not a raw-alloc duplication.)
- **CR-6 [major] hand-rolled SIMD dispatch duplicates hermes.** apollo-fft
  (~28 files), CFDrs cfd-core simd, kwavers-math/solver, and moirai-utils simd
  hand-roll `std::arch` intrinsics + `is_*_feature_detected!`. Domain FFT/CFD/FDTD
  kernels may justify local kernels, but the ISA detection/dispatch machinery
  should consume hermes; moirai-utils' generic add/mul/dot belongs in hermes.
  (eunomia's `packed/intrinsics` is the sanctioned numeric-core exception.)
- **CR-7 [minor] moirai-parallel `DisjointMutPtr` should use melinoe's
  `WriterShard::chunks`.** `moirai-parallel/src/melinoe_ext.rs` re-derives
  disjoint sub-slices via `from_raw_parts_mut` that melinoe already provides
  safely. melinoe should upstream an indexed disjoint-shard accessor
  (`WriterShard::chunk_at(index)` / a `ParChunks::get`) so moirai deletes
  `DisjointMutPtr` and melinoe's own driver stops hand-rolling the same unsafe.
  Owner: melinoe (additive) + moirai (consumer).
- **CR-8 [minor] NUMA topology descriptors re-describe themis.** moirai-iter
  `NumaTopology` and kwavers-core `NumaTopology` are separate structs for layout
  themis owns (moirai-scheduler's `CpuTopology` is a documented ACL adapter —
  acceptable). Consolidate onto a themis descriptor. Owner: moirai, kwavers.
- **CR-9 [major] geometry Point/Vector types outside leto.** kwavers-driver,
  kwavers-therapy, ritk-spatial define their own Point/Vector. Consume leto
  geometry (ritk's are const-generic `Point<const D>` — verify the
  dimension-generic seam before consolidating). Owner: per-repo.

## Phantom-feature census

The `mnemosyne-memory`/`parallel` feature pair is REAL in ~8 crates (leto,
hermes-simd-core numa, moirai-core/executor/scheduler, hermes-simd facade
forward) and PHANTOM (`= []`, gate nothing) in ~40 (eunomia, themis, melinoe,
hermes leaves, apollo's ~22 crates, moirai's leaf crates, hephaestus wgpu).
FIXED this session in the clean 7-core repos: themis, melinoe. IN PROGRESS:
hermes leaves. COORDINATED FOLLOW-UP: eunomia's phantom `parallel`/
`mnemosyne-memory` are *forwarded* by hermes-simd/hermes-simd-intrinsics, so
removing them is a coupled eunomia+hermes change (do after the hermes hygiene
branch lands). Remaining ~35 phantom declarations (apollo, moirai leaves,
hephaestus) are filed for those repos' owners.

## Version skew

mnemosyne/moirai/themis git-rev pins diverge across consumers (hermes/leto pin
`1e014d25`, apollo `938d0c2b`, others track main), but every consumer workspace
`[patch]`-redirects all `github.com/ryancinsight/*` to `../<repo>` path deps, so
in the synchronized meta-repo checkout the skew is INERT — all resolve to one
tree. Real hazard only for a downstream git-source build without those patches,
or a committed Cargo.lock pinning a stale rev. The leto→themis "skew" is a
feature-set opt-out (leto uses themis `default-features=false` to avoid a second
melinoe resolution), not a version skew. Recommend pinning the stack to a
coherent rev set as an upstream co-evolution item.

## Verified clean (do not re-chase)

Acyclic graph; themis topology (no re-impl outside themis); allocation (no
GlobalAlloc/arena duplication in the 7-core; gaia VertexPool is Vec-backed);
gaia correctly extends `eunomia::RealField`; hermes eunomia-migration complete
with no fake generics; melinoe variance soundness (all 11 branded types);
hephaestus moirai-gpu-planner-only boundary; every 7-core repo's unsafe
FFI/SIMD is SAFETY-documented except the hermes intrinsic fns (in progress) and
the 3 hephaestus sites (filed).
