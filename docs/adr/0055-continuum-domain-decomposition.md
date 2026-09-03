# ADR 0055: Continuum domain decomposition for Proteus, Ares, and Prometheus

- Status: Accepted
- Date: 2026-09-03
- Class: `[arch]`
- Relates to: [ADR 0030](0030-hyperion-photon-optical-promotion.md),
  [ADR 0032](0032-modality-transport-and-therapy-boundaries.md),
  [ADR 0050](0050-typed-physical-field-exchange.md)

## Context

Atlas targets a general multiphysics simulation suite. The current stack covers
fluid flow, acoustics, radiation transport, optical interaction, biological
response, geometry, solvers, time integration, coupling, and uncertainty. Two
continuum domains are absent: mechanical response of solids and species
transformation.

Two provisional names have carried those roles since the P2 decision: `ares`
for solid mechanics and `prometheus` for reaction networks. Both are deferred
with unmet promotion gates.

The names were assigned without a stated design axis. The stack map recorded
why each was deferred and one sentence of eventual scope, but not the rule that
separates the three material-adjacent packages from one another. That omission
has a measured cost: an external review of the stack proposed creating
`prometheus` as the structural-mechanics package, inverting the recorded
assignment and citing the roadmap itself as confirmation. A boundary that can
be read backwards from its own documentation is underspecified.

Proteus compounds the ambiguity. It owns "material properties and constitutive
response", which reads as though it could own stress-strain response — the
thing `ares` is reserved for. Nothing recorded says where the material's
response function ends and the solid's balance equation begins.

## Decision

Adopt one decomposition axis for every continuum domain in the suite:

> A continuum domain is a **conserved quantity**, its **balance operator**, and
> the **constitutive closure** that makes the balance well-posed. Closure is a
> pointwise material property. Balance is a field operator. They are owned by
> different packages.

This yields the three roles without residual overlap:

| Package | Layer | Conserved quantity | Owns |
| --- | --- | --- | --- |
| `proteus` | Closure | none | Pointwise material response: property validity, constitutive contracts, and the response functions that close a balance law. |
| `ares` | Balance | Linear and angular momentum in solids | Solid kinematics, stress divergence, equilibrium, contact and constraint enforcement, failure and fatigue measures. |
| `prometheus` | Balance | Species mass | Reaction networks, stoichiometry, rate-law assembly, reaction source and enthalpy terms. |

`CFDrs` already occupies the same axis for fluid momentum and mass, `kwavers`
for acoustic momentum, `helios` and `hyperion` for radiative transport, and
`asclepius` for biological response. `harmonia` couples balance domains and
owns no physics.

The classical mappings hold under this axis rather than merely decorating it:

- **Proteus**, who changes form under conditions and answers truthfully when
  held, is the material's response function — what it becomes under a given
  local state.
- **Ares**, god of force and violence, owns stress, deformation, contact, and
  failure.
- **Prometheus**, who brought fire and shaped matter with forethought, owns
  combustion and reaction kinetics — transformation of one species into
  another, predicted ahead of time.

### Boundary rules

Each rule is mechanically checkable, so a violation fails review rather than
inviting argument.

- **R1 — Proteus is field-free.** No `proteus` public signature names a `leto`
  array, a `gaia` mesh, a field, an index, or a grid. Inputs and outputs are
  `aequitas` quantities and the `ConstitutiveLaw::State<'a>` associated type.
  A material law that needs a neighbour value is not a closure and does not
  belong here.
- **R2 — Balance owners name no concrete material.** `ares` and `prometheus`
  bind `L: ConstitutiveLaw<T>` and monomorphize. A hardcoded modulus, rate
  constant, or named alloy inside a balance operator is a defect.
- **R3 — Internal state variables split by role.** The *evolution law* for a
  history variable (plastic strain, damage, degree of cure, species fraction)
  is a pointwise ODE and belongs to Proteus. Its *storage, transport, and
  parallel update across the field* belong to the balance owner. This is the
  seam Proteus's GAT `State<'a>` already exists to carry.
- **R4 — Temperature dependence is Proteus.** Arrhenius rate coefficients,
  temperature-dependent moduli, and thermal softening are
  `proteus::TemperatureResponse` instances, not per-domain reimplementations.
  Prometheus assembles networks from coefficients; it does not own how a
  coefficient varies with temperature.
- **R5 — Kinematics belong to the owner of the primal field.** Deformation
  gradient, strain measures, and rate-of-deformation derive from displacement,
  so they are `ares`. Concentration gradients and diffusive fluxes derive from
  composition, so they are `prometheus`.
- **R6 — Contact splits at geometry.** Proximity queries, surface
  representation, and intersection are `gaia`. Constraint formulation,
  enforcement, and friction law are `ares`.
- **R7 — No direct balance-to-balance edge.** Thermo-mechanical,
  fluid-structure, and reactive-flow coupling route through `harmonia`. An
  `ares` dependency on `CFDrs`, or the reverse, is an architecture defect.

### Substrate contract

All three packages consume the first-party stack and add no third-party
equivalent of a capability the stack already owns. Specifically prohibited in
these packages: `nalgebra`, `ndarray`, `rayon`, `num-traits`, and any parallel,
array, allocation, or scalar-trait crate duplicating a stack provider.

| Concern | Provider |
| --- | --- |
| Scalar vocabulary, generic numeric traits | `eunomia` |
| Physical quantities, dimensions, units | `aequitas` |
| Host arrays, layouts, views, linear algebra | `leto` |
| Accelerator devices, buffers, kernels | `hephaestus` |
| Parallel iteration, scheduling, async | `moirai` |
| Allocation, arenas, staging memory | `mnemosyne` |
| NUMA placement and locality | `themis` |
| Branded capability evidence | `melinoe` |
| Linear solvers | `athena` |
| Time integration and subcycling | `horae` |
| Geometry, topology, meshes | `gaia` |
| Cross-domain coupling | `harmonia` |
| Sensitivity, adjoints, optimization | `coeus` |
| Uncertainty and ensembles | `tyche` |
| Persistence | `consus` |
| Diagnostic views | `iris` |

### Typed physics

Every physical value crossing a public boundary in these packages is an
`aequitas` quantity, never a raw scalar. Where a dimension is shared by
physically distinct concepts, the quantity carries a semantics marker so the
type system separates them — the mechanism `aequitas` already uses for
`AbsoluteTemperature` against `TemperatureDifference`, and for
`SpringStiffness`, `FlexuralRigidity`, `MechanicalImpedance`, and
`SurfaceTension`, which share dimensions with unrelated quantities.

| Quantity | Dimension | Status |
| --- | --- | --- |
| Young's modulus, Lame parameters, bulk modulus | `Pressure` | present, in use by `proteus::elastic` |
| Strain, Poisson's ratio | `Dimensionless` | present |
| Displacement | `Length` | present |
| Force, traction resultant | `Force` | present |
| Strain-energy density | `EnergyPerVolume` | present |
| Species concentration | `MolarConcentration` | present, already carries a semantics marker |
| Activation energy | `MolarEnergy` | present |
| Cauchy stress | `Pressure` dimension | **to add**: a stress semantics marker, so stress does not silently unify with hydrostatic pressure or with elastic moduli |
| Reaction rate | mol·m⁻³·s⁻¹ | **to add** |
| Molar flux | mol·m⁻²·s⁻¹ | **to add** |

The three additions land upstream in `aequitas` under upstream ownership, not
locally in a consumer, and are prerequisites of the corresponding promotion —
not work the new package performs on itself.

## Promotion triggers

This ADR changes no gate. The gate in the stack map stands: two production
consumers, a named deletion ledger, and a net-deletion result. What changes is
that each candidate now has a concrete, checkable trigger rather than a
narrative one.

| Candidate | Trigger | Prerequisite state |
| --- | --- | --- |
| `ares` | A second integrator consumes the same solid-kinematics or momentum-balance operator, and both can delete a matching implementation. | Proteus elastic SSOT merged (`proteus` `1726082`); consumer deletion slices in `CFDrs` and `kwavers` outstanding. |
| `prometheus` | A second production reaction-network consumer can delete a matching implementation. | Kwavers converges on one reaction/species representation; `horae` owns the reusable embedded integration policy. Neither started. |

Kwavers is the only current owner of solid-mechanics operators, so `ares` has
one consumer, not two. The honest reading is that `ares` is one CFDrs
structural slice away from its trigger and `prometheus` is further out.

## Suite coverage

Recording the target explicitly, so gaps are tracked rather than rediscovered.

| Capability | Owner | State |
| --- | --- | --- |
| Fluid flow, turbulence, multiphase | `CFDrs` | present |
| Heat transfer | `CFDrs`, `asclepius` (bioheat) | present |
| Acoustics and ultrasound | `kwavers` | present |
| Radiation transport and dose | `helios`, `hyperion` | present |
| Optical interaction | `hyperion` | present |
| Biological response | `asclepius` | present |
| Geometry, meshing, NURBS, topology | `gaia` | present |
| Linear solvers | `athena` | present |
| Time integration | `horae` | present |
| Multiphysics coupling | `harmonia` | present |
| Uncertainty, sensitivity, optimization | `tyche`, `coeus` | present |
| **Solid mechanics** | `ares` | **absent — gated** |
| **Chemical species and reactions** | `prometheus` | **absent — gated** |
| **Electromagnetics beyond optical** | none | **absent — no candidate** |
| **Parametric solid modelling (MCAD)** | none | **absent — separate product line** |

### Electromagnetics

`hyperion` owns photon and optical *interaction coefficients*, not field PDEs.
Electrostatics, magnetostatics, induction heating, and full-wave propagation
are a field-balance domain on the same axis as `ares` and `prometheus`, and are
a different bounded context from interaction coefficients. Provisional name:
`astrape`, the personification of lightning. No promotion follows from this
ADR: there is currently no consumer, so the candidate does not even reach the
first gate condition. It is recorded so the next audit does not attempt to
widen `hyperion` into it.

### Parametric solid modelling

COMSOL-class analysis and SolidWorks/Inventor-class authoring are different
product lines. The suite reaches the first without an MCAD kernel, by importing
geometry. Recording the honest position:

`gaia` already owns more of the foundation than a survey suggests — NURBS basis
functions, curves, knot vectors, surfaces, and tessellation, plus half-edge
topology, manifold predicates, orientation, and adjacency, over `leto`,
`eunomia`, and `aequitas` with optional `mnemosyne` and `moirai`. That is the
curve/surface and topology half of a boundary-representation kernel.

What is genuinely absent is the authoring half: trimmed faces, shells and
solids, boolean operations on B-rep solids, a sketch constraint solver, a
feature history tree, assembly mates, and drawing generation. This is a large
body of work whose scale should not be understated — an established kernel of
this class is a multi-year effort, not a package extraction.

Provisional name `daedalus`, the archetypal craftsman and designer. It is not a
roadmap candidate under the current gate, because the gate requires extracting
duplicated code from two existing consumers and no consumer implements
parametric modelling today. If this line is pursued it starts as a `gaia`
extension for solid B-rep and booleans — where the existing NURBS and half-edge
foundation lives — and separates only if the constraint and feature layers
outgrow it. That ordering keeps the geometry kernel single-owner and defers the
naming decision until there is code to name.

## Consequences

- No repository is created by this ADR. `.gitmodules` and the package count are
  unchanged.
- The stack map gains a decomposition axis, so the next review that proposes a
  structural-mechanics package has a stated rule to check its proposal against
  rather than a name table to misread.
- Proteus's boundary narrows explicitly: it is a closure layer and gains no
  balance operators, which retroactively justifies keeping the elastic slice to
  moduli conversion and a catalog while leaving grid traits with `kwavers`.
- Three `aequitas` additions become prerequisites of `ares` and `prometheus`
  rather than discoveries made during their implementation.
- The MCAD position is recorded as a separate product line, so the suite goal
  does not silently expand the multiphysics roadmap into a CAD kernel.

## Non-goals

- Promoting `ares`, `prometheus`, `astrape`, or `daedalus`.
- Changing the promotion gate conditions.
- Moving any operator out of `kwavers` or `CFDrs` before its consumer slice
  runs.
- Widening `hyperion` into general electromagnetics, which
  [ADR 0032](0032-modality-transport-and-therapy-boundaries.md) already
  declined.

## Verification

The boundary rules are checkable, and the checks are the acceptance oracle for
any future promotion:

- R1 by grep: no `leto`, `gaia`, or field type in a `proteus` public signature.
- R2 by grep: no numeric material constant inside an `ares` or `prometheus`
  operator module.
- R7 by the committed architecture test over `cargo metadata`, which already
  asserts the allowed edge set: an `ares` to `CFDrs` edge fails the build.
- Substrate contract by `cargo deny bans` on the prohibited crate list.
