<a id="slop-burndown"></a>
## ATLAS-SLOP-BURNDOWN-2026-09-06 - Measured debt burn-down against the conformance ratchet [patch] - in-progress

Parent: [`#atlas-hygiene-baseline-001`](backlog.md#atlas-hygiene-baseline-001).

- **outcome:** every class in `scripts/atlas-conformance.py` sits at or below
  its recorded baseline, and the scan runs in CI so the next increase fails
  rather than accumulating behind a stale pin.
- **measured 2026-09-06** at `d15afbf5a`, 26 members, ~4,000 sites. The four
  largest classes are `unwrap_production` 724, `manifest_implementation` 662,
  `oversized_files` 614, and `allow_sites` 508; `kwavers` alone holds 260, 286,
  107, and 322 of those. This is a programme, not an increment.
- **resolved 2026-09-06:**

  | Class | Where | What |
  | --- | --- | --- |
  | `target_forks` | apollo, consus, leto | Repo-local `target/` trees forking the shared build cache; deleted |
  | `root_sprawl` | apollo, `<meta>` | Detector corrected for `.provider-identity-baseline`; scratch file relocated |
  | `member_namespace_pollution` | `<meta>` | `repos/prometheus` ignored until its remote exists |
  | `crate_level_allows` | moirai | Nine example `#![allow(dead_code)]` → `#![expect(…, reason)]` ([#263](https://github.com/ryancinsight/Moirai/pull/263)) |
  | `manifest_implementation`, `oversized_files` | leto | `leto-python/src/lib.rs` 576 → 21 lines; tests split beside their subjects ([#174](https://github.com/ryancinsight/leto/pull/174)) |
  | `reexport_shims` | coeus | `RandomScalar` and `FiniteDifferenceAxis` aliases deleted, 51 call sites moved ([#378](https://github.com/ryancinsight/Coeus/pull/378)) |

- **a finding worth more than the fixes.** Several apparent regressions were
  not new debt: measured at each member's *pinned gitlink*, `ritk`'s
  `type_suffixed_fns` was already 71 against a baseline of 69, and `mnemosyne`'s
  pin equals its `main`, so both of its violations were arithmetically
  impossible to have been caused by any commit. **The baseline was recorded
  against revisions the gitlinks had since moved past, so the ratchet was
  measuring stale trees and could not see debt landing behind them.** Advancing
  nine gitlinks immediately surfaced `kwavers` +2 oversized files and +3
  existence-only assertions, and `hephaestus` +1 allow site, none of which the
  gate had reported.
- **so the first fix is the instrument, not the counts.** The ratchet must
  measure what is actually on each member's default branch, and the gitlink
  advance must be routine rather than an occasional sweep — otherwise the gate
  reports on history. Until then a "clean" ratchet run means nothing.
- **`type_suffixed_fns` needs a rule, not a burn-down.** `ritk` has 71, and
  many are protocol-fixed: `read_u8`/`read_u32` on a JPEG-2000 codestream
  reader are operations on a wire format that fixes the type, which
  `standards` explicitly exempts ("a concrete signature is correct when the
  … protocol, storage, I/O, or FFI contract fixes the type"). Renaming them
  would be worse code. The detector cannot tell those from a forked generic
  dimension, so this class needs an exemption mechanism before its count means
  anything.
- **`coeus/target_forks` is resolved, and not the way it was first recorded.**
  It was written up as deferred because 37 GB of it was being written to by
  live `cargo` processes. That judgement was correct but arrived late: a
  background deletion launched before it had already been running and completed
  the removal. All four forks are gone. No harm done — a build cache is derived
  state and any interrupted build re-runs — but the deferral note was wrong
  about what had happened, and the sequencing error is the real lesson: a
  destructive action was in flight while the decision not to take it was being
  made.
- **`apollo/excess_worktrees` genuinely stands:** three trees, two held by peers
  with commits in the last twenty minutes. A lane migrates at its item's
  completion, never under a running process.
- **the shared cache is 779 GB.** `performance_engineering` makes build and
  artifact size a tracked budget with eviction on a committed cadence, and
  there is no such cadence here — the four forks were the visible symptom of an
  unbounded store, not the store itself. Filed as
  `#shared-cache-unbounded`.

