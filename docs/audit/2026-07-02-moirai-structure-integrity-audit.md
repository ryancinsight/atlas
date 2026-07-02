# 2026-07-02 moirai audit — structure, integrity, memory, perf (all 16 crates)

Five-agent read-only fan-out over the moirai workspace (~64k lines), primed to
skip the 18 settled adversarial concurrency rounds (SSOT:
`repos/moirai/docs/concurrency_audit.md`). Lens: DRY/SSOT/SoC, integrity
(mocks/stubs in delivered code), memory efficiency, performance, dead-code
hygiene, plus cross-repo seams vs themis / melinoe / hephaestus.

Two confirmed **shippable correctness bugs are already fixed** (moirai commit
`a07a2cd`, scoped to moirai-async): RateLimiter `new(0)` underflow (→ ~4.3B
permits) and the async executor poll-after-completion panic (stale reactor
waker re-enqueuing a finished task). Everything below is filed for the moirai
owner as Definition-of-Ready backlog — much of it is `[arch]` and the repo is
under concurrent edit (a Kwavers-integration session holds uncommitted
moirai-parallel WIP), so it must be sequenced with that work, not raced.

## Highest-leverage: dead/mock code removal (net-subtractive, ~thousands of lines)

- **moirai-iter (~14.6k lines) — prune, extract 4 real pieces. [arch, ADR]**
  Its `ParallelIterator` executes **sequentially** on the caller
  (`parallel/sources.rs` `VecParIter::drive` recursively splits then runs both
  halves inline); "SIMD" loads an unused `_mm256` intrinsic then scalar-loops
  (`iter_ops.rs`); multi-system reports **hardcoded 0.5/0.3 utilization**;
  distributed/async-terminal ops are "execute locally — for now" placeholders
  or per-element `block_on`. **Zero production consumers** anywhere in atlas
  (only the facade re-export, benchmarks, and an unused `let _iter` in an
  example). Contrast: **moirai-parallel is the real SSOT** — 79+ call sites
  across apollo/kwavers/CFDrs/helios/gaia. Plan: extract `par_sort*` (real,
  rebased onto `global()`/SyncTask, resolving the duplicate `ParallelSliceMut`
  name), `stream.rs::concurrent_map` → moirai-async, numa/prefetch primitives
  if a consumer materializes; delete the rest; drop `iter` from `moirai`
  default features as the low-risk first increment.
- **moirai-core dead subsystems (~2500+ lines). [major]** `dtype/` (~600, zero
  consumers, contains a prohibited widen-to-f64 seam), `core::metrics/` (~700,
  duplicate of moirai-metrics AND moirai-executor's own, zero consumers),
  `security/` (~800, no executor invokes auditing — wire into spawn or delete),
  `wasm_executor.rs` (references a nonexistent `ExecutorError::QueueFull`, E0446
  private-type leak, JS worker `pop()` is `// simplified for brevity` — a
  feature gating non-compiling mock), `coroutine::CoroutineScheduler` (drops its
  own channel senders, `TaskId::new(0)` "real impl would…"), `ExecutorPlugin`
  (no registration, no invocation), no_std plumbing (unconditional
  `compile_error!` + `alloc::sync::mpsc` which doesn't exist — permanently dead).
- **moirai-executor `reactor.rs` — mock (`is_fd_ready_for_read` returns `true`),
  fully dead** (real reactor is moirai-pal). Delete it + the dead cluster
  (`TaskWaitFuture` unconstructable, `IoEvent`, `WorkerId`). [minor]
- **moirai-pal reactor task subsystem (~350 lines incl. unsafe, noop raw waker)
  — dead**; WASM reactor `poll_events` always returns empty while reporting
  `Ok(())` (stub). [minor/major]
- **moirai-utils ~900+ dead lines**: `bits.rs` (std-method wrappers, type-suffix
  names, latent debug-panics), `random.rs`, `time.rs`, `backoff.rs`,
  `queue::RingBuffer` (`!Sync`, so its SPSC purpose is unusable), plus
  compat-alias re-exports (`SimdCounter::simd_utilization_ratio` "for
  compatibility", "Legacy re-exports"). [patch]

## SSOT duplication (consolidate to one generic + ZST policy)

- **5 ring-buffer implementations in moirai-core** (`communication::RingBuffer`,
  `channel::spsc` line-for-line clone, `memory::UnifiedRingBuffer` mutex-locked,
  `zero_copy::MemoryMappedRing` spin-locked, `channel::mpmc` Vyukov — only the
  last is a distinct algorithm). One SPSC ring + one Vyukov MPMC over a ZST
  wait-policy (the crate already has `ResultWaitPolicy`) covers all. [arch]
- **4 channel families + 3 duplicate error enums** (`ChannelError`,
  `UnifiedChannelError`, `ZeroCopyError` all repeat Full/Empty/Closed/WouldBlock)
  — only `MpmcChannel` is used by the live runtime. [arch]
- **Duplicate metrics primitives** core vs moirai-metrics; **duplicate
  AtomicCounter** moirai-sync vs moirai-utils; **3 cache-padded wrappers**
  in moirai-utils; **3 timer impls**; **verbatim freelist copy-paste**
  `memory/pool.rs` == `pool/stack.rs`; waiter-queue state machine cloned 4×
  across notify/semaphore/rwlock; per-work-class spawn boilerplate ×5;
  `Priority→usize` ×3; pal net WouldBlock scaffolding ×6. [patch/minor each]
- **utils is not functioning as the SSOT it claims** — siblings re-implement its
  exports (RingBuffer, AtomicCounter, backoff, timestamp) instead of consuming.

## Integrity (non-shippable but delivered mocks/placeholders)

`UdpTransport` send/recv return `Closed` while `supports(Remote)` is `true`
[major]; `Catch` combinator never catches + trait bounds make it
unconstructible; `TaskManager::cancel_task` no-op; executor & async `ExecutorStats`
counters (waker_notifications, io_operations, cpu/mem utilization) never
incremented — constants masquerading as telemetry; `Histogram::record` bucket
math collapses all sub-2^49 samples to bucket 0; many `*Config` knobs
(ExecutorConfig async_threads/queue caps/numa/preemption, TcpServerConfig
nodelay/keepalive/timeout, UdpConfig) accepted and silently ignored;
`TaskFuture`/`TaskFuture::poll` block inside poll and hang if re-polled.

## Memory

16 MiB-per-worker pre-allocated injector ring in moirai-executor (ignores the
queue-capacity config; ~256 MiB idle on 16 workers) [minor, wire
`max_global_queue_size`]; `UnifiedChannel` allocates an unreachable 2×cap
`MemoryPool` per channel; `LockFreeStack::new` eagerly materializes 65536 nodes;
bounded MPMC double-allocates a `VecDeque` alongside the lock-free ring; PubSub &
SecurityAuditor maps grow unboundedly; reactor hot loop allocates a fresh
1024-event Vec per `poll_events` (a reuse buffer exists but is dead); `Arc`
layers never cloned (`Box<[Arc<WorkerState>]>`, async sync primitives).

## Performance

Arc-waker allocated per poll per task (async executor) — build once at spawn;
reactor waker-map lock taken twice per event and held across two syscalls on the
interest-widening path (EPOLL_CTL_MOD/EV_ADD would be one); interest widening =
2 syscalls; fixed 10ms reactor poll timeout → 100 idle wakeups/s despite a
working `wake()`; broadcast recv linear-scans the message deque (dense seq → O(1)
index). All conservative — attach criterion baselines before changing.
The SeqCst schedule/park handshake is **load-bearing, confirmed, not to touch.**

## Cross-repo SSOT seams

- **themis (topology): CLEAN.** No hand-rolled cpuid/NUMA detection anywhere;
  moirai-scheduler and moirai-iter consume `themis::CpuTopology`/`current_numa_node`.
- **melinoe (branding): mostly clean**, one candidate — `moirai-parallel`'s
  `DisjointMutPtr` raw-pointer chunk splitter re-derives what melinoe's safe
  `WriterShard::chunks`/`PartitionPlan` already owns; consolidation review [minor].
- **hephaestus (GPU): significant.** moirai-gpu's `wgpu-backend` (wgpu **0.19**,
  no readback path, `available_devices: vec![] // Simplified`, fabricated
  MemoryInfo) **duplicates hephaestus's real wgpu-26 runtime downstream** —
  hephaestus already consumes moirai-gpu **planner-only** and owns its own
  runtime. Shrink moirai-gpu to its exemplary `occupancy.rs` planner (typed
  themis×mnemosyne intersection, closed-form-verified); delete the wgpu-backend
  modules; the default feature set currently enables the stale backend. [arch]

## Test quality

`tests/src/database_connection_pool_edge_tests.rs` (920 lines) has **zero
assertions** — it exercises a mock built inside the test file and `println!`s
stats; `principle_based_edge_tests.rs` (~1922) is ~60% self-referential property
tests over locally-defined types that never touch the moirai API, with
tautological `assert!(x.is_ok() || x.is_err())`, and six gate features default-off
so much never runs in CI. GPU crate tests are compile-only (`let _result = task`).
Rewrite as value-semantic against real moirai types or delete.

## Config hygiene

`.config/nextest.toml` uses `terminate-after = 1` (hard-kill at 30s, no
slow-marking band — deviates from the 30s-slow/60s-terminate policy);
edition 2021 / resolver 2 (stale); no `rust-toolchain.toml`; no
`[workspace.lints]`; dev `debug = true` (full DWARF) + release missing
`strip = "symbols"`; `#![deny(missing_docs)]` absent on transport/metrics/
python/gpu; phantom features across nearly every crate (`parallel`,
`mnemosyne-memory`, and in moirai-utils `simd` gates on `std` not on itself);
~30 blanket `#![allow(clippy::…)]` "temporarily" in moirai-core.

## Verified clean (do not re-chase)

The 18-round concurrency machinery is intact: SeqCst schedule/park handshake,
IdleBitset, LifoSlot, ScheduledJob drop discipline, Chase-Lev steal/reclaim,
FutexMutex, level-triggered epoll/kqueue/WSAPoll reactor, IoReactor RAII restore,
ipc SharedQueue hardening, BoundedMpmcQueue Vyukov protocol, TaskResultSlot.
moirai-tls (real rustls delegation), moirai-python (real thin PyO3), moirai-http
(real max_response_bytes budget), moirai-gpu occupancy planner, moirai-parallel
(entire crate incl. concurrent WIP), and utils SIMD are all genuinely real.
