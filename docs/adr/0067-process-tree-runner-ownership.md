# ADR 0067: Atlas owns bounded process-tree execution

- Status: Accepted
- Date: 2026-09-29
- Item: `ATLAS-PROCESS-TREE-SSOT-2026-09-29`
- Delivery: [atlas#396](https://github.com/ryancinsight/atlas/pull/396)

## Context

Atlas automation launches commands that may outlive their direct parent. Killing
an already-reaped parent by its numeric process-group identifier can signal an
unrelated process after identifier reuse. Windows has a second race when a
command creates descendants before it is assigned to a Job Object. Metis had a
working supervisor and Job Object implementation, while Atlas's Git wrapper and
other repositories carried weaker or duplicated variants.

Leto also needs bounded Criterion execution in a standalone checkout. Its CI
can consume selected Atlas tooling at an exact revision, so package publication
or a service boundary would add lifecycle and dependency surface without a
current requirement.

## Decision

[scripts/process_tree.py](../../scripts/process_tree.py) is the single Atlas
implementation for bounded standard-library-only subprocess-tree execution.
It owns the complete tree from launch through collection:

- POSIX launches an unreaped supervisor as process-group leader. The supervisor
  reports the command's exit status, then remains alive until group termination,
  so the process-group identifier cannot be reused before cleanup.
- Windows launches a bootstrap held on a control pipe, assigns it to a
  kill-on-close Job Object, then releases it to create the requested command.
- timeout and cleanup each have finite budgets; interruption before destructive
  cleanup completes is retryable while ownership remains held.
- status and byte-exact standard streams remain command results, including an
  optional standard-input payload.

Atlas-specific Git environment sanitation, archive validation, and typed errors
remain in [scripts/atlas_git_process.py](../../scripts/atlas_git_process.py),
which delegates process ownership to the canonical runner.

Standalone consumers use an exact sparse Atlas checkout pinned by a full commit
identifier and verify `HEAD` before importing the helper. They do not copy the
file, consume a moving branch, publish a package, or call a network endpoint.

## Rejected alternatives

- Per-repository copies preserve the duplication and allow safety fixes to
  diverge.
- Publishing a Python package introduces a release boundary for one internal
  file and delays consumers behind publication.
- `taskkill` and post-reap `killpg` do not close the descendant-creation and
  identifier-reuse races.

## Consequences

The focused tests in
[scripts/tests/test_process_tree.py](../../scripts/tests/test_process_tree.py)
exercise normal return, timeout, live descendants, cleanup interruption, and
Windows assignment-before-release. Consumer repositories remain responsible for
their own command budgets and exact Atlas revision validation. Future process
ownership fixes land once in Atlas and consumers advance their pinned checkout.

Overturn this decision if standard-library primitives cannot preserve tree
ownership on a supported host, or if several external consumers justify a
versioned distribution boundary.
