<a id="atlas-cfdrs-chain-ladder-001"></a>
## ATLAS-CFDRS-CHAIN-LADDER-001 — Consolidate the two tiered ladders [patch] — in-progress

outcome: `LinearSolverChain::solve`/`solve_with_state` become one
parameterized ladder; cfd-math's remaining Leto consumers migrate to Athena
and the leto-ops iterative dependency is deleted.
- Done: cfd-validation (`f8634e43`, `SolverKind` enum dispatch) and cfd-1d
  (`4ca6518d`, 736/736 nextest) converted.
- next: cfd-3d — `projection_solver.rs` GMRES/CG fields, `solver.rs` dead
  `_linear_solver` field (delete), `LinearSolverChain` call (already Athena).
  **Blocked**: files were live peer-edited (Quantity migration). Re-open:
  cfd-3d/src/fem goes quiet.
- next: delete `cfd_math::iterative` facade + leto-ops dep once cfd-3d lands.
- Found in passing (filed separately): `jfnk.rs` carries its own hand-rolled
  matrix-free GMRES — a fifth GMRES in the stack.
