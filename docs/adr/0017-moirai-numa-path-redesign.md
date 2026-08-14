# ADR 0017 — Moirai NUMA path integrity redesign

- Status: **Accepted**
- Date: 2026-07-15
- Drivers: P0 integrity defects in `moirai-iter/src/numa.rs` (4 distinct violations); zero external consumers of this API surface; redundant infrastructure already exists in Themis (topology/placement), Mnemosyne (NUMA-aware allocation), and Moirai executor (NUMA-aware work-stealing).
- Anchors: `atlas/docs/adr/0002-heterogeneous-topology-law.md` (Themis owns topology vocabulary, Mnemosyne owns allocation, Moirai owns execution); `repos/moirai/moirai-iter/src/numa.rs` (target); `repos/mnemosyne/crates/mnemosyne-arena/src/numa.rs` (existing NUMA node query); `repos/mnemosyne/crates/mnemosyne-arena/src/segment/pool/numa_bucket.rs` (NUMA-aware segment pools); `repos/themis/src/branded/sync_region.rs` (NumaNodePlacement split); `repos/themis/src/branded/thread_local.rs` (ThreadLocalPlacement pin_local); `repos/moirai/moirai-executor/src/schedule/runtime/types.rs:162` (worker_numa_nodes).
- Supersedes: the implicit assumption in `moirai-iter` that an iterator crate owns raw `mmap`+`mbind` allocation and NUMA-aware iteration.
- Index: docs/adr/INDEX.md#ADR-0017

## Context

### Defect inventory

The `moirai-iter/src/numa.rs` module (334 lines) exposes a `NumaContext`, `NumaIter`, and raw memory management through `numa_alloc`/`numa_free`. It was apparently split out of a larger Moirai 0.x codebase before the cross-crate ownership map was settled, and it now sits in the wrong crate with the wrong abstractions. Four distinct P0 defects:

1. **MOI-NUMA-001 — NumaPolicy stored but never applied (HARD: fake generics / dead path)**

   `NumaContext` stores `policy: NumaPolicy` (with variants `Local`, `Interleaved`, `Bind(usize)`, `Preferred`) but `execute_iter`, `map_owned_numa_batches`, and `reduce_owned_numa_batches` never branch on it. Every call site passes a policy that is silently ignored — the policy enum is a dead parameter collected at construction and never inspected. This is dead code that creates false architectural promises.

2. **MOI-NUMA-002 — Raw mmap+mbind allocation in iterator crate (HARD: architecture violation)**

   `NumaContext::numa_alloc` performs `libc::mmap` + `libc::syscall(SYS_mbind, ..., 2, &nodemask, 64, 0)` with hardcoded magic numbers (`2` = `MPOL_BIND`, `64` = maxnode bit count, `nodemask = 1u64 << node`). `numa_free` calls `libc::munmap`.

   Per ADR 0002 (heterogeneous topology law), Mnemosyne owns memory allocation across all NUMA nodes; it already stores `numa_node: u32` on every `Segment`, has per-NUMA-node segment pools (`numa_bucket.rs` with `NUMA_BUCKETS=16` and `steal_from` for cross-node fallback), and queries topology through Themis. An iterator crate should never perform raw OS-level memory management.

3. **MOI-NUMA-003 — Sequential single-threaded "batch" functions (HARD: fake parallelism)**

   `map_owned_numa_batches` and `reduce_owned_numa_batches` are sequential single-threaded loops that chunk the input `Vec` into batches but never spawn threads, dispatch to workers, or use the thread pool. They are named "batch" and live in a "parallel" module tree, yet execute entirely synchronously on the calling thread.

4. **MOI-NUMA-004 — Fake async fn surface with discarded errors (HARD: mock-like API)**

   `NumaIter::for_each`/`map`/`reduce` are `async fn` with zero `.await` points — they are entirely synchronous. Errors are discarded: `execute_iter`'s `Result` return is swallowed by `let _ =` (for_each) and `.unwrap_or_default()` (map). This creates a mock-like facade: the async keyword suggests non-blocking I/O or parallelism, the `Result` type suggests fallibility, yet neither property exists in the execution path.

### Existing correct infrastructure

The stack already has working NUMA-aware subsystems in the correct crates:

| Capability | Owner crate | Status |
|---|---|---|
| Topology detection (`CpuTopology`, `NumaNodeId`) | `themis/src/topology/` | ✅ Production, with cache levels, distance matrices, adjacent-node tables |
| NUMA node query (`current_numa_node()`) | `themis/src/query/cache.rs` | ✅ Thread-local cached, refreshable |
| NUMA node placement (`NumaNodePlacement`) | `themis/src/branded/sync_region.rs` | ✅ Split, split_with, split_static, Const/ThreadLocal variants |
| Thread-local NUMA pinning (`pin_local`) | `themis/src/branded/thread_local.rs` | ✅ Produces `ThreadLocalNumaPlacement` |
| NUMA-tagged allocation (`Segment.numa_node`) | `mnemosyne-core/src/types/segment.rs` | ✅ Every segment records its NUMA node |
| Per-NUMA-node segment pools | `mnemosyne-arena/src/segment/pool/numa_bucket.rs` | ✅ 16 buckets, steal_from for cross-node fallback |
| NUMA-aware work-stealing | `moirai-executor/src/schedule/runtime/` | ✅ `worker_numa_nodes` array drives victim selection |
| Parallel iteration with auto-Adaptive policy | `moirai-parallel/src/ops.rs` | ✅ Production work-stealing thread pool |

### Consumer impact

Verified zero external consumers of moirai-iter's NUMA API:
- `kwavers` has its own `ArenaLayoutNumaPolicy`/`NumaAwareAllocator` — does not use `moirai_iter::numa`
- `apollo`, `gaia`, `helios` depend on `moirai-iter` crate but do not import `pub mod numa`
- The sole benchmark at `moirai/benchmarks/benches/numa_context_comparison.rs` benches `NumaContext::new(NumaPolicy::Local)` + single-threaded `.execute()` — functionally a no-op wrapper benchmark
- `moirai/tests/src/lib.rs` integration test does not reference the `numa` module
- `moirai/benchmarks/tests/benchmark_contracts/iter_source_contracts.rs` does not reference the `numa` module

## Decision

**Delete `moirai-iter/src/numa.rs` entirely.** The NUMA module in moirai-iter is not salvageable by refactoring — its four defects are architectural, not cosmetic. The capabilities it incorrectly claims to provide (NUMA-aware allocation, NUMA-aware iteration) are already provided correctly by Mnemosyne and Themis respectively. The capabilities it incorrectly represents (parallel batch iteration via sequential loops, async iteration via sync functions) are already provided correctly by Moirai's own `ParallelContext` and `moirai-parallel` crate.

### Rationale for deletion over retention/refactor

| Option | Assessment |
|---|---|
| **Delete** | Correct. Removes 334 lines of dead/fake code, eliminates HARD integrity violations, no consumer impact. |
| **Redirect via Themis/Mnemosyne** | Would keep a type with no real users but swap its internals. Net zero improvement — the callers that would benefit already use the real infrastructure directly. Creates an unnecessary forwarding layer. |
| **Retain + fix async surface** | Fixes MOI-NUMA-004 but leaves MOI-NUMA-001/002/003 intact. Cannot address the architecture violation (mmap in iterator crate) without moving to Mnemosyne. |

### Migration of benchmark

The sole consumer is `moirai/benchmarks/benches/numa_context_comparison.rs`, which benchmarks `NumaContext::new(NumaPolicy::Local).execute(|| ... )`. This is a single-threaded identity wrapper; the benchmark measures overhead of constructing a `NumaContext` that does nothing NUMA-specific. Delete this benchmark — it measures nothing real.

### What consumers should use instead

- **Per-node memory allocation**: `mnemosyne` with its NUMA-tagged segments (already the default for all allocations through Mnemosyne). To query the current thread's NUMA node: `themis::current_numa_node()`.
- **NUMA-aware thread placement**: `themis::ThreadLocalPlacement::pin_local()` for thread-confined placement, `themis::SyncRegionPlacement::split()` for per-node split placement with compile-time brand verification.
- **NUMA-aware parallel iteration**: `moirai_parallel` with its `ParallelIterator`, `ParallelSliceMut`, and auto-Adaptive policy. The Moirai executor's `worker_numa_nodes` already guides work-stealing victim selection across NUMA domains.
- **Topology queries**: `themis::CpuTopology::detect()` for the full CPU/NUMA topology.

## Consequences

1. **Positive**: Removes 334 lines of dead, integrity-violating code from the moirai-iter crate. Closes 4 P0 defects (MOI-NUMA-001 through 004) in a single deletion.

2. **Positive**: Eliminates the unsafe `libc::mmap`/`libc::syscall(SYS_mbind)` path from an iterator crate, where it was architecturally unsound per ADR 0002.

3. **Positive**: Eliminates the fake `async fn` surface that could mislead future developers into thinking `NumaIter::map().await` is async or NUMA-aware.

4. **Neutral**: The `pub mod numa` re-export in `moirai-iter/src/lib.rs` is removed. This is a [major] change to `moirai-iter`'s public API if any external crate imports it, but verified zero consumers exist.

5. **Neutral**: `NumaPolicy` type is removed. Future callers needing policy specification should use the Themis placement vocabulary (which brands the node ID at compile time rather than carrying a dead enum).

6. **Positive**: Benchmarks at `benchmarks/benches/numa_context_comparison.rs` that measured nothing are removed alongside.

## Verification plan

1. `cargo check -p moirai-iter` — clean, no dead-code warnings from removed module.
2. `cargo nextest run -p moirai-iter` — all existing parallel/async/stream iterator tests still pass.
3. `cargo check -p moirai-executor -p moirai-parallel` — unaffected.
4. `cargo check --workspace` — no crate references the removed `pub mod numa` from moirai-iter.
5. Delete `benchmarks/benches/numa_context_comparison.rs` and `benchmarks/tests/benchmark_contracts/` tests for bench-suite cleanliness.
