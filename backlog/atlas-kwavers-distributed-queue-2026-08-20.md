<a id="atlas-kwavers-distributed-queue-2026-08-20"></a>
## ATLAS-KWAVERS-DISTRIBUTED-QUEUE-2026-08-20 — close queue completion and deadline contracts [patch] — in-progress

- **Owner:** current Atlas session; detached Kwavers checkout with a disjoint
  distributed-scheduler scope while Aequitas hosted book gates run.
- **Claimed scope:** `crates/kwavers-analysis/src/distributed/{queue,scheduler,task,mod}.rs`;
  preserve the checkout's peer-owned medium, physics, and ADR changes.
- **Baseline findings:** `wait_all` observes only queued work after workers
  remove tasks, so it can return while the last task is executing; worker idle
  handling polls with a fixed sleep; deadline construction wraps on
  `u64::MAX` overflow.
- **Acceptance:** queue completion waits for both queued and executing work;
  workers block on scheduler state notification; overflowing deadlines return
  the existing typed invalid-input error; deterministic value-semantic tests
  cover active-task completion and the overflow boundary; focused locked
  format, Clippy, nextest, doctest, and rustdoc evidence is collected or the
  exact shared-cache blocker is recorded.
- **Landed provider increment:** Kwavers commits `073a5adbb` and `7245db7e4`
  implement and document the slice. PR [#427](https://github.com/ryancinsight/kwavers/pull/427)
  is open at exact head `7245db7e44a7f461a34ff2d67e5b7f1a76bc69c1`; local
  focused evidence passes, while repository-hosted CI/Architecture runs have
  not yet attached to the reopened PR event.
- **Non-goals:** no changes to the existing peer-owned Kwavers medium,
  physics, visualization, workflow, lockfile, or documentation edits.

