<a id="atlas-dmri-tractogram-fmt-014"></a>
## ATLAS-DMRI-TRACTOGRAM-FMT-014 — Tractogram container ownership [arch] — in-progress
- Status: in-progress; priority: architecture; scope: ADR 0036, RITK format ownership, and the Atlas ownership summary.
- Resolution: `.tck`, `.trk`, and TRX are RITK interchange codecs; Consus owns derived-array persistence; `ritk-mif` owns the image container while `ritk-diffusion-scheme` owns `DW_scheme` semantics.
- Acceptance: compact ADR 0036 below 150 lines, record the dated revision and `.mif.gz` implementation limit, synchronize the Atlas summary, and pass ADR/index/link gates; basis: `cfd99f331`.
- Next: revise ADR 0036 and close this item only after the ownership record and evidence are committed.
