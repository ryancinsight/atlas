<a id="next-steps"></a>
## ATLAS-NEXT-STEPS-2026-09-03 - Sequenced plan toward the suite [arch] — todo

Atlas is a shared location; members compose as needed.

**First-party boundary.** First-party ownership targets **stack concerns** -
scalars, quantities, arrays, allocation, scheduling, placement, accelerators,
numerics, physics - where a third-party dependency costs correctness control
and the ability to fix upstream. It does **not** target the **shell boundary**:
a frontend framework (Tauri, egui) is ecosystem-solved, sits outside the
safety-relevant core, and reimplementing one enlarges the verification surface
of a regulated product for no gain. The dual frontend and backend split is the
asset - it puts document state, validation, units, and solver orchestration on
the Rust side of the IPC line. That is per-product integrator work, not a stack
package. The same reasoning admits `wgpu`, DICOM, and format libraries at their
boundaries and refuses `nalgebra`, `ndarray`, `rayon`, and `num-traits` inside
the stack (ADR 0055 substrate contract).

| # | Increment | Repo | Class | Status |
| --- | --- | --- | --- | --- |
| 1 | Delete the CFDrs elastic copy; compose `proteus::IsotropicSolid` | CFDrs | `[patch]` | done (`f063be4b`) |
| 2 | Delete the kwavers elastic copy | kwavers | `[minor]` | done for A0 (`1f86a9172`); residual `computed.rs` formulas |
| 3 | aequitas stress semantics marker | aequitas | `[minor]` | done (`#50`) |
| 4 | aequitas `ReactionRate` and `MolarFlux` | aequitas | `[minor]` | done (`#50`) |
| 5 | Architecture test R7 and `cargo deny bans` substrate list | atlas | `[patch]` | delivered 2026-09-04 (`4a574a801`); live-balance enum in WT |
| 6 | Ares A1 through A9 | ares | `[arch]` | A0-A8 done; A9 blocked on unpublished `proteus-mat` |
| 7 | Prometheus P1 through P9 | prometheus | `[arch]` | Phase 0 computation done (11 commits, Robertson included via the Horae implicit seam); **Ask-User** for `ryancinsight/prometheus` |

Steps 1 to 5 are mutually independent and can run concurrently on disjoint
scopes.

**Not in this plan:** no GUI package, no universal model tree, no in-stack UI
framework. The application layer stays per product behind the IPC boundary of
each tool.

