# ADR 0036: Neuroimaging, diffusion MRI, and MR physics ownership

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]`
- Relates to: [ADR 0032](0032-modality-transport-and-therapy-boundaries.md),
  [ADR 0029](0029-iris-visualization-promotion.md),
  [ADR 0026](0026-tyche-uq-promotion.md)

## Context

A forward-looking requirement was raised: RITK should support tractography and
connectomics from diffusion MRI, plus MRI processing for population studies. The
open question was framed as "does this fit the current crates, or should it be
its own repository", alongside a parallel question about RF now that CFD,
ultrasound, and radiation are separate integrators.

This is the same class of question ADR 0032 answered for optics, and it must be
answered the same way: against the
[promotion gate](../../README.md#promotion-gate), not against subject-matter
novelty. Diffusion MRI is unfamiliar relative to the current stack contents,
which makes a new repository feel proportionate. Familiarity is not a gate
condition.

### Source audit (2026-07-28)

RITK already owns every input and every primitive this work consumes. At this
revision its workspace carries 30 crates, including:

| Crate | Capability the neuroimaging work needs |
| --- | --- |
| `ritk-nifti`, `ritk-mgh`, `ritk-minc`, `ritk-nrrd`, `ritk-dicom` | every container diffusion-weighted volumes arrive in |
| `ritk-spatial`, `ritk-transform`, `ritk-interpolation` | voxel-to-world geometry, resampling, deformation |
| `ritk-registration` | motion and eddy-current correction, atlas alignment |
| `ritk-filter`, `ritk-morphology`, `ritk-segmentation` | denoising, masking, parcellation support |
| `ritk-tensor-ops`, `ritk-core` | tensor operations on Coeus (`coeus-core` dependency) |
| `ritk-statistics`, `ritk-analyze` | per-image measures |
| `ritk-snap`, `ritk-vtk` | display through Iris color law and view contracts |

Diffusion model fitting is image processing over those primitives. Nothing in
the requirement introduces a bounded context that RITK does not already border.

Applying the gate to a candidate `neuro` package:

| Gate condition | Status | Evidence |
| --- | --- | --- |
| 1. Two packages need it, or code sits in the wrong layer | **Unmet** | RITK is the only consumer. No integrator, and no other domain package, reads diffusion models, streamlines, or connectivity matrices. |
| 2. No current provider owns the bounded context | **Unmet** | RITK owns medical-image processing; this is medical-image processing. |
| 3. ADR defines contract and direction | Satisfiable | — |
| 4. Deletion ledger in every first-wave consumer | **Unmet** | Nothing exists to delete. This is new capability, not consolidation. |
| 5. First change moves real computation into the new owner | **Unmet** | There is no computation to move. |
| 6. Independently versioned or consumed across repository boundaries | **Unmet** | Consumed only inside the RITK workspace. |
| 7. Registration moves with the change | Satisfiable | — |

Five of seven conditions fail. Condition 4 fails in the way the gate treats as
disqualifying on its own: a proposed repository with no named deletion is
rejected.

## Decision

### 1. Neuroimaging lands as RITK workspace crates, not a new package

The deep vertical hierarchy already applies inside a workspace. Three new leaf
crates in RITK, each with one bounded concern:

```text
crates/ritk-diffusion      DWI signal models: tensor, kurtosis,
                           multi-compartment, orientation distribution functions
crates/ritk-tractography   streamline integration, seeding, termination criteria
crates/ritk-connectome     parcellation-to-graph construction and graph measures
```

Crate boundaries follow the data, not the literature: a model that maps signal to
a per-voxel quantity is `ritk-diffusion`; a policy that integrates a field into a
curve is `ritk-tractography`; a reduction of curves and a parcellation into a
graph is `ritk-connectome`. Population and cohort analysis is not a fourth crate
— see decision 3.

Each crate is a complete vertical increment when it lands: specification,
implementation, generic instantiation coverage across shipped scalar types,
analytical or published-reference oracles, Rustdoc, and its book chapter. A crate
that exists as a module tree without oracles is not delivered.

### 2. The new crates consume existing owners rather than reimplementing them

| Concern | Owner | Boundary RITK must not cross |
| --- | --- | --- |
| Nonlinear model fitting | `coeus` | Diffusion fits use Coeus autodiff and optimizers. RITK adds no local optimizer, no local gradient, and no local linear-least-squares path that duplicates `coeus-optim`. |
| Streamline geometry and topology | `gaia` | Streamlines are polyline geometry. RITK owns the integration and termination policy that produces them; Gaia owns the geometric predicates, topology, and any mesh they become. |
| Population and group statistics | `tyche` | Cohort sampling designs, ensembles, sensitivity, and reproducible study vocabulary stay in Tyche. RITK supplies per-subject image measures as study responses. |
| Rendering and color | `iris` | Tract and connectome display uses Iris color law and borrowed view contracts through `ritk-snap` / `ritk-vtk`, per ADR 0029. |
| Derived-array persistence | `consus` | Fitted fields, streamline sets, and connectivity matrices persist through Consus formats, not bespoke writers. |
| Quantities and scalars | `aequitas`, `eunomia` | Diffusivity, b-values, gradient directions, and derived anisotropy are typed quantities over Eunomia scalars. Raw `f32` fields for physical values are prohibited. |
| Execution | `moirai` | Per-voxel fitting and per-seed integration are data-parallel work items dispatched through Moirai, not a local thread pool. |

The recurring failure mode for this kind of work is a package that grows its own
optimizer, its own geometry, and its own statistics because each is locally
convenient. Each of those is a provider edge, and the audit above is the
acceptance criterion.

### 3. Cohort and study processing is a Tyche consumption, not a new owner

"MRI processing for studies" decomposes into two parts with different owners.
Per-subject processing — correction, registration, model fitting, measure
extraction — is RITK. Study structure — cohort design, ensemble execution over
subjects, statistics across subjects, sensitivity, and reproducibility of the
study as a unit — is exactly Tyche's registered bounded context per ADR 0026.

RITK therefore exposes per-subject measures as a Tyche response, and no
`ritk-study` crate is created. A study driver that needs to exist as a program is
an integrator concern, and at this revision no such integrator exists.

### 4. MR physics is a separate question and stays closed

MR *image processing* and MR *physics* are different bounded contexts and must
not be merged under one "MRI" label.

Bloch-equation acquisition simulation — spin evolution, gradient encoding,
k-space formation, sequence timing, coil sensitivity — is an integrator concern
of the same kind as Helios and Kwavers. It is not a RITK concern: RITK consumes
reconstructed images, it does not form them.

No consumer for acquisition simulation exists at this revision. It is
demand-gated, not duplication-gated: it opens when a program needs to simulate
acquisition, and it opens as an integrator, never as a crate inside RITK.

### 5. "RF" names two unrelated concerns; neither justifies a package

ADR 0032 deferred RF and electromagnetics with a named prerequisite. This ADR
adds the distinction that makes that deferral precise:

| Concern | Physics | Home |
| --- | --- | --- |
| RF power deposition and SAR | field → volumetric power density → bioheat | the shared deposition spine (ADR 0032 decision 5); the transport stage is a modality slot, the stages behind it are shared |
| RF at the Larmor frequency for spatial encoding | spin precession and gradient encoding | MR acquisition simulation (decision 4), closed at this revision |

Treating these as one "RF package" would put a therapy-deposition transport
stage and a signal-formation model in the same bounded context. The prerequisite
from ADR 0032 is unchanged: consolidate the existing Kwavers electromagnetics
behind the deposition-spine contract before any RF extraction is considered.

### 6. Trigger to reopen a separate package

A neuroimaging repository opens when, and only when, a second production consumer
outside the RITK workspace deletes a matching implementation in the extraction
change. The most plausible path is a neuroimaging integrator that consumes
connectome graphs alongside a second imaging package; until that consumer exists,
extraction would add topology without consolidating code.

Graph algorithms are the one plausible lower-level owner in this area. They are
not promoted speculatively: if a second package needs the same graph vocabulary,
the recurrence is recorded and the gate is applied then.

## Consequences

- RITK grows three leaf crates and gains diffusion, tractography, and connectome
  capability without a new repository, a new pin, or a new release history.
- The provider edges in decision 2 become RITK's acceptance criteria, so the new
  capability cannot silently fork Coeus optimization, Gaia geometry, or Tyche
  statistics.
- The Atlas package count stays at 25. The
  [stack table](../../README.md#current-stack) and
  [`.gitmodules`](../../.gitmodules) are unchanged by this decision.
- Two future decisions are explicitly left open with named triggers rather than
  implied by this one: MR acquisition simulation as an integrator, and a
  neuroimaging package on a second-consumer recurrence.
- RITK's book gains a diffusion section, and the crates are sequenced so the
  chapter can cite the Coeus and Gaia chapters they depend on.

## Alternatives rejected

**A `neuro` repository now.** Fails gate conditions 1, 2, 4, 5, and 6. It would
create a package whose only consumer is RITK, whose primitives all live in RITK,
and whose first change deletes nothing.

**A single `ritk-neuro` crate.** Collapses three bounded concerns — per-voxel
model fitting, curve integration, graph reduction — into one crate, against the
deep vertical hierarchy and the 500-line file target. The three concerns have
different dependency sets: only tractography needs Gaia, only connectome work
needs graph vocabulary.

**Modules inside `ritk-image` or `ritk-analyze`.** Puts diffusion-specific models
in general-purpose crates, forcing every consumer of basic image processing to
carry the diffusion dependency set. The crate boundary exists to keep the Coeus
autodiff and Gaia geometry edges optional.

**A `ritk-study` crate for population analysis.** Duplicates Tyche's registered
ownership of sampling, ensembles, statistics, and reproducible studies (ADR
0026). Rejected as a second owner for a bounded context that already has one.

**An "MRI" package spanning acquisition and processing.** Merges signal
formation with image analysis. The two share a modality name and nothing else:
different inputs, different oracles, different consumers, different layer.

## Verification

This ADR is a boundary decision; its verification is the audit above plus the
conditions the first implementation increment must satisfy:

1. `.gitmodules` and the Atlas stack table are unchanged — no package is added.
2. The first `ritk-diffusion` increment contains no local optimizer, no local
   gradient computation, and no `rayon`/`tokio` edge; fitting routes through
   `coeus-optim` and `coeus-autograd`, execution through Moirai.
3. Diffusion tensor estimation is verified against an analytical oracle:
   a synthesized tensor field round-trips through signal simulation and
   estimation within a tolerance derived from the scheme's condition number and
   the machine epsilon of `T`, not an empirical constant.
4. Physical values in public signatures are Aequitas quantities; a raw scalar
   field carrying diffusivity or a b-value fails review.
5. Streamline output is expressed in Gaia geometry types; a RITK-local polyline
   type is a boundary violation.
6. Every generic entry point is instantiated across the shipped scalar types in
   the test suite, not only at one concrete type.

## References

- [ADR 0032](0032-modality-transport-and-therapy-boundaries.md) — the modality
  boundary decision this ADR extends to MR and RF.
- [ADR 0029](0029-iris-visualization-promotion.md) — Iris ownership of color law
  and view contracts consumed by tract and connectome display.
- [ADR 0026](0026-tyche-uq-promotion.md) — Tyche ownership of reproducible
  studies, which decision 3 relies on.
- [Promotion gate](../../README.md#promotion-gate) — the seven conditions applied
  in the source audit.
- [Neuroimaging, diffusion MRI, and MR physics](../../README.md#neuroimaging-diffusion-mri-and-mr-physics)
  — the stack-table-facing summary of this decision.
