# ADR 0012 — `ritk` Burn-trait rebind to Atlas-typed parallel trait surface (Batch #3, 6 atomic sub-batches)

- Status: **Accepted** — Sub-batch #1 (`RITK Atlas-typed parallel trait surface, additive`) **closed** 2026-07-06. Sub-batches #2-#6 reserved per the §Sequencing / atomic-boundary discipline below.
- Date: 2026-07-06.
- Drivers: ritk Atlas migration (Batch #3 in `atlas/backlog.md`); provider-side Burn GPU-default drift closed 2026-07-06 by inner RITK commit `65a1a0fd` (cross-walked in `atlas/gap_audit.md` risk #1).
- Anchors: `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (Accepted 2026-07-05) — confirms `coeus_core::Scalar: eunomia::NumericElement` (universal SSOT) and `coeus_core::ComputeBackend` as the Atlas-side backend seam; `atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` (Accepted 2026-07-05) — anchors the Atlas-pointer-advance + tag ritual that this ADR's commit chain follows (reserved inner tag: `ritk/atlas-migration-push/batch3`).
- Supersedes: the per-batch cron in `atlas/checklist.md` §Batch #3 §Plan (which captured the rebind's boundary intent at high level) and the §ritk entry in `atlas/gap_audit.md` Migration evidence inventory (which captured the rebind's pre-implementation scope). The 6-sub-batch atomic-boundary discipline recorded below formalises that intent into additive / non-breaking increments.

- Index: docs/adr/INDEX.md#ADR-0012

## Context

`ritk` (medical image processing workspace, 33-crate Cargo workspace at `repos/ritk/`) is the Burn-keyed imaging substrate inside atlas. The legacy trait surface as of `65a1a0fd` (RITK HEAD post-Burn-GPU-default closeout, 2026-07-06):

| Surface | File:line | Burn-keyed shape |
|---|---|---|
| `Image<B, D>` (re-export) | `repos/ritk/crates/ritk-core/src/lib.rs:11` (UI re-export) → `repos/ritk/crates/ritk-image/src/types.rs:18` | `pub type Image<B: Backend, const D: usize> = burn::tensor::Tensor<B, D>;` (Burn-keyed only) |
| `Transform<B, D>` | `repos/ritk/crates/ritk-core/src/transform/trait_.rs:19` | `pub trait Transform<B: Backend, const D: usize>: Sized { fn transform_points(&self, points: Tensor<B, 2>) -> Tensor<B, 2>; fn inverse(&self) -> Option<Self> { None } }` |
| `Resampleable<B, D>` | `repos/ritk/crates/ritk-core/src/transform/trait_.rs:43` | `pub trait Resampleable<B: Backend, const D: usize> { fn resample(&self, shape, origin, spacing, direction) -> Self; }` |
| `Interpolator<B>` | `repos/ritk/crates/ritk-core/src/interpolation/trait_.rs:18` | `pub trait Interpolator<B: Backend> { fn interpolate<const D: usize>(&self, data: &Tensor<B, D>, indices: Tensor<B, 2>) -> Tensor<B, 1>; }` |
| `Vector<D>::Module`/`Record` impls | `repos/ritk/crates/ritk-spatial/src/vector.rs:7` | `impl<B: Backend, const D: usize> burn::module::Module<B> for Vector<D>` + `impl<B: Backend> burn::record::Record for Vector<B>`; same pattern on `Point`, `Direction`, `Spacing`. |
| `apply_row_chunks<B: Backend>` | `repos/ritk/crates/ritk-wgpu-compat/src/lib.rs:40+` | GPU row-chunk helper bound on `burn::tensor::Backend`. |
| `ImageReader`/`ImageWriter<Image<f32, B, 3>>` | `repos/ritk/crates/ritk-io/src/{reader,writer}.rs` | Bound on `burn::tensor::Backend`. |
| `CpuOrGpu<B>` | `repos/ritk/crates/ritk-registration/src/deformable_field_ops/mod.rs` | Default `burn::backend::NdArray`. |

Atlas migration target: `coeus_core::ComputeBackend` (`repos/coeus/coeus-core/src/backend/traits.rs:31` — `pub trait ComputeBackend: private::Sealed + Send + Sync + Clone + 'static { ... }`) and `coeus_core::Scalar: eunomia::NumericElement` (CR-4 closure 2026-07-05, ADR 0005 §Decision §1). The Atlas-native image carrier already lives at `repos/ritk/crates/ritk-image/src/native.rs:18-25` — `pub struct Image<T, B, const D: usize> where T: Scalar, B: ComputeBackend { data: Tensor<T, B>, origin: Point<D>, spacing: Spacing<D>, direction: Direction<D> }` — meaning the **Atlas substrate carrier is already present**; the gap is the trait surface (`Transform`, `Interpolator`, `Resampleable`) and the `ritk-spatial::{Vector, Point, Direction, Spacing}` Burn `Module`/`Record` impls.

### Single source of truth: Burn GPU-default drift, closed

As of inner RITK commit `65a1a0fd` (2026-07-06, prior to this ADR's sub-batch #1): `repos/ritk/Cargo.toml` workspace `burn` features are `[std, ndarray, autodiff]` (no `wgpu`, no `cuda`, no `rocm`); `xtask/burn_surface.allowlist` lists every approved Burn touchpoint; the RITK workspace dependency graph contains no `burn-wgpu`, `burn-cuda`, or `burn-rocm` package (verified by `cargo tree --workspace -i` for each). This commit closed `atlas/gap_audit.md` risk #1. Sub-batch #1 of this ADR does NOT touch `Cargo.toml` Burn features or the allowlist.

### Correction note: cognate Atlas substrate already exists

`repos/ritk/crates/ritk-image/src/native.rs:18` already exposes `pub struct Image<T: Scalar, B: ComputeBackend, const D: usize>` (Atlas-typed). Reading the pre-implementation state T1 confirms the substrate is in place; the rebind need only add the trait surface (parallel `TransformAtlas<T, B, D>`, `InterpolatorAtlas<T, B>`, `ResampleableAtlas<T, B, D>`) so that downstream consumer crates can incrementally migrate per sub-batch #3+. This avoids the additive-scope mistake of needing to also rewrite `Image<B, D>` (which remains the re-exported legacy public type and is untouched by this ADR's sub-batch #1).

## Decision

The Burn-keyed trait surface migrates to an Atlas-typed parallel trait surface across **6 atomic sub-batches**, each entitled to one atomic inner-repo commit and one atlas-meta pointer-advance chore commit. Atomic-boundary discipline (mandatory for all sub-batches):

1. **Strict additive OR strict subtractive per sub-batch**. A sub-batch either widens the Atlas surface (adds new pub-export, new trait, new impl) OR narrows the Burn surface (deprecates, removes, rewrites a symbol) — never both in one commit. This protects the rollback path: if a sub-batch's atomic commit causes a compile regression in a peer-active repo, the bisect can land on the violating commit and either revert or split.
2. **No public-type signature narrowing on the Burn-keyed surface** until sub-batch #5 (`ritk-burn-remove`, [major]). The legacy `Image<B: Backend, D>`, `Transform<B: Backend, D>`, `Interpolator<B>`, `Resampleable<B, D>`, `Vector<D>::Module<B>`, `Point<D>::Module<B>`, `Direction<D>::Module<B>`, `Spacing<D>::Module<B>`, and per-crate reader/writer `B: Backend` fn signatures stay exactly as today through sub-batch #4. Sub-batch #5 owns the cycle that changes these signatures or removes them.
3. **Cargo.toml is in one place per sub-batch**. Sub-batches #1, #2, #3, #4 grow three manifests (`ritk-core/Cargo.toml`, `ritk-image/Cargo.toml`, `ritk-spatial/Cargo.toml`) additively (new `[dependencies]` lines) where Atlas-typed declarations cross new crate boundaries. Sub-batch #5 is the only commit allowed to delete or rename `[dependencies]` lines in `ritk-core/Cargo.toml` or `ritk-wgpu-compat/Cargo.toml`. Sub-batch #6 owns the `xtask/burn_surface.allowlist` refresh.
4. **Compile gate per sub-batch**: `cargo fmt --check` + `cargo clippy --workspace --all-targets -- -D warnings` + `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` + `cargo test --doc` + `cargo doc --no-deps` (warning-clean).
5. **Atlas-only validation per sub-batch**: `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero (Burn GPU defaults closed; `burn-ndarray` CPU ref remains valid). `xtask/burn_surface.allowlist` only changes in sub-batch #6.

### Sub-batch #1 — `RITK-Atlas-typed-trait-surface` `[patch]` — **CLOSED 2026-07-06**

Additive Atlas-typed parallel trait surface alongside the Burn-keyed legacy. No breakage. No Burn dep removal. No `Cargo.toml` dep deletion. No allowlist refresh.

File scope (4 files plus 1 manifest, 5 files total):

1. **`repos/ritk/crates/ritk-core/Cargo.toml`** — add `coeus-core = { workspace = true }` and `coeus-tensor = { workspace = true }` to `[dependencies]`. Both are workspace-declared at `repos/ritk/Cargo.toml:78-79`. Pure inline adition.
2. **`repos/ritk/crates/ritk-image/src/lib.rs:11`** — add `pub use native::Image as AtlasImage;` immediately after the existing `pub use types::Image;`. The `AtlasImage<T, B, D>` re-export points at `native::Image<T, B, D>` from `ritk-image/src/native.rs:18-25` (Atlas-typed, already in place). This makes `AtlasImage` cross-crate reachable: `ritk_core::AtlasImage<T, B, D>` resolves via `ritk_image::AtlasImage` because `ritk-core/Cargo.toml:18` already depends on `ritk-image`.
3. **`repos/ritk/crates/ritk-core/src/transform/trait_.rs`** — append two new Atlas-typed traits AFTER the existing `Transform` and `Resampleable` traits:
   ```rust
   /// Atlas-typed parallel to [`Transform`]. Day-1 surface; concrete impls
   /// land in sub-batch #3+ as consumer crates migrate. The carrier is
   /// `ritk_image::AtlasImage<T, B, D>`, re-exported in [transform/trait_]
   /// as [`AtlasImage`].
   #[allow(dead_code)]
   pub trait TransformAtlas<T: coeus_core::Scalar, B: coeus_core::ComputeBackend, const D: usize>: Sized {
       fn transform_points(&self, points: coeus_tensor::Tensor<T, B>) -> coeus_tensor::Tensor<T, B>;
       fn inverse(&self) -> Option<Self> { None }
   }

   /// Atlas-typed parallel to [`Resampleable`].
   #[allow(dead_code)]
   pub trait ResampleableAtlas<T: coeus_core::Scalar, B: coeus_core::ComputeBackend, const D: usize> {
       fn resample(
           &self,
           shape: [usize; D],
           origin: ritk_spatial::Point<D>,
           spacing: ritk_spatial::Spacing<D>,
           direction: ritk_spatial::Direction<D>,
       ) -> Self;
   }
   ```
4. **`repos/ritk/crates/ritk-core/src/interpolation/trait_.rs`** — append one new Atlas-typed trait AFTER the existing `Interpolator`:
   ```rust
   /// Atlas-typed parallel to [`Interpolator`]. Day-1 surface.
   #[allow(dead_code)]
   pub trait InterpolatorAtlas<T: coeus_core::Scalar, B: coeus_core::ComputeBackend> {
       fn interpolate<const D: usize>(
           &self,
           data: &coeus_tensor::Tensor<T, B>,
           indices: coeus_tensor::Tensor<T, B>,
       ) -> coeus_tensor::Tensor<T, B>;
   }
   ```

Trait-body shape: the three new traits use **default-method-only bodies with no concrete impls on day 1**. Rationale: a same-shape parallel trait with no impls is the minimum viable additive surface, exposing the Atlas contract so downstream consumer crates (`ritk-filter`, `ritk-registration`, `ritk-segmentation`, `ritk-transform`, `ritk-interpolation`) can choose to implement one or the other (or both, for compatibility) during sub-batch #3 migration. This is the SSOT `coeus_core::Scalar`-bound counterpart of the Burn-keyed trait; the Burn trait's `transform_points`/`interpolate`/`resample` required-method shape is preserved verbatim with only the backend/generic swap.

Critical correction (cross-walked from the thinker's pre-implementation review): the legacy `Transform` operates on **point geometries** (`Tensor<B, 2>` shape `[Batch, D]`) not full images; the legacy `Interpolator` uses **batched indices** (`Tensor<B, 2>`, `[Batch, Rank]`) not `[f64; D]` arrays. The Atlas-typed parallels must mirror these exactly — any operator signature confusion would force an additional cross-trait shape-bridging commit in sub-batch #3 and break the additive-only invariant.

### Sub-batch #2 — `RITK-trait-deprecate` `[patch]` — RESERVED

Soft deprecation markers on the Burn-keyed surface. Add `#![deprecated]`-equivalent documentation warnings only. No `#[deprecated]` attribute on Burn-keyed items (that would force consumer compile warnings on every use today, multiplied by 671 burner source files). Document the migration path on each trait's doc-comment. Cargo.toml, allowlist, Burn deps: untouched.

### Sub-batch #3 — `RITK-crate-migrate` `[minor]` — RESERVED

Per-crate Atlas-typed migrators: `ritk-filter` (296 burner-touching files, leads), then `ritk-registration` (~109-129 files), then `ritk-segmentation` (88 files), then `ritk-model` (18-36 files), then `ritk-statistics` (~20-32 files), then `ritk-{io,interpolation,transform}` (24-30 each), then `ritk-{python,cli,snap}` (11-14 each). Each per-crate commit is itself sub-sub-atomic (allowlist is still the SSOT). The sub-batch #3 closeout is when the last per-crate commit lands and `xtask/burn_surface.allowlist` source-entries parcels to the migration-done rows.

### Sub-batch #4 — `RITK-spatial-rebind` `[patch]` — RESERVED

`repos/ritk/crates/ritk-spatial/src/{vector,point,direction,spacing}.rs`: drop `impl<B: Backend, D> burn::module::Module for *` and `impl<B: Backend> burn::record::Record for *` impls. Add `impl<T: Scalar, B: ComputeBackend> coeus_nn::Record for *` (only if downstream `coeus-nn` Pin-NN code requires the rebind; otherwise omit and skip the impl entirely — Burn-keyed `Module`/`Record` go away with no Atlas-side replacement). Cross-walk ADR 0005 §Decision §5 for the `coeus_core::Scalar` SSOT validity of any downstream submit.

### Sub-batch #5 — `RITK-burn-remove` `[major]` — RESERVED

Cargo dep strip cycle for Burn: `repos/ritk/Cargo.toml:69-72` (or current `burn` workspace dep), `ritk-core/Cargo.toml:23-24` (`[dev-dependencies] burn`, `burn-ndarray`), `ritk-image/Cargo.toml:9-10` and `ritk-wgpu-compat/Cargo.toml:8` (feature `apply_row_chunks<B: Backend>` removal / docstring only, no async), per-crate `burn` and `burn-ndarray` dep cleanup from `crates/ritk-{filter,transform,interpolation,registration}/Cargo.toml`. Also: `Image<B, D>` re-export path switches from `pub use types::Image;` to `pub use native::Image;` (or a new shim file `pub use AtlasImage as Image;` — verify which is preferred by `atlas/checklist.md` §Batch #3 §Plan step 1). CHANGELOG: `[major]` per RITK; cross-link the [arch] Burn remove plan in next sprint.

### Sub-batch #6 — `RITK-xtask-ci` `[patch]` — RESERVED

`xtask/burn_surface.allowlist` contract on sub-batch #5 re-enter (allowlist source-entries removed; the allowlist file becomes the post-migration SSOT and is archived or rewritten). CI scan gates tighten: new CI gate asserts zero `burn::tensor::Backend`-bound public symbols; new CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph. CHANGELOG `[patch]` per RITK (CI-only).

## Alternatives considered

### Alternative A — single `[major]` Burn removal commit

The §Plan in `atlas/checklist.md` §Batch #3 §Plan 1 records this as the original intent: "Migrate signatures: `Image<B: ComputeBackend, D>`; `Transform<B: ComputeBackend, D>`; ...; Drop `burn::record::Record` impls on `ritk-spatial::Vector/Point/Direction/Spacing`; ...". Rejected because: (i) the rebind covers 671 burner source files; one atomic commit would create an unreviewable diff at `cargo diff -U20` magnitude; (ii) any single error forces a revert of the entire rebind, not just the offending sub-tree; (iii) downstream consumer crates in `kwavers-imaging`, `helios-imaging`, `ritk-cli`, `ritk-python` would each need a synchronized commit, multiplying the peer-WIP collision surface. The 6-sub-batch cadence is the proposed SSOT-respecting discipline per the atomic-boundary rule above.

### Alternative B — empty `pub trait TransformAtlas: coeus_core::ComputeBackend {}` (zero required methods)

Rejected per `consolidation_discipline` and the §Decision §2 atomic-boundary discipline: a zero-method parallel trait with zero impls on day 1 is structurally dead code and an alias-driven architecture violation (`integrity`). The day-1 surface must at minimum mirror the Burn trait's required method (`transform_points` / `interpolate` / `resample`) so that downstream consumer crates that pick one or the other during sub-batch #3 have a concrete contract to satisfy.

### Alternative C — interop shim `Image<B: Backend + ComputeBackend>` single-bound impl

Rejected per the thinker's pre-implementation critique: the trait bound `B: burn::tensor::Backend + coeus_core::ComputeBackend` cannot be satisfied by any type because `burn::backend::NdArray` implements only `burn::tensor::Backend` and `coeus_core::SequentialBackend` implements only `coeus_core::ComputeBackend` — no shared type exists. Any interop shim must accept TWO distinct backend parameters and route through `Vec<T>` after `data_cow_on`/`to_contiguous_on`: `fn from_legacy<B_burn: Backend, B_coeus: ComputeBackend>(legacy: Image<B_burn, D>) -> Image<B_coeus, D>`. This is a sub-batch #3+ surface, not sub-batch #1; defer to that commit so the additive-only invariant of sub-batch #1 holds.

### Alternative D — keep `#![deprecated]` attr on every Burn-keyed consumer (`#[deprecated(since = "0.X", note = "...")]`)

Rejected for sub-batch #2: the 671-file consumer surface would emit a compile `#[deprecated]` warning per use site per build, polluting test logs (`cargo test` warnings count must be zero per `atlas/checklist.md` §Per-batch pre-flight gates). Soft documentation deprecation only.

## Failure modes / risks

- **Cross-stream peer-WIP collision**: `repos/ritk` HEAD as of this ADR is `65a1a0fd` (clean, no peer WIP). Sub-batches #2-#6 land on subsequent turns; any peer stream that opens a concurrent claim on `repos/ritk` must coordinate via `atlas/docs/coordination/` (per ADR 0011 §Decision §Leg 3 disjoint-scope rule).
- **Cargo.toml dep-cycle risk**: sub-batch #1 adds `coeus-core` and `coeus-tensor` to `ritk-core/Cargo.toml`. Both are workspace-declared (cross-walked at `repos/ritk/Cargo.toml:78-79`); adding them as cross-crate deps does NOT introduce new transitive deps (coeus-core pulls eunomia and hermes; coeus-tensor pulls coeus-core; the dep graph is well-formed in atlas-meta).
- **Trait-bound conflation risk (legacy ↔ Atlas)**: a user implementor who wants both `Transform<B: Backend, D>` AND `TransformAtlas<T: Scalar, B: ComputeBackend, D>` for the same `Self` type must be able to disambiguate. The legacy vs Atlas trait names are distinct (`Transform` vs `TransformAtlas`, `Interpolator` vs `InterpolatorAtlas`, `Resampleable` vs `ResampleableAtlas`) and the type-parameter cardinality is mirrored. No conflation.
- **Sub-batch #5 signature-removal risk (CR-1-like)**: deleting `pub use types::Image;` or renaming the re-export is a `[major]` event per RITK semver; must be coordinated with the cross-link to `atlas/checklist.md` §Batch #3 #5 and the next-sprint roll-out.
- **Atlas-meta residual-pointer drift**: the atlas-meta submodule pointer for `repos/ritk` advances per sub-batch. If a sub-batch's inner-repo commit does not land in the same turn as the atlas-meta chore commit, the Atlas-meta pointer lags; the `atlas/backlog.md` §In-flight claims row flags this lag explicitly. The first atlas-meta chore after this ADR lands: `chore(atlas): Sync ritk/atlas-migration-push/batch3 sub-batch #1 + Atlas meta pointer advance`, anchoring on the inner SHA from step §Sequencing 1.

## Verification plan

Per `engineering_gates` and §Sequencing / atomic-boundary discipline §4:

1. After sub-batch #1 (closed): `cargo fmt --check` + `cargo clippy --workspace --all-targets -- -D warnings` + `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` + `cargo test --doc` + `cargo doc --no-deps` (warning-clean).
2. `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero (re-verify the post-`65a1a0fd` state).
3. `xtask/burn_surface.allowlist` header-line count unchanged: still 1 header + 27 manifest rows + 437 source rows (sub-batch #1 does not change the allowlist).
4. Atlas-meta confirmation per `atlas/checklist.md` §Per-batch pre-flight gates: `git -C repos/ritk status --short` outputs zero (post inner commit). Atlas-meta submodule pointer advances; atlas-meta PM artifacts (`backlog.md`, `checklist.md`, `gap_audit.md`) record sub-batch #1 closure.
5. ADR-0005 cross-walk: `repos/ritk/crates/ritk-core/src/transform/trait_.rs` and `interpolation/trait_.rs` (post sub-batch #1) reference `coeus_core::Scalar` directly (matches SSOT rebind resolution per ADR 0005 §Decision §5).
6. Reserved inner tag: `ritk/atlas-migration-push/batch3` per ADR 0010 §Decision §"Per-batch name pattern"; tag annotation body enumerates the 6-sub-batch chain.

## Sequencing (implementation increments, atomic commits)

Per §Decision §atomic-boundary discipline §1, each sub-batch is its own atomic commit. Reserved sequence per the atlas-meta `codex/kwavers-atlas-integration` branch:

1. **Sub-batch #1** — current turn. Inner commit on `repos/ritk` titled `feat(ritk)!: Sub-batch #1 RITK Atlas-typed parallel trait surface (additive, ceremonious)`; atlas-meta chore `chore(atlas): Sync ritk/atlas-migration-push/batch3 sub-batch #1 + Atlas meta pointer advance`. CHANGELOG per RITK `[patch]`. Inner tag `ritk/atlas-migration-push/batch3` annotates on the inner RITK SHA.
2. **Sub-batch #2** — next turn (or whenever the @codex-codex task picks up Batch #3; reserved — drop into `atlas/backlog.md` §In-flight claims if not in-current-turn). Inner commit on `repos/ritk` titled `feat(ritk): Sub-batch #2 RITK Atlas trait soft deprecation documentation`; atlas-meta chore `chore(atlas): Sync ritk/atlas-migration-push/batch3 sub-batch #2 + docs-rounding`. CHANGELOG `[patch]`.
3. **Sub-batch #3** — reserved. Multi-commit canvas (one per per-crate increment). Inner commits on `repos/ritk` titled `feat(ritk): Sub-batch #3.{a,b,c,d,e,f} RITK per-crate Atlas-typed migration`; atlas-meta chore per per-crate increment advances the `ritk/atlas-migration-push/batch3` tag-update (single tag, multiple annotated commits on the annotated chain). CHANGELOG `[minor]` per RITK; cross-link the per-crate commits in the tag annotation body.
4. **Sub-batch #4** — reserved. Inner commit on `repos/ritk` titled `feat(ritk): Sub-batch #4 RITK-spatial rebind (drop Burn Module/Record impls)`; atlas-meta chore. CHANGELOG `[patch]`.
5. **Sub-batch #5** — reserved. Inner commit on `repos/ritk` titled `feat(ritk)!: Sub-batch #5 RITK Burn Cargo dep strip + Image<B,D> re-export path`; atlas-meta chore. CHANGELOG `[major]`; BREAKING CHANGE footer; pre-merge gate [`cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial`](https://github.com/obi1kenobi/cargo-semver-checks) authoritative classification.
6. **Sub-batch #6** — reserved. Inner commit on `repos/ritk` titled `ci(ritk): Sub-batch #6 RITK xtask/burn_surface.allowlist contract + CI scan gates + Atlas-only backend trait assertion`; atlas-meta chore. CHANGELOG `[patch]`.

Atlas-meta claim scope per sub-batch: `atlas/{backlog,checklist,gap_audit}.md` and (for sub-batches #2+ only) `docs/adr/INDEX.md` cross-link. The atlas-meta branch anchor remains `codex/kwavers-atlas-integration` per `atlas/backlog.md` §In-flight claims.

## Out of scope (explicit non-goals)

- **Re-binding Burn-wgpu / Burn-cuda / Burn-rocm backends** (already retired per `repos/ritk/Cargo.toml:69-72` post `65a1a0fd`). Sub-batch #5 reinforces the retirement; no replacement GPU Burn backend slot opens.
- **Re-binding `burn::record::Record` to a coeus-side equivalent when no Atlas-side consumer requires it**. Sub-batch #4 only adds `coeus_nn::Record` impls IF downstream PINN-SSM consumer code in `kwavers-solver` or `helios-solver` mandates them; otherwise sub-batch #4 is a strict removal commit.
- **Migrating `pyo3` Python bindings in `ritk-python`** in this rebind (out-of-scope per the Atlas-meta convention: Python bindings stay Burn-keyed at the python crate level and route through the `Image<B, D>` legacy type; the Atlas-side Python work is a separate epic in `atlas/backlog.md` §Outer-scope).
- **Forward-porting Atlas substrate to `kwavers-imaging` or `helios-imaging`**. Those crates consume `ritk` and would migrate after sub-batch #5 lands; their Atlas migration is tracked separately in `atlas/backlog.md` §Out-of-scope and `kwavers/gap_audit.md` / `helios/gap_audit.md` per-repo.
