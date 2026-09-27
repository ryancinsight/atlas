<a id="atlas-substrate-004"></a>
## ATLAS-SUBSTRATE-004 — Generic plan/execution layer for Apollo [arch] — todo
- **priority:** tightening
- **outcome:** Apollo's transform plan/execution paths share one generic `<T: Scalar>`/backend-parameterized layer instead of per-type or per-backend cloned variants, per the compute-substrate consolidation ADR 0039.
- **next:** adopt the generic layer in two crates first to prove the seam, then the remaining crates one per claim (waste-bounded, dependency-ordered per `sprint`: task generation).
- **Acceptance:** `cargo-llvm-lines` instantiation count does not regress; differential tests against the pre-migration per-type paths pass; no crate reverts to a cloned specialization.
- Owner: unclaimed; scope is Apollo (`repos/apollo`).
