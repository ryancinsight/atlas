# ADR 0047: `SliceSeries` carries an owned per-slice rigid transform list

- Status: Accepted
- Date: 2026-08-18
- Class: `[arch]`
- Refs: atlas `backlog.md#atlas-us-capability-023` item US-023-A4 (the mandating
  item); ADR 0042, whose two open questions this resolves.

## Context

ADR 0042 introduced `CoordinateMap` with `Cartesian`, `CurvilinearArray` and
`PhasedArray3D` shipped, and left `SliceSeries` for later with an explicit open
question: whether per-slice transforms are stored inline or referenced.

`SliceSeries` models a wobbler or freehand sweep: a stack of 2-D acquisitions,
each placed in 3-D by its own transform. It differs in kind from the two shipped
variants, which is why it was deferred. From
`itkSliceSeriesSpecialCoordinatesImage.h`:

- The map composes a **2-D slice image's own** index→physical map with a
  **per-slice 3-D transform**, looked up by `GetSliceTransform(sliceIndex)`.
- For a continuous index it fetches the transforms at `floor` and `ceil` of the
  slice coordinate and interpolates between the two resulting points.
- Out-of-range slice indices clamp to the first or last transform, with the
  residual carried on the slice axis.

So unlike the other variants there is no closed form: the map is a *table
lookup plus interpolation*, and its size is proportional to the sweep.

## Options considered

1. **Owned inline list, `Vec<RigidTransform>`** *(selected)*. The map owns one
   transform per slice.

2. **Reference into an external transform store** (`Arc<[…]>`, or an index into
   a registry). Rejected: it makes `CoordinateMap` no longer `Copy` in spirit
   even if mechanically possible, introduces a lifetime or shared-ownership
   question into a type that currently answers geometry questions with pure
   arithmetic, and buys sharing that no consumer has asked for.

3. **Parametric sweep** (fixed angular or translational increment). Rejected as
   the *primary* representation: it describes an idealized wobbler and cannot
   represent freehand or tracked acquisitions, which are the case that makes
   this variant worth having at all. It remains available later as a constructor
   that expands into the list.

## Decision — storage

Adopt option 1. The memory budget settles it rather than taste: a realistic
sweep is hundreds of slices, and a rigid transform is a rotation plus a
translation. At 256 slices that is on the order of a few tens of kilobytes —
negligible beside the image the map describes, which at 256 slices of even
256×256 `f32` is 64 MB. Optimizing the transform list against that is
optimizing the wrong term by three orders of magnitude.

Consequence: `CoordinateMap` stops being `Copy`. Every existing use is by
reference or clone-on-attach, so this is a mechanical change, but it *is* a
breaking change to the enum's traits and must land as one.

## Decision — ADR 0042's second open question

ADR 0042 also asked whether non-Cartesian variants compose with a non-identity
`Direction`, and recommended composing. That recommendation is **adopted and
now settled**: the acquisition map produces a point in the probe's own frame,
and `origin`/`Direction` then place that frame in world space. This is what
makes a tracked sweep expressible — the tracker's pose is exactly that outer
placement — and it is why composing rather than assuming identity was the right
default. Tests assert the identity case reduces to the current behaviour.

## Decision — out-of-range slices

ITK clamps to the end transforms and carries the residual on the slice axis.
That is adopted for the *forward* map, matching ITK so shared data agrees.

The **inverse** map rejects a point whose nearest slice lies outside the sweep,
rather than clamping. This follows the convention already set by the shipped
variants, which reject points outside the fan instead of aliasing them onto a
real beam: a point beyond the last slice was not acquired, and returning the
last slice's index would present un-acquired geometry as measured data.

## Verification plan

- Round-trip within a tolerance derived from the interpolation: for a slice
  index that lands exactly on a slice, `world_to_index(index_to_world(i)) == i`
  to the same bound the other variants use; between slices, the bound widens by
  the transform-interpolation error, which must be stated rather than assumed.
- Degenerate sweep: a series whose per-slice transforms are pure translations
  along one axis must reproduce the Cartesian map exactly, which pins the
  composition order.
- Identity `Direction` reduces to the probe frame, per the composition decision.
- Out-of-range: forward clamps as ITK does; inverse rejects.
- A single-slice series is a valid degenerate case and must behave as the 2-D
  slice map alone.

## Open questions

None. Both of ADR 0042's open questions are resolved here.
