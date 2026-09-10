# Audit 2026-09-09: foundation layer — what remains

- Scope: the law and capability foundation (`eunomia`, `aequitas`, `melinoe`,
  `themis`), compute and data substrate (`mnemosyne`, `moirai`, `hermes`,
  `leto`, `hephaestus`, `apollo`, `coeus`), solver policy (`athena`), and the
  compact domain providers.
- Method: read-only. Measured sizes and stub counts directly; reconciled ADR
  claims against source; verified three agent findings that conflicted with
  `docs/audit/math-ssot-ledger.md` before recording them.
- Excluded by request: `repos/leoneuro-rs`, and the integrators except where
  they hold a substrate concern hostage.

## Summary

The foundation is not unfinished in the sense of containing stubs. Across ~4.3k
source files and ~759k LOC it holds **zero real `todo!`/`unimplemented!`** — the
six hits in `moirai` are string literals inside the scanner's own forbidden-token
tests. What remains is four different things, and only one of them is "write more
code":

1. **Ownership decided on paper, not on disk.** ADR 0033 gives Krylov to
   `athena`; `cfd-math` still carries a Krylov solver, a multigrid
   preconditioner, and a direct solver. ADR 0039 says no consumer re-forks the
   vendor dimension; `coeus-rocm`/`coeus-metal` still carry ~1,528 lines of
   cloned tests.
2. **Capability holes nobody has written down.** No second-order autodiff in
   `coeus`; `RealField` implemented for `f32`/`f64` only in `eunomia`; no SSE
   and no WASM SIMD in `hermes`, and `SVE` is a phantom target; no MINRES,
   FGMRES, or multigrid in `athena`.
3. **Documentation that now misdirects planning.** The math-SSOT ledger's
   capability table lists `leto` as owning the iterative solvers and
   preconditioners that ADR 0033 moved out. The README lists two "upstream gaps"
   that are both already closed. `leto-ops`'s linalg module doc advertises
   solvers it does not contain.
4. **Two ADRs Proposed since 2026-07-28 with nothing driving them.** ADR 0038's
   conformance crate exists but is additive — the per-backend `contract.rs` it
   was meant to replace has *grown*, 15,939 → 16,391 lines.

## 1. Measured state

| Repo | `.rs` files | LOC | `todo!` | `unimpl!` | `#[allow]` | `#[ignore]` |
| --- | --- | --- | --- | --- | --- | --- |
| eunomia | 73 | 11,217 | 0 | 0 | 2 | 0 |
| aequitas | 78 | 7,800 | 0 | 0 | 0 | 0 |
| melinoe | 78 | 10,531 | 0 | 0 | 2 | 0 |
| themis | 62 | 7,349 | 0 | 0 | 0 | 0 |
| mnemosyne | 235 | 47,318 | 0 | 0 | 0 | 0 |
| moirai | 575 | 121,403 | 0\* | 0\* | 41 | 9\* |
| hermes | 245 | 63,296 | 0 | 0 | 0 | 0 |
| leto | 320 | 65,860 | 0 | 0 | 16 | 0 |
| hephaestus | 660 | 134,904 | 0 | 0 | 9 | 0 |
| apollo | 940 | 134,109 | 0 | 0 | 19 | 42 |
| coeus | 944 | 146,855 | 0 | 0 | 0 | 8 |
| athena | 72 | 8,767 | 0 | 0 | 0 | 1 |
| horae | 43 | 3,747 | 0 | 0 | 0 | 0 |
| harmonia | 37 | 3,430 | 0 | 0 | 0 | 0 |
| consus | 107 | 37,759 | — | — | — | — |
| gaia | 175 | 33,197 | — | — | — | — |

\* The raw grep reports 3 + 3 for `moirai` and 12 `#[ignore]`. All six stub hits
are string literals in `benchmarks/tests/benchmark_contracts/` scanner guards;
three `#[ignore]` hits are doc comments. Real counts: **0 stubs, 9 ignored**.

The scale is the context for everything below. Substrate ≈ **759k LOC**. The
domain-law providers that substrate exists to serve total ≈ **92k LOC**:
`proteus` 2,933, `tyche` 2,272, `asclepius` 1,067, `hyperion` 3,269, `iris`
1,541, `horae` 3,747, `harmonia` 3,430, `ares` 1,362, `prometheus` 1,456. Some
of that is correct — a law crate should be small — but `proteus` owning the
material-property vocabulary for an entire multiphysics suite at 2.9k LOC is
thin, and it is where the image-to-material conversion from the companion audit
would have to land.

## 2. Findings

### F1 — Solver ownership is split three ways, and the owner has the least

Verified directly, because it contradicts the standing ledger:

- **`athena`** (8.8k LOC) owns `Cg`, `Gmres<_, RESTART>` (restarted,
  right-preconditioned), `BiCgStab`, `Lsqr`, the `Preconditioner` trait, and
  `Jacobi` / `IncompleteLu` / `SuccessiveOverRelaxation` / triangular.
- **`leto`** has **no `Preconditioner` type and no iterative module at all.**
  `crates/leto-ops/src/application/linalg/` contains only direct and dense
  decompositions. The only file in the crate that mentions `ConjugateGradient`
  or `BiCGSTAB` is `linalg/mod.rs` — in a doc comment.
- **`CFDrs`** still owns `cfd-math/src/linear_solver/` with `krylov.rs`,
  `preconditioners/{ilu, multigrid}`, `block_preconditioner.rs`,
  `direct_solver.rs`, `chain.rs`, `dense_bridge.rs`. `kwavers` carries one more
  Krylov file.

Two consequences worth stating plainly:

- **Multigrid exists only inside `CFDrs`.** Zero occurrences in `athena`,
  `leto`, or `coeus`. The one preconditioner family that makes large multiphysics
  solves tractable lives in an integrator's math crate, and the member chartered
  to own solver policy cannot see it.
- `athena` additionally has no MINRES (symmetric indefinite), no FGMRES
  (variable preconditioner), no deflation/recycling, no Chebyshev, no QMR/TFQMR/
  IDR, no LSMR, and no Arnoldi/Lanczos machinery.

ADR 0033 is Accepted and assigns Krylov to `athena`. `ATLAS-GMRES-FORK-DEFECTS-001`
closed on 2026-08-03 having *ported corrections into* the CFDrs and kwavers forks
rather than deleting them, so the forks were known and preserved.

### F2 — The math-SSOT ledger's capability table is stale

`docs/audit/math-ssot-ledger.md` §3 lists `leto` as owning
`application::linalg::iterative`: `ConjugateGradient`, `BiCGSTAB`, `GMRES`,
`LsqrSolver`, `Preconditioner`, `Jacobi`/`ILU`/`SSOR`. **None of it is there.** It
was removed by ADR 0033 and now lives in `athena`.

Sections 4–7 of the ledger remain sound, and moves 1–4 look delivered on both
sides: `leto` has `FiniteDifference3D` / `FiniteDifference3DScheme` /
`StaggeredLeapfrog3D` under `application/diff/three_dimensional/`; `kwavers`'s
`central_difference_2` and `special/` are gone and `linear_algebra/{ext,complex}.rs`
are gone; `cfd-math` lost `differentiation/`, `integration/`, `interpolation/` and
gained `fd_extensions.rs` with `pub mod fd` / `pub mod interp` re-exports. Moves
5–9 and §5's open questions are untouched.

The defect is narrow and dangerous: anyone scoping work from §3 will plan against
a capability that does not exist.

### F3 — Two ADRs Proposed since 2026-07-28 with no driver

**ADR 0038 (one generic conformance suite).** `crates/hephaestus-conformance`
exists — 21 modules, 7,020 LOC, `publish = false`. It is **additive, not a
replacement**:

- Per-backend `contract.rs` totals **16,391 lines, up from 15,939** at the ADR's
  writing (cuda 4,098 / wgpu 5,585 / rocm 4,879 / metal 1,829). wgpu's file alone
  holds 352 `assert`s.
- Not generic over `<T: Scalar>`: the seam is `ComputeDevice`, and signatures read
  `assert_dense_vector_contract<D, E: DenseVectorOps<D, f32>>` — the scalar is
  concrete. 579 `f32` mentions against 98 `f64`. No `ComputeBackend` trait exists.
- No one-call `assert_backend_contract::<B>()`; a backend that omits one of the 21
  functions loses that coverage silently.
- The crate has no `tests/` of its own, so "a deliberately broken backend fails
  only that backend" has no home.

**ADR 0039 (topology, no consumer re-forks the vendor dimension).** Seams landed —
`hephaestus-core` defines 72 traits and all four backends implement the main
families. But:

- `coeus-rocm` / `coeus-metal` are **not deleted**. `src/` is correctly reduced to
  device acquisition, but `tests/` is still cloned: `elementwise.rs` 431 vs 428,
  `reduction.rs` 156 vs 155, `attention.rs` 92 vs 79, `cross_entropy.rs` 69 vs 62
  — ~1,528 lines no deletion ledger ever counted.
- `leto` is the oracle but runs nothing: `assert_leto_differential_contract`
  covers **9 of the 14** entry points. `svd_decompose`, `svd_rank_revealing`,
  `schur`, `hessenberg`, `bidiagonalize` have analytical invariants only. `leto`
  implements no role trait, so "Leto *and* each backend as implementors" is half done.
- Apollo's scaffold consolidation: **16 of 23 crates** still carry both
  `application/execution/plan/` and `domain/contracts/` (baseline was 19-of-23).
  No generic layer, and no `trait …Plan` exists anywhere.

### F4 — `eunomia`'s `RealField` excludes half the charter

`RealField` is implemented for `f32` and `f64` only
(`crates/eunomia/src/impls/field.rs:11,30`); `ComplexField` inherits the
restriction. `UnitScalar` covers all ten real storage types (`f32`, `f64`, `F16`,
`F32`, `F64`, `F4`, `F8`, `Bf4`, `Bf8`, `Bf16`) and `NumericElement` reaches them
by macro. So every domain function bounded by `T: RealField` silently excludes
the entire reduced-precision half of the datatype law. Either implement it or
document the exclusion — today it is neither.

Also: ADR 0005 is mis-cited. `eunomia`'s own `docs/adr/0005-…` is about NaN and
signed-zero min/max; the "`NumericElement` is the universal `Scalar` supertrait"
doctrine exists only in Atlas README prose. And two parallel `Scalar` traits
survive — `leto-ops::Scalar` (`domain/scalar/contract.rs:17`) and
`coeus-core::Scalar` (`dtype/traits.rs:342`) — carrying **overlapping slice-kernel
default methods** (`add_slice`, `dot_slice`, `axpy_slice`, …), with a comment at
`coeus-core:378` asserting they must stay off `NumericElement`. Two layers own the
same backend seam.

### F5 — `hermes` declares ISA targets it does not implement

`TargetId` is `Scalar | Avx2 | Avx512 | Neon | Sve`
(`crates/hermes-simd/src/target.rs:23`), runtime-dispatched with a scalar
fallback. Actually implemented: `avx2_{f16,f32,f64}`, `avx512_{f16,f32,f64}`,
`amx`, `avx_vnni_tiling`, `neon_{f16,f32,f64}`.

- **No SSE.** AVX2 is the x86 floor; anything below it falls to scalar.
- **No WASM SIMD at all** — zero `wasm32`/`simd128` hits workspace-wide, despite
  `build-wasm.sh` living in `moirai`.
- **`SVE` is lane-emulated.** `SveArch` (`aarch64/sve.rs:25`) is documented
  "lane-emulated; executes on every host". A declared ISA target with no
  implementation.

Consumer-side, the README's "displaces hand-written intrinsics" is closer but not
true: `apollo` 22 `core::arch` files / 117 `#[target_feature]`, `eunomia` 4/23,
`moirai` 3/22, `kwavers` 3/5; `CFDrs` is 0/0 (converted). The `gap_audit.md:67`
"four consumers" finding carries **no resolution stamp**.

One question has no answer: `moirai-utils/src/simd/arch/{x86,aarch64}.rs` forks
SIMD by design, because the README orders `moirai` *below* `hermes`, so it cannot
take a `hermes` edge without inverting the stack.

### F6 — `coeus` has no second-order autodiff

No `create_graph`, `retain_graph`, `double_backward`, `grad_of_grad`, `hessian`,
`jacobian`, `jvp`, or `hvp` anywhere in `coeus-autograd`. Forward coverage is
broad (98 op files, no op found with a forward and no backward) and Apollo is
genuinely differentiated in place via `coeus-fft`.

This is the unrecorded blocker for kwavers' PINN work, which needs ∂²u/∂x².
Related: `LevenbergMarquardt` is **dense-only** (builds a dense `JᵀJ`) and
requires a **user-supplied analytic Jacobian** with no bridge from
`coeus-autograd`; there is no L-BFGS, no trust region, no line search, and no
sparse/iterative LM.

**Two README "upstream gaps" are already closed** and `README.md:715` is stale:
Gauss-Newton/LM exists at `coeus-optim/src/least_squares/`, and the even-order
symmetric SH basis exists at
`apollo/crates/apollo-sht/src/infrastructure/kernel/real_spherical_harmonic.rs`
(`MAX_REAL_SH_DEGREE = 85`, MRtrix3 convention), with RITK already consuming it.

### F7 — Smaller items that are real

- **`leto`:** AMD ordering is **done** (`application/sparse/amd.rs`, wired at
  `lu_symbolic.rs:45`). Missing: sparse Cholesky, sparse QR, sparse eigensolvers
  — `application/sparse/` is LU-only. Batched: `lu_batch.rs` only.
- **`leto-ops/src/application/linalg/mod.rs`** documents "Iterative solvers (CG,
  BiCGSTAB, GMRES, LSQR) and preconditioners" directly above `pub mod lu;`. False.
- **`hephaestus`:** wgpu, cuda, rocm are real; **metal is not** — 5,959 LOC, zero
  `metal::`/`objc`/`MTL`/MSL, delegates to wgpu. `ATLAS-ARCH-009` open. CUDA is
  dynamically loaded (`libloading`, `nvcuda.dll`/`libcuda.so.1`) and
  `HEPH-CUDA-DRIVER-BOUNDARY` is done (PR #277) — `backlog.md:738` still says
  in-progress.
- **`moirai` 0.6.0 forward sweep:** landed for tyche, consus, leto, hephaestus,
  gaia, coeus, ritk, kwavers; **helios and CFDrs remain**. Separately, leto's
  `refactor(layout)!` moved `transpose_complex_matrices` behind a trait and
  `apollo-fft` still imports it from the root, blocking helios `--all-features`
  (#92) until apollo#338 lands.
- **`moirai` unwired declarations:** `#[allow(dead_code)]` comments at
  `moirai-async/src/executor/task.rs:70,88,92` and `moirai-pal/src/reactor/core.rs:29`
  mark a priority-aware run queue, queue-latency accounting, and reactor
  telemetry that were declared and never wired. ~5% of the 41 `#[allow]` sites
  are real debt; the rest is naming/cast boilerplate.
- **`mnemosyne`:** the 2026-06/07 soundness-perf audit **was** fixed in-cycle (11
  commits; residual AR-2 `WGPU_*_CALLBACK` `AtomicPtr` hole and AR-4). But the
  three *structural* audits were only recommended and never executed: no
  `macro_rules!` in `src/lib.rs` (both `unsafe impl GlobalAlloc` still open-coded
  at `allocator.rs:15,119`); `HasSegmentPool` never lifted to `mnemosyne-core`;
  `mnemosyne-hardened` still a crate; `TieredBackend::for_tier` open-coded 3× at
  `tiered_heap.rs:201,261,308`.
- **`melinoe` / `themis`** are genuinely wired (mnemosyne 10 files, moirai,
  themis 6, gaia 2) — the "unused capability system" worry does not hold. But
  `coeus-ops` declares `melinoe` with **zero** `melinoe::` sites; `melinoe`'s
  `nightly` feature has zero `#[cfg(feature = "nightly")]` sites;
  `contracts/atlas-device` declares its own `[workspace]` so root `members = ["."]`
  means the gates never compile it; and `themis::TpuTopology` has **zero external
  consumers** (16 refs, all internal; `tests/tpu.rs` 28 lines).
- **`aequitas`:** `StressSemantics` (`dimension/model.rs:47`), `ReactionRate` and
  `MolarFlux` (`systems/si/dimensions.rs:70,75`) all exist — `backlog.md:1385` and
  `:1405` still read `todo`. Runtime unit/expression evaluation is still
  compile-time plus the Python wheel, gated on a second consumer. Deferred:
  affine units (Celsius/Fahrenheit), integer/rational storage; `serde` has one
  gated site.
- **`apollo`'s 42 ignored tests:** 37 are perf instruments run by hand, 3 are
  allocation probes requiring process isolation, and 2 are **open numerical
  disagreements** — `mixed_radix/dispatch.rs:713` (composite-length route
  divergence) and `:746` (radix-table disagreement). The practical cost is that
  apollo's performance evidence is not reproducible in CI.

## 3. Next steps

### Tier A — ownership on disk (deletions and moves, no new algorithms)

Highest leverage per unit of risk. Everything here is already decided; it just
has not been done.

1. **Close the Krylov split.** Move `cfd-math/src/linear_solver/` — `krylov.rs`,
   `preconditioners/{ilu,multigrid}`, `block_preconditioner.rs`,
   `direct_solver.rs`, `chain.rs`, `dense_bridge.rs` — into `athena` (policy) and
   `leto` (kernels) per ADR 0033, and delete the two CFDrs and one kwavers Krylov
   files. This is the best single item on the list: it simultaneously removes a
   fork and gives `athena` the multigrid and block preconditioner the stack
   currently lacks entirely.
2. **Finish ADR 0039.** Delete the ~1,528-line `coeus-rocm`/`coeus-metal` test
   clone (the `src/` half is already done); build the generic plan layer for
   Apollo's 16 remaining crates; make `leto` a real `DecompositionOps`
   implementor with a role trait; add the five missing Leto oracles.
3. **Finish ADR 0038.** Make the conformance suite generic over `<T: Scalar>`, add
   `assert_backend_contract::<B>()`, give the crate its own tests including the
   deliberately-broken-backend case — and only then delete the per-backend
   `contract.rs`. Deleting first is how the suite lost its own rationale.
4. **Collapse the `hermes` consumer forks** (apollo 22 files, eunomia 4, moirai 3,
   kwavers 5) and answer the moirai-below-hermes topology question by decision
   rather than by leaving it open.

### Tier B — capability holes nobody has recorded

5. **`eunomia`: implement `RealField` for the reduced-precision types**, or
   document the exclusion. Nothing else in the law layer gates as much.
6. **`coeus`: second-order autodiff** — `jvp`/`hvp`, `double_backward`,
   `hessian`. Unblocks kwavers' PINN work. Then bridge `LevenbergMarquardt` to
   `coeus-autograd` and add a sparse/iterative variant.
7. **`athena`: MINRES, FGMRES, deflation/recycling, Chebyshev**, plus multigrid
   arriving from step 1.
8. **`hermes`: SSE backend and WASM SIMD128**; decide whether `SVE` becomes real
   or leaves `TargetId`.
9. **`leto`: sparse Cholesky, sparse QR, sparse eigensolvers**, and batched
   QR/Cholesky/SVD to match `lu_batch.rs`.

### Tier C — documentation that misdirects (cheap, and it is actively costing)

10. **`math-ssot-ledger.md` §3** — remove the `application::linalg::iterative`
    row and the preconditioner families; ADR 0033 moved them to `athena`.
11. **`README.md:715`** — Gauss-Newton/LM and the even-order symmetric SH basis
    are delivered; drop them from the upstream-gap list.
12. **`leto-ops/src/application/linalg/mod.rs`** — delete the false doc comment.
13. **Stale board rows:** `backlog.md:1385` and `:1405` (aequitas mechanics and
    reaction quantities, both done); `backlog.md:738` (CUDA driver boundary, done
    at PR #277).
14. **ADR 0005 citation** — either author the `NumericElement` supertrait ADR or
    stop citing `eunomia`'s 0005, which is about NaN min/max.

### Tier D — unwired declarations and hygiene

15. `coeus-ops` dead `melinoe` dependency; `melinoe`'s `nightly` feature with zero
    cfg sites; `contracts/atlas-device`'s own `[workspace]`; `themis::TpuTopology`
    — for each, wire it or remove it.
16. Moirai forward sweep: **helios and CFDrs**; and unblock helios
    `--all-features` via apollo#338 (`transpose_complex_matrices`).
17. `mnemosyne`: execute or formally decline the three recommended structural
    refactors, and close AR-2 against `hephaestus`.
18. `apollo`: give the 37 hand-run perf instruments a CI home, and resolve the two
    ignored numerical disagreements.
19. `aequitas`: decide affine units and integer/rational storage; finish `serde`.

## 4. What is not a gap

Recorded so this is not re-audited:

- **No stub crisis.** Zero real `todo!`/`unimplemented!` across the foundation.
  `moirai`'s raw hits are scanner-guard string literals.
- **`melinoe` and `themis` are not speculative.** Both have real consumers in
  `mnemosyne` and `moirai`.
- **`proteus`'s elastic SSOT landed** and `CFDrs` has consumed it; the consolidated
  named catalogs were found already drifted (aluminium 70 GPa vs 69 GPa), which is
  the argument for the move, not against it.
- **`ares` A0–A6 and `prometheus` Phase 0 are delivered.** `ares` A9 is blocked on
  `proteus-mat` reaching crates.io, not on unfinished work.

## 5. Evidence index

- Ledger: `docs/audit/math-ssot-ledger.md` (§3 stale; §4–§7 sound; §6 ranked
  moves; §10 open follow-ups).
- Conformance: `docs/audit/2026-07-28-computebackend-conformance-triage.md`,
  `docs/audit/2026-09-02-conformance-green-ratchet.md`.
- Doctrine: ADR 0031, 0033, 0034, 0038, 0039, 0055, 0061; index at
  `docs/adr/INDEX.md`.
- Mnemosyne history: `docs/audit/2026-06-27-mnemosyne-*` and
  `2026-07-01-mnemosyne-soundness-perf-audit.md`.
- Companion audit: `docs/audit/2026-09-09-medical-imaging-suite-next-steps.md`.
