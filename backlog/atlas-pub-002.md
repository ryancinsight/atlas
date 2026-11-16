<a id="atlas-pub-002"></a>
## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — todo
outcome: each of CFDrs/Helios/RITK/kwavers's book workflows becomes a caller of `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only `output-path`, per [ADR 0035](../docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5; each package's Pages deployment succeeds through the shared workflow.
Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books (ATLAS-BOOK-001).
