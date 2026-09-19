<a id="atlas-pub-002"></a>
## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — in-progress

outcome: each of CFDrs/Helios/RITK/kwavers's book workflows becomes a caller of `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only `output-path`, per [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5; each package's Pages deployment succeeds through the shared workflow.

Delivered: `ritk` joined the Atlas cross-book gate (`docs.yml`); CFDrs's `mdbook-linkcheck2` install gap fixed (PRs #339/#340) and its caller merged; Helios (`31716457700`) and Kwavers (`31716399219`) have successful Deploy mdBook runs at their recorded heads.

Open: RITK's Deploy mdBook run `31716974169` remains queued at the historical head `f98a9191` — needs a current-pin run after its caller PR merges, with fresh deployment evidence, before this item closes.

Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books (ATLAS-BOOK-001).
