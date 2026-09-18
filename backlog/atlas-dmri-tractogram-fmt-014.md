<a id="atlas-dmri-tractogram-fmt-014"></a>
## ATLAS-DMRI-TRACTOGRAM-FMT-014 — Tractogram container ownership [arch] — todo

- **Decision needed**: MRtrix `.tck`, TrackVis `.trk`, and TRX are published
  byte-level interchange specifications, which is the RITK format-crate pattern;
  ADR 0036 decision 2 routes derived-array persistence to Consus. The two rules
  point at different owners for the same artifact.
- **Recommended resolution** (per bias-to-completion, proceed on this unless
  overridden): an interchange format that other toolchains read is a RITK format
  crate; a derived-array store for Atlas-internal persistence is Consus. A
  streamline set written for MRtrix or TrackVis to read is interchange.
- **Also open**: MRtrix `.mif` / `.mif.gz`, which is both an image container and
  an embedded gradient-scheme carrier, so it spans 001 and 003.
- **Deliverable**: ADR 0036 revision recording the resolution, or a new ADR if it
  generalizes beyond this artifact.
- **Class**: `[arch]`, no public-surface break — `[patch]` on the SemVer axis.

