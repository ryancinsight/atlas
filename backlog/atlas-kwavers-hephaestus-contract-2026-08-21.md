<a id="atlas-kwavers-hephaestus-contract-2026-08-21"></a>
## ATLAS-KWAVERS-HEPHAESTUS-CONTRACT-2026-08-21 — Define the neutral visualization handoff [major][arch] — in-progress

- **Owner:** Atlas integration coordination with Hephaestus provider review.
- **Decision record:** `docs/adr/0054-kwavers-hephaestus-visualization-contract.md`.
- **Current evidence:** Kwavers `kwavers-analysis` still constructs WGPU
  instances, adapters, devices, queues, buffers, and `pollster` waits in its
  visualization transfer/renderer modules. Hephaestus exposes backend-neutral
  `ComputeDevice` and backend-specific WGPU implementations, but no existing
  visualization-specific role contract was found.
- **Contract increment:** the proposed seam is limited to backend acquisition,
  typed field upload, dimensions/range metadata, transfer receipts, and typed
  unavailable-capability errors. It deliberately excludes renderer/shader API,
  CPU fallback, and raw device/resource handles.
- **Ownership:** analysis computes neutral field metadata; Hephaestus owns all
  concrete WGPU objects and synchronization. The implementation must be placed
  at the deepest existing shared contract boundary to avoid the current
  `kwavers-gpu -> kwavers-analysis` dependency cycle.
- **Next gate:** provider owners must review the role signatures and create
  clean lanes from fetched defaults before any provider source edit. No dirty
  checkout, branch, lockfile, or Atlas gitlink is changed by this design step.

