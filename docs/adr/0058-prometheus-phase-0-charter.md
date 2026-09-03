# ADR 0058: Prometheus Phase 0 — homogeneous reaction networks

- Status: Accepted
- Date: 2026-09-03
- Class: `[arch]` `[minor]`
- Relates to: [ADR 0055](0055-continuum-domain-decomposition.md),
  [ADR 0056](0056-new-construction-promotion-path.md)

## Context

The stack has no owner for species transformation. Kwavers carries competing
reaction representations and a bespoke embedded integrator; CFDrs has
manufactured reactive-flow oracles but no production reaction-network consumer.
Neither owns reaction kinetics as a reusable contract.

[ADR 0055](0055-continuum-domain-decomposition.md) fixes the scope: species
mass balance, with Proteus supplying temperature-dependent rate coefficients.
[ADR 0056](0056-new-construction-promotion-path.md) defines the path.

## Decision

Promote `prometheus` as the owner of species mass balance and reaction
kinetics, entering at Phase 0 with scope: **homogeneous reaction networks and
their zero-dimensional integration**.

Phase 0 is zero-dimensional on purpose. Reaction kinetics and reactive
*transport* are separable, and the network is the part that is duplicated and
reusable; the transport discretization belongs to whichever balance domain
carries the field. Shipping the network alone keeps the boundary against CFDrs
clean from the first commit.

### Phase 0 owns

- **Species.** Species identity, molar mass, and a validated concentration
  boundary over `aequitas::MolarConcentration`.
- **Stoichiometry.** Reactions as stoichiometric coefficients over a species
  set, with reactant and product sides distinguished, stored as a sparse
  stoichiometric matrix over Leto.
- **Rate laws.** Mass-action kinetics with arbitrary reaction order;
  equilibrium constants and reverse-rate consistency.
- **Rate coefficients.** Arrhenius `k(T) = A exp(-Ea / (R T))` expressed as a
  `proteus::TemperatureResponse`, per ADR 0055 R4. Prometheus assembles
  networks from coefficients; it does not own how a coefficient varies with
  temperature.
- **Net production.** `omega_i = sum_j nu_ij r_j`, the source term a transport
  equation consumes.
- **Reaction enthalpy.** Heat release per reaction, the coupling term a thermal
  balance consumes.
- **Zero-dimensional integration.** Batch and continuously-stirred reactors
  integrated through Horae's stepping policy, including a stiff path.

### Phase 0 does not own

Reactive-transport discretization, combustion closure and flame models,
turbulence-chemistry interaction, surface and heterogeneous reactions, plasma
chemistry, electrochemistry, phase equilibrium, transport properties.
Reactive-transport in particular stays with the balance domain that owns the
field: Prometheus supplies `omega_i` and CFDrs discretizes it.

Boundary against adjacent owners: Proteus owns rate-coefficient temperature
response and material properties; Horae owns integration policy and step
control; Harmonia owns coupling to thermal or flow balance; Tyche owns
parameter uncertainty over rate constants.

### Substrate

`aequitas` quantities, `eunomia` scalars, `leto` arrays for the stoichiometric
matrix, `proteus` rate coefficients, `horae` integration. Optional `moirai` for
independent-network parallelism, `tyche` downstream for kinetic-parameter
uncertainty. Prohibited: `nalgebra`, `ndarray`, `rayon`, `num-traits`. Generic
over `T: RealField`, tested at `f32` and `f64`.

## Gate evidence under ADR 0056

**Condition 1 — unowned, stated.** No provider owns reaction networks. Position
stated by ADR 0055.

**Condition 2 — product driver.** Sonodynamic and photodynamic therapy
modelling: reactive-oxygen-species generation and consumption kinetics coupled
to a delivered dose field. CFDrs already carries a closed-form
`sonosensitizer_activation_efficiency` metric, which is a single efficiency
expression rather than a species network — the driver is the network that
expression approximates.

**Condition 3 — first consumer.** Kwavers, for sonodynamic species kinetics
under an acoustic dose field, at the Harmonia boundary. CFDrs is the intended
second consumer, replacing its closed-form efficiency metric with a network
once Phase 0 exists; that replacement is the deletion ledger, arriving later.

**Condition 4 — vertical slice.** Phase 0 integrates a species vector forward
from an initial composition, a temperature, and a network. No mocks, no stubs.

**Condition 5 — analytical oracles.** Every one closed-form, a conservation
law, or a published benchmark:

| Oracle | Statement | Why it catches what it catches |
| --- | --- | --- |
| First-order decay | `A -> B` gives exactly `c_A(t) = c_A0 exp(-k t)` | Catches rate-law and integrator errors against a closed form |
| Second-order decay | `2A -> B` gives `1/c_A(t) = 1/c_A0 + 2 k t` | Catches reaction-order handling that first order cannot |
| Reversible equilibrium | `A <-> B` converges to `c_B / c_A = K_eq` | Catches reverse-rate and equilibrium-consistency errors |
| Element conservation | Total mass `sum_i M_i c_i` is invariant to integrator tolerance | A conservation identity independent of the network |
| Non-negativity | No species concentration goes negative for a physical network | Catches a stiff-integrator failure mode that tolerance checks miss |
| Arrhenius recovery | Fitting `ln k` against `1/T` recovers `Ea` and `A` | Catches coefficient plumbing through Proteus |
| Robertson problem | The published stiff benchmark, against reference values | Exercises the stiff path; a classic that non-stiff integrators visibly fail |
| Convergence order | Refinement recovers the integrator's declared order | Catches a step controller that is converging to the wrong thing |
| Scalar generality | Every oracle at `f32` and `f64` | Catches fake generics |

Tolerances derive from the integrator's declared order and the problem's
conditioning; stiff cases state their conditioning explicitly.

**Condition 6 — dependency direction.** Inward only, asserted by the
architecture test.

**Condition 7 — delivery unit.** As for Ares.

## Prerequisites

1. `aequitas` gains `ReactionRate` (mol·m⁻³·s⁻¹) and `MolarFlux`
   (mol·m⁻²·s⁻¹). Phase 0 types production rates from the first commit.
2. Horae's embedded stepping policy is consumer-ready. It is recorded as
   consumer-gated with no current caller; Prometheus is that caller, so this is
   an integration step rather than new Horae work.

The Kwavers reaction-vocabulary consolidation recorded as the historical
Prometheus prerequisite is **not** a blocker under the new-construction path.
It was required to produce a deletion ledger; under ADR 0056 that ledger
arrives with the consumer migration instead. Consolidating Kwavers's competing
representations remains worthwhile and proceeds on its own merits.

## Registry name

`prometheus` on crates.io is the widely used metrics client and is
unavailable. Registry name `prometheus-kinetics`, import path `prometheus` via
`[lib] name`. Availability verified before creation.

The collision is worth noting for a second reason: a stack crate importing as
`prometheus` alongside any observability tooling that uses the metrics client
would be confusing to a reader. The import path stays `prometheus` for
consistency with the stack's naming, and the registry name carries the
disambiguation.

## Later phases, not authorized here

Phase 1 reactive transport source coupling through Harmonia. Phase 2
heterogeneous and surface reactions. Phase 3 combustion closure. Each needs its
own charter and driver.

## Consequences

- The suite gains chemical kinetics, and reactive-flow and therapy-response
  couplings become expressible.
- CFDrs acquires a migration target for its closed-form efficiency metric.
- Prometheus becomes Horae's first embedded-stepping consumer, which retires a
  capability that has been consumer-gated with no caller.
- The risk is the same as for Ares: analytical oracles are the only safety net.
  The Robertson benchmark and the conservation and non-negativity invariants
  are included specifically because stiff kinetics fail in ways that a
  smooth-case tolerance check does not reveal.

## Non-goals

- Anything in the "does not own" list, transport discretization especially.
- A direct dependency on CFDrs or Kwavers.
- Owning temperature response, which is Proteus's.
