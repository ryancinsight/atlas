# ADR 0054: Provider-neutral visualization transfer contract

- Status: Accepted
- Date: 2026-08-21 (accepted 2026-08-24)
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
- `kwavers-gpu` owns the provider adapter and stores all concrete transfer
  resources through Hephaestus's typed WGPU device and buffer APIs.
- Hephaestus owns the concrete WGPU objects and synchronization beneath that
  adapter; Kwavers does not construct raw WGPU resources.
- The implementation must be injected by the provider boundary; analysis must
  not depend on `kwavers-gpu` while `kwavers-gpu` depends on analysis.
- The existing dependency direction is retained because the neutral role is
  already owned by `kwavers-analysis`; introducing a reverse dependency would
  create a cycle.
- The adapter must not import analysis's concrete visualization resources.

## Implementation evidence

The accepted implementation is in PR [#602](https://github.com/ryancinsight/kwavers/pull/602),
head `2b9328a12`. `VisualizationTransferProvider` is the neutral role in
`kwavers-analysis`; `VisualizationBackend::{Leto, Hephaestus}` selects the
provider in `kwavers-gpu`, and the top-level `kwavers` feature forwards that
selection to callers. The analysis crate has no production WGPU, raw-device,
queue, buffer, or `pollster` ownership.

The contract tests preserve distinct values and field identities, propagate
provider failures without CPU degradation, and exercise the real Hephaestus
adapter when a WGPU adapter is available. Local exact-head gates passed; hosted
checks remain the merge acceptance gate.

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
