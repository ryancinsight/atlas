# ADR 0002 (atlas): Heterogeneous compute & memory topology law

- Status: Accepted
- Date: 2026-06-11
- Class: [arch] — cross-repo ownership map for CPU/GPU/TPU execution over the
  full memory hierarchy (registers, shared memory, L1/L2/L3 cache, NUMA DRAM,
  HBM, GDDR, pinned host, persistent)

- Index: docs/adr/INDEX.md#ADR-0002
## Context

The stack targets CPU (SIMD + MIMD), GPU (wgpu + CUDA via hephaestus), and —
long-term — TPU, over heterogeneous memory: per-core caches (L1/L2/L3), NUMA
DRAM, device HBM/GDDR, GPU register files and shared memory, pinned host
staging. Without one ownership map, tier knowledge would scatter across
consumers and drift.

Two physical facts bound what software can own, and this ADR encodes them
rather than pretending otherwise:

1. **Warp scheduling is hardware.** SM warp schedulers issue warps; no host
   runtime schedules individual warps. The software-ownable layer is *launch
   shaping*: occupancy-driven grid/block dimensions, register/shared-memory
   budgets per kernel, stream orchestration, and (advanced) persistent
   kernels with device-side work queues. "Moirai supports warp scheduling"
   means moirai owns this shaping/occupancy policy layer.
2. **GPU register allocation is the kernel compiler's.** PTX→SASS register
   assignment happens at compile/JIT time; registers are not heap-allocatable.
   "Register files through mnemosyne" means mnemosyne owns the **kernel
   resource budget** vocabulary and accounting — registers/thread and
   shared-memory/block as typed quantities — which moirai's occupancy planner
   consumes and hephaestus passes to kernel compilation (cutile). Mnemosyne
   additionally owns literal allocation for GDDR/HBM device pools, pinned
   host staging, and shared-memory arena budgets.

## Ownership map (SSOT per concern)

| Concern | Owner | Form |
| --- | --- | --- |
| Tier/topology **vocabulary**: `MemoryTier` (+ `Gddr`, `HostPinned`, device `Registers`/`SharedMem` tiers), `CacheLevel` (L1/L2/L3), NUMA, **GPU topology** (SM count, warp width, regs/SM, shared-mem/SM), **TPU topology** (cores, HBM) | **themis** | typed law, no state |
| Host allocation (NUMA-aware), **device pools (HBM/GDDR)**, pinned staging, **kernel resource budgets** (regs/thread, shared/block) | **mnemosyne** | allocator + budget accounting behind `MemoryBackend`/policy seams |
| SIMD lanes (CPU data-parallel) | **hermes** | arch-marker kernels |
| MIMD threads + **GPU launch shaping**: occupancy planner (from themis GPU topology + mnemosyne budgets), grid/block selection, stream co-scheduling, persistent-kernel work queues | **moirai** | ExecutionPolicy/scheduler layer over hephaestus |
| Device backends: wgpu, CUDA (cuda-oxide + cutile, hephaestus ADR 0001), **TPU via PJRT C API** (dynamic load, long-term) | **hephaestus** | `ComputeDevice` impls; placement-aware allocation (`PlacementHint` from themis) |
| CPU array kernels, **cache-aware tiling/blocking** (tile sizes from themis `CacheLevel`) | **leto** | const-generic tiles; criterion-gated per performance_engineering |
| Tensor/autodiff composition over all backends | **coeus** | unchanged seams |

Dependency direction is unchanged: themis ← {mnemosyne, moirai, hephaestus,
leto consumers}; nothing flows upward.

## Decisions

1. **themis extends the law**: add `MemoryTier::Gddr` and `HostPinned`;
   add device-side tiers (`Registers`, `SharedMem`) as *budgeted* tiers
   (queryable capacity, non-allocatable by host); add `GpuTopology` and a
   minimal `TpuTopology` snapshot alongside `CpuTopology`. Detection may be
   provider-fed (hephaestus reports device properties into themis types) —
   themis stays stateless law.
2. **mnemosyne** implements device pools/pinned staging keyed by
   `MemoryTier` + `PlacementHint`, and a `KernelResourceBudget` type
   (regs/thread, shared/block, themis-typed) with occupancy-relevant
   accounting. No pretense of allocating registers.
3. **moirai** adds the GPU execution-shaping stage: an occupancy planner
   (themis `GpuTopology` × mnemosyne `KernelResourceBudget` → grid/block
   shape), stream/queue co-scheduling with the work-stealing host scheduler,
   and persistent-kernel work distribution as the advanced stage.
4. **hephaestus** threads `PlacementHint` through `ComputeDevice` allocation
   (HBM vs GDDR vs unified vs pinned), reports device topology into themis
   types, and accepts launch shapes from moirai's planner instead of its
   current fixed 256-wide workgroups. TPU lands as `hephaestus-tpu` over the
   PJRT C API (dlopen, no SDK to compile) only when a consumer drives it —
   the `ComputeDevice` seam already accommodates it.
5. **leto** applies cache-aware tiling (const-generic tile sizes selected
   from themis `CacheLevel` data) to matmul/reduction hot paths — strictly
   gated on criterion baselines per the performance gate (no unmeasured
   "optimization").

## Consequences

- Each repo's backlog carries its slice (themis/mnemosyne/moirai/hephaestus/
  leto updated in the same change as this ADR).
- The first measurable increments: leto criterion baselines (prerequisite for
  tiling), themis tier/topology vocabulary, hephaestus placement-aware
  allocation signature.
- TPU is explicitly long-term and driver-gated; no speculative scaffolding.
