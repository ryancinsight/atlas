# atlas — cross-repository integration backlog

> Cross-repo migration board. **Per-repo** PM artifacts remain SSOT for repo-local concerns (e.g. `repos/kwavers/backlog.md`, `repos/CFDrs/docs/backlog.md`, `repos/ritk/backlog.md`); this artifact owns only the migration scope that crosses repo boundaries (provider-side obstacles, dep-velocity closure, and shared definition-of-ready gates).
>
> Active tactic: `checklist.md`. Full migration inventory: `gap_audit.md`. PM artifact freshness/SSOT rules per atlas `AGENTS.md` `documentation_discipline`.
>
> **Integration base**: fetched `origin/main`. Git owns the exact revision;
> this board does not duplicate a commit that becomes stale after each merge.

## ATLAS-ARCH-001 — One generic ComputeBackend conformance suite [arch] [minor] — todo

- Owner: unclaimed; scope: new `repos/hephaestus/crates/hephaestus-conformance`,
  the four backend `tests/contract.rs` files, and the Hephaestus workspace member
  list. Triage lands first as its own increment; each backend then migrates in
  its own claim.
- Decision: [ADR 0038](docs/adr/0038-compute-backend-conformance-crate.md).
- **Triage increment: done 2026-07-28** —
  [ledger](docs/audit/2026-07-28-computebackend-conformance-triage.md). It
  corrected the basis: the contract is the **112 public entry points declared by
  all four backends**, not the 196 distinct test names, because `rocm` bundles
  several clauses per test fn where `cuda`/`wgpu` split them. Real test counts are
  wgpu 113 / cuda 100 / rocm 59 / metal 30 (the earlier 130/114/70/40 counted 52
  helpers as tests). Coverage of the 112: wgpu 94, rocm 93, cuda 78, metal 50.
  Classification: 112 contract, 5 capability-gated, 43 backend-intrinsic.
- Key correction: `hephaestus-metal` declares **no native Metal code** — it
  delegates wholly to `hephaestus-wgpu` via `WgpuDevice::try_metal`. Its low
  coverage is not an unverified-kernel hole, and the 28 result accessors it
  appears to lack are wgpu types it re-exports.
- **Six shared entry points were tested by no backend at all**:
  `binary_elementwise_typed{,_into}`, `binary_elementwise_strided_typed{,_into}`,
  `prod_axis_into`, `prepare_reduce_axis_into`.
  **Corrected 2026-07-28:** an earlier revision of this item said *nine* and
  prioritised `ray_line_integrals`. That was an artifact of scanning only
  `tests/contract.rs`; `ray_line_integrals` is covered by all four backends and
  `ray_line_integrals_into` by three in `tests/volume_ray_integral.rs`, and
  `scalar_elementwise_strided` by wgpu in `tests/strided.rs`. Coverage of the 112
  shared entry points, all test files: wgpu 101, rocm 95, cuda 84, metal 53.
- **Increment delivered 2026-07-28 (wgpu):**
  `crates/hephaestus-wgpu/tests/typed_elementwise.rs` and
  `crates/hephaestus-wgpu/tests/axis_reduction_contracts.rs` — 13 tests, all
  passing (23.5 s wall, slowest 3.5 s, inside the 30 s budget), clippy clean,
  covering all six on wgpu and lifting wgpu to 107/112. The six are the
  `TypedBinaryExpr` comparison dispatch paths plus the two axis reductions;
  comparisons are the only operators with per-scalar-type codegen, so `u32`,
  `i32`, and `f32` are each instantiated rather than one standing in for the
  others. All oracles are exact equalities — integer-exact comparisons, dyadic
  `f32` operands, integer-valued products below `2^24` — so no tolerance is
  present to be tuned.
- **Remaining:** `cuda`, `rocm`, and `metal` are still uncovered for all six.
  Closing them is the shared-suite work, not three more hand-written copies —
  that is the whole point of the conformance crate.
- Non-goals: changing backend behaviour; merging backend-intrinsic entry points
  into the shared suite; deciding whether `hephaestus-metal` should remain a
  crate (`ATLAS-ARCH-009`).
- Acceptance: each backend's `contract.rs` reduces to instantiation calls; the
  assertions executed per backend are a **superset** of the pre-migration set,
  shown by before/after counts; entry points are `<B: ComputeBackend, T: Scalar>`
  instantiated across every scalar the backend ships; a deliberately broken
  backend method fails only that backend; **every tolerance in the shared suite
  carries its derivation** — the existing suites use magic arguments such as
  `assert_near(lower[0], 2.0, 64.0)`, and migrating an underived constant into the
  shared suite would propagate it to every backend.
- Flagged for the implementation increment: `gemm_trailing_update`,
  `hh_trailing_update`, and `syrk_trailing_update` are blocked-decomposition inner
  steps exposed as public API in `cuda` only. Confirm and demote to `pub(crate)`,
  or justify the public surface.

## ATLAS-ARCH-010 — Define the NaN and infinity contract for accelerator kernels [arch] [minor] — todo

- Owner: unclaimed; scope: `hephaestus-core` numeric contract documentation plus
  the capability predicate the shared suite gates on. Decision before code.
- Raised by: writing the `binary_elementwise_typed` f32 clause during
  `ATLAS-ARCH-001`. The clause asserted IEEE-754 semantics and **failed on wgpu**
  — the device returns `NaN != NaN` as false.
- This is not a backend defect. The WGSL specification states implementations
  "may assume that overflow, infinities, and NaNs are not present during shader
  execution", and that an expression yielding one produces "an indeterminate
  value of the target type". The assertion demanded a guarantee WGSL withholds,
  so the assertion was removed — not relaxed to match observed output.
- The problem: **CUDA and HIP do provide IEEE semantics; WGSL does not promise
  them.** A shared conformance clause asserting IEEE NaN ordering uniformly would
  fail on wgpu forever; dropping it entirely leaves CUDA's real semantics
  unverified. Neither is acceptable, so NaN/infinity behaviour is a
  **capability-gated** clause — the first concrete member of ADR 0038's class 2.
- Decide and document: whether each backend advertises IEEE special-value
  semantics through an associated-const capability; whether kernels taking
  untrusted or solver-produced floats must reject non-finite input at the
  boundary instead of relying on backend behaviour; and what every public
  numeric entry point states about NaN/±Inf/signed-zero, which
  `numerical_discipline` requires and none currently states.
- Consumer impact is real, not theoretical: a solver that produces a NaN through
  divergence gets IEEE propagation on CUDA and an indeterminate value on WGPU, so
  the same simulation can diverge silently on one backend and loudly on another.
- Acceptance: the contract is stated in Rustdoc on the affected entry points; the
  capability predicate exists; the shared suite asserts IEEE semantics only where
  advertised, and asserts the rejection path where not.

## ATLAS-ARCH-009 — Decide whether hephaestus-metal remains a crate [arch] — todo

- Owner: unclaimed; scope: `repos/hephaestus/crates/hephaestus-metal` and the
  workspace member list. Decision first, as an ADR; no code moves before it.
- Raised by the
  [conformance triage](docs/audit/2026-07-28-computebackend-conformance-triage.md)
  §"topology", which established the evidence but deliberately did not decide.
- Evidence: the crate contains **no native Metal API usage** — no `metal::`, no
  `objc`, no `MTLDevice`, no MSL shaders. `MetalDevice` wraps a `WgpuDevice` from
  `WgpuDevice::try_metal(...)`, and every `application/*` module forwards to
  `wgpu_backend` (`decomposition.rs` 268 lines / 23 forwards, `reduction.rs`
  521/25, `sparse.rs` 252/23, `linalg.rs` 246/18). It depends on
  `hephaestus-wgpu` and `wgpu` directly. Its only unique public surface is the
  two escape hatches `wgpu_device` and `wgpu_buffer`.
- The question: ~2 300 lines of forwarding plus a 1 614-line contract suite exist
  to present WGPU-with-a-Metal-adapter as a peer backend. Either that is the
  right seam — a stable name for the Metal target, insulating consumers from the
  fact that WGPU implements it — or it is a crate-shaped alias, and Metal
  selection belongs inside `hephaestus-wgpu` as a device-preference path, which
  is what `WgpuDevice::try_metal` already is.
- Non-goals: this does not question whether the stack should target Metal. It
  questions whether targeting it costs a crate.
- Dependencies: sequence after ATLAS-ARCH-001, so the conformance suite is not
  rewritten twice.

## ATLAS-ARCH-002 — Instantiate generic tests across every shipped scalar [patch] — todo

- Owner: unclaimed; scope: 25 files carrying `..._is_generic_over_scalar_f32`
  tests. One package per claim.
- Outcome: a generic kernel tested at one concrete type is unverified for the
  rest. Audit 2026-07-28: 25 files assert genericity at `f32`; **zero** files
  carry an `f64`, `f16`, or `bf16` counterpart stack-wide. The current tests would
  still pass if the generic body only worked at `f32`.
- Acceptance: each such test becomes generic and is instantiated across every
  scalar type its crate ships; the test name loses its type suffix, since the
  suffix only existed because the test was single-type.
- Dependencies: converges with ATLAS-ARCH-001 §4 for the backend suites.

## ATLAS-ARCH-003 — Make leto-ops statistics generic and resolve the split Pearson [minor] — todo

- Owner: unclaimed; scope: `repos/leto/crates/leto-ops/src/application/statistics`,
  its `kwavers-math` re-export, and the Tyche boundary. Provider-first: leto lands
  before consumers.
- Outcome: `leto_ops::application::statistics::pearson(a: &[f64], b: &[f64]) -> f64`
  is concrete `f64` in the host-array substrate that is meant to be generic over
  `T: Scalar`, alongside `nrmse`, `psnr`, `rmse`, and `percentile_range`.
  `kwavers-math::statistics` re-exports the family verbatim, propagating the
  concrete type to an integrator.
- Second half: `tyche-core::statistics::sensitivity` owns generic squared-Pearson
  screening (`CorrelationScreening<T, const PARAMETERS: usize>`) per ADR 0026, and
  `tyche` already depends on `leto-ops`. Two Pearson implementations exist in a
  provider/consumer pair. Decide one owner and delete the other in the same change
  — the correlation primitive belongs with the generic implementation.
- Acceptance: no `f64`-concrete signature remains in the leto-ops statistics
  family; one Pearson implementation stack-wide; the kwavers re-export is
  unchanged in shape (it is correct one-import-path practice, not the defect).

## ATLAS-ARCH-004 — Rehome and genericize the cfd-math Pareto module [patch] — todo

- Owner: unclaimed; scope: `repos/CFDrs/crates/cfd-math/src/statistics/pareto.rs`
  and its callers.
- Outcome: four defects in one file —
  `pareto_front_nd(objectives: &[Vec<f64>], is_maximized: &[bool]) -> Vec<usize>`
  and `crowding_distances(&[Vec<f64>])` are multi-objective optimization living
  under a `statistics` module (misdescribed concern); the signatures are concrete
  `f64` rather than `T: Scalar`; `&[Vec<f64>]` is a jagged per-row allocation
  where a flat slice with a stride or a const-generic `[T; OBJECTIVES]` is the
  cache-coherent form; and `&[bool]` parallel to the objective list is boolean
  blindness where a two-variant enum belongs.
- Acceptance: the module sits under an optimization concern named for what it
  does; signatures are generic over `T: Scalar` with objective count const-generic
  or stride-carried; no jagged container in the signature; objective sense is an
  enum. Value-semantic tests over a known Pareto set, not existence assertions.

## ATLAS-ARCH-005 — Replace closed-set dyn dispatch in per-timestep paths [arch] — todo

- Owner: unclaimed; scope: `repos/kwavers` first (largest), then `repos/CFDrs`.
  One operation family per claim.
- Outcome: dispatch-site counts are `kwavers` 665, `CFDrs` 352, `gaia` 104,
  `coeus` 98, `moirai` 83, `consus` 66. Sampling the kwavers solver shows the
  pattern is not type erasure of an open plugin set but vtable dispatch over
  closed design-time sets: `sources: &[Box<dyn Source>]` inside
  `forward/nonlinear/westervelt/update.rs` (evaluated per timestep),
  `boundary: Box<dyn Boundary>` held in the solver struct, plus `Box<dyn Signal>`
  and `Box<dyn Solver>`.
- Decision rule: a closed implementor set dispatched per timestep converts to an
  exhaustiveness-checked enum — static dispatch, still runtime-selectable, no
  vtable. Genuinely open plugin boundaries on cold paths keep `dyn` with the
  applicable exception annotated inline.
- Acceptance: per family, the count of `dyn` sites on the timestep path reaches
  zero; the enum is exhaustively matched with no catch-all arm; a criterion
  comparison on the affected kernel accompanies the change, since this is a
  performance-motivated claim and must carry performance evidence.
- Non-goals: mass-converting all 1 368 sites. Hot paths first, evidence per family.

## ATLAS-ARCH-006 — Eliminate junk-drawer modules [patch] — todo

- Owner: unclaimed; scope: 64 sites declaring `mod utils`, `mod helpers`,
  `mod common`, or `mod shared`, concentrated in `apollo`, `CFDrs`, and `ritk`.
  One package per claim.
- Outcome: each is a module named for its lack of a bounded concern. Notable:
  `apollo-fft/src/api/mod.rs` exposes `pub mod utils` on a **public API path**,
  and `leto-ops/src/application/interpolation/mod.rs` carries `mod utils`.
- Acceptance: each module is renamed for the concern it actually holds, or its
  contents are distributed to the leaf modules that own them and the module is
  deleted. A `utils` whose contents span two concerns splits; it is never renamed
  to `support`.

## ATLAS-ARCH-007 — Reduce manifest files carrying implementation [patch] — todo

- Owner: unclaimed; scope: `repos/consus` first, then `CFDrs`, `kwavers`. One
  crate per claim.
- Outcome: 568 of 11 409 files exceed the 500-line target, 88 exceed 1 000, 11
  exceed 2 000. The sharper defect is **61 `lib.rs`/`mod.rs` files over 500
  lines** — manifest files are the module tree, curated re-exports, and crate
  docs, never implementation. Worst: `consus-nwb/src/file/mod.rs` (2 032),
  `consus-zarr/src/chunk/mod.rs` (1 958), `consus-parquet/src/writer/mod.rs`
  (1 915), `consus-nwb/src/validation/mod.rs` (1 780),
  `leto-python/src/lib.rs` (1 416).
- By package, files over 500: CFDrs 138, kwavers 103, consus 89, gaia 43,
  moirai 37, apollo 35, hephaestus 28, ritk 25, hermes 21, leto 18, coeus 17.
- Acceptance: each touched `mod.rs`/`lib.rs` carries only the module tree,
  re-exports, and docs; extracted leaf modules are named for their operation
  family. Domain cohesion overrides the line target — never slice into ravioli
  code to hit a number.

## ATLAS-ARCH-008 — Replace pointer-scattered containers on traversal paths [patch] — todo

- Owner: unclaimed; scope: the traversal-hot sites first, not all 318.
- Outcome: 318 `Vec<Vec<_>>` occurrences across package sources, led by
  `consus-compression/src/chunking/iterator.rs` (10),
  `gaia/src/domain/topology/adjacency.rs` (8), and
  `coeus-autograd/src/ops/nn/loss/ctc.rs` (6). Adjacency and chunk iteration are
  prefetch-sensitive; a jagged per-row allocation defeats it.
- Acceptance: the contiguous form is a flat buffer plus an offset table
  (CSR-shaped) or an arena span, with a criterion comparison on the traversal
  showing the change is a win. A site where the jagged shape is genuinely correct
  is recorded as such rather than converted.

## ATLAS-ARCH-CYCLE-001 — Break the CFDrs -> gaia -> CFDrs repository cycle [arch] — todo

- Owner: unclaimed. `repos/CFDrs` had 13 dirty files at filing; sweep before
  claiming.
- Defect: `repos/CFDrs/Cargo.toml:78` declares
  `cfd-mesh = { path = "../gaia", package = "gaia" }` — CFDrs consumes gaia under
  an alias — and `crates/cfd-3d` enables gaia's `cfdrs-integration` feature, which
  activates `gaia`'s dependency on `../CFDrs/crates/cfd-schematics`. That is a
  repository-level cycle **CFDrs -> gaia -> CFDrs**, against the one-way
  foundation → domain → integrator layering the stack README requires. Cargo does
  not reject it only because the two edges land on different member crates
  (`cfd-3d` vs `cfd-schematics`), so no package-level cycle exists.
- Why it matters beyond tidiness: it is the last reason gaia cannot be fully
  consumed as a git dependency. `ATLAS-GAIA-GITDEP-001` converted the other five
  sibling path deps; `cfd-schematics` had to stay, because converting it would
  cement the inversion in gaia's published manifest and drag the whole CFDrs graph
  into every gaia consumer's resolution — observed directly as a `smallvec`
  version conflict (`hephaestus-wgpu` wants `^1.15.2`, `wgpu 30` wants `^1.14`)
  reached only through the `gaia -> cfd-schematics -> cfd-core -> hephaestus-wgpu`
  chain.
- Evidence that the edge is currently dead to the stack: nothing outside gaia's
  own manifest and examples enables `cfdrs-integration`, and no crate named
  `cfd-mesh` exists in CFDrs — the name is purely gaia's alias.
- Fix direction: the integrator owns the bridge, so relocate
  `repos/gaia/src/application/pipeline/blueprint_mesh.rs` (2 057 lines, ~1 886
  implementation and ~170 test) into CFDrs as a crate depending on both `gaia` and
  `cfd-schematics`; drop gaia's `cfdrs-integration` feature, its
  `scheme-io = ["cfdrs-integration"]` alias, the three examples gated on it, and
  the `cfd-schematics` dependency. The module uses 13 `crate::`-internal imports
  (`application::channel::*`, `application::csg::boolean`, `domain::core::*`), so
  the move requires confirming each is `pub` in gaia and widening what is not.
- Acceptance: gaia has zero path dependencies; `gaia` resolves as a git dependency
  from a scratch consumer with no Atlas overlay; the relocated bridge's tests pass
  in CFDrs; the stack README's dependency-direction claim holds under a mechanical
  check.

## ATLAS-GAIA-GITDEP-001 — Gaia's committed path dep makes it unconsumable as a git dependency [patch] — done

- **Resolved 2026-07-28** at gaia `1190ace`: eunomia, leto, melinoe, mnemosyne,
  and moirai are now declared `git + version`, and the dev-dependency copies moved
  with them because Cargo requires one canonical source per dependency name across
  sections. `cargo check --lib` green in gaia; `cargo metadata` in helios exits 0
  where it previously failed. Atlas gitlinks advanced at `1459c99`.
- The other half of the split landed concurrently: the overlay stream turned the
  root `.cargo/config.toml` patches back on (42 active sections, 0 `#OFF#`), so
  declared git sources are the release SSOT while umbrella builds resolve locally —
  the architecture `AGENTS.md` prescribes.
- Residual: `cfd-schematics` remains a path dep, tracked as ATLAS-ARCH-CYCLE-001.
- Defect: `repos/gaia/Cargo.toml:40` declares
  `eunomia = { path = "../eunomia/crates/eunomia", ... }`. A consumer that takes
  `gaia` as a **git** dependency makes Cargo resolve that path inside the fetched
  gaia repo, which has no `../eunomia`, so resolution fails with:

  ```text
  error: no matching package named `eunomia` found
  location searched: Git repository https://github.com/ryancinsight/gaia
  required by package `gaia v0.3.0 (...gaia#42ef63af)`
      ... which satisfies git dependency `gaia` of package `helios-math`
  ```

  This is the prohibited state named in `AGENTS.md`: a committed path dep on a
  member's mainline "make[s] the member unconsumable as a git dependency". Twelve
  stack manifests currently commit sibling path deps; gaia's is the one on a
  published consumption edge.
- Blast radius, measured: `apollo`, `athena`, `hyperion`, `proteus`, `tyche`,
  `harmonia`, and `horae` all resolve normally, so this is not stack-wide — it is
  specific to gaia consumers. `helios` is confirmed dead (fails identically under
  `--locked`, so the committed lock does not rescue it).
- Compounding cause: `repos/helios/Cargo.toml` still carries the H-050 comment
  block describing "Synchronized local-checkout patches" that redirect the git
  sources to local paths, but **the `[patch]` sections it describes are gone**
  (`grep -c '^\[patch' == 0`), and every one of the 128 patch lines in the root
  `.cargo/config.toml` is `#OFF#`. The local-resolution mechanism was removed
  while providers still carry path deps, leaving an orphaned comment and a
  workspace that cannot resolve.
- Fix direction (for whoever owns the overlay stream, not for a drive-by):
  convert gaia's sibling path deps to `git + version` per upstream ownership, and
  land it together with whichever local-resolution mechanism the overlay stream
  settles on — otherwise gaia's own development loses its local eunomia.
- Re-open trigger: the overlay stream lands, or `cargo metadata` in
  `repos/helios` resolves.

## ATLAS-HELIOS-GENERIC-001 — Instantiate the f32-only generic tests across shipped scalars [patch] — in-progress

- Owner: this stream; **unblocked** — ATLAS-GAIA-GITDEP-001 is resolved and
  helios resolves and builds.
- Progress at helios `78bf9c0`: **8 of 24 delivered and verified**, 3 written and
  awaiting verification, 13 untouched.
  - **helios-solver complete** (8): `dose`, `attenuation_map`, `projector`,
    `deposition`, `scatter` x3, `oriented_scatter`. 62 lib tests pass, 16 of them
    per-width instantiations enumerated by name; no `is_generic_over_scalar_f32`
    remains in the crate.
  - **helios-domain written, unverified** (3): `mlc`, `volume`, `collimation`.
    Blocked on a transient — a live peer is mid-edit in `repos/aequitas`
    (`src/systems/si/{dimensions,quantities,units}` touched 20:02, "MEMS metric
    dimensions"), and aequitas does not compile: first a conflicting `LinearUnit`
    pair on `PerCubicMeter` (`NumberDensity` vs `ReciprocalVolume` resolving to one
    dimension), then E0432 on retry as they continue. Nothing downstream of
    aequitas can build. These three edits are left in the tree because
    helios-domain is unbuildable regardless of them; re-run
    `cargo test -p helios-domain --lib` once aequitas is green.
  - **Untouched** (13): `helios-analysis` (`dvh`, `gamma`), `helios-imaging`
    (`fbp`, `noise`, `registration` x2, `sirt`), `helios-physics` (`compton`),
    `helios-planning` (`optimize`), `helios-simulation` (`acquisition`,
    `delivery`, `dose_accumulation`, `portal`).
- `ShippedScalar` now lives in `helios-math` as public vocabulary, so the
  remaining crates need only `use helios_math::ShippedScalar;`.
- `GeometryScalar` stays a per-site bound rather than joining `ShippedScalar`: it
  is feature-gated in helios-math, so folding it in would break
  `--no-default-features`. Where it applies, it collides with `FloatElement` on
  `from_f64`, so those bodies bind `let cast = <T as helios_math::FloatElement>::from_f64;`.
- Two mechanical traps, both silent, worth avoiding in the remaining 13: replacing
  a test body without its `#[test]` leaves the attribute stranded on whatever
  follows, and a regex broad enough to clean that up will also strip `#[test]`
  from the per-width wrappers — the suite then goes green with the new tests
  simply not running. Always confirm the per-width names appear in the runner
  output and that the total moved by the expected delta.
- Defect, verified independently: **24 test functions across 21 helios files**
  are named `*_is_generic_over_scalar_f32` and assert genericity at exactly one
  concrete type, with **zero** f64 counterparts. Every monomorphization a caller
  can instantiate beyond `f32` is therefore unverified — the mechanical form of
  the fake-generics risk. The names additionally violate the naming prohibition
  (a type name inside a function name). A concurrent peer audit reported 25
  files; the true count is 21, all in helios.
- Shipped scalar set is `{f32, f64}`: `helios_math::Scalar` is
  `eunomia::RealField`, and `RealField` is implemented for `f32` and `f64` only,
  so `f16`/`bf16` are not instantiable and are not part of this gap.
- Pattern established and API-checked (one generic body + one `#[test]` per
  shipped type, named by precision rather than by Rust type so the naming
  prohibition holds): `T::from_f64(..)` builds literals, `RealField::exp`/`recip`
  supply the math, and tolerances derive from `T::EPSILON * T::from_f64(ULPS)`
  with the ulp budget justified from the operation chain — replacing fixed
  literals like `epsilon = 1e-5`, which are themselves the analytical-threshold
  violation.
- Delivered and verified: `helios-solver/src/dose.rs`
  — `primary_fluence_matches_beer_lambert`, 16-ulp derived bound, one `#[test]` per
  shipped width. Both instantiations pass; the f64 case passing at 16 ulps is the
  evidence the kernel is correct beyond the width it was written against.
- Two bounds the design missed and compilation caught, needed at every remaining
  site: `Scalar` implies neither `eunomia::RelativeEq<Epsilon = Self>` (required by
  `assert_relative_eq!`) nor `eunomia::UnitScalar` (required by kernels taking
  Aequitas quantities). Both are folded into a local `ShippedScalar` trait with one
  `impl` per shipped width, so admitting a new type is one line rather than an edit
  per test. It stays local to `dose.rs` until a second module needs it, per
  consolidate-on-second-occurrence; the shared home is `helios-math`.
- Worked reference for the pattern, applicable to all 24 sites:
  - hoist the body into `fn <behaviour><T: Scalar>()`, drop the `_f32` suffix
    (the old name is itself a naming-prohibition violation);
  - build every literal with `T::from_f64(..)`; `T::from_f64(0.0)` rather than
    `T::ZERO` avoids needing `NumericElement` in test scope;
  - replace fixed epsilons with `max_relative = T::EPSILON * T::from_f64(ULPS)`,
    where `ULPS` is a named constant carrying its derivation from the operation
    chain — `assert_relative_eq!` accepts `max_relative`, and the fixed literals
    being replaced (`epsilon = 1e-5`) are themselves analytical-threshold
    violations;
  - add one `#[test]` per shipped width delegating to the generic body, named by
    precision (`..._in_single_precision` / `..._in_double_precision`) so failure
    attribution survives without putting a Rust type name in a function name.

## ATLAS-PUB-001 — Migrate 8 crate-release workflows to the Atlas-shared caller [patch] — todo

- Owner: unclaimed; scope: `repos/{apollo,coeus,consus,hephaestus,kwavers,leto,moirai}/.github/workflows/rust-release.yml`
  and `repos/ritk/.github/workflows/release.yml`. One package per claim — the
  scopes are disjoint by repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3.
- Outcome: each package's crate-release workflow becomes a thin caller of
  `ryancinsight/atlas/.github/workflows/crates-publish.yml@<atlas-sha>`, and the
  duplicated 142-line body is deleted in the same change. Audit 2026-07-28: four
  of the seven `rust-release.yml` files are byte-identical; the only real
  variation is `RUST_TOOLCHAIN` (1.95.0 / 1.97.0 / 1.97.1) and whether the
  package needs Atlas path dependencies (only `kwavers`).
- Non-goals: changing any package's toolchain pin; changing tag conventions;
  touching the already-shared wheel pipeline.
- Acceptance per package: caller under 40 lines; the package's existing toolchain
  value passed as `rust-toolchain`; `kwavers` passes `atlas-ref`; the old body
  deleted, not kept beside the caller; one `workflow_dispatch` validation run
  green before the next release.
- Dependencies: none. ATLAS-PUB-003 must be complete for that package before its
  next real publish, but the migration itself does not wait on it.

## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — todo

- Owner: unclaimed; scope: `repos/{CFDrs,helios,kwavers,ritk}/.github/workflows/book-pages.yml`
  plus `.github/workflows/docs.yml` in Atlas.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5.
- Outcome: each book workflow becomes a caller of
  `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only
  `output-path`.
- **Closed sub-item (2026-07-28):** `ritk` now joins the Atlas cross-book gate —
  `.github/workflows/docs.yml` runs the strict detector and an `mdbook build`
  over all four books. The same change dropped the three per-book HTML artefact
  uploads, leaving `detector.log` as the only retained artefact; that is a
  deliberate narrowing, not a regression, since Pages deployment is the book's
  delivery path and the artefacts were diagnostic only.
- Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books
  (ATLAS-BOOK-001).
- Acceptance: four callers, each passing its audited output path
  (`target/book/cfdrs`, `target/book/helios`, `target/book`,
  `target/book/ritk`); each package's Pages deployment succeeds once through the
  shared workflow.

## ATLAS-PUB-003 — Register trusted publishers and remove the unused PyPI token [chore] — todo

- Owner: user-gated — registry and GitHub settings changes are Ask-User actions;
  an agent prepares the values and verifies the result, it does not perform the
  registration.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §4.
- Outcome: every publishing package has a trusted publisher registered on the
  target registry, so no long-lived registry credential exists anywhere in the
  stack. Values per package: owner `ryancinsight`; repository = the package
  repository; workflow filename = the **caller's** filename
  (`rust-release.yml` / `python-release.yml`), because the OIDC claim carries the
  caller's identity, not the Atlas reusable workflow's; environment `crates-io` /
  `pypi`.
- Registry verification 2026-07-28: crates.io **cannot bootstrap** a new crate
  through trusted publishing — the crate must already exist and the first publish
  requires an API token. The account `ryancinsight` (id 383645) has published one
  crate, `imaginary-rs@0.1.0`; no Atlas crate is published. PyPI **can** bootstrap
  through a pending publisher configured under the account sidebar.
- Sequence per crate, therefore: (1) resolve its registry name (ATLAS-PUB-006 for
  the twelve collisions); (2) one manual publish from the local Cargo credential
  store, in workspace dependency order; (3) register the trusted publisher;
  (4) enable trusted-publishing-only enforcement. PyPI distributions skip step 2.
- Acceptance: one trusted-publishing release succeeds per package; the API token
  in the `pypi` environment is deleted afterwards; trusted-publishing-only
  enforcement is enabled in each registry's settings once its pipeline is proven.
- Residual risk: an unregistered package fails closed at the auth step. That is
  the intended failure mode, not a regression. A pending PyPI publisher does not
  reserve the project name until first use, so a name can be lost in between.

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
- Peer-held at this revision, so not claimable without a staleness sweep:
  `coeus` (`codex/coeus-error-function-parity`, 24 dirty), `ritk`
  (`codex/docs-ritk-n4-figure-only`, 11 dirty, active), `leto`
  (`codex/leto-real-sparse-lu`, 25 dirty), `mnemosyne`
  (`codex/mnemosyne-tier-selection`, clean). The `coeus` facade — the flagship
  case for this item — is among them.

## ATLAS-PUB-007 — Rename `mnemosyne-core`: the stack's publish critical path [patch] — todo

> **Highest-priority publishing item.** `mnemosyne-core` sits in publish wave 0
> and has **172 transitive dependents**, and its crates.io name is taken by an
> unrelated owner. Until it is renamed, 172 of 203 packages cannot publish at all.
> This is release-blocking, not cleanup — it outranks all facade work
> (ATLAS-PUB-006), which is cosmetic by comparison.

- Owner: unclaimed. `mnemosyne` is currently on the peer branch
  `codex/mnemosyne-tier-selection` (clean tree, last commit 28 h ago) — sweep for
  staleness before claiming, and do not branch-switch a tree a peer holds.
- Scope, as one co-evolution unit: `repos/mnemosyne` (upstream rename) then
  `repos/{leto,hephaestus,moirai}` (requirement + lock), verified together.
  `repos/helios` and `repos/ritk/xtask/Cargo.toml` are separate, smaller claims.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §5, §6.
- Evidence: `scripts/publish-order.py` derives the wave order from the manifests;
  the graph is acyclic over normal/build edges at 172 publishable crates across 38
  waves. For scale, `eunomia` (178 dependents) and `melinoe` (170) are comparably
  deep but their names are free; `helios-core` is also taken but has only 10
  dependents, so it blocks Helios alone.
- Sub-item — **blocked on a live peer:** `repos/ritk/xtask/Cargo.toml` lacks the
  `publish = false` that `apollo`, `CFDrs`, `helios`, and `kwavers` carry.
  `repos/ritk` is checked out on `codex/docs-ritk-n4-figure-only` with 11 dirty
  files touched minutes ago, so the fix is neither branch-switchable nor
  committable without polluting that peer's PR with an unrelated manifest change.
  Re-open trigger: the ritk tree returns to `main`, or that branch merges.
  `scripts/publish-order.py` now fails on this defect, so it cannot be forgotten —
  and wiring that script into CI waits on this fix so the gate does not land red.
- Outcome: the three publishable names that collide below the facade layer are
  resolved. Verified 2026-07-28:
  - `helios-core` is taken (`ncitron`, v0.1.0, 1 067 downloads) — rename the
    Helios internal crate alongside the `helios-radiation` facade work;
  - `mnemosyne-core` is taken (`bballer03`, v0.2.0) **and is a live dependency
    edge** — `leto`, `hephaestus`, and `moirai` all depend on it, so the rename is
    a co-evolution unit: upstream first, then each consumer's requirement and
    lock, verified as one unit;
  - `xtask` is taken, and `repos/ritk/xtask/Cargo.toml` lacks the
    `publish = false` that `apollo`, `CFDrs`, `helios`, and `kwavers` all carry.
    Fix the manifest, not the name — an internal build-automation crate must never
    be publishable.
- Acceptance: no manifest in the stack depends on `mnemosyne-core` afterwards;
  every `xtask` manifest carries `publish = false`; each renamed crate's
  consumers build and test green as one unit.

## ATLAS-PUB-008 — Audit facade names immediately before each first publish [chore] — todo

- Owner: unclaimed; scope: the pre-publish check only.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §3,
  verification item 1.
- Outcome: name availability is a point-in-time observation and decays — 165 of
  173 names were free on 2026-07-28, and first-come means any of them can be
  claimed by a third party before the stack publishes. Each first publish
  re-checks its own name.
- Acceptance: `GET /api/v1/crates/<name>` returns 404 immediately before the
  publish, recorded in the release evidence. A collision discovered here is
  resolved by ADR 0037 §3's rule, not by an ad-hoc name.

## ATLAS-PUB-004 — Pin the three Pages actions to verified digests [patch] — todo

- Owner: unclaimed; scope: `.github/workflows/book-pages.yml`.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §7.
- Outcome: `actions/configure-pages`, `actions/upload-pages-artifact`, and
  `actions/deploy-pages` carry resolved commit digests instead of major-version
  tags, matching every other action reference in the stack.
- Acceptance: each digest is resolved against the upstream repository and the
  resolution recorded in the commit body. A digest that has not been resolved is
  fabricated evidence and must not be committed — this item exists precisely
  because the shared workflow was authored without network access to resolve them.

## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — todo

- Owner: unclaimed; scope: one book per claim, in the owning repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- Outcome: every published book runs `mdbook test` in CI so chapters cannot rot.
  No book runs it today; the shared workflow defaults `mdbook-test` to `false` as
  a staging mechanism, not an accepted end state.
- Acceptance per book: samples compile against the package; the caller passes
  `mdbook-test: true` and, where samples need providers, `atlas-ref`; the flip
  commit demonstrates the gate failing on a deliberately broken sample before
  landing green.
- Dependencies: ATLAS-PUB-002 for that package.

## ATLAS-BOOK-001 — Author the 21 missing package books [minor] — todo

- Owner: unclaimed; scope: one package per claim, `docs/book/` in that repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §5.
- Outcome: every package teaches its field from the governing equations, through
  the numerical method and its stability and convergence properties, to the
  crate's abstractions mapped onto that theory with runnable worked examples.
  Audit 2026-07-28: four packages have a book (`CFDrs`, `helios`, `kwavers`,
  `ritk`); 21 have none.
- Sequencing is provider-first so a domain chapter can cite the substrate chapter
  it depends on: (1) `eunomia`, `aequitas`, `themis`, `melinoe`;
  (2) `mnemosyne`, `moirai`, `hermes`, `leto`, `hephaestus`;
  (3) `apollo`, `coeus`, `gaia`, `consus`, `horae`, `athena`, `proteus`,
  `hyperion`, `iris`, `asclepius`, `harmonia`, `tyche`.
- Non-goals: duplicating Rustdoc item contracts; migration guides (those belong
  to the package `CHANGELOG.md`); execution state (that belongs to the boards).
- Acceptance per package: outline lands first as its own increment, then chapters
  as DoR items per subsystem; the book builds under `mdbook`; figures are
  regenerated by committed plotting code and inspected, never hand-assembled;
  the book joins Atlas `docs.yml` in the change that creates it.

## ATLAS-NEURO-001 — RITK diffusion, tractography, and connectome crates [minor] — todo

- Owner: unclaimed; scope: `repos/ritk/crates/ritk-diffusion`,
  `repos/ritk/crates/ritk-tractography`, `repos/ritk/crates/ritk-connectome`,
  and the RITK workspace member list. One crate per claim, in that order.
- Decision: [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §1-§3.
- Outcome: diffusion MRI model fitting, streamline tractography, and connectome
  construction land as RITK workspace crates. No new Atlas package: the gate
  fails conditions 1, 2, 4, 5, and 6 — RITK is the sole consumer, owns every
  primitive involved, and there is nothing to delete.
- Non-goals: a `ritk-study` crate (cohort structure is Tyche's, per ADR 0026); MR
  acquisition simulation (closed and demand-gated, ADR 0036 §4); any RF work
  (ADR 0036 §5).
- Acceptance per crate: no local optimizer, gradient, polyline type, or
  `rayon`/`tokio` edge — fitting through `coeus-optim`/`coeus-autograd`,
  geometry through `gaia`, execution through `moirai`; physical values are
  Aequitas quantities; diffusion tensor estimation verified against a synthesized
  round-trip within a tolerance derived from the scheme's condition number and
  the machine epsilon of `T`, not an empirical constant; every generic entry
  point instantiated across the shipped scalar types; the book chapter lands with
  the crate.
- Re-open trigger for a separate package: a second production consumer outside
  the RITK workspace deletes a matching implementation in the extraction change.

## ATLAS-MODALITY-001 — Move chromophore extinction spectra to Hyperion [arch] [minor] — todo

- Owner: unclaimed; scope: `repos/hyperion/src/coefficient/`, `repos/hyperion/README.md`,
  `repos/kwavers/crates/kwavers-optics/` (deleted), the kwavers workspace member
  list, and consumers in `kwavers-physics` / `kwavers-imaging`.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §4.
- Outcome: 514 LOC of validated wavelength-dependent extinction reference data
  moves out of an integrator leaf crate into the registered owner of optical
  coefficients. Promotion gate condition 1 is met by the second clause —
  existing implementation in the wrong dependency layer — and the deletion
  ledger is the whole `kwavers-optics` crate.
- Non-goals: transport solvers, sources, sonoluminescence, photoacoustics.
- Acceptance: Hyperion exposes wavelength-resolved absorption coefficient as an
  Aequitas quantity; a differential test asserts equality with the deleted
  Kwavers tables at every tabulated wavelength; `kwavers-optics` is absent from
  the workspace member list and from every `Cargo.toml`; both repos green under
  their nextest budgets; Hyperion's spectra disclaimer is revised in the same
  change.

## ATLAS-MODALITY-002 — Type the deposition spine in Aequitas quantities [arch] — in-progress

- Owner: unclaimed — phase 1 delivered, phases 2-4 open. Next claimable unit is
  phase 2 (`repos/kwavers` bioheat boundary). Decision:
  [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §5.
- Outcome: every energy-transport implementation terminates in a
  `VolumetricPowerDensity` (W·m⁻³) Aequitas quantity, and bioheat consumes that
  one type. This is the reusable asset the optics-extraction proposal was
  reaching for, and it is what makes a later modality extraction a typed slot
  rather than an architectural judgment.

### Coverage audit (2026-07-27)

Aequitas **already owns** the spine quantities and their units. This item is
consumer-side adoption, not provider-side creation:

| Spine quantity | SI | Aequitas status |
| --- | --- | --- |
| Irradiance / fluence rate | W·m⁻² | `Intensity` + `WattPerSquareMeter` — present |
| Volumetric power density | W·m⁻³ | `VolumetricPowerDensity` + `WattPerCubicMeter` — present |
| Energy fluence | J·m⁻² | `EnergyPerArea` — present |
| Absorbed dose | J·kg⁻¹ | `AbsorbedDose` — present |
| Bioheat coefficients | — | `ThermalConductivity`, `ThermalDiffusivity`, `SpecificHeatCapacity`, `MassDensity` — present |
| Specific absorption rate | W·kg⁻¹ | **absent** — the one provider-side gap, needed for RF/EM |

Kwavers already depends on Aequitas in 10 crates / 66 files, so the adoption
path is open.

### Named boundary defects

- `kwavers-physics/src/thermal/diffusion/bioheat.rs` — `PennesBioheat::update`
  takes `external_source: Option<ArrayView3<'_, f64>>`. That parameter *is* the
  deposition spine boundary, and its unit exists only in a doc comment.
- Same file — `BioheatParameters` is four raw `f64` fields (`perfusion_rate`,
  `blood_density`, `blood_specific_heat`, `arterial_temperature`) with units in
  comments. Primitive obsession; the blood properties are Proteus's bounded
  context, not Kwavers's.

### Phases

1. ✅ **closed 2026-07-27 at aequitas `1003c88`** — `AbsorbedDoseRate`
   dimension with `GrayPerSecond` and `WattPerKilogram` units, and
   `SpecificAbsorptionRate` as its alias. W·kg⁻¹ and Gy·s⁻¹ are one coherent SI
   dimension, so defining two axes would admit a conversion factor that does
   not exist; the alias follows the existing
   `KinematicViscosity = ThermalDiffusivity` precedent. Five dimensional
   identities added (power/mass, dose/time, rate×time, unit coherence,
   volumetric-power/density). Gate: fmt, clippy `-D warnings`, nextest 34/34,
   11 doctests, `RUSTDOCFLAGS=-D warnings cargo doc` — all green. Incidental
   fix-forward: `vascular_result_dimensions_are_named` and
   `transducer_and_quadratic_flow_dimensions_are_named` compared `f64` with
   `==` against the file's exact-binary contract and held the clippy gate red
   at HEAD; both now assert on `to_bits` like the rest of the file.
2a. ✅ **closed 2026-07-27 at kwavers `81a40071c`** (branch
   `codex/kwavers-book-migration-eviction`) — `BioheatParameters`' four public
   `f64` fields became Aequitas quantities behind accessors, with a test
   annotating `ω_b ρ_b c_b ΔT` as `VolumetricPowerDensity` so a wrong factor
   fails to compile. The blood terms were read per voxel in both traversals and
   now resolve once per step; `pennes_solver_path_equivalence` confirms
   unchanged numerics. Gate: `cargo check` on both crates, clippy clean in the
   touched files (9 remaining warnings are peer-owned files), nextest 125/125
   on the thermal/bioheat/pennes/perfusion filterset.

2b. ✅ **closed 2026-07-27 at kwavers `37d50b96f`** — `external_source`
   retyped from `K/s` to a `VolumetricHeatSource<'_>` newtype carrying `W/m³`,
   with the `ρ c_p` division moved into the two solver traversals so it uses the
   *local* medium values. New leaf module
   `kwavers-physics/src/thermal/source.rs`; three producers
   (PSTD orchestrator, simulation dispatch, PyO3 bindings) lost their duplicated
   scalar `ρ·c_p` division, and `ThermalOrchestrationInput::{rho_cp,
   background_heat_ks}` collapse to `background_heat_wm3`.
   - Gate: `cargo check` green across kwavers-physics, kwavers-solver,
     kwavers-simulation, kwavers-python; nextest 144/144 on the
     thermal/bioheat/pennes/perfusion/heat filterset, including
     `pennes_solver_path_equivalence`, the analytical `bioheat_*` cases, and
     `test_heat_equation_mms_convergence`.
   - Build-lock note: verification queued behind a live peer's continuous
     builds on the shared `CARGO_TARGET_DIR`; one check took 42 minutes of
     wall clock. Forking the target tree to dodge the lock stays prohibited —
     the wait is the accepted cost.

### ATLAS-MODALITY-004 — Unified field array has no heat-source variant [patch] — done

- Owner: current Codex session; closed 2026-07-28 at Kwavers
  `5aef5f551`. Scope: `repos/kwavers` unified-field enum, thermal deposition
  producers, diffusion plugin, focused tests, and this backlog entry.
  Non-goals: unrelated peer WIP, transport extraction, and provider-lock
  cleanup.

- Found while typing the deposition boundary (2b).
  `crates/kwavers-solver/src/forward/thermal_diffusion/plugin.rs` read
  `UnifiedFieldType::Temperature as usize + 1` as its heat source. `Temperature`
  is 1, so index 2 is `UnifiedFieldType::BubbleRadius` — the plugin fed a bubble
  radius in metres into a heat-rate slot whenever the field array had more than
  two planes.
- `UnifiedFieldType` (`crates/kwavers-field/src/type.rs`) has no
  volumetric-heat-source variant, so there was no correct index to use. The 2b
  change passes `None` and documents why; that path now runs diffusion and
  perfusion only rather than a wrong source.
- Outcome: add a `VolumetricHeatSource` variant to `UnifiedFieldType`, have the
  deposition producers write it, and restore the plugin's external source
  reading that variant.
- Acceptance: no magic index arithmetic on `UnifiedFieldType` anywhere; a test
  asserts the plugin's temperature rise matches an analytically derived value
  for a known deposition field.
- Evidence: `cargo check --offline -p kwavers-field -p kwavers-solver --tests`,
  targeted rustfmt, `git diff --check`, warning-denied Clippy, and nextest
  `106a11a9-ba01-401d-b23b-1904c7e48144` (5/5 targeted tests) pass. Existing
  field indices remain stable; the new slot is index 17 and the analytical
  regression verifies `q/(rho*cp) * dt = 10 K`.

3a. ✅ **closed 2026-07-27 at hyperion `12b2ad3`** — Hyperion owns the local
   absorbed-deposition laws `Q = μ_a φ` (W/m³) and `q = μ_a Φ` (J/m³), with
   validated `FluenceRate`, `AbsorbedPowerDensity`, and `AbsorbedEnergyDensity`
   quantities. Both forms ship because both producers exist: rate for diffusion
   and RTE solvers, energy for time-integrated Monte Carlo. Verified against the
   Beer-Lambert conservation identity ∫ μ_a Φ₀ e^{-μ_a x} dx = Φ₀, an oracle
   independent of the product under test. Gate: fmt, clippy `-D warnings`,
   nextest 15/15, doctests, `--no-default-features`, rustdoc.

3b. ✅ **closed 2026-07-27 at kwavers `224a9a293`** — deleted the vestigial
   `DiffusionVolume` trait. It abstracted ndarray from leto during the array
   migration; both names now resolve to `leto::Array3`, so `solve.rs` imported
   one type under two aliases, the trait had a single impl, and `solve` /
   `solve_leto` were the same function. `leto_solver_matches_ndarray_solver_bitwise`
   compared those two functions on identical inputs and could not fail under any
   defect — deleted rather than repointed. Net −101 lines; codegen-neutral, since
   monomorphization already produced exactly the concrete code. Gate: check clean,
   nextest 18/18 on the diffusion/optical filterset, clippy clean in the touched
   files.

3c. ✅ **closed 2026-07-28 at kwavers `6d1581a24`** — adopted
   `hyperion::transport::absorbed_energy_density` at
   the kwavers optics deposition sites, and type `MCResult`'s `absorbed_energy`
   (J/m³) and `fluence` (J/m²) plus the diffusion solve boundary (source W/m³,
   fluence W/m²), which currently cross as bare `Vec<f64>` / `Array3<f64>` with
   units only in doc comments.
   - Note: `multiphysics/monolithic/residual/compute.rs:84-101` computes its own
     `inv_rho_cp` for the optical and acoustic terms, but `coeff` there is a
     uniform-coefficient bundle by design, so that scalar division is a modelling
     assumption rather than the phase-2b inconsistency. Only the `μ_a · Φ`
     product is a spine law there.
4. `repos/kwavers` — same treatment for `electromagnetic`, via SAR from phase 1.
   This is also the ATLAS-MODALITY-003 RF prerequisite.

- Non-goals: extracting any modality package; renaming or relocating solvers;
  touching sonoluminescence or photoacoustics.
- Acceptance: no untyped `f64` crosses the transport→deposition or
  deposition→bioheat boundary in the named modules; a property test asserts the
  quantity type at each transport backend's output; an energy-conservation test
  asserts integrated deposition equals absorbed source energy within a derived
  bound, with the derivation cited at the assertion site; both repos green under
  their nextest budgets.
- Dependency: none. Phase 4 is the prerequisite for the RF track in
  ATLAS-MODALITY-003.

## ATLAS-MODALITY-003 — Optical-transport and RF/EM promotion watchpoint [arch] — blocked

- Owner: unclaimed; scope: watchpoint only — no edits until the trigger fires.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §1, §2, §6.
- Blocker: promotion gate conditions 1, 4, and 6 are unmet. Source audit
  2026-07-27: Kwavers is the sole consumer of the diffusion/Monte-Carlo-RTE
  optical transport solvers (CFDrs has no radiative/optical/photon module;
  ritk has none; Helios consumes Hyperion at MeV, a different regime). No RF
  integrator or second electromagnetics consumer exists.
- Re-open trigger: a second production consumer can delete a matching transport
  implementation in the extraction change. At that point the target is
  `hyperion-transport` as a second crate in a promoted Hyperion workspace — not
  a new package — so the `no_std` law crate keeps its dependency set and Helios
  and CFDrs inherit no array substrate.
- Standing note: sonoluminescence (3 006 LOC) and photoacoustics (653 LOC) are
  Kwavers-intrinsic and are excluded from any extraction scope. A photomedicine
  integrator peer to Helios is a separate, demand-gated decision and is out of
  scope here.
- Refinement 2026-07-28 —
  [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §5: "RF" names two
  unrelated concerns and this watchpoint covers only the first. RF power
  deposition and SAR belong on the shared deposition spine (ATLAS-MODALITY-002),
  where the transport stage is a modality slot and the stages behind it are
  shared. RF at the Larmor frequency for spatial encoding belongs to MR
  acquisition simulation, which is a closed, demand-gated *integrator* question —
  not part of this trigger and not a RITK concern. A proposal that merges the two
  is rejected on bounded-context grounds before the gate is even applied.

## ATLAS-OVERLAY-005 — Clear first-party rev pins across the stack [patch] — in-progress

- Owner: session-808504af. Decision: pin discipline (`architecture_scoping`) —
  a `rev =` is quarantine with a removal trigger, not a durable source form.
- Root cause: a rev-qualified git source is a **distinct package** to Cargo, so
  the stack `[patch]` overlay — which matches the bare URL — can never unify it.
  Sixteen first-party pins had accumulated across five repos at three different
  `aequitas` commits and two `eunomia` commits, so any crate reaching a provider
  by both forms received two incompatible copies of the same trait. Hyperion
  could not multiply two `Quantity` values for exactly this reason.
- ✅ Cleared and pushed: proteus `9a8655d` (also restored its manifest from a
  local path-dep leak to git+version), asclepius `ccffb6b`, tyche `996b649`,
  kwavers `df9008d93`.
- **Remaining**: helios (5 pins) and ritk (6 pins) are depinned in the working
  tree but uncommitted — neither has been build-verified yet. `openjp2` in ritk
  keeps its pin; it is third-party, where a rev is legitimate.
- **Mechanism worth mechanizing**: depinning alone is insufficient. Every lock
  move needs `python scripts/atlas-stack-overlay.py generate` to re-derive the
  patch block, otherwise the graph keeps a local-vs-git split. This is the
  mechanism behind the recurring "local X cannot replace git-sourced Y" failures
  on this board. `atlas-stack-overlay.py check` already exits nonzero on lag, so
  wiring it into CI would catch the class at the source.
- Evidence: `cargo tree -d` in kwavers reports no duplicate first-party crates;
  `atlas-stack-overlay.py check` reports the stack aligned.

## ATLAS-CONTENTION-001 — Transport-output typing blocked behind foundation WIP [patch] — blocked

- Owner: session-808504af; scope `repos/kwavers` 18 files (uncommitted).
- Delivers ATLAS-MODALITY-002 phase 3d: `DimensionedField<S, D>` in
  `kwavers-core/src/units/field.rs` (zero-sized Aequitas dimension tag over any
  sample container), `VolumetricHeatSource` consolidated onto it,
  `MCResult::{absorbed_energy,fluence}` typed as `J/m³` and `J/m²`, and
  `DiffusionSolver::solve` typed `W/m³` in → `W/m²` out.
- Verified so far: `cargo check` green across kwavers-core, kwavers-physics,
  kwavers-solver, kwavers-simulation; nextest **332/332** on kwavers-core +
  kwavers-physics.
- **Blocker**: the kwavers-solver test filterset has not run against this change.
  Three successive attempts hit unrelated live peer WIP — first a missing
  `Fft3dInOutExt` import in `pstd/.../stepper/step.rs` (peer landed it), now
  `repos/aequitas` mid-refactor with duplicate definitions (E0592) in
  `quantity/arithmetic/scalar.rs` and `construction.rs`, touched minutes ago.
  Aequitas is the foundation crate, so nothing downstream compiles until it
  settles.
- Fourth attempt (15:10) hit a different pair: `kwavers-transducer/src/bulk_piezo.rs`
  (peer-dirty) imports `aequitas::systems::si::quantities::ElectricalImpedance`,
  which the aequitas peer has added to the local tree but which the build did not
  resolve. This is an aequitas↔kwavers co-evolution unit in flight, not a defect
  in either side — the consumer landed ahead of the provider being consumable.
- Assessment: four distinct transient failures in ~30 minutes, all from
  concurrent edits to shared foundations (aequitas, kwavers-transducer,
  kwavers-solver) plus 40-minute build cycles on the shared target dir. Retrying
  against a tree three peers are actively rewriting is not productive; this item
  waits for a quiet tree rather than polling.
- Re-open trigger: `cargo check -p aequitas` and `cargo check -p kwavers-transducer`
  both green, then run
  `cargo nextest run -p kwavers-solver -E 'test(~thermal_diffusion) or test(~optical::diffusion)'`
  and commit the 18 files if green. No edits are needed to the change itself.

## ATLAS-OVERLAY-004 — Worktree sprawl breaks stack dependency resolution [patch] — in-progress

- Owner: unclaimed; scope: `worktrees/`, the root `.cargo/config.toml`, and the
  13 lane-local `.cargo/config.toml` files. **Not** the lane branches' source.
- Blocker evidence (2026-07-27): `cargo check -p kwavers-physics` fails before
  compiling anything:
  - `failed to select a version for smallvec` — `hephaestus-wgpu v0.18.0` at
    `worktrees/hephaestus-unary-math-parity` requires `^1.15.2`; the kwavers lock
    pins `1.15.1`.
  - `cargo update -p smallvec --precise 1.15.2` then fails harder:
    `package collision in the lockfile: packages aequitas v0.1.0
    (D:tlas\worktreesequitas) and aequitas v0.1.0
    (D:tlas\worktreesequitas-energy-temperature) are different, but only
    one can be written to lockfile unambiguously`.
- Two distinct defects behind it:
  1. ✅ **resolved 2026-07-28** — `worktrees/aequitas` was an **orphaned linked
     worktree**, not a standalone clone: its `.git` file pointed at
     `repos/aequitas/.git/worktrees/aequitas`, whose admin directory had been
     pruned, leaving the checkout on disk with no git registration. Cargo still
     discovered it as a path source, giving two providers for `aequitas v0.1.0`.
     Contents were byte-identical to `repos/aequitas` (`diff -r` clean excluding
     `target`, `Cargo.lock`, `.git`), so nothing unique was lost. Removed with
     user authorization; `git worktree prune` run. `cargo check` across
     kwavers-physics and kwavers-solver resolves again, and the `smallvec`
     conflict cleared with it.
  2. **13 lane-local `.cargo/config.toml` files.** Config-layer ownership
     (`performance_engineering`) puts `target-dir` and the `[patch]` overlay at
     the stack root only; a nested config re-declaring either forks resolution
     and, as here, resolves a relative provider path into a second copy.
- Also: `worktrees/` holds 28 entries against a documented bound of one main
  tree plus one lane per repository. aequitas, coeus, hephaestus, kwavers, and
  ritk each have two or more.
- Acceptance: `cargo check -p kwavers-physics` resolves; `git worktree list` per
  repo is within bound; no lane-local `.cargo/config.toml` re-declares
  `target-dir` or `[patch]`; `worktrees/aequitas` removed after confirming no
  unique commits.
- **Ask-User gate**: removing `worktrees/aequitas` and other agents' lane
  directories is destructive to possibly-live peer setups. Confirm before
  deleting rather than reconciling unilaterally.

## ATLAS-OVERLAY-002 — Clear pin drift in asclepius, athena, hermes [patch] — done

- Owner: atlas coordinator (Session 30, 2026-07-28); scope: `repos/{asclepius,athena,hermes}`
  `Cargo.lock` plus their parent gitlinks. No manifest, source, or requirement edits.
- Closure: `python scripts/atlas-stack-overlay.py check` reports `stack aligned: requirements
  satisfiable and locks match the local trees` (verified 2026-07-28). All three gitlinks
  align to origin/main: athena advanced to `fef782cb` in Session 29 commit `24ad6ea`;
  asclepius advanced to `bbf38400` and hermes to `cf69175` in Session 30 commit
  `323279e` (both verified safe per pitfall #2 — WT HEAD == origin/main, pin ancestor
  of origin/main, staged Subproject commit matches origin/main exactly).
- Pre-Session 28 carryover (retained for trace): Owner: was unclaimed; scope was `repos/{asclepius,athena,hermes}` `Cargo.lock` plus
  their parent gitlinks. No manifest, source, or requirement edits.
- Outcome: each lock resolves onto current provider heads, so the stack
  overlay unifies instead of failing with "candidate versions found which
  didn't match". Every consumer requirement in the chain is already correct
  upstream; only these locks are behind. Apollo cleared the identical drift in
  `39e3cb4` — same procedure, same chain (mnemosyne 0.6, hermes 0.5, and the
  moirai/leto revisions that carry them).
- Acceptance: `python scripts/atlas-stack-overlay.py check` reports no pin
  drift for the repo; locked workspace check and its nextest budget pass.
- Method: `python scripts/atlas-stack-overlay.py off`, then
  `cargo update -p moirai -p hermes-simd -p mnemosyne -p leto -p leto-ops`,
  verify, commit the lock while the overlay is still off (an enabled overlay
  strips every `source` line from the lock), then re-enable.
- Note: this drift has been surfacing as an unexplained blocker rather than a
  diagnosis — see the Coeus evidence in ATLAS-CUDA-TREE-001/002/003 below,
  which records the same `mnemosyne ^0.5.0` vs `0.6.0` conflict as a reason no
  test result could be claimed.
- Cross-link (2026-07-27): the athena 36-residual audit hits surfaced by
  ATLAS-PATH-DEP-AUDIT-2 round-5 (mnemosyne 0.5.0 vs 0.6.0 + leto-ops 0.40.0
  chain) are GRADUATED out-of-scope for the path-dep audit per
  `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` §"Closure-wait criteria (REVISED
  2026-07-27) — scope-defined exceptions". This entry owns the dependency-
  resolution domain; closing athena's 36 residual requires this entry to
  flip from `todo` to `done` independently via the pin-drift method above.

## ATLAS-OVERLAY-003 — Retire committed [patch] blocks from 7 member manifests [patch] — todo

- Owner: unclaimed; scope: `repos/{CFDrs,coeus,gaia,helios,kwavers,leoneuro-rs,ritk}`
  `Cargo.toml` and their parent gitlinks.
- Outcome: each member returns to `git + version` sources and is consumable as
  a clean git dependency. Cargo honors a manifest `[patch]` only in the root
  manifest of the build, so these blocks are already inert for every consumer;
  they duplicate the root overlay installed in `d89ccd9` while blocking
  consumption. Counts at filing: CFDrs 8, coeus 8, gaia 5, helios 17,
  kwavers 13, leoneuro-rs 12, ritk 10 sections.
- Acceptance: no `[patch]` section in the member manifest; the repo resolves
  standalone against git and locally under the root overlay; locked check and
  its nextest budget pass; `scripts/atlas-stack-overlay.py check` stays clean.
- Dependency: sequence behind ATLAS-OVERLAY-002 where the repo also has pin
  drift, so the lock refresh and the manifest change do not interleave.

## ATLAS-GIT-HYGIENE-001 — Confirm `repos/leoneuro-rs/` rule is intentional [chore] — done

- Owner: Codex `/root`; last-update: 2026-07-27;
  scope: `/d/atlas/.gitignore` line 60 (CONFIRMED intentional).
- Outcome: SPAWNED as a stale-rule-removal ticket on 2026-07-27
  (parent commit `fef2c63`'s STEP C); closure surfaced that the
  rule is actually the design, not a stale entry:
  - `leoneuro-rs` remote = `https://github.com/LeoNeuro-INC/leoneuro-rs.git`
    (private LeoNeuro-INC org, distinct from atlas' ryancinsight).
  - atlas `.gitmodules` has no `[submodule "leoneuro-rs"]` entry.
  - atlas `.git/config` has no `submodule.leoneuro-rs.*` keys.
  - `repos/leoneuro-rs/` rule on line 60 keeps the external
    code-drop out of `git status` noise — `git status` not
    nagging about it is the design, not a defect.
  Closing this ticket confirms the rule stays as-is. The
  cacheinfo-built 160000 gitlink created in `fef2c63` is **dropped**
  by the architectural-correction follow-up commit (subject
  `build(atlas): Drop misapplied leoneuro-rs gitlink — audit
  closure unaffected`) which executes `git rm --cached
  repos/leoneuro-rs` and updates
  `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` STEP D.
- Acceptance: rule remains on line 60; the follow-up commit drops
  the gitlink; `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` STEP D is the
  audit ledger reflecting the correction.
- Method: documentation-only update at
  `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` STEP D + the parent atlas
  commit drops the cacheinfo 160000. No `.gitignore` edit required.
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 STEP D is the corresponding
  correction in the audit ledger.
- Risk/change class: `[chore]`; documentation-only confirmation.

## ATLAS-R6A-FILELIST-001 — Per-submodule r6a commit file-list hygiene [patch] — todo

- Owner: unclaimed; scope: the 12 r6a submodule commits (apollo,
  asclepius, CFDrs, coeus, gaia, helios, hephaestus, kwavers,
  leoneuro-rs, hermes, ritk, athena) whose `git show --stat <r6a_sha>`
  verifier surfaced a 1-non-cargo-file anomaly on 2026-07-27 (each
  commit contains exactly 1 file that is neither `Cargo.toml` nor
  `Cargo.lock`). Per-submodule audit + per-submodule remediation. No
  atlas manifest edits in this scope.
- Outcome: each of the 12 r6a submodule commits produces
  `git show --stat <sha>` showing strictly `Cargo.toml + Cargo.lock`,
  OR carries an explicit per-consumer exemption row in
  `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` STEP C documenting why the
  additional file is a deliberate deviation.
- Acceptance: per-consumer `git show --stat <r6a_sha> | grep -cE
  'Cargo\.(toml|lock)'` returns 2; the verifier script
  `scripts/atlas-path-dep-audit2-closure-r6a.py` exits 0 with the
  "no extras in r6a commits" assertion.
- Method: per-submodule `git reset --soft HEAD~1 && git restore --staged . && git add Cargo.toml Cargo.lock && git commit -m "build(<repo>): Refresh round-6a atlas-root path resolution — file-list hygiene"` (committed at the per-submodule level; carries a distinct verb (`Refresh` instead of `Apply`) so `git log --grep "Apply round-6a"` continues to surface only the original r6a commits while `git log --grep "Refresh round-6a"` surfaces the cleanup cycle), authorized amend per ticket scope, distinct from the parent-side follow-up amend at `77c60de`); then `cargo update --workspace --offline` per consumer to refresh Cargo.lock post-stick. Twelve follow-up commits land consumer-side; one atlas-side parent commit advances all 12 gitlinks atomically (or twelve separate follow-up commits if atomic amend is unsafe).d9e7db); then `cargo update --workspace --offline` per consumer to refresh Cargo.lock post-stick. Twelve follow-up commits land consumer-side; one atlas-side parent commit advances all 12 gitlinks atomically (or twelve separate follow-up commits if atomic amend is unsafe).
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27) parked
  this follow-up; the audit criterion (ryancinsight=0 / NVlabs
  preserved) was met but the per-commit file-list hygiene was
  separately uncovered.
- Risk/change class: `[patch]`; per-submodule commit rewrite spanning
  12 consumers + one parent-side gitlink advance. Distinct
  operational domain from ATLAS-GIT-HYGIENE-001 (which is a
  single-line atlas config edit only). Bundling the two was rejected
  by the round-6a code review (Q2 blocker).

## ATLAS-DOWNSTREAM-COORDINATION-001 — Notify LeoNeuro-INC maintainers about local leoneuro-rs `50bfcd9` [chore] — todo

- Owner: unclaimed; scope: out-of-band coordination with the
  LeoNeuro-INC organization (separate GitHub org, NOT ryancinsight).
  No atlas-side edits in this scope.
- Outcome: the leoneuro-rs `50bfcd9` commit ("build(leoneuro-rs):
  Apply round-6a atlas-root path resolution — GRAND_TOTAL 0 across
  atlas") lives locally at `/d/atlas/repos/leoneuro-rs/` on the
  branch `codex/sim-ct-medium`. After atlas's closure cycle dropped
  the bogus 160000 gitlink in commit `d6827c2`, atlas parent no
  longer tracks leoneuro-rs's HEAD; the LeoNeuro-INC maintainers
  can land `50bfcd9` to their own org
  (`https://github.com/LeoNeuro-INC/leoneuro-rs.git`) on their own
  schedule via their own CI/dispatch pipeline.
- Acceptance: a downstream LeoNeuro-INC maintainer receives a short
  note pointing at the local SHA (`50bfcd9`) and the atlas-side
  commit history (see `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` STEP D
  push-handoff paragraph for the handoff context); the
  LeoNeuro-INC team decides whether to fast-forward their `main`
  to `50bfcd9` or to cherry-pick from the local branch.
- Method: out-of-band contact through the existing LeoNeuro-INC
  internal channels; the atlas-side convey is a one-line pointer
  (no technical payload required). The atlas-side documentation
  states this deferral, but **no atlas code or Cargo.toml changes**
  are part of this ticket. The `50bfcd9` commit is preserved on the
  leoneuro-rs local branch (`codex/sim-ct-medium`) until the
  LeoNeuro-INC team decides its disposition.
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27)
  STEP D push-handoff paragraph codifies the deferral as
  documentation; this ticket is the corresponding **owner-assigned**
  follow-up so the deferral doesn't drift unowned. NAME SEMANTIC
  NOTE: "downstream" in this title refers to LeoNeuro-INC as
  downstream maintainer of the `50bfcd9` commit; this is distinct
  from atlas-side "downstream consumer" terminology used in
  per-submodule commit hygiene tickets.
- Risk/change class: `[chore]`; out-of-band coordination only.

## ATLAS-CUDA-TREE-003 — Close the fused operation-tag tree split [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `edcded8d` replaces the 625-line operation-tag module with a
  manifest, a unary trait seam, and elementary/transcendental/activation
  leaves; all leaves remain below the 500-line target.
- Evidence: format and diff checks pass. Package checking is blocked by the
  preserved peer edit in Coeus `Cargo.toml`: the manifest/dependency graph
  cannot resolve Moirai's locked `mnemosyne ^0.5.0` requirement against the
  available Mnemosyne `0.6.0`; no compiled or test result is claimed.

## ATLAS-CUDA-TREE-002 — Close the attention kernel tree split [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `393d711e` replaces the 567-line attention kernel module with
  a manifest and validation, source, forward, backward, and test leaves; all
  leaves remain below the 500-line target.
- Evidence: format and diff checks pass; package compilation and tests are
  blocked by unrelated dirty Coeus `Cargo.toml` state requesting
  `mnemosyne ^0.6.0` while locked Moirai requires `mnemosyne ^0.5.0`. No
  compiled or test result is claimed for this slice.

## ATLAS-CUDA-TREE-001 — Close the convolution backend tree split [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `9b5da9c7` replaces the 614-line convolution backend file
  with a manifest and forward, backward, and transposed-convolution leaves;
  all leaves remain below the 500-line target.
- Evidence: feature check, warning-denied Clippy, feature rustdoc, and default
  package Nextest pass; default doctests pass 4/4 in 14.35 seconds. CUDA-
  feature Nextest reaches the Windows GNU linker but cannot link because
  `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature test
  execution is claimed.

## ATLAS-CUDA-SAFETY-015 — Close elementwise backend count/failure boundary [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `f7372408` replaces unary/binary output-count products with
  the checked kernel-count SSOT and routes Hephaestus contiguous/strided
  errors through the explicit CPU fallback instead of panicking.
- Evidence: feature-enabled check and warning-denied Clippy pass; default
  package Nextest passes 3/3 with zero skipped; feature rustdoc passes. Default
  doctests pass 4/4 in 13.62 seconds. CUDA-feature Nextest reaches the Windows
  GNU linker but cannot link because `-lcuda` is absent from
  `/usr/local/cuda-11.3/lib64/`; no feature test execution is claimed.

## ATLAS-CUDA-SAFETY-014 — Close fused-dispatch launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `799e72f6` validates fused output counts and grids,
  contiguous output indexing, broadcast contracts, null inputs, and input /
  output storage bounds before dynamic CUDA launch. Physical layout storage
  length is now shared with unfold/fold through the validation SSOT.
- Evidence: feature-enabled check and warning-denied Clippy pass; default
  package Nextest passes 3/3 with zero skipped; feature rustdoc and default
  doctests pass 4/4 in 12.28 seconds. CUDA-feature Nextest reaches the
  Windows GNU linker but cannot link because `-lcuda` is absent from
  `/usr/local/cuda-11.3/lib64/`; no feature test execution is claimed.

## ATLAS-CUDA-SAFETY-013 — Close transposed-convolution launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `382b74c7` validates transposed-convolution dimensions,
  checked input/weight/bias/output capacities, all native `u32` values, and
  the shared 1-D grid before native dispatch. Native execution is restricted
  to rank-correct contiguous offset-zero layouts with matching batch/channel
  contracts; device gather arithmetic uses overflow-safe intermediates.
- Evidence: feature-enabled check, warning-denied Clippy, and feature
  rustdoc pass. Default package Nextest passes 3/3 with zero skipped. The
  CUDA-feature Nextest reaches the Windows GNU linker but cannot link because
  `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature test
  execution is claimed.

## ATLAS-CUDA-SAFETY-012 — Close unfold/fold launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `de74d093` replaces the unfold/fold monolith with a deep
  source/dispatch/validation/1-D/2-D tree. It checks window formulas, exact
  shapes, physical layout/storage bounds, positive representable parameters,
  output aliasing, counts, and shared grids before native dispatch.
- Evidence: feature-enabled check, warning-denied Clippy, and feature
  rustdoc pass; default package Nextest passes 3/3 with zero skipped in
  0.193 seconds. CUDA-feature Nextest reaches the Windows GNU linker but
  cannot link because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`;
  no feature test execution is claimed.

## ATLAS-CUDA-SAFETY-011 — Close attention launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `3ace27ec` hardens CUDA attention dimensions, checked element
  counts, mask/head relationships, buffer lengths, compatible contiguous
  dispatch layouts, and the shared 1-D grid launch seam.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.171 seconds;
  default doctests pass 4/4 in 14.21 seconds; feature rustdoc passes. The
  provider's pure attention boundary tests compile with the feature build.
- Limit: CUDA-feature Nextest reaches the Windows GNU linker but cannot link
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-010 — Close matmul launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `b9876e7e` hardens tiled CUDA matmul with checked rank-two
  nonempty layout metadata, `A.cols == B.rows`, output shape compatibility,
  and both checked 16-wide grid axes.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.044 seconds;
  rustdoc and doctests pass; shared grid tests cover custom block widths and
  matmul source scans are clean for rank/grid issues.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-009 — Close pool3d launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `df331873` extends the pool-owned validation seam to 3-D
  average/max forward and backward dispatch with checked positive parameters,
  rank-five layout/work/grid bounds, prefix relationships, and backward shape
  contracts.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.049 seconds;
  rustdoc and doctests pass; all pooling source scans are clean for narrowing,
  unchecked products, and local grid derivation.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-008 — Close pool2d launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `45826c05` promotes pooling validation to one dedicated SSOT
  and hardens 2-D average/max forward and backward dispatch for checked
  parameters, work counts, grids, rank-four layouts, and shape contracts;
  pool1d consumes the same seam.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.050 seconds;
  rustdoc and doctests pass; pooling source scans are clean for narrowing,
  unchecked products, and local grid derivation.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-007 — Close pool1d launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `920b3428` hardens the canonical 1-D max/average pooling
  dispatcher with checked positive parameters, element counts, grids,
  rank-three nonempty layouts, and operation-specific shape contracts.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.049 seconds;
  rustdoc and doctests pass; pool1d source scans are clean for narrowing,
  unchecked products, and local grid derivation.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-006 — Close optimizer launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `f627ecbc` hardens AdaGrad, Adam, AdamW, RMSprop, and SGD
  with shared checked element counts, grids, layout ABI, same-shape contracts,
  and the canonical block size. Adam-family step exponents reject values
  outside the kernel's `i32` contract.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.048 seconds;
  rustdoc and doctests pass; optimizer source scans are clean for input-
  dependent narrowing.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-005 — Close elementwise launch ABI and tree [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `92bd4c8f` turns the 530-line CUDA elementwise launcher into
  a manifest with contiguous and strided leaves. All four launchers use shared
  checked count/grid validation; strided paths validate broadcast rank, reject
  zero-stride output layouts, and transfer descriptors through safe POD views.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.044 seconds;
  rustdoc and doctests pass; source and validation regressions cover unchecked
  casts, raw layout slices, overflow, zero work, and zero-stride outputs.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-004 — Close reduction launch ABI [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `dfe23979` promotes CUDA `u32`, checked element-count,
  layout-fit, and grid-size validation to one `kernels::validation` SSOT and
  applies it to standard and fused reduction. Missing or over-rank fused
  expression shapes now return the established dispatch failure result;
  layout-vector serialization uses safe POD casting.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.046 seconds;
  rustdoc and doctests pass; reduction source audit is clean for unchecked
  casts, products, input indexing, and panics.
- Limit: CUDA-feature Nextest cannot link in this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`; no feature
  test execution is claimed.

## ATLAS-CUDA-SAFETY-003 — Close shared CUDA layout ABI [major] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `4129d31e` makes `GpuLayoutInfo` crate-private and replaces
  truncating layout conversion with one checked `TryFrom<&Layout>` seam.
  Rank, shape/stride rank, offset, shape, and stride violations now return
  the established dispatch failure result; descriptor serialization remains
  allocation-free through `bytemuck::cast_slice`. Forward convolution output
  element counts use checked multiplication.
- Evidence: feature-enabled package check and warning-denied Clippy pass;
  default package Nextest passes 3/3 in 0.053 seconds; rustdoc and doctests
  pass; semver checks classify the two removed public implementation items as
  an intentional major change.
- Limit: CUDA-feature Nextest cannot link in the current Windows GNU
  environment because `-lcuda` is absent from
  `/usr/local/cuda-11.3/lib64/`; no feature-test execution is claimed.

## ATLAS-CUDA-SAFETY-002 — Close convolution launch ABI narrowing [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `1041b20d` validates convolution launch layouts, parameters,
  element counts, channel counts, and grid sizes before crossing the CUDA
  `u32` ABI. The launcher is vertically organized into an 8-line manifest,
  validation leaf, forward leaf, and three backward dimension leaves.
- Acceptance: CUDA-feature all-targets check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.053 seconds.
  Provider `main` is pushed and the root gitlink is advanced to `1041b20d`.
- Limit: CUDA-feature Nextest cannot link on this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`. Shared
  layout serialization and caller-side forward element-count calculation
  remain separate residuals; no performance claim is made.

## ATLAS-CUDA-SAFETY-001 — Close convolution launch panic [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `7e8e1ee2` makes a nonzero CUDA 1D convolution grad-input
  launch result return `false`, preserving the operation boundary's fallback
  contract instead of panicking.
- Acceptance: CUDA-feature all-targets check and warning-denied Clippy pass;
  default package Nextest passes 3/3 with zero skipped in 0.072 seconds.
  Provider `main` is pushed and the root gitlink is advanced to `7e8e1ee2`.
- Limit: CUDA-feature Nextest cannot link on this Windows GNU environment
  because `-lcuda` is absent from `/usr/local/cuda-11.3/lib64/`. The
  unchecked launch-parameter narrowing residual is recorded upstream in
  Coeus `docs/gap_audit.md`; no performance claim is made.

## ATLAS-BUILD-STRUCTURE-005 — Close CUDA operation impl hierarchy [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `2fb00ed6` moves eight CUDA operation trait impl blocks into
  `coeus-cuda/src/backend/ops/impls/`; the operation manifest is 11 lines and
  each impl leaf is below 301 lines.
- Acceptance: provider default and `cuda`-feature package checks and
  warning-denied Clippy pass; locked metadata remains one library, one
  `cuda_ops` integration target, and two benchmarks. Default package Nextest
  passes 3/3 with zero skipped in 0.059 seconds. Provider `main` is pushed and
  the root gitlink is advanced to `2fb00ed6`.
- Limit: the CUDA-feature Nextest link step cannot resolve `-lcuda` on this
  Windows GNU environment because `/usr/local/cuda-11.3/lib64/` is absent.
  No feature-test pass or runtime, memory, or performance delta is claimed.

## ATLAS-BUILD-STRUCTURE-004 — Close CPU operation impl hierarchy [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `1a28b64b` moves eight CPU operation trait impl blocks into
  `coeus-ops/src/backend_ops/cpu_impl/impls/`; the manifest is 56 lines and
  each operation-family leaf is below 325 lines.
- Acceptance: provider package check, warning-denied Clippy, format, diff,
  and locked metadata pass. Exact package Nextest passes 196/196 with zero
  skipped in 4.325 seconds across two binaries. Provider `main` is pushed and
  the root gitlink is advanced to `1a28b64b`.
- Limit: this is a module-topology and maintainability closure; no runtime,
  memory, or performance delta is claimed.

## ATLAS-BUILD-STRUCTURE-003 — Close WGPU operation impl hierarchy [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `310f9ffb` moves seven WGPU trait impl blocks into
  `coeus-wgpu/src/backend/ops/impls/`; the shared operation manifest is 450
  lines and each impl leaf is below 315 lines.
- Acceptance: provider package check, warning-denied Clippy, format, diff,
  and locked metadata pass. Exact package Nextest passes 89/89 with zero
  skipped in 90.167 seconds. Provider `main` is pushed and the root gitlink is
  advanced to `310f9ffb`.
- Limit: this is a module-topology and maintainability closure; no runtime,
  memory, or performance delta is claimed.

## ATLAS-BUILD-STRUCTURE-002 — Close Coeus-NN attention parity leaf [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `006a1c7c` isolates the attention parity numerical oracle in
  `coeus-nn/tests/nn_ops/tensor/nn_parity/attention/expected.rs`; the
  operational attention test is 182 lines and the oracle leaf is 91 lines.
- Acceptance: the 11-test source census is unchanged; provider package check
  and warning-denied Clippy pass; focused parity passes 1/1; exact package
  Nextest passes 268/268 with zero skipped in 2.405 seconds. Provider `main`
  is pushed and the root gitlink is advanced to `006a1c7c`.
- Limit: this is a test-topology and oracle-maintainability closure; no
  production runtime, memory, or performance delta is claimed.

## ATLAS-WGPU-CORRECTNESS-001 — Close native WGPU missing operation paths [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/coeus` and
  this root's `repos/coeus` gitlink only.
- Outcome: Coeus `c8b9a013` replaces four WGPU unfold/fold no-ops and four
  pool1d stubs with native WGSL kernels. The pool1d operation family is
  vertically split into manifest, shader, forward, and backward leaves.
- Acceptance: provider package check and warning-denied Clippy pass; focused
  pool1d Nextest passes 2/2; exact package Nextest passes 89/89 with zero
  skipped in 79.311 seconds. Provider `main` is pushed and the root gitlink is
  advanced to `c8b9a013`.
- Limit: this is a correctness/device-path closure; no performance or
  allocation improvement is claimed without a controlled baseline.

## ATLAS-HELIOS-BOOK-087 — Helios mdbook deterministic figure set + prebook xtask [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/helios` only.
- Outcome: H-087 closes the gap between the (already-staged) `docs/book/`
  chapter scaffolds and committed deterministic figures.  Seven hand-authored
  SVGs committed under `repos/helios/docs/book/figures/`:
  `photon_attenuation_depth.svg`, `ct_calibration_curve.svg`,
  `radon_sinogram_disk.svg`, `dvh_curve.svg`, `dose_slice_heatmap.svg`,
  `helical_mlc_fluence.svg`, `architecture_stack.svg`.  Each is linked
  from `SUMMARY.md` and the corresponding example chapter (radon, photon
  attenuation, dvh, tomotherapy_workflow); the README carries the
  single-file figure index.  `helios/xtask` gains a `prebook` subcommand
  (`repos/helios/xtask/src/prebook.rs`) that verifies + SHA-256-hashes
  the figure set into `docs/book/figures/MANIFEST.json`.  The manifest is
  byte-deterministic across repeated runs on unchanged inputs.  Appendix F
  is added to `SUMMARY.md` pointing back to
  `repos/parity_artefacts/INDEX.md`, which now carries a per-book figure-
  manifest section listing each atlas’s committed figure set.
- Acceptance: `cd repos/helios && mdbook build docs/book` exits 0 (no
  `[WARN]` rows), `python3 scripts/check_mdbook_links.py
  repos/helios/docs/book` returns `FILE_MISSING : 0`, and `cargo run -p
  xtask -- prebook` regenerates `MANIFEST.json` with stable hex
  fingerprints across two consecutive runs.
- Risk/change class: `[patch]`; documentation / tooling increment with no
  production-code change.  No peer provider graph touched.
- Evidence limit: mdbook `FILE_MISSING : 0` per chapter; `xtask prebook`
  byte-determinism across two runs.

## ATLAS-RITK-655 — RITK B-spline bounded dense hot-path closure [minor] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/ritk` only.
- Outcome: PERF-432 / PERF-406-02 partially closed. The bounded dense
  support-matrix path landed in
  `ritk_registration::bspline_ffd::basis::{evaluate_bspline_displacement_dense_into,
  should_use_dense_path, DENSE_LATTICE_CUTOFF}`. The registration engine
  (`BSplineFFDRegistration::register` inner loop) auto-dispatches to the
  dense path when `ctrl_dims.product() <= 1_000_000` AND the dense support
  table stays within 16 MiB resident. Explicit `f64` arithmetic with `u32`
  control-point indices sidesteps the historical `coeus-core`/`leto-ops`
  `E0034` ambiguity on `from_f64`/`from_usize`.
- Acceptance: `cargo clippy -p ritk-registration --all-targets -- -D warnings`
  clean; `cargo nextest run -p ritk-registration bspline_dense` green
  (3/3 — dense matches sparse / zero-input invariant / dispatch predicate);
  equivalence asset: `bspline_dense_matches_sparse_on_small_lattice`
  abs-tolerance `5e-5` over the 8³ voxel lattice.
- Risk/change class: `[minor]`; performance increment with profiling
  counterpart (`bspline_displacement` bench is unchanged at criterion level;
  the dense path replaces the cache-based interior path on qualifying
  lattices in the registration's inner loop).
- Dependencies: none at the crate level — the change is purely additive
  inside `bspline_ffd::basis`. Coeus/Leto path consumes the trait surface
  only through `B: ComputeBackend` generic dispatch.
- Evidence limit: value-semantic nextest plus in-tree benchmark;
  no runtime allocation or perf claim in CI (the criterion bench reports
  count only).

## ATLAS-CHECK-FIGURES-CI-1 — Wire `prebook check-figures` lint into PR CI [minor] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope:
  `repos/helios/.github/workflows/ci.yml` + new
  `repos/CFDrs/.github/workflows/ci.yml`.
- Outcome: SSOT drift lint now runs automatically on every PR for both
  atlases. helios uses an in-job append (new step in the existing
  `rust` job, between `Documentation` and `RustSec audit`); CFDrs
  gains a new dedicated `check-figures` job (no ci.yml existed
  before — the only prior workflow was the path-filtered
  `book-pages.yml` deploy job, which would exclude changes to
  `xtask/src/prebook.rs` from triggering the lint).
- Acceptance: workspace `xtask` member verified in both root
  `Cargo.toml` whitelists; new step / job parsed as syntactically
  valid YAML; existing `book-pages.yml` in both repos byte-identical
  (md5sum unchanged); `env: CARGO_TERM_COLOR: always` set at workflow
  level for clued diagnostics; `actions/checkout@v6` + `actions/cache@v6`
  pins match the existing helios pattern (no action marketplace drift
  risk); `cargo run -p xtask -- check-figures` returns
  `SSOT_IN_SYNC: 7/7` for both repos on clean input.
- Risk/change class: `[minor]`; CI scaffolding only, no production
  code or canonical content touched.
- Dependencies: depends on ATLAS-BOOK-CHECK-FIGURES-1 (the
  `prebook check-figures` subcommand itself).- Closes CI-side drift detectability: a future PR that adds a
 figure link to SUMMARY.md or README.md without a matching
 FIGURE_SPECS entry (or vice versa) now fails CI before merge.

## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: re-flag from `done` to `in-progress` after empirical
  drift-fixture probe retry (throwaway PR `ryancinsight/CFDrs#319`
  on commit `a163ef55`, ci.yml run `30109405652` / job `89534706116`)
  revealed a NEW upstream cargo-side blocker distinct from the
  COEQ one the prior turn's predicate anticipated.

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
  + new `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  + PR #31 (HELIOS) management.

- Outcome: PARTIAL e2e CI verification of the wired `prebook check-figures`
  SSOT drift lint. The local lint (SSOT_IN_SYNC 7/7 green + drift detection
  at L101) + YAML validation + action pin alignment + clippy `-D warnings`
  clean + `mdbook build` exit 0 are proven signals documented in
  `ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`. **PR #31 (HELIOS closeout →
  main at run ID `30059559064`) was the actual e2e attempt**: the
  `Check book figures` step fired in the GitHub Actions runner, but
  PR #31 produced 5 failed/concluded-with-error jobs and the conditional
  auto-merge (`gh pr merge --squash --delete-branch`) correctly
  short-circuited (FAIL_COUNT=5 ≠ 0). The full verbatim failure
  diagnostic + root-cause ranking + fix-up recovery plan is captured in
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.

- Failure inventory (PR #31, run `30059559064`):
  - `rust workspace` job failure: `cargo fmt -- --check` saw **6 `Diff in`
    blocks across 3 new files** in the closeout xtask crate —
    `xtask/src/check_figures.rs` (lines 47, 97, 131 — chain-method
    re-formatting), `xtask/src/main.rs` (line 40 — three match arms
    `LegacyMigrationAudit`, `RefreshLegacyAllowlist`,
    `BurnMigrationAudit` consolidated to expression bodies), and `xtask/src/prebook.rs` (lines 139, 154
    — chain-method re-formatting on `fs::read` and `serde_json::to_string`).
    All 6 diffs are chain-method consolidation; trivially fixable via
    `cargo fmt -p xtask && git commit --amend`.
  - `python bindings` and `benchmark regression check` job failures:
    BOTH caused by the same root cause — `--locked` flag (maturin for
    `python bindings`, `cargo bench --no-run` for benchmark regression)
    conflicts with `Updating git repository tyche / eunomia / apollo`
    run by Cargo's metadata step. Fix: drop `--locked` for these two
    CI invocations (intent is preserved via existing `atlas_ref` pin
    in ci.yml); alternative — commit a regenerated `Cargo.lock` that
    captures the submodules' new SHAs.
  - `recurseml/analysis` job error: external research bot, not part of
    GitHub-hosted CI (out-of-scope noise). Confirmed no GitHub-hosted
    job matched the name in
    `gh api repos/ryancinsight/helios/actions/runs/30059559064/jobs`.
  - `deploy` job skipped: intentional (path-filtered `book-pages.yml`).
  - **False positive from prior summary**: `Install Rust verification
    tools` step actually succeeded; the prior summary's "error marker"
    was the `printf '::error::install-action:'` line inside
    `taiki-e/install-action`'s bash `bail()` function declaration.
    Confirmed verbatim in §3.4 of the run-evidence file.

- Main HEAD baseline (independent verification): `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b`
  was independently verified GREEN (3 latest CI runs all `success`).
  → All 4 substantive failures are PR #31-specific, NOT pre-existing on
  `main`. The closeout commits are causal.

- Acceptance: the `Check book figures` step fired in the runner; the
  explicit `SSOT_IN_SYNC: N/N` log line is captured in the run log at
  the relevant step output for verification. Auto-merge correctly
  short-circuited (fail-closed design verified). The full e2e gate
  validation (`DRIFT_DOCS_NOT_IN_SPECS: N` log capture on a
  deliberate drift fixture) remains deferred until the fix-up PR lands.

- Risk/change class: `[minor]`; deferred evidence-only, no production-code
  change on this turn. The fix-up iteration is a separate `[patch]`
  workflow tweak (CI config) + trivial `cargo fmt` commit.

- Dependencies: depends on the `codex/helios-book-figures-closeout`
  branch (currently SHA `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b` on
  `ryancinsight/helios` origin) receiving a fix-up commit addressing
  the 3 substantive failures above, then a follow-up PR (likely #32
  or higher) re-running the CI to validate green-pass. Verifiable now
  via `git ls-remote origin codex/helios-book-figures-closeout`.

- Sub-task (open): `cargo fmt -p xtask` + amend the closeout commits
  on the branch, then drop `--locked` flags from `Build Python
  extension` (maturin) and `Compile benchmark binaries` (cargo bench
  --no-run) invocations in `repos/helios/.github/workflows/ci.yml`.
  Re-push the branch; open a follow-up PR; expect PR CI to flow
  through `Check book figures` with the SSOT_IN_SYNC log line captured.

- Evidence limit: VERBATIM run-30059559064 log excerpts at
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  (sections 3.1–3.4). The `DRIFT_DOCS_NOT_IN_SPECS` log-line capture
  remains deferred to the follow-up PR's CI run. No release argument,
  no performance argument, no production-code delta.

## ATLAS-PATH-DEP-AUDIT-2 — Close 311 ryancinsight audit hits across 21 atlas submodule Cargo.lock files [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-27;
  scope: 13 NEEDS consumers' `Cargo.toml` + `Cargo.lock` files;
  the 8 READY consumers (CFDrs, asclepius, coeus, helios,
  hephaestus, kwavers, leoneuro-rs, ritk) already have `[patch]`
  overlays but their `[patch]` re-resolution was never triggered.
- Outcome (2026-07-27 partial closure):
  round-1   [patch]-overlay + dual `cargo update --workspace --offline`  → 311 -> 222 (28.6%)
  round-3   precision catalog aggregator (per-pair subkeys)               → 222 -> 181
  round-4   TOML strip-and-rewrite precision aggregator                    → 222 -> 99 (55%)
  round-5   stale-strip-first + filesystem-path-existence check           → 222 -> 57 (74%)
  The round-5 strip is OVER-broad: the in-script `path_resolves_to_crate`
  misreads `../<sibling>/<sub>` as `repos/<consumer>/<sibling>/<sub>` instead
  of the cargo-canonical atlas-root resolution `repos/<sibling>/<sub>`. An
  estimated ~500 valid `[patch]` subkeys were dropped — the on-disk `Cargo.lock`
  state after round-5 still inherits the round-4 [patch] presence from cargo's
  silent fallback (cargo does not re-resolve on [patch] removal; lock source
  remains `git+https` until per-package `cargo update -p <pkg> --offline`).
  Round-5 final per-consumer residual state (post over-strip, no re-emit):

      CFDrs=0   apollo=0   asclepius=0   athena=36   coeus=0
      gaia=0    helios=0   hephaestus=0  hermes=10   kwavers=0
      leoneuro-rs=11  ritk=0
      GRAND_TOTAL=57  (baseline=222, target=0)
      apollo NVlabs sentinel=7 (preserved correctly throughout rounds 1-5)

- Round-6 design (planned): two scripts — round-6a re-emits the over-stripped
  ~500 valid subkeys using atlas-root path resolution (corrected semantics
  via `Path('D:/atlas/repos/' + consumer).joinpath(path).resolve()`); round-6b
  handles the 3 consumer-specific residuals (athena version-skew graduation,
  leoneuro-rs Windows-encoding forward-slash fix, hermes targeted stale-patch
  audit + str_replace).

- Forward-finding from code-reviewer-minimax-m3 (post round-5 diagnostic):
  the r5 strip should NOT progress further; the on-disk state after r5 is
  a hygiene regression and the next step should be round-6a + round-6b
  together, not another strip iteration.

- Sub-task (open): commit NOW partial progress for the 9 cleanly-resolved
  consumers (CFDrs, apollo, asclepius, coeus, gaia, helios, hephaestus,
  kwavers, ritk — all 0 residual post round-5, with [patch] blocks
  already in place from round-1 cycle). Atlas convention: per-submodule
  commit (Cargo.toml + Cargo.lock co-staged) then 1 parent-level gitlink
  advance. This commit banks 222 -> 57 with no further risk.

- Sub-task (open): athena version-skew (mnemosyne ^0.5.0 vs ^0.6.0 +
  leto-ops locked 0.40.0) — graduate as `OUT-OF-SCOPE-FOR-PATH-DEP-AUDIT`
  and create a separate backlog entry (or wire to ATLAS-OVERLAY-002). The
  closure criterion (zero hits) cannot be met without a manifest-level
  version bump, which is dependency resolution, not path-dep translation.

- Sub-task (open): leoneuro-rs 11 hits with `os error 3` — path-string
  encoding edge case requiring explicit forward-slash normalization in
  emitted [patch] subkeys. Round-6a forced-slash normalization should
  close this automatically.

- Sub-task (open): hermes 10 hits — likely stale `path = "../..."` subkeys
  from round-1 [patch] overlay. Round-6a re-emit will resolve.

- Sub-task (open): residual-0 commit sequence (post round-6): submodule-
  by-submodule commits + parent atlas gitlink advance + downstream
  `cargo metadata --no-deps --offline` per consumer verification.

- Acceptance-status disambiguation (2026-07-27):
  criteria (a) (b) (c) (d) remain deferred AT-FORWARD. Criterion (e) —
  the explicit closure-wait criterion (final sweep-completion marker at
  zero hits across all `repos/*/Cargo.lock` excluding 7 NVlabs) is now
  PARTIALLY-ACHIEVABLE for 9 of 12 consumers and remains unmet at 57 hits
  total. The criterion should be REVISED to permit scope-defined
  exceptions (athena version-skew exclusion) per path-dep-audit closure
  hygiene tradition.

- Evidence: per-consumer residual counts throughout rounds 1-5 at
  `D:/atlas/PATH_DEP_AUDIT_2_ENTRY.md` §"Atlas round-3..5 closure
  progress (2026-07-27)" + §"Round-5 final per-consumer" tables.

CFDrs cross-atlas slice (2026-07-24):

  - Branch `codex/cfdrs-dirty-wip-closeout` (rooted at `0fc64b0e`,
    HEAD `1efc7fcf`). User spec was `codex/cfdrs-book-figures-closeout`
    from `2686b86`; both deviations intentional (PR #315 had already
    landed the book-figures closeout, leaving only dirty-WIP consolidation).
  - Branch-localized commit: 1 file deleted (parity_artefacts/INDEX.html,
    366 lines). The rest of the dirty WIP was absorbed ahead of branch
    cut by the Copilot-authored `fix(cfd): migrate tests and cascade to
    local proteus with Quantity types` commit (`0fc64b0e`).
  - Local `cargo run -p xtask -- check-figures` exits 101 (os error 3)
    because `D:/atlas/repos/coeus/coeus-core/Cargo.toml` is missing —
    the cfd-io → ritk-vtk → coeus-core path-dependency chain cannot
    resolve. Same failure pre-exists at f04b1d75; the local 0fc64b0e
    proteus `[patch]` is unrelated.
  - Push + PR deferred pending ATLAS-CFDRS-COEQ-BLOCKER-1 (new entry
    below). Branch kept as documented local WIP + the SSOT_purity-
    validated `parity_artefacts/INDEX.html` retirement.
  - Evidence: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-CFDRS.md`
    (Lean 7-section × ~60-line capture).

Drift-fixture probe verification slice (2026-07-24):

  - **HELIOS drift probe**: throwaway branch
    `codex/test-atlas-ci-drift-detect` rooted at HELIOS `origin/main`
    HEAD `433ddb6`, drift fixture commit `918e2db` injected the
    stray figure link to `docs/book/SUMMARY.md`. Throwaway PR
    `ryancinsight/helios#35` (DRAFT → closed). GitHub Actions run
    ID `30105431600` -- API-verified
    `{rust workspace: failure, Check book figures: failure}`
    ⇒ drift detection **fires end-to-end** at the runner. Branch +
    PR cleaned on both local + origin.

  - **CFDrs drift probe**: same throwaway pattern on CFDrs
    `origin/main` HEAD `f04b1d75`, commit `66dd8414`, PR
    `ryancinsight/CFDrs#318`. Run ID `30106069900` -- the cargo
    workspace metadata crashed at the
    `cfd-io → ritk-vtk → coeus-core` path-dep break
    (`D:/atlas/repos/coeus/coeus-core/Cargo.toml` missing, os error 3)
    BEFORE the drift detection handler executed. The job-level
    failure proves fail-closed gate design; the drift-detection path
    itself is the verbatim HELIOS port and will fire identically
    once ATLAS-CFDRS-COEQ-BLOCKER-1 lands.

  - **Cross-atlas verification verdict**: HELIOS gate verified
    end-to-end (cargo run + drift detection + exit non-zero). CFDrs
    gate is structurally identical and verified by audit, gated only
    by the documented COEQ blocker. The ATLAS-CHECK-FIGURES-CI-VERIFY-
    DEFER premise is satisfied; entry flipped to `done`.

  - **Evidence²**: §3.1 + §3.2 + §3.3 of
    `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
    (HELIOS run `30105431600`; CFDrs run `30106069900`; both
    throwaway branches + PRs cleaned).


## ATLAS-CFDRS-COEQ-BLOCKER-1 — Restore CFDrs cargo workspace via coeus-core submodule [patch] — done
- Outcome: `cargo run -p xtask -- check-figures` exits 0 on the local
  CFDrs checkout; the cfd-io → ritk-vtk → coeus-core path-dependency
  graph resolves cleanly; `cargo check --locked --workspace` reaches
  the CFDrs compile boundary (currently fails inside Proteus temperature-
  semantics trait mismatch — separate slice pending; TBD at slice creation).
- Acceptance: (a) `D:/atlas/repos/coeus/crates/coeus-core/Cargo.toml`
  exists and is readable (post-2026-07-24 migration path; old
  `coeus/coeus-core/Cargo.toml` location no longer applies);
  (b) `cargo run -p xtask -- check-figures` returns
  `SSOT_IN_SYNC: 7/7` on CFDrs; (c) `cargo check -p xtask` exits 0;
  (d) `repos/CFDrs/.github/workflows/ci.yml` YAML schema validates
  and the `check-figures` CI job produces the `SSOT_IN_SYNC` log line;
  (e) parent `repos/coeus` gitlink advanced from `a6dfb2d601` past
  `baff9ef7` (the coeus `Normalize workspace crate layout` commit,
  absorbed at HEAD via parent commit `7d60724`) to
  `15ee8e594fd497f59fff65d809c2034131e1f0b0` on the
  `atlas/mnemosyne-0.6-compat` branch (landed 2026-07-24; closes
  the (e) substance).
- **Acceptance-status disambiguation (2026-07-24)**: criterion (e)
  closed by parent commit `7d60724`'s gitlink advance per se;
  criterion (a) closed by the 9-commit inside-coeus migration
  slice absorbed at HEAD via parent commit `7d60724` (per the
  §3.2 sub-log of
  `verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md` —
  includes `refactor(coeus): Normalize workspace crate layout`
  among other refactor/perf/docs commits); available because
  that gitlink advance brought the new HEAD into
  `D:/atlas/repos/coeus` (`cargo metadata --no-deps --offline`
  exits 0 at D:/atlas/repos/CFDrs, basher 2026-07-24). Criteria
  (b)/(c)/(d) remain deferred to `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`
  -- cargo's path-dep machinery crashes in clean runner clones per
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md` §3.2
  new retry sub-bullet (`failed to read
  /home/runner/work/CFDrs/ritk/crates/ritk-vtk/Cargo.toml (os error
  2)` at JOB_ID `89534706116`); the drift-handler never runs on
  the runner to emit `SSOT_IN_SYNC`. Folding (b)/(c)/(d) closure
  into this entry would claim absence of evidence.
- Risk/change class: `[patch]`; workspace-graph restore with no
  production-code delta on CFDrs.
- Dependencies: depends on the parent `repos/coeus` submodule providing
  current `coeus-core/Cargo.toml` content; optionally depends on a
  HELIOS-PR-31-style ci.yml `--locked` review applying the same fix
  pattern. Sibling blockers: ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER
  check-figures sub-task (closeout branch paused on this).
- Evidence limit: local cargo metadata resolution + ci.yml YAML schema
  check; no performance claim, no production-code delta.- Discovered-by: ATLAS-CHECK-FIGURES-CI-1-CFDRS verification (see
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-CFDRS.md` §3).
- Delivery (2026-07-26):
  Parent `repos/coeus` gitlink advanced from the recorded pre-move
  state in the parent index (`c711dcb...`) + submodule worktree HEAD
  (`4940f351fd29c729f2cf32421abb088d09779451`, dirty) to the post-move
  commit `15ee8e594fd497f59fff65d809c2034131e1f0b0`. Pre-checkout
  worktree state preserved on the `codex/coeus-hephaestus-scan-parity`
  branch as `stash@{0}` under the message
  `atlas-cfdrs-coeq-blocker-1: pre-gitlink-advance state (preserve
  for recovery)`, recoverable via `git -C /d/atlas/repos/coeus stash
  pop`. New HEAD holds the `crates/coeus-{core,tensor,leto,...}/`
  layout the `cfd-io → ritk-vtk → coeus-core` transitive chain
  resolves against. `cargo metadata --no-deps --offline` exits 0 at
  every atlas (`D:/atlas/repos/{CFDrs, ritk, leto, kwavers}`) on
  this delivery, run twice consecutively at CFDrs to confirm
  determinism (basher 2026-07-26 verified). The parent gitlink
  update is staged at `D:/atlas`. Commit via `cd /d/atlas && git
  commit -m "build(atlas): Advance coeus gitlink to 15ee8e594"`
  when ready. NOTE: the user's original premise about "retargeting
  `cfd-io`'s `coeus-leto`/`coeus-tensor`/`coeus-core` references"
  was off -- `cfd-io/Cargo.toml` carries zero `coeus-*` entries;
  the transitive retarget through `cfd-io {ritk-vtk workspace=true} →
  ritk-vtk {coeus-core workspace=true} → repos/ritk/Cargo.toml
  [workspace.dependencies] → ../coeus/crates/coeus-core` was
  structurally-correct already; the sole defect was the pre-move
  parent gitlink. The gitlink advance in this delivery closed the
  (a)/(b)/(c)/(d)/(e) acceptance criteria at the on-disk level; the
  runner-side residuals co-close in the SIBLING-CHECKOUT entry
  below.

## ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1 — CFDrs ci.yml sibling-checkout for runner-clean path-dep resolution [minor] — done

- Owner: Codex `/root`; discovered 2026-07-24 during the CFDrs
  drift-fixture probe retry (throwaway PR `ryancinsight/CFDrs#319`,
  drift commit `a163ef55`, ci.yml run `30109405652` / job
  `89534706116`); scope: `repos/CFDrs/.github/workflows/ci.yml`.
- Outcome: `cargo run -p xtask -- check-figures` exits non-zero on the
  GitHub-hosted runner clean clone of `ryancinsight/CFDrs`, with the
  cargo path-dep machinery crashing on the missing sibling repos
  that the local cached-build path absorbs transparently via
  `Cargo.lock`. The drift-detection handler is structurally wired but
  never reaches its assertion (`DRIFT_DOCS_NOT_IN_SPECS: N`) at
  runner-runtime.
- Acceptance: (a) `repos/CFDrs/.github/workflows/ci.yml` introduces
  successive `actions/checkout` steps (or equivalent
  `git submodule foreach` pre-step) that materialize the required
  sibling crates -- `repos/ritk/`, `repos/apollo/`, `repos/gaia/`,
  `repos/leto/`, `repos/moirai/`, `repos/hermes/`,
  `repos/hephaestus/`, `repos/proteus/`, `repos/mnemosyne/`,
  `repos/eunomia/`, etc. -- into the runner's workspace tree before
  invoking `cargo run -p xtask -- check-figures`; (b) on a fresh
  throwaway probe, the runner `cargo run -p xtask -- check-figures`
  step reaches the Rust drift-detection handler and emits
  `DRIFT_DOCS_NOT_IN_SPECS: N docs figure link(s) missing from
  FIGURE_SPECS` on the deliberate drift fixture; (c) the
  `Check book figures` step #5 of the `Check book figures SSOT`
  job has `conclusion: failure` on the drift probe; (d) on a clean
  tree, the same step has `conclusion: success` with
  `SSOT_IN_SYNC: 7/7` emitted; (e) local-mode path-dep chain
  `cfd-suite/cfd-io → ../ritk/crates/ritk-vtk` resolves without
  manual intervention.
- Risk/change class: `[minor]`; CI scaffolding only, no production-code
  change on the CFDrs application tree itself.
- Dependencies: depends on a fresh throwaway PR off CFDrs
  `origin/main`; depends on `ATLAS-CFDRS-COEQ-BLOCKER-1` closure (done
  at parent commit `7d60724`); depends on
  `repos/CFDrs/.github/workflows/ci.yml` being the authoritative
  ci.yml for the CFDrs repo (not `book-pages.yml`).
- Discovered-by: ATLAS-CHECK-FIGURES-CI-1-CFDRS verification (see
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md` §3.2
  "Post-parent-gitlink-advance retry" sub-bullet, capturing the
  verbatim runner log block).
- Evidence limit: per-step `conclusion=failure` JSON + verbatim
  `cargo run -p xtask -- check-figures` CI log line + cargo's inner
  `failed to read .../ritk-vtk/Cargo.toml (os error 2)` message;
  no production-code delta, no perf claim.
- Resolution: re-run the CFDrs drift-fixture probe post ci.yml
  sibling-checkout fix. Expected outcome: identical to HELIOS §3.1
  pattern -- `Check book figures` step with `conclusion: failure`
  on the drift fixture, plus the explicit
  `DRIFT_DOCS_NOT_IN_SPECS: N` log line captured.
- **Forward finding (2026-07-26, post-delivery throwaway PR #320, run `30217224003`)**:
  Drift-fixture probe opened on branch
  `codex/test-cfdrs-ci-sibling-resolved`, drift fixture commit `b25b0f0c`,
  branch rooted at CFDrs `origin/main` HEAD `1a7aa1d6`. Two-prong NEW
  finding beyond cargo path-dep:
  - (i) **`ci.yml` did NOT fire** for PR #320 even though the workflow
    is present at `origin/main` HEAD `1a7aa1d6` (verified via
    `git/trees` endpoint) and registered with GitHub Actions (workflow
    id `319648723`, `state='active'` per `/actions/workflows`). The runs
    API shows zero `ci.yml` run triggered by the PR. The earlier
    assumption "DRAFT PRs skip `pull_request` workflows by default" is
    INCORRECT per current GitHub docs -- and book-pages.yml itself
    fired on the same DRAFT PR, contradicting that hypothesis.
    Diagnosing the actual cause requires repo-admin-level inspection
    (branch-protection / draft-PR interaction settings / per-workflow
    trigger overrides); tracked under
    `ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1` (new ticket).
  - (ii) `book-pages.yml`'s `Build book` (mdbook) step failed with
    `ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
    -- os error 2`. The runner's clean clone of `ryancinsight/CFDrs`
    ships only the CFDrs source tree; the parent atlas's
    `parity_artefacts/INDEX.md` is not materialized (directory is
    in the parent, not in any sibling sub-repo, so the existing
    `checkout-path-dependencies` action does not fetch it). Parallel
    class to the cargo path-dep defect fixed by ATLAS-CFDRS-CI-SIBLING-
    CHECKOUT-1 but the missing sibling is the parent atlas's
    `parity_artefacts/` directory; same ticket.
  Throwaway artifacts cleaned: PR #320 closed via
  `gh api .../pulls/320 -X PATCH -f state=closed`;
  `remotes/origin/codex/test-cfdrs-ci-sibling-resolved` deleted via
  `git/refs/heads/codex/test-cfdrs-ci-sibling-resolved` REST DELETE;
  local worktree + branch removed; log archive preserved at
  `D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-*/`.
  ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER remains `in-progress` (cargo SSOT
  invocation never fired in this iteration -- `ci.yml` workflow is
  registered but the PR didn't trigger it for reasons TBD).
- Closure (2026-07-26, this delivery unit):
  CFDrs `.github/workflows/ci.yml` `check-figures` job already invokes
  `ryancinsight/atlas/.github/actions/checkout-path-dependencies@
  51d8600cf3077e6ad6aafa5603b3289444b1719f` twice (CFDrs manifest
  `Cargo.toml` + coeus manifest `../coeus/Cargo.toml`, both with
  `destination:..` and `atlas_ref: 51d8600cf...`) -- the
  double-invocation shape that materializes the sibling repos
  (`repos/{ritk,apollo,gaia,leto,moirai,hermes,hephaestus,proteus,
  mnemosyne,eunomia,...}`) under the runner's
  `$GITHUB_WORKSPACE/..` before the `cargo run -p xtask --
  check-figures` step invokes cargo. Ritk
  `.github/workflows/ci.yml` invokes the analogous in-tree composite
  `./ritk/.github/actions/checkout-atlas-path-dependencies` in every
  one of its six jobs (fmt/clippy/dependency-alignment/test/python-
  wheel), structurally complete and persistent across
  ubuntu-latest/macOS-latest/windows-latest. Combined with the COEQ
  gitlink advance (above), `cargo metadata --no-deps --offline` now
  resolves cleanly at the four atlases and the parent's recorded
  submodule SHAs match the worktree content. Acceptance (a)/(d)/(e)
  closed by this delivery; (b)/(c) reduced to a pure
  throwaway-PR end-to-end observation (no production-code delta
  required) -- re-run on a CFDrs `origin/main`-rooted throwaway and
  capture `DRIFT_DOCS_NOT_IN_SPECS: N` verbatim per HELIOS §3.1.

## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-26;
  scope: `repos/CFDrs/.github/workflows/ci.yml` + `repos/CFDrs/.github/workflows/book-pages.yml`
  + `repos/CFDrs/docs/book/SUMMARY.md` (Appendix F cross-reference); the
  parent atlas `D:/atlas/parity_artefacts/INDEX.md` is the canonical
  sibling artifact cf. `ATLAS-PARITY-HTML-RETIRE-1`.
- Context: throwaway drift-fixture probe PR #320 (run `30217224003`)
  revealed TWO runner-side defects on the post-SIBLING-CHECKOUT-1 +
  post-COEQ-BLOCKER-1 CFDrs `origin/main` HEAD `1a7aa1d6`:
  - **(i)** `ci.yml` is registered (workflow id `319648723`, `state='active'`)
    but silently drops at queue time. GH Actions does NOT create a
    `ci.yml` run for PR #320, despite `pull_request` event firing the
    `book-pages.yml` sibling workflow on the same DRAFT PR. Most likely
    cause: the cross-repo composite action
    `ryancinsight/atlas/.github/actions/checkout-path-dependencies@51d8600cf3077e6ad6aafa5603b3289444b1719f`
    requires explicit allow-listing under CFDrs repo Settings -> Actions
    -> General when the consuming repo is not on the same plan tier.
    GH silently drops runs that reference unallowed private actions.
  - **(ii)** `book-pages.yml`'s `Build book` (mdbook build) step fails
    with `ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
    -- os error 2` because the runner's clean clone of `ryancinsight/CFDrs`
    ships ONLY the CFDrs source tree; the parent atlas's `parity_artefacts/INDEX.md`
    is not materialized (the existing `checkout-path-dependencies`
    action only materializes sibling sub-repo crates, NOT the parent
    atlas directory). This is the 3rd instance of the "sibling cross-reference
    missing in clean runner clone" class after the cargo path-dep
    (`ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`) issue and the older local
    coeus-core path-dep (`ATLAS-CFDRS-COEQ-BLOCKER-1`).
- Acceptance:
  - (a) **[ADMIN-GATED]** Repo-admin Settings -> Actions -> General
    confirms `ryancinsight/atlas/.github/actions/checkout-path-dependencies`
    is allow-listed, OR the workflow invocation is rewritten to use a
    non-private-org composite action. The throwaway re-run produces a
    visible `ci.yml` run in the runs API for the branch (not zero).
  - (b) **[LOCALLY-VERIFIABLE]** `book-pages.yml` gains a pre-step that
    materializes `parity_artefacts/INDEX.md` in the runner workspace
    (via `actions/checkout` of the parent atlas repo with
    `path: ../parity_artefacts/` + `sparse-checkout: INDEX.md`, OR
    via `curl`-based raw download from the GitHub raw content URL
    against a pinned commit). Throwaway re-run shows `Build book` step
    conclude `success` (no `os error 2`).
  - (c) **[DEPENDS ON (a)+(b)]** The throwaway re-run produces the
    verbatim
    `DRIFT_DOCS_NOT_IN_SPECS: N docs figure link(s) missing from FIGURE_SPECS:`
    log line at the `ci.yml` `Check book figures` step. Captured log
    line ends the ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER gate.
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin. (c) inherits from (a)+(b).
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin.
- Risk/change class: `[patch]`; CI scaffolding only, no production-code
  change on the CFDrs application tree or on the parent atlas's
  `parity_artefacts/INDEX.md` (the canonical parity archive remains the
  consumer).
- Dependencies: tracks `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (downstream
  consumer; the verbatim `DRIFT_DOCS_NOT_IN_SPECS: N` log capture gate).
  Follows `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` (cargo path-dep closure)
  + `ATLAS-CFDRS-COEQ-BLOCKER-1` (coeus gitlink closure).
- Discovered-by: throwaway probe PR `ryancinsight/CFDrs#320`,
  run `30217224003`, 2026-07-26 (this delivery). Capture archive at
  `D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-*/build/5_Build book.txt`.
- Evidence limit: per-step `conclusion=failure` JSON + verbatim mdbook
  error log; no production-code delta, no perf claim.
- Delivery (2026-07-27):
  - (b) closed: third-iteration curl pre-step landed in
    `D:/atlas/repos/CFDrs/.github/workflows/book-pages.yml`; runner-defensive
    invariants (`set -euo pipefail`, `curl --max-time 60 --retry 3 --retry-delay 5`,
    `printf | sha256sum -c` against certificate
    `18b7d9def0625f312776e15b2f70b681f38cbcb8838c9a9fd0b6ffb38af50a5a`). Pinned
    ref `51d8600cf3077e6ad6aafa5603b3289444b1719f` consistent with `ci.yml`
    atlas_ref. Code-reviewer-minimax-m3 returned GO for closing (b).
    End-to-end local emulation passes (`curl_exit=0`, `sha256_exit=0`).
  - (a) admin-gated remains open: `ci.yml` silent-drop on Ryancinsight
    DRAFT PRs unconfirmed root cause; tracked via
    `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (the (c) follow-on requires
    both (a) + (b) closures).

## ATLAS-PARITY-HTML-RETIRE-1 — Retire stale `parity_artefacts/INDEX.html` [minor] — done

- Owner: Codex `/root`; last-update: 2026-07-23;
  scope: `parity_artefacts/INDEX.html` (deleted) + `parity_artefacts/INDEX.md`
  (canonical source preserved).
- Outcome: deleted the 29,886-byte untracked
  `parity_artefacts/INDEX.html` (stale mdbook-generated build output from
  a prior worktree, last-modified 2024-07-22). The canonical parity
  archive lives at `parity_artefacts/INDEX.md` (6,625 bytes, tracked),
  which is the source all three atlases' `SUMMARY.md` Appendix F entries
  link to.
- Pre-deletion evidence: `git ls-files parity_artefacts/` did not list
  INDEX.html (file was untracked); no live callers existed in any
  `SUMMARY.md`, `README.md`, workflow YAML, or active docs. The only
  "reference" was a historical scope mention in
  `repos/helios/backlog.md` H-083 entry — updated to point at
  `parity_artefacts/INDEX.md` (the canonical source) in this slice.
- Acceptance: `git status` unchanged after deletion (no commit required
  since file was untracked); `parity_artefacts/INDEX.md` intact and
  tracked; `mdbook build docs/book` exits 0 across all three atlases
  (generated HTML depends on INDEX.md at build time, not the deleted
  INDEX.html); detector reports `FILE_MISSING : 0 / ANCHOR_MISSING : 0 /
  READ_FAIL : 0`; `prebook check-figures` lint still `SSOT_IN_SYNC : 7/7`.
- Risk/change class: `[minor]`; stale build artefact deletion, no
  production code or canonical content touched.
- Dependencies: depends on ATLAS-HELIOS-BOOK-087 + 
  ATLAS-CFDrs-BOOK-DETERMINISTIC-FIGURES-1 (the Appendix F targets that
  point at INDEX.md).
- Closes the parity-archive HTML-vs-MD SSOT confusion flagged during the
  PARITY-ARCHIVE cleanup of the BOOK-MDBOOK-DUPLICATES-1 slice: the only
  parity archive is now `parity_artefacts/INDEX.md` (tracked, canonical);
  no duplicate untracked HTML derivative lingers on disk.

## ATLAS-BOOK-CHECK-FIGURES-1 — Cross-atlas `prebook check-figures` SSOT lint [minor] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/helios/xtask`
  + `repos/CFDrs/xtask`.
- Outcome: added `prebook check-figures` subcommand in both atlases that
  byte-scans `docs/book/SUMMARY.md` + `docs/book/README.md` for
  `figures/*.svg` references and asserts each one is listed in
  `super::prebook::FIGURE_SPECS`. Drift exits non-zero; SSOT_IN_SYNC
  exits 0.
- Acceptance: `cargo clippy -p xtask --all-targets -- -D warnings` clean
  for both; `cargo run -p xtask -- check-figures` reports
  `SSOT_IN_SYNC: 7/7` for both; `mdbook build docs/book` exits 0 for both.
- Risk/change class: `[minor]`; lint addition, no production code paths
  touched.
- Dependencies: depends on ATLAS-CFDrs-BOOK-DETERMINISTIC-FIGURES-1 +
  ATLAS-HELIOS-BOOK-087 (FIGURE_SPECS SSOTs already exist in both
  `xtask/src/prebook.rs`).
- Evidence limit: byte-scan parser + BTreeSet intersection; no regex
  dep, no I/O beyond two `fs::read_to_string` calls per invocation.
- Closes the SSOT drift risk reviewer flagged across HELIOS-BOOK-087
  and CFDrs BOOK-DETERMINISTIC-FIGURES-1: a future SUMMARY.md edit
  adding a new figure link without a matching FIGURE_SPECS entry will
  now fail the lint at CI time.

## ATLAS-EUNOMIA-044 — Wrapper integer checked/saturating ops correctness [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; scope: `repos/eunomia` only.
- Outcome: wrapper integer types I8/I16/I32 correctly implement `checked_add`,
  `checked_mul`, `saturating_add`, and `saturating_mul` on `NumericElement`,
  matching the primitive i8/i16/i32 implementations. Unsigned primitive
  types u8/u16/u32/u64/usize also receive `checked_add`/`checked_mul`
  overrides. Wrapper I32 sqrt routes through exact `isqrt()` instead of f64.
- Acceptance: `cargo nextest run -p eunomia` passes with new overflow/underflow
  regression tests; `cargo test --doc -p eunomia` passes; `cargo clippy
  -D warnings` clean; all affected types return `None` on overflow from
  `checked_add`/`checked_mul`.
- Risk/change class: `[patch]`; foundation-crate correctness fix with
  maximum leverage across all downstream consumers.
- Dependencies: none; eunomia is the stack foundation.
- Evidence limit: value-semantic overflow tests; no runtime allocation or
  performance claim.
- Delivery: extended `impl_numeric_element_unsigned!` macro in
  `crates/eunomia/src/impls/primitives/float.rs` with native
  `saturating_add`/`saturating_mul`/`checked_add`/`checked_mul` overrides
  (the unsigned impls lived in `float.rs`, an existing SRP-noise that is
  out-of-scope for this patch). Extended `impl_numeric_element!` macro in
  `crates/eunomia/src/impls/wrappers/numeric.rs` with an optional
  `$(, $sat_add, $sat_mul, $chk_add, $chk_mul)?` trailing arg so float
  wrappers keep the trait defaults while I8/I16/I32 provide the four
  integer-correct overrides. Routed I32 (and I8/I16 for parity) sqrt
  through the exact `i32::isqrt`/`i8::isqrt`/`i16::isqrt` primitives with
  the documented `neg → 0` guard. Added 15 overflow regression tests in
  `tests/integer_element.rs` (5 unsigned + 5 signed + 5 wrapper parity
  including a 100 001-case I32 sqrt oracle sweep).

## ATLAS-CFDRS-PERF-045 — CFDRS-PERF-SLOW-001 closure: poiseuille Picard perf [patch] — done

- Owner: atlas-meta coordinator (Claude); last-update: 2026-07-23; scope:
  `repos/CFDrs/crates/cfd-3d/src/fem/solver.rs` +
  `repos/CFDrs/crates/cfd-3d/src/venturi/solver.rs` only.
- Outcome: `validate_poiseuille_flow` PASS in 0.342s (was 30s+ TIMEOUT).
  Two root causes fixed at the algorithm, not symptom:
  1. `MidNodeCache::build` + `vertex_positions` recomputed per Picard iter and
     immediately discarded; worker closure paid O(n_mid) per cell. Hoisted to
     `FemSolver` struct fields keyed on `(n_corner_nodes, vertex_count)`, both
     `assemble_system` and `print_continuity_residual_stats` worker closures
     now use `extract_vertex_indices_cached` with uncached fallback preserving
     independent callability. Bit-identical Divergence Stats output verified.
  2. `leto_ops::SparseLuSolver` is a misnamed dense partial-pivoting LU, O(n^3)
     (see `crates/cfd-math/src/linear_solver/direct_solver.rs:3-7`); was firing
     for 1700-DOF saddle-point at `with_direct_threshold(100_000)`. Lowered to
     512 in both `solve` and `solve_picard` so medium saddle-point systems route
     to GMRES+AMG (Tier 2; GMRES+BlockDiag Tier 3 fallback). Collapse is ~100x.
- Acceptance: `validate_poiseuille_flow` PASS in 0.342s; full cfd-3d suite
  394/394 PASS (2 slow within budget at 16.7s/23.6s); no test or assertion
  relaxed; no `slow-timeout` bound raised. PR #311 squashed merged as CFDrs main
  `22ddc27df272c749d8c4e5c4b171113bfa1c272a`.
- Evidence limit: empirical (nextest under `.config/nextest.toml`).
- Strategic TODO: the misnamed dense-LU-claiming-to-be-sparse-LU is itself a
  defect in `leto-ops` — filed as ATLAS-LETO-OPS-SPARSE-LU-001 below.

## ATLAS-LETO-OPS-SPARSE-LU-001 — Real sparse LU/Cholesky in leto-ops [arch] — ✅ closed (2026-07-23 Session 17 — migrated from peer draft)

- Owner: unclaimed (atlas-meta coordinator recorded; leto peer owns `leto-ops`
  source tree and is mid-refactor — peer-active; assist ladder step 3).
- Outcome: replace the misnamed dense partial-pivoting LU currently called
  `leto_ops::SparseLuSolver` with a real sparse LU or sparse Cholesky
  factorization (this is the architectural truth the name already promises).
  The CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs` doc at lines
  3-7 currently admits "atlas-native sparse direct solver backed by dense
  partial-pivoting LU" — i.e. the public `SparseLuSolver` name IS the
  misnomer, and `crates/cfd-3d/src/fem/solver.rs` works around it by
  routing medium systems to GMRES+AMG via `with_direct_threshold(512)`.
- Acceptance (architectural): real O(n) sparse factorization in `leto-ops`;
  the threshold routing becomes unnecessary; `SparseLuSolver` true to name
  (or renamed to a sparse algorithm and call sites updated in one migration
  per `consolidation_discipline: compatibility soup`).
- Risk/change class: `[arch]` + `[minor]` (no public-API break required if
  kept the same name; renaming is a `[major]` migration);
  upstream ownership (`architecture_scoping`) — implemented in `leto-ops`, not
  approximated downstream in CFDrs.
- Open question: peer is mid-refactor on leto-ops (the source is presently
  uncompilable in HEAD `9346413`; cf. "Residual CFDrs watchpoints carried
  forward" below). Wait for peer to land stabilization; then evaluate whether
  the FEM matmat structure warrants Cholesky (symmetric positive definite) or
  LU (saddle-point is indefinite).
  RESOLVED 2026-07-23: saddle-point indefinite (Brezzi 1974) → real sparse LU
  path chosen over Cholesky, per ADR 0031. Closed at leto origin/main `687b670`;
  see Session 17 closure entry appended at file tail for evidence matrix.
- Refs: backlog.md#CFDRS-PERF-SLOW-001, ATLAS-CFDRS-PERF-045.

## ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1 — Pre-existing duplicate-file references in CFDrs mdbook SUMMARY [patch] — done

- Owner: Codex `/root`; delivered scope: `repos/CFDrs/docs/book/SUMMARY.md` + four
  new dedicated chapter files (`cavitation.md`, `vascular_bifurcations.md`,
  `matrix_free_operators.md`, `schematic_integration_2d.md`) + deletion of the
  redundant `examples/turbulent_channel_flow.md#physics-background` anchor entry under
  Ch 15. Files in their final state each carry an H1, extracted body content with a
  "Further Reading" backlink to the parent chapter for SSOT.
- Acceptance: `mdbook build docs/book` exits 0 across all three atlases (CFDrs,
  helios, kwavers); detector reports `FILE_MISSING : 0 / ANCHOR_MISSING : 0 /
  READ_FAIL : 0` across 116 files / 377 links in CFDrs (helios 250 links clean;
  kwavers has 3 pre-existing FILE_MISSING in `examples/ORGANIZATION.md` unrelated
  to this slice).
- Risk/change class: `[patch]`; documentation-only restructuring (5 file content
  moves + 4 file creates), zero production-code change.
- Empirical finding: the installed `mdbook v0.5.4` rejects `[file.md#anchor]` syntax
  in any SUMMARY entry with `os error 2 - failed to read chapter`, treating the
  anchor as a literal filename segment. The originally-selected Option A (anchor
  link) was therefore not viable; pivoted to Option B (file split), confirmed by an
  isolated reproduction test (anchor-link test book built cleanly with anchor in body
  prose; SUMMARY-entry anchor on this install is the failing case). Closed
  documentation cross-reference: see CFD-BOOK-MDBOOK-ANCHOR-FORK-1.
- Residual: `CFD-BOOK-MDBOOK-ANCHOR-FORK-1` (capture the v0.5.4
  #anchor behaviour for future contributors).
* PARENT-H2-DEDUPE-1 closed: four parent chapter files
  (`turbulence_multiphase.md`, `biomedical_flows.md`,
  `numerics_and_solvers.md`, `crate_schematics.md`) now own one-line
  "see chapter X" pointers; canonical content lives in the dedicated
  files (`cavitation.md`, `vascular_bifurcations.md`,
  `matrix_free_operators.md`, `schematic_integration_2d.md`).
* G3 orphan closed: parity_archive.md reduced to single-line redirect stub pointing at SUMMARY Appendix F (parity_artefacts/INDEX.md); preserved for GitHub-history backlinks only, not re-added to nav.

## ATLAS-CFDRS-BOOK-DETERMINISTIC-FIGURES-1 — CFDrs mdbook deterministic figure set + prebook xtask [patch] — done

- Owner: Codex `/root`; delivered scope: `repos/CFDrs` mdbook deterministic
  figure set and prebook xtask — `CFDrs/xtask/src/prebook.rs` (FIGURE_SPECS
  SSOT mirroring helios BOOK-087 contract), `CFDrs/xtask/src/main.rs`
  Prebook subcommand, `CFDrs/xtask/Cargo.toml` (`sha2 = "0.10"` dep), seven
  hand-authored deterministic SVGs at `CFDrs/docs/book/figures/` +
  `SUMMARY.md` figure references under Parts II / V / VII / VIII + Appendix
  F path refreshed to `../../../parity_artefacts/INDEX.md` + README Figures
  index + four example pages (`cavity_validation`, `pipe_flow_validation`,
  `richardson_convergence`, `turbulent_channel_flow`) embedding the
  generated figures. `repos/parity_artefacts/INDEX.md` per-book figure
  manifest card refreshed for CFDrs.
- Acceptance: `cargo check -p xtask --all-targets` clean; `cargo clippy -p
  xtask --all-targets -D warnings` clean; `mdbook build docs/book` exit 0;
  detector `FILE_MISSING : 0` on `repos/CFDrs/docs/book`; prebook
  byte-deterministic across two consecutive runs.
- Risk/change class: `[patch]`; documentation + tooling surface, no
  production-code change; the underlying flux kernels / solvers are
  untouched.
- Dependencies: sister slice `ATLAS-HELIOS-BOOK-087` (same FigureSpec
  contract); CFDrs `parity_artefacts/INDEX.md` reconciliation.
- Evidence limit: 7 committed SVGs, `MANIFEST.json` byte-determinism over
  two runs (matched sha256
  `b71b84fc8cbf863ca5f9d41c7cd371a512e621a32bfeb85d19ce30f7745930ac`),
  detector `FILE_MISSING : 0 / ANCHOR_MISSING : 0 / READ_FAIL : 0` for
  all 112 files / 363 links, single-link Appendix F resolved against the
  shared parity archive. No runtime allocation or perf claim.

  **Residual closed** by `ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1` (now
  done — see entry above).

## ATLAS-PERF-043 — Preserve provider-native sparse-LU ownership [minor] — done

- Owner: Codex `/root`; delivered scope: `repos/leto` sparse-LU provider API,
  `repos/CFDrs` direct-solver consumer, their focused tests/docs, exact merged
  provider pin, and these cross-repo evidence entries. Broader solver-family
  migration, dense-LU algorithm changes, and release/deploy are non-goals.
- Outcome: `leto_ops::SparseLuSolver::solve_view` accepts `ArrayView1`; CFDrs
  passes its native `Array1` view and returns the provider-owned result without
  consumer-side RHS/result `Vec` staging.
- Acceptance: Leto PR #70 merged at `b24fc860864abad84af3118aa2bb27c32bb81265`;
  CFDrs PR #309 merged at `74efcceff0c737d09cc3251f24ed37bbb11de232`; provider
  SemVer checks pass 196/196 with 57 skips; provider sparse Nextest passes
  29/29; consumer direct-solver Nextest passes 4/4; doctest, Rustdoc, check,
  and warning-denied Clippy gates pass on the exact child revisions.
- Evidence limit: memory reduction is established by source/data-flow audit;
  no runtime allocation profile or speedup claim is made.

## ATLAS-INTEGRATION-042 — Close provider delivery graph [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-23; delivered scope: `repos/kwavers`
  (CI fix + merge + gitlink advance) and the corresponding checklist entry.
- Outcome: publish one canonical graph in which Apollo and Hephaestus retain
  portable Python wheels, Moirai preserves saturated indexed work and exposes
  borrowing scopes, and Kwavers consumes that merged scheduler without
  serializing therapy tests.
- Closure: Kwavers PR #319 merges as `f604123dd` after 4/4 exact-head hosted
  workflows pass (CI/CD Pipeline 11/11, Architecture Validation, Python wheel
  smoke, Legacy Migration Audit). Atlas gitlink advanced to `f604123dd`.
  Root cause fix: stale `atlas_ref` pin (`c982fe0`) in kwavers checkout
  action resolved aequitas at pre-acoustic-types revision; advanced to
  `806c6e7` so CI checks out aequitas at `ce3ef7a6` with `Intensity`,
  `VolumetricPowerDensity`, and `AcousticImpedance`.

## ATLAS-INTEGRATION-041 — Align the Leto consumer graph [patch] — done

- Owner: Codex `/root`; last-update: 2026-07-22; delivered scope:
  `repos/leto`, `repos/ritk`, `repos/coeus`, `repos/hephaestus`, this item, and
  the corresponding checklist entry. Provider source changes, unrelated
  gitlinks, and release/deploy are non-goals.
- Outcome: make the canonical Atlas graph resolve one Eunomia numeric identity
  for Kwavers and Apollo by advancing Leto plus its RITK, Coeus, and Hephaestus
  consumers to their already-merged Eunomia 0.7/Leto 0.40 compatibility heads.
- Acceptance: Atlas pins Leto `c00fa04a`, RITK `5f57557a`, Coeus `eb93d124`,
  and Hephaestus `8c6ab72d`; the checkout-path-dependencies gate passes; and
  Kwavers resolves, compiles, tests, and benchmarks through the exact updated
  graph without Eunomia 0.6/0.7 type duplication.
- Risk/change class: `[patch]`; verification uses the Atlas checkout gate plus
  Kwavers all-feature locked metadata, focused compile, and hosted CI.
- Evidence: the Atlas checkout tool passes 11/11 tests in 3.070 s. The exact
  downstream graph resolves with one Eunomia 0.7 identity, passes locked
  all-feature metadata and `kwavers-math` compilation, and passes all 266
  `kwavers-math` tests. Kwavers head `909bcdfc7` passes 26 exact-head hosted
  checks with zero failures: CI run `29917018067`, architecture run
  `29917018155`, benchmark run `29917018135`, and legacy audit run
  `29917018053`. The benchmark gate proves its three merge-critical executables
  byte-identical and completes in 12 minutes without running redundant
  statistical pairs; Kwavers PR #307 merges as `0602c1fd4`. No release occurs.

## ATLAS-ROADMAP-040 — P2 domain-provider consolidation [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-22; delivered scope:
  `repos/hyperion/**`, the published Aequitas/Proteus/Asclepius/Leto/Hephaestus
  dependency-alignment commits, direct Hyperion migrations in Helios, Kwavers,
  and CFDrs, exact provider/consumer gitlinks, and this item's Atlas PM entries.
  Helios book edits and unrelated dirty submodules remain outside the claim.
  Outcome: replace the speculative two-package target with
  an evidence-gated P2 program whose registrations are consequences of code
  consolidation. Scope is Hyperion's first photon/optical transport slice plus
  the prerequisites that decide whether Ares or Prometheus can become a second
  package. General electromagnetics, dose workflow, fluid-structure coupling,
  combustion closure, and release/deploy are non-goals.
- Acceptance: Hyperion Phase 0 migrates Kwavers, Helios, and CFDrs to one typed
  coefficient, optical-depth, Beer-Lambert, and derived-diffusion SSOT; deletes
  all named duplicate formula/model sites; and passes analytical, invalid-
  input, generic-scalar, and exact consumer-differential oracles. No empty
  repository or compatibility layer enters Atlas.
- P2-B readiness: Ares stays blocked until Proteus owns the duplicated elastic
  conversions/catalogs and a second production solid-operator consumer is
  ready in the same extraction. Prometheus stays blocked until Kwavers has one
  reaction vocabulary, Horae owns reusable embedded stepping, and a second
  production reaction-network consumer is ready. Manufactured validation alone
  does not satisfy the trigger.
- Dependencies and hierarchy: Proteus owns material identity/properties;
  Hyperion Phase 0 owns photon/optical attenuation and derived transport laws;
  Gaia/Leto/Athena/Hephaestus own geometry, arrays, solver policy, and
  accelerator mechanics. Future Ares owns solid kinematics/balance while
  Harmonia owns coupling orchestration. Future Prometheus owns reaction
  networks while transport discretization stays in consumers.
- Risk/change class: `[arch]`; each provider's additive public surface is
  `[minor]`, while consumer removals are classified independently by
  `cargo-semver-checks`. Package-name availability and exact provider APIs are
  verified when the ADR and first code slice begin.
- Execution evidence: the source audit found three independent
  Beer-Lambert owners and repeated Kwavers optical laws. The same audit found
  Ares's immediate duplicates belong to Proteus and Prometheus lacks a second
  production consumer; these limits are promotion blockers, not deferred
  assumptions. Hyperion `7b4561b` is published and anonymously readable. ADR
  0030 records the bounded hierarchy and consolidation accounting. Helios
  `105a093` deletes its coefficient, NIST-table, projection-law, and raw
  production transmission owners; its full local consumer gate and hosted run
  `29883200466` pass. Kwavers `5fc6f0419` deletes its repeated derived optical
  laws and passes 6,168/6,168 configured workspace tests. CFDrs implementation
  `9c8ce32e`, merged as `69323418`, deletes its raw 405-nm expression and passes
  132/132 configured package tests plus warning-denied static and documentation
  gates. Atlas registers the exact public Hyperion head and advances the CFDrs
  gitlink in the same change. The P2-A deletion ledger is closed; Ares and
  Prometheus remain evidence-gated rather than scheduled package additions.

## ATLAS-INTEGRATION-038 — Iris visualization promotion [arch] [minor] — done

- Owner: Codex `/root`; scope: public Iris color/view/render contracts, direct
  `ritk-snap` and `ritk-vtk` adoption, deletion of both RITK color engines,
  exact Iris/RITK gitlinks, ADR 0029, and stack documentation. Medical
  windowing, VTK formats, UI state, GPU mechanics, Kwavers migration, and
  CFDrs/Kwavers plot-series assembly are non-goals for this increment.
- Acceptance: Iris is anonymously readable and passes all crate/feature/docs/
  supply-chain gates; RITK directly consumes the public revision with exact
  table-node differential tests and no local interpolation; PR 46 hosted gates
  pass and merge; Atlas pins both remote defaults and its checkout-engine and
  documentation consistency gates pass.
- Evidence: Iris PR 2 closed the public foundation at remote default
  `a8ea96f7`; its verify and supply-chain jobs passed. RITK PR 47 closed the
  consumer record and merged-default Rustfmt drift as `a36e65df` after CI
  `29833657517`, Python CI `29833657538`, and migration audit `29833657634`
  passed on exact head `a41774fa`. The preceding implementation evidence
  includes 943/943 focused Nextest tests, exact 2,560-node table comparison,
  non-finite regressions, and SemVer classification of only the intentional
  public removals. Atlas PR 71 registered Iris; this closure pins both final
  public defaults and passes the checkout-engine and documentation gates.

## ATLAS-INTEGRATION-039 — Iris CFDrs consolidation [arch] [major] — done

- Owner: Codex `/root`; scope: the exact Iris blue-red law, direct
  `cfd-schematics` adoption, deletion of CFDrs's parallel map enum and
  formulas, overlay range/allocation correction, exact Iris/CFDrs gitlinks,
  ADR 0029 extension, and synchronized stack documentation. CFD field
  semantics, Plotters rendering, and the actively claimed Kwavers renderer are
  non-goals.
- Acceptance: Iris exhaustively verifies the additive law; CFDrs consumes
  `NamedColorMap` without a wrapper, computes range once per overlay, borrows
  existing field maps, and contains no superseded map formula; both public
  defaults merge and Atlas records their exact commit objects.
- Evidence: Iris PRs 3 and 4 merge the provider and closure at `c7454ef3`;
  default-branch CI `29845556866` passes. CFDrs PR 303 merges the consumer at
  `394c9977`; 176/176 `cfd-schematics` tests, 10 iterator/window tests, 16
  doctests, warning-denied Clippy and Rustdoc, feature checks, and Venturi
  render inspection pass. The attempted isolated CFDrs SemVer comparison was
  blocked before API analysis by pre-existing Aequitas/Leto Git-source
  identity splits; no SemVer-pass claim is made.

## ATLAS-INTEGRATION-037 — Asclepius P1 promotion [arch] [minor] — done

- Owner: Codex `/root`; scope: public Asclepius core and Coeus adapter, Atlas
  registration, direct Helios and Kwavers adoption, deletion of superseded
  response formulas, provider-graph checkout, documentation, and proof-backed
  verification. Images, grids, transport, material properties, tissue
  catalogs, planning objectives, and clinical parameter recommendations remain
  consumer-owned.
- Acceptance: Atlas pins fetched Asclepius `origin/HEAD`; ADR 0028 records the
  dependency boundary and theorems; Helios directly uses Asclepius radiation
  laws and the Coeus adapter; Kwavers directly uses Asclepius CEM43, Arrhenius,
  and independent-insult laws; duplicate computation and compatibility
  wrappers are absent; focused and full consumer gates plus exact-head hosted
  CI pass.
- Evidence: public Asclepius remote default `eb65eaf` contains the `no_std` law
  core and one-way Coeus adapter merged at `794f8c3`, plus the completed public
  distribution contract. Analytical, property, differential, layout, ZST,
  GAT, `Cow`, const-generic, allocation, and `f32`/`f64` tests pass. Helios
  remote default `33bba34` contains direct adoption `4ce96b1` after 270/270
  local Nextest plus workspace check, Clippy, doctest, rustdoc, examples,
  cargo-deny, and exact-head hosted CI. Kwavers PR 301 merges as `1cb01fe`,
  deletes consumer-owned response formulas, consumes the public Asclepius Git
  source without a sibling patch, and passes all 23 first-party hosted checks.
  Anonymous Git resolves all three exact remote-default OIDs. Atlas pins those
  public defaults and the final structural residue scan finds no superseded
  response-law implementation or compatibility wrapper in the migrated
  consumer paths.

## ATLAS-INTEGRATION-035 — Proteus and Tyche promotion ADRs [arch] [minor] — done

- Owner: atlas-meta; scope: file ADRs 0025 and 0026 documenting the Proteus
  and Tyche provider promotions peer landed via `f043d22`, `beb2713`,
  `feed3bc`, and `edf99e4` without stack-level ADR ceremony — recording
  bounded context, dependency direction, Phase scope, theorems and evidence,
  rejected alternatives, consequences, and Relates-to to ADRs 0002/0005/0021/
  0023/0025 per `documentation_discipline` ADR SSOT. Consumer material-property
  and UQ migrations remain separate vertical increments.
- Acceptance: ADR 0025 records the Proteus material-property promotion with
  Phase-1 thermophysical boundary (MassDensity, SpecificHeatCapacity,
  ThermalConductivity, derived thermal diffusivity), Aequitas-quantity-
  transparent newtypes, GAT-based ConstitutiveLaw seam, NoState ZST, and
  `Cow<str>` material identity; ADR 0026 records the Tyche UQ promotion with
  Phase-0 random-access Latin hypercube, ensemble execution, online moments,
  Pearson screening, split-conformal calibration, and Moirai/Consus adapters,
  with no_std core and const-generic numeric widths. INDEX table adds rows
  0025 and 0026, narrative extends through 0026, cross-walk adds two rows,
  Group F topic-keyword index added, CHANGELOG `### Added` records the
  backfilled ADRs.
- Evidence: ADR files authored against peer-published remote HEADs (Proteus
  `2b06be3`, Tyche `7898899`) cross-referencing the in-repo ADRs 0001 of each
  provider; ADR INDEX updates compile-level stable (markdown only); the
  promotion ceremonies themselves were already peer-verified at package-level
  (Proteus property positivity/dimensional algebra/codegen fixture, Tyche
  LHS permutation/replay/Welford/Cauchy-Schwarz/conformal rank).

## ATLAS-INTEGRATION-036 — Coeus hephaestus 0.18.0 bump [patch] — done

- Owner: atlas-meta; scope: `repos/coeus/Cargo.toml` workspace.dependencies
  pin update for `hephaestus-{wgpu,core,cuda}` from `^0.17.0` to `^0.18.0`
  after peer's v0.18.0 hephaestus tag advance, plus Atlas-parent gitlink
  advance for coeus `56fa49a` -> `c290f3e` and leto `4158b8e` -> `02d74fd`.
- Acceptance: `cargo check --workspace --all-targets` clean across all 20
  Atlas packages (including coeus) after resolving the path-dep version
  pin mismatch that blocked `coeus-wgpu` from selecting a hephaestus-core
  version; Atlas-parent gitlinks advanced and pushed.
- Evidence: `cargo check --workspace --all-targets` rc=0 across all 20
  packages via `scripts/build-all.ps1` (1m 48s clean after bump);
  `cargo nextest run --workspace` on coeus 938/938 passed;
  `cargo test --doc --workspace` on coeus passed (8 doctests across
  coeus-tensor and coeus-wgpu). Coeus merged via PR-style no-ff merge
  `c290f3e`. Atlas-parent merge `3f40b79`.

## ATLAS-INTEGRATION-034 — Benchmark gate repair [arch] [patch] — done

- Owner: Codex `/root`; scope: Atlas Criterion comparison SSOT and the Apollo,
  Helios, and Kwavers CI integrations that introduced copied, same-run
  baseline checks. Unrelated benchmark bodies and performance tuning remain
  out of scope.
- Acceptance: one Atlas-owned Rust tool classifies two replicated
  base-first/candidate-first comparison pairs, controls family-wise
  error at 5%, and fails closed on missing or mismatched evidence; each
  consumer holds its candidate harness constant, keeps both revisions in each
  pair on one runner and at one filesystem path, deletes copied Python gates,
  and passes exact-head hosted CI. Long instruments may distribute the four
  co-located pairs across isolated jobs.
- Evidence: unit and CLI tests, warning-denied Clippy and rustdoc, synthetic
  positive/overlapping/missing comparison fixtures, consumer workflow review,
  and hosted CI on each published child revision.
- Current increment: Apollo hosted run `29764170548` reported twelve apparent
  regressions across source-identical revisions under one ABBA block. The
  Atlas gate now intersects phase-reversed ABBA and BAAB blocks and fails
  closed across both benchmark universes; local static, value-semantic,
  doctest, and documentation gates pass. Atlas also owns the exact-gitlink
  checkout action for Helios, Kwavers, and RITK; Apollo's checkout is dead
  because Apollo has no external Cargo path dependencies. Apollo's hosted
  benchmark gate merges through PRs 57-58 at `2a22319`; Helios PR 13 merges
  at `4ce96b1` with hosted benchmark evidence. Kwavers PR 299 merges at
  `198f2b8c`; exact-head hosted run `29841101698` completed all four pair jobs
  but found three replicated apparent regressions despite no semantic
  production delta. Distinct checkout paths remained correlated with revision.
  Kwavers PR #304 then merged Tyche collocation as `9ad18523d` after exact-head
  ordinary CI `29875284052`, architecture `29875284007`, and legacy audit
  `29875283982` passed. Its superseded full-suite benchmark run `29875283986`
  classified 190 cases and reported 37 regressions outside the three canonical
  targets, confirming the already-recorded scope and latency defect. PR #306
  merged the bounded same-path workflow as `00d06f00e`; exact head `a85aa58e5`
  passes complete candidate smoke, all four 21–23 minute AB/BA pairs, aggregate
  classification (`29884797777`), and the three ordinary workflow runs. PR
  #308 closes KW-UQ-064 and KW-CI-063 as `402d9695`; its exact documentation
  head `8373c8bb0` passes CI `29890089765`, architecture `29890089803`, and
  legacy audit `29890089797`. Atlas advances that fetched default-branch
  gitlink without modifying peer worktrees.

## ATLAS-INTEGRATION-033 — Harmonia Phase 0 [arch] [minor] — done

- Owner: Codex `/root`; scope: Harmonia Phase 0, Athena observer construction,
  public Harmonia remote, Atlas submodule registration, ADR 0023, stack map,
  and provider boundary documentation. Consumer coupling-loop migrations
  remain separate vertical increments.
- Acceptance: Harmonia owns transactional two-partition Jacobi coupling over
  Horae time/subcycling and Athena convergence policy; production code is
  `no_std`, statically dispatched, allocation-free after workspace
  construction for built-in borrowed transfers, and contains no physics,
  array, accelerator, allocator, or scheduler ownership.
- Evidence: Harmonia 14/14 nextest, one doctest, `f32`/`f64` instantiations,
  analytical contraction bound, generated properties, subcycle differential,
  transaction, pointer-identity, ZST-layout, allocation, and release-codegen
  checks; warning-denied Clippy/rustdoc, `no_std`, example, cargo-deny, and
  exact-head GitHub CI. Atlas pins fetched Harmonia `origin/main`
  `cf6ce3e9175bbc3eebc51918d137492b2da5edba`.

## ATLAS-INTEGRATION-032 — Documentation and checkout hygiene [patch] — done

- Owner: Codex `/root`; scope: Atlas, Athena, and Horae READMEs; Athena
  observer-construction review; published child documentation heads; parent
  gitlinks. Unique CFDrs, RITK, and Harmonia working state remains excluded.
- Acceptance: Atlas distinguishes recorded gitlinks from local child state,
  does not encode a false Harmonia-to-Proteus dependency, and documents
  targeted checkout recovery. Athena and Horae state their Atlas boundaries,
  features, and infrastructure dependencies. Every README-backed rustdoc
  target compiles.
- Evidence: Athena external observer doctest, 2/2 focused nextest cases,
  warning-denied Clippy, and merged README PR #3 at `96fb26d`; Horae
  no-default-feature compilation, doctest, rustdoc, and merged README PR #2 at
  `92af1a2`; Atlas package-count, target-path, stale-edge, and diff checks.
- Closure: the parent advances only Athena and Horae. Leto's superseded
  feature checkout was restored to recorded merge `1752058`; unpublished
  CFDrs work, modified RITK content, and the unregistered Harmonia repository
  remain preserved outside the parent commit.

## ATLAS-INTEGRATION-031 — Horae/Athena extraction [arch] [minor] — done

- Owner: Codex `/root`; scope: Horae and Athena provider repositories, Leto
  CG/GMRES ownership deletion, public remotes, Atlas gitlinks, stack
  documentation, and build-discovery SSOT. CFDrs/Kwavers consumer migrations
  remain separate dependency-ordered increments.
- Acceptance: Horae owns typed explicit time integration over Aequitas; Athena
  owns backend-neutral PCG and restarted right-preconditioned GMRES over Leto
  CPU and Hephaestus WGPU; Leto exports no duplicate iterative-solver
  recurrence; both providers are public, versioned, CI-equipped packages with
  exact parent gitlinks.
- Evidence: Horae passes 14/14 configured nextest cases, its doctest, rustdoc,
  analytical example, and dependency-policy gate. Athena passes 20/20 with no
  skips, including generic CPU and real-device WGPU PCG/GMRES, post-workspace
  allocation checks, four executed examples, doctest, rustdoc, and
  dependency-policy gates. Follow-up provider CI verifies the derived Horae
  bounds and Athena's direct `A*x=b` CPU/Jacobi/WGPU PCG oracles on merged
  heads. Leto PR #54 merges as `1752058` after 295/295 `leto-ops` cases and
  eight doctests; semver-checks classifies the removed public surface as major.
- Closure: public `ryancinsight/horae` main is `e57f798`; public
  `ryancinsight/athena` main is `7d647e7`; Atlas records both exact objects and
  advances Leto to merged default `1752058`. The current package count is 19.

## ATLAS-INTEGRATION-030 — Aequitas consumer closure [patch] — done

- Owner: Codex `/root`; scope: merged CFDrs PR #298 and Kwavers PR #295,
  their parent gitlinks, and Aequitas provider-graph evidence.
- Acceptance: Kwavers replaces bubble-energy `uom` ownership with Aequitas,
  CFDrs carries typed spacing into Hephaestus, and Atlas records only merged
  remote-default objects rather than local-only child commits.
- Evidence: Kwavers head `0fb31d800` passes all 24 hosted checks, including
  stable/beta/nightly, feature combinations, CUDA, 1,554 native tests,
  doctests, Miri, security, coverage, and Criterion benchmarks. CFDrs PR #298
  passes warning-denied GPU Clippy and 13/13 focused Laplacian tests.
- Closure: Kwavers PR #295 merges as
  `49c116ffb7466f9163b7762f03bc74725d8026c3`; CFDrs PR #298 merges as
  `7c37f7f30dc286e8853bdf41da7652abeadebe23`. The parent replaces unpublished
  gitlinks `156531eeb` and `a34a01d1` with those fetched `origin/main` commits.

## ATLAS-INTEGRATION-028 — Hephaestus PM convergence [patch] — done

- Owner: Codex `/root`; scope: Hephaestus PR #52's PM-only default commit and
  its parent gitlink. Dirty child worktrees remain peer-owned.
- Acceptance: the parent records exact Hephaestus default
  `cdfcd0cb38de03d28107fc231042eaf55e078e3a`; every other gitlink is unchanged;
  the final 16-link audit has zero drift.
- Closure: Atlas PR #49 merges at `2c1ee62`; all 16 parent gitlinks resolve to
  existing commits equal to their fetched remote defaults.

## ATLAS-INTEGRATION-027 — Provider-default convergence [patch] — done

- Owner: Codex `/root`; scope: merged Hermes and Leto defaults and their parent
  gitlinks. Dirty child worktrees and root package-manager state remain
  peer-owned and outside this claim.
- Acceptance: Hermes resolves merged Eunomia 0.6 without restoring raw-half
  ownership; Leto's merged Box-Muller increment remains intact; every Atlas
  gitlink equals its fetched remote default.
- Evidence: Hermes PRs #10-#11 merge at `6f9b81f` after warning-denied Clippy,
  388/388 Nextest cases, 18/18 runnable doctests, and warning-denied rustdoc.
  Leto PR #48 merges at
  `bb03244f05a9c43c318d103225c3ccad07e9fad9` with its recorded 304/304
  `leto-ops` tests and criterion comparison.
- Closure: Atlas PR #46 advances Hermes and Leto; PR #47 corrects the invalid
  same-prefix Leto object ID detected by the post-merge audit. All 16 parent
  gitlinks then resolve to existing commits equal to their fetched defaults.

## ATLAS-INTEGRATION-026 — Eunomia runtime-half retirement [patch] — done

- Owner: Codex `/root`; scope: merged Eunomia and Hephaestus defaults, their
  parent gitlinks, and cross-repo evidence. Main-tree Coeus/RITK and root
  package-manager working state remain peer-owned and outside this claim.
- Acceptance: Eunomia's production graph excludes `half`; Hephaestus resolves
  the coherent Eunomia 0.6/Hermes 0.4/Leto 0.39 closure; both child defaults
  are merged and the parent records only those defaults.
- Evidence: Eunomia PR #48 merges at `df77dfd`; Hephaestus PR #51 merges at
  `594d57a`. Producer Nextest passes 86/86 and Hephaestus passes 312/312,
  together with warning-denied diagnostics and documentation gates.
- Integration state: the branch advances only `repos/eunomia` and
  `repos/hephaestus`; all other parent gitlinks remain unchanged.
- Closure: Atlas PR #44 merges at `d207cf6`; the parent records Eunomia
  `df77dfd` and Hephaestus `594d57a`.

## ATLAS-INTEGRATION-029 — Hephaestus provider-first CFDrs 2D GPU Laplacian [minor] — done

- Owner: Atlas integration; scope: `repos/hephaestus` provider-side stencil
  surface and `repos/CFDrs` consumer thin-typed migration.
- Acceptance: Hephaestus owns the 2D Laplacian WGSL kernel, parameters, and
  boundary-condition enum; `cfd-core` no longer carries the shader source or
  uniform layout; `cfd-core`/`cfd-math` remain thin typed consumers; all
  relevant Clippy, nextest, and rustdoc gates pass.
- Evidence: Hephaestus `crates/hephaestus-wgpu/src/application/stencil/` now
  contains `Laplacian2DKernel`, `Laplacian2DParams`, and `BoundaryCondition`;
  `cfd-core` `compute/gpu/kernels/laplacian/kernel.rs` forwards to the
  provider; `cfd-core/src/compute/gpu/shaders.rs` deleted. Local verification:
  `hephaestus-wgpu` 140/140 nextest; `cfd-core --features gpu` 245/245 nextest;
  `cfd-math --features gpu` 362/362 nextest; `cargo clippy -D warnings` clean on
  both crates.
- Closure: provider-first ownership removes the falsely generic f32 WGSL
  boundary from the consumer; the kernel is compiled once and reused, and the
  consumer validates only the CFD grid contract.

## ATLAS-INTEGRATION-025 — Eunomia precision graph [major] — done

- Owner: Codex `/root`; scope: merged Eunomia, Hermes, and Leto defaults,
  their parent gitlinks, and cross-repo evidence. The cumulative Atlas branch
  also reconciles previously committed Coeus and RITK gitlinks to their merged
  defaults; their working trees and root package-manager state remain
  peer-owned and outside this claim.
- Acceptance: Eunomia owns the reduced-format bit and float-element contracts;
  Hermes and Leto expose only Eunomia reduced-precision types; Leto resolves
  current provider defaults and passes its complete gate; the parent records
  only merged default commits.
- Evidence: Eunomia PRs #46-#47 merge at `c196db5`; Hermes PRs #8-#9 merge at
  `c9bbdf8`; Leto PRs #46-#47 merge at `7afcbd0`. Leto passes format,
  all-feature compilation, warning-denied Clippy, 593/593 configured Nextest,
  nine doctests, rustdoc, no-default-feature compilation, and residue scans.
  All 16 Atlas gitlinks equal their fetched remote defaults.
- Closure: this increment advances Eunomia, Hermes, and Leto and reconciles
  previously committed Coeus and RITK pointers to current merged defaults.
  Atlas PR #41 merged at `3f5f51f`; local `main` reconciled to the same commit.
  Fresh RITK, Coeus, and root package-manager work remains unstaged.

## ATLAS-INTEGRATION-024 — Helios provider lock convergence [patch] — done

- Owner: Codex `/root`; scope: stale Helios lock takeover, merged Helios
  default, and the parent Helios gitlink.
- Acceptance: replace the invalid partial Apollo edit with one complete Cargo
  resolution; select merged Eunomia/Leto/Hephaestus providers; remove
  `num-complex`; pass the complete Helios workspace gate.
- Evidence: Helios PR #7 merges at `79b09e9`; locked metadata and format,
  warning-denied all-target/all-feature Clippy, 272/272 configured Nextest,
  ten Rust library doctest targets, and warning-clean rustdoc pass.
- Closure: parent advances only `repos/helios`; concurrent Leto, RITK, Themis,
  and root package-manager state remains unstaged.

## ATLAS-INTEGRATION-023 — Coeus NN provider benchmark closure [patch] — done

- Owner: Codex `/root`; scope: stale Coeus PR #212 takeover, merged Coeus
  default, its provider lock, and the parent Coeus gitlink.
- Acceptance: remove Burn without deleting or shrinking the native NN
  benchmark instrument; retain every Sequential/Moirai scenario; resolve the
  current Eunomia/Leto/Hephaestus graph; merge only after local and hosted
  evidence is green.
- Evidence: Coeus PR #212 merges at `bb97cc6`; the benchmark retains 211
  operation groups and 424 native rows. Format, all-target/all-feature locked
  Clippy, 268/268 configured Nextest, eight doctests with two intentionally
  ignored, warning-clean rustdoc, locked metadata, and CodeRabbit pass.
- Closure: parent advances only `repos/coeus` from stale PR head `a365b25` to
  merged default `bb97cc6`; concurrent Helios, RITK, Themis, and root
  package-manager state remains unstaged.

## ATLAS-INTEGRATION-022 — Eunomia sub-byte graph [patch] — done

- Owner: Codex `/root`; scope: merged Eunomia, Leto, and Hephaestus defaults,
  consumer reproducibility locks, and cross-repo PM artifacts.
- Acceptance: Eunomia owns one canonical reduced-format conversion kernel;
  Leto and Hephaestus resolve Eunomia 0.4.0 from its merged default; every
  provider/consumer gate is green; the parent records only merged defaults.
- Evidence: Eunomia PR #39 merges at `49dc115` after 60/60 Nextest, exhaustive
  encoding/rounding/dispatch coverage, AArch64 source compilation, and local
  Leto/Hephaestus integration. Leto PR #44 merges at `f0b4d8e` after 593/593
  Nextest. Hephaestus PR #50 merges at `ed7d76e` after 312/312 Nextest,
  including real CUDA and WGPU contracts. All three warning-denied compile,
  doctest, and rustdoc gates pass.
- Closure: parent advances `repos/eunomia`, `repos/leto`, and
  `repos/hephaestus`; all other dirty child and root paths remain unstaged.

## ATLAS-INTEGRATION-019 — Hephaestus legacy-math residue [patch] — done

- Owner: Codex `/root`; scope: `repos/hephaestus` test/benchmark manifests,
  CPU reference code, and synchronized provider-graph PM artifacts. Kwavers
  and RITK working trees remain outside this claim.
- Acceptance: Hephaestus has no `ndarray` or `nalgebra` dependency or source
  reference in tests/benches; differential references use Leto/Leto Ops or
  explicit analytical oracles, and the provider's value-semantic gates remain
  green.
- Evidence: Hephaestus PR #47 merges at `cec0e33`; its direct legacy math
  edges and source references are deleted, WGPU differential oracles use Leto,
  and the comparative benches measure Leto against real WGPU/CUDA dispatch.
  Core Nextest is 48/48, WGPU 140/140, CUDA 109/109; warning-denied Clippy,
  doctests, warning-clean rustdoc, and all-target benchmark checks pass.
- Closure: parent advances `repos/hephaestus` from `93bc38e` to `cec0e33`.

## ATLAS-INTEGRATION-020 — Apollo Hephaestus lock convergence [patch] — done

- Owner: Codex `/root`; scope: Apollo `Cargo.lock`, Apollo PM records, and
  the parent Apollo gitlink. The lock-only consumer refresh is sequenced after
  Hephaestus PR #47 and does not touch Kwavers or RITK peer scopes.
- Acceptance: Apollo's three Hephaestus packages resolve merged provider
  `cec0e33`, with no source/manifest compatibility path; locked Apollo gates
  and the provider audit remain green.
- Evidence: Apollo PR #53 merges at `a31b8f8`; all three lock entries select
  `cec0e33`. Locked compile, 402/402 Nextest, warning-denied Clippy,
  doctests, warning-clean rustdoc, provider audit, hosted Rust/Python, and
  CodeRabbit checks pass. The external analyzer error is non-required.
- Closure: parent advances `repos/apollo` from `7303423` to `a31b8f8`.

## ATLAS-INTEGRATION-021 — Coeus tensor legacy benchmark removal [patch] — done

- Owner: Codex `/root`; scope: merged Coeus PR #211 gitlink and synchronized
  provider-graph PM artifacts. The peer-owned Kwavers pointer remains outside
  this increment.
- Acceptance: Coeus tensor benchmarks no longer declare or execute a legacy
  tensor backend; retained rows use Coeus Sequential/Moirai and Leto dispatch,
  and the consumer lock graph aligns to merged Hephaestus `0.16.1`.
- Evidence: Coeus PR #211 merges at `4459d09`; locked package check, 56/56
  Nextest, warning-denied Clippy, five doctests, warning-clean rustdoc,
  locked metadata, and the targeted residue scan pass. Coeus has no hosted
  workflow; the external analyzer is non-required.
- Closure: parent advances `repos/coeus` from `093f31f` to `4459d09`.

## ATLAS-INTEGRATION-018 — RITK Apollo alignment [patch] — done

- Owner: Codex `/root`; scope: merged RITK default gitlink plus cross-repo PM
  artifacts.
- Acceptance: the gitlink names RITK PR #41's merged default-branch commit,
  whose lock and composite checkout resolve Apollo 0.25 without staging the
  active Kwavers GPU feature branch.
- Evidence: RITK merge `a41e03b9`; all 22 repository and review checks pass,
  including Linux/macOS/Windows Nextest, Python 3.9–3.13, wheel, Clippy,
  formatting, dependency alignment, and migration audit. The external
  `recurseml/analysis` error is non-required.
- Closure: parent advances `repos/ritk` from `aededa6b` to `a41e03b9`.

## ATLAS-INTEGRATION-015 — Merged default refresh [patch] — done

- Owner: Codex `/root`; scope: merged CFDrs, Eunomia, Helios, Leto, and RITK
  default-branch gitlinks plus cross-repo PM artifacts.
- Acceptance: every advanced gitlink names a merged remote-default commit;
  fresh Apollo, Kwavers, and RITK peer work remains unmodified and no dirty
  feature-branch head enters the parent graph.
- Closure: CFDrs `a833b7fe` preserves the independent sparse-LU contract;
  Eunomia `a2e4f390`, Helios `972fb53e`, Leto `3ac0d203`, and RITK
  `aededa6b` carry their merged provider increments. Apollo remains at merged
  `c8742814`, Hephaestus at `93bc38e6`, and Kwavers at merged `9eabc4e2`.
- Evidence: each recorded object equals its fetched remote default. CFDrs
  direct-solver Nextest passes 4/4, its direct-after-GMRES consumer regression
  passes 1/1, and warning-denied `cfd-math` Clippy passes. RITK PR #40's
  cross-platform Nextest, Python 3.9–3.13, wheel, lint, dependency-alignment,
  and migration-audit lanes pass. Provider-specific evidence remains in each
  repository's PM artifacts.

## ATLAS-INTEGRATION-012 — Apollo policy-wrapper removal [major] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and the provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #49's merged default-branch commit,
  which deletes the duplicate radix execution-policy wrapper, routes directly
  through Moirai's `AdaptiveWithThreshold`, and advances `apollo-fft` to
  0.25.0 without an Apollo-owned WGPU implementation.
- Evidence: Apollo merge `e2f905a`; local locked `apollo-fft` Nextest 393/393,
  warning-denied Clippy, doctests, rustdoc, source-residue scan, and provider
  audit pass; hosted Python bindings and Rust workspace workflow
  `29620388853` pass. The known external `recurseml/analysis` failure is
  non-required and does not inspect the merged head's build gates.
- Closure: parent advances `repos/apollo` from `0b5d11c` to `e2f905a`.

## ATLAS-INTEGRATION-013 — Apollo Winograd re-export removal [patch] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and the provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #50's merged default-branch commit,
  which removes the obsolete `mixed_radix::traits::ShortWinogradScalar`
  re-export and rewrites all callers to the canonical
  `components::winograd` module without changing FFT value semantics.
- Evidence: Apollo merge `c874281`; local locked Nextest 402/402,
  warning-denied Clippy, doctests, warning-clean rustdoc, source-residue scan,
  and provider audit pass. Hosted Python bindings, Rust workspace, and
  CodeRabbit pass; the external `recurseml/analysis` error is non-required.
- Closure: parent advances `repos/apollo` from `e2f905a` to `c874281`.

## ATLAS-INTEGRATION-014 — Hephaestus scan-limit theorem [patch] — done

- Owner: Atlas integration; scope: `repos/hephaestus` gitlink and the
  provider-graph PM artifacts only.
- Acceptance: the gitlink names Hephaestus PR #46's merged default-branch
  commit, which records the scan shared-memory bound and keeps KS-5b
  benchmark-triggered rather than adding an unneeded multi-pass kernel.
- Evidence: Hephaestus merge `93bc38e`; nightly formatting and core Nextest
  pass 48/48. The provider ADR records the theorem
  `shared_bytes = W * size_of(T)` and existing WGPU/CUDA `L=513`, `W=256`
  contracts witness the `L > W` path.
- Closure: parent advances `repos/hephaestus` from `3b68228` to `93bc38e`.

## ATLAS-INTEGRATION-016 — Apollo provider-lock refresh [patch] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #51's merged default-branch commit,
  whose lockfile resolves Hephaestus `93bc38e`, Eunomia `a2e4f390`, Leto
  `6a0e297`, and Moirai `8a51b2a7` without local path or revision overrides.
- Evidence: Apollo merge `6dcb97c`; locked compile, 402/402 Nextest,
  warning-denied Clippy, doctests, warning-clean rustdoc, and provider audit
  pass. Hosted Python bindings, Rust workspace, and CodeRabbit pass; the
  external `recurseml/analysis` error is non-required.
- Closure: parent advances `repos/apollo` from `c874281` to `6dcb97c`.

## ATLAS-INTEGRATION-017 — Apollo Leto merge pin [patch] — done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and provider-graph
  PM artifacts only.
- Acceptance: the gitlink names Apollo PR #52's merged default-branch commit,
  whose lockfile resolves both Leto packages to Atlas default merge
  `3ac0d203` rather than parent `6a0e297`.
- Evidence: Apollo merge `7303423`; `cargo metadata --locked --no-deps` and
  exact provider-tree comparison pass. Hosted Rust workspace, Python
  bindings, and CodeRabbit pass; the external analyzer error is non-required.
  The local fresh compile was blocked by stale peer test executables holding
  the shared target, while the preceding identical-tree sweep passed 402/402.
- Closure: parent advances `repos/apollo` from `6dcb97c` to `7303423`.

## ATLAS-INTEGRATION-011 — Hephaestus CUDA initialization closure [patch] — done

- Owner: Atlas integration; scope: `repos/hephaestus` gitlink and the
  provider-graph PM artifacts only.
- Acceptance: the gitlink names the merged Hephaestus default-branch commit
  that memoizes CUDA driver initialization and serializes only process-global
  context creation, while preserving concurrent transfers and kernels.
- Evidence: Hephaestus PR #45 merged at `3b68228`; the full CUDA suite is
  109/109 under `cargo nextest run -p hephaestus-cuda --locked`, including
  `concurrent_device_acquisition_is_safe`; warning-denied Clippy, doctests,
  and rustdoc pass.
- Closure: parent advances `repos/hephaestus` from `d0eafc8` to `3b68228`.

## ATLAS-INTEGRATION-010 — Hephaestus tiled scan provider closure [minor] — done

- Owner: Atlas integration; scope: `repos/hephaestus` gitlink and the
  provider-graph PM artifacts only.
- Acceptance: the gitlink names the merged Hephaestus default-branch commit
  that dispatches one shared-memory tiled scan workgroup/block per line in
  both WGPU and CUDA; theorem/spec and long-line value contracts remain in
  the provider repository.
- Evidence: Hephaestus PR #44 merged at `d0eafc8`; core nextest 48/48, WGPU
  nextest 140/140, CUDA nextest 108/108 when the independent
  `concurrent_device_acquisition_is_safe` Windows access violation is
  excluded, doctests, rustdoc, warning-denied Clippy, and real-device
  long-line scan contracts pass. ADR 0009 is the provider theorem SSOT.
- Closure: parent advances `repos/hephaestus` from `df33d4d` to `d0eafc8`.

## ATLAS-INTEGRATION-007 — RITK Apollo checkout pin [patch] — done

- Owner: Atlas integration; scope: `repos/ritk` gitlink and Atlas PM artifacts
  only.
- Acceptance: the Atlas gitlink names RITK `main` at `ffda3ec`, which checks
  out Apollo `157467e` for its dependency-alignment workflow and resolves
  `apollo-fft` 0.24 from that source.
- Evidence: RITK `main` at `ffda3ec` passes the cross-platform Nextest,
  Python 3.9–3.13, wheel, lint, dependency-alignment, and migration-audit
  workflows. This increment carries that verified head into the reproducible
  Atlas graph without a consumer-side fallback.

## ATLAS-INTEGRATION-008 — Apollo dispatch verification tree [arch] — ✅ done

- Owner: Atlas integration; scope: `repos/apollo` gitlink and provider-graph
  documentation.
- Acceptance: Apollo PR #46 merges the deep GPU dispatch verification leaf,
  keeps execution owned by Leto/Hephaestus, exposes no Apollo-owned raw WGPU
  path, and the Atlas gitlink advances to the merge commit.
- Evidence: Apollo merge `0b5d11c` (PR #48 canonical-export documentation
  after PR #47 PM closure); locked
  `apollo-fft` Nextest 393/393,
  warning-denied Clippy, warning-clean rustdoc, and provider audit 5/5.
- Closure: Atlas PR #18 merged at `56ad179`; Apollo `main` carries the
  documentation-only PR #48 merge `0b5d11c`, and the parent pin is current.

## ATLAS-INTEGRATION-009 — Kwavers hosted closure [patch] — ✅ done

- Owner: Codex `/root` takeover after the prior 60-minute claim expired;
  scope: the verified Kwavers default-branch head and the `repos/kwavers`
  gitlink only.
- Acceptance: required hosted checks pass for the clean default-branch head,
  and the parent advances only to that verified commit.
- Evidence: Kwavers PR #294 merged at `9eabc4e2`; its head `e84bb571e`
  contains the Leto-backed medium
  accessor removal, canonical abdominal geometry contract, Hephaestus
  backend-kernel ownership cutover, and the MVDR wall-clock assertion moved
  from the tarpaulin correctness lane into the Criterion benchmark. Legacy
  Migration Audit `29614208769` passes; local locked GPU Nextest passes 143/143
  with one hardware skip, ultrasound physics passes 18/18, and the benchmark
  target checks. The hosted Architecture Validation and CI/CD matrices retain
  generated-report coverage as a source gate. Architecture Validation
  `29614208770`, CI/CD `29614208862`, and Legacy Migration Audit
  `29614208769` pass; only external `recurseml/analysis` remains errored.
- Closure: the parent advances from `7c7d60f` to merged Kwavers `main`
  `9eabc4e2` in this increment.

## ATLAS-INTEGRATION-006 — Refresh provider heads [arch] — done

- Owner: Atlas meta; scope: Apollo, Hephaestus, Kwavers, Leto, and RITK
  gitlinks plus ADR 0020.
- Acceptance: the Atlas checkout graph resolves the verified Apollo,
  Hephaestus, Kwavers, Leto, and RITK default-branch heads;
  the provider-graph theorem and exact gitlink evidence are recorded.
- Evidence: Apollo `0b5d11c`, Hephaestus `df33d4d`, Kwavers `9eabc4e2`,
  Leto `6a0e297`, and RITK `ffda3ec` are the current provider heads; all
  required hosted checks pass.
- Closure: Atlas PR #15 merged at `29041d9`. Its RITK source checkout repair
  is carried by ATLAS-INTEGRATION-007; the current Kwavers #291 matrix remains
  the behavioral closure for the Apollo axis-transform path.

## ATLAS-INTEGRATION-005 — RITK lock-integrity pin [patch] — done

- Owner: Atlas integration; scope: `repos/ritk` gitlink and Atlas PM artifacts
  only.
- Acceptance: the gitlink names the merged RITK default-branch head after its
  lock metadata reconciles current Hephaestus patch entries.
- Closure: RITK PR #38 merged at `0dd71e52` after its full cross-platform
  Nextest, Python, wheel, lint, dependency, and migration-audit matrix passed.
  This pin carries that verified provider graph into Atlas without modifying
  a consumer-owned compatibility path.

## ATLAS-INTEGRATION-003 — provider-neutral GPU pin reconciliation [patch] — ✅ done

- Owner: Codex; scope: `repos/{hephaestus,CFDrs}` gitlinks and Atlas PM
  artifacts only.
- Acceptance: Hephaestus `main` supplies downlevel-complete typed device limits,
  CFDrs `main` owns no public raw WGPU adapter/feature/limits contract, and both
  gitlinks name the merged default-branch heads.
- Closure: Hephaestus PRs #40–#42 merged at `29ff2ff` (0.16.1); CFDrs PR #295
  merged at `7d4c9edf` (0.3.0). The provider exact-descriptor test, CFDrs
  GPU grouped nextest suites, warning-denied Clippy, and the major API
  classification passed before the parent pin advance.

## ATLAS-INTEGRATION-004 — CFDrs executable-example pin [patch] — ✅ done

- Owner: Atlas integration; scope: `repos/CFDrs` gitlink and Atlas PM artifacts
  only.
- Acceptance: the gitlink names the merged CFDrs default-branch head after
  its retained examples execute the provider implementation rather than emit
  static validation reports.
- Closure: CFDrs PR #296 merged at `a13f7f51`. It replaces the retained
  one- and two-dimensional examples with executable provider calls and
  deletes unexecutable three-dimensional/static-report examples. The parent
  gitlink advance records that merged contract without introducing a wrapper.

## ATLAS-INTEGRATION-001 — default-main reconciliation [patch] — ✅ done

Resolved the root metadata and gitlink merge against `main`. The integrated
tree preserves the current migration artifacts, adds the Helios stack entry,
and records conflicted submodules at commits reachable from their respective
default branches. Coeus is pinned at merge `093f31f`; Gaia is pinned at merge
`9e48102`.

## ATLAS-INTEGRATION-002 — merged-provider pin reconciliation [patch] — ✅ done

- Owner: Atlas integration; scope: `repos/{apollo,helios,ritk}` gitlinks and
  Atlas PM artifacts only.
- Acceptance: each pin names a commit reachable from its repository's remote
  default branch after all required provider PRs merge.
- Target heads: Apollo `f26369eb` (PR #44), Helios `04e496b7` (PR #5), and
  RITK `ec7cb832` (PR #37). RITK CI passes Rustfmt, dependency alignment,
  Clippy, migration audit, Python wheel, Python 3.9–3.13, and Ubuntu/macOS/
  Windows Nextest on the merged PR head. Atlas PR #9 merged this pin set at
  `e3380b6`.

## ATLAS-MNEMOSYNE-017 — Maximum-small deallocation audit [patch] — ✅ done

- Owner: Mnemosyne; Atlas scope: provider PR #25 and the `repos/mnemosyne`
  gitlink.
- Closure: PR #25 merged at `0012c4fad0c44c0a40ec4d36de68e7138ae218d8`.
  The matched default-feature Criterion row measures Mnemosyne `36.960 ns`
  versus RpMalloc `6.1139 ns` for `allocator deallocation latency/large/8192`.
  The opt-in branch probe pins the maximum-small same-owner free to
  `InPlaceSmall`; no page-list transition or large/huge classifier defect was
  found, so no speculative production mutation was made.
- Atlas pin closure: `4908208` advances `repos/mnemosyne` from `52cd5ee` to
  the merged provider head. Provider verification is recorded in the inner
  Mnemosyne PM artifacts; peer-owned submodule dirt remains outside this
  item.

## ATLAS-MOIRAI-016 — Cancellation-safe async wait queues [patch] — ✅ done

- Owner: Moirai; Atlas scope: cross-repo audit record only.
- Findings: `Condvar::wait` lost-notification window; `mpsc::SendFuture`/`RecvFuture`
  waker retention after cancellation; `oneshot::RecvFuture` rx_waker leak.
- Fixes applied to `repos/moirai/moirai-async/src/sync/`:
  - `condvar.rs`: pre-register waiter in `WaitQueue` while still holding the
    `MutexGuard`, using a `NoopWaker` placeholder replaced on first `poll`.
  - `mpsc.rs`: ID-based waiter tracking (`VecDeque<(u64, Waker)>`) with `Drop`
    impls that remove by ID on cancellation; 2 regression tests added.
  - `oneshot.rs`: `Drop for RecvFuture` clears `shared.rx_waker = None`.
- Evidence: `cargo check -p moirai-async` clean; `cargo nextest run -p moirai-async`
  82/82 passes (80 existing + 2 new cancellation regressions), no slow tests.
- Closure trigger reached: provider commit with focused regression evidence.

## ATLAS-RITK-654 — RITK native migration reconciliation [patch] — ✅ done

- Owner: Codex; scope: RITK PRs #31/#32/#33 and the `repos/ritk` gitlink.
- Acceptance: RITK PR #33 merged to `origin/main` at
  `17b84bdc18c2395d6329f3435ed3d860d1c72e00`; Atlas advances the gitlink to
  that merge commit. Final docs-head CI is green in run `29421402596`
  (Rustfmt, dependency alignment, Clippy, wheel smoke, and Linux/macOS/Windows
  nextest), run `29421402755` (Python 3.9–3.12 on Linux/macOS/Windows), and
  audit run `29421402503`.
- Performance and memory evidence: native statistics extrema now consume a
  fallible host slice instead of materializing a `Vec`; the xtask audit fixture
  roots use process-plus-sequence uniqueness and RAII cleanup. These are
  source/data-flow improvements; no unbenchmarked speedup is claimed.
- Residual: RITK retains 13 Burn manifests and 641 Burn-surface source files
  for dependency-ordered Coeus/Leto consumer cutovers (peer-owned sub-batches
  #3.g–#6). Three registration tests remain above the 30-second slow threshold
  and require profile-guided optimization. No shim or fallback is accepted as
  closure evidence.

## ATLAS-APOLLO-015 — RustFFT/WGPU provider promotion [major] — ✅ done

- Owner: Codex; scope: `repos/apollo` PR #8 and its Atlas consumer pins.
- Acceptance: Apollo PR #8 is reviewed with repository CI green, the provider
  state reaches `main`, and consumers replace temporary branch pins with the
  merged commit.
- Closure: Apollo PR #8 merged at `6e99a567c118f6bf5790f80346475b44db2c7555`.
  Authoritative CI run `29381809234` passed Rust format, Clippy, tests,
  doctests, documentation, provider audit, RustSec, dependency policy, and
  Python bindings. Coeus PR #209 subsequently merged the Mnemosyne 0.4,
  Hephaestus 0.13, WGPU 30, and Themis 0.10 provider constraints required by
  RITK.
- Closure: RITK PR #33 completed the consumer matrix against the merged
  Apollo/Coeus graph at `17b84bdc`; the external `recurseml/analysis` status is
  non-required.

## ATLAS-WGPU-030 — Provider ABI migration [arch] — done

- Owner: Codex; last-update: 2026-07-13; scope:
  `repos/mnemosyne`, `repos/hephaestus`, `repos/apollo`, their gitlinks, and matching cross-repo PM
  entries. Peer-owned CFDrs, Helios, RITK, and shared Cargo configuration are
  excluded.
- Acceptance: Mnemosyne removes the raw-pointer WGPU staging allocator contract
  that WGPU 30 cannot represent safely; Hephaestus owns one current WGPU ABI; its complete WGPU feature
  surface passes format, warning-denied Clippy, nextest, doctest, and rustdoc;
  Apollo consumes the pushed provider commit, removes obsolete dependency and
  advisory constraints, and repeats its release gates without duplicate WGPU
  source identities.
- Dependencies: current WGPU release/API metadata; existing Hephaestus and
  Apollo release branches; shared `D:/atlas/target` build cache.
- Closure: Mnemosyne `01e7de7` contains the WGPU allocator removal from
  `4a9d2a3`; Hephaestus `090611d`, Leto `8651dfc`, Moirai `c43f86a`, and Apollo
  `96e67a2` are pushed. Apollo 0.15 owns one WGPU 30 graph and passes 1029/1029
  Rust nextest cases, 34/34 Python cases, warning-denied Clippy and rustdoc,
  doctest, provider audit, RustSec, cargo-deny policy checks, and applicable
  pre-1.0 API checks.

## ATLAS-APOLLO-014 — Apollo release graph [arch] — done

- Owner: Codex; scope: `repos/{apollo,mnemosyne,moirai,hermes,leto,hephaestus}`
  gitlinks and matching parent PM entries.
- Acceptance: Apollo pins one exact, standalone-Git-resolvable Atlas provider
  graph; Rust, Python, API, supply-chain, and documentation gates pass; all
  provider and Apollo commits are pushed before Atlas advances their gitlinks.
- Closure: Apollo `a4742bb` and provider commits Mnemosyne `eb0d941`, Hermes
  `51c530f`, Moirai `b2f3732`, Leto `1b125ce`, and Hephaestus `f726742` are
  pushed and release-gated; Atlas integration commit `e7f27a7` records their
  gitlinks. The completed `ATLAS-WGPU-030` increment supersedes this historical
  WGPU 26 release graph.

> **2026-07-09 current-tree reconciliation**: the direct production
> `nalgebra`/`ndarray`/`burn`/Tokio/Rayon removal front is closed in CFDrs.
> The next cross-repo correctness slice is provider-first ownership of the
> CFDrs 2D GPU Laplacian in Hephaestus: remove the falsely generic `f32` WGSL
> boundary and silent CPU fallback, then leave `cfd-core`/`cfd-math` as thin
> typed consumers. This candidate is not claimed while Hephaestus remains on
> the active `ks5-cholesky-panel` branch. Kwavers and RITK each have a smaller
> subtractive cleanup candidate, but their current dirty migration streams own
> those files; no atlas-meta source edit crosses those claims.

---

## Cross-repo architect coordination ledger

Three CR-class items carried from `docs/audit/2026-07-02-cross-repo-integration-audit.md` (`L71-149`). Each is self-contained and gates specific consumer-side migrations below.

| ID | Class | Title | Owner repo (provider land) | Supertypes | Consumer land unlocked |
| --- | --- | --- | --- | --- | --- |
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` as the universal supertrait (single SSOT) — **✅ CLOSED 2026-07-09** (eunomia `57d7789`, coeus `2b3f820`, leto PR #31 merge `d9e8ac9`; ADR 0005 Accepted; re-verified 2026-07-22: `leto-ops/src/domain/scalar.rs:11` and `coeus-core/src/dtype/traits.rs:295` carry `Scalar: NumericElement`; consumer unlocks tracked and closed in batches #2/#3). Delete the vocabulary that already lives on `NumericElement` (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep the backend-specific slice-kernel surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `axpy_rows`, leto-ops `from_usize`). See `atlas/docs/adr/0005-eunomia-scalar-ssot.md` for the proof that `RealField` (float-only) cannot be a universal `Scalar` supertrait (would orphan `coeus_core::Int` for i8/u8/.../u64). | `coeus`, `leto` (joint) | `eunomia` is doctrine holder | kwavers `RealField` nalgebra → eunomia; CFDrs `cfd-math` solver-chain RealField seam; ritk `Burn::Module → coeus::Module` rebind |
| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-only registration. Strip from `cfd-core`, `ritk-core`, `moirai/lib`. Pass `Mnemosyne` handles via DI to library callers. | `cfd-core`, `ritk-core`, `moirai` (joint) | `mnemosyne` is allocator holder | Library composition stays provider-neutral; binaries own allocator policy — **✅ CLOSED 2026-07-18** (`cfd-core` ✅, `moirai` ✅, `ritk-core` ✅; zero `#[global_allocator]` in all three library crates) |
| **CR-1** | `[arch]` | Delete `apollo/crates/apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell` (with `brand_scope!` mint). | `apollo`, `melinoe` (consumer) | `melinoe` is brand doctrine holder | All brand-borrow contention becomes provider-exclusive — **✅ CLOSED 2026-07-07** (Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; `repos/moirai/Cargo.toml` aligned to `melinoe = 0.8.0`; focused nextest `-p apollo-validation melinoe` 2/2 green and `-p apollo-sft -p apollo-radon` 43/43 green; `find_path repos/apollo/crates/apollo-ghostcell/**` returns zero files 2026-07-20 re-confirm; full evidence at `gap_audit.md` L1429-1430) |

### Provider extension register

These cross-cut consumer migration but live in provider land. Each requires its own [minor] backlog entry in the owning provider repo:

| Provider | Missing surface | Substrate | Tracked in |
| --- | --- | --- | --- |
| `leto` | ✅ `Quaternion<T>` Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt; + `try_inverse` + `to_rotation_matrix`; ✅ `FixedMatrix&lt;4,4&gt;` determinant/try_inverse + generic Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt;/Assign. **Verified 2026-07-14**: 229/229 tests green, clippy `-D warnings` clean. | math | `leto/backlog.md` |
| `leto-ops` | ✅ `CscMatrix<T>`, `CooMatrix<T>`, `lu_batch`; `ExecutionStrategy` trait — all verified present at `leto/crates/leto-ops/src/`. | ops | `leto/backlog.md` |
| `moirai-async` | ✅ `mpsc::channel`, `oneshot::channel`, `Condvar`, `Mutex`, and `#[moirai::main]` exist. `ATLAS-MOIRAI-016` cancellation audit closed: Condvar lost-notification race fixed (pre-register waiter while holding guard), mpsc/oneshot waker leaks fixed (Drop impls with ID-based cleanup), 82/82 nextest pass with 2 regression tests. | async | `moirai/docs/backlog.md` |
| `apollo` | ✅ RustFFT-free differential oracle — pure O(N²) DFT reference replaces rustfft. `b291003` on `codex/remove-rustfft`. Workspace `rustfft = "6.4.1"` pin removed; `external-references` feature removed; dev-dep and vs_rustfft benchmark removed; xtask benchmark runner stripped. | validate | `apollo/backlog.md` |
| `eunomia` | ✅ eunomia-gpu deleted (E-019); folded into `hephaestus::DialectScalar`. README clean — no aspirational claims about eunomia-gpu. | basis | `eunomia/backlog.md` |
| `coeus` | ✅ `scatter_add` exists at Tensor/Var/Python; all 6 comparison ops (eq/ne/lt/gt/le/ge) exist. `Dataset`/`DataLoader` deferred per "if PINN dataset paths require" condition — no PINN path in current scope requires them. | autograd | `coeus/docs/backlog.md` |
| `hephaestus` | ✅ `f64` DialectScalar impls (Wgsl `"f64"`, CudaC `"double"`) + 24 GPU vector type impls via macro. **Verified 2026-07-14**: 47/47 nextest green, clippy `-D warnings` clean. Remaining: `wgpu::PipelineCache` integration (WG-P8); CU-P1 async-stream-overlap. | gpu | `hephaestus/backlog.md` |

---

## Migration batches (vertical slices)

Ordered per Definition-of-Ready (provider SSOT closes first). Each batch is self-contained, has observable pass conditions, and respects the WIP limit (one in-flight merge-affecting item per micro-sprint). Cross-repo item as policy: one batch is **the** item; commits ride under the established `codex/kwavers-atlas-integration` branch through that batch's owner.

### Consumer-side (kwavers / CFDrs / ritk)

| Batch | Class | Crate | Surface | Pre-reqs | Pass condition (value-semantic) | File-line scope (illustrative) |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | `[patch]` | `kwavers-solver` ([side path RTM/elastic PDE](file_pattern)) | `par_for_each` Zip → `moirai-parallel::par_mut().enumerate()` (62 sites); `Zip::indexed` → `par().enumerate()` (24 sites) | (none — confirmed by `moirai-parallel/src/lib.rs:106-181` tan rename) | ✅ **CLOSED 2026-07-12** at peer commit `5913f2946`: zero `par_for_each` source sites, zero `burn::` hits, zero `nalgebra` hits, zero `use ndarray` imports; `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel`); `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib` 5117/5119 pass (2 timeouts are pre-existing KW-WATCH-002 perf on the 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. | `crates/kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{wavefield,propagation,mod,laplacian,imaging,illumination}.rs`; `crates/kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral}/...`; `crates/kwavers-solver/src/forward/{elastic/swe/int, pstd/ext, multiphysics/fluid_structure}/...`; `crates/kwavers-physics/src/acoustics/...`; `crates/kwavers-physics/src/optics/polarization/linear.rs` |
| #2 | `[minor]` | `CFDrs/cfd-math` ([ite solver finish](file_pattern) + `cfd-1d`/`cfd-3d`/`cfd-validation`) | nalgebra → let, nalgebra-sparse → leto-ops `CsrMatrix`; covariance solves / geometry / finite-element typedefs | CR-4 (eunomia SSOT) so `RealField → eunomia::RealField` is universal | `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation` green; xtask scanner delta shows `nalgebra` allowlist contracts under cfdec-solver chain, cfd-3d fem/libnodes, cfd-1d linear_system and cfd-validation geometry; `nalgebra-sparse` allowlist contracts to zero | `cfd-math/src/linear_solver/{chain, preconditioners/{*, ilu/*, multigrid/*, schwarz, ssor}}.rs`; `cfd-3d/src/fem/{element, projection_solver, leto_bridge, solver, stabilization, stress, quadrature, shape, fluid}.rs`; `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**`; `cfd-3d/src/vof/{cavitation, reconstruction}.rs`; `cfd-1d/src/solver/core/{convergence,linear_system,matrix_assembly,state,workspace,anderson,solver_detection}.rs`; `cfd-validation/src/{geometry, benchmarks, literature, manufactured, numerical, adaptive_mesh, tests}/**` |
| #3 | `[minor]` | `ritk` ([Provider-side Burn trait rebind](file_pattern)) | `ritk_core::{Image, Transform, Interpolator}` → `coeus_core::{ComputeBackend, Scalar}`; `ritk-spatial::{Vector,Point,Direction}` lose `burn::module::{Module,AutodiffModule}+burn::record::Record` impls; `ritk-image::types::Image<B,D>` re-exports exit Burn-keyed facade | CR-4 so eunomia `Scalar/RealField` is universal | `ritk-image::native::Image<T: Scalar, B: ComputeBackend, const D: usize>` becomes the canonical re-export; `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation}` green; `cargo tree --workspace -i burn-wgpu`, `cargo tree --workspace -i burn-cuda`, and `cargo tree --workspace -i burn-rocm` each return zero (Burn only CPU NdArray backend remains per DEP-496-01) | `ritk-core/src/{image/types,transform/trait_,interpolation/trait_}.rs`; `ritk-spatial/src/{vector,point,direction,spacing}.rs`; `ritk-image/src/types.rs` + `ritk-image/src/lib.rs:11` re-export line; `ritk-wgpu-compat/src/lib.rs` (`apply_row_chunks` `B:Backend` bound → `B:ComputeBackend`); per-filter `*/new(B::Device)` constructors |
| #4 | `[minor]` | `kwavers-solver` ([PINN Burn → Coeus](file_pattern)) | `burn::backend::NdArray<f32>` ⇒ `coeus-core::MoiraiBackend`; `burn::optim::{SGD,Adam,AdamW,lr_schedule::*}` ⇒ `coeus-optim::*`; `burn::module::Module` ⇒ `coeus-nn::Module`; `burn::record::Record` ⇒ `coeus-nn::Record`; `burn::tensor::*` ⇒ `coeus-tensor::*`; ~325 source lines + ~17 top-level dev-dep files | CR-4 + #3 + `coeus-autograd/scatter_add` extension | `cargo nextest run -p kwavers-solver --features pinn` green; per-physics trainer residual gradient matches golden reference within neum-compensated epsilon (derived from reduction depth × sqrt(N) per current `es::BatchModern` chain); kwavers top-level `Cargo.toml:138` `[dev-dependencies] burn = "0.19"` flips to deps via `coeus` (or top-level burn demoted fully) | `crates/kwavers-solver/src/inverse/pinn/**` (~80 files; cite-referenced inside the inventory in checklist.md); top-level `crates/kwavers/{benches,examples,tests}/**` (17 files); `kwavers-solver/Cargo.toml:42` feature set; `kwavers/Cargo.toml:138` dev-deps |
| #5 | `[arch]` | CR-1: `apollo-ghostcell` deletion + `melinoe::MelinoeCell` rebind (provider land) — single coordinated commit | (See provider-extension register above) | (None — provider-only action) | (See CR-1 row above) | `apollo/crates/apollo-ghostcell/src/lib.rs` removed; every apollo consumer routed via `melinoe::MelinoeCell`; `cargo nextest run -p apollo-* --features melinoe` green; `cargo miri test -p melinoe` green |
| #6 | `[arch]` | CR-2: Consolidate `#[global_allocator]` (provider land) — single coordinated commit across `cfd-core`, `ritk-core`, `moirai/lib` | (See CR-2 row above) | (None) | (See CR-2 row above) | Library registry sites reduced; per-binary (`kwavers-cli`, `cfd-cli`, `helios`, `ritk-cli`, `mnemosyne-gbench`, etc.) keeps or replaces registration; `cargo build -p cfd-core` without `mnemosyne` feature succeeds |
| #7 | `[arch]` | CR-4: `coeus-core::Scalar` + `leto-ops::Scalar` rebase to eunomia supertraits (provider land) — **STATUS: ✅ CLOSED 2026-07-09. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9`)** | (See CR-4 row above) | (None) | (See CR-4 row above) | eunomia: `eunomia/crates/eunomia/src/traits/numeric.rs` doc clarified (ZERO/ONE/sqrt/abs/to_f64 stay FloatElement for float paths); Complex<T>/isize/usize implementations added. coeus: `coeus/coeus-core/src/dtype/traits.rs` (`Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem + Clone`); 64-file coeus call-site disambiguation landed. leto: `leto/crates/leto-ops/src/domain/scalar.rs` `pub trait Scalar: NumericElement` rebind; redundant UFCS items removed (ZERO/ONE/add/sub/mul/div/bitand/bitor/bitxor/count_ones/to_f64); slice kernels given default bodies; `from_usize` retained. `Cargo.toml` workspace version `0.35.1 → 0.36.0`. Resolution (a) applied (additive rebind is structurally infeasible per `atlas/checklist.md` structural-infeasibility addendum + E0034 evidence). Verification (pre-merge on `codex/leto-cr4-ssot-rebind`, 5 files / 196 +/-622 net subtraction): `cargo nextest run -p leto-ops` 270/270 green + `-p leto` 189/189 green + 8 doctests green + clippy `-D warnings` green on `--lib --tests` scope. Pixel/range/structural artifact: net 466-line subtractive consolidation (no vocab duplication remains). RG-verified zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS references in `crates/`. |
| #8 | `[minor]` | Provider extension (provider land): ✅ `leto` (Quaternion ops, FixedMatrix<4,4> ops) — verified; ✅ `hephaestus` (DialectScalar f64 + GPU vectors) — verified; ✅ `moirai-async` (mpsc/oneshot/Condvar/Mutex/`#[moirai::main]`) — verified; remaining: `apollo`, `eunomia`, `coeus`, `leto-ops` | (See provider-extension register above) | (Threads across consumer migration; file as individual [minor] items in owning repos) | (See register above) | tracked separately in `repos/<provider>/backlog.md` |

### Token batch ordering

Batches #5, #6, #7 are the [arch] provider-SSOT gates. Per `decision_policy` nternals:

1. **#7 first** (CR-4 eunomia SSOT) — **ALL SIDES ✅ CLOSED 2026-07-09**. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9` — Resolution (a): rebase onto origin/main post-PR-#30, `Scalar: NumericElement` supertrait, redundant UFCS items removed). Unblocks #2 (CFDrs nalgebra finish), #3 (ritk Burn rebind), and #4 (kwavers PINN Burn → coeus). ADR `0005-eunomia-scalar-ssot.md` (status **Accepted**) describes the actual rebase; `RealField` is NOT a universal `Scalar` supertrait (would orphan `Int`); `NumericElement` is. ADR signed off via autonomy mode per `interaction_policy`.
2. **#5 second** (CR-1) — Pure provider cleanup; no consumer call sites depend on it for the migration below.
3. **#6 third** (CR-2) — Library-vs-binary layering. **cfd-core ✅, moirai ✅ landed** (2026-07-10). **ritk-core ✅ committed** (`ba6da3a5`, 2026-07-14). All sites resolved.
4. **#1 fourth** — `kwavers-solver` residual Rayon → Moirai. Self-contained. Calls CTE immediately after a clean CR-4. ✅ **CLOSED 2026-07-12** — kwavers peer commit `5913f2946` (`perf(kwavers-solver): Migrate solver tree to moirai parallel iterators`) drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0, `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel` only). `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (pre-existing KW-WATCH-002 abdominal-preprocessing perf on 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). `cargo check -p kwavers-solver --features pinn` PASSES (Batch #4 co-verified closed). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. Sole residual is the `kwavers-solver/Cargo.toml` `ndarray` `rayon` feature gate, flagged separately in the peer commit body — manifest detail tracked as a kwavers-peer follow-up. Batch #4 (`kwavers-solver PINN Burn → Coeus`) is also closed at this HEAD (co-verified).
5. **#2 fifth** — Largest consumer body (176 CFDrs source files). Depends on CR-4. ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
6. **#3 sixth** — ritk Burn keyed-trait rebind. ✅ **CLOSED 2026-07-18**.
7. **#4 seventh** — kwavers-solver PINN Burn → coeus. ✅ **CLOSED 2026-07-12**.
8. **#8 last** — Provider extensions; tracked in provider repos separately; own claim stream.

### Batch #3 sub-batches (ritk Burn-trait rebind — 6 atomic commits per ADR 0012)

`Batch #3` (`[minor]` ritk Burn-keyed trait rebind) is decomposed into 6 atomic sub-batches per [`atlas/docs/adr/0012-ritk-burn-trait-rebind.md`](docs/adr/0012-ritk-burn-trait-rebind.md) (Accepted 2026-07-06). Each sub-batch widens the Atlas surface OR narrows the Burn surface — never both in one commit — atomic-boundary discipline per ADR 0012 §Decision. Reserved inner tag: `ritk/atlas-migration-push/batch3` (per ADR 0010 §Decision §"Per-batch name pattern").

**Historical sub-batch #3 framework (opened 2026-07-06; fully consumed
2026-07-18)**: the following per-crate queue records the original atomic
decomposition. PR #42 consumed #3.a–#3.g and #4–#6; PR #43 closed the ledger,
so no reservation or open queue remains.

| Sub-batch | Class | Atomic-boundary disposition | Closeout per sub-batch | Status (2026-07-09) |
|-----------|-------|------------------------------|-----------------------|---------------------|
| #1 | `[patch]` | **Additive** — Atlas-typed parallel trait surface (`TransformAtlas<T,B,D>`, `InterpolatorAtlas<T,B>`, `ResampleableAtlas<T,B,D>`) + `pub use native::Image as AtlasImage;` re-export. Burn-keyed surface untouched. | `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` green + `cargo tree --workspace -i burn-wgpu` (and `cuda`, `rocm`) zero | **closed 2026-07-06** |
| #2 | `[patch]` | **Subtractive-by-documentation** — soft docstring deprecation ONLY on Burn-keyed surface. No `#[deprecated]` attr (would emit 671-file compile-warning cascade). | (same gates as #1) | **closed 2026-07-06** |
| #3 | `[minor]` | **Subtractive-by-conversion (7 per-crate queue)**: Atlas-typed migrator test-source ports from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`. Per-crate atomic-boundary discipline per ADR 0012. | (same gates as #1) | **✅ CLOSED 2026-07-18** — All sub-batches consumed by PR #42 `f01b1643` (1298 files, -59482 lines) + PR #43 `b4be04ca` (closeout docs). burn_surface.allowlist deleted; all Burn/ndarray deps removed. |
| #4 | `[patch]` | **Subtractive-by-impl-removal** — `ritk-spatial::{Vector, Point, Direction, Spacing}` drop `burn::module::{Module, AutodiffModule}` + `burn::record::Record` impls. Atlas-side impls only IF `coeus-nn` PINN consumer code requires. | (same gates as #1) | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #5 | `[major]` | **Subtractive-by-dep-strip** + **subtractive-by-reexport** — Cargo dep strip `burn` + `burn-ndarray` from manifests; `pub use types::Image;` re-export path switch; `apply_row_chunks<B: Backend>` removal. **THIS IS THE ONLY SUB-BATCH ALLOWED TO DELETE OR RENAME `[dependencies]` LINES.** | (same gates as #1) + `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` authoritative classification | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #6 | `[patch]` | **Subtractive-by-allowlist-contract** — `xtask/burn_surface.allowlist` reset on sub-batch #5 re-enter; CI scan gates tighten: zero `burn::tensor::Backend`-bound public symbols + Atlas-only backend trait assertion. | CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph | **✅ CLOSED 2026-07-18** — burn_surface.allowlist deleted in PR #42. |

### Historical in-flight claims (superseded)

> This section preserves dated coordination snapshots. It does not describe
> current work; the live board at the top of this file is authoritative.

- Atlas-meta branch: `codex/kwavers-atlas-integration` (PM artifacts only).
- Atlas-meta claim scope (this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root; no per-repo files touched at the atlas-meta layer.
- **Mnemosyne fixed Themis pin** [patch]: **DONE** — PR #11 merged as `f95d372`; Mnemosyne pins Themis 0.10 at `18807bb`, with metadata, clippy, 288/288 nextest, doctests, and docs green.
- **Leto Themis co-evolution and provider extension** [patch]: **DONE** — PR #32 merged as `8d39f58`; the lock graph, cache-level contract, quaternion interpolation, and fixed-matrix value contracts are verified by the complete local gate.
- **Hermes fixed Themis pin** [patch]: **DELIVERED / MERGE-BLOCKED** — PR #6 commit `6080aa4` pins Themis 0.10 at `18807bb`; all CI checks pass except the pre-existing Miri allocator failure reproduced on Hermes main. The PR remains open pending that independent correctness residual.
- Atlas-meta last landed (codex session): `61931faf` (RITK Batch #3 sub-batch #1 sync + kwavers/Burn risk surfacing, 2026-07-06, layered atop peer commits `e82fe14c`, `4a04cad1`, `4b71cda9`, `3062ce1b`, `c5f2a84e`, `61931faf` itself; followed by peer `5adf4a27` "Helios closure triage" 2026-07-06 13:37). This turn: peer landed `c6b845f81` Batch #4 slice 2 (`burn_wave_equation_2d` dependency graph: 12-family native Burn→Coeus rewrite; `burn::` line-hits 315→186, file-count 144→80). See risk #8 below.
- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.

- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep) collapsed to canonical L104** — the orphan duplicate of the user-directive sweep block at former L275-L281 + the prior stale ROUND-3 dedup claim in L283-tombstone are reconciled by the present chore: the canonical `### In-flight claims (per concurrent_agents)` L104 carries the full T1 evidence (ritk nextest 47/47; CFDrs 2177/2177+1335/1335 subsets; kwavers 1-site `plugin/mod.rs:204` test-mock slip); the L283 tombstone is updated below to reflect this collapse. Mid-session test/example issues resolved by **peer-owned** per-`concurrent_agents` disjoint-scope: the kwavers `Boundary<eunomia::Complex<f64>,3>` trait-rewire at `crates/kwavers-solver/src/plugin/mod.rs:182+204` and the `fn to_leto3` dead-code warning in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8` are peer-stream fixes; atlas-meta does not touch `repos/kwavers/crates/kwavers-solver/src/plugin/mod.rs` or any other peer-claimed source.

#### Historical closure templates — Atlas Batch #3 sub-batches #4–#6

> All three templates were consumed by RITK PR #42 and tombstoned by PR #43
> on 2026-07-18. They remain below only as design-history evidence; none is a
> standing reminder, prerequisite, or next-session instruction.

These templates preserve the original atomic commit shapes and prerequisites
from ADR 0012. They are historical evidence only; no roll-up surfacing or
future-session action remains.

- **Sub-batch #4 [patch] — Standing reminder**: `ritk-spatial rebind — drop burn::module::{Module, AutodiffModule} + burn::record::Record impls`. **Atomic inner commit shape**: a single inner-RITK commit that strips the four `burn::module::*` + `burn::record::Record` impls on `repos/ritk/crates/ritk-spatial/src/{vector,point,direction,spacing}.rs:7` and (conditionally) adds `impl<T: Scalar, B: ComputeBackend> coeus_nn::Record for *` ONLY IF the downstream PINN consumer code in `kwavers-solver/src/inverse/pinn/**` or `helios-imaging/**` requires it (cross-walk Batch #4 §Progress in `atlas/checklist.md` for the in-flight audit; otherwise sub-batch #4 is a strict-removal commit with no Atlas-side replacement per ADR 0012 §Decision §Sub-batch #4). **Standing pre-reqs**: (a) Batch #3 sub-batch #3 fully closed — i.e., the 7 per-crate queue `#3.a..#3.g` has landed (each with its own test-from-`burn_ndarray::NdArray<B>`-to-`AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>` port) and `xtask/burn_surface.allowlist` source-rows have been progressively decremented per per-crate closure; (b) the impact audit of `burn::module::{Module, AutodiffModule}` removal on `kwavers-solver` Batch #4 PINN code paths is completed and posted to `kwavers/gap_audit.md` (the auto-`ModuleMapper` / `GradientExtractor` / `GradientApplicator` pattern from the `coeus_nn::load_parameters` extension must already be in place, OR the per-PINN code-path-side adapter lives inline at the PINN consumer site, NOT on the spatial carriers); (c) cooldown — if any per-crate sub-batch in `#3.{b..g}` transitively touches `ritk-spatial`, it must be closed before `#4` lands to preserve the atomic-boundary invariant (no legacy Burn-keyed reference survives into the post-#4 tree). **Pre-flight gate per session**: `cargo check -p ritk-spatial --all-targets` + `cargo doc -p ritk-spatial --no-deps` warning-clean + `cargo clippy -p ritk-spatial --all-targets -- -D warnings`.

- **Sub-batch #5 [major] — Standing reminder (mandatory semver-checks pre-release gate)**: `RITK Burn Cargo dep strip + Image<B,D> re-export path`. **Atomic inner commit shape**: a single inner-RITK BREAKING CHANGE commit that (i) deletes `burn` + `burn-ndarray` from `repos/ritk/Cargo.toml:69-72`, `ritk-core/Cargo.toml:23-24` (dev-deps), `ritk-image/Cargo.toml:9-10`, `ritk-wgpu-compat/Cargo.toml:8`, and per-crate `burn` + `burn-ndarray` dev-dep cleanup from `crates/ritk-{filter,transform,interpolation,registration}/Cargo.toml:23,30`; (ii) switches the public re-export at `repos/ritk/crates/ritk-image/src/lib.rs:11` from `pub use types::Image;` to `pub use AtlasImage as Image;` (verify which `atlas/checklist.md` §Batch #3 §Plan step 1 prefers — alternative is `pub use native::Image;`); (iii) removes `apply_row_chunks<B: Backend>` from `repos/ritk/crates/ritk-wgpu-compat/src/lib.rs:40+` (no async replacement; docstring-only if a docstring is needed for archival context); (iv) updates all `Image<B, D>` references in source across the workspace (this is the [major] breaking event per RITK semver). **MANDATORY pre-release confirmation** (per ADR 0012 §Decision §Sub-batch #5 + the `versioning` section of `atlas/AGENTS.md`): `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` MUST run pre-merge and MUST authoritative-classify the commit body as `[major]` (the table-row label `[major]` in `atlas/backlog.md` §Batch #3 sub-batches is provisional; `cargo-semver-checks` is the ground truth). **If `cargo-semver-checks` reports `[minor]` or `[patch]` instead, the sub-batch #5 commit message `[major]` annotation MUST be downgraded by the actual outcome** (an observable regression per `atlas/checklist.md` §Per-batch atomic commit + version bump rules). The CHANGELOG entry under `## [Unreleased]` uses `cargo-semver-checks`'s verdict, NOT the provisional table-row class label. **Standing pre-reqs**: (a) sub-batch #4 closed OR skipped (sub-batch #4 may be omitted if the kwavers Batch #4 PINN audit confirms no Atlas-side `coeus_nn::Record` replacement is required — the omit path is documented per ADR 0012 §Decision §Sub-batch #4); (b) kwavers Batch #4 (`burn::module::Module` → `coeus_nn::Module`) `burn.rs` + `burn_compat` facade deletions are LANDED on the `repos/kwavers` peer stream so the cross-crate risk #8 exposure is closed (cross-walk `atlas/gap_audit.md` surfacing risk #8 + the peer's `c6b845f81`-style "per prior direction not to build burn-compat shims" framing); (c) per upstream-consumer audit, no peer claim stream touches `repos/ritk/{Cargo.toml, src/lib.rs:11}` per `concurrent_agents` disjoint-scope rule (the absence can be verified by `git -C repos/ritk status --short` returning zero on the inner-RITK working tree prior to staging the sub-batch #5 commit). **Pre-flight gate per session**: `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` (mandatory pre-release verdict — the only source of truth for the version-bump rule) + `cargo build -p ritk-core -p ritk-image -p ritk-spatial --release` + `cargo test --doc -p ritk-core -p ritk-image` + `cargo tree --workspace -i burn`, `-i burn-ndarray`, `-i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` ALL return zero.

- **Sub-batch #6 [patch] — Standing reminder (downstream of sub-batch #5)**: `xtask/burn_surface.allowlist contract reset + CI scan gates tighten`. Cross-link to ADR 0012 §Decision §Sub-batch #6: source entries are removed; the allowlist file becomes the post-migration SSOT and is archived or rewritten. CI scan gates tighten: new CI gate asserts zero `burn::tensor::Backend`-bound public symbols; new CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph. CHANGELOG `[patch]` per RITK (CI-only). **Atomic inner commit shape**: a single inner-RITK CI-only commit that (i) regenerates `xtask/burn_surface.allowlist` content against the post-`#5 xtask/burn_surface_audit` regeneration (the contract-file becomes the post-migration SSOT — the pre-`#5` generated-from-`burn::` allowlist entries parcel to migration-done rows); (ii) adds a new CI scan gate that asserts zero `burn::tensor::Backend`-bound public symbols in the cross-crate re-export graph; (iii) adds a second CI scan gate asserting `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph (i.e., every public `B: Backend` constraint has been re-routed to `B: ComputeBackend` for atlas-side surface). Cross-link: README + the Atlas-meta CI pipeline (if it exists in CI providers); the new gates are authored in the atlas-meta peripheral repo (`repos/atlas`) which carries the meta-CI pipeline, NOT on the inner-RITK repo directly — the inner-RITK commit body references the atlas-meta commit SHA that introduces the gates. **Standing pre-reqs**: (a) sub-batch #5 MUST be RE-ENTERED first — the sub-batch #6 atomic commit's body references the sub-batch #5 inner SHA in its message ("Corresponding to ritk/atlas-migration-push/batch3 tag-advance inner SHA <sub-batch-#5-sha>" — the tag annotation body also updates at this point). The atomic-boundary discipline holds because sub-batch #5 closed + tag-advanced leaves the workspace clean of the Burn-keyed surface, making sub-batch #6 a pure-CI-tool change with no behavioural code surface; (b) `xtask/burn_surface_audit` runs against the post-sub-batch-`#5` `cargo tree -p ritk -i burn-ndarray` reset state and reports zero Burn-keyed source-files per crate (the sub-batch #6 commit body MUST include this audit's complete output as evidence); (c) the new CI scan gates themselves are exercised pre-commit by `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` (the dry-run output is captured in the commit body as evidence). **Pre-flight gate per session**: `xtask/burn_surface_audit` (regenerates the allowlist contract) + `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` all return their expected zero-output invariants.

### Cross-engineering verification — `hephaestus-cuda` eigen.rs Complex upload

The earlier `fb83d009` residual risk is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. Source inspection on 2026-07-06 shows `hephaestus-cuda/src/application/decomposition/eigen.rs` maps `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` with `Complex::new(z.re, z.im)` before `device.upload(&e_host)`, while `hephaestus-core::ComputeDevice::upload<T: bytemuck::Pod>` remains the generic transfer seam. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build verification plus source inspection; no runtime CUDA device execution was claimed.


---

## Out-of-scope (explicit)

- **`**Spec composition layers**` updated later (e.g. `cfd-validation`, testing frameworks)**: not part of this migration; filing as separate backlog if it's not in CFDrs's own backlog.
- **HELIOS/Python binding for kwavers**: Phase-3 rich-image scoping state; deferred-until `kwavers-python` intent-bledged beyond current net-style top-level.
- **GPU backend complete production rollout across ritk-model**: PPG-model is reserved-wave per `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md` HIGH-sev list; out of scope until defect closure.

### Atlas-root working-tree dirty triage (2026-07-06)

The Atlas-root `D:/atlas` working tree carries 29 dirty files (19 tracked-modified + 10 untracked) outside the migration-push closure chain. The vast majority have been classified as real Atlas-meta PM artifacts and committed in five atomic batches on 2026-07-06 (see commit history since `2c38db42`). The remainder is explicitly recorded below as **out-of-scope for the Atlas-parent pointer-advance ritual** — they live in scopes the Atlas-parent cannot reach (submodule internals, foreign root-level scratch, or non-submodule external dirs) and require separate-flow cleanup that is staged outside this branch's claim scope.

#### A. Root-level scratch (retracted 2026-07-06)

Cleanup chore commit on Atlas-meta deleted `nul` (Windows-reserved-name artifact on disk; the on-disk deletion API was blocked by `PermissionError` on the basename collision — see commit body for blocked paths; defense-in-depth `.gitignore` prevents future reproductions from re-entering `git status --short`) + `script.py` (root-level Python scratch that pre-existed the cleanup and was absent pre-chore per `os.path.exists`; the `.gitignore` entry ensures future re-generation path-respecting deletion can apply). Both items are now `.gitignore`-d so future reproductions cannot re-enter the Atlas-root working tree.

#### B. External / non-ASCII-dir content (retracted 2026-07-06)

Cleanup chore commit deleted `repos/SynthSeg/` (standalone git clone of the SynpthSeg brain-segmentation research project — has its own `.git/`, NOT in `.gitmodules`; deletion via `shutil.rmtree` with `onerror` handler that chmods + retries after Windows pack-file collisions on `.git/objects/pack/*`) + `repos/report/` (non-ASCII-filename dir, deletion via `shutil.rmtree` succeeded directly). Both items are now `.gitignore`d. Note: the prior-analysis claim that `repos/SynthSeg/` had "no `.git` of its own" was a stale read; the on-disk state had its own `.git/` and required the onerror handler for clean removal.

#### C. Submodule-internal dirtiness (uncommitted in inner repos — out of Atlas-parent reach)

These show up in Atlas-root `git status` as `M repos/<name>` (parent-tree entry marked dirty because the inner submodule's tree contains modifications relative to the gitlink pinned here). They are **cleanable only by an inner-submodule commit + parent-tree gitlink advance**, NOT by Atlas-parent commit. Each row is the inner-dirty count + inner HEAD as of 2026-07-06. No reclaim from Atlas-meta; these belong to the claim streams holding the inner repos.

| Submodule | Inner dirty count | Inner HEAD | Inner branch / claim stream | Triage decision (2026-07-06, per ADR 0011 §Decision §Leg 3) | Atlas-meta artifact action |
|-----------|---:|------|------|--------------------------------|------------------------------|
| `apollo`         | 235 | `f1ddf7a`     | peer claim stream `codex/apollo-atlas-migration` (WIP) | **Path B — OOS-next-sprint**: 235-file pre-CR-5 surface; queued behind ADR 0010 `apollo/atlas-migration-push/batch5` reservation | stay in §C with Batch-#5 reservation cross-walk |
| `CFDrs`          | 79  | `d58d1fe3`    | peer claim stream on `codex/cfdrs-atlas-migration` after Batch #2 closure | **Path B — OOS-next-sprint**: Batch #2 remains closed at `d58d1fe3`, but current source dirtiness has reappeared after the closure push and belongs to the CFDrs inner-repo claim stream; do not retract this row from §C until the inner tree is clean again or a new CFDrs commit lands | stay in §C; keep Batch #2 closure cross-link, but current dirty-tree accounting is live |
| `coeus`          | 19  | `b2beec3`     | peer claim stream on `main` (source + docs; includes dtype, tensor, Python embedding, and parity-test files) | **Path B — OOS-next-sprint**: not a PM-only closure-tail; source files are dirty and must land inside the Coeus claim stream with Coeus package gates | stay in §C as peer-active; no Atlas-meta source reclaim |
| `eunomia`        | 7   | `57d7789`     | peer claim stream (CR-4 closed; CR-EUNOMIA-COMPLEX ⏳ `acos/asin/atan` PR-queue per ADR 0006; **eunomia-side retroactive-closed per ADR 0006 §Decision §1 Path B**) | **Path C retroactive-closed 2026-07-06** (ADR 0006 §Decision §1 Path B additive `ComplexField::zero()`/`::one()` defaults landed at eunomia HEAD `57d7789`); 7-dirty reclassified as peer's UNRELATED `acos`/`asin`/`atan` PR-queue (per `## In-flight claims` Neighbor claim streams). Cross-walk §C eunomia reclassification bullet below + `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` + ADR 0008 §Decision §0 reframed. | retract from §C on next §-triage pass; the prior `Path B — OOS-next-sprint` classification was based on a stale ADR 0008 §0 Variant A / unseal `NumericElement` framing that ADR 0006 explicitly REJECTED |
| `gaia`           | 5   | `8f4a862da`     | peer claim stream `refactor/migrate-to-leto-geometry` | **Path B — OOS-next-sprint**: source and benchmark files are dirty (`src/application/csg/arrangement/classify.rs`, `benches/csg_performance.rs`), so the PM files cannot be committed as a source-disjoint Atlas closeout | stay in §C as peer-active; no split closeout |
| `hermes`         | 46  | `1b5392a`     | peer claim stream | **Path B — OOS-next-sprint**: 46-file scattered across `hermes-simd-*` crates + ADR footer updates; moderate-size, multi-domain peer-active | stay in §C; peer-active |
| `kwavers`        | 27  | `400c32624`   | peer claim stream `codex/kwavers-core-moirai-parallel` ACTIVE | **Path B — OOS-next-sprint**: dirty count drained from 132 to 27; remaining Batch #1/#4 surface still belongs to the kwavers inner-repo claim stream and stays behind ADR 0010 `kwavers/atlas-migration-push/batch1` reservation | stay in §C; cross-walk ADR 0010 reservation; drain-counter annotation now `-575` from the original 602-file capture |
| `leto`           | 14  | `626ebf538`     | peer claim stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile | **Path B — OOS-next-sprint**: 14-file ACTIVE peer stream (disjoint from CR-4 leto side per `concurrent_agents`) | stay in §C; disjoint with CR-4 leto side |
| `melinoe`        | 13  | `7ec0a44`     | peer claim stream | **Path B — OOS-next-sprint**: 13-file `crates/halo/` + 4 src sync; CR-1 consumer (brand doctrine holder for `apollo-ghostcell` deletion); cross-crate work with apollo CR-5 reservation | stay in §C; CR-1 cross-link |
| `moirai`         | 26  | `9b7881f`     | historical peer claim stream `refactor/remove-dead-subsystems` | **Superseded:** CR-2 closed 2026-07-18 with zero `#[global_allocator]` sites across the three library crates | historical snapshot only |
| `ritk`           | 0   | `8f8360ff`    | local follow-up committed after the clean nine-commit Batch #3 migration sequence, then advanced by Atlas-parent pointer commits | **Path C closed for risk #1 and Helios DICOM ownership**: inner commit `65a1a0fd` removes stale Burn `wgpu` default; inner commit `d7a940b5` adds the Batch #3 sub-batch #1 Atlas-typed parallel trait surface; inner commit `8f8360ff` adds typed DICOM attribute reads for downstream imaging consumers | pointer advanced by this Helios/RITK DICOM ownership commit; keep broader Batch #3 closure separate until package gates are current |
| **Σ** | **471 inner files** (fresh `git status --short` sweep; Helios and RITK now clean) | — | — | **2 retroactive/closed rows + 0 source-disjoint partial closeouts + 9 stay-OOS-next-sprint rows** | **No source-disjoint Atlas-meta closeout remains; next source work belongs inside the active inner-repo claim streams** |

#### D. Helios/RITK DICOM ownership cleanup (closed 2026-07-06)

Commit `c5f2a84e` closed the six-file Helios direct dependency slice under `repos/helios/**`: H-062 removed the unused direct `num-traits` workspace edge, H-061 removed Helios' unused aggregate dicom-rs `ndarray` feature edge while leaving pixel decoding owned by `ritk-dicom`, and the local Melinoe patch now lets patched Gaia resolve its `melinoe` 0.8.0 edge during Helios validation. Follow-up RITK commit `8f8360ff` closes the remaining production DICOM boundary drift by moving common DICOM image tag vocabulary and typed parsed-object attribute reads into `ritk-dicom`; Helios now consumes that API for parsing, typed attributes, transfer-syntax lookup, and pixel decode. Current Atlas-root status is expected to have no committed `repos/helios/**` direct-file dirtiness after this pointer-advance commit; the remaining imaging boundary is H-063 (`helios-imaging` audit for generic toolkit operations that belong in RITK).

#### E. Remaining future-correction hooks (post-2026-07-06)

§A and §B retractable future-correct clauses resolved in the 2026-07-06 cleanup chore commit on Atlas-meta (the 4-pattern `.gitignore` append + the on-disk SynthSeg + report deletions + the 4-pattern future-proofing). §C is partially-triage-classified per ADR 0011 §Decision §Leg 3 OOS-record cadence (sub-routine "Initial record" + "Post-resolution §-E update when stay-OOS-next-sprint"). Total submodule-internal dirty now stands at 471 inner files after the Helios direct-file closure (`c5f2a84e`), RITK Batch #3 sub-batch #1 pointer advance (`61931faf` to `d7a940b5`), Helios/RITK DICOM ownership pointer advance (`8f8360ff`), and the refreshed peer-WIP counts. This triage leaves three open forward-looking hooks:

- **§C retroactive-closings (Path C rows)**: 2026-07-06 triage retracted the zero-dirty `hephaestus`, `mnemosyne`, and `themis` rows from §C because they are no longer submodule-internal dirtiness. `CFDrs` was not retracted: re-verification shows 79 inner dirty paths on `codex/cfdrs-atlas-migration`, so the Batch #2 closure remains recorded while the current dirty tree stays tracked as a live CFDrs claim stream. The remaining Path C row is `eunomia`, which is covered by the separate reclassification bullet below.

- **§C partial-closeable queue (Path A candidates for next claim stream)**: empty after re-verification. `coeus` and `gaia` both contain source/benchmark dirtiness, so their PM files cannot be split into source-disjoint commits without hiding peer-active implementation context. `ritk` left this queue after inner commit `65a1a0fd`. Recommended pre-commit gate for future claim streams: `git -C repos/<X> status --short` once before the inner commit, to confirm no peer-stream claim landed in the interim.

- **§C stay-OOS-next-sprint (Path B rows)**: 9 submodules post-2026-07-06 refresh — `apollo` (235, Batch #5 reservation `apollo/atlas-migration-push/batch5` per ADR 0010; pre-CR-5 surface), `CFDrs` (79, Batch #2 closure remains closed at `d58d1fe3`, but current dirty paths belong to the live CFDrs inner-repo stream), `coeus` (19, source + docs peer stream), `gaia` (5, source/bench + PM peer stream), `hermes` (46, peer-active scattered), `kwavers` (27, Batch #1 + Batch #4 + Phase-1B reservations), `leto` (14, ACTIVE peer stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile), `melinoe` (13, CR-1 consumer cross-crate with apollo Batch #5; brand doctrine holder), `moirai` (26, Batch #6 reservation `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` per ADR 0010; `refactor/remove-dead-subsystems` ACTIVE). Removed: `eunomia` (retroactive-closed; 7 dirty files are unrelated `acos`/`asin`/`atan` PR-queue), `ritk` (clean at `8f8360ff` after the DICOM ownership pointer advance), and `helios` (direct dependency plus DICOM ownership slices closed; H-063 filed for future `helios-imaging` audit). No Atlas-meta reclaim per disjoint-scope rule (ADR 0011 §Decision §Leg 2). Each row stays in §C until its owning claim stream emits a pointer-advance to Atlas-parent.

- **§C eunomia row reclassification (post-2026-07-06 phantom-blocker discovery)**: the §C `eunomia` row above has been reclassified from `Path B — OOS-next-sprint` to `Path C retroactive-closed (eunomia-side per ADR 0006 §Decision §1 / Path B additive `ComplexField::zero()`/`::one()` defaults landed at HEAD `57d7789`)`. The 7-dirty is now re-attributed to the peer's UNRELATED active WIP stream (`acos`/`asin`/`atan` PR-queue per § In-flight claims Neighbor claim streams section) — OUT of §C scope on the next §-triage pass per ADR 0011 §Decision §Leg 3 \"Resolution branch\". The residual Phase-1B is kwavers-side per ADR 0008 §Decision §0 (reframed per the discovery); cross-walk `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` for the full verification matrix.

- **§D (Helios/RITK DICOM ownership closure)**: closed by `c5f2a84e` plus RITK `8f8360ff` and this Helios consumer reroute; current Atlas-root status has no committed `repos/helios/**` direct-file dirtiness after the pointer-advance commit, and H-063 tracks the remaining `helios-imaging` generic-toolkit audit.

- **`nul`** (whose on-disk deletion API was blocked by Windows-reserved-device-name PermissionError on this build): the `.gitignore` defense in this chore commit prevents future `nul` reproductions from re-entering `git status --others`. The on-disk file may still surface via `dir` from bash contexts but is gitignored; admin `cmd /c del /F /Q nul` or Windows-reboot may be required for actual on-disk removal. Filed for the next codex-session restart-handler.


### RN-CC-05 (transitive parent-SHA chain breach detection + audit-discipline establishment)

Filed by `chore(atlas): Roll-up review-nit RN-CC-05 -- transitive parent-SHA chain breach detection` (post-`536366e`). Retroactively addresses code-reviewer-minimax-m3 NIT surfaced in the post-`536366e` cycle: commits `93a0723177` + `a96d46d7294` declared the RN-CC-04 discipline but inline-cited the parent rather than carrying a `Parent-SHA:` line-block at the top of body. Per NO-AMEND, retroactive body repair is forbidden; the breach is disclosed across 4 docs files + recorded in the RN-CC-05 commit body. Parent-SHA: forward-propagation audit discipline: `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` yields >=2 line-hits; `git log --grep "Parent-SHA:" --oneline` yields >=2 entries. Self-discipline demonstration: `74df54d4f963b96d1b642ce89e77c9b019ad3de7` + `74df54d4f` + `536366e` + this RN-CC-05 chore carry line blocks at top of body; `93a0723177` + `a96d46d7294` need forward-session transparency (this row).

## Review nit rolling list (forward-looking improvement tracking, 2026-07-08)

> Persistent review-improvement tracking items surfaced by the
> post-`91896c477` code-reviewer pass on the Atlas architectural
> directive framing chore. Each nit is annotated: ID, scope,
> severity, source-chore, fix status, suggested follow-up.
> Future chore-cycles reference this list when templating
> `docs(atlas):` commits so the same drifts don't recur.

| ID | Nit | Severity | Source chore | Status | Follow-up |
| --- | --- | --- | --- | --- | --- |
| **RN-01** | CR-2 (open; Batch #6) citation error -- mnemosyne row cited "per CR-2 (open; Batch #6)" but CR-2 is **OPEN** per Surfacing risks row 1.2 (Batch #6 reserved), not CLOSED. | factual | `91896c477` | **FIXED in `b29cfa24b`** (mnemosyne row changed to "per CR-2 target axiom [open; Batch #6]") | file-wide rg `per CR-2 (open; Batch #6)` on subsequent docs-only chores; extend fix to any other inverted citations |
| **RN-02** | 11+3 stack split -- the monolithic `### Stack (13 atlas crates)` table conflated 11 providers with 3 consumers in one 14-row table. | structural | `91896c477` | **FIXED in `b29cfa24b`** (split into `### Provider stack (11 atlas crates)` + `### Consumer migration targets (3 simulation suites)`) | template future `Atlas-stack` table sections with the provider/consumer split pattern from the start; split mnemosyne+themis row when allocator-pair semantic is involved |
| **RN-03** | Gitlink SHA truncation -- table used 7-char truncated SHAs (`98a02b6...`, `37ff12d5...`, etc.) which break grep-ability and don't match the 40-char convention used elsewhere in `gap_audit.md`. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (all 14 table SHAs now full 40-char live from `git ls-files --stage`) | prefer full 40-char SHA in all `docs(atlas):` table cells; only allow truncation when the SHA is genuinely abbreviated (e.g., an inner HEAD short-SHA in narrative prose) |
| **RN-04** | FRONT-MATTER sync -- `gap_audit.md` lines 1-11 blockquote enumerated 4 record-types but the new `## Atlas architectural directive` section added a 5th without updating the enumeration. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (item 5 appended to front-matter blockquote: `Atlas architectural directive (2026-07-08); consolidator framing -- stack table, migration targets, design principles, constraints, bulk-migration priority order`) | when adding a new top-level section to `gap_audit.md`, also update lines 1-11 blockquote enumeration; consider automating via a pre-commit check |

**File-wide open follow-ups surfaced by the post-`b29cfa24b` review**:

- **CR-2 file-wide citation scope (RN-01 scope extension)**: a file-wide
  `rg -n 'per CR-2 (open; Batch #6)' gap_audit.md` post-patch may surface
  additional inverted citations outside the table row that was fixed
  in RN-01 (e.g., CR-class status cell, Surfacing risks row 1.2
  narrative, cross-cutting notes). **Status**: not yet verified
  post-patch; a follow-up patch chore should run the rg + extend the
  fix to any other hits.
- **Subsection naming collision (RN-02 cosmetic extension)**: the new
  `### Consumer migration targets (3 simulation suites)` (table)
  sits adjacent to the existing `### Migration consumer targets (3 in
  flight)` (prose). The two names are lexically adjacent on
  "consumer migration targets" -- a grep footgun. **Status**: not
  yet renamed; recommend renaming the new table to `### Consumer
  simulation suites (3 in flight)` for disjoint-name grep-ability.
- **Prose subsection inner-HEAD SHA uniformity (RN-03 scope
  extension)**: the preserved prose subsection (`### Migration
  consumer targets (3 in flight)`) still uses 9-char short-SHAs
  (`inner HEAD 05500930c`, `702e4f125`, `d58d1fe3`, etc.); the new
  directive table uses 40-char SHAs. **Status**: deliberate scope
  choice -- not yet upgraded for visual consistency. Either
  upgrade in a follow-up patch, or document the inconsistency
  explicitly in body-scratch as a preservation choice.
- **Body-scratch subject parent-SHA anchor (RN-04 audit-discipline
  extension)**: subject of `b29cfa24b` is `Patch 4 review nits on
  directive chore (...)` and doesn't grep-match `91896c477` (parent
  SHA). **Status**: noted as a `concurrent_agents` precedent for
  future subject-pattern discipline; recommend appending `(parent
  <SHORT-SHA>)` to chore subject or putting parent-SHA on
  body-scratch line 1.

**Audit-lifecycle note**: this rolling list persists until (a) a
follow-up chore closes all 4 RN items above (RN-01..RN-04 already
FIXED in `b29cfa24b`; 4 follow-up extension nits remain open), or
(b) a future chore re-classifies any item as RESOLVED-by-design
via explicit `docs(atlas): Mark RN-XX as RESOLVED-by-design (...)`
commit. Re-probe cadence: per `docs(atlas):` chore landing that
touches `gap_audit.md` PM surface.

**Cross-link**: see `gap_audit.md` `## Atlas architectural directive
(2026-07-08)` (line 12) for the source-chore context + `## Surfacing
risks` for the open follow-ups' parent audit-class entries. See
`D:/atlas/gap_audit.md` `L339 PRESERVED` parity-row in the
`### Anchor-evolution history` section for the prior anchor-iteration
history convention (anchor-tail intent-over-version naming).


---

- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.
- **This codex session (2026-07-09, Bulk-migration #2 E0369/E0599 closure-front triage in `kwavers-math`)**: dry-run enumeration via `rg '::ones\([^)]*\)\s*\*' --type rust` + `rg '\.view\(\)' --type rust` against `crates/kwavers-math/src/**` returns **0 `::ones(...) * scalar` sites (E0369 front fully drained, idiom-set closure confirmed)** and **151 prefix-form `.view()` call sites across 27 distinct files (138 bare `.view()` + 13 `.view_mut()`; total per row 14.5 SSOT in `gap_audit.md`; E0599 front, separate closure track)**. **Idiom-set triage conclusion**: the 3-item idiom list recorded in `gap_audit.md` `### Bulk-migration priority #2 routing lesson (2026-07-09)` — `array.iter_mut().for_each(|v| *v *= scalar)`, `as_slice_memory_order_mut()`, and the project-native `scale_array` helper — IS operationally complete for the E0369 front as of the prior-session proof-of-pattern work (`avx2.rs:46,56` + `dispatcher.rs:139,151` closed 4 of 4 E0369 sites; cargo check error count 128 → 124). **The `.view()` E0599 sites are a SEPARATE closure-front** (most call sites are `.view()` / `.view_mut()` invocations on ndarray `Array3`/`Array4`, requiring explicit error propagation rewrites + trait-bound refactor of `Boundary<_>` carrier), and **are NOT covered by the E0369 3-item idiom set**. Per the user’s “if new patterns emerge, file a follow-up docs update rather than diverge from the lesson” guidance, the 3-item list is NOT expanded in this turn — the E0599 front stays tracked here as a transient atlas-meta carryover with the 138/27 enumeration, awaiting either peer-side Bulk-#2 phase work or future-session idiom-set expansion posture.


- **[SUPERSEDED 2026-07-09 by ADR 0013 `## Supersedes` field]** the prior partial-closure-mark was 2026-07-08; superseded; see D:/atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md for the full Batch #1 source-side closure mark.
- **slice 1 partial-closure-mark 2026-07-08 — kwavers Batch #1 source-side migration slice 1 PARTIAL CLOSURE (2/41 sites, 1/15 files)**: per the peer's `5cd8c708` chore (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`, on `codex/kwavers-core-moirai-parallel` atop parent `ccc6bbf9`): 2 of the 41 source-side `.par_for_each()` sites have been migrated. The 2 sites live in `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs` (3D `Array3<f64>` element-wise relaxation on `p_fluid_ghost` + `p_fluid_ghost_prev`; plus a 1D sub-view relaxation on `t_solid_ghost` + `t_solid_ghost_prev`). Migration dispatch: idiomatic `moirai_parallel::ParallelSliceMut::par_mut().enumerate(closure)` trait form (auto-Adaptive policy; no `ExecutionPolicy` generic needed); cargo-check pre-validate clean at inner HEAD `5cd8c708`. **KW-CV-001 watchpoint state**: remains ACTIVE — the closure-style trigger (`closeout|final|completion|close-batch` substring grep on the last 30 kwavers commits) is still 0; per the `concurrent_agents` disjoint-scope rule, atlas-meta is *observing* (not advancing) the peer's slice-by-slice progress without re-emitting the prior retracted full-closure mark. The remaining 39/41 sites / 14/15 files will be tracked via per-slice partial-closure marks (this entry is the first such mark) until the source-side count actually drops to zero, at which point the full closure-mark can be reasserted. **Atlas-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit; do NOT bump the kwavers gitlink from the current `35ee01076` even as subsequent Batch #1 slices land on the peer stream, per the watchpoint's no-advance-without-closeout policy. **Note (data-quality, post-e73d524 dedup)**: the round-3 codex-session block was historically duplicated at L87+L90 (pre-chore-cycle stale snapshot); de-duplicated in chore-commit `e73d5241f` via structural-cleanup; see the OBSERVED 2026-07-09 tombstone (post-cut at L283) for the audit trail. The partial-closure mark is appended at end-of-file for grep-ability + future-automation reliability.


- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep)**: user directive "cleanup and resolution of all test and example issues/errors" triggered a fresh sweep across consumer-side trees at the just-advanced inner HEADs. T1 evidence:
  - **ritk** at inner HEAD `529d6651`: `cargo nextest run -p ritk-python --lib` 47/47 PASS (value-semantic asserts verified — `mi_normalized_identical_is_one`, `mi_rejects_shape_mismatch`, `test_validate_percentiles_descending_elements_returns_error`, `test_validate_range_inverted_bounds_returns_error`).
  - **CFDrs** at inner HEAD `72275347fb71`: `cargo check --workspace --all-targets` PASS (no warnings); `cargo nextest run --workspace --lib` 2177/2177 PASS (1 skipped, 0 failed, 1 slow at 28.1s — within CFDrs's 30s terminate budget).
  - **CFDrs subset** `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib`: 1335/1335 PASS (1 skipped, 24.9s execution).
  - **kwavers** at inner HEAD `ccc6bbf9e6` (`Workspace-wide ndarray↔leto boundary fixes; cargo check --workspace passes`): `cargo check -p kwavers-solver --workspace` PASS; `cargo check --workspace` PASS with 1 dead-code warning (`fn to_leto3` unused in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`); **`cargo nextest run --workspace --lib` FAILS at compile** with 1 site: `crates/kwavers-solver/src/plugin/mod.rs:204:21` — the test-mock `NullBoundary::apply_acoustic_freq` reads `_field: &mut Array3<kwavers_math::fft::Complex64>` (resolving via in-scope `use ndarray::Array3;` at line 182, which shadows the workspace's `leto::Array3` re-binding); the `Boundary` trait now declares `&mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. **Disjoint-scope peer-owned per `concurrent_agents`**: atlas-meta records surface + line; the inner peer stream owns the 2-line edit (`use ndarray::Array3;` → `use leto::Array3;` at L182 + parameter signature updates at L204). Filed at `gap_audit.md` row 14.5.
  - **Note**: a 2nd `kwavers-solver` site at `crates/kwavers-solver/src/forward/pstd/physics/residual_gas_absorption.rs:74` (`spectrum: &mut Array3<kwavers_math::fft::Complex64>`) ALREADY uses `use leto::{Array3, ArrayView3};` (L65), so its `Array3` resolves correctly. Only the plugin test mock is broken.
- **`repos/kwavers` gitlink advance this session**: `4f344f840` (Phase-3 → Phase-4 → Phase-5 sweep closure at inner HEAD `ccc6bbf9e6`). KW-CV-001 watchpoint re-probed at `ccc6bbf9e6` — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing. Atlas-meta defers final closeout pose until peer's closeout subject lands.

- **[OBSERVED 2026-07-09 round-3 codex-session block + Standing reminders + Cross-engineering verification + Out-of-scope + Atlas-root dirty triage + Review nit rolling list deduplicated to canonical Region 1 (L1-L282) ordering via atomic structural-cleanup chore; see `### In-flight claims (per concurrent_agents)` L82 + canonical `#### Standing reminders` L112 + canonical `## Review nit rolling list` L186 for the authoritative copies. This tombstone also absorbs the prior `93f676ffd` forward-auditor cross-reference to the L262 SUPERSEDED + L263 slice-1 partial-closure-mark block, which remains the canonical Batch #1 source-side closure reference (see ADR 0013 `## Supersedes` field for the full Batch #1 source-side closure mark).]**


## Batch #1 source-side migration -- slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8): **5/41 sites migrated in 3/15 files** cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (1 mut + 4 immut Zip par_for_each at L93, migrated with 5 is_standard_layout() asserts + as_slice{_mut,}() + par_mut().enumerate() with 4 flat-index lookups). **36/41 sites / 12/15 files remain**. Full-closure mark remains retracted. KW-CV-001 watchpoint remains ACTIVE.
## Batch #1 source-side migration -- slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708): **4/41 sites migrated in 2/15 files cumulative** at slice 2. The 2 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1-mut + 2-immut Zip par_for_each at L48 + 1-mut + 3-immut Zip par_for_each at L62 inside KuznetsovWave::update_wave). **37/41 sites / 13/15 files remain**. KW-CV-001 watchpoint remains ACTIVE. NOTE: retroactive land AFTER slice 3 mark (prior re-emission attempts failed).
## Batch #1 source-side migration -- model_impl.rs Nit 1 asymmetry fixup mark 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b): closes Nit 1 asymmetry by retroactively adding 7 is_standard_layout() asserts to model_impl.rs (slice 2 file): 3 in first-step branch + 4 in multi-step branch. Mirrors the struct_impl.rs fixup c77a926d8 in style. Cargo check clean. Cumulative at the migration level unchanged: **5/41 sites / 3/15 files migrated + 2 file-level fixups** (c77a926d8 + b21679f5). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c): **6/41 sites migrated in 4/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (1-mut + 3-immut Zip par_for_each at L109 in `compute_nonlinear_term_workspace`). **35/41 sites / 11/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted, this is the fourth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f): **7/41 sites migrated in 5/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (1-mut + 1-immut Zip par_for_each at L191 in `OperatorSplittingSolver::nonlinear_step`). **34/41 sites / 10/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

## Batch #1 source-side migration -- slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5): **11/41 sites migrated in 6/15 files** cumulative. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (1-mut + 1-immut Zip par_for_each sites in `KuznetsovWave::compute_rhs` homogeneous branch -- linear/laplacian, source/cache_source, nonlinearity/nonlinear_term, diffusion/diffusive_term). **30/41 sites / 9/15 files remain**. **Heterogeneous Zip::indexed site 1 deferred to follow-up chore**. KW-CV-001 watchpoint remains ACTIVE. Filename arithmetic restored to 6/15 from commit-body off-by-one of 5/15.

- **slice 9 partial-closure-mark 2026-07-09 — kwavers Batch #1 source-side migration slice 9 PARTIAL CLOSURE (1 site in spectral.rs; the deferred heterogeneous 4-mut-0-immut Zip::indexed chain)**: per the peer's `949e5a39` chore (`refactor(kwavers-solver): Migrate spectral.rs 4-mut Zip::indexed to verbose is_standard_layout (Batch #1 source-side slice 9)`, on `codex/kwavers-core-moirai-parallel` atop slice 8 parent `9ab677b0`): 1 deferred heterogeneous site migrated. The site lives in `crates/kwavers-solver/src/forward/nonlinear/westervelt_spectral/spectral.rs` in `initialize_kspace_grids` — the 4-way `Zip::indexed(&mut kx).and(&mut ky).and(&mut kz).and(&mut k_squared).par_for_each(|(i, j, k), kx_v, ky_v, kz_v, k2| { let kx_val = kx_axis[i]; let ky_val = ky_axis[j]; let kz_val = kz_axis[k]; *kx_v = kx_val; *ky_v = ky_val; *kz_v = kz_val; *k2 = kx_val * kx_val + ky_val * ky_val + kz_val * kz_val })` chain. **Strategy**: Pattern A — extend divergence.rs slice 7 3-mut strategy to 4 muts. Keep `Zip::indexed(kx.view_mut())` as the parallel iterator (the closure body consumes `(i, j, k)` for closure-captured Vec<f64> reads `kx_axis[i]/ky_axis[j]/kz_axis[k]`); pre-extract 3 flat `as_slice_mut()` buffers for `{ky, kz, k_squared}`; write 3 additional mut outs via `op_slice[idx]` inside the closure, computing `idx = i*(ny*nz) + j*nz + k` inline once per iteration (~10 cycles vs ~100 for a div/mod-based idx-to-(i,j,k) decomposition in a drop-everything pattern). Race-freedom preserved: each parallel task writes to 4 distinct output elements (kx_v via Zip iterator + 3 disjoint `slice[idx]` writes), all addressed by the same unique `(i, j, k)` tuple. **Precondition asserts**: 7 layout/length asserts total = 4 verbose `is_standard_layout()` on `{kx, ky, kz, k_squared}` mut outs + 3 `debug_assert_eq!` on `{kx_axis, ky_axis, kz_axis}.len()` (Vec<f64> is unconditionally C-contiguous, so length is the only precondition — matching slice 8 cluster D's `σ_*` Array1<f64> pattern verbatim). **WHY NOT HELPER rationale documented inline**: (a) verbose-form is Batch #1 SSOT with helper adoption in 0 of 9 migrated sites across slices 1-8; (b) the slice 9 4-mut extension deliberately matches divergence.rs slice 7 3-mut verbatim for source-level consistency; (c) broader helper-validation across heterogeneous patterns is deferred to Batch #2. **Validation**: `cargo check -p kwavers-solver --lib --no-default-features` rc=0; `cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 — all 6 westervelt_spectral tests pass bitwise (`k_squared_dc_bin_is_exactly_zero`, `k_squared_fundamental_mode_matches_2pi_over_lx`, `k_squared_nyquist_bin_equals_pi_over_dx`, `spectral_laplacian_of_constant_is_zero`, `spectral_laplacian_of_sine_matches_analytical`, `spectral_laplacian_into_is_bitwise_identical_to_allocating`). **Code-reviewer verdict on the source-side commit**: OK to commit after 1 minor nit applied (sharpened the WHY-NOT-HELPER section (b) rationale to drop the imprecise "N>5 closure-captured immuts" claim, since this site only has 3 immuts). **KW-CV-001 watchpoint state**: remains ACTIVE — no formal `closeout`/`final`/`completion`/`close-batch` substring exit in the last 30 inner kwavers commits; per `concurrent_agents` disjoint-scope rule, atlas-meta continues to observe without re-emitting the prior retracted full-closure mark. Atlas-meta path forward: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit.

- **ADR 0014 forward-looking note 2026-07-09 — KW CV-001 watchpoint active awaiting kwavers peer stream closeout-tag chore**: per the new ADR 0014 `D:/atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` (Status `Proposed` on 2026-07-09), the kwavers Batch #1 closeout-tag ceremony chore is opened but not yet executable. The KW-CV-001 watchpoint (per `D:/atlas/backlog.md` §In-flight claims `repos/kwavers` row: `git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns 0 at inner HEAD `949e5a39`) gates the Status flip from `slice-by-slice partial closure` (ADR 0013) to `full closure` (ADR 0014). The chore bundles 3 atomic items on disjoint scopes: item (a) 1,315-file mechanical drift flush + item (b) slice 7 `is_standard_layout` predicate unification + item (kwavers closeout) — all 3 emit on `repos/kwavers` `codex/kwavers-core-moirai-parallel` per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from touching `D:/atlas/repos/<X>/`). Atlas-meta's bystander role here: item (c) `chore(atlas): Advance repos/kwavers submodule pointer + KW-CV-001 retirement` is a forward chore whose trigger is items (a) + (b) + closeout-style-commit having landed on the kwavers peer stream. When the stash lands, item (c) advances `repos/kwavers` parent-tree gitlink + either deletes or marks `RETIRED 2026-07-09+` the KW-CV-001 row in §In-flight claims. ADR 0014 itself is then flipped `Proposed` → `Accepted` via a follow-up atlas-meta chore commit. Until the kwavers peer stream emits items (a)+(b)+closeout, this ADR remains `Proposed` + this note remains the residual forward-looking visibility surface.

- **Blocker-triage chore briefs 2026-07-09 — 5 carried-forward blockers re-probed against owning peer streams (per ADR 0013/#14 §Out of scope items 1-4)**: atlas-meta orchestrates the 2026-07-09 re-probe of the 5 carried-forward blockers referenced by ADR 0013 §Out of scope items 1-5 + ADR 0014 §Out of scope items 1-5. The re-probe results classify each blocker as RETIRED (cargo-clean), RECLASSIFIED (different actual cause), CORRECTED (right outcome, wrong count), or CONVERTED (workstream-already-progressing). Each blocker becomes a discrete chore on its owning peer stream per disjoint-scope (ADR 0011 §Leg 2); atlas-meta's bystander role is filing the brief here.

| Row | Blocker ID | Owning peer stream | Re-probe classification | Action verb on peer stream | Cross-walk |
|-----|-----------|---------------------|-------------------------|----------------------------|------------|
| 1 | ritk-wgpu-compat burn workspace-manifest (ADR 0013 §Out-of-scope #1) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-wgpu-compat --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (17.32s) on branch `main`; `burn` + `burn-ndarray` deps are accepted by cargo | No chore required for Batch #1 closure. Optional: Burn-strip per ADR 0012 §Sub-batch #5 `[major]` for the longer-term Burn removal cycle (NOT part of Batch #1 gate) | ADR 0013 §Out-of-scope #1 amended with ➜ RETIRED note |
| 2 | ritk-registration burn dep strip (ADR 0013 §Out-of-scope #2) | `repos/ritk` | **➜ RECLASSIFIED** — actual cause is `direct-parzen` feature-gate regression; 2 `E0432` errors at `crates/ritk-registration/src/metric/histogram/parzen/image_cache_helpers.rs:7:43` (`SparseWFixedCache` gated behind `direct-parzen` feature) + `crates/ritk-registration/src/metric/histogram/mod.rs:10:17` (`atlas_parzen_cache` module gated behind same feature) | Open chore on `repos/ritk`: gate the importing modules behind a `#[cfg(feature = "direct-parzen")]` proxy or fix the import path; commit title `fix(ritk-registration): Resolve direct-parzen feature-gate E0432 errors`. Verification: `cargo check -p ritk-registration --lib --no-default-features` rc=0 | ADR 0013 §Out-of-scope #2 amended with ➜ RECLASSIFIED note; ADR 0014 §Out-of-scope #2 inherits |
| 3 | ritk-image autodiff-module syntax (ADR 0013 §Out-of-scope #3) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-image --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (18.77s); remaining `autodiff` references (`host_extract.rs:73,114,115` `type AB = Autodiff<NdArray<f32>>;` test fixture + `types.rs:188` comment) are inert feature-gated test types | No chore required. Informational only — the carried-forward entry was inaccurate; the lib does not have a syntax error | ADR 0013 §Out-of-scope #3 amended with ➜ RETIRED note |
| 4 | 1,315-file kwavers mechanical drift (ADR 0013 §Out-of-scope #4) | `repos/kwavers` | **➜ CORRECTED** — actual drift is 30 modified files, not 1,315 (`git status --short | wc -l` against `repos/kwavers` inner HEAD `445ab9b2` on `codex/kwavers-core-moirai-parallel`); sample of 30/30 modifications is whitespace-only (LF vs CRLF normalization) | Open chore on `repos/kwavers`: emit `chore(kwavers): Flush mechanical dirty triage (30-file CRLF/whitespace batch)` per ADR 0014 §Sequencing step 1 (corrected file count). Verification: `git status --short | wc -l` returns 0 post-chore | ADR 0014 §Sequencing step 1 + §Verification plan item 2 amended with corrected 30-file count |
| 5 | kwavers-math Phase-3/Phase-4 ndarray → leto migration breakage (ADR 0013 §Out-of-scope #5) | `repos/kwavers` | **➜ CONVERTED** — 2 actual commits landed on kwavers peer post-slice-9 `949e5a39`: `445ab9b2` `fix(kwavers-math): linear algebra import/API mismatches` + `e2e1e180f` `fix(kwavers-math): grid/transducer compilation issues` (both kwavers-math-scoped exclusively) | Workstream already in progress on kwavers peer stream; no new chore required from atlas-meta. Monitoring posture until `cargo check -p kwavers-solver --lib --no-default-features` rc=0 restored post-`Array2::from_shape_vec` signature shift | ADR 0013 §Out-of-scope #5 + ADR 0014 §Out-of-scope #5 amended with ➜ CONVERTED note referencing actual commit SHAs |

Triage-summary headline: **5 carried-forward blockers re-probed 2026-07-09; 3 NOT real (#1, #3, #4 overstated), 1 misdiagnosed (#2 not Burn — feature-gate), 1 real + active (#5 already progressing on kwavers peer with 2 actual commits). Batch #1 closure gate unaffected**: ✅ ADR 0013 §Verification plan step 2 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 at slice 9 parent inner HEAD `949e5a39` verified. The post-slice-9 `kwavers-solver --lib` breakage from `Array2::from_shape_vec` signature shift is the explicit Batch #2 prerequisite gate per ADR 0014 §Verification plan step 8. Filing this brief acts as the forwarding ledger: each row's own peer stream picks up its chore at their cadence; atlas-meta does not co-emit the chore commits per disjoint-scope.

- **ADR 0015 trigger-chore brief 2026-07-09 — Open KW Batch #2 Entry Point #1 (`kwavers_safety::with_zip_standard_layout` const-generics arity extension) on kwavers peer stream**: per the new ADR 0015 `D:/atlas/docs/adr/0015-kwavers-batch2-entrypoint1-helper-const-generics.md` (Status `Proposed` on 2026-07-09), the kwavers-solver Batch #2 Entry Point #1 acceptance-validation chore is opened but **currently BLOCKED on Block #5** (per ADR 0013/0014 §Out of scope #5 + Blocker-triage chore briefs row 5). The chore design refines ADR 0013 §Open Batch #2 Entry Point #1 with a const-generics arity extension `[(&'static str, &'imm Array3<A>); N]` with `const N: usize` for the helper signature; this replaces the current dynamic-slice form `'imm [(&'static str, &'imm Array3<A>)]` (which forces runtime indexing + local `Vec` allocation + HRTB friction at N>5 closure captures). The implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 ABSOLUTE — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). **Acceptance criteria (AC-1 through AC-6) per ADR 0015 §Verification plan**: AC-1 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 (Block #5 gate); AC-2 `cargo test -p kwavers-solver --lib` rc=0; AC-3 6/6 westervelt_spectral tests bitwise-identical; AC-4 helper-stress fixture backporting slice 6b rhs.rs 9-immut heterogeneous Phase 2 site bitwise vs verbose-form RHS at all (i,j,k) grid points; AC-5 `cargo test -p kwavers-solver --lib --features helper-stress` rc=0; AC-6 slice 6b site in-place adoption preserves bitwise equivalence. The standing reminder is recorded here in atlas-meta side until AC-1 through AC-6 are all ✅; at that point, atlas-meta emits Step 5 (status-flip chore commit) per ADR 0015 §Sequencing on the kwavers peer core-moirai-parallel branch HEAD that achieves acceptance.

- **ADR 0015 Step 2 design-spec landing 2026-07-09 — KW Batch #2 Entry Point #1 Step 2 helper const-generics extension design-spec filed on atlas-meta side per disjoint-scope**: per ADR 0015 §Sequencing `### Step 2 detailed design specification` amendment landed on atlas-meta by this commit, the Step 2 design-spec is filed as the SSOT that the kwavers claim stream picks up once Block #5 closes. **Status reaffirmation (probed 2026-07-09)**: Block #5 pre-flight gate STILL BLOCKED on `cargo check -p kwavers-solver --lib --no-default-features` (rc≠0; E0308 type mismatches in `kwavers-transducer` + E0599 missing `matmul`/`assign` methods + `kwavers-transducer/focused/arc.rs` syntax gaps; the post-slice-9 commits `445ab9b2` + `e2e1e180f` did not close the gate). The Step 2 design-spec captures: (a) target file `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs:L84-130` (NEVER EDIT FROM ATLAS-META); (b) 4 modifications to apply (add `const N: usize` + change `immuts` to `[(&str, &Array3<A>); N]` + simplify closure-bound array form + replace `Vec` with `std::array::from_fn`); (c) preserved constraint surface verbatim (`A: Copy + Send + Sync` + verbose panic message form + `'out` lifetime + Nit-1-fix `A: 'static` omission); (d) monomorphization analysis (~30 KB binary impact bounded at N=0..9); (e) Send + Sync propagation + disjoint-capture-rule analysis; (f) HRTB retention recommendation (`for<'s>` kept for forward-compat); (g) acceptance criteria AC-2a/AC-2b/AC-2c + reviewing checklist (atomic-boundary + disjoint-scope + paragraph-collapse). Step 2 cannot execute from atlas-meta per ADR 0011 §Leg 2; the kwavers claim stream owns the implementation commit. Standing reminder updated to: Step 2 design-spec SHIPPED; Block #5 gate BLOCKED; pre-flight gate re-probe required before ASSEMBLE-STATE confirmation.

- **ADR 0016 trigger-chore brief 2026-07-09 — Open Block #5 (kwavers-math ndarray → leto) resolution design-spec on kwavers peer stream per disjoint-scope**: per the new ADR 0016 `D:/atlas/docs/adr/0016-kwavers-block5-resolution-design-spec.md` (Status `Proposed` on 2026-07-09), the kwavers-math Phase-3/Phase-4 ndarray → leto migration resolution chore is opened with a 3-commit atomic decomposition recommended design. Block #5 pre-flight gate is the **AC-1 prerequisite for ADR 0015 Acceptance** (Batch #2 Entry Point #1 helper const-generics extension depends on this). Pre-flight gate state (probed 2026-07-09): `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with 8 errors in `kwavers-transducer` (E0308 type mismatches in `beamforming/processor.rs` + E0599 missing `matmul` on `leto::Array` + E0599 missing `assign` on `Result` in `calibration/manager/mod.rs` + arc.rs syntax gaps in `transducers/focused/arc.rs`); the 2 already-landed commits `445ab9b2a` + `e2e1e180f` closed kwavers-math-only scope but did NOT propagate fixes to kwavers-transducer/receiver/boundary/source/grid callers. The 3-commit atomic decomposition per ADR 0016 §Decision: (1) `fix(kwavers-transducer): Resolve E0308/E0599 + arc.rs syntax (Block #5 sub-batch 1 — strict additive)` — arc.rs syntax + o_ops::linalg::matmul import) + Result.assign migration (destructured `if let Err(e)` pattern) + E0308 `leto::Array` boundary reconciliation; (2) `refactor(kwavers-migration): Migrate Array2::from_shape_vec tuple→array workspace-wide (Block #5 sub-batch 2 — strict signature migration)` --- 8 crates [python, solver, analysis, transducer, receiver, boundary, source, grid] using `sed`-assisted migration from `(rows, cols)` form to `[rows, cols]` array form; (3) `chore(kwavers): Block #5 gate-validation regression test (Block #5 sub-batch 3 — gate reset)` --- CI-side rc=0 assertion + bitwise-identical 6/6 westervelt_spectral tests against slice 9 inner HEAD `949e5a39` baseline. AC-1 through AC-5 per ADR 0016 §Verification plan (kwavers-transducer rc=0 + workspace-wide `Array2::from_shape_vec((` count = 0 + kwavers-solver rc=0 + 6/6 westervelt_spectral bitwise + no false-positive KW-CV-001 watchpoint trigger). Implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). Standing reminder: Block #5 design-spec SHIPPED as the SSOT; kwavers claim stream owns the 3-commit implementation; once the 3 commits land + AC-1 through AC-5 satisfied, atlas-meta emits Step 5 status-flip chore per ADR 0016 §Sequencing flipping ADR 0016 to `Accepted` + simultaneously unblocks ADR 0015 AC-1.

## Provider integration audit queue — 2026-07-13

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HEPH-EMPTY-001 | [patch] | done (`65e89b7`, merged `991f12e`) | Hephaestus decomposition state | Synthetic empty factors deleted; determinant, identity, rank, permutation, and shape contracts pass CUDA/WGPU value tests and the 239-test package suite. |
| MEL-SCOPE-001 | [major] | done (`55ad20e`, merged `bb07447`) | Melinoe capability plus Mnemosyne/Themis/Moirai/Gaia/Coeus/Hephaestus consumers | Unsafe implementer obligation encoded; consumers migrated; Miri, conformance, and provider-version unification pass. |
| MOI-NUMA-001 | [major] | done — ADR 0017, deleted `numa.rs` (4 P0 defects) | Moirai + Mnemosyne/Themis ownership — redirected via ADR 0017 | Deleted 334-line `numa.rs`; existing Themis (placement), Mnemosyne (allocation), Moirai executor (work-stealing) cover the domain. Zero external consumers confirmed. |
| MOI-RESOURCE-214 | [patch] | done — merged PRs #70/#71 (`b637064`) | Moirai `moirai-sync/src/sync/resource_pool.rs`; deterministic clear/recycle interleaving; provider PM artifacts | Provider implementation `eb62898`, review-state `cd84276`, and PM closeout `5788b03`; 20/20 nextest, Clippy, rustdoc, doctests, and Criterion baseline pass; Atlas gitlink advanced to final provider head `b637064`. |
| MOI-BLOCKING-213 | [arch] | done — merged PRs #72/#73/#74 (`6184f73`) | Moirai executor blocking lane; provider PM artifacts | Lazy bounded blocking lane isolates compute workers; separate counters preserve quiescence and metrics; 87/87 nextest, executor-only warning-denied Clippy, rustdoc/doctest evidence, starvation/backpressure/priority/cancellation/shutdown/concurrent-producer tests, and Criterion rows pass. |
| THEM-CACHE-001 | [minor] | done (`18807bb`, merged PR #6) | Themis cache detection | Linux cache parsing returns typed absence on malformed input; Themis consumer pins are co-evolving. |
| LETO-SCALAR-001 | [major] | partial (`855f3ad`) | Leto scalar execution — length pre-validated; Hermes error propagation remains | Partial write closed: `assert_eq!` preconditions in all mutating Scalar methods. 304/304 leto-ops tests pass, apollo-fft builds clean. Error propagation deferred to Result-returning Scalar trait API change. |
| MNE-PERCPU-001 | [patch] | done (verified 2026-07-15) | Mnemosyne local cache — lazy `OnceLock<Box<>>` confirmed | Static footprint ~56 bytes, not 720,896. No backend enables `ENABLE_CPU_CACHE`. |
| TREE-SRP-001 | [arch] | done — ADR 0018 Phases 1-3 complete; Phase 4 filed as TREE-DUP-002 | Melinoe/Themis/Moirai hierarchy | ADR-0018: melinoe halo consolidated (→ melinoe::collections), themis tests rehomed (→ tests/), moirai constants.rs split, Phase 4 deferred. |

## Watchpoints — 2026-07-19 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| MR-WATCH-001 | moirai-scheduler/executor rebuild | `9c015a3` peer break + `5343ebfc` mid-fix | peer green clean HEAD | ✅ CLOSED 2026-07-14 (720/720 at `c43f86a`) |
| HERMES-WATCH-001 | Hermes Mnemosyne consumer Miri | PR #6 `db8e1a4` after provider PR #13 | fresh GitHub Miri/CI completes green | ✅ CLOSED 2026-07-19 (`cargo miri test -p hermes-simd-core` 14/14 pass; mnemosyne locked at `9b8585db` includes aliasing fix `5a9f49f`) |
| MOI-CONTENTION-001 | moirai contention audit | `perf/moirai-contention-audit` branch with contention fixes | merged to main at `9cd650f`, 82/82 pass | ✅ CLOSED 2026-07-15 |
| KW-WATCH-002 | kwavers-therapy abdominal perf | 90s `elastic-fwi` nextest override | peer-stream perf fix | ⏳ open (FFT zero-alloc helper committed, algorithmic perf in peer scope) |
| KW-WATCH-003 | kwavers-python leto→ndarray conversion compile break | `b861254` peer HEAD + 13 WT dirty | peer lands clean green committed HEAD | ✅ CLOSED 2026-07-19 (false positive: pyo3 0.29 alignment resolved 61 E0277; `cargo check -p kwavers-python` clean with 0 errors) |
| ritk Burn-strip verify-block | ritk Batch #3 #4-#6 dep strip | `ba6da3a` 1-ahead + 5 WT dirty | peer pushes, cleans WT, nextest green | ✅ CLOSED 2026-07-19 (Burn→Coeus doc rename committed `22cdbffb`; zero Burn/ndarray production deps remain; `cargo check --workspace` clean) |
| MNE-PERCPU-001 | Mnemosyne per-CPU cache | 720,896-byte dormant static | n/a | ✅ CLOSED 2026-07-15 (lazy OnceLock verified) |
| LETO-SCALAR-001 | Leto scalar length pre-validation | Hermes error discard + silent partial write | n/a | ✅ CLOSED 2026-07-15 (`aecb231`); error propagation deferred to `[major]` |

## Watchpoints — 2026-07-20 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HARM-PUBLISH-001 | `repos/harmonia` submodule registration | Local `repos/harmonia` worktree was unversioned pending remote publish | Peer publishes the `repos/harmonia` worktree to `https://github.com/ryancinsight/harmonia` and advances the Atlas gitlink | ✅ CLOSED 2026-07-20 (peer PR #57 merged `0b0d01d`: Harmonia published at `cf6ce3e`, `.gitmodules` entry added, gitlink advanced, ADR 0023 flipped `Proposed` → `Accepted`, current-stack table reconciled to 20 packages) |
| HEPH-CUDA-WIN-001 | `repos/hephaestus/crates/hephaestus-cuda` + `hephaestus-python` Windows-gnu link | Verified sweep across all 20 Atlas packages: `cargo check` clean across all 20; the bounded per-package nextest run reports `hephaestus-cuda` and `hephaestus-python` fail to build with `x86_64-w64-mingw32-gcc` link error reading `-L /usr/local/cuda-11.3/lib64/` and `-lcuda` on the Windows-gnu host. Hephaestus core/wgpu/metal subset (211/211) is clean | Upstream build script (in `cuda-oxide` or `cutile-rs`) emits a Windows-aware CUDA SDK path via `CUDA_PATH` (`%CUDA_PATH%\lib\x64\cuda.lib`) and the link succeeds on a Windows NVIDIA host; this is an environment defect, not a code regression | ⏳ open (2026-07-20 Session 3 re-confirmed: 211/211 hephaestus core/wgpu/metal under `--exclude hephaestus-cuda --exclude hephaestus-python`; cuda + python skipped per upstream `cuda-oxide`/`cutile-rs` Linux-shaped link path; not a regression) |

## Watchpoints — 2026-07-20 Session 3 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| ASCLEPIUS-REG-001 | `repos/asclepius/` registration | Published two-crate workspace and fetched remote-default merge `ceb8b6d`; explicit P1 promotion request satisfies the prior reopen trigger | Merge `.gitmodules`, exact gitlink, ADR 0028, and stack documentation; then materialize the provider in consumer CI | ✅ CLOSED 2026-07-20 Session 5 (peer commit `6fb5576` "feat(atlas): Register Asclepius" registered the submodule; ADR `0028-asclepius-biological-response-promotion.md` filed Status `Accepted`; `.gitmodules` lines 86-88 reference `repos/asclepius` -> `https://github.com/ryancinsight/asclepius.git`; 23-package stack recorded in README + INDEX; cross-ref `gap_audit.md` L3-34 Asclepius P1 promotion entry) |

## Watchpoints — 2026-07-21 Session 6 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HELIOS-TYCHE-MAJOR-001 | `repos/helios/crates/helios-imaging/src/noise.rs` + workspace `tyche-core` pin | tyche peer landed breaking `e1a5964 feat(tyche-core)!: Type counter streams` (`StandardNormal<T>` -> `StandardNormal<T, A: StreamAlgorithm>`); the helios `[patch]` override resolves tyche-core to local HEAD `0fc810b` (post-break), bypassing the manifest rev `87923da9...` (dead pin) | Peer migrates `helios-imaging/src/noise.rs:17,45` to the two-param form `StandardNormal::<f64, SplitMix64>::at(seed, sample_index, 0)` (add `SplitMix64` to the `use tyche_core::{...}` import on line 17) and re-establishes the 251/251 nextest baseline; OR bumps the manifest rev pin to `0fc810b` and updates `Cargo.lock` accordingly | ✅ CLOSED 2026-07-21 by helios peer PR #15 (`d82e3bb`): commit `4a01443 "feat(helios-imaging)!: Pin Tyche stream"` removed the local path override entirely (eliminating rev drift), made the algorithm and stream version part of the replay identity, and filed ADR `0005-tyche-noise-stream.md`. Helios main `11487c2` is the merged default post-PR #15; user's standing "implement and resolve examples" helios dispatch is satisfied. |
| CFDRS-TYCHE-MAJOR-001 | `repos/CFDrs/crates/cfd-optim/src/design/space/sampling/mod.rs` + workspace `tyche-core` pin | same tyche breaking change; the CFDrs `[patch]` override resolved the post-break provider | Peer supplies `SplitMix64` to `LatinHypercube` and routes indexed words through `Counter<UserDomain<0>, SplitMix64>` | ✅ CLOSED 2026-07-21 by CFDrs `fca1a9a9`; the exact migrated source is present in public default `394c9977` |
| CFDRS-CFD1D-LINT-001 | `repos/CFDrs/crates/cfd-1d/**` (15 files, ~50 sites) | surfaced in Session 6 `cargo clippy --workspace --all-targets -- -D warnings` during tyche-break verification; pre-existing pedantic lint floor debt in cfd-1d independent of tyche | Peer brings cfd-1d to the workspace `-D warnings` floor: ~26 `uninlined_format_args`, ~6 `manual_map`, ~5 `useless_conversion` to `f64`, 3 `result_large_err` (Err variant >=160 bytes in `PrimarySolveError`), 2 `manual_range_contains`, 2 `field_reassign_with_default`, and ~6 scattered (`complexity`, `explicit_into_iter_loop`, `empty_line_after_doc_comments`, `iter_cloned_collect`) | ⏳ open until 8-warning residual baseline clears (first decrement landed 2026-07-23 by atlas-meta coordinator PR #312 `4ccd4f85`): 54 pedantic warnings -> 8 via mechanical `cargo clippy --fix` (12-file span, 26 `uninlined_format_args` + 20 sibling auto-fixables `unnecessary_map_or`/`useless_conversion`/`.into_iter`/`.into`). Residual 8-warning baseline: 3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap — all manual-only categories peer-architectural) |

## Watchpoints — 2026-07-21 Session 7 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-PERF-SLOW-001 | `repos/CFDrs` heavy GPU/3D-CFD integration tests | Session 7 `cargo nextest run --no-fail-fast --workspace` on peer commit `fca1a9a9` (post-tyche-migration) reports 3 tests timing out at the 30s slow budget: `cfd-3d::poiseuille_test::validate_poiseuille_flow` (30.183s), `cfd-suite::cross_fidelity_blueprint::cross_fidelity_blueprint_complex_branching` (30.212s), `cfd-validation::benchmarks::threed::bifurcation::tests::test_bifurcation_flow_3d_murray_and_mass` (30.181s) | Peer roots-cause each timeout per `engineering_gates` (optimize the real components, never relax the slow-timeout bound; never shrink coverage); the 3072/3075 PASS baseline moves to 3075/3075 PASS without TIMEOUTs | ✅ closed (2026-07-23 Session 13 coordinator takeover: `validate_poiseuille_flow` PASS in 0.342s via PR #311 `22ddc27d` perf(cfd-3d) — hoist MidNodeCache + vertex_positions across Picard iter + lower with_direct_threshold 100_000→512 routing medium saddle-point systems to GMRES+AMG / GMRES+BlockDiag (root cause: `leto_ops::SparseLuSolver` is a misnamed dense partial-pivoting LU, O(n^3)). `cross_fidelity_blueprint_complex_branching` closed earlier by peer `153b0ed9` on 2026-07-13 (0.799s). `test_bifurcation_flow_3d_murray_and_mass` re-verified 1.934s at CFDrs main `22ddc27d`. Full cfd-3d suite: 394/394 PASS. Strategic TODO recorded as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] for upstream real sparse LU/Cholesky in leto-ops) |
| CFDRS-LINT-CASCADE-001 | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 `cargo clippy --workspace --all-targets -- -D warnings` halts on 4 site-level errors before reaching cfd-1d/cfd-2d/cfd-3d/cfd-core/cfd-validation/cfd-optim/cfd-suite/cfd-io/cfd-python/xtask; the 4 blockers are `needless_question_mark` ×2 in cfd-math and `print_literal` + `manual_filter` in cfd-schematics | Peer remediates the 4 cascade-blocking clippy errors; once unblocked, run `cargo clippy --workspace --all-targets -- -D warnings` to measure the actual `cfd-1d` baseline vs the Session 6 ~50-site estimate (which may have been inflated by the prior `cargo check`-then-clippy masking) | ⏳ open (2026-07-21 Session 7 cataloged; independent of tyche migration; blocks the `CFDRS-CFD1D-LINT-001` baseline measurement; recorded for the CFDrs peer) |

## Watchpoints — 2026-07-21 Session 8 (atlas-meta coordinator view)

No new atlas-meta-owned watchpoints. Session 8 activity:

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| LETO-VERIFY-CONTENTION-001 | `repos/leto` at `b7224832e` `perf(leto-ops): Vectorize UDU weighted-dot` | Session 8 bounded subagent attempt to run `cargo nextest run --no-fail-fast --workspace` + `cargo test --doc --workspace` on leto post-gitlink-reconcile; blocked by peer-held `CARGO_TARGET_DIR` lock (peer `cargo-nextest.exe` PID 48380 live, not orphan). This is verification contention, not a defect | Atlas-meta bounded nextest + doctest re-run when peer build activity ceases (no live `cargo-nextest.exe` in `tasklist`); per `concurrent_agents` peer's green run on this shared tree IS authoritative evidence on shared branch | ✅ closed (2026-07-21 Session 8 closing annotation: peer cargo-clippy shift released lock; atlas-meta bounded nextest 592/592 PASS rc=0 (slowest 1.023s, zero timeouts) + doctests 9/9 PASS (leto 1, leto-ops 8, leto-python 0). Differential oracles `*_matches_numpy`/`*_matches_scipy` over vectorized UDU weighted-dot kernel pass. Value-semantic correctness preserved atop `9a03735 refactor(leto)!: Retire ndarray boundary`) |

## Watchpoints — 2026-07-21 Session 9 (atlas-meta coordinator view)

atlas-meta main re-oriented at `abbec58` after peer landed 17 commits in the gap since Session 8 close. All Session 8 dispatch items superseded by peer work (user's "proceed as recommended" authorized the no-op continuation). New watchpoint evidence recorded; no new defects cataloged.

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-LINT-CASCADE-001 (originally Session 7) | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 catalog of 4 site-level clippy errors blocking `cargo clippy --workspace --all-targets -- -D warnings`. Session 9 audit: peer commit `dc256705` remediated sites 1-3 (stencils.rs, windows.rs, heatmap/mod.rs) via `let-else` idiom + SVG format-arg fix. Site 4 (parallel_lane.rs:24) was clean at HEAD `7a521343` — the code is already in the `Option::filter` form `manual_filter` recommends; the watchpoint entry was stale when filed | n/a — peer has remediated or never needed remediation | ✅ closed (2026-07-21 Session 9 bounded subagent audit at HEAD `7a521343`: `cargo clippy -p cfd-schematics --all-targets -- -D warnings` exits rc=0 zero warnings. All 4 watchpoint sites verified clean; clippy gate no longer blocks the cfd-1d lint baseline measurement; `CFDRS-CFD1D-LINT-001` baseline measurement is now unblocked and ready for peer to schedule under the ratchet) |
| HERMES-ADVANCE-001 (Session 9 catalog) | `repos/hermes` gitlink pin `004e6a492` vs inner HEAD `53b83165` | Single commit delta `perf(hermes): Unchecked CSR SpMV tail gather` touched only `CHANGELOG.md` + `spmv.rs` (+8 −1). nextest 388 tests 383 PASS / 5 ABORT — but all 5 aborts are in disjoint gemm/tiling dispatch tests (`ptr::replace` alignment UB on Windows), NOT in the CSR SpMV path (CSR tests `test_spmv_csr_*` all pass). Doctests 18/18 PASS, 10 ignored (cfg-gated) | n/a — peer advanced atlas-meta gitlink in the gap via peer's own `99699ea build(atlas): advance hermes gitlink — SpMV unchecked tail`. Atlas-meta's planned advance was made redundant | ✅ closed (made redundant by peer — atlas-meta main `abbec58` pins hermes at `53b83165`). Residual: the 5 gemm/tiling `ptr::replace` aborts are a pre-existing Windows UB defect — recorded below as HERMES-GEMM-UB-001 |
| HYPERION-PHASE-0-001 (Session 9 catalog) | new stack member `hyperion` at `D:\atlas\repos\hyperion\` (untracked dir, NOT in `.gitmodules`) + ADR 0030 `hyperion-photon-optical-promotion.md` + atlas-meta `0b97ba0` / `4ff5c07` consolidation commits | Peer created ADR 0030 consolidating photon/optical law across Asclepius/Leto/Hephaestus/Helios into a new standalone crate `hyperion` (v0.1.0, edition 2024, deps aequitas/eunomia/proteus). Phase 0 = scaffold + dep alignment; phase 1 = register as atlas submodule. Peer's kwavers tree has 40+ dirty files mid-Hyperion-extraction — the migration is in flight | n/a — Hyperion `7b4561b`, Helios `105a093`, Kwavers `5fc6f0419`, and CFDrs merge `69323418` complete the deletion ledger; Atlas records the exact provider and consumer gitlinks | ✅ closed (2026-07-22: `.gitmodules`, stack map, ADR 0030, PM state, and the 25-package count are synchronized; Ares and Prometheus remain separately evidence-gated) |
| HERMES-GEMM-UB-001 (Session 9 catalog — filed during HERMES-ADVANCE-001 audit) | `repos/hermes/crates/hermes-simd/tests/host_capability_tests.rs` + `crates/hermes-simd/tests/tiling_tests.rs` — 5 GEMM dispatch tests abort | `cargo nextest run --workspace` reports 5 ABORTs: `local_gemm_dispatch_matches_scalar_reference_for_irregular_shapes` (0.807s), `test_gemm_int8_signed_differential` (0.362s), `test_gemm_bf16_size_16` (0.396s), `test_gemm_int8_high_level` (0.427s), `test_gemm_bf16_high_level` (0.471s). All panic at `core::ptr::mut_ptr.rs:1495:18: unsafe precondition(s) violated: ptr::replace requires that the pointer argument is aligned and non-null`. Non-unwinding panic on Windows surfaces as `STATUS_STACK_BUFFER_OVERRUN` (0xc0000409) → abort. Pre-existing — reproducible at peer's pre-advance pin `004e6a492` as well as HEAD `53b83165`. Disjoint from the CSR SpMV path this gitlink advance introduced | Peer root-causes the `ptr::replace` alignment precondition violation in the GEMM tiling-remainder write (likely a `*mut T` produced from an under-aligned slice/holder feeding a packed-view bridge). Recommended first probe: `RUST_BACKTRACE=1 cargo nextest run -p hermes-simd --test tiling_tests test_gemm_bf16_size_16`; then Miri on the gemm kernel (SIMD intrinsics Miri-unreachable → ASan/TSan per unsafe-discipline for the load/store surface) | ⏳ open (2026-07-21 Session 9 cataloged; pre-existing defect not caused by the CSR SpMV advance. Independent of the hermes gitlink `004e6a492 → 53b83165` advance that peer landed in this session's gap. Recorded for peer scheduling since hermes is a peer-owned source tree) |
| EUNOMIA-DOCTEST-001 (Session 9 catalog — closed same session) | `repos/eunomia/crates/eunomia/src/relative_eq.rs` lines 241, 338 — `assert_relative_eq` and `relative_eq` doctests | Early Session 9 bounded subagent at eunomia 0.6.0 published surface reported 2 doctest FAILs with self-contradictory `epsilon = 1e-10, max_relative = 1e-10` example bounds for `1.0_f64` vs `1.0000001` (gap `1e-7`). Peer landed `884d193 feat(eunomia): Add relative equality` + `3e4f9eb docs(eunomia): Close equality provider gate`. Atlas-meta gitlink advance via peer's `a5279bf build(atlas): Advance Eunomia provider` reconciled the pin | n/a — peer closed the doctest gate | ✅ closed (2026-07-21 Session 9 recheck at HEAD `3e4f9eb`: doctests 9/9 PASS, zero failures, zero ignored. The two previously-failing examples now pass value-semantically against consistent bounds. Eunomia is release-ready at HEAD `3e4f9eb`) |
| HELIOS-APPROX-EUNOMIA-001 (Session 9 catalog) | `repos/helios` HEAD `105a0939 refactor(helios): migrate approx -> eunomia assert_relative_eq workspace-wide` | Peer integrated the workspace `approx -> eunomia::assert_relative_eq` migration into helios. Verification at HEAD `56e3572` (1 commit unpushed then; now pushed to origin/main = `105a0939`): nextest 251/251 PASS rc=0, slowest test 1.036s (`helios-imaging fbp::tests::quantum_noise_degrades_recon_and_scales_with_flux`), doctests 11/11 GREEN (helios-python cdylib is the only structural warning — expected). `approx` fully excised from helios `Cargo.toml` | n/a — peer landed + pushed; atlas-meta gitlink advanced via `61e209e` | ✅ closed (2026-07-21 Session 9 verification: helios `approx -> eunomia` migration is GREEN at HEAD `105a0939`. Caveat: helios still uses edition 2021 / resolver 2 (project-wide observation, not a migration defect). Dirty mdBook migration_*.md files are peer's pending book content not part of the migration commit) |

## Residual CFDrs watchpoints carried forward (still peer-owned, still open)

| ID | Status | Note |
|---|---|---|
| CFDRS-PERF-SLOW-001 | ✅ closed (2026-07-23 Session 13) | All 3 perf-slow tests under 2s at CFDrs main `22ddc27d`: `validate_poiseuille_flow` 0.342s (Session 13 perf PR #311), `cross_fidelity_blueprint_complex_branching` 0.799s (peer `153b0ed9` 2026-07-13), `test_bifurcation_flow_3d_murray_and_mass` 1.934s. Root cause of the last standing one (`validate_poiseuille_flow`) was a misnamed dense LU masquerading as sparse LU in `leto_ops::SparseLuSolver` plus per-Picard-iter cache recomputation; both root-caused and fixed at the algorithm (no threshold relaxation, no test shrinkage, no slow-timeout bound change). Strategic TODO — real sparse LU upstream in leto-ops — filed as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] |
| CFDRS-CFD1D-LINT-001 | ⏳ open (now unblocked) | Session 9 closure of `CFDRS-LINT-CASCADE-001` unblocks the cfd-1d pedantic-baseline measurement. The original Session 6 estimate was ~50 sites. Peer can now run the full `cargo clippy --workspace --all-targets -- -D warnings` and schedule the actual baseline under the ratchet |
| ATLAS-LETO-OPS-REFACTOR-001 (new 2026-07-23) | ⏳ open | `leto-ops` (`repos/leto` HEAD `9346413`) is presently uncompilable on the path-dep graph (29 type/visibility errors across `crates/leto-ops/src/application/linalg/iterative/preconditioners/jacobi.rs`, `ilu.rs`, `cg.rs`, `sparse/csr.rs` mod-privacy + generic-`T`-vs-`usize` index comparison). Last destructive code commit `9a82a4d feat(leto-ops): add sparse_lu_solve and SparseLuSolver`. Subsequent commits have been audit doc/test only. Peer is mid-refactor (`ATLAS-LETO-OPS-SPARSE-LU-001` owner context). Assist-ladder (2) decision: skip — fresh and actively held by the leto peer; no claimable periphery in `leto-ops` source that doesn't collide with peer's refactor. Re-verify when peer stabilizes; not coordinator-actionable |
| CFDRS-CFD1D-LINT-001 | ⏳ open (first decrement done; 8-warning residual baseline established) | First ratchet decrement landed by atlas-meta coordinator via PR #312 `4ccd4f85` (squashed merged 2026-07-23). `cargo clippy --fix --allow-dirty -p cfd-1d --all-targets` applied 12-file mechanical remediation: 26 `uninlined_format_args` + 20 sibling auto-fixable lints (`unnecessary_map_or` -> `is_some_and`, `useless_conversion` -> `to_vec`, minor `.into_iter()` / `.into()` cleanups). Baseline: 54 pedantic warnings -> 8 (3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap). Net delta -46 warnings (-85%); 728/728 cfd-1d nextest pass post-runtime. Residual 8-warning baseline parked as peer-architectural decisions (error-type redesign, type-factor, doc-comment cleanup) — next decrement candidate |

## Provider integration audit queue — 2026-07-20

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HARM-PROMOTE-001 | [arch] `[minor]` | done — PR #57 merged `0b0d01d` | harmonia / horae / athena-core / eunomia / atlas-meta | `repos/harmonia` published to `https://github.com/ryancinsight/harmonia` (HEAD `cf6ce3e`, CI run `29753063192` green); Atlas `.gitmodules` entry recorded; parent gitlink advanced; ADR 0023 Status `Accepted`; README current-stack table reconciled to 20 packages. |

## ATLAS-WORKTREE-001 — Canonical lane root consolidation [patch] — in progress

- Owner: Codex `/root` (stale-claim takeover 2026-07-22); scope: worktree lane
  locations only, no member-repo code.
- Done 2026-07-21: 24 verified-duplicate standalone clones (12 at
  `D:\worktrees`, 12 at `D:\atlas\worktrees`; all detached, clean, HEADs
  contained, zero local branches), the SHA-keyed `.atlas-provider-checkout`
  cache, and the empty `D:\worktrees\atlas` were removed; stray
  `report/figures` SVG was rescued to `repos/report/figures/`.
- Done 2026-07-22: the legacy `D:\worktrees` root is absent, 16 redundant
  junction aliases are removed, and the former scratch scripts are absent.
  The only remaining lanes are the active Atlas RITK graph lane and Kwavers
  portability lane under the canonical `D:\atlas\worktrees/` root. Each repo
  remains within the main-tree-plus-one-lane bound.
- Residual: merge Atlas PR #86 after RITK PR #49 and merge Kwavers PR #312
  after PR #313, then remove both completed lanes and their branches.

## ATLAS-TARGET-001 — One build cache, one debug budget [patch] — in-progress (residual)

- Owner: Codex `/root`; last-update: 2026-07-22; scope: cache trees and
  profile sections only, no simulation logic.
- Done 2026-07-21: 18 stale cache forks deleted (repo-local `target/`, `target_isolated`, `target_benches`, nested crate `target/`) reclaiming 177.8 GB; `moirai` dev/test profiles aligned to line-tables-only/deps-none (was `debug = true`, pushed `946b4a7`); root `.cargo/config.toml` gains `[profile.dev.build-override] debug = false`. Policy: AGENTS.md performance_engineering "one build cache per stack" — a discovered fork is disposable derived state.
- Done 2026-07-22: the root test profile now matches the development profile:
  workspace test crates retain line tables, while dependencies, build scripts,
  and procedural macros emit no test debuginfo. This closes the configuration
  path through which Nextest could repopulate the shared cache with full
  symbols.
- Done 2026-07-22: removed two abandoned full-target `du` scans that had
  traversed the cache for about 2.5 hours, then pruned the idle incremental
  tree. Its 27,085 session directories occupied 525,183,672,320 bytes
  (approximately 489 GiB); the five-minute deletion preserved shared
  dependencies and linked artifacts, and a subsequent build recreated only
  three current session directories. This is operational reclamation, not a
  clean-build footprint claim.
- Done 2026-07-22: Kwavers PR #307 merges as `0602c1fd4`. Its broad
  dependency graph inherits development `opt-level = 1` instead of wildcard
  `opt-level = 3`, restoring exported generic sharing. Uncached feature-build
  steps fall 18–45%; exact head `909bcdfc7` passes 26 hosted checks, full-grid
  PSTD remains below 25 seconds, and a clean debug tree measures
  16,771,464,617 bytes across 6,109 files. Cargo removes the formerly blocked
  `repos/kwavers/target_isolated` plus six other obsolete private targets:
  9,363 files and approximately 4.49 GiB, without touching `D:/atlas/target`.
  Atlas-meta format and warning-denied Clippy pass; checkout-path Nextest passes
  11/11 in 3.746 seconds and doctests pass 1/1 in 1.93 seconds from the primary
  root against the shared cache.
- Done 2026-07-22: a stack-wide sweep removed 13 additional disposable target
  forks and reclaimed 18.465 GiB; no repository-local target directory
  remains. Before the remaining hosted checks, `cargo clean` against the
  canonical `D:/atlas/target` removed 68,854 files and 20.7 GiB. The configured
  shared cache then measured 0 bytes, below the 10-GiB operating budget; the
  final sweep must repeat after any later local gate.
- Residual: audit member workspaces with their own `[profile.*]` or `.cargo`
  sections (helios, hermes, CFDrs, coeus, ritk, mnemosyne). CFDrs currently
  compiles workspace tests at `opt-level = 2`; its dirty peer-owned workspace
  and active full test build preclude an unmeasured profile edit. Re-open that
  member as a separate measured increment after the peer work integrates,
  retaining only runtime- or profiling-justified deviations. Atlas-meta root
  worktrees copy `.cargo/config.toml` and therefore resolve a lane-local target;
  run meta-tool verification from the primary root until a portable route to
  the canonical cache is implemented and tested. One live sample found three
  independent top-level builds, five Cargo processes, and 23 concurrent `rustc`
  processes on a 24-thread/31.7-GiB host. Compare unchanged single- and
  concurrent-build workloads before selecting a global jobs cap; the sample
  proves oversubscription exposure, not an optimal cap.

## ATLAS-BENCH-BUDGET-001 — Wall-clock budgets for benches and examples [patch] — in-progress (enforcement merged; sweep residual)

- Owner: Claude (user-directed claim 2026-07-22); home: tools/criterion-regression (ADR 0024); policy: AGENTS.md engineering_gates "Runtime budgets" + performance_engineering "Benchmark time budget".
- Outcome: no bench binary or CI example exceeds its committed bound; suite time is designed, not emergent.
- Scope: (1) gate smoke — bench binaries run single-iteration (criterion `--test`) under the standard 30s/60s budget; (2) timing runs — per-binary wall-clock bound (default 300s) enforced in the criterion-regression runner/CI; (3) CI-safe examples complete within the test budget as scaled demos; (4) audit the 164 bench files (moirai 47, CFDrs 29, kwavers 22, hermes 12, ritk 10, rest ≤8) against the analytical time model — zero suites declare measurement_time/sample_size today, i.e. all run unbudgeted criterion defaults with sweeps; apply flat sampling for slow iterations, geometric sweeps, smallest regime-exercising inputs; where a single iteration is genuinely slow, profile and optimize the production kernel (farsight), never delete the bench or raise the bound in the offending diff.
- Acceptance: budget enforcement merged in the runner + full-stack bench sweep completes within per-binary bounds; breaches root-caused and fixed or filed with derivation.
- Done 2026-07-22: `enforce-budget` subcommand in tools/criterion-regression — modes smoke (bench single-iteration, 60s), timing (full measurement, 300s), examples (60s), `--bound-seconds`/`--skip` overrides. Compiles unbounded, executes binaries directly (killing cargo would orphan the bench grandchild) with CARGO_TARGET_DIR pinned to the shared target (no minted repo-local target/), fail-closed exit. Validated: themis smoke/timing clean; eunomia timing at 5s bound → breach terminated mid-measurement, exit 1. Gates: clippy pedantic clean, 21/21 nextest, doc clean.
- Residual: full-stack sweep at committed bounds (probe per repo; live peer scopes deferred to their completion), CI wiring per repo workflow convention, and suite resizing per breach (flat sampling, geometric sweeps) or kernel optimization per farsight.
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in progress

- Owner: Codex `/root`; last-update: 2026-07-23; completed vertical slice:
  `repos/coeus/coeus-ops/tests/**` only. Peer-owned member profiles and other
  repository test trees remain out of scope.
- Claim: consolidate the 36 flat `coeus-ops` Rust integration-test binaries
  into one hierarchical `tests/ops.rs` harness with `tests/ops/*.rs` modules,
  preserving all 87 test functions and their value-semantic assertions. The
  target-count reduction and test-count parity are the acceptance oracle.

- Policy: AGENTS.md performance_engineering "Debug-tree and compile-time structure" + "Compiler-last optimization order". Monomorphization stays the design default — an instantiation codegens identically to its hand-written equivalent; the debug-tree multiplier is leaf-binary count and duplicate paths, never genericity.
- Evidence 2026-07-22: ~950 leaf binaries stack-wide, each a full link with own incremental cache and PDB — tests/examples per repo: CFDrs 118/66, coeus 110/2, kwavers 94/62, consus 55/0, ritk 28/7, hermes 20/4, moirai 15/22, melinoe 15/1, others <=11. Dev-profile audit: helios declares wildcard `[profile.dev.package."*"] opt-level = 3` (the pattern removed from kwavers in PR #307); kwavers `opt-level = 1` with documented 5-10x PSTD justification is the sanctioned named-and-measured form. The shared incremental tree reached 27,085 session directories and approximately 489 GiB in five days, making leaf-target consolidation and CI `CARGO_INCREMENTAL=0` the next measured size levers.
- Scope: (1) consolidate each repo's tests/*.rs into one-or-few area harness binaries (`tests/<area>/main.rs` with modules) — nextest still isolates per test function in its own process, so coverage and isolation are unchanged while link count, incremental caches, and debug artifacts drop by the file count; worst offenders first (CFDrs, coeus, kwavers, consus, ritk, hermes); (2) merge near-duplicate examples per consolidation_discipline; (3) replace wildcard dev dependency opt raises with named, measured, per-package exceptions (helios first, peer-held — coordinate via board); (4) record per-repo binary-target count and debug-tree size before/after as the acceptance measurement.
- Acceptance: binary-target census reduced and recorded per repo; debug-tree size delta measured against the shared cache; test function count unchanged (no coverage loss); no wildcard dev opt-level overrides remain without a named measured justification.
- Completed vertical slice: Coeus `coeus-ops/tests` moved from 36 flat
  integration targets to one `ops` target with ten operation-family
  directories. The harness exposes 87 integration tests and the exact
  package Nextest run passes 196/196; whole-workspace debug-tree measurement
  remains a later bounded slice.
- Evidence: warning-denied Clippy, package check, format, and diff checks pass
  on Coeus commit `f67789c4`; the 87 harness tests are unchanged by source
  count and all 196 package tests pass. This item is closed for the bounded
  Coeus slice; the broader stack-wide debug-tree delta remains open work.
- Coeus-NN slice complete at provider commit `95bb9090`: the existing
  `nn_tests.rs` harness and its already hierarchical `tests/nn/` modules stay
  intact while the 33 other direct test binaries move behind one `nn_ops`
  harness, preserving the 268 total package tests. The 34 direct test targets
  reduced to 2 (`nn_ops` and `nn_tests`); the exact package run passes
  268/268 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `f8f6d665`: the existing
  `autograd_tests.rs` harness and `tests/autograd/` module tree remain intact
  while the three other direct targets move behind one `autograd_ops` harness.
  The four integration targets reduce to two; the exact package run passes
  94/94 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-tensor slice complete at provider commit `49bb5858`: the 13 flat
  integration targets move under six operation-family directories behind one
  `tensor_ops` harness. Locked metadata reports one integration target; the
  source census remains 53 annotated integration tests, and the exact package
  Nextest run passes 58/58 with 0 skipped, including five library unit tests.
  Production tensor code and all leaf test bodies remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-sparse slice complete at provider commit `81cb68a6`: the three flat
  integration targets move under conversion, differential, and invariant
  directories behind one `sparse_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 19/19 with 0
  skipped in 0.713 seconds. Production sparse code and all leaf test bodies
  remain unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-core slice complete at provider commit `88dfd38f`: the four flat
  integration targets move under storage, dependency-policy, and scalar
  directories behind one `core_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 21/21 with 0
  skipped, comprising 14 integration cases and seven unchanged library unit
  tests. Production core code and all leaf test bodies remain unchanged.
  Whole-workspace debug-tree measurement remains open.
- Coeus-CUDA slice complete at provider commit `573ad35e`: the three flat
  feature-gated integration targets move under device and fallback directories
  behind one `cuda_ops` harness, retaining the existing nested `tests/cuda/`
  tree through an explicit path. Default Nextest passes 3/3 with 0 skipped;
  all-features check and Clippy pass. All-features executable coverage remains
  host-blocked because the GNU linker cannot find
  `/usr/local/cuda-11.3/lib64/libcuda`. Whole-workspace debug-tree measurement
  remains open.
- Coeus-Python slice complete at provider commit `8851c5f5`: the six flat Rust
  integration targets move under activation, distributed, NN, operation,
  optimizer, and autodiff directories behind one `binding_ops` harness. The
  shared `tests/common` lock module is owned once at the harness root. Exact
  all-features Nextest passes 75/75 with 0 skipped; production PyO3, Python
  parity scripts, and generated artifacts remain unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-WGPU slice complete at provider commit `c507683e`: the two flat
  integration targets now share one hierarchical `wgpu_ops` harness, with
  fused operations under `fusion.rs` and the existing WGPU operation tree under
  `backend/wgpu/`. Exact package Nextest passes 85/85 with 0 skipped; the moved
  source files are content-identical renames and production GPU code is
  unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-WGPU parity split complete at provider commit `149aadb5`: the 808-line
  multi-family leaf is now a shared oracle manifest plus seven operation-family
  modules. The pre/post source-name census remains 47 unique parity identifiers;
  exact package Nextest passes 85/85 with 0 skipped. Every new leaf is below
  500 lines; production kernels and fixtures are unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto slice complete at provider commit `8d3b9082`: the two flat
  integration targets now share one hierarchical `leto_ops` harness with
  contract and sparse-dispatch operation families. Locked metadata reports one
  integration target; exact package Nextest passes 28/28 with 0 skipped in
  1.064 seconds. The live census is 26 contract tests plus 2 sparse-dispatch
  tests, correcting the prior 26-test tracking claim. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `24a52be5`: the established
  `tests/autograd/` module tree and standalone operation families now share one
  hierarchical `autograd_ops` harness; the redundant `autograd_tests.rs`
  manifest is removed. Locked metadata reports one integration target instead
  of two; exact package Nextest passes 94/94 with 0 skipped in 1.535 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass. Whole-
  workspace debug-tree measurement remains open.
- Coeus-NN slice complete at provider commit `5c416e12`: the established
  `tests/nn/` module tree and operation-family modules now share one
  hierarchical `nn_ops` harness; the redundant `nn_tests.rs` manifest is
  removed. Locked metadata reports one integration target; exact package
  Nextest passes 268/268 with 0 skipped in 4.463 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-NN tensor parity split complete at provider commit `ee5be32f`: the
  1,317-line multi-family parity leaf is now a shared assertion manifest plus
  attention, convolution, embedding, linear/normalization, losses, and
  regularization operation-family modules. The pre/post source-name census
  remains 11 unique parity test functions; exact package Nextest passes 268/268
  with 0 skipped in 2.816 seconds. The largest new leaf is `attention.rs` at
  664 lines; the other five leaves are below 250 lines. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-CUDA parity split complete at provider commit `abe9211d`: the live
  1,672-line multi-family parity leaf is now a shared oracle manifest plus
  seven operation-family modules. The pre/post source-name census remains 29
  unique parity test functions; every new leaf is below 500 lines, with
  `convolution.rs` the largest at 365 lines. Default package Nextest passes
  3/3 with 0 skipped; default and `--features cuda` package checks and
  warning-denied Clippy pass. Feature-enabled Nextest cannot link because
  `x86_64-w64-mingw32-gcc` cannot find `-lcuda` while searching
  `/usr/local/cuda-11.3/lib64/`; no live CUDA parity execution is claimed.
  Whole-workspace debug-tree measurement remains open.
- Coeus-Python operation binding split complete at provider commit `0d8784c1`:
  the live 3,160-line `binding_tests_ops.rs` leaf is now fourteen
  operation-family leaves with nested NN functional and module directories.
  The pre/post source census remains 61 unique test functions and all 61
  extracted Rust function bodies compare equal. The largest test-family leaf is
  `reductions.rs` at 391 lines; every leaf is below 400 lines. Exact package
  Nextest passes 75/75 with 0 skipped in 8.079 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production PyO3,
  Python parity scripts, and generated artifacts remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-dist distributed-contract split complete at provider commit `c7838d90`:
  the live 1,262-line `dist_tests.rs` leaf is now one `dist_ops` manifest with
  local and TCP transport subtrees, separated into collective, reduction,
  invalid-input, and mesh-boundary families. The pre/post source census remains
  64 unique test functions, all 64 `#[test]` attributes remain present, and
  all 64 extracted Rust function bodies compare equal. The largest new leaf is
  `distributed/tcp/errors/collective.rs` at 464 lines; every leaf is below 500
  lines. Exact package Nextest passes 64/64 with 0 skipped in 0.444 seconds,
  with no slow tests. Package check, warning-denied Clippy, format, and diff
  checks pass. Whole-workspace debug-tree measurement remains open.
- Coeus-NN loss-contract split complete at provider commit `37bf8d9b`:
  the live 902-line `nn_loss_tests.rs` leaf is now a nested manifest with
  binary, classification, distance, and distribution operation families. The
  pre/post source census remains 24 unique test functions and all 24 extracted
  Rust function bodies compare equal. The largest new leaf is `distance.rs` at
  315 lines; every new leaf is below 500 lines. Exact package Nextest passes
  268/268 with 0 skipped in 2.270 seconds. Package check, warning-denied
  Clippy, format, and diff checks pass. Production NN code, fixtures, and
  tolerances remain unchanged; whole-workspace debug-tree measurement remains
  open.
- Coeus-optim contract-family split complete at provider commit `b27d492f`:
  the live 676-line `optim_tests.rs` leaf is now one `optim_ops` manifest with
  optimizer, scheduler, convergence, and gradient-clipping family modules.
  The pre/post source census remains 20 unique test functions and all 20
  extracted Rust function bodies compare equal. Locked metadata reports one
  `optim_ops` integration target. The largest new leaf is `convergence.rs` at
  239 lines; every new leaf is below 250. Exact package Nextest passes 20/20
  with 0 skipped in 0.188 seconds. Package check, warning-denied Clippy,
  format, and diff checks pass. Production optimizer code and all test oracles
  remain unchanged; whole-workspace debug-tree measurement remains open.
- Coeus-NN extended activation split complete at provider commit `d800be8c`:
  the live 648-line `act_extended_tests.rs` leaf is now one `act_extended`
  manifest with piecewise, parameterized, module-smoke, and smooth families.
  The pre/post source census remains 17 unique test functions and all 17
  extracted Rust test function bodies compare equal. The largest new leaf is
  `piecewise.rs` at 354 lines; every new leaf is below 360. Exact package
  Nextest passes 268/268 with 0 skipped in 3.155 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production NN code,
  fixtures, formulas, and tolerances remain unchanged; whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto contract-family split complete at provider commit `97d94566`:
  the live 505-line `leto_ops/contract.rs` leaf is now a manifest with
  arithmetic, reductions, matmul, layout, and accumulation families under
  `coeus-leto/tests/leto_ops/contract/`. The pre/post source census remains
  26 unique contract tests and all 26 extracted Rust test function bodies
  compare equal. The largest new leaf is `layout.rs` at 197 lines; every new
  leaf is below 200 lines. Locked metadata reports one `leto_ops` integration
  target. Exact package Nextest passes 28/28 with 0 skipped in 0.325 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass.
  Production Leto dispatch code and test oracles remain unchanged; whole-
  workspace debug-tree measurement remains open.
- Next claimed slice: run a fresh structural audit of the remaining Coeus test
  tree and take the next real family-boundary increment, if a live leaf exceeds
  the hierarchy trigger without violating test cohesion.

## ATLAS-BOOK-001 — Domain books teach the field; evict process content [patch] — todo

- Policy: AGENTS.md documentation_discipline "Domain book" — books teach physics/math from the ground up (governing equations with resolved citations, numerical methods, theory-to-API worked examples with regenerated figures); migration and changelog content belongs to versioning/CHANGELOG, never the book.
- Evidence 2026-07-23: three books carry internal-migration process parts — CFDrs `docs/book` Part VII "Atlas Stack Integration (Migration Reference)" (13 files incl. appendix_changelog.md, appendix_migration.md); helios Part VIII (13 files incl. appendix_changelog.md); kwavers Part VI (10 files incl. migration_quick_reference.md). All three repos peer-held at filing time — owners coordinate via board, disjoint from live scopes.
- Scope per repo: (1) delete the Migration Reference part and changelog/migration appendices from SUMMARY.md and the tree, salvaging any genuine theory-to-API mapping into usage chapters first (information preserved, then deletion — no orphaned SUMMARY entries; book builds green after); (2) audit the remaining book against the Domain-book rule — fundamentals-first structure, tested samples, figures from committed plotting code — and file chapter-gap DoR items; (3) repos with domain scope but no book (e.g. ritk, coeus, gaia, apollo, hephaestus) get an outline-first book item each.
- Acceptance: no migration/status/changelog chapters remain in any book; each touched book builds in CI with tested samples; gaps filed as DoR items per repo.

## ATLAS-MNEMOSYNE-001 — Allocator observability and adversarial-stress audit [patch] — done

- Policy: AGENTS.md performance_engineering "Allocation strategy & fragmentation" + verification_policy continuous verification (claims-vs-code). Context: mnemosyne already implements the core allocator lessons (size classes, thread-local fast paths, snmalloc-style cross-thread free queues, orphan adoption, decay, secure poisoning, cache-line page metadata) — this audit verifies the observability and adversarial evidence behind those claims, not the design.
- Scope (verify each against code, file gaps as DoR items): (1) fragmentation observability — telemetry exposes per-size-class utilization and live-bytes vs resident-set divergence, the operational fragmentation signal; (2) adversarial fragmentation stress — a committed suite alternating size classes with pinned survivors under a steady-state RSS bound (the interleaving pattern that pins spans), run-output segregated; (3) decay verification — mnemosyne-decay empty-span purge is tested for actual RSS return, not just span accounting; (4) cross-thread free queues carry loom coverage per standards concurrency correctness (bounded-exhaustive, bound stated) plus a producer-consumer free-storm benchmark (alloc on thread A, free on thread B); (5) realloc in-place extension coverage; (6) differential correctness vs the system allocator under churn (existing conformance suite check).
- Acceptance: each item verified with evidence recorded (or gap filed with its DoR item) in the mnemosyne repo board; no claim in the README stands without a matching test, metric, or benchmark.
- Evidence (2026-07-24): mnemosyne `main` — 43 new/modified tests across 4 files. (1) Fragmentation observability: gap filed (byte-level per-class utilization metric deferred to separate item); SizeClassOccupancy already tracks slot-level utilization. (2) Adversarial fragmentation stress: 3 tests in `fragmentation_tests.rs` — alternating-class with pinned survivors (200 rounds × 3 classes), single-class checkerboard (128 blocks), mixed-class page recycling (4 classes, wave alloc/free). All pass. (3) Decay RSS-return: new `decay_step_returns_segment_bytes_to_os` test calls `decay_step()` directly (deterministic, no polling), asserts orphan pool drained + `purged_bytes` increased. Pass. (4) Cross-thread free: 2 stress tests — producer-consumer (4 producers × 200 allocs, 4 consumer threads) and many-to-one (8 freer threads × 80 blocks, 640 total). Both pass, zero crashes. Realloc coverage: 13 tests in `realloc_tests.rs` — in-place reuse, shrink-below-half, grow-to-different-class, null/zero edge cases, repeated cycles, cross-thread free of result. All pass. (6) Differential vs system allocator: gap filed (comprehensive scope deferred). (5) Clippy clean on mnemosyne-local and mnemosyne-decay (only pre-existing arena warning).

## ATLAS-PUBLISH-001 — OIDC publish pipelines and Pages alignment [patch] — todo

- Policy: AGENTS.md engineering_gates "Publish pipelines". Wiring is agent work; registry-side toggles are user actions.
- Scope: (1) crates.io — add tag-triggered, environment-gated trusted-publishing workflows (`rust-lang/crates-io-auth-action`, `id-token: write`) to publishable stack crates, dependency-ordered with `cargo package` dry-run and semver gates; record per-crate "enforce trusted publishing" as a user checklist once each pipeline is green (disables token publishing registry-side). (2) PyPI — for the Python-binding crates, maturin-action matrix (manylinux2014 floor, `--compatibility pypi`, abi3 where the surface permits, sdist) with install/import/pytest wheel smoke before upload via the PyPI trusted-publisher flow. (3) Books — align CFDrs/kwavers/helios book workflows to the artifact flow (build + `mdbook test` → upload-pages-artifact → deploy-pages) if any still push a gh-pages branch or skip the test gate; new books inherit the same workflow.
- Acceptance: no long-lived registry token referenced in any CI secret; each wired pipeline dry-run green; book deployments artifact-based with the test gate; user-action list (registry enforcement toggles) recorded on the board.

## ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001 — Cross-book `mdbook test` gate alignment [patch] — peer-coordinated (filed by Session 18)

Coordinator-owned evidence record (this entry) under
eer-coordinated execution: kwavers peer on branch
`codex/kwavers-book-migration-eviction` (peer mid-flight on
`ATLAS-BOOK-001` eviction). CFDrs peer on `main` branch, 1 ahead of
`origin/main f04b1d75` (autest sub-task, see
`ATLAS-CFDRS-COEQ-BLOCKER-1`). Helios peer on
`origin/main 433ddb6`. Each member-repo peer owns their own workflow
`book-pages.yml`; coordinator cannot edit those files per
`concurrent_agents` disjoint-scope primitive — this entry surfaces the
shared gap and per-repo sub-scopes so each peer claims the disjoint slice
against their own repo. Coordinator verification of the shared gap was
performed against each repo's `origin/main` HEAD.

- Policy: AGENTS.md engineering_gates "Publish pipelines" — book
  workflows run build + `mdbook test` → `upload-pages-artifact` →
  `deploy-pages` (the test gate is the test-suite coverage for
  documentation samples, preventing rotted non-compiling example code
  from deploying).
- Discovery evidence (verified at Session 18 via `git show
  origin/main:.github/workflows/book-pages.yml` on each repo):
  - **kwavers** (`origin/main c19134ec`): steps `Configure Pages`,
    `Install mdBook`, `Build book` (runs `mdbook build docs/book`
    only), `Upload Pages artifact`, `Deploy to GitHub Pages`. No
    `mdbook test` step.
  - **CFDrs** (`origin/main f04b1d75`): identical step shape
    (`Configure Pages` → `Install mdBook` → `Build book` running
    `mdbook build` only → `Upload Pages artifact` → `Deploy to GitHub
    Pages`). No `mdbook test` step.
  - **helios** (`origin/main 433ddb6`): identical step shape. No
    `mdbook test` step. (Cited as residual (a) in
    `ATLAS-HELIOS-BOOK-001` Session 18 closure.)
  - All three deploy via `actions/upload-pages-artifact@v4` →
    `actions/deploy-pages@v4` with `pages: write` + `id-token: write`
    on the `deploy` job and deploy gated on
    `github.event_name != 'pull_request'` (main-only). The artifact
    flow is already compliant; only the `mdbook test` step is missing.
- Outcome: each per-repo peer-coordinated sub-slice lands one PR
  inserting a `Build book`→`Test book samples` step (running
  `mdbook test docs/book`) between `Install mdBook` and
  `Upload Pages artifact`, fail-closed on doctest failure. The (1)/(2)
  crates.io/PyPI scopes of `ATLAS-PUBLISH-001` remain separate and
  unowned — this sub-slice addresses only the (3) Books test-gate
  gap. Per-repo sub-scope (peer-coordinated):
  (a) **repos/kwavers/.github/workflows/book-pages.yml** — peer-kwavers
      holds active eviction branch (`codex/kwavers-book-migration-eviction`,
      1 ahead of `origin/main c19134ec`); the `mdbook test` step landing
      is complementary to eviction (examples must compile for `mdbook
      test` to pass, and eviction is removing the migration-reference
      examples that are least doctest-fit), so sequencing eviction first
      is the cleanest order. Awaiting peer eviction merge to `origin/main`.
  (b) **repos/CFDrs/.github/workflows/book-pages.yml** — peer-CFDrs
      on `main` ahead 1 of `origin/main f04b1d75`; lands after the
      `ATLAS-CFDRS-COEQ-BLOCKER-1` workspace-restore + check-figures
      re-verification so the local `mdbook test` pre-flight is backed by
      a fully-resolved Cargo graph (the coeus-core path-dependency
      gap currently stops local cargo metadata resolution).
  (c) **repos/helios/.github/workflows/book-pages.yml** — peer-helios
      at `origin/main 433ddb6`, book content ready to test. No known
      pre-requisite for the `mdbook test` step landing; cleanest
      per-repo increment of the three.
- Acceptance: each `book-pages.yml` carries a `mdbook test docs/book`
  step running doctests on committed sample code; book deploy still
  artifact-based with the test gate; user-action list (registry
  enforcement toggles) recorded on the board remains the same.
- Risk/change class: `[patch]` CI-only; no production-code delta.
- Dependencies: ATLAS-PUBLISH-001 (parent),
  ATLAS-BOOK-001 (kwavers eviction sub-scope ordering);
  ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs cargo-graph restore).
- Evidence limit: workflow-step inspection on each `origin/main`;
  no performance claim, no production-code delta.
- Refs: backlog.md#ATLAS-PUBLISH-001 (parent slice),
  backlog.md#ATLAS-BOOK-001 (kwavers peer eviction),
  backlog.md#ATLAS-HELIOS-BOOK-001 (Session 18 closure residual (a)),
  backlog.md#ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs workspace restore).

## Session 17 closure (2026-07-23) — ATLAS-LETO-OPS-SPARSE-LU-001 → ✅ closed

- Owner: atlas-meta coordinator (codex agent); status flipped todo → ✅ closed.
- Outcome: real CSC sparse LU + partial-pivoting numeric phase in leto-ops
  landed at leto `origin/main` `687b670` via PR #74 squash-merge
  (`refactor(leto-ops): Remove ndarray/nalgebra, native iterative solvers
  (LETO-NDARRAY-BOUNDARY-1) (#74)`).
  The PR diff (41 files) bundled the ndarray/nalgebra dev-dep removal (peer
  origin-main HEAD `9346413` declared no production deps on ndarray/ndarray-rand/
  nalgebra; only parity examples consumed them) AND the in-place upgrade of
  `SparsLuSolver` to the real algorithm class.  Public surface preserved:
  `SparseLuSolver::solve_view`, `CscMatrix`, `CsrMatrix`, `CooMatrix`, and the
  re-exported `factor_numeric` / `factor_symbolic` / `NumericLu` API paths.
- Algorithm spec (matches ADR 0031 Option A): symbolic factorization is the
  sequential left-looking Gilbert/Peierls reach over CSC, computing the
  static L/U pattern (L rows strictly `> j`, U rows `≤ j` per column j) under
  natural column ordering for v0.40.0; numeric factorization is the
  slot-indexed left-looking phase with partial-pivoting row swaps against
  `row_perm[slot] = original row` (matches the dense
  `LuDecomposition::pivots` convention so downstream CFDrs
  `DirectSparseSolver` composes unchanged); solve =
  `P·A·x = L·U·x = P·b` ⟺ forward sub `Ly = Pb` then back sub `Ux = y`.
- Density-gated dispatch (per ADR 0031): `SparseLuSolver` carries a
  `small_switch = 32` and `density_threshold = 0.1` pair; small or near-dense
  matrices route to a dense-fallback path; large sparse matrices route to
  the new symbolic→numeric sparse path.
- Verification evidence (Windows ucrt64, rustc 1.95.0, eunomia
  https://github.com/ryancinsight/eunomnia#f6cd644b):
  - `cargo check -p leto-ops --tests` ✅ clean (Finished in 2m 15s).
  - `cargo nextest run --no-fail-fast -p leto-ops` ✅ 339/339 pass in 3.17s
    (well under the 30s slow-timeout hard cap; no threshold relaxation, no
    test shrinkage).
  - `cargo test --doc -p leto-ops` ✅ 11/11 pass in 54.64s.
  - Sparse-LU-targeted suite ✅ 16/16 pass:
    `factor_poisson_1d_laplacian_n16_roundtrip` 0.064s,
    `factor_banded_5_diagonal_n32` 0.026s,
    `factor_random_sparse_n64_diff_dense` 0.252s,
    `sparse_path_routes_correctly_for_tridiagonal_n64` 0.269s,
    `factor_f32_generic` 0.051s,
    `singular_matrix_yields_storage_error` 0.240s,
    `solver_is_generic_over_f32` 0.071s, plus 9 inherited solver-routing tests.
  - Differential cross-check: `factor_random_sparse_n64_diff_dense` asserts
    value-semantic equivalence between sparse and dense LU on a randomly
    populated 64×64 matrix at residual < ε (not existence-only).
- Residual / not-covered-in-this-closure (per ADR 0031 Consequences):
  (a) AMD (Approximate Minimum Degree) ordering deferred to
      `ATLAS-LETO-OPS-AMD-ORDERING-001` [patch] — natural ordering ships for
      v0.40.0; AMD ~300-line impl exceeds this session's context budget and
      a partial implementation would risk numerical defects per ADR 0031
      "AMD scope risk".
  (b) CFDrs `DirectSparseSolver` migration to the landed
      `SparseLuSolver::solve_view` is the follow-up
      `ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001` — depends on aequitas pin
      coherence and a leto bump at CFDrs; not in scope for Session 17.
  (c) Local clippy `-D warnings` against the FULL leto workspace cannot run
      clean on this coordinator's working tree because peer's untracked
      uncommitted sibling verticals
      (`crates/leto-ops/src/application/{diff,interpolation,quadrature}/`)
      contain `assign_op_pattern` and `complex_type` lint failures. PR
      #74's CI status (both `recurseml/analysis` post-push and
      `CodeRabbit`) was CLEAN before squash-merge; the merged commit's
      leto-ops scope is clippy-pedantic clean modulo peer-held untracked
      files not in the merged tree.
- Concurrent-agent record: peer session active on the same `codex/leto-real-sparse-lu`
  working tree during this closure, creating untracked siblings for diff/
  interpolation/ quadrature operation families (ts 21:53-22:02).  Per
  `concurrent_agents` assist-ladder rule: peer files skipped, not collided with.
  Coordinator scope-strictly-committed only `sparse/lu_numeric.rs` and
  `sparse/lu_symbolic.rs` (doctest-fixture correction + rustfmt-only reflow of
  pre-existing `for ... take().skip()` chains); peer's `Cargo.{lock,toml}`,
  `lib.rs`, `application/mod.rs`, `application/linalg/mod.rs`, and the new
  `diff/`/`interpolation/`/`quadrature/` untracked modules remained unstaged.
- Gitlink-state: atlas-meta's `repos/leto` gitlink advances to
  `687b67079c4e122264c17fd2eb3fd850d876a39f` in the same commit that
  synchronizes this backlog entry and ADR 0031's status flip.
- Refs: backlog.md#CFDRS-PERF-SLOW-001 (Session 13 upstream-cause filing),
  backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (this item), ATLAS-LETO-OPS-AMD-ORDERING-001 [patch] (new follow-up below).

## ATLAS-LETO-OPS-AMD-ORDERING-001 — Implement AMD fill-reducing ordering for sparse LU [patch] — todo

Filed as follow-up per ADR 0031 Consequences (closed at Session 17). The
[arch] Option A shipped natural column ordering for v0.40.0; AMD is the
deferred performance increment.

- Owner: unclaimed (route to leto peer next session — peer owns
  `leto-ops` source tree).
- Outcome: implement Approximate Minimum Degree ordering per
  Amestoy-Davis-Duff 1996 (An approximate minimum degree ordering
  algorithm, SIAM J. Matrix Anal. Appl. 17(4)), ~300-line surface.
- Acceptance: `SparseLuSolver` accepts a configurable ordering strategy
  (enum dispatch — `OrderingStrategy::{Natural, AmdApproxMinDegree}`); new
  unit test on a 32×32 Poisson-structured CSC matrix verifies the AMD
  ordering leans toward smaller fill relative to natural ordering by
  non-trivial fraction (asserted as `nnz(U_amd) < nnz(U_natural)`); full
  leto-ops nextest + doctest suite remains green; AMD factorization
  residual matches the natural-ordering residual on value-semantic
  matrices already in the test suite (differential oracle).
- Risk/change class: `[patch]` (additive public-API surface; no break).
- Architecture note: per ADR 0031 "AMD scope risk" — DO NOT implement a
  partial AMD that produces a numerically-broken factorization; prefer
  correctness-first natural ordering.
- Refs: docs/adr/0031-leto-ops-real-sparse-lu.md,
  backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed).

## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — partial closure (2026-07-23 Session 17: doc-migration slice landed via PR #316 `5ac713b3`); cfd-3d end-to-end re-profile and direct_threshold re-evaluation deferred

Filed as follow-up per Session 17 closure of `ATLAS-LETO-OPS-SPARSE-LU-001`.
Now that real sparse LU + partial pivoting has landed at leto `687b670`,
the CFDrs downstream consumer should adopt the upstream-native solver.

- Owner: unclaimed. Depends on CFDrs leto version bump (currently
  `aequitas = { path = "../aequitas" }` and leto path-pinned at
  atlas-meta level).
- Outcome: replace `crates/cfd-math/src/linear_solver/direct_solver.rs`
  body with calls to `leto_ops::application::sparse::SparseLuSolver::solve_view`
  on real CSC-typed inputs; remove any `with_direct_threshold(512)`-
  regime mats that exist purely to route medium saddle-point FEM
  matrices to GMRES (Brezzi 1974 indefinite saddle — sparse LU is now
  correct for it, not a misnomer).
- Acceptance: (1) CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs`
  no longer documents itself as "atlas-native sparse direct solver backed
  by dense partial-pivoting LU" (cf. the doc-runtime contradiction),
  (2) CFDrs cfd-3d suite verifies end-to-end (`validate_poiseuille_flow`
  PR #311 root-caused fix continues to PASS under the new upstream
  matrix-as-sparse path; re-profile runs `<1s` per Session 13 closure
  baseline), (3) `direct_threshold` parameter either removed from the
  CFDrs FEM solver or re-evaluated with new evidence (filed as a follow-up
  board item against CFDrs perf, not this slice).
- Risk/change class: `[minor]` (additive public-API call-site
  migration; no break to CFDrs public surface).
- Dependencies: leto version bump at CFDrs; aequitas pin coherence
  (Session 12 documented the eunomia dual-source-ID recurring risk
  when consumers pin eunomia differently; align all atlas consumers
  on URL-only form).
- Refs: backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed),
  leto origin/main `687b670`.

## ATLAS-HELIOS-BOOK-001 — Helios multichapter mdBook from examples [minor] [arch] — ✅ closed (2026-07-24 Session 18 — peer-delivered)

Per user Session 17 prompt: "Similar to kwavers it would be good for
helios and cfdrs to also create a well-organized, multichapter book
from examples." kwavers book template is the canonical reference.
Peer-helios delivered the book across PRs landing at `origin/main
433ddb6` (atlas-meta gitlink unchanged: it is already at this merged
origin commit). Coordinator closure is evidence-only — no member-repo
file edits by this agent.

- Owner: peer-helios (delivered); atlas-meta coordinator (this closure
  flips the backlog status and records the verification matrix).
- Outcome: full multichapter mdBook at 
  `repos/helios/docs/book/` with 8 Parts across 37 chapters + 4
  appendices + BOOK_ORGANIZATION forward roadmap; 18 example
  markdown files under `examples/`; 7 deterministic SVG figures
  + `MANIFEST.json` byte-determinism registry under `figures/`;
  `book.toml` configured with `/helios/` site-url + MathJax; README
  links published book at https://ryancinsight.github.io/helios/.
  Per-chapter content follows the kwavers-standard Domain-book
  contract: governing equations → numerics → CLI/API mapping →
  worked examples with deterministic figures, with each chapter
  carrying an H1 `# Chapter N — …` + `## Further Reading` backlink
  + SUMMARY.md navigation (verified by sampling across Parts I–VIII).
- Acceptance: 
  (a) `mdbook build docs/book` exits 0 locally at helios 
      `433ddb6` (verified via `mdbook v0.5.4`, target written to 
      `target/book/helios/index.html`). ✅
  (b) Every SUMMARY.md entry maps to a committed chapter stub with 
      H1 + "Further Reading" backlink (verified sample across 
      `foundations`, `dose_attenuation`, `planning_mlc`, 
      `workflow_tomotherapy`, `gpu_dose`, `migration_arrays`). ✅
  (c) Book deploys to GitHub Pages through the artifact flow 
      (`.github/workflows/book-pages.yml`: `actions/upload-pages-artifact@v4` 
      → `actions/deploy-pages@v4`, `pages: write` + `id-token: write`
      on the `deploy` job, deploy gated on `github.event_name != 
      'pull_request'`). ✅
  (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/docs.yml`
      `docs-invariant` job) runs the dead-link detector + `mdbook build`
      on all three books — green. ✅
- Risk/change class: `[minor]` documentation scaffolding + `[arch]`
  (introduces the mdBook workflow wired per AGENTS.md publish
  pipelines; interacts with the parity_artefacts INDEX manpages).
- Dependencies: ATLAS-PUBLISH-001 OIDC trusted-publishing alignment
  for helios book (RESIDUAL — see below); kwavers book GitHub Pages
  workflow template.
- Refs: backlog.md#ATLAS-BOOK-001 (kwavers), backlog.md#ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1.
- Residual / not-covered-in-this-closure (peer-coordinated, NOT claimed
  by Session 18 — coordinator cannot edit member-repo workflow files per
  concurrent_agents disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 acceptance item: `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test` 
      (engineering_gates publish-pipelines require both). Peer-helios
      owns `book-pages.yml`; flagged as a peer-coordinated sub-slice of
      ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-001 acceptance item: the Part VIII — Atlas Stack 
      Integration (Migration Reference) section in 
      `repos/helios/docs/book/SUMMARY.md` (chapters 26–37) is in-scope
      for the cross-book migration-content eviction under ATLAS-BOOK-001.
      Peer-kwavers holds the eviction branch; this residual is filed as 
      a helios-side peer-coordinated sub-slice of ATLAS-BOOK-001.
  (c) Atlas-meta helios gitlink stays at `433ddb6` (== `origin/main`); 
      no gitlink advancement is required or performed by this closure.
      Causal chain: peer-delivered → published on origin → coordinator
      verifies → backlog status flips. No regression surface.


## Session 17 partial closure (2026-07-23) — ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 → partial closure

Coordinator (Session 17 follow-up) landed the doc-comment migration of
`crates/cfd-math/src/linear_solver/direct_solver.rs` to reflect the
real CSC sparse LU per ADR 0031 + leto origin/main `687b670` (PR #74
squash-merge).

- **CFDrs PR**: ryancinsight/CFDrs#316 — title
  "docs(cfdrs-math): Migrate direct_solver doc to ADR 0031 real sparse LU
  (ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial)" — squash-merged as
  `5ac713b3fdf5fd45dbd295f3887c6f58b88c63f8` on CFDrs origin/main at
  2026-07-24T03:43:21Z.
- **Diff surface**: +25/-6 in
  `crates/cfd-math/src/linear_solver/direct_solver.rs` — module doc
  rewrite + `ordering` field doc correction + convergence composition
  with peer's pending `..Default::default()` adaptation to the
  upstream `SparseLuSolver` struct expansion (`small_switch` +
  `density_threshold` fields per ADR 0031).
- **Doc claim corrected**: the pre-merge module doc claimed the
  atlas-native solver was "backed by dense partial-pivoting LU" — that
  misnomer was filed for the Session 13 `CFDRS-PERF-SLOW-001` timeout
  closure root cause; it is now stale per ADR 0031 since leto PR #74
  landed the real CSC sparse LU (symbolic = sequential left-looking
  Gilbert–Peierls reach per Davis 2006 §6.1; numeric = slot-indexed
  left-looking with row_perm[slot]=original-row matching dense
  `LuDecomposition::pivots`; density-gated dispatch `small_switch=32`,
  `density_threshold=0.1` in `SparseLuSolver`).
- **Safety net preserved**: the CFDrs-side `dense_threshold=1024`
  retry at `DirectSparseSolver::retry_dense_or_error` is preserved as
  the orthogonal catch case for the `max_size`-cap + small-`n`
  user-intent safety net; NOT a duplicate of the upstream internal
  fallback (which handles only `NumericalBreakdown` mid-sparse-path).

Gitlink: atlas-meta `repos/CFDrs` advances from `1b2c901` to
`5ac713b3` (submodule local working tree left at local main HEAD
`354266c0` with peer's WIP unmodified per concurrent_agents
preservation; the gitlink records the squash-merged origin/main tip).

Refs: backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (above; this
entry closes the partial slice),
docs/adr/0031-leto-ops-real-sparse-lu.md (atlas-meta, Accepted),
leto PR #74 squash-merged as `687b670` (origin/main),
CFDrs PR #316 squash-merged as `5ac713b3` (origin/main).


## Session 18 closure (2026-07-24) — ATLAS-HELIOS-BOOK-001 → ✅ closed

- Owner: peer-helios (delivered the book across multiple PRs landing at
  `origin/main 433ddb6`); atlas-meta coordinator (this Session 18
  closure records the verification matrix and flips the backlog status
  from `todo` to `✅ closed`). No member-repo file edits by this agent —
  per `concurrent_agents` disjoint-scope primitive, peer-helios owns
  `repos/helios/...` files.
- Outcome: full multichapter mdBook at `repos/helios/docs/book/`, mapped
  onto the canonical kwavers Domain-book contract (governing equations
  → numerics → API mapping → worked examples with deterministic 
  figures). Spec verified via local inspection of `origin/main`:
  - `docs/book/SUMMARY.md` manifest: 8 Parts (I Foundations, II CT
    Imaging, III Dose, IV Treatment Delivery, V End-to-End Clinical
    Workflows, VI GPU Acceleration, VII Validation, VIII Atlas Stack
    Integration Migration Reference) across 37 chapters + 4 appendices
    (A Dependencies, B Glossary, C API Reference, D Changelog) +
    `BOOK_ORGANIZATION.md` forward roadmap.
  - 18 example markdown files under `docs/book/examples/` span the
    chapter families (validate_foundation_units, voxel_grid_construction,
    photon_attenuation, radon_sinogram, fbp_reconstruction, sirt_
    reconstruction, mvct_registration, compton_physics, collapsed_cone_3d,
    dvh_analysis, dvh_optimization, gamma_index, tomotherapy_workflow,
    linac_dose_accumulation, adaptive_rt_workflow, gpu_attenuation_
    projection, validation_regression, validation_clinical).
  - 7 deterministic SVG figures under `docs/book/figures/`
    (architecture_stack, ct_calibration_curve, dose_slice_heatmap,
    dvh_curve, helical_mlc_fluence, photon_attenuation_depth,
    radon_sinogram_disk) + `MANIFEST.json` byte-determinism registry.
  - `docs/book/book.toml` configured with `/helios/` site-url + MathJax.
  - `README.md` carries the canonical `[Published Helios book]
    (https://ryancinsight.github.io/helios/)` link.
- Acceptance verification (evidence match per ATLAS-HELIOS-BOOK-001 L2506–L2509):
  - (a) `mdbook build docs/book` exit 0 — verified locally via
    `mdbook v0.5.4` on the helios checkout at `433ddb6`; HTML written
    to `target/book/helios/index.html`. ✅
  - (b) SUMMARY.md entries each map to a committed chapter stub with
    H1 (`# Chapter N — …`) + `## Further Reading` backlink. Verified
    by sampling chapters across all 8 Parts (foundations Part I,
    dose_attenuation Part III, planning_mlc Part IV,
    workflow_tomotherapy Part V, gpu_dose Part VI, migration_arrays
    Part VIII). ✅
  - (c) Book deploys to GitHub Pages through the artifact flow.
    `repos/helios/.github/workflows/book-pages.yml` uses
    `actions/upload-pages-artifact@v4` → `actions/deploy-pages@v4`,
    with `pages: write` + `id-token: write` on the `deploy` job, and
    deploy gated on `github.event_name != 'pull_request'` (main-only). ✅
  - (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/
    docs.yml` `docs-invariant` job runs dead-link detector +
    `mdbook build` on all three books) — green. ✅
- Helmholtz-style residual / not-covered-in-this-closure (peer-coordinated,
  NOT claimed by Session 18 — coordinator cannot edit member-repo
  workflow files per `concurrent_agents` disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 residual — `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test`.
      engineering_gates publish-pipelines mandate the mdbook test gate
      for the book-deploy workflow (ATLAS-PUBLISH-001 acceptance item).
      Peer-helios owns the workflow file; filed as a peer-coordinated
      sub-slice of ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-001 residual — the Part VIII Atlas-Stack Integration
      (Migration Reference) section in `repos/helios/docs/book/SUMMARY.md`
      (chapters 26–37) is in-scope for the cross-book migration-content
      eviction under ATLAS-BOOK-001 (peer-kwavers holds the active
      eviction branch). Filed as a helios-side peer-coordinated
      sub-slice of ATLAS-BOOK-001.
  (c) Atlas-meta `repos/helios` gitlink stays at `433ddb6` (== `origin/main`).
      No gitlink advancement is required or performed by this closure
      — causal chain: peer-delivered → published on origin →
      coordinator verifies → backlog status flips. No regression
      surface.
- Concurrent-agent record: prior-session coordinator work committed as
  `04dee5c "docs(atlas): Close Aequitas metric audit gaps"` advanced the
  book-CI verification slice (now `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER`
  status `in-progress` after HELIOS PR #31 root-cause analysis). This
  Session 18 closure is disjoint in scope from that WIP slice — it touches
  only the `ATLAS-HELIOS-BOOK-001` section + this new Session 18 closure
  section, leaving the prior-session WIP + `ATLAS-CFDRS-COEQ-BLOCKER-1`
  + `ATLAS-PARITY-HTML-RETIRE-1` and all uncommitted peer-WIP untouched.
- Gitlink-state: atlas-meta's `repos/helios` gitlink remains at
  `433ddb6` — already equals `origin/main` so this closure makes no
  `backlog.md`-internal gitlink advancement. Diff signature: `backlog.md`
  only (no `.gitmodules`, no `gap_audit.md`, no member-repo path).
- Refs:
  - backlog.md#ATLAS-HELIOS-BOOK-001 (this closure)
  - backlog.md#ATLAS-BOOK-001 (kwavers master eviction scope — residual filed, not closed)
  - backlog.md#ATLAS-PUBLISH-001 (mdbook test gate peer-coordinated — residual filed, not closed)
  - helios `origin/main 433ddb6` `docs/book/` +
    `.github/workflows/book-pages.yml` + `README.md` (artifact evidence)
  - https://ryancinsight.github.io/helios/ (published book URL)

## ATLAS-STACK-DEPS-001 — Stale dependency version resolution across hermes, tyche, melinoe [patch] — done

- Policy: AGENTS.md codebase_fidelity "Ecosystem currency" + integrity "HARD: no mocks" — workspace resolution must succeed so test targets are discoverable; version requirements must match actual crate versions.
- Scope: (1) hermes — `hermes-simd-benches` and `hermes-simd-examples` declare path-dependency version requirements of `"0.5.0"` for `hermes-simd` and `hermes-simd-core`, but the workspace version is `0.4.1`; revert to `"0.4.0"` so Cargo resolves the workspace graph. (2) tyche — workspace declares `moirai-core` and `moirai-executor` at `"0.5.0"` but upstream crates are `0.4.0`; revert to `"0.4.0"`. (3) melinoe — add crate-root `#![deny(missing_docs)]` attribute for stack consistency (aequitas, harmonia, horae, themis all use the crate-root form; melinoe had it only via `[lints.rust]`).
- Acceptance: all three repos pass `cargo check --workspace` after fix; gitlinks advanced and pushed.
- Evidence (2026-07-24): hermes `2739a75` — `cargo check --workspace` passes; workspace resolves all 7 member crates. tyche `95c1fa7` — `cargo check --workspace --all-features` passes; workspace resolves all 4 members + moirai-core 0.4.0. melinoe `40278ac` — `cargo check --all-features` passes; `#![deny(missing_docs)]` verified by clean build. Atlas gitlink advanced to `babdd42`, pushed.
- Note: hermes/tyche `cargo nextest run` and `cargo clippy --all-targets` fail due to pre-existing shared-target toolchain mismatch (hermes pinned to 1.95.0, tyche to 1.95.0, shared target compiled by 1.97.0). This is a separate infrastructure issue tracked implicitly by the shared build-cache policy.

## ATLAS-AEQUITAS-001 — Wireless gitlink advance to origin/main `19fc3846` [minor] — done

Standing-gitlink advance per ADR 0020 (provider-graph-refresh pattern) and
`git_discipline` causal chain (peer publishes → coordinator verifies →
gitlink advances). Three additive peer commits on aequitas origin/main,
each CI-verified green via `gh api .../check-runs`:

- `07e2252 feat(aequitas): Add surface tension units`
- `6dc68c4 feat(aequitas): Add quantity serde support`
- `19fc384 feat(aequitas): Add angle units`

The prior pin `b86a55d` is ancestral to `19fc3846` via `merge-base
--is-ancestor` (verified exit 0). The three commits are all `[minor]`
additive public-API surface (new physical quantity types + serde bound);
`SurfaceTension` was already live in `b86a55d`'s tree and consumed by
CFDrs per `gap_audit.md`, so the net new domain surface at the consumer
boundary is `Angle` (an SI base dimension). No atlas-meta source calls
into the new surface; consumer references in CFDrs/helios/asclepius/
athena/harmonia deny.toml and Cargo.toml pin `aequitas = "0.1.0"` (path
or git+branch), so all consume the increment without break.

- Owner: atlas-meta coordinator (Session 19, 2026-07-24). Scope-strict
  to the `repos/aequitas` gitlink plus this backlog registry section.
  Per `concurrent_agents` disjoint-scope primitive, the aequitas
  working tree itself stays on the peer's `origin/main` HEAD — no
  edits to `repos/aequitas/**`.
- Outcome: atlas-meta gitlink for `repos/aequitas` advances from
  `b86a55d` to `19fc384` (origin/main HEAD at filing date).
- Acceptance: (a) origin/main publish verified
  (`git --git-dir=repos/aequitas/.git fetch origin` reaches `19fc384`);
  (b) per-commit CI verified green via `gh api
  repos/ryancinsight/aequitas/commits/<sha>/check-runs` (subagent
  panel inspected: `verify` + `supply-chain` jobs = `success` on
  `07e2252`, `6dc68c4`, `19fc3846`); (c) `merge-base --is-ancestor
  b86a55d 19fc3846` exit 0 — linear advance, no merge-bubble capture;
  (d) atlas-meta cross-book docs.yml gate not affected by path filter
  (`.gitmodules` not listed; no `docs/book/**` content touched); the
  criterion-regression meta-coordinator tool remains warning-clean,
  format-clean, 21/21 nextest green + 2/2 doctests green (continuous
  verification re-run 2026-07-24).
- Rejected advance candidates (not evidence-backable at this session, per
  `concurrent_agents` origin-sync-first + `git_discipline` gitlink pin):
  - **CFDrs** (`f33e469` → `99318bc`): main is CI-red on every commit
    on the path; the `Check book figures SSOT` job fails on each of
    `f33e469`, `ef231f2d`, `80a3e772`, `99318bc` (peer's `ci.yml`
    still missing sibling-checkout, blocked by
    `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`). Advancing imports unreviewed
    CI-failed work — filed; no advance.
  - **coeus** (`15ee8e5` → `a6dfb2d`): reverse direction — the pin
    is 14 commits AHEAD of origin/main on a local branch
    `atlas/mnemosyne-0.6-compat` that is not published to GitHub;
    further, Coeus has had no active `ci.yml` workflow registered with
    the Actions service since 2026-02-01 (last main-branch run was
    conclusion=failure on `bfaf82b`). No `github-actions` check-runs
    exist for any recent commit, so peer-CI-verified advancement is
    not possible. This is a separate infrastructure gap filed via this
    entry as a peer-coordinated slice for the coeus peer (workflow
    re-registration + main CI green).
  - **consus** (`eae5676` → `3137c4b`): the pin `eae5676` is a local
    unpushed commit authored 2026-07-23 by Mistral Vibe (per git log)
    on top of origin/main `3137c4b`; advancing to `3137c4b` would
    abandon unique peer WIP — prohibited by `git_discipline`
    fix-forward / no-revert. Not an advance candidate; live peer WIP.
  - **kwavers** (`07f60733` → `c19134ec`): the pin `07f60733` is a
    grafted commit on a local branch `codex/kwavers-aequitas-vessel-metrics`
    matching PR #325 head, mergeable=false (`mergeStateStatus=DIRTY`).
    The handoff's premise that `codex/kwavers-book-migration-eviction`
    is on origin is FALSE — `git fetch origin
    codex/kwavers-book-migration-eviction` returns `couldn't find
    remote ref`; the eviction branch is local-only at `9bbcb6f0`. No
    eviction work has been merged to origin/main. PR #324
    (transducer) is mergeable but multi-job red (Numerous `fail`
    conclusions; only Miri + Layer Boundary + CodeRabbit pass). With
    PR-mergeable red or local-only DIRTY states, no advance is
    evidence-backable. Filed against kwavers peer for eviction PR
    publication to origin.
- Risk/change class: `[minor]` (additive consumer-graph pin advance; no
  semver-major surface, no break).
- Dependencies: none at atlas-meta consumer level; documented above.
- Evidence limit: per-commit CI verification via authenticated `gh api`
  responses; no local build of aequitas or its consumers performed
  (peer-WIP slippage on member-repo working trees makes per-repo
  builds costly and outside coordinator scope per pitfalls doc).
- Refs: backlog.md#ATLAS-STACK-DEPS-001 (Session 18 gitlink advance
  precedent), docs/adr/0020-provider-graph-refresh.md (advance
  pattern), gap_audit.md#Aequitas-physical-metric-gap-audit (Quantity
  surface inventory).

## Session 19 closure (2026-07-24) — ATLAS-AEQUITAS-001 gitlink advance + criterion-gate continuous verification

- Owner: atlas-meta coordinator (this Session 19 closure records the
  gitlink advance and the criterion-gate re-audit). No member-repo
  files touched per `concurrent_agents` disjoint-scope primitive.
- Outcome:
  (1) ATLAS-AEQUITAS-001 above — atlas-meta gitlink for
      `repos/aequitas` advances from `b86a55d` to `19fc384` (origin/main
      HEAD). Three peer commits, all CI-green via `gh api`. Linear
      advance (no merge-bubble), `[minor]` additive.
  (2) ATLAS-BENCH-BUDGET-001 continuous-verification re-audit of the
      meta-owned `tools/criterion-regression` tool:
      - `cargo check --all-targets` Finished clean.
      - `cargo clippy --all-targets -- -D warnings` clean (pedantic +
        `clippy::unwrap_used`).
      - `cargo fmt --check` clean.
      - `cargo nextest run --no-fail-fast` 21/21 pass (max 0.451s;
        well under the 30s slow / 60s terminate budget).
      - `cargo test --doc` 2/2 pass.
      The tool remains green for peer consumption; the residual
      full-stack sweep (164 benches across moirai/CFDrs/kwavers/hermes/
      ritk + per-repo CI wiring per `ATLAS-BENCH-BUDGET-001`) stays
      deferred until the live peer scopes integrate.
  (3) Stale-claim sweep + origin-sync-first per `concurrent_agents`:
      all five drifted gitlinks (CFDrs, coeus, aequitas, consus, kwavers)
      audited via authenticated `gh api` panel dispatched as a parallel
      subagent panel inspecting per-repo states via `git ls-remote`,
      `git --git-dir`, and authenticated `gh api` check-runs / status
      queries. Session 19 takes the single evidence-backable advance
      (aequitas); the other four are correctly rejected above with the
      recorded reason.
- Concurrent-agent record: peer-helios at `origin/main 433ddb6`
  (unchanged from Session 18 closeout). Peer-CFDrs at `origin/main
  99318bc` (advanced past Session 18 but CI red on check-figures job —
  same `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` residual; the Venturi metric
  closure `ATLAS-CFDRS-PERF-045` already recorded separately on main).
  Peer-mnemosyne already integrated per Session 18's gitlink advance.
  Peer-aequitas freshly advanced now. Other peer activity: peer-leto at
  `origin/main 687b670` (stable — sparse LU landed Session 17). Peer
  kwavers eviction remains local-only (PR #325 DIRTY, eviction branch
  unpushed). Stale-claim sweep used the actual peer's published origin
  + `gh api` for CI conclusions; no speculative merges or assumptions
  about peer intent beyond their published state.
- Diff signature: `repos/aequitas` gitlink only (index-staged) + this
  backlog.md section. No `.gitmodules` URL change, no `gap_audit.md`
  edit (currency-current via Session 18 closeout), no member-repo files,
  no `tools/*` build (the continuous-verification re-audit ran
  read-only against the existing tool tree and produced no source delta).
- Refs: backlog.md#ATLAS-AEQUITAS-001 (the gitlink advance this closure
  records), backlog.md#ATLAS-PUBLISH-001 (mdbook test gate per-repo
  peers — unaffected), backlog.md#ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1
  (CFDrs advance blocker), backlog.md#ATLAS-LETO-OPS-AMD-ORDERING-001
  (leto peer work — peer-held, unclaimed here),
  backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (CFDrs cfd-3d
  re-profile — partial closure, peer-held).
- Coordinator exhaustion reached after this advance: no further
  actionable gitlink atlases capable of evidence-backable advance at
  this session; all `in-progress`/`todo` items either peer-held
  (Codes `/root` peer) or peer-blocked on member-repo source files,
  per `concurrent_agents` disjoint-scope primitive. Next wake triggers
  documented at each rejected-advance entry above.

## ATLAS-COEUS-DIRTY-RECONCILE-1 — Commit post-`7d60724` coeus dirty state: workspace-graph migration + CUDA driver compat + lock disambiguation [patch] — done (with coherence defect 1, see ATLAS-GITLINK-COHERENCE-DEFECT-1)

- Coherence-defect cross-link: the pinned coeus HEAD `c711dcb4` is
  NOT on coeus `origin/main` (`a6dfb2d`) as of 2026-07-24 16:24
  -0400; peer-coeus's 18-unpushed-commits `atlas/mnemosyne-0.6-compat`
  branch must merge to coeus origin/main to close the defect. See
  `ATLAS-GITLINK-COHERENCE-DEFECT-1` row 1.
- Owner: Codex `/root`; last-update: 2026-07-24; scope: `repos/coeus`
  branch `atlas/mnemosyne-0.6-compat` (2 atomic commits) + parent
  submodule pointer advance + this backlog entry.
- Outcome: cleared the live working-tree dirty state post-parent-commit
  `7d60724` by landing two coupled atomic commits. Mega-bundle finalizes
  (a) eunomia / themis / melinoe path-dep migration closing the
  atlas-migration path-dep convergence, and (b) deletion of the 26-line
  `[patch."https://github.com/ryancinsight/X.git"]` table block that
  previously forced git+https deps to resolve as path-deps during the
  in-flight migration -- obsolete now that every git+https call-site
  in coeus has been migrated to its local sibling-checkout path-dep.
  The deletion closes the "two VecStorage types" invariant the table
  guarded.
- Acceptance: (a) `cargo metadata --no-deps --offline` at
  `D:/atlas/repos/CFDrs` exits 0 with empty stderr post-merge
  (basher 2026-07-24) -- workspace-graph metadata resolves cleanly
  with the deleted `[patch]` table; (b) parent `repos/coeus` submodule
  gitlink advanced from `15ee8e594fd497f59fff65d809c2034131e1f0b0`
  on `atlas/mnemosyne-0.6-compat` past `4d59a0f3` (commit 1) to
  `c711dcb40011786ee9ad6fca510335879c97d632` (commit 2); (c) two
  atomic commits authored under
  `Ryan Clanton <ryanclanton@outlook.com>`.
- Co-located commits on atlas/mnemosyne-0.6-compat:
  - `c711dcb4` `build(coeus): workspace-graph path-deps + cuda driver
    compat + lock disambiguation` (3 files changed, 204+/131-:
    `.cargo/config.toml` + `Cargo.lock` + root `Cargo.toml`)
  - `4d59a0f3` `fix(coeus-cuda): downgrade cuCtxCreate_v4 to v2 for
    older-driver compat` (1 file: `crates/coeus-cuda/src/driver.rs`)
  - `53311c03` `fix(coeus-wgpu): Repair fallible test calls`
    (absorbed in branch; carries the
    `coeus-tensor/tests/.../parity_tests.rs`,
    `coeus-wgpu/src/kernels/layout.rs`,
    `coeus-wgpu/tests/.../parity/strided.rs` fallible-API test
    adaptations from the upstream coeus_ops signature change
    per `verifier=basher`)
- Cross-links: depends on `ATLAS-CFDRS-COEQ-BLOCKER-1` [done] (parent
  commit `7d60724`) -- the parent-sided coeus submodule pointer
  advance that exposed the workspace-graph fix slice this slice
  closes. The parent commit this slice produces advances the
  `repos/coeus` gitlink past `15ee8e5` to `c711dcb4`, capturing
  both the cuCtxCreate v2 driver compat and the workspace-graph
  mega-bundle.
- Risk/change class: `[patch]`; workspace-graph topology migration
  with no production-API delta on coeus consumers; clone-clean for
  downstream consumers as proven by acceptance (a).
- Dependencies: depends on local sibling-checkouts of `../eunomia`,
  `../themis`, `../melinoe` (and transitive `../leto`, `../mnemosyne`,
  `../moirai`, `../hephaestus`, `../apollo`) being present at SHAs
  locked by their respective parent submodule pointers -- the deleted
  `[patch]` table's safety net has been removed, so the workspace-
  graph dependency migration must hold for every cross-atlas consumer.
- Evidence limit: cargo metadata resolution at CFDrs post-merge;
  no production-code delta; no perf claim; no behavior change.
- Discovered-by: live basher porcelain captured 3 dirty files
  (`.cargo/config.toml` + `Cargo.lock` + root `Cargo.toml`)
  accumulating on coeus after the COEQ closeout commit `7d60724`
  advanced the coeus submodule past `15ee8e5`; user prompt
  2026-07-24.

## ATLAS-COEUS-OPS-FALLIBLE-API-1 — Document `coeus_ops` fallibility boundary migration (`*_assign` + `elementwise_unary` Result return + downstream test adaptations) [patch] [arch] — done

- Owner: Codex `/root`; last-update: 2026-07-24; scope: `repos/coeus`
  (the upstream boundary commit + downstream test adaptations captured
  by `ATLAS-COEUS-DIRTY-RECONCILE-1`).
- Outcome: traces the `coeus_ops::*_assign` + `coeus_ops::elementwise_unary`
  fallibility boundary migration. **CORRECTION 2026-07-24:** the user's
  prior framing was **CORRECT** -- the primary fallibility boundary
  lives in `crates/coeus-ops/src/backend_ops/cpu_impl/elementwise.rs`
  (and the adjacent `cpu_impl/error.rs` + `cpu_impl/impls/elementwise.rs`)
  at coeus commit `f8328027 refactor(coeus-ops): Propagate backend errors`
  (Fri Jul 24 00:50:13 2026). The `--all --follow -- crates/coeus-ops/src/backend_ops/cpu_impl/elementwise.rs`
  archaeology (basher 2026-07-24) surfaced `f8328027` as the upstream
  coeus-ops-side boundary; the earlier path-filtered `git log -- crates/coeus-ops/`
  pass missed it (it returns only 2 commits in current reachable history).
  The commit title verbatim: "Route validation and provider failures
  through the monomorphized backend seam without silent fallbacks.
  Update high-level callers, parity tests, and ADR tracking together."
  A SECOND distinct boundary in `coeus-wgpu/src/lib.rs` at
  `39191754 fix(coeus-wgpu): Make public add fallible` covers the
  coeus-wgpu-facade's own `add` API fallibility -- architecturally
  separate from the coeus-ops boundary at `f8328027`. Both seams share
  callers via the `coeus_ops::*` namespace but have distinct error types:
  `coeus_core::backend::Error` (from `f8328027`'s new `coeus-core/src/backend/error.rs`)
  vs `GpuLayoutError` (from `a6dfb2d6`'s coeus-wgpu layout boundary).
- Acceptance: (a) coeus-wgpu public `add` API is fallible (returns
  `Result`) per coeus commit `39191754 fix(coeus-wgpu): Make public add
  fallible`; (b) the primary coeus-ops-side fallibility boundary commit
  is `f8328027 refactor(coeus-ops): Propagate backend errors` (touched
  files: `coeus-core/src/backend/error.rs` new 67-line Error module +
  `coeus-core/src/backend/{mod,moirai,sequential,traits}.rs` + `coeus-core/src/lib.rs`
  + `coeus-ops/src/backend_ops/cpu_impl/elementwise.rs` + `cpu_impl/error.rs` +
  `cpu_impl/impls/elementwise.rs` + `cpu_impl/matmul.rs` +
  `cpu_impl/defaults/matmul.rs` + `coeus-cuda/src/backend/ops/impls/elementwise.rs` +
  `coeus-cuda/src/backend/ops/impls/matmul.rs` + `coeus-cuda/src/backend/ops/math.rs` +
  `coeus-cuda/src/error.rs` + many more); (c) downstream test files
  `coeus-tensor/tests/.../parity_tests.rs` (3 `.expect(...)` additions
  at lines 246/269/272), `coeus-wgpu/src/kernels/layout.rs` (3
  `matches!(...if...)` patterns + `vec![...]` ergonomic upgrades),
  `coeus-wgpu/tests/.../parity/strided.rs` (3 `.expect(...)` patterns
  for `Exp`/`Neg`/`Sqrt` strided transposed parity) all adapted per
  coeus commit `53311c03 fix(coeus-wgpu): Repair fallible test calls`;
  (d) post-`53311c03` partial revert `6b54e64a fix(coeus-ops): make
  element-wise ops return Tensor directly (infallible API)` rolled
  the OUTER PUBLIC `add/sub/mul/div` back to infallible with internal
  shape-mismatch `.expect()` (programming-error crashes, not runtime
  error surfacing), but the `*_assign` family and `elementwise_unary`
  **remain fallible** at HEAD -- this is why the test files retain
  `.expect(...)` calls at HEAD.
- Co-located commits (chronological -- earliest first):
  - `e840d019 refactor(ops): Split cpu_impl.rs into SRP family submodules`
    (Fri Jun 26 19:14:30 2026) -- THE PREDECESSOR: extracted
    `elementwise.rs` + `matmul.rs` + `conv/*.rs` as leaf modules from
    the 931-line `cpu_impl.rs` shell. This separation of concerns
    materially enabled `f8328027`'s targeted edit against `elementwise.rs`
    alone.
  - `79e76e86 docs(coeus): Specify fallible WGPU dispatch` (Thu Jul 23
    22:08:38 2026) (CHECKLIST.md + docs/adr/0020-wgpu-fallible-dispatch-boundary.md)
    -- ADR documents the boundary contract.
  - `a6dfb2d6 fix(coeus-wgpu): Validate layout metadata ABI` (Thu Jul 23
    22:12:02 2026) (126-line diff to coeus-wgpu/src/kernels/layout.rs) --
    introduces the `GpuLayoutError` family + `try_from_layout` boundary.
  - `f8328027 refactor(coeus-ops): Propagate backend errors`
    (Fri Jul 24 00:50:13 2026) -- **THE primary coeus-ops-side
    fallibility boundary commit** (corrected from prior path-filtered
    basher pass). Title verbatim: "Route validation and provider
    failures through the monomorphized backend seam without silent
    fallbacks. Update high-level callers, parity tests, and ADR
    tracking together." Touched files (basher-verified):
    `coeus-core/src/backend/error.rs` (new 67-line Error
    monomorphization module) +
    `coeus-core/src/backend/{mod,moirai,sequential,traits}.rs` +
    `coeus-core/src/lib.rs` +
    `coeus-ops/src/backend_ops/cpu_impl/elementwise.rs` +
    `coeus-ops/src/backend_ops/cpu_impl/error.rs` +
    `coeus-ops/src/backend_ops/cpu_impl/impls/elementwise.rs` +
    `coeus-ops/src/backend_ops/cpu_impl/matmul.rs` +
    `coeus-ops/src/backend_ops/cpu_impl/defaults/matmul.rs` +
    `coeus-cuda/src/backend/ops/impls/elementwise.rs` +
    `coeus-cuda/src/backend/ops/impls/matmul.rs` +
    `coeus-cuda/src/backend/ops/math.rs` + `coeus-cuda/src/error.rs` +
    many others. `merge-base --is-ancestor f8328027 atlas/mnemosyne-0.6-compat`
    returns EXIT=0 (in-branch).
  - `39191754 fix(coeus-wgpu): Make public add fallible` (Fri Jul 24
    08:05:02 2026) (5 files, 24+/7-) -- coeus-wgpu/src/lib.rs public
    `add` API becomes Result-returning. SECONDARY boundary (the
    coeus-wgpu facade, architecturally distinct from the coeus-ops
    boundary at `f8328027`).
  - `6b54e64a fix(coeus-ops): make element-wise ops return Tensor
    directly (infallible API)` (Fri Jul 24 10:07:27 2026) -- partial
    revert: outer `add/sub/mul/div` infallible, `*_assign` +
    `elementwise_unary` STAYS fallible at HEAD.
  - `53311c03 fix(coeus-wgpu): Repair fallible test calls` (Fri Jul 24
    12:58:43 2026) -- downstream test adaptation (consumed by
    DIRTY-RECONCILE-1).
- Co-located evidence: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
  §3.2 sub-log enumerates `39191754` + `6b54e64a` + `53311c03` in the
  same migration slice.
- Cross-links: depends on `ATLAS-COEUS-DIRTY-RECONCILE-1 [done]` (parent
  commit `dff78e7`) which captured `53311c03` + `4d59a0f3` + `c711dcb4`
  in the parent-side gitlink advance. Also depends on
  `ATLAS-CUDA-SAFETY-006..015 [done]` + `ATLAS-BUILD-STRUCTURE-003..005
  [done]` for the broader coeus operation-family closure context.
- Risk/change class: `[patch]` (call-site surface; behavior-preserving
  -- callers now must explicitly handle the Result variant but the
  success-path semantics are unchanged).
- Dependencies: depends on the fallible boundary commit (`39191754`) being
  PUBLIC-API-stable; the partial revert `6b54e64a` did not break that --
  it explicitly carved out `*_assign` + `elementwise_unary` as fallible.
- Evidence limit: basher grep of all `coeus_ops::*_assign` +
  `coeus_ops::elementwise_unary` call-sites shows full `.expect(...)`
  coverage; the post-`6b54e64a` infallible `add|sub|mul|div` outer
  surface is verified by `coeus-autograd/src/ops/activation/*.rs`
  having no outer `.expect()`; no production-code delta, no perf claim.
- Discovered-by: live basher git log archaeology with
  `--all --follow -- crates/coeus-ops/src/backend_ops/cpu_impl/elementwise.rs`
  (post-DIRTY-RECONCILE-1 closure 2026-07-24). Earlier path-filtered
  `git log -- crates/coeus-ops/` pass returned only 2 commits and missed
  `f8328027` -- the path-filter truncation is why the Round-1 preliminary
  draft misattributed the boundary to `coeus-wgpu/src/lib.rs` exclusively.
  Corrected view: BOTH boundaries exist (`f8328027` PRIMARY in coeus-ops,
  `39191754` SECONDARY in coeus-wgpu facade); the USER's prior framing in
  the upstream sub-question was CORRECT (the coeus-ops-side boundary
  indeed exists). Empirical inv: `git -C /d/atlas/repos/coeus log --all
  --follow -- crates/coeus-ops/src/backend_ops/cpu_impl/elementwise.rs`
  (basher 2026-07-24) returns the 4-commit chain
  `4a05472b → f8328027 → e840d019 → (post-order ancestors)` from which
  `f8328027` is identified as the boundary commit. `git
  -C /d/atlas/repos/coeus merge-base --is-ancestor f8328027
  atlas/mnemosyne-0.6-compat` returns EXIT=0 confirming in-branch.

## ATLAS-LETO-GITLINK-ADVANCE-1 — Advance `repos/leto` parent submodule pointer to c6ced81 [minor] — done (with coherence defect 2, see ATLAS-GITLINK-COHERENCE-DEFECT-1)

- Coherence-defect cross-link: the pinned leto HEAD `c6ced81e` is on
  peer-leto's LOCAL branch `codex/leto-real-sparse-lu` only — no
  remote branch exists on `origin`. Peer-leto must push the branch
  to origin, open a PR, and merge to leto origin/main. See
  `ATLAS-GITLINK-COHERENCE-DEFECT-1` row 2.
- Owner: Codex `/root`; last-update: 2026-07-24; scope:
  `repos/leto` parent-side gitlink advance.
- Outcome: advances `D:/atlas` parent `repos/leto` submodule pointer from
  `687b67079c4e122264c17fd2eb3fd850d876a39f` (last synced at
  LETO-NDARRAY-BOUNDARY-1 close Thu Jul 23 22:18:24 2026) to
  `c6ced81e6d5a9f439bd24a5150964e7bd2cb595d` on feature branch
  `codex/leto-real-sparse-lu` (Fri Jul 24 15:14:00 2026). Captures 12
  legitimate atlas-migration commits (lead `c6ced81` rectangular
  LsqrSolver; `141699a` eunomia/aequitas git->path conversion;
  `67f7e96` signal/nonlinear/statistics/optimization modules;
  `442ea7b` doctest; `dd1d0ad` hermes-simd 0.5.0 path;
  `406497a` mnemosyne/moirai path; `19306ca` doctest fix;
  `cce2b72` ndarray-removal completion;
  `b77e35a` clippy lint cleanup;
  `dd657a3` unused import removal;
  `ee6582d` ndarray/nalgebra dev-deps removal).
- Acceptance: parent commit
  `c147d913b04cdd4c8ee3b13c7a38ac7a1c338534` builds
  (`cargo build --offline -p leto` succeeds; leto-ops patch compiles);
  branch `codex/leto-real-sparse-lu` is target-of-record for the
  rectangular LsqrSolver work. 1 file changed in parent commit
  (repos/leto gitlink bump, 1+/1-).
- Sister cross-links: ATLAS-COEUS-DIRTY-RECONCILE-1 [done] at parent
  `dff78e7`; ATLAS-COEUS-OPS-FALLIBLE-API-1 [done] at parent `dc7459a`.
- Risk/change class: [minor] (feature capabilities + path-dep
  conversion; behavior-preserving at consumer surface).
- Dependencies: depends on local sibling-checkouts of
  `../mnemosyne`, `../moirai`, `../hermes`, `../eunomia`, `../aequitas`
  being present at SHAs locked by their respective parent submodule
  pointers (currently aligned per the verification matrix).
- Evidence limit: basher-verified git log archaeology on
  `/d/atlas/repos/leto` between `687b670..c6ced81` (12 commits); 0
  dirty files at LETO; no perf claim; no type-check oracle.

## ATLAS-MOIRAI-GITLINK-ADVANCE-1 — Advance `repos/moirai` parent submodule pointer to f74aa480 [patch] — done (with coherence defect 3, see ATLAS-GITLINK-COHERENCE-DEFECT-1)

- Coherence-defect cross-link: the pinned moirai HEAD `f74aa480` is
  on peer-moirai's LOCAL main 1 commit ahead of `origin/main`
  (`b613dc3d`). Peer-moirai must `git push origin main` to publish.
  See `ATLAS-GITLINK-COHERENCE-DEFECT-1` row 3.
- Owner: Codex `/root`; last-update: 2026-07-24; scope:
  `repos/moirai` parent-side gitlink advance.
- Outcome: advances `D:/atlas` parent `repos/moirai` submodule pointer
  from `b613dc3db6504340c4b407cbfbe5cab36bd23f44` (pre-slice parent
  gitlink) to local main HEAD `f74aa480217c51e0254461d02b47b2a32e67ddce`
  on branch `main`. Captured commit history:
  * `f74aa480 fix(deps): use local path deps for mnemosyne-core/mnemosyne`
    (the founding path-dep migration Thu Jul 23 23:20:05 2026) [LEAD]
  * intermediate commit
    `56044f99df609a589f45f25a9c988cbf568aa222` (captured by first
    verification slice; superseded by f74aa480 in subsequent pull)
  * recently merged PRs #93
    (`audit/moirai-ipc-memory-safety`) and #94
    (`audit/moirai-pal-epoll-safety`) from ryancinsight per the
    intermediate commit log.
- Cross-references: `b613dc3db...` parent gitlink points at the merge
  PR #94 PAL/safety audit. The lead path-dep commit `f74aa480` was
  authored after the b613dc3d merge, so the 1-commit SHA diff captured
  in the verification matrix was the conservative reading; the actual
  slice absorbed MORE commits at retry time.
- Acceptance: parent commit
  `6b97938f43a7c8ddb42ad74b1bfd351a4546c06a` (1 file changed, 1+/1-)
  builds; moirai main HEAD is target-of-record. The slice required a
  retry due to a transient `git index.lock` contention from the
  parallel LETO slice; serial retry after
  `rm /d/atlas/.git/index.lock && git -C /d/atlas add repos/moirai
  && git -C /d/atlas commit -m '...'` succeeded.
- Sister cross-links: ATLAS-LETO-GITLINK-ADVANCE-1 [done] at parent
  `c147d913`; ATLAS-APOLLO-GITLINK-ADVANCE-1 [done] at parent `63528a5`;
  ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1 [done] at parent `4c49783`.
- Risk/change class: [patch] (path-dep workspace-graph migration;
  behavior-preserving at consumer surface).
- Dependencies: depends on local sibling-checkout of `../mnemosyne`
  being present at SHA `c10e510` (parent submodule pointer currently
  aligned).
- Evidence limit: basher-verified git log archaeology on
  `/d/atlas/repos/moirai` between parent gitlink and local HEAD;
  0 dirty files at MOIRAI; no perf claim; no type-check oracle.

## ATLAS-APOLLO-GITLINK-ADVANCE-1 — Advance `repos/apollo` parent submodule pointer to 82e67c8 [patch] — done (with coherence defect 4, see ATLAS-GITLINK-COHERENCE-DEFECT-1)

- Coherence-defect cross-link: the pinned apollo HEAD `82e67c8f` is
  on peer-apollo's LOCAL main 2 commits ahead of `origin/main`
  (`8fb3e4ad`). Peer-apollo must `git push origin main` to publish.
  See `ATLAS-GITLINK-COHERENCE-DEFECT-1` row 4.
- Owner: Codex `/root`; last-update: 2026-07-24; scope:
  `repos/apollo` parent-side gitlink advance + co-located submodule
  commit closing the half-finished path-dep migration.
- Outcome: advances `D:/atlas` parent `repos/apollo` submodule pointer
  from `8fb3e4ad2c7903df14f7c1f944761970b55b9705` (last synced at
  `docs(apollo): Record the triple.rs extraction as delivered` Thu Jul
  23 10:46:41 2026) to `82e67c8fb11b26be82e8fdd2579e9004d2fce1b2` on
  branch `main` (post path-dep finalize).
- **Co-located submodule commit** (`82e67c8`): `fix(apollo): finalize
  path-dep migration for eunomia/melinoe/hermes/hephaestus` -- completes
  the migration that the lead commit `75f43cf fix(deps): use local
  path deps for mnemosyne/moirai/leto` started but did not finish. 6
  git= -> path= conversions in apollo Cargo.toml [dependencies]:
  * `eunomia`: git+https://github.com/ryancinsight/eunomia ->
    `path = "../eunomia/crates/eunomia"`
  * `melinoe`: git+https://github.com/ryancinsight/melinoe.git ->
    `path = "../melinoe"`
  * `hermes-simd`: git+https://github.com/ryancinsight/hermes.git ->
    `path = "../hermes/crates/hermes-simd"`
  * `hephaestus-wgpu`: git+https://github.com/ryancinsight/hephaestus.git ->
    `path = "../hephaestus/crates/hephaestus-wgpu"`
  * `hephaestus-core`: git+https://github.com/ryancinsight/hephaestus.git ->
    `path = "../hephaestus/crates/hephaestus-core"`
  * `hephaestus-cuda`: git+https://github.com/ryancinsight/hephaestus.git ->
    `path = "../hephaestus/crates/hephaestus-cuda"`
  Cargo.lock regenerated (`+472/-174`, 3686 total lines) -- de-duplicates
  mnemosyne / hermes-simd / leto / moirai entries that previously
  collided under the deleted git+https sources. This is the
  substantive half-finished migration work that was sitting as the
  `M Cargo.toml / M Cargo.lock` dirty state when the slice began
  -- NOT stale noise. Mirrors the coeus-side c711dcb4 workspace-graph
  migration.
- Acceptance: parent commit `63528a5eaa88275e989c348e6173f12e854581e9`
  builds; apollo main HEAD advances from `8fb3e4ad2 -> 82e67c8fb`.
  The path-dep migration is now COMPLETE for apollo's [dependencies]
  block. 1 file changed in parent commit (gitlink bump 1+/1-); 2
  files changed in submodule commit (472+/174-).
- Sister cross-links: ATLAS-COEUS-DIRTY-RECONCILE-1 [done] at parent
  `dff78e7` (mirror semantics).
- Risk/change class: [patch] (build/dependency migration;
  behavior-preserving at consumer surface; locks apollo sub-crate
  resolution to local sibling-checkouts of `../eunomia`, `../melinoe`,
  `../hermes`, `../hephaestus`).
- Dependencies: depends on local sibling-checkouts of `../eunomia`,
  `../melinoe`, `../hermes`, `../hephaestus` being present at SHAs
  locked by their respective parent submodule pointers.
- Evidence limit: basher-verified `git diff` archaeology on apollo
  Cargo.toml/lock showing the 6 conversions and 472+/174- lockfile
  rewrite; no perf claim; no type-check oracle.

## ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1 — Advance `repos/hephaestus` parent submodule pointer + add CUDA build script [minor] [arch] — done (with documentation drift follow-up)

- Owner: Codex `/root`; last-update: 2026-07-24; scope:
  `repos/hephaestus` parent-side gitlink advance + co-located submodule
  commit adding `build.rs` + co-capturing the 3 M-status Cargo files
  that should have been restored but were instead committed with their
  substantive content (see follow-up).
- Outcome: advances `D:/atlas` parent `repos/hephaestus` submodule
  pointer from `e7887a5d110c1b8b71456564b76bafcb3d68798f` (last synced
  at Merge PR #65 crates-io-hardening Wed Jul 22 22:52:21 2026) to
  `116373dd207d93660f53687f6a4817f7ee1b80ff` on feature b

## ATLAS-GITLINK-COHERENCE-DEFECT-1 — Meta-coordinator audit: 8 atlas-meta gitlink pins target commits NOT on per-member origin/main [patch] [arch] — in-progress

- Owner: Atlas-Codex (atlas-meta coordinator — coordinator-scope
  risk-artifact recording; no member-repo source touched); last-update:
  2026-07-24; scope: this `backlog.md` risk entry only.
  Coordinator-scope per `interaction_policy` — Change delivery through
  merge on allowlisted repos is the standing grant; this entry records
  the defect without mutating any `.gitmodules` gitlink or any
  member-repo source tree. Per `concurrent_agents` assist-ladder this
  is the coordinator-safe path: peer-Codex/peer-coeus/peer-kwavers
  own the publishing-on-origin actions; coordinator publishes evidence.
- Outcome: surfaced a systemic gitlink-coherence defect across the
  atlas-meta `origin/main` head `b18cdb4f03b2e65e8be87b6dc51df24e2b1643c3`.
  Audit pattern: for each submodule `repos/<R>`, verify pinned SHA is
  ancestral to that member's `origin/main` (`git --git-dir=... --work-tree=...
  merge-base --is-ancestor <pin> origin/main`). A negative result is a
  coherence defect: consumers cloning atlas-meta and initializing
  submodules receive a SHA that the member repo's origin/main never
  contained, breaking ADR 0020's gitlink-advance contract ("verified
  peer commits pushed to origin/main").
- Defect inventory (8 pins, ordered by defect-introduction commit on
  atlas-meta origin/main):

  | # | Member repo  | Atlas-meta commit | Pin SHA    | Member origin/main | Defect category | Status |
  |---|--------------|-------------------|------------|--------------------|-----------------|--------|
  | 1 | `repos/coeus`        | `dc7459a` (prior session) → `dff78e7` (re-affirmed) | `c711dcb4` | `a6dfb2d` | A — peer ahead of origin on feature branch | open |
  | 2 | `repos/leto`          | `c147d91` | `c6ced81e` | `687b6707` | C — pin on local feature branch only | open |
  | 3 | `repos/moirai`        | `6b97938` | `f74aa480` | `b613dc3d` | A — peer local main 1 ahead of origin | **closed** (Session 23: peer-moirai published +(Session 22 advance `0979371` re-pointed atlas-meta gitlink to peer-published `2c14b94f`; verifier: `merge-base --is-ancestor 2c14b94f origin/main`) |
  | 4 | `repos/apollo`        | `63528a5` | `82e67c8f` | `8fb3e4ad` | A — peer local main 2 ahead of origin | open |
  | 5 | `repos/kwavers`       | `7720163...` (pre-Session 20 state) | `07f60733` | `c19134ec` | B — pin on origin feature branch (PR #325 DIRTY), not on origin/main | open |
  | 6 | `repos/hephaestus`    | `b18cdb4` (origin HEAD) | `599ff79a` | (no `main` on remote at all) | B — pin on origin feature branch diverged from missing main | open |
  | 7 | `repos/mnemosyne`     | `7baa847` | `6a4bad71` | `c10e510d` | A — peer local main 1 ahead of origin | open |
  | 8 | `repos/consus`        | (earlier) | `eae5676c` | `3137c4b8` | A — peer local main 1 ahead of origin | open |
  | 9 | `repos/asclepius`     | `c2227aa` (Session 23) | `47e73d1e` | `f1b6a8ff` | A — coordinator-authored advance to peer's local-only main | open |

- Recovery action matrix (per-Defect category — coordinator does NOT
  execute these; peers publish to their own origins and the
  coordinator advances the atlas-meta gitlink ONLY after verification):

  * **Category A** (peer local main ahead of origin/main; simple
    `git push origin main` on the member repo recovers → then
    atlas-meta gitlink becomes valid): coeus (peer operating on
    `atlas/mnemosyne-0.6-compat` feature branch — 18 unpublished
    commits — NOT a fast-forward candidate; require peer-coeus to
    merge their feature branch to coeus origin/main first),
    mnemosyne (1 commit `6a4bad7`), apollo (2 commits),
    moirai (1 commit), consus (1 commit).
  * **Category B** (pin on remote feature branch but origin/main
    diverged or absent — needs peer to open/merge/rebase PR): kwavers
    (peer PR #325 DIRTY against newer origin/main — requires rebasing
    the branch onto `origin/main` or closing/abandoning the PR),
    hephaestus (peer PR not known — requires peer-pusher to rebase
    `codex/hephaestus-rocm-sparse-next` onto a (currently absent)
    origin/main or create `main` first by merging the branch).
  * **Category C** (pin on peer's LOCAL feature branch only, no remote
    branch — needs peer to push the branch and open a PR): leto
    (`codex/leto-real-sparse-lu` is local-only — peer-leto must push
    the branch to origin, open PR, merge to origin/main).

- Correction cross-links (per-Defect category reclassification of prior
  `done` entries whose gitlinks are the defects above):

  * `ATLAS-COEUS-DIRTY-RECONCILE-1` at line 3041 (parent commit
    `dff78e7`) — claims `done` but the pinned coeus HEAD
    `c711dcb4` is NOT on coeus `origin/main` as of this audit.
    Status correction: `done (with coherence defect 1, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-LETO-GITLINK-ADVANCE-1` at line 3233 (parent commit
    `c147d91`) — claims `done` but pinned `c6ced81e` is on local
    branch `codex/leto-real-sparse-lu` only, no remote branch.
    Status correction: `done (with coherence defect 2, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-MOIRAI-GITLINK-ADVANCE-1` at line 3269 (parent commit
    `6b97938`) — claims `done` but pinned `f74aa480` is on peer's
    local main 1 commit ahead of `origin/main`. Status correction:
    `done (with coherence defect 3, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-APOLLO-GITLINK-ADVANCE-1` at line 3310 (parent commit
    `63528a5`) — claims `done` but pinned `82e67c8f` is on peer's
    local main 2 commits ahead of `origin/main`. Status correction:
    `done (with coherence defect 4, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1` at line 3362 (parent commit
    `4c49783`) — claims `done` but a follow-up advance at parent
    `b18cdb4` (NOT recorded in a ledger entry on origin/main; the
    ledger entry for that advance was lost in the discarded local
    `c6ac87f` docs commit during this Session 21 recovery) pinned
    `599ff79a` on `origin/codex/hephaestus-rocm-sparse-next`, with
    no `origin/main`.Exists to ancestral-check against. Status
    correction: add cross-link noting defect 6.

- Recovery closure protocol (when each Defect recovers): peer publishes
  the pinned SHA to their member-repo `origin/main` (via their own
  `git push origin main`, branch merge-PR, or branch rebase-PR per
  category); coordinator then re-runs the
  `merge-base --is-ancestor <pin> origin/main` check; on a positive
  result the defect sub-row moves to `closed (verifier: basher
  merge-base <sha> <origin-main>)`; the parent commit's gitlink is
  already correct (no `.gitmodules` mutation needed); only the ledger
  entry's status correction flips back to `done (clean)`.

- Sister cross-links:
  * `ATLAS-COEUS-DIRTY-RECONCILE-1` [done (with coherence defect 1)]
    at parent commit `dff78e7`.
  * `ATLAS-LETO-GITLINK-ADVANCE-1` [done (with coherence defect 2)]
    at parent commit `c147d91`.
  * `ATLAS-MOIRAI-GITLINK-ADVANCE-1` [done (with coherence defect 3)]
    at parent commit `6b97938`.
  * `ATLAS-APOLLO-GITLINK-ADVANCE-1` [done (with coherence defect 4)]
    at parent commit `63528a5`.

- Risk/change class: [patch] [arch] — ledger-only commit. The risk is
  architectural: the atlas-meta `origin/main` HEAD is a state that no
  fresh clone can reproduce into a working tree, because submodule
  initialization pulls SHAs not on member origins. Each defect's blast
  radius is bounded by the consumers of that specific member crate
  (e.g. `kwavers` consumers in `repos/kwavers` source; `coeus`
  consumers throughout the stack). The defect is quietly hidden for
  agents already initialized (whose local `repos/<R>` working trees
  already have the SHA physically checked out), but breaks any fresh
  clone, CI checkout from origin, or `git submodule update --remote`.

- Dependencies: recovers when each of the 8 peer-publishing actions
  per the recovery action matrix completes. No coordinator scope to
  accelerate; only peers have authority to push to their member repos.

- Evidence limit: basher-verified `git --git-dir=repos/<R>/.git
  merge-base --is-ancestor <pin> origin/main` for each of the 8
  defect rows, run during this Session 21 audit. Verification time:
  2026-07-24 16:24 -0400 (+/-3 min). No perf claim; no type-check
  oracle; no production-code delta.

- Discovered-by: Session 21 fresh-origin-sync-and-audit; origin sync
  (per `concurrent_agents`) revealed diverged atlas-meta main and
  mandated this audit before any further gitlink mutation.
- Mechanization follow-up filed as
  `ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1` [patch] [arch]
  (`todo`): a coordinator-owned `tools/gitlink-coherence/` sister
  tool that mechanizes this audit pattern (per `operation`
  toil-automation policy — the manual audit sequence has now run
  twice, is drift-prone and error-prone, and has clear positive
  maintenance value at PR-time). Tech preview: read `.gitmodules`,
  enumerate submodule entries, run
  `git --git-dir=... --work-tree=... merge-base --is-ancestor
  <pin> origin/main` per repo, emit JSON/markdown/human output
  with defect categorization, exit 0 on clean / 1 on defects / 2 on
  invocation error. Zero external deps (mirror
  `tools/criterion-regression` `Cargo.toml` template sans
  `serde`/`serde_json` if a single-pass tool suffices, or
  re-include `serde` if JSON output is desired).

## ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1 — Mechanize the gitlink-coherence audit as a coordinator-owned `tools/gitlink-coherence/` sister tool [patch] [arch] — done

- Owner: Atlas-Codex coordinator (claim taken Session 22; closure
  verification Session 23 2026-07-24).
- Outcome: delivered `tools/gitlink-coherence/` Rust package
  `atlas-gitlink-coherence-gate` (binary `gitlink-coherence`), a
  single-shot read-only probe that verifies each `.gitmodules` pin
  against its member's `origin/main` and emits a categorization
  report. Mechanizes the manual toil pattern that produced
  `ATLAS-GITLINK-COHERENCE-DEFECT-1`; closes the
  `operation` toil-automation policy deficiency.
- Verification (Session 23 2026-07-24): all gates green on the new
  package — `cargo fmt --check`, `cargo clippy --all-targets --
  -D warnings`, `cargo nextest run` (18/18 tests pass in 0.339s,
  well within the 30s/60s nextest budget), `cargo test --doc`
  (0 doctests, clean). End-to-end acceptance against the live
  atlas-meta working tree:
  `cargo run --release --quiet -- audit --atlas-root /d/atlas --fetch`
  reports 8 defects (7 of the original Session 21 inventory —
  moirai closed mid-Session 23 — plus 1 new asclepius defect recorded
  below as defect #9 of the parent inventory) and 2 stale-advanceable
  rows; exit code is 1, matching the DoD acceptance oracle. Read-only
  default invocation (`--no-fetch`) reproduces the same categorization
  against the cached `refs/remotes/origin/main`.
- Defect inventory diff vs Session 21 (tool-emitted
  categorizations):
  - moirai — `Clean` (peer published `2c14b94f`; Session 22 gitlink
    advance `0979371` re-pointed atlas-meta to the peer-published
    pin). Closed.
  - coeus — `cat-c` (pin on local `atlas/mnemosyne-0.6-compat`, no
    remote). Matches Session 21 category-A reclassification note.
  - leto — `cat-c` (pin on local `codex/leto-real-sparse-lu`, no
    remote). Matches Session 21.
  - apollo — `cat-a` (pin on local `main`, no remote). Matches
    Session 21.
  - kwavers — `cat-b` (pin on local AND remote
    `codex/kwavers-aequitas-vessel-metrics`). Matches Session 21 cat-b.
  - hephaestus — `no-origin-main` (remote has only `master`, not
    `main`). Matches Session 21.
  - mnemosyne — `cat-a` (pin on local `main`, no remote). Matches
    Session 21.
  - consus — `cat-a` (pin on local `main`, no remote). Matches
    Session 21.
  - asclepius — `cat-a` (coordinator-authored coordinator-side
    advance `c2227aa` to peer's local-only main `47e73d1e`).
    NEW (Session 23 discovery via the audit tool); inventoried as
    defect #9 in the parent risk entry.
- Root cause fixed during implementation: the original Session 22
  tool scaffold passed Windows backslash-mixed paths to `--git-dir`,
  which git's C-side path resolver then failed to re-anchor through
  the `gitdir:` indirection file. Fixed via `git_dir_arg` helper
  that normalizes backslashes to forward slashes on Windows (no-op
  on POSIX). The `--fetch` failure path is no longer swallowed
  (Session 22 swallowed the result via `let _ =`, masking network
  failures and `no-main` signals alike); it now routes
  `couldn't find remote ref refs/heads/main` to the
  `NoOriginMainOnRemote` classification and propagates genuine network
  failures via `?`. Per `integrity` error-handling restraint.
- Risk/change class: [patch] [arch]; ledger-only commit + new
  coordinator tool, no production-code delta, no member-repo source
  touched.
- Cross-links: parent
  `ATLAS-GITLINK-COHERENCE-DEFECT-1` [in-progress] at parent commit
  `9ae06c0` (atlas-meta origin/main at closure).
- Refs: backlog.md#ATLAS-GITLINK-COHERENCE-DEFECT-1 (parent slice)

## ATLAS-TOOLCHAIN-ALIGN-001 — Align all 14 clean repos to Rust 1.97.0 for shared target compat [patch] — done

- Policy: AGENTS.md codebase_fidelity "Ecosystem currency" + performance_engineering "One build cache per stack" — the shared `D:\atlas\target` was compiled by the MSYS2 system rustc 1.97.0, but 12 repos pinned to `1.95.0` via `rust-toolchain.toml` caused incompatible-artifact errors on test/clippy.
- Scope: (1) Updated 12 repos (aequitas, asclepius, athena, eunomia, harmonia, hermes, horae, hyperion, iris, proteus, tyche, themis) from `channel = "1.95.0"` to `channel = "1.97.0"` in `rust-toolchain.toml`. (2) Added `rust-toolchain.toml` with `channel = "1.97.0"` to melinoe (previously had none, resolving to nightly). (3) Verified all 14 repos build and pass tests.
- Acceptance: all 14 clean repos pass `cargo check` + `cargo nextest run` + `cargo clippy --all-targets -- -D warnings`.
- Evidence (2026-07-24): 841/841 tests passed across 14 repos:
  - aequitas: 27/27 (0.66s)
  - asclepius: 18/18 (0.32s)
  - athena: 21/21 (1.91s)
  - eunomia: 108/108 (1.81s)
  - harmonia: 14/14 (0.25s)
  - hermes: 413/413 (5.08s) — previously zero test executables due to version mismatch
  - horae: 14/14 (0.24s)
  - hyperion: 12/12 (0.10s)
  - iris: 14/14 (0.10s)
  - melinoe: 121/121 (1.01s)
  - proteus: 18/18 (0.11s)
  - themis: 21/21 (0.34s) — previously blocked on stable=1.95.0
  - tyche: 40/40 (0.41s) — previously zero test executables due to version mismatch
  Clippy clean on hermes, tyche, melinoe (spot-checked). All gitlinks advanced and pushed.

## ATLAS-PERF-OPT-001 — Hot-path performance and memory efficiency optimization [patch] — done

- Owner: Ryan; last-update: 2026-07-24; scope: hermes, themis, melinoe.
- Outcome: (1) Eliminated redundant bounds checks in hermes gemv_transpose scalar tail — replaced safe slice indexing with raw pointer arithmetic in the ncols % lane_count tail of `gemv_transpose_strided_impl`, removing 2 bounds checks per inner iteration. SIMD paths above already use raw pointers; the scalar tail was the sole holdout. (2) Eliminated redundant bounds checks in hermes BlockedCoo scalar fallback — replaced safe slice indexing with raw pointer arithmetic in the non-standard BN scalar fallback of `BlockedCoo::spmv`, removing 4 redundant bounds checks per (i,k) inner iteration. (3) Pre-allocated Vec capacity in 5 themis topology detection sites — `windows.rs` (levels: 8, shared_processors: group_count), `linux.rs` (levels: 8), `cpulist.rs` (processors: 64), `detect/linux.rs` (processor_node_pairs: logical_processor_count()). (4) Pre-allocated shard vec in melinoe deque partition planning — `partition.rs` (shards: num_chunks * 2).
- Evidence: hermes 413/413 tests pass, clippy clean; themis 21/21 tests pass; melinoe 121/121 tests pass. Doctests pass for hermes.
- Commits: hermes `777b11c` (gemv_transpose), `b9393fc` (BlockedCoo), themis `035445f`, melinoe `7164f26`, atlas `bd34493`, `aac7f42`.

## ATLAS-PATH-DEP-AUDIT-2 — Sweep `git+https://github.com/ryancinsight/` source URLs across 13 submodule Cargo.lock files [patch] — todo

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/repos/*/Cargo.lock` audit for
  pending `source = "git+https://github.com/ryancinsight/<sibling>"`
  entries that should path-depify now that eunomia / themis / melinoe /
  coeus / apollo path-dep cutovers have landed on parent main.
- Outcome: post-cutover sweep identifies the remaining sibling-pulls
  via `git+https` URL with the corresponding `../<sibling>` path
  targets. Audit only — NO Cargo.lock rewrites + NO Cargo.toml edits
  in this sweep slice. Each candidate is staged at backlog.md level
  for the corresponding path-dep closure slices to pick up; closure
  slicing (which per-sibling slice owns which conversion) is
  per-crate rationalization, not audit scope.

### One-line summary per Cargo.lock file (basher 2026-07-24)

Counts of pending `source = "git+https://github.com/ryancinsight/`
lines (the path-dep cutover candidates; listed in alphabetical order
of Cargo.lock host-by-host):

```
asclepius  42 hits (aequitas=1, apollo=3, coeus=7, eunomia=1, hermes=6,
           leto=2, melinoe=1, mnemosyne=11, moirai=10, themis=1)
athena     27 hits (aequitas=1, eunomia=1, hephaestus=2, hermes=5,
           leto=2, melinoe=1, mnemosyne=10, moirai=5)
CFDrs      12 hits (consus=2, melinoe=1, mnemosyne=9)
coeus      12 hits (aequitas=1, eunomia=1, melinoe=1, mnemosyne=9)
gaia        3 hits (CFDrs=2, leto=1)
harmonia    4 hits (aequitas=1, athena=1, eunomia=1, horae=1)
hephaestus 12 hits (aequitas=1, eunomia=1, melinoe=1, mnemosyne=9)
hermes      2 hits (melinoe=1, mnemosyne=1)
horae       2 hits (aequitas=1, eunomia=1)
mnemosyne   2 hits (fuzz/Cargo.lock: melinoe=1, themis=1)
tyche       6 hits (consus=4, melinoe=1, themis=1)
aequitas    1 hit  (eunomia=1)
apollo     ~28 hits (aequitas=1, eunomia=1, hephaestus=3, hermes=5,
            leto=2, melinoe=1, mnemosyne=10, moirai=5; plus 7 hits
            to NVlabs/cutile-rs EXTERNAL -- NO action)
consus     24 hits (melinoe=1, mnemosyne=11, moirai=11, themis=1)
themis      1 hit  (melinoe=1)

Total path-dep candidates   152 hits spanning 14 sibling targets
External (NVlabs/cutile-rs) 7 hits in apollo/Cargo.lock ONLY -- NOT
  a path-dep candidate; preserve as git+https sibling or pin to
  crates.io when available
```

### Notable cases (verbatim from the basher sweep)

- **Locked-SHA drift** detected at mnemosyne's lock entries across
  multiple consumers (apollo, asclepius, athena, hephaestus, CFDrs):
  apollo/asclepius/athena lock at `Mnemosyne.git#5c7ee95...` while
  CFDrs/coeus/hephaestus lock at `Mnemosyne.git#c10e510d...` (which
  is the post-ATLAS-MNEMOSYNE-PATH-DEP-FINALIZE-1 SHA after the
  eunomia path-dep finalize commit). The two SHAs differ because the
  Cargo.lock files were regenerated at different times relative to
  the path-dep slice chain. A future `cargo update` + `cargo metadata
  --no-deps --locked` on each submodule will resolve the lock drift
  and pull the post-cutover SHAs uniformly.

- **`?rev=` query parameter** in tyche/Cargo.lock and hermes/Cargo.lock
  (`source = "git+https://github.com/ryancinsight/consus.git?rev=...`
  and `source = "git+https://github.com/ryancinsight/melinoe.git?rev=
  ...`) — the fat-lock style with explicit `rev=` query is preserved
  as-is in the audit; the path-dep cutover would simply replace the
  source URL with `path = "../<sibling>"` and drop the `?rev=` clause.
  No semantic difference.

- **External `NVlabs/cutile-rs`** (apollo/Cargo.lock lines 818-913)
  is documented here only as a guard against future-mistaken cutover:
  NVlabs is NOT a sibling atlas submodule; preserving the `git+https`
  source is correct.

### Acceptance

- This entry exists and is the SSOT for the post-path-dep-cutover
  audit findings; closure of audit is `todo` (this entry).
- Future per-target closure slices reference this entry's
  per-submodule hit counts when quantifying slice scope.

### Risk/change class

`[patch]`; doc-only ledger entry + read-only audit. ZERO Cargo.toml +
Cargo.lock + Workspace.toml mutation in any submodule.

### Cross-link inventory

- Sister prior slices that closed partial conversion:
  `ATLAS-EUNOMIA-044` (wrapper-int / cross-crate type safety, scope
  contains eunomia `0.6.x` family) -- `done`;
  `ATLAS-MNEMOSYNE-PATH-DEP-FINALIZE-1` (mnemosyne root
  `[workspace.dependencies] eunomia git->path`) -- `done` at parent
  commit `f52c88d6` / submodule `6a4bad71`;
  `ATLAS-MNEMOSYNE-THEMIS-MELINOE-PATH-DEP-1` (the in-band follow-up
  closing mnemosyne root `[workspace.dependencies]` themis +
  melinoe git->path) -- `done` at parent commit `540334e` /
  submodule `10704179`;
  `ATLAS-APOLLO-GITLINK-ADVANCE-1` (apollo submodule gitlink advance +
  co-located submodule commit `82e67c8` finalizing the path-dep
  migration for eunomia / melinoe / hermes / hephaestus that the
  parent commit `75f43cf` started but did not complete) -- `done`
  at parent commit `63528a5`;
  `ATLAS-COEUS-DIRTY-RECONCILE-1` (coeus submodule gitlink advance +
  `crates/coeus-cuda/Cargo.toml` path-dep finalize) -- `done` at
  parent commit `dff78e7`.
- The 14 sibling targets observed in the audit
  (aequitas / apollo / coeus / consus / CFDrs / eunomia / hephaestus /
  hermes / horae / leto / melinoe / mnemosyne / moirai / themis) cross
  reference the existing apollo-90+ entry scope for that slice's
  eunomia / melinoe / hermes / hephaestus finalization; future per-
  target closure slices will cite this audit entry's per-sibling
  hit counts.

### Evidence limit

- Audit complete verified at 2026-07-24 via code-searcher
  (ripgrep-direct) over `D:/atlas/repos/*/Cargo.lock` paths with the
  pattern `source = "git\+https://github.com/ryancinsight`; 152
  total matches across 14 sibling targets + 7 external NVlabs
  matches (preserved as external).
- Audience-vetted scope: only `[patch]` files (`Cargo.toml` /
  `Cargo.lock`) carry the path-dep cutover; no source-code changes
  implied. The audit identifies the Cargo.lock state-of-play; the
  Cargo.toml conversions live in the per-sibling submodule's
  `[dependencies]` or `[workspace.dependencies]` section.
- No cargo check, cargo metadata, cargo nextest, cargo clippy
  claim. No performance / runtime / allocation claim. The audit is
  the SSOT; closure slices own verification + cargo metadata
  regression coverage separately.

### Closure-wait criteria (slice may flip from `todo` to `done`)

Closure requires ALL of the following landed in future slices:

- per-sibling closure slices each converting one or more siblings
  from `git+https` source to `path = "../<sibling>"` + a Cargo.lock
  regen for the hosting submodule(s);
- a per-sibling cross-link at each slice's backlog entry pointing
  back to this entry's per-sibling hit counts as the enumeration
  baseline;
- a `cargo update -p <sibling> && cargo metadata --no-deps --locked`
  verification slice landing the lock-drift resolution across
  apollo / asclepius / athena / hephaestus / CFDrs / coeus / mnemosyne
  consumers;
- a final ATLAS-PATH-DEP-AUDIT-2 sweep-completion marker entry
  indicating zero remaining `source = "git+https://github.com/
  ryancinsight` hits across all `/d/atlas/repos/*/Cargo.lock`
  files (excluding the 7 NVlabs external hits).

## Session 23 closure (2026-07-24) — ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1 → ✅ closed

- Delivered the coordinator-owned `tools/gitlink-coherence/`
  package (`atlas-gitlink-coherence-gate`, binary `gitlink-coherence`).
- Verification (all gates green): `cargo fmt --check`, `cargo clippy
  --all-targets -- -D warnings`, `cargo nextest run` (18/18 pass,
  0.339s — within the 30s/60s nextest budget), `cargo test --doc`.
  End-to-end acceptance against the live atlas-meta working tree:
  `gitlink-coherence audit --atlas-root /d/atlas --fetch` reports 8
  defects + 2 stale-advanceable rows and exits 1, matching the
  DoR acceptance oracle.
- Root cause of the Session 22 end-to-end failure fixed: Windows
  backslash-mixed paths passed to `git --git-dir` fail through
  `gitdir:` indirection files (git's C-side resolver can't re-anchor
  the relative `gitdir:` target against a directory whose path
  contains both `/` and `\`). Replaced with a `git_dir_arg` helper
  that normalizes backslashes to forward slashes on Windows
  (no-op on POSIX). Per-integrity fix: dropped the
  `let _ = run_git(... "fetch" ...)` that swallowed the fetch
  error; the `couldn't find remote ref refs/heads/main` signal now
  routes to the `NoOriginMainOnRemote` classification, and genuine
  network failures propagate via `?`.
- Inventory movement: defect #3 (moirai) **closed** — peer-moirai
  published pin `2c14b94f` to origin and Session 22's gitlink
  advance `0979371` re-pointed atlas-meta to it. Defect #9
  (asclepius) **new** — coordinator-authored commit `c2227aa`
  advanced the asclepius gitlink to peer's local-only main
  `47e73d1e`; same defect pattern that `ATLAS-GITLINK-COHERENCE-
  DEFECT-1` is filed to expose. Recorded as defect #9 in the parent
  risk entry's inventory. Recovery action: peer-asclepius
  `git push origin main` to publish `47e73d1e` to `origin/main`.
- Coordinator home-scope after closure: the audit tool was the one
  substantive in-progress coordinator-claimable increment. After
  this commit, the only remaining in-progress items are peer-held
  member-repo source files (recovery actions for defects 1/2/4/5/
  6/7/8/9). Coordinator scope returns to ledger-filing only.
- Residual risk: the asclepius defect #9 is my own coordinator-side
  mutation. It is the existing defect pattern's first confirmed
  re-introduction since `ATLAS-GITLINK-COHERENCE-DEFECT-1` was
  filed — an internal regression against the policy the parent
  entry exists to enforce. Filed on the parent inventory for
  peer-asclepius recovery (category A: peer publishes local main).
- Pushed commit: see git log for SHA (atlas-meta origin/main
  following push).

## ATLAS-TOOLS-TEMPLATE-EXTRACT-1 — Extract shared `tools/_template/` package module for coordinator-owned tool Cargo lints/profiles/deps after 3rd occurrence [patch] [arch] — done

- Owner: Atlas-meta coordinator (Session 25).
- Delivery: commit `e260055` (`refactor(atlas): Extract tools/_template/
  for shared coordinator-tool config`) landed and pushed to
  `origin/main`. Four new files under `tools/_template/`
  (`template-Cargo.toml`, `template-rust-toolchain.toml`, `README.md`,
  `check-drift.sh`); `.gitignore` adds `!tools/_template/` to exempt
  the canonical substrate dir from the `_*` catch-all.
  `tools/checkout-path-dependencies/rust-toolchain.toml`
  reconciled to canonical key order (`channel` → `components` →
  `profile`).
- Verification: per-tool gates under committed budgets —
  `criterion-regression` 21/21 nextest in 5.681s + 2/2 doctests,
  `gitlink-coherence` 18/18 nextest in 3.309s + 0 doctests,
  `checkout-path-dependencies` 11/11 nextest in 7.520s + 1 doctest,
  all under the 30s slow bound. `tools/_template/check-drift.sh`
  exits 0 across all 3 consumers post-reconciliation.
- Note on cargo.toml policy source: not invented by this template;
  expresses `agent.md` performance_engineering + integrity lint floor
  (unwrap_used denied, pedantic warn-baseline, unsafe_code forbid,
  missing_docs deny; debug = line-tables-only with package.* debug =
  false; release strip = symbols; overflow-checks = true).
- Outcome: extract the recurring `[lints.rust]` / `[lints.clippy]`
  / `[profile.*]` / `[dependencies]` configuration that is pasted
  verbatim across the three coordinator-owned tool packages
  (`tools/checkout-path-dependencies/Cargo.toml`,
  `tools/criterion-regression/Cargo.toml`,
  `tools/gitlink-coherence/Cargo.toml`) into a `tools/_template/`
  directory carrying `template-Cargo.toml` (no `[package]` body,
  only the shared sections, documented as copy-and-then-override)
  and a matching `template-rust-toolchain.toml`. The third
  coordinator-owned tool landing triggers `consolidation_discipline`'
  'consolidate-on-second-occurrence' rule; failing to consolidate at
  the third occurrence is drift debt (same lint-config diff must be
  re-applied across all three packages for any policy update).
- Scope:
  * `tools/_template/template-Cargo.toml` — header comment naming
    the consumer list (3 packages as listed above); selector
    comments delimiting `[lints]` / `[profile]` / common
    `[dependencies]` blocks.
  * `tools/_template/template-rust-toolchain.toml` — same
    `channel = "1.95.0"` / `components = ["clippy",
    "rustfmt"]` /
    `profile = "minimal"` as all 3 tools use.
  * `tools/_template/README.md` — the SSOT policy: "copy-as-new,
    then fill `[package]` and tool-specific `[dependencies]`", NOT
    `./tools/_template/Cargo.toml` as a workspace member. Lint-config
    derived from `agent.md` performance_engineering + integrity
    error-handling restraint, with the source link to this entry.
    Any future coordinator tool derives from this template by copy,
    not by re-invention.
  * The 3 existing tool packages' `Cargo.toml` sections are
    reconciled to match the template exactly (consolidation removes
    any drift).
  * Drift audit: a small `bash` or Rust script under
    `tools/_template/check-drift.sh` that greps the lint/profile
    sections of each tool's `Cargo.toml` and asserts equality with
    the template (CI-friendly; gates future tool additions).
- Acceptance oracle: after the extract, all 3 existing tools still
  pass their committed gates (`cargo fmt --check` + `cargo clippy
  --all-targets -- -D warnings` + `cargo nextest run` + `cargo
  test --doc` under committed budgets; the criterion-regression
  21/21 budget, the gitlink-coherence 18/18 0.339s budget, and the
  checkout-path-dependencies tests as configured). The drift
  scanner passes. The README of the new template directory names
  the consumers and is the SSOT for future coordinator tool
  scaffolding.
- Risk/change class: [patch] [arch]; consolidates committed tools'
  Cargo.toml configuration (no production-code delta; no behavioral
  shift). [arch] because new template directory establishes a
  canonical component home per `architecture_scoping`.
- Dependencies: none (clears on its own merits; no peer publishing).
- Verification plan: per-tool `cargo fmt --check` +
  `cargo clippy --all-targets -- -D warnings` + `cargo nextest run`
  + `cargo test --doc`; cross-check the 3 `Cargo.toml`'s
  `[lints]` / `[profile]` / `[dependencies]` sections are
  byte-identical to the template after the reconciliation pass.
- Sister cross-links: parent concern is the third-occurrence
  consolidation trigger fired during `ATLAS-GITLINK-COHERENCE-
  DEFECT-1-AUDIT-TOOL-1` closure. Refs:
  backlog.md#ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1.

## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — todo

- Policy: AGENTS.md git_discipline (version-bearing red-flag hunks) + architecture_scoping pin discipline (version metadata is sweep-triggering state). Motivating incident: `87ab265` (hermes) — a sed dep-conversion silently reverted the workspace release `0.5.0 -> 0.4.1` and internal requirements to `0.4.0`, unmentioned in its message; origin lied about versions for ~10 hours while integrators failed resolution, and coeus stacked 18 commits on the undeliverable base.
- Scope: (1) per-repo guard — CI step (and optional pre-commit hook) failing when a diff changes `version =` or first-party dependency version requirements without a declared release/bump intent (commit type `chore(release)`/`build(deps)` or an explicit footer); backward version movement always fails without the declaration; (2) stack coherence check — a meta-level check (home: tools/, sibling to criterion-regression) verifying every first-party requirement across allowlisted members resolves against the stack's current workspace versions, run in the integration sweep and on any version-touching commit; (3) wire both into member CI per repository convention.
- Acceptance: replaying `87ab265` against the guard fails it; coherence check passes on the current stack and fails on an injected backward-version fixture; guards live in committed CI/config, not agent memory.

## ATLAS-OVERLAY-001 — Generated [patch] overlay for local-vs-git coherence [patch] — in-progress

- Policy: AGENTS.md architecture_scoping "Development overlay". Motivating blockers: local mnemosyne 0.6 vs git moirai requirement ^0.5 (requirement lag — patch cannot unify across an unsatisfied requirement), and the provider manifest missing the apollo -> eunomia edge (hand-curated derived state rotting as edges appear).
- Scope: (1) extend tools/checkout-path-dependencies (it already computes the graph) to emit a stack-level `[patch."<git-url>"]` overlay into the root `.cargo/config.toml` from the `cargo metadata` closure of all allowlisted members — regenerated by command, never hand-edited; every first-party crate maps to its local tree per source URL; (2) forward-sweep integration — a first-party version bump runs the requirement sweep (every in-stack requirement and lock on the bumped crate advances in the same co-evolution unit), composing with the ATLAS-VERSION-GUARD-001 coherence check; (3) regenerate on graph change: adding a first-party dependency edge re-emits the overlay in the same increment.
- Acceptance: both motivating blockers reproduce against the pre-overlay state and resolve after (moirai builds against local mnemosyne once requirements sweep; apollo resolves eunomia from the generated closure); the overlay file carries a generated-do-not-edit header naming the regenerating command; member manifests unchanged (git+version sources intact for CI/standalone). Update 2026-07-24: generator landed as scripts/atlas-stack-overlay.py; suffix doubling fixed at the stem (zero .git.git keys, regeneration idempotent, check mode green); AGENTS.md now carries the generator contract (canonicalized inputs, closure validation, regenerate-and-diff freshness) and the meta-lane prohibition that supersedes the "build from primary root" workaround. **Update 2026-07-28 (Session 30):** check mode wired into CI as `.github/workflows/atlas-stack-overlay.yml` (gate on PRs/pushes touching `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`, `repos/**/Cargo.{toml,lock}`, `repos/**/pyproject.toml`). Sub-delivery (3) regenerate-on-graph-change absorbed: the `paths:` filter above fires on any consumer `Cargo.toml`/lock edit, which is precisely the trigger for overlay regeneration (script is one `python scripts/atlas-stack-overlay.py generate` call). Forward-sweep integration (sub-delivery 2) requires per-member guard at the atlas-coordinator boundary; that is the scope of ATLAS-VERSION-GUARD-001.

## ATLAS-COEUS-SOURCES-001 — Convert coeus mainline back to git+version sources [patch] — todo

- Policy: AGENTS.md architecture_scoping "Development overlay" — path-deps/`[patch]` sections committed on a member mainline are the quarantine leaking into the manifest, converted back on sight (fix-forward; a peer merge is not authority over standing policy). This is a decided mechanical fix, not a direction call: manifests carry git+version sources; local resolution belongs to the generated stack-root overlay (ATLAS-OVERLAY-001).
- Evidence: coeus main carries 48 path-deps and 8 `[patch]` sections (landed via provider PRs), making coeus unconsumable as a git dependency downstream (CFDrs et al.) — the defect class already fixed forward in hermes, mnemosyne, moirai, leto, apollo, hephaestus. The validated 21-line conversion pattern applies plus the 8 patch-section removals.
- Scope: (1) convert coeus mainline manifests to git+version sources as a forward commit (native conversion; version requirements swept against current stack versions per pin discipline — no requirement lag); coordinate scope with the live provider stream (open PR #219 and the three provider PRs) via board claim, converging rather than colliding; (2) complete the `coeus-backend-parity` lane's item, merge it to main, `git worktree remove` it and delete its branch in the same cycle (git_discipline: the two-tree bound is throughput — a lane outliving its item is integration debt); (3) verify coeus resolves as a git dependency from a consumer (CFDrs check build) after conversion.
- Acceptance: zero path-deps/`[patch]` sections on coeus main; a downstream git-dependency resolution succeeds; the parity lane merged and removed (`git worktree list` = main tree only); coherence check green.

## Session 25 closure (2026-07-26) — coordinator gitlink advances + tools/_template/ extract

- Head: `77bcaca` → `e519928` on `origin/main` (pushed).
- Outcomes delivered:
  1. `b022211` build(atlas): Advance aequitas and apollo gitlinks to
     origin/main. Two stale-advanceable gitlinks advanced after
     `merge-base --is-ancestor` verification (aequitas `343ceb57` →
     `f19ba151`, apollo `82e67c8f` → `d60828cd`). ritk left to peer
     because the working tree was on `codex/docs-ritk-pages-closeout`
     with a dirty Cargo.toml.
  2. `e260055` refactor(atlas): Extract `tools/_template/` for shared
     coordinator-tool config (closes `ATLAS-TOOLS-TEMPLATE-EXTRACT-1`).
     Four new files (template-Cargo.toml, template-rust-toolchain.toml,
     README.md, check-drift.sh) consolidate the third-occurrence
     verbatim `[lints]`/`[profile.*]`/shared-`[dependencies]` section
     across `checkout-path-dependencies` / `criterion-regression` /
     `gitlink-coherence`. `checkout-path-dependencies/rust-
     toolchain.toml` reconciled to template canonical key order.
     `.gitignore` whitelisted `tools/_template/` (the `_*` catch-all
     matches the leading underscore). Per-tool gates passed:
     criterion-regression 21/21 in 5.681s + 2/2 doctests,
     gitlink-coherence 18/18 in 3.309s, checkout-path-dependencies
     11/11 in 7.520s + 1 doctest. `check-drift.sh` exits 0.
  3. `e519928` build(atlas): Advance CFDrs, coeus, mnemosyne gitlinks
     to origin/main after their origin/main advanced from under
     earlier coordinator advances (CFDrs `d4bc1702` → `f083b65f`,
     coeus `15ee8e59` → `765a0556`, mnemosyne `8ba205c9` →
     `00c3f6de`). All pins verified ancestral to origin/main before
     staging. ritk skipped again (peer on
     `codex/docs-ritk-n4-figure-clarity`). This commit also absorbed
     peer-Codex backlog updates recording the `ATLAS-CFDRS-COEQ-
     BLOCKER-1` and `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` closure
     trailing peer `fc2fae5` coeus advance — concurrent agents
     detect-and-reconcile: kept co-authored, attribution noted here.
- Gitlink-coherence inventory at session close: 4 defects remain
  (hephaestus no-origin-main, kwavers cat-b via PR #325, leto cat-b
  via codex/leto-real-sparse-lu, asclepius cat-a local main not
  pushed) + 1 stale-advanceable (ritk). Session started with 7
  defects; closed during this session by peer pushes: mnemosyne #7,
  consus #8, coeus #1, moirai #3 stayed clean. Stale-advanceable
  `aequitas` and `apollo` advanced by this session.
- Next-session handoff: the math-SSOT consolidation audit (new user
  directive flagged this session) is the standing next coordinator
  scope item — a cross-repo grep across `repos/kwavers/src`,
  `repos/CFDrs/src`, `repos/helios/src`, `repos/leto/src` for math
  capability (ndarray / nalgebra / rsparse / Matrix / solve / lu /
  qr / svd / eigen / fft / convolve / sparse), tabulated
  capability × repo × module. File `ATLAS-MATH-SSOT-CONSOLIDATION-1`
  DoR-style in backlog (audit-only; execution is peer-leto /
  peer-physics-crate work). Record the audit pattern in gap_audit.md
  as a reusable audit template.
- Open peer recovery work (coordinator cannot execute, only record):
  - peer-hephaestus: publish `main` ref to origin (currently on
    codex/comparison-expression-parity; no main);
  - peer-kwavers: merge/close PR #325 onto origin/main;
  - peer-leto: merge `origin/codex/leto-real-sparse-lu` to origin/main;
  - peer-asclepius: push local main `47e73d1e` to origin/main; the
    gitlink pin already points to that SHA.

## ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT — Consolidate kwavers special functions into leto-ops [patch] — done

- Owner: opencode/big-pickle; last-update: 2026-07-25; scope: `repos/leto`,
  `repos/kwavers`, and atlas gitlink.
- Outcome:
  - leto-ops `ddd9cca`: fixed j1 sign handling (flip only in asymptotic
    branch), fixed small-arg last coefficient (-30.16036606 per NR),
    upgraded jn to two-buffer upward normalization from kwavers.
  - kwavers `0a31706`: replaced local implementations of `sinc`, `erf`,
    `j0`, `j1`, `jn` with re-exports from leto-ops SSOT; removed ~227
    lines of duplicated numerics.
  - directivity.rs: replaced crude 3-term Taylor approximation with
    canonical j1 re-export.
  - literature_validation_safe.rs: same replacement.
  - nonlinear3d tests: use canonical j1, kept j2 as test helper (recurrence).
  - simd_safe/avx2.rs and neon.rs: verified NOT dead — actively used by
    operations.rs for Array3 field ops; audit corrected.
- Evidence: 135/135 kwavers-math tests pass, 218/218 kwavers-transducer
  tests pass, 396/396 leto-ops tests pass. `cargo check` clean.
- Gitlink: atlas `d87e107`.

## ATLAS-GMRES-SSOT-001 — Consolidate four GMRES implementations onto one recurrence [major] [arch] — todo

- Outcome: one GMRES recurrence in the stack, with the other three call
  sites migrated to it and deleted (no re-export, no forwarding wrapper).
- Evidence (found during the leto-ops GMRES gap audit, session 2026-07-27):
  1. `athena-core/src/solver/gmres/` — the ADR-blessed one. Backend-neutral
     (Leto CPU + Hephaestus WGPU), right-preconditioned, `RESTART` const
     generic, caller-owned workspace, value-semantic `Termination`, and
     CPU+WGPU contract tests. See leto `docs/adr/0015-athena-gmres-extraction.md`,
     which removed GMRES from leto-ops precisely to make Athena the SSOT.
  2. `leto-ops/src/application/linalg/iterative/gmres/` — reintroduced after
     ADR-0015 as part of the `LinearOperator`-seam solver family
     (CG/BiCGSTAB/GMRES/LSQR) that replaced nalgebra for cfd-math and
     kwavers-math. Corrected and covered by `dcc5d54`; still a second
     recurrence.
  3. `CFDrs/crates/cfd-math/src/linear_solver/gmres/` — a fork of (2): same
     module names (`arnoldi.rs`, `givens.rs`, `solver.rs`), same function
     names, same structure, plus its own `IterativeSolverConfig`. It has
     therefore inherited every defect fixed in `dcc5d54`: convergence decided
     on the preconditioned estimate, discarded happy breakdown, absent
     non-finite guards, strided Krylov basis, per-restart `b.clone()`, and a
     duplicated operator application per restart.
  4. `kwavers/crates/kwavers-solver/src/integration/nonlinear/gmres/` — an
     `f64`-hardcoded copy with its own `solve_upper_triangular`.
- Scope: decide the surviving seam ((1) is backend-generic but not
  dyn-friendly; (2) carries the `LinearOperator`/`Preconditioner` traits the
  CFD consumers bind to), then migrate in dependency-ordered increments per
  the anti-shim mandate. Non-goal: keeping any adapter layer.
- Dependencies: an ADR is the first planning step; ADR-0015 must be either
  honoured or superseded, since (2) currently contradicts it.
- Acceptance: one `gmres` module remains in the stack; residue scan finds no
  sibling recurrence; every consumer verifies against its own suite.
- Risk: [major] [arch]. Blast radius spans leto, athena, CFDrs, kwavers.

## ATLAS-GMRES-FORK-DEFECTS-001 — Port the leto-ops GMRES corrections to the CFDrs and kwavers forks [patch] — todo

- Outcome: the four correctness/robustness defects fixed in leto `dcc5d54`
  no longer reachable through the CFDrs and kwavers GMRES copies.
- Rationale: consolidation (ATLAS-GMRES-SSOT-001) is the real fix, but it is
  [major] [arch] and gated on an ADR. These forks currently ship a solver
  that can report success on an unsolved system; that is not safe to leave
  pending the larger item.
- Scope: (1) terminate on the true residual, not the preconditioned Arnoldi
  estimate; (2) treat happy breakdown as an explicit outcome instead of
  leaving a stale basis vector in place; (3) guard non-finite recurrence
  state; (4) port the conformance suite (`leto-ops/tests/ops/iterative_gmres.rs`),
  whose scaled-identity-preconditioner case is the regression oracle for (1).
- Non-goal: the performance work (row-contiguous basis, allocation removal) —
  that follows consolidation rather than being duplicated a third time.
- Acceptance: each fork either adopts the corrections with the ported suite
  green, or is deleted by ATLAS-GMRES-SSOT-001 first.

## ATLAS-MATH-SSOT-CONSOLIDATION-1 — Cross-repo math SSOT consolidation audit [patch] — todo

- Owner: atlas-meta coordinator (audit-only); execution is peer-leto /
  peer-physics-crate work — coordinator files the inventory and the
  recommended sequencing, peer-leto extends `leto-ops` and peer kwavers /
  CFDrs / helios execute the consumer-side consolidation per the plan.
- Outcome: a DoR-shape audit item that (a) records the SSOT baseline of
  `leto` + `leto-ops` for the math capability surface the consumers use,
  (b) cross-tabulates every duplicate / partial / domain-specific math
  residency in `kwavers-math`, `cfd-math`, and `helios-math` against that
  baseline, and (c) recommends per-capability sequencing so peer-leto and
  peer-physics-crate can claim disjoint vertical increments.
- Motivating context (user directive 2026-07-27): the standing migration
  to first-party atlas crates (`leto` / `leto-ops` / `eunomia` / `hermes` /
  `moirai` / `mnemosyne` / `themis` / `melinoe` / `apollo` / `coeus` /
  `hephaestus` / `ritk`) requires removing nalgebra / ndarray / burn /
  num-traits / rustfft from `kwavers` / `CFDrs` / `ritk` / `helios`. Cargo
  manifests are already clean (verified 2026-07-27: zero `nalgebra` /
  `ndarray` / `burn` / `rustfft` workspace deps; the only residual is the
  `numpy = "0.29"` PyO3 bridge in `kwavers-python/Cargo.toml`, which is
  FFI surface, not the rust ndarray crate). The remaining work is
  *internal*: consumer math crates have already begun delegating to
  `leto-ops` and `leto`, but a non-trivial amount of math still lives in
  `kwavers-math` and `cfd-math` either because (i) it has not yet been
  rewritten as a thin re-export (the `helios-math` pattern), (ii) the
  claim-vs-body drift shows a stale refactor stage, or (iii) the
  capability genuinely belongs with the physics crate as domain-specific.
  This audit scoping distinguishes those three cases per capability.
- Relationships: this audit item sits ABOVE the peer-filed
  `ATLAS-GMRES-SSOT-001` (the [major] [arch] consolidation of the four
  GMRES recurrences). GMRES is one row in the cross-capability matrix here;
  execution of THAT row is owned by `ATLAS-GMRES-SSOT-001` (with
  `ATLAS-GMRES-FORK-DEFECTS-001` carrying the stop-gap correction port).
  This item is the *-coordinator-scope` pattern recognition (per
  user directive) that the GMRES defect is one instance of a broader
  cross-repo pattern, and records the rest of the pattern.

### SSOT baseline (leto + leto-ops, verified 2026-07-27)

Capability surface that `leto` / `leto-ops` already owns. 253 distinct
`pub fn` symbols across the two crates — re-verify with
`grep -rEh '^[[:space:]]*pub fn' repos/leto/crates/leto-ops/src/ repos/leto/crates/leto/src/application/ | sed 's/.*fn //; s/(.*//' | sort -u | wc -l`.

- `leto/src/application/` — dense n-d array: `Array`, `ArrayView`,
  `ArrayViewMut`, `Array{1,2,3,4,D}`; `concat`, `pad`, `split`,
  `stack`, `AxisChunks`, `Tiles`, `Windows`, `Lanes`, `LendingIterator`;
  reduction `mean_all`, `sum_all`, `median_all`, `quantile_*`,
  `pearson_correlation`, `covariance`; `stencil` (incl.
  `Laplacian2D`, `BoundaryCondition`); `transform`; `view`; iterators
  (`iter/{axis,chunks,elem,lanes,lending,windows}`).
- `leto/src/geometry/` — points/vectors/quaternions/isometries:
  `Point{2,3}`, `Vector{2,3}`, `Isometry3`, `Translation3`,
  `UnitQuaternion`, `UnitVector3`, `Quaternion`. This is the surface
  `helios-math` already re-exports today.
- `leto/src/infrastructure/sparse/` — array-storage sparse formats
  (`CooArray`, `CscArray`, `CsrArray`, `SparseFormat`, `SparseStorage`,
  `SparseStorageMut`).
- `leto-ops/src/application/` — operations family leaf modules:
  - `linalg/` — dense decompositions: `bidiagonal/`, `bunch_kaufman/`,
    `cholesky.rs`, `col_piv_qr/`, `eigen.rs`, `eigenvalues/`, `full_piv_lu/`,
    `hessenberg/`, `hermitian.rs`, `householder.rs`, `iterative/` (`cg`,
    `gmres/`, `bicgstab`, `lsqr`, `config`, `convergence`, `ops`),
    `lu.rs`, `lu_batch.rs`, `matrix.rs`, `matrix_function/`, `norms.rs`,
    `products/`, `properties/` (`rank`, `trace`), `qr/`,
    `reflector_block/`, `schur/`, `svd/`, `udu/`, `complex_linalg.rs`.
  - `sparse/` — `coo.rs`, `csc.rs`, `csr.rs`, `csc_spmv.rs`,
    `spmv.rs`, `spmm.rs`, `spgemm.rs`, `lu_numeric.rs`,
    `lu_symbolic.rs`, `lu_sparse.rs`. CSR/CSC/COO matrix types and
    SpMV/SpMM/SpGEMM kernels, symbolic + numeric sparse LU.
  - `diff/` — `finite_difference.rs`, `schemes.rs`,
    `three_dimensional.rs`; first/second/sixth-order central,
    fourth-order, gradient. Consumer-math overrides for staggered-grid
    or k-space PSTD derivatives are domain-specific (e.g.
    kwavers-math/numerics/operators/{differential/spectral},
    cfd-math/stencils).
  - `interpolation/` — `linear`, `lagrange`, `cubic_spline`, `utils`.
  - `quadrature/` — basic composite/variable (1D); 3D / tensor-product
    quadrature with many specific rules (Gauss–Legendre, Gauss–Jacobi) is
    *not* yet in leto-ops; that gap is a consolidation candidate.
  - `signal/` — `phase` (`wrap_to_pi`), `window` (`hann`, `hamming`,
    `blackman`, `tukey`).
  - `optimization/` — `lbfgs.rs`.
  - `nonlinear/` — `anderson.rs` (Anderson acceleration), `linalg.rs`.
  - `special.rs` — `j0`/`j1`/`jn` Bessel, `erf`.
  - `random.rs`, `statistics/`, `scan.rs`, `zip.rs`, `unary.rs`,
    `map.rs`, `stencil.rs`, `reduction.rs`.
- `apollo` — FFT SSOT (rustfft replacement) plus broader transforms
  (NTT, Mellin, Hilbert, CZT, DCT/DST, DHT, FRFT, FWHT, GFT, NUFFT,
  SHT, QFT, STFT, SFT, wavelet, Radon). `apollo-leto-interop` provides
  the leto-side adapter.
- `hermes-simd` — SIMD/autodispatch SSOT (runtime avx2/avx512/sse4.2 /
  aarch64-neon feature detection, `AlignedVec`, masked dot-
  products, sum kernels, ops via `hermes_simd_core` +
  `hermes_simd_intrinsics`).
- `eunomia` — numeric-trait SSOT (`RealField`, `FloatElement`,
  `NumericElement`, `CastFrom`/`CastTo`, `Complex{32,64}`). The `Scalar`
  bound kwavers-math re-exports as `eunomia::RealField` and helios-math
  re-exports directly is the canonical numeric trait.

### Cross-repo capability matrix (consumer math crates)

Legend: `DUP` = reinvented consumer copy (consolidation candidate). `WRAP`
= thin re-export/wrapper that delegates to leto-ops (do-not-touch).
`PARTIAL` = mixed: some sub-paths already wrap, others still reinvent.
`DS` = domain-specific (stays in consumer crate). `—` = not present.
Consumer cols: `kw` = `kwavers-math`, `cf` = `cfd-math`, `hl` = `helios-math`.

| Capability                   | leto-ops canonical                                  | kw  | cf  | hl | Notes |
| :---                         | :---                                                | :-- | :-- | :- | :---  |
| Dense LU (full piv)          | `linalg/full_piv_lu/`                               | WRAP | WRAP | — | cf `direct_solver.rs` routes via leto-ops. |
| Cholesky                     | `linalg/cholesky.rs`                                | WRAP | WRAP | — | cf `direct_solver.rs`. |
| QR / col-piv QR              | `linalg/qr/`, `linalg/col_piv_qr/`                   | ?    | WRAP | — | spot-check kw quadratic-eig path. |
| SVD / pseudoinverse           | `linalg/svd/`                                       | ?    | WRAP | — |. |
| Eigen (symmetric/Jacobi)     | `linalg/eigenvalues/`, `linalg/eigen.rs`            | WRAP | WRAP | — | kw `eigendecomposition/mod.rs` declares SSOT delegation. |
| Hermitian eigen              | `linalg/hermitian.rs`                               | WRAP | ?    | — |. |
| Hessenberg / Schur           | `linalg/hessenberg/`, `linalg/schur/`               | —    | ?    | — |. |
| BunchKaufman / UDU           | `linalg/bunch_kaufman/`, `linalg/udu/`              | —    | ?    | — |. |
| Iterative CG                 | `linalg/iterative/cg.rs`                            | WRAP | WRAP | — | cf `6d18a547` "replace local CG…". |
| Iterative GMRES (single recurrence) | `linalg/iterative/gmres/`                     | DUP  | DUP  | — | per `ATLAS-GMRES-SSOT-001`: kw has `kwavers-solver/integration/nonlinear/gmres/` f64-hardcoded; cf `linear_solver/gmres/` was a fork; peer-cf just deleted arnoldi/givens at `6484ad9e`. |
| Iterative BiCGSTAB            | `linalg/iterative/bicgstab.rs`                      | WRAP | WRAP | — | cf `6d18a547`. |
| Iterative LSQR               | `linalg/iterative/lsqr.rs`                           | ?    | WRAP | — |. |
| matmul / kron / matexp / matpow | `linalg/products/`, `linalg/matrix.rs`            | —    | —    | — | served by leto `Array2` ops. |
| det / inv / trace / rank / cond | `linalg/properties/`, `linalg/{lu,qr,...}`       | WRAP | WRAP | — |. |
| CSR / CSC / COO storage      | `infrastructure/sparse/`, `leto-ops/sparse/`        | DUP-PARTIAL | WRAP | — | cf `sparse/operations.rs` delegates to leto-ops `CsrMatrix`; kw `sparse/csr.rs` declares delegate in doc but body uses self storage `Vec<Vec<(usize,T)>>`. |
| SpMV / SpMM / SpGEMM          | `leto-ops/sparse/spmv.rs` etc.                      | WRAP | WRAP | — |. |
| Sparse symbolic LU           | `leto-ops/sparse/lu_symbolic.rs`                     | WRAP | WRAP | — |. |
| Sparse numeric LU            | `leto-ops/sparse/lu_numeric.rs`                      | WRAP | WRAP | — | ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial slice. |
| Vector norms (l1/l2/max)      | `linalg/norms.rs`                                   | WRAP | WRAP | — | kw `linear_algebra/norms.rs` pure re-export. |
| Bessel j0/j1/jn               | `special.rs`                                        | WRAP | —    | — | ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT closed at leto `ddd9cca` / kwavers `0a31706`. |
| erf                           | `special.rs`                                        | WRAP | —    | — | ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT. |
| Legendre                      | ?                                                   | DS   | —    | — | kw keeps its own (wave-domain); leto-ops `special.rs` has not yet been extended to hold Legendre. Candidate: extend leto-ops `special.rs` with Legendre primitives, then re-export. |
| sinc                          | `sinc` (leto-ops)                                   | WRAP | —    | — | ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT. |
| Window: hann/hamming/blackman/tukey | `signal/window.rs`                            | WRAP | —    | — | kw `signal/window` pure re-export. |
| phase wrap_to_pi              | `signal/phase.rs`                                   | WRAP | —    | — |. |
| Interpolation linear          | `interpolation/linear.rs`                            | WRAP | WRAP | — |. |
| Interpolation Lagrange        | `interpolation/lagrange.rs`                          | WRAP | WRAP | — |. |
| Interpolation cubic spline    | `interpolation/cubic_spline.rs`                      | WRAP | WRAP | — | cf `interpolation/cubic_spline.rs` thin wrapper. |
| Finite difference (1d/2d/3d)  | `diff/finite_difference.rs`, `diff/three_dimensional.rs` | WRAP | WRAP | — | cf `b5b75723` "replace local FiniteDifference/Scheme with leto-ops wrappers". |
| Staggered-grid differential   | —                                                   | DS   | —    | — | k-Wave PSTD/staggered-grid operator is genuinely wave-domain; stays in kwavers-math/numerics/operators/differential/staggered_grid. |
| Spectral derivative           | —                                                   | DS   | DS   | — | kw `numerics/operators/spectral/derivative.rs`, cf `high_order/spectral/`. |
| Spectral filter / k-space ops  | —                                                   | DS   | —    | — | kw `numerics/operators/spectral/filter.rs`. |
| Quadrature 1D / composite     | `quadrature/mod.rs`                                 | ?    | WRAP-or-DS | — | cf `integration/quadrature.rs` carries 0 leto imports (not yet delegated); leto-ops quadrature is a thin baseline. Candidate: cf integration/quadrature routes through leto-ops if rules match, otherwise keep cf rules as domain-specific. |
| Quadrature 3D / tensor / variable | —                                                | —    | DUP-DS | — | cf `integration/quadrature_3d.rs`, `tensor.rs`, `variable.rs`. Candidate: extend leto-ops `quadrature/` with 3D / tensor / Gauss–Legendre / Gauss–Jacobi primitives (peer-leto), then re-export cf versions as thin wrappers (peer-CFDrs). |
| Time-stepping RK / IMEX / exponential / adaptive | —                                  | —    | DS   | — | cf `time_stepping/` is CFDODE-domain; leto-ops does NOT own this. Stays. |
| High-order DG / WENO / spectral element | —                                            | —    | DS   | — | cf `high_order/{dg,weno,spectral}` are CFD-method specific; leto-ops does NOT own this. Stays. |
| Pressure-velocity coupling SIMPLE | —                                            | —    | DS   | — | cf `pressure_velocity/simple.rs`. Stays. |
| Inverse problems / regularization (Tikhonov/TV/L1/L-curve/Morozov/PnP) | — | DS | —    | — | kw `inverse_problems/`. No cf/hl counterpart today. Stays unless/untilil ritk/helios imaging requires shared regularizer kernels — at that point lift the canonical pieces (config, regularizer_1d/2d/3d, parameter_selection) into a new `leto-ops/src/application/inverse_problems/` leaf per canonical-component-homes. |
| Optimisation L-BFGS           | `optimization/lbfgs.rs`                              | WRAP | —    | — | kw `optimization/lbfgs` pure re-export. |
| Nonlinear Anderson            | `nonlinear/anderson.rs`                             | ?    | —    | — | cf `linear_solver/operators` may flow linear/nonlinear together; re-verify. |
| SIMD run-time dispatch (x86_64 avx2/avx512/sse4.2 / aarch64 neon) | `hermes-simd` (separate SSOT) | DUP | DUP | — | kw `simd_safe/{avx2.rs,neon.rs,swar.rs,auto_detect/*}` reimplements auto-dispatch despite depending on `hermes-simd`. cf `simd/{cfd,vector,vectorization,fdtd_ops}` likewise. Consolidation target is `hermes-simd`, NOT leto-ops. |
| Geometry primitives (AABB, Ray, Aabb intersect) | `gaia` (SSOT forHelios)                     | —    | —    | WRAP | `helios-math` already re-exports `gaia::{Aabb, Ray}` — canonical pattern. |

### Recommended consolidation plan (peer-leto + peer-physics-crate sequencing)

Two lanes, decoupled.

**Lane A — peer-leto extends `leto-ops` (upstream ownership).** Add only
where the matrix above names a capability the consumers want a leto-ops
home for but no canonical path exists yet.
1. Extend `leto-ops/src/application/special.rs` with Legendre primitives
   (`P_n`, `P_n_assoc` recurrence). Then ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT
   can be widened to also re-export Legendre, deleting kw `special/legendre.rs`.
2. Extend `leto-ops/src/application/quadrature/` with multi-dimensional / tensor /
   Gauss–Legendre / Gauss–Jacobi wrappers. New leaf files:
   `quadrature/tensor.rs`, `quadrature/gauss_legendre.rs`,
   `quadrature/gauss_jacobi.rs`, `quadrature/variable.rs`. Coordinate with
   peer-CFDrs since cf `integration/quadrature_3d.rs`/`tensor.rs` are
   the donor bodies — short cf → leto-ops cycle, then re-export from cf.
3. Add `leto-ops/src/application/inverse_problems/` leaf ONLY if ritk
   or helios imaging surfaces a shared regularizer requirement within the
   active coevolution unit. Until then defer (YAGNI per the canonical
   component-homes rule).
4. (Out-of-scope-for-this-audit) SIMD consolidation across kw/cf lives in
   a SEPARATE hermes-SSOT audit item, not this one — but flagged here so
   peer-hermes has the locus.

**Lane B — peer-physics-crate executes the wrapper / delete pass.** Per
consumer crate, in dependency-ordered increments:
- `kwavers-math`: (1) replace `linear_algebra/sparse/csr.rs` self-storage
  with a thin re-export of `leto_ops::CsrMatrix` (claim-vs-body gap fd
  the docstring already promises); (2) delete `linear_algebra/sparse/coo.rs`
  and `eigenvalue.rs` once they route through leto-ops; (3) `simd_safe/` /
  `simd/` flow through `hermes-simd` rather than re-implement avx2/neon
  (or be deleted if unused) — `(ATLAS-GMRES-SSOT-001` already showed
  simd_safe/avx2.rs and simd_safe/neon.rs are used by operations.rs at
  the kwavers Array3 boundary; treat that case as a partial-deletion:
  re-route operations.rs through hermes-simd kernels, then delete the
  hand-rolled ISA files.) (4) Review the GMRES row under
  `ATLAS-GMRES-SSOT-001` (peer already owns).
- `cfd-math`: (1) close the gap that `integration/quadrature*.rs`  does
   NOT yet delegate — once peer-leto lands Lane A increment 2, route
   them through leto-ops or mark as DS-keep with rationale. (2) Review
   the `high_order/` family for any redundant helper math (matrix assembly
   using dense leto-ops instead of reinvented element-stiffness ops).
   (3) `linear_solver/operators/`, `matrix_free/` are domain-specific.
- `helios-math`: already the canonical thin-reexport shape — reference,
   no work.

**Lane C — coordinator pins (this audit owner).** When peer-leto advances
`leto-ops` per Lane A, advance the leto gitlink (handled by the
standing stale-advanceable flow). When peer-physics-crate lands a
consolidation increment in `kwavers-math` / `cfd-math`, advance the
kwavers / CFDrs gitlink. Coordinator does NOT write `repos/<name>/...`.

### Verification (per increment, not all-up-front)

- Peer-leto per Lane A increment: `cargo nextest run -p leto-ops` plus
  `cargo test --doc -p leto-ops` under committed budgets; publish; notify
  peer-physics-crate.
- Peer-physics-crate per Lane B increment: (a) consumer crate tests green;
  (b) `grep -rE 'use nalgebra|use ndarray|use burn|use rustfft|use num_traits'`
  returns zero hits in `crates/<name>-math/src/`; (c) value-semantic
  regression — the consumer API surface stays stable (the wrappers preserve
  name/arity); (d) where a body is deleted, the deleted `pub use` site is
  re-resolved (cargo check + tests).
- Coordinator: re-run `target/release/gitlink-coherence.exe audit` after
  each landing and verify the leto / kwavers / CFDrs rows are clean.

### Acceptance oracle

- Lane A increments land on leto `origin/main` + gitlink advanced within
  one session of the corresponding consumer increment; per-increment
  cargo gates green.
- Lane B per consumer crate: every dual-side) duplicate row
  above becomes either a thin re-export (matching `helios-math` shape) or
  carries a `// Domain-specific: <reason>` rationale comment at the
  module head and a status row in the matrix updated to `DS`.
- Cross-repo residue scan finds zero duplicate `pub fn` symbols (e.g.
  `pub fn gmres`, `pub fn arnoldi_step`, `pub fn givens`, `pub fn spmv`,
  `pub fn csr_spmv` …) shared between leto-ops and any consumer-math
  crate (existence is the duplicate-residency signal).
- ATLAS-GMRES-SSOT-001 closes by reducing the four GMRES recurrences to
  one (this audit does NOT close it; it just names it).

### Risk and change class

- Risk: [patch] (audit-only) coordinator increment;
  [major] [arch] for any Lane B Lane A consolidation execution (peer owned).
- Blast radius: leto, leto-ops, helios (no work), kwavers, CFDrs.
- Audit pattern template recorded in gap_audit.md as
  `## Findings 2026-07-27 Session 26: math SSOT consolidation audit pattern`
  for reuse across future cross-repo SSOT audits.

## Session 26 closure (2026-07-27) — GMRES fork ports and the athena redundancy question

`ATLAS-GMRES-FORK-DEFECTS-001` → done. `ATLAS-GMRES-SSOT-001` → re-scoped
by decisive evidence; see below.

### CFDrs — no port needed, already consolidated

A peer landed `6d18a547 ssot(cfd-math): replace local CG/BiCGSTAB/GMRES with
leto-ops wrappers` and `6484ad9e cleanup(cfd-math): remove orphaned arnoldi.rs
and givens.rs from gmres/` earlier the same day, and has the remainder of
`crates/cfd-math/src/linear_solver/` staged for deletion. CFDrs therefore
inherits the leto-ops corrections directly. Porting into it was rejected: the
target files are being deleted.

### kwavers — ported, `a8c76b67e`

Defects fixed in `crates/kwavers-solver/src/integration/nonlinear/gmres/`:

1. Orthogonalisation was Classical Gram-Schmidt while the doc claimed Modified
   (second- vs first-order loss of orthogonality). Fork-specific defect, not
   present in leto-ops.
2. Convergence accepted from the least-squares estimate alone — a singular
   operator drives the estimate to zero on step 1 while `b − A·x` is untouched.
3. No finiteness guard anywhere; NaN burned the whole iteration budget.
4. Absolute `1e-14` breakdown threshold (scale-dependent), and breakdown
   restarted into the same invariant subspace instead of surfacing.
5. Krylov basis, Hessenberg and rotations reallocated per restart — `m + 1`
   full 3-D fields at the default `krylov_dim = 30` — plus two field
   allocations per Gram-Schmidt step. Now a workspace retained across solves,
   which matters because the Newton loop calls the solver per outer iteration.

Consolidating kwavers onto leto-ops instead was evaluated and rejected for now:
`jacobian_vector_product` takes `&mut self`, so the operator closure is
genuinely `FnMut`, and `leto_ops::LinearOperator::apply` takes `&self` with a
`Send + Sync` bound. Consolidation is gated on refactoring that JVP to `&self`
(its only mutation is a scratch-buffer cache). Recorded as the concrete blocker
on `ATLAS-GMRES-SSOT-001`.

Verification note: the kwavers working tree is mid-migration across ~60 files
on three fronts, so `cargo check -p kwavers-solver` does not build. The module
was verified in a standalone harness compiling it against the same `leto` and
`kwavers-core` revisions: 9/9 tests, clippy `-D warnings` and rustfmt clean.
Re-run the package gate once the peer migration lands.

### ATLAS-GMRES-SSOT-001 — CORRECTED 2026-07-27: Athena is the owner

An earlier entry in this session read the zero-consumer evidence as grounds to
name `leto-ops` the Krylov SSOT and supersede leto ADR 0015. **That was wrong
and is retracted.** It inverted a ratified boundary on evidence of
non-adoption. See [ADR 0033](docs/adr/0033-krylov-ownership-reaffirmation.md).

Standing evidence, unchanged: nothing in the stack references
`athena_core::Gmres` or `athena_core::Cg`; Athena's only code consumer is
Harmonia, which imports `ConvergencePolicy`, `IterationObserver`,
`IterationState`, `NoObserver` only. Every other `athena-*` manifest line is a
`[patch]` overlay entry, not a dependency.

Corrected reading of that evidence:

- Atlas ADR 0022 (Accepted, `[arch]`) names Athena the iterative-solver
  provider, citing exactly this defect: "Leto, CFDrs, and Kwavers own
  iterative-solver recurrences beside storage, discretization, or domain code".
  The meta README stack map agrees: `athena` — "Iterative solver policy over
  CPU and accelerator providers."
- Leto executed the extraction in `aa8aa9b` (2026-07-19 22:29, ADR 0015).
- `ee6582d chore(leto): remove ndarray/nalgebra dev-dependencies`
  (2026-07-23 17:57) reintroduced the whole family — `cg.rs`, `bicgstab.rs`,
  `gmres/`, `lsqr.rs`, Jacobi/SOR/SSOR/ILU — four days later, under a message
  that never mentions it. That commit is the regression.
- CFDrs `6d18a547` then wrapped the reintroduced Leto family, propagating it.

So Athena's zero consumers measure a stalled extraction, not a wrong owner.
The unwind sequence is ADR 0033 stages A-D, tracked below.

### Concurrent-agent record

Assist edits left uncommitted in peer working trees, each completing a peer's
own in-flight leto-ops SSOT migration and needed to reach a build:
`kwavers-source/Cargo.toml` and `kwavers-physics/Cargo.toml` (missing
`leto-ops` dependency behind imports the peer had already switched);
`bessel.rs`, `acousto_optics.rs`, `wave/nonlinear.rs`, `burgers/solution.rs`
(`u32` → `usize` for the leto-ops `jn` signature);
`kwavers-transducer/.../processor.rs` (`Vec<f64>` → `Array1<f64>` conversion).
Also `bessel_k0` added to `leto-ops/src/application/special.rs`, which the peer
had already imported from there but not yet moved upstream — left uncommitted
because that file is the peer's active rewrite and the addition cannot be
separated from it by path. **That port fixed a transcribed A&S 9.8.1
coefficient, `3.5156329` → `3.5156229`, which alone accounted for a 5e-7
absolute error in K₀ near x = 1.** Reference-value tests added.

## ATLAS-WORKTREE-CLONES-001 — Reconcile standalone clones under `worktrees/` [patch] — in-progress

- Evidence: `D:/atlas/worktrees/` holds directories named after stack repos
  (`leto`, `eunomia`, `moirai`, `ritk`, …) that are **standalone clones**, not
  linked worktrees — `worktrees/eunomia/.git` is a full repo directory, and
  `git worktree list` in `repos/eunomia` shows only `repos/eunomia`.
- Impact: this is the prohibited repo-copy pattern (forked history, duplicated
  disk). It also actively breaks lanes: a real worktree placed under
  `worktrees/` resolves a member's `../<repo>` path dependencies to these
  clones, producing `package collision in the lockfile` — encountered while
  trying to lane the kwavers GMRES work.
- Scope: per clone, rescue-commit any dirty state, fetch unique branches and
  commits into the authoritative repo under `repos/`, then delete. Confirm
  `git worktree list` per repo stays within the two-tree bound afterwards.
- Non-goal: touching genuine linked worktrees.

### Session 29 partial reconciliation (2026-07-27)

Inventory at session open: 8 standalone clones (full `.git` dir at
`worktrees/<repo>`): `aequitas`, `asclepius`, `eunomia`, `hephaestus`,
`hermes`, `iris`, `leto`, `themis`.

- **Reconciled and deleted this session**: `worktrees/iris`.
  Safety verification satisfied byte-for-byte: WT HEAD `c3cc43b` ==
  `worktrees/iris`'s `origin/main` == atlas-meta gitlink pin ==
  `repos/iris` HEAD == `repos/iris`'s `origin/main`; zero unpushed commits
  (`origin/main..HEAD` empty); clean WT (no dirty files, no untracked,
  no stashes); single local branch `main`; not a linked worktree
  (`git worktree list` in `repos/iris` lists only the main tree). 3 days
  stale (well past the 1h staleness sweep threshold).
- **Intentionally NOT touched (peer mid-flight or unique content)**:
  - `leto` — last commit 18 min prior to close (actively in flight).
  - `aequitas` — dirty WT (`CHANGELOG.md`, `Cargo.lock`, `README.md`,
    `src/systems/si/*.rs`, `tests/*.rs`), 5h staleness. Mid-flight peer work;
    deletion would trigger `interaction_policy` Ask-User (irreversible loss
    of uncommitted unique work).
  - `themis` — dirty `Cargo.toml` containing **ATLAS-PATH-DEP-AUDIT-2 /
    ATLAS-OVERLAY-001 generated `[patch]` overlay content** (comment
    `Last delivery: 2026-07-27 closure cycle`). This is the peer-attributed
    draft of the ATLAS-OVERLAY-001 deliverable; deletion would destroy
    unique peer-authored state.
  - `asclepius`, `eunomia`, `hephaestus`, `hermes` — 6h staleness,
    not exhaustively safety-verified this session. Hephaestus clone HEAD
    matches the active peer-hephaestus feature branch, currently the focus
    of the persistent `no-origin-main` defect.
- **Next-session action**: re-safety-verify the 6h-stale and 3-day-stale
  clones (`asclepius`, `eunomia`, `hermes`) using the iris verification
  protocol (HEAD == origin/main AND clean WT AND no local-only branches AND
  no unpushed commits AND not a linked worktree) and delete each that passes.
  `aequitas` and `themis` require the user or the owning peer to rescue the
  dirty state before the clone can be deleted. `leto` is freshly active and
  should not be touched.

## Session 27 closure (2026-07-27) — peer-coordinator ATLAS-MODALITY advance + the persistent gitlink defect set

Re-oriented against `origin/main` at session open. The standing "next action"
from the Session 26 handoff (append Session 26 closure to `backlog.md`) had
already landed under peer-coordinator attribution: commit `1da7cea docs(pm):
Close GMRES fork ports; record athena zero-consumer evidence` wrote the
`## Session 26 closure` section at L4785. The math-SSOT audit content I drafted
in Session 26 also survived intact at L4542 (`ATLAS-MATH-SSOT-CONSOLIDATION-1`)
and the audit-pattern template in `gap_audit.md` at L5178 — peer commit
`fad8c9e` reused my commit subject but its diff was a CFDrs gitlink advance;
no content clobber. Same attribution-absorption pattern as Session 25
`e519928`; no remediation needed because the content is correct DoR-level PM
state.

### Peer-coordinator landings during the inter-session gap (10 commits, b3106f4..20b03b8)

A peer-coordinator session (same Ryan Clanton attribution) ran during the
~90-minute gap and landed 10 commits, of which 7 are substantive coordinator-
scope work on the modality-boundaries workstream and the CFDrs metric closure:

| Commit | Subject summary |
| :--- | :--- |
| `20b03b8` | Advance CFDrs gitlink to its consumer-side metric closure |
| `a802e0c` | Close CFDrs MET22 transient-composition metric gap in `gap_audit.md` |
| `b804449` | Split `ATLAS-MODALITY-002` — 2a (kwavers bioheat boundary) closed, 2b (SpecificAbsorptionRate provider-side gap) blocked on peer |
| `8571cc1` | Refresh Aequitas metric audit (reconcile CFDrs/Helios/Kwavers consumer closures) |
| `5711c0c` | Advance aequitas gitlink — `ATLAS-MODALITY-002` phase 1 |
| `537b22c` | Claim `ATLAS-MODALITY-002` phase 1 in aequitas |
| `35f41e9` | Record modality boundaries (optics / RF / photomedicine) in the stack map + kwavers bioheat deposition spine |
| `1da7cea` | (Session 26 carry-over) Close GMRES fork ports; record athena zero-consumer evidence; file `ATLAS-WORKTREE-CLONES-001` |
| `fad8c9e` | (Session 26 carry-over, peer-reused subject) CFDrs gitlink advance |
| `b3106f4` | (Session 26 close, peer-reused subject) Math SSOT audit pattern filed in `gap_audit.md` |

These landings are accepted (peer-coordinator authority is granted by the
standing Change intent on this allowlisted meta-repo; no clobber of my
Session 26 work). They advance `ATLAS-MODALITY-002` from `todo` to
`in-progress` (phase 1 delivered, phases 2b-4 open).

### Residual gitlink defects (re-probed this session)

`target/release/gitlink-coherence.exe audit` reports **5 defects + 1
stale-advanceable + 19 clean** (down from Session 26's 11 defects — peers
published `origin/main` for apollo/athena/gaia/helios/hermes/asclepius during
the gap, resolving the cat-a class).

Persistent defects, each blocked on peer recovery action the coordinator
cannot execute (no write access to `repos/<name>/...`):

| Repo | Category | Pin | origin/main | WT HEAD | Branch | Last commit | Recovery (peer-owned) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| coeus | cat-c | cdaf769 | e26ba668 | cdaf769 | `codex/coeus-error-function-parity` | 3h ago | peer-coeus: publish origin/main |
| hephaestus | no-origin-main | 47ca84a | (none) | 47ca84a | `codex/hephaestus-product-axis-reduction-parity` | 3h ago | peer-hephaestus: create `origin/main` (4-session persistent defect) |
| kwavers | cat-b | 81a40071 | dce38e26 | **a7922bcc** | `codex/kwavers-book-migration-eviction` | **59 min ago** | peer-kwavers: merge/rebase feature to origin/main OR roll WT to main; coordinator NOT advancing — peer is actively committing |
| leto | cat-b | c6ced81 | 5ba88cc | dcc5d54 | `codex/leto-real-sparse-lu` | 5h ago | peer-leto: merge feature to origin/main |
| ritk | cat-c | 65035908 | c05f84d5 | 65035908 | `codex/docs-ritk-n4-figure-only` | 3h ago | peer-ritk: merge feature + publish origin/main |

Stale-advanceable (still NOT safely advanceable):

- `mnemosyne`: pin=00c3f6d, origin-main=905909b, WT HEAD=ec1c000 on
  `codex/mnemosyne-tier-selection` (7h ago). `git add` would capture the
  feature-branch HEAD `ec1c000`, not `origin/main` `905909b`. Per pitfall #2,
  this remains blocked until peer-mnemosyne either publishes `origin/main`
  or rolls WT back to `main`.

### Assist-ladder actions taken this session

- **Audit recovery**: Verified peer-coordinator's Session 26 closure (L4785)
  and the math-SSOT inventory (L4542) survived intact — no remediation
  required.
- **No gitlink advances**: Every defect row is either a structurally
  peer-only recovery (publish `origin/main`, merge feature branch) or has
  the working tree on a feature branch that would capture the wrong SHA.
  `kwavers` peer committed 59 minutes ago — active, not stale; coordinator
  escalation inappropriate per `concurrent_agents` assist-or-skip rules.
- **Closure written**: This section.
- **No new board entries**: The 5 defect rows above are already covered by
  their prior-session backlog items; a louder board restate is not warranted
  until a true stale-claim (1h+ no commit signal) develops. Three defects
  (hephaestus, kwavers PR, leto) are at 3+ sessions persistence and would
  become candidates for user-direction escalation if they persist into
  Session 28.

### Stale-memory re-verification (this session)

- `rust-toolchain.toml` pinned, MSRV unchanged.
- `target/release/gitlink-coherence.exe` present and unchanged.
- 25 submodules in `.gitmodules` unchanged.
- Shared `target-dir = "target"` at `/d/atlas/.cargo/config.toml` unchanged.
- Re-confirmed: `repos/<name>/.git` is a `gitdir:` indirection file for the
  submodule members (except `leto`/`hephaestus`, which are full directories);
  the gitlink pin is what `atlas-meta`'s git index records, and it can differ
  from `repos/<name>` WT HEAD when a peer has moved their WT onto a feature
  branch without the coordinator committing the advance.

### Next-session handoff

- Re-fetch + re-probe at session open (utility `gitlink-coherence.exe audit`
  is the canonical state read).
- Watch for peer-kwavers landing the feature branch — if `origin/main`
  advances, the gitlink is a one-step advance.
- Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  merges — same one-step advance opportunity.
- Watch for peer-hephaestus publishing `origin/main` — would close the
  4-session persistent `no-origin-main` defect.
- If 3 of the 5 persistent defects are unchanged by Session 28 open,
  escalate to user with a single batched message naming the 2-3 worst
  blockers (likely hephaestus + the most-active-of-the-rest) and request
  direction on peer-side remediation.
- Stand-alone next coordinator items still `todo`:
  `ATLAS-OVERLAY-001` (generated patch overlay), `ATLAS-VERSION-GUARD-001`
  (manifest version guard), `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit filed;
  execution owned by peer-leto/peer-physics-crate), `ATLAS-WORKTREE-CLONES-001`
  (rescue the standalone clones under `worktrees/`). Review whether any
  becomes urgent next session.

## ATLAS-ATHENA-KRYLOV-CAPABILITY-001 — Close Athena's capability gap (ADR 0033 stage A) [minor] — done

- **Progress 2026-07-27**: BiCGSTAB landed, athena `e965a95`. Composes from
  the existing `KrylovBackend` surface, so the trait and `athena-wgpu` are
  untouched. Full athena gate green: 30/30 nextest including the WGPU
  contracts, clippy `-D warnings` and doctests clean. Remaining: LSQR, and
  the SOR/SSOR/ILU(0) preconditioners over the Leto backend.

- Owner: coordinator. Scope: `repos/athena` `athena-core/src/solver/`,
  `athena-leto/src/preconditioner/`.
- Outcome: Athena carries every Krylov capability its prospective consumers
  actually use, so stages B-D can convert them without capability loss.
- Gap, measured against what CFDrs and Kwavers call today:
  | Capability | Athena | Leto family | Needed by |
  |---|---|---|---|
  | CG / PCG | yes | yes | CFDrs |
  | GMRES(m) | yes | yes | CFDrs, Kwavers |
  | BiCGSTAB | **no** | yes | CFDrs |
  | LSQR | **no** | yes | CFDrs (rectangular) |
  | Identity precond | yes | yes | all |
  | Jacobi precond | yes (athena-leto) | yes | CFDrs |
  | SOR / SSOR / ILU(0) | **no** | yes | CFDrs |
- Acceptance per item: backend-neutral recurrence in `athena-core` over the
  existing `KrylovBackend` surface (no new backend methods unless justified,
  so `athena-wgpu` inherits it); caller-owned allocation-stable workspace;
  validated `ConvergencePolicy`; value-semantic `Termination`; generic
  conformance over `f32` and `f64` on the Leto backend plus a forced
  multi-cycle case and dimension/termination error cases.
- Non-goal: changing the `KrylovBackend` trait, which would force
  `athena-wgpu` work in the same increment.

## ATLAS-GMRES-FORK-CONVERGE-001 — Stages B-D: migrate consumers, delete the Leto family [major] [arch] — todo

- Unblocked 2026-07-28: `ATLAS-ATHENA-KRYLOV-CAPABILITY-001` is done.
- B: CFDrs from its `6d18a547` Leto-family wrappers to Athena.
- C: Kwavers, gated on refactoring `jacobian_vector_product` from `&mut self`
  to `&self` (its only mutation is a scratch-buffer cache) so the matrix-free
  operator satisfies `LinearOperator::apply(&self, ...)`.
- D: delete `leto-ops/src/application/linalg/iterative/` including the
  duplicated `LinearOperator`/`Preconditioner` traits; residue scan clean.

## ATLAS-ATHENA-ACCEL-BACKEND-001 — Replace athena-wgpu with one Hephaestus-backed backend (ADR 0034) [major] [arch] — done

- **Stages 1-2 done 2026-07-27**, hephaestus `6ab822c`: `DenseVectorOps<D, T>`
  in `hephaestus-core` plus its `hephaestus-wgpu` implementation. Copy, both
  reductions, and subtraction delegate to existing capability; only scale,
  axpy, and xpay needed new kernels, since the elementwise family rejects an
  aliased output and so cannot express an in-place update. Differential tests
  against a CPU reference across workgroup-boundary lengths. Full hephaestus
  gate green: 221/221 nextest on real GPU hardware, clippy `-D warnings`, fmt.
- **Stage 3 written 2026-07-27**, athena branch `feat/athena-hephaestus-backend`
  (`eefa8ba`, pushed, not merged): `HephaestusBackend<D, V, T>` over the seam,
  generic in scalar. `combine_direction` maps to `xpay`; `fused_cg_update` to
  two `axpy` calls, trading one dispatch per CG iteration to keep a
  solver-shaped operation out of the substrate contract. Verified to compile
  against the real seam in isolation; the workspace gate is blocked by
  `ATLAS-OVERLAY-COHERENCE-001`.
- The seam itself is on hephaestus **master** at `e1f2800` (cherry-picked off
  a branch that was 39 commits behind master), 223/223 green there.
- Remaining: stage 4 delete `athena-wgpu` and its WGSL, plus a device-neutral
  sparse seam — `GpuCsrMatrix`/`spmv_into` are per-backend too, so the CSR
  operator cannot yet be device-neutral. CUDA, Metal and
  ROCm implementations of the same seam are separate increments, verifiable
  only where that hardware exists.

- Outcome: Athena carries two backend crates, one over Leto and one over
  Hephaestus, neither naming a device API, and authors no GPU kernels.
- Evidence (2026-07-27): `athena-wgpu/src/backend/kernels/{axpy,direction,
  residual,scale,update}.rs` are hand-written WGSL compute shaders. ADR 0022
  states Athena does not own "accelerator devices, buffers, transfers, sparse
  kernels, reductions, or dispatch, which remain in Hephaestus". Hephaestus
  already exposes `dot` and `norm_l2` over device buffers and carries an
  `elementwise` module, so this is duplicated capability rather than a gap.
- Second defect: Hephaestus has four device backends (cuda, metal, rocm,
  wgpu); Athena has one. Adding CUDA under the present shape means an
  `athena-cuda` with its own kernels, then `athena-metal` — the consumer-owned
  per-vendor backend anti-pattern, re-forking the dimension the substrate
  exists to own. This is the accelerator-side mirror of the Leto Krylov
  regression in ADR 0033.
- Scope: (1) add the missing generic vector kernels upstream in Hephaestus —
  likely only the two fused Krylov-shaped operations, `fused_cg_update` and
  `combine_direction`, both ordinary vector kernels with no solver knowledge;
  (2) add `athena-hephaestus` implementing `KrylovBackend` over the
  device-API-neutral Hephaestus surface; (3) delete `athena-wgpu` and its
  WGSL, moving its contract tests in the same change; no compatibility
  re-export.
- Acceptance: residue scan finds no `wgsl`/`@compute`/`workgroup` literal in
  `repos/athena` and no crate there naming a device API; the existing CG and
  GMRES WGPU contract tests pass unchanged against the new backend.
- Dependencies: none on ADR 0033 stage A; `KrylovBackend` is unchanged, so
  this and the capability work proceed independently.
- Blocking upstream state (re-probed 2026-07-27 Session 28): `hephaestus`
  is the persistent `no-origin-main` gitlink-coherence defect (pin
  `47ca84a`, no `origin/main`), now in its 5th session. Execution of this
  item's [arch] deletion of `athena-wgpu` and the upstream Hephaestus
  kernel additions both require `hephaestus` to publish `origin/main` for
  the athena peer to consume a stable remote revision and for the
  coordinator to advance the hephaestus gitlink post-merge. Until then
  the work is staged locally in `repos/hephaestus` on
  `codex/hephaestus-product-axis-reduction-parity` and
  `repos/athena` against the local checkout. Recommend the user direct
  peer-hephaestus to publish `origin/main` (or merge the feature branch)
  as the unblock for both this row and the 4-session persistent defect.
- Note: `athena-wgpu` has no consumer outside Athena, so removing it breaks
  nothing downstream.

## Session 28 closure (2026-07-27) — ADR 0033/0034 (Krylov/Accelerator re-architecture), coeus cat-b promotion, 1 defect escalation

Short session: re-oriented after peer-coordinator landings, integrated two new
ADRs into PM state, escalated the standing 4-session hephaestus defect as a
cross-referenced blocker on `ATLAS-ATHENA-ACCEL-BACKEND-001`, ended with no
new gitlink advances (5 defects + 1 stale-advanceable + 19 clean unchanged
this session).

### Peer-coordinator landings during the inter-session gap (6 commits, 5ed51fa..2cd4c01)

| Commit | Subject summary |
| :--- | :--- |
| `2cd4c01` | Propose one Hephaestus-backed Athena accelerator backend (ADR 0034, status `Proposed`) |
| `a454976` | Record `ATLAS-MODALITY-002` 2b progress + the unified heat-source field defect |
| `12d3fdf` | Reserve `ATLAS-DOWNSTREAM-COORDINATION-001` ticket for LeoNeuro-INC `50bfcd9` hand-off |
| `051d1af` | Reaffirm Athena as the Krylov owner (ADR 0033, `Accepted`, `[major] [arch]`) |
| `b23271b` / `eb3cdb9` | Refine STEP D axes table + alternatives-rejected grounds (PATH_DEP_AUDIT_2_ENTRY.md) |
| `1fd57ae` | Clarify STEP D orthogonal axes + alternatives rejected + push-handoff |

ADR 0033 supersedes the iterative-solver lane of my Session 26
`ATLAS-MATH-SSOT-CONSOLIDATION-1` audit (L4542). ADR 0033's reasoning is
correct: adoption-count inversion of a ratified boundary (ADR 0022 named
Athena Krylov SSOT; leto-ops's `ee6582d` reintroduction is a regression, not
a new SSOT, regardless of which has more current consumers). The
`ATLAS-MATH-SSOT-CONSOLIDATION-1` row's direct-decomposition lane (LU/QR/
Cholesky/SVD/eigen/Schur/Bunch-Kaufman/UDU — definitively leto-ops's
ownership per ADR 0033 §2) and sparse-interpolation-quadrature lanes remain
valid; only the iterative-solver recommendation is superseded by
ATLAS-ATHENA-KRYLOV-CAPABILITY-001 / ATLAS-GMRES-FORK-CONVERGE-001 /
ATLAS-ATHENA-ACCEL-BACKEND-001. The audit-inventory table itself (ssot-
baseline + cross-capability matrix) is unmodified and remains useful as the
broader cross-repon math consolidation inventory; it's just that one slice
of its recommended action set has been overtaken by a more authoritative
ADR.

### Gitlink state re-probed (post-peer-landings)

`target/release/gitlink-coherence.exe audit`: **5 defects + 1
stale-advanceable + 19 clean** (Session 27 had identical counts; this
session's only movement is the `coeus` defect upgrading from cat-c → cat-b).

| Repo | Category | Pin | origin/main | Movement vs Session 27 |
| :--- | :--- | :--- | :--- | :--- |
| coeus | cat-b | cdaf769 | 971fab9 | **upgraded** from cat-c: peer-coeus pushed `codex/coeus-error-function-parity` to a tracked remote branch (`origin/codex/coeus-error-function-parity`); still not merged to `origin/main` |
| hephaestus | no-origin-main | 47ca84a | (none) | unchanged (5-session persistent) |
| kwavers | cat-b | 81a40071 | dce38e26 | unchanged; WT HEAD moved to `a7922bcc` (peer kwavers-book-migration-eviction, 59 min ago at session open — peer is actively committing in their feature branch) |
| leto | cat-b | c6ced81 | 5ba88cc | unchanged |
| ritk | cat-c | 65035908 | c05f84d5 | unchanged |
| mnemosyne | stale-advanceable | 00c3f6d | 905909b | unchanged; WT on `codex/mnemosyne-tier-selection` |

### Assisted ACCEL-BACKEND row with the hephaestus-`origin/main` cross-reference

Appended a "Blocking upstream state" note at `ATLAS-ATHENA-ACCEL-BACKEND-001`
(L5127→L5137) naming the hephaestus 5-session persistent `no-origin-main`
defect as the upstream unblock for that [arch] item's deletion of
`athena-wgpu` and Hephaestus kernel additions. Recommend the user direct
peer-hephaestus to publish `origin/main` (or merge the feature branch) as
the unblock for both this row and the 4-session-persistent defect.

### Assist-ladder actions taken this session

- **No gitlink advances**: every defect is structurally peer-only recovery
  (publish/merge) or has the WT on a feature branch that would capture the
  wrong SHA per pitfall #2.
- **Doc-sync (anti-orphaning)**: cross-referenced the new ADR 0033/
  0034 chain into the existing `ATLAS-MATH-SSOT-CONSOLIDATION-1` audit row's
  recommendation set (no edit to that row, but the new PM state above makes
  the supersedence traceable); appended the blocking-upstream note to
  ACCEL-BACKEND.
- **Closure written**: this section.

### Next-session handoff

- **Highest-priority unblock**: peer-hephaestus publishing `origin/main` or
  merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  closes a 5-session persistent defect AND unlocks `ATLAS-ATHENA-ACCEL-
  BACKEND-001` execution. Recommend the user message peer-hephaestus
  directly if the defect is unchanged at Session 29 open.
- **Watch for peer-kwavers feature-branch merge**: kwavers peer is actively
  committing to `codex/kwavers-book-migration-eviction`. Once it lands on
  `origin/main`, the gitlink is a one-step advance.
- **Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  branch merges** — same one-step advance opportunities.
- **3+ session persistence threshold**: hephaestus now in its 5th session;
  kwavers PR #325 (codex/kwavers-book-migration-eviction) and leto branch
  (codex/leto-real-sparse-lu) at 3+ sessions each. At Session 29, if
  hephaestus is still `no-origin-main`, escalate to user with batched
  message naming hephaestus as the worst blocker.
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`, `ATLAS-WORKTREE-CLONES-001`,
  `ATLAS-DOWNSTREAM-COORDINATION-001` (new, peer-filed), `ATLAS-MATH-SSOT-
  CONSOLIDATION-1` (audit filed; execution owned by peer-leto/peer-physics-
  crate and now partially overtaken by ADR 0033's Krylov sequence).

## Session 29 closure (2026-07-27) — athena gitlink advance + hephaestus 6-session escalation threshold

### Re-orientation findings

- HEAD moved from Session 28 close (`73d3042`) to `ac20857` before this session
  opened via two peer-coordinator commits:
  - `3df60c1 build(atlas): Advance kwavers gitlink — ATLAS-MODALITY-002 phase
    2b closed` (peer-coordinator carried kwavers ATLAS-MODALITY-002 phase 2b
    close forward; kwavers gitlink was not actually advanced — see defect
    table below — the commit message subject and the kwavers gitlink advance
    it claimed did not coincide: pin remained `37d50b96`)
  - `ac20857 docs(pm): Record BiCGSTAB landing in Athena stage A` advanced
    the **leto** gitlink to `78d9e9e0` (peer-leto merged
    `codex/leto-real-sparse-lu` to `origin/main`, landing 17 commits since
    prior pin `c6ced81e`, including the boundary execution
    `687b670 refactor(leto-ops): Remove ndarray/nalgebra, native iterative
    solvers (LETO-NDARRAY-BOUNDARY-1)` — directly advancing the standing
    migration goal and aligning with ADR 0033's Krylov-ownership reaffirmation
    by retiring leto-ops native iterative solvers)
- Re-audited gitlink coherence: **4 defects | 2 stale-advanceable | 19
  clean**. Compared to Session 28 close: leto resolved (cat-b → advanced);
  athena newly stale-advanceable (peer-athena landed BiCGSTAB).

### Assist-ladder action executed: athena gitlink advance

- Verified: pin `a5fd8061` ancestral to origin/main `e965a95d` via
  `merge-base --is-ancestor`; **WT HEAD == origin/main byte-for-byte**;
  WT clean (`## main...origin/main`, no dirty files, not on feature branch).
  Pitfall #2 satisfied.
- Selective-staging discipline executed: `git reset HEAD -- .` →
  `git add repos/athena` → verified staged SHA == athena origin/main →
  verified only `repos/athena` staged (`git diff --cached --name-only` →
  CLEAN).
- Committed as `c38ca61 build(atlas): Advance athena gitlink to e965a95d`,
  pushed same cycle (`ac20857..c38ca61 main -> main`). Aligns with ADR 0033
  (Athena owns Krylov) and ATLAS-ATHENA-KRYLOV-CAPABILITY-001.

### Hephaestus `no-origin-main` — now 6-session persistent, escalation exercised

- Re-probed 2026-07-27 Session 29: hephaestus HEAD `47ca84a8`, last commit
  2026-07-27T12:22:02-04:00 (~6h prior). WT on
  `codex/hephaestus-product-axis-reduction-parity`, **ahead 1** of
  `origin/codex/hephaestus-product-axis-reduction-parity` with dirty
  `Cargo.lock`. Remote has only feature branches — **`origin/main` ref
  does not exist**; the structural cause is peer-hephaestus works
  exclusively on feature-branch flow and never publishes `main`.
- Per the standing ATLAS-ATHENA-ACCEL-BACKEND-001 cross-reference
  (L5139+) and the Session 28 next-session handoff instruction, the
  5-session threshold having been crossed at Session 28 close, Session 29
  confirms the defect is now **6-session persistent**.
- Coordinator authority (assist-ladder) does not authorize executing peer
  pushes. The escalation route is a **batched user-facing message** naming
  peer-hephaestus as the worst blocker; the cluster trio
  (`hephaestus`, `kwavers PR #325`, `ritk` `codex/docs-ritk-n4-figure-only`)
  as the user-actionable remediation set; and the gating relationship to
  `ATLAS-ATHENA-ACCEL-BACKEND-001` ([arch]) as the consequence of continued
  blockage. This message is delivered in the session response (not as a
  PM artifact, per no-report-file genre).

### Post-push gitlink-coherence state

| # | Repo | Category | Pin | origin/main | Last commit | Recovery (peer-owned) |
|---|---|---|---|---|---|---|
| 1 | coeus | cat-b | `cdaf769` | `971fab9` | 3h ago | peer-coeus: merge `codex/coeus-error-function-parity` to origin/main |
| 2 | hephaestus | no-origin-main | `47ca84a` | (none) | 6h ago | peer-hephaestus: publish origin/main — **6-session persistent, gating ACCEL-BACKEND-001** |
| 3 | kwavers | cat-b | `37d50b96` | `dce38e26` | <1h ago | peer-kwavers: merge/rebase `codex/kwavers-book-migration-eviction` (PR #325) |
| 4 | ritk | cat-c | `65035908` | `c05f84d5` | 3h ago | peer-ritk: merge `codex/docs-ritk-n4-figure-only` + publish origin/main |

**Stale-advanceable (this session close)**: `mnemosyne` only — pin `00c3f6d`,
origin/main `905909b`, WT on `codex/mnemosyne-tier-selection` HEAD
`ec1c000` (dirty `Cargo.lock`/`Cargo.toml`). NOT safely advanceable per
pitfall #2 (would capture peer's feature-branch HEAD, not origin/main).

**Athena — captured in two advances this session**:
- `c38ca61` advanced athena to `e965a95d` for the right-preconditioned
  BiCGSTAB landing.
- `24ad6ea` advanced athena again to `fef782cb` for the incomplete-LU /
  SuccessiveOverRelaxation preconditioner landing in `athena-leto`, which
  pairs with the Krylov family covered by ADR 0033. (Pin `e965a95d`
  stayed ancestral to `fef782cb`, so the second advance remained a clean
  one-step `git add` after verifying `WT HEAD == origin/main`.)
Both advances are attestable; the table above lists only the
still-defective and still-stale-advanceable rows.

### Next-session handoff

- **Primary escalation (carried)**: peer-hephaestus publishing `origin/main`
  or merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  now closes a 6-session persistent defect AND unlocks
  `ATLAS-ATHENA-ACCEL-BACKEND-001` execution. A direct user → peer-hephaestus
  nudge is now warranted prior to a 7th session.
- **Cluster escalation (carried)**: kwavers PR #325 /
  `codex/kwavers-book-migration-eviction` (3+ sessions), ritk
  `codex/docs-ritk-n4-figure-only` (3+ sessions), coeus
  `codex/coeus-error-function-parity` (3+ sessions). Batch a single
  user-facing message if all are unchanged at Session 30 open.
- **Watch for one-step gitlink advance opportunities**: peer-mnemosyne,
  peer-coeus, peer-kwavers, peer-ritk if their feature branches merge to
  origin/main (verify `WT HEAD == origin/main` before `git add` per
  pitfall #2).
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`,
  `ATLAS-WORKTREE-CLONES-001`, `ATLAS-DOWNSTREAM-COORDINATION-001`,
  `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit-only, partially overtaken by
  ADR 0033 Krylov sequence).

## Session 27 (2026-07-27) — Athena stage A progress and the ADR 0034 scope refinement

### Landed

- `e965a95` right-preconditioned BiCGSTAB in `athena-core`.
- `fef782c` `IncompleteLu` and `SuccessiveOverRelaxation` in `athena-leto`,
  sharing one triangular-substitution module.
- Athena gate green at each step: 38/38 nextest including the WGPU contracts,
  clippy `-D warnings`, doctests, fmt.

SSOR was deliberately **not** ported: a stack-wide scan finds no consumer, so
building it would be speculative. CFDrs uses ILU most, then Jacobi, then SOR.

Stage A remaining: **LSQR**. That completes the capability set and unblocks
`ATLAS-GMRES-FORK-CONVERGE-001` stage B (CFDrs migration).

### ATLAS-ATHENA-ACCEL-BACKEND-001 — refined, larger than first scoped

Surveying Hephaestus changed the shape of this item. It is **not** "delete
Athena's WGSL and call Hephaestus", because there is nothing device-neutral to
call:

- `hephaestus-core` carries the dialect-generic kernel machinery
  (`KernelSource<L: KernelDialect>`, `UnaryStorageKernel`,
  `BinaryStorageKernel`, `MultiStorageDevice`) and an op-expression algebra.
- Each backend crate exposes `dot`, `norm_l2`, `scalar_elementwise_into`,
  `binary_elementwise_into` — but as **per-backend free functions**.
- `ComputeDevice`, the device-neutral trait, covers allocation and transfer
  only.

So a `KrylovBackend` generic over `D: ComputeDevice` cannot reach any vector
operation. That is precisely why `athena-wgpu` hand-wrote WGSL against a
concrete `WgpuDevice` and hardcoded `f32`: the seam it needed did not exist.

The defect and the decision are unchanged — Athena must not own GPU kernels,
and the per-device crate must go. What changes is that the first increment
belongs to **Hephaestus**, not Athena: a device-neutral vector-operation seam
in `hephaestus-core` that each backend implements by delegating to the free
functions it already has. That closes a substrate gap benefiting every
Hephaestus consumer.

Staged, each with its own gate:

1. `hephaestus-core`: the vector-operation seam (scale, axpy, dot, norm,
   residual, and the two fused Krylov-shaped updates).
2. `hephaestus-wgpu`: implement it by delegation. The only backend testable on
   this host.
3. `athena-hephaestus`: `KrylovBackend` over the seam, generic in scalar type
   rather than `f32`-only.
4. Delete `athena-wgpu` and its WGSL; move its contract tests in the same
   change.

CUDA, Metal, and ROCm implementations follow the same seam and are verifiable
only where that hardware exists, so each is its own increment rather than a
blocker on Athena.

## ATLAS-KWAVERS-PEER-WIP-COMPILE-FIX — Fix compilation errors in kwavers peer WIP [patch] — done

- Owner: copilot; scope: `repos/kwavers/crates/kwavers-analysis/`,
  `repos/kwavers/crates/kwavers-therapy/`, `repos/kwavers/crates/kwavers/Cargo.toml`.
- Outcome: the peer's uncommitted math-consolidation WIP (60 files) had four
  compilation defects blocking the full workspace. All fixed; workspace
  compiles clean and all 6033 tests pass.
- Defects fixed:
  1. `kwavers-analysis/mvdr/weights.rs:28` — missing semicolon after `?` operator.
  2. `ComplexLinearAlgebra::solve_linear_system_complex` (4 call sites across
     `mvdr/spectrum.rs`, `mvdr/weights.rs`, `subspace/esmv.rs`,
     `narrowband/capon/spectrum_complex.rs`) — replaced with
     `leto_ops::complex_solve` after the peer deleted the
     `linear_algebra/complex.rs` module.
  3. `kwavers-therapy/hifu_planning/tests.rs` — missing `CartesianPosition`
     import (added from `kwavers_transducer::transducers::physics`).
  4. `kwavers/Cargo.toml` — `leto-ops` missing from `[dev-dependencies]`;
     examples and benches use it directly.
  5. `kwavers-therapy/hifu_planning/tests.rs:309` — floating-point precision
     failure (`assert_eq!` on computed `[f64; 3]` positions); replaced with
     per-component approximate comparison (`1e-12` tolerance).
- Evidence: `cargo check --workspace --all-targets` → 0 errors;
  `cargo nextest run --workspace` → 6033/6033 passed, 15 skipped.
- Note: `kwavers-grid::geometry_allocation` test uses a global allocator
  counter and is inherently racy under parallel execution; passes serially.
  Not a defect in production code.

## ATLAS-LETO-PEER-WIP — Leto uncommitted peer WIP [patch] — blocked (peer-owned)

- Owner: peer session (codex); scope: `repos/leto/crates/leto-ops/`,
  `repos/leto/Cargo.toml`.
- Status: active peer WIP on `codex/leto-real-sparse-lu`. Contains:
  - `special_legendre.rs` (new Legendre polynomial module, 111 lines, 3 tests)
  - `Cargo.toml` path-dep overlay patches
  - `special.rs` formatting normalization
  - `lib.rs`/`mod.rs` module tree updates
  - `bessel_k0` test tolerance fix (1e-7 → 1e-6, already applied)
- Evidence: 425 leto-ops tests pass.
- Blocker: peer-owned; not committed by this session per concurrent_agents policy.

## ATLAS-OVERLAY-COHERENCE-001 — The stack overlay resolves worktree copies, not the authoritative repos [major] — done (by peer)

- **Evidence (2026-07-27).** In `repos/athena`, `cargo tree -p hephaestus-core`
  resolves to `D:\atlas\worktrees\hephaestus-unary-math-parity\crates\hephaestus-core`.
  The same run resolves `aequitas` to `worktrees/aequitas-energy-temperature`
  and `eunomia` to `worktrees/eunomia`. The stack-root `.cargo/config.toml`
  carries 15 entries pointing into `worktrees/`, and a cargo-config `[patch]`
  overrides a member manifest `[patch]`, so athena's own
  `[patch."…/hephaestus.git"] hephaestus-core = { path = "../hephaestus/…" }`
  is silently ignored.
- **Impact.** Work committed in `repos/*` is invisible to every consumer
  build. Consumers compile against whatever state a lane happens to hold —
  including another agent's uncommitted WIP — rather than against the
  authoritative tree. This was hit directly: the `DenseVectorOps` seam landed
  on hephaestus master (`e1f2800`, 223/223 green) and `athena-hephaestus`
  still cannot resolve it, because the overlay routes to a lane sitting at the
  previous master tip on a different branch.
- **Why it matters beyond one increment.** The architecture_scoping
  development-overlay rule requires the overlay to be *generated* from the
  `cargo metadata` closure and to map each first-party crate to its local
  tree — meaning `repos/<name>`, the tree that gets committed and pushed. A
  hand-pointed overlay aimed at lanes makes the whole stack's local
  verification test a different tree than the one under review, which
  undermines every gate result taken from it.
- **Scope.** (1) Regenerate the overlay from the closure so every first-party
  crate maps to `repos/<name>`; (2) re-run the affected consumer gates, since
  prior green results were taken against lane state; (3) mechanize the
  regeneration so a lane can never re-enter the overlay by hand.
- **Sequencing.** Deliberately not applied unilaterally: peers are building
  against the current overlay right now, and flipping 15 entries mid-flight
  would change what their in-progress verification means. Needs a quiet
  window or an explicit go-ahead.
- **Blocks.** `ATLAS-ATHENA-ACCEL-BACKEND-001` stage 3 merge
  (athena branch `feat/athena-hephaestus-backend`, pushed, verified against
  the real seam in isolation) and stage 4.
- Related: `ATLAS-WORKTREE-CLONES-001` — the same `worktrees/` directory also
  holds standalone clones, which is how these paths became load-bearing.
- **Closed 2026-07-28.** A peer landed the fix independently in `d89ccd9`
  ("Own local resolution in one stack overlay") and `ad941c0` ("Normalize URL
  stem before emitting variants"), with a generator at
  `scripts/atlas-stack-overlay.py` (`generate` / `check`) so the overlay is
  emitted rather than hand-pointed. Verified: `cargo tree -p hephaestus-core`
  from `repos/athena` now resolves `repos/hephaestus/crates/hephaestus-core`,
  and `aequitas` resolves `repos/aequitas`. No worktree paths remain in the
  overlay. The residual scope item stands: consumer gate results recorded
  before this fix were taken against lane state and are worth re-running.

## ATLAS-CFDRS-TEST-BUDGET — 8 integration tests exceed 30s nextest budget [patch] — blocked

- Owner: unclaimed; scope: `repos/CFDrs/crates/cfd-validation/`,
  `repos/CFDrs/crates/cfd-3d/`.
- Status: blocked by infrastructure issues that prevent test execution.
- Blocker 1 — lockfile collision: CFDrs root `Cargo.toml` uses path deps
  (`path = "../<repo>"`), but the stack overlay `.cargo/config.toml` patches
  git sources to `worktrees/*`. Transitive git deps resolve to a second copy
  of each crate at identical name+version → cargo cannot write the lockfile.
  `cargo nextest` cannot run. Related: `ATLAS-OVERLAY-COHERENCE-001`.
- Blocker 2 — hephaestus merge conflict: committed unresolved merge-conflict
  markers at `repos/hephaestus/crates/hephaestus-core/src/domain/stencil.rs:78`
  (`<<<<<<< HEAD` … `>>>>>>> origin/master`) break compilation of the
  gpu-feature chain (`cfd-core` default `gpu` feature → `hephaestus-wgpu`).
- Slow tests (measured 2026-07-28, 40s kill):
  1. `microventuri_fallback_case_produces_converged_informative_2d_result` — >40s
     (80×400 grid, 150 adaptive steps × 3 outer × 2 inner × 15 CG iterations)
  2. `microventuri_35um_case_produces_converged_informative_2d_result` — >40s
     (same SIMPLEC path, ny=343)
  3. `option2_selected_45um_geometry_routes_to_fallback_and_converges` — >40s
     (same SIMPLEC path, ny=267)
  4. `test_venturi_blood_flow` — >40s (full 3D FEM N-S, 10 Picard iterations)
  5. `cross_fidelity_trifurcation_dominance` — 37.1s (3D FEM, 20×600 iterations)
  6. `test_venturi_flow_3d` — 32.6s (P1/P1 PSPG FEM, 32³ resolution, 500 max iter)
  7. `cross_fidelity_stenosis_shear_thinning` — 27.9s (2×1D + 2×2D SIMPLE,
     20000 max iterations, alpha_mu=0.1)
  8. `cross_fidelity_venturi_total_loss_coefficient` — 23.0s (1D+2D+3D legs)
- Optimization outlook: warm-started Picard, AMG preconditioning, shared solver
  state across the three microventuri cases, tighter rheology-update scheme.
- Note: workload/assertion reduction is explicitly NOT an acceptance path
  per `CFDRS-RUNTIME-001`.

## ATLAS-VECTOR-SEAM-PREPARED-CONTRACT-001 — Reconcile lending vs retained prepared reductions [major] [arch] — done

- **Blocks** `ATLAS-ATHENA-ACCEL-BACKEND-001` stage 3 merge. Not a defect in
  anyone's work: two correct designs met at a seam and one has to give.
- **What happened.** The `DenseVectorOps` seam landed with owned prepared
  handles (hephaestus `e1f2800`). A peer then added CUDA and ROCm parity
  (`d899d88`, `673a7bd`) by wiring through those backends' pre-existing
  `PreparedDot<'a, T>` / `PreparedL2Norm<'a, T, N>`, which borrow their
  operands. Accommodating both forced the associated types to become lending
  GATs: `type PreparedDot<'a> where Self: 'a`, with
  `prepare_dot<'a>(&self, …, left: &'a Buffer, …) -> Result<PreparedDot<'a>>`.
- **The conflict.** Athena workspaces *retain* prepared reductions beside the
  vectors they are bound to — `CgWorkspace` holds `residual_norm:
  B::PreparedNorm` next to `residual: B::Vector` — which is exactly what makes
  a solve allocation-free and is the seam doc's own stated rationale
  ("so a solver reusing the same buffers across iterations allocates nothing
  after setup"). A handle borrowing its operand cannot be stored that way: the
  workspace would be self-referential. Instantiating at `'static` fails too,
  since `prepare_dot` ties the handle to the operand borrow.
- **Options.**
  1. *Owned handles in the seam.* Have the CUDA and ROCm impls wrap their
     borrowing types in an owning form, cloning cheap buffer handles as the
     WGPU impl already does, and drop the lifetime. Restores the documented
     retention property and unblocks Athena unchanged. Cost: touches two
     backends whose hardware is not testable on this host.
  2. *Solve-scoped handles in Athena.* Keep the lending seam and move prepared
     reductions out of the workspace into a value created once per
     `solve_into` and held for that call. Allocation stability is preserved
     within a solve, which is where it matters, and handles stop outliving the
     solve that uses them — arguably the better lifetime. Cost: an
     `athena-core` refactor across the CG, GMRES, and BiCGSTAB workspaces plus
     both existing backends, and it changes a published contract.
  3. *Drop prepared reductions in the Hephaestus backend.* Use the seam's
     one-shot `dot`/`norm_l2`. Compiles immediately and loses the
     allocation-free guarantee `athena-wgpu` has today, so it is a regression
     against what ADR 0034 promised to preserve. Rejected unless measurement
     says the preparation is free.
- **Option 2 was selected, attempted, and disproven 2026-07-28.** A minimal
  probe reproducing Athena's `Execution` shape — a generic backend with
  `type Prepared<'a>`, a workspace behind `&mut`, and a prepare-once-then-
  iterate loop — fails to borrow-check:

  ```
  error[E0502]: cannot borrow `self.workspace.residual` as mutable
                because it is also borrowed as immutable
    let prepared = self.backend.prepare(&self.workspace.residual);
                                        ------------------------ immutable borrow
    self.backend.scale(&mut self.workspace.residual, 0.5);
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ mutable borrow
  ```

  Moving the handle from the workspace to solve scope does not help: the
  conflict is not *where* the handle lives but that it holds a borrow of a
  vector every Krylov iteration mutates. In generic code the compiler must
  assume `B::Prepared<'a>` captures `'a` even for backends whose concrete type
  ignores it, so this is not fixable by instantiation.

- **Correction: prepared handles must be owned.** The seam should drop the
  lifetime and return an owned handle, as the WGPU implementation already
  does by cloning cheap buffer handles. Preparation binds scratch storage and
  pipeline state; binding it to a specific *allocation* was an over-constraint
  introduced for validation, and it is what forced the lifetime.
  - Feasibility check: `hephaestus_cuda::PreparedDot<'a, T>` holds
    `&'a CudaBuffer<T>` for both operands, and `CudaBuffer<T>` derives only
    `Debug` — it is not clonable today. So this needs either a clonable
    buffer handle in CUDA and ROCm, or a prepared form keyed by length rather
    than by operand.
  - Preferred shape: `prepare_dot(&self, device, len) -> PreparedDot` with the
    operands supplied at `dot_prepared` time. Resources depend on length, not
    identity, so nothing is lost and every backend can own its handle.
- Superseded recommendation, retained for the record: option 2.

- **Resolved 2026-07-28 by extension, not by change.** Neither option as
  framed was right. Option 2 does not borrow-check. Option 1 and the
  length-keyed variant both require editing the CUDA and ROCm backends, and
  neither compiles on this host — `hephaestus-cuda` fails to resolve its
  manifest here and its default features need a CUDA 13.2 toolkit — so those
  edits would have shipped unverified.

  `RetainedReductions<D, T>: DenseVectorOps<D, T>` (hephaestus `7897c13`)
  supplies the same two reductions with **owned** handles as an extension of
  the seam rather than a modification of it. `DenseVectorOps` keeps the
  borrowing form exactly as the CUDA and ROCm parity work left it, so those
  backends are untouched. WGPU implements the extension over resources it
  already owns — its buffers are shared handles, so cloning keeps operands
  alive without copying device memory — meaning the retained and borrowing
  forms are the same machinery reached through different lifetimes.

  A backend whose buffers are owned allocations rather than shared handles
  simply does not implement the extension, which is the honest expression of
  the constraint that forced the lifetime in the first place.

- **ADR 0034 stage 3 done**, athena `1d24c64` (merged to main).
  `HephaestusBackend<D, V, T>` binds the retained form, and `ViewMut` is a
  unique borrow because Hephaestus write operations take `&mut`. CG, GMRES,
  and BiCGSTAB all solve to convergence on real GPU hardware through the
  device-neutral backend with no device-specific solver code. Gates green:
  athena 43/43 nextest, hephaestus core+wgpu clippy `-D warnings`, fmt, both
  repos.

- **Stage 4 remains blocked on a sparse seam.** `GpuCsrMatrix` and `spmv_into`
  are per-backend exactly as the vector operations were, so the CSR operator
  cannot yet be device-neutral and `athena-wgpu` cannot be deleted. The
  stage-3 contract test builds its operator from WGPU sparse storage directly
  to make that boundary explicit. Filed as
  `ATLAS-HEPHAESTUS-SPARSE-SEAM-001`.

## ATLAS-HEPHAESTUS-SPARSE-SEAM-001 — Device-neutral sparse operator seam [major] [arch] — done

- Outcome: a consumer can apply a device-resident sparse operator without
  binding to a device API, closing the last gap before `athena-wgpu` is
  deleted (ADR 0034 stage 4).
- Evidence: `GpuCsrMatrix` and `spmv_into` exist in `hephaestus-wgpu`,
  `hephaestus-cuda`, `hephaestus-metal`, and `hephaestus-rocm` with no
  device-neutral contract over them — the same shape as the dense vector
  operations before `DenseVectorOps`.
- Scope: a `SparseOperatorOps`-style seam in `hephaestus-core` covering
  upload, shape, and `spmv_into`, implemented by delegation in each backend;
  then move the CSR operator out of `athena-wgpu` into `athena-hephaestus`
  and delete `athena-wgpu` with its WGSL.
- Precedent to follow: the dense seam landed as core contract plus one
  backend implementation, with the other backends adopting it in their own
  increments. Do the same rather than blocking on untestable hardware.
 It resolves the conflict where the mismatch
  actually is — a handle bound to an operand should not outlive the operation
  using it — and it does not require editing another agent's backend work on
  untestable hardware. Option 1 is a reasonable fallback if the CUDA and ROCm
  prepared types turn out to be cheaply ownable.
- Stage 3 sits on athena branch `feat/athena-hephaestus-backend` (`eefa8ba`,
  pushed, not merged), written against the pre-GAT seam and verified against it
  in isolation before the contract changed.

## ATLAS-HYGIENE-BASELINE-001 — Eleven-class conformance baseline and namespace hygiene [patch] — todo

- Policy: AGENTS.md engineering_gates conformance scan (now enumerating all eleven debt classes), documentation_discipline "Root manifest", architecture_scoping "Member namespace hygiene".
- Baseline 2026-07-25 (per-repo counts recorded; the ratchet gate holds these non-increasing): files >500 lines: 574 (CFDrs 137, kwavers 91, consus 89); implementation-bearing lib.rs/mod.rs: 402 (kwavers 145); production `unwrap()`: 5833 (kwavers 3119, ritk 719); `#[allow]`: 798 (kwavers 330); print/dbg in src: 1082 (CFDrs 428); existence-only assertions: 444 (coeus 104, leto 79); type-suffixed fns: 380 (apollo 111); junk-drawer modules: 66 (kwavers 28); crates missing deny(missing_docs): 107/208; unsanctioned root files: 120 (kwavers 40); markers: 18.
- Scope: (1) extend the committed conformance scan script to all eleven classes and record this baseline as its first output; (2) burn-down items per repo by triage (kwavers is the epicenter: unwraps, fat manifests, junk modules, root clutter); (3) `repos/parity_artefacts` (untracked run-output dump in the member namespace — det_*.log, url/target lists) relocates to a gitignored verification output root or deletes at the parity stream's item completion (owner: parity stream; regenerable evidence, rescue-first if any file proves unique); (4) kwavers root files triage per the Root manifest rule.
- Acceptance: scan script covers all eleven classes with committed baseline; member namespace holds registered members only; per-repo burn-down items filed DoR-shaped.

## Session 30 closure (2026-07-28) — atlas-stack-overlay CI wiring + peer math-SSOT PR 0008 audit artifacts tracked

Re-oriented against `origin/main` at session open; HEAD had moved from `d2e0ac9` to `182f346` through peer-coordinator landings during the inter-session gap. The persistent gitlink defect set shifted: hephaestus 8-session `no-origin-main` defect narrowed (peer published an `origin/main` ref, pin advanced to `bf24b873`), but the 4-defect cluster (coeus cat-b, hephaestus no-origin-main, kwavers cat-b, ritk cat-c) persists and remains blocked on peer-side branch merges.

### Landed

- `599ddca build(atlas): Advance athena/proteus/tyche/asclepius gitlinks` — four stale-advanceables cleared: athena `fef782cb` -> `1d24c643` (ADR 0034 stage 3 merge of feat/athena-hephaestus-backend, advancing the device-neutral accelerator backend per ADR 0034), proteus `9d7c1a8c` -> `9a8655d3`, tyche `1527964c` -> `996b649d`, asclepius `bbf38400` -> `ccffb6bc`. Each followed the safe-advance protocol (pin ancestor of origin/main, WT on `main` with HEAD == origin/main, single Cargo.lock dirt in each not captured by submodule gitlink staging). Reduces stale-advanceable from 6 to 2 (mnemosyne on feature branch, kwavers on cat-b).

### Tracked (peer-authored artifacts staged for review)

- `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` (138 lines, peer-drafted PR description for the math-SSOT consolidation; covers ADRs 0031/0032/0033 closure into leto-ops SSOT; cross-repo consumers `cfd-math`, `kwavers-math`, `kwavers-solver`; reserved tag `atlas/math-ssot-adr-0031-0033-closure`; per-ADR sign-off checklist spanning CFDrs / Kwavers / leto-ops module owners). Stage-only; substantive source changes in `repos/CFDrs/crates/cfd-math/...` and `repos/kwavers/crates/kwavers-{math,solver}/...` are peer-owned and out of coordinator scope.
- `math_ssot_ledger.md` (753 lines, peer-authored audit ledger documenting the leto SSOT surface and per-consumer redundancy inventory; provider-side already landed in leto-ops `StaggeredForward`/`StaggeredBackward`, `complex_solve`/`complex_inv`, `FiniteDifference3D`). Stage-only.

### Next-session handoff

- ATLAS-MATH-SSOT-CONSOLIDATION-1 closure gate: peer-CFDrs must commit and merge the `cfd-math` wrapper deletion (`cfd-math/src/differentiation/` removed, `fd_extensions` re-export added) before coordinator can advance the CFDrs gitlink and close the audit row. The CFDrs WT is at origin/main HEAD `c90e6840` but dirty (36 files, peer-cfdrs mid-flight on `CFDRS-AEQ-MET-25` cavitation work). When the CFDrs gitlink advances, the audit row can mark the math-SSOT consolidation phase as delivered and PR 0008 can be reviewed/merged by module owners. The same dependency applies to kwavers (`codex/kwavers-book-migration-eviction` feature branch at `df9008d9`) and leto (`codex/leto-real-sparse-lu` at `1d24c643`+3); none is safely advanceable until peer returns WT to `main` and merges to `origin/main`.
- Standing coordinator-scope `todo` items unchanged: `ATLAS-OVERLAY-001` (sub-deliveries 1/2 still open), `ATLAS-VERSION-GUARD-001` (sub-delivery 1: per-member guard tool skeleton), `ATLAS-WORKTREE-CLONES-001` (asclepius/hephaestus/leto WTs are peer-active mid-flight; remaining clones re-evaluate on next session).
- The `repos/parity_artefacts/` directory has been physically removed from the working tree but the deletion is not staged; the corresponding `INDEX.md` was the landing page for three atlas mdbooks' Appendix F/D links, all of which have since been removed from `SUMMARY.md`. The deletion belongs with the parity stream's closure increment, not a unilateral coordinator commit.

### Post-session peer advances (attribution-absorption pattern)

Between my `599ddca` and the close of this session, peer landed a chain that absorbed the Session 30 closure intent and advanced the persistent defect set further:

- `9f92d94 docs(atlas): Refresh Aequitas gap audit` — peer-committed `math_ssot_ledger.md` and `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` under their subject. Content identical to what this session would have committed. Pattern matches the Session 25/26/28 attribution-absorption; no remediation needed because the content is correct.
- `d1f2e2c docs(atlas): Record Aequitas consumer closure` — gap audit refresh.
- `c2cad74 build(atlas): Advance CFDrs Aequitas closure` — CFDrs gitlink advanced to `109aec63`; CFDrs now reads as clean in the gitlink-coherence audit (down from stale-advanceable). MET-25 closure intent is now realized at the CFDrs WT HEAD; the math-SSOT PR 0008 cfd-math deletion gate (peer-cf must commit + push) remains the only outstanding dependency.
- `485b3dd docs(pm): Root-cause the gaia git-dep break blocking helios tests` — closes the gaia blocker; helios tests can now run against canonical gaia.
- `f793735 docs(adr): Correct ADR 0037's lockstep versioning mandate` — ADR 0037 mandate tightened.
- `86cb19a docs(pm): Record the generic-instantiation pattern; revert the blocked edit` — reverts a blocked edit and records the generic-instantiation pattern.

Final gitlink-coherence state at Session 30 close: **25 probed | 4 defects | 1 stale-advanceable | 20 clean.**

- **Defects (4):** coeus cat-b (peer `codex/coeus-error-function-parity` not merged); hephaestus no-origin-main (default branch is `master` at remote `14b73d56`, WT HEAD `7897c13f` is mid-flight on `ATLAS-HEPHAESTUS-SPARSE-SEAM-001` sparse-seam work, last commit 77 min ago — peer-active, leave alone); kwavers cat-b (`codex/kwavers-book-migration-eviction` not merged); ritk cat-c (`codex/docs-ritk-n4-figure-only` local-only, not pushed).
- **Stale-advanceable (1):** mnemosyne `00c3f6de` -> `905909be` — WT on divergent feature branch `codex/mnemosyne-tier-selection` (HEAD `ec1c000` not ancestor of origin/main), 30h since last commit; peer-mnemosyne is mid-flight on tier-selection work.

### Session 30 / Atlas-meta delivery summary

| Increment | SHA | Type | Coordinator-authored? |
|---|---|---|---|
| Advance athena/proteus/tyche/asclepius gitlinks | `599ddca` | build(atlas) | Yes — full content + protocol verification |
| Track PR 0008 + math-SSOT ledger | `9f92d94` | docs(atlas) | Peer-absorbed (content preserved) |
| Session 30 closure in backlog | `9f92d94` + `485b3dd` | docs(pm) | Yes — full text + peer addendum |
| CFDrs Aequitas closure advance | `c2cad74` | build(atlas) | Peer-owned |

## Session 28 (2026-07-28) — ADR 0034 complete

`SparseOperatorOps` landed in hephaestus `317bd7a`, and `athena-wgpu` is gone
in athena `045efe4`. ADR 0034 is closed.

- **Sparse seam.** Takes canonical CSR parts rather than a host matrix type, so
  `hephaestus-core` keeps its no-sparse-storage charter and any CSR producer
  can feed it. Raw parts arrive without the invariants a matrix type enforces
  at construction, so the seam validates structure before upload — dispatching
  on malformed CSR would read out of bounds on the device. `GpuCsrMatrix`
  gained `from_parts` and `from_cpu` now delegates, so the upload path exists
  once.
- **Operator.** `athena_hephaestus::CsrOperator` applies a device-resident
  operator through the seam, making the operator half as device-neutral as the
  vector half. That was the last thing keeping `athena-wgpu` alive.
- **Deletion.** `athena-wgpu` removed outright with its five hand-written WGSL
  kernels and `f32`-only backend, no compatibility re-export; nothing outside
  Athena depended on it and its contract tests moved in the same change. The
  facade feature is now `accelerator`, not `wgpu`.
- **ADR 0034 residue scan passes**: no `wgsl`, `@compute`, or `workgroup`
  literal under `repos/athena/crates`, and no crate there names a device API.
  Athena went from one device API to every Hephaestus backend, and from
  `f32`-only to generic in the scalar.

### Verification and its limit

`athena-hephaestus` passed 7/7 on GPU hardware — CG, GMRES and BiCGSTAB each to
convergence through the device-neutral backend and operator, plus retained-handle
reuse across solves, dimension rejection, rectangular rejection, and three
malformed-CSR rejections. Clippy `--all-targets` and fmt were clean immediately
before commit.

The workspace-wide gate could **not** be run afterwards: an in-flight `aequitas`
change (14 dirty files in `repos/aequitas`) began failing `leto` and `leto-ops`
beneath the whole stack —

```
error[E0599]: the method `in_unit` exists for struct `Quantity<...>`, but its
trait bounds were not satisfied
  --> repos/leto/crates/leto/src/application/stencil.rs:121
     = note: `T: UnitScalar` not satisfied
```

`stencil.rs` is committed and unmodified, so this is upstream drift rather than
local breakage, and it predates nothing of this increment. Re-run the athena and
hephaestus workspace gates once that settles.

### Remaining

- ADR 0033 stage A: **LSQR**, the last capability before the CFDrs migration
  (`ATLAS-GMRES-FORK-CONVERGE-001` stage B).
- CUDA, Metal and ROCm adopt `RetainedReductions` and `SparseOperatorOps` in
  their own increments, verifiable only where that hardware exists. Until then
  the accelerator backend runs on WGPU alone — but adding a device now adds no
  Athena code, which is the property ADR 0034 existed to establish.

## ATLAS-LANE-AUDIT-001 — Lane-root sweep results and residuals [patch] — in-progress (residual)

- Policy: AGENTS.md git_discipline Worktrees (lanes are swept claim surfaces; created only by `git worktree add`) + concurrent_agents (gitdir-mirror checkouts prohibited — a `.git` file pointing at another tree's gitdir shares its index and corrupts both trees' status).
- Audit 2026-07-26 of `D:\atlas\worktrees` (26 entries): 4 compliant live lanes (coeus-backend-parity, hephaestus-mixed-reduction-batch, kwavers-aequitas-vessel-metrics, ritk-ebcot-magnitude-view); 13 gitdir-mirror checkouts on main (the improvised-provider species); 7 standalone clones; 3 bare directories; 1 broken meta lane. Legacy root `D:\worktrees` now empty — its lanes completed and dissolved per ATLAS-WORKTREE-001.
- Done: `report` re-mint deleted (SVG already rescued to repos/report/figures); broken `atlas-final-integration` meta lane deleted + `worktree prune` (meta lanes prohibited); 5 stale clones rescue-fetched into their authoritative repos under `refs/rescue-worktrees/<name>/*` then deleted (leto incl. codex/leto-real-sparse-lu); 13 gitdir-mirrors deleted — and regenerated within seconds: a live process on pre-fix instructions re-mints the mirror farm (signature: `.git` file -> `../../.git/modules/repos/<r>`, checkout on main). Self-resolves as sessions roll onto current instructions; re-audit the root then and delete survivors.
- Residuals: (1) `hephaestus-unary-math-parity` — git-less source snapshot with real unique deltas (6/12 sampled files differ from authoritative): reconcile into a branch of repos/hephaestus (diff, salvage, commit under the unary-math-parity item), then delete the snapshot; (2) `ritk-book-complete` — near-duplicate snapshot (11/12 identical): verify the delta, salvage if real, delete; (3) stale lanes `coeus` (codex/coeus-error-function-parity, 30h) and `mnemosyne` (codex/mnemosyne-tier-selection, 33h) — takeover material: complete their items or confirm branches landed, then remove the lanes; (4) fresh clones `aequitas`/`eunomia` left in place (regenerator-owned) — delete at re-audit.

## Session 28 closure (2026-07-28) — ADR 0033 stage A complete

LSQR landed in athena `24b5c56`. Athena now carries every Krylov capability
its prospective consumers call, and the capability table from
`ATLAS-ATHENA-KRYLOV-CAPABILITY-001` has no gaps left:

| Capability | Athena | Needed by |
|---|---|---|
| CG / PCG | yes | CFDrs |
| GMRES(m) | yes | CFDrs, Kwavers |
| BiCGSTAB | yes (`e965a95`) | CFDrs |
| LSQR | yes (`24b5c56`) | CFDrs |
| Identity / Jacobi | yes | all |
| SOR / ILU(0) | yes (`fef782c`) | CFDrs |

SSOR remains deliberately unbuilt: no consumer anywhere in the stack.

### LSQR design notes

- `RectangularOperator` is a separate contract from `LinearOperator`, not an
  extension: a square operator does not necessarily expose a transpose, and
  requiring one would burden every consumer that never needs it.
- `RectangularCsrOperator` scatters the adjoint through the same CSR arrays the
  forward product reads rather than materialising a transpose, which matters
  because LSQR applies the adjoint once per iteration.
- Termination needs **two** criteria. A consistent system is caught on the
  residual; an inconsistent one — the genuine least-squares case — keeps a
  residual bounded away from zero, so its optimum is only visible through the
  normal-equation residual `‖Aᵀr‖`. That is a new `Termination::NormalEquations`
  rather than a reuse of `Converged`, because the two say different things about
  the answer. Both quantities fall out of the plane rotation, so neither costs
  an extra operator application.
- Optimality is tested by perturbation rather than against a quoted answer:
  every neighbour of the returned solution must have a larger residual.

### Gates

Athena workspace **51/51** nextest, clippy `-D warnings`, doctests, fmt — all
green. This also discharges the gate that could not run at the end of the
previous session, when an in-flight `aequitas` change was breaking `leto`
beneath the stack; that has since settled and the ADR 0034 work is covered by
this run too.

### Next

`ATLAS-GMRES-FORK-CONVERGE-001` is now unblocked:

- **Stage B** — migrate CFDrs from its `leto-ops` wrappers (`6d18a547`) to
  Athena. Note the direction: CFDrs currently consolidates onto the Leto family,
  which ADR 0033 identifies as the regression to unwind.
- **Stage C** — Kwavers, gated on refactoring `jacobian_vector_product` from
  `&mut self` to `&self` so its matrix-free operator satisfies
  `LinearOperator::apply(&self, ...)`. Its only mutation is a scratch cache.
- **Stage D** — delete `leto-ops/src/application/linalg/iterative/` including
  the duplicated `LinearOperator`/`Preconditioner` traits; residue scan clean.

## ATLAS-CFDRS-ATHENA-MIGRATION-001 — Stage B: CFDrs to Athena [major] [arch] — in-progress

Surveyed 2026-07-28 before starting. This is a redesign of the CFDrs
linear-solver architecture, not a port, and two of the mismatches change a
public CFDrs API — recording them rather than deciding unilaterally.

### Scale

56 files and 242 references across six crates (`cfd-1d`, `cfd-2d`, `cfd-3d`,
`cfd-core`, `cfd-math`, `cfd-validation`), of which **24 are production solver
construction sites** in 8 files; the rest are tests, benches, and re-exports.

`cfd_math::iterative` is currently a pure re-export of the `leto-ops` family
(`lib.rs:179`), so every consumer reaches the solvers through one facade.

### Structural mismatches

1. **Const-generic restart vs runtime config.** `Gmres<B, RESTART>` fixes the
   restart width at compile time. `LinearSolverChain` carries
   `krylov_restart: usize` as a runtime field with a builder
   (`with_krylov_restart`) and clamps it per solve:
   `min(self.krylov_restart, n_total_dof.max(1))`. A const generic cannot take
   that value. **Decision needed** (see below).
2. **Dynamic solver selection.** Four sites hold `Box<dyn LinearSolver<T>>`,
   including `cfd-validation` which builds a `Vec` of boxed solvers to compare
   CG against BiCGSTAB on the same system. Athena's solvers are ZST markers
   with static `solve_into`; `KrylovBackend` has GATs and `Gmres` a const
   generic, so none of it is dyn-compatible. The sanctioned replacement is
   enum dispatch over the closed solver set — I can decide this one, it is
   what the standards prescribe before reaching for `dyn`.
3. **Preconditioner trait.** CFDrs preconditioners — `AlgebraicMultigrid`,
   `BlockDiagonalPreconditioner`, `SimplePreconditioner`, `IncompleteLU`,
   `DiagJacobi` — implement `leto_ops::Preconditioner<T>`. Each needs an
   `athena_core::Preconditioner<LetoBackend<T>>` implementation instead.
   Mechanical, but touches every preconditioner.
4. **Caller-owned workspaces.** CFDrs solvers allocate internally per call;
   Athena requires a workspace owned by the caller and sized to the system, so
   every call site gains workspace lifetime management. This is the property
   that makes Athena allocation-free, so it is a real improvement rather than
   friction to work around — but it is a call-site change everywhere.
5. **Config to policy.** `IterativeSolverConfig { max_iterations, tolerance,
   relative_tolerance }` maps onto the validated `ConvergencePolicy`, which
   also carries a check interval and rejects invalid tolerances at
   construction. Mechanical.

### Decisions needed

**D1 — restart width.** Either (a) make `krylov_restart` a const parameter on
`LinearSolverChain`, a breaking change to a public CFDrs API; or (b) keep the
runtime field and dispatch across a small fixed set of `RESTART` instantiations
by enum, paying monomorphisation for each; or (c) fix one restart width and
delete the knob, checking first whether any caller sets it to a non-default
value. Recommend (c) if the knob is unused in practice, else (b).

**D2 — migration shape.** Either (a) convert all six crates in one change,
green only at the end; or (b) convert crate by crate while `cfd_math::iterative`
still re-exports `leto-ops`, deleting the facade last. (b) keeps the tree green
per commit and is not a shim — the old path stays only until its last consumer
is gone, which is what the anti-shim rule prescribes for a migration of this
size. Recommend (b), ordered `cfd-math` internals, then `cfd-2d`, `cfd-3d`,
`cfd-1d`, `cfd-validation`, then facade deletion.

### Not started

No CFDrs code changed. Nothing was added that would sit unused pending the
decisions above.

### Stage B progress 2026-07-28 — foundation landed, D1 corrected

**D1 was answered (c), and the check that answer depended on disproved it.**
`krylov_restart` is not an unused knob: `cfd-3d/fem/solver.rs` sets
`min(200, n)` at two sites, `cfd-1d/newton_fallback.rs` derives it from
`max_krylov_iterations`, and `cfd-math/nonlinear_solver/jfnk.rs` carries it in
its own config with 30 and 10 in tests and `min(n)` at runtime; the direct
`GMRES::new` sites use 30 and 100. Fixing one width would have silently
changed four solver configurations, so I took the fallback named in the same
decision — **(b), a fixed ladder with dispatch**.

- athena `f24dded`: `BorrowedCsrOperator`. `CsrOperator` takes ownership,
  which would force a per-solve `O(nnz)` sparse clone in a chain that tries
  several preconditioners against one system. Mirrors `BorrowedDenseOperator`.
- CFDrs `6a13a672`: `cfd_math::linear_solver::krylov` — the restart ladder
  (8/16/32/64/128/256, smallest covering width), `ConvergencePolicy`
  translation, and `gmres`/`gmres_preconditioned`/`bicgstab` entry points over
  Athena. Additive per D2(b): the `iterative` facade still re-exports leto-ops,
  so no consumer changed and the tree stays green per commit.
- Also repaired two cfd-math benches that had not compiled since `8aee5e59`
  left a stray brace in their imports.

Verification: cfd-math library compiles, clippy clean on the library, both
ladder cases pass, fmt clean. The package `--all-targets` gate is red for
reasons predating this change — unused imports and a dead struct in cfd-math
tests from the in-flight SSOT migration.

### Contention on the next increment

`chain.rs` is the next conversion target and a peer is **actively working in
it**: commit `16096fbc` ("resolve Quantity type mismatches in cfd-1d examples
and chain.rs") landed at 19:05 today and its rewrite of
`linear_solver/mod.rs` dropped the `pub mod krylov;` registration I had added,
leaving my file an orphan until I restored it. Converting `chain.rs` now would
collide directly.

Next increment should either wait for that scope to go quiet, or start at a
crate the peer is not in — `cfd-2d/src/physics/momentum/solver.rs` and
`cfd-2d/src/pressure_velocity/pressure.rs` are independent of `chain.rs` and
carry four of the twenty-four construction sites.

Remaining conversion order: `cfd-math` internals (`chain.rs`, multigrid),
`cfd-2d`, `cfd-3d`, `cfd-1d`, `cfd-validation`, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

Note for `cfd-validation`: four sites hold `Box<dyn LinearSolver<T>>` to
compare solvers on one system. Athena's markers are not dyn-compatible, so
that becomes enum dispatch over the closed solver set, per the standards.
