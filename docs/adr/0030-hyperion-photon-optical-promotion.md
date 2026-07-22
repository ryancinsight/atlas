# ADR 0030: Promote Hyperion photon and optical transport

- Status: Accepted
- Date: 2026-07-21
- Class: `[arch]` `[minor]`

## Context

Helios, Kwavers, and CFDrs independently evaluate Beer–Lambert transmission.
Helios also owned coefficient newtypes and NIST attenuation tables, while
Kwavers repeated reduced-scattering, diffusion, effective-attenuation, and
penetration-depth formulas across several crates. These are the same
photon/optical interaction laws in different consumer hierarchies.

Neither Aequitas nor Proteus owns those laws. Aequitas owns dimensions,
quantities, and units; Proteus owns material identity, validated material
properties, and constitutive response. Leaving attenuation in an integrator
duplicates validation, equations, reference data, and tests. Moving all
radiation, optics, dose, or electromagnetics into one package would instead
create an unbounded domain and reverse valid dependency edges.

## Decision

Promote public package `hyperion` as the bounded owner of photon and optical
interaction coefficients and laws. Phase 0 owns:

- validated absorption, scattering, reduced-scattering, linear, effective,
  transport, and mass-attenuation coefficients;
- path length, photon energy, energy fluence, anisotropy, optical depth,
  transmission, and ordinary/reduced albedo contracts;
- mass-to-linear attenuation, additive optical depth, Beer–Lambert
  transmission, mean-free-path, half-value-layer, diffusion, and effective-
  attenuation laws; and
- bounded NIST attenuation reference tables with declared interpolation
  semantics.

The dependency direction is:

```text
eunomia ──> aequitas ──┐
                       ├──> hyperion ──> helios / kwavers / CFDrs
proteus ───────────────┘
```

Hyperion depends on Aequitas quantities and accepts Proteus material density at
the mass-to-linear boundary. Aequitas and Proteus do not depend on Hyperion.
Consumers import Hyperion directly; no Helios, Kwavers, or CFDrs facade,
re-export, adapter, or mirrored type family remains.

The boundary is deliberately narrow. Helios retains CT calibration, Compton
source models, spatial projection, dose deposition, imaging, planning, and
delivery. Kwavers retains chromophore spectra, acoustic/photoacoustic coupling,
sources, and workflows. CFDrs retains flow, empirical coefficient selection,
and device scoring. Geometry, arrays, solver policy, and accelerator execution
remain with Gaia, Leto, Athena, and Hephaestus.

## Consolidation accounting

| Concern | Before | Authoritative result | Required consumer deletion |
| --- | --- | --- | --- |
| Coefficient vocabulary | Helios and Kwavers define parallel coefficient models. | Hyperion types over one Aequitas quantity identity. | Remove consumer types, constructors, re-exports, and conversion wrappers. |
| Reference attenuation data | Helios owns local NIST tables. | Hyperion owns bounded tables and interpolation tests. | Delete Helios tables and redirect coefficient consumers. |
| Beer–Lambert law | Three packages call raw `exp(-tau)`. | Hyperion owns validated optical depth and transmission. | Replace production scalar laws; retain independent analytical expressions only as test/benchmark oracles. |
| Derived optical laws | Kwavers repeats reduced-scattering and diffusion formulas. | Hyperion owns one generic implementation and theorem suite. | Delete every duplicate formula and make aggregates delegate directly. |
| Material boundary | Density is passed as an unvalidated scalar. | Proteus validates density; Hyperion evaluates mass-to-linear attenuation. | Remove consumer material-property substitutes. |

The package is therefore justified by net deletion and a lower common owner,
not by package count. P2 does not authorize a second new package. Ares and
Prometheus remain blocked until their prerequisite consolidation produces a
second production consumer and a deletion ledger that cannot be satisfied by
Proteus or Horae.

## Migration

1. Extend Aequitas with the required reciprocal-length, area-per-mass, and
   energy-per-area dimensions and align Proteus to that exact revision.
2. Publish Hyperion with analytical, adversarial, generic-scalar, layout,
   allocation, and exact NIST-knot evidence; verify anonymous access.
3. Migrate Helios, Kwavers, and CFDrs in dependency order. Each consumer change
   deletes its superseded owner, preserves an independent differential oracle,
   and propagates typed validation errors.
4. Register Hyperion in Atlas only after every first-wave deletion is published
   and the parent can pin one coherent graph.
5. Re-audit the Ares and Prometheus promotion triggers independently; neither
   inherits authority from Hyperion's promotion.

Mutating Helios TERMA deposition was sequenced as a separate vertical increment
because a typed failure must leave the dose volume unchanged and must not
introduce a per-segment allocation. That increment is complete at `45986d8`:
the complete sampled ray is validated before mutation without a staging buffer.

## Evidence

Aequitas `cf9b2c3` and Proteus `a61d0e5` pass their local gates and hosted CI.
Hyperion `064a189` is anonymously readable; its local format, feature checks,
warning-denied Clippy, 12/12 Nextest cases, doctest, Rustdoc, example,
dependency-policy, and SemVer gates pass, as does hosted CI run `29877136400`.
Asclepius `e85350d` passes local gates and hosted CI after aligning the shared
Aequitas identity. Leto `80406d9` and Hephaestus `71b3ca7` pass their applicable
local consumer gates; those repositories have no push-triggered Rust CI
workflow.

Helios `45986d8` deletes its local coefficient types, NIST tables, projection
law, and production Beer–Lambert expressions, including transactional TERMA
deposition. Its exact local revision passes all-feature warning-denied Clippy,
257/257 configured Nextest cases, doctests, warning-denied Rustdoc, examples,
dependency policy, residue scans, and consumer differentials. SemVer identifies
the four intended major physics-facade removals and no additional violation.

Kwavers and CFDrs migration plus Atlas registration evidence remains open.
Acceptance of this ownership decision does not claim that the three-consumer
deletion ledger is complete.

## Rejected alternatives

- Keeping the laws in Helios leaves Kwavers and CFDrs depending on a
  radiation-therapy integrator or retaining copies.
- Putting photon transport in Proteus conflates material state with radiation
  interaction and makes general material consumers inherit an unrelated law
  surface.
- A consumer facade or compatibility re-export preserves two vocabularies and
  defeats the SSOT migration.
- Promoting Ares or Prometheus now adds a repository without two production
  consumers or net deletion; their immediate shared work belongs in Proteus or
  Horae.
- Expanding Hyperion to Maxwell solvers, Monte Carlo transport, dose, or
  workflow policy creates a cross-domain package instead of a bounded owner.

## Consequences

One provider now owns validation, units, equations, reference data, and theorem
tests for the shared transport domain. Consumers shrink to orchestration and
their own spatial or workflow policies. Public consumer removals are breaking
changes and are classified independently; Hyperion's new API is additive.

This split adds one dependency edge but removes several implementations and
prevents future optical backends from copying laws into each integrator. The
remaining risk is migration completeness, measured by the deletion ledger,
residue scans, consumer differentials, and exact hosted revision gates.
