<a id="atlas-kwavers-bench-smoke-2026-08-25"></a>
## ATLAS-KWAVERS-BENCH-SMOKE-2026-08-25 — Bound cold-build benchmark smoke [patch] — in-progress

outcome: every plotting-eligible Criterion target executes once under the existing finite bound on a cold hosted runner, with compilation and execution separated so setup cost cannot consume the smoke budget.
- Acceptance oracle: reproduce run `32867271654`, retain the full 19-target set, build bench binaries once as a separately bounded artifact, verify cold-build and bounded-smoke phases independently, obtain a terminal green hosted plotting feature-matrix leg.
- Cause: the release-profile compile was still building `proptest` at 29 minutes when the 30-minute job bound killed Cargo/Rustc — no Criterion target ever ran.
- Fix applied: delete the standalone benchmark job; run one bounded dev-profile build plus one bounded `--test` execution inside the already-cached plotting feature-matrix leg (reuses checkout/toolchain/dependency cache and the exact feature graph); `--no-fail-fast` keeps later targets running after an individual failure. Independent review found no remaining issue (duplicate-step, feature-fingerprint, complete-failure-reporting checks).
- Lane: `worktrees/kwavers-ci-opt`, branch `ci/kwavers-build-matrix-timings`, PR #641 at `84ba553ef`.
- Re-open: completion re-opens `ATLAS-KWAVERS-VIS-CONFIG-2026-08-25` for its gitlink advance.
