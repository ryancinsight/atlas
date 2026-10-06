# ADR 0069: Eunomia–Leto–Coeus vertical redundancy audit and consolidation sequence

- Status: Proposed
- Date: 2026-10-06
- Class: `[arch]`
- Relates to: [ADR 0005](0005-eunomia-scalar-ssot.md),
  [ADR 0022](0022-horae-athena-provider-extraction.md),
  [ADR 0033](0033-krylov-ownership-reaffirmation.md),
  [ADR 0038](0038-compute-backend-conformance-crate.md),
  [ADR 0039](0039-compute-substrate-topology.md),
  [ADR 0062](0062-iterative-solver-and-preconditioner-ownership.md)

## Context

The stack README's provider table already states the correct vertical
ownership: eunomia owns datatype vocabulary, leto owns host arrays and CPU
linear algebra, coeus owns tensor semantics and differentiation. The manifests
agree: `coeus-core` depends on `leto-ops` and `eunomia`, and `leto` depends on
`eunomia`. The dependency direction is right; the code lags it.

This ADR records the audit of 2026-10-06 over the datatype → array → tensor
column and the sequence that removes the measured duplication. Audit basis
(working-tree heads, ahead of the recorded gitlinks): coeus `5f7a97c`,
leto `e4e61b9`, eunomia `a20e075`. Coeus HEAD is itself mid-transition —
`fix(coeus-core): Scalar: leto_ops::Scalar supertrait` — so finding F1 below
describes a rebase in progress, not a steady state.

### Finding F1: the Scalar stack redeclares instead of extending

Three Scalar-ish traits form one chain —
`eunomia::NumericElement` → `leto_ops::Scalar` → `coeus_core::Scalar` — as
[ADR 0005](0005-eunomia-scalar-ssot.md) requires. But the top link redeclares
what the lower links own:

- `coeus_core::Scalar`
  (`repos/coeus/crates/coeus-core/src/dtype/traits.rs`) requires
  `leto_ops::Scalar` as a supertrait yet redeclares 9 identical slice kernels
  (`add/sub/mul/div/sum/dot/axpy/min/max_slice`) with near-identical scalar
  defaults, plus `zero/one/to_f64/from_f64/sqrt_val/abs_val`, which duplicate
  `NumericElement::{ZERO, ONE, to_f64, sqrt, abs}` and
  `FloatElement::from_f64` under different names.
- The same 9 kernels therefore have **two SIMD dispatch paths**: coeus
  `f32`/`f64` overrides route directly to `hermes_simd`, leto routes through
  `SimdStrategy`.
- The trait's own documentation forbids this: "Backend `Scalar` traits must
  extend — not redeclare — `NumericElement`."

`leto_ops::Scalar` (`repos/leto/crates/leto-ops/src/domain/scalar/contract.rs`)
is the correct pattern: it extends `NumericElement` and adds only slice-level
CPU/SIMD hooks. F1 is coeus not yet following the pattern its own supertrait
already demonstrates.

### Finding F2: three float-transcendental surfaces

- `eunomia::FloatElement`: ~40 libm-backed methods
  (`exp`, `ln`, `sin`, `powf`, `erf`, `lgamma`, …).
- `coeus_core::Float`: redeclares ~25 of the same functions
  (`exp`, `ln`, `sin`, `powf`, `powi`, `is_nan`, `is_finite`, …) plus `NAN` /
  `INFINITY` consts that duplicate `NumericElement`'s.
- `coeus_core::FloatOps`: redeclares 24 more with an `_op` suffix
  (`exp_op`, `log_op`, `sin_op`, …).
- `CpuUnaryOp` adds a 60+-variant dispatch enum over the same function set.

`coeus_core::Float: Scalar + FloatOps + eunomia::FloatElement`, so every
implementor writes each function up to three times under three names. The
`_op`-suffixed layer and the duplicated `Float` methods are the redundancy;
the enum is a legitimate dispatch tag once it routes to a single
implementation. `coeus_core::Int` likewise duplicates `count_ones` and `abs`
from `NumericElement`.

### Finding F3: two array substrates (dynamic Layout + Storage + Tensor/Array)

- Layout: coeus `Layout`/`Shape`/`Strides` (SmallVec dynamic rank) beside
  leto `Layout<const N>` (const rank) and leto `LayoutDyn` (boxed-slice
  dynamic rank, per leto ADR 0007 a boundary carrier sharing the `kernels`
  arithmetic SSOT). Two dynamic-rank layouts with independent arithmetic.
- Storage: coeus `Storage`/`CpuStorage`/`CowStorage` (always Mnemosyne-backed,
  backend-generic via `try_as_slice`) beside leto
  `Storage`/`VecStorage`/`MnemosyneStorage`/`CowStorage`/`StackStorage`
  (host-only). The CPU path overlaps; the GPU path (`DeviceBuffer`,
  fallible device access) is coeus's legitimate extension.
- Array: `coeus_tensor::Tensor` (COW, views, slicing, broadcast, checkpoint)
  beside `leto::{Array, ArrayView}` with the same vocabulary. `coeus-core`
  `src/` totals 4,033 lines; the layout + storage + dtype modules are the
  overlap under discussion.

### Finding F4: sparse types in three vocabularies, kernels consolidated

- `leto` `infrastructure/sparse` (1,088 lines): `CooArray`/`CsrArray`/`CscArray`.
- `leto-ops` `application/sparse` (4,368 lines): `CooMatrix`/`CsrMatrix`/
  `CscMatrix` plus `spmv`/`spmm`/`spgemm`, numeric/symbolic LU, AMD ordering.
- `coeus-sparse` (255 lines): `CooTensor`/`CsrTensor`; conversions and kernels
  in `coeus-ops/sparse/` (526 lines) via `coeus-leto` dispatch.

CPU kernels route `leto-ops` ← `coeus-leto` ← `coeus-ops` (verified for
attention end to end; the sparse dispatch surface exists at
`coeus-leto/src/dispatch/sparse.rs` but per-op delegation is not yet verified
here). The fork is the **type vocabulary**, including an intra-leto split
between `leto` and `leto-ops` sparse types.

### Finding F5: ML kernels sit in leto-ops, validation repeats per layer

`leto-ops/src/application/` carries `loss` (+ `ctc`, 1,157 lines),
`attention` (1,018), `optimization`/`lbfgs` (532), `stateful_update` (464),
and `nonlinear`/`anderson` (731) — ~3,900 lines of ML/optimization concerns in
the array substrate, against the leto README's own boundary ("Coeus owns
autodiff graphs, NN orchestration, optimizers"). The math lives once (good:
`coeus-ops` CPU impls delegate through 36 `coeus_leto` sites in 15 files, and
the 4,446-line `backend_ops/cpu_impl` tree is delegation, not a second kernel
set). The cost is per-layer repetition: leto-ops validation →
`coeus-leto` dispatch → `coeus-ops` `BackendOps` trait → `coeus-ops`
free-function validation (e.g. `attention.rs::rank_three`/`validate_mask`
restating `leto-ops` `attention/validation.rs`) plus error-enum mapping at
each hop (`AttentionError` → `BackendError`).

### Non-findings (correct layering, no action)

- `coeus_core::Complex` re-exports `eunomia::Complex`; the coeus-side module
  adds only trait impls. The consolidation ADR 0039's era left open is done.
- `leto_ops::{Scalar, RealScalar}` extend eunomia traits without redeclaring
  element methods — the pattern F1 converges to.
- `coeus-ops` top-level modules route through `BackendOps`
  (`unary/kernel.rs`, `binary/kernel.rs` verified); `backend_ops/ops.rs`
  re-exports the `coeus-core` op enums. One dispatch surface, no intra-crate
  fork.
- `eunomia::layout` (byte-layout `Pod`/`Zeroable` markers) vs
  `coeus_core::layout` (array shape/strides) is a module-name collision over
  different concerns, not duplication. A rename is optional polish, not a
  consolidation slice.
- leto `geometry` (`Point`/`Vector`/`Quaternion`/`Isometry`, 1,644 lines) is
  small-vector vocabulary; gaia owns mesh generation. Different concerns.
- `coeus-fft` over `apollo-fft` remains wrappers plus differentiation per
  ADR 0039 (not remeasured; no action).

## Decision

Provider seam first, consumer collapse second — the ADR 0039 ordering. A
consumer must never invent an abstraction over a provider seam that is about
to be completed; each slice below lands provider-side before its consumer
deletes anything.

### S1. Eunomia completes the element surface (provider, first)

1. Confirm `FloatElement` covers everything `coeus_core::{Float, FloatOps}`
   needs. Known non-members: `gelu`/`sigmoid` are NN-activation compositions
   and stay in `coeus-ops` as compositions, not scalar-trait methods;
   `is_integer`/`fract`/`MAX`/`MIN_POSITIVE` need an own-or-extend ruling each.
2. Rule the integer bit surface: `NumericElement` already owns
   `count_ones`/`bitand`/`bitor`/`bitxor`; either promote
   `count_zeros`/`leading_zeros`/`trailing_zeros`/`rotate_*` to eunomia or keep
   `coeus_core::Int` as the thin extension. Either way `Int::{count_ones, abs}`
   is deleted as duplicated.
3. Non-goal: no new eunomia crate. Additions are trait methods with libm-backed
   defaults, following the existing `FloatElement` pattern.

### S2. Leto-ops becomes the single slice-kernel and SIMD-dispatch owner

1. `leto_ops::Scalar` stays the one slice-kernel trait; reconcile its
   `SimdStrategy` routing with coeus's direct `hermes_simd` calls into one
   documented path before S3 deletes the coeus side.
2. No element-surface change (already correct per the non-findings).

### S3. Coeus-core deletes its redeclared surface (consumer collapse)

1. Remove the 9 redeclared slice kernels from `coeus_core::Scalar` (inherit
   them from the `leto_ops::Scalar` supertrait) and remove
   `zero/one/to_f64/from_f64/sqrt_val/abs_val` in favor of the eunomia
   supertrait items; migrate call sites to the SSOT paths. This completes the
   rebase coeus `5f7a97c` started.
2. Collapse the `Float` / `FloatOps` / `CpuUnaryOp` triple per the S1 rulings:
   `Float` keeps only what eunomia provably lacks, `_op` methods delegate or
   are deleted, and `CpuUnaryOp` remains solely as the CPU dispatch tag routing
   to the single implementation.
3. Layout/Storage: coeus keeps the backend-generic traits (`Storage`,
   `try_as_slice`, `DeviceBuffer`) that GPU backends need, but `CpuStorage`
   becomes a thin wrapper over leto storage (or both build on a
   mnemosyne-owned aligned host buffer — the S3 design step decides), and
   runtime-rank layout arithmetic delegates to leto's shared `kernels`.
   Deletion ledger: the overlapping `coeus-core` layout/storage/dtype lines,
   counted against the 4,033-line S3 baseline.

### S4. Sparse converges on one type vocabulary

1. Intra-leto first: merge `leto` `infrastructure/sparse` types with
   `leto-ops` `application/sparse` types (one `Coo`/`Csr`/`Csc` set; kernels
   already live in `leto-ops`).
2. Then `coeus-sparse` becomes generic adapters over the leto vocabulary
   (mirroring how `CooTensor` composes `Tensor` today), with GPU sparse
   remaining behind the hephaestus/coeus bridges. Verify per-op
   `coeus-leto` sparse delegation before deleting any `coeus-ops/sparse`
   kernel.

### S5. ML placement is decided by a consumer audit, not by assertion

`loss`/`ctc`/`optim`/`stateful_update` read as coeus-owned (coeus can own
kernels over `leto-ops` primitives without inverting the dependency), while
`attention`/`matmul`/`conv` may be legitimate leto "array algorithms" if
non-ML consumers (CFDrs, kwavers) call them directly. S5 starts with that
consumer audit; the move-or-redefine decision per module follows the evidence.
If a module stays in leto-ops, the leto README boundary claim is corrected
instead of the code. Either outcome deletes the per-layer validation/error
restatement (F5): one validation site plus one error type per op across the
`leto-ops` → `coeus-leto` → `coeus-ops` chain.

## Consequences

- One scalar element surface (eunomia), one slice-kernel surface (leto-ops),
  one CPU dispatch tag set (coeus `CpuUnaryOp`), one sparse type vocabulary
  (leto), one validation site per op.
- Coeus implementors write each scalar function once; a new element type
  touches eunomia plus thin per-layer extensions instead of three full
  surfaces.
- No new repository and no new package. Every slice is inside an existing
  workspace; `.gitmodules` and the stack table are untouched.
- S3 and S5 are breaking changes for coeus consumers (ritk and below) and
  ship as versioned migrations with call-site rewrites, not silent deletions.

## Alternatives rejected

**Collapse the consumer first.** Deleting coeus's kernels before the provider
seam is complete forces coeus to invent its own abstraction — the exact
failure ADR 0039 sequenced against.

**Merge the three repositories.** Destroys the independent release histories
the datatype vocabulary was extracted to protect (eunomia README provenance:
stable vocabulary vs perf-volatile kernels) and would put GPU dependencies
under host-array consumers.

**Freeze the duplication and enforce by review.** ADR 0039 already ran this
experiment on the vendor dimension: the clones are individually plausible and
only a normalized cross-repo diff makes the overlap visible. The seam removes
the ability to reintroduce them.

**Move ML kernels down into eunomia.** Eunomia owns representations, not
algorithms; its README non-goals ("no computation kernels") already decline
this.

## Implementation log

- 2026-10-06, S3a landed in the coeus working tree (branch
  `fix/coeus-einsum-panic`, uncommitted): the 9 redeclared slice kernels are
  deleted from `coeus_core::Scalar` and its f32/f64 impls; resolution is via
  the `leto_ops::Scalar` supertrait. Net −178 lines across 9 files. Kept
  deliberately: `scale_slice` (no provider owns it),
  `zero/one/to_f64/from_f64/sqrt_val/abs_val` (S3b: 800+ call sites, needs
  the S1 int-semantics rulings first), `total_add/total_mul` and
  `has_zero_bit_pattern` (coeus-specific semantics). Behavior deltas accepted:
  leto length asserts now guard all CPU slice calls (fail-fast), empty
  `min/max_slice` returns the extreme value instead of panicking (provider
  contract; no call site exercises it), F16/Bf16 kernels move from scalar
  loops to hermes-SIMD. Tracking: `backlog/atlas-adr0069-stages.md`.
- 2026-10-06, S1 rulings (evidence in the coeus/eunomia working trees):
  `gelu_op`/`sigmoid_op` are NN-activation compositions over `FloatOps` and
  stay in `coeus-ops` as compositions (S3b moves the `CpuUnaryOp` eval arms,
  not the math). `Float::{MAX, MIN_POSITIVE, NEG_INFINITY, fract,
  is_integer, is_infinite}` stay: eunomia's `MAX_VALUE`/`MIN_VALUE` are
  infinities for floats (fold identities, not finite bounds), and it has no
  `MIN_POSITIVE`/`NEG_INFINITY`/`fract`/`is_integer`/`is_infinite`.
  `Float::{NAN, INFINITY}` and the ~20 transcendental redeclarations delete
  in S3b. `Scalar::from_f64` stays abstract (integers need it; eunomia's
  `TryFromCount` refuses rather than saturates — different contract).
  `Int` keeps `count_zeros`/`leading_zeros`/`trailing_zeros`/`rotate_*`/`pow`
  (no eunomia equivalent); `count_ones`/`abs` delegate. `AttentionScalar`
  (`coeus-leto`) is a legitimate dispatch-bound trait over `Float`, not a
  parallel scalar hierarchy — no action.
- 2026-10-06, S3a2 landed in the coeus working tree (same branch,
  uncommitted): `Scalar::{zero, one, to_f64, sqrt_val, abs_val}`,
  `Int::{count_ones, abs}`, and `Float::is_infinite` collapse to
  SSOT-delegating provided defaults; all per-type bodies deleted (~150
  lines). Zero call-site churn by design (API unchanged; full deletion is
  S3b). Int `sqrt_val` now takes the exact-`isqrt` route: the old f64
  round-trip is provably wrong at the u64 top edge (`u64::MAX`: old
  `2^32`, correct `2^32-1`; witness in `/tmp/isqrt_witness.rs`) and
  survives elsewhere only via double-rounding absorption (3M+ adversarial
  samples, zero other divergence). `Complex::sqrt_val` keeps its correct
  principal-root formula deliberately (see next bullet).
- FINDING (eunomia-side, not fixed here): `NumericElement::sqrt for
  Complex<T>` (`repos/eunomia/crates/eunomia/src/impls/primitives/
  numeric.rs`) computes its rectangular form over `|z|^2` where the
  principal root needs `|z|` (e.g. `sqrt(3+4i)` yields `u≈3.74` instead of
  `2`), while eunomia's own inherent `Complex::sqrt` (polar form,
  `types/complex/float.rs`) is correct. The inherent method shadows the
  trait method for direct calls, so only generic `T: NumericElement` code
  observes the defect. Owned by the eunomia repo: reconcile or delete the
  trait impl against the inherent oracle; coeus must not delegate
  `Complex::sqrt_val` until then.

## Verification

1. `coeus_core::Scalar` declares no method also declared on
   `leto_ops::Scalar` or `eunomia::NumericElement` (mechanical check:
   intersect the three `fn` name sets; expect empty). S3a status 2026-10-06:
   the 9 slice kernels intersect at zero; the 6 identity methods remain and
   are S3b.
2. Each transcendental function has exactly one implementation per type; the
   `Float`/`FloatOps`/`CpuUnaryOp` name sets no longer pairwise intersect on
   function identity.
3. `coeus-ops` CPU tests and `leto-ops` tests pass unchanged (differential
   oracle: kernel behavior is identical before/after each deletion slice).
4. Sparse: one `Coo`/`Csr`/`Csc` vocabulary in leto; `coeus-sparse` holds only
   adapters; every `coeus-ops/sparse` kernel routes through `coeus-leto`.
5. Each op in the `leto-ops` → `coeus-leto` → `coeus-ops` chain has one
   validation site and one error type; the attention chain is the pilot.
6. S5's consumer audit names every non-coeus caller of the ML-placed modules
   before any move-or-redefine decision.
