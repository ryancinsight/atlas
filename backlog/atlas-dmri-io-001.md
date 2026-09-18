<a id="atlas-dmri-io-001"></a>
## ATLAS-DMRI-IO-001 — Rank-generic acquisition-series I/O [minor] — in-progress

- **outcome:** `ritk-nifti`, `ritk-nrrd`, `ritk-dicom` read/write a series
  carrying an acquisition axis, and `ritk-io` dispatches it.
- **done:** NRRD closed on merged RITK head (`d3d3d811`, PR #119). NIfTI
  series delivered at `ritk` `2a4b1f62` (PR #78): rank 3/4 parsing,
  series read/write, one-grid validation; 49/49 tests, clippy/doc clean.
- **open:** `ritk-mgh` series read (extension — MGH fails loudly per
  ATLAS-DMRI-MGH-FRAMES-002), `ritk-dicom` multi-frame/series assembly,
  the `ritk-io` dispatch tail.
- **design note:** series stays `Vec<Image<f32, B, 3>>`, not a new
  domain type; contiguous layout stays open behind ATLAS-DMRI-SCHEME-003.
- **acceptance:** round-trip an N-volume series recovering voxels/
  metadata exactly; 3-D entry points keep their signatures.
