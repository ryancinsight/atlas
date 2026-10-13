<a id="atlas-alloc-count-per-thread"></a>
## ATLAS-ALLOC-COUNT-PER-THREAD — Count test allocations on the measuring thread only [patch] — todo
- Outcome: every stack allocation-budget test counts only the thread under test; libtest main-thread allocations never land in the window.
- Landed 2026-10-12: the wrapper in mnemosyne (`counting::CountingAllocator`, open-window gated in [Mnemosyne #235](https://github.com/ryancinsight/Mnemosyne/pull/235); base wrapper #234). Already on `measure`: athena-leto, harmonia, horae, hyperion, proteus, coeus-ops.
- Remaining: asclepius `crates/asclepius/tests/allocation_instrument.rs` + manifest `stats_alloc` -> `CountingAllocator<System>`+`measure` (critic-approved); locate and migrate kwavers-alloc-probe's hand-rolled counter (not found in the 2026-10-12 pass).
- Oracle: second-thread allocations inside the window read zero for the measuring thread; existing exact budgets hold unchanged.
- priority: verification; needs: none; scope: asclepius test+manifest, kwavers-alloc-probe. Next: the asclepius switch, then kwavers probe, then delete this item. basis: mnemosyne main `8f6ea38`, 2026-10-12.
