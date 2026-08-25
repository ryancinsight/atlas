# Atlas legacy-dependency migration audit — kwavers, CFDrs, ritk

- **Branch:** `codex/kwavers-atlas-integration`
- **Date:** 2026-07-05 (snapshot refresh — counts folded from live `xtask -- legacy-migration-audit` / `-- burn-migration-audit` runs)
- **Owner:** codex (Atlas migration)
- **Status:** in-progress; *coexist → cutover* phase. This document is a human-readable snapshot; the canonical machine-readable surface is each crate's `xtask/src/migration_audit.rs` and the matching `xtask/legacy_surface.allowlist` (kwavers, CFDrs) or `xtask/burn_surface.allowlist` (ritk), which already gates CI on allowlist drift.

## 1. Executive summary

The three physics/medical-imaging crates — `kwavers` (acoustics), `CFDrs` (CFD), `ritk` (image toolkit) — currently coexist with their eventual Atlas replacements. Every subcrate already declares the **full Atlas cluster** via path-pinned (vendored) mutable copies in `workspace.dependencies` (`moirai`, `moirai-parallel`, `leto`, `leto-ops`, `hephaestus-core`, `hephaestus-wgpu`, `coeus-core/tensor/ops/autograd/leto/nn/optim`, `apollo-fft`, `apollo-nufft`, `eunomia`, `hermes-simd`, `mnemosyne`, `melinoe`, `gaia`, `aconsus`). Migration is the remaining work of **removing the legacy deps alongside**, not introducing the Atlas deps.

### 1.1 Workload & Atlas imports — 2026-07-05 live counts

Produced by `cargo run -p xtask -- legacy-migration-audit` for kwavers/CFDrs and `cargo run -p xtask -- burn-migration-audit` for ritk. Counts are fed by token-only string matches; per-file token counts are sums over the audit’s `BURN_TOKENS` / `LEGACY_SOURCE_TOKENS` lists. The kwavers source-file count includes vendored upstream `vendor/numpy-0.27.1/**` (12 of the 19 allowlist-drift entries below) — first-party migration debt is the remainder.

| Crate | Manifest w/ legacy | Source w/ legacy tokens | Source-token hits (Σ) | Manifest w/ Atlas | Legacy deps in workspace SSOT |
| --- | ---: | ---: | ---: | ---: | --- |
| `kwavers`      | 22 | 1681¹ | – (raw counts only per-file) | 16 | `nalgebra 0.33 (+serde-serialize)`, `ndarray 0.16 (+rayon)` |
| `CFDrs`        |  6 |   76 | – | 10 | `nalgebra 0.33 (+serde-serialize)`, `nalgebra-sparse 0.10` (+ `nalgebra 0.33` re-declared in root `[dependencies]`) |
| `ritk`         | 27 |  671 | – | (not enumerated by burn audit²) | `burn 0.19 (+std, ndarray, autodiff, wgpu)`, `burn-ndarray 0.19`, `num-traits 0.2` |
| **Σ first-party** | **55** | **≥ 2351** | – | – | – |

¹ kwavers `1681` source files include `vendor/numpy-0.27.1/**` (`58` legacy-token hits across `12` files). First-party-only count after subtracting vendored: `1669` files.  
² ritk's burn audit prints the `COEUS_REQUIREMENTS` list in lieu of an explicit "Manifests with Atlas" tally. Ritk's Atlas `workspace.dependencies` block already pins `moirai`, `mnemosyne`, `eunomia`, `coeus-{core,tensor,ops,leto,autograd}`, `leto`, `leto-ops`, `hephaestus-{core,wgpu}`, `apollo-fft` — effectively every subcrate in the table inherits these via `workspace = true`.

### 1.2 Allowlist drift per crate

| Crate | Allowlist file `xtask/legacy_surface.allowlist` (or `burn_surface.allowlist` for ritk) | New drift entries | Stale "already migrated" cleanup candidates |
| --- | --- | ---: | ---: |
| `kwavers` | `xtask/legacy_surface.allowlist` | **19** | 27 |
| `CFDrs`   | `xtask/legacy_surface.allowlist` |  **1** | 95 |
| `ritk`    | `xtask/burn_surface.allowlist`    |  **1** | 135 |

Kwavers drift headliners (excluding the 12 vendored-upstream noise entries): `crates/kwavers-gpu/src/beamforming/three_dimensional/delay_sum/processor/dispatch.rs`, `crates/kwavers-gpu/src/beamforming/three_dimensional/delay_sum/processor/dynamic_focus_dispatch.rs`, `crates/kwavers-gpu/src/beamforming/three_dimensional/provider.rs`, `crates/kwavers-python/src/utils_bindings/geometry.rs`, `crates/kwavers-solver/src/burn.rs`, `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat.rs` — note kwavers-solver has its own direct `burn::` namespace usage (Pinn / autograd compatibility layer).  
CFDrs drift only: `crates/cfd-1d/src/solver/core/vector_bridge.rs`.  
Ritk drift only: `crates/ritk-image/src/lib.rs` — needs allowlist entry or migration to `coeus-tensor` slice.

### 1.3 Data-plane legacy use — top ritk subcrates by Burn-token hits (refresh)

| ritk crate | Manifest burn | Source-token hits Σ |
| --- | :---: | ---: |
| `ritk-registration`  | ✓ | 1153 |
| `ritk-filter`        | ✓ |  605 |
| `ritk-interpolation` | ✓ |  510 |
| `ritk-transform`     | ✓ |  408 |
| `ritk-model`         | ✓ |  311 |
| `ritk-segmentation`  | ✓ |  284 |
| `ritk-io`            | ✓ |  263 |
| `ritk-python`        | ✓ |  145 |
| `ritk-cli`           | ✓ |  128 |
| `ritk-image`         | ✓ |  121 |
| `ritk-spatial`       | ✓ |   42 |
| `ritk-statistics`    | ✓ |   46 |
| `ritk-vtk`           | ✓ |    8 |
| `ritk-wgpu-compat`   | ✓ |   21 |
| `ritk-{codecs,metaimage,mgh,nifti,nrrd,png,jpeg,tiff,minc,analyze,snap,tensor-ops,macros}` | ✓ / – | 13 – 50 each |
| `ritk-macros`        | – |   25 (token-only; no manifest burn) |

Top three (registration, filter, interpolation) account for **2268 / ≥ 4471 Σ ritk-token hits** — well over half the bridge surface. The ritk-registration alone (~1153) is the densest single crate and the natural Phase-1 registration + Coeus-nn convergence target (§3 ritk sequencing).

### 1.4 Workspace legacy deps remaining (unchanged from prior snapshot)

| Crate | Legacy deps still in `workspace.dependencies` | xtask audit surface | Notes |
| --- | --- | --- | --- |
| `kwavers` | `nalgebra 0.33`, `ndarray 0.16 (+rayon)` | `xtask/legacy_surface.allowlist` + 7 legacy-dep tokens | path-pinned full cluster |
| `CFDrs`   | `nalgebra 0.33`, `nalgebra-sparse 0.10`          | `xtask/legacy_surface.allowlist` + 7 legacy-dep tokens | path-pinned full cluster; `nalgebra 0.33` also re-declared in root `[dependencies]` |
| `ritk`    | `burn 0.19`, `burn-ndarray 0.19`, `num-traits 0.2` | `xtask/burn_surface.allowlist` + burn-specific tokens | path-pinned full cluster; `cfd-mesh = { package = "gaia", ... }` reuses gaia as the mesh crate |

Subcrate-level `[dev-dependencies]` for `approx` (kwavers / CFDrs / ritk) are not enumerated by the workspace SSOT but recur widely in tests; promote them into the xtask audit lists (see §5).

## 2. Per-crate module migration matrix

Complexity grades: **M** = mechanical swap (import rename + shim); **A** = API rewrite required inside the consuming crate; **E** = Atlas-side extension required before a 1:1 port. "Blanket" is a judgment of test density (unit + integration + property + examples + benches).

### 2.1 `kwavers` (acoustics)

| Module | Legacy surface | Atlas replacement | Grade | Blanket |
| --- | --- | --- | --- | --- |
| `kwavers-math`        | `ndarray`, `nalgebra` math primitives, possible sub-[dev-]`approx`/`num-traits` | `leto` + `leto-ops` + `eunomia` (numeric SSOT)            | M  | high   |
| `kwavers-grid`, `kwavers-field` | `ndarray` allocation, slicing, strided views                                       | `leto` tensor types                                         | A  | high   |
| `kwavers-physics`, `kwavers-solver` | FFT (`rustfft`-derivable), dense/iterative solves, dense-matrix kernels        | `apollo-fft` + `apollo-nufft` + `leto-ops` + `hermes-simd` inner loops | A  | high   |
| `kwavers-analysis`, `kwavers-simulation` | `nalgebra::Vector3/Point3`, `approx::assert_*_eq`, parallelism (`rayon`)          | `leto` + `eunomia`-derived bounded-epsilon asserts (E5) + `moirai-parallel` | A  | high   |
| `kwavers-boundary/source/receiver/transducer/imaging/medium/mesh/phantom/optics/diagnostics/therapy` | `nalgebra::Vector3/Point3`, primitives scattered through pipelines | `leto`                                                 | A  | medium |
| `kwavers-driver`, `kwavers-python` | `pyo3`, `numpy` boundary conversions                                              | `pyo3` + `leto` → numpy conversion shims               | M  | medium |
| `kwavers-gpu` (PSTD + KZK kernels) | WGSL via raw `wgpu`, GPU-bound math                                                | `hephaestus-wgpu` + `gaia` GPU geometry kernels        | A  | medium |

### 2.2 `CFDrs` (fluid dynamics)

| Module | Legacy surface | Atlas replacement | Grade | Blanket |
| --- | --- | --- | --- | --- |
| `cfd-math`              | `nalgebra::RealField/Scalar`, dense `Vector3/Point3/Matrix3`                        | `leto` SSOT traits + `eunomia` numeric traits            | A  | high   |
| `cfd-core`, `cfd-schematics` | mesh traits, scheme re-exports                                                   | `leto` + `gaia` geometry                                  | A  | high   |
| `cfd-1d`, `cfd-2d`, `cfd-3d` | local math, `nalgebra` Dense, dense small matrices, implicit solve                | `leto` + `leto-ops` + `apollo-nufft` where applicable    | A  | high   |
| `cfd-optim`, `cfd-validation` | `DMatrix` (dynamic), `DVector`, sparse LU / iterative + Newton variants            | `leto` dense (E3) + `leto-ops` sparse (E4)              | E  | high   |
| `cfd-io`                | HDF5 / VTK mesh I/O, mesh-adapter re-exports                                         | `aconsus` (HDF5) + `ritk-vtk` + `gaia` exported as `cfd-mesh` | M  | medium |
| `cfd-python`, examples, benches | `pyo3`, `numpy`, `approx::assert_*_eq` pervasive in tests / properties           | `pyo3` + `eunomia` + `atlas-assert` (E5)               | M→E | high   |

### 2.3 `ritk` (image toolkit + registration)

| Module | Legacy surface | Atlas replacement | Grade | Blanket |
| --- | --- | --- | --- | --- |
| `ritk-tensor-ops` | `burn-tensor` algebra, reductions, matmul                    | `coeus-tensor` + `coeus-ops` (foundation layer)            | A  | high   |
| `ritk-core`, `ritk-spatial`, `ritk-image` | `burn` dimensional objects, image buffers    | `leto` + `coeus-tensor` views                                | A  | medium |
| `ritk-interpolation`, `ritk-transform` | autodiff over image tensors, MI/NCC/CR/Parzen metrics | `coeus-autograd` + `coeus-ops` + `hephaestus` scatter (E6) | E  | high   |
| `ritk-registration`, `ritk-segmentation`, `ritk-model` | `burn::module::{Module, Param}`, `burn::nn`, `burn::optim` | `coeus-nn` + `coeus-optim` + `coeus-autograd`                | E  | high   |
| `ritk-codecs/*` (dicom, nifti, nrrd, mgh, minc, png, jpeg, tiff, analyze, metaimage, vtk, snap) | optional `burn-ndarray` (test image tensors) | `coeus-tensor` + `leto's ndarray parity`               | A  | medium |
| `ritk-cli`, `ritk-python` | `pyo3`, `numpy`, command-line plumbing                       | `pyo3` + `numpy` boundary rewrites                           | M  | medium |
| `ritk-analyze`, `ritk-statistics`, `ritk-morphology`, `ritk-annotation`, `ritk-filter` | `burn-ndarray` (test tensors) + `num-traits` math | `eunomia` + `coeus-tensor` CPU ref backend            | A  | medium |
| `ritk-wgpu-compat` | raw WGSL / wgpu plumbing                                  | `hephaestus-wgpu` (compat layer collapsed)                    | A  | low    |
| `ritk-macros` | module-generating macros                                  | `coeus-nn` reflection / module macros (E1)                   | E  | low    |

## 3. Migration sequencing (foundations-first)

Per crate, migrations move bottom-up so type signatures match across module boundaries by the time upper crates are reached. Within each phase, work in micro-steps inside a single subcrate so regressions localize to one direction.

### `kwavers`
1. `kwavers-math` — `num-traits` → `eunomia`, `approx` → `eunomia` epsilon macros, `ndarray`/`nalgebra` types → `leto`.
2. `kwavers-grid`, `kwavers-field` — owned/sliced tensor migration.
3. `kwavers-physics`, `kwavers-solver` — inner FFT to `apollo-fft`, parallelism to `moirai-parallel`, hot loops to `hermes-simd`.
4. `kwavers-analysis`, `kwavers-simulation`, plus `kwavers-{boundary,source,receiver,transducer,imaging,medium,mesh,phantom,optics,diagnostics,therapy}` — orchestration + each leaf's local math port.
5. `kwavers-driver`, `kwavers-gpu`, `kwavers-python` — PyO3 + GPU closure pass; cascade churn controlled by leaving numpy shim last.

### `CFDrs`
1. `cfd-math` — dense math-primitive port (`RealField`, `Scalar`, `Vector3`, `Matrix3`).
2. `cfd-core`, `cfd-schematics`, mesh (`cfd-mesh = { package = "gaia", ... }`) — port mesh traits and align with `gaia` geometry types.
3. `cfd-1d`, `cfd-2d`, `cfd-3d` — bulk numeric kernels, sparse via `nalgebra-sparse` → `leto-ops` sparse (E4).
4. `cfd-validation`, `cfd-optim` — heavy `DMatrix` / sparse solve work (depends on E3, E4).
5. `cfd-io`, examples, `cfd-python`, benches — closure pass; `approx` test macros migrated to `atlas-assert` (E5).

### `ritk`
1. `ritk-tensor-ops` — `burn-tensor` → `coeus-tensor` shim established first; this is the foundation for everything else.
2. `ritk-core`, `ritk-spatial`, `ritk-image`, `ritk-codecs/*` — image pipeline + codec CPU/GPU decode migration.
3. `ritk-interpolation`, `ritk-transform` — `coeus-autograd` regrid + metrics.
4. `ritk-registration`, `ritk-segmentation`, `ritk-model` — autodiff loss + `coeus-nn`/`coeus-optim` (depends on E1, E2, E6).
5. `ritk-analyze`, `ritk-statistics`, `ritk-morphology`, `ritk-annotation`, `ritk-filter`, `ritk-cli`, `ritk-python`, `ritk-macros`, `ritk-wgpu-compat` — closure pass.

## 4. Atlas-side extension requests (gap analysis)

These block clean migration unless addressed on the Atlas side. Each row is a candidate for an Atlas ADR / Cluster Request (CR) before the matching dependent crate can cut over.

1. **`coeus-nn` — 3-D convolution + module macros.** `ritk-registration` / `ritk-segmentation` rely on `burn::nn::Conv3d`, `burn::module::{Module, Param}`, and pooling families. A 1:1 port needs equivalent `coeus-nn` 3-D convolution + module reflection macros.
2. **`coeus-autograd` — image-shaped (rank-3/4) autodiff.** The `COEUS_REQUIREMENTS` list in `repos/ritk/xtask/src/migration_audit.rs` already enumerates this; pull it forward into a CR.
3. **`leto` / `leto-ops` — dense LAPACK equivalent surface.** `cfd-validation`, `cfd-optim`, parts of `cfd-3d` use `nalgebra::DMatrix` (dynamic) + `nalgebra::DVector` + LU/SVD/Eigen solves. `leto` must expose a dense dynamic matrix type with the same decomp set, OR the current memory-backed dense must be lifted into `leto's` symbol set.
4. **`leto-ops` — sparse parity for `nalgebra-sparse`.** CFDrs is the heaviest user. A parity layer wrapping `csr_adaptive`/`csc` plus iterative solvers would let `cfd-{1,2,3}d` cut over without rewriting each solver.
5. **`eunomia` (or a sibling `atlas-assert` test crate) — bounded-epsilon CPU↔GPU asserters.** All three crates use `approx::assert_relative_eq`/`assert_abs_diff_eq` in unit, integration, and validation tests. Unified macros that cross-compare CPU vs WGPU float outputs at the same epsilon band keep the test blanket intact.
6. **`hephaestus` — sparse Parzen histogram scatter-add.** `ritk-registration` needs sparse Parzen-window histogram accumulation in MI / CR metrics. Custom WGSL scatter-add (or generic scatter kernel) required before `ritk-registration` can drop the trailing `burn-ndarray` reference.
7. **`moirai` — drop-in `tokio::spawn`-style facade for kernels.** `kwavers-simulation` and `cfd-validation` already emit telemetry-side scheduling through a tokio-style model. A parity shim in `moirai-async` would localize the leaf-math migration from fan-out rewrites (Atlas tracks `moirai-async` — cross-check GA).
8. **`apollo` — top-level crate re-exporting subcrates.** kwavers / CFDrs pin `apollo = { path = "...", package = "apollo-fft" }`. Once `apollo` re-exports `apollo-fft`, `apollo-nufft`, etc., the three crates can drop the `package = "..."` workaround.

## 5. Open follow-ups for this audit

- Run `cargo run -p xtask -- legacy-migration-audit` (kwavers, CFDrs) and `cargo run -p xtask -- burn-migration-audit` (ritk); reflect the fresh counts into §1 so the snapshot stays in sync.
- Confirm subcrate-level `[dev-dependencies]` `approx` and `num-traits` declarations in kwavers (root workspace SSOT does not currently declare these) — they may live entirely at the subcrate level. Promote the audit to include them.
- Extend each `xtask/src/migration_audit.rs` to also enumerate `approx`, `num-traits`, `rustfft`, and the standalone `ndarray` consumer (currently the kwavers/CFDrs audits cover `nalgebra`, `nalgebra-sparse`, `ndarray`, `burn`, `burn-ndarray`, `tokio`, `rayon`; ritk covers the burn token set + `COEUS_REQUIREMENTS`). Once each xtask audits the full map, CI drift detection will catch re-imports automatically.
- Cross-link each Atlas extension row (§4) into the dependent subcrate's `backlog.md` with explicit `blocked-by: <CR-id>`.

## 6. PM artifact crosslinks

| Crate | Backlog | Checklist | Changelog | Gap audit |
| --- | --- | --- | --- | --- |
| `kwavers` | `repos/kwavers/backlog.md` | `repos/kwavers/CHECKLIST.md` | `repos/kwavers/CHANGELOG.md` | `repos/kwavers/gap_audit.md` |
| `CFDrs`   | `repos/CFDrs/backlog.md`   | `repos/CFDrs/CHECKLIST.md`   | `repos/CFDrs/CHANGELOG.md`   | `repos/CFDrs/gap_audit.md`   |
| `ritk`    | `repos/ritk/backlog.md`    | `repos/ritk/checklist.md`    | `repos/ritk/CHANGELOG.md`    | `repos/ritk/gap_audit.md`    |

The persistent per-crate drift surface is `xtask/legacy_surface.allowlist` (kwavers, CFDrs) and `xtask/burn_surface.allowlist` (ritk). Each is backed by an `xtask` audit binary that hard-fails CI on new legacy surfaces, so this document serves as the human-readable migration roadmap that aligns with — not duplicates — that machine surface.
