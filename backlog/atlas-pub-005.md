<a id="atlas-pub-005"></a>
## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — todo
- **outcome:** every published book runs `mdbook test` in CI so chapters cannot rot. Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- **state (live read of default branches, 2026-11-16):** the CFDrs, helios and ritk callers pass `mdbook-test: true`; kwavers passes it on every event except pull requests; gaia's own `book-pages.yml` runs `mdbook test docs/book` itself and does not call the shared workflow.
- **acceptance per book:** samples compile against the package; caller passes `mdbook-test: true` and, where needed, `atlas-ref`; flip commit demonstrates the gate failing on a broken sample before landing green.
- **dependency:** none outstanding; the CFDrs, helios, ritk and kwavers callers use the shared workflow, gaia's does not (state above).
- **per-book prerequisites:** the `mdbook test docs/book` step sits between `Install mdBook` and `Upload Pages artifact`, fail-closed, so the deploy stays artifact-based (the shared `book-pages.yml` input `mdbook-test` is that step).
