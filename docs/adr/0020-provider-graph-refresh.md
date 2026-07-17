# ADR 0020: Refresh the Atlas provider graph

- **Status:** Accepted
- **Date:** 2026-07-17
- **Class:** [arch]

## Context

The Kwavers CI checkout action resolves sibling providers from the fixed
`codex/kwavers-atlas-integration` Atlas branch. That branch had pinned an
obsolete RITK batch commit (`b1850302`) and older Apollo, Hephaestus, Kwavers,
and Leto heads. The stale RITK source failed before Kwavers tests compiled.

## Decision

The initial ATLAS-INTEGRATION-006 graph advanced the Atlas provider gitlinks
to merged or explicitly published heads:

| Provider | Commit |
|---|---|
| Apollo | `157467e` |
| Hephaestus | `cf4df20` |
| Kwavers | `2fb8661` |
| Leto | `37968f7` |
| RITK | `a5e375f` |

Apollo remains a consumer of `hephaestus-wgpu`; no Apollo crate owns a direct
`wgpu` dependency. RITK `a5e375f` is the merged PR #39 head and removes the
non-compiling batch source from the reproducible graph.

The follow-up RITK default-branch head `ffda3ec` corrects the composite
checkout action to select Apollo `157467e`, matching `apollo-fft` 0.24. That
source correction is pinned separately by ATLAS-INTEGRATION-007 after its
cross-platform hosted matrix passes.

## Follow-up graph status (2026-07-17)

Apollo PR #46 and PM closure PR #47 are now merged at `eb46e77`. Their deep
verification-tree change
does not alter the provider boundary: Apollo consumes Hephaestus/Leto and
still owns no direct raw WGPU implementation. The current parent-side
follow-up is therefore:

| Provider | Current or pending commit |
|---|---|
| Apollo | `0b5d11c` (parent update pending) |
| Hephaestus | `df33d4d` |
| Kwavers | PR #293 `203b1a0` (parent update pending hosted closure) |
| Leto | `6a0e297` |
| RITK | `ffda3ec` |

The Kwavers entry remains pending in the parent because Architecture Validation
`29606149255` passes but CI/CD `29606149197` generated its coverage report and
then received external Codecov HTTP 429 rate limiting. PR #293 `203b1a0`
retains the tarpaulin report gate and makes only that external transport
non-blocking; its hosted matrix must pass and merge before the parent pin moves.

## Theorem (provider-graph closure)

Let `G` be the directed graph materialized by the Atlas gitlinks, and let `P`
be the provider set above. If every first-party edge resolves to its recorded
commit in `P`, and each commit is reachable from its provider remote branch,
then the checkout action materializes one reproducible graph `G(P)`. A
consumer cannot silently select an older provider revision because the action
fetches the exact gitlink object.

This is a structural Git proof obligation; compile and test results remain the
behavioral obligation of each consumer pull request.

## Rejected alternatives

- Keep the stale RITK batch pin: rejected because it fails before consumer
  tests compile.
- Add consumer-local compatibility wrappers: rejected by provider-first
  ownership and the no-shim constraint.
- Float provider defaults in CI: rejected because it removes graph
  reproducibility.
