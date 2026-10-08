<a id="atlas-leto-oversize-burndown-001"></a>
## ATLAS-LETO-OVERSIZE-BURNDOWN-001 — Five grown leto files block every leto push [correctness] — todo
- priority: correctness (a red stack gate on all leto delivery)
- outcome: `leto/oversized_files` returns to its baseline row (7); every leto push from current main passes the conformance gate again.
- scope: `repos/leto/crates/leto-ops/src/application/unary.rs` (634), `src/application/diff/three_dimensional/tests.rs` (637), `src/application/diff/three_dimensional/operator.rs` (519), `tests/ops/sparse.rs` (598), `tests/ops/loss/ctc.rs` (548).
- **why (measured 2026-10-08):** the five files grew past 500 lines on leto main after the pin hold, raising the class 7 -> 12 against the atlas baseline; the pre-push conformance gate now blocks any leto revision based on current main (observed blocking the dense-bridge kernel, rescue leto#340).
- **method:** split by concern following the in-tree pattern (`tests/ops/attention/`, `layout/` are directories): `unary.rs` into `unary/{map,operators}` (the map kernels vs the `UnaryOp` family), the test modules into submodule directories, `operator.rs` by its impl families. Pure moves; the full leto-ops suite re-verifies.
- **open:** rescue [leto#340](https://github.com/ryancinsight/leto/pull/340) (the verified dense-bridge kernel) re-pushes from main once this lands; the CFDrs consumer deletion (chain tier-1 re-point, `multigrid/cycles` re-point, `DirectSparseSolver` retirement) follows against it.
- next: split the three test modules first (mechanical), then `operator.rs`, then `unary.rs`.
