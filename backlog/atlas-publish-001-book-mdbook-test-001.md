<a id="atlas-publish-001-book-mdbook-test-001"></a>
## ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001 — Cross-book `mdbook test` gate alignment [patch] — blocked

outcome: each of kwavers/CFDrs/helios `.github/workflows/book-pages.yml` gains a `Test book samples` step (`mdbook test docs/book`) between `Install mdBook` and `Upload Pages artifact`, fail-closed on doctest failure — book deploy stays artifact-based, gated by a passing test step.
- kwavers: blocked on peer's active eviction branch (`codex/kwavers-book-migration-eviction`, ATLAS-BOOK-002) merging to `origin/main` first — eviction removes the least doctest-fit examples, so sequencing it first is cleanest.
- CFDrs: blocked on `ATLAS-CFDRS-COEQ-BLOCKER-1` (workspace restore + check-figures re-verification) so local `mdbook test` runs against a fully-resolved Cargo graph.
- helios: no known prerequisite — cleanest of the three, ready to claim at `origin/main 433ddb6`.
- Coordinator note: each per-repo workflow file is peer-owned; this item surfaces the shared gap and per-repo sub-scopes for each peer to claim disjointly.
- Refs: backlog.md#ATLAS-PUBLISH-001 (parent), backlog.md#ATLAS-BOOK-002, backlog.md#ATLAS-CFDRS-COEQ-BLOCKER-1, backlog.md#ATLAS-HELIOS-BOOK-001.
