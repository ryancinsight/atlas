<a id="substrate-contract-measured"></a>
## ATLAS-SUBSTRATE-CONTRACT-MEASURED-2026-09-03 - The contract is already satisfied; the guard is preventive [patch] - todo

Measurement before mechanization, per ADR 0055's substrate contract.

**Current violations across all 25 registered members: zero.** Scanning every
`Cargo.toml` in every member for `nalgebra`, `ndarray`, `rayon`, and
`num-traits` returns two hits, and neither is a violation:

| Hit | Verdict |
| --- | --- |
| `moirai` | `rayon` appears only in `[dev-dependencies]` of `moirai-parallel` and in comparison benchmarks and examples (`moirai_vs_tokio_rayon_comparison`, `rayon_parallel_patterns`). This is the sanctioned interop-or-comparison-target role: rayon is the baseline the first-party provider is measured against. |
| `leoneuro-rs` | Not a registered stack member; absent from `.gitmodules`. Outside the contract's scope. |

So the guard is **preventive, not remedial** - it locks in a property the stack
already has rather than opening a burn-down. That also fixes its shape: deny
these crates in runtime `[dependencies]` only, and permit `[dev-dependencies]`,
benches, and examples, because forbidding the comparison baseline would forbid
measuring the first-party provider against the thing it replaces.

**Implementation is not a new tool.** `cargo deny` already performs exactly this
check through a `[bans]` section, every member already carries a `deny.toml`,
and CI already runs a supply-chain job. Building a bespoke checker would
duplicate a capability the stack has.

**Blocked on region occupancy, not on design.** The two candidate homes are
both under live peer edit: `scripts/atlas-conformance.py` and its test file are
dirty, and `tools/version-guard/` likewise. A per-member `deny.toml` sweep is
the remaining route, but 25 near-identical `deny.toml` files are themselves the
fleet-scale duplication defect the conformance scan exists to catch - so the
sweep should land one stack-level `[bans]` definition that members inherit,
which is a decision about shared-config ownership rather than a mechanical
edit.

- **re-open trigger:** the conformance script leaves peer hands, or a decision
  on where the shared `[bans]` definition lives.
- **note:** this supersedes nothing in `#archtest-balance-edges`; R7 (no
  balance-to-balance edge) still needs the architecture test, and no such test
  exists in `tools/` today - the tools are `_template`,
  `checkout-path-dependencies`, `criterion-regression`, `gitlink-coherence`,
  and `version-guard`.

