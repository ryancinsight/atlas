# ADR 0065: Overflow-safe rational derivative products

- Status: Accepted
- Date: 2026-09-23
- Item: [ATLAS-GAIA-NURBS-SCALE-001](../../backlog.md#atlas-gaia-nurbs-scale-001)
- Provider contract: [Eunomia ADR 0006](https://github.com/ryancinsight/eunomia/blob/main/docs/adr/0006-binary-float-scaling.md)

## Context

Rational curve and surface derivatives contain finite product ratios whose intermediate weight normalization can overflow. For f32/f64, let `m` be the smallest positive subnormal and `M` the largest finite value. A degree-one clamped curve with coordinates `[0, m]`, weights `[m, M]`, and `t = 0` has an exact endpoint derivative `M`. Computing `M / m` before multiplying by the coordinate difference `m` produces infinity instead. The surface partials have the same failure mode.

Eunomia PR #104 adds sealed `FloatElement` operations for binary exponent extraction and power-of-two scaling. f32/f64 retain native precision; reduced formats retain their existing f32 conversion semantics. The provider is the representation boundary, while Gaia owns the geometry formula.

## Decision

For finite, nonzero factors, Gaia evaluates each derivative term as one generic
product ratio. It extracts each factor's significand and binary exponent,
multiplies the four bounded numerator significands, divides by the two bounded
denominator significands, accumulates exponents separately, and applies one
final binary scale. The coordinate difference participates in the same ratio
as the derivative basis, weight, and homogeneous denominator; it is never
multiplied after a potentially overflowing intermediate coefficient.

The same operation serves curve tangents and both surface partials. Zero or non-finite factors follow the existing IEEE operation path because they have no finite binary exponent. Results outside the scalar format remain overflow or underflow. The method does not provide cancellation-safe summation or prevent overflow while forming a coordinate difference.

## Alternatives rejected

- Normalize only `weight / active_weight_scale`: the ratio itself can exceed the format before later factors reduce it.
- Convert all factors to f64: this changes f32 evaluation and cannot protect f64 from its own intermediate range.
- Implement scaling separately in Gaia: this duplicates representation rules owned by sealed `FloatElement`.

## Consequences

Tests cover the f32/f64 endpoint counterexample for curves and both surface partials, including subnormal and maximum-finite weights. Ordinary surface derivative cases compare against an independent per-operation IEEE oracle (`0x3f75c28f` and `0xbda3d70c`), replacing assertions one ULP above that reference. The implementation remains generic over the scalar contract and uses one shared ratio routine.

Overturning evidence: any supported finite product ratio with representable exact output still overflows an intermediate, or the independent IEEE cases diverge beyond their derived rounding behavior.
