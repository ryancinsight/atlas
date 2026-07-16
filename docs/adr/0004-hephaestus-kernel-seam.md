# ADR 0004 — Hephaestus custom-kernel seam (consumer-authored kernels over wgpu + CUDA)

- Status: **Accepted** (user sign-off 2026-07-02: "proceed with recommendations completely and with monomorphization"); implementation in progress on hephaestus branch `arch/kernel-seam`
- Date: 2026-07-02
- Drivers: helios (`backlog.md:43` fused affine-clamp blocked on hephaestus op set), kwavers
  (private `PhysicsKernelRegistry` + full hand-rolled substrate, GPU stack gated during wgpu-26
  repair), CFDrs (private `GpuPipelineManager`/`GpuKernel` trait), and the hephaestus-internal
  wgpu↔cuda duplication (~2.5–3.5k structurally duplicated host-orchestration lines; see
  `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md`).
- Fulfils the seam follow-up ADR promised by hephaestus ADR 0001.

- Index: docs/adr/INDEX.md#ADR-0004
## Context

Hephaestus core exposes `ComputeDevice` (memory lifecycle only) and a storage-kernel dispatch
seam (`UnaryStorageKernel`/`BinaryStorageKernel`) that is implemented only by the wgpu backend,
constructed from raw WGSL, and limited to 1-in/1-out / 2-in/1-out fixed-shape synchronous
dispatch. Consequences observed in the wild:

1. Consumers cannot author kernels portably: helios upstreams every kernel into hephaestus
   (including the domain-specific ray marcher now living at `hephaestus-wgpu/src/application/volume.rs`
   — a layer-boundary inversion: consumer domain logic in the substrate); kwavers and CFDrs each
   rebuilt device init, pipeline caching, bind-group management, and a kernel registry privately.
2. Backend-internal ops duplicate all host orchestration per backend because there is no
   backend-neutral dispatch vocabulary; the O(L²) scan defect was copied into both backends.
3. Kernel params have no first-class path (helios packs params into an f32 storage buffer with
   exact-f32 count constraints; kwavers requires push constants; CFDrs re-creates uniform buffers
   per execute).

Surveyed requirement union (34+ kernels across three consumers): param struct + N read-only +
M read-write storage bindings with heterogeneous element types; 1D/2D/3D grids; multi-pass
single-submission chains with inter-pass barrier semantics; device-resident loops with ping-pong
buffers, GPU-side clears, and two readback patterns (bulk end-of-run; small mid-loop scalar);
workgroup shared memory; multi-entry-point modules; consumer-defined fused elementwise ops.
Explicit non-goals (no surveyed kernel needs them): atomics, indirect dispatch, textures/samplers,
device f64, subgroup ops. These bound the v1 surface; they are seam-compatible extensions, not
design constraints to pre-build.

## Decision

Extend `hephaestus-core` with a dialect-parameterized kernel-authoring and dispatch seam; both
backends implement it; hephaestus's own op families migrate onto it (dogfooding), collapsing the
duplicated host layer.

### 1. Dialect vocabulary (core, ZST, sealed)

```rust
pub trait KernelDialect: sealed::Sealed { const NAME: &'static str; }
pub struct Wgsl;   // hephaestus-wgpu (and metal-via-wgpu)
pub struct CudaC;  // hephaestus-cuda (NVRTC)

/// Unifies today's per-backend WgslScalar::WGSL_TYPE / CudaScalar::CUDA_TYPE.
pub trait DialectScalar<L: KernelDialect>: bytemuck::Pod {
    const TYPE_TOKEN: &'static str;
}
```

### 2. Kernel interface vs. kernel source (SSOT split)

The binding/param interface is declared once, dialect-independent; only the source text varies
per dialect. A kernel authored for one dialect simply does not implement the other — dispatching
it on the wrong backend is a **compile error**, which is the honest expression of partial
portability (no runtime "unsupported" surprises).

```rust
pub trait KernelInterface {
    /// POD parameter block; backend maps to push constants when available
    /// (size ≤ declared limit checked at prepare), else a pooled uniform /
    /// native kernel argument. One params path replaces three improvisations.
    type Params: bytemuck::Pod;
    /// Compile-time binding declaration: per-binding access + element size.
    const BINDINGS: &'static [BindingDecl];
    const LABEL: &'static str;
    /// Workgroup/block shape; must match the source; validated at prepare.
    const WORKGROUP: [u32; 3];
    /// CUDA dynamic shared memory bytes (0 for none; WGSL declares statically).
    const SHARED_BYTES: u32 = 0;
}

pub struct BindingDecl { pub access: Access, pub elem_size: usize }
pub enum Access { ReadOnly, ReadWrite }

pub trait KernelSource<L: KernelDialect>: KernelInterface {
    const ENTRY: &'static str;
    /// Cow: static sources allocate nothing; generated sources (scalar-token
    /// substitution) build once per cache key.
    fn source(&self) -> alloc::borrow::Cow<'static, str>;
}
```

### 3. Dispatch extension on the device seam

```rust
pub trait KernelDevice: ComputeDevice {
    type Dialect: KernelDialect;
    /// Cached pipeline/module handle; prepare is cache-hit cheap
    /// (keyed by kernel TypeId, monomorphized — no string keys, no format!).
    type Prepared<K: KernelSource<Self::Dialect>>: Clone;
    /// Multi-pass recording surface; wgpu: CommandEncoder + compute passes,
    /// cuda: per-device CUstream. Inter-pass barrier semantics guaranteed
    /// (wgpu pass boundaries / CUDA stream order).
    type Stream<'d>: CommandStream<'d, Self> where Self: 'd;

    fn prepare<K: KernelSource<Self::Dialect>>(&self, k: &K) -> Result<Self::Prepared<K>>;
    fn stream(&self) -> Result<Self::Stream<'_>>;
}

pub trait CommandStream<'d, D: KernelDevice + ?Sized> {
    fn encode<K: KernelSource<D::Dialect>, B: BindingList<'d, D>>(
        &mut self,
        prepared: &D::Prepared<K>,
        bindings: B,                // typed tuple, see §4 — no dyn
        params: &K::Params,
        grid: DispatchGrid3,        // checked covering_domain, 1D/2D/3D
    ) -> Result<()>;
    fn copy<T: Pod>(&mut self, src: &D::Buffer<T>, dst: &D::Buffer<T>) -> Result<()>;
    fn fill_zero<T: Pod>(&mut self, dst: &D::Buffer<T>) -> Result<()>;
    /// Submit recorded work; token supports sync wait now (core stays
    /// synchronous per the async-contagion rule); an ExecutionPolicy-bridged
    /// async wrapper is a later additive item.
    fn submit(self) -> Result<D::SubmitToken>;
}
```

One-shot convenience (`device.dispatch(prepared, bindings, params, grid)`) is a default method:
`stream → encode → submit`. This makes the encoder-borrowing layer (audit WG-P4) the primitive
and the per-op submit the wrapper — inverting today's structure.

### 4. Bindings: typed at construction, erased to a homogeneous slice (as built)

Bindings borrow typed `D::Buffer<T>` handles with per-binding element types (u32 index buffers,
i8 quantized weights, f32 fields coexist in one dispatch). As built, this deviates from the
draft's recursive-tuple `BindingList`: `KernelDevice` carries an erased
`type BindingHandle<'a>: Copy` GAT (`&wgpu::Buffer` / CUDA device pointer), and
`Binding::read/read_write` capture `(access, elem_size, len, handle)` from the typed borrow, so
one homogeneous `&[Binding<'a, D>]` slice carries heterogeneous element types with zero
trait-object indirection and no per-arity trait machinery. Arity, access mode, and element size
are validated value-semantically against `K::BINDINGS` at encode (`validate_bindings`, shared by
all backends) with typed errors naming position and invariant. Rationale for the deviation:
the tuple encoding bought compile-time arity at the cost of an impl family per arity and a
harder-to-read consumer surface; the slice encoding keeps element-type safety at the borrow
site (the only place it is load-bearing) and moves arity/access to one shared value check.
Write-write and read-write aliasing rejection stays value-semantic (pointer identity), matching
the existing `WgpuBuffer::aliases` discipline.

### 5. Op-marker unification (immediate DRY win, unblocks helios first)

Today's `trait UnaryWgslOp { const WGSL_EXPR }` / `trait UnaryCudaOp { const CUDA_EXPR }` pairs
(and their scan/reduction siblings) collapse to one core trait per family, dialect-parameterized:

```rust
pub trait UnaryExpr<L: KernelDialect> { const EXPR: &'static str; }
// core defines AddOp, MulOp, ExpNegOp, … once, with impls for both dialects.
```

Consumers implement `UnaryExpr<Wgsl>` (and `<CudaC>` if they target it) on their own ZSTs —
helios's fused affine-clamp op becomes a ~10-line consumer-side definition with zero hephaestus
changes. This item is deliverable before the full §2–§4 surface and unblocks helios immediately.

### 6. Consolidation (the payoff)

With §3 in place, the duplicated host layer hoists into core generic over `D: KernelDevice`:
validation, `#[repr(C)]` meta packing, blocked-decomposition loops, `Gpu*Decomposition` types,
allocating/`*_into` wrapper pairs, and the scan/reduction/elementwise orchestration. Backends
retain only: device acquisition, buffer/transfer, dialect source templates, and the
`CommandStream` mechanics. Expected deletion: 2.5–3.5k lines from hephaestus-cuda's application
layer alone; the python crate's 83 backend match arms collapse to one generic call under a single
enum dispatch; hephaestus-metal reduces to a pinned-backend constructor decision. The helios ray
marcher (`volume.rs`) migrates back to helios as an authored kernel, restoring the layer boundary.

## Alternatives considered

- **Status quo (upstream every consumer kernel)** — rejected: does not scale (helios already
  blocked; kwavers/CFDrs domain kernels do not belong in the substrate), and it inverts the layer
  boundary (consumer domain logic accretes in hephaestus).
- **Runtime kernel registry (name → source strings)** — what kwavers built privately; rejected
  for the seam: stringly keys, runtime arity/access failures, vtable dispatch. The typed seam
  subsumes it; a thin registry can sit on top for dynamic tooling if ever needed.
- **Single portable kernel IR (rust-gpu / naga-IR / CubeCL-style)** — deferred: heavy dependency
  and toolchain risk against a working WGSL + NVRTC pipeline; per-dialect source with a shared
  typed interface captures the portability that consumers actually exercise today. Revisit only
  if per-dialect source maintenance measurably dominates.
- **`dyn`-based kernel objects** — rejected: hot-path vtables violate the zero-cost rule;
  monomorphized `Prepared<K>` keyed by TypeId is both faster and simpler.

## Failure modes / risks

- Dialect drift: the same kernel's WGSL and CUDA C sources can diverge semantically. Mitigation:
  the differential-verification mandate applies per kernel (backend vs CPU reference, epsilon
  bounds per numerical_discipline reduction-order rules); cross-backend contract tests live in
  core and are exercised by both backends.
- Monomorphization fan-out: `Prepared<K>` per kernel type is the intended instantiation count
  (one per real kernel — identical to hand-written); no dimension is speculatively specialized.
- Params portability: push-constant size limits differ (wgpu 128 B typical vs CUDA 4 KiB+);
  `Params` size is validated at prepare against the backend's declared limit with a typed error,
  and the uniform fallback keeps oversized params working on wgpu.

## Verification plan

- Core contract-test suite generic over `D: KernelDevice` (arity/access/alias rejection, grid
  covering, params round-trip, multi-pass ordering via a ping-pong sum, fill_zero semantics),
  instantiated by both backends; value-semantic assertions throughout.
- Differential tests: each migrated op family keeps its existing CPU-reference differential
  tests unchanged — the migration must pass the same non-simplified suites.
- Criterion baselines recorded before migration for elementwise/reduction/scan/matmul dispatch
  paths; the seam must be regression-free (zero-cost claim verified by benchmark, and the
  prepare/encode split should *improve* multi-op chains by deleting per-op submits).
- helios affine-clamp op (§5) as the first external acceptance test; kwavers PSTD time-loop
  shape (31 bindings, push constants, resident loop) as the stress acceptance test.

## Sequencing

1. §5 op-marker unification + CUDA impl of the existing storage-kernel seam ([minor], no breaks).
2. §1–§4 seam surface in core + both backend impls ([minor]: additive traits).
3. §6 consolidation per op family — scan first (fixes the duplicated O(L²) defect once), then
   decomposition host loops, then wrappers ([major] where public surfaces move; call sites
   updated in the same change, no compatibility shims).
4. Consumer adoption: helios (immediate), kwavers (during its wgpu-26 repair), CFDrs (replacing
   its private manager; its precision contract made honest at the same time).
