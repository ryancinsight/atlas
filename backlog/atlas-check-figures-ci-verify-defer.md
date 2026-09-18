<a id="atlas-check-figures-ci-verify-defer"></a>
## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — in-progress

- **outcome:** the wired `prebook check-figures` SSOT drift lint is
  verified end-to-end in hosted CI, incl. a captured
  `DRIFT_DOCS_NOT_IN_SPECS: N` log line on a deliberate drift fixture.
- **status:** local lint proven clean. PR #31 (HELIOS) was the e2e
  attempt: the check fired but the PR had 5 failing jobs, so auto-merge
  correctly short-circuited; main HEAD verified green independently.
- **open:** on `codex/helios-book-figures-closeout` (`e66a16afcd7`):
  `cargo fmt -p xtask` + amend; drop `--locked` from the maturin and
  `cargo bench --no-run` CI steps. Re-push, open follow-up PR, confirm
  the `SSOT_IN_SYNC` log capture.
- **evidence:** `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.
