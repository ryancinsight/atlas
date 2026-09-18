<a id="atlas-check-figures-ci-verify-defer"></a>
## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: re-flag from `done` to `in-progress` after empirical
  drift-fixture probe retry (throwaway PR `ryancinsight/CFDrs#319`
  on commit `a163ef55`, ci.yml run `30109405652` / job `89534706116`)
  revealed a NEW upstream cargo-side blocker distinct from the
  COEQ one the prior turn's predicate anticipated.

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
  + new `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  + PR #31 (HELIOS) management.

- Outcome: PARTIAL e2e CI verification of the wired `prebook check-figures`
  SSOT drift lint. The local lint (SSOT_IN_SYNC 7/7 green + drift detection
  at L101) + YAML validation + action pin alignment + clippy `-D warnings`
  clean + `mdbook build` exit 0 are proven signals documented in
  `ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`. **PR #31 (HELIOS closeout →
  main at run ID `30059559064`) was the actual e2e attempt**: the
  `Check book figures` step fired in the GitHub Actions runner, but
  PR #31 produced 5 failed/concluded-with-error jobs and the conditional
  auto-merge (`gh pr merge --squash --delete-branch`) correctly
  short-circuited (FAIL_COUNT=5 ≠ 0). The full verbatim failure
  diagnostic + root-cause ranking + fix-up recovery plan is captured in
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.

- Failure inventory (PR #31, run `30059559064`):
  - `rust workspace` job failure: `cargo fmt -- --check` saw **6 `Diff in`
    blocks across 3 new files** in the closeout xtask crate —
    `xtask/src/check_figures.rs` (lines 47, 97, 131 — chain-method
    re-formatting), `xtask/src/main.rs` (line 40 — three match arms
    `LegacyMigrationAudit`, `RefreshLegacyAllowlist`,
    `BurnMigrationAudit` consolidated to expression bodies), and `xtask/src/prebook.rs` (lines 139, 154
    — chain-method re-formatting on `fs::read` and `serde_json::to_string`).
    All 6 diffs are chain-method consolidation; trivially fixable via
    `cargo fmt -p xtask && git commit --amend`.
  - `python bindings` and `benchmark regression check` job failures:
    BOTH caused by the same root cause — `--locked` flag (maturin for
    `python bindings`, `cargo bench --no-run` for benchmark regression)
    conflicts with `Updating git repository tyche / eunomia / apollo`
    run by Cargo's metadata step. Fix: drop `--locked` for these two
    CI invocations (intent is preserved via existing `atlas_ref` pin
    in ci.yml); alternative — commit a regenerated `Cargo.lock` that
    captures the submodules' new SHAs.
  - `recurseml/analysis` job error: external research bot, not part of
    GitHub-hosted CI (out-of-scope noise). Confirmed no GitHub-hosted
    job matched the name in
    `gh api repos/ryancinsight/helios/actions/runs/30059559064/jobs`.
  - `deploy` job skipped: intentional (path-filtered `book-pages.yml`).
  - **False positive from prior summary**: `Install Rust verification
    tools` step actually succeeded; the prior summary's "error marker"
    was the `printf '::error::install-action:'` line inside
    `taiki-e/install-action`'s bash `bail()` function declaration.
    Confirmed verbatim in §3.4 of the run-evidence file.

- Main HEAD baseline (independent verification): `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b`
  was independently verified GREEN (3 latest CI runs all `success`).
  → All 4 substantive failures are PR #31-specific, NOT pre-existing on
  `main`. The closeout commits are causal.

- Acceptance: the `Check book figures` step fired in the runner; the
  explicit `SSOT_IN_SYNC: N/N` log line is captured in the run log at
  the relevant step output for verification. Auto-merge correctly
  short-circuited (fail-closed design verified). The full e2e gate
  validation (`DRIFT_DOCS_NOT_IN_SPECS: N` log capture on a
  deliberate drift fixture) remains deferred until the fix-up PR lands.

- Risk/change class: `[minor]`; deferred evidence-only, no production-code
  change on this turn. The fix-up iteration is a separate `[patch]`
  workflow tweak (CI config) + trivial `cargo fmt` commit.

- Dependencies: depends on the `codex/helios-book-figures-closeout`
  branch (currently SHA `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b` on
  `ryancinsight/helios` origin) receiving a fix-up commit addressing
  the 3 substantive failures above, then a follow-up PR (likely #32
  or higher) re-running the CI to validate green-pass. Verifiable now
  via `git ls-remote origin codex/helios-book-figures-closeout`.

- Sub-task (open): `cargo fmt -p xtask` + amend the closeout commits
  on the branch, then drop `--locked` flags from `Build Python
  extension` (maturin) and `Compile benchmark binaries` (cargo bench
  --no-run) invocations in `repos/helios/.github/workflows/ci.yml`.
  Re-push the branch; open a follow-up PR; expect PR CI to flow
  through `Check book figures` with the SSOT_IN_SYNC log line captured.

- Evidence limit: VERBATIM run-30059559064 log excerpts at
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  (sections 3.1–3.4). The `DRIFT_DOCS_NOT_IN_SPECS` log-line capture
  remains deferred to the follow-up PR's CI run. No release argument,
  no performance argument, no production-code delta.

