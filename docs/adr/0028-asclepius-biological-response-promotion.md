# ADR 0028: Promote Asclepius biological-response law

- Status: Accepted
- Date: 2026-07-20
- Class: `[arch]` `[minor]`

## Context

Helios and Kwavers independently implemented biological-response laws that
belong neither to radiation transport nor acoustic propagation. Helios owned
generalized equivalent uniform dose (gEUD), logistic tumour-control
probability (TCP), Lyman normal-tissue complication probability (NTCP), and a
second gEUD expression on its Coeus autodiff tape. Kwavers owned repeated CEM43
thermal-exposure formulas, two Arrhenius damage implementations, and
independent-insult composition.

The duplicated formulas carried different validation, unit, allocation, and
error contracts. Aequitas already owns the physical quantities, Eunomia owns
the scalar law, and Coeus owns autodiff. No current provider owned the
biological-response equations that compose those foundations.

## Decision

Promote public package `asclepius` as the Atlas owner for shared
biological-response and treatment-outcome laws. P1 contains two crates:

- `asclepius`: a `no_std + alloc` law core over Aequitas quantities and
  Eunomia `RealField` scalars;
- `asclepius-coeus`: the outward Coeus adapter for differentiable gEUD graph
  construction.

The core owns typed probability, damage, exposure, and response parameters;
gEUD, logistic TCP, Lyman NTCP, CEM43, first-order Arrhenius damage,
independent-insult composition, and tissue/model composition. It does not own
dose-volume histograms, treatment objectives, tissue catalogs, voxel grids,
images, material properties, transport solvers, persistence, or device
execution.

`BiologicalResponse<T>` uses a generic associated observation type so models
borrow inputs without cloning. `UniformTemperatureObservation<T>` exposes a
sealed generic associated exact-size iterator, and `TemperatureSamples<I, T>`
carries arbitrary iterator pipelines without materializing a history.
Thermal cumulative methods consume each observation once and write to
caller-owned slices. `IndependentInsults<const N: usize>` is a const-generic
zero-sized policy. `Tissue<'name, Model>` uses `Cow<'name, str>` so static
catalogs borrow names and runtime definitions own them through one API. All
model and adapter dispatch is generic and monomorphized; no vtable, precision
widening, hidden allocation, or compatibility wrapper participates in
evaluation.

### Dependency direction

```text
asclepius ──> aequitas ──> eunomia
          └─> eunomia

asclepius-coeus ──> asclepius
                 └─> coeus

helios  ──> asclepius + asclepius-coeus
kwavers ──> asclepius
```

The law core has no dependency on Coeus or an integrator. The adapter depends
outward on both law and autodiff providers. Consumers retain their domain
state and select concrete laws at the operation boundary.

## Theorems and proof obligations

Asclepius ADR 0001 and the law Rustdoc own the complete mathematical
specification. Atlas records the cross-package obligations:

### Generalized-mean bounds and homogeneity

For positive doses and finite `a != 0`, the generalized-mean inequality gives
`min(D) <= M_a(D) <= max(D)`. For `c >= 0`,
`M_a(cD) = c M_a(D)` by factoring `c^a` from the sum. These facts justify a
detached positive normalization scale in the Coeus graph: the normalized
forward value is identical and its analytical gradient remains the gEUD
gradient because the scale is algebraically absent from the represented
function.

### Probability range and monotonicity

The logistic TCP denominator is at least one. At its midpoint dose the ratio
term is one, hence `TCP = 1/2`; its derivative is positive for positive dose
and parameters. Lyman NTCP composes an affine standardized dose with the
monotone standard-normal CDF, so it is monotone and equals `1/2` at its
midpoint.

### Thermal accumulation and survival

Arrhenius rate `A exp(-E_a/(R T))` is positive for valid positive parameters
and absolute temperature. CEM43 has a positive timestep and positive
temperature factor. Their cumulative rectangle sums are therefore
non-negative and non-decreasing.

The first-order survival equation `dS/dt = -k(t)S` separates and integrates to
`S(t)/S(0) = exp(-Omega)`, giving kill probability
`1 - exp(-Omega)`.

For a fixed step and an identical ordered temperature sequence, borrowed and
streamed observations feed the same recurrence with the same initial state.
Induction on the sample index therefore gives bitwise-identical cumulative
states when the iterator yields the same scalar representation and order.

### Independent response composition

For `p_i in [0,1]`, every survival factor `1 - p_i` lies in `[0,1]`.
Therefore `1 - product(1 - p_i)` also lies in `[0,1]`; its partial derivative
with respect to each `p_j` is the non-negative product of all remaining
survival factors.

The proofs establish the mathematical contracts. Executable property,
analytical-oracle, differential, representation, and allocation tests establish
the implementation evidence; neither evidence category substitutes for the
other.

## Migration

1. Add the Aequitas response quantities and coherent units.
2. Publish the Asclepius core and its executable theorem suites.
3. Publish the Coeus adapter and verify values and closed-form gradients.
4. Add streamed exact-size thermal observations and caller-owned cumulative
   output without an intermediate collection.
5. Replace Helios response laws and autodiff reconstruction; delete the local
   duplicates.
6. Replace Kwavers CEM43, Arrhenius, and independent-insult formulas while
   retaining its grids, workflows, and tissue catalogs.
7. Register the exact remote-default Asclepius gitlink in Atlas and verify the
   consumer graph through the Atlas-owned checkout action.

Every consumer slice migrates callers and deletes superseded computation.
No forwarding wrapper, local adapter, or fallback implementation remains.

## Evidence

Atlas pins Asclepius merge object
`ceb8b6d9e0f119181258a27ae4888aa099b64d99`. That revision contains the law
core and Coeus adapter and passed format, workspace and `no_std` checks,
warning-denied Clippy, Nextest, doctests, warning-denied rustdoc, examples,
and cargo-deny. Its tests cover `f32` and `f64`; generalized-mean bounds and
homogeneity; TCP/NTCP midpoint and monotonicity; published CEM43 reference
cases; Arrhenius constant-temperature and survival oracles; const-generic
composition; GAT borrowing; `Cow` identity; transparent layout; zero-sized
routing; allocation-free borrowed evaluation; streamed/borrowed bitwise
equivalence; allocation-free lazy Celsius mapping; invalid step, empty input,
and output-length failures; and Coeus value/gradient differential contracts
over Sequential and Moirai backends.

Helios commit `dcf3ffcff9fcd0e4850209efa233f2a1ac1d5acf`
directly consumes Asclepius, deletes its scalar-law duplicate, delegates Coeus
gEUD construction, and passes its local workspace gates. Hosted verification
and the Kwavers thermal-response migration remain tracked by
`ATLAS-INTEGRATION-037`; their completion evidence is not implied by this
promotion record.

The packages are `publish = false`; no registry baseline exists for
`cargo-semver-checks`. SemVer comparison begins from the public Git contract.
Atlas checkout-engine format, locked check, warning-denied Clippy, 11/11
Nextest cases, doctest, and warning-clean rustdoc pass. A real provider-graph
smoke test at pushed Atlas registration commit `6fb5576` materializes public
Asclepius gitlink `ceb8b6d`, verifies its clean exact revision, and resolves
`crates/asclepius/Cargo.toml`.

## Rejected alternatives

- Consumer-local formulas retain divergent validation and unit contracts.
- An Asclepius-owned scalar, quantity, or autodiff engine forks Eunomia,
  Aequitas, or Coeus ownership.
- Returning owned cumulative histories introduces avoidable allocations and
  copies.
- Dynamic response dispatch adds a vtable where concrete model selection is
  known at the operation boundary.
- Moving DVHs, grids, images, catalogs, planning objectives, or transport
  state into Asclepius creates a cross-domain package.

## Consequences

- Atlas records 23 public packages.
- Biological-response equations have one provider-owned implementation while
  consumer-specific state and workflows remain local.
- The Coeus dependency cannot enter the `asclepius` core.
- New response laws enter Asclepius only with a stated validity domain,
  mathematical specification, proof obligation, and executable oracle.

## Relates to

- ADR 0005: Eunomia scalar SSOT.
- ADR 0020: exact Atlas provider-graph closure.
- ADR 0021: Aequitas quantity-law foundation.
- ADR 0025: Proteus material-property boundary, complementary to biological
  response.
- ADR 0027: Atlas-owned path-dependency materialization.
- `repos/asclepius/docs/adr/0001-biological-response-boundary.md`: canonical
  law boundary, theorem statements, migration, and evidence map.
