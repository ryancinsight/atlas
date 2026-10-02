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
Ownership is membership in a kernel container from launch through collection,
and its completeness differs by host:

- Windows owns every descendant: the Job Object permits no breakaway, so even a
  detached child created with its own process group stays a member.
- POSIX owns every descendant that remains in the supervisor's process group. A
  descendant that calls `setsid` or `setpgid` leaves the group, and `killpg`
  cannot reach it; git's detached auto-gc is one such process. The runner does
  not claim to contain it, and a hard-killed caller leaves the POSIX group
  running, whereas Windows retires the tree when the job handle closes.

The mechanisms:

- POSIX launches an unreaped supervisor as process-group leader. The supervisor
  reports the command's exit status, then remains alive until group termination,
  so the process-group identifier cannot be reused before cleanup.
- Windows creates the requested root process suspended, assigns it to a
  kill-on-close Job Object, then resumes its initial thread. An absent input
  payload leaves standard input inherited from the caller.
- timeout and cleanup each have finite budgets; a `KeyboardInterrupt` before
  destructive cleanup completes is retried while ownership remains held, and
  any other exception raised by cleanup propagates unchanged.
- optional input is delivered concurrently with deadline observation, so pipe
  backpressure cannot delay timeout or cleanup.
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

The focused tests exercise normal return, timeout, live descendants, cleanup
interruption, and standard-input delivery in
[scripts/tests/test_process_tree.py](../../scripts/tests/test_process_tree.py)
and
[scripts/tests/test_process_tree_cleanup.py](../../scripts/tests/test_process_tree_cleanup.py).
[scripts/tests/test_windows_process.py](../../scripts/tests/test_windows_process.py)
opens handles to a descendant chain and a detached child before termination and
asserts each is signalled when `run` returns on normal exit and on timeout, and
within the cleanup budget after the caller is hard-killed; it also pins
Windows API failure reporting. Suspended assignment-before-resume ordering is
pinned in the first file. The POSIX escape above has no test: it is a limit,
not a behavior. Consumer repositories remain
responsible for their own command budgets and exact Atlas revision validation.
Future process ownership fixes land once in Atlas and consumers advance their
pinned checkout.

Overturn this decision if standard-library primitives cannot preserve tree
ownership on a supported host, or if several external consumers justify a
versioned distribution boundary.
