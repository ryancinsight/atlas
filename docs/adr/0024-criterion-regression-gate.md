# ADR 0024: Centralize Criterion regression classification

- Status: Accepted
- Date: 2026-07-20
- Amended: 2026-07-21
- Closed: 2026-07-22
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

Kwavers exact-head run `29841101698` then completed all four isolated pair
jobs but reported three replicated regressions even though the only production
diff was a line wrap in an unrelated Kalman implementation. Both execution
orders changed, but revision identity remained correlated with two distinct
checkout paths on every runner. The experiment therefore does not isolate the
revision until each pair also holds the source path constant.

Finally, applying one 95% interval independently to every case does not provide
95% confidence for the benchmark family. The classifier must control
family-wise false regressions without assuming independent runs or cases.

Kwavers run `29875283986` completed all four pairs for 190 cases and reported
37 replicated regressions outside the three canonical production targets. The
run finished almost five hours after dispatch and exercised long-horizon and
ancillary scenarios already shown to exceed a finite pull-request budget. It
therefore confirms that the complete statistical universe is not a viable PR
instrument; it does not falsify the bounded target decision below.

## Decision

Atlas owns one Rust tool at `tools/criterion-regression`. Consumer CI:

1. holds the candidate benchmark harness constant across both revisions;
2. materializes both revisions at the same filesystem path inside each pair;
3. runs four co-located base/head pairs: two in `A B` order and two in `B A`
   order, where `A` is the base and `B` is the candidate;
4. computes the required per-case confidence as `1 - 0.05 / m`, where `m` is
   the number of benchmark cases in the saved baseline;
5. supplies that confidence to all four Criterion comparison runs;
6. retains each completed `target/criterion` tree under its execution order;
   and
7. runs an exact-commit Atlas `check-replicated-counterbalanced` command.

A candidate slowdown requires the candidate-versus-baseline interval to be
wholly positive in both baseline-first pairs and the
baseline-versus-candidate interval to be wholly negative in both
candidate-first pairs. Each interval compares revisions on the same machine.
The opposite orders reject an order-confined slowdown. When pair jobs are
isolated, the second pair in each order samples another hosted runner.
Consumers may execute all four pairs serially on one runner or distribute them
across isolated pair jobs when the complete instrument exceeds a finite job
budget. The tool also requires identical benchmark universes, complete change
estimates, and the derived confidence level in all four comparisons.

When even one distributed complete pair exceeds the finite budget, a consumer
may record a canonical merge-critical target set whose existing workloads and
sample counts remain unchanged. Every excluded statistical target must still
execute once on the candidate in the same workflow. This separates functional
benchmark coverage from repeated statistical inference without tuning the
measurement bodies or hiding a failed scenario.

For `m` cases with per-case interval miscoverage `alpha`, Bonferroni's
inequality gives family-wise miscoverage at most `m * alpha` without an
independence assumption. A replicated false regression is a subset of an
interval miss in the first replication's baseline-first comparison. Selecting
`alpha = 0.05 / m` therefore bounds the probability of any false regression
in the family by 5%; requiring three additional agreeing intervals does not
weaken that bound or require independence. This is the simultaneous-interval
construction in the
[NIST/SEMATECH handbook][nist]. Criterion documents that its confidence level
is [configurable from the command line][criterion-cli] and records that level
in the [estimate consumed by the tool][criterion-estimate].

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
  threshold but is unsupported; unanimity preserves the bound without that
  assumption.
- Mixing base and candidate measurements from different runners inside one
  confidence interval was rejected because machine variation would be
  indistinguishable from a revision effect.
- Compiling revisions from distinct fixed checkout paths was rejected after
  Kwavers run `29841101698`; path identity remained correlated with revision
  and three apparent regressions survived both orders and replications despite
  no semantic production delta.
- Repeating every long-horizon scenario statistically on each PR was rejected
  after Kwavers runs `29867760523` and `29875283986`; the first remained active
  after 157 minutes and the second required almost five hours. One-pass
  candidate execution retains scenario coverage without weakening the
  canonical statistical target workloads.
- A committed historical timing file compares different runner conditions and
  cannot isolate a code change without controlled hardware.
- A moving `main` download makes CI behavior non-reproducible.

## Consequences

- Pull-request benchmark jobs execute eight passes of the selected statistical
  universe. A consumer may use four isolated pair jobs and a one-pass complete
  candidate smoke to keep the critical path within its derived job budget.
- The candidate harness measures both revisions. Harness performance itself is
  outside this gate; a harness-only change must be validated separately.
- Benchmark additions or removals fail closed until both order-specific
  universes match inside and across both replications.
- Phase-reversed replication rejects an effect confined to one execution
  order. Isolated pair runners expose runner variation but do not prove
  immunity to arbitrary hosted noise; hosted source-identical canaries remain
  required evidence.
- Criterion report roots do not encode runner or source-path identity. The
  classifier cannot prove pair co-location or path equivalence; consumer
  workflow review and hosted execution establish those preconditions.
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
- Kwavers exact bounded head `a85aa58e5` passes complete candidate smoke, all
  four 21–23 minute AB/BA pair jobs, and aggregate classification in run
  `29884797777`; PR #306 merged that workflow as `00d06f00e`.

## Relates to

- ADR 0010: cross-repository integration cadence.
- ADR 0011: Atlas-meta ownership and disjoint consumer delivery.

[criterion-cli]: https://github.com/bheisler/criterion.rs/blob/0.4.0/src/lib.rs#L812-L816
[criterion-estimate]: https://github.com/bheisler/criterion.rs/blob/0.4.0/src/estimate.rs#L27-L32
[nist]: https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm
