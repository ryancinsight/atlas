# atlas — kwavers/CFDrs/ritk → Atlas migration backlog

> Cross-repo migration board. **Per-repo** PM artifacts remain SSOT for repo-local concerns (e.g. `repos/kwavers/backlog.md`, `repos/CFDrs/docs/backlog.md`, `repos/ritk/backlog.md`); this artifact owns only the migration scope that crosses repo boundaries (provider-side obstacles, dep-velocity closure, and shared definition-of-ready gates).
>
> Active tactic: `checklist.md`. Full migration inventory: `gap_audit.md`. PM artifact freshness/SSOT rules per atlas `AGENTS.md` `documentation_discipline`.
>
> **Active sprint target version**: 0.16.0 (atlas meta — current branch `codex/kwavers-atlas-integration`).

---

## Cross-repo architect coordination ledger

Three CR-class items carried from `docs/audit/2026-07-02-cross-repo-integration-audit.md` (`L71-149`). Each is self-contained and gates specific consumer-side migrations below.

| ID | Class | Title | Owner repo (provider land) | Supertypes | Consumer land unlocked |
| --- | --- | --- | --- | --- | --- |
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` as the universal supertrait (single SSOT). Delete the vocabulary that already lives on `NumericElement` (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep the backend-specific slice-kernel surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `axpy_rows`, leto-ops `from_usize`). See `atlas/docs/adr/0005-eunomia-scalar-ssot.md` for the proof that `RealField` (float-only) cannot be a universal `Scalar` supertrait (would orphan `coeus_core::Int` for i8/u8/.../u64). | `coeus`, `leto` (joint) | `eunomia` is doctrine holder | kwavers `RealField` nalgebra → eunomia; CFDrs `cfd-math` solver-chain RealField seam; ritk `Burn::Module → coeus::Module` rebind |
| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-only registration. Strip from `cfd-core`, `ritk-core`, `moirai/lib`. Pass `Mnemosyne` handles via DI to library callers. | `cfd-core`, `ritk-core`, `moirai` (joint) | `mnemosyne` is allocator holder | Library composition stays provider-neutral; binaries own allocator policy |
| **CR-1** | `[arch]` | Delete `apollo/crates/apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell` (with `brand_scope!` mint). | `apollo`, `melinoe` (consumer) | `melinoe` is brand doctrine holder | All brand-borrow contention becomes provider-exclusive |

### Provider extension register

These cross-cut consumer migration but live in provider land. Each requires its own [minor] backlog entry in the owning provider repo:

| Provider | Missing surface | Substrate | Tracked in |
| --- | --- | --- | --- |
| `leto` | `Quaternion<T>` + 4-row `Matrix4<T>` operator coverage | math | `leto/backlog.md` |
| `leto-ops` | `CscMatrix<T>`, `CooMatrix<T>`, `lu_batch`; `ExecutionStrategy` → `MoiraiBackend::ParIter` seam | ops | `leto/backlog.md` |
| `moirai-async` | `mpsc::channel`, `oneshot::channel`, `Condvar`, `Mutex`; `#[moirai::main]` proc-macro | async | `moirai/docs/backlog.md` |
| `apollo` | RustFFT-free differential oracle; prune workspace `rustfft = "6.4.1"` pin (`apollo/Cargo.toml:84`) gated behind `apollo-validation` dev-dep | validate | `apollo/backlog.md` |
| `eunomia` | Author `eunomia-gpu` OR fold into `hephaestus::DialectScalar` (close README aspirational claim). (The `NumericElement::ZERO`/`::ONE` constants already exist per `eunomia/src/traits/numeric.rs:27-29`; the prior register line proposing to add `zero()/one()` is disproven and removed.) | basis | `eunomia/backlog.md` |
| `coeus` | Autograd-side `Var<T,B> {scatter_add}` wrapper (ops-only Tensor exists); `eq/ne/lt/gt` comparison free fns in `coeus-ops::BackendOps`; `Dataset`/`DataLoader` trait if PINN dataset paths require | autograd | `coeus/docs/backlog.md` |
| `hephaestus` | `wgpu::PipelineCache` integration (perf, WG-P8 from substrate audit); close `CU-C1`, `CU-P1`, `WG-S1`, `BOTH-SCAN` HIGH-sev defects (substrate audit) | gpu | `hephaestus/backlog.md` |

---

## Migration batches (vertical slices)

Ordered per Definition-of-Ready (provider SSOT closes first). Each batch is self-contained, has observable pass conditions, and respects the WIP limit (one in-flight merge-affecting item per micro-sprint). Cross-repo item as policy: one batch is **the** item; commits ride under the established `codex/kwavers-atlas-integration` branch through that batch's owner.

### Consumer-side (kwavers / CFDrs / ritk)

| Batch | Class | Crate | Surface | Pre-reqs | Pass condition (value-semantic) | File-line scope (illustrative) |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | `[patch]` | `kwavers-solver` ([side path RTM/elastic PDE](file_pattern)) | `par_for_each` Zip → `moirai-parallel::par_mut().enumerate()` (62 sites); `Zip::indexed` → `par().enumerate()` (24 sites) | (none — confirmed by `moirai-parallel/src/lib.rs:106-181` tan rename) | `cargo nextest run -p kwavers-solver` green; spatial-step norm conservation within derived epsilon; `ndarray = ..., features = ["rayon"]` strip from `kwavers-solver/Cargo.toml:24` and `kwavers-physics/Cargo.toml:20` asserts `cargo tree -p kwavers-solver \| grep rayon` empty | `crates/kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{wavefield,propagation,mod,laplacian,imaging,illumination}.rs`; `crates/kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral}/...`; `crates/kwavers-solver/src/forward/{elastic/swe/int, pstd/ext, multiphysics/fluid_structure}/...`; `crates/kwavers-physics/src/acoustics/...`; `crates/kwavers-physics/src/optics/polarization/linear.rs` |
| #2 | `[minor]` | `CFDrs/cfd-math` ([ite solver finish](file_pattern) + `cfd-1d`/`cfd-3d`/`cfd-validation`) | nalgebra → let, nalgebra-sparse → leto-ops `CsrMatrix`; covariance solves / geometry / finite-element typedefs | CR-4 (eunomia SSOT) so `RealField → eunomia::RealField` is universal | `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation` green; xtask scanner delta shows `nalgebra` allowlist contracts under cfdec-solver chain, cfd-3d fem/libnodes, cfd-1d linear_system and cfd-validation geometry; `nalgebra-sparse` allowlist contracts to zero | `cfd-math/src/linear_solver/{chain, preconditioners/{*, ilu/*, multigrid/*, schwarz, ssor}}.rs`; `cfd-3d/src/fem/{element, projection_solver, leto_bridge, solver, stabilization, stress, quadrature, shape, fluid}.rs`; `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**`; `cfd-3d/src/vof/{cavitation, reconstruction}.rs`; `cfd-1d/src/solver/core/{convergence,linear_system,matrix_assembly,state,workspace,anderson,solver_detection}.rs`; `cfd-validation/src/{geometry, benchmarks, literature, manufactured, numerical, adaptive_mesh, tests}/**` |
| #3 | `[minor]` | `ritk` ([Provider-side Burn trait rebind](file_pattern)) | `ritk_core::{Image, Transform, Interpolator}` → `coeus_core::{ComputeBackend, Scalar}`; `ritk-spatial::{Vector,Point,Direction}` lose `burn::module::{Module,AutodiffModule}+burn::record::Record` impls; `ritk-image::types::Image<B,D>` re-exports exit Burn-keyed facade | CR-4 so eunomia `Scalar/RealField` is universal | `ritk-image::native::Image<T: Scalar, B: ComputeBackend, const D: usize>` becomes the canonical re-export; `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation}` green; `cargo tree -p ritk -i burn-wgpu -i burn-cuda -i burn-rocm` returns zero (Burn only CPU NdArray backend remains per DEP-496-01) | `ritk-core/src/{image/types,transform/trait_,interpolation/trait_}.rs`; `ritk-spatial/src/{vector,point,direction,spacing}.rs`; `ritk-image/src/types.rs` + `ritk-image/src/lib.rs:11` re-export line; `ritk-wgpu-compat/src/lib.rs` (the apply_row_chunks shim's `B:Backend` bound → `B:ComputeBackend`); per-filter `*/new(B::Device)` constructors |
| #4 | `[minor]` | `kwavers-solver` ([PINN Burn → Coeus](file_pattern)) | `burn::backend::NdArray<f32>` ⇒ `coeus-core::MoiraiBackend`; `burn::optim::{SGD,Adam,AdamW,lr_schedule::*}` ⇒ `coeus-optim::*`; `burn::module::Module` ⇒ `coeus-nn::Module`; `burn::record::Record` ⇒ `coeus-nn::Record`; `burn::tensor::*` ⇒ `coeus-tensor::*`; ~325 source lines + ~17 top-level dev-dep files | CR-4 + #3 + `coeus-autograd/scatter_add` extension | `cargo nextest run -p kwavers-solver --features pinn` green; per-physics trainer residual gradient matches golden reference within neum-compensated epsilon (derived from reduction depth × sqrt(N) per current `es::BatchModern` chain); kwavers top-level `Cargo.toml:138` `[dev-dependencies] burn = "0.19"` flips to deps via `coeus` (or top-level burn demoted fully) | `crates/kwavers-solver/src/inverse/pinn/**` (~80 files; cite-referenced inside the inventory in checklist.md); top-level `crates/kwavers/{benches,examples,tests}/**` (17 files); `kwavers-solver/Cargo.toml:42` feature set; `kwavers/Cargo.toml:138` dev-deps |
| #5 | `[arch]` | CR-1: `apollo-ghostcell` deletion + `melinoe::MelinoeCell` rebind (provider land) — single coordinated commit | (See provider-extension register above) | (None — provider-only action) | (See CR-1 row above) | `apollo/crates/apollo-ghostcell/src/lib.rs` removed; every apollo consumer routed via `melinoe::MelinoeCell`; `cargo nextest run -p apollo-* --features melinoe` green; `cargo miri test -p melinoe` green |
| #6 | `[arch]` | CR-2: Consolidate `#[global_allocator]` (provider land) — single coordinated commit across `cfd-core`, `ritk-core`, `moirai/lib` | (See CR-2 row above) | (None) | (See CR-2 row above) | Library registry sites reduced; per-binary (`kwavers-cli`, `cfd-cli`, `helios`, `ritk-cli`, `mnemosyne-gbench`, etc.) keeps or replaces registration; `cargo build -p cfd-core` without `mnemosyne` feature succeeds |
| #7 | `[arch]` | CR-4: `coeus-core::Scalar` + `leto-ops::Scalar` rebase to eunomia supertraits (provider land) — **STATUS: ✅ CLOSED 2026-07-05. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`b15439b` ✅ on `codex/leto-cr4-ssot-rebind`)** | (See CR-4 row above) | (None) | (See CR-4 row above) | eunomia: `eunomia/crates/eunomia/src/traits/numeric.rs` doc clarified (ZERO/ONE/sqrt/abs/to_f64 stay FloatElement for float paths); Complex<T>/isize/usize implementations added. coeus: `coeus/coeus-core/src/dtype/traits.rs` (`Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem + Clone`); 64-file coeus call-site disambiguation landed. leto: `leto/crates/leto-ops/src/domain/scalar.rs` `pub trait Scalar: NumericElement` rebind; redundant UFCS items removed (ZERO/ONE/add/sub/mul/div/bitand/bitor/bitxor/count_ones/to_f64); slice kernels given default bodies; `from_usize` retained. `Cargo.toml` workspace version `0.35.1 → 0.36.0`. Resolution (a) applied (additive rebind is structurally infeasible per `atlas/checklist.md` structural-infeasibility addendum + E0034 evidence). Verification (pre-merge on `codex/leto-cr4-ssot-rebind`, 5 files / 196 +/-622 net subtraction): `cargo nextest run -p leto-ops` 270/270 green + `-p leto` 189/189 green + 8 doctests green + clippy `-D warnings` green on `--lib --tests` scope. Pixel/range/structural artifact: net 466-line subtractive consolidation (no vocab duplication remains). RG-verified zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS references in `crates/`. |
| #8 | `[minor]` | Provider extension (provider land): `leto Quaternion`, `leto-ops {Csc,Coo,lu_batch}`, `moirai-async {mpsc,oneshot,Condvar,Mutex,#[moirai::main]}`, `apollo wasm-free oracle` | (See provider-extension register above) | (Threads across consumer migration; file as individual [minor] items in owning repos) | (See provider-extension register above) | tracked separately in `repos/<provider>/backlog.md` |

### Token batch ordering

Batches #5, #6, #7 are the [arch] provider-SSOT gates. Per `decision_policy` nternals:

1. **#7 first** (CR-4 eunomia SSOT) — **eunomia + coeus sides ✅ landed 2026-07-05**; leto side 🔴 blocked on `reak/array-to-vec` PR #30 origin divergence — user decision required to unblock (see checklist.md `## blocker ##`). Required by #2 (CFDrs nalgebra finish), #3 (ritk Burn rebind), and #4 (kwavers PINN Burn → coeus). Single provider-only commit in `coeus-core` + `leto-ops` (+ tiny `complex.rs` impl update + optional `leto-ops/Cargo.toml num-traits` strip). ADR `0005-eunomia-scalar-ssot.md` (status **Accepted**) describes the actual rebase; `RealField` is NOT a universal `Scalar` supertrait (would orphan `Int`); `NumericElement` is. ADR signed off via autonomy mode per `interaction_policy`.
2. **#5 second** (CR-1) — Pure provider cleanup; no consumer call sites depend on it for the migration below.
3. **#6 third** (CR-2) — Library-vs-binary layering; consumer migrations (#1, #2, #3, #4) are not strictly gated by it but the layering matters on connect-build.
4. **#1 fourth** — `kwavers-solver` residual Rayon → Moirai. Self-contained. Calls CTE immediately after a clean CR-4.
5. **#2 fifth** — Largest consumer body (176 CFDrs source files). Depends on CR-4. ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
6. **#3 sixth** — ritk Burn keyed-trait rebind. Depends on CR-4.
7. **#4 seventh** — kwavers-solver PINN Burn → coeus. Depends on CR-4 + #3.
8. **#8 last** — Provider extensions; tracked in provider repos separately; own claim stream.

### In-flight claims (per concurrent_agents)

- Atlas-meta branch: `codex/kwavers-atlas-integration` (PM artifacts only).
- Atlas-meta claim scope (this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root; no per-repo files touched at the atlas-meta layer.
- Atlas-meta last landed (codex session): `5328de1c` (CR-4 closure 2026-07-05 20:27). Peer ryancinsight landed the Batch #2 closure pointer advance + sync as `51922a56` / `7a046c13` / `dd676d13` early 2026-07-06 08:14–08:21 — parent HEAD now `dd676d13` (peer's own atlas-meta commits, recorded here for cross-session attribution). **Latest closed migration batch**: Batch #2 (CFDrs nalgebra → leto + nalgebra-sparse → leto-ops CsrMatrix across cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation) — landed in inner CFDrs as commit **`d58d1fe320d046816425e1d20d16735fcfee7995`** on branch `codex/cfdrs-atlas-migration` (2026-07-05 23:33); Atlas-parent submodule pointer advance landed as `51922a56` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
- **This codex session (2026-07-06)**: Path C atlas-meta cleanups — (1) deleted stray 0-byte `nul` artifact at workspace root (Windows-reserved-name shell-redirect artifact, untracked); (2) T1 re-verification of gap_audit surfacing risks #2 and #3, both retracted as stale-memory misreads — `ritk-core` `mnemosyne-alloc` feature exists at `Cargo.toml:8` and `default = ["mnemosyne-alloc"]`, and no `rust-toolchain*` file exists at `repos/kwavers/`; (3) closed surfacing risk #7 (ADR 0005 status bump done in `b66ec228`). `docs/adr/0005-eunomia-scalar-ssot.md` already at status "Accepted — implementation closed 2026-07-05". `repos/themis` triaged: peripheral provider-cache single-crate, no migration relevance, left alone. Risk #1 (`RITK/Cargo.toml:69` retains `wgpu` feature in `burn` workspace dep) verified still live — stays open for Batch #3 work.
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (last landed 2026-07-05 22:19, ~2.5h ago as of this edit): two new commits in this session's window — `1dc47028a refactor(kwavers-math)!: Port to eunomia/leto/moirai-parallel, drop nalgebra` and `f36995162 refactor(kwavers-gpu, kwavers-solver)!: Generic GPU provider seam over Hephaestus`. The peer's recent work migrated `kwavers-math` (drop nalgebra) and added a GPU provider seam over Hephaestus. **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai) remains OPEN**: 107 residual `ndarray::Zip::indexed(...).par_for_each(...)` / `Zip::from(...).par_for_each(...)` sites across 40 files (31 in `kwavers-solver`, 9 in `kwavers-physics`); `kwavers-math` and `kwavers-core` are Rayon-free. `kwavers` root `Cargo.toml:43`, `kwavers-solver/Cargo.toml:24`, `kwavers-physics/Cargo.toml:20` all still carry `ndarray = { ..., features = ["rayon", ...] }`. **No reclaim**: the peer is actively landing adjacent scope per `concurrent_agents` disjoint-scope rule; the kwavers Batch #1 surface belongs to the peer's claim stream. This meta layer therefore does not initiate kwavers-source edits and tracks the peer's progress as it lands.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (peer, 20+ WIP files — moirai source forbidden); `repos/leto` `codex/leto-fixed-spatial-reconcile` (peer, 2 stashes + ~41 unstaged + `Cargo.toml:39` serde_json workspace-dep placeholder still breaks leto's `cargo` parse — leto source forbidden); `repos/coeus` `crates/coeus-ops/Cargo.toml` melinoe 0.7.0 → 0.8.0 uncommitted; `repos/eunomia` `crates/eunomia/src/{traits,impls/primitives,impls/wrappers}/float.rs` `acos/asin/atan` uncommitted; `repos/apollo`, `repos/CFDrs`, `repos/gaia`, `repos/hermes`, `repos/helios`, `repos/melinoe`, `repos/mnemosyne`, `repos/ritk`, `repos/themis` carry in-flight peer claims.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.

### Cross-engineering verification — `hephaestus-cuda` eigen.rs Complex upload

The earlier `fb83d009` residual risk is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. Source inspection on 2026-07-06 shows `hephaestus-cuda/src/application/decomposition/eigen.rs` maps `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` with `Complex::new(z.re, z.im)` before `device.upload(&e_host)`, while `hephaestus-core::ComputeDevice::upload<T: bytemuck::Pod>` remains the generic transfer seam. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build verification plus source inspection; no runtime CUDA device execution was claimed.


---

## Out-of-scope (explicit)

- **`**Spec composition layers**` updated later (e.g. `cfd-validation`, testing frameworks)**: not part of this migration; filing as separate backlog if it's not in CFDrs's own backlog.
- **HELIOS/Python binding for kwavers**: Phase-3 rich-image scoping state; deferred-until `kwavers-python` intent-bledged beyond current net-style top-level.
- **GPU backend complete production rollout across ritk-model**: PPG-model is reserved-wave per `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md` HIGH-sev list; out of scope until defect closure.

### Atlas-root working-tree dirty triage (2026-07-06)

The Atlas-root `D:/atlas` working tree carries 29 dirty files (19 tracked-modified + 10 untracked) outside the migration-push closure chain. The vast majority have been classified as real Atlas-meta PM artifacts and committed in five atomic batches on 2026-07-06 (see commit history since `2c38db42`). The remainder is explicitly recorded below as **out-of-scope for the Atlas-parent pointer-advance ritual** — they live in scopes the Atlas-parent cannot reach (submodule internals, foreign root-level scratch, or non-submodule external dirs) and require separate-flow cleanup that is staged outside this branch's claim scope.

#### A. Root-level scratch (Windows-reserved + atroot scratch)

- `nul` — 0-byte Windows-reserved-name artifact (likely a `> nul` shell-redirect leak). **Recommendation**: delete + add `nul` line to `.gitignore`. Separate chore commit; out of scope here.
- `script.py` — root-level Python scratch that doesn't belong at the meta layer (no shebang or module docstring; left at atlas workspace root by ad-hoc shell invocation during a peer-claim experiment). **Recommendation**: delete and re-stage under `scripts/`. Separate chore commit; out of scope here.

#### B. External / non-ASCII-dir content

- `repos/SynthSeg/` — external Python research project (SynthSeg brain segmentation). **Not** a submodule (no `.gitmodules` entry; no `.git` of its own; original `repos/SynthSeg/CHANGELOG` reads "external tooling"). **Recommendation**: add `repos/SynthSeg/` to `.gitignore` (single-line chore commit). Out of scope here.
- `repos/report/` — non-ASCII-filename name dir (likely generated report output). Shell `find` fails to enter the path on the working machine, so its true contents are unknown. **Recommendation**: add `repos/report/` to `.gitignore` if generated, otherwise delete. Out of scope here (typed as an investigation, not a fix).

#### C. Submodule-internal dirtiness (uncommitted in inner repos — out of Atlas-parent reach)

These show up in Atlas-root `git status` as `M repos/<name>` (parent-tree entry marked dirty because the inner submodule's tree contains modifications relative to the gitlink pinned here). They are **cleanable only by an inner-submodule commit + parent-tree gitlink advance**, NOT by Atlas-parent commit. Each row is the inner-dirty count + inner HEAD as of 2026-07-06. No reclaim from Atlas-meta; these belong to the claim streams holding the inner repos.

| Submodule | Inner dirty count | Inner HEAD | Inner branch / claim stream |
|-----------|---:|------|---|
| `apollo`         | 235 | `f1ddf7a`     | peer claim stream `codex/apollo-atlas-migration` (WIP) |
| `CFDrs`          | 0   | `d58d1fe3`    | (clean post-Atlas-provider migration push, tagged `batch2` per ADR 0010) |
| `coeus`          | 19  | `1ae2f30`     | peer claim stream |
| `eunomia`        | 7   | `57d7789`     | peer claim stream (CR-4 ⏳ pending CR-EUNOMIA-COMPLEX-side `acos/asin/atan` land) |
| `gaia`           | 5   | `8f4a862`     | peer claim stream |
| `hephaestus`     | 0   | `007a1a1`     | (clean — `ks5-cholesky-panel` HEAD) |
| `hermes`         | 46  | `1b5392a`     | peer claim stream |
| `kwavers`        | 602 | `f36995162`   | peer claim stream `codex/kwavers-core-moirai-parallel` (Batch #1 Rayon→Moirai in flight) |
| `leto`           | 7   | `626ebf5`     | peer claim stream `codex/leto-fixed-spatial-reconcile` (disjoint from CR-4 leto side) |
| `melinoe`        | 13  | `7ec0a44`     | peer claim stream |
| `mnemosyne`      | 0   | `3c41870`     | (clean — post-[patch] ChainMnemosyneHeap + macro-consolidation) |
| `moirai`         | 26  | `9b7881f`     | peer claim stream `refactor/remove-dead-subsystems` |
| `ritk`           | 631 | `3c36e847`    | peer claim stream |
| `themis`         | 0   | `e87618a`     | (clean — no migration relevance; triaged 2026-07-06) |
| **Σ** | **1591 inner files** | — | — |

#### D. Helios-internal pre-session WIP (uncommitted inside `repos/helios`)

The Atlas-root `M repos/helios/<file>` markers below denote 6 specifically-named files inside the inner-helios submodule, which itself carries 29 internal dirty files at HEAD `2c38db42` (= Atlas-parent HEAD, coincidence of SHA only; the inner working tree differs from its tree-commit baseline). These land in `repos/helios` (atomic commits there), not in Atlas-parent.

| File | Description | Clearable by |
|------|-------------|--------------|
| `repos/helios/CHANGELOG.md`   | Sprint-1 prior paragraph updates pre-2026-07 | inner-helios commit |
| `repos/helios/CHECKLIST.md`   | Pre-session `[arch]` cleanups | inner-helios commit |
| `repos/helios/Cargo.lock`     | 3 dropped deps + 6 dep-cap bumps | inner-helios commit (post dep-drop) |
| `repos/helios/Cargo.toml`     | num-traits removal (H-062) + dicom/ndarray feature-edge removal (H-061) — already in 2026-07-05 draft, not committed yet | inner-helios commit (H-061 / H-062) |
| `repos/helios/backlog.md`     | Pre-session Helios Sprint-1 task adds | inner-helios commit |
| `repos/helios/gap_audit.md`   | Pre-session Helios gap closures (H-061/H-062 entries, this turn's) | inner-helios commit |

Plus 23 additional `repos/helios/**` file-dirty markers across helios-domain/dicom, helios-simulation, helios-planning, helios-analysis sub-tree — counted in `git -C repos/helios status --short | wc -l` = 29 internal total, minus the 6 named above. All require inner-helios commit; the Atlas-parent cannot reach them.

#### E. Future-correction hooks (not in scope this turn)

If during 2026-07-07 via 2026-07-13 cleanup sprints the Atlas-root commits listed in §A / §B land (deleting `nul`/`script.py`, `.gitignore` adding `repos/SynthSeg/`, `nul`, `repos/report/`), this OOS subsection can be retracted. The Atlas-root pointer-advance ritual deliberately does not own these fixes because (1) the user-scoped brief was "triage" not "fix", and (2) the inner-submodule rows (§C, §D) cleanup is intertwined with the per-repo claim streams and must not be reclaimed by Atlas-meta per `concurrent_agents` disjoint-scope rule.
