<a id="atlas-cfdrs-hosted-fmt-2026-08-20"></a>
## ATLAS-CFDRS-HOSTED-FMT-2026-08-20 — repair required Rust format gate [patch] — in-progress
- **outcome:** three files pass the formatter with a diff of formatter output only: `cfd-2d/.../cell_tracking/tracker.rs`, `cfd-core/.../aggregates/parameters.rs`, `cfd-core/.../cavitation/number.rs`.
- **open:** hosted gate stays red — nextest run `fdf1abe0-d650-4346-b1d2-e82fd96e3eed` fails at peer-dirty `cfd-2d::...::gorkov::tests::f1_f2_analytical_values` (peer changed test constants, outside this item's scope). Stays open until the owning change reconciles the oracle and a clean default-head rerun passes.
