# ADR 0061: Hyperion and Asclepius are closure domains

- Status: Accepted
- Date: 2026-09-09
- Relates to: [ADR 0055](0055-continuum-domain-decomposition.md) (R7 and the
  balance/closure axis), [ADR 0030](0030-hyperion-photon-optical-promotion.md)
- Board: [ATLAS-CLOSURE-SURFACE-SPLIT](../../backlog.md#atlas-closure-surface-split)

## Context

ADR 0055 put every stack member on one axis — balance, closure, or coupling —
and R7 forbids a direct runtime dependency between two balance members, since
multi-balance coupling belongs to `harmonia`. The conformance scan enforces R7
at member granularity.

That rule reported `kwavers -> hyperion` and `kwavers -> asclepius` as
forbidden. Both edges arrived deliberately: `737ab04fb` retired
`kwavers-optics` for hyperion's spectra and `f00513e9c` migrated the optical
module, which is upstream ownership working as intended — a local duplicate
deleted, the owning member consumed.

ADR 0055 assigned hyperion and asclepius to the balance axis by subject matter,
"`helios` and `hyperion` for radiative transport, and `asclepius` for
biological response". A balance domain is one that owns a *balance operator* —
something that advances a conserved quantity over a field. Reading the two
surfaces shows neither does.

`hyperion` is a single crate whose whole public surface is closed-form and
pointwise: `transport::beer_lambert` gives `optical_depth`,
`half_value_layer`, `penetration_depth` and `planar_fluence_at_depth`;
`transport::deposition` gives `absorbed_power_density` and
`absorbed_energy_density` from a fluence and an absorption coefficient;
`transport::diffusion` derives `OpticalDiffusionCoefficient` and
`DiffusionCoefficients`. There is no field, no grid, no solve, and no state
advance anywhere in it — the README's own ownership row says as much, leaving
"spatial solvers, dose, acoustics" to their existing owners.

`asclepius` is response laws over a sample series — `ArrheniusDamage`, `Cem43`,
`GeneralizedEquivalentUniformDose`, `LymanComplicationProbability`,
`DamageIntegral` — plus a tissue vocabulary. ADR 0055's own R3 assigns exactly
that shape to closure: a rate law integrated pointwise is a closure, and its
storage and transport belong to the caller.

Every symbol `kwavers` imports from either is a coefficient, a quantity, or a
pointwise response law. Nothing that crosses those boundaries is a balance
operator.

## Decision

`hyperion` and `asclepius` are closure domains. They move out of
`MEMBER_BALANCE_DOMAINS` and into `CLOSURE_DOMAINS` in
`scripts/atlas_architecture_test.py`, so an integrator consuming them
classifies as `closure_provider` — which R7 already permits — and two balance
members still may not depend on each other.

Membership is decided by reading the public surface for a balance operator, not
by subject matter. Radiative transport is a balance when something advances a
radiance field; a Beer-Lambert attenuation and a diffusion-coefficient
derivation are closures that such a solver would consume. `helios` keeps its
balance registration on that test; hyperion does not meet it.

R7 is unchanged, and so is the rule it enforces.

## Alternatives

**Split each member's closure vocabulary into its own crate and register that.**
This ADR recommended exactly that before its surfaces were read, on the
assumption that each member owned both a balance operator and a closure
vocabulary. Reading them removed the premise: there is no balance operator to
separate the vocabulary from, so the split would have produced a crate boundary
with nothing on the far side of it, two `[minor]` publish surfaces, and a
dependency retarget across seven manifests to reach the same classification a
one-line registration reaches.

**Route the edges through `harmonia`.** Rejected: `harmonia` owns multi-balance
coupling — interface transfer, relaxation, subcycling — and a coefficient
lookup is none of those. It would put a transactional exchange in front of a
pure function and grow `harmonia` a passthrough surface per coefficient.

**Relax R7 to allow balance-to-balance edges.** Rejected: that discards the
rule that keeps two balance operators from advancing each other's fields
directly, which is the defect R7 exists to catch.

**Absorb the count into the baseline.** Rejected: it records a permanent
violation for edges this ADR finds correct, and the ratchet stops meaning
anything for the class.

## Consequences

- `kwavers/balance_domain_edges` returns to zero with no baseline change.
- A member that later grows a balance operator moves back, and the test that
  decides is the same one: does its public surface advance a field?
- ADR 0055's continuum-domain narrative keeps its axis; what changes is that
  membership is read from the surface rather than assigned by subject, which
  is recorded there as a revision note.
- `helios` remains a balance member and is not re-examined here; its
  registration rests on owning a transport solve, which this ADR does not test.

## Verification

- `scripts/tests/test_atlas_architecture_test.py` covers the decided edges:
  `kwavers-physics -> hyperion` and `-> asclepius` classify as non-violations,
  while `cfd-3d -> kwavers-physics` still trips the rule. 49 tests pass.
- `atlas-conformance.py check --repo kwavers` reports no
  `balance_domain_edges` regression.
