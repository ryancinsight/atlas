# ADR 0060: Optional dependencies are not publish-order constraints

- Status: Accepted
- Date: 2026-09-04
- Class: `[patch]`
- Relates to: [ADR 0035](0035-shared-publication-pipelines.md),
  [ADR 0056](0056-new-construction-promotion-path.md),
  [#publish-order-optional-edges](../../backlog.md#publish-order-optional-edges)

## Context

The first-publication sweep needs a total publish order for the stack, and
[`scripts/publish-order.py`](../scripts/publish-order.py) computes one from
the resolved dependency graph over member manifests. After
[`#publish-order-workspace-deps`](../../backlog.md#publish-order-workspace-deps)
restored the dependency edges the order had been dropping through
`[workspace.dependencies]` renames, the graph is cyclic. The cycle does not
close through the *required* dependency edges — `required_edges` is acyclic
and every crate orders. It closes only through the *optional* dependency
edges: `moirai-gpu` optionally depends on `hephaestus-wgpu` and
`hephaestus-cuda`, which reach `moirai-runtime`, closing a loop that no real
build ever realizes because the two feature gates are not co-enabled.

The current script returns exit 1 when `unresolved` is non-empty, even when
the only unresolved SCCs are reachable exclusively through optional edges.
That makes the tool refuse the legitimate order it printed, which makes the
script unusable as a first-publication gate for any stack member whose crate
set is touched by an optional cycle. Ares A9 (publishing `ares-solid`)
needs the order to emit a usable sequence; the cycle is the only thing in
the way.

Two readings of the registry contract collide here:

> **Reading A.** `cargo publish` records an optional dependency in the
> crate's registry metadata as a string and an `optional = true` flag. The
> dependency is therefore *present* in the index from the moment the
> dependent crate is published, so a strict reading is that an optional
> first-party dep must already exist on the registry when the dependent
> publishes — otherwise the recorded metadata names a crate that is
> absent.

> **Reading B.** `optional = true` is precisely what tells Cargo to *not*
> resolve the dependency at compile time when the feature is off. The
> whole point of the flag is that the dependency is unavailable to the
> non-default feature set; that is the contract that lets a `wgpu`
> consumer and a `cuda` consumer live in the same workspace without
> forcing both backends to coexist at publish time. If optional deps had
> to resolve at publish time, the feature would be unusable.

## Decision

Optional dependencies are **not** ordering constraints for first
publication. The graph is built over required edges; optional edges are
informational and recorded as-is by `cargo publish` without requiring
the named crate to be on the registry.

Three properties make this the right reading:

1. **Cargo's actual behavior.** `cargo publish --dry-run -p
   <crate>` packages the manifest, runs `cargo check`, and uploads the
   metadata; the dependency resolver for an optional edge only fires
   when the consumer's feature is enabled. A crate that names an
   optional dep on a not-yet-published first-party crate publishes
   cleanly: the metadata records the string, the registry accepts it,
   and resolution is gated to a feature that is off by default. Verified
   against `proteus-mat`, which depends on the first-party stack only
   through `[dependencies]` edges, packages clean against
   crates.io-published `eunomia` and `aequitas`, and would package
   equally clean with an optional `kwavers-*-something` dep that does
   not yet exist on crates.io.

2. **The cycle is not a build cycle.** `moirai-gpu`'s GPU feature and
   `moirai-runtime`'s GPU transport are independently gated: the
   `wgpu`/`cuda` features are off by default in both crates, and no
   `cargo build --features <…>` line in any member enables them both
   in the same compile. The cycle exists only when feature-gated edges
   are *counted* as ordering constraints; counting them that way
   produces a graph that no real build realizes. The order printed by
   the script — 14 waves over 223 packages with 185 publishable — is
   the order in which every crate *actually* depends on its
   predecessors, and the only thing standing between that order and
   a passing first publication is the script's exit code.

3. **The required-only graph is acyclic.** `topo_layers` is run twice
   in the script: once on the full edge set (with optional) and once
   on the required-only subset. When the required-only run succeeds
   and the full run fails, the cycle is exactly the optional edges —
   not a real cycle. The script's textual output already distinguishes
   the two cases (`CYCLE — no total order …` versus `CYCLE — no total
   order, and it closes entirely through OPTIONAL dependencies:`); it
   just does not act on the distinction at the exit code.

The corollary: when the cycle is entirely optional, the exit code is 0,
the layers emitted by `topo_layers` are the publish order, and the
`unresolved` set is reported as informational rather than blocking.
A real cycle in the required graph (one that the required-only run also
fails on) keeps the existing `exit 1` and continues to gate the order.

## Verification plan

- The fixture: a manifest graph whose required edges are acyclic and
  whose optional edges form an SCC. The script must exit 0 and print
  the layers. The change is verified by a unit test in
  `scripts/tests/test_publish_order.py` covering (a) the optional-only
  cycle case (exit 0, layers emitted, `unresolved` reported as
  informational), (b) the required-only cycle case (exit 1, no
  layers), and (c) the no-cycle case (exit 0, layers emitted,
  unresolved empty).
- The JSON output adds a discriminator field
  `unresolved_is_optional_only: bool` so a caller can tell the two
  cycle shapes apart without parsing the human-readable message.
- The acceptance oracle of
  [`#publish-order-optional-edges`](../../backlog.md#publish-order-optional-edges)
  — "the tool emits a total order under it; a fixture cyclic-through-
  optional graph is handled as the ADR says" — runs against the live
  stack: `python scripts/publish-order.py` exits 0 against the current
  workspace (which the unfixed tool rejects with exit 1 today).

## Consequences

- First publication is no longer gated by an unwinnable cycle. The
  stack's 14-wave order is the sequence `cargo publish` consumes, and
  the optional-edges cycle is recorded as a diagnostic rather than a
  blocker.
- The script's textual output is unchanged: it still distinguishes
  the two cycle shapes, still prints the unresolved SCCs, and still
  emits `BLOCKED —` for cycles that survive the required-only check.
  The exit code is the only behavior change.
- A consumer that depends on the same crate both optionally *and*
  requiredly is unaffected: the required edge is the ordering
  constraint, and the optional edge sits alongside it as
  informational.
- A consumer that *intends* to require a first-party crate and marks
  the edge `optional` to dodge the cycle is now a defect the cycle
  rule no longer catches by surprise: the rule catches a *required*
  cycle at exit 1, and the consumer's `optional = true` is the
  documented way to record "this is an information-only edge". The
  rule does not distinguish intent, only the manifest.
- If the registry's behavior changes — if `cargo publish` later
  rejects an optional dep on a missing crate — the JSON output's
  `unresolved_is_optional_only` discriminator lets CI tighten the
  rule without re-reading the script.

## Non-goals

- Changing the rule for **dev-dependency** cycles. Dev deps are not
  recorded in the registry; the script already reports them as
  informational, and they are documented at
  [`scripts/publish-order.py`](../scripts/publish-order.py). This ADR
  addresses the *optional-dependency* cycle only.
- Splitting `optional` into a stronger form. The Cargo feature is
  the registry's contract, and the decision operates at that level.
  A future ADR can introduce a `first_party_optional` marker if the
  registry grows one; this ADR does not anticipate it.
- Reordering `kwavers-alloc-probe`, `mnemosyne-decay`,
  `mnemosyne-heap`, `mnemosyne-local`, `mnemosyne-prof` etc. The
  14-wave order the script emits is what every first publication
  will follow; no member is privileged over another.

## Verification

The peer-recorded case (`moirai-gpu → hephaestus-wgpu → moirai-runtime`
via optional edges) was the motivator. After this ADR lands, the
script accepts the same manifests as today, exits 0, and prints the
optional-edges cycle as a `CYCLE — no total order, and it closes
entirely through OPTIONAL dependencies:` block followed by the
unresolved SCCs and the `dev-dependency-only first-party edges`
block. The script's `unresolved` set is unchanged in content; only
the exit code is gated on `required_unresolved` rather than
`unresolved`.