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
(working-tree heads, ahead of the recorded gitlinks): coeus mid-transition
(see below), leto with a local version-bump, eunomia `a20e075`. Coeus HEAD
is itself mid-transition — `fix(coeus-core): Scalar: leto_ops::Scalar
supertrait` — so finding F1 below describes a rebase in progress, not a
steady state.

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
   in-progress `Scalar: leto_ops::Scalar` rebase.
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
- FINDING (eunomia-side, FIXED 2026-10-06, pushed on branch
  `fix/complex-sqrt-principal`):
  `NumericElement::sqrt for Complex<T>` computed its rectangular form over
  `|z|^2` where the principal root needs `|z|`; now over `|z|`, matching
  the inherent polar oracle. Regression: `tests/complex_provider_contract.rs`.
- 2026-10-06, S3b core landed on coeus branch `fix/coeus-einsum-panic`
  (pushed, pre-push gate passed; 125 files, +461/−586, BREAKING): `Scalar::{zero, one, to_f64, sqrt_val, abs_val}`,
  `Int::{count_ones, abs}`, `Float::{abs, is_nan, is_finite}` deleted;
  ~600 call sites migrated to `eunomia::NumericElement` SSOT paths
  (convention: `use eunomia::NumericElement` in-core,
  `coeus_core::NumericElement` facade elsewhere — the same item). No
  delegation shims: direct SSOT correction per the consumer-collapse
  decision. Verified: workspace check green, clippy zero lints (one
  pre-existing `coeus-fft` warning), fmt clean, nextest 1466 passed / 1
  pre-existing environmental failure (reproduced pristine) / 8 skipped,
  doctests 163/163.
- 2026-10-06, verification #1 measured GREEN post-S3b: the
  `eunomia::NumericElement` / `leto_ops::Scalar` / `coeus_core::Scalar`
  `fn` name sets pairwise-intersect at zero. `coeus_core::Scalar` keeps
  exactly `{has_zero_bit_pattern, from_f64, total_add, total_mul,
  scale_slice}` — all provider-unowned.
- FINDING (eunomia-side, FIXED 2026-10-06, pushed on the eunomia branch):
  `FloatElement::powi`'s exp-by-squaring default negated the exponent
  (`n = -n`), which panics on `i32::MIN` in debug and wraps to `MIN`
  (silently returning `ONE`) in release; only generic `T: FloatElement`
  code observes it (inherent `powi` shadows for direct calls). Fixed via
  `n.unsigned_abs()` (`u32` holds 2^31 exactly); behavior identical for
  all other exponents. Regression: exact MIN/MAX assertions in the
  `float_element.rs` contract (all four types; observed the authentic
  4-way overflow panic pre-fix). Unblocks S3b-Float deletion of coeus
  `Float::powi`.
- 2026-10-06, S3b-Float remainder scoped (NOT deleted; coeus tree under
  live peer edit): `Float` keeps 21 same-name transcendental
  redeclarations over `FloatElement` + `NAN`/`INFINITY` (S1-ruled for
  deletion) + the `sqrt` ambiguity against `NumericElement::sqrt`
  (forces `<T as Float>::sqrt` qualification at generic sites — observed
  in the live peer migration); `FloatOps` keeps 24 `_op` methods; the
  60+-variant `CpuUnaryOp` stays as the dispatch tag. Deletion entry
  criteria: (a) a libm-crate-vs-system-libm differential gate — eunomia
  routes f32 transcendentals via the `libm` crate while coeus natives
  route via std inherent, so deletion can move results ~1 ulp;
  (b) the `round` routing rule — `Float::round` is ties-away (std) while
  the `CpuUnaryOp::Round` arm is ties-even (torch/`roundTiesToEven`,
  routed via `f64::round_ties_even`); eunomia provides both
  (`round`/`round_ties_even`), so each consumer maps to the right one;
  (c) `powi(i32::MIN)` fixed provider-side (done). Non-finding:
  `RealField`/`ComplexField` are a legitimate nalgebra-compat algebra
  seam (blanket impls, identities via `NumericElement`) — no action.
- 2026-10-06, S2 audited: exactly one direct `hermes_simd` call remains
  in coeus non-test code — the `scale_slice` native override
  (`native.rs:27`, `hermes_simd::scale`); all other slice kernels route
  via leto's `SimdStrategy`/`SimdOperations`. `SimdOperations` has no
  `scale`, so completion is provider adoption first (leto adds `scale`
  to `SimdOperations`/`Scalar`), then coeus deletes its override and
  declaration (which becomes a redeclaration). Pending cold-tree
  micro-slice: drop the redundant `eunomia::FloatElement` from
  `coeus_core::Float`'s supertraits (`RealScalar` implies it).
- 2026-10-06, S4 audited (the "per-op delegation unverified" gap is now
  measured): 0/4 `coeus-ops/sparse` ops route via `coeus-leto`
  dispatch — `spmv`/`spmm`/`spmm_backward_values`/`spmm_backward_dense`
  are own-kernel `backend.parallel_for` loops with zero references to
  `coeus_leto`/`leto_ops`; the tested `spmv_into`/`spmm_into` dispatch
  has zero production callers. Wiring blockers: (a) the dispatch copies
  3 vecs per call (`CsrMatrix::from_parts` takes owned `Vec`s only) —
  leto needs a borrowed CSR view first or wiring regresses memory
  against today's zero-copy ptr loops; (b) the forward ops are
  `B: Backend`-generic, so S4 needs a CPU-vs-device branch design;
  the backward ops stay in coeus (autodiff-owned).
- 2026-10-06, S2 provider adoption landed on leto branch
  `fix/leto-scale-adoption` (pushed, gate passed; plus a fmt follow-up):
  `leto_ops::Scalar` gains the `scale_slice` default (lane-independent
  scalar loop, same body coeus carries), `SimdOperations` gains the
  strategy route over `hermes_simd::scale` for f32/f64/F16/Bf16, and the
  `impl_scalar_simd!` types take the strategy-first path with scalar
  fallback; ints/complex inherit the default via their plain impls. Test
  pins bitwise SIMD==scalar on all four float types (259 elements, past
  any scalar tail) plus the i32 default route, the taken-not-declined
  strategy route, and empty input. Verified: nextest 725/725, clippy
  zero lints, fmt clean. Consumer collapse (delete coeus's `scale_slice`
  declaration + native override + last direct `hermes_simd` call) waits
  for a cold coeus tree — peers are actively migrating adjacent call
  sites on the same branch.
- 2026-10-07, S3b-Float deletion gate landed on the coeus branch (45
  tests, 42 live): every same-name transcendental pinned at its measured
  envelope (exact ops bitwise 0, the rest 0–1 ulp over edges + sweeps).
  The gate forced one provider fix first: eunomia's `powi` inverted
  first (`(1/x)^|n|`, up to 8 ulp off std) and flushed subnormals; it
  now inverts last with a cold-path downward recomputation on overflow
  (pushed on the eunomia branch with MIN + gradual-underflow
  regressions). Staging note: member CI resolves providers from git
  mains, so the three `powi` differential tests ship `#[ignore]`d until
  the eunomia fix lands on its main — they compile, pass explicitly,
  and activate by deleting three attributes. The gate also recorded one
  accepted behavior change: negative f32 bases at extreme odd exponents
  flip from std's sign-dropped infinities/zeros to eunomia's C/libm
  signs on deletion. Citations in this file name pushed branches, never
  unmerged hashes, per the board lint's `unresolved_references` rule.
- 2026-10-06, S5 consumer audit complete (verification #6 satisfied):
  every non-coeus dependent of `leto-ops` was searched (direct,
  braced-import, and `application::` path forms; apollo/ares/athena/ritk
  zero; `coeus-push` verified a coeus mirror and excluded). `loss` /
  cross-entropy → hephaestus-host CPU reference + hephaestus-conformance
  oracle: STAY. `attention` → hephaestus-host seam + hephaestus-wgpu
  test oracle: STAY. `optimization` / LBFGS → kwavers production FWI
  and elastography inversions (+ `kwavers-math` re-export): STAY.
  `nonlinear` / Anderson → CFDrs re-export only, zero fleet callers;
  the CFDrs "helios" doc claim is stale (zero `Anderson` refs in
  helios; zero direct refs in kwavers): STAY-wach (generic numerical
  math, not ML-specific — flag the uncalled status, correct the doc
  claim). `loss` / ctc → coeus-only (coeus maps `CtcError` from leto
  kernels): MOVE candidate to coeus. `stateful_update` (Adam/SGD/…)
  → zero callers anywhere including coeus (coeus-optim owns its own):
  MOVE-or-DELETE candidate — the leto README already assigns
  optimizers to coeus. Next: per-module move-or-redefine executions
  plus README boundary corrections for the stayers.

## Verification

1. `coeus_core::Scalar` declares no method also declared on
   `leto_ops::Scalar` or `eunomia::NumericElement` (mechanical check:
   intersect the three `fn` name sets; expect empty). S3b status 2026-10-06:
   GREEN — pairwise intersection is empty (see implementation log).
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
