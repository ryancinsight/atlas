# ADR 0051: Kwavers visualization backend ownership

- Status: Proposed
- Date: 2026-08-21
- Class: `[major] [arch]`
- Refs: `backlog.md#atlas-kwavers-vis-wgpu-2026-08-21` (the mandating item)

## Context

The current Kwavers default has two WGPU ownership paths. The
`kwavers-analysis` crate enables `wgpu`, `bytemuck`, and `pollster` for its
visualization feature, stores concrete WGPU devices and queues in
`RendererGpuContext` and `DataPipeline`, acquires adapters and devices, and
allocates and writes field buffers. The `kwavers-gpu` crate separately owns
the Hephaestus-backed WGPU provider. This duplicates runtime ownership and
keeps the analysis layer coupled to a concrete device API.

The existing dependency direction is `kwavers-gpu → kwavers-analysis` because
GPU beamforming implementations consume analysis operation contracts. A
reverse dependency cannot carry the visualization implementation without a
cycle. The historical visualization closure addressed invalid initialization
and multi-field semantics; it did not remove the remaining concrete runtime
from `kwavers-analysis`.

## Decision

Keep visualization configuration, backend-neutral field metadata, CPU
processing, and the public domain contract in `kwavers-analysis`. Move GPU
device acquisition, resource allocation, transfers, render pipelines, and
shader dispatch into `kwavers-gpu`, using its existing Hephaestus-backed
provider boundary. The role seam is owned at the deepest common consumer
boundary and is implemented by the provider layer; the dependency direction
must remain acyclic.

The migration is a replacement, not an adapter. All callers move to the
provider-generic visualization contract in the same change. The analysis
manifest and source delete their direct `wgpu`, `bytemuck`, and `pollster`
edges and raw device/resource fields. Unavailable GPU capability is returned
as a typed error. A requested GPU operation never silently changes to CPU
execution, and no re-export or forwarding wrapper preserves the old concrete
surface.

The implementation must first identify the smallest provider-neutral resource
and transfer roles needed by the current visualization operations. It must
not invent a training, rendering, or device abstraction that has no current
caller. The existing field-count, initialization-error, and CPU semantics
remain the behavioral contract and are migrated without relaxation.

## Alternatives considered

1. **Keep the analysis-owned WGPU runtime and mark the gap closed.** Rejected:
   the duplicated device, queue, and buffer ownership remains observable in
   the dependency graph and contradicts the provider boundary.
2. **Make `kwavers-analysis` depend on `kwavers-gpu`.** Rejected: the existing
   `kwavers-gpu → kwavers-analysis` beamforming contract would create a cycle.
3. **Re-export Hephaestus WGPU types from analysis or add forwarding wrappers.**
   Rejected: this retains concrete infrastructure in the domain crate and
   creates a compatibility path rather than deleting the duplicate runtime.
4. **Create a second visualization implementation in a new crate.** Rejected
   for the current increment: it would duplicate the existing public contract
   before a dependency-direction need proves that a new workspace boundary is
   required.
5. **Use a CPU fallback when GPU resources are unavailable.** Rejected: the
   current contract distinguishes requested GPU execution from CPU rendering;
   silent degradation masks capability failures.

## Verification

- Static source audit finds no direct `wgpu`, raw device/resource, or
  `pollster` ownership under `kwavers-analysis`.
- Cargo metadata and locked dependency inspection show one WGPU provider path
  owned by `kwavers-gpu` and no dependency cycle.
- Value-semantic tests cover single-field transfer, multi-field preservation,
  distinct-input sensitivity, unavailable-resource errors, and CPU/GPU
  differential behavior where a real adapter exists.
- `cargo fmt --check`, feature-enabled warning-denied check and Clippy,
  `cargo nextest`, `cargo test --doc`, `cargo doc --no-deps`, and
  `cargo-semver-checks` pass for the affected public surface.
- The Kwavers book gate and hosted Pages deployment pass at the exact merged
  provider default, with the Atlas pointer advanced only after that evidence.

## Consequences

Kwavers has one concrete WGPU runtime owner and the analysis layer becomes
backend-neutral for visualization. The migration is a breaking provider API
change and requires updating in-repository callers in the same increment.
The provider-generic role seam adds compile-time structure, but it removes
the current duplicate WGPU version and prevents future visualization code
from acquiring devices outside the provider boundary.
