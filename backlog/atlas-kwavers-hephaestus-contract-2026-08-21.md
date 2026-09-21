<a id="atlas-kwavers-hephaestus-contract-2026-08-21"></a>
## ATLAS-KWAVERS-HEPHAESTUS-CONTRACT-2026-08-21 — Define the neutral visualization handoff [major][arch] — in-progress
- **outcome:** a backend-neutral visualization handoff contract (backend acquisition, typed field upload, dimensions/range metadata, transfer receipts, typed unavailable-capability errors) replaces Kwavers `kwavers-analysis`'s direct construction of WGPU instances/devices/ queues/buffers and `pollster` waits.
- **decision record:** `docs/adr/0054-kwavers-hephaestus-visualization-contract.md`.
- **ownership:** analysis computes neutral field metadata; Hephaestus owns all concrete WGPU objects/sync; implementation lands at the deepest shared boundary to avoid the `kwavers-gpu -> kwavers-analysis` cycle. Excludes renderer/shader API, CPU fallback, raw handles.
- **next:** provider owners review role signatures and create clean lanes from fetched defaults before any provider source edit.
