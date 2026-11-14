<a id="atlas-registry-slice-001"></a>
## ATLAS-REGISTRY-SLICE-001 — Compact the publication pipeline record (ADR 0035, part 1) [patch] — todo
- outcome: ADR 0035's header, Context, shared-workflows and registry-authentication sections replace main's lines 1-189 (header, Context, source audit, Decisions 1-4), shrinking the Proposed record toward the ADR line budget; est. 240 lines.
- oracle: docs only; the docs/adr/README.md row stays Proposed; `git grep` still finds the caller-filename trusted-publisher rule, crates.io's inability to bootstrap, and the PyPI pending-publisher flow in the record.
- basis: 2b000c51b; priority: verification; needs: none; pins: none (docs only); scope: `docs/adr/0035-shared-publication-pipelines.md`
- next: take head lines 1-5 and 10-57 of the ADR at `refs/pull/587/head`, leaving out the 2026-10-29 revision note (ATLAS-REGISTRY-SLICE-014 owns it).
- links: slice 1 of the PR 587 verdict (https://github.com/ryancinsight/atlas/pull/587#issuecomment-6866306457); source tree `refs/pull/587/head`; cut from its net diff against main.
