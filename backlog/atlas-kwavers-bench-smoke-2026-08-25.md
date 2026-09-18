<a id="atlas-kwavers-bench-smoke-2026-08-25"></a>
## ATLAS-KWAVERS-BENCH-SMOKE-2026-08-25 — Bound cold-build benchmark smoke [patch] — in-progress

- **Owner:** current session; lane `worktrees/kwavers-ci-opt`, branch
  `ci/kwavers-build-matrix-timings`, PR #641 at `84ba553ef`. **Scope:**
  Kwavers benchmark-smoke command and its
  directly required CI/cache structure. **Non-goals:** no timeout increase,
  benchmark deletion, reduced target coverage, or production-kernel change
  without profile evidence.
- **Outcome:** every plotting-eligible Criterion target executes once under the
  existing finite bound on a cold hosted runner; compilation and execution are
  separated or consolidated so setup cost cannot consume the smoke budget.
- **Acceptance oracle:** reproduce run `32867271654`, retain the full target
  set, build the bench binaries once as a separately bounded artifact, verify
  the cold build and bounded smoke phases independently, and obtain a terminal
  green hosted plotting feature-matrix leg containing both benchmark steps.
- **Risk/dependencies:** `[patch]`; the completed log proves no Criterion target
  executed: the release-profile compile was still building `proptest` at 29
  minutes and the 30-minute job bound then killed Cargo and Rustc. The
  visualization implementation is unchanged. Completion re-opens
  `ATLAS-KWAVERS-VIS-CONFIG-2026-08-25` for its gitlink advance.
- **Fix:** delete the standalone benchmark job and run one bounded dev-profile
  build plus one bounded `--test` execution in the already-cached plotting
  feature-matrix leg. The leg reuses checkout, toolchain, dependency cache, and
  the exact `--no-default-features --features plotting` graph; static manifest
  enumeration retains all 19 plotting-eligible targets. Cargo's
  `--no-fail-fast` keeps later targets executing after an individual failure.
  Independent review found no remaining issue after duplicate-step,
  feature-fingerprint, and complete-failure-reporting checks.

