<a id="atlas-runner-starvation-2026-09-02"></a>
## ATLAS-RUNNER-STARVATION-2026-09-02 — Hosted runner queue starves every verification run [infra] — todo (Ask-User)
- **outcome:** hosted CI queue time returns under the five-minute job target stack-wide; kwavers `GPU Parity (scheduled)` turns green.
- **Ask-User:** (1) spending cap/billing stop on the account? (2) register self-hosted runners org-wide (`self-hosted, linux, x64`, `cuda` on the RTX 5080 host).
- **acceptance oracle:** `gh run list` median queue under 5 min; kwavers GPU Parity scheduled row green. Evidence 2026-09-23: job queue is twice the work it waits for (ATLAS-CI-RUNNER-SATURATION-2026-08-25).
