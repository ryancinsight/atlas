<a id="atlas-kwavers-alloc-probe-deny-docs-2026-08-21"></a>
## ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 — Pilot deny(missing_docs) [patch] — in-progress

The `missing_deny_docs` assessment found 114 of 118 flagged crates have
undocumented public items, so the directive cannot be safely added without
per-crate provider work. This pilot picks the one crate that is trivially
safe — `kwavers-alloc-probe` — a single-file crate (no submodules) with
every public item already documented, to demonstrate the pattern and drop
the count by one.

**Scope:** `crates/kwavers-alloc-probe/src/lib.rs` on a clean lane based on
fetched `origin/main` `377a98c8`, plus root PM records.

**Acceptance:** `#![deny(missing_docs)]` compiles without missing-docs errors;
format, check, warning-denied Clippy, nextest, doctests, and rustdoc pass;
the branch is published for review.

**Implementation evidence (2026-08-21):** clean lane branch
`fix/kwavers-alloc-probe-deny-docs` is based on fetched `origin/main`
`377a98c8670bb4c8c2750a032b1418ceeab60172` and publishes commit
`aa5ab2bc` — one line added after the existing
`#![doc = include_str!("../README.md")]` attribute. Format, check, clippy
(`-D warnings`), nextest (0 tests — probe library), doctests (1 ignored),
and rustdoc all pass on the clean lane.

Published as PR
[#598](https://github.com/ryancinsight/kwavers/pull/598) at exact head
`aa5ab2bc94ba31dbd5f7438aaef41195e9bf5c8e`. Hosted checks are the
acceptance oracle; merge only at the exact PR head after terminal required
checks. The dirty primary Kwavers checkout and Atlas gitlink remain
unchanged.

- **Hosted hold (2026-08-21):** PR #598 is `MERGEABLE` but `UNSTABLE`; all
  25 workflow runs (CI/CD Pipeline `32521893944`, Architecture Validation
  `32521893980`, benchmark regression `32521893996`, Legacy Migration Audit
  `32521894011`, Deploy mdBook `32521894392`) remain `queued` after 56
  minutes of observation across two re-check cycles. CodeRabbit passed;
  `recurseml/analysis` is errored (report-only). No runner has picked up a
  single job. No pointer advance or bypass is authorized; re-open on
  terminal provider checks or a hosted state transition.

