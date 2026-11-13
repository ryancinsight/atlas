# ADR 0070: Cargo owns stack package facts

Status: Accepted

## Context

The stack overlay reconstructed Cargo workspace membership, inheritance,
exclusions, versions, path dependencies, and target-specific tables from TOML.
That parallel interpreter diverged from Cargo on valid workspaces and could omit
a provider needed by a selected consumer. Coherence needs facts from exact
revisions without the working-tree overlay or lock mutation.

## Decision

Export every selected Git tree into one immutable `repos/<member>` topology.
Before Cargo executes, reject any implicit ancestor workspace, discovered
manifest, or manifest path input outside those selected exports. Immutable
object reads ignore local replacement refs and archive attributes.
For every committed lock, run bounded `cargo metadata --locked --offline
--no-deps --format-version 1` from a neutral directory. Cargo's records own
package identity and dependency source, requirement, rename, kind, and target.
Pinned and exact-revision callers use immutable selected exports. The overlay's
working mode reads the registered canonical trees live with the same bounded
native declaration parser and source-bound provider projection; its basis names
each repository with no revision and makes no immutable-state claim.

Retain same-name package facts. Provider eligibility is first bound to the Git
repository declared by the dependency source, then exactly one matching
package must exist in that selected export; zero or multiple candidates fail
closed. Export complete source trees rather than fabricating targets for
incomplete snapshots.

## Rejected alternatives

- More TOML interpretation repeats Cargo semantics and the escaped defect.
- Root or workspace-member facts alone miss Git-consumable excluded packages.
- Traversal-order duplicate selection makes coherence nondeterministic.

## Consequences

Every selected manifest and committed lock root must be readable by the pinned
Cargo without mutation. `--no-deps` extracts declarations; it does not prove
that unavailable dependencies, stale locks, or APIs resolve. Separate locked
graph and consumer gates own those claims. This pass performs no compilation,
creates no target cache, and verifies lock bytes remain unchanged.

Revision note (2026-10-29): executable Cargo fixtures disproved the manual
workspace model, so native metadata replaces it.
