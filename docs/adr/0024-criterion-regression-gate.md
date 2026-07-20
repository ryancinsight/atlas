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

Criterion already computes a bootstrap confidence interval for relative
change when the head run names a saved base run. A cross-package policy should
consume that statistical result rather than recreate benchmark statistics or
maintain package-specific copies.

## Decision

Atlas owns one Rust tool at `tools/criterion-regression`. Consumer CI:

1. checks out the pull request base revision;
2. runs Criterion with `--save-baseline atlas-base`;
3. checks out the head revision on the same runner while preserving
   `target/criterion`;
4. runs Criterion with `--baseline atlas-base`; and
5. runs a pinned Atlas revision of `criterion-regression`.

The tool recursively discovers every named baseline, reads Criterion's
relative median-change confidence interval, and reports a regression only
when the interval's lower bound is above zero. A baseline benchmark without a
change estimate fails closed because a removed, renamed, or skipped benchmark
must not silently reduce coverage.

The consumer pin is an exact Atlas commit. Tool evolution lands in Atlas
first, then consumers advance that pin through reviewed commits.

## Rejected alternatives

- Package-owned copies retain three sources of truth and had already drifted.
- A fixed percentage threshold is empirical and discards Criterion's measured
  uncertainty.
- A committed historical timing file compares different runner conditions and
  cannot isolate a code change without controlled hardware.
- A moving `main` download makes CI behavior non-reproducible.

## Consequences

- Pull-request benchmark jobs run both base and head measurements on one
  runner, increasing benchmark-job duration.
- Push jobs may exercise the benchmark suite without classification because a
  push event has no pull-request base contract.
- Atlas is a CI-tool dependency for the three consumers but is not a build or
  runtime dependency.
- Regression evidence remains statistical performance evidence; static gates
  and tool unit tests establish only classifier correctness.

## Verification

- Synthetic nested Criterion fixtures cover positive, zero-overlapping, and
  missing comparison results.
- Boundary tests reject path-traversing baseline names and absent baselines.
- The tool passes format, check, warning-denied Clippy, nextest, doctest, and
  rustdoc gates.
- Each consumer workflow must pass exact-head hosted CI after adopting the
  pinned tool.

## Relates to

- ADR 0010: cross-repository integration cadence.
- ADR 0011: Atlas-meta ownership and disjoint consumer delivery.
