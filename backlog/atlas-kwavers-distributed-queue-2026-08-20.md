<a id="atlas-kwavers-distributed-queue-2026-08-20"></a>
## ATLAS-KWAVERS-DISTRIBUTED-QUEUE-2026-08-20 — close queue completion and deadline contracts [patch] — in-progress

- outcome: `wait_all` waits for both queued and executing work (not just
  queued removal); workers block on scheduler-state notification instead of
  fixed-sleep polling; deadline construction returns a typed invalid-input
  error instead of wrapping on `u64::MAX` overflow.
- scope: `crates/kwavers-analysis/src/distributed/{queue,scheduler,task,mod}.rs`;
  peer-owned medium/physics/ADR changes are preserved untouched.
- delivered: Kwavers commits `073a5adbb`, `7245db7e4` implement and document
  the slice. [PR #427](https://github.com/ryancinsight/kwavers/pull/427) is
  open at head `7245db7e44a7f461a34ff2d67e5b7f1a76bc69c1`; local focused
  evidence (format/Clippy/nextest/doctest/rustdoc) passes.
- next: confirm hosted CI/Architecture runs attach and pass on the reopened
  PR event before merging.
