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
tightening, not baseline laundering: zero new files entered the set.

## Handoff re-verification — 2026-09-04, post-delivery

All meta gates re-run after the kwavers delivery landed:

| Gate | Result |
| --- | --- |
| `make board-lint` | PASS — all item ids unique (appendix fix holds); 375-mention prose note is the calibrated warning |
| board-lint test suite | 9/9 |
| architecture-test suite | 29/29 |
| conformance test suite | 65/65 |
| `make verify-scattered-oracle` | FAIL — expected; drift re-measured below |
| `atlas-conformance.py check` | exit 1 — 6 ratchet regressions, decomposed below |

### Re-measured oracle drift (18 site entries)

Same shape as the orientation measurement — **no new file enters the set** —
now decomposed by owner:

- Line shift from this session's delivery:
  `kwavers-solver/src/forward/viscoacoustic/solver.rs:103:20 → 110:20` (one
  site, same file, same classification). The kwavers branch worktree is ahead
  of its recorded pin, so the scan reads the delivery tree.
- Peer line shifts in trees ahead of their pins:
  `interpolator.rs:30/212 → 238`, `consus-mat matrix.rs:289 → 292`.
- New peer conversions since orientation: CFDrs
  `channel_system.rs:15:24/52:6 → 16:24`, `detection.rs:95:22`.

The pinned-oracle disposition above is unchanged: regenerate only in the
post-gitlink-advance commit, which then also absorbs the shifted kwavers site.

### Conformance check decomposition (peer in-flight state)

- `apollo/oversized_files 38→39`, `root_sprawl 0→1`, `target_forks 0→1`,
  `moirai/manifest_implementation 25→26`, `moirai/crate_level_allows 16→20`:
  uncommitted in-flight work in those members' trees observed all session
  (apollo's AVX edit mid-iteration this session).
- `<meta>/member_namespace_pollution 0→1`: `repos/prometheus/` — a checkout
  created/touched mid-session (12:36 today), neither registered nor ignored.
  Same promotion-mid-flight pattern as `ares` before its
  register-and-ignore commit; left untouched for the owning stream.
- The three tightenings (CFDrs oversized 141→140, allow_sites 92→91, eunomia
  manifest 3→2) are peer progress in the right direction.

Every red is attributable to documented peer in-flight state, none to this
session's deliverables; each flips green when its owning stream lands.
