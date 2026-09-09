# ADR 0061: Balance members expose their closure vocabulary as its own crate

- Status: Proposed
- Date: 2026-09-09
- Relates to: [ADR 0055](0055-continuum-domain-decomposition.md) (R7 and the
  balance/closure axis), [ADR 0030](0030-hyperion-photon-optical-promotion.md)
- Board: [ATLAS-CLOSURE-SURFACE-SPLIT](../backlog.md#atlas-closure-surface-split)

## Context

ADR 0055 put every stack member on one axis — balance, closure, or coupling —
and R7 forbids a direct runtime dependency between two balance members, since
multi-balance coupling belongs to `harmonia`. The conformance scan enforces R7
at member granularity (`classify_member_edge`), with an intra-member exemption
because balance members are multi-crate workspaces.

That rule now reports `kwavers -> hyperion` and `kwavers -> asclepius` as
forbidden. Both edges arrived deliberately: `737ab04fb` retired
`kwavers-optics` for hyperion's spectra and `f00513e9c` migrated the optical
module, which is upstream ownership working exactly as intended — a local
duplicate deleted, the owning member consumed.

The rule and the migration cannot both be right as stated, so the question is
which surface actually crosses the boundary. Every import does:

```
hyperion::coefficient::{InteractionCoefficient, ReducedScattering,
                        hemoglobin_absorption, OXYHEMOGLOBIN, DEOXYHEMOGLOBIN}
hyperion::quantity::{OpticalDepth, PathLength}
hyperion::transport::{reduced_scattering, DiffusionCoefficients}
asclepius::{DamageIntegral, BiologicalResponse, Probability}
asclepius::response::thermal::{Cem43, ArrheniusDamage}
asclepius::response::composition::IndependentInsults
```

Every one is a coefficient, a quantity, or a pointwise response law. No solver,
no field, and no balance operator crosses either boundary — `reduced_scattering`
and `DiffusionCoefficients` are coefficient derivations (`mu_s' = mu_s (1 - g)`,
`D = 1 / (3 (mu_a + mu_s'))`), not a transport solve. ADR 0055's own R4 already
classifies this shape: "Arrhenius rate coefficients ... are
`proteus::TemperatureResponse` instances".

So the edges are closure consumption, which R7 permits (`closure_provider`), and
the rule misreads them because a member that owns a balance operator may also
own a closure vocabulary. Member granularity cannot tell the two apart.

## Decision

A balance member that owns a closure vocabulary publishes that vocabulary as its
own crate, and only that crate is registered as a closure package. The balance
operator stays in the member's balance crates, and R7 keeps forbidding direct
edges into those.

- `hyperion` splits its coefficient, quantity, and coefficient-derivation
  surface out of the crate that owns radiative transport.
- `asclepius` splits its response-law surface out of the crate that owns the
  biological-response balance.
- Consumers depend on the closure crate. `kwavers` retargets its seven
  manifests; no import path outside the split changes.
- `scripts/atlas_architecture_test.py` registers the two closure crates in
  `CLOSURE_DOMAINS`, and the conformance baseline regenerates in that change.

R7 is unchanged. What changes is that the stack states, in crate boundaries,
the distinction the rule already draws in its categories — so the check runs at
the granularity the manifests can express.

## Alternatives

**Route the edges through `harmonia`.** Rejected: `harmonia` owns multi-balance
coupling — interface transfer, relaxation, subcycling — and none of that is
what a coefficient lookup needs. Routing a pointwise absorption coefficient
through a coupling layer would put a transactional exchange in front of a pure
function, and `harmonia` would grow a passthrough surface per coefficient.

**Relax R7 to allow balance-to-balance edges.** Rejected: it discards the rule
that keeps two balance operators from advancing each other's fields directly,
which is the defect R7 exists to catch. The reported edges are not that defect;
the rule should keep catching the one that is.

**Classify the edge by consumed surface rather than by crate.** Rejected as the
enforcement mechanism: manifests carry crate names, not import paths, so the
scan would have to parse every consumer's `use` statements and stay correct
through re-exports. The crate split makes the same distinction checkable from
the dependency graph, which is where the rule already runs.

**Leave the classification and absorb the count into the baseline.** Rejected:
that records a permanent violation for edges this ADR finds correct, and the
ratchet stops meaning anything for the class.

## Consequences

- Two crate splits, one dependency retarget across seven `kwavers` manifests,
  and a scan registration — dependency-ordered, one member at a time.
- Each split is a `[minor]` publish surface change in its own member: the
  closure crate is new, and the balance crate loses the re-exports that moved.
- Until the splits land, the two `kwavers` edges stay on the conformance
  scan as open regressions rather than being absorbed, so the count states the
  work that remains.
- A future balance member with a closure vocabulary follows the same shape at
  registration, so R7 needs no further exception.

## Verification

- `scripts/atlas_architecture_test.py` fixture tests cover a closure-crate edge
  from a balance member (allowed) beside a balance-crate edge from the same
  member (forbidden), so the split is what the rule keys on.
- The conformance scan reports `balance_domain_edges` at zero for `kwavers`
  with no baseline increase.
- Each member's own suites and the consumer integration verification per the
  co-evolution protocol.
