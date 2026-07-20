# ADR 0022: Extract Horae and Athena provider boundaries

- Status: Accepted
- Date: 2026-07-19
- Class: [arch] [minor]

## Context

Atlas integrators repeat two cross-domain policies:

- CFDrs and Kwavers own overlapping time-stepping, event, and subcycle
  mechanics beside their equations; and
- Leto, CFDrs, and Kwavers own iterative-solver recurrences beside storage,
  discretization, or domain code.

Aequitas owns physical time quantities. Leto owns host arrays, views, CSR,
SpMV, reductions, decompositions, and CPU kernels. Hephaestus owns accelerator
devices, buffers, transfers, sparse kernels, reductions, and dispatch.
Extracting new providers must preserve those owners and delete superseded
recurrences rather than hide them behind adapters.

## Decision

Promote two independently versioned public providers.

### Horae

Horae depends on Aequitas and Eunomia and owns:

- finite simulation instants and positive steps over Aequitas time;
- a borrowed-slice explicit-system seam;
- one const-generic explicit Runge--Kutta recurrence;
- reusable stage workspace;
- adaptive accept/reject policy;
- borrowed sorted event schedules with exact clipping; and
- zero-sized const-generic subcycle-ratio plans.

Horae owns no equation, spatial discretization, CFL formula, implicit or
nonlinear solve, coupling invocation, array, scheduler, or device backend.

### Athena

Athena's dependency direction is:

```text
athena-leto ──> athena-core <── athena-wgpu
     │                              │
     └── Leto                       └── Hephaestus
```

`athena-core` depends on Eunomia, not Aequitas. It owns operator and
preconditioner seams, convergence policy, scalar reports, workspaces, and
backend-neutral solver recurrences. `athena-leto` supplies Leto CPU execution.
`athena-wgpu` supplies real Hephaestus WGPU execution. Full GPU vectors remain
resident; only reduction scalars and the explicitly requested final result
cross the host boundary. No CPU fallback exists in the WGPU path.

Athena initially provides:

- preconditioned conjugate gradient for symmetric positive-definite systems;
  and
- restarted right-preconditioned GMRES for general nonsymmetric systems.

GAT view families map both recurrences to zero-copy Leto array views and
borrowed typed Hephaestus buffers. ZST policy types select algorithms and
identity preconditioning. GMRES encodes restart width as a structural const
generic and reuses a bounded basis and Hessenberg workspace.

## Migration plan

1. **Complete:** implement Horae and Athena with code, documentation, examples,
   value-semantic tests, toolchain pins, bounded nextest policy, and CI.
2. **Complete:** delete Leto's public CG implementation and result type after
   Athena CPU/WGPU conformance passes.
3. **Complete:** implement restarted GMRES in Athena with reusable basis and
   Hessenberg storage and a nonsymmetric analytical oracle, then delete Leto's
   GMRES implementation and result type in the same increment.
4. **Pending:** migrate CFDrs and Kwavers time-stepping families to Horae in
   dependency-ordered vertical slices, deleting each converted recurrence.
5. **Pending:** migrate CFDrs and Kwavers iterative solver families to Athena
   operator and preconditioner implementations, deleting each converted
   recurrence.
6. **Complete:** publish independent public repositories, record exact
   submodule gitlinks, advance Leto to its merged removal, and move Horae and
   Athena into the Atlas current-stack table.

Each remaining migration slice updates all in-scope callers and deletes the
superseded path. No forwarding module, compatibility re-export, local provider
mirror, or CPU fallback is permitted.

## Rejected alternatives

### Put Athena beneath Aequitas

Rejected because linear-solver scalar, storage, and execution contracts come
from Eunomia, Leto, and Hephaestus. Physical units are not an intrinsic
dependency of a dimensionless Krylov recurrence.

### Put time integration in Moirai

Rejected because Moirai owns execution scheduling. Simulation time, tableau
law, event clipping, and accept/reject policy are numerical orchestration
rather than task scheduling.

### Add GPU algorithms directly to Leto

Rejected because it makes the host array provider own accelerator execution
and prevents the solver recurrence from remaining backend-neutral.

### Promote empty or incomplete repositories

Rejected because a name and scaffold do not satisfy the Atlas package gate.
Both promoted repositories contain real input-sensitive computation,
independent analytical tests, runnable examples, public remotes, CI, and exact
parent gitlinks. Leto's duplicate solver ownership is deleted before
promotion.

## Consequences

- Atlas records 19 current packages.
- Horae can migrate explicit consumers without importing scheduler, array, or
  device policy.
- Athena CPU solves allocate nothing after workspace construction.
- Current Hephaestus reductions still allocate provider-local scalar and
  scratch resources and synchronize scalar readback. GPU zero-allocation
  remains an upstream provider increment, not a hidden Athena claim.
- CFDrs and Kwavers migrations remain dependency-ordered follow-up work; their
  existing recurrences are not treated as Athena implementations.

## Verification

- Horae passes 14 configured nextest cases, one doctest, warning-denied Clippy
  and rustdoc, its analytical example, and dependency-policy checks.
- Athena passes 20 configured nextest cases with no skips, including generic
  `f32`/`f64` CPU PCG and GMRES, allocation measurements, forced multi-cycle
  restart, termination cases, and real-device Hephaestus WGPU PCG and GMRES.
- Athena's four CPU/WGPU examples execute and match their manufactured
  solutions.
- Leto passes 295 `leto-ops` nextest cases and eight doctests after removing
  `cg`, `gmres`, `CgResult`, `GmresResult`, and the solver module.
- `cargo-semver-checks` identifies the Leto removals as requiring a major
  release boundary.
- Horae and Athena hosted verification and supply-chain jobs pass on their
  merged public heads after the final numerical-oracle review fixes.
- Both public gitlinks resolve to their remote `main` objects, and the Leto
  gitlink resolves to merged PR #54.
