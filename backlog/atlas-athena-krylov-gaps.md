<a id="atlas-athena-krylov-gaps"></a>
## ATLAS-ATHENA-KRYLOV-GAPS — Fill athena's Krylov gaps: MINRES, FGMRES, Chebyshev, deflation [feature][minor] — todo
- outcome: `athena-core` gains MINRES (symmetric indefinite), FGMRES (variable preconditioner), Chebyshev, and deflation/recycling on the established `solver/` module pattern, with the leto instantiations the ladder requires.
- oracle (ADR 0056 new-construction rule, ADR 0062 table): each method at f32 and f64 — MINRES recovers a closed-form indefinite solution where CG fails; FGMRES converges where fixed-preconditioned GMRES stalls; Chebyshev damps a high-frequency residual within the analytic bound; the zero-null and identity round-trip composition oracles hold.
- priority: feature; needs: —; scope: `repos/athena/crates/athena-core/src/solver/`, `repos/athena/crates/athena-leto/src/`, `repos/athena/crates/athena-leto/tests/`.
- next step: MINRES first — its closed-form indefinite oracle is self-contained; publish the oracle fixture before the recurrence per ADR 0056's promotion path.
- Decision: [ADR 0062](../docs/adr/0062-iterative-solver-and-preconditioner-ownership.md) Phase 2; Phase 1 delivered by athena#98–#109, CFDrs#527–#537, leto#340–#343, kwavers#941.
- basis: athena main c2882ef, CFDrs main 3fc2cacc, atlas origin/main 565a5d3e (2026-10-11).
