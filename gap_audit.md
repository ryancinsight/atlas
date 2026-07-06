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
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `let''o-ops::Scalar` over `eunomia::NumericElement` (NOT `NumericElement + RealField` — `RealField` is float-only and would orphan `coeus_core::Int` for i8/u8/.../u64). Delete duplicated vocabulary (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep backend slice-kernel surface. | **2026-07-05**: Implementation split across 3 commits. T1 evidence landed per repo sub-row: eunomia `57d7789` (SSOT trait doc + Complex<T>/isize/usize impls + private::Sealed + CastFrom<i32>); coeus `2b3f820` (`feat(scalar)!:` — coeus_core traits + 64-file call-site disambiguation across coeus-{autograd, ops, nn, fft, optim, tensor}, doctests, clippy `assign_op_pattern` adjacent fix); leto `b15439b` (`feat(scalar)!:` on `codex/leto-cr4-ssot-rebind` — `pub trait Scalar: NumericElement` rebind; redundant UFCS removed; slice kernels to operator-syntax; `cargo` workspace `0.35.1 -> 0.36.0`). ADR: `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (status **Accepted**).<br>**2026-07-05 (CR-4 closure)**: Atlas-meta submodule pointer for `repos/leto` bumped from `21681967e` to `b15439ba`; atlas-meta PM artifacts (`atlas/{backlog,checklist,gap_audit}.md`) updated to mark CR-4 closed and unblock Batches #2/#3/#4 as Definition-of-Ready. Pre-stage gates on the rebind: 270/270 nextest `-p leto-ops` + 189/189 `-p leto` + 8 doctests + clippy `-D warnings` `--lib --tests` scope; `cargo fmt` clean; `cargo doc --no-deps` warnings peer-scope only (not introduced). Net subtractive consolidation: 196 added / 622 removed across 5 files. RG-verified: zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS in `crates/`. `cargo --workspace` scope on the rebind is blocked by peer-WIP `serde_json = { workspace = true }` in `repos/leto/crates/leto/Cargo.toml:39` without matching workspace dep declaration (peer claim stream; disjoint-scope rule prevents CR-4 from touching).<br>**2026-07-05 (alpha sync)**: `fb83d009 chore(atlas): Align submodule pointers to CR-4 eunomia/coeus/leto commits` aligned `repos/{coeus,eunomia,leto}` to the three landing SHAs (`1ae2f30c8` / `57d778930` / `21681967e`), records the kwavers-foundation GPU-error-boundary rule in `README.md`, pushes the chore to `origin/codex/kwavers-atlas-integration`. Re-verification at `fb83d009`: eunomia 29/29 + coeus `-p coeus-{core,tensor,ops,autograd,nn,sparse,dist,fft,optim,leto}` 758/758 nextest green; clippy `-D warnings` clean on the same set; doctests pass; `cargo doc --no-deps` warn-clean.<br>**2026-07-06 Hephaestus CUDA blocker refresh**: the earlier `coeus-wgpu`/`coeus-cuda` blocker is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. `hephaestus-cuda/src/application/decomposition/eigen.rs` converts `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` before `device.upload(&e_host)`, and `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build plus source inspection; runtime CUDA nextest coverage remains unclaimed. | **CLOSED 2026-07-05**. eunomia `57d7789` ✅, coeus `2b3f820` ✅, leto `b15439b` ✅. Batches #2/#3/#4 now Definition-of-Ready. |

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
- **Closure state**: ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). The pre-closure baseline (Sprint 1.96.126–1.96.137 trait-surface Leto-keyed; `_linear_system` / `_linear_operator` / `_preconditioner` / solver-chain internals / sparse storage / preconditioner internals still nalgebra-keyed) is consumed in this commit. Post-push `cargo tree -p CFDrs | grep nalgebra` returns zero production ops; the 185-line xtask `legacy_surface.allowlist` contracts to zero entries. Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277`.

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
  - T1 evidence: `rg --count-matches 'par_for_each' crates --type rust` re-measured at inner HEAD `aa10a6e76` (2026-07-06). No `use rayon::*` direct imports anywhere in the kwavers tree; the Rayon path enters through `ndarray`'s `rayon` feature flag (`cargo tree -p kwavers-solver | grep rayon` shows `ndarray v0.16.1` → `rayon v1.11.0`).
  - **Total: 84 occurrences across 28 files** (`kwavers-solver` 68 in 21 files; `kwavers-physics` 16 in 7 files).
  - `kwavers-solver` per-directory breakdown (68 sites):
    - `inverse/reconstruction/seismic/rtm/inherent/*` (6 files, 27 sites: `imaging.rs` 14, `wavefield.rs` 5, `laplacian.rs` 4, `mod.rs` 2, `illumination.rs` 1, `propagation.rs` 1).
    - `forward/nonlinear/kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}.rs` (8 files, 17 sites: `solver/rhs.rs` 7, `spectral.rs` 2, `solver/model_impl.rs` 2, `numerical.rs` 2, `workspace.rs` 1, `operator_splitting/mod.rs` 1, `nonlinear.rs` 1, `diffusion.rs` 1).
    - `forward/nonlinear/westervelt_spectral/spectral.rs` (1 file, 2 sites).
    - `forward/elastic/swe/{integration/integrator/mod.rs, stress/divergence.rs}` (2 files, 14 sites: `integrator/mod.rs` 11, `stress/divergence.rs` 3).
    - `forward/pstd/extensions/{elastic.rs, elastic_orchestrator/pml/mod.rs}` (2 files, 5 sites: `elastic.rs` 4, `pml/mod.rs` 1).
    - `multiphysics/fluid_structure/{interface.rs, solver/struct_impl.rs}` (2 files, 3 sites: `interface.rs` 1, `solver/struct_impl.rs` 2).
  - `kwavers-physics` per-directory breakdown (16 sites):
    - `acoustics/conservation/heat.rs` (2 sites).
    - `acoustics/mechanics/acoustic_wave/nonlinear/{numerical_methods/{spectral/mod.rs (7), nonlinear_term.rs (1)}, wave_model.rs (1)}` (3 files, 9 sites).
    - `acoustics/mechanics/cavitation/damage/model.rs` (1 site).
    - `acoustics/therapy/sonogenetics/{arf_field.rs (2), channels/gating.rs (2)}` (2 files, 4 sites).
  - Per-directory scan tallies add to 84 (68+16), matching the global ripgrep total. The peer migration in `ea7e09948 refactor(kwavers-physics)!: Route Rayon dispatch through moirai-parallel` (2026-07-06 10:21) drained sub-families elsewhere (`thermal`, `sonoluminescence/{blackbody,bremsstrahlung,cherenkov}`, `transducer`, `RTM`, `Monte Carlo`, `bubble interactions`, `field_surrogate`, `chemistry/{reaction-kinetics,ros-plasma}`, `optics/polarization`) but the `acoustics/{conservation, mechanics/{acoustic_wave,cavitation}, therapy/sonogenetics}` families remain on the pre-migration `Zip::*().par_for_each()` chain at this HEAD.
  - Note: the per-family header site-count breakdown from the prior record (62 solver + 24 physics = 86) is the pre-`ea7e09948` snapshot; the peer migration drained 86 → 84 (-2 sites net).
- **Residual `ndarray = { features = ["rayon", "serde"] }` manifests** (T1 grep at HEAD `aa10a6e76`):
  - `crates/kwavers-solver/Cargo.toml:24` ⚠ OPEN — manifest retains `ndarray = { version = "0.16", features = ["rayon", "serde"] }`. Until this feature is stripped, `cargo tree -p kwavers-solver | grep rayon` returns `rayon v1.11.0`/`rayon-core v1.13.0`. The Batch #1 closure condition (zero-Rayon dep tree) is unmet at this HEAD.
  - `crates/kwavers-physics/Cargo.toml:20` ⚠ OPEN — same manifest form. Same Batch #1 closure condition unmet for `kwavers-physics`.
  - `kwavers-solver/src/inverse/same_aperture/operator/linear_op.rs` (6 sites) — already routes through `moirai_parallel::ParallelSliceMut`; not a migration target (preserved for downstream-batch completeness).
- **Residual `burn`** (T1 re-verified at inner HEAD `400c32624` 2026-07-06 post peer commit `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" on `codex/kwavers-core-moirai-parallel`):
  - `crates/kwavers/Cargo.toml:138` non-optional dev-dep `burn = { version = "0.19", default-features = false, features = ["std", "ndarray", "autodiff"] }` (no GPU features).
  - `crates/kwavers-solver/Cargo.toml:53` optional dep `burn = { version = "0.19", default-features = false, features = ["std", "train", "ndarray", "autodiff"], optional = true }`, gated under the `pinn` feature (per `Cargo.toml:62-70`). The comment at L48-49 reads "After coeus-based PINN replacement is complete this dep will be removed entirely." — keeps Burn transitively live whenever the `pinn` feature is on.
  - `cargo tree -p kwavers-solver | grep burn` is **non-empty** at this HEAD: pulls `burn v0.19.0`, `burn-core`, `burn-autodiff`, `burn-ndarray`, `burn-nn`, `burn-optim`, `burn-tensor`, `burn-ir`, `burn-derive`, `burn-common`, `burn-std`, `burn-backend`, plus a stray `burn-std v0.20.1` / `burn-tensor v0.20.1` / `burn-backend v0.20.1` (version-mismatch). The Batch #4 completion condition (`cargo tree -p kwavers-solver | grep burn` returns zero) is **unmet**.
  - **`burn::` line-hits total**: 315 across 144 files (`rg ' burn::' crates --type rust -c` at `400c32624`). 260 in `kwavers-solver`, 55 across top-level `kwavers` benches/examples/tests.
  - **`use burn` import-sites total**: 222 across 139 files (`rg 'use burn' crates --type rust -c`).
  - **PINN-subtree residual (260 hits / 126 files)**: at `crates/kwavers-solver/src/inverse/pinn/**`. The peer's `400c32624` commit migrated only the `ml/burn_wave_equation_1d/` family; the rest of the PINN surface remains burn-routed via the `burn_compat as compat` alias module at `crates/kwavers-solver/src/burn.rs` (see surfacing risk #8). Unmigrated families under `pinn/ml/` include `burn_wave_equation_3d/{wavespeed,tests}` (16 hits), `cavitation_coupled`, `meta_learning/{gradient,learner,optimizer}`, `sonoluminescence_coupled/{domain,tests}`, `uncertainty_quantification/{conformal,bayesian}`, `transfer_learning/{learner,evaluation}`, `adaptive_sampling`, `quantization`, `universal_solver/{types,training,solver,constructors,accessors}`, `acoustic_wave`, `field_surrogate`, `physics.rs`, `mod.rs`. Plus `elastic_2d/{training/optimizer,training/loop,tests/gradient_validation}`.
  - **Top-level `kwavers` (55 hits / 17 files)**: `benches/{adaptive_sampling_opt, pinn_elastic_2d_training, pinn_vs_fdtd_benchmark}.rs` (3 files), `examples/{electromagnetic_simulation, field_surrogate_demo, multiphysics_sonoluminescence, pinn_2d_heterogeneous, pinn_2d_wave_equation, pinn_training_convergence, seismic_imaging_demo, seismic_imaging_3d_demo, skull_ct_phase_correction, transfer_learning_pinn}.rs` (10 files), `tests/{electromagnetic_validation, pinn_bc_validation, pinn_elastic_validation, pinn_ic_validation}.rs` (4 files).
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
  - ~~`RITK/Cargo.toml:69` retained `wgpu` in the workspace Burn feature list despite `DEP-496-01` being marked done.~~ **RETRACTED 2026-07-06**: `repos/ritk/Cargo.toml` now uses `features = ["std", "ndarray", "autodiff"]`. Verification: `rustup run nightly cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, and `-i burn-rocm` each reported no matching package; `rustup run nightly cargo metadata --locked --format-version 1` completed successfully. Evidence tier: dependency graph + locked metadata.
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
- **Closure state**: Sprint 495 (native writers for 9 formats — `MIGH, META, MINC, TIFF, JPEG, NRRD, Analyze, NIfTI, PNG`) merged into `ritk-io::ImageWriter<Image<f32,B,3>>` with Burn + native façade; `DEP-496-01` (default Burn features) is now file-literal consistent: `repos/ritk/Cargo.toml` removes Burn's `wgpu` feature and the workspace dependency graph selects no Burn GPU backend package.
- **2026-07-06 — Sub-batch #1 of Batch #3 closed per ADR 0012**: inner RITK atomic commit adds Atlas-typed parallel trait surface (`TransformAtlas<T: Scalar, B: ComputeBackend, D>`, `InterpolatorAtlas<T: Scalar, B: ComputeBackend>`, `ResampleableAtlas<T: Scalar, B: ComputeBackend, D>`) + `pub use native::Image as AtlasImage;` re-export + 2-crate Cargo.toml dep additions (`coeus-core` + `coeus-tensor` referenced as `{ workspace = true }`). **Purely additive**: no Burn-keyed surface mutation; `xtask/burn_surface.allowlist` unchanged; Burn GPU-default drift (closed by inner commit `65a1a0fd`) preserved. Sub-batches #2-#6 (`RITK-trait-deprecate`, `RITK-crate-migrate`, `RITK-spatial-rebind`, `RITK-burn-remove`, `RITK-xtask-ci`) reserved per `atlas/docs/adr/0012-ritk-burn-trait-rebind.md` §Decision.

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

1. ~~**DRIFT**: `RITK/Cargo.toml:69` retains `wgpu` feature despite DEP-496-01's DONE narrative. Confirm whether the backlog narrative is canonical or the file literal — reopen DEP-496-01 if file is authoritative.~~ **CLOSED 2026-07-06**: inner RITK commit `65a1a0fd` corrected the file literal to remove `wgpu`, refreshed `xtask/burn_surface.allowlist`, and verified Burn GPU backend packages are absent from the RITK workspace dependency tree.
2. ~~**DEAD-FEATURE**: `ritk-core/src/lib.rs:15-17` cfg gate `feature = "mnemosyne-alloc"` references a feature that does not exist in `ritk-core/Cargo.toml`. Confirm and strip.~~ **RETRACTED 2026-07-06** (T1 re-verification): `ritk-core/Cargo.toml:8` declares `mnemosyne-alloc = ["dep:mnemosyne"]` and `Cargo.toml:7` lists it in `default = ["mnemosyne-alloc"]`; `src/lib.rs:15-17` cfg is consistent. The feature exists; the prior claim was a stale-memory misread. No action.
3. ~~**NIGHTLY-PINNED TOOLCHAIN**: `kwavers` workspace pins `nightly` rust (`rust-toolchain-pinned nightly` per `crates/kwavers/simiconductor.rs`;; verify on kwavers toolchain).~~ **RETRACTED 2026-07-06** (T1 re-verification): no `rust-toolchain*` file exists at `repos/kwavers/` (workspace root) or in any first-level subdirectory; the cited `crates/kwavers/simiconductor.rs` path is fictitious. The workspace does not pin nightly at the manifest level. Any nightly-feature usage must be re-verified at the per-crate site, not at the workspace toolchain pin level.
4. **TRAIN-PIN**: `let''o_dict`/realbind picked in mid-sprint between `coeus-tensor::Tensor` vs `let''o::Array` for autodiff carrier; coordinate via design note in `let''o/crate` and `coeus/docs/`.
5. **CR-2 dependency-edge cycles**: removing `#[global_allocator]` from library crate `cfd-core`/`ritk-core` requires DI handles in main binaries — verify binaries have zero-handle init paths after tracking.
6. **PEER-WIP COLLISION (refreshed 2026-07-06 inventory)**: every consumer-batch-owning repo and most provider repos carry **active uncommitted peer WIP** in their working trees, blocking autonomous reclaim. Per-tree state (modified-files count on each branch's working tree):
   - `repos/CFDrs` `codex/cfdrs-atlas-migration`: **79 modified/untracked inner paths on 2026-07-06 recheck** after the `d58d1fe3` Batch #2 closure push. Batch #2 (CFDrs nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix`) remains **CLOSED** at `d58d1fe3`, but the current dirty tree is live inner-repo WIP and is not reclaimable from Atlas-meta. Do not retract the CFDrs §C row until the inner tree is clean again or a new CFDrs commit lands.
   - `repos/ritk` `main`: **0 modified files** after inner commits `65a1a0fd` and `d7a940b5`; `65a1a0fd` removed Burn's stale `wgpu` feature from the workspace dependency, refreshed `xtask/burn_surface.allowlist`, and synced RITK PM evidence, while `d7a940b5` added the Batch #3 sub-batch #1 Atlas-typed parallel trait surface. Atlas-parent commit `61931faf` advanced the pointer.
   - `repos/apollo` `refactor/apollo-fft-eunomia`: **235 modified files** (Batch #5 / CR-1 ghostcell→melinoe rebind).
   - `repos/kwavers` `codex/kwavers-core-moirai-parallel`: **27 modified/untracked inner paths on 2026-07-06 recheck** at `400c32624` — peer is actively landing; landed `1dc47028a` (`kwavers-math` nalgebra → eunomia/leto/moirai-parallel), `f36995162` (kwavers-gpu/solver Hephaestus seam), and most recently `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" — a Batch #4 vertical slice, **not closure** (315 `burn::` hits / 144 files remain across the kwavers tree; see L91-103 residual inventory). Branch is `[ahead 12]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git status -sb` (12 unpushed peer commits as of 2026-07-06). Batch #1 (Rayon→Moirai residual) and Batch #4 (PINN Burn→Coeus) both remain OPEN but peer-active; Atlas-meta defers to peer.
   - `repos/hermes` `perf/compress-buffer-hoist`: 46 modified (peer SIMD-ISA dispatch).
   - `repos/moirai` `refactor/remove-dead-subsystems`: 26 modified.
   - `repos/leto` `codex/leto-cr4-ssot-rebind`: 14 modified (peer fixed-spatial-reconcile; disjoint from Atlas-meta).
   - `repos/melinoe` `codex/halo-vecdeque-migration`: 13 modified.
   - `repos/helios` `codex/kwavers-atlas-integration`: **0 dirty direct paths** after `c5f2a84e`; H-061/H-062 removed the unused direct `num-traits` edge and aggregate dicom-rs `ndarray` feature edge, added the local Melinoe patch required by patched Gaia, and synced Helios PM evidence.
   - `repos/gaia` `refactor/migrate-to-leto-geometry`: 5 modified, including CSG source and benchmark files; no PM-only split claim remains.
   - `repos/coeus` `main`: 19 modified, including dtype/tensor/Python/docs files; no PM-only split claim remains.
   - `repos/eunomia` `main`: 7 modified (acos/asin/atan peer claim).
   - **Clean working trees** (no uncommitted WIP): `repos/helios` (direct dependency slice closed by `c5f2a84e`), `repos/ritk` (pointer advanced to `d7a940b5` by `61931faf`), `repos/themis` (peripheral provider-cache crate, no migration surface), `repos/hephaestus` (clean inner tree; ks5-cholesky-panel active-regular commits), and `repos/mnemosyne` (clean inner tree; codex/eunomia-local-source active-regular commits). These are no longer counted as submodule-internal dirty rows in `backlog.md`; parent gitlink deltas, if present, are Atlas-parent pointer work rather than inner-submodule WIP.
   - **Net effect**: Atlas-meta's only disjoint-contribution surface during this 2026-07-06 refresh is the atlas-meta PM artifacts themselves. The CR-class provider-side obstacles and the consumer batches #1–#4 all reside inside trees with peer WIP, so the next autonomous consumer-batch sprint must defer until peer WIP commits land or the claim is genuinely released via the documented abandon-protocol.
7. **CR-4 ADR 0005 status**: status **Proposed**, deferred bump-to-Accepted across this session (live implementation closed the rebind per `2b3f820` coeus + `b15439b` leto + `5328de1c` atlas closure). **CLOSED 2026-07-05** by atlas-meta commit `b66ec228` — `docs/adr/0005-eunomia-scalar-ssot.md` status line now reads "Accepted — implementation closed 2026-07-05" citing all four closing commits (`57d7789` eunomia + `2b3f820` coeus + `b15439b` leto + `5328de1c` atlas closure). No further action.
8. **BATCH #4 SLICE-INTEGRITY (kwavers, surfaced 2026-07-06)**: peer commit `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" claims in its body: "rewritten directly against coeus rather than via a burn-shaped compat facade". T1 verification at the commit's own HEAD contradicts this claim: `crates/kwavers-solver/src/burn.rs` (112 lines) IS a burn-shaped compat facade, with module header docstring stating verbatim "Every `use burn::…` in the PINN submodules resolves here — zero changes to those files are required." and "Migration note: As each PINN submodule is fully ported to native coeus API the imports from this module are replaced with direct coeus imports and the module declaration in `lib.rs` is removed." The facade re-exports `burn_compat::{tensor, module, nn, optim, backend, config, prelude, record}` aliased to shadow the removed `burn` crate name. Per `atlas/AGENTS.md` `integrity` §Compatibility soup HARD rule and §"distributed shim, equally prohibited" — `pub use old as new`, `#[deprecated]` re-export, forwarding wrapper, module alias, or adapter layer kept to avoid updating callers" are all prohibited. The facade violates the first (module alias, forwarding wrapper). The companion coeus-side `Module::load_parameters` extension called out in the peer's commit message as having been added in a companion coeus commit is a legitimate upstream-first implementation per `architecture_scoping` upstream-ownership (the capability gap was filled upstream in coeus), EXCEPT the API shape was driven by the burn facade's needs (per the commit body, motivated by replacing Burn's `ModuleMapper` visitor pattern) — i.e., the extension risks recreating the burn-shaped API topology in coeus. `integrity` §"Converted code is rewritten natively in the target API's idioms — never a mechanical transliteration that recreates the old API's shape through local helpers, extension traits, or conversion chains" is an `integrity` HARD-tier prohibition specifically on the *distributed-shim pattern* across the consumer-provider boundary.
   - **Skew**: peer commit message framing ≠ actual code shape at the commit's own HEAD. Surface for peer self-reconciliation: either (a) the `400c32624` commit body is corrected to retract the "no compat facade" claim, AND the Batch #4 closure plan is restated as multi-slice (Slice 1 = `burn_wave_equation_1d` ✅ landed, Slice 2..N = migrate remaining 60+ PINN submodules + 17 top-level files + strip `burn` from `kwavers-solver/Cargo.toml:53` and `kwavers/Cargo.toml:138` + delete `crates/kwavers-solver/src/burn.rs` and `burn_compat` module); or (b) `burn.rs` is deleted now, with all remaining `use burn::…` callsites re-pointed at native `coeus::{core,nn,optim,tensor,autograd,record}` imports per the canonical burn→coeus trait rewire (checklist Batch #4 §B), and the coeus `Module::load_parameters` API is reviewed for idiomatic coeus shape vs burn-shape leakage.
   - Atlas-meta scope: surface-and-record only. The kwavers source tree is peer-claimed (`codex/kwavers-core-moirai-parallel`, `[ahead 12]`, peer ACTIVE). Resolution per `concurrent_agents` disjoint-scope rule is peer-owned. No Atlas-meta pointer advance for `repos/kwavers` until this slice-closure pattern is reconciled.

---

## Validator invariants (per criticality level)

- **Tier-A (cross-provider SSOT)**: CR-1, CR-2, CR-4 — landing arrangement coordinated per `atlas/AGENTS.md` documentation-disciple rule + ADR requirement.
- **Tier-B (provider-extension)**: above, listed in provider-own backlogs but track at-meta-level here.
- **Tier-C (consumer-batch)**: Batch #1–#4. Definition-of-Ready at the meta-level; batch itself is the per-repo backlog item.
