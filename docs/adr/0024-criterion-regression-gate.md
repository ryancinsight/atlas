# ADR 0024: Centralize Criterion regression classification

- Status: Accepted
- Date: 2026-07-20
- Class: `[arch]` `[patch]`

## Context

Apollo, Helios, and Kwavers independently added benchmark-regression scripts.
Each workflow ran its benchmarks once, saved that output as a baseline, and
immediately compared the unchanged output with itself. The checks were
tautological. The scripts also duplicated one implementation and selected an
unjustified 15 percent threshold.

The first Apollo base-then-candidate experiment subsequently reported 31
source-identical regressions. That hosted falsification proves a fixed
execution order confounds code change with thermal, frequency, and runner
drift. One ABBA counterbalanced block removed the fixed-order confound, but
Apollo hosted run `29764170548` still reported twelve apparent regressions
between source-identical production revisions. The remaining result is
confounded with run phase. A pull request changing the benchmark harness also
changes the measurement instrument unless CI pins it across both revisions.

Finally, applying one 95% interval independently to every case does not provide
95% confidence for the benchmark family. The classifier must control
family-wise false regressions without assuming independent runs or cases.

## Decision

Atlas owns one Rust tool at `tools/criterion-regression`. Consumer CI:

1. holds the candidate benchmark harness constant across both revisions;
2. runs one ABBA counterbalanced replication and one phase-reversed BAAB
   replication on one runner, producing the complete schedule `A B B A B A A
   B`;
3. computes the required per-case confidence as `1 - 0.05 / m`, where `m` is
   the number of benchmark cases in the saved baseline;
4. supplies that confidence to all four Criterion comparison runs;
5. retains each completed `target/criterion` tree under its execution order;
   and
6. runs an exact-commit Atlas `check-replicated-counterbalanced` command.

A candidate slowdown requires the candidate-versus-baseline interval to be
wholly positive in baseline-first execution and the
baseline-versus-candidate interval to be wholly negative in candidate-first
execution in both replications. Across the eight run positions, each revision
has a position sum of 18 and a squared-position sum of 102. The complete
schedule therefore balances revision exposure for constant, linear, and
quadratic period terms. The tool also requires identical benchmark universes,
complete change estimates, and the derived confidence level in all four
comparisons.

For `m` cases with per-case interval miscoverage `alpha`, Bonferroni's
inequality gives family-wise miscoverage at most `m * alpha` without an
independence assumption. A replicated false regression is a subset of an
interval miss in the first replication's baseline-first comparison. Selecting
`alpha = 0.05 / m` therefore bounds the probability of any false regression
in the family by 5%; requiring three additional agreeing intervals does not
weaken that bound or require independence. This is the simultaneous-interval
construction in the
[NIST/SEMATECH handbook][nist]. Criterion documents that its confidence level
is configurable and records that level in the estimate consumed by the tool.

The consumer pin is an exact Atlas commit. Tool evolution lands in Atlas
first, then consumers advance that pin through reviewed commits.

## Rejected alternatives

- Package-owned copies retain three sources of truth and had already drifted.
- A fixed percentage threshold is empirical and discards measured uncertainty.
- One fixed execution order was rejected by hosted falsification.
- One ABBA block was rejected by the second hosted falsification because it
  did not balance benchmark exposure across run phases.
- Default 95% per-case intervals were rejected because their family-wise error
  grows with the benchmark count.
- Assuming independent execution orders would permit a less conservative
  threshold but is unsupported on one shared runner.
- A committed historical timing file compares different runner conditions and
  cannot isolate a code change without controlled hardware.
- A moving `main` download makes CI behavior non-reproducible.

## Consequences

- Pull-request benchmark jobs execute eight benchmark passes, increasing job
  duration while preserving the full benchmark workload.
- The candidate harness measures both revisions. Harness performance itself is
  outside this gate; a harness-only change must be validated separately.
- Benchmark additions or removals fail closed until both order-specific
  universes match inside and across both replications.
- Phase-reversed replication controls constant, linear, and quadratic period
  imbalance in the complete schedule. It does not prove immunity to arbitrary
  runner noise; hosted source-identical canaries remain required evidence.
- Push jobs may exercise the benchmark suite without classification because a
  push event has no pull-request base contract.
- Atlas is a CI-tool dependency for consumers, not a build or runtime
  dependency.
- Regression evidence remains statistical performance evidence; static gates
  and tool unit tests establish classifier correctness only.

## Verification

- Synthetic nested Criterion fixtures cover replicated regression,
  one-phase slowdown rejection, missing comparisons, within-replication and
  cross-replication benchmark-universe mismatch, insufficient family-wise
  confidence, and malformed input.
- Boundary tests reject path-traversing baseline names and absent baselines.
- The tool passes format, check, warning-denied Clippy, nextest, doctest, and
  rustdoc gates.
- Each consumer workflow must pass exact-head hosted CI after adopting the
  pinned tool.

## Relates to

- ADR 0010: cross-repository integration cadence.
- ADR 0011: Atlas-meta ownership and disjoint consumer delivery.

[criterion]: https://bheisler.github.io/criterion.rs/book/user_guide/command_line_options.html
[nist]: https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm
