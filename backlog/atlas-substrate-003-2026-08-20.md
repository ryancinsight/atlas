<a id="atlas-substrate-003-2026-08-20"></a>
## ATLAS-SUBSTRATE-003-2026-08-20 — Give the Leto/Hephaestus decomposition pair one seam and one oracle [minor][arch] — in-progress

The Hephaestus audit found nine duplicated Leto differential helpers in the
decomposition conformance module, a stale 14-method count against the current
15-method `DecompositionOps` seam, and no exact host gate for the complete
surface. This session claims only the provider conformance module, its host
decomposition test, the required provider ADR/index update, and these Atlas PM
records. Other Hephaestus peer edits remain untouched.

Acceptance: one parameterized differential clause covers all current
decomposition methods with tolerances derived from the existing numerical
contract; the stale count is corrected; the host runs the same clause as the
GPU backends; and focused provider formatting, warning-denied checks, and
nextest pass. The exact hosted provider gate remains required before the Atlas
gitlink advances.

Evidence: Hephaestus commit `d24513a` routes the nine Leto differential cases
through `assert_leto_differential_contract`, corrects the host and ADR 0046
count to fifteen, and preserves the shared host clause. Local checks pass:
focused compile, host decomposition nextest (1/1), warning-denied Clippy,
doctests, and direct rustfmt/diff checks. The exact commit is the head of draft
Hephaestus PR [#215](https://github.com/ryancinsight/hephaestus/pull/215);
CUDA, Metal, ROCm, and WGPU hosted checks are queued. The local locked check
remains blocked by the Atlas overlay requesting a dirty provider lockfile
rewrite.

