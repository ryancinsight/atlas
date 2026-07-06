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
5. **#2 fifth** — Largest consumer body (176 CFDrs source files). Depends on CR-4.
6. **#3 sixth** — ritk Burn keyed-trait rebind. Depends on CR-4.
7. **#4 seventh** — kwavers-solver PINN Burn → coeus. Depends on CR-4 + #3.
8. **#8 last** — Provider extensions; tracked in provider repos separately; own claim stream.

### In-flight claims (per concurrent_agents)

- Branch: `codex/kwavers-atlas-integration`.
- Claim scope (this turn): atlas-root cross-repo PM artifacts (`backlog.md`, `checklist.md`, `gap_audit.md`); no per-repo files touched.
- Claim start: 2026-07-04.
- Neighbor claim stream: `codex/kwavers-core-moirai-parallel` in `repos/kwavers` (separate scope); no collision.

### Cross-engineering residual risk — `hephaestus-cuda` eigen.rs ↔ `device.upload` Complex-type mismatch

Discovered at `fb83d009` verification: under the checked-out `ks5-cholesky-panel` branch tip (`3bddfed5`), `hephaestus-cuda/src/application/decomposition/eigen.rs:173` calls `device.upload(&e_host)` with `Vec<let''o::Complex<f32>>` while `hephaestus-core/src/domain/device.rs:99` retains `&[num_complex::Complex<T>]` signature. NOT a CR-4 regression: the breaking change is `3bddfed5 fix(hephaestus-cuda): Use cuda-oxide substrate` (ks5-cholesky-panel scope) which migrated eigenvalues data flow to `let''o::Complex<T>` (`1840b38 refactor(hephaestus)!: Migrate eigenvalues to let''o::Complex<T>`) but did not update the `eigen.rs:173` upload caller to the eunomia/leto complex type. Effect: any `cargo nextest run --workspace` in `repos/coeus` (or other workspaces depending on `hephaestus-cuda/wgpu`) fails to compile. `cargo nextest run -p coeus-{core,tensor,ops,autograd,nn,sparse,dist,fft,optim,leto} --no-fail-fast` is unaffected (758/758 green). Owner: `hephaestus` ks5-cholesky-panel agent. Atlas-meta migration scoring remains GREEN on the coefficient-determining focus set; ks5 reconcile unblocks the wgpu/cuda gate.


---

## Out-of-scope (explicit)

- **`**Spec composition layers**` updated later (e.g. `cfd-validation`, testing frameworks)**: not part of this migration; filing as separate backlog if it's not in CFDrs's own backlog.
- **HELIOS/Python binding for kwavers**: Phase-3 rich-image scoping state; deferred-until `kwavers-python` intent-bledged beyond current net-style top-level.
- **GPU backend complete production rollout across ritk-model**: PPG-model is reserved-wave per `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md` HIGH-sev list; out of scope until defect closure.
