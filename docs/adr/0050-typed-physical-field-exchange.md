# ADR 0050: Typed physical-field exchange at the Harmonia boundary

- Status: Accepted
- Date: 2026-08-21
- Class: `[major] [arch]`
- Refs: `backlog.md#atlas-harmonia-field-exchange-050-2026-08-21` (the mandating item)

## Context

Harmonia's existing partition and transfer contracts exchange raw scalar
slices. They validate runtime lengths and coupling dimensions, but those
contracts do not identify the physical quantity represented by a value or the
grid frame in which it is sampled. A CFDrs, Kwavers, or Helios adapter could
therefore connect fields with different SI dimensions or incompatible spatial
metadata while satisfying the existing slice contract.

The stack already has two relevant owners. Aequitas owns the compile-time SI
quantity vocabulary, including `Intensity` and `VolumetricPowerDensity`.
Harmonia owns coupling orchestration and is the deepest common consumer of the
future multiphysics exchange. The first increment must establish the boundary
contract without moving solver algorithms or inventing conversions.

## Decision

Harmonia adds `GridGeometry<T, RANK>` and
`FieldEnvelope<'a, T, D, RANK>`.

`GridGeometry` validates nonzero extents, checked cell-count multiplication,
positive finite SI spacing, finite origin coordinates, finite direction
cosines, and an orthonormal direction matrix. Its orientation threshold is
`16 · RANK · ε_T`; the factor covers the input and fused-multiply-add rounding
sites in the construction-time dot-product check. Geometry compatibility is
then exact because shape, frame metadata, and time identify the sampling
contract rather than a numerical result.

`FieldEnvelope` stores a borrowed `&[aequitas::Quantity<T, D>]`, the validated
geometry, and a finite `horae::Instant<T>`. Construction checks the exact
value count and performs no allocation or value copy. The dimension parameter
is part of the public type, so a function accepting an intensity envelope
cannot receive a volumetric-power-density envelope. Harmonia does not convert
units, interpolate nonmatching meshes, or add solver source terms in this
increment.

The later adapter path is dependency ordered: CFDrs, Kwavers, and Helios each
adapt their authoritative domain fields to this envelope; a separate item then
connects the typed source term and supplies a manufactured conservation case.
The providers remain owners of their solver state and numerical algorithms.

## Alternatives considered

1. **Keep raw scalar slices and add caller conventions.** Rejected: conventions
   are not enforced at the type or validation boundary and cannot prevent an
   intensity/power-density interchange.
2. **Add a parallel unit or field vocabulary to Harmonia.** Rejected: it would
   fork Aequitas's quantity-law single source of truth and create conversion
   drift.
3. **Add unit conversion or mesh interpolation in this increment.** Rejected:
   no current adapter contract selects conversion policy, interpolation order,
   conservation law, or error bound. Those are downstream domain decisions.
4. **Copy values into an owned exchange buffer.** Rejected: the current
   boundary only needs validated borrowing, and copying would add allocation
   and synchronization cost without supplying a contract benefit.

## Verification

- Harmonia's `cargo nextest` suite covers valid borrowed envelopes, value-count
  and geometry boundary partitions, non-finite inputs, checked shape overflow,
  exact frame/time compatibility, and generated positive shape products.
- The `FieldEnvelope` rustdoc compile-fail example verifies that Aequitas
  quantity dimensions are not interchangeable.
- `cargo test --doc` runs the existing coupling example and the compile-fail
  dimension example.
- `cargo clippy --all-targets --all-features -- -D warnings` and
  `cargo doc --no-deps` are required clean-lane gates.

## Consequences

Future multiphysics adapters have one typed, zero-copy boundary for physical
field metadata. Existing scalar partition mechanics remain unchanged, so the
consumer integration still requires explicit adapter and numerical-source
items. The exact metadata comparison intentionally rejects semantically
different frames; callers must perform a domain-owned resampling or conversion
before constructing the exchange envelope.
