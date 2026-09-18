<a id="atlas-build-source-identity"></a>
## ATLAS-BUILD-SOURCE-IDENTITY — Detect stale artifacts across source trees [patch] — todo
- **Outcome:** shared-cache gates consume artifacts from their recorded source tree and revision.
- **Scope:** Atlas build entry points and checkout coordination; preserve one shared target directory and peer work.
- **Evidence:** Apollo's release macro DLL contains a scratch-checkout path and the old parser diagnostic while the canonical source accepts `scheduled_pairs`; [retained artifacts](output/apollo-square-transpose/integration/composite-schedules/macro-artifact/) establish the mismatch.
- **Acceptance:** reproduce the source-tree transition, detect stale package artifacts before accepting a gate, rebuild only affected packages, and retain source/artifact identities without changing workloads or cache roots.
- **Dependencies:** reconcile the live scratch-checkout producer without discarding its unique work; [Apollo integration](repos/apollo/backlog.md#apollo-codelet-schedule-controls) repairs its affected release artifact now.
- **Verification:** deterministic source-transition regression, ordinary shared-cache reuse, and concurrent-owner preservation checks.

