# ADR 0037: Workspace facade crates and crates.io registry naming

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]` `[minor]`
- Relates to: [ADR 0035](0035-shared-publication-pipelines.md)

## Context

ADR 0035 §7 recorded that crate names collide on crates.io and deliberately left
the naming decision open. Two requirements then fixed the shape of the answer:
each workspace must present **one main crate that a user reaches for** — `coeus`,
not `coeus-core`, the way `burn` works — and the stack-wide `atlas-` prefix is
rejected.

That converts an open question into a bounded design problem: what the entry
crate is, how it relates to the sub-crates, and what it is called when the
obvious name is taken.

### Facade practice in comparable projects (verified 2026-07-28)

Read from the crates.io API rather than from recollection:

| Project | Entry crate | Sub-crate versioning | Backends |
| --- | --- | --- | --- |
| `burn` 0.21.0 | `burn` | lockstep `^0.21.0` across `burn-core`, `burn-nn`, `burn-optim`, `burn-std` | 18 further sub-crates **optional**: `burn-wgpu`, `burn-cuda`, `burn-rocm`, `burn-autodiff`, `burn-ndarray`, `burn-candle`, `burn-tch`, … |
| `bevy` 0.19.0 | `bevy` | lockstep `^0.19.0` across `bevy_ecs`, `bevy_asset`, `bevy_animation`, … | feature-gated |
| `polars` 0.54.4 | `polars` | lockstep `^0.54.4` across `polars-arrow`, `polars-compute`, … | feature-gated |
| `tokio` 1.53.1 | `tokio` | **independent**: `tokio-util ^0.7`, `tokio-stream ^0.1`, `tokio-macros ~2.7.0` | feature-gated |

Two established patterns exist. Lockstep (burn, bevy, polars) publishes every
member at one workspace version and gates optional members behind facade
features. Independent (tokio) versions each member on its own cadence. Lockstep
matches Atlas: each repository already carries a single workspace `version`, and
`coeus` already has exactly burn's crate shape — `coeus-core`, `coeus-tensor`,
`coeus-ops`, `coeus-autograd`, `coeus-nn`, `coeus-optim`, `coeus-sparse`,
`coeus-fft` alongside optional `coeus-wgpu`, `coeus-cuda`, `coeus-rocm`,
`coeus-metal`, `coeus-leto`, `coeus-hephaestus`.

### crates.io name policy (verified 2026-07-28)

- Names are **first-come, first-serve**.
- There are **no namespaces**. Scoping is not available as a fix.
- The crates.io team **will not transfer ownership** without the current owner's
  explicit approval; taking over a name means contacting the owner directly.
- Trading names for compensation is prohibited.
- Name squatting — a crate that "exists only to reserve a name for a prolonged
  period of time … without having any genuine functionality" — violates policy,
  and the team may remove such crates on a case-by-case basis. This is a
  reporting path, not a reliable plan.

### Name audit (2026-07-28)

All 207 package manifests across the 25 packages were enumerated; 34 are
`publish = false`, leaving 173 publishable names checked against the registry.
**Only 8 collide:**

| Name | Registry state | Owner |
| --- | --- | --- |
| `athena` | v0.0.0, 891 downloads, 2025-01-31 | `zakarumych` |
| `gaia` | v0.2.1, 6 775 downloads, 2018-03-28 | `ucarion` |
| `helios-core` | v0.1.0, 1 067 downloads, 2024-10-27 | `ncitron` |
| `mnemosyne` | v0.3.1, 2 361 downloads, 2026-02-07 | `elde-n` |
| `mnemosyne-core` | v0.2.0, 153 downloads, 2026-03-08 | `bballer03` |
| `themis` | v0.14.0, 19 629 downloads, 2021-12-23 | `ilammy`, `vixentael`, `forelocked-beobachter` |
| `tyche` | v0.3.1, 5 338 downloads, 2025-03-14 | `Gawdl3y` |
| `xtask` | v0.1.4, 586 downloads, 2026-06-30 | `AprilNEA` |

The earlier "12 collisions" figure counted bare *repository* names. Most are not
publishable crate names at all, because those workspaces have no crate bearing
the bare name — which is the real finding below.

### Facade gap audit (2026-07-28)

**14 of 25 packages cannot present an entry crate today:**

| Situation | Packages |
| --- | --- |
| Facade crate exists but is `publish = false` | `aequitas`, `asclepius`, `harmonia`, `hermes-simd`, `horae`, `hyperion`, `moirai`, `proteus` |
| No facade crate exists — the workspace root is virtual | `apollo`, `CFDrs`, `coeus`, `helios`, `hephaestus`, `ritk` |
| Facade crate exists and is publishable | `consus`, `eunomia`, `iris`, `kwavers`, `leto`, `melinoe`, plus `athena`, `gaia`, `mnemosyne`, `themis`, `tyche` under colliding names |

So the requirement is unmet for more than half the stack, and for a reason
unrelated to name collisions: six workspaces have no entry crate to publish, and
eight have one that is excluded from publishing.

## Decision

### 1. Every package publishes exactly one facade crate

Each workspace presents one entry crate that re-exports its sub-crates. A user
depends on `coeus`, never `coeus-core`. The facade owns no logic: it is a
re-export surface plus the feature flags that select optional sub-crates.

Re-exports are `pub use` with `#[doc(inline)]` so rustdoc presents the items at
the facade path rather than sending readers into sub-crates. The facade's own
documentation is the crate-level overview; item contracts stay with the
implementing crate.

Sub-crates remain published — they are how a consumer takes a narrow dependency,
and they are what other stack packages depend on internally. They are simply not
the advertised entry point.

### 2. Lockstep versioning with optional backend sub-crates

Following burn, bevy, and polars: the facade depends on its required sub-crates at
the shared workspace version, and every backend or optional capability is an
optional dependency behind a facade feature. Tokio's independent-versioning model
is rejected — it requires per-crate semver reasoning across 173 crates, and the
stack already versions per workspace.

### 3. Naming rule: bare classical name where free, `<name>-<domain>` where taken

No `atlas-` prefix, on the standing naming preference. No stack-wide `-rs`
suffix either — it is not uniformly available (`apollo-rs`, `athena-rs`,
`hermes-rs`, and `mnemosyne-rs` are all taken), so it would fail as a rule and
produce the inconsistency it was meant to avoid.

The rule that does hold: a package reserves its `<name>-` prefix family, and the
facade is the bare classical name when free, or `<name>-<domain>` when not. The
classical-name mapping in the stack README is unaffected — this governs registry
identity only, not repository names, directory names, module paths, or the naming
scheme itself.

Every target below was verified available on 2026-07-28:

| Package | Facade crate | Action required |
| --- | --- | --- |
| `aequitas` | `aequitas` | flip `publish` |
| `apollo` | `apollo-transforms` | author facade (`apollo` taken, v0.0.2 2023) |
| `asclepius` | `asclepius` | flip `publish` |
| `athena` | `athena-solvers` | rename facade (`athena` taken by a v0.0.0 placeholder) |
| `CFDrs` | `cfdrs` | author facade |
| `coeus` | `coeus` | author facade |
| `consus` | `consus` | ready |
| `eunomia` | `eunomia` | ready |
| `gaia` | `gaia-geometry` | rename facade (`gaia` taken, 2018) |
| `harmonia` | `harmonia-coupling` | rename + flip `publish` |
| `helios` | `helios-radiation` | author facade (`helios` taken, 2019) |
| `hephaestus` | `hephaestus` | author facade |
| `hermes` | `hermes-simd` | flip `publish` |
| `horae` | `horae` | flip `publish` |
| `hyperion` | `hyperion-photon` | rename + flip `publish` |
| `iris` | `iris` | ready |
| `kwavers` | `kwavers` | ready |
| `leto` | `leto` | ready |
| `melinoe` | `melinoe` | ready |
| `mnemosyne` | `mnemosyne-alloc` | rename facade (`mnemosyne` taken, active) |
| `moirai` | `moirai-runtime` | rename + flip `publish` |
| `proteus` | `proteus-materials` | rename + flip `publish` |
| `ritk` | `ritk` | author facade |
| `themis` | `themis-placement` | rename facade (`themis` is Cossack Labs' crypto library, 19 629 downloads) |
| `tyche` | `tyche-uq` | rename facade |

`hyperion-photon` deliberately leaves `hyperion-transport` free for the future
crate ADR 0032 reserves.

### 4. Two sub-crate collisions are renamed, and one is a publish defect

- `helios-core` is taken (`ncitron`). The Helios internal crate is renamed in the
  same change that authors the `helios-radiation` facade.
- `mnemosyne-core` is taken (`bballer03`), and it is a **dependency edge**:
  `leto`, `hephaestus`, and `moirai` all depend on `mnemosyne-core`. Renaming it
  is a cross-repository co-evolution unit, not a local edit.
- `xtask` is taken, and `repos/ritk/xtask/Cargo.toml` lacks the `publish = false`
  that `apollo`, `CFDrs`, `helios`, and `kwavers` all carry. That is an
  inconsistency defect: an internal build-automation crate must never be
  publishable. Fix the manifest rather than the name.

### 5. Taking a colliding name is not part of the plan

Contacting an owner is permitted and may succeed for the clearly dormant names
(`athena` at v0.0.0, `gaia` untouched since 2018, `apollo` at v0.0.2). It is not
scheduled work: it depends on a third party's cooperation, and crates.io will not
transfer without their approval. The facade names in decision 3 are chosen so no
publish waits on a negotiation. If a name is later obtained, adopting it is a
rename, not a re-architecture.

`themis` specifically is not a squatting candidate — it is an actively used
crypto library with 19 629 downloads, and a report would be meritless.

## Consequences

- Six facade crates are authored (`apollo-transforms`, `cfdrs`, `coeus`,
  `helios-radiation`, `hephaestus`, `ritk`) and eight `publish = false` flags are
  flipped, so every package gains an entry crate.
- Seven facades publish under a `<name>-<domain>` name. Repository names,
  submodule paths, and the classical mapping are untouched.
- `mnemosyne-core`'s rename is a co-evolution unit across `leto`, `hephaestus`,
  and `moirai`, sequenced before those packages' first publish.
- 165 of 173 publishable names are free, so the registry surface is otherwise
  unblocked.
- The pipelines from ADR 0035 need no change: a caller passes a package name, so
  every rename here is a manifest change.

## Alternatives rejected

**`atlas-` prefix on all 25.** Rejected on the standing naming preference, and it
would rename 165 names that are already free to solve 8 that are not.

**Stack-wide `-rs` suffix.** Not uniformly available — `apollo-rs`, `athena-rs`,
`hermes-rs`, and `mnemosyne-rs` are taken — so it fails as a rule.

**Publish sub-crates only, no facade.** Directly contradicts the requirement that
a user reach for `coeus` rather than `coeus-core`, and leaves 25 packages with no
advertised entry point.

**`-core` crates as the entry point.** `athena-core` and `coeus-core` are free, but
naming the entry crate `-core` teaches users to depend on the internal layer —
the exact outcome the facade exists to prevent. It also collides twice already
(`helios-core`, `mnemosyne-core`).

**Independent per-crate versioning (tokio's model).** Requires per-crate semver
reasoning across 173 crates for no gain; the stack already versions per workspace.

**Reporting the colliding names as squatting.** Two might qualify; `themis`
plainly does not, and the outcome is a case-by-case team decision. Not a schedule
a release plan can depend on.

## Verification

1. Every facade name in decision 3 returns 404 from
   `GET /api/v1/crates/<name>` immediately before its first publish — availability
   is a point-in-time fact and decays.
2. Each facade crate contains no logic: its `src/lib.rs` is re-exports, feature
   gates, and crate-level documentation only.
3. `cargo doc` on the facade shows the re-exported items inline at facade paths,
   not as bare `pub use` links.
4. Building the facade with `--no-default-features` and with each backend feature
   individually succeeds, and no backend is reachable without its feature.
5. `cargo publish --dry-run` passes for the facade after its sub-crates publish,
   proving the dependency order.
6. `repos/ritk/xtask/Cargo.toml` carries `publish = false`, matching the other
   four `xtask` crates.
7. No manifest anywhere in the stack depends on `mnemosyne-core` after the rename.

## References

- [ADR 0035](0035-shared-publication-pipelines.md) §7 — the open naming question
  this ADR closes, and the pipelines that consume these names.
- [Facade crates and registry names](../../README.md#facade-crates-and-registry-names)
  — the stack-facing summary and the per-package facade table.
- crates.io Package Ownership policy — first-come names, no team-forced transfer,
  squatting defined and removable case-by-case.
- crates.io API, 2026-07-28 — the 173-name audit, the 8 collisions with owners and
  download counts, and every facade-name availability check recorded above.
