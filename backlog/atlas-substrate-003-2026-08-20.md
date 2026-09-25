<a id="atlas-substrate-003-2026-08-20"></a>
## ATLAS-SUBSTRATE-003-2026-08-20 — Give the Leto/Hephaestus decomposition pair one seam and one oracle [minor][arch] — in-progress
outcome: one parameterized differential clause covers every current `DecompositionOps` method with tolerances derived from the existing numerical contract, replacing nine duplicated Leto differential helpers and a stale 14-vs-15-method count; the host runs the same clause as the GPU backends.
Open: head of draft PR [#215](https://github.com/ryancinsight/hephaestus/pull/215) — CUDA/Metal/ROCm/WGPU hosted checks queued; local locked check blocked by the Atlas overlay requesting a dirty provider lockfile rewrite. Atlas gitlink advances only once the exact hosted provider gate is green.
