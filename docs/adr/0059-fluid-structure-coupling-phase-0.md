# ADR 0059: Fluid-structure coupling, Phase 0 — one-way traction loading

- Status: Proposed
- Date: 2026-09-03
- Class: `[arch]`
- Relates to: [ADR 0050](0050-typed-physical-field-exchange.md),
  [ADR 0055](0055-continuum-domain-decomposition.md),
  [ADR 0057](0057-ares-phase-0-charter.md)

## Context

[ADR 0057](0057-ares-phase-0-charter.md) charters `ares` with fluid-structure
interaction as its product driver, and A8 as its first-consumer integration.
That charter's evidence has since been corrected: CFDrs has **no** FSI
machinery, so both halves of the coupling are new construction rather than a
connection to existing hooks. This ADR specifies the coupling before either
half is built, because the ownership split decides what Ares Phase 0 must
expose and what CFDrs must grow.

Three facts from the current stack constrain the design more than any
preference does.

**Harmonia does not interpolate.** Its `Transfer` implementations are
`IdentityTransfer` and `IndexTransfer` — index-shaped, no interpolation
anywhere — and [ADR 0050](0050-typed-physical-field-exchange.md) states
plainly that Harmonia "does not convert units, interpolate nonmatching meshes,
or add solver source terms". Non-conforming interface meshes are the normal
case in FSI, so this is the binding constraint, not a detail.

**Harmonia's coupling driver is untyped; its field exchange is typed.**
`Partition<T>` advances and exports through flat `&[T]` slices, while
`FieldEnvelope<'a, T, D, RANK>` carries `aequitas::Quantity<T, D>` values with
validated geometry and a `horae::Instant`. The dimension lives in the envelope
type, not in the driver.

**CFDrs cannot move its mesh.** There is no ALE, mesh-motion, or
moving-boundary path anywhere in it. Two-way FSI requires deforming the fluid
domain in response to structural displacement, so two-way coupling is not
reachable from the current CFDrs without building that first.

Kwavers supplies the physics reference: its `multiphysics/fluid_structure`
module states traction balance `t_s = -p_f n + tau_f . n`, pressure continuity,
velocity continuity, and an interface energy-conservation theorem. It solves a
different problem — acoustic-elastic coupling against a stress field its
elastodynamic solver already produces — but the interface conditions are the
same physics and are reused as the specification here.

## Decision

Phase 0 couples **one way, fluid to solid, quasi-statically**: the flow solve
produces an interface traction, the structural solve consumes it as a Neumann
condition and produces displacement and stress. The structural response does
not feed back into the fluid domain.

This is not a simplification of the target; it is the honest reachable scope.
Feedback requires moving the fluid mesh, CFDrs has no mechanism to do so, and a
"two-way" coupling that silently ignores the displacement it computes would be
a mock of the thing it claims to be. One-way loading answers the named driver —
vessel and device wall mechanics under pressure loading — completely, and it is
the standard first step for a low-deformation regime where the fluid domain is
substantially unchanged by the structural response.

### Ownership

| Concern | Owner | Rationale |
| --- | --- | --- |
| Interface traction from the flow state, `t = -p n + tau . n` | `CFDrs` | Reads its own pressure and viscous stress; the fluid state is its own (ADR 0050: providers stay owners of solver state) |
| Structural solve under that traction | `ares` | Momentum balance in solids (ADR 0055) |
| Constitutive closure | `proteus` | Closure layer; `ares` names no material (ADR 0055 R2) |
| Interface geometry, facet topology, normals, node correspondence | `gaia` | Geometry and topology owner |
| Partition driving, transfer, relaxation, subcycling | `harmonia` | Coupling mechanics owner; owns no physics |
| Linear solve | `athena` | Solver policy |

No direct `ares` to `CFDrs` edge in either direction, per ADR 0055 R7. Both
depend inward on Harmonia and Gaia; neither depends on the other.

### Conforming interface, stated as a precondition

Phase 0 requires the fluid and solid interface discretizations to **conform**:
one-to-one node correspondence across the interface, so transfer is an index
permutation that `IndexTransfer` already expresses.

This is a real restriction and it is recorded rather than hidden. The
alternative — a projection or mortar transfer for non-conforming meshes — is a
genuine body of work with its own conservation properties to prove, and it
belongs to whoever owns interpolation. Nobody does today. Inventing it inside
`ares` would put mesh interpolation in a balance package, which ADR 0055
forbids; inventing it inside Harmonia would contradict ADR 0050's explicit
scope.

The precondition is **asserted, not assumed**: constructing the coupling
validates node correspondence against the Gaia interface description and
returns a typed error when it does not hold. A silent mismatch would produce a
plausible, wrong answer, which is the failure mode this whole design exists to
avoid.

### Typed exchange, and where the typing stops

Fields cross the domain boundary as `FieldEnvelope`:

| Field | Direction | Dimension |
| --- | --- | --- |
| Interface traction | CFDrs to `ares` | `Stress` — the semantics-marked variant, so a traction cannot be filled from a hydrostatic pressure or an elastic modulus |
| Interface displacement | `ares` to CFDrs | `Length` |
| Interface stress (diagnostic) | `ares` out | `Stress` |

The traction dimension depends on the `aequitas` stress semantics marker,
which is a prerequisite, not part of this work
([aequitas #50](https://github.com/ryancinsight/aequitas/pull/50)). Phase 0
must not ship with traction typed as bare `Pressure`: that is precisely the
confusion the marker exists to prevent, and retrofitting it after the coupling
API exists is a breaking change.

Inside Harmonia's driver the values are flat `&[T]`, because `Partition` is
defined that way. The typing therefore holds at the envelope boundary and each
partition marshals to and from the flat slice. That marshalling carries a
stated ordering contract — interface node index major, component minor — and it
is verified, not assumed: a round trip through `export` and `advance` must
reproduce the envelope it came from.

### What Ares Phase 0 must expose for this

Only two things beyond its charter, and both are already implied by it: the
ability to apply a per-facet Neumann traction as a boundary condition, and the
ability to report interface displacement. No new physics.

## Non-goals

- **Two-way coupling.** Requires fluid mesh motion; CFDrs has none.
- **ALE or moving-boundary formulations** in CFDrs.
- **Non-conforming interface transfer**, projection, or mortar methods.
- **Dynamics.** Phase 0 of `ares` is static, so velocity continuity does not
  apply and no interface time-derivative condition is imposed. The kwavers
  reference states it for the dynamic case; it enters when Ares Phase 1 does.
- **Contact** between structural surfaces.
- **Migrating the kwavers acoustic-elastic FSI.** Different problem, its own
  solver, unchanged by this.

## Verification

The coupling's correctness claim is a conservation statement, so the oracles
are conservation identities and closed forms, per the
[ADR 0056](0056-new-construction-promotion-path.md) new-construction rule.

| Oracle | Statement |
| --- | --- |
| Interface work balance | Work done by interface traction, `integral of t . u` over the interface, equals the strain energy of the structural solve. A conservation identity independent of either discretization |
| Thick-walled cylinder under fluid pressure | A uniform interface pressure recovers the Lame closed-form wall displacement, coupling the flow-side traction extraction to the structural solve end to end |
| Traction extraction | Against an analytical pressure and viscous stress field, extracted traction matches `-p n + tau . n` per facet to machine precision, independent of any structural solve |
| Zero-traction null case | A zero interface traction produces exactly zero displacement, so the coupling adds no spurious loading |
| Rigid-body invariance | Translating the whole coupled configuration leaves interface work and structural stress unchanged |
| Marshalling round trip | `export` then `advance` reproduces the source envelope exactly, so the ordering contract holds |
| Conformity rejection | A deliberately non-conforming interface is rejected with a typed error rather than silently transferred |
| Scalar generality | Every oracle at `f32` and `f64` |

## Consequences

- The named driver is answered: wall mechanics under pressure loading is
  computable end to end once Ares Phase 0 and this coupling exist.
- Ares gains its first consumer without acquiring a CFDrs dependency, so the
  ADR 0055 balance-to-balance prohibition holds under a real integration rather
  than only in principle.
- The conforming-interface precondition will eventually bind and will need
  someone to own interpolation. Recording it now means that decision is taken
  deliberately, with a named owner, rather than discovered when a user meshes
  the two sides independently.
- CFDrs gains a traction-extraction surface it does not have, which is
  independently useful: interface traction is a reportable quantity whether or
  not a structural solve consumes it.

## Alternatives considered

1. **Two-way coupling in Phase 0.** Rejected: requires ALE in CFDrs, which does
   not exist. Building it as part of a first integration would make the first
   integration the largest one.
2. **Interpolating transfer in Harmonia.** Rejected: contradicts ADR 0050's
   stated scope, and a conservative interpolation scheme is its own ADR with
   its own conservation proofs.
3. **Ares owning interface interpolation.** Rejected: puts mesh interpolation
   inside a balance package, which ADR 0055 R6 assigns to geometry.
4. **A direct CFDrs-to-Ares call, skipping Harmonia.** Rejected by ADR 0055 R7.
   It would also duplicate the relaxation and subcycling Harmonia already owns,
   which is what the coupling package exists for.
5. **Reusing the kwavers FSI module.** Rejected: it couples an acoustic fluid to
   an elastodynamic solid through ghost cells on a shared grid, and consumes a
   stress field rather than computing one. Different problem, different
   discretization. It remains the specification reference for the interface
   conditions.
