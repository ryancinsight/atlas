<a id="atlas-metis-apple-setup"></a>
## ATLAS-METIS-APPLE-SETUP — Native and browser Apple setup [minor] — todo

- status: todo; priority: verification; target: Metis 0.2.1, Moirai 0.7.1 and moirai-webview 0.1.1; phase: Closure; outcome: one Rust frontend runs in browsers and installed Apple apps.
- [x] [patch] Clone all 28 components; resolve the native Rust 1.97.0 host and matching WASM loader.
- [x] [minor] Derive graph-scoped configuration; compile and package browser/macOS/iOS/device/simulator assets with SDK, signature and final inventory checks.
- [x] [patch] Deliver Darwin process cleanup and closed-peer forwarding fixes through Moirai PRs 606/607; native iPhone/iPad resource delivery passes.
- [x] [patch] Verify 678 standalone Metis tests, 125 provider tests, 99 Python checks and documentation; Windows, Apple and complete fuzz merge gates pass.
- [x] [patch] Package and decode the macOS icon; preserve invalid-input outputs. Fix native Fetch status through Moirai PR 608; actual Greet clicks return exact normal, Unicode and empty-name Rust results.
- [ ] [patch] Merge Atlas PR 530 after canonical hook rollout (PR 450), RITK's three Metis requirement advances, 14 consumer lock updates and 24 stale member pins; current integration gates fail.
- [x] [minor] Resolve standalone workspace/fuzz locks with one provider identity; preserve unrelated main-lock revisions and repair the original fuzz baseline.
- [x] [minor] Merge Metis PR 491; commit and push Atlas's two default-branch pointers separately. Real reload/failure preservation and ADR checks pass; target versions remain unreleased.
- [ ] [patch] Observe remaining Safari/mobile input, Dock branding, geometry, rotation and suspension; macOS Greet is verified after unlock, while the Simulator UI client is absent.
- [ ] [minor] Obtain owner-selected physical-device signing/provisioning and availability; Android/plugin capability work remains in Metis's backlog.
- artifacts: [manual](../repos/metis/docs/manual/apple.md), [ADR 0069](../docs/adr/0069-portable-host-toolchain.md), [gap audit](../gap_audit.md); this backlog owns execution state.
