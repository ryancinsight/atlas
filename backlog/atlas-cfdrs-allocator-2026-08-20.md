<a id="atlas-cfdrs-allocator-2026-08-20"></a>
## ATLAS-CFDRS-ALLOCATOR-2026-08-20 — Remove library global allocator [major][arch] — in-progress

- **outcome:** `cfd-validation` drops its process-wide
  `#[global_allocator]`; tracking allocator is explicit-harness-only; a
  downstream-style test declares `System`; provider's locked workspace
  all-target gate passes. Public breaking change per the recorded
  allocator decision.
- **delivered:** provider commit `d1305ee2`; nextest 187/187 + 1/1,
  clippy/fmt clean, benchmark compiles.
- **open:** required locked check — Atlas overlay needs a provider
  `Cargo.lock` rewrite under `--locked`; lockfile is peer-dirty. Carried
  by open CFDrs PR [#360](https://github.com/ryancinsight/CFDrs/pull/360).
