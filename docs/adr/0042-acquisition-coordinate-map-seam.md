# ADR 0042: Non-Cartesian acquisition geometry as an enum-dispatched coordinate map on `ritk_image::Image`

- Status: Accepted
- Date: 2026-08-13
- Class: `[arch]`
- Refs: atlas `backlog.md#atlas-us-capability-023` item US-023-A (the mandating
  item); `gap_audit.md#atlas-us-capability-023` (gap G2, and G4 whose ownership
  this ADR also settles); ADR 0041 (closed-set enum dispatch — the precedent
  this decision follows).

## Context

The ITKUltrasound capability audit recorded gap G2: we cannot represent an
ultrasound acquisition whose index→physical map is non-Cartesian. ITK models
curvilinear arrays, 3-D phased arrays and slice-series (wobbler) acquisitions
as *image types* — `CurvilinearArraySpecialCoordinatesImage`,
`PhasedArray3DSpecialCoordinatesImage`, `SliceSeriesSpecialCoordinatesImage` —
that override the virtual `TransformIndexToPhysicalPoint` /
`TransformPhysicalPointToIndex`. Because the map is a property of the image,
every existing ITK resampler, filter and registration method operates on beam
data unchanged, and scan conversion is just `ResampleImageFilter` onto a
Cartesian grid.

Our equivalent is a leaf function. `kwavers-analysis/.../b_mode/scan_conversion.rs`
converts sector and convex fans to a Cartesian raster by bilinear
interpolation, 2-D only, in one direction. Nothing else in the stack can
consume beam-space data, so any filter that should run *before* scan conversion
(QUS windowed spectra, speckle reduction, block matching) either cannot run in
acquisition coordinates or must re-implement the geometry locally.

The constraint is in `ritk-image`. `Image<T, B, const D: usize>`
(`crates/ritk-image/src/types.rs:16`) exposes `index_to_world_native` and
`world_to_index_native` (`types.rs:483,552`) as **inherent methods** computing
the affine origin/spacing/direction map. The map is not a seam: it is welded to
the concrete type, and `Image<T, B, D>` appears across ~39 ritk crates plus
kwavers, which depends on `ritk-image`, `ritk-spatial`, `ritk-core`,
`ritk-io` and `ritk-registration` (one-way; ritk has no kwavers dependency).

The candidate geometry set is closed and fixed by acquisition physics:
Cartesian, curvilinear/convex array, 3-D phased array, slice series. Each has a
closed-form inverse map (`atan2`/`asin` plus a radial term), which is what makes
`world_to_index` tractable without iteration.

## Options considered

1. **Generic map parameter** — `Image<T, B, D, M = Cartesian>` with
   `M: CoordinateMap<D>`. Truly open seam, no enum tag in codegen. Rejected:
   a fourth type parameter on the stack's most pervasive type propagates
   virally into every downstream signature and bound (the struct-level-bound
   contagion the standards warn about); a default type parameter does not save
   generic downstream code, which must still name or re-parameterize `M`.
   The blast radius is the whole of ritk plus kwavers for a seam whose
   implementor set is closed.

2. **Enum-dispatched coordinate map field** *(selected)* —
   `Image` carries `map: CoordinateMap<D>`, an exhaustively matched enum whose
   variants carry exactly their geometry parameters. No new type parameter, so
   existing `Image<T, B, D>` signatures are untouched and `CoordinateMap::Cartesian`
   preserves current behavior bit-for-bit.

3. **Separate `AcquisitionImage` type with explicit conversion** — leaves
   `Image` untouched; generalizes scan conversion to all three geometries but
   keeps it a conversion step. Rejected: it forfeits the property that motivates
   the change — that existing filters and resamplers work in beam space
   unchanged — and guarantees a second geometry implementation the moment any
   filter needs beam coordinates.

4. **Status quo (leaf functions)** — rejected; it is the gap.

## Decision

Adopt option 2. `ritk-image` owns a `CoordinateMap<const D: usize>` enum with
variants `Cartesian`, `CurvilinearArray`, `PhasedArray3D` and `SliceSeries`,
each carrying its own parameters (lateral/elevational angular extent and
spacing, radius, per-slice transforms) so an invalid parameter combination is
unrepresentable. `Image` gains the field; `index_to_world_native` and
`world_to_index_native` dispatch on it.

This follows ADR 0041's standing precedent: a closed design-time implementor
set dispatches by exhaustive enum, not by `dyn`. Dispatch resolves **once at
the operation boundary** — a resampler matches the arm, then runs a monomorphic
per-voxel loop — per the dispatch-at-kernel-granularity rule; a per-voxel match
inside the loop would be the defect this ADR must not introduce, and is the
first thing to check in review.

Consequences of adoption:

- Scan conversion becomes `resample(beam_image → cartesian_grid)` and the
  standalone `kwavers-analysis/.../b_mode/scan_conversion.rs` converter is
  deleted, its callers migrated in the same change (no compatibility shim,
  no second geometry implementation). Inverse scan conversion falls out for
  free as the opposite resample direction.
- Every ritk filter and registration method becomes usable in acquisition
  coordinates without modification, which is the precondition US-023-B (QUS
  windowed spectra) and US-023-D (block matching) both want.
- `Image` grows by one enum; the `Cartesian` variant is the default and carries
  no parameters, so existing serialized images and IO paths are unaffected.

## Ownership (settles US-023-A's second question)

- **G2 — coordinate maps and resampling: ritk.** It owns `Image`, the spatial
  transform stack and the interpolators. kwavers constructs the *acquisition
  parameters* from its transducer models and consumes the seam.
- **G4 — block-matching framework: ritk-registration.** The metric-image and
  displacement-calculator seams are registration machinery, and ritk already
  holds the NCC metric, B-spline FFD and displacement-field operations. kwavers'
  existing NCC + parabolic sub-sample kernel
  (`.../elastography/thermal_strain/tracking.rs`) consolidates onto it rather
  than being duplicated; kwavers retains the ultrasound-specific calculators
  and the elastography domain logic above the seam.

This keeps the dependency direction one-way and matches the existing bridge
(`kwavers-imaging/src/medical/ritk_bridge.rs`).

## Verification plan

- Value-semantic parity: for `Cartesian`, `index_to_world_native` and
  `world_to_index_native` are float-exact against the current implementation
  across the existing `ritk-image` transform tests.
- Round-trip: for every non-Cartesian variant, `world_to_index(index_to_world(i)) == i`
  within a tolerance derived from the geometry's condition number, over the
  acquisition's valid domain (and rejecting points outside the fan).
- Differential: resampling a synthetic curvilinear phantom through the new
  seam reproduces the current `ScanConverter` output within bilinear
  interpolation error, before that converter is deleted.
- Codegen: confirm the per-voxel loop of a resampler contains no enum
  discriminant test (dispatch hoisted to the operation boundary).
- Reference cases: `PhasedArray3D` and `SliceSeries` maps validated against
  ITKUltrasound's published test geometry parameters.

## Open questions

- Whether `SliceSeries` stores per-slice transforms inline or references a
  transform list — bounded by how large a realistic wobbler sweep is; decide
  during implementation from the memory budget, not speculatively.
- Whether non-Cartesian variants must reject `Direction` cosines other than
  identity, or compose with them. Composition is more general; identity-only is
  what ITK effectively assumes. Recommend composing, and asserting the
  identity case in tests.
