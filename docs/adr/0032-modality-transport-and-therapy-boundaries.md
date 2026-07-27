# ADR 0032: Modality transport and therapy-integrator boundaries

- Status: Proposed
- Date: 2026-07-27
- Class: `[arch]`

## Context

A proposal was raised to extract optics from Kwavers into a standalone package
that would be "the SSOT for optics, similar to Helios for radiation therapy",
with RF lesioning, electromagnetics, and further physics domains to follow.

The framing merges two distinct Atlas roles. Helios is an **Integrator**: it
owns radiation-therapy workflow, planning, delivery, and imaging. It is not the
SSOT for radiation physics — Hyperion owns photon coefficients and transport
law, Proteus owns material identity and properties, Asclepius owns biological
response, Aequitas owns quantities. A package "similar to Helios" is therefore
an *integrator* decision, entirely separate from "who owns optical transport".

Both decisions must clear the [promotion gate](../../README.md#promotion-gate).

### Source audit (2026-07-27)

Optics in Kwavers is 8 592 LOC across six crates, and it is not one bounded
context:

| Region | LOC | Bounded context |
| --- | --- | --- |
| `kwavers-physics/src/optics/sonoluminescence` | 3 006 | Acousto-optic emission driven by bubble dynamics — **Kwavers-intrinsic** |
| `kwavers-physics/src/optics/monte_carlo` | 1 696 | Radiative-transfer-equation solver (photon MC) |
| `kwavers-solver/src/forward/optical/diffusion` | 1 023 | Diffusion-approximation transport solver |
| `kwavers-physics/src/optics/scattering` | 650 | Rayleigh/Mie coefficient derivation |
| `kwavers-physics/src/optics/polarization` | 576 | Jones calculus |
| `kwavers-optics` (crate) | 514 | Chromophore extinction spectra (hemoglobin) |
| `kwavers-physics/src/optics/quantum_optics` | 498 | Einstein coefficients, Gaunt factors |
| `kwavers-medium/src/properties/optical` | 392 | Optical material properties |
| `kwavers-physics/src/optics/diffusion` | 340 | Diffusion law |
| `kwavers-source/src/optical` | 295 | Laser, LED, fiber sources |
| `kwavers-physics/src/photoacoustics` | 653 | Acousto-optic **coupling** — Kwavers/Harmonia |

Consumer audit for optical transport: `CFDrs` has no radiative, optical, or
photon module; `ritk` has none; `Helios` consumes Hyperion for MeV photon
attenuation, a different regime from the diffusion/RTE solvers above.
**Kwavers is the sole consumer.**

Adjacent modality audit: Kwavers already owns electromagnetics —
`kwavers-physics/src/electromagnetic` (1 948), `kwavers-solver/src/forward/fdtd/
electromagnetic` (596), `kwavers-source/src/electromagnetic` (291) — and bioheat
in `kwavers-physics/src/thermal` (3 237). No RF-lesioning consumer exists.

Hyperion is a `no_std`, Aequitas-typed law crate depending only on
`aequitas`, `eunomia`, `proteus`. It already owns `transport/diffusion.rs`,
`quantity/fluence.rs`, and the optical coefficient set. Its README currently
disclaims chromophore spectra and radiative-transfer solvers as a Phase-0
scoping line.

## Decision

### 1. Reject a standalone `optics` package at this revision

Promotion gate conditions 1, 4, and 6 are unmet: one consumer, a deletion
ledger confined to one repository, and no cross-repository consumption. This is
the same verdict the stack map already records for Ares and Prometheus, reached
by the same audit. The proposal is deferred with named prerequisites, not
rejected on principle.

### 2. Optical transport law and solvers extend Hyperion, not a rival package

Hyperion is the registered owner of light. Founding a second optics package
forks that concept and violates terminology SSOT. Transport capability is added
upstream in Hyperion under provider-first ownership.

Hyperion promotes from single crate to workspace so the `no_std` law layer does
not force an array substrate onto Helios and CFDrs:

```text
crates/hyperion            law, no_std   (aequitas, eunomia, proteus)   — unchanged
crates/hyperion-transport  solvers       (+ leto, hephaestus, moirai, athena, tyche)
```

`hyperion-transport` owns the modality-neutral transport operators: diffusion
approximation, Monte Carlo RTE, and the coefficient-to-operator assembly. It
does not own sources, applicators, geometry, coupling, or workflow.

### 3. Sonoluminescence, photoacoustics, and quantum optics stay in Kwavers

3 006 LOC of sonoluminescence is emission physics driven by Rayleigh–Plesset
bubble dynamics, and 653 LOC of photoacoustics is an acousto-optic coupling.
Both are Kwavers-intrinsic; a scope that swallows them is wrong regardless of
the package decision. Coupling orchestration belongs to Harmonia.

### 4. Chromophore spectra move to Hyperion now

The `kwavers-optics` crate is 514 LOC of validated wavelength-dependent
extinction reference data sitting in an integrator leaf crate while Hyperion
owns optical coefficients. That is promotion gate condition 1, second clause —
an existing implementation in the wrong dependency layer — and it carries a
named deletion (the whole crate). Hyperion's spectra disclaimer is revised;
wavelength-resolved absorption coefficient is its bounded context.

### 5. The reusable seam is the deposition spine, not "optics"

Optics, RF/EM, radiation, and focused ultrasound share one pipeline and differ
only in the transport stage:

```text
source/applicator → energy transport → volumetric deposition → bioheat → damage response → safety/planning
                    ↑ modality-specific    ↑ SHARED             ↑ SHARED   ↑ Asclepius      ↑ Integrator
```

The extractable asset is the shared middle, expressed in Aequitas quantities so
every modality speaks one vocabulary:

| Interface quantity | SI | Producer |
| --- | --- | --- |
| Irradiance / fluence rate | W·m⁻² | transport |
| Volumetric power density | W·m⁻³ | deposition |
| Specific absorption rate | W·kg⁻¹ | RF/EM deposition |
| Absorbed dose | J·kg⁻¹ | deposition |

Every transport implementation — present and future — terminates in
`VolumetricPower` as an Aequitas quantity. Bioheat consumes that one type, and
Asclepius consumes bioheat output. A modality package then becomes a slot that
plugs into a typed contract, and its promotion is mechanical rather than a
judgment call. This is the answer to the scaling question the proposal raises:
name and type the spine, and modality packages stop being architectural
decisions.

### 6. RF lesioning and electromagnetics stay deferred with a named prerequisite

No second consumer and no RF integrator exist. The prerequisite is the same as
for optics: consolidate Kwavers electromagnetics behind the deposition-spine
contract (SAR → `VolumetricPower` → bioheat), at which point a second consumer
can delete a matching implementation in the extraction change.

### 7. A photomedicine integrator is a separate, later decision

A laser/LED/PDT/PBM therapy suite peer to Helios is an integrator, gated on
demand rather than on duplication. Nothing beyond 295 LOC of source models
exists today; Kwavers `therapy` (41 674 LOC) is acoustic-therapy workflow.
Revisit only when photomedicine planning exists and is large enough that
Kwavers is the wrong home. It is out of scope for this ADR.

## Consequences

- Hyperion becomes a workspace; consumers of the law crate see no dependency
  change because `hyperion` keeps its `no_std` dependency set.
- Kwavers deletes `kwavers-optics` and repoints `kwavers-imaging` /
  `kwavers-physics` chromophore consumers at Hyperion.
- Kwavers optics is consolidated behind a single internal boundary before any
  transport extraction, so extraction is a move rather than a redesign.
- Naming is unchanged: Hyperion remains the single name for light. No new name
  is minted for optics, and no name carries an `Atlas` prefix.

## Alternatives rejected

- **Standalone `optics` package now.** Fails gate 1/4/6; forks the light
  concept away from Hyperion; would capture sonoluminescence and photoacoustics
  by proximity rather than by boundary.
- **One `photonics` package spanning optics + RF + EM.** Creates the unbounded
  domain ADR 0030 already rejected, and reverses valid dependency edges.
- **Leave everything in Kwavers.** Retains chromophore reference data in an
  integrator leaf crate against the wrong-layer clause, and leaves the
  deposition spine untyped so each new modality re-derives it.

## Verification

- Chromophore migration: differential test asserting Hyperion spectra equal the
  deleted `kwavers-optics` tables at every tabulated wavelength; `kwavers-optics`
  absent from the workspace member list and from every `Cargo.toml`.
- Deposition spine: property test that each transport backend's output is a
  `VolumetricPower` quantity, and an energy-conservation test that integrated
  deposition equals absorbed source energy within a derived bound.
- Transport extraction (when gated): shared conformance suite instantiated over
  every scalar and backend, plus a Kwavers differential test against the
  pre-extraction implementation.

## References

- [`README.md#promotion-gate`](../../README.md#promotion-gate) — the seven gate conditions applied above.
- [ADR 0030](0030-hyperion-photon-optical-promotion.md) — Hyperion's bounded context and the unbounded-domain rejection this ADR extends.
- [ADR 0028](0028-asclepius-biological-response-promotion.md) — biological-response ownership at the end of the deposition spine.
- [ADR 0021](0021-aequitas-quantity-law-foundation.md) — the quantity law the spine contract is expressed in.
