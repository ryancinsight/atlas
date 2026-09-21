<a id="atlas-modality-003"></a>
## ATLAS-MODALITY-003 — Optical-transport and RF/EM promotion watchpoint [arch] — blocked
outcome: promote the diffusion/Monte-Carlo-RTE optical transport solvers into a standalone `hyperion-transport` crate in a promoted Hyperion workspace, once a second production consumer exists.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §1, §2, §6; refined by [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §5 (RF power/SAR belongs to the shared deposition spine, ATLAS-MODALITY-002; Larmor-frequency RF is a separate MR-acquisition question, out of scope here).
- Blocker: promotion gate conditions 1, 4, 6 unmet — Kwavers is the sole optical-transport consumer (CFDrs has no radiative/optical module, ritk has none, Helios's Hyperion use is a different regime); no RF integrator or second EM consumer exists.
- Re-open trigger: a second production consumer can delete a matching transport implementation in the extraction change.
- Standing exclusion: sonoluminescence (3006 LOC) and photoacoustics (653 LOC) are Kwavers-intrinsic, never in extraction scope; a photomedicine integrator is a separate, demand-gated decision.
