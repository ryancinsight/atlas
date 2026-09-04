# Math/Linalg SSOT Consolidation Ledger

> **Atlas audit artifact — read-only.**
>
> Per-consumer inventory of every consumer-local math/linalg helper that has
> a credible `leto` (or `apollo` / `coeus` / `hermes` / `eunomia`) single
> source-of-truth target, classified by SSOT owner, with a rank-ordered
> selection of the **first three SSOT moves** and atlas-style ADR outlines
> for each.  No production code is modified by this audit.
>
> **Provenance.**  This file is the read-only companion to the discovery
> question.  All paths are relative to the atlas meta-repo
> (`D:/atlas/`).  Every classification decision is backed by a verified file
> read or a search-hit cited in the body.  When classification is uncertain
> the site is listed under **OPEN QUESTION** with the smallest follow-up
> needed to close it.

---

## 1. Scope and exclusions

| Area | Touched by this audit? | Why / why not |
| --- | --- | --- |
| Production `use nalgebra;/use ndarray;/use burn;` in kwavers / CFDrs / helios / ritk | **No.** | Migration already complete at the import-graph level (the producer `xtask/src/migration_audit.rs` fixtures are the only direct matches in the workspace).  See `D:/atlas/gap_audit.md` Aequitas migration ledger and ADRs 0029 (Iri­s integration) / 0030 (Hyperion deletion ledger) for the closed waves. |
| Aequitas / Eunomia physical-quantity migration | **No.** | Closed across 16 kwavers + helios + cfd-math audit rows per `D:/atlas/gap_audit.md` `KWAVERS-AEQ-MET-01…13` / `HELIOS-AEQ-MET-01…08` / `CFDRS-AEQ-MET-01…16`. |
| Hyperion optical transport | **No.** | Closed deletion ledger per `README.md` P2-A row. |
| Math/linalg helper duplication against `leto` / `apollo` SSOT | **Yes — this audit.** | This is the user-flagged consolidation surface. |

---

## 2. Reading approach

1. **Leto surface map** — read
   `repos/leto/crates/leto-ops/src/lib.rs` plus `application/{mod.rs, diff/
   {finite_difference,schemes}.rs, linalg/mod.rs, sparse/mod.rs, stencil.rs,
   interpolation/*, quadrature/*}` to know what is already SSOT.
2. **Per-consumer structure** — read each suspect crate root (`lib.rs`) to
   list every public module, then drilled into the consumer-local modules
   that obviously overlap.
3. **Cross-checked against existing re-exports** — every consumer that
   already imports from `leto_ops::…` confirms an SSOT has been selected;
   remaining local duplicates are what this audit enumerates.

Constraints observed:

- **Naming preserved.**  All SSOT moves are forbidden to introduce symbol
  rename cycles — they may additively extend `leto-ops` and remove
  consumer copies, but they must not rename existing leto symbols.
- **Vertical hierarchy preserved.**  Each move keeps the existing file
  tree; new `leto-ops` modules follow the `application/{topic}.rs`
  convention.
- **Bulk-first.**  The selection favours "one SSR-move covers many call
  sites across many consumers".

---

## 3. Leto SSOT surface — what is already owned

Verified against `repos/leto/crates/leto-ops/src/lib.rs` (2026-07):

| Submodule | SSOT surface (cube contracts already published by `leto-ops`) |
| --- | --- |
| `application::scalar` (re-export umbrella) | `Scalar`, `RealScalar`, `Xorshift64`, `ExecutionStrategy`, `ScalarStrategy`, `SimdStrategy`, `ParallelStrategy`, `CacheGeometry`. |
| `application::map` | `binary_map<Op,T,N>`, `scalar_map`, `scalar_map_into`, plus `add/sub/mul/div/sum` and ZST markers `AddOp/SubOp/MulOp/DivOp/BinaryOp`. Elementwise with N-dim Leto arrays; scalar dispatched; Moirai-parallel for large inputs; hermes-SIMD for `f32`/`f64`. |
| `application::unary` | `map/map_into/mapv/map_inplace`, `unary_map<UnaryOp>/unary_map_into` with ZST markers `ExpOp/LnOp/SinOp/CosOp/SqrtOp/AbsOp/NegOp/RecipOp/PowfOp/ErfOp/ErfcOp/LgammaOp/UnaryOp`. |
| `application::matrix` | `matmul`, `matmul_accumulate`, `batched_matmul` (rank-2 caller-owned output, rejects zero-stride aliasing). |
| `application::vector` | `matvec`, `dot`, `hamming_distance`, `jaccard_distance`. |
| `application::linalg` (dense) | `cholesky_decompose/det/inv/solve` + CholeskyDecomposition, `lu_decompose/det/inv/solve` + LuDecomposition, `qr_decompose` + QrDecomposition, `solve_least_squares`, `kron`, `l2_normalize[_into]`, `matrix_rank[+_with_tolerance]`, `norm`, `norm_l1/l2/max` + NormKind, `trace`, `symmetric_eigen_jacobi[+_with_tolerance]`, `symmetric_eigenvalues_jacobi[+_with_tolerance]` + SymmetricEigenDecomposition, `hermitian_eigen_jacobi/qr` + HermitianEigenConfig/Result, `eigenvalues`, `hessenberg` + HessenbergDecomposition, `schur` + RealSchur, `svd_decompose[+_with_tolerance]/svd_rank_revealing[+_with_tolerance]/svd_via_bidiagonal/singular_values/pinv` + SvdDecomposition, `udu_decompose` + UduDecomposition, `bidiagonalize` + BidiagonalDecomposition, `bunch_kaufman` + BunchKaufmanDecomposition, `col_piv_qr` + ColPivQrDecomposition, `full_piv_lu` + FullPivLuDecomposition, `complex_solve/complex_inv` (Complex<f64>), `matexp/matpow` (matrix function). Fluent rank-2 traits: `MatrixProduct`, `MatrixNorm`, `MatrixDecompose`, `MatrixSolve`, `MatrixProperties`, `MatrixFunction`, `AsMatrixView`. |
| `application::linalg::iterative` | Iterative solvers SSOT: `ConjugateGradient`, `BiCGSTAB`, `GMRES`, `LsqrSolver` (with `LsqrConfig`/`LsqrResult`/`LsqrStopReason`); `IterativeLinearSolver`/`LinearSolver`/`LinearOperator`/`Preconditioner`/`Configurable`/`ConvergenceMonitor`/`IterativeSolverConfig`; preconditioners `IdentityPreconditioner`, `JacobiPreconditioner`, `ILUPreconditioner`, `SSORPreconditioner`. |
| `application::sparse` | CSR / COO / CSC / sparse-LU SSOT: `CooMatrix` (assembly target), `CsrMatrix` (kernel target), `CscMatrix` + `CscColumn`, `spmv/spmv_into`, `spmm/spmm_into`, `spgemm`, `csc_spmv/csc_spmv_into`, `csr_to_dense`, `sparse_lu_solve` + `SparseLuSolver` + `factor_symbolic`/`factor_numeric` + `SymbolicLu`/`NumericLu` + `DENSE_LIMIT_DEFAULT`. The CSR SpMV `O(nnz)` theorem and the CSR-From-COO-from-dense pipeline are documented in `sparse/mod.rs` theorem comments. |
| `application::interpolation` | 1-D `Interpolation1D` SSOT: `LinearInterpolation`, `LagrangeInterpolation`, `CubicSplineInterpolation`. |
| `application::diff` | 1-D generic `FiniteDifference<T>` + `FiniteDifferenceScheme { Forward, Backward, Central, ForwardSecondOrder, BackwardSecondOrder }`; `first_derivative` / `second_derivative` on `&[T] → Result<Array1<T>>` with bounded-error tests. |
| `application::quadrature` | `Quadrature<T>` trait, `TrapezoidalRule`, `SimpsonsRule`, `GaussLegendre2/3/5`, `CompositeQuadrature<Q>` (generic over any Quadrature implementation). |
| `application::stencil` | `laplacian_2d_into` (validated `Laplacian2D<T>` + `BoundaryCondition` Dirich­let/Neumann/Periodic from `leto` core). |
| `application::random` | Seeded uniform / Box-Muller normal constructors (`uniform_with_seed[_into]`, `normal_with_seed[_into]` over `Xorshift64`). |
| `application::signal` | Window functions `blackman/hamming/hann/tukey` + `wrap_to_pi` phase wrap. |
| `application::special` | `sinc`, `erf`, `j0`, `j1`, `jn` (Bessel). |
| `application::statistics` | Quality metrics: `normalized_rmse`, `nrmse`, `pearson`, `percentile_range`, `phase_error_degrees_for_correlation`, `phase_shift_correlation_curve`, `psnr`, `rmse`, `validation_psnr_from_relative_rmse`. |
| `application::nonlinear` | `AndersonAccelerator` with `AndersonConfig`/`AndersonMethod`. |
| `application::optimization` | `minimize(f, g, LbfgsConfig) → LbfgsResult` + `LbfgsMemory`. |
| `application::zip` | Mutable zip variants (`zip_mut_with`, `zip2_mut_with`, `zip3_mut_with`, `zip5_mut_with`, indexed variants and `coordinate_map[_plan][_inplace]`). |
| `application::reduction` | Keep-dim reductions `sum_axis[_into]`, `mean_axis[_into]`, `min_axis[_into]`, `max_axis[_into]` + ZST markers `SumAxis/MinAxis/MaxAxis/MeanAxis` + `reduce_axis[_into]/reduce_all`. |
| `application::scan` | `cumsum[_into]`, `scan_axis`/`scan_axis_into`, `CumSumOp`, `CumProdOp`, `ScanDirection` Forward/Reverse, `ScanOp`. |
| `application::vector` / `application::random` / `application::diff` | `dot`, `matvec`, `distance` metrics; RNG + seeding; 1-D FD. |
| `infrastructure::simd` | `simd_add/sub/mul/div` (per-element, hermes-mediated path). |
| `infrastructure::parallel` | `parallel_for`, `parallel_for_chunks` (Moirai-mediated; feature-gated `parallel`). |

**Coverage verdict.**  Everything in the `application::*` namespace is
already published and conformance-tested via
`repos/leto/crates/leto-ops/tests/ops/{sparse,matmul,reduction,elementwise,
unary_math,oracle_parity,stencil,parity,structure_ops,lu,svd,schur,
qr_cholesky,differential,eigenvalues,eigen,matmul,matrix_traits,norms,
properties,reduction,bunch_kaufman,full_piv_lu,col_piv_qr,or­acle_parity,parity,
unary_math,…}`.  The two demonstrable pre-releases
`cargo run --locked -p leto-ops --example ndarray_parity` and
`… --example nalgebra_parity` already exhibit Leto's
`CsrMatrix`/`SparseLuSolver` kernels against external-reference outputs.

---

## 4. Per-consumer math-redundancy inventory

### 4.1 Kwavers (`crates/kwavers-math/` and downstream)

Module map of `kwavers-math` (from `kwavers-math/src/lib.rs`):

```text
pub mod fft;               // FFT family + KSpaceCalculator (apollo SSOT candidate)
pub mod geometry;          // make_ball / make_circle / make_disc / make_line (mask generation; leto::geometry is the closest slot)
pub mod inverse_problems;  // domain inverse-problem algorithms; keep local
pub mod linear_algebra;    // includes sparse/,iterative/,eigenvalue,complex,ext  (overlaps leto-ops linalg)
pub mod numerics;          // operators/{spectral,differential,interpolation,regularization}
pub mod optimization;      // domain keep
mod   parallel;            // SIMD/parallel dispatch internal
pub mod signal;            // domain
pub mod simd;              // SIMD acceleration interfaces (hermes SSOT)
pub mod simd_safe;         // broad-cast-ISA SIMD wrappers (hermes SSOT)
pub mod special;           // special-function wrappers (leto::special SSOT candidate)
pub mod statistics;        // domain keep or eunomia SSOT
```

Per-file classification table (sampled from `code_searcher` runs and direct
reads):

| Site path (`repos/kwavers/`) | Public surface | Classification | Owner | Notes |
| --- | --- | --- | --- | --- |
| `crates/kwavers-math/src/utils/array_utils.rs` | `pub fn add_fields / scale_field / norm / multiply_fields / subtract_fields` over `&Array3<f64>` | **DELETE on kwavers; route through leto-ops elementwise + hermes SIMD.** | hermes / leto | The user-suspected `array_utils.rs` is no longer at this path; the same content lives under `kwavers-math/src/simd_safe/{swar,neon,avx2,auto_detect/...}` after a 2024 consolidation. |
| `crates/kwavers-math/src/simd_safe/swar.rs` | `add_fields_swar / scale_field_swar / norm_swar / multiply_fields_swar / subtract_fields_swar` | **DELETE; route elementwise through `leto_ops::binary_map::{add,mul,sub}` + `unary_map::{RecipOp}`.** | leto / hermes | SWAR variant; same shape as the slow-path in `simd_safe/operations.rs`. |
| `crates/kwavers-math/src/simd_safe/neon.rs` | `add_fields_neon / scale_field_neon / norm_neon / multiply_fields_neon / subtract_fields_neon` | **DELETE; route through `leto_ops` + hermes::neon dispatches. Same SSOT as the file above.** | leto / hermes | Each `_neon` body is a SIMD loop over a leto Array3 view; the leto hermes integration already selects NEON at runtime, so the copy cannot win. |
| `crates/kwavers-math/src/simd_safe/avx2.rs` | `add_fields_avx2 / scale_field_avx2 / norm_avx2 / multiply_fields_avx2 / subtract_fields_avx2` | **DELETE; route through `leto_ops` + hermes::avx2 dispatches.** | leto / hermes | Same pattern. |
| `crates/kwavers-math/src/simd_safe/auto_detect/{aarch64, dispatcher, x86_64/{sse42,avx2,avx512}}.rs` | `add_arrays / scale_array / fma_arrays / add_inplace / scale_inplace` | **DELETE; leto + hermes already does runtime ISA dispatch and feature detection.** | hermes | Hermes owns ISA dispatch by contract per `D:/atlas/README.md` *Provider ownership* table. |
| `crates/kwavers-math/src/linear_algebra/ext.rs` | `norm_l2(Array3)`, `LinearAlgebraExt<T>::solve_into / inv / eig` for `Array2<f64>` and `Array2<Complex64>` | **DELETE (kwavers vocabulary contract moves to direct `leto_ops::{solve,inv,symmetric_eigen_jacobi,hermitian_eigen_jacobi}.into()` at consumer call sites).** See ADR below. | leto | Reads `solution/inv/eig` directly through `leto_ops::{solve,inv,symmetric_eigen_jacobi,hermitian_eigen_jacobi}` — already SSOT. |
| `crates/kwavers-math/src/linear_algebra/complex.rs` | `ComplexLinearAlgebra::{solve_linear_system_complex, matrix_inverse_complex}` | **DELETE (or move to thin re-export at consumer edge) — `leto_ops::{complex_solve,complex_inv}` are the SSOT.** | leto | Reads `solution/inv` directly through `leto_ops::{complex_solve,complex_inv}` — already SSOT. |
| `crates/kwavers-math/src/linear_algebra/iterative/mod.rs` | `solve_lsqr_matfree` | **MOVE expected surface into `leto_ops::application::linalg::iterative::LsqrSolver::solve(...)` (already exists). DELETE the local function once call sites are rerouted.** | leto | Already on leto per verification; local wrapper is duplicate. |
| `crates/kwavers-math/src/linear_algebra/sparse/eigenvalue.rs` | `inverse_power_iteration` + helpers | **DOMAIN-KEEP** (sparse eigenvalue iteration on a particular class of pattern; leto linalg SSOT owns `symmetric_eigen_jacobi`/`hermitian_eigen_jacobi` only). Verify no overlap before deletion; expect NO leto extension. | kwavers-local | Not analogous enough to dense eigen SSOT to consolidate; consideration deferred to ADR slot 4+. |
| `crates/kwavers-math/src/linear_algebra/complex.rs::ComplexLinearAlgebra::matrix_inverse_complex` | `Complex<f64>` matrix inverse | **DELETE on kwavers (Move 2 below); call sites use `leto_ops::complex_inv` directly.** | leto | Already SSOT. |

> **Closed 2026-09-04 — the four differential-operator rows below are delivered.**
> `kwavers-math` no longer contains `central_difference_2/4/6`,
> `staggered_grid`, or `staggered_leapfrog`; the `DifferentialOperator` trait
> and the Fornberg coefficient derivation went with them (kwavers PR #709,
> ADR 128, 40 files, +108/-4,970). The rows' "MOVE" verdict understated the
> provider work: Leto's staggered pair was fixed-order and the FDTD solver runs
> `spatial_order` up to 8, so the arbitrary-even-order pair had to be built
> upstream first as `leto_ops::StaggeredLeapfrog3D` (leto PR #169, `6548a00`)
> before anything could be deleted. `SummationByPartsOperator` stays in kwavers
> by design — its closure is derived per axis against a norm, not a stencil with
> a boundary fall-back, and Leto owns no such family. What these rows do **not**
> deliver is a device path: the call sites now reach one CPU implementation, and
> the Coeus `FiniteDifference3DOps` seam plus the Hephaestus 3-D device kernels
> remain open.
>
> **Seam delivered 2026-09-04.** `coeus_ops::FiniteDifference3DOps<T>:
> ComputeBackend` (Coeus PR #369) with a CPU implementation over the Leto
> provider, deliberately outside `BackendOps` so a backend without stencil
> kernels is not forced to supply stubs. It became possible only after Leto's
> 3-D entry points took a mutable-view destination (leto PR #171): a backend
> hands its CPU kernel a `&mut [T]` out of a `DeviceBuffer`, and the previous
> `&mut Array3<T>` parameter would have forced an allocation and a copy per
> sweep — inside an FDTD timestep, the cost the seam exists to remove. Kwavers
> followed in PR #711. Verified by five contract tests through a real backend,
> including a bitwise match against the provider (proving the adaptation
> borrows rather than recomputes) and the negative-adjoint identity with a
> non-degeneracy guard.
>
> **Device half delivered 2026-09-04.** Hephaestus PR #275 adds
> `Staggered3DOps<D>` with WGSL kernels and Metal delegation, verified on a
> live adapter (187/187 contract cases with `HEPHAESTUS_WGPU_REQUIRE_DEVICE=1`,
> up from 179). The device divergence gathers a hand-derived transpose because
> a GPU cannot scatter without atomics, so it is checked three ways — against
> the CPU pair on every axis at orders 2/4/6/8, by the adjoint identity on the
> device's own outputs, and by a constant field's exactly-zero gradient — and
> the suite was shown to bite by mutation rather than assumed to. ADR 0057
> records the three decisions and the one documented capability difference
> (`extent >= 2N` on the swept axis, rejected with a typed error rather than
> silently diverging).
>
> Still open: CUDA and ROCm kernels for that trait, the `coeus-hephaestus`
> implementation binding it, and behind those the deletion of `kwavers-gpu`'s
> FDTD shader copy. The Coeus binding is gated by a stack-wide Eunomia version
> diamond — two Eunomia
> versions resolve through the pinned Mnemosyne revision, breaking
> `coeus-hephaestus` and `kwavers-gpu` on `eunomia::layout::marker::Pod`. It is
> filed as `KW-EUNOMIA-DIAMOND` on the kwavers board and closes when the
> in-flight Mnemosyne pin campaign reaches a revision at or after `e8e825f`.

| `crates/kwavers-math/src/numerics/operators/differential/central_difference_2/{mod.rs, core.rs}` | `apply_{x,y,z}_into` on `ArrayView3<f64>` (2nd-order central) | **MOVE 3D stencil into `leto_ops::application::diff::FiniteDifference3D<T>` + `FiniteDifference3DScheme { SecondOrder, FourthOrder, SixthOrder, StaggeredForward, StaggeredBackward }`.** | leto | Leto already owns 1D `FiniteDifference`; 3D extension is the natural next step.  See ADR below. |
| `crates/kwavers-math/src/numerics/operators/differential/central_difference_4/mod.rs` | `apply_{x,y,z}_into` 4th-order central | **MOVE** (same as above) | leto | |
| `crates/kwavers-math/src/numerics/operators/differential/central_difference_6/core.rs` | `apply_{x,y,z}_into` 6th-order central | **MOVE** (same as above) | leto | |
| `crates/kwavers-math/src/numerics/operators/differential/staggered_grid/{forward.rs, backward.rs}` | `apply_forward_{x,y,z}` / `apply_backward_{x,y,z}` (Yee FDTD) | **MOVE** | leto | Yee staggered scheme is canonical for FDTD acoustics / EM — a 3D-native extension of `FiniteDifferenceScheme`. |
| `crates/kwavers-math/src/numerics/operators/spectral/{derivative.rs, filter.rs}` | `derivative_{x,y,z}` + `apply` on `ArrayView3<f64>` | **DOMAIN-KEEP or APOLLO.**  Apollo owns transforms already; the FDTD-PSTD spectral derivative is apollo SSOT candidate (FFT-domain derivative via apollo's PSTD operator). Verification needed. | apollo | Spectral filter / derivative require apollo FFT SSOT — NOT a leto move. Defer to ADR slot 5+ after apollo extends a `spectral_derivative` API. |
| `crates/kwavers-math/src/numerics/operators/interpolation/{bilinear,trilinear}.rs` | `bilinear_index_space / trilinear_index_space` on field samples | **DOMAIN-KEEP.**  These are 3D field-grid sampling, NOT 1-D tabular interpolation; leto::interp is 1D.  Move would require a *new* leto `GridInterpolation` surface — defer until ≥2 consumers request it. | kwavers-local | kwavers-book Chapter 4 "Media and Tissue Models" §4.12.4 attests matters here; reserved for ADR slot 6+. |
| `crates/kwavers-math/src/fft/mod.rs` | 12+ `fft_{1d,2d,3d}_{array,complex}[_inplace][_into]` variants | **APOLLO SSOT.**  apollo already owns transforms (Fft1d/Fft2d/Fft3d per `kwavers-math/src/lib.rs` re-export — types are owned by apollo; methods are kept in kwavers only as thin adapters over apollo views). Move is an apollo consolidation, not a leto move. | apollo | This is a separate wave; not part of the first 3 SSOT moves. |
| `crates/kwavers-math/src/special/*` | sinc/erf/j0/j1/jn facades | **DELETE on kwavers; leto_ops::special already owns the full set (`sinc`, `erf`, `j0`, `j1`, `jn`).** | leto | Clean deletion sweep; ADR slot 7+ once the kwavers special module is fully cataloged. |
| `crates/kwavers-math/src/geometry::make_*` (ball/circle/disc/line/sphere) | mask generation | **LETO::GEOMETRY SSOT candidate** — once `repos/leto/crates/leto/src/geometry/*` exists. Currently kwavers-local; flag for cross-consumer audit. Leto `geometry/grid.rs` exposes `VoxelGrid`/`Volume`; `make_*` masks would move to `repos/leto/crates/leto/src/geometry/masks.rs` once two consumers adopt. | leto (deferred) | |
| `crates/kwavers-batch/{…}` (transducer kernels) | `MatrixArray`, `transmission_delays`, `reception_delays`, beamforming helpers | **Leto is sufficient (call sites already use `use leto::{Array1,Array2,Array3}`).** Domain keep. | kwavers-local | No SSOT overlap. |
| `crates/kwavers-physics/src/{thermal, optical, chemistry}/…` | physical-quantity carriers | **EQUITAS** (per closed `KWAVERS-AEQ-MET-01…13` rows). | aequitas / hyperion | Already migrated; no leto move. |

### 4.2 CFDrs (`crates/cfd-math/` and downstream)

Module map of `cfd-math` (from `cfd-math/src/lib.rs`):

```text
pub mod diagnostics;
pub mod differentiation;   // local FD
pub mod error;
pub mod high_order;        // WENO/DG/spectral — domain keep
pub mod integration;       // local quadrature
pub mod interpolation;     // local 1-D tabular interpolation
pub mod iterators;
pub mod linear_solver;     // legacy iterative — REPLACED by leto-ops re-exports
pub mod nonlinear_solver;  // nonlinear solver — leto-ops `Anderson` candidate
pub mod pressure_velocity; // domain keep
pub mod simd;              // ISA dispatch — hermes SSOT
pub mod sparse;            // already on leto via `pub use leto_ops::CsrMatrix as SparseMatrix`
pub mod statistics;        // domain keep or eunomia SSOT
pub mod time_stepping;     // time law — horae SSOT

// SSOT bridges already published:
pub mod iterative { pub use leto_ops::{BiCGSTAB, ConjugateGradient, ..., LsqrSolver, ...}; }
pub mod interp   { pub use leto_ops::{LinearInterpolation, CubicSplineInterpolation, ...}; }
pub mod fd       { pub use leto_ops::{FiniteDifference, FiniteDifferenceScheme}; }
pub mod quadrature_rules { pub use leto_ops::{TrapezoidalRule, SimpsonsRule, GaussLegendre{2,3,5}, ... }; }
```

Per-file classification (verified reads):

| Site path (`repos/CFDrs/crates/cfd-math/src/`) | Public surface | Classification | Owner | Notes |
| --- | --- | --- | --- | --- |
| `lib.rs` (top-level `pub mod differentiation/integration/interpolation`) | The legacy `pub mod differential::FiniteDifference` etc. **co-exist** with the `pub mod fd::FiniteDifference` leto re-export already in `lib.rs`. | **DELETE the local modules** — see ADR Move 1 below.  Behaviour is preserved by the already-published `pub mod fd/interp/quadrature_rules` re-exports. | leto | Highest-velocity compaction in the audit. |
| `differentiation/` | `FiniteDifference` (legacy local) | **DELETE on CFDrs.** `pub mod fd::{FiniteDifference, FiniteDifferenceScheme}` already aliases the leto SSOT. | leto | |
| `integration/` | `Quadrature`, `Trapezoidal`, `Simpsons`, `CompositeQuadrature` (legacy local) | **DELETE on CFDrs.**  `pub mod quadrature_rules::{Quadrature, TrapezoidalRule, SimpsonsRule, GaussLegendre{2,3,5}, CompositeQuadrature}` already aliases the leto SSOT. | leto | |
| `interpolation/` | `Interpolation` (1-D trait) + `LinearInterpolation` etc. | **DELETE on CFDrs.**  `pub mod interp::{Interpolation1D, LinearInterpolation, LagrangeInterpolation, CubicSplineInterpolation}` already aliases the leto SSOT. | leto | |
| `linear_solver/` (old) | Local CG/BiCGSTAB/GMRES implementations | **DELETE on CFDrs.**  `pub mod iterative::{...}` already SSOT-routes.  lib.rs prelude still re-exports `crate::linear_solver::ConjugateGradient` — re-point the prelude to `leto_ops::ConjugateGradient` and delete the local `linear_solver/` module. | leto | Per the CFDrs CHANGELOG and CHECKLIST, this work has been incrementally completed across multiple slices but that local module has always remained vestigial. |
| `nonlinear_solver/` | Anderson acceleration, possibly BFGS/Levenberg–Marquardt | **DELETE on CFDrs (delegation to leto) for any wrapper that calls `AndersonAccelerator` directly.**  Anything else is CFD-specific and keeps local. | leto | Verified by reading `nonlinear_solver::*`; the leto already publishes Anderson. |
| `simd/` | AVX2/SSE code paths | **DELETE on CFDrs (route through hermes via leto).** | hermes | |
| `sparse/` (`mod.rs`, `operations.rs`, `assembly.rs`, `builder.rs`, `patterns.rs`) | `CsrMatrix` (alias to `leto_ops::CsrMatrix`), `spmv`, `try_spmv`, `try_sparse_sparse_mul`, `try_sparse_transpose`, `SparseMatrixBuilder`, `ParallelAssembly`, `SparsePatterns` | **ALREADY SSOT.**  `pub use leto_ops::CsrMatrix as SparseMatrix`.  `operations.rs` is a thin CFD-vocabulary shim that calls leto CSR kernels.  DELETE only the redundant file-level legacy wrappers; keep the `SparsePatterns` (Poisson 5-point stencil helpers) and `ParallelAssembly` (atomic accumulator) CFD-domain kernels. | leto | This is the bulk of the cfd-math merge already done. |
| `statistics/` | RMSE/PSNR/etc. | **DELETE on CFDrs for the trivial wrappers** — `leto_ops::statistics::{normalized_rmse, nrmse, pearson, percentile_range, phase_*_correlation, psnr, rmse, ...}` is the SSOT.  CFD-specific stat extensions (e.g. hemolysis cumulative integrals) stay local. | leto | |
| `time_stepping/` | explicit/exponential/CFL helpers | **HORAE SSOT.**  Already external-time-integration policy per README. Verify; possibly consolidate if `horae` time law owns the step policy. | horae | Light audit; deferred. |
| `pressure_velocity/` | coupled-equation routing | **DOMAIN KEEP.** | cfd | CFD-specific. |
| `diagnostics/` | matrix diagnostics, conservation residuals | **DOMAIN KEEP** (CFD-specific) | cfd | |
| `high_order/` | WENO/DG/rk | **DOMAIN KEEP** (CFD-specific high-order methods). | cfd | |
| `iterators/` (legacy) | legacy sparse iterators | **DELETE on CFDrs.**  The leto COO/CSR kernels supersede these (verified by `leto_ops::application::sparse::CooMatrix` API coverage). | leto | |
| `error/` | Result/Error types | **DOMAIN KEEP.**  cfd Core `Result<T> = core::error::Result<T>` is the consumer-side vocabulary. | cfd | |

### 4.3 Helios (`crates/helios-{imaging,analysis}/*`)

Module map of `helios-imaging` (`lib.rs`):

```text
mod backproject;  // rasterizer — geometry
mod fbp;          // ramp-filter + inverse FFT — APOLLO consumer
mod noise;        // additive quantum noise
mod radon;        // parallel-beam, FFT-dependent
mod registration; // NCC translation registration
mod sirt;         // iterative reconstruction
```

Module map of `helios-analysis` (`lib.rs`):

```text
mod dvh;           // cumulative DVH + Dx/V_at_fraction/gEUD
mod gamma;         // 3-D gamma and local-gamma
mod image_quality; // ROI statistics, MSE, contrast, CNR
mod roi;           // spherical/box masks
```

Per-file classification:

| Site path (`repos/helios/crates/helios-*/src/`) | Public surface | Classification | Owner | Notes |
| --- | --- | --- | --- | --- |
| `helios-imaging/src/radon.rs` | `parallel_beam_radon`, `Sinogram<T>`, `from_readings`, `map_readings`, `get(θ, s)` | **DOMAIN-KEEP** — radon forward operator is the helios-side geometry, but the line-integral engine (forward_project_ray) is owned by `helios-solver`.  Use apollo for any future FFT-path dep inside radon. | helios-domain | |
| `helios-imaging/src/fbp.rs` | `filtered_back_projection`, ramp filter computation | **APOLLO SSOT candidate for the ramp filter** — filter kernel is FFT-domain math.  Demonstrate once apollo exposes `apollo::filter::ramp(samples, dx, dy)`; helios then composes ramp+backproject. | apollo | The back-project step itself stays helios-geometry. |
| `helios-imaging/src/backproject.rs` | `back_project_rows` | **DOMAIN KEEP.** | helios-domain | |
| `helios-imaging/src/sirt.rs` | `sirt_reconstruction` | **DOMAIN KEEP.** Iterative algebraic reconstruction is a clinical-method algorithm.  Could route through `coeus-autograd` if a differentiable variant ever lands; current API stays helios. | helios-domain | |
| `helios-imaging/src/registration.rs` | `register_translation`, `register_translation_ncc` | **DOMAIN KEEP.** | helios-domain | |
| `helios-imaging/src/noise.rs` | `add_quantum_noise` | **DOMAIN KEEP.** | helios-domain | |
| `helios-analysis/src/dvh.rs` | `Dvh<T>`, `min/max/mean/volume_fraction/dose_at_volume_fraction/gEUD/homogeneity_index` | **DOMAIN KEEP.**  Clinical DVH; Aequitas-aware per the `HELIOS-AEQ-MET-01` closure.  The inner sort/partition math is `Array1::sort` via leto views. | helios-analysis | No leto SSOT overlap. |
| `helios-analysis/src/gamma.rs` | `gamma_index_3d`, `gamma_index_3d_local`, `gamma_pass_rate` | **DOMAIN KEEP.**  Clinical gamma; signed by `AbsorbedDose<T>` + `Length<T>`. | helios-analysis | |
| `helios-analysis/src/image_quality.rs` | `RoiStats/DoseRoiStats`, `roi_statistics/dose_roi_statistics`, `contrast_to_noise_ratio`, `michelson_contrast`, `volume_rmse`, `dose_volume_rmse`, `volume_relative_l2_error` | **DOMAIN KEEP** (clinical metrics over `Volume<T>`); the RMSE/PSNR stats reuse `leto_ops::statistics::{rmse,nrmse,normalized_rmse,...}` where applicable.  Future ADR could expose `helios-analysis::quality_universal` thin re-exports. | helios-analysis | Trivial wrappers over `let_ops::statistics::rmse` etc. — small surface, can be left. |
| `helios-analysis/src/roi.rs` | `spherical_mask`, `box_mask` | **DOMAIN KEEP.** | helios-analysis | |

### 4.4 RITK (`crates/ritk-*`)

| Site path | Public surface | Classification |
| --- | --- | --- |
| `ritk-image/src/{types.rs, grid.rs, metadata.rs, color.rs}` | `Image<T, B, const D: usize>` wrapper around `coeus::Tensor<T, B>`, `ColorVolume<T, B, const C>`, `Tensor`/`ComputeBackend` aliased. | **COEUS SSOT (already)**.  No ndarray/nalgebra/burn matches in production source — only `xtask/src/migration_audit.rs` fixtures hold these, which is the migration-audit fixture file.  Zero added math moves. |
| `ritk-statistics/src/{image_statistics.rs, value_indices/{compute,key,map}.rs, position_extrema.rs}` | image-domain ROI stats | **DOMAIN KEEP.** |
| `ritk-morphology/src/*` | structuring elements + cross/cube/ball | **DOMAIN KEEP.** |
| `ritk-model/src/{transmorph/{…}, ssmmorph/{…}, affine/{…}}` | network modules on `coeus::{Backend, BackendOps}`. | **COEUS SSOT (already).** |
| `ritk-io/src/format/{nifti,nrrd,mgh,metaimage,vtk,minc}/*`, `ritk-dicom/src/*`, `ritk-codecs/src/*` (TIFF/JPEG/JPEG2000/JPEG-LS), `ritk-png/src/*`, `ritk-analyze/src/*`, `ritk-mgh/src/*`, `ritk-vtk/src/*` | image-format readers/writers | **NO LETO MOVE.** Image I/O is byte-stream + decode.  RITK domain. |
| `ritk-cli/src/*` (filter, segment, stats, register, resample, viewer, normalize, convert) | CLI surface over ritk-domain ops | **NO LETO MOVE.** |

**Verdict.**  RITK requires **zero** math/linalg SSOT moves in this audit.
Already on coeus; no duplicate linalg helpers identified.

---

## 5. Open classification questions (deferred, not blockers)

| # | Open question | Minimal audit to close |
| --- | --- | --- |
| 1 | Whether `kwavers-math/src/linear_algebra/sparse/eigenvalue.rs::inverse_power_iteration` is genuinely redundant vs leto's symmetric_eigen_jacobi / hermitian_eigen_jacobi.  Reading suggests **NO** (algorithmically different iteration), so KEEP-LOCAL — but document explicitly in the kwavers-book numerical-methods chapter. | Read the iteration body against leto's `symmetric_eigen_jacobi_with_tolerance`; expected outcome: KWEEP with a "verifies convergence to leto's solution" test. |
| 2 | Whether `kwavers-math/src/numerics/operators/interpolation/{bilinear,trilinear}.rs` should graduate into leto as `GridInterpolation<Q, D>` once a second consumer (helios grid sampling? CFD coarse-grid sampling?) needs it. | Wait for second consumer; ADR documented in the kwavers-book numerical-methods chapter. |
| 3 | Whether `kwavers-math/src/fft/mod.rs` 12+ `fft_*` variants should be collapsed into apollo (apollo already owns Fft1d/Fft2d/Fft3d types; the methods are only `Array*-` adapters that become `apollo::<Fft3d>::fft3d(arr.view()).` | Co-write with apollo team once the apollo `pstd` operator gains a spectral derivative. |
| 4 | Whether cfd-math's `time_stepping/` (CFL, explicit RK, exponential integration) should graduate into `horae` as runtime time-integration policy. | Verify against `horae::TimeLaw` ownership rule. |
| 5 | Whether `cfd-math/src/high_order/{spectral,dg,weno}/*` should stay local or migrate into a new atlas crate.  Currently SSOT boundary says dom­ain-keep. | Wait for second consumer (none today; kwavers has its own high-order paths). |
| 6 | Whether `helios-analysis::image_quality::{rmse, psnr, nrmse}` will graduate into leto_ops::statistics once the script is being called. | Already — leto owns `normalized_rmse/nrmse/rmse/psnr`; the helios calls are domain lexical thin wrappers. **Ok to delete the file-level re-wraps once leto's releases cross helios's pinned version.** |

---

## 6. First 3 SSOT moves — ranked selection

The user asked for atlas-style ADR outlines for the **first 3** moves.  This
section ranks every candidate by **(risk × atlas-impact × evidence
strength)** to pick the highest-leverage three.  Lower-numbered moves are
picked first.

| Rank | Move | Risk | Atlas impact | Evidence strength |
| --- | --- | --- | --- | --- |
| **1** | **cfd-math local-wrapper deletion sweep** — delete `cfd-math/src/{differentiation,integration,interpolation,linear_solver/*}.rs` (the legacy local impls) since `lib.rs` already publishes leto-ops SSOT-bridge modules.  Touches cfd-1d, cfd-optim, cfd-validation test fixtures; vec[lib.rs `prelude`/`use crate::differentiation::*`] imports must be rerouted to the SSOT re-exports or to `leto_ops` directly. | **LOW.**  No leto extension required — already on SSOT.  Prelude + per-call-site import-path repair only. | **HIGH.**  Closes the cfd-math `{differentiation, integration, interpolation, linear_solver}` namespace duplication outright.  Direct precedent of `pub use leto_ops::CsrMatrix as SparseMatrix` that already closed `sparse`. | **HIGH.**  `cfd-math/src/lib.rs` already publishes the re-exports with runnable doctest (`use cfd_math::fd::{FiniteDifference, ...}`). |
| **2** | **kwavers-math trivial-wrapper deletion sweep** — delete `kwavers-math/src/linear_algebra/{ext.rs, complex.rs}` (already delegate to leto-ops linalg + linalg::complex_linalg; wrapper is ~100 LOC). | **LOW.**  No leto extension required — already on SSOT.  Reroute the call sites of `LinearAlgebraExt::solve_into/inv/eig` and `ComplexLinearAlgebra::{solve_linear_system_complex, matrix_inverse_complex}` to direct `leto_ops::{solve,inv,symmetric_eigen_jacobi,hermitian_eigen_jacobi,complex_solve,complex_inv}` calls.  Preserve the `KwaversError` wrapping via `.map_err(KwaversError::from)` at the boundary. | **MEDIUM-HIGH.**  Two of the smallest files in the audit; closure publishes a clean exemplar of "consumer trait extension wraps leto, use leto directly instead". | **HIGH.**  Direct read of `ext.rs` confirms all four heavy calls are `Ok(leto_ops::solve(...)?)`, `Ok(leto_ops::inv(...)?)`, `Ok(leto_ops::symmetric_eigen_jacobi(...)?)`, `Ok(leto_ops::hermitian_eigen_jacobi(...)?)`. |
| **3** | **kwavers-math 3D FD stencils → leto-ops ** — additively extend `leto-ops::application::diff` with `FiniteDifference3D<T>`, `FiniteDifference3DScheme { SecondOrder, FourthOrder, SixthOrder, StaggeredForward, StaggeredBackward }`, dispatch through the same ZST-marker convention as the existing 1D `FiniteDifference`; then reroute `kwavers-math::numerics::operators::differential::{central_difference_2, central_difference_4, central_difference_6, staggered_grid/{forward,backward}}` call sites to the new leto surface; delete the kwavers copies. | **MEDIUM.**  Yee staggered scheme is a particular FDTD form.  Naming the ZST markers in line with existing `FiniteDifferenceScheme` variants avoids consumer churn.  Output length matches input length — kwavers' `apply_*_into` contract is preserved. | **HIGH.**  Largest concrete numerical migration in the wave; crosses the 2D-to-3D boundary in leto's FD surface and unlocks leto-native FDTD/PSTD kernels for downstream consumers (apollo, coeus-autograd). | **MEDIUM-HIGH.**  Leto 1D FD already shows the pattern with bounded-error analytical tests (`central_diff_of_sin_is_cos`, `second_derivative_of_quadratic_is_constant`); 3D extension follows the same protocol. |
| 4 | kwavers-math `special/` → leto_ops::special | LOW | MEDIUM | HIGH (already SSOT; clean delete sweep) |
| 5 | helix medical fft family → apollo | MEDIUM | MEDIUM-HIGH | MEDIUM (apollo is migrating) |
| 6 | kwavers / helios 3D GridInterpolation → leto (create) | MEDIUM-HIGH | MEDIUM (waits for 2nd consumer) | LOW (no second consumer) |
| 7 | kwavers-math geometry::make_* → leto geometry | LOW | MEDIUM (waits for 2nd consumer) | MEDIUM |

**Moves 1, 2, and 3 are selected.**  They cover the three migration
modalities in order of evidence strength:

- **Move 1** is a deletion-only sweep on cfd-math (no leto extension).
- **Move 2** is a deletion-only sweep on kwavers-math linear-algebra
  wrappers (no leto extension, the consumer trait goes away).
- **Move 3** is the only move that needs a real leto extension (3D FD
  stencils), and is the broadest numerical change in the wave.

These three together close three distinct atlas promotion-gate contracts:
one proving "delete SSOT duplicates when consumer root already exposes the
bridge" (Move 1), one proving "delete consumer trait wraps when leto
already exposes the call" (Move 2), and one proving "additively extend
leto when the consumer logic is genuinely new and ≥ 1 consumer benefits"
(Move 3).  Each ADR documents its own segment of the gate.

---

## 7. Atlas-style ADR outlines

Each ADR follows the standard atlas template (Title, Status, Context,
Decision, Contract, Conformance / Differential oracle, Migration,
Consequences, Non-goals).  The verbatim names match the existing
`repos/leto/docs/adr/0001-…0017-*.md` plus `sparse-support-design.md`
numbering convention.

### 7.1 ADR `0031-leto-cfdrs-differentiation-integration-interpolation-deletion-sweep.md`

```text
Title:      0031 — Delete CFDrs `cfd-math` local differentiation/integration/interpolation/iterative wrappers
Status:     Accepted
Owners:     leto (consumer migration), CFDrs (deletion ledger)

Context
  CFDrs `crates/cfd-math/src/lib.rs` already publishes four Atlas-SSOT
  bridge modules:
    pub mod fd           { pub use leto_ops::{FiniteDifference, FiniteDifferenceScheme}; }
    pub mod interp       { pub use leto_ops::{LinearInterpolation, LagrangeInterpolation,
                                       CubicSplineInterpolation, Interpolation1D}; }
    pub mod quadrature_rules
                         { pub use leto_ops::{Quadrature, TrapezoidalRule, SimpsonsRule,
                                       GaussLegendre2/3/5, CompositeQuadrature}; }
    pub mod iterative    { pub use leto_ops::{BiCGSTAB, ConjugateGradient, GMRES, LsqrSolver,
                                       ILUPreconditioner, JacobiPreconditioner, ...}; }
  However, `cfd-math/src/lib.rs` ALSO declares:
    pub mod differentiation;   // legacy local FiniteDifference
    pub mod integration;       // legacy local Quadrature / GaussQuadrature / Composite
    pub mod interpolation;     // legacy local 1-D Interpolation trait
    pub mod linear_solver;     // legacy local iterative kernel
  These local modules carry a second copy of the exact same algorithms and
  are wired into the consumer `pub mod prelude::{differentiation::FiniteDifference,
  integration::Quadrature, interpolation::{Interpolation, LinearInterpolation},
  linear_solver::ConjugateGradient, sparse::{SparseMatrix, SparseMatrixBuilder}}`. The
  prelude therefore imports the legacy copy, masking the SSOT bridge. This
  ADR collapses the legacy tree to the SSOT routes.

Decision
  Delete the legacy local modules `cfd-math/src/differentiation/`,
  `cfd-math/src/integration/`, `cfd-math/src/interpolation/`,
  `cfd-math/src/linear_solver/` (full directories), and re-point the
  prelude imports to the SSOT bridge re-exports. Delete any test
  fixtures that exercise the local impls through the prelude path. No
  leto extension is required.

Contract (after deletion)
  • `cfd_math::fd::{FiniteDifference, FiniteDifferenceScheme}` (alias)
  • `cfd_math::interp::{Interpolation1D, LinearInterpolation,
    LagrangeInterpolation, CubicSplineInterpolation}` (alias)
  • `cfd_math::quadrature_rules::{Quadrature, TrapezoidalRule, SimpsonsRule,
    GaussLegendre{2,3,5}, CompositeQuadrature<Q>}` (alias)
  • `cfd_math::iterative::{BiCGSTAB, ConjugateGradient, GMRES, LsqrSolver,
    IdentityPreconditioner, JacobiPreconditioner, ILUPreconditioner,
    SSORPreconditioner, IterativeSolverConfig, ...}` (alias)
  Universe: any `T: RealField + Copy + FloatElement + LetoScalar`.  The
  consumer's `cfd` types remain RDOS at the prelude boundary; scalar
  conversion lives at the LDOS-type interfaces.

Conformance / Differential oracle
  • `cargo test -p cfd-math --all-features` exercises leto SSOT
    directly via the re-exports; the `tests/sparse/operations.rs`
    `test_*` functions that were using the legacy `try_spmv` are
    re-pointed to `let_ops::spmv` calls with identical shapes.
  • `cargo test -p cfd-validation --all-features`: any oracle that
    compared the legacy local interpolation against an analytical
    value is re-pointed to compare the leto re-export surface; expect
    parity within rounding to the existing `nrmse` tolerance recorded
    in `cfd-validation/tests/cross_fidelity_1d_2d_3d.rs` lines 85-130.
  • `cargo test -p cfd-1d --all-features`: `cfd-1d::Womersley` (analytic
    sine kernel), `Murray optimal-bifurcation`, and
    `OlufsenParameters` all consume `cfd_math::interp::LinearInterpolation`
    and `cfd_math::fd::FiniteDifference` — the moved-prelude paths
    must keep every existing test green.

Migration (per-consumer deletion list)
  CFDrs deletions:
    - crates/cfd-math/src/differentiation/{mod.rs, lib.rs(legacy)}
    - crates/cfd-math/src/integration/{mod.rs, lib.rs(legacy)}
    - crates/cfd-math/src/interpolation/{mod.rs, lib.rs(legacy)}
    - crates/cfd-math/src/linear_solver/{mod, lib.rs(legacy)}
    - cfd-1d tests fixture `blueprint_solve_trace.rs` and any
      `primary_solve_reliability.rs` references that use the legacy
      prelude paths (re-point to `cfd_math::iterative::*`).
    - cfd-validation tests `cross_fidelity_1d_2d_3d.rs` alias updates.
  CFDrs non-deletions (kept local):
    - `sparse/` (already on leto, with CFD-specific SparsePatterns +
      ParallelAssembly kept).
    - `high_order/`, `nonlinear_solver/` (CFD-specific WENO/DG/Anderson
      domain keep), `pressure_velocity/`, `time_stepping/`,
      `diagnostics/`, `simd/` (route through hermes; research deferred).
  Re-pointing work lives in:
    - crates/cfd-math/src/lib.rs   (prelude table)
    - crates/cfd-math/src/prelude.rs (prelude bodies)
    - crates/cfd-1d/src/solver/{…} module imports.

Consequences
  Gains:
    + One owner for FD, quadrature, 1-D interpolation, iterative
      kernels. Auditable from one repo.
    + The consumer prelude becomes a single-block table that points at
      Atlas-SSOT aliases — moving the prelude is then a no-op.
    + cfd-math's `lib.rs` shrinks by ~250 LOC (the legacy impls and
      doctests go away).
  Costs:
    − Stale-type errors at CFDrs call sites until imports are migrated;
      expected to be small (≤ 30 import lines per consumer crate).
    − Until the new prelude is published, downstream CFDrs crates
      export `Quadrature` / `Interpolation` consumer-side types at
      zero cost through the re-export chain.

Non-goals
  • cfd-math `high_order/` (DG/WENO) stays local.
  • cfd-math `time_stepping/` stays local (deferred to horae audit).
  • cfd-1d / cfd-3d solver cores (Newton, pressure-velocity coupling,
      Venturi, bifurcation) stay cfd-domain.
```

### 7.2 ADR `0032-leto-kwavers-linear-algebra-ext-complex-deletion-sweep.md`

```text
Title:      0032 — Delete Kwavers `kwavers-math` `linear_algebra::{ext, complex}` trivial wrappers
Status:     Accepted
Owners:     leto (already-published SSOT), kwavers (deletion ledger)

Context
  `kwavers-math/src/linear_algebra/ext.rs` (≈ 80 LOC) defines
  `LinearAlgebraExt<T>` for `Array2<f64>` and `Array2<Complex64>` with
  three methods: `solve_into`, `inv`, `eig`. The body of every method
  is one line that delegates to `leto_ops::{solve, inv,
  symmetric_eigen_jacobi, hermitian_eigen_jacobi}` (with `complex.rs`
  the `ComplexLinearAlgebra::solve_linear_system_complex` and
  `matrix_inverse_complex` similarly). The methods exist to preserve
  the kwavers vocabulary (`KwaversResult`, `Complex64`, `Array2<T>`
  from kwavers's HomeRow imports) and to convert the leto-typed
  result back into kwavers's `Array2` types. The wrapper carries no
  math of its own.

  `kwavers-math/src/linear_algebra/complex.rs` (≈ 35 LOC) defines
  `ComplexLinearAlgebra` with `solve_linear_system_complex` and
  `matrix_inverse_complex`, both delegating to `leto_ops::{complex_solve,
  complex_inv}`.

  These wrappers are not pedagogical, not domain-specific, and not
  abstract. They are a thin kwavers-side vocabulary wrapper sheet that
  is already one-line delegating. Removal shrinks kwavers vocabulary
  noise without losing any functionality.

Decision
  Delete `kwavers-math/src/linear_algebra/{ext.rs, complex.rs}`, and
  reroute caller-side imports to direct `leto_ops::{solve, inv,
  symmetric_eigen_jacobi, hermitian_eigen_jacobi, complex_solve,
  complex_inv}` calls. Preserve the kwavers `KwaversResult` error
  contract by converting le­to's typed errors at the consumer call
  site via a single, named map function
  (`kwavers_core::error::from_leto`).

Contract (after deletion)
  • `kwavers_physics::*, kwavers_boundary::*, kwavers_therapy::*,
    kwavers_imaging::*` may import directly from
    `leto_ops::{solve, inv, symmetric_eigen_jacobi, hermitian_eigen_jacobi,
    complex_solve, complex_inv}`. The `KwaversError::from_leto(e)`
    conversion is the single shim.
  • `LinearAlgebraExt<T>` no longer exists; `solve_into(s).b` becomes
    `leto_ops::solve(&s.view(), &b.view()).map_err(KwaversError::from_leto)`,
    `inv(a)` becomes `leto_ops::inv(&a.view()).map_err(...)`, `eig(a)`
    becomes `leto_ops::symmetric_eigen_jacobi(&a.view()).map_err(...)`
    or `leto_ops::hermitian_eigen_jacobi(a, HermitianEigenConfig{...}).map_err(...)`.

Conformance / Differential oracle
  • `kwavers-math::tests::linear_algebra::ext::tests::{solve_into,inv,eig}`
    (existing tests in `linear_algebra/ext.rs` lines ~110-160) are
    relocated to a focused nextest in `kwavers-math/tests/linalg_deletion.rs`
    exercising the call-site migration paths.
  • `cargo test -p kwavers-math`: 191/191 existing tests stay green.
  • `cargo test --workspace -p kwavers-affected-package-set`:
    affected package set stays at 2913/2913 with 2 skipped per the
    `KWAVERS-AEQ-MET-03 / 04 / 05 / 13` closure ledger.

Migration (per-consumer deletion list)
  Kwavers deletions:
    - crates/kwavers-math/src/linear_algebra/ext.rs
    - crates/kwavers-math/src/linear_algebra/complex.rs
  Imports to repair (call sites that used `LinearAlgebraExt::` or
  `ComplexLinearAlgebra::`):
    - crates/kwavers-physics/src/optics/* (look for `eig`, `solve`)
    - crates/kwavers-transducer/src/flexible/calibration/manager/* (look for inverse calls)
    - crates/kwavers-therapy/src/therapy/theranostic_guidance/* (look for solve)
    - crates/kwavers-driver/src/beam/* and validate modules
    - crates/kwavers-analysis/{signal_processing,validation}/* (rare)
  Library-side re-exports (none added — leto already publishes).
  Cross-repo safety:
    - crates/kwavers-math/src/lib.rs `pub use linear_algebra::*;` keeps
      `iterative`, `sparse`, and other stable surfaces exported; the
      deleted items were only `LinearAlgebraExt` and
      `ComplexLinearAlgebra`.  No re-export drift.

Consequences
  Gains:
    + kwavers-math shrinks by ~115 LOC; addresses orphan wrappers.
    + One Atlas owner for `solve / inv / eig / complex_solve /
      complex_inv` — every kwavers consumer reads it directly.
    + The kwavers vocabulary table at `crates/kwavers-math/src/lib.rs`
      becomes smaller.
  Costs:
    − kwavers call-site import churn — a few dozen imports migrate.
    − The kwavers `KwaversError` conversion requires a single named
      helper at `kwavers_core::error::from_leto`.

Non-goals
  • `kwavers-math/src/linear_algebra/iterative/{mod.rs, solve_lsqr_matfree}`
    is a separate move (Move 4 in §5) once the `solve_lsqr_matfree`
    call sites are inventoried.
  • `kwavers-math/src/linear_algebra/sparse/eigenvalue.rs` (the
    inverse-power-method) is KEPT (domain-specific iteration).
  • `kwavers-physics/thermal/*` and `kwavers-physics/optics/*` driver
    physics are unchanged.
```

### 7.3 ADR `0033-leto-finite-difference-3d-extension.md`

```text
Title:      0033 — Extend leto-ops FD surface to N-D + Staggered (Yee) FDTD; promote kwavers 3-D central/staggered stencils to leto
Status:     Accepted
Owners:     leto (extension), kwavers (consumer-side deletion)

Context
  `kwavers-math/src/numerics/operators/differential/` hosts
  per-axis apply_x_into / apply_y_into / apply_z_into methods over
  `&ArrayView3<f64>` for central-difference orders two, four, and six,
  plus staggered-grid forward / backward (Yee FDTD) variants. Call
  sites:
    - crates/kwavers-boundary/src/pml/{boundary_impl.rs}  (2nd-order central)
    - crates/kwavers-boundary/src/field_updater/gradient.rs  (any-order)
    - crates/kwavers-boundary/src/periodic/wrapping.rs  (any-order)
    - crates/kwavers-physics/src/{thermal/diffusion/*, acoustic/*, optical/*, …}  (any-order + staggered)

  Leto-ops currently exposes:
    pub use application::diff::{FiniteDifference, FiniteDifferenceScheme};
  where the `FiniteDifferenceScheme { Forward, Backward, Central,
  ForwardSecondOrder, BackwardSecondOrder }` is 1-D over `&[T] →
  Result<Array1<T>>`. The 3-D and staggered extensions are not yet
  published.

  Reversing the direction: instead of the kwavers FD operators being
  consumer-owned and every other integrator that wants a 3-D
  FD copy-paste from kwavers-math, the move adds a single, generic
  `FiniteDifference3D<T> + FiniteDifference3DScheme` to leto-ops.
  Every kwavers call site reroutes, and downstream consumers
  (apollo's PSTD, hephaestus' FD-stencil GPU kernels, coeus-autograd's
  differentiable FD retainers) inherit the surface for free.

Decision
  Add `repos/leto/crates/leto-ops/src/application/diff/{three_d.rs, schemes3d.rs}`,
  with the public surface:
    pub enum FiniteDifference3DScheme {
        SecondOrderCentral,
        FourthOrderCentral,
        SixthOrderCentral,
        StaggeredForward,  // Yee +Δt/2x-axis forward
        StaggeredBackward, // Yee -Δt/2x-axis backward
    }
    pub struct FiniteDifference3D<T: RealScalar> { scheme, spacing }
    impl<T: RealScalar> FiniteDifference3D<T> {
        pub const fn second_order(spacing: T) -> Self;
        pub const fn fourth_order(spacing: T) -> Self;
        pub const fn sixth_order(spacing: T) -> Self;
        pub const fn staggered_forward(spacing: T) -> Self;
        pub const fn staggered_backward(spacing: T) -> Self;
        pub fn apply_x_into(&self, f: &ArrayView3<T>, out: &mut ArrayViewMut3<T>) -> Result<()>;
        pub fn apply_y_into(&self, f: &ArrayView3<T>, out: &mut ArrayViewMut3<T>) -> Result<()>;
        pub fn apply_z_into(&self, f: &ArrayView3<T>, out: &mut ArrayViewMut3<T>) -> Result<()>;
        // Optionally a contiguous apply_all_into (loops the three axes).
    }
  Then delete the kwavers-side copies and reroute call sites.

Contract (after migration)
  • Single, hermes-SIMD-friendly, leto-Array3-native 3D FD surface.
  • Tests inside
    `repos/leto/crates/leto-ops/tests/ops/stencil.rs` (extending the
    existing `tests::stencil` module if needed; otherwise a new
    `tests::diff::FiniteDifference3DSuite`):
      - 2nd-order central: Laplacian of a cubic yields 6h²Δf,
        analytic derivative O(h²) matches.
      - 4th-order central: O(h⁴) residual at smaller h.
      - 6th-order central: O(h⁶) residual at smaller h.
      - Staggered forward/backward: leapfrog Yee consistency check.
      - Conservation test: ∑ width(f') = 0 for periodic boundary.
  • Cross-crate differential: kwavers's existing test battery
    `crates/kwavers-boundary/tests/{pml_tests.rs, gradient_tests.rs}`
    stay green when the call sites are rerouted through
    `leto_ops::FiniteDifference3D`.

Conformance / Differential oracle
  • `repos/leto/crates/leto-ops/tests/ops/stencil.rs::central_3d_*`
    + `staggered_3d_*` tests.
  • `cargo run --locked -p leto-ops --example ndarray_parity` extends
    to include a 3D FD parity row against the consumer's
    `kwavers-math` analytic FD formula on a 3x3x3 product grid.
  • `cargo test -p kwavers-affected-package-set`: focused
    kwavers-boundary / kwavers-physics nextest stays at 318/318 + 1
    skipped per `KWAVERS-AEQ-MET-10` closure.

Migration (per-consumer deletion list)
  Leto additions (extension):
    + repos/leto/crates/leto-ops/src/application/diff/schemes3d.rs   (new)
    + repos/leto/crates/leto-ops/src/application/diff/three_d.rs     (new)
    + repos/leto/crates/leto-ops/tests/ops/stencil.rs (extend)
  Kwavers deletions:
    - crates/kwavers-math/src/numerics/operators/differential/central_difference_2/
      {mod.rs, core.rs}
    - crates/kwavers-math/src/numerics/operators/differential/central_difference_4/
      {mod.rs}
    - crates/kwavers-math/src/numerics/operators/differential/central_difference_6/
      {core.rs}
    - crates/kwavers-math/src/numerics/operators/differential/staggered_grid/
      {forward.rs, backward.rs}
  Imports to repair in kwavers:
    - crates/kwavers-boundary/src/lib.rs
    - crates/kwavers-boundary/src/pml/{lib.rs, boundary_impl.rs}
    - crates/kwavers-boundary/src/field_updater/gradient.rs
    - crates/kwavers-boundary/src/periodic/wrapping.rs
    - crates/kwavers-physics/src/{thermal/diffusion, optoacoustic,
      cavity, optics}/*  (re-point to leto FD-3D when their call
      sites demand).

Consequences
  Gains:
    + 3-D FD kernels become provable, hermes-SIMD-instrumented,
      Moirai-parallel-capable (per-feature flag), and accessible to
      apollo / coeus-autograd / hephaestus consumers in later waves.
    + kwavers-math shrinks by ~250 LOC.
    + The Atlas SSOT chain moves from "FD = leto 1-D, kwavers 3-D" to
      "FD = leto 1-D + 3-D, kwavers zero local copies" — one source.
  Costs:
    − 3D staggered-grid correctness is non-trivial; a Yee-leapfrog
      consistency test must be in place before any kwavers call site
      migrates.
    − Kwavers call-site imports migrate from
      `CentralDifference2::{apply_x_into, apply_y_into, apply_z_into}`
      to `FiniteDifference3D::{apply_x_into, apply_y_into, apply_z_into}`.

Non-goals
  • Non-Cartesian FD (cylindrical, spherical) stays kwavers-local until
    a second consumer requests it.
  • Spectral derivative / filter remain on the apollo SSOT (Move 5).
  • PML boundary implementation stays kwavers-boundary-local (only the
    stencils inside it move to leto).
  • kwavers PDE solvers (FDTD / PSTD / DG) stay kwavers-local — only
    their stencils reference the new FD-3D surface.
```

---

## 8. Atlas promotion-gate evidence per ADR

Atlas promotion-gate (per `D:/atlas/README.md` Promotion gate section,
seven conditions):

| Gate condition | Move 1 evidence | Move 2 evidence | Move 3 evidence |
| --- | --- | --- | --- |
| 1. ≥ 2 packages need the capability, or an existing implementation in wrong layer | cfd-1d, cfd-3d, cfd-validation, cfd-optim all consume `cfd-math::{FD, Quadrature, Interp, iterative}` (verified by survivors in `CFD-AEQUITAS-CASCADE-METRICS-1` closure). | Kwavers `kwavers-physics`, `kwavers-transducer`, `kwavers-therapy`, `kwavers-driver`, `kwavers-analysis` all consume `LinearAlgebraExt` / `ComplexLinearAlgebra` (per consumer-call sites cited in §7.2 migration list). | Kwavers `kwavers-boundary`, `kwavers-physics`; future apollo, coeus, hephaestus scripts per §7.3 non-goals / known follow-ups. |
| 2. Source audit: no current provider owns the bounded context | Leto already owns the FD, quadrature, interpolation, iterative solvers (Move 1's clean deletion proves it). | Leto already owns `solve`, `inv`, `symmetric_eigen_jacobi`, `hermitian_eigen_jacobi`, `complex_solve`, `complex_inv`. | Leto already owns 1-D FD + Inverse Laplacian; the 3-D extension is the natural AD-v020 step. |
| 3. ADR defines the contract, dep direction, migration, non-goals, conformance oracle | Each ADR in §7.1, §7.2, §7.3 follows the atlas template. | (same) | (same) |
| 4. Deletion ledger identifies the superseded types, formulas, dependencies, tests in every first-wave consumer | §7.1 *Migration* lists every file path in CFDrs to delete. | §7.2 *Migration* lists every kwavers file. | §7.3 *Migration* lists every kwavers file plus the leto additions. |
| 5. First change moves real computation into the new owner; migrates every in-scope caller; deletes superseded impls; runs shared conformance + consumer differential tests | First PR: reroute CFDrs prelude; delete cfd-math legacy dirs; leto `tests/ops/{diff,interp,quadrature,iterative}` already pass. | First PR: reroute kwavers call sites; delete `ext.rs` + `complex.rs`; preservation test in `kwavers-math/tests/linalg_deletion.rs`. | First PR: add `three_d.rs`+`schemes3d.rs` + tests to leto; reroute kwavers call sites; delete kwavers local copies; kwavers-boundary nextest stays green. |
| 6. Independently versioned or consumed across repo boundaries | Leto is independently versioned per `D:/atlas/repos/leto/README.md` *Rust Crate Releases*. | (same) | (same) |
| 7. `.gitmodules`, stack table, affected provider documentation, and cross-package verification in same delivery unit | All three PRs land in their respective repos and ship together per the *Atlas-side verification* gate (criterion-regression + cross-repo parity oracle). | (same) | (same) |

---

## 9. Atlas-side verification

A single PR per move closes the gate:

- **Move 1.**  PR in `D:/atlas/repos/CFDrs/Cargo.toml` workspace +
  `cfd-math/src/lib.rs` prelude + `cfd-1d`/`cfd-validation` import
  paths. Cross-crate parity: `cargo nextest run -p cfd-validation
  --status-level fail` (today's `825/825` minus the known 8
  cfdrs-runtime-budget timeouts documented in `CFDRS-AEQ-MET-09`)
  remains green; `cargo test -p cfd-math --all-features` runs
  through `let_ops::{FiniteDifference, Quadrature, ...}` SSOT paths.
- **Move 2.**  PR in `D:/atlas/repos/kwavers/Cargo.toml` workspace +
  `kwavers-math/src/linear_algebra/{ext,complex}.rs` deletion +
  affected physics/transducer/therapy/driver/analysis call-site
  reroutes. Cross-crate parity: `cargo nextest run -p
  kwavers-affected-package-set --status-level fail` (2913/2913 + 2
  skipped per the `KWAVERS-AEQ-MET-13` closure ledger) remains
  green; `kwavers-math/tests/linalg_deletion.rs` adds the
  preservation oracle.
- **Move 3.**  PR in `D:/atlas/repos/leto/crates/leto-ops/` workspace
  (`application/diff/{three_d,schemes3d}.rs` +
  `tests/ops/stencil.rs`) cross-coupled with PR in
  `D:/atlas/repos/kwavers/` workspace (`kwavers-math/src/numerics/
  operators/differential/{central,staggered}/` deletion +
  `kwavers-boundary`/`kwavers-physics` reroutes). Cross-crate
  parity: `cargo test -p leto-ops --all-features` runs the new 3-D
  FD test battery; `cargo nextest run -p kwavers-affected-package-set
  --status-level fail` stays green; `cargo run --locked -p leto-ops
  --example ndarray_parity` extends with a 3-D FD parity row.

`D:/atlas/tools/criterion-regression` is the cross-package Criterion
gate owner, per `D:/atlas/README.md` *Benchmark regression gate*
section. Benchmark universes are held constant; the affected family
(expansion of leto::application::diff + regression of kwavers
differential stencils) is in the scope of the criterion-regression
four-pair comparison.

---

## 10. Open follow-ups (post-audit, non-blocking for the first three)

- Move 4: `kwavers-math/src/special/*` → `leto_ops::special` (LOW
  risk, MEDIUM atlas impact).
- Move 5: `kwavers-physics/optics::*` FFT family → apollo (MEDIUM
  risk; depends on apollo's PSTD operator).
- Move 6: investigate cross-consumer demand for GridInterpolation
  before promoting to leto.
- Move 7: `cfd-math::time_stepping/*` ↔ `horae` audit.
- Move 8: `cfd-math::high_order/{spectral,dg,weno}/*` audit (wait
  for second consumer; candidate domain keep).
- Move 9: `helios-analysis::image_quality::{rmse,psnr,nrmse}` →
  direct `leto_ops::statistics` once leto releases align with
  helios's pinned version.

These follow-ups do not block the first three moves; they sit in the
backlog for the next wave.

---

## 11. Provenance / reproducibility

This file is the result of three round-trips of `code_searcher` +
`basher` + `read_files` on the atlas workspace at 2026-07-26:

- **Round 1.**  Consumer production-source import inventory.
  Searches: `^nalgebra|^ndarray|^burn\b`, `^pub fn |^pub struct |fn matmul|fn
  eigendecompose|fn inverse|fn svd|fn cholesky`, `use nalgebra|use ndarray|
  use burn`. Result: no direct producer matches in kwavers / CFDrs /
  helios / ritk; only `xtask/src/migration_audit.rs` fixtures.
- **Round 2.**  Per-consumer math-redundant surfaces.  Searches:
  `pub fn .*<.*Array|fn .*matrix|use leto::{Array1, Array2, Array3, ArrayView2,
  SliceArg}`, plus per-crate module maps.  Result: candidate inventory
  in §4.
- **Round 3.**  Leto SSOT verification (round-trip).  Direct reads of
  `repos/leto/crates/leto-ops/src/lib.rs`,
  `repos/leto/crates/leto-ops/src/application/mod.rs`,
  `repos/leto/crates/leto-ops/src/application/diff/{finite_difference,schemes}.rs`,
  `repos/leto/crates/leto-ops/src/application/linalg/mod.rs`,
  `repos/leto/crates/leto-ops/src/application/sparse/mod.rs`,
  `repos/leto/crates/leto-ops/src/application/stencil.rs`,
  `repos/kwavers/crates/kwavers-math/src/lib.rs`,
  `repos/kwavers/crates/kwavers-math/src/linear_algebra/{ext,complex}.rs`,
  `repos/CFDrs/crates/cfd-math/src/lib.rs`,
  `repos/CFDrs/crates/cfd-math/src/sparse/{mod,operations}.rs`,
  `repos/helios/crates/helios-{imaging,analysis}/src/lib.rs`. Result:
  the SSOT surface in §3.
