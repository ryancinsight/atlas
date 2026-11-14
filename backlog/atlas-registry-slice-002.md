<a id="atlas-registry-slice-002"></a>
## ATLAS-REGISTRY-SLICE-002 — Compact the publication pipeline record (ADR 0035, part 2) [patch] — todo
- outcome: ADR 0035's sections 5-8, Consequences, Adoption ledger, Alternatives, Verification and References (main lines 190-381) are replaced by the existing-behavior paragraphs of the head record; est. 250 lines.
- oracle: docs only; the ATLAS-PUB-006 reference stays (still open); a blank line precedes `## Verification`; deleting section 8 is justified by book-pages.yml pinning the Pages actions to SHAs on main (verdict slice 2).
- basis: 2b000c51b; priority: verification; needs: ATLAS-REGISTRY-SLICE-001; pins: none (docs only); scope: `docs/adr/0035-shared-publication-pipelines.md`
- next: take head lines 58-68 and 96-150 minus the evidence-specific lines, which move to ATLAS-REGISTRY-SLICE-014.
- links: slice 2 of the PR 587 verdict (https://github.com/ryancinsight/atlas/pull/587#issuecomment-6866306457); source tree `refs/pull/587/head`; cut from its net diff against main.
