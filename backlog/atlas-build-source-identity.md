<a id="atlas-build-source-identity"></a>
## ATLAS-BUILD-SOURCE-IDENTITY — Detect stale artifacts across source trees [patch] — todo
- Status: todo; priority: correctness; scope: ADR 0064, shared source/artifact provenance, build entry points, and checkout coordination.
- Outcome: shared-cache gates consume artifacts from their recorded source tree and revision while preserving one target directory and peer work.
- Evidence: Apollo's retained release macro artifact records no source-tree identity; Cargo's shared proc-macro fingerprint reused the prior revision.
- Acceptance: reproduce a source transition, reject stale artifacts before gate acceptance, rebuild the affected dependency closure, and retain source/artifact identities without changing workloads or cache roots.
- Dependencies: compose the core with the live pre-push lease in PR #277; Apollo's release-artifact repair is delivered.
- Verification: 30 core identity tests, 16 hook-publisher tests, 48 pre-push gate tests, and the full scripts suite (1028 passed, 2 skipped, 136 subtests) are green; next: collect the four member hook PRs, advance their gitlinks, and merge PR #299.
