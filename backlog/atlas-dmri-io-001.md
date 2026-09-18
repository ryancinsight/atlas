<a id="atlas-dmri-io-001"></a>
## ATLAS-DMRI-IO-001 — Rank-generic acquisition-series I/O [minor] — in-progress

**Claim 2026-08-11 — Codex current session:** own the next vertical
`ritk-nrrd` increment on branch `codex/ritk-nrrd-series` in the reclaimed
`worktrees/ritk-book-wf` lane. Claimed files are the NRRD reader/writer,
their co-located tests, and the package-local documentation needed for rank-4
acquisition-series round trips. Non-goals are MGH, DICOM, `ritk-io` dispatch,
and the peer-dirty ADR index in the primary RITK checkout.

**Re-audit closure 2026-08-11:** no NRRD implementation was added because
`origin/main` already carries the complete `d3d3d811` series implementation:
leading and trailing acquisition-axis decoding, rank-4 writing, shared-grid
validation, and value-semantic tests. RITK PR #119 merged at
`0a1a4dc98ec541ea2caa952dd2385c9ebfac583b` with its hosted Rust, Python,
workspace-alignment, and platform test jobs green. The local `--locked` gate
was blocked before compilation by the separately tracked provider drift
(`hermes-simd` 0.5.0 and `moirai-runtime` 0.4.0 locks versus current provider
heads); RITK PR #118 owns the overlay-free release-lock repair. The NRRD
sub-scope therefore closes as an evidence-backed stale-gap correction, while
MGH, DICOM, and `ritk-io` dispatch remain open sub-increments of this item.

**`ritk-nifti` increment delivered** at `ritk` `2a4b1f62`, pushed to
`codex/perf-ritk-mgh-stream-book` (PR #78, a peer's branch — the scopes are
disjoint, `ritk-nifti` vs the peer's `ritk-mgh` streaming slice, so the increment
rides that branch per the shared-branch model rather than opening a second PR).

Rank 3 and rank 4 both parse; the payload byte range spans every declared volume
instead of one; `read_nifti_series` / `read_nifti_series_from_bytes` /
`write_nifti_series` / `write_nifti2_series` are the series surface. The writer
selects rank from the volume count, so a one-volume series stays a rank-3 file
byte-identical to `write_nifti`, and it validates that every volume shares one
grid rather than emitting a file whose sform covers only part of its content.
`read_nifti` and `read_nifti_labels` now name the volume count and fail on a
rank-4 file instead of decoding volume 0 — the MGH defect class, caught before it
could ship in a second codec.

Verified: 49/49 `ritk-nifti` (0.564s), 370/370 `ritk-io` + `ritk-analyze`
downstream, clippy `--all-targets -D warnings` clean, `RUSTDOCFLAGS=-D warnings
cargo doc` clean.

Design decision recorded here rather than an ADR, being reversible and internal:
the series surface returns `Vec<Image<f32, B, 3>>` rather than a new
`ImageSeries` domain type. Volumes on one grid is what the format states, it
needs no cross-crate public API, and it does not prejudge the type
ATLAS-DMRI-SCHEME-003 actually needs — which carries the gradient scheme
alongside the volumes and is where the per-voxel-across-volumes access pattern
will be known. A contiguous layout stays open behind that type.

Remaining sub-increments: `ritk-mgh` series read (currently fails loudly per
ATLAS-DMRI-MGH-FRAMES-002, so this is an extension not a fix), `ritk-dicom`
multi-frame/series assembly, and the `ritk-io` dispatch tail. The NRRD
increment is closed by `d3d3d811` on the merged RITK head.



## ATLAS-DMRI-IO-001 original specification

- **Outcome**: `ritk-nifti`, `ritk-nrrd`, and `ritk-dicom` read and write a
  series carrying an acquisition axis, and `ritk-io` dispatches it.
- **Evidence of gap at item creation**: `ritk-nifti/src/header/validate.rs:74`
  bailed on `dim[0] != 3`; `ritk-nrrd` rejected acquisition-series headers;
  and `ritk-io/src/lib.rs:164` fixed `NativeImage = Image<f32, NativeBackend,
  3>`. The NRRD rejection was closed by `d3d3d811`; MGH, DICOM, and dispatch
  remain the live gaps.
- **Non-goals**: no change to `Image<T, B, D>`, which is already rank-generic;
  no arbitrary-rank generalization beyond one acquisition axis.
- **Design note**: a DWI series is 3 spatial axes plus 1 acquisition axis, not a
  4-D image. `Point<4>`/`Spacing<4>`/`Direction<4>` would assert direction
  cosines over the acquisition axis, which is meaningless. The type carries 3-D
  spatial metadata plus a per-volume scheme (ATLAS-DMRI-SCHEME-003), so the
  metadata stays 3-D and only storage gains the axis.
- **Acceptance**: round-trip a synthesized N-volume series through each codec
  recovering voxels and spatial metadata exactly; the existing 3-D entry points
  keep their signatures and tests.
- **Class**: `[minor]` — additive public surface.
- **Sequencing note (2026-07-31)**: no longer split — the `ritk-io` block
  cleared when ATLAS-RITK-MODULE-FORWARD-000 resolved. The `ritk-nifti` and
  `ritk-nrrd` increments are now closed on `origin/main`. The next increments
  are the `ritk-io` dispatch tail and the `ritk-mgh` series extension; MGH
  already fails loudly on a multi-frame file per ATLAS-DMRI-MGH-FRAMES-002, so
  its series read is an extension rather than a defect fix.

