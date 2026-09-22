<a id="atlas-build-structure-001"></a>
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in-progress
- Census 2026-09-21 (top-level `tests/*.rs` per crate): 114 binaries — cfd-validation 37, cfd-1d 25, cfd-3d 18, cfd-2d 14, cfd-math 7, cfd-schematics 6, cfd-optim 4, cfd-core 2, cfd-io 1.
- Delivered 2026-09-21 as CFDrs PR #441, merged `5645e5b0`: cfd-validation's 35 contract files moved into `tests/main/` under one `tests/main.rs` root; `allocator_compat`/`tracking_allocator` stay standalone (one global allocator per binary is a documented contract). 37 links -> 3. Parity: 252/252 integration listed and executed, 439/439 pass; the 188-vs-187 textual gap reproduces on untouched `src/` (pre-existing).
- Next slice when claimed: cfd-1d (25 binaries).
