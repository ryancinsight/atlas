<a id="atlas-publish-graph-2026-08-19"></a>
## ATLAS-PUBLISH-GRAPH-2026-08-19 — crates.io dependency closure — blocked

- `scripts/publish-order.py --json` resolves 182 publishable packages across
  34 dependency layers with zero unresolved edges and no contested names.
- Fourteen publishable packages remain blocked by unpublishable foundations:
  `hyperion` blocks CFDrs, Helios, and Kwavers consumers; `proteus` blocks
  CFDrs, Helios, and Kwavers consumers; `horae` blocks `helios-domain`; and
  `asclepius-coeus` blocks `helios-planning`. These are release-topology
  blockers, not compilation evidence.
- The provider manifests intentionally retain `publish = false`; Horae’s
  board records its occupied registry name, while `hyperion` and `proteus`
  have occupied crates.io names. Renaming/flipping them is a breaking,
  release-authority change and remains an explicit follow-up rather than an
  implicit compatibility rename.

