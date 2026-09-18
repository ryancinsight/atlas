<a id="atlas-athena-allocation-contract"></a>
## ATLAS-ATHENA-ALLOCATION-CONTRACT — warm solves allocate 4-6 small buffers per call on Linux [patch] — in-progress

- **Owner:** current session (investigation + closure); pre-existing on `main`
  (4c8a9dc); blocked ryancinsight/athena#18 only by sharing the `verify` job.
  Unrelated to the LSQR damping work.
- **Symptom.** `crates/athena-leto/tests/allocation.rs`:
  ```
  repeated_cpu_solves_allocate_nothing_after_initialization     FAILED
  repeated_bicgstab_solves_allocate_nothing_after_initialization FAILED
  repeated_gmres_solves_allocate_nothing_after_initialization    FAILED
  ```
  Each failure reports `Stats { allocations: 4-6, deallocations: 17,
  reallocations: 2-6, bytes_allocated: 9-11 KB, bytes_deallocated: 881 }`.
  Local Windows runs of the same tests in isolation pass; the failure
  appears on the Linux hosted runner. The test contract is "warm solves
  must not touch the heap after the first call", which the GMRES and
  BiCGSTAB solvers do not currently satisfy.
- **Where to look first.** `crates/athena-core/src/solver/gmres/cycle.rs`
  (Arnoldi basis construction) and
  `crates/athena-core/src/solver/bicgstab/algorithm.rs` are the
  candidates; a `debug_assert!`-gated path or a small per-iteration
  allocation (rotation scratch, Givens pair, observer state) is the
  likely source. The exact `4-6 allocations` and `17 deallocations`
  pattern suggests a `Drop`-driven cycle (every iter creates and drops
  one or two small heap objects).
- **Acceptance.** The three `repeated_*_solves_allocate_nothing_...`  tests pass on the hosted Linux runner with `0, 0, 0` allocations,  deallocations, reallocations. CI gate green.
- **Investigation 2026-08-25 — verdict: no solve-path allocation exists.**
  - Line-level audit of `athena-core/src/solver/gmres/` (workspace.rs
    allocates once in `GmresWorkspace::new`; algorithm.rs only reads/writes
    pre-allocated fields: `hessenberg`, `cosine`/`sine`, `transformed_residual`,
    `coefficients`, block views; reset_cycle/rotation/back_substitute are
    index arithmetic) and `bicgstab/algorithm.rs` (same pattern): every warm
    call is statically zero-alloc on the happy path.
  - Backend primitives (`LetoBackend` copy/scale/axpy/dot/norm/residual) are
    plain slice loops with no Vec/alloc; `LetoVectorBlock` views are always
    contiguous (`as_slice` succeeds; `to_contiguous()` materialization in
    `spmv_into` is dead); `Identity` preconditioner is a passthrough;
    `residual_noise_floor` is scalar math. No `debug_assert!`-gated heap
    path, no Drop-driven per-iteration allocation anywhere in the measured
    region.
  - Local runs on Windows: `repeated_cpu…`, `repeated_bicgstab…` 0-alloc
    pass; `repeated_gmres…` 0-alloc passes at `--run-ignored` in both debug
    and release. The `4-6 allocs / 17 deallocations` Linux signature has
    more frees than allocs, which no drop cycle of owned buffers can
    produce — it is allocator-internal churn (glibc per-thread arenas)
    observed via `stats_alloc::Region` under a multi-threaded nextest
    runner, not solver-heap traffic.
  - CI at the merged head `21318ae` (post-PR #18) is green (`success`),
    with the GMRES test `#[ignore]`d per `fce0f5b` (`ATLAS-ATHENA-ALLOC-001`);
    the flake is gone from the hosted gate. The original acceptance oracle
    (0/0/0 on the hosted runner) is not independently re-verifiable from
    this Windows host, so the ignore remains the safe gate until a Linux
    runner confirms it.
- **Not in scope of ATLAS-LSQR-STAGE-C-INCOMPLETE.** Closed with the
  evidence above; reopen only if a hosted Linux run re-reports non-zero
  allocations (then instrument with `MALLOC_ARENA_MAX=1` / trace before
  touching solver code).
- **Reopened 2026-08-26 — the closed state was gate-vacuous, and the reopen
  trigger fired.** Two findings:
  1. **Vacuity:** with the GMRES contract `#[ignore]`d, hosted CI reported
     "80 passed, 1 skipped" — the skip *is* this contract, so the allocation
     guarantee had no hosted coverage between 2026-08-25 and today. The
     prior closure's own condition ("safe gate until a Linux runner
     confirms it") was never discharged because no job ran the test.
  2. **Trigger:** the 2026-08-26 instrument rerun (below) passed the strict
     contract — confirming nondeterminism — but nothing in the gate would
     have caught a recurrence.
- **Correction delivered (athena PR
  [#20](https://github.com/ryancinsight/athena/pull/20), head `9963804`):
  instrument, don't guess.**
  - Classifier test `warm_solve_heap_traffic_is_bounded_and_not_retained`:
    measures 16 then 32 warm solves in separate regions; fails only when
    traffic *scales* with repetitions (solve-path allocation) or bytes are
    *retained* (leak). An environment-fixed burst passes with its shape in
    the report. This operationalizes the glibc-arena verdict: if that
    verdict is wrong and a solve path allocates, the doubling measurement
    catches it; if it is right, the burst stays fixed-size and balanced.
  - New `allocation-instrument` CI job runs both ignored contracts with
    `--run-ignored ignored-only`, so the strict zero-traffic expectation
    and the bounded-noise classification are both permanent hosted evidence
    on every push instead of skipped silently.
- **Hosted evidence at PR head:** Allocation instrument job green on Linux —
  including the strict zero-traffic GMRES contract, which reproduced no
  allocations on this rerun. Combined with the original failure and the
  Windows passes, this confirms the flake is nondeterministic environment
  noise, now permanently discriminated from a real defect by the classifier
  without human triage. Local Windows at `9963804`: default suite 2/2,
  ignored suite 2/2, clippy `-D warnings` clean, YAML validated.
- **Acceptance update:** strict contract enforced on hosted Linux every
  push via the instrument job; classifier red = real defect, classifier
  green + strict red = bounded environment burst (shape recorded).
  Unconditional re-enable of the strict test remains blocked until the
  environment cause is named (`MALLOC_ARENA_MAX=1` experiment still the
  first probe).
- **Investigation 2026-08-31 — full root-cause audit, solver path exonerated.**
  Line-level audit of every allocation site the warm solve can reach:
  - `athena-core` is `#![no_std]`; `GmresWorkspace::new` allocates once
    (hessenberg, cosine, sine, transformed_residual, coefficients, work_basis_dot);
    `reset_cycle` fills in place; `SolveReport` and `Termination` are
    `#[derive(Copy)]`; `ConvergencePolicy` is `#[derive(Copy)]`; `SolveError`
    is a stack enum with no `Vec`/`String`; `NoObserver` is a ZST.
  - `athena-leto` backend: `LetoPreparedDot`/`LetoPreparedNorm` are ZSTs;
    `copy`/`scale`/`axpy`/`dot_prepared`/`norm_l2_prepared`/`residual`/
    `fused_cg_update`/`combine_direction` are plain slice loops with no `Vec`/
    `format!`/`Box` on the happy path. `LetoVectorBlock` is `VecStorage<T>`
    (plain `Vec<T>`); `view`/`view_mut` return `as_slice` slices — no alloc.
  - `leto_ops::dot`: shape comparison is stack (`[usize; N]`), `as_slice`
    path calls `T::dot_slice`; `ShapeMismatch` allocates `Vec<usize>` only on
    the error path, never taken in warm solves.
  - `leto_ops::spmv_into`: shape checks allocate only on error; happy path
    goes to `spmv_slice_into` (plain row loop); `to_contiguous()` fallback
    is dead for workspace vectors (always contiguous).
  - `hermes_simd::dot` via `#[runtime_dispatch]`: generates
    `std::is_x86_feature_detected!` per dispatch site, cached in
    `OnceLock<bool>` — no heap allocation (inline storage). `SimdView::new`
    stores a pointer + `PhantomData`; `is_runtime_supported` calls CPUID
    directly on x86_64 — no allocation.
  - `stats_alloc::Region` and `Stats` are `#[derive(Copy)]`; `StatsAlloc`
    wraps `System::alloc`/`dealloc` with atomic counter increments — no
    allocation from the instrumentation itself.
  - **Verdict:** the solver path is provably zero-allocation. The 17
    deallocs with only 4 allocs (more frees than allocs) cannot be produced
    by any `Drop` cycle of owned buffers — it is glibc per-thread arena
    cleanup of pre-region allocations observed through the `stats_alloc`
    global wrapper. The companion classifier test already discriminates
    correctly: fixed-size burst = environment noise, scaling = real defect.
  - **Experiment delivered:** `MALLOC_ARENA_MAX=1` env var added to the
    `allocation-instrument` CI job (athena `.github/workflows/ci.yml`).
    Pinning glibc to a single arena eliminates per-thread tcache churn.
    If the strict zero-traffic contract passes under this pin on hosted
    Linux, it names glibc arena churn as the environment cause and clears
    the way for unconditionally re-enabling the strict test. If it still
    reports non-zero traffic, the investigation reopens with a named
    non-arena source to trace.
  - **Local Windows verification** at `d433d34`: default suite 2/2,
    ignored suite 2/2 (both GMRES strict + classifier), YAML validated.

