<a id="atlas-metis-rust-browser"></a>
## ATLAS-METIS-RUST-BROWSER — Rust browser presentation [minor] — todo

- status: todo; priority: verification; target: Metis 0.3.0, Moirai 0.8.2, Gaia 0.5.2; phase: Closure.
- scope: Rust owns browser configuration/navigation, HTTP codecs, cancellation, mount leases and DOM updates; authored application JavaScript falls from 505 to nine initialization lines.
- [x] [minor] Merge bounded browser mechanisms and corrections through Moirai PRs 611/612/613; merge Gaia PR 169's compatible provider graph.
- [x] [patch] Verify 686 Rust tests, 395 Python tool checks, native/WASM diagnostics, 784 locked API checks and 22 production wheel tests; four platform-specific wheel cases remain skipped.
- [x] [patch] Exercise actual Unicode/empty data, status/code denials, target/stale rejection, listener stop, pending-reset isolation, exact/excess streams, bodyless metadata, redirect, deadline and peer-observed cancellation.
- [x] [patch] Build frozen macOS/device/simulator bundles and verify native Greet normal/Unicode/empty results.
- [x] [patch] Review 32 Tauri native surfaces: 124 admitted pairs, 46 bounded and 78 open; validator rejects missing owners and hidden admission gaps.
- [ ] [patch] Merge the pushed Metis Rust migration through protected checks, then record all three component defaults in a gitlink-only commit.
- [ ] [patch] Merge Atlas PR 530 after the canonical hook rollout and consumer-graph/pin closure; current root conformance still rejects member gate versions 1→2.
- residual: native plugin/permission, physical mobile, Safari input and matched Tauri performance acceptance remains in the component backlog.
- artifacts: [ADR 0056](../repos/metis/docs/adr/0056-rust-browser-shell.md), [Tauri review](../repos/metis/docs/manual/tauri.md), [component gap audit](../repos/metis/gap_audit.md).
