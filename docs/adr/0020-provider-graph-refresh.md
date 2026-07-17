# ADR 0020: Refresh the Kwavers Atlas provider graph

- **Status:** Accepted
- **Date:** 2026-07-17
- **Class:** [arch]

## Context

The Kwavers CI checkout action resolves sibling providers from the fixed
`codex/kwavers-atlas-integration` Atlas branch. That branch pinned an obsolete
RITK batch commit (`b1850302`) whose source does not compile against the
current Coeus/Leto contracts, and it also lagged the merged Apollo,
Hephaestus, and Leto heads. The result was a stale dependency graph even when
the Kwavers change itself passed its package-scoped local gates.

## Decision

Advance the integration branch gitlinks to the provider commits that are
currently used and verified by the consumer work:

| Provider | Commit |
|---|---|
| Apollo | `157467e` |
| Hephaestus | `cf4df20` |
| Kwavers | `2fb8661` |
| Leto | `37968f7` |
| RITK | `a5e375f` |

Apollo remains a consumer of `hephaestus-wgpu`; the graph contains no direct
Apollo-owned `wgpu` dependency. RITK is pinned to its merged compiling default
head, which removes the stale batch source from the CI graph.

## Theorem (provider-graph closure)

Let `G` be the directed dependency graph materialized by the integration
branch, and let `P` be the set of provider gitlinks above. If every edge from a
consumer to a first-party provider resolves to the recorded commit in `P`, and
each recorded commit is reachable from that provider's remote branch, then
the CI checkout action materializes one reproducible provider graph `G(P)`.
No consumer can silently select an older provider revision, because the
checkout action reads the gitlink object from this branch and fetches that
exact object.

The proof obligation is structural (Git object reachability and exact
gitlink equality); compile/test evidence remains the separate behavioral
obligation in the Kwavers pull request.

## Rejected alternatives

- Keep the stale RITK batch pin: rejected because its source emits compile
  errors before any Kwavers test can run.
- Add consumer-local compatibility wrappers: rejected by the provider-first
  ownership and no-shim constraints.
- Change the checkout action to use floating provider defaults: rejected
  because it destroys the reproducible graph this branch exists to pin.
