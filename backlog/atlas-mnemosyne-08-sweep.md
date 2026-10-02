<a id="atlas-mnemosyne-08-sweep"></a>
## ATLAS-MNEMOSYNE-08-SWEEP — Every member locks one Mnemosyne generation [correctness] — todo
- priority: correctness
- outcome: every allowlisted member's default-branch `Cargo.lock` resolves the Mnemosyne 0.8 generation (`mnemosyne-memory` 0.8.0, arena 0.5.0, backend 0.6.0, memory-core 0.3.0, heap 0.5.0, local 0.5.0; Mnemosyne main at or after ryancinsight/Mnemosyne#208), so asclepius and harmonia can take [ATLAS-ALLOC-COUNT-PER-THREAD](atlas-alloc-count-per-thread.md).
- oracle: per member, `cargo metadata --locked` resolves outside the overlay, every `mnemosyne-*` lock entry is at that generation, and `cargo tree -d` lists no duplicate mnemosyne crate.
- basis 2026-10-02, fetched default branches: hermes, moirai, leto, gaia, apollo, athena are at 0.8. Manifests still on `^0.7`: coeus, ritk, helios, kwavers (kwavers also `rev`-pins ritk). Locks on the 0.7 generation with no manifest change needed: hephaestus, consus, tyche, metis, harmonia, ares, asclepius, CFDrs.
- order: resolution reads a dependency's manifest, never its lock, so a lock-only member gates no consumer. Ready now: hephaestus, consus, tyche, metis, harmonia, ares, coeus. After coeus: ritk, asclepius. After ritk: helios, kwavers, CFDrs.
- scope: `Cargo.toml` and `Cargo.lock` of the twelve members above; source edits only where a bump breaks a call site.
- overlap: these lock advances also retire the melinoe/themis lock drift [ATLAS-LOCK-SWEEP-LANE-BOUND-2026-10-02](atlas-lock-sweep-lane-bound-2026-10-02.md) records for ares, asclepius, harmonia, metis, ritk and tyche.
- next: one `build(deps)` PR per member in the order above, auto-merged on its gate.
