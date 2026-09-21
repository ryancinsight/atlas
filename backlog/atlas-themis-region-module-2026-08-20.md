<a id="atlas-themis-region-module-2026-08-20"></a>
## ATLAS-THEMIS-REGION-MODULE-2026-08-20 — Split branded region implementation [arch][patch] — in-progress
- **outcome:** Themis `src/branded/region/mod.rs` (481-line file) splits into a manifest (declarations + curated re-exports) and a leaf module (`region/scope.rs`); public exports/safety arguments unchanged; `manifest_implementation` conformance class drops by one.
- **open:** post-merge default runs (MSRV `32473974344`, CI `32473974353`, Pages `32473973059`) were queued at recording. Gitlink and dirty primary checkout stay unchanged until those and the live-page check are terminal.
