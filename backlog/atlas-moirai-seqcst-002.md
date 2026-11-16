<a id="atlas-moirai-seqcst-002"></a>
## ATLAS-MOIRAI-SEQCST-002 — Weakest-ordering audit for Moirai atomics [patch] — todo
- **priority:** tightening; Owner: unclaimed; scope is `repos/moirai`
- **outcome:** each Moirai atomic access documents the happens-before edge it relies on (or that none exists) and uses the weakest ordering that provides it, per `standards`: concurrency correctness.
- **next:** relaxations delivered in moirai#642 (merged 2026-10-27; #632 closed unmerged). Remaining against the acceptance at moirai origin/main: `loom` coverage of the lock-free deque, which uses `std` atomics (moirai `gap_audit.md` MOI-GAP-CHASE-LEV-LOOM-COVERAGE-001), and the MPMC notifier fence (moirai `backlog.md` MOI-MPMC-NOTIFY-FENCE-COST-2026-09-24). Re-run the SeqCst inventory against fetched `origin/main`, then close the item once both are delivered or moved to their own homes.
- **Acceptance:** focused nextest and `clippy -D warnings` pass on the relaxed family; `loom` coverage where the access is on the lock-free/atomics rung.
