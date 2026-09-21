<a id="atlas-pub-005"></a>
## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — in-progress
- **outcome:** every published book runs `mdbook test` in CI so chapters cannot rot. Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- **open — helios (H-103):** book's illustrative Rust fragments fail direct `mdbook test docs/book` (missing setup, unresolved imports, non-Rust fenced as Rust); convert snippets before flipping the caller.
- **acceptance per book:** samples compile against the package; caller passes `mdbook-test: true` and, where needed, `atlas-ref`; flip commit demonstrates the gate failing on a broken sample before landing green.
- **dependency:** ATLAS-PUB-002 for that package.
