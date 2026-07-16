# ADR 0001 (atlas): Shared GPU/accelerator substrate — `hephaestus`

- Status: Accepted
- Date: 2026-06-10
- Scope: stack-level (atlas topology); drivers `coeus` and `apollo`
- Class: [arch]

- Index: docs/adr/INDEX.md#ADR-0001
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
   - **CUDA** — **composing `cuda-oxide` and `cutile`** (they coexist):
     `cuda-oxide` for driver/runtime/device-memory/stream management, `cutile`
     for tile/PTX kernel authoring. Preserve the dynamic-load /
     no-toolkit-to-compile property.

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
- `coeus-wgpu`/`coeus-cuda` re-base onto `hephaestus`; the CUDA backend gains
  `cuda-oxide` alongside `cutile`.
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
CUDA backend (cuda-oxide + cutile), mnemosyne device pools, and the coeus
re-base at its wgpu 26 bump.
