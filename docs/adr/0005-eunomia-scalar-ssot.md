# ADR 0005: `eunomia::NumericElement` as the single scalar-vocabulary SSOT (CR-4)

- Status: Accepted
- Date: 2026-07-04; revised 2026-10-02.
- Index: docs/adr/README.md
- Revision 2026-10-02: count conversion moved from the member `Scalar`
  traits into eunomia (`FloatElement::from_count`/`from_integer`,
  `TryFromCount::try_from_count`; eunomia PR #143, Item
  EUNOMIA-COUNT-CONV-001), reversing the 2026-07-04 decision that kept
  `from_usize` on `leto_ops::Scalar` and refused it on `NumericElement`.
  Driver: the stack cast rule (bare `as` conversions) assigns every
  conversion std has no trait for to one module in the foundation crate.
  The record was compacted to the current decision; the 2026-07-04 text,
  its delivery sequencing and its closure claims are in git history.

> Cite this document as `atlas:0005`; `eunomia:0005` is the unrelated
> `min_scalar`/`max_scalar` special-value contract in
> `repos/eunomia/docs/adr/`.

## Context

Three member traits redeclared element vocabulary that eunomia owns:
`coeus_core::Scalar` (`zero`, `one`, `to_f64`, `from_f64`, `from_usize`,
`sqrt_val`, `abs_val`), `leto_ops::Scalar` (`from_usize`) and `gaia::Scalar`
(`from_f64`, plus `from_usize`/`from_index` defaults routed `usize -> f64 ->
Self`). Each `from_usize` was a bare `as` cast (gaia's `f32` arm a
widen-then-narrow double rounding), with three different contracts.

`NumericElement` is implemented for the full integer and float lattice, so a
`Scalar: RealField` binding would orphan coeus's integer `Int` subtrait. The
member traits also carry legitimate backend surface: coeus and leto slice
kernels (`add_slice` .. `max_slice`, `axpy_rows`, `gemv_*`, `tiled_gemm`),
`CpuUnaryDispatch`, `Pod`; gaia's `tolerance()` and `total_cmp`.

## Decision

1. Member `Scalar` traits take `eunomia::NumericElement` as supertrait and
   declare only backend-specific surface. Vocabulary `NumericElement`,
   `FloatElement` or `ComplexField` provides is deleted from them, with every
   call site migrated in the same change.
2. Eunomia is the single home for integer-to-element conversion:
   - `FloatElement::from_count(usize)` and `from_integer(i64)`: round to
     nearest, ties to even; exact below `2^p` (53 `f64`, 24 `f32`, 11 `F16`,
     8 `Bf16`). Narrower formats round the integer to odd at 24 bits,
     exact in `f32`, then narrow: one rounding. A round-to-nearest `f32`
     intermediate double-rounds (`2^25 + 2^17 + 1` into `Bf16`).
   - `TryFromCount::try_from_count(usize)`, a `NumericElement` supertrait:
     exact or `CountRangeError` for integer elements, infallible for floats,
     real embedding for `Complex<T>`. Generic code that may run at an integer
     element uses it; float-bound code uses `from_count`.
   - `const fn` forms: `F32::from_count`/`from_integer`,
     `F64::from_count`/`from_integer`.
   The casts live in `eunomia/crates/eunomia/src/convert/count.rs` under one
   module-scoped `#[expect]`.
3. No member defines its own count conversion (`from_usize`, `from_index`, a
   local scalar trait method or free function wrapping `as`).
4. Validating index newtypes (gaia `VertexId::from_usize` and kin) are
   constructors, not scalar conversions, and are outside this decision.

## Rejected alternatives

- `Scalar: NumericElement + RealField`: float-only, orphans integer impls.
- Empty `Scalar` (no methods): deletes live slice-kernel dispatch surface.
- Keeping the redeclared vocabulary beside the supertrait, as required or
  defaulted forwarding methods: two homes for one vocabulary.
- Slice kernels on `NumericElement`: they are backend dispatch, not element
  vocabulary.
- `from_usize` per member trait (the 2026-07-04 decision): three contracts
  for one conversion and a bare `as` in each member.
- An infallible `NumericElement::from_count`: an integer element has no
  honest result for a count outside its range; the checked form makes the
  failure a typed error.
- Generic `CastFrom`/`CastTo` (`as` semantics between any pair): carries no
  per-conversion contract; its retirement is EUNOMIA-CASTFROM-RETIRE
  (`repos/eunomia/backlog.md#eunomia-castfrom-retire`).

## Consequences

- Float-bound kernels write `T::from_count(n)`; integer-capable kernels
  propagate `CountRangeError`.
- Above `2^p` a count rounds; callers whose correctness needs exactness state
  the bound at the call site.
- Open remainder: `coeus_core::Scalar` still declares `zero`, `one`, `to_f64`,
  `from_f64` at coeus `70e39493` (COEUS-SCALAR-VOCAB,
  `repos/coeus/backlog.md#coeus-scalar-vocab`). The push gate for bare
  casts is not yet built (gap_audit.md, 2026-10-02).

## Overturning evidence

A consumer needing a count conversion whose contract is neither
round-to-nearest (floats) nor exact-or-refused (integers).
