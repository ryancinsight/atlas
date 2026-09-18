<a id="atlas-runner-starvation-2026-09-02"></a>
## ATLAS-RUNNER-STARVATION-2026-09-02 — Hosted runner queue starves every verification run [infra] — todo (Ask-User)

- **outcome:** hosted CI queue time returns under the five-minute job
  target stack-wide; kwavers `GPU Parity (scheduled)` turns green.
- **status 2026-09-09:** queue is stopped, not slow — nine kwavers runs
  `queued`, zero jobs started, zero self-hosted runners; reads as a
  spending cap, billing stop, or outage. Local pre-push gate still runs
  (kwavers#754, 9s); a workflow-file change has no CI substitute, so
  kwavers#755 stays open.
- **Ask-User:** (1) spending cap/billing stop on the account? (2)
  register self-hosted runners org-wide (`self-hosted, linux, x64`,
  `cuda` on the RTX 5080 host).
- **acceptance oracle:** `gh run list` median queue under 5 min;
  kwavers GPU Parity scheduled row green.
