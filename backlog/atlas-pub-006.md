<a id="atlas-pub-006"></a>
## ATLAS-PUB-006 — Stand up one facade crate per package [minor] — todo

- Owner: unclaimed; scope: one package per claim, in that package's repository.
  The `mnemosyne-core` rename is a cross-repo co-evolution unit and is claimed as
  a single item spanning `mnemosyne`, `leto`, `hephaestus`, and `moirai`.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md).
  Naming is settled; nothing here waits on a user answer.
- Outcome: every package presents one facade crate that re-exports its
  sub-crates, so a user depends on `coeus`, not `coeus-core` — the shape `burn`,
  `bevy`, and `polars` use. The facade holds no logic: re-exports with
  `#[doc(inline)]`, feature gates selecting optional backend sub-crates, and the
  crate-level overview. Lockstep versioning at the workspace version.
- Audit 2026-07-28 — 14 of 25 packages cannot present a facade today:
  - **author a facade** (workspace root is virtual, no entry crate exists):
    `apollo` → `apollo-transforms`, `CFDrs` → `cfdrs`, `coeus` → `coeus`,
    `helios` → `helios-radiation`, ~~`hephaestus` → `hephaestus`~~ **delivered**,
    `ritk` → `ritk`;
  - `hephaestus` facade landed in `repos/hephaestus/crates/hephaestus`
    (`bf24b87`): flat `#[doc(inline)]` re-export of the contract layer, backends
    under `hephaestus::{wgpu,cuda,rocm,metal}` behind features, no backend
    enabled by default (a default backend would make every trait consumer pull a
    device stack, and `cuda`/`rocm` need vendor toolkits at build time). Two
    design facts worth carrying to the remaining five:
    `default-features = false` cannot override a workspace-inherited dependency,
    so a facade declares its contract-layer dep directly; and weak feature refs
    (`dep?/feature`) are required so forwarding `parallel` does not silently
    enable an unrequested backend.
  - Verification complete — all four configurations pass: default `cargo check`,
    `--no-default-features`, the doctest, and `--features wgpu,decomposition,sparse`
    (11 m 32 s, queued behind a peer's build-directory lock). The `bf24b87`
    commit message recorded the wgpu set as unconfirmed because it was still
    building at commit time; this entry supersedes that.
  - Evidence limit: those checks ran against a working tree carrying a peer's
    uncommitted edits to `hephaestus-core/src/{lib.rs,domain/vector.rs}` and
    `hephaestus-wgpu/src/application/vector/mod.rs`. They prove the facade
    compiles against the tree as it stood, not against committed state. The glob
    re-export is robust to surface additions, but re-verify on a clean tree once
    that peer work lands.
  - Not verified: that a backend is unnameable without its feature. That follows
    directly from `#[cfg(feature = ...)]` on the re-export, and a `compile_fail`
    doctest asserting it would itself pass or fail depending on which features
    the test run enables — a fragile test of language semantics rather than of
    this contract, so none was added.
  - **flip `publish`** (facade exists, excluded from publishing): `aequitas`,
    `asclepius`, `horae`, `hermes-simd` — names already free;
  - **rename and flip `publish`**: `harmonia` → `harmonia-coupling`,
    `hyperion` → `hyperion-photon`, `moirai` → `moirai-runtime`,
    `proteus` → `proteus-materials`;
  - **rename only** (publishable under a colliding name): `athena` →
    `athena-solvers`, `gaia` → `gaia-geometry`, `mnemosyne` →
    `mnemosyne-alloc`, `themis` → `themis-placement`, `tyche` → `tyche-uq`;
  - **ready, no action**: `consus`, `eunomia`, `iris`, `kwavers`, `leto`,
    `melinoe`.
- Non-goals: repository names, submodule paths, directory names, module paths,
  and the classical-name mapping in the stack README. This is registry identity
  only. Also out of scope: negotiating a colliding name from its current owner —
  permitted, but no publish waits on it (ADR 0037 §7).
- Acceptance per package: the facade's `src/lib.rs` contains no logic; `cargo doc`
  shows re-exported items inline at facade paths; `--no-default-features` builds
  and no backend is reachable without its feature; `cargo publish --dry-run`
  passes after the sub-crates; the facade name returns 404 from the registry
  immediately before first publish, since availability decays.
- Non-blocking: ATLAS-PUB-001, -002, -004, and -005 proceed independently — a
  caller passes a package name, so every rename here is a manifest change.
- **Correction 2026-07-28 — do not flip `publish = false` ahead of dependencies.**
  An earlier reading of this item treated the eight guards as oversights. They are
  correct ordering guards: `cargo package` on `aequitas` fails with
  `no matching package named 'eunomia' found`, because a crate can only publish
  once its first-party dependencies are on the registry. Cargo *does* rewrite a
  `{ version, git }` dependency to a registry dependency, so git sources are not
  the blocker (`hermes-simd`'s manifest comment overstates it) — dependency order
  is. Each flip is the final step of that crate's own bootstrap publish, in the
  order `scripts/publish-order.py` derives. Four flips were attempted and reverted
  on this evidence; see [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §4.
- **Registry re-measure 2026-08-24 — README is stale, and the naming diverged from
  ADR 0037 in four places.** A live crates.io check plus the committed manifests
  correct the record:
  - **Already published (user's crates):** `aequitas` 0.2.0, `eunomia` 0.8.0,
    `asclepius` 0.1.0, `leto`+`leto-ops` 0.42.0, `melinoe` 0.9.0, `apollo-fft`
    0.26.0, `apollo-fft-macros` 0.2.0, `moirai-core`+`runtime` 0.5.0,
    `coeus-core`+`tensor`+`ops` 0.10.0, `mnemosyne-core` 0.2.0, `mnemosyne-heap`
    0.4.0, `themis` 0.14.0, `tyche-core` 0.2.0, `gaia-mesh` 0.4.0, `hermes-simd`
    0.6.0, `hephaestus-core`+`host`+`wgpu` 0.19.0, `ritk-core` 0.10.0,
    `ritk-image` 0.3.0, `consus` 0.1.0. The README line "No Atlas crate is
    published yet" (line 1084) is false and must be corrected.
  - **Naming deviations from ADR 0037, found in the manifests (not the README):**
    - athena's facade is `athena-krylov` (`[lib] name = "athena"`, `publish =
      true`), not `athena-solvers` as the README table lists.
    - iris's package is `iris-viz`, not `iris`; gaia's is `gaia-mesh` (already
      published 0.4.0), not `gaia-geometry`.
    - themis's package is `themis-topology` (`[lib] name = "themis"`, publishable),
      not `themis-placement`; `leto` publishes under the bare name 0.42.0.
    - tyche root is `publish = false`; mnemosyne root publish is unset.
  - **Third-party name collisions confirmed:** `hyperion` (patrickisgreige
    LSystem), `proteus` (rust-playground JSON), `harmonia` (sogh music theory),
    `gaia` (ucarion terrain), `mnemosyne-core` (bballer03 JVM analyzer), `athena`
    (unrelated). All five unblocker repos (hyperion, proteus, harmonia, horae,
    asclepius) are clean at their recorded gitlinks and `publish = false`.
  - **The unblocker chain is the critical path:** proteus → `proteus-materials`,
    hyperion → `hyperion-photon` (repoint its `proteus` dep), horae (name free),
    harmonia → `harmonia-coupling` (repoint `horae`+`athena-core` deps), then
    asclepius-coeus; athena's family must publish before harmonia.
  - **Delivery 2026-08-25 — first link merged across the stack; publish itself
    still pending.** All five PRs merged to their default branches:
    proteus #19 (`cd93e67`, later main `cb00193`), CFDrs #371 (`5ebbf1f`),
    hyperion #25 (`017a669`), kwavers #637 (`f5a996c` → main `cf5852f`),
    helios #71 (`c2cf177`). Atlas gitlinks advanced in `5c9efcac8` (+ hermes
    `4a1228ce`); overlay regenerated (44 sections, stack aligned);
    `atlas-provider-integration-audit.py --exact-heads` green.
  - **Lockfile lesson (kwavers/helios):** a committed lockfile must be generated
    *without* the Atlas overlay — the overlay's `[patch]` redirects strip the
    git `source =` lines from lock entries and inject `[[patch.unused]]`
    sections, both of which break CI's `--locked` resolution. Helios now enforces
    this at push time via its pre-push hook (`scripts/lockfile.py --regenerate`).
    Remaining: the actual `cargo publish` of `proteus-mat` (release authority),
    then the next links: hyperion → `hyperion-ph`, horae, harmonia →
    `harmonia-cpl`.
- Peer-held at this revision, so not claimable without a staleness sweep:
  `coeus` (`codex/coeus-error-function-parity`, 24 dirty), `ritk`
  (`codex/docs-ritk-n4-figure-only`, 11 dirty, active), `leto`
  (`codex/leto-real-sparse-lu`, 25 dirty), `mnemosyne`
  (`codex/mnemosyne-tier-selection`, clean). The `coeus` facade — the flagship
  case for this item — is among them.

