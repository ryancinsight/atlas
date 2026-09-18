<a id="atlas-conformance-ratchet-2026-08-19"></a>
## ATLAS-CONFORMANCE-RATCHET-2026-08-19 — exact provider regressions [patch] — blocked

- Hosted conformance run `32250014209` reached the exact root head `a4f24ee`
  after the root line-ending and submodule-status fixes. It reports three
  source regressions; the committed baseline remains unchanged.
- Exact gitlink attribution is CFDrs `834340f7`:
  `crates/cfd-1d/src/solver/core/network_solver.rs` crossed 500 lines
  (`500 -> 568`); Consus `2e0df9f8`:
  `crates/consus-zarr/src/codec/mod.rs` crossed 500 lines (`439 -> 643`);
  and Coeus `5adc2d16`:
  `crates/coeus-autograd/src/lib.rs` contributes the counted crate-level
  `#![allow(...)]` surface (`18 -> 19`).
- No baseline raise is authorized. The source repairs require provider-owned
  edits, focused gates, hosted conformance, and an exact-head pointer sweep.
  The current provider checkouts/lanes are peer-owned and dirty; re-open when
  those claims land or become stale and reclaimable.
- Fresh clean-checkout run `32389729879` at root `dfc0184` confirms the same
  defect class with six current regressions: `CFDrs/oversized_files` 134 ->
  135, `coeus/crate_level_allows` 18 -> 19, `consus/oversized_files` 82 ->
  83, `moirai/seqcst_production` 101 -> 107, `ritk/manifest_implementation`
  105 -> 106, and `ritk/commented_out_code` 8 -> 9. The run also reports 15
  tightenings; none authorizes a baseline increase. These counts bind to the
  committed provider gitlinks and remain blocked on provider-owned source
  repairs, not on the Atlas book-gate change.
- The next exact root run at `f621c1d` reduced the class to five regressions:
  CFDrs `oversized_files` 134 -> 135, Coeus `crate_level_allows` 18 -> 19,
  Moirai `seqcst_production` 101 -> 107, and RITK
  `manifest_implementation` 105 -> 106 plus `commented_out_code` 8 -> 9.
  Consus no longer regresses after Atlas corrected its gitlink to merged
  default `e121b9d4`. The concurrent overlay run `32391551896` exposed two
  stale `moirai-http` entries caused by dirty local Moirai state; root commit
  `f621c1d` removes them from the generated block. No baseline raise is
  authorized; the next hosted run must collect both fixes.
Re-open trigger: CFDrs, Coeus, Moirai, or RITK lands the named source repair,
or its provider claim becomes stale and is reclaimed for a focused repair.

