# ADR 0046: Decline the HDF5 ultrasound format; keep NRRD as the acquisition-geometry carrier

- Status: Accepted
- Date: 2026-08-18
- Class: `[arch]`
- Refs: atlas `backlog.md#atlas-us-capability-023` item US-023-F (the mandating
  item); `gap_audit.md#atlas-us-capability-023` (gap G5); ADR 0042 (the
  coordinate-map seam this format would have carried).

## Context

The ITKUltrasound capability audit recorded gap G5: no ultrasound HDF5 IO and no
special-coordinates-aware reader. The reader half is delivered — ritk PR #174
persists `CoordinateMap` through NRRD — which leaves the format question.

ITK's `itkHDF5UltrasoundImageIO` reads a specific, small layout, confirmed from
`src/itkHDF5UltrasoundImageIO.cxx`:

| Dataset | Contents |
| --- | --- |
| `/bimg` | B-mode pixel data |
| `/axial` | axial pixel locations |
| `/lat` | lateral pixel locations |
| `/eleAngle` | elevational slice angle |

It also probes `/ITKImage` to distinguish a plain ITK HDF5 image from an
ultrasound one. Notably the geometry is carried as **explicit coordinate lookup
tables**, not as the parametric fan our `CoordinateMap` uses.

The obstacle is that **ritk cannot read HDF5 at all**. Its only HDF5 code is
`crates/ritk-minc/src/hdf5_binary.rs`, a 521-line MINC2 *writer*, and no
workspace crate depends on an `hdf5` crate. Reading this format therefore means
acquiring an HDF5 reader first.

## Options considered

1. **Add the `hdf5` crate.** Rejected. It is a `-sys` binding over the C
   library, which the standards' pure-Rust preference treats as a last resort
   reserved for true system boundaries — OS interfaces, GPU stacks, vendor SDKs.
   A scientific container format is not one. It would also be invisible to
   clippy, miri and the mutation gates, add a cross-compilation and vendoring
   burden to every consumer of `ritk-io`, and drag a C toolchain requirement
   into a workspace that currently needs none. The cost lands on the whole
   stack; the benefit is one reader for one vendor-adjacent layout.

2. **Hand-roll a constrained HDF5 reader.** Rejected for now. A reader limited
   to contiguous, uncompressed datasets with simple datatypes is achievable, but
   HDF5's superblock, object headers, and B-tree indexing make even that subset
   a substantial artefact to write and, more importantly, to keep correct
   against files written by other tools. It would be the second HDF5
   implementation in the tree, beside the MINC2 writer, and consolidating those
   into one reader/writer is a larger undertaking than the capability justifies
   today.

3. **Decline the format; carry geometry in NRRD** *(selected)*. NRRD already has
   a key/value mechanism, ritk already reads and writes it, and PR #174 already
   carries `CoordinateMap` through it losslessly and round-trip-tested.

4. **Convert at the boundary.** Ask users holding ITK ultrasound HDF5 to convert
   with ITK or `h5py`, which both already read it. Complementary to option 3
   rather than an alternative, and recorded below as the migration path.

## Decision

Adopt option 3. The stack does not gain an HDF5 dependency for this capability,
and NRRD remains the carrier for acquisition geometry.

This is a decision to **not build something the audit listed**, so the reasoning
matters more than usual:

- The capability the audit actually wants is *"acquisition geometry survives
  IO"*, and that is delivered. The HDF5 layout is one vendor-adjacent encoding
  of it, not the capability itself.
- Our geometry model is parametric (`CurvilinearArray`, `PhasedArray3D`), while
  ITK's file carries sampled coordinate tables. Reading that format would
  require either fitting a parametric fan to the tables — inferring parameters
  we were not given — or a fourth `CoordinateMap` variant holding explicit
  tables. Both are real design work that this format alone does not justify.
- Declining costs interoperability only in the read direction, and only for
  files that two widely available tools already convert.

## Consequences

- `ritk-io` gains no C dependency, and the workspace continues to build without
  a C toolchain.
- Users holding ITK ultrasound HDF5 convert to NRRD with ITK or `h5py`. The
  geometry is preserved on the NRRD side by ADR 0042's coordinate map, so the
  conversion is lossless with respect to what ritk models.
- If a real acquisition source emerges that emits only this format, this ADR is
  revisited rather than worked around. The trigger is a *source*, not a
  hypothetical: a file someone actually has, from hardware or a collaborator.
- The explicit-coordinate-table representation stays unmodelled. If it is ever
  needed, it is a `CoordinateMap` variant carrying sampled axes, and that is the
  design conversation to have then.

## Verification

There is nothing to verify beyond what PR #174 already asserts — that a
non-Cartesian acquisition survives a NRRD write/read unchanged. This ADR's claim
is that no further format work is warranted, and its falsifier is the revisit
trigger above.
