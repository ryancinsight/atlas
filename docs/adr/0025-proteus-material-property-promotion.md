# ADR 0025: Promote Proteus material-property foundation

- Status: Accepted
- Date: 2026-07-20
- Class: `[arch]` `[minor]`

## Context

CFDrs, Kwavers, and Helios each carried private copies of validated
material-property and constitutive-law contracts: density, specific heat
capacity, thermal conductivity, and the derived thermal-diffusivity law.
The validity boundaries, cohesive property bundles, statically dispatched
constitutive evaluation, and named material identity recur across the
three integrators. Reimplementing the same thermophysical law in each
consumer violates provider-first ownership and SSOT.

Aequitas owns dimensions and units. Eunomia owns the real scalar contract.
Proteus composes those providers without re-owning any of them. Each
integrator retains its domain-specific constitutive behavior: Kwavers keeps
acoustic attenuation, optical response, and perfusion; CFDrs keeps fluid
rheology and flow closure; Helios keeps photon interaction and CT
calibration. Proteus owns the shared material-property vocabulary; it does
not duplicate the domain laws.

## Decision

Promote public package `proteus` as the Atlas owner for shared material
properties and statically dispatched constitutive-law contracts. Phase 1
is one `no_std + alloc` crate with `#![forbid(unsafe_code)]` and
`#![deny(missing_docs)]`. It begins with validated isotropic
thermophysical properties: mass density, specific heat capacity, thermal
conductivity, and the derived thermal-diffusivity law.

The constitutive seam is generic over state by associated type.
`ConstitutiveLaw<Law>` carries a state family so state-dependent
implementations can borrow solver state through GATs, and `ConstantLaw`
uses the zero-sized `NoState`. Property newtypes are `#[repr(transparent)]`
over Aequitas quantities so dimensional algebra reduces the result and
validation lives at the boundary. `Material` uses `Cow<str>` so static
catalogs borrow names and runtime materials own names through one API.

### Dependency direction

```text
proteus ──> aequitas
        ──> eunomia
```

Proteus depends on Aequitas and Eunomia. It does not depend on Leto,
Hephaestus, Moirai, Mnemosyne, Themis, Melinoe, Hermes, Coeus, Horae,
Athena, Harmonia, or any integrator. It owns no array, device buffer,
scheduler, allocator, capability proof, time integration, or solver.

## Migration plan

1. Publish Proteus Phase 1 and register its fetched remote-default
   gitlink (done at master HEAD `2b06be3`).
2. Migrate one consumer material-property site at a time in dependency
   order. Each consumer increment adopts the Proteus newtype and removes
   the local copy in the same vertical slice; no adapter or compatibility
   shim lands.
3. Extend the constitutive-law vocabulary only after each new law's
   validity boundary, dimensional algebra, and consumer overlap are
   recorded and independently verifiable.

## Theorems and evidence

Proteus ADR 0001 owns the formal statements and proof obligations:

- Density positivity: `rho > 0` is a typed boundary enforced at
  construction.
- Heat-capacity positivity: `c_p > 0` is a typed boundary.
- Conductivity non-negativity: `k >= 0` is a typed boundary.
- Thermal diffusivity law: `alpha = k / (rho c_p)` with positive
  denominator so `alpha >= 0`; Aequitas dimensional algebra reduces the
  result to `L^2/T`.

Revision `2b06be3` passed format, `no_std`, warning-denied Clippy,
nextest over `--all-features`, doctest, warning-denied rustdoc, and
cargo-deny. The suite covers positivity, linear conductivity scaling,
`f32` and `f64` instantiation, and the typed-vs-raw codegen equivalence
fixture.

The package is `publish = false`; no `cargo-semver-checks` baseline
exists against a prior registry release. SemVer comparison begins from
this public Git contract.

## Rejected alternatives

- Consumer-owned material-property tables duplicate validity boundaries,
  dimensional reduction, and statically dispatched evaluation in three
  integrators.
- Proteus-owned Aequitas dimensions or Eunomia scalars fork the
  `Scalar` and quantity contracts.
- A graph-coupled multi-phase material library in Phase 1 speculates
  about consumer contracts that are not stable.
- A Proteus dep on Leto or Hephaestus pulls arrays or device buffers into
  a vocabulary layer that should be array- and device-neutral.

## Consequences

- Atlas records 21 public packages once the Proteus gitlink is recorded
  at `2b06be3` (peer commits `f043d22`, `beb2713`).
- Consumer migrations proceed as dependency-ordered vertical slices owned
  by the respective integrator claim streams.
- Phase 1 excludes anisotropic constitutive laws, reaction kinetics,
  tabular property lookup, phase and mixture vocabulary, and
  rate-dependent laws. No excluded capability is represented by a stub
  or compatibility shim.

## Relates to

- ADR 0002: heterogeneous topology law — Proteus Phase 1 stays inside
  the bounded material-property role.
- ADR 0005: Eunomia scalar SSOT — Proteus consumes the real scalar
  contract.
- ADR 0021: Aequitas quantity law — Proteus property newtypes are
  transparent over Aequitas quantities.
- ADR 0023: Harmonia coupling promotion — Proteus composes with
  integrator-owned physics while Harmonia composes coupling mechanics.
- `repos/proteus/docs/adr/0001-thermophysical-material-boundary.md`:
  canonical Proteus-side contract, dimensional algebra, and evidence
  limits.
