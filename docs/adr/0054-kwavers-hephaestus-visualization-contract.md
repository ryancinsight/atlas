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

The accepted implementation is in merged PR [#602](https://github.com/ryancinsight/kwavers/pull/602),
source head `2b9328a12`, merge `41f1c8047`. `VisualizationTransferProvider` is the neutral role in
`kwavers-analysis`; `kwavers-gpu` owns the concrete Leto and Hephaestus
providers. The analysis crate has no production WGPU, raw-device, queue,
buffer, or `pollster` ownership.

The contract tests preserve distinct values and field identities, propagate
provider failures without CPU degradation, and exercise the real Hephaestus
adapter when a WGPU adapter is available. Merged follow-up PR [#626](https://github.com/ryancinsight/kwavers/pull/626)
(`871341d62`) adds transactional state updates so a failed upload cannot commit
metadata, buffer replacement, memory accounting, or streaming-buffer selection.
Merged documentation follow-up PR [#628](https://github.com/ryancinsight/kwavers/pull/628)
(`c11b64491`) resolves the affected transfer RustDoc links under
`rustdoc -D warnings`.

Revision 2026-08-24: provider ownership alone did not satisfy the composition
contract because `kwavers` merely re-exported selection implemented by
`kwavers-gpu`. Follow-up PR [#630](https://github.com/ryancinsight/kwavers/pull/630),
source head `6b344eb5f`, moves `VisualizationBackend::{Leto, Hephaestus}` and
the selection factory to top-level `kwavers`; the provider implementations
remain in `kwavers-gpu`, and Hephaestus remains the sole owner of WGPU resource
construction. The requested Hephaestus path fails closed and performs a real
device transfer in the scheduled self-hosted GPU gate. Local exact-head Leto
and Hephaestus contract tests pass. `cargo-semver-checks` reports the two
removed `kwavers-gpu` selection items and therefore confirms the declared
major-version impact. PR #630 merged as `40e482ee9` from the exact tested
source tree.

Independent review then found that the factory returned
`Box<dyn VisualizationTransferProvider>` and retained that vtable through each
engine-to-pipeline transfer. Fix-forward PR
[#631](https://github.com/ryancinsight/kwavers/pull/631), source
`a36cb1ea2`, merge `c7db87a74`, replaces the open trait object with the closed
`VisualizationProvider::{Leto, Hephaestus}` enum. The large Hephaestus variant
is boxed once for layout control; transfer dispatch remains exhaustive enum
dispatch. `VisualizationEngine<P>` and `DataPipeline<P>` retain the concrete
provider type, and the unconfigured engine typestate cannot initialize GPU
transfer. No fallback is added: requested Hephaestus acquisition, upload, or
synchronization failures remain typed errors. The merge and source trees are
identical (`d95f04a991b7a94c11c41318b469cb556b7190be`). Local full CPU and GPU
Nextest suites, the real-adapter transfer oracle, doctests including the
compile-fail typestate proof, warning-denied Rustdoc, and no-default-features
compilation pass. The hosted PR #631 matrix remains queued; no hosted-green
claim is made.

Evidence follow-up PR
[#632](https://github.com/ryancinsight/kwavers/pull/632), source
`6f400e1a9`, merge `534051c04`, extends the scheduled real-adapter oracle
through top-level Kwavers selection and analysis `DataPipeline` conversion
before the Hephaestus upload. It preserves the physical double-buffer memory
assertion and adds exact pipeline dimensions, value range, and logical byte
count for a distinct second upload. The source and merge trees are identical
(`6e104e339ed3731fccee8f7192678b39ffe7f192`). Local real-hardware, normal
library, warning-denied Clippy, formatting, and workflow-shape gates pass; its
hosted matrix remains queued.

## Required tests

The first implementation must prove:

- one field upload preserves dimensions and byte count;
- two distinct fields do not collapse into one upload;
- multi-field upload preserves field-kind identity;
- unavailable capability returns the typed error;
- a failed transfer does not commit backend-neutral or provider-owned state;
- no package graph cycle is introduced;
- top-level Kwavers selection reaches both concrete providers without a
  compatibility re-export or fallback;
- the closed provider set dispatches by enum at the operation boundary, with
  no `dyn VisualizationTransferProvider` retained by the engine or pipeline;
- an unconfigured engine cannot initialize GPU transfer;
- the scheduled Hephaestus test requires a real adapter and device transfer;
- static scans find no `wgpu`, `pollster`, raw device, queue, or buffer symbols
  in the neutral consumer module after migration.

These tests are contract tests, not hardware-performance claims. The real
adapter/device test runs in the scheduled Hephaestus hosted WGPU gate.
