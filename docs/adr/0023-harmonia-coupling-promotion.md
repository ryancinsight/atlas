# ADR 0023: Promote Harmonia coupling orchestration over Horae and Athena

- Status: Proposed (awaiting publish of `repos/harmonia` remote)
- Date: 2026-07-20
- Class: `[arch]` `[minor]`

## Context

Atlas integrators repeatedly couple independently advanced physics partitions
across one time window: CFDrs couples flow to structural and energy partitions,
Kwavers couples acoustic, elastic, and thermal fields, and Helios couples
dose, transport, and imaging partitions. Each integrator currently owns its
ad-hoc coupling loop. The shared concerns across those loops are:

- snapshotting caller-owned partition state and interface guesses before
  iteration;
- advancing two partitions independently over the same window with possibly
  heterogeneous subcycle ratios;
- exporting and transferring interface state without forcing ownership of the
  source buffer;
- checking the unrelaxed fixed-point defect `r = ||F(x) - x||` against a
  validated convergence policy;
- relaxing the interface guess only when another iteration is required; and
- guaranteeing transactional failure: any error, including iteration-budget
  exhaustion, leaves every caller slice unchanged.

Those concerns are present in each integrator's coupling path and would
duplicate a law that already exists. Harmonia's own
[ADR 0001](../../repos/harmonia/docs/adr/0001-partitioned-coupling-boundary.md)
establishes the partitioned-coupling boundary, the Felippa--Park--Farhat and
Meisrimel--Birken references, the transaction theorem, the contraction
residual bound, the relaxation-honesty theorem, and the subcycle endpoint
invariant.

Horae already owns typed simulation time and const-generic subcycle ratios.
Athena Core already owns convergence policy and allocation-free iteration
observation. Aequitas owns physical time quantities, and Eunomia owns the
real scalar contract. Harmonia composes these without re-owning any of them.

## Decision

Promote Harmonia from P0 roadmap candidate to a current Atlas package owning
partitioned multiphysics coupling mechanics.

### Phase 0 contract

Phase 0 is one `no_std + alloc` crate with `#![forbid(unsafe_code)]` and
`#![deny(missing_docs)]`. The `PartitionedPair<M, T, FIRST_SUBSTEPS,
SECOND_SUBSTEPS>` advances two partitions from the same window-start snapshot:

1. Snapshot caller-owned states and interface guesses.
2. Restore both partition work states from the snapshots.
3. Advance each partition over the window using its const-generic Horae
   subcycle plan.
4. Export and transfer both interface states.
5. Check the unrelaxed Euclidean defect `r = ||F(x) - x||`.
6. Commit work states and `F(x)` only when Athena's policy accepts `r`.
7. Otherwise compute `x <- x + omega (F(x) - x)` and repeat.

The loop is generic over the pair model, scalar, transfer policy, relaxation
policy, observer, and two const subcycle ratios. Monomorphization eliminates
the vtable; static transfer and relaxation policies are zero-sized types.

### Dependency direction

```text
harmonia ──> horae
         ──> athena-core
         ──> eunomia
```

`harmonia` depends on `horae`, `athena-core`, and `eunomia`. It transitively
reaches `aequitas` through Horae. It does not depend on Leto, Hephaestus,
Moirai, Mnemosyne, Themis, Melinoe, Hermes, or Coeus. Physics partitions
receive and return borrowed slices; Harmonia never owns an array, device
buffer, scheduler, allocator, capability proof, or compute backend.

### Bounded context

Harmonia owns:

- partition contracts (`Partition`, `Substep`) over caller-owned slices;
- the two-partition Jacobi coupling iteration;
- workspace construction and dimension validation;
- transfer policies that return `Cow<'a, [T]>`;
- relaxation policies (`FixedRelaxation`, `FullRelaxation`); and
- coupling reports carrying residual norm, threshold, and iteration count.

Harmonia owns no equation, spatial discretization, mesh, field, material law,
linear solver, accelerator, scheduler, allocator, array, or capability proof.
The optional dev-dependency on Aequitas exists only for example and test
fixtures; it is not a runtime dependency.

## Migration plan

1. **Complete (local):** Phase 0 crate, ADR 0001, runnable example, value
   semantic nextest suite, doctest, warning-denied Clippy, no-std build,
   format and rustdoc gates. Verified 2026-07-20 against the local checkout.
2. **Pending (user action):** publish `repos/harmonia` to a public remote at
   `https://github.com/ryancinsight/harmonia`. Atlas-meta cannot create
   GitHub repositories. The local clone is currently an untracked worktree
   with no commits and no `origin` remote; the promotion gate's condition 5
   (independent versioning and remote identity) cannot be satisfied from
   atlas-meta.
3. **Pending (atlas-meta, after publish):** add the submodule entry to
   `.gitmodules`, advance the parent gitlink to the published HEAD, update
   the README current-stack table and ADR INDEX from `Proposed` to
   `Accepted`, and remove the `harmonia` watchpoint recorded here.
4. **Pending (consumer claim streams):** migrate the per-integrator coupling
   loops to `PartitionedPair` in dependency-ordered vertical slices. Each
   increment converts one coupling site, deletes the superseded ad-hoc loop,
   and runs the integrator's own gate. No compatibility shim lands; the
   working branch is the isolation layer.

## Rejected alternatives

### Let CFDrs, Kwavers, and Helios continue owning coupling loops

Rejected because the transaction theorem, the contraction-residual bound, the
subcycle endpoint invariant, and the zero-allocation workspace contract recur
in each integrator. Three implementations of the same fixed-point law violate
SSOT and `architecture_scoping`.

### Promote a graph-coupled N-partition crate from day one

Rejected per Harmonia ADR 0001 §Rejected alternatives: no stable scheduling
and ownership contract exists yet for N>2 partitions, Gauss--Seidel ordering,
or quasi-Newton acceleration. Promoting that surface now would add
indirection without a present requirement, violating `standards`'s
speculative-generality prohibition.

### Make Harmonia own time, convergence, or units

Rejected because Horae, Athena Core, and Aequitas are the authoritative
providers. Re-owning any of those in a coupling crate creates a second source
of truth.

### Allow dynamic dispatch for transfer or relaxation policies

Rejected because the implementor set is closed at each call site. Static
dispatch preservesInlining, scalar specialization, and the ZST policy
encoding that the relaxation-honesty theorem depends on.

## Consequences

- Atlas records 20 current packages once the remote publishes.
- Harmonia Phase 0 covers two partitions, synchronous Jacobi, one time
  window, and const-generic heterogeneous subcycle ratios. Waveform
  interpolation, N>2 partitions, Gauss--Seidel ordering, quasi-Newton
  acceleration, distributed scheduling, and conservation-aware nonmatching
  transfer remain out of Phase 0 scope and are not behind stubs or feature
  flags.
- Consumer migrations are dependency-ordered follow-up work owned by the
  respective integrator claim streams. They are not part of this promotion
  increment and are not authorized by it.
- No `cargo-semver-checks` baseline exists against the `crates.io`
  `harmonia` 0.1.0 music-theory package; Harmonia is `publish = false`, and
  the registry package is not an API predecessor. SemVer comparison begins
  from this repository's first published Git contract.

## Verification

Local evidence collected 2026-07-20 against the unversioned Harmonia
worktree at `repos/harmonia`:

- `cargo check --workspace --all-targets`: rc=0.
- `cargo nextest run --workspace`: 14/14 pass (no skips). The suite covers
  the transaction theorem (`theorems::nonconvergence_is_transactional`), the
  contraction-residual bound (`theorems::contraction_residual_bounds_fixed_point_error`,
  with independently solved analytical oracle), relaxation honesty
  (`theorems::relaxation_weight_cannot_manufacture_convergence`), index
  transfer selection, fixed-relaxation interval rejection, workspace
  dimension mismatch, generic-scalar monomorphization, heterogeneous
  subcycle endpoint semantics, contractive linear-pair a-posteriori bound,
  pointer-identity for identity transfer, ZST static-policy type-layout
  assertions, codegen equivalence between generic and concrete relaxation
  bodies, and zero-allocation-after-construction rigor.
- `cargo test --doc`: 1/1 pass (the README `PartitionedPair` example).
- `cargo clippy --all-targets -- -D warnings`: rc=0.
- `cargo fmt --check`: rc=0.
- `cargo doc --no-deps`: rc=0, no new warnings.

The pending remote publish is the open condition for the Atlas promotion
gate; the residual watchpoint is recorded in `backlog.md` §Watchpoints (2026-07-20).

## Relates to

- ADR 0002 (heterogeneous topology law — Harmonia Phase 0 stays inside the
  bounded Coupling role).
- ADR 0021 (Aequitas quantity law — Harmonia transitively reaches Aequitas
  via Horae only through the dev-dependency example fixture).
- ADR 0022 (Horae and Athena extraction — Harmonia composes Athena Core and
  Horae rather than re-owning them).
- `repos/harmonia/docs/adr/0001-partitioned-coupling-boundary.md` (the
  Harmonia-side coupling-boundary record).
