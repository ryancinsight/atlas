<a id="atlas-build-source-identity"></a>
## ATLAS-BUILD-SOURCE-IDENTITY — Detect stale artifacts across source trees [patch] — todo
- Status: todo; priority: correctness; scope: shared source/artifact provenance, build entry points, and checkout coordination.
- Outcome: shared-cache gates consume artifacts from their recorded source tree and revision while preserving one target directory and peer work.
- Evidence: Apollo's retained release macro artifact records no source-tree identity; Cargo's shared proc-macro fingerprint reused the prior revision.
- Acceptance: reproduce a source transition, reject stale artifacts before gate acceptance, rebuild only affected packages, and retain source/artifact identities without changing workloads or cache roots.
- Dependencies: compose with the live pre-push lease in PR #277; Apollo's release-artifact repair is already delivered.
- Verification: deterministic source-transition regression, ordinary shared-cache reuse, and concurrent-owner preservation checks.
