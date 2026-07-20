# ADR 0026: Promote Tyche uncertainty-quantification foundation

- Status: Accepted
- Date: 2026-07-20
- Class: `[arch]` `[minor]`

## Context

CFDrs, Kwavers, and Helios each carried private copies of
uncertainty-quantification (UQ) vocabulary: parameter spaces, Latin
hypercube designs, ensemble execution, online moments, correlation
screening, calibration, and reproducible seed law. The shared shape
recurs across the three integrators along with the same correctness
contract — a study must replay bit-identically regardless of Moirai
scheduling, sampling must remain inside the recorded bounds, and
statistics must report typed absence rather than silent `NaN`.

Moirai owns scheduling and runtime lifecycle. Consus owns stores,
formats, compression, and durability. Domain packages own their
physics and model semantics. Reimplementing study identity, sampling
laws, ensemble statistics, and calibration in each integrator violates
provider-first ownership and SSOT. Eunomia owns the scalar contract;
Aequitas owns dimensional units, which Tyche uses only for tagged
endpoint scalars when a domain model composes a real-valued response.

## Decision

Promote public package `tyche` as the Atlas owner for reproducible
uncertainty studies. Phase 0 is one workspace with four crates:
`tyche-core` (`no_std + alloc`, no runtime or persistence dependency),
`tyche-moirai` (borrowed scoped execution), `tyche-consus` (validated
Store adaptation), and the `tyche` facade.

Phase 0 provides validated parameter spaces, counter-stream
random-access Latin hypercube designs, index-addressed ensemble
execution, online moments, correlation screening, finite-sample
split-conformal calibration, and provider adapters for Moirai and
Consus.

`tyche-core` is `no_std + alloc`, `#![forbid(unsafe_code)]`, and
`#![deny(missing_docs)]`. `Parameter`, `Study`, and `ArtifactKey` use
`Cow<str>` for one borrowed/owned API. Numeric widths are const
generics. `StudyModel::Response<'a>` is a GAT so the statically
dispatched reducer consumes it before its borrow ends. Designs,
models, reducers, scalar precision, variance policy, and Moirai chunk
width monomorphize without algorithm-path vtables.

### Dependency direction

```text
tyche-core ──> eunomia
tyche-moirai ──> tyche-core
             ──> moirai
tyche-consus ──> tyche-core
             ──> consus
tyche ──> tyche-core
      ──> tyche-moirai
      ──> tyche-consus
```

`tyche-core` depends on Eunomia only. The provider adapters pull Moirai
and Consus; the facade composes them. The core never carries a runtime
or persistence dependency.

## Migration plan

1. Publish Tyche Phase 0 and register its fetched remote-default
   gitlink (done at master HEAD `7898899`).
2. Migrate one consumer UQ site at a time in dependency order. Each
   integrator increment adopts the Tyche design and removes the local
   LHS, moments, and calibration in the same vertical slice; no adapter
   or compatibility shim lands.
3. Extend sampling breadth and UQ breadth only after each new estimator
   has its scenario, replay law, and consumer overlap recorded and
   independently verifiable.

## Theorems and evidence

Tyche ADR 0001 owns the formal statements, proof obligations, and
rejected alternatives:

- Latin hypercube permutation: for sample count `n`, each dimension
  uses stride `a` coprime to `n` and offset `b`; the affine map
  `pi(i) = a*i + b (mod n)` is a permutation, hence
  `x_i = (pi(i) + u_i)/n`, `0 <= u_i < 1`, places one point in every
  stratum.
- Counter-addressed replay: jitter depends only on
  `(seed, index, dimension)`, so Moirai scheduling cannot reorder
  inputs or output slots.
- Welford recurrence: stores the mean and centered sum; population
  variance divides by `n`, sample variance by `n - 1`. The
  zero-sized variance policy makes singleton sample variance a typed
  error instead of `NaN`.
- Squared Pearson screening lies in `[0, 1]` by Cauchy-Schwarz and is
  deliberately not called Sobol.
- Split-conformal calibration uses corrected rank
  `ceil((n + 1)(1 - alpha))`, capped at `n`.

Revision `7898899` passed format, `no_std` for `tyche-core`,
warning-denied Clippy, workspace nextest over `--all-features`,
doctests, warning-denied rustdoc, the `reproducible_study` example,
and cargo-deny. Zero-sized `SplitMix64`, `StandardNormal`,
`PopulationVariance`, and `SampleVariance` were asserted; the Latin
hypercube stores `O(PARAMETERS)` coefficients, and repeated core
sampling and statistics allocate nothing.

The package is `publish = false`; no `cargo-semver-checks` baseline
exists against a prior registry release. SemVer comparison begins from
this public Git contract.

## Rejected alternatives

- Consumer-owned UQ libraries duplicate replay laws, sampling designs,
  singleton handling, and calibration across three integrators.
- Tyche-owned scheduling or persistence forks Moirai and Consus
  contracts.
- A Tyche dependency on Coeus couples a measurement vocabulary to a
  specific backend stack and breaks the layered ownership.
- A graph-coupled study schema in Phase 0 speculates about Consus
  transactional stores that are not yet committed.

## Consequences

- Atlas records 22 public packages once the Tyche gitlink is recorded
  at `7898899` (peer commits `feed3bc`, `edf99e4`).
- Consumer migrations proceed as dependency-ordered vertical slices
  owned by the respective integrator claim streams.
- Phase 0 excludes random-access Sobol, runtime-dimension views,
  categorical and weighted sampling, versioned distribution vectors,
  deterministic bootstrap, Morris, and true Saltelli Sobol estimators;
  a versioned Consus study schema waits for a Consus transaction
  capability. No excluded capability is represented by a stub or
  compatibility shim.

## Relates to

- ADR 0002: heterogeneous topology law — Tyche Phase 0 stays inside
  the bounded UQ role.
- ADR 0005: Eunomia scalar SSOT — Tyche consumes the real scalar
  contract.
- ADR 0023: Harmonia coupling promotion — Tyche studies can wrap a
  Harmonia-partitioned model as one of many response reducers.
- ADR 0025: Proteus material-property promotion — Tyche can sweep
  Proteus material parameters without crossing ownership boundaries.
- `repos/tyche/docs/adr/0001-reproducible-study-boundary.md`:
  canonical Tyche-side contract, replay laws, proof obligations, and
  evidence limits.
