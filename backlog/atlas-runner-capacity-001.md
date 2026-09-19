<a id="atlas-runner-capacity-001"></a>
## ATLAS-RUNNER-CAPACITY-001 - Size runner slots to fleet width [infra] [patch] — todo

- Outcome: no verification job queued past its own runtime target; runner
  slots sized to fleet width x per-event jobs, or per-event jobs shrunk by
  affected-scope filters (KWAVERS-CI-PIPELINE-001 is the largest shed).
- Evidence 2026-08-24: kwavers queue depth ~10 with one in_progress.
- Status: todo

