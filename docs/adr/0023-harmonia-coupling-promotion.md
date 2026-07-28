# ADR 0023: Promote Harmonia coupling orchestration

- Status: Accepted
- Date: 2026-07-20
- Class: `[arch]` `[minor]`

## Context

CFDrs, Kwavers, and Helios need to exchange interface state between
independently advanced physics partitions. Snapshotting, heterogeneous
subcycling, transfer, relaxation, fixed-point convergence, and transactional
failure are coupling mechanics rather than properties of one physics model.

Horae owns typed simulation time and const-generic subcycle ratios. Athena
Core owns validated convergence policy and allocation-free iteration
observation. Eunomia owns the real scalar contract. Reimplementing those laws
inside integrators or Harmonia would violate provider-first ownership and
SSOT.

## Decision

Promote public package `harmonia` as the Atlas owner for partitioned
multiphysics coupling mechanics. Phase 0 is one `no_std + alloc` crate with
unsafe code forbidden and missing public documentation denied.

`PartitionedPair<M, T, FIRST_SUBSTEPS, SECOND_SUBSTEPS>` executes a synchronous
Jacobi fixed-point iteration over one time window:

1. Snapshot caller-owned partition states and interface guesses.
2. Restore both work states before every fixed-point iteration.
3. Advance each partition with its const-generic Horae subcycle plan.
4. Export and transfer both interface states through `Cow<'a, [T]>`.
5. Check the raw defect `||F(x) - x||` with Athena's convergence policy.
6. Commit all caller slices together only after convergence.
7. Otherwise apply the selected relaxation policy and iterate.

The pair model bundles partition, transfer, and relaxation types through
associated types. Rust monomorphizes the loop; identity transfer, const-index
transfer, and full relaxation are zero-sized static policies. Reusable
boxed-slice workspaces allocate at construction and remain allocation-free for
Harmonia's borrowed transfers.

### Dependency direction

```text
harmonia ──> horae ──> aequitas
         ├─> athena-core
         └─> eunomia
```

Harmonia does not own equations, spatial discretizations, meshes, fields,
material laws, linear solvers, arrays, accelerators, allocators, schedulers, or
capability proofs.

## Migration plan

1. Publish Harmonia Phase 0 and register its fetched remote-default gitlink.
2. Migrate one consumer coupling site at a time in dependency order.
3. Replace all callers and delete the superseded ad-hoc loop in the same
   consumer increment; no adapter or compatibility shim lands.
4. Add later coupling regimes only after their scheduling, conservation, and
   ownership contracts are present and independently verifiable.

## Theorems and evidence

Harmonia ADR 0001 owns the formal statements and proofs:

- Transaction theorem: every error leaves caller slices unchanged because the
  only caller writes occur together in the convergence branch.
- Contraction residual theorem: for contraction factor `q < 1`,
  `||x - x*|| <= ||F(x) - x|| / (1 - q)`.
- Relaxation-honesty theorem: convergence checks the unrelaxed defect, so a
  small relaxation weight cannot manufacture convergence.
- Subcycle endpoint invariant: the last typed child step is the remaining
  duration to the exact window endpoint.

Revision `cf6ce3e9175bbc3eebc51918d137492b2da5edba` passed format,
`no_std`, warning-denied Clippy, 14/14 nextest tests, one doctest,
warning-denied rustdoc, the coupled-decay example, and cargo-deny. The suite
contains analytical, generated-property, differential-subcycle, `f32`/`f64`
instantiation, pointer-identity, ZST-layout, transactional, and zero-allocation
evidence. Release assembly emitted one body for the generic full-relaxation
policy and its handwritten concrete reference.

GitHub CI run
[`29753063192`](https://github.com/ryancinsight/harmonia/actions/runs/29753063192)
passed verification and supply-chain jobs. The registry contains an unrelated
music-theory package with the same crate name, so `cargo-semver-checks` cannot
supply a valid predecessor baseline. Harmonia is `publish = false`; SemVer
comparison begins from this public Git contract.

## Rejected alternatives

- Consumer-owned loops duplicate transaction, residual, relaxation, and
  subcycle laws.
- Dynamic dispatch adds vtables where each implementation type is known at the
  operation boundary.
- Harmonia-owned time, unit, scalar, or convergence types create competing
  provider vocabularies.
- An N-partition graph in Phase 0 speculates about scheduling and ownership
  contracts that are not stable.

## Consequences

- Atlas records 20 public packages.
- Consumer migrations proceed as dependency-ordered vertical slices.
- Phase 0 excludes waveform interpolation, more than two partitions,
  Gauss-Seidel ordering, quasi-Newton acceleration, distributed scheduling,
  and conservation-aware nonmatching-mesh transfer. No excluded capability is
  represented by a stub or compatibility shim.

## Relates to

- ADR 0002: heterogeneous topology law.
- ADR 0021: Aequitas quantity law.
- ADR 0022: Horae and Athena provider extraction.
- `repos/harmonia/docs/adr/0001-partitioned-coupling-boundary.md`: canonical
  Harmonia-side contract, proofs, references, and evidence limits.
