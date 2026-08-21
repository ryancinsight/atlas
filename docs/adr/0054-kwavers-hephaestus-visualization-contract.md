# ADR 0054: Provider-neutral visualization transfer contract

- Status: Proposed implementation contract
- Date: 2026-08-21
- Class: `[major] [arch]`
- Related: ADR 0051, ADR 0053

## Scope

This contract is intentionally limited to the operations already present in
Kwavers visualization:

1. acquire a visualization backend;
2. upload one field as contiguous `f32` values with dimensions and field kind;
3. expose value range and transfer statistics;
4. report unavailable GPU capability as a typed error.

It does not define a renderer, shader API, CPU fallback, or generalized device
abstraction.

## Roles

A backend-neutral consumer uses these conceptual roles:

```text
VisualizationBackend::open(config) -> Result<BackendSession, VisualizationError>
BackendSession::upload(field: FieldUpload<'_>) -> Result<UploadReceipt, VisualizationError>
BackendSession::capabilities() -> BackendCapabilities
```

`FieldUpload` contains only backend-neutral data:

- `field_kind`: the existing `UnifiedFieldType` vocabulary;
- `dimensions`: `(u32, u32, u32)`;
- `values`: contiguous little-endian `f32` values;
- `value_range`: `(f32, f32)` computed by the consumer before transfer;
- `mode`: blocking, asynchronous, or streaming transfer policy.

`UploadReceipt` reports logical dimensions, byte count, and the selected field
kind. It does not expose a WGPU buffer, queue, adapter, or device.

## Ownership and dependency direction

- Kwavers analysis owns the data conversion, metadata, and neutral role types.
- Hephaestus owns the implementation of `VisualizationBackend`, including all
  WGPU objects and synchronization.
- The implementation must be injected by the provider boundary; analysis must
  not depend on `kwavers-gpu` while `kwavers-gpu` depends on analysis.
- If the current graph prevents this direction, move the neutral role types to
  the deepest existing shared contract crate rather than creating a cycle.
- Hephaestus may depend on the neutral contract crate and implement the roles;
  it must not import analysis's concrete visualization modules.

## Required tests

The first implementation must prove:

- one field upload preserves dimensions and byte count;
- two distinct fields do not collapse into one upload;
- multi-field upload preserves field-kind identity;
- unavailable capability returns the typed error;
- no package graph cycle is introduced;
- static scans find no `wgpu`, `pollster`, raw device, queue, or buffer symbols
  in the neutral consumer module after migration.

These tests are contract tests, not hardware-performance claims. A real
adapter/device test belongs in the Hephaestus hosted WGPU gate.
