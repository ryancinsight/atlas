<a id="atlas-publish-graph-2026-08-19"></a>
## ATLAS-PUBLISH-GRAPH-2026-08-19 — crates.io dependency closure — blocked
outcome: all 182 publishable packages across 34 dependency layers publish to crates.io with zero unresolved edges.
`scripts/publish-order.py --json` already resolves that graph cleanly. Publish is blocked on 14 packages behind unpublishable foundations: `hyperion` and `proteus` each block CFDrs/Helios/Kwavers consumers, `horae` blocks `helios-domain`, and `asclepius-coeus` blocks `helios-planning` — a release-topology gap, not a compilation defect.
Blocker: `hyperion`/`proteus` occupy contested crates.io names and `horae`'s occupied name is tracked on its own board; all three manifests intentionally keep `publish = false`. Renaming/flipping any of them is a breaking, release-authority change and is an explicit follow-up, never an implicit compatibility rename.
