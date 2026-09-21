<a id="atlas-cfdrs-stale-example-pages-001"></a>
## ATLAS-CFDRS-STALE-EXAMPLE-PAGES-001 - Book example pages for deleted examples [docs] [patch] [S] — todo
- Outcome: docs/book/example pages reference sources that exist and run.
- Found 2026-08-24: the strict pre-commit dead-link gate flags cfd_demo.md and matrix_free_demo.md linking ../../../examples/{cfd,matrix_free}_demo.rs - both .rs files no longer exist, so their Run commands fail too. Pages carry generated-figure markers, so the fix belongs in the generating pipeline (skip examples whose source file is absent), not in hand-edited markdown.
