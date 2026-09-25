<a id="atlas-build-source-identity"></a>
## ATLAS-BUILD-SOURCE-IDENTITY — Detect stale artifacts across source trees [patch] — todo
- Status: todo; priority: correctness; scope: ADR 0064, shared source/artifact provenance, build entry points, and checkout coordination.
- Outcome: shared-cache gates consume artifacts from their recorded source tree and revision while preserving one target directory and peer work.
- Evidence: Apollo's retained release macro artifact records no source-tree identity; Cargo's shared proc-macro fingerprint reused the prior revision.
- Acceptance: reproduce a source transition, reject stale artifacts before gate acceptance, rebuild the affected dependency closure, and retain source/artifact identities without changing workloads or cache roots.
- Dependencies: compose the core with the live pre-push lease in PR #277; Apollo's release-artifact repair is delivered.
- Verification: deterministic source/dependency-transition regression, ordinary shared-cache reuse, lock restoration, and concurrent-owner preservation checks; next: run the integrated hook and full gate, then close the item.
