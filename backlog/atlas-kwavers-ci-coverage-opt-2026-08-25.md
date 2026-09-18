<a id="atlas-kwavers-ci-coverage-opt-2026-08-25"></a>
## ATLAS-KWAVERS-CI-COVERAGE-OPT-2026-08-25 — Bound full-workspace test topology [perf][patch] — in-progress

- **Owner:** current session; lane `worktrees/kwavers-ci-coverage-opt`,
  branch `perf/kwavers-test-coverage-profile`, PR
  [#642](https://github.com/ryancinsight/kwavers/pull/642) at `e1ecdd231`,
  stacked on PR #641 head `84ba553ef`.
- **Evidence (measured on ryancinsight/kwavers main, successful runs):**
  Architecture Validation wall 33–67m across recent runs, with the job's
  own queueing adding ~30m beyond its longest member; inside it,
  **Test Suite Coverage 35m19s** dominates (next: feature-matrix jobs
  9–14m each, Validate Clean Architecture 11m41s). CI/CD Pipeline runs
  ~37m. All far past the five-minute verification target.
- **Root causes found in Test Suite Coverage:** it had no rust-cache, serialized
  independent tests to one process, and rebuilt the disjoint full-feature
  doctest graph after the large workspace suite.
- **Hosted falsification and correction:** head `5c49bb2c` completed the
  5,759-test suite in 9m43s after an 18m53s cold compile, PINN in 4m01s,
  and bounded full-grid simulations in 4m26s, then exhausted the unchanged
  45-minute cap rebuilding the disjoint full-feature doctest graph. Commits
  `63513fca1` + `ed44d3d52` first moved that doctest to Documentation and
  bounded nextest/Rayon concurrency. Commit `27c88e88b` then corrected the
  profile strategy: Test Suite Coverage stays on the shared dev graph, both
  initial nextest invocations run at two processes with two Rayon workers,
  bounded full-grid binaries retain the default profile's complete
  `full-grid-sim` grouping, and artifact measurement remains `target/debug`.
- **Correctness correction (workload/timeout unchanged):** the proposed O3
  coverage-profile change is removed. Rust instrumentation coverage warns that
  optimized-out functions can make coverage results unprocessable, so an O3
  timing win is not coverage-correctness evidence. `Cargo.toml` has no remaining
  behavior delta; speed comes from the pinned shared cache, bounded 2x2
  concurrency, and eliminating duplicate doctest compilation. YAML, locked
  metadata, diff checks, and independent static review pass.
- **Next:** collect PR #642's hosted rerun; if green, record the new
  Test Suite Coverage duration and tighten the 45-minute timeout toward
  measured + 20% variance in a follow-up commit (bound tightening follows
  evidence, never precedes it).
- **Follow-up sweep 2026-08-25 — full pipeline job-time baseline measured**
  (CI/CD Pipeline run `32877332731`, the successful proteus-mat adoption
  run; own times, sorted):
  | job | own time |
  |---|---|
  | Heavy Validation (reviewed profile) | 41.6 m |
  | Code Coverage | 33.4 m |
  | Build & Test (beta) | 20.2 m |
  | Build & Test (nightly) | 18.6 m |
  | Build & Test (stable) | 17.4 m |
  | PINN Convergence / Benchmark Smoke / Solver Validation / PINN Feature | 11.5–12.9 m each |
  | Code Quality / Miri / Security Audit / Lockfile / Python Surface | 0.9–5.0 m |
  Pipeline wall 136 m, Architecture Validation wall 110 m on the same
  evening — both dominated by hosted-runner queueing (24+ ubuntu-latest
  jobs per PR across the two workflows), not by any single job's work.
  Live confirmation the same hour: PR #647's ci.yml run sat queued
  26 minutes and PR #642's Architecture Validation run 34 minutes
  before their first job started — with every workflow already carrying
  cancel-in-progress concurrency. The residual lever is structural:
  consolidate jobs or add runners; that is a user decision. A same-hour
  snapshot found **25 active workflow runs across seven concurrent peer
  branches** (`fix/kwavers-run-compiled-tests`, `test/kwavers-spectral-
  laplacian`, `ci/kwavers-build-matrix-timings`, and this session's three)
  — the queue is contention between parallel agent lanes on one repo, so
  lane scheduling is part of the fix alongside any job consolidation.
  Two cache defects found and fixed:
  - **Heavy Validation** used a private branch-scoped `actions/cache`
    whose key never matches on PR checkouts — every PR run recompiled the
    workspace from an empty `target/`, which is exactly the cold-cache
    budget its 45 m timeout was sized against (the 2026-08-23 note).
    Switched to the shared-key rust-cache (PR #647, `7cb10de8f`); timeout
    deliberately unchanged until a warm-cache measurement confirms.
  - **Code Coverage** had no cache at all: every run compiled tarpaulin
    0.37.0 from source and refetched registry/git before the instrumented
    build. Added a coverage-dedicated actions/cache (registry + git +
    tarpaulin binary, key separate from the uninstrumented shared key) and
    skip-if-installed (PR #648, `135d1ab89`).
- nextest timeout topology (`nextest.toml`) audited in the same sweep:
  default 60 s per-test / 15 m suite, ci 10 m, heavy 300 s with a
  documented 600 s override for `nl_swe_workflow` — already evidence-based,
  no change.
- **Outcome 2026-08-25 late:** PR #647 (Heavy Validation shared rust-cache)
  merged at `e78a4e8`; its first hosted run already showed Heavy Validation
  41.6 m → 33.6 m with the shared entry restored. PR #642 was folded into the
  peer lane #641 by its owner (`ea504bf`) to avoid a duplicate CI matrix —
  workload preserved. PR #648 (coverage cache) was briefly auto-closed in the
  #647 merge race and reopened; checks re-running.
- **Queue-time quantified across members 2026-08-25 night.** The bottleneck is
  not job duration anywhere anymore — it is hosted-runner wait:
  - athena: wall 30.4 m, own work 3.3 m (queue 15–30 m per job);
  - CFDrs: max queue 59 m against 15 m of own work;
  - ritk: max queue 74 m;
  - coeus: 60 m queue on a single-job run;
  - kwavers: PR #650's checks sat queued 36+ minutes before first start.
  Every workflow already carries cancel-in-progress. The levers are (a) job
  consolidation across the per-member matrices, (b) larger runner quota or
  self-hosted runners, and (c) lane-scheduling discipline between concurrent
  agent sessions. All three are user decisions; the data above is the input.
  Cache fixes like #647/#648/#375 remove the *work* side; queueing now
  dominates every member's PR wall time.
