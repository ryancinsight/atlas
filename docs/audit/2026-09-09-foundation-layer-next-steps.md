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

### F3 — Two ADRs whose status had drifted from their substance

*(Corrected 2026-09-10. The original heading called these "Two ADRs Proposed
since 2026-07-28 with no driver." Both are in fact `Accepted`, and two of the
three ADR-0039 complaints below rested on a wrong premise.)*

**ADR 0038 (one generic conformance suite) — Accepted 2026-07-28; flipped from
`Proposed` 2026-09-10.** `crates/hephaestus-conformance` exists: 22 files,
7,020 LOC, `publish = false`, **21 public `assert_*_contract` free functions**,
generic over `ComputeDevice`. It is a **dev-dependency of all four backends**,
each calling it from 18–19 test files. The crate is therefore *not* dead — but
it remains **additive rather than a replacement**:

- Per-backend `contract.rs` totals **16,391 lines, up from 15,939** at the
  ADR's writing (cuda 4,098 / wgpu 5,585 / rocm 4,879 / metal 1,829). The drain
  the ADR asked for has not happened.
- **Scalar genericity is partial, not absent.** The seam is `ComputeDevice`, and
  most clauses pin the scalar via `where f32: DialectScalar<E::Dialect>`
  (measured **616 `f32` vs 110 `f64`** mentions). But the convolution module
  *is* scalar-generic through a local `ContractScalar: Scalar + Pod + PartialEq
  + Debug` (implemented for both `f32` and `f64`), and `typed_elementwise.rs:78`
  takes `<D, T>`. The real deviation is that the ADR's `<B: ComputeBackend, T:
  Scalar>` shape was never built — **no `ComputeBackend` trait exists** — not
  that the crate is un-generic.
- **No one-call entry.** Zero matches for `assert_backend_contract` /
  `assert_full_contract` / `assert_all_contracts`. A backend that omits one of
  the 21 functions loses that coverage silently. *(Re-confirmed still open.)*
- **No `tests/` of its own** — 0 `#[test]` in the crate and no `tests/`
  directory, so the ADR's negative control ("a deliberately broken backend fails
  only that backend") has no home. *(Re-confirmed still open.)*

**ADR 0039 (topology, no consumer re-forks the vendor dimension) — Accepted
2026-07-28, revised 2026-08-12.** Two of the three original complaints were
wrong:

- ~~"`coeus-rocm` / `coeus-metal` are not deleted"~~ — **wrong premise.** All
  four `coeus-<vendor>` crates declare `hephaestus-<vendor>` + `hephaestus-core`
  + `coeus-hephaestus` as dependencies, i.e. they are now thin *bindings* over
  the Hephaestus backends, not re-forks. `src/` measures rocm **152** / metal
  **163** lines. The 2026-08-12 "Metal/ROCm provider collapse" is real: the
  vendor dimension is **not** re-forked.
- The ADR's own revision names the residual, and measurement agrees: **CUDA/WGPU
  duplication remains open** — `coeus-cuda` **2,204** and `coeus-wgpu` **2,356**
  lines of `src`, an order of magnitude more than the collapsed pair.
- The ~1,528-line figure was real but **misattributed**: it is *test*
  duplication, not a vendor re-fork. `coeus-rocm` + `coeus-metal` `tests/`
  (776 + 752 = **1,528** lines) are hand-rolled clones — each defines its own
  `assert_close`, and neither dev-depends on `hephaestus-conformance`. Across
  all four coeus backends the hand-rolled test surface is **10,837 lines**,
  none of it wired to the shared suite.
- ~~"`leto` is the oracle but runs nothing: 9 of 14 entry points"~~ — **wrong.**
  `assert_leto_differential_contract` is a private helper at
  `hephaestus-conformance/src/decomposition.rs:87` that **is** invoked, from the
  public `assert_decomposition_contract` at line 50. The 9 is a *deliberate
  closed set*, documented in-source as "the decomposition operations with an
  independent Leto oracle"; the other **6 of 15** carry analytical-invariant
  clauses by design (`svd_recovers_exact_spectra`,
  `general_spectral_reductions_hold_their_invariants`). The genuine gap is
  narrower than claimed: `leto` implements no role trait, so "Leto *and* each
  backend as implementors" is still half done.
- Apollo's scaffold consolidation: **16 of 23 crates** still carry both
  `application/execution/plan/` and `domain/contracts/`; no `trait …Plan` exists
  anywhere in the repo. *(Re-measured 2026-09-10, unchanged.)*

### F4 — `eunomia`'s `RealField` excludes half the charter

`RealField` is implemented for `f32` and `f64` only
(`crates/eunomia/src/impls/field.rs:11,30`); `ComplexField` inherits the
restriction. `UnitScalar` covers all ten real storage types (`f32`, `f64`, `F16`,
`F32`, `F64`, `F4`, `F8`, `Bf4`, `Bf8`, `Bf16`) and `NumericElement` reaches them
by macro. So every domain function bounded by `T: RealField` silently excludes
the entire reduced-precision half of the datatype law. Either implement it or
document the exclusion — today it is neither.

Also: **ADR numbers are not namespaced.** Atlas `docs/adr/0005-…` is the
`NumericElement` SSOT (Accepted, closed 2026-07-05); `repos/eunomia/docs/adr/0005-…`
is `Real-scalar minimum and maximum special values` (Accepted 2026-08-21) — a
different document with the same number. **Fifteen** repos carry their own
`0001…` ADR sequence (`aequitas`, `apollo`, `coeus`, `eunomia`, `helios`,
`hephaestus`, `leto`, `metis`, `mnemosyne`, `moirai`, `ritk`, `themis`, `tyche`, …),
and `docs/adr/INDEX.md` carries no rule for telling them apart. Bare "ADR 0005"
in prose is therefore unresolvable without opening the file.

And two parallel `Scalar` traits survive — `leto-ops::Scalar`
(`domain/scalar/contract.rs:17`, `pub trait Scalar: NumericElement`) and
`coeus-core::Scalar` (`crates/coeus-core/src/dtype/traits.rs:342`,
`Scalar: NumericElement + CpuUnaryDispatch + Pod + EunomiaPod + Rem + Clone`) —
both correctly rebased per ADR 0005, but carrying **overlapping slice-kernel
default methods** (`add_slice` at `contract.rs:23` / `traits.rs:392`, `sub_slice`
`:33`/`:400`, `dot_slice` `traits.rs:430`, `axpy_slice` `traits.rs:460`, …), with a
comment at `traits.rs:382-387` asserting they must stay off `NumericElement`.
That overlap is ADR 0005's own decision, so it is not drift — but it does mean two
layers own the same backend seam, which is what ADR 0038's single conformance
suite is meant to settle.

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
2. **Finish ADR 0039** *(corrected 2026-09-10 — the original item said "delete the
   ~1,528-line coeus-rocm/coeus-metal test clone" and "add the five missing Leto
   oracles"; neither survives re-measurement)*. The vendor dimension is **not**
   re-forked — all four `coeus-<vendor>` crates are thin bindings over
   `hephaestus-<vendor>`. What remains, in priority order:
   - **CUDA/WGPU duplication** — `coeus-cuda` 2,204 / `coeus-wgpu` 2,356 lines of
     `src`, versus 152/163 for the already-collapsed rocm/metal pair. This is the
     item the ADR's own 2026-08-12 revision left open.
   - **10,837 lines of hand-rolled coeus backend tests** consume no shared suite.
     Note these are *coverage*, not dead weight: do not delete them into a hole.
     First decide whether `hephaestus-conformance` (generic over
     `hephaestus_core::ComputeDevice`) can be applied to coeus-level APIs at all;
     if not, the fix is a coeus-level shared suite, not a retrofit.
   - Build the generic plan layer for Apollo's **16 of 23** remaining crates
     (re-measured, unchanged; no `trait …Plan` exists anywhere).
   - Make `leto` a real `DecompositionOps` implementor with a role trait — the one
     surviving half of the original "Leto runs nothing" complaint.
   - ~~Add the five missing Leto oracles~~ — **withdrawn.** The 9-of-15 split is a
     deliberate closed set documented in-source
     (`hephaestus-conformance/src/decomposition.rs:50-87`); the other 6 are
     covered by analytical-invariant clauses by design.
3. **Finish ADR 0038** *(corrected 2026-09-10)*. The crate is Accepted and wired to
   all four backends, so this is now residual work, not construction:
   - Add **`assert_backend_contract::<B>()`** — 21 free functions with no aggregate
     entry, so an omitted function loses coverage silently. *(Still open.)*
   - Give the crate **its own `tests/`**, including the deliberately-broken-backend
     negative control. It currently has 0 `#[test]`. *(Still open.)*
   - **Scalar genericity is partial**: bulk clauses pin `f32` via
     `DialectScalar` (616 `f32` vs 110 `f64`), while `convolution` is already
     generic over `ContractScalar` and `typed_elementwise` takes `<D, T>`. The
     decision to take is whether to build the ADR's `ComputeBackend` trait — it
     does not exist, and `ComputeDevice` is the de facto seam — not to
     "genericize from scratch."
   - Only then delete the per-backend `contract.rs` (16,391 lines). Deleting first
     is how the suite lost its own rationale.
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
14. **ADR number namespaces collide** *(corrected 2026-09-10 — the original note
    claimed the `NumericElement` ADR did not exist; it does, at
    `docs/adr/0005-eunomia-scalar-ssot.md`, and it has landed).* The real defect is
    that "ADR 0005" is ambiguous: 15 repos each ship their own `0001…` sequence.
    Fix = add a qualification convention (`atlas:0005` vs `eunomia:0005`) to
    `docs/adr/INDEX.md` and a disambiguation header on Atlas ADR 0005. No ADR
    needs authoring; the doctrine is already recorded and already implemented.

### Tier D — unwired declarations and hygiene

15. **Four suspected unwired declarations — re-measured 2026-09-10: one is real,
    three are false alarms.** Do not act on this item as originally written.

    | Claim | Verdict | Measured evidence |
    |-------|---------|-------------------|
    | `coeus-ops` dead `melinoe` dep | **REAL** | `crates/coeus-ops/Cargo.toml:25` `melinoe = { workspace = true }`; **0** occurrences of `melinoe` anywhere under `crates/coeus-ops/src/`. |
    | `melinoe` `nightly` feature dead | **FALSE ALARM** | The measurement (0 `feature = "nightly"` cfg sites repo-wide) is right but the inference is wrong: the feature is consumed by the **build script**, not by cfg. `build.rs:15` reads `CARGO_FEATURE_NIGHTLY` and `:34` gates `doc_cfg_active` on `(is_nightly_compiler && is_nightly_feature) \|\| is_docsrs`. Deleting the feature would silently disable `doc_cfg` on every nightly build that is not docs.rs — a real regression, not a cleanup. |
    | `contracts/atlas-device` own `[workspace]` | **FALSE ALARM** | Path is `repos/melinoe/contracts/atlas-device/`. The `[workspace]` is load-bearing: `melinoe`'s own workspace is `members = ["."]` (`Cargo.toml:16`), so this crate is **not** a member; `[patch]` tables only apply at a workspace root, and it carries a 30-line `[patch]` block with depth-adjusted paths that is the only thing unifying `mnemosyne`/`moirai` local checkouts. Removing the `[workspace]` breaks type identity across that boundary. |
    | `themis::TpuTopology` unwired | **FALSE ALARM** | Fully implemented: `src/topology/tpu.rs:13` struct, `:18` `from_provider`, 5 `#[must_use]` accessors, re-exported at `src/topology/mod.rs:12` and `src/lib.rs:39`, and **tested** at `tests/tpu.rs:14,23`. It has no *producer* because no TPU backend exists yet — the doc comment states this is by design ("themis stays stateless law, so there is no `detect()` here"). Absence of a caller is not unwiredness. |

    **The one real item, and why it is not deleted here.** `coeus-ops` has no
    `build.rs` and no `CARGO_FEATURE_*` reads, so there is no build-script
    consumer that a source grep would miss — the declaration has no referent at
    all. But removing it is a `Cargo.toml` edit in a peer repo whose `Cargo.lock`
    lists `melinoe` under the `coeus-ops` package entry and would need pruning for
    `--locked` to keep passing. Regenerating by running `cargo` under the stack
    overlay is the known ADR 0044 hazard — it silently rewrites committed `git+`
    sources to the stripped form and is the direct cause of the `--locked`
    failures this stack is currently fighting. Worse, **coeus sits on the forced
    sweep order** (`leto → hephaestus → coeus → gaia → ritk → helios/CFDrs →
    kwavers`), so its lock is load-bearing for four downstream repos mid-sweep.
    Land the manifest edit together with a lock prune performed outside the
    overlay, and sequence it after the sweep.
16. Moirai forward sweep: **helios and CFDrs**, plus the **apollo quarantine** and
    **athena**, which cannot regenerate its lock at all. Current state is tracked
    authoritatively at
    [`#atlas-moirai-06-forward-sweep`](../../backlog.md#atlas-moirai-06-forward-sweep)
    — landed for tyche, consus, leto, hephaestus, gaia, coeus, ritk (partial) and
    kwavers. Also unblock helios `--all-features` via apollo#338
    (`transpose_complex_matrices`), which is a **second, independent break**: leto's
    `refactor(layout)!` moved that symbol off the `leto-ops` root behind
    `ComplexLayout` and made the free function `pub(super)`, and no single leto
    revision satisfies both `coeus-ops` (needs new leto for `leto_ops::ctc`) and
    apollo (needs old leto for the root export).
    **Do not advance atlas's submodule gitlinks yet** — advancing now would make the
    pinned-snapshot coherence gate fail, correctly, on helios, CFDrs and apollo.
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
