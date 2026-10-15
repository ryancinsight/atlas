## ATLAS-BOOK-PUBLICATION-AUTHORIZATION [minor] — review

- Owner: `codex/book-publication-authorization`; base Atlas `799880c2`,
  Aequitas `f9c84f8c`; standalone review clones preserve existing stack lanes.
- Contract: book validation and artifact upload run regardless of publication
  authorization. Deploy only after successful validation, a true caller input
  and a non-PR event. The optional input defaults to true for other consumers.
- Aequitas adoption: manual dispatch on main with `publish: true`; dependency
  pushes and PRs retain executable sample validation without publication.
- Design: [ADR 0035](../docs/adr/0035-shared-publication-pipelines.md#caller-authorized-pages-publication).
- Verification: the regression fails against the unchanged base because its
  deploy predicate lacks caller authorization. Focused workflow tests and
  actionlint verify the candidate; exact results are in `checklist.md`.
- Integration order: review Atlas first, then the Aequitas caller pinned to
  the exact tested Atlas commit. This task authorizes neither merge nor Pages
  deployment nor package publication. No gitlink or other caller advances.
- Remaining acceptance: hosted review/checks and separately authorized
  integration; actual Pages publication requires release authorization.
