# ADR 0036: Neuroimaging, diffusion MRI, and MR physics ownership

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]`
- Item: [ATLAS-DMRI-TRACTOGRAM-FMT-014](../../backlog.md#atlas-dmri-tractogram-fmt-014)
- Relates to: [ADR 0032](../../docs/adr/0032-modality-transport-and-therapy-boundaries.md), [ADR 0029](../../docs/adr/0029-iris-visualization-promotion.md), [ADR 0026](../../docs/adr/0026-tyche-uq-promotion.md)

## Context

A forward-looking requirement asks whether diffusion MRI, tractography, connectomics, and population MRI belong in RITK or a new repository. RITK already borders the bounded contexts: image containers and codecs, spatial transforms, registration, tensor operations, filtering, segmentation, and visualization are present. The question is ownership against the [promotion gate](../../README.md#promotion-gate), not subject-matter novelty.

The 2026-07-30 capability audit corrected an earlier overclaim: RITK owning a bounded context did not mean it already read every required artifact. At that audit basis, no RITK reader accepted a diffusion-weighted series, and no crate modeled b-values and gradient directions. Those are format-crate prerequisites, not evidence for a new repository. The current RITK workspace has 42 library crates and now carries the acquisition, tractography, connectome, and tractogram format increments.

The promotion gate fails for a new repository: RITK is the only current consumer; no existing implementation would be deleted; no computation would move; and no independently versioned cross-repository consumer exists. Conditions 1, 2, 4, 5, and 6 fail, while the contract and registration conditions remain satisfiable. A second production consumer that deletes a matching implementation remains the trigger to reconsider extraction.

## Decision

### 1. Neuroimaging lands as RITK workspace crates

Three leaf crates follow the data and policy boundaries:

```text
crates/ritk-diffusion      DWI signal models: tensor, kurtosis,
                           multi-compartment, and ODF models
crates/ritk-tractography   streamline integration, seeding, and termination
crates/ritk-connectome     parcellation-to-graph construction and measures
```

A model that maps signal to a per-voxel quantity belongs to `ritk-diffusion`; a policy that integrates a field into a curve belongs to `ritk-tractography`; a reduction of curves and a parcellation into a graph belongs to `ritk-connectome`. Each increment includes its contract, implementation, scalar coverage, analytical or published-reference oracle, Rustdoc, and book chapter. A module tree without oracles is not delivered.

### 2. Provider boundaries remain one-way

| Concern | Owner | RITK boundary |
| --- | --- | --- |
| Nonlinear fitting | `coeus` | Use Coeus autodiff and optimizers; no local optimizer, gradient, or least-squares path. |
| Dense linear solves | `leto` | Assemble the design matrix; solve through `leto-ops`. |
| Spherical harmonics | `apollo` | Consume the basis, normalization, transforms, and scattered-direction design matrix. |
| Streamline geometry | `gaia` | RITK owns integration policy; Gaia owns `Polyline`, predicates, topology, and meshes. |
| Study structure | `tyche` | Supply per-subject measures as Tyche responses; do not create `ritk-study`. |
| Rendering and color | `iris` | Use Iris color and view contracts through RITK display crates. |
| Derived-array persistence | `consus` | Normative boundary: store fitted fields, streamline sets, and connectivity matrices through Consus; do not write bespoke persistence. |
| Quantities and scalars | `aequitas`, `eunomia` | Use typed physical quantities; raw scalar fields are invalid. |
| Execution | `moirai` | Dispatch per-voxel fitting and per-seed integration; no local pool. |

At the audit basis, four provider gaps were recorded: nonlinear least squares in Coeus, the real symmetric SH basis in Apollo, constrained nonnegative solves in Leto, and a Gaia polyline type. They are upstream work, never RITK workarounds; their current delivery state is tracked by the provider boards. Sphere tessellation and direction-set generation are also Gaia geometry.

### 3. Cohort and study processing is a Tyche consumption

Per-subject correction, registration, fitting, and measurement remain RITK. Cohort design, ensemble execution, cross-subject statistics, sensitivity, and reproducibility remain Tyche under ADR 0026. RITK exposes per-subject measures; no `ritk-study` crate is created. A future study driver is an integrator concern.

### 4. MR physics is separate and remains closed

MR image processing and MR physics are different bounded contexts. Bloch-equation acquisition simulation, gradient encoding, k-space formation, sequence timing, and coil sensitivity are integrator concerns. RITK consumes reconstructed images and does not form them. No acquisition-simulation consumer exists at this revision; the capability opens only when a program requires it, as an integrator rather than a RITK crate.

### 5. RF names two unrelated concerns

RF power deposition and SAR belong on the shared deposition spine defined by ADR 0032. RF at the Larmor frequency for spatial encoding belongs to acquisition simulation and remains closed. Combining them would mix transport-stage policy with signal formation. The ADR 0032 prerequisite remains unchanged: consolidate Kwavers electromagnetics behind the deposition-spine contract before considering extraction.

### 6. Trigger to reopen a separate package

A neuroimaging repository opens only when a second production consumer outside RITK deletes a matching implementation in the extraction change. A neuroimaging integrator consuming connectome graphs with another imaging package is the plausible trigger. Graph algorithms are not promoted speculatively; a second consumer of the same graph vocabulary invokes the gate again.

### 7. Acquisition-series I/O is a prerequisite wave

The format crates must read and write the acquisition axis before model fitting. `Image<T, B, D>` is already rank-generic; restrictions in NIfTI, NRRD, MGH, and DICOM are format-crate work. The MGH frame-drop defect is independent and is fixed regardless.

One typed acquisition scheme carries b-values and unit gradient directions in a declared frame. RITK's physical metadata is LPS; readers state their input frame and convert once. A transform applied to a series reorients its gradient table. FSL `.bval`/`.bvec`, MRtrix `DW_scheme`, NRRD DWI keys, and DICOM diffusion tags are codecs for that one contract; a standalone MRtrix `.b` file codec remains a prerequisite. Surface-based parcellation formats remain a named prerequisite for `ritk-connectome` and are not resolved by this decision.

### 8. Tractogram and MIF ownership revision — 2026-09-24

The previously open tractogram-container distinction is resolved by the current workspace:

- MRtrix `.tck`, TrackVis `.trk`, and TRX are published interchange grammars owned by `ritk-tck`, `ritk-trk`, and `ritk-trx`. They own byte parsing, validation, writing, and their format-specific coordinate conventions. `ritk-tractography` owns integration policy; Gaia owns the returned `Polyline` geometry.
- Consus remains the scientific storage provider for derived arrays. A Consus-backed store of tractogram-derived data does not transfer ownership of `.tck`, `.trk`, or TRX to Consus and authorizes no Consus tractogram codec or canonical tractogram model.
- `ritk-mif` owns the MRtrix image container, dimensions, layout, geometry, and voxel I/O. `ritk-diffusion-scheme` owns the typed `GradientScheme` and `DW_scheme` semantics. A future `.mif.gz` implementation remains in the RITK interchange boundary; the current tree has no `.mif.gz` support, and this revision selects no compression provider or claims end-to-end MIF scheme writing.

The evidence is the RITK workspace manifest and the `ritk-tck`, `ritk-trk`, `ritk-trx`, `ritk-mif`, and `ritk-diffusion-scheme` crate contracts. Consus's format inventory contains no tractogram codec. This is a clarification of ownership already implemented in RITK, not a repository promotion or code migration.

## Consequences

- RITK keeps three domain crates and the format crates that own external bytes; the Atlas package count and `.gitmodules` do not change.
- Consus remains a storage provider and does not become a second tractogram format owner.
- Provider gaps and diffusion codecs remain explicit prerequisites; no RITK-local substitute is permitted.
- The RITK book gains diffusion and tractography sections, and a future `.mif.gz` codec remains a RITK format task.

## Alternatives rejected

- A new `neuro` repository fails the promotion gate and duplicates an existing RITK boundary.
- A single `ritk-neuro` crate collapses distinct model, integration, and graph concerns.
- Diffusion modules in `ritk-image` or `ritk-analyze` force unrelated consumers to depend on diffusion code.
- A `ritk-study` crate duplicates Tyche's study and statistics ownership.
- One broad MRI package mixes image processing with acquisition physics.
- Assigning `.tck`, `.trk`, TRX, or `.mif` codecs to Consus contradicts the current RITK format ownership and would create a second byte-level owner.

## Verification

1. `.gitmodules` and the Atlas stack table remain unchanged.
2. The first `ritk-diffusion` increment contains no local optimizer, gradient, spherical-harmonic basis, `rayon`, or `tokio` edge; provider edges follow decision 2.
3. Tensor estimation is checked against a synthesized field with a condition-number-derived tolerance.
4. Public physical values use Aequitas quantities rather than raw scalar fields.
5. Streamline output uses Gaia geometry types.
6. Generic entry points instantiate every shipped scalar type.
7. A known anisotropic field rotated by a correction recovers its principal direction only when the gradient scheme is reoriented.
8. FSL, MRtrix, NRRD, and DICOM acquisition-scheme codecs round-trip and agree on one dataset.
9. The RITK workspace manifest and crate contracts identify `ritk-tck`, `ritk-trk`, `ritk-trx`, and `ritk-mif` as format owners; the Consus format inventory contains no tractogram codec; the MIF scheme boundary names `ritk-diffusion-scheme` and records the `.mif.gz` limitation.

## Revision history

- 2026-07-30: capability audit withdrew the claim that RITK already read every input and recorded the acquisition-series prerequisites.
- 2026-09-22: downstream repository references were generalized under the privacy-naming decision.
- 2026-09-24: resolved tractogram interchange ownership, the Consus derived-array boundary, and the MIF image/scheme split using current RITK and Consus source evidence.

## References

- [ADR 0032](../../docs/adr/0032-modality-transport-and-therapy-boundaries.md)
- [ADR 0029](../../docs/adr/0029-iris-visualization-promotion.md)
- [ADR 0026](../../docs/adr/0026-tyche-uq-promotion.md)
- [Promotion gate](../../README.md#promotion-gate)
- [RITK diffusion pipeline](../../repos/ritk/docs/adr/0017-diffusion-mri-pipeline.md)
- [RITK tractogram format crates](../../repos/ritk/crates/ritk-tck/src/lib.rs)
