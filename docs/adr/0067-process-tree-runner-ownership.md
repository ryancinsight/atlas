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
Ownership is membership in a kernel container, and its completeness and its
start differ by host:

- Windows owns every descendant: the Job Object permits no breakaway, so even a
  detached child created with its own process group stays a member, and the job
  handle closing with a hard-killed caller retires the tree. The one gap is the
  window stated below, in which the suspended root belongs to no job.
- POSIX owns every descendant that remains in the supervisor's process group,
  and the supervisor retires that group itself when the deadline passes or the
  caller's pipe reaches end of file, so neither a hard-killed caller nor a
  stalled one leaves it running. A descendant that calls `setsid` or `setpgid`
  leaves the group, and neither `killpg` nor the supervisor can reach it; git's
  detached auto-gc is one such process. The runner does not claim to contain it.

The mechanisms:

- POSIX launches an unreaped supervisor as process-group leader, with a pipe
  whose write end only the caller holds. It refuses to start unless it leads its
  group (`killpg` of a group it merely belongs to would kill the caller's),
  reports the command's status, then stays alive, so the group identifier cannot
  be reused, until the group is retired: by the caller, by end of file on the
  pipe, or by the deadline. The last two kill the group, supervisor included,
  with one `killpg` from a watcher thread. A dead caller (killed by any signal)
  closes the pipe and the group is retired at once; a caller alive but stalled
  past the deadline is passed by it, and the supervisor kills at the deadline on
  its own.
- The deadline is one absolute `time.monotonic()` reading taken once by the
  caller, passed to the supervisor and waited for by both, so the sides cannot
  disagree about when it falls whatever the scheduling or the supervisor's
  start-up. `time.monotonic()` reads `CLOCK_MONOTONIC` on Linux, shared by every
  process on the host; `CrossProcessClockTests` pins that a child reads the
  caller's clock. The earlier design gave each side a deadline relative to its
  own start: a supervisor kill that landed first read as end of file before the
  caller's deadline and was reported as an invalid status (found by CI). The
  supervisor now writes `timeout` before it kills at the deadline, the first
  report winning, and the caller classifies by that report, never by clock; end
  of file with no report is a supervisor killed from outside, an error.
- The supervisor is an interpreter started in isolated mode (`-I`). A plain
  `-c` start puts the command's working directory first on `sys.path` and
  honours `PYTHONPATH` and `PYTHONHOME`, so a `subprocess.py` in either would
  replace the module that runs the command (reproduced; `atlas-pin-compile.py`
  runs commands in a materialized member tree). Isolated mode closes both
  routes. The supervisor is the only interpreter the runner starts.
- Windows creates the kill-on-close Job Object, then the requested root
  suspended, assigns the root to the job, then resumes its initial thread. An
  absent input payload leaves standard input inherited from the caller. The root
  belongs to no job from `CreateProcessW` returning inside `subprocess.Popen`
  until `AssignProcessToJobObject` returns, and a caller hard-killed in that
  interval leaves the suspended root running: 98 us at the median, 188 us at the
  maximum over 60 runs (Windows 11, Python 3.13.12). Removing it needs the job
  attached at creation (`PROC_THREAD_ATTRIBUTE_JOB_LIST`), which `subprocess`
  does not expose and which would replace `Popen` with a hand-written
  `CreateProcessW` path.
- On both hosts a `SIGINT` in the main thread is held over the launch window,
  from creating the root until it is owned, and delivered to the caller's
  handler afterwards, so the interrupt retires the owned tree; it is dropped,
  with a note on the exception, when the launch fails, and is not held off the
  main thread. Any other `BaseException` raised after the launch call returns
  retires the owned tree and, on Windows while the root is not yet in the job,
  terminates the root through its handle. An asynchronous exception inside the
  launch call leaves a Windows root running; on POSIX the pipe closes as the run
  unwinds and the supervisor retires its group.
- On both hosts the wait for the command proceeds in slices of 0.1 s, so a
  caller's interrupt is observed within one slice: a Windows process wait and a
  POSIX selector wait are otherwise one kernel call that an interrupt flagged
  without an operating-system signal does not end, delaying it to the deadline.
- A timeout that is not finite and positive is rejected before any launch
  (`ValueError`; a NaN would otherwise busy-loop the wait, a non-number raises
  `TypeError`). The Git wrapper maps them without launching: a deadline of zero
  or less has passed and is a timeout; one that is no finite number (NaN, an
  infinity, `None`, a string) names no instant and is a typed error that is not
  a timeout.
- A timeout carries a cleanup failure in its message and `__cause__` as well as
  `cleanup_error`, so a consumer that only prints the exception sees it.
- Timeout and cleanup each have finite budgets; a `KeyboardInterrupt` before
  destructive cleanup completes is retried while ownership remains held, and
  any other exception raised by cleanup propagates unchanged.
- Optional input is delivered concurrently with deadline observation, so pipe
  backpressure cannot delay timeout or cleanup; status and byte-exact standard
  streams remain command results.

Atlas-specific Git environment sanitation, archive validation, and typed errors
remain in [scripts/atlas_git_process.py](../../scripts/atlas_git_process.py),
which delegates process ownership to the canonical runner.

Standalone consumers use an exact sparse Atlas checkout pinned by a full commit
identifier, verified at `HEAD` before import; they do not copy the file, consume
a moving branch, publish a package, or call a network endpoint.

## Rejected alternatives

- Per-repository copies preserve the duplication and let safety fixes diverge.
- Publishing a Python package adds a release boundary for one internal file.
- `taskkill` and post-reap `killpg` do not close the descendant-creation and
  identifier-reuse races.
- On Windows, the caller assigning itself to a kill-on-close job so that every
  child joins it at creation: job membership is irreversible and inherited by
  everything the caller starts afterwards, so every unrelated child of the
  caller, and the caller, would die when the handle closed; and a caller already
  in a job (a console host, CI) nests under the outer job's limits. The window
  is 0.1 ms, and the job-list attribute above is the exact fix.
- `PR_SET_PDEATHSIG` as the POSIX caller-death mechanism: Linux only, and the
  kernel delivers it when the thread that created the child exits, not the
  process, so a caller launching from a worker thread would lose its supervisor
  early. End of file on a pipe is portable and fires on process death only.

## Consequences

The tests in [scripts/tests/](../../scripts/tests/) cover normal return,
timeout, live descendants, cleanup interruption and failure, input delivery,
supervisor isolation (with a hijacked unisolated control), interrupts inside the
launch window, the 0.1 s wait slice on both hosts, the Git wrapper's typed
outcomes, Windows handle signalling after normal exit, timeout and a hard-killed
caller, and Windows API failure reporting. `test_process_tree_supervisor.py`
runs the supervisor's watchers in process on every host (the `timeout` report,
first-report-wins, the leader check) and, on POSIX, kills a real caller during
the wait and after the status write, drives `run` end to end with a caller
stalled inside its wait to observe the group retired at the deadline `run`
passed, and launches the supervisor directly. The POSIX escape above has no
test: it is a limit, not a behavior.
Consumer repositories remain
responsible for their own command budgets and exact Atlas revision validation.
Future process ownership fixes land once in Atlas and consumers advance their
pinned checkout.

Overturn this decision if standard-library primitives cannot preserve tree
ownership on a supported host, or if several external consumers justify a
versioned distribution boundary.
