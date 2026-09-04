# ARCH-008 scattered-container oracle drift — measured 2026-09-04

Instrument: `python scripts/atlas_scattered_containers_classify.py --json`
against all member working trees (every member clean except apollo's five
peer-owned n=32 files and leoneuro-rs/report scratch), diffed against
`scripts/oracles/arch-008-production-sites.txt` (249 sites, 161 files).

## Result

| Measure | Oracle | Live | Delta |
| --- | --- | --- | --- |
| Production sites | 249 | 239 | −10 |
| Production files | 161 | 158 | −3 |
| New files entering the set | — | **0** | — |

- **No new file carries the pattern.** Every one of the 239 live sites lies in
  a file the oracle already knows. The site-level churn that makes
  `make verify-scattered-oracle` exit 1 is line/column shift inside known
  files, plus three genuine conversions.
- **Converted out of the set (three whole files):**
  - `repos/CFDrs/crates/cfd-schematics/src/geometry/intersection/detection.rs`
  - `repos/CFDrs/crates/cfd-schematics/src/visualizations/schematic/layout.rs`
  - `repos/coeus/crates/coeus-autograd/src/ops/nn/loss/ctc.rs`

  `ctc.rs` was ARCH-008's largest named production exemplar (6 occurrences);
  it is now zero. The item is converging, not running in place, as of this
  measurement.

## Disposition

The oracle is **not** regenerated in this session. Per
ATLAS-ARCH-008-RUNNING-IN-PLACE-225 the oracle is only ever regenerated in a
commit whose subject says so, and the member gitlink pins are mid-advance by a
peer stream (`MM repos/*` staged at orientation). Regenerating against
worktree heads while CI scans the recorded pins would desync the oracle from
the state the gate actually measures and red the conformance gate spuriously.

Re-open trigger: the in-flight gitlink advance lands (member heads pinned).
Then regenerate in a commit whose subject says
`chore(oracle): Regenerate the ARCH-008 site list after CFDrs/coeus conversions`,
recording the three conversions and the 249 → 239 site tightening. This is a
tightening, not baseline laundering: zero new sites entered the set.
