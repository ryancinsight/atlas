<a id="atlas-dmri-tractogram-fmt-014"></a>
## ATLAS-DMRI-TRACTOGRAM-FMT-014 — Tractogram container ownership [arch] — todo

- **Decision needed:** MRtrix `.tck`, TrackVis `.trk`, and TRX are published byte-level interchange specs (RITK format-crate pattern), but ADR 0036 decision 2 routes derived-array persistence to Consus — the two rules point at different owners for the same artifact.
- **Recommended (proceed unless overridden):** an interchange format other toolchains read is a RITK format crate; a derived-array store for Atlas-internal persistence is Consus.
- **Also open:** MRtrix `.mif`/`.mif.gz` spans both an image container (001) and an embedded gradient-scheme carrier (003).
- **Deliverable:** ADR 0036 revision recording the resolution, or a new ADR if it generalizes beyond this artifact. **Class:** `[arch]`, `[patch]` on SemVer.
