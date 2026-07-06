# ADR 0003 — Secure parallelization of accelerator device access

Status: Proposed
Date: 2026-06-16
Relates to: ADR 0001 (GPU/accelerator substrate), ADR 0002 (heterogeneous topology law)
Affected crates: moirai, melinoe, hephaestus (primary); themis, mnemosyne (supporting)

## Context

Real-GPU validation of `hephaestus-cuda` (the only place in the stack where CUDA
actually runs, because building cutile-rs requires `CUDA_TOOLKIT_PATH`) surfaced
two distinct classes of defect. They must not be conflated:

1. **Symbol-resolution fault (fixed, not a parallelization issue).**
   `cuda_core::sys::cuDeviceTotalMem_v2` is an unresolved dynamic symbol in the
   cutile-rs binding; calling it faults (`0xc0000005`). The device-family
   `cuDeviceGetAttribute` and the memory-family `cuMem*` entry points resolve
   correctly. Fix: query total memory via `cuMemGetInfo_v2` (current-context,
   memory family) instead of `cuDeviceTotalMem_v2`. Verified on real hardware.

2. **Inter-process CUDA-initialization race (the subject of this ADR).**
   Under `cargo nextest run --features cuda` (one process per test) the suite
   faults `0xc0000005` during device acquisition. Bisection established:

   | Configuration | Result |
   | --- | --- |
   | 16 threads acquiring the device + transferring, **one process** | **pass** |
   | `nextest` default parallelism (many processes) | fault |
   | `nextest -j2` (two processes) | fault |
   | `nextest -j1` (serial) | **83/84 pass** (1 unrelated logic bug) |

   Conclusion: **intra-process concurrent device acquisition is already safe;
   the fault is purely concurrent CUDA *context initialization* across separate
   OS processes** contending for one GPU. The fault is a segmentation violation
   inside the driver/cutile-rs init path, not a returnable `CUresult`, so it
   cannot be caught and retried — it must be *prevented*.

A blocking OS file lock around init would prevent the race but contradicts the
stack's design goals: moirai is a **lock-free unified scheduler/router** whose
stated target is "a single scheduler hierarchy that can grow into GPU, TPU, NPU
… without duplicating algorithms or fabricating execution" (moirai README §7).
The correct fix removes the *need* for N processes to initialize CUDA at all,
rather than serializing N inits behind a mutex.

## Forces (grounded in the current code)

- **melinoe is intra-process only.** Its guarantee is an invariant `'brand`
  lifetime (`PhantomData<fn(&'brand ()) -> &'brand ()>`), a compile-time
  construct with no runtime representation; it cannot be serialized or shared
  across a process boundary. melinoe therefore *cannot by itself* coordinate the
  inter-process race. It is the right tool for the *intra-process* sub-problem
  (single-writer / multi-reader device-buffer ownership — its planned Stage D1).
- **moirai already owns the cross-process substrate.**
  `moirai-core/src/ipc.rs` provides `SharedMemory` (POSIX `shm_open`/`mmap`;
  Win32 `CreateFileMappingW`/`MapViewOfFile`) and a lock-free `SharedQueue<T>`
  (`create`/`open`/`send`/`recv`) laid out inside a shared segment. This is the
  message-passing primitive the solution needs.
- **moirai already has the route metadata, unconsumed.**
  `SchedulerRoute::Accelerator` with `AcceleratorKind::{Cpu,Gpu,Tpu,Npu}` exists
  as sealed ZST policies, but no backend consumes it; GPU co-scheduling is the
  open "Stage E". The substrate to admit GPU work through the unified scheduler
  is already designed — it is not wired to a device.
- **Mutual exclusion of init is inherently not lock-free**, but *single
  ownership* is: if exactly one entity ever initializes/holds the context, there
  is no init contention to serialize, and work submission to it is lock-free
  message passing.

## Decision

Adopt a **single-owner device context with lock-free cross-process work
submission**, realizing moirai's unified-scheduler vision for the accelerator
route. No file lock; no per-process context.

1. **One context owner per (GPU, machine).** Exactly one process retains the
   CUDA primary context. Ownership is claimed **lock-free** via a CAS on an
   `AtomicU64` owner-slot in a named `moirai` `SharedMemory` segment (first
   successful CAS wins; losers become clients). No process other than the owner
   ever calls `cuInit`/context-create, so the inter-process init race is
   eliminated *by construction*.

2. **Clients submit GPU work via moirai's lock-free cross-process queue.**
   Extend `SharedQueue` from SPSC to MPSC (multiple client producers, the owner
   as single consumer) for the accelerator work channel. Submission is a
   lock-free enqueue of a fixed-format, archive-owned descriptor (consistent
   with moirai-transport's existing "no pointers cross a boundary; bytes only"
   invariant). The owner drains the queue and dispatches onto its context.

3. **Intra-process device ownership is branded by melinoe (Stage D1).** Within
   the owner process, the context and device buffers are shared across worker
   threads using melinoe tokens: a `SyncRegionToken<'brand>` carries the
   single-writer capability (exclusive device mutation / kernel launch), and
   `SharedReadToken<'a,'brand>` fans out concurrent device reads — exclusivity
   proven at compile time, zero runtime cost. This is the `DeviceBuffer<'brand,T>`
   pattern named in the hephaestus README and melinoe backlog.

4. **The unified scheduler consumes `SchedulerRoute::Accelerator`.** GPU work is
   admitted through moirai's `HybridRouter` like any other work class; the router
   delivers it to the local owner thread or, from a client process, onto the
   MPSC shared queue. CPU and GPU work live under one scheduler — the stated
   goal — instead of a separate ad-hoc GPU path.

5. **Ground and verify the lock-free core.** moirai's Chase-Lev deque
   (`moirai-scheduler/src/deque.rs`) uses a platform-conditional fence discipline
   (x86 `Release`; non-x86 `Relaxed` + `fence(SeqCst)`) that is correct but
   **uncited and not model-checked**. Cite Lê, Pop, Cohen & Nardelli, *Correct
   and Efficient Work-Stealing for Weak Memory Models* (PPoPP 2013) — the
   reference C11 Chase-Lev whose fence placement this matches — and add a `loom`
   exhaustive-interleaving test (required by the stack's concurrency standard:
   "lock-free/atomics only with written justification, verified by loom").
   Evaluate Wang et al., *BWoS: Formally Verified Block-based Work Stealing*
   (OSDI 2023) as the block-partitioned successor that lowers owner/thief
   contention — the "improve upon Chase-Lev from the latest research" track.

## Why not the alternatives

- **OS file/named-mutex lock around init** — works, but is a blocking lock on
  the device-acquisition hot path, foreign to the lock-free design and leaves N
  redundant per-process contexts. Rejected as the architecture (retained only as
  the interim test mitigation; see Consequences).
- **melinoe-only branding** — cannot cross processes; solves the intra-process
  sub-problem only. Adopted *as part of* the solution (point 3), not as the whole.
- **Per-process context + retry** — the fault is an uncatchable SIGSEGV, not a
  `CUresult`; retry is impossible.

## Consequences

- The inter-process init race is removed by construction; GPU work is unified
  under moirai's scheduler (realizes Stage E); device-buffer aliasing is a
  compile error (melinoe Stage D1).
- **Interim mitigation already in place:** `hephaestus/.config/nextest.toml`
  serializes the `hephaestus-cuda` test group (`max-threads = 1`). This stays as
  defense-in-depth until single-owner lands, then becomes redundant for
  correctness (kept only as a resource-contention guard).
- New indirection: cross-process GPU work routes through the owner. Justified by
  correctness and the unified-scheduler goal; latency measured against the
  direct path before/after.
- **Supporting roles (explicitly not the locus of this fault):** themis already
  supplies the topology the owner uses for launch shaping (no change required);
  mnemosyne owns device-memory pools in the owner process and the byte-archive
  handoff that moirai-transport already mandates. Neither needs a change to fix
  the race; fabricating changes there would be scope inflation.

## Staged plan (each stage independently verifiable)

1. **Done.** Diagnosis; `cuMemGetInfo_v2` symbol fix; real `cuDeviceGetAttribute`
   topology (replacing hardcoded placeholders); nextest serialization mitigation.
2. **moirai [patch] — substantially done; loom pending.** A new concurrency
   stress test (`moirai-scheduler/tests/deque_concurrency.rs`, single-owner /
   multi-thief, asserting exactly-once consumption) **reproduced a real
   safety violation**: under multi-thief contention + ring wraparound the
   `ChaseLevDeque` duplicated one item and lost another. Root cause confirmed as
   predicted below: `steal`/`steal_batch_with` read the value *after* the
   claiming CAS and lacked the inter-load `SeqCst` fence. **Fixed** by adopting
   the canonical Lê-Pop-Cohen-Nardelli form — `SeqCst` fence between the `top`
   and `bottom` loads, and read-the-value-*before*-the-CAS (so a successful CAS
   proves no wraparound overwrite); the batch path buffers the pre-read items in
   a bounded stack array (`[MaybeUninit<T>; MAX_BATCH_STEAL]`, allocation-free,
   no drop on lost claim). 28/28 scheduler tests pass, clippy clean. The harness was then generalized over
   a `WorkStealer` trait and extended to `BlockBasedDeque`, which **passes the
   same exactly-once contention/batch tests unchanged** — the newer block deque
   is correct under contention and now carries regression coverage (31/31
   scheduler tests, clippy clean). Remaining: the `loom` exhaustive model check
   (retrofit atomics behind `#[cfg(loom)]`). Original analysis (now confirmed)
   from reading `moirai-scheduler/src/deque.rs`:
   - `pop` follows the canonical algorithm: `b = bottom-1`; on non-x86 a
     `Relaxed` bottom store + `fence(SeqCst)` then `top.load(Relaxed)` (exactly
     Lê et al.); on x86 a fast path that uses a `Release` bottom store when
     `b > t+1` (clearly ≥2 elements, so a stale-low `top` read is only
     conservative) and a `SeqCst` store on the near-empty path. This x86-TSO
     specialization is plausible but unproven here.
   - `steal` reads `top` (`Acquire`) then `bottom` (`Acquire`) with **no
     `SeqCst` fence between the two loads** — a deviation from the canonical
     formulation, which places a `SeqCst` fence (or SeqCst loads) between them
     so a thief cannot observe an inconsistent `(top, bottom)` snapshot relative
     to a concurrent `pop`. The `SeqCst` CAS on `top` may still arbitrate the
     last-element contest, but the read-side consistency is the open question.
     This is the highest-value target for the loom model check; if it fails,
     restore the canonical `fence(SeqCst)` between the `top` and `bottom` loads.
   - loom retrofit requires routing the deque's atomics through a
     `#[cfg(loom)] use loom::sync::atomic` shim; structure the change so the
     production path is byte-identical.
3. **melinoe Stage D1 / hephaestus [minor]** — `DeviceBuffer<'brand,T>` over a
   `CudaBuffer`/`WgpuBuffer`, exclusivity via melinoe tokens; intra-process
   secure device sharing, contract-tested.
4. **moirai [minor]** — lock-free owner election (`SharedMemory` + CAS) and an
   MPSC accelerator work queue (SPSC `SharedQueue` → MPSC).
5. **hephaestus [arch]** — single-context owner draining the queue; clients route
   GPU work via `SchedulerRoute::Accelerator`. Remove the per-process init path.
6. **moirai [minor]** — evaluate/prototype BWoS block-based deque; keep if a
   measured contention win on the recorded baseline.

## Evidence tier

Root-cause diagnosis: empirical (differential serial/parallel runs on real CUDA
v13.2 hardware, this machine). Architecture: design-level, to be substantiated
per stage by loom (stage 2), compile-time encoding + contract tests (stage 3),
and differential benchmarks (stages 4–6).
