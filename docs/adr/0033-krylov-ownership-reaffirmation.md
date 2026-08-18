# ADR 0033: Reaffirm Athena as the Krylov owner and unwind the Leto regression

- Status: Accepted
- Date: 2026-07-27
- Class: [major] [arch]
- Amends: [ADR 0022](0022-horae-athena-provider-extraction.md); does not
  supersede it.

## Context

ADR 0022 promoted Athena as the stack's iterative-solver provider precisely
because "Leto, CFDrs, and Kwavers own iterative-solver recurrences beside
storage, discretization, or domain code". Leto executed its half in
`aa8aa9b refactor(leto-ops)!: Extract solvers to Athena` (leto ADR 0015,
2026-07-19 22:29), deleting `leto_ops::gmres` without a compatibility layer.

Four days later, `ee6582d chore(leto): remove ndarray/nalgebra
dev-dependencies` (2026-07-23 17:57) reintroduced a full iterative-solver
family into `leto-ops/src/application/linalg/iterative/`: `cg.rs`,
`bicgstab.rs`, `gmres/`, `lsqr.rs`, and Jacobi/SOR/SSOR/ILU preconditioners.
The commit message records neither the reintroduction nor a reason. The
evident driver is the nalgebra removal: CFDrs and Kwavers needed
nalgebra-free Krylov solvers, and Athena did not provide the required
capability set, so the recurrences were rebuilt where the arrays live.

The regression then propagated. CFDrs `6d18a547` replaced its own
CG/BiCGSTAB/GMRES with wrappers over the Leto family, and Kwavers retains a
third, `f64`-hardcoded GMRES in `kwavers-solver`. A gap audit on 2026-07-27
established that nothing in the stack references `athena_core::Gmres` or
`athena_core::Cg`; Athena's only code consumer is Harmonia, which imports the
convergence-policy and observer vocabulary alone.

An earlier reading of that audit proposed naming `leto-ops` the Krylov SSOT on
the strength of adoption counts. That inverts a ratified boundary on evidence
of non-adoption, and is rejected here: adoption did not happen because Athena
lacked capability, not because its ownership was wrong.

## Decision

1. Athena remains the sole owner of Krylov recurrences, operator and
   preconditioner seams, convergence policy, workspaces, and solve reports, as
   ADR 0022 states. The Leto iterative family is a boundary regression to
   unwind, not a second sanctioned home.
2. Leto's ownership is unchanged and unaffected: host arrays, views, CSR,
   SpMV, reductions, and the direct decompositions (LU, QR, Cholesky, SVD,
   eigen, Schur, Bunch-Kaufman, UDU). This ADR concerns iterative solvers
   only; no direct factorization moves.
3. Unwinding is sequenced behind capability, because deleting the Leto family
   before Athena can replace it would strand CFDrs and Kwavers:
   - **A.** Close Athena's capability gap: BiCGSTAB and LSQR recurrences, and
     the Jacobi/SOR/SSOR/ILU preconditioner set over the Leto backend.
   - **B.** Migrate CFDrs from its Leto-family wrappers to Athena.
   - **C.** Migrate Kwavers, which additionally requires refactoring
     `jacobian_vector_product` from `&mut self` to `&self` so its matrix-free
     operator satisfies the `LinearOperator::apply(&self, ...)` seam. Its only
     mutation is a scratch-buffer cache.
   - **D.** Delete `leto-ops/src/application/linalg/iterative/` and the
     `LinearOperator`/`Preconditioner` traits duplicated there.
4. Each stage lands as its own increment with its consumers converted in the
   same change. No compatibility re-export, forwarding wrapper, or adapter
   layer merges at any stage, per the standing anti-shim mandate and ADR 0022's
   own "delete superseded recurrences rather than hide them behind adapters".

## Consequences

- Corrections landed in the Leto family before this ADR (GMRES true-residual
  termination, happy-breakdown handling, non-finite guards, contiguous Krylov
  basis, conformance suite) remain valuable while stage D is outstanding,
  because CFDrs depends on that code today. They do not confer permanence.
- Athena gains solver families it did not previously carry. Each must satisfy
  the existing contract: backend-neutral over Leto CPU and Hephaestus WGPU,
  caller-owned allocation-stable workspace, validated absolute-plus-relative
  convergence policy, and value-semantic `Termination` rather than panics.
- Kwavers stage C is a `[minor]` breaking change to an internal seam.
- Until stage D completes, the stack knowingly carries two CPU Krylov
  implementations. The duplication is tracked, bounded, and scheduled rather
  than silent.

## Verification

- Board items `ATLAS-GMRES-SSOT-001` (re-scoped to this sequence) and
  `ATLAS-ATHENA-KRYLOV-CAPABILITY-001`.
- Stage A: each new recurrence passes generic conformance over `f32` and `f64`
  on the Leto backend, a forced multi-restart or multi-cycle case, dimension
  and termination error cases, and a post-initialization allocation
  measurement, matching the existing CG and GMRES contract tests.
- Stage D acceptance: a residue scan finds no Krylov recurrence outside
  Athena, and every consumer suite passes against Athena.
