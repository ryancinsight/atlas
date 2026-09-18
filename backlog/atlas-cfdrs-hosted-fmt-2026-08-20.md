<a id="atlas-cfdrs-hosted-fmt-2026-08-20"></a>
## ATLAS-CFDRS-HOSTED-FMT-2026-08-20 — repair required Rust format gate [patch] — in-progress

- **Owner:** current Atlas session; peer-assist claim on the clean files only.
- **Scope:** `repos/CFDrs/crates/cfd-2d/src/solvers/cell_tracking/tracker.rs`,
  `repos/CFDrs/crates/cfd-core/src/management/aggregates/parameters.rs`, and
  `repos/CFDrs/crates/cfd-core/src/physics/cavitation/number.rs`.
- **Acceptance:** the three files pass the repository formatter, the staged
  diff contains only formatter output in those files, and the focused provider
  check records the exact branch head. Unrelated peer-owned CFDrs dirt remains
  outside this item.
- **Evidence:** hosted CFDrs run `32323543129` reports the same three files as
  the Rust workspace formatting failure. This item fixes that concrete gate
  defect without changing tests, workloads, tolerances, or budgets.
- **Landed:** CFDrs commit `cd56f744` (`fix(cfd): Restore hosted formatter
  compliance`) is pushed to `codex/cfdrs-tvd-test-integration`; PR #360 open.
  Exact-file `rustfmt --edition 2024 --check` passes, and the overlay-free locked package
  check for `cfd-core` and `cfd-2d` passes.
- **Verification residual:** focused `cargo nextest` run
  `fdf1abe0-d650-4346-b1d2-e82fd96e3eed` reaches 55 passes and 27 configured
  skips before the first failure in peer-dirty
  `cfd-2d::physics::acoustics::gorkov::tests::f1_f2_analytical_values`
  (`0.19151009397460816` vs `0.2315809676184497`, bound `1e-10`); 800 tests
  were cancelled by fail-fast. The peer edit in `gorkov.rs` changed
  `typical_rbc()` from the test's `1000/1500` values to blood constants. This
  item does not modify that peer-owned file; the hosted gate remains open until
  the owning change reconciles the oracle and a clean default-head rerun passes.

