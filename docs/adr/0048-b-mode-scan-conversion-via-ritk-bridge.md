# ADR 0048: B-mode scan conversion is a resample through the ritk CoordinateMap seam

- Status: Accepted
- Date: 2026-08-19
- Class: `[arch]`
- Refs: ADR 0042 (the seam this decision resolves); ADR 0041 (closed-set
  dispatch precedent); US-023-A6 (the mandating backlog item); US-023-A3
  (kwavers ScanConverter delegates polar math to ritk-spatial).

## Context

ADR 0042 introduced `CoordinateMap` on `ritk_image::Image` so beam-space
acquisitions (curvilinear, 3-D phased array, wobbler sweep) can flow through
every resampler and filter unchanged — scan conversion then becomes an ordinary
resample onto a Cartesian grid rather than a bespoke step.

The kwavers `ScanConverter` predates ADR 0042. US-023-A3 already migrated its
polar arithmetic to the ritk-spatial geometry SSOT, but the converter itself
still lives in kwavers and still applies the polar inverse explicitly rather
than routing through the seam.

ADR 0042 stated as a consequence: "scan conversion becomes an ordinary resample
through the seam rather than a bespoke step." That consequence was deferred to
this ADR because it splits the B-mode pipeline across crates, which is a design
boundary worth an explicit record.

## Decision

**Move scan conversion behind the ritk-image resampler using
`CoordinateMap::CurvilinearArray`.** The kwavers B-mode pipeline will:

1. Load an RF acquisition as a `ritk_image::Image` with
   `CoordinateMap::CurvilinearArray` attached (US-023-E2 already handles the
   NRRD path; kwavers' in-memory path attaches the map directly).
2. Call the ritk-image resampler with a Cartesian target grid.
3. Use the result directly; no `ScanConverter` struct is invoked.

The bespoke kwavers `ScanConverter` is deleted. No second scan-conversion
implementation remains in the stack after this change.

## Options considered

1. **Resample through the seam (selected).** A beam-space `Image` already
   answers `index_to_world_native_on` through its `CurvilinearArray` arm. A
   Cartesian target grid calls `world_to_index_native_on` on the beam image to
   find the source index for each output voxel, then interpolates. Bilinear
   interpolation in beam space is equivalent to what `ScanConverter` does; any
   difference lands within rounding error of the interpolation scheme.

2. **Keep the bespoke converter.** Rejected because: (a) it duplicates the
   seam, (b) it cannot be composed with the registration, filter, or
   tractography pipelines the way an `Image` with an attached map can, and (c)
   ADR 0042's stated purpose was precisely to eliminate this class of converter.

3. **Bridge via a kwavers-owned adapter.** Rejected: an adapter over a seam is
   a re-implementation of the seam. The seam exists; use it.

## Acceptance oracle

The differential is: scan-converted output via the ritk resampler agrees with
the existing `ScanConverter` output to within bilinear interpolation error
(absolute pixel error ≤ 0.5 intensity unit on the benchmark B-mode dataset).
The `ScanConverter` and its tests are deleted; no test is migrated without
validation through the seam.

## Non-goals

- No change to the acquisition geometry parameterization — the
  `CurvilinearArray` geometry is already owned by ritk-spatial.
- No change to the beam-space RF processing pipeline; only the
  beam-to-raster conversion step changes.
- No new kwavers-ritk feature bridge crate; kwavers-physics already depends on
  `ritk-spatial` and ritk-image will be added to kwavers-imaging for the
  resampler.
- No support for non-convex or non-centred fan geometries beyond what
  `CurvilinearArray` already covers; edge cases that the old converter handled
  incorrectly are bugs to fix in the geometry, not reasons to preserve the
  converter.

## Consequences

- `kwavers-imaging` gains a `ritk-image` dependency (already anticipated in
  ADR 0042 and currently available through the Atlas workspace overlay).
- The kwavers B-mode test suite must include a differential oracle before the
  converter is deleted.
- US-023-A6 is closed by this ADR; implementation follows as a separate PR.
