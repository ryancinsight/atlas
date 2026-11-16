<a id="atlas-pub-002"></a>
## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — done
outcome: each of CFDrs/Helios/RITK/kwavers's book workflows becomes a caller of `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only `output-path`, per [ADR 0035](../docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5; each package's Pages deployment succeeds through the shared workflow.
Closed 2026-11-16: RITK's caller merged and Deploy mdBook run `43534192587` (2026-11-14) succeeded on main at `e4bd3567` — build + Pages deploy green through the shared caller at the current pin `book-pages.yml@20c93980`; neither the caller nor the book changed between that run and the main tip, so it stands as current-pin deployment evidence. CFDrs/helios/kwavers callers verified in place (pins `bb505e5e`/`6ed29a95`/`ddee9af1`).
Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books (ATLAS-BOOK-001).
