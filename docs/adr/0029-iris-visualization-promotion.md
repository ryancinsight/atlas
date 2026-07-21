# ADR 0029: Promote Iris visualization contracts

- Status: Accepted
- Date: 2026-07-21
- Class: `[arch]` `[minor]`

## Context

The source audit found three independent named-color implementations:
`ritk-snap` defined eight display maps, `ritk-vtk` defined five presets and a
second interpolation engine, and Kwavers Analysis owns another volume-renderer
lookup table. RITK, Kwavers, and CFDrs also assemble scientific presentation
views from domain result storage.

Normalized scalar-to-color laws and borrowed result views belong neither to
medical imaging, acoustic propagation, fluid dynamics, array storage, GPU
mechanics, nor persistence. No current Atlas provider owned this bounded
context. The duplicated RITK implementations already crossed two packages,
satisfying the promotion gate without moving a speculative API.

## Decision

Promote public package `iris` as the Atlas owner for domain-neutral scientific
visualization contracts. Its initial crate provides:

- a validated `Normalized` newtype and normalized `Rgba` model;
- zero-sized static color-map strategies plus exhaustive `NamedColorMap` enum
  dispatch for runtime selection;
- `LookupTable<M, const N: usize>` with fixed inline storage;
- zero-copy `SeriesView` and const-rank `ScalarFieldView` contracts;
- `Cow<'_, str>` axis metadata; and
- a GAT `RenderBackend` seam that lends backend-owned frame storage.

Iris uses static dispatch and const generics where the dimension is structural.
It contains no array, solver, image, mesh, GPU, UI, or format dependency.

### Dependency direction

```text
domain result storage ──borrow──> iris views

ritk-snap ──> iris color laws
ritk-vtk  ──> iris color laws

consumer renderer ──implements──> iris RenderBackend
```

RITK retains medical windowing, session/UI state, VTK data models and
serialization, and GPU resource mechanics. RITK ADR 0011 removes the public
`Colormap` and `ColormapPreset` contracts and migrates every in-tree caller to
Iris `NamedColorMap`; no compatibility layer remains. The Kwavers and CFDrs
view migrations remain later vertical increments after their separate source
and contract audits.

## Theorems and proof obligations

For adjacent control channels `a,b in [0,1]` and interpolation coordinate
`u in [0,1]`, the linear channel value is `(1-u)a + ub`. Both coefficients are
non-negative and sum to one, so the result lies in the convex hull of `a` and
`b`, hence in `[0,1]`. Induction over every piecewise interval proves the
normalized RGBA invariant for table maps; analytic maps clamp each channel to
the same interval.

Every `u8` integer is exactly representable in `f32`; division by the exactly
representable positive value `255` is finite and in `[0,1]`. Therefore
`Normalized::from_u8` needs no fallible runtime validation branch. Exhaustive
enumeration of all 256 inputs checks strict monotonicity and endpoint identity.

`SeriesView` validates equal cardinality once. `ScalarFieldView` checks extent
multiplication for overflow and compares the product with storage length.
These construction proofs make every subsequently lent element an existing
borrow from caller-owned storage; view construction performs no allocation or
copy.

The analytical arguments establish the contracts. Executable property,
differential, layout, and borrow-identity tests establish implementation
evidence; neither category substitutes for the other.

## Migration

1. Publish Iris with its first complete color, view, and render-contract slice.
2. Add the consumer-required branch-free 8-bit coordinate conversion upstream.
3. Replace both RITK color engines and every in-scope caller with direct Iris
   APIs; delete the superseded module, enum, and interpolation functions.
4. Register the fetched public Iris default and merged RITK consumer revision
   as exact Atlas gitlinks.
5. Audit and migrate the Kwavers lookup table and CFDrs/Kwavers result-view
   assembly as separate complete consumer increments.

## Evidence

Iris implementation revision `e2edd47615454111b4b0df2e68dc6076161ba457` is publicly
readable without credentials. Format, all-feature and no-default-feature
checks, warning-denied all-target Clippy, 14/14 Nextest cases, two doctests,
warning-clean Rustdoc, example execution, cargo-deny, and package verification
pass. Tests cover all maps over 1,025 points, exact endpoints and control
points, every 8-bit coordinate, lookup/direct equivalence, ZST/table layout,
borrow identity, cardinality failures, and the lending render seam.

RITK PR 46 merged as `1bc665d4c2d56c97e1b2b51e7135e9a86bf14d08`
from exact head `33855845ec27d361056a8fd62c8ae81275fbc6a8`. CI run
`29831435735`, Python CI run `29831435956`, and migration-audit run
`29831435835` pass. The change deletes 250 lines of local Snap interpolation
and the VTK interpolation family. Local package formatting, warning-denied
all-target Clippy, 943/943 focused Nextest tests, doctests, and warning-clean
Rustdoc pass. VTK compares all 256 nodes of all ten named maps bit-for-bit
against direct Iris sampling. Snap tests display boundary vectors and
deterministic non-finite window endpoints. `cargo-semver-checks` reports only
the intentional major removals documented by RITK ADR 0011.

The closure revisions preserve those implementations while synchronizing
public evidence: Iris PR 2 merged as
`a8ea96f7e74b3c2ed0f8cbe32e97094f8418393b` with verify and supply-chain jobs
green; RITK PR 47 merged as
`a36e65dfe1d4401d6950ebc31123205b9db04c50` from exact head `a41774fa` after CI
`29833657517`, Python CI `29833657538`, and migration audit `29833657634`
passed. Atlas pins these two anonymous public defaults as commit gitlinks.

## Rejected alternatives

- Keeping color laws in RITK leaves simulation consumers dependent on a
  medical-imaging owner and retains cross-package duplication.
- An RITK wrapper enum preserves a second vocabulary and conversion table.
- Moving arrays, images, meshes, formats, UI state, shaders, or domain
  diagnostics into Iris crosses existing provider boundaries.
- Dynamic renderer or color-map trait objects add vtables where closed enum or
  compile-time strategy selection is sufficient.
- Creating plotting or GPU implementations before a consumer contract exists
  would be speculative scaffolding.

## Consequences

Atlas gains a small public visualization-law provider with one-way consumer
dependencies. RITK has one normalized color authority and fixed VTK table
storage. Additional plotting, diagnostic, and renderer capabilities enter Iris
only when a complete consumer slice demonstrates the shared contract.
