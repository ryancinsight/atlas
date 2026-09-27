<a id="atlas-moirai-seqcst-002"></a>
## ATLAS-MOIRAI-SEQCST-002 — Weakest-ordering audit for Moirai atomics [patch] — todo
- **priority:** tightening
- **outcome:** each Moirai atomic access documents the happens-before edge it relies on (or that none exists) and uses the weakest ordering that provides it, per `standards`: concurrency correctness.
- **next:** re-run the SeqCst inventory against fetched `origin/main`; select one coherent family; apply justified weakest-ordering relaxations, naming each happens-before edge inline.
- **Acceptance:** focused nextest and `clippy -D warnings` pass on the relaxed family; `loom` coverage where the access is on the lock-free/atomics rung.
- Owner: unclaimed; scope is `repos/moirai`.
