<a id="atlas-alloc-count-per-thread"></a>
## ATLAS-ALLOC-COUNT-PER-THREAD — Count test allocations on the measuring thread only [patch] — todo
- Outcome: every stack allocation-budget test counts allocations made by the thread under test, so libtest's own main-thread allocations never land in the measured window.
- Evidence: `stats_alloc` counts process-wide. ryancinsight/horae#80 traced a `left: 4, right: 0` failure to libtest's main thread allocating after spawning the test thread, and fixed horae alone. The same `Region::new` pattern is in asclepius `crates/asclepius/tests/allocation_instrument.rs`, harmonia `tests/allocation.rs` and `tests/field.rs`, hyperion `tests/contracts/layout_and_allocation.rs`, proteus `tests/layout.rs`, and athena `crates/athena-leto/tests/allocation.rs`.
- Oracle: per member, a test that allocates on a second thread inside the window still reads zero for the measuring thread, and the existing budgets hold unchanged.
- priority: verification
- needs: none
- scope: mnemosyne (the wrapper), then the six test files above and their manifests; horae moves off `allocation-counter` with them.
- Next step: land one per-thread counting `GlobalAlloc` wrapper, generic over the inner allocator, in mnemosyne, then switch each member to it. `allocation-counter` (horae#80's choice) installs its own global allocator, so it conflicts with athena's deliberate `StatsAlloc<Mnemosyne>`; kwavers-alloc-probe and the leto and coeus-ops tests hand-roll counters the wrapper replaces.
