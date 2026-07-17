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

Advance the Atlas provider gitlinks to merged or explicitly published heads:

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
