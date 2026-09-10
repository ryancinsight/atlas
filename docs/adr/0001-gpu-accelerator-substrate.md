# ADR 0001: Shared GPU/accelerator substrate — `hephaestus`

- Status: Accepted
- Date: 2026-06-10
- Scope: stack-level (atlas topology); drivers `coeus` and `apollo`
- Class: [arch]

- Item: [ATLAS-CUDA-DRIVER-BOUNDARY](../../backlog.md#atlas-cuda-driver-boundary)
## Context

Both `apollo` (spectral transforms) and `coeus` (tensor/autodiff) need GPU
execution. Today:

- `apollo` has wgpu-only `-wgpu` crates with their own device/queue/pipeline
  plumbing (`apollo-wgpu-helpers`).
- `coeus` has a `ComputeBackend` seam with a wgpu backend and a CUDA backend
  currently built on `cutile`.
- `mnemosyne` has a dlopen CUDA unified-memory backend.

This duplicates device/buffer/dispatch plumbing and risks divergence. The
question is where a *shared* GPU device substrate should live.

The governing constraint is the atlas dependency rule that motivates `leto`:
**`apollo` must not depend on `coeus`.** Therefore a substrate shared by both
must sit at or below the infrastructure tier; it cannot live in `coeus`.

## Decision

1. **Create a standalone infrastructure-tier repository, `hephaestus`**, as the
   shared GPU/accelerator device substrate — a sibling of `leto`, `moirai`,
   `hermes`, and `mnemosyne`. It owns: device/context/queue, device buffers, and
   a `ComputeBackend`-style dispatch seam with two backends:
   - **wgpu** — portable.
   - **CUDA** — Hephaestus owns the driver ABI, runtime loading, context,
     device-memory and stream operations. Kernel authoring remains a separate
     concern. Driver acquisition compiles without a CUDA toolkit and loads
     the installed driver at runtime; runtime CUDA source compilation may
     separately require NVRTC.

   Rejected alternatives: putting the substrate in `coeus` (would force an
   `apollo`→`coeus` edge or duplication); putting it inside `leto` core
   (overloads leto's array/layout bounded context and drags GPU deps into a
   CPU-only crate). A separate crate inside the leto workspace was considered
   but a standalone repo gives cleaner bounded-context isolation and independent
   versioning, consistent with the rest of the infrastructure tier.

2. **Autodiff stays in `coeus`.** Device kernels (matmul, conv forward/backward,
   elementwise, …) are autodiff-agnostic functions; `coeus`'s tape composes
   forward+backward kernels. `coeus`'s `ComputeBackend` is *implemented over*
   `hephaestus`; the high-level `Tensor<T, B>` and the `ComputeBackend`/
   `BackendOps` seam are unchanged.

3. **`leto` stays CPU-only.** `hephaestus` reuses leto's host-side `Layout<N>`
   as backend-agnostic indexing metadata; it does not depend on leto's CPU
   compute. leto arrays may optionally gain a device-backed storage impl over
   `hephaestus` buffers later, behind a feature, without leto-core taking a GPU
   dependency.

4. **Device memory is owned by `mnemosyne`** (device pools, pinned-host staging,
   unified-vs-discrete policy) and **ownership is proven by `melinoe`** tokens
   (moving a `SyncRegionToken` transfers device write capability; a
   `SharedReadToken` fans out concurrent device reads).

## Consequences

- `apollo`'s `-wgpu` crates re-base their device plumbing onto `hephaestus`,
  keeping their WGSL kernels; a new CUDA transform path becomes possible.
- `coeus-wgpu`/`coeus-cuda` re-base onto `hephaestus`; consumers do not own
  a second driver ABI or duplicate its device/context lifetime.
- Adding `hephaestus` updates this topology SSOT (done) and is a coordinated
  cross-repo unit per the co-evolution protocol: scaffold `hephaestus` →
  consumers pin it → integration verified in `apollo` and `coeus`.
- Implementation is staged in each consumer's backlog (coeus MS-60+ Stage D;
  apollo Stage D4) and in `mnemosyne`/`melinoe` Stage D1.

## Status / next step

Scaffolded and integrated (2026-06-10). `hephaestus` 0.1.0 is live at
<https://github.com/ryancinsight/hephaestus>: `hephaestus-core` (GPU-dep-free
`ComputeDevice` seam) + `hephaestus-wgpu` (acquisition, typed buffers,
elementwise/scalar/unary/reduction dispatch with pipeline caching), with
differential contract tests green on real hardware. First consumer slice
delivered: `apollo-wgpu-helpers` delegates device acquisition to hephaestus
(public API preserved; apollo GPU FFT tests pass on the hephaestus-acquired
device). Next: strided-layout-aware dispatch over leto metadata, the composed
CUDA backend, mnemosyne device pools, and the coeus
re-base at its wgpu 26 bump.

## 2026-09-05 revision: provider-owned CUDA driver boundary

The original `cuda-oxide` prescription contradicts the decision's dynamic-load
contract. Version 0.4.0 links the toolkit's CUDA import library; on Windows
CUDA 13.3 that library also requests LIBCMT. Its generated `size_t = c_ulong`
is 32 bits on Windows x64, whereas `cuMemGetInfo_v2` writes pointer-sized
outputs. The replaced Hephaestus boundary supplies those undersized locals. Apollo's
all-feature dependency audit additionally rejects the dependency's license.

Replace that dependency in its owning provider with curated declarations
verified against the installed NVIDIA header and a library-owning function
table. Contexts, buffers and modules preserve that library lifetime; resolve
symbols at initialization, never inside numerical loops. Distinguish driver
absence, missing symbols and driver faults. The public compute seam, kernel
semantics and license policy remain unchanged. Hephaestus ADR 0001 owns the
implementation contract and its ABI, device and consumer verification.

Hephaestus `242520e` delivers this boundary; `59436b5` removes the CI-injected
stub driver so Linux adapterless contracts exercise actual driver absence.
Required-device Windows tests, release tests and Linux adapterless CI pass.
Apollo `1de31e26` adopts the provider with all-feature native tests and the
unchanged dependency policy passing. These runs establish tested behavior and
ABI-layout checks, not a formal proof or Miri coverage of CUDA FFI.
