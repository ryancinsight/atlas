<a id="atlas-kwavers-swe3d-baseline-regression-2026-08-26"></a>
## ATLAS-KWAVERS-SWE3D-BASELINE-REGRESSION-2026-08-26 — integration oracle regression on main [major] — in-progress

- **Owner:** unclaimed; scope: `repos/kwavers` (integration baseline + SWE 3D
  validation test).
- **Symptom.** Architecture Validation → Test Suite Coverage on **main**
  fails with: `integration regression: kwavers::swe_3d_validation
  volumetric_tracking_covers_non_pml_domain` (1 of 681 integration tests;
  "Refresh with: scripts/integration_tests.py --update" suggested by the
  gate). Present in main runs 32921558574 and 32914486868 — the check has
  been red on the default branch across at least two runs.
- **Not caused by any open PR:** kwavers PR #650 (CSR interpolator) shows the
  identical failure while its 5,764-test lib suite passes; evidence comment
  recorded on the PR.
- **Decision needed before mechanical refresh:** the gate offers
  `--update`, but refreshing an oracle to make a red gate green hides a real
  numerical change if one occurred. First diff the stored baseline against a
  local run of `volumetric_tracking_covers_non_pml_domain`: if the delta is a
  genuine solver-behavior change, find the merging commit that moved it
  (`git bisect` over recent main merges: #622 run-compiled-tests, #638 viz
  config unify, #640 learning-rate schedule are candidates); if it is
  platform noise (the baseline was regenerated on a different runner), then
  `--update` is the correct fix and should note that in its commit.
- **Local diagnosis 2026-08-26:** the current Kwavers main tree has an empty
  integration baseline, and the focused test passes unchanged:
  `volumetric_tracking_covers_non_pml_domain` reports `100.0%` coverage and
  `12,544` valid points, matching `(40 - 2*6) * (40 - 2*6) * (28 - 2*6)`.
  The failure is therefore not reproducible from the current source and no
  baseline refresh is justified. The hosted runs remain historical evidence;
  the item stays open until a fresh full hosted integration run confirms the
  baseline is green.
- **Full local integration run 2026-08-26 (head `9982b37f`, the merge that
  absorbed the right-sized-grid fix `252d86716`):** `cargo nextest run -p kwavers
  --tests --no-default-features --features full --test-threads=1 --no-fail-fast`
  reports `681 tests run: 681 passed (9 slow), 27 skipped`, `Summary [266.087s]`,
  zero `FAIL` and zero `TIMEOUT` lines. The 60×60×40 grid that timed out hosted
  runners is gone; the 40×40×28 grid keeps every non-PML voxel asserted by the
  test and the sweep runs in 4 m 26 s locally, comfortably below the 25-minute
  script bound and the 45-minute coverage job bound. The local
  `scripts/integration_tests.py` cannot enforce here because the Atlas overlay
  Cargo.lock is stale against the `--locked` flag it carries; that is an
  environment blocker, not a regression.
- **Status:** local evidence closes the diagnosis; the item stays open until a
  fresh hosted integration run at the merge head returns `success`. A
  `--update` is not justified, because no test is currently failing and an
  empty baseline is the correct shape.
- **Local escape restored (kwavers PR #653 at `8165488c2`, merged 2026-08-26):**
  `scripts/integration_tests.py` was made unconditionally `--locked` when the
  baseline was eliminated, which makes the gate unrunnable on a tree under
  the Atlas development overlay (the overlay redirects first-party crates to
  local paths, so cargo refuses before the suite starts). The PR adds an
  `--unlocked` flag that drops the flag for local runs; CI keeps the locked
  default, so the committed-lockfile check is unchanged. All 24 real hosted
  checks pass on the exact head (lockfile 1m36s, audit burn 8m, audit legacy
  2m, all feature combinations 5–19m, build stable/beta/nightly 1–7m, CUDA
  10m, code coverage 32m, code quality 10m, doc 14m, heavy validation split
  legs 7–14m, integration runner windows 1m, layer boundary 21s, miri 4m, PINN
  feature 12m, python typed 1m, security 2m, solver validation 6m, test suite
  coverage 40m, validate clean architecture 3m). The local `--unlocked` run
  reproduces the canonical evidence from the prior diagnosis:
  `integration suite: 681 tests run, 0 failed; no regressions; 0 known
  failures unchanged` (matching the empty baseline). The command-form check
  that earned its place — splitting `--color --locked` at the wrong index
  produces a silent nonsense value with no `--locked` — is now part of the
  test surface. `recurseml/analysis` is the always-report-only error.
- **Acceptance:** main's Test Suite Coverage green; either the baseline is
  refreshed with a justification, or the solver change that moved the result
  is identified and reviewed. The local escape is now in place so the next
  hosted regression can be diagnosed against the same gate the CI runs,
  without reconstructing the command by hand.
- **Two new integration regressions observed locally 2026-08-26** at
  the post-`#653` / `apollo-fft`-signature-fix tip `dddb75c12` (the same
  tip the SWE 3D sweep is run from):
  1. `pstd_finite_window_born source_phasing_is_frechet_derivative`
     panics with `full=6.675873e-3, half=1.121181e-2`. The test asserts
     `half.normalized_residual < full.normalized_residual` (Born residual
     must converge under contrast refinement) and the half-resolution
     residual is now larger than the full. The test was added in commit
     `586f16858 fix(kwavers): Eliminate integration baseline` and has no
     history of passing, but no prior sweep caught it because the
     integration runner was only running four named binaries before
     #653. The PSTD solver has had six recent refactors
     (`b2cd15d37 fix(kwavers-physics): a caller's absorption coefficient
     reach the solver`, `b20158763 fix(kwavers-solver): give plugins the
     sources they are handed`, `247b0e97c refactor(kwavers-solver): slice
     fill for CPML scratch`, `4ea703892 refactor(kwavers-solver): remove
     elastic config placeholder`, `a81f8a6e6 refactor(kwavers-solver):
     complete debug field coverage`, plus the elastic/config placeholder
     removal); one of these likely changed the source-phasing path
     without the Born contrast test catching it because the prior runner
     was only running `swe_3d_validation`/`nl_swe_workflow`/`kuznetsov`/
     `absorption_decay`. Bisect is the next step, not a `--update`.
  2. `pinn_ic_validation test_ic_combined_loss_decreases` panics on
     `kwavers-solver` link errors under the dev overlay — the Windows
     rust-lld 17.1 link line and `pyo3-ffi 0.29.2` symbol resolution
     cannot produce the test binary in the local 60s window. The
     integration runner invokes the same `cargo nextest run` invocation
     that compiles the test binary, so the same link error is what
     the CI runner hits. A separate clean-room build with no
     overlay resolves it; the defect is the overlay, not the test.
- **Optimisation lever applied in this item: kwavers PR
  [#664](https://github.com/ryancinsight/kwavers/pull/664) at head
  `03ca874b` switches `scripts/integration_tests.py` from
  `--test-threads=1` to `--profile ci --no-fail-fast`. The committed `ci`
  profile carries `test-threads=4`, the `integration` group cap of
  `max-threads=2`, and the `full-grid-sim` / `gpu` groups'
  `max-threads=1`. The 4-core hosted runner's 681-test sweep went from
  17m28s to (projected) ~8m; the local run was 4m26s of which all but
  2s was the single-threaded serialization. The no-fail-fast intent is
  preserved (`--no-fail-fast` overrides the profile's `fail-fast=true`).
  Re-enable trigger: the test pair above must be passing on the
  current main before the lever can land.

- **ARCH-008 gaia CSG assessment 2026-08-25 — recorded correct-as-jagged.**
  `gaia/src/application/csg/boolean/indexed.rs` sites (`remap_binary_face_soups`
  :254, `components` :1130/:1304) are per-operand face-soup groupings built
  once per boolean operation, each operand's list growing independently — the
  moirai `channel_fusion` pattern. No traversal-hot path; conversion would add
  complexity without a win. Not claimed.
- **ARCH-008 seventh conversion opened off this sweep** — kwavers conservative
  interpolator transfer matrix → CSR (PR #650). The bench's byte-parity gate
  caught that `leto::Array3` indexing is x-major before any timing ran; the
  per-entry unravel stays. Measured: −22% at refine_4, +5% at refine_2
  (win grows with entries-per-row), recorded honestly on the PR.

