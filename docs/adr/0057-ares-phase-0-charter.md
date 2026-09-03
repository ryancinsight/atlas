# ADR 0057: Ares Phase 0 — small-strain linear elastostatics

- Status: Accepted
- Date: 2026-09-03
- Class: `[arch]` `[minor]`
- Relates to: [ADR 0055](0055-continuum-domain-decomposition.md),
  [ADR 0056](0056-new-construction-promotion-path.md)

## Context

The stack has no owner for mechanical response of solids. Kwavers computes
elastic wave propagation, which is momentum balance in a solid, but owns it as
a wave-solver internal rather than as a reusable balance operator. CFDrs has
fluid-structure coupling hooks and no structural side to couple to.

[ADR 0055](0055-continuum-domain-decomposition.md) fixes what a solid-mechanics
package would own: momentum balance in solids, with Proteus supplying the
constitutive closure. [ADR 0056](0056-new-construction-promotion-path.md)
defines the path a new-construction candidate walks.

## Decision

Promote `ares` as the owner of solid momentum balance, entering at Phase 0 with
a deliberately narrow scope: **small-strain linear elastostatics on an
unstructured mesh**.

Phase 0 is narrow because the gate's condition 4 requires a complete vertical
slice rather than a broad scaffold. A package that ships strain measures,
stress assembly, boundary conditions, a solve, and an analytical verification —
and nothing else — is a smaller claim and a stronger one than a package that
ships module stubs across the whole of solid mechanics.

### Phase 0 owns

- **Kinematics.** Displacement-gradient and small-strain tensor
  `eps = (grad u + grad u^T) / 2`. Symmetric second-order tensor storage and
  invariants.
- **Stress.** Cauchy stress, its invariants, von Mises equivalent stress, and
  principal stresses.
- **Constitutive coupling.** Isotropic Hooke's law
  `sigma = lambda tr(eps) I + 2 mu eps`, consuming
  `proteus::elastic::IsotropicModuli` for `(lambda, mu)`. Ares stores no
  material constants and names no alloy, per ADR 0055 R2.
- **Balance.** Static equilibrium residual `div sigma + b = 0`.
- **Discretization.** Continuous-Galerkin finite elements on Gaia meshes,
  linear simplices in 2-D and 3-D, with isoparametric mapping and Gauss
  quadrature.
- **Boundary conditions.** Dirichlet (prescribed displacement) and Neumann
  (prescribed traction), applied as typed conditions rather than as raw index
  manipulation.
- **Assembly and solve.** Assembly to an Athena linear system and solution
  through Athena's existing PCG, backend-neutral over Leto and Hephaestus.

### Phase 0 does not own

Plasticity, viscoelasticity, hyperelasticity, finite deformation, contact and
friction, dynamics and modal analysis, fracture, fatigue, anisotropy,
composites, thermal expansion coupling, buckling. Each is a later phase or a
consumer concern, and none is scaffolded in Phase 0.

Boundary against adjacent owners, per ADR 0055: Proteus closes and Ares
balances; Gaia owns mesh, geometry, and proximity queries; Athena owns solver
policy; Horae owns time when dynamics arrive; Harmonia owns every coupling to
another balance domain, so Ares gains no CFDrs or Kwavers edge in any phase.

### Substrate

`aequitas` quantities, `eunomia` scalars, `leto` arrays, `proteus` closure,
`gaia` mesh, `athena` solve. Optional `moirai` for assembly parallelism,
`mnemosyne` for arena-backed element storage, `themis` for placement.
Prohibited: `nalgebra`, `ndarray`, `rayon`, `num-traits`. Generic over
`T: RealField` throughout, with tests instantiated at `f32` and `f64`.

## Gate evidence under ADR 0056

**Condition 1 — unowned, stated.** No provider owns solid momentum balance.
Position stated by ADR 0055.

**Condition 2 — product driver.** Fluid-structure interaction for flow devices:
CFDrs models the flow and has coupling hooks with nothing structural on the
other side. Vessel and device wall mechanics under pressure loading is the
named analysis.

**Condition 3 — first consumer.** CFDrs, at the Harmonia partition boundary.
The integration surface is a traction field in and a displacement field out,
exchanged as typed physical fields per
[ADR 0050](0050-typed-physical-field-exchange.md). Kwavers is the intended
second consumer, migrating its elastic-wave operators once Phase 1 adds
dynamics; that migration is the deletion ledger the consolidation path would
have required, arriving later rather than never.

**Condition 4 — vertical slice.** Phase 0 computes a displacement field from a
mesh, material, and boundary conditions. No mocks, no placeholder bodies, no
feature-gated stubs.

**Condition 5 — analytical oracles.** Every one is closed-form or a
conservation statement; none is a differential against existing code:

| Oracle | Statement | Why it catches what it catches |
| --- | --- | --- |
| Patch test | A constant-strain displacement field on an arbitrary distorted patch is reproduced to machine precision | The canonical FEM correctness test; fails on almost any assembly, mapping, or quadrature defect |
| Rigid-body motion | Translation and infinitesimal rotation produce exactly zero stress | Catches a strain measure that is not frame-invariant |
| Thick-walled cylinder | Lame closed-form radial and hoop stress under internal pressure | Catches constitutive and axisymmetric boundary errors |
| Cantilever tip deflection | `delta = P L^3 / (3 E I)` in the slender limit, approached from the known FEM direction | End-to-end sanity against an independent structural theory |
| Convergence order | h-refinement recovers `O(h^2)` in the L2 displacement norm for linear elements | Catches defects that leave a solve plausible but not converging |
| Manufactured solution | MMS body force recovers a prescribed analytical displacement field | Independent of any special geometry |
| Energy consistency | Strain energy equals external work for a linear elastic static solve | A conservation identity, independent of the discretization |
| Scalar generality | Every oracle runs at `f32` and `f64` | Catches fake generics per the integrity rules |

Tolerances derive from conditioning and discretization error, never tuned.
The patch test and rigid-body oracles are exact to machine precision and are
asserted as such.

**Condition 6 — dependency direction.** `ares` depends only inward on
foundation, compute, and domain layers. Asserted by the architecture test.

**Condition 7 — delivery unit.** `.gitmodules`, stack table, naming table,
roadmap, dependency order, and the architecture test move together.

## Prerequisites

1. The Proteus elastic consolidation completes its consumer deletions. Ares
   consumes `IsotropicModuli`; shipping while CFDrs and Kwavers still hold
   private copies would create a third owner rather than resolve two.
2. `aequitas` gains a stress semantics marker, so Cauchy stress does not
   silently unify with hydrostatic pressure or an elastic modulus. Phase 0
   types stress from the first commit; retrofitting a semantics marker after a
   public API exists is a breaking change.

Neither is Ares work, and both are already on the board.

## Registry name

`ares` is unavailable on crates.io. Registry name `ares-solid`, import path
`ares` via `[lib] name`, following `proteus-mat` and `gaia-mesh`. Availability
is verified before the repository is created.

## Later phases, not authorized here

Phase 1 dynamics and modal analysis, over Horae. Phase 2 finite deformation and
hyperelasticity, with Proteus supplying the strain-energy density. Phase 3
plasticity and damage, with Proteus owning the internal-variable evolution per
ADR 0055 R3. Phase 4 contact, with Gaia supplying proximity. Each requires its
own charter and is gated on its own driver.

## Consequences

- The suite gains solid mechanics, and thermo-mechanical and fluid-structure
  couplings become expressible through Harmonia.
- Kwavers acquires a migration target for its elastic-wave operators, deferred
  to Phase 1 so Phase 0 does not block on it.
- The risk is that Phase 0's analytical oracles are the only safety net, since
  no reference implementation exists to difference against. The oracle table is
  deliberately broad for that reason, and the patch test plus rigid-body checks
  are exact rather than tolerance-bounded.

## Non-goals

- Any capability in the "does not own" list.
- A direct dependency between Ares and any integrator or other balance domain.
- Storing material constants in Ares.
