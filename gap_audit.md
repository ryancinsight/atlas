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
| **CR-1** | `[arch]` | Delete `apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell`. | Source: `apollo/crates/apollo-ghostcell/src/lib.rs`; `melinoe/src/lib.rs:18-24,65-115,233` (`pub use cell::{MelinoeCell,MelinoeMut,MelinoeRef}`); `atlas/docs/audit/2026-07-02-cross-repo-integration-audit.md`:L71-75 ([arch] CR-1 citation). Closeout evidence 2026-07-07: Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; stale Apollo-owned GhostCell plan removed; `repos/moirai/Cargo.toml` aligned to `melinoe = 0.8.0`; `cargo metadata --locked --no-deps --format-version 1` green in `repos/apollo`; focused nextest `-p apollo-validation melinoe` 2/2 green and `-p apollo-sft -p apollo-radon` 43/43 green. | **CLOSED 2026-07-07**. Evidence tier: source/static dependency graph + compile/build + value-semantic nextest. Full Apollo workspace, clippy, and Melinoe Miri not rerun in this closeout. |
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
- **Residual `burn`** (T1 re-verified 2026-07-07 against the dirty inner `repos/kwavers` working tree after the neutral-name Burn cleanup continuation):
  - Requested migration scope is clean: `rg -n "Burn|burn_|\bburn\b|burn-|CoeusPINN|coeus_wave" crates/kwavers-solver/src/inverse/pinn crates/kwavers/tests crates/kwavers/benches crates/kwavers/examples crates/kwavers/Cargo.toml Cargo.toml` returns zero hits.
  - Kwavers manifests are clean: `rg -n "\bburn\b|burn-" -g Cargo.toml .` returns zero hits under `repos/kwavers`.
  - The `crates/kwavers-solver/src/burn.rs` facade is absent and `rg -n "burn_compat|crate::burn|kwavers_solver::burn|pub mod burn|mod burn"` finds no `burn_compat` alias path. The 1-D, 2-D, and 3-D PINN module paths are now framework-neutral (`wave_equation_1d`, `wave_equation_2d`, `wave_equation_3d`), and the beamforming adapter path is `pinn_adapter`.
  - Whole-repo literal residual is **366 lines across 22 files**, concentrated in `Cargo.lock`, `xtask/legacy_surface.allowlist`, and historical PM/audit prose rather than the requested PINN/top-level source scope. Scoped PINN/top-level source residual is **0 lines across 0 files**.
  - `cargo tree -p kwavers-solver --features pinn -i burn` remains non-empty through RITK provider crates (`ritk-image`, `ritk-interpolation`, `ritk-spatial`, `ritk-wgpu-compat`, and downstream `ritk-*` paths), so full Burn graph closure is still blocked outside the kwavers manifest/source surface.
  - Verification evidence: `rustup run nightly cargo fmt -p kwavers-solver -p kwavers --check` passed; `rustup run nightly cargo check -p kwavers-solver --features pinn` passed; `rustup run nightly cargo check -p kwavers --features pinn --tests --benches --examples` passed with pre-existing warning noise in `kwavers-math`, `pinn_elastic_validation`, and `phase6_persistent_adam_benchmarks`; `rustup run nightly cargo nextest run -p kwavers --features pinn --test pinn_bc_validation --test pinn_ic_validation --status-level fail --no-fail-fast` compiled and ran 16 tests: 12 passed, 4 failed on legacy 3-D PINN loss thresholds (`test_ic_loss_zero_field`, `test_ic_combined_loss_decreases`, `test_bc_loss_decreases_with_training`, `test_dirichlet_bc_zero_boundary`). These are retained as validation residuals; assertions were not weakened.
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
- **2026-07-06 — Sub-batch #2 of Batch #3 closed per ADR 0012**: inner RITK atomic commit (docstring-only) appends soft deprecation callout to the four Burn-keyed foundational surfaces `Transform<B, D>`, `Resampleable<B, D>`, `Interpolator<B>`, and `Image<B, D>`. **Docstring-only**: no `#[deprecated]` attribute (which would emit ≥671 `#[warn(deprecated)]` warnings across `xtask/burn_surface.allowlist` source files); zero public Burn-keyed surface symbol removal/narrowing/renaming; zero `Cargo.toml` mutation; `xtask/burn_surface.allowlist` unchanged (auto-generated, signature-keyed). Forward-pointing intra-doc-links `[`TransformAtlas`]` / `[`ResampleableAtlas`]` / `[`InterpolatorAtlas`]` / `[`AtlasImage`]` resolve to the Atlas-side parallels added in sub-batch #1. Compile-gate: `cargo check -p ritk-core -p ritk-image` passes; `cargo doc -p ritk-core -p ritk-image --no-deps` intra-doc-link resolution passes; `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each zero (Burn GPU-default state preserved from `65a1a0fd`). Sub-batches #3-#6 (`RITK-crate-migrate`, `RITK-spatial-rebind`, `RITK-burn-remove`, `RITK-xtask-ci`) reserved per ADR 0012 §Decision.
- **2026-07-06 — Sub-batch #3 of Batch #3 OPENED per ADR 0012**: per-crate Atlas-typed migrators, 7-per-crate sub-atomic increment queue. Each per-crate commit lands as its own subtractive-by-conversion atomic commit on `repos/ritk` (8-file pattern: 1 test source port + 1 atlas-meta inner PM sync + tag-chain references + atlas-meta chore commit on atlas-meta). Per-crate order: `ritk-filter` (`morphology/tests_binary_erode.rs`) → `ritk-registration` (`metric/histogram/parzen/tests/cache_property_tests.rs`) → `ritk-segmentation` (`morphology/binary_erosion/tests.rs`) → `ritk-model` (`ssmmorph/encoder/tests.rs`) → `ritk-statistics` (`tests_image_statistics.rs`) → `ritk-{io,interpolation,transform}` (`format/dicom/color/tests.rs` + `interpolation/tests_trilinear.rs` + `transform/affine/tests_affine.rs`) → `ritk-{python,cli,snap}` (one CLI command test + one snapshot handler test + one python binding test). Each per-crate commit ports one specific test from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`, drops 1 source-row from `xtask/burn_surface.allowlist`, preserves every public Burn-keyed signature intact. Sub-batch #5 remains the only commit authorised to delete/rename `[dependencies]` lines; sub-batch #6 owns the allowlist refresh ritual. The `ritk/atlas-migration-push/batch3` annotated tag annotation body will enumerate the 7 per-crate SHAs per ADR 0010 §Decision §Per-batch name pattern. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 (amended 2026-07-06) + §atomic-boundary discipline §1.

### Cross-utility

- `tokio`: zero hits in any of CFDrs, kwavers, ritk — fully migrated.
- `rayon`: zero direct hits; transitive only via ndarray `rayon` feature (above).
- `rustfft`: zero hits — `apollo-fft` consumed instead.
- `packed_simd`: zero hits.

---

## SSOT enforcement surface (per-repo migration-audit gate)

> The `.github/workflows/legacy-migration-audit.yml` gate enforces a per-repo **single SSOT enforcement surface** so every Atlas-provider migration push stays inside the allowlist contract. The gate is wired across 6 repos under the `kwavers-Atlas-migration-push` ceremony anchor: 3 original (cfdrs / ritk / kwavers), 3 added 2026-07-07 (apollo / gaia / helios).

| Repo | Workflow file | xtask subcommand | Allowlist path / state | Branch triggers | Commit anchors |
|------|---------------|------------------|------------------------|-----------------|----------------|
| **cfdrs** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (185 lines) | `[main, refactor/**, codex/**]` | per-submodule `d58d1fe3` Batch #2 closure (cfdrs `codex/cfdrs-atlas-migration`) |
| **ritk** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- burn-migration-audit` | `xtask/burn_surface.allowlist` (~764 source-rows × 27 crates) | `[main, refactor/**, codex/**]` | per-submodule `8f8360ff` RITK pointer advance (post-Batch #3 sub-batch #3.f closeout) |
| **kwavers** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (84 `par_for_each` + nalgebra + ndarray + burn residual inventory) | `[main, refactor/**, codex/**]` | per-submodule peer-active (`codex/kwavers-core-moirai-parallel` Batch #1 + Batch #4 reservations per ADR 0010) |
| **apollo** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- provider-audit` (native; hard-fails on forbidden ndarray references via `concat!("nd", "array")`) | (no `.allowlist` file — dynamic forbidden-pattern check + provider-usage matrix; consumes `xtask/src/provider_audit.rs` directly) | `[main, codex/**]`¹ | per-submodule `9df5294e + 2940d66 + cd05eac` (workflow + branch-narrowing + workflow-YAML fix) |
| **gaia** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (header-only baseline; 0 legacy surface items found by T1 grep over `nalgebra/ndarray/burn/tokio/rayon`) | `[main, refactor/**, codex/**]` | per-submodule `6a7b7d0 + d47d8a6` (scaffold + phantom-dep drop) |
| **helios** | `.github/workflows/legacy-migration-audit.yml` | `cargo run -p xtask -- legacy-migration-audit` | `xtask/legacy_surface.allowlist` (header-only baseline; 0 legacy surface items found by T1 grep) | `[main, refactor/**, codex/**]` | per-submodule `8a6637b + 065bf39` (scaffold + phantom-dep drop) |

¹ Excludes `refactor/**` to defer day-1 verdict damage on Apollo's in-flight `refactor/apollo-fft-eunomia` migration (~234 dirty files mid-migration); expand to `refactor/**` once that migration lands, matching the cfdrs/ritk/kwavers shape.

### Recently closed (2026-07-07)

- **Apollo / Gaia / Helios migration-audit gate lift** — landed under the `kwavers-Atlas-migration-push` ceremony anchor on 2026-07-07. Apollo's existing xtask exposes `provider-audit` (a forbidden-crater check + provider-usage matrix) and was added workflow-only; gaia and helios received fresh `xtask` workspace members (mirrored verbatim from `cfdrs/xtask` per the canonical pattern: `Cargo.toml` + clap-based `src/main.rs` + `src/migration_audit.rs` BTreeSet-diff scanner + header-only `xtask/legacy_surface.allowlist` baseline). Gate file path `.github/workflows/legacy-migration-audit.yml` is uniform across all 6 repos for ecosystem discoverability; the subcommand invoked differs only on apollo (its native `provider-audit` shape was preserved). Evidence tier: structural on-disk confirmation (file presence + workflow YAML schema-correct `on:` + `permissions:` + `concurrency:` + `jobs:` blocks per repo). First CI-run verdict target: day-1 exit 0 on the active inner branch tip of each repo.
- **Apollo workflow branch-list narrowing** — restricted triggers to `[main, codex/**]` (not `refactor/**`) so Apollo's active `refactor/apollo-fft-eunomia` branch (~234 dirty files mid-migration) does not flip the gate red on day-1. Once that migration lands, expand to `refactor/**` per the cfdrs/ritk/kwavers shape. Already-closed chore commit `2940d66` documented the narrowing rationale.
- **Phantom-dep drop on gaia + helios xtask** — the first-pass scaffold mirrored `kwavers/xtask/Cargo.toml` (with `walkdir 2.3` / `regex 1.8` / `chrono 0.4`), but `migration_audit.rs` only imports `anyhow::{bail, Context, Result}` + `std::{collections::BTreeSet, fs, path::{Path, PathBuf}}`. None of `walkdir`/`regex`/`chrono` are referenced from `src/`, so they're phantom deps that `cargo-deny` would flag. Chore commits `d47d8a6` (gaia) + `065bf39` (helios) replaced the kwavers-shaped dep set with the cfdrs-mirror set (anyhow + clap + serde + serde_json + toml).
- **Apollo workflow YAML fix commit** — chore commit `cd05eac` replaced a botched first-pass str_replace's malformed `pull_request:branches:` collapsed YAML with the corrected shape. GitHub Actions would have refused to parse the first-pass shape on first invocation (the `pull_request:` key would have been read as a literal `pull_request:branches` key without the per-mapping interpretation). First-pass `2940d66` retained the on-disk correction context; fix-commit `cd05eac` is the final, gate-runnable shape.

### Gate-internal mechanics (cfdrs / ritk / kwavers / gaia / helios canonical shape)

Per `cfdrs/xtask/src/{main.rs, migration_audit.rs}` (the canonical pattern the new scaffolds mirror):
- **`src/main.rs`**: `clap` derive-`Parser` binary with `enum Command { LegacyMigrationAudit, RefreshLegacyAllowlist }` (or `BurnMigrationAudit` / `RefreshBurnAllowlist` for ritk); each variant calls into `migration_audit` module functions.
- **`src/migration_audit.rs`**: walks `Cargo.toml` / `**/*.rs` files in the workspace root, computes `BTreeSet<Cow<str>>` of legacy-source tokens (e.g. `nalgebra::`, `ndarray::`, `burn::tensor::Backend`, `tokio::`, `rayon::`, `Zip::par_for_each`), compares against the per-repo `xtask/{legacy|burn}_surface.allowlist` set, and `bail!` with a non-zero exit code on any contained-but-not-allowlisted hit (or any allowlisted-but-now-absent row). Refresh path writes the allowlist file with the current surface, gated to the SSOT marker header.
- **`Cargo.toml` workspace edge**: each per-repo `xtask/Cargo.toml` declares `anyhow` + `clap` (v4.0–4.5 derive) + `serde` (derive) + `serde_json` + `toml` (0.8). `walkdir` / `regex` / `chrono` were dropped as phantom deps per the 2026-07-07 gaia/helios chore commits.
- **Apollo's asymmetric gate**: `xtask/src/provider_audit.rs` is structurally similar but exempts the `.allowlist` contract — it dynamically computes the forbidden-reference set (the only entry is `ndarray`, encoded via `concat!("nd", "array")` to bypass any in-file crate-name matching) and the provider-usage matrix (a structured `Vec<ProviderUsageRow>` enumerating each provider crate name + dependency direction + dependency-version constraint). Source-level nextest coverage at apollo HEAD `f1ddf7a` (per `repos/apollo/xtask/src/provider_audit.rs`).

### Cross-repo invariants

1. **File uniformity**: `.github/workflows/legacy-migration-audit.yml` on all 6 repos — centralized CI/CD query-ability + ecosystem discoverability.
2. **Subcommand uniformity**: `cargo run -p xtask -- legacy-migration-audit` is the canonical invocation; `burn-migration-audit` (ritk) and `provider-audit` (apollo) are explicit divergence points documented in the table above.
3. **Allowlist naming**: cfdrs/gaia/helios use `xtask/legacy_surface.allowlist`; ritk uses `xtask/burn_surface.allowlist`; apollo uses NO allowlist file (dynamic check).
4. **Buffering shape**: the first-pass scaffolds (gaia/helios) initially included `walkdir`/`regex`/`chrono` from the kwavers xtask pattern but the `migration_audit.rs` body uses only `std::fs::read_dir` recursively + `serde` for allowlist-parse — phantom deps were stripped to the cfdrs-shape (anyhow + clap + serde + serde_json + toml) per the 2026-07-07 chore commits.

### Limitations and forward-looking hooks

- Apollo's `xtask` exposes only `provider-audit` (no `legacy-migration-audit` / `refresh-legacy-allowlist` pair); a future `[minor]` Apollo-side chore may add the symmetric pair if phobos asks for the cfdrs/kwavers/ritk/helios-shape parity.
- The `target/xtask-*.log` upload-artifact path remains on the **gaia + helios** workflows; Apollo's earlier-fix dropped it. A forward-looking chore commit may drop it on the other two for symmetry.
- `Cargo.lock` cache key uses `'Cargo.lock'` non-recursive on all 3 new workflows (already tight per the prior ceremony's micro-nit convention).
- First automated `cargo run -p xtask -- legacy-migration-audit` validation is deferred to CI day-1 (out-of-session for Atlas-meta); the per-repo workflow file presence + YAML schema-correctness is the Atlas-meta-side confirmation tier.

---

## In-flight claims (transient atlas-meta carryover)

Per `D:/atlas/backlog.md` `## In-flight claims (per concurrent_agents)` precedent, transient atlas-meta carryovers that resolve via a separate atomic chore (peer-claim resolution OR next-session followup) are surfaced here rather than in the persistent `Limitations and forward-looking hooks` inventory above. Items here resolve away once the named chore commits — they are not forward-looking TODOs.

- **[carryover] `repos/ritk` atom-pointer advance** (this turn's transient artifact) — D:/atlas working-tree `repos/ritk` gitlink advance `7aaae9eb2df00d77829c7ce6d1f451aea3051fb9` → `6710f29ad7837f0ea8bb89abaafa025b0c063aa0` (19 commits ahead) was excluded from this turn's docs-only chore commit chain (`cce3c64` = SSOT enforcement surface section + `a02d6d1` = numeric-superscript rendering fix) per disjoint-scope (ADR 0011 §Leg 2). Per ADR 0010 §Per-batch ceremony convention, this should land as a separate atomic chore `chore(atlas): Advance ritk submodule pointer to 6710f29ad7837f0ea8bb89abaafa025b0c063aa0` — or, if peer-claimed / WIP per `concurrent_agents`, surface as a working-tree dirty row in `atlas/backlog.md` §In-flight claims.

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
- `helios` DICOM real-input path: **closed 2026-07-06** for production DICOM ownership. RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}`; Helios H-061 now consumes RITK for parse, typed image attributes, transfer-syntax lookup, and pixel decode. Direct `dicom` remains only as a Helios dev-dependency for synthetic Part 10 fixture generation. Remaining audit H-063 covers `helios-imaging`: generic medical-image I/O/registration/toolkit operations move upstream to RITK first, while radiation-domain MVCT projection/reconstruction kernels stay in Helios.

---

## Surfacing risks (closeout axioms for next sprint)

1. ~~**DRIFT**: `RITK/Cargo.toml:69` retains `wgpu` feature despite DEP-496-01's DONE narrative. Confirm whether the backlog narrative is canonical or the file literal — reopen DEP-496-01 if file is authoritative.~~ **CLOSED 2026-07-06**: inner RITK commit `65a1a0fd` corrected the file literal to remove `wgpu`, refreshed `xtask/burn_surface.allowlist`, and verified Burn GPU backend packages are absent from the RITK workspace dependency tree.
2. ~~**DEAD-FEATURE**: `ritk-core/src/lib.rs:15-17` cfg gate `feature = "mnemosyne-alloc"` references a feature that does not exist in `ritk-core/Cargo.toml`. Confirm and strip.~~ **RETRACTED 2026-07-06** (T1 re-verification): `ritk-core/Cargo.toml:8` declares `mnemosyne-alloc = ["dep:mnemosyne"]` and `Cargo.toml:7` lists it in `default = ["mnemosyne-alloc"]`; `src/lib.rs:15-17` cfg is consistent. The feature exists; the prior claim was a stale-memory misread. No action.
3. ~~**NIGHTLY-PINNED TOOLCHAIN**: `kwavers` workspace pins `nightly` rust (`rust-toolchain-pinned nightly` per `crates/kwavers/simiconductor.rs`;; verify on kwavers toolchain).~~ **RETRACTED 2026-07-06** (T1 re-verification): no `rust-toolchain*` file exists at `repos/kwavers/` (workspace root) or in any first-level subdirectory; the cited `crates/kwavers/simiconductor.rs` path is fictitious. The workspace does not pin nightly at the manifest level. Any nightly-feature usage must be re-verified at the per-crate site, not at the workspace toolchain pin level.
4. **TRAIN-PIN**: `let''o_dict`/realbind picked in mid-sprint between `coeus-tensor::Tensor` vs `let''o::Array` for autodiff carrier; coordinate via design note in `let''o/crate` and `coeus/docs/`.
5. **CR-2 dependency-edge cycles**: removing `#[global_allocator]` from library crate `cfd-core`/`ritk-core` requires DI handles in main binaries — verify binaries have zero-handle init paths after tracking.
6. **PEER-WIP COLLISION (refreshed 2026-07-06 inventory)**: every consumer-batch-owning repo and most provider repos carry **active uncommitted peer WIP** in their working trees, blocking autonomous reclaim. Per-tree state (modified-files count on each branch's working tree):
   - `repos/CFDrs` `codex/cfdrs-atlas-migration`: **79 modified/untracked inner paths on 2026-07-06 recheck** after the `d58d1fe3` Batch #2 closure push. Batch #2 (CFDrs nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix`) remains **CLOSED** at `d58d1fe3`, but the current dirty tree is live inner-repo WIP and is not reclaimable from Atlas-meta. Do not retract the CFDrs §C row until the inner tree is clean again or a new CFDrs commit lands.
   - `repos/ritk` `main`: **0 modified files** after inner commits `65a1a0fd`, `d7a940b5`, and `8f8360ff`; `65a1a0fd` removed Burn's stale `wgpu` feature from the workspace dependency, `d7a940b5` added the Batch #3 sub-batch #1 Atlas-typed parallel trait surface, and `8f8360ff` added typed DICOM attribute reads for downstream imaging consumers. Atlas-parent pointer commits advanced the pointer.
   - `repos/apollo` `refactor/apollo-fft-eunomia`: **235 modified files** (CR-1 closed 2026-07-07; residual Apollo dirty remains peer-active provider WIP).
   - `repos/kwavers` `codex/kwavers-core-moirai-parallel`: **27 modified/untracked inner paths on 2026-07-06 recheck** at `c6b845f81` (`[ahead 13]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`, 2026-07-06 12:45) — peer is actively landing Batch #4 Burn→Coeus migration: landed `1dc47028a` (`kwavers-math` nalgebra → eunomia/leto/moirai-parallel), `f36995162` (kwavers-gpu/solver Hephaestus seam), `400c32624` slice 1 (`burn_wave_equation_1d` PINN→Coeus, 12 files, ~563 lines reconstructed), and `c6b845f81` slice 2 (`burn_wave_equation_2d` dependency graph: acoustic_wave, cavitation_coupled, sonoluminescence_coupled, electromagnetic, adaptive_sampling, meta_learning, transfer_learning, distributed_training, quantization, uncertainty_quantification, universal_solver, field_surrogate/training/trainer). Slice 2 drain: `burn::` line-hits 315→186 (-41%), `use burn` imports 222→125 (-44%), file-count 144→80 (-44%); remaining surface = `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}` + `elastic_2d/{training,loss,adaptive_sampling}` + 17 top-level test/bench/example files + `kwavers-solver/Cargo.toml:53` `burn` optional dep + `pinn` `dep:burn` line at L62-70 + `crates/kwavers-solver/src/burn.rs` and `burn_compat` module deletions (still pending). Risk #8 framing now partially-resolved by `c6b845f81` (commit body: "per prior direction not to build burn-compat shims"); risk stays live until the facade + Cargo.toml strip land. Batch #1 (Rayon→Moirai residual, 84 sites / 28 files) and Batch #4 (Burn→Coeus, 186 hits / 80 files — down from 315/144 after slice 2) both remain OPEN but peer-active; Atlas-meta defers to peer.
   - `repos/hermes` `perf/compress-buffer-hoist`: 46 modified (peer SIMD-ISA dispatch).
   - `repos/moirai` `refactor/remove-dead-subsystems`: 26 modified.
   - `repos/leto` `codex/leto-cr4-ssot-rebind`: 14 modified (peer fixed-spatial-reconcile; disjoint from Atlas-meta).
   - `repos/melinoe` `codex/halo-vecdeque-migration`: 13 modified.
   - `repos/helios` `codex/kwavers-atlas-integration`: **0 dirty direct paths** after the Helios/RITK DICOM ownership closure; H-061/H-062 removed the unused direct `num-traits` edge and aggregate dicom-rs `ndarray` feature edge, routed production DICOM parse/typed attributes/transfer syntax/pixel decode through `ritk-dicom`, added the local Melinoe patch required by patched Gaia, and synced Helios PM evidence. H-063 tracks the remaining `helios-imaging` generic-toolkit audit.
   - `repos/gaia` `refactor/migrate-to-leto-geometry`: 5 modified, including CSG source and benchmark files; no PM-only split claim remains.
   - `repos/coeus` `main`: 19 modified, including dtype/tensor/Python/docs files; no PM-only split claim remains.
   - `repos/eunomia` `main`: 7 modified (acos/asin/atan peer claim).
   - **Clean working trees** (no uncommitted WIP): `repos/helios` (DICOM production path now RITK-owned; H-063 imaging audit filed), `repos/ritk` (pointer advanced to `8f8360ff` by the Helios/RITK DICOM ownership commit), `repos/themis` (peripheral provider-cache crate, no migration surface), `repos/hephaestus` (clean inner tree; ks5-cholesky-panel active-regular commits), and `repos/mnemosyne` (clean inner tree; codex/eunomia-local-source active-regular commits). These are no longer counted as submodule-internal dirty rows in `backlog.md`; parent gitlink deltas, if present, are Atlas-parent pointer work rather than inner-submodule WIP.
   - **Net effect**: Atlas-meta's only disjoint-contribution surface during this 2026-07-06 refresh is the atlas-meta PM artifacts themselves. The CR-class provider-side obstacles and the consumer batches #1–#4 all reside inside trees with peer WIP, so the next autonomous consumer-batch sprint must defer until peer WIP commits land or the claim is genuinely released via the documented abandon-protocol.
7. **CR-4 ADR 0005 status**: status **Proposed**, deferred bump-to-Accepted across this session (live implementation closed the rebind per `2b3f820` coeus + `b15439b` leto + `5328de1c` atlas closure). **CLOSED 2026-07-05** by atlas-meta commit `b66ec228` — `docs/adr/0005-eunomia-scalar-ssot.md` status line now reads "Accepted — implementation closed 2026-07-05" citing all four closing commits (`57d7789` eunomia + `2b3f820` coeus + `b15439b` leto + `5328de1c` atlas closure). No further action.
8. **BATCH #4 SLICE-INTEGRITY (kwavers, surfaced 2026-07-06)**: peer commit `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" claims in its body: "rewritten directly against coeus rather than via a burn-shaped compat facade". T1 verification at the commit's own HEAD contradicts this claim: `crates/kwavers-solver/src/burn.rs` (112 lines) IS a burn-shaped compat facade, with module header docstring stating verbatim "Every `use burn::…` in the PINN submodules resolves here — zero changes to those files are required." and "Migration note: As each PINN submodule is fully ported to native coeus API the imports from this module are replaced with direct coeus imports and the module declaration in `lib.rs` is removed." The facade re-exports `burn_compat::{tensor, module, nn, optim, backend, config, prelude, record}` aliased to shadow the removed `burn` crate name. Per `atlas/AGENTS.md` `integrity` §Compatibility soup HARD rule and §"distributed shim, equally prohibited" — `pub use old as new`, `#[deprecated]` re-export, forwarding wrapper, module alias, or adapter layer kept to avoid updating callers" are all prohibited. The facade violates the first (module alias, forwarding wrapper). The companion coeus-side `Module::load_parameters` extension called out in the peer's commit message as having been added in a companion coeus commit is a legitimate upstream-first implementation per `architecture_scoping` upstream-ownership (the capability gap was filled upstream in coeus), EXCEPT the API shape was driven by the burn facade's needs (per the commit body, motivated by replacing Burn's `ModuleMapper` visitor pattern) — i.e., the extension risks recreating the burn-shaped API topology in coeus. `integrity` §"Converted code is rewritten natively in the target API's idioms — never a mechanical transliteration that recreates the old API's shape through local helpers, extension traits, or conversion chains" is an `integrity` HARD-tier prohibition specifically on the *distributed-shim pattern* across the consumer-provider boundary.
   - **Skew**: peer commit message framing ≠ actual code shape at the commit's own HEAD. Surface for peer self-reconciliation: either (a) the `400c32624` commit body is corrected to retract the "no compat facade" claim, AND the Batch #4 closure plan is restated as multi-slice (Slice 1 = `burn_wave_equation_1d` ✅ landed, Slice 2..N = migrate remaining 60+ PINN submodules + 17 top-level files + strip `burn` from `kwavers-solver/Cargo.toml:53` and `kwavers/Cargo.toml:138` + delete `crates/kwavers-solver/src/burn.rs` and `burn_compat` module); or (b) `burn.rs` is deleted now, with all remaining `use burn::…` callsites re-pointed at native `coeus::{core,nn,optim,tensor,autograd,record}` imports per the canonical burn→coeus trait rewire (checklist Batch #4 §B), and the coeus `Module::load_parameters` API is reviewed for idiomatic coeus shape vs burn-shape leakage.
   - Atlas-meta scope: surface-and-record only. The kwavers source tree is peer-claimed (`codex/kwavers-core-moirai-parallel`, `[ahead 12]`, peer ACTIVE). Resolution per `concurrent_agents` disjoint-scope rule is peer-owned. No Atlas-meta pointer advance for `repos/kwavers` until this slice-closure pattern is reconciled.

9. **SEMVER-CHECKS RESOLUTION BLOCKER (mnemosyne-arena → themis dep-resolution)** (2026-07-06, surfaced by pre-batch-#5 verification): `rustup run nightly cargo semver-checks -p ritk-core -p ritk-image -p ritk-spatial --baseline-rev HEAD~N` (regardless of N) diverges at the per-crate `cargo update` regeneration step before rustdoc generation, surfacing `error: failed to select a version for the requirement "themis = \"^0.8.0\""` against the transitive dependency chain `ritk-{core,image,spatial} → leto 0.36.0 → mnemosyne v0.2.0 (git rev 1e014d25) → mnemosyne-arena v0.2.0 (git rev 1e014d25) → themis = ^0.8.0`. This blocks the RITK Batch #3 sub-batch #5 `[major]` standing reminder's pre-merge authoritative-classification gate per `atlas/backlog.md` §In-flight claims §Standing reminders §Sub-batch #5 [major].
   - **Tool/registry mismatch**: the installed toolchain `cargo-semver-checks 0.48.0` does NOT recognise the literal `cargo semver-checks release ...` subcommand (`error: unrecognized subcommand 'release'` exit 2); nor `--locked`/`--offline` flags (`unexpected argument`). Available v0.48.0 baseline modes are `--baseline-version <X.Y.Z>` (registry), `--baseline-rev <REV>` (git rev), `--baseline-root <PATH>`, `--baseline-rustdoc <JSON_PATH>`. The three deletion-authorised packages `ritk-core 0.9.0` / `ritk-image 0.2.0` / `ritk-spatial 0.1.0` are NOT published on crates.io so default registry baseline is unusable.
   - **Dep-resolution result**: cargo's dep-resolver could not select any `themis` version matching `^0.8.0` (the cargo-update error enumerated only `0.9.17` as the candidate, which is non-matching; the upstream themis git source `https://github.com/ryancinsight/themis` local-tag inventory is not verified by this error output, only that the resolver found no compatible match).
   - **Resolution path (i) — upstream canonical fix (preferred long-term)**: `mnemosyne-arena` (a real workspace sibling of `mnemosyne` in the `Mnemosyne` monorepo, transitively pulled per the cargo-update error chain) lifts its `themis = ^0.8.0` requirement to `^0.9` (or absorbs themis transitively into its own version surface). Cross-walk `atlas/backlog.md` §In-flight claims "This codex session (2026-07-06, pre-batch-#5 `cargo semver-checks` verification)" for the resolution narrative.
   - **Resolution path (ii) — triage workaround**: extend the existing `[patch."https://github.com/ryancinsight/Mnemosyne.git"]` block in `repos/ritk/Cargo.toml` (currently patching only `mnemosyne = { path = "../mnemosyne/crates/mnemosyne" }`) with `mnemosyne-arena = { path = "../mnemosyne/crates/mnemosyne-arena" }` — this synchronises the themis-resolution constraint locally without modifying the `Mnemosyne.git?rev=1e014d25` upstream and unblocks the semver-checks run. Path-hypothesis caveat: the `../mnemosyne/crates/mnemosyne-arena/` local subdirectory existence is not verified from the cargo-update error alone — requires checking the local `repos/mnemosyne/` mirror before applying this workaround (the dep chain only proves the git source has the crate).
   - **Compile-cleanliness analog-evidence (NOT a substitute for the semver-impact verdict)**: `rustup run nightly cargo build --release -p ritk-core -p ritk-image -p ritk-spatial` PASSES (`Finished release profile [optimized] target(s) in 0.70s` with only cosmetic hephaestus `[patch]` warnings). This signals source compiles cleanly under the current additive state; does NOT speak to API-surface delta or the `[major]`/`[minor]`/`[patch]` verdict that requires the semver-checks toolchain.
   - **Standing-reminder status**: the standing reminder's "MUST run pre-merge" clause is **unsatisfiable** in this session environment until (i) or (ii) lands; tracking in `atlas/backlog.md` §In-flight claims capture before this gap_audit.md entry was added (the pre-batch-#5 verification verdict row).

---

## Validator invariants (per criticality level)

- **Tier-A (cross-provider SSOT)**: CR-1, CR-2, CR-4 — landing arrangement coordinated per `atlas/AGENTS.md` documentation-disciple rule + ADR requirement.
- **Tier-B (provider-extension)**: above, listed in provider-own backlogs but track at-meta-level here.
- **Tier-C (consumer-batch)**: Batch #1–#4. Definition-of-Ready at the meta-level; batch itself is the per-repo backlog item.
