<a id="atlas-mnemosyne-08-sweep"></a>
## ATLAS-MNEMOSYNE-08-SWEEP — Every member locks one Mnemosyne generation [correctness] — blocked
- priority: correctness
- outcome: every allowlisted member's default-branch `Cargo.lock` resolves the Mnemosyne 0.8 generation (`mnemosyne-memory` 0.8.0, arena 0.5.0, backend 0.6.0, memory-core 0.3.0, heap 0.5.0, local 0.5.0; Mnemosyne main at or after ryancinsight/Mnemosyne#208), so asclepius and harmonia can take [ATLAS-ALLOC-COUNT-PER-THREAD](atlas-alloc-count-per-thread.md).
- oracle: per member, `cargo metadata --locked` resolves outside the overlay, every `mnemosyne-*` lock entry is at that generation, and `cargo tree -d` lists no duplicate mnemosyne crate.
- landed: hermes, moirai, leto, gaia, apollo, athena (before the sweep); hephaestus (ryancinsight/hephaestus#389), consus (#156), ares (#47), tyche (#94), harmonia (#64).
- in flight: coeus in draft ryancinsight/Coeus#491 (float-only `Mean`, merge held for a judge); metis completes from rescue draft ryancinsight/metis#469 beside open metis#468; ritk source changes parked at rescue draft ryancinsight/ritk#736.
- blocker: asclepius, helios, kwavers and CFDrs need coeus merged and [ATLAS-PROVIDER-VERSIONS-20261002](atlas-provider-versions-20261002.md): Mnemosyne main requires `eunomia` 0.9.0 while those four, and coeus and ritk, still require 0.8 at their default heads, so `cargo update -p mnemosyne-memory` cannot resolve in them.
- re-open trigger: Coeus#491 merged and the eunomia requirement sweep merged for asclepius, helios, kwavers and CFDrs; the in-flight members above proceed meanwhile.
- needs: ATLAS-PROVIDER-VERSIONS-20261002
- scope: `Cargo.toml` and `Cargo.lock` of coeus, metis, ritk, asclepius, helios, kwavers, CFDrs; source edits only where a bump breaks a call site.
- overlap: these lock advances also retire the melinoe/themis lock drift [ATLAS-LOCK-SWEEP-LANE-BOUND-2026-10-02](atlas-lock-sweep-lane-bound-2026-10-02.md) records for metis, ritk and asclepius.
- next: land Coeus#491, then one `build(deps)` PR per remaining member in the order coeus, ritk, asclepius, then helios, kwavers, CFDrs, each auto-merged on its gate.
- basis: 3ea1f062969718a419bceac2dca48d4437878513
