<a id="atlas-nightly-probe-consolidation"></a>
## ATLAS-NIGHTLY-PROBE-CONSOLIDATION - One nightly-rustc probe for the stack [patch] - todo
- outcome: the build-script probe that emits `nightly_tls_active` from `$RUSTC -vV` has one owner. Today it exists as the shared helper `mnemosyne-build-util` and as hand-copied `build.rs` bodies in moirai-executor, moirai-pal, themis (byte-identical to moirai-executor's), and melinoe (a variant that also emits `doc_cfg_active`).
- acceptance: `git grep -n 'release: ' -- '*build.rs'` across members finds the probe body once, in the owning crate; every consumer's `build.rs` is a call to it; each consumer's `nightly_tls` path still builds on stable and nightly.
- priority: tightening
- needs: none (the `rerun-if-env-changed=RUSTC` removals that shaped the copies landed or are enqueued: melinoe#44, themis#63, Mnemosyne#159, Moirai#470).
- scope: `repos/mnemosyne/crates/mnemosyne-build-util`, `repos/moirai/moirai-executor/build.rs`, `repos/moirai/moirai-pal/build.rs`, `repos/themis/build.rs`, `repos/melinoe/build.rs`.
- next: pick the home from the README stack map. A build-dependency must not point up the layering, so if themis or melinoe sit below Mnemosyne, the probe moves to the lowest layer every consumer may depend on, rather than to `mnemosyne-build-util`.
- basis: c034d7046e10 (atlas origin/main when filed).
