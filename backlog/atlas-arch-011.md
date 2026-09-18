<a id="atlas-arch-011"></a>
## ATLAS-ARCH-011 — Retire hephaestus-metal per ADR 0047 [arch] [major] — blocked

outcome: `hephaestus-metal` (5,449 forwarding + 2,606 test lines) is deleted; Metal targeting survives as `WgpuDevice::try_metal(...)`, vendor identity as `device.adapter_info().map(|i| i.backend)`, and the facade's `metal` feature is kept and re-pointed to mean "acquire a Metal-preferring `WgpuDevice`".

acceptance oracle: (a) hephaestus workspace `cargo nextest run --all-targets` green with the member gone and `metal` feature building re-pointed; (b) conformance suite green with the Metal instantiation removed and no clause unreferenced; (c) stack-wide grep finds no `hephaestus_metal` outside Coeus's tracked item; (d) both CFDrs `backend_name()` assertions still pass. `[major]`: needs a CHANGELOG Unreleased entry (`MetalDevice::try_default` → `WgpuDevice::try_metal`); release itself stays outside this item's authority.

blocked: `repos/coeus` depends on `hephaestus-metal` (`coeus/Cargo.toml:59`, `coeus-metal`), and the stack overlay's dependency-closure `[patch]` breaks every build under the stack root while any member declares it. `repos/coeus` is on a live peer's `codex/coeus-publish-cycle` branch with a fresh commit-backed claim on exactly these files (coeus board: `coeus-hephaestus`, `coeus-rocm`, `coeus-metal`), mid-publish-cycle.

re-open trigger: `repos/coeus` no longer declares `hephaestus-metal` (ATLAS-SUBSTRATE-002 deletes `coeus-metal`) or the peer's publish cycle completes and the claim releases — then replay the ~15-minute mechanical removal, landing both repos as one unit.

Depends on ATLAS-SUBSTRATE-002 (ADR 0047 Accepted; only sequencing is in question). Owner: claude/fable-loop.
