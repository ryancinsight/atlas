<a id="atlas-pub-002"></a>
## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — in-progress

- Owner: current session (Atlas coordination); scope: reusable-workflow
  evidence and the CFDrs caller's backend input. Other provider caller files
  and peer-owned working-tree changes are excluded.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5.
- Outcome: each book workflow becomes a caller of
  `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only
  `output-path`.
- **Closed sub-item (2026-07-28):** `ritk` now joins the Atlas cross-book gate —
  `.github/workflows/docs.yml` runs the strict detector and an `mdbook build`
  over all four books. The same change dropped the three per-book HTML artefact
  uploads, leaving `detector.log` as the only retained artefact; that is a
  deliberate narrowing, not a regression, since Pages deployment is the book's
  delivery path and the artefacts were diagnostic only.
- Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books
  (ATLAS-BOOK-001).
- Acceptance: four callers, each passing its audited output path
  (`target/book/cfdrs`, `target/book/helios`, `target/book`,
  `target/book/ritk`); each package's Pages deployment succeeds once through the
  shared workflow.
- **Hosted residual 2026-08-13, closed:** CFDrs run `31716368183` failed during
  the shared build because `book.toml` declares a non-optional
  `[output.linkcheck2]` renderer and the pinned Atlas workflow `d875348` did
  not install it. Root commits `042e448` and `4c31dd7` added the opt-in
  installer and pinned the stable Rust toolchain before `cargo install`. CFDrs
  PRs #339/#340 merged the full root pin, `mdbook-linkcheck2-version: 0.12.2`,
  and `target/book/cfdrs/html`; obsolete PR #338 was closed after verification.
- Helios `31716457700` and Kwavers `31716399219` now have successful Deploy
  mdBook conclusions at their recorded provider heads. RITK `31716974169`
  remains queued at the historical head `f98a9191`, so RITK still requires a
  current-pin run after its caller PR merges. The four current caller PRs must
  still merge and produce fresh deployment evidence before this item closes.

