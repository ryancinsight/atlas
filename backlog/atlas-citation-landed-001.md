<a id="atlas-citation-landed-001"></a>
## ATLAS-CITATION-LANDED-001 — Re-cite branch-only hashes as landed commits [patch] — todo
- priority: verification; needs: none; basis: 5e46d75ff; scope: `backlog.md`, `backlog/`, `checklist.md`, `gap_audit.md`, `CHANGELOG.md`, `docs/adr/` of atlas and members. Oracle: per repo, `board_lint.resolve_hashes(..., landed=True)` over its reference artifacts equals `resolve_hashes(...)`: no citation names a commit only a non-default branch reaches, so no sweep can raise `unresolved_references`.
- 59 sites at basis (`<meta>` 37, mostly `checklist.md`). Next: `<meta>`, then one PR per member, re-citing the PR or the landed patch-id match. Then make the count a conformance class; default branches only grow, so it cannot rise without a commit.
