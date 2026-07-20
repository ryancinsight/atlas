# ADR 0027: Centralize exact provider checkout

- Status: Accepted
- Date: 2026-07-20
- Class: `[arch]` `[patch]`

## Context

Kwavers, RITK, and Helios depend on sibling Atlas repositories through Cargo
paths. Their CI must reconstruct that directory topology before Cargo can
resolve metadata.

Kwavers cloned moving Atlas `main` and inferred provider names with `sed`.
RITK duplicated eleven provider URLs and revisions. Apollo duplicated eight
checkouts even though its manifest now uses Git dependencies and has no
external path dependency. Helios had no checkout step, so its hosted build
failed before compilation. These are four inconsistent owners for one provider
graph.

The Atlas commit already records every provider repository twice: `.gitmodules`
owns its URL and the `repos/<provider>` gitlink owns its exact revision.

## Decision

Atlas owns one Rust engine at `tools/checkout-path-dependencies` and one thin
composite action at `.github/actions/checkout-path-dependencies`.

1. The caller supplies its root Cargo manifest, an authorized provider
   destination, and a full 40-character Atlas commit.
2. The engine parses Cargo dependency, patch, and replacement sections. Paths
   inside the consumer repository remain untouched; external paths must
   resolve below `destination/<provider>`.
3. The exact Atlas commit supplies each provider URL and gitlink revision.
   Provider lists, URLs, and revisions are never repeated in consumers.
4. A missing provider is initialized and fetched at the exact gitlink.
   An existing provider is reused only when its `HEAD` matches and its worktree
   is clean.
5. Every declared dependency directory must contain `Cargo.toml` after
   checkout.
6. Consumers invoke the action itself at the same exact Atlas commit. Moving
   branch names are invalid inputs.
7. Apollo deletes its checkout action because Git dependencies resolve from
   `Cargo.lock`; adding the centralized action where no path dependency exists
   would retain dead work.

## Rejected alternatives

- Static consumer-owned checkout lists duplicate URLs and revisions and drift
  independently of the Atlas graph.
- Resolving moving `main` makes a green workflow irreproducible.
- Text extraction with `sed` does not implement Cargo's TOML grammar and can
  misclassify target-specific or inline dependency tables.
- Silently accepting an existing directory at another revision hides
  cross-job contamination.
- Initializing every Atlas submodule downloads repositories outside the
  consumer's dependency closure.

## Consequences

- The action installs the pinned Rust toolchain and compiles a small
  non-published tool before Cargo verification.
- Only providers named by external Cargo paths are downloaded.
- A provider revision advance occurs once in Atlas; consumers advance one
  exact Atlas pin.
- Dirty, stale, unknown, missing-manifest, and destination-escape states fail
  before the consumer build.
- The engine uses Git subprocesses on a cold infrastructure path. No runtime
  simulation code depends on it.

## Verification

- End-to-end tests synthesize local provider and Atlas repositories, discover
  dependency-, patch-, and replacement-only declarations, create a real
  gitlink, check out the exact provider revision, verify a nested dependency
  manifest, and reuse a clean checkout.
- Negative tests reject dirty reuse, wrong-revision reuse, a non-exact Atlas
  reference, a path outside the authorized destination, and a provider absent
  from the graph.
- Format, locked check, ten Nextest cases, one doctest, warning-denied
  Clippy, and warning-clean rustdoc pass.
- Each migrated consumer must pass exact-head hosted CI with the merged Atlas
  action revision.

## Relates to

- ADR 0010: cross-repository integration cadence.
- ADR 0011: Atlas-meta ownership and worktree hygiene.
- ADR 0020: exact provider graph.
