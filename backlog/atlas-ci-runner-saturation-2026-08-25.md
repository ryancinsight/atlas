<a id="atlas-ci-runner-saturation-2026-08-25"></a>
## ATLAS-CI-RUNNER-SATURATION-2026-08-25 — Hosted-runner queue depth delays every merge gate [patch] — in-progress

- **outcome:** a merge-gate run starts within its own runtime target, so a merge to a default branch is verified in minutes rather than landing unverified for the length of a queue.
- **Still unmet, measured 2026-09-09:** nine atlas runs queued, none started, oldest waiting sixteen minutes — against the five-minute target. Unavailability here is a queue, not an outage; merges proceed on committed-gate PR evidence when the venue is unavailable.
- **Delivered so far** (measurement-first, then per-repo path filters / concurrency-cancel / shared-key rust-cache / job splits): hephaestus, CFDrs, moirai, ritk, helios, kwavers, eunomia, tyche, horae, themis — each merged and gitlink-advanced.
- **next:** consus — fleet's worst queue consumer (3,374 queue-min/wk); shared-key rust-cache lever applied in [consus PR #59](https://github.com/ryancinsight/consus/pull/59) (`808c816`), pending terminal green on the starved runner pool.
- **Acceptance oracle:** queue time for a merge-gate run stays under its own runtime target on a normal fleet day, with the per-repository minutes report (`scripts/atlas-ci-queue-report.py`) showing where the reduction came from.
- **Risk / change class:** [patch], infrastructure. Dependencies: none.
