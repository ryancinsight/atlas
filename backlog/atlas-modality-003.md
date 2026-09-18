<a id="atlas-modality-003"></a>
## ATLAS-MODALITY-003 — Optical-transport and RF/EM promotion watchpoint [arch] — blocked

- Owner: unclaimed; scope: watchpoint only — no edits until the trigger fires.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §1, §2, §6.
- Blocker: promotion gate conditions 1, 4, and 6 are unmet. Source audit
  2026-07-27: Kwavers is the sole consumer of the diffusion/Monte-Carlo-RTE
  optical transport solvers (CFDrs has no radiative/optical/photon module;
  ritk has none; Helios consumes Hyperion at MeV, a different regime). No RF
  integrator or second electromagnetics consumer exists.
- Re-open trigger: a second production consumer can delete a matching transport
  implementation in the extraction change. At that point the target is
  `hyperion-transport` as a second crate in a promoted Hyperion workspace — not
  a new package — so the `no_std` law crate keeps its dependency set and Helios
  and CFDrs inherit no array substrate.
- Standing note: sonoluminescence (3 006 LOC) and photoacoustics (653 LOC) are
  Kwavers-intrinsic and are excluded from any extraction scope. A photomedicine
  integrator peer to Helios is a separate, demand-gated decision and is out of
  scope here.
- Refinement 2026-07-28 —
  [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §5: "RF" names two
  unrelated concerns and this watchpoint covers only the first. RF power
  deposition and SAR belong on the shared deposition spine (ATLAS-MODALITY-002),
  where the transport stage is a modality slot and the stages behind it are
  shared. RF at the Larmor frequency for spatial encoding belongs to MR
  acquisition simulation, which is a closed, demand-gated *integrator* question —
  not part of this trigger and not a RITK concern. A proposal that merges the two
  is rejected on bounded-context grounds before the gate is even applied.

