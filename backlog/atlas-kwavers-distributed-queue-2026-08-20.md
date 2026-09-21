<a id="atlas-kwavers-distributed-queue-2026-08-20"></a>
## ATLAS-KWAVERS-DISTRIBUTED-QUEUE-2026-08-20 — close queue completion and deadline contracts [patch] — in-progress
- outcome: `wait_all` waits for both queued and executing work (not just queued removal); workers block on scheduler-state notification instead of fixed-sleep polling; deadline construction returns a typed invalid-input error instead of wrapping on `u64::MAX` overflow.
- scope: `crates/kwavers-analysis/src/distributed/{queue,scheduler,task,mod}.rs`; peer-owned medium/physics/ADR changes are preserved untouched.
- next: confirm hosted CI/Architecture runs attach and pass on the reopened PR event before merging.
