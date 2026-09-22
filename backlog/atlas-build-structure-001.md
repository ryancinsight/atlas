<a id="atlas-build-structure-001"></a>
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in-progress
- Census 2026-09-21 (top-level `tests/*.rs` per crate): 114 binaries — cfd-validation 37, cfd-1d 25, cfd-3d 18, cfd-2d 14, cfd-math 7, cfd-schematics 6, cfd-optim 4, cfd-core 2, cfd-io 1.
- Delivered (all merged, listed=executed parity): validation → 3 harnesses (#441), 1d → 1 (#443), 3d → 1 (#445), math → 1 (#448),   schematics → 1 (#449: 30/30 integration, 214/214). Rustdoc drift
  repaired along the way (#446 for cfd-3d, cfd-2d links inside #447's
  unit — both merged, no bypasses since). Next slice when claimed:
  cfd-optim (4).
