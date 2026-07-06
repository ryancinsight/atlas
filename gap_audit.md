# atlas — kwavers/CFDrs/ritk → Atlas migration gap audit

> Cross-repo consolidator: per-repo gap audits (`repos/kwavers/gap_audit.md`, `repos/CFDrs/docs/gap_audit.md`/`backlog.md`, `repos/ritk/gap_audit.md`) remain authoritative for repo-local gaps. This file records:
>
> 1. Three cross-repo architect coord items (CR-1/CR-2/CR-4) carried out of `docs/audit/2026-07-02-cross-repo-integration-audit.md`;
> 2. Migration evidence inventory (off-tree residual that was hidden from individual repo gap audits);
> 3. Provider-extension register with file-line anchors;
> 4. Provider-side obstacles that block consumer migration until the provider extension lands.

---

## Cross-repo architect coord items (CR-class)

| ID | Class | Title | Evidence | Status |
| --- | --- | --- | --- | --- |
| **CR-1** | `[arch]` | Delete `apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell`. | Source: `apollo/crates/apollo-ghostcell/src/lib.rs`; `melinoe/src/lib.rs:18-24,65-115,233` (`pub use cell::{MelinoeCell,MelinoeMut,MelinoeRef}`); `atlas/docs/audit/2026-07-02-cross-repo-integration-audit.md`:L71-75 ([arch] CR-1 citation). | OPEN. Carried into `backlog.md` Batch #5. |
| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-level registration. Strip library crate presence. Library crates pass Mnemosyne handle via DI. | Source citations T1: `cfd-core/src/lib.rs:45-53`; `ritk-core/src/lib.rs:15-17` (dead cfg gate per audits); `moirai/lib.rs`; `coeus/coeus-python/src/lib.rs:7-9`; `atlas/docs/audit/2026-07-02-cross-repo-integration-audit.md`:L76 (CR-2 [arch] citation, audit_id). | OPEN. Batch #6. |
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `let''o-ops::Scalar` over `eunomia::NumericElement` (NOT `NumericElement + RealField` — `RealField` is float-only and would orphan `coeus_core::Int` for i8/u8/.../u64). Delete duplicated vocabulary (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep backend slice-kernel surface. | **2026-07-05**: Implementation split across 3 commits. T1 evidence landed per repo sub-row: eunomia `57d7789` (SSOT trait doc + Complex<T>/isize/usize impls + private::Sealed + CastFrom<i32>); coeus `2b3f820` (`feat(scalar)!:` — coeus_core traits + 64-file call-site disambiguation across coeus-{autograd, ops, nn, fft, optim, tensor}, doctests, clippy `assign_op_pattern` adjacent fix); leto `b15439b` (`feat(scalar)!:` on `codex/leto-cr4-ssot-rebind` — `pub trait Scalar: NumericElement` rebind; redundant UFCS removed; slice kernels to operator-syntax; `cargo` workspace `0.35.1 -> 0.36.0`). ADR: `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (status **Accepted**).<br>**2026-07-05 (CR-4 closure)**: Atlas-meta submodule pointer for `repos/leto` bumped from `21681967e` to `b15439ba`; atlas-meta PM artifacts (`atlas/{backlog,checklist,gap_audit}.md`) updated to mark CR-4 closed and unblock Batches #2/#3/#4 as Definition-of-Ready. Pre-stage gates on the rebind: 270/270 nextest `-p leto-ops` + 189/189 `-p leto` + 8 doctests + clippy `-D warnings` `--lib --tests` scope; `cargo fmt` clean; `cargo doc --no-deps` warnings peer-scope only (not introduced). Net subtractive consolidation: 196 added / 622 removed across 5 files. RG-verified: zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS in `crates/`. `cargo --workspace` scope on the rebind is blocked by peer-WIP `serde_json = { workspace = true }` in `repos/leto/crates/leto/Cargo.toml:39` without matching workspace dep declaration (peer claim stream; disjoint-scope rule prevents CR-4 from touching).<br>**2026-07-05 (alpha sync)**: `fb83d009 chore(atlas): Align submodule pointers to CR-4 eunomia/coeus/leto commits` aligned `repos/{coeus,eunomia,leto}` to the three landing SHAs (`1ae2f30c8` / `57d778930` / `21681967e`), records the kwavers-foundation GPU-error-boundary rule in `README.md`, pushes the chore to `origin/codex/kwavers-atlas-integration`. Re-verification at `fb83d009`: eunomia 29/29 + coeus `-p coeus-{core,tensor,ops,autograd,nn,sparse,dist,fft,optim,leto}` 758/758 nextest green; clippy `-D warnings` clean on the same set; doctests pass; `cargo doc --no-deps` warn-clean. `coeus-wgpu`/`coeus-cuda` nextest blocked by `hephaestus-cuda` eigen.rs ↔ `device.upload` Complex-type mismatch (`let''o::Complex` vs `num_complex::Complex`); **NOT a CR-4 regression** — pre-existing on `repos/hephaestus` `ks5-cholesky-panel` branch (commit `3bddfed5`, scope: ks5-cholesky-panel agent; eigen.rs:173 caller of `let''o_ops::eigenvalues(&view)` returning `Vec<let''o::Complex>`, while `device.upload` signature retains `&[num_complex::Complex<T>]` from `hephaestus-core/src/domain/device.rs:99`). Outside atlas-meta migration scope; ks5 to reconcile. | **CLOSED 2026-07-05**. eunomia `57d7789` ✅, coeus `2b3f820` ✅, leto `b15439b` ✅. Batches #2/#3/#4 now Definition-of-Ready. |

---

## Migration evidence inventory (residual surfaces scope-traced)

### CFDrs (`D:/atlas/repos/CFDrs`) — residual nalgebra surface

Source: xtask allowlist scanner `xtask/src/migration_audit.rs:6-23` (`LEGACY_MANIFEST_DEPS` + `LEGACY_SOURCE_TOKENS`); 185-line `xtask/legacy_surface.allowlist` auto-gen list.

- **Manifest residual**: 7 manifests × legacy deps:
  - `CFDrs/Cargo.toml:38,39,41` (`nalgebra 0.33 [serde-serialize]`, `nalgebra-sparse 0.10`, `num-traits 0.2`)
  - `crates/cfd-1d/Cargo.toml:21,22` (nalgebra + nalgebra-sparse via workspace)
  - `crates/cfd-3d/Cargo.toml:24,25`
  - `crates/cfd-core/Cargo.toml:21,22`
  - `crates/cfd-math/Cargo.toml:13,14`
  - `crates/cfd-validation/Cargo.toml:21,22`
  - `[simba 0.9]` workspace dep — auto-included via `nalgebra-simba` transitively; strips with nalgebra
- **Source residual**: 176 files (auto-allowlist); heaviest per-file:
  - `cfd-validation/src/geometry/mod.rs:55 hits`
  - `cfd-core/src/geometry/shapes.rs:52`
  - `cfd-3d/src/fem/projection_solver.rs:44`
  - `cfd-math/src/linear_solver/{conjugate_gradient:39, bicgstab:35, tests/mod:37, tests/extended_edge_case_tests:28, gmres/{arnoldi,solver}}`
  - `cfd-core/src/physics/boundary/geometry.rs:27`
  - `cfd-3d/src/{trifurcation/solver:27, fem/element:27, vof/reconstruction:24, ibm/forcing:22, trifurcation/geometry:20, fem/mesh_utils:19}/.rs`
  - `cfd-1d/src/solver/core/linear_system.rs:20`
- **Total nalgebra source impact T2**: ~1,900 symbol hits across cfdec topology.
- **Closure state**: per Sprint 1.96.126–1.96.137, LinearOperator/Preconditioner/solver trait surface is Leto-keyed. `_linear_system`, `_linear_operator`, `_preconditioner`, solver-chain internals, sparse storage, preconditioner internals still nalgebra-keyed.

### kwavers (`D:/atlas/repos/kwavers`) — residual nalgebra / ndarray / Rayon / burn surface

Source: hand-verified grep over `crates/*/src` plus `Cargo.toml` per-file evidence.

- **Residual nalgebra** (13 source sites × 5 manifests):
  - `crates/kwavers-mesh/src/tetrahedral/mesh.rs:14` (`Matrix3,Vector3`)
  - `crates/kwavers-transducer/src/flexible/calibration/{types.rs:3, manager/mod.rs:80, manager/kalman.rs:5}` (`DMatrix,DVector` for Kalman filter)
  - `crates/kwavers-medium/src/anisotropic/{christoffel.rs:130, stiffness.rs:191,225}` (`Matrix3,SymmetricEigen` for Christoffel acoustic tensor; small-size LU)
  - `crates/kwavers-analysis/src/signal_processing/beamforming/three_dimensional/cpu/mvdr/mod.rs:62` (`DMatrix,DVector` for Capon covariance-matrix solve)
  - `crates/kwavers-solver/src/inverse/fwi/frequency_domain/cbs/solve.rs:58` (`DMatrix,DVector` for FWI-CBS frequency-domain solver)
  - `crates/kwavers-solver/src/forward/hybrid/bem_fem_coupling/interface/mod.rs:3` (`Vector3`)
  - `crates/kwavers-solver/src/forward/hybrid/bem_fem_coupling/coupler/struct_impl/solvers.rs:3` (`Matrix3,Vector3`)
  - `crates/kwavers-solver/src/forward/helmholtz/fem/solver/core/{interpolation.rs:3, element.rs:3}` (`Matrix3,Vector3`)

- **Residual ndarray** (top contributors):
  - `crates/kwavers-solver/src/**` 759 line-hits (`inverse/pinn/...`, `forward/{nonlinear,elastic,pstd,...}`, `inverse/{fwi,reconstruction/seismic/rtm/inherent}`, `multiphysics/...`)
  - `crates/kwavers-physics/src/**` 290 (acoustics, EM, optics, field_surrogate, chemistry)
  - `crates/kwavers-analysis/src/**` 261 (signal_processing/beamforming, ml, performance)
  - `crates/kwavers-therapy/src/**` 148
  - `crates/kwavers-math/src/**` 106 (tensor/fft/numerical/simd)
  - `crates/kwavers-python/src/**` 100 (PyO3 bindings)
  - All 24 crates declare `ndarray` dep; `kwavers-phantom/gpu/phantom` use `workspace = true` → inherits `ndarray = "0.16" [rayon, serde]`.

- **Residual `Zip::par_for_each` (transitive Rayon)**:
  - `kwavers-solver`: 62 sites across `inverse/reconstruction/seismic/rtm/inherent/*` (23), `forward/nonlinear/{kuznetsov,westervelt_spectral}/*` (~21), `forward/elastic/swe/{integration,stress}/*` (13), `forward/pstd/extensions/elastic*` (4), `multiphysics/fluid_structure/{interface,solver}/*` (3), and `inverse/same_aperture/operator/linear_op` (6, already `moirai_parallel::ParMut`).
  - `kwavers-physics`: 24 sites across `acoustics/{conservation, mechanics, therapy, skull}` and `optics/polarization/linear.rs`.
- **Residual `ndarray = { features = ["rayon"] }` manifests**:
  - `crates/kwavers-solver/Cargo.toml:24` ⚠ (OPEN `[patch]` per `kwavers/gap_audit.md:3016`).
  - `crates/kwavers-physics/Cargo.toml:20` ⚠ (analogue).
- **Residual `burn`**:
  - `crates/kwavers/Cargo.toml:138` dev-deps `[std,ndarray,autodiff]` (no GPU features).
  - `crates/kwavers-solver/Cargo.toml:42` `[std,train,ndarray,autodiff]` (full suite).
  - `kwavers-solver/src/inverse/pinn/**`: ~325 `burn::` line-hits across 80+ files.
  - Top-level `crates/kwavers/{benches,examples,tests}`: 17 files using burn.
- **Provider-boundary closure (2026-07-04)**: the 3-D beamforming WGPU
  operation provider moved from `kwavers-analysis` to
  `kwavers-gpu::beamforming::three_dimensional::WgpuBeamformingProvider`.
  `kwavers-analysis` now keeps only `BeamformingGpuProvider` and the CPU
  reference, and `kwavers-analysis/gpu` no longer forwards WGPU/bytemuck/
  Hephaestus/pollster dependencies. Remaining GPU holdouts are exact:
  `kwavers-analysis/src/visualization/**` still owns WGPU visualization behind
  `gpu-visualization`; CUDA 3-D DAS kernels are not implemented; broader
  `kwavers-gpu` WGPU providers still need real CUDA operation-family kernels
  plus WGPU/CUDA differential tests; solver PINN Burn code is outside this
  provider-boundary slice.
- **Residual `num_complex`**: 12 crates declare `num-complex = "0.4"`; source-import sites 194 (kwavers-solver 55, kwavers-analysis 45, kwavers-physics 32). Apollo path is via `eunomia::Complex` already (`kwavers-math`).
- **Residual `num_traits`**: 5 manifests (`kwavers-{analysis,grid,math,physics,solver}`); 11 source-import sites.
- **Residual `std::arch::*` SIMD**: 27 line anchors across `kwavers-math/src/simd_*/...` (Hermes-routed), `kwavers-solver/src/forward/fdtd/avx512_stencil/{velocity,pressure}.rs` (libtargets for AVX-512), and `kwavers-analysis/src/performance/optimization/{config,cache}.rs` (`_mm_prefetch` hint). Stencil SIMD paths need separate [minor] migration to Hermes.
- **Closure state**: per `kwavers/gap_audit.md`, `~50` prior Rayon edges closed 2026-07-02/03 across solver/physics/imaging/simulation/top-level. Residual is the trip above.

### ritk (`D:/atlas/repos/ritk`) — residual burn surface (provider side obstacle)

Source: hand-verified scan over all 27 crates plus `RITK/Cargo.toml:69-72` workspace burn feature set.

- **Manifest residual**:
  - `RITK/Cargo.toml:69` `burn = { version = "0.19", default-features = false, features = ["std", "ndarray", "autodiff", "wgpu"] }` ← **`wgpu` still present despite `DEP-496-01` backlog-narrative DONE** — file drift flagged.
  - `RITK/Cargo.toml:70` `burn-ndarray = "0.19"`.
  - `RITK/Cargo.toml:88,112` `num-complex`, `num-traits` (manifest only; zero source uses detected).
- **Source residual** (764 burner-touching files; top contributors):
  - `ritk-filter`: 296
  - `ritk-registration`: 109–129 (autodiff metrics + classical spatial + backforms + optimizer/cgnostics)
  - `ritk-segmentation`: 88 (SurfaceExtraction `SignedDistanceTransformFilter`, `AntiAliasBinarySmoothFilter`, etc.)
  - `ritk-model`: 18–36 (DLSSM/TransMorph architectures)
  - `ritk-statistics`: 20–32
  - `ritk-{io,interpolation,transform}`: 24–30 each
  - `ritk-{python,cli,snap}`: 11–14 each (UI/thin bedrock)
  - `ritk-core/interpolation/trait_:20` public type `Interpolator<B: Backend>` (Provider-side obstacle; locks `Burn::Backend` trait surface for entire downstream).
  - `ritk-core/transform/trait_:19` public type `Transform<B: Backend, const D: usize>`.
  - `ritk-core/image/types:18` public type `Image<B: Backend, const D: usize>` (re-exported from `ritk_core::lib.rs:11`); downstream inherits Burn.
  - `ritk-spatial/{vector,point,direction,spacing}` impl `burn::module::{Module,AutodiffModule} + burn::record::Record` (Provider-side obstacle).
  - `ritk-io::{ImageReader,ImageWriter}<Image<f32,B,3>>` writes `B: Backend` parameter.
  - `ritk-deformer_field_ops::deformable_field_ops::CpuOrGpu<B>` defaults `burn::backend::NdArray` post `DEP-496-01`.
- **ndarray**: only 3 source sites, all in `ritk-python` for Python-side numpy interop (`use numpy::{ndarray::Array2, Array3, Array4}` etc.). Zero domain-side contact.
- **Closure state**: Sprint 495 (native writers for 9 formats — `MIGH, META, MINC, TIFF, JPEG, NRRD, Analyze, NIfTI, PNG`) merged into `ritk-io::ImageWriter<Image<f32,B,3>>` with Burn + native façade; `DEP-496-01` (default Burn features) marked DONE in backlog narrative — **unconfirmed by file literal** (drift to reconcile).

### Cross-utility

- `tokio`: zero hits in any of CFDrs, kwavers, ritk — fully migrated.
- `rayon`: zero direct hits; transitive only via ndarray `rayon` feature (above).
- `rustfft`: zero hits — `apollo-fft` consumed instead.
- `packed_simd`: zero hits.

---

## Provider extension register (provider land owned)

Source: provider capability baseline audit 2026-07-04.

| Provider | Missing surface | Owner | Refers |
| --- | --- | --- | --- |
| `let''o` | `Quaternion<T>` | `let''o` | `let''o/backlog.md` |
| `let''o` | `Matrix4<T>` typed-const + complete `Add/Sub/Mul` operator surface | `let''o` | `let''o/backlog.md` |
| `let''o-ops` | `CscMatrix<T>` | `let''o` (post leto-ops publishing) | `let''o/backlog.md` |
| `let''o-ops` | `CooMatrix<T>` | `let''o` | `let''o/backlog.md` |
| `let''o-ops` | `lu_batch` (batched-LU API to replace `rsparse` parity) | `let''o` | `let''o/backlog.md` |
| `let''o-ops` | `ExecutionStrategy::ParallelStrategy` → `MoiraiBackend::ParIter` trait-bounded seam (remove `ExecutionStrategy` enum-dispatch) | `let''o` | `let''o/backlog.md` |
| `moirai-async` | `mpsc::channel` (multi-producer single-consumer) | `moirai` | `moirai/docs/backlog.md` |
| `moirai-async` | `oneshot::channel` (one-reader one-message) | `moirai` | `moirai/docs/backlog.md` |
| `moirai-async` | `Condvar` primitive | `moirai` | `moirai/docs/backlog.md` |
| `moirai-async` | `Mutex` async primitive | `moirai` | `moirai/docs/backlog.md` |
| `moirai` | `#[moirai::main]` macro for binary entry (or document permanent `tokio::main` carriers) | `moirai` | `moirai/docs/backlog.md` |
| `apollo` | RustFFT-free differential oracle (MMS polynomial FFT) | `apollo` | `apollo/backlog.md` |
| `apollo` | Prune `rustfft = "6.4.1"` workspace pin (`apollo/Cargo.toml:84`); gate `apollo-validation` rustfft-only dep behind dev-feature | `apollo` | `apollo/backlog.md` |
| `apollo` | Verify GPU NUFFT path (`apollo-nufft-wgpu`) feature works downstream | `apollo` | `apollo/backlog.md` (testing RITKinsey/MIR) |
| `eunomia` | `NumericElement::zero()`/`one()` methods direct on the trait surface (today `Default`-derived only) | `eunomia` | `eunomia/backlog.md` |
| `eunomia` | Document `eunomia-gpu` aspirational claim status, or fold into `hephaestus::DialectScalar` and retire | `eunomia` | `eunomia/backlog.md` |
| `coeus-core` | `eq/ne/lt/gt` comparison free fn surface on `BackendOps` | `coeus` | `coeus/docs/backlog.md` |
| `coeus-autograd` | `Var<T,B>::{scatter_add}` autograd-side wrapper (frame-side ops-only today) | `coeus` | `coeus/docs/backlog.md` |
| `coeus-nn` | `Dataset`/`DataLoader` trait if PINN dataset code requires it (deferred if not) | `coeus` | `coeus/docs/backlog.md` |
| `hephaestus-wgpu` | `wgpu::PipelineCache` integration (perf, WG-P8 from substrate audit) | `hephaestus` | `hephaestus/backlog.md` |
| `hephaestus-cuda` | Close `CU-C1`, `CU-P1`, `WG-S1`, `BOTH-SCAN` HIGH-sev defects (substrate audit) | `hephaestus` | `hephaestus/backlog.md` |

---

## Provider-side obstacles for consumer migration (SSOT gates)

These are TypeScript-style locks that prevent consumer migration until the provider extension lands.

| Consumer migration batch | Obstacle | Required provider fix |
| --- | --- | --- |
| **Batch #2 (CFDrs nalgebra finish)** | `cfd-math::chain.rs:62-72` `LetoRealScalar` chain parallel-eunomia trait vocabulary; `RealField` bound currently `nalgebra::RealField`. | CR-4 (eunomia SSOT). |
| **Batch #3 (ritk Burn-trait rebind)** | `ritk-core::{Image<B,D>, Transform<B,D>, Interpolator<B>}` + `ritk-spatial::{Vector,Point,Direction}<D>` Burn `Module/Record` impls. | CR-4 (eunomia SSOT) + `eunomia::RealField` extended for backend/parametrized autograd. |
| **Batch #4 (kwavers-solver PINN)** | `burn::{Module,AutodiffBackend,Backend,optim::*,record::Record}` substitutions. | CR-4 + `coeus_autograd::scatter_add` + `coeus-ops::BackendOps::{eq,lt,...}`. |
| **Batch #1 (kwavers-solver/phys residual Rayon — already self-contained)** | `moirai-parallel::par_mut().enumerate()` rename pattern; chunk primitives naming distinction. | (None — verified by `moirai/moirai-parallel/src/lib.rs:106-181`.) |
| **Batch #8 (provider extensions — provider land)** | Provider-side extensions owned by provisioner repos. | Tracked above. |

---

## Imaging-side cross-cuts

- `kwavers-python`: numpy/numpy-npy + ndarray pinned on top-level (`crates/kwavers/Cargo.toml:46` `=0.16.1`); dev-test path bound through coeus or migration target.
- `kwavers-solvers-python` interaction with `ke-rma-wgpu`: `kwaver-plicity-wgpu` path uses `coeus-wgpu`/`hephaestus-wgpu`/`apollo-wgpu-helpers`; cutover depends on `coeus` GPU adapter reaching wgpu-26 step-up phase.
- `kwavers-pinn`: Coeus extension `scatter` + `eq/lt` for mask/vanishing_point/aggregating, post-CR-4.

---

## Surfacing risks (closeout axioms for next sprint)

1. **DRIFT**: `RITK/Cargo.toml:69` retains `wgpu` feature despite DEP-496-01's DONE narrative. Confirm whether the backlog narrative is canonical or the file literal — reopen DEP-496-01 if file is authoritative.
2. **DEAD-FEATURE**: `ritk-core/src/lib.rs:15-17` cfg gate `feature = "mnemosyne-alloc"` references a feature that does not exist in `ritk-core/Cargo.toml`. Confirm and strip.
3. **NIGHTLY-PINNED TOOLCHAIN**: `kwavers` workspace pins `nightly` rust (`rust-toolchain-pinned nightly` per `crates/kwavers/simiconductor.rs`;; verify on kwavers toolchain). Miri and nightly-feature-only requires per kwavers manual restriction.
4. **TRAIN-PIN**: `let''o_dict`/realbind picked in mid-sprint between `coeus-tensor::Tensor` vs `let''o::Array` for autodiff carrier; coordinate via design note in `let''o/crate` and `coeus/docs/`.
5. **CR-2 dependency-edge cycles**: removing `#[global_allocator]` from library crate `cfd-core`/`ritk-core` requires DI handles in main binaries — verify binaries have zero-handle init paths after tracking.
6. **PEER-WIP COLLISION (session 2026-07-05 22:30 inventory)**: every consumer-batch-owning repo and most provider repos carry **active uncommitted peer WIP** in their working trees, blocking autonomous reclaim. Per-tree state (modified-files count on each branch's working tree):
   - `repos/CFDrs` `codex/cfdrs-atlas-migration`: **772 modified files** (last commit 2026-06-14, but uncommitted WIP — NOT reclaimable per `concurrent_agents` "preserve peer's uncommitted work"). Batch #2 nalgebra→leto closure is peer-active despite apparent branch staleness.
   - `repos/ritk` `main`: **631 modified files** (Batch #3 Burn→Coeus rebind WIP).
   - `repos/apollo` `refactor/apollo-fft-eunomia`: **235 modified files** (Batch #5 / CR-1 ghostcell→melinoe rebind).
   - `repos/kwavers` `codex/kwavers-core-moirai-parallel`: **NEW commits today** (`1dc47028a` + `f36995162`, 2026-07-05 22:16/22:19) — peer is actively landing; migrated `kwavers-math` off nalgebra, added GPU provider seam. Batch #1 (107 residual Rayon sites in solver+physics, 40 files; plus 3 Cargo.toml strip sites) still open but peer-active.
   - `repos/hermes` `perf/compress-buffer-hoist`: 46 modified (peer SIMD-ISA dispatch).
   - `repos/moirai` `refactor/remove-dead-subsystems`: 26 modified.
   - `repos/leto` `codex/leto-cr4-ssot-rebind`: 42 modified (peer fixed-spatial-reconcile; `crates/leto/Cargo.toml:39` `serde_json = { workspace = true }` placeholder breaks `cargo` parse on this workspace).
   - `repos/melinoe` `codex/halo-vecdeque-migration`: 13 modified.
   - `repos/helios` `codex/kwavers-atlas-integration`: 35 modified.
   - `repos/gaia` `refactor/migrate-to-leto-geometry`: 5 modified.
   - `repos/coeus` `main`: 8 modified (melinoe 0.7→0.8 bump peer claim).
   - `repos/eunomia` `main`: 6 modified (acos/asin/atan peer claim).
   - **Clean working trees** (no uncommitted WIP): `repos/themis` (3-day-stale provider-cache crate, peripheral to migration), `repos/hephaestus` (clean; ks5-cholesky-panel active-regular commits), `repos/mnemosyne` (clean; codex/eunomia-local-source active-regular commits).
   - **Net effect**: Atlas-meta's only disjoint-contribution surface during the 2026-07-05 22:30 window is the atlas-meta PM artifacts themselves (this file, `backlog.md`, `checklist.md`, and the ADR `0005` Proposed→Accepted state bump). The CR-class provider-side obstacles (CR-1 apollo, CR-2 global_allocator consolidation, CR-4 — DONE) and the consumer batches #1–#4 all reside inside trees with peer WIP, so the next autonomous consumer-batch sprint must defer until peer WIP commits land or the claim is genuinely released via the documented abandon-protocol.
7. **CR-4 ADR 0005 status**: status **Proposed**, deferred bump-to-Accepted across this session (live implementation closed the rebind per `2b3f820` coeus + `b15439b` leto + `5328de1c` atlas closure). Next atlas-meta docs commit should set status **Accepted** in `docs/adr/0005-eunomia-scalar-ssot.md` and reference the closing commits.

---

## Validator invariants (per criticality level)

- **Tier-A (cross-provider SSOT)**: CR-1, CR-2, CR-4 — landing arrangement coordinated per `atlas/AGENTS.md` documentation-disciple rule + ADR requirement.
- **Tier-B (provider-extension)**: above, listed in provider-own backlogs but track at-meta-level here.
- **Tier-C (consumer-batch)**: Batch #1–#4. Definition-of-Ready at the meta-level; batch itself is the per-repo backlog item.
