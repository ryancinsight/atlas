<a id="atlas-moirai-seqcst-002"></a>
## ATLAS-MOIRAI-SEQCST-002 — Weakest-ordering audit for Moirai atomics [patch] — todo
- **priority:** tightening
- **outcome:** each Moirai atomic access documents the happens-before edge it relies on (or that none exists) and uses the weakest ordering that provides it, per `standards`: concurrency correctness.
- **next:** re-run the SeqCst inventory against fetched `origin/main`; select one coherent family; apply justified weakest-ordering relaxations, naming each happens-before edge inline.
- **Claimed 2026-10-21, delivering as [Moirai#632](https://github.com/ryancinsight/Moirai/pull/632):** the inventory re-run found every production family already documented (futex mutex fence pair, Chase-Lev gate loom-bounded, MPMC waiter registration, idle bitset Dekker handshake, join-quiescence pair, channel SPSC store/load const); the delivered relaxation names the two cfg(test) hooks' edges (blocking WRITE_CAP and the peak counter at Relaxed, shutdown()'s parking handshake) plus the fs throttle and scheduler lifecycle edges. The workspace bumps to 0.10.1 for the published-crate guard with both locks following, and rustls-webpki 0.103.16 clears RUSTSEC-2026-0382.
- **Acceptance:** focused nextest and `clippy -D warnings` pass on the relaxed family; `loom` coverage where the access is on the lock-free/atomics rung.
- Owner: unclaimed; scope is `repos/moirai`.
