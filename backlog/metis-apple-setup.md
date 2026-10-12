<a id="atlas-metis-apple-setup"></a>
## ATLAS-METIS-APPLE-SETUP — Native and browser Apple setup [minor] — todo

- status: todo; priority: verification; target: Metis 0.2.0, Moirai 0.7.1 and moirai-webview 0.1.0; phase: Closure; outcome: one Rust frontend runs in browsers and installed Apple apps.
- [x] [patch] Clone all 28 components; resolve the native Rust 1.97.0 host and matching WASM loader.
- [x] [minor] Derive graph-scoped configuration; compile and package browser/macOS/iOS/device/simulator assets with SDK, signature and final inventory checks.
- [x] [patch] Deliver Darwin process cleanup and closed-peer forwarding fixes through Moirai PRs 606/607; native iPhone/iPad resource delivery passes.
- [x] [patch] Verify 678 standalone Metis tests, 125 provider tests, 34 configuration/index/page/icon tests, lint and documentation; no input domain is reduced.
- [x] [patch] Package the vector-derived macOS icon in installed and supervised development bundles; verify native decoding, exact pixels and unchanged outputs on invalid inputs.
- [x] [patch] Verify real-source reload, compiler/icon-error preservation, exact restoration and terminal-child cleanup; ADR generation retains committed-tree checks.
- [x] [minor] Resolve standalone workspace/fuzz locks with one provider identity; preserve unrelated main-lock revisions and repair the original fuzz baseline.
- [ ] [minor] Deliver Metis and advance Atlas pointers from merged default branches; no release tag is authorized by this increment.
- [ ] [patch] Observe native/Safari input, Dock branding, geometry, rotation and suspension after Mac unlock.
- [ ] [minor] Obtain owner-selected physical-device signing/provisioning and availability; Android/plugin capability work remains in Metis's backlog.
- artifacts: [manual](../repos/metis/docs/manual/apple.md), [ADR 0069](../docs/adr/0069-portable-host-toolchain.md), [gap audit](../gap_audit.md); this backlog owns execution state.
