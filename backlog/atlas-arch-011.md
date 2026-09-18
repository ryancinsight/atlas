<a id="atlas-arch-011"></a>
## ATLAS-ARCH-011 — Retire hephaestus-metal per ADR 0047 [arch] [major] — blocked

- Owner: claude/fable-loop (claimed 2026-08-03); scope: `repos/hephaestus`
  (`crates/hephaestus-metal`, the
  workspace member list, the `hephaestus` facade's `metal` feature, and the
  conformance suite's Metal instantiation). Coeus is **out of scope** — see
  the note under ATLAS-SUBSTRATE-002.
- Outcome: the crate and its 5 449 forwarding lines plus 2 606 test lines are
  deleted. Metal targeting survives unchanged as
  `WgpuDevice::try_metal(...)`, and the vendor identity as
  `device.adapter_info().map(|i| i.backend)`.
- The facade's `metal` feature is **kept and re-pointed**, so consumers'
  spelling of intent survives the removal: it comes to mean "acquire a
  Metal-preferring `WgpuDevice`" instead of "compile a second copy of the
  operation surface".
- Acceptance oracle: (a) `cargo nextest run` green for the hephaestus
  workspace at `--all-targets` with the member entry gone, and the `metal`
  feature seam building in its re-pointed form; (b) the conformance suite
  passes with the Metal instantiation removed and no clause left
  unreferenced; (c) a stack-wide grep finds no `hephaestus_metal` reference
  outside Coeus's tracked item; (d) the two CFDrs `backend_name()`
  assertions still pass, confirming no observable contract moved.
- Risk/change class: `[major]` — a published crate is removed. Needs a
  CHANGELOG entry under Unreleased with the one-line migration
  (`MetalDevice::try_default` → `WgpuDevice::try_metal`). Release itself
  stays outside this item's authority.
- Verification note: coverage is not lost. The Metal instantiation ran the
  same clauses over the same code path as the WGPU one, so it asserted
  nothing WGPU does not already assert; Metal-*adapter* coverage is a
  question of which adapter CI acquires, not of which crate the suite names.
- Dependencies: **ATLAS-SUBSTRATE-002** (see the blocker below). ADR 0047 is
  Accepted; the decision is not in question, only its sequencing.
- **BLOCKED 2026-08-03, discovered by executing it.** The hephaestus-side
  removal is mechanically complete and was verified to that point — member
  entry, workspace dep, the facade's optional dep and its three `?/` feature
  entries, the `metal` feature re-pointed to `["wgpu"]`, the
  `pub use hephaestus_metal as metal` re-export, and the crate itself, with
  `cargo metadata` green and **zero** residual `hephaestus_metal` references
  in any `.rs`/`.toml` under `repos/hephaestus`. It was then reverted, for
  the reason below.
- **`repos/coeus` depends on `hephaestus-metal`** (`coeus/Cargo.toml:59`, and
  `coeus/crates/coeus-metal/` consumes it). The ADR scoped Coeus out on the
  grounds that its collapse is SUBSTRATE-002's business — that scoping was
  wrong, and the stack overlay is what proves it: the overlay is generated
  from the *dependency closure*, so while any member declares
  `hephaestus-metal`, it emits a `[patch]` pointing at the deleted crate
  directory and **every build beneath the stack root fails**, not just
  Coeus's. Upstream removal and the consumer edge are one co-evolution unit.
- Cutting that edge is not available: `repos/coeus` is on a live peer's
  `codex/coeus-publish-cycle` branch, and the Coeus board claims
  `coeus-hephaestus`, `coeus-rocm`, `coeus-metal` under Codex
  (`coeus/docs/backlog.md:464`) — a fresh, commit-backed claim over exactly
  the files this needs, mid-publish-cycle. Deleting a crate out from under a
  publish cycle is the one thing not to do here.
- Re-open trigger: `repos/coeus` no longer declares `hephaestus-metal` —
  i.e. ATLAS-SUBSTRATE-002 deletes `coeus-metal`, or the peer's publish cycle
  completes and its claim is released. Then re-apply the hephaestus removal
  (it is a ~15-minute mechanical replay of the list above) and land both
  repos as one unit.
- Sizing note for whoever takes SUBSTRATE-002's metal slice: `coeus-metal` is
  1 233 lines with **zero in-repo dependents** — no manifest outside the
  workspace member list names it, and the only code references are its own
  tests. It is a file-for-file copy of `coeus-rocm` (per-file diffs of 0, 0,
  0, 2, 17, 25 lines after normalizing the vendor token), and
  `coeus-hephaestus` already implements the whole op surface generically for
  `HephaestusBackend<P>`. The only content not reproducible from a ~56-line
  provider marker is one `fill_zero` override.

