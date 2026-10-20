<a id="atlas-zip9-cohort-sweep"></a>
## ATLAS-ZIP9-COHORT-SWEEP — Clear the zip < 9 advisories by moving kwavers onto the 0.10 provider cohort [patch] — todo
outcome: `cargo deny --config deny.toml --manifest-path crates/kwavers/Cargo.toml check` passes on kwavers main, with no advisory ignore, older pin or gate change, and the kwavers `CI gate` is green on main. RUSTSEC-2026-0367/0368/0369 (zip < 9.0.0) fail the gate on main and every PR. The stack drops the `zip` crate: consus, gaia and ritk use the first-party `consus-zip` container (consus ADR0007).
priority: correctness
needs: none
scope: repos/consus, repos/asclepius, repos/tyche, repos/gaia, repos/ritk, repos/kwavers
basis: 6100ff1f9
- kwavers' lock reaches zip 2.4.2 through gaia-mesh 0.5.2 (kwavers and ritk-io/filter/vtk at the pinned ritk rev), and zip 6.0.0 through consus-npy. ritk's own xtask carries zip 0.6.6.
- gaia 0.6.9 (zip 9.0.4) requires Moirai, eunomia and Mnemosyne 0.10. A git source resolves to one revision, so every first-party crate kwavers reaches must accept that cohort. Laggards at filing: ritk (Moirai 0.9, consus 0.2), tyche (eunomia/Mnemosyne 0.9, Moirai 0.7, consus 0.1), asclepius (eunomia/Mnemosyne 0.9).
- The owner chose a first-party container over zip 9: consus#180 adds `consus-zip` and moves NPZ onto it at consus 0.4.0. gaia 0.6.10 moves its 3MF writer (`src/infrastructure/io/three_mf.rs`) onto `consus-zip`; ritk's xtask `extract_zip` moves onto it with explicit member-path validation.
- Order: asclepius ∥ tyche ∥ consus 0.4.0 → gaia 0.6.10 ∥ ritk (consus 0.4) → kwavers requirements, lock and caller migration, with the ritk `rev =` pin and the unused `zip = "0.6"` removed. metis#505 hit the same cohort conflict; consus#179 landed Moirai 0.10 on consus main.
next step: land consus#180, then the gaia and ritk PRs, then the kwavers sweep PR.
