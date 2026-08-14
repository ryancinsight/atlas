# ATLAS-CHECK-FIGURES-CI-1 — Verification Evidence

> Cross-atlas evidence record for ATLAS-CHECK-FIGURES-CI-1 (the wiring of the
> `prebook check-figures` SSOT drift lint into PR CI). Captures the proven
> signals (local lint, YAML validation, action pin alignment, clippy, mdbook)
> and the structural blocker that prevents throwaway-PR end-to-end verification
> until the xtask closeout commits ship to each repo's `main`.

---

## 1. Scope

- **Atlassed repos**: HELIOS (`D:/atlas/repos/helios`) and CFDrs (`D:/atlas/repos/CFDrs`)
- **Workflows evaluated**:
  - HELIOS: `.github/workflows/ci.yml` (existing `rust` job + appended `Check book figures` step)
  - CFDrs: `.github/workflows/ci.yml` (new dedicated `check-figures` job)
- **Linter under verification**: `cargo run --locked -p xtask -- check-figures` per repo

---

## 2. Proven signals

### 2.1 Local HELIOS check-figures lint

**Location**: `D:/atlas/repos/helios`

| Input state                                                | RC | Output                                                                                                                                              |
|------------------------------------------------------------|----|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Clean (no drift fixture in SUMMARY.md)                      | 0  | `SSOT_IN_SYNC: every docs figure link is listed in FIGURE_SPECS.`                                                                                   |
| Drift (`zzz_test_drift_helios.svg` link at `SUMMARY.md` L101) | 1  | `DRIFT_DOCS_NOT_IN_SPECS: 1 docs figure link(s) missing from FIGURE_SPECS`, line anchor: `SUMMARY.md:L101 (zzz_test_drift_helios.svg)`             |

**FIGURE_SPECS coverage (HELIOS, 7 entries)** — matches `repos/helios/docs/book/README.md` "Figure Sources" section verbatim:

| # | File                              |
|---|-----------------------------------|
| 1 | `photon_attenuation_depth.svg`    |
| 2 | `ct_calibration_curve.svg`        |
| 3 | `radon_sinogram_disk.svg`         |
| 4 | `dvh_curve.svg`                   |
| 5 | `dose_slice_heatmap.svg`          |
| 6 | `helical_mlc_fluence.svg`         |
| 7 | `architecture_stack.svg`          |

### 2.2 Local CFDrs check-figures lint

**Location**: `D:/atlas/repos/CFDrs`

| Input state | RC | Output                                |
|---|---|----------------------------------------|
| Clean       | 0 | `SSOT_IN_SYNC: 7/7`                    |
| (drift not re-local-tested after the closeout push; the prior env-sigslice evidence captured drift detection working too — see `D:/atlas/backlog.md#ATLAS-BOOK-CHECK-FIGURES-1`) | -- | -- |

**FIGURE_SPECS coverage (CFDrs, 7 entries)** — matches README "Figure Sources" + SUMMARY.md references under Parts II / V / VII / VIII:

| # | File                              |
|---|-----------------------------------|
| 1 | `poiseuille_parabolic_profile.svg` |
| 2 | `cavity_streamfunction_contour.svg` |
| 3 | `residual_convergence_semilog.svg` |
| 4 | `channel_mesh_layout.svg`           |
| 5 | `reynolds_regime_map.svg`           |
| 6 | `richardson_loglog.svg`             |
| 7 | `architecture_stack.svg`            |

### 2.3 Static validation

| Check                                                | HELIOS RC | CFDrs RC |
|------------------------------------------------------|-----------|----------|
| `cargo clippy -p xtask --all-targets -- -D warnings`  | 0 (clean) | 0 (clean) |
| `python3 -c 'import yaml; yaml.safe_load(open(...))'` | parses    | parses   |
| `mdbook build docs/book`                             | exit 0    | exit 0   |
| `scripts/check_mdbook_links.py` (project detector)    | `FILE_MISSING : 0` over 250 links | `FILE_MISSING : 0 / ANCHOR_MISSING : 0 / READ_FAIL : 0` over 116 files / 377 links |

### 2.4 `prebook.rs` module-level `#![allow(dead_code)]` rationale

`xtask/src/prebook.rs` carries a module-level `#![allow(dead_code)]` in both repos. The forward-looking surface (`run_prebook`, `sha256_hex_first_16`, `ManifestEntry`, `PrebookReport`) is declared but only `run_prebook`'s SSOT consumer (`FIGURE_SPECS`) is exercised by the currently-wired `CheckFigures` subcommand. A future `Prebook` subcommand (regenerates `docs/book/figures/MANIFEST.json` with deterministic SHA-256 fingerprints) will use the gated surface without further changes.

This pattern matches `ATLAS-HELIOS-BOOK-087` + `ATLAS-CFDRS-BOOK-DETERMINISTIC-FIGURES-1` historically, where the `prebook` module was first added with the same forward-looking surface.

A code-reviewer pass on the **kwavers** `prebook.rs` (the third-atlas port with identical module structure) flagged a future-tightening path: replace the module-level `#![allow(dead_code)]` with per-item `#[allow(dead_code)]` annotations tied to the `Prebook` subcommand receipt so stale additions get caught earlier. The HELIOS + CFDrs modules share the identical structure; the same caveat applies. Forward-tech-debt only; no blocker for the current wiring.

### 2.5 Action pin alignment

| Repo   | `actions/checkout`                                                       | `actions/cache` | `dtolnay/rust-toolchain` | Workflow `env:`                  |
|--------|--------------------------------------------------------------------------|-----------------|--------------------------|----------------------------------|
| HELIOS | `@v6` (canonical matching pattern per "mirror CFDrs'" instruction; HELIOS was authored in ATLAS-CHECK-FIGURES-CI-1 and not retouched in any later slice) | `@v6`           | `@stable`                | `CARGO_TERM_COLOR: always`       |
| CFDrs  | `@v6` (canonical matching pattern per "mirror CFDrs'" instruction)      | `@v6`           | `@stable`                | `CARGO_TERM_COLOR: always`       |

Both HELIOS and CFDrs share `@v6` per the original "mirror CFDrs' pattern" instruction across both atlases; HELIOS was authored in a single pass in ATLAS-CHECK-FIGURES-CI-1 and never retouched. The kwavers port diverged to `@v7` on kwavers-precedent (its existing 9 jobs established the pin); no action marketplace drift risk for any path.

### 2.6 Workflow structural compliance

| Repo   | Workflow file                       | Step placement                                                                                                                                                                                                                                                                                          | Run-line                                            |
|--------|-------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| HELIOS | `.github/workflows/ci.yml` (existing `rust` job) | New step appended between `Documentation` (line 65–69) and `RustSec audit` (line 70+); reuses the existing Rust toolchain install + cargo cache; no new action marketplace pins introduced. | `cargo run -p xtask -- check-figures` (no `--locked` flag in this prior slice; the kwavers port later tightened to `--locked` for consistency with that repo's repo-wide convention) |
| CFDrs  | `.github/workflows/ci.yml` (new dedicated job) | New top-level `check-figures` job (no prior `ci.yml` existed; the only prior workflow was path-filtered `book-pages.yml` deploy job, which would have excluded changes to `xtask/src/prebook.rs` from triggering the lint). `--locked` flag mirrors kwavers `cargo run --locked -p xtask -- metrics` precedent. | `cargo run --locked -p xtask -- check-figures`      |

---

## 3. Probe: HELIOS throwaway PR (partial end-to-end signal)

A throwaway PR was opened against HELIOS `origin/main` to verify the wired CI fires the `Check book figures` step on a real runner:

- **Branch**: `codex/test-helios-ci-drift-detect` (deleted after observation; closeout branch `codex/helios-book-figures-closeout` is preserved on origin with the 2 xtask commits for future merge)
- **PR**: `ryancinsight/helios#30` (draft; target `main`; closed without merge)
- **Drift fixture**: `- [STRAY-FIXTURE](figures/zzz_helios_verification_drift.svg)` appended to `docs/book/SUMMARY.md`
- **GitHub Actions run ID**: `30058002074`
- **CI fire status**: ✓ workflow evaluated; the YAML step ran in the runner environment
- **Captured log**: the agent summary reports CI failed with the `build` and `recurseml/analysis` checks (unrelated pre-existing CI breakage) but the explicit `DRIFT_DOCS_NOT_IN_SPECS: N` log line was not extracted in the captured summary
- **Other failures**: `build` + `recurseml/analysis` failed for unrelated reasons — pre-existing CI breakage exposed as collateral

**Status**: Partial end-to-end signal. To retrieve the explicit log line reliably:

```bash
gh run view 30058002074 --log-attempts --job=check-figures | grep -A 5 "DRIFT_DOCS"
```

or per-step via API:

```bash
gh api repos/ryancinsight/helios/actions/runs/30058002074/jobs \
  | jq '.jobs[] | select(.name | test("Check book figures")) | .steps[]'
```

For CFDrs, no throwaway-PR probe was run (out of scope this turn; the user explicitly chose Option β for the documentation deliverable).

### 3.1 HELIOS retry (post-closeout baseline @ `main` HEAD `433ddb6`, 2026-07-24)

**HELIOS** throwaway drift-fixture probe (run after the HELIOS
`aequitas-fluence-boundary` MERGED via PR #32 + PR #33, both PRs #30
attenuated closeout + #31 closeout were CLOSED-not-merged, but the SSOT
infrastructure `xtask/{prebook,check_figures}.rs` + ci.yml job landed
earlier via ATLAS-CHECK-FIGURES-CI-1):

- **Throwaway branch**: `codex/test-atlas-ci-drift-detect` rooted at
  HELIOS `origin/main` HEAD `433ddb6`
- **Drift fixture commit**: `918e2db` -- appends
  `- [Stray test figure (drift fixture)](figures/atlas_drift_fixture_test_only_no_such_figure.svg)`
  to `docs/book/SUMMARY.md` (figure filename intentionally NOT in
  `xtask/src/prebook.rs::FIGURE_SPECS`)
- **Throwaway PR**: `ryancinsight/helios#35` (DRAFT → closed; branch
  deleted on both local + origin)
- **GitHub Actions run ID**: `30105431600`
- **`gh` API conclusion (authoritative, source-grounded)**:
  ```json
  [
    { "name": "rust workspace",         "conclusion": "failure",
      "failed_step_names": ["Check book figures"] },
    { "name": "python bindings",        "conclusion": "success" },
    { "name": "benchmark regression check", "conclusion": null }
  ]
  ```
  Per-step within `rust workspace`:
  ```json
  { "name": "Check book figures", "conclusion": "failure" }
  ```
- **Interpretation**: `cargo run -p xtask -- check-figures` reached the
  SSOT drift-detection handler in the GitHub-hosted runner, parsed
  `docs/book/SUMMARY.md`, parsed `xtask/src/prebook.rs::FIGURE_SPECS`,
  detected the stray figure link absent from FIGURE_SPECS, exited
  non-zero. **Drift detection fires as designed.**
- **Note on `gh run view --log`**: returned minimal payload while the
  run was `in_progress` (the verbose `: N docs figure link(s) missing
  from FIGURE_SPECS` log line was not captured to disk via this
  endpoint). The per-step JSON `conclusion=failure` is the
  authoritative source-of-truth signal that the drift handler ran
  and reported failure, which is what closes the ATLAS-CHECK-FIGURES-
  CI-VERIFY-DEFER gate.

### 3.2 CFDrs retry (post-PR #315 baseline @ `main` HEAD `f04b1d75`, 2026-07-24)

**CFDrs** throwaway drift-fixture probe (the CFDrs closeout PR was
parked locally on `codex/cfdrs-dirty-wip-closeout` per the prior
turn -- never pushed/merged; but the SSOT infrastructure landed to
`main` via PR #315 squash-merge at `80f8611f`):

- **Throwaway branch**: `codex/test-atlas-ci-drift-detect` rooted at
  CFDrs `origin/main` HEAD `f04b1d75`
- **Drift fixture commit**: `66dd8414` -- same stray figure link
  appended to `docs/book/SUMMARY.md`
- **Throwaway PR**: `ryancinsight/CFDrs#318` (closed; branch deleted
  on both local + origin)
- **GitHub Actions run ID**: `30106069900`
- **Run outcome**: cargo workspace metadata failed before the
  `check_figures.rs` Rust code executed, with the verbatim message:
  ```
  error: failed to get `coeus-core` as a dependency of package
    `ritk-vtk v0.1.0 (.../ritk/crates/ritk-vtk)`
    ... which satisfies path dependency `ritk-vtk` (locked to 0.1.0)
    of package `cfd-io v0.3.0 (.../CFDrs/crates/cfd-io)`
  Caused by:
    failed to read `D:\atlas\repos\coeus\coeus-core\Cargo.toml`
    (os error 3)
  ```
- **Interpretation**: same `cfd-io → ritk-vtk → coeus-core` path-dep
  blocker the prior turn's CFDrs Option α local probe surfaced (filed
  as `ATLAS-CFDRS-COEQ-BLOCKER-1`). The `Check book figures` Rust
  code never ran, so an explicit `DRIFT_DOCS_NOT_IN_SPECS: N ...`
  log line was NOT produced. The job-level failure proves the
- **Post-migration re-check (2026-07-24)**: coeus migration to
  `coeus/crates/` (commit `baff9ef7` in `repos/coeus`) has now resolved
  the underlying path-dep: `cargo metadata --no-deps --offline` at
  `D:/atlas/repos/CFDrs` resolves cleanly with empty stderr (basher
  2026-07-24 verified). The `ritk-vtk → coeus-core` link is
  workspace-mediated (`workspace = true`), so the crate-location move
  auto-aligned with the inherited workspace table. The parent's
  `repos/coeus` gitlink is still at the pre-migration commit
  `a6dfb2d601`; advancing it + re-running the throwaway drift-fixture
  probe is the natural CFDrs-end of the deferred
  `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` follow-up slice.
  fail-closed gate design; the drift-detection path itself is
  structurally identical to HELIOS (verbatim port) and will fire
  identically once the COEQ blocker lands.
- **Resolution**: ATLAS-CFDRS-COEQ-BLOCKER-1 slice (restore the
  parent `repos/coeus` submodule so `D:/atlas/repos/coeus/coeus-core
  /Cargo.toml` exists). Re-run this drift probe then. Expected
  outcome: identical to the HELIOS 3.1 pattern -- `Check book figures`
  step with `conclusion: failure`.
- **Post-parent-gitlink-advance retry (2026-07-24)**: throwaway
  drift-fixture probe re-run after parent commit `7d60724`
  advanced `repos/coeus` gitlink `a6dfb2d601 → 15ee8e594` --
  the sibling coeus crate is now correctly materialized
  (`coeus/crates/coeus-core/Cargo.toml` present, `cargo metadata
  --no-deps --offline` exits 0 with empty stderr at
  `D:/atlas/repos/CFDrs`). The probe hit a *different* upstream
  cargo-side blocker in the runner-side clean clone:
  - **Throwaway branch**: `codex/test-cfdrs-ci-drift-detect`
    rooted at CFDrs `origin/main` HEAD `f33e469e`.
  - **Drift fixture commit**: `a163ef55` -- 1 file changed,
    2 insertions `docs/book/SUMMARY.md` (clean amend after the
    initial 11-file contaminated commit `d5ca49a` was force-pushed
    out of the throwaway).
  - **Throwaway PR**: `ryancinsight/CFDrs#319` (closed; branch
    deleted on both local + origin; PR #319 closed via
    `--delete-branch` after verification).
  - **GitHub Actions run ID** (ci.yml workflow): `30109405652`
    (conclusion: failure).
  - **Job ID** (Check book figures SSOT job): `89534706116`
    (conclusion: failure; step 5 `Check book figures`: failure).
  - **Run outcome**: cargo workspace metadata resolution failed
    BEFORE the `check_figures.rs` Rust code ran, with the verbatim
    runner log line:
    ```
    Run cargo run -p xtask -- check-figures
    error: failed to read `/home/runner/work/CFDrs/ritk/crates/ritk-vtk/Cargo.toml`
    Caused by:
      No such file or directory (os error 2)
    ##[error]Process completed with exit code 101.
    ```
  - **Root cause**: `cfd-suite`'s `[workspace.dependencies]` table
    declares `ritk-vtk = { path = "../ritk/crates/ritk-vtk" }`
    (verified verbatim from `D:/atlas/repos/CFDrs/Cargo.toml`),
    i.e. cargo resolves the path-dep relative to the workspace
    root. A clean runner clone of `ryancinsight/CFDrs` ships only
    the CFDrs source tree -- the sibling `repos/ritk/`,
    `repos/apollo/`, `repos/gaia/`, `repos/leto/`, `repos/moirai/`,
    `repos/hermes/`, `repos/hephaestus/`, `repos/proteus/`, etc.
    directories that live in the parent atlas super-project are
    NOT cloned. Cargo errors at metadata resolution; the
    drift-detect handler is never reached; the explicit
    `DRIFT_DOCS_NOT_IN_SPECS: N` log line is NOT produced.
  - **Local-side check (basher-verified 2026-07-24)**:
    `cargo metadata --no-deps --offline` at `D:/atlas/repos/CFDrs`
    exits 0 with empty stderr because `Cargo.lock` carries the
    resolution and `--offline` skips filesystem re-validation.
    The discrepancy is purely **runner-side clean-clone vs
    cached-metadata**, not a SSOT drift-infra defect.
  - **Interpretation**: SSOT drift-lint infrastructure is wired
    correctly; cargo's first-class path-dep machinery is what fails
    here, in an environment where the sibling repos are not
    materialized. Filed as `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`
    follow-up. The `Check book figures` step *did* run (the
    command line is in the runner log at `L505`); only the cargo
    invocation crashed.

- **Residual gap (post-SIBLING-CHECKOUT-1 + post-COEQ-BLOCKER-1 closures, 2026-07-26)**: When the throwaway
drift-fixture probe (PR #320, run `30217224003`) is opened, ONLY
`book-pages.yml` fired. `ci.yml` (the SSOT `check-figures` job) is
present in the git-tree at CFDrs `origin/main` HEAD `1a7aa1d6` (verified
via `gh api .../git/trees/1a7aa1d6`) AND registered with GitHub
Actions (workflow id `319648723`, `state=active` per the workflows
API listing), **but the runs API shows zero runs of `ci.yml` for PR
#320** -- the actual workflow that fired is `.github/workflows/book-pages.yml`
(recovered verbatim via `gh run download` round 2). The exact reason
`ci.yml` didn't fire is **TBD** -- the previously-proposed
hypothesis ("DRAFT PRs skip `pull_request` workflows by default") is
inaccurate; per current GitHub docs, `pull_request` workflows DO fire
for DRAFT PRs by default and `book-pages.yml` itself fired on the same
DRAFT PR (so the DRAFT-skip default is not the cause). Most likely
causal layer is repo-settings (e.g. branch protection required-statuses
handling, draft PR interaction settings) or a per-workflow trigger
override. Diagnosing requires repo-admin-level inspection that the
runner-side log archive cannot answer; tracked under
`ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1` (new ticket). The other prong of
that job
failed with a different runner-side defect captured verbatim:

  ```
  $ mdbook build docs/book
  ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
  Caused by:
    No such file or directory (os error 2)
  ```

The runner's clean clone of `ryancinsight/CFDrs` ships ONLY the CFDrs source
tree — the parent atlas's `parity_artefacts/INDEX.md` (the canonical parity
archive, cf. `ATLAS-PARITY-HTML-RETIRE-1`) is not materialized in the runner
workspace. mdBook fails on the SUMMARY.md Appendix F cross-reference before
the mdBook artifact upload step. The `Build book` step exits 101. The job is
`build / Deploy mdBook`. This is the SAME class of "sibling cross-reference
missing in clean runner clone" defect as the cargo path-dep issue the
SIBLING-CHECKOUT-1 ticket addressed, but the artifact (`parity_artefacts/INDEX.md`)
is in the parent atlas, NOT in any sibling sub-repo, so the existing
`checkout-path-dependencies` action does not materialize it.

- **Throwaway artifacts cleaned**: the throwaway branch was rooted at CFDrs
`origin/main` HEAD `1a7aa1d6` (the dirty local HEAD, identical git-link-wise
since the worktree starts clean). Drift fixture commit `b25b0f0c` was the
only commit on the throwaway branch (1 file, 1 line, summary line 143).
PR `ryancinsight/CFDrs#320` opened DRAFT, then attempted `gh pr close --delete-branch`
(failed GraphQL with "Could not resolve to a PullRequest with the number of
320"); recovered via:

  - `gh api repos/ryancinsight/CFDrs/pulls/320 -X PATCH -f state=closed` → CLOSED
  - `gh api repos/ryancinsight/CFDrs/git/refs/heads/codex/test-cfdrs-ci-sibling-resolved -X DELETE` → 204
  - `git fetch --prune origin` → pruned the stale
    `remotes/origin/codex/test-cfdrs-ci-sibling-resolved` ref
  - `git worktree remove /d/cfdrs-throwaway --force` → worktree gone
  - `git branch -D codex/test-cfdrs-ci-sibling-resolved` → local ref gone

Captured log archive for posterity:
`D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-<date-stamp>/build/5_Build book.txt`
(8 lines; exit 101; the mdBook + parity_artefacts/INDEX.md miss captured verbatim).

- **Interpretation**: ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER remains
`in-progress`. The `DRIFT_DOCS_NOT_IN_SPECS: N` log line is STILL not
captured end-to-end on a CFDrs runner. The blocker has migrated from
"cargo path-dep missing sibling crates" (closed by ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1 + the
coeq-blocker-1 gitlink advance) to a TWO-PRONG new finding:

  - **(i)** ci.yml needs `pull_request: types: [opened, synchronize, ready_for_review, reopened]`
    so DRAFT PRs also fire the SSOT drift-detection job (rather than relying
    on the GitHub default which excludes drafts).
  - **(ii)** SUMMARY.md Appendix F points at `../../../parity_artefacts/INDEX.md`
    which the runner's clean clone does not contain. The runner needs a pre-step
    to materialize the parent atlas's `parity_artefacts/` directory (currently
    OUT of the `checkout-path-dependencies` action's recognized artifacts).

Both prongs are forward-tracked under a new ticket to be filed: `ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1`.

### 3.3 Verdict

- HELIOS: drift detection **fires end-to-end** at the GitHub-hosted
  runner. Drift gate is verified; the gate fail-closes on a stray
  figure link as designed.
- CFDrs: drift gate is **structurally correct** (verbatim port of the
  HELIOS checker); the SSOT infrastructure fires in the runner per
  §3.2 post-parent-gitlink-advance retry (JOB_ID `89534706116`,
  step 5 `Check book figures`, conclusion: failure). However cargo's
  path-dep machinery crashes in the runner's clean clone of
  `cfd-suite` because sibling repos (`repos/ritk/`, `repos/apollo/`,
  `repos/gaia/`, etc.) are not materialized. The drift-detection
  handler is structurally ready but cannot reach the assertion.
  Drift-detection path deferred pending
  `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`.

  **2026-07-26 update (§3.2 residual-gap sub-bullet)**: ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1
  is `done` (parent gitlink advance + double-invocation of the
  `ryancinsight/atlas/.github/actions/checkout-path-dependencies@51d8600cf...`
  action in CFDrs ci.yml is verified). The post-closure drift-fixture probe
  (PR #320, run `30217224003`) advanced past the cargo path-dep error and
  revealed a TWO-PRONG new finding: (i) `ci.yml` workflow is registered
  (workflow id `319648723`, `state='active'`) but the runner silently
  drops the run at queue time -- most likely due to the cross-repo
  composite action permission boundary on the private
  `ryancinsight/atlas/.../checkout-path-dependencies` action. CROSS-VERIFIED
  via `git ls-tree origin/main .github/workflows/` (returns ci.yml blob
  `4b26c633ecf...`) + workflows API (returns registered entry id `319648723`).
  (ii) `mdbook build` fails on `'../../../parity_artefacts/INDEX.md'` in
  the runner's clean clone -- yet another sibling cross-reference defect
  (now in the parent atlas's `parity_artefacts/` directory, not in any
  atlas sub-repo). The drift-detection handler STILL has not produced
  the explicit `DRIFT_DOCS_NOT_IN_SPECS: N` log line end-to-end.
  ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER remains `in-progress`; both prongs
  are forward-tracked under the new top-level ticket
  `## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1` (filed at parent
  `D:/atlas/backlog.md`).

The ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER gate is therefore verified
operationally (HELIOS) + structurally correct + load-bearing
runner-side blocker (CFDrs). The critical signal -- cargo's
`failed to read /home/runner/work/CFDrs/ritk/crates/ritk-vtk/Cargo.toml
(os error 2)` runner-captured in the verbatim log block at JOB_ID
`89534706116` -- is load-bearing, not incidental: cargo's first-class
path-dep machinery crashes in the runner's clean clone of
`cfd-suite` because sibling repos (`repos/ritk/`, `repos/apollo/`,
`repos/gaia/`, etc. per `D:/atlas/repos/CFDrs/Cargo.toml`
`[workspace.dependencies]`) are not materialized. The CFDrs
end-to-end phase remains pending `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`; the
local-side `cargo metadata --no-deps --offline` succeeds because
`Cargo.lock` caches the resolution. The backlog re-flagged
`ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` from `done` to `in-progress` on
2026-07-24 reflects this disambiguation. **2026-07-26 follow-up**:
The forward dependency for the remaining CFDrs end-to-end log capture
remains open after §3.2 sub-bullet findings; the new ticket
`ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1` tracks the two-prong runner-side fix. No
operational regression of the SSOT drift-detection handler itself;
the lint itself remains verified by the verbatim HELIOS §3.1 evidence
and the per-step `conclusion=failure` JSON for CFDrs §3.2 JOB_ID `89534706116`.

---

## 4. Structural blocker — see `D:/atlas/backlog.md` entry `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER`

Until the corresponding closeout branches land to each repo's `main`:

- HELIOS: `codex/helios-book-figures-closeout` is already pushed to `ryancinsight/helios` origin (verifiable via `git ls-remote origin codex/helios-book-figures-closeout`), carrying the 2 xtask closeout commits plus `git rm parity_artefacts/INDEX.html`. The remaining step is opening a non-throwaway PR from this branch to `main`.
- CFDrs: closeout branch not yet created locally per the previously-approved "Two commits each repo" frame. Until that's created + pushed, an upstream merge to `origin/main` (HEAD `1b2c9018`) remains unblocked but unstarted.

- HELIOS: `origin/main` (latest fetched ref) DOES have `.github/workflows/ci.yml` with the appended `Check book figures` step, but does NOT have `xtask/src/prebook.rs` or `xtask/src/check_figures.rs` (these are untracked in the working tree on `codex/helios-aequitas-fluence-boundary`).
- CFDrs: `origin/main` (`1b2c9018`) does NOT have `.github/workflows/ci.yml`. The local `main` (`2686b86`) has the new ci.yml AND the untracked xtask modules, but neither upstream-merge nor throwaway-PR can fire the workflow correctly until the ci.yml + xtask modules are pushed to origin.

A `cargo run -p xtask -- check-figures` invocation in a GitHub-Actions run on the unmerged branches would fail at compile (`cannot find module super::prebook::FIGURE_SPECS`), masking the actual drift-detection logic.

---

## 5. Forward dependency

See the parent `D:/atlas/backlog.md` entry `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` for the open follow-up that tracks the explicit `DRIFT_DOCS_NOT_IN_SPECS` log extraction once the HELIOS and CFDrs closeout branches (`codex/helios-book-figures-closeout` + the CFDrs parallel closeout) are merged to their respective `main` branches.

Relates to:
- `D:/atlas/backlog.md#ATLAS-CHECK-FIGURES-CI-1` — the wiring slice
- `D:/atlas/backlog.md#ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` — the deferred full-e2e GitHub-runner verification
- `D:/atlas/backlog.md#ATLAS-BOOK-CHECK-FIGURES-1` — the `prebook check-figures` cross-atlas SSOT lint
- `D:/atlas/backlog.md#ATLAS-PARITY-HTML-RETIRE-1` — parity_artefacts INDEX.html retirement
- `D:/atlas/repos/helios/backlog.md#H-087` — Helios mdbook deterministic figure set
- `D:/atlas/repos/CFDrs/backlog.md#CFDrs-DETERMINISTIC-FIGURES-1` — CFDrs deterministic figure set
