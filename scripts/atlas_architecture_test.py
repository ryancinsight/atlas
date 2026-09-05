"""ADR 0055 architecture-test rule definitions.

The boundary rules in
[ADR 0055](docs/adr/0055-continuum-domain-decomposition.md) are
mechanically checkable, and the checks are the acceptance oracle for any
future continuum-domain promotion. R7 — *no direct balance-to-balance
dependency edge; coupling routes through `harmonia`* — is the rule this
module encodes. R1 and R2 are grep-shaped and belong in the conformance
scan (`scripts/atlas-conformance.py`) rather than here.

The rule was preventive until 2026-09-04, when `ares` registered its
Phase 0 and became the first entry in the boundary list. A forbidden
edge now fails at the merge gate rather than at code review.

Boundary table is encoded directly from ADR 0055's continuum-domain
table:

| Layer | Owner | Conserved quantity | Status |
| --- | --- | --- | --- |
| Balance | `CFDrs` | fluid momentum / mass | live |
| Balance | `kwavers` | acoustic momentum | live |
| Balance | `helios` / `hyperion` | radiative energy | live |
| Balance | `asclepius` | bio-heat | live |
| Closure | `proteus` | n/a (material response) | live |
| Coupling | `harmonia` | n/a (multi-balance router) | live |

| Balance | `ares` | solid momentum | live (2026-09-04) |
| Balance | `prometheus` | species mass | chartered, not created |

`prometheus` joins `BALANCE_DOMAINS` at its own registration. The
calibration point is unchanged: the live stack must pass with no
recorded violations, and the fixture tests below must show the rule
rejects the same edge set a human reviewer would.

The function surface stays small so a future rule (R3, R4, R5, R6) can
sit alongside R7 without disturbing the existing test contracts.

Public surface:

- [`BALANCE_DOMAINS`]: stack packages that own a continuum balance
  operator. Empty today; grows per ADR 0055.
- [`COUPLING_LAYERS`]: stack packages sanctioned as the multi-balance
  coupling route. R7 names `harmonia`; coupling through any other
  package is the defect.
- [`forbidden_edges`]: every direct runtime dependency edge between two
  members of [`BALANCE_DOMAINS`].
- [`is_coupling_edge`]: classify a single edge as allowed /
  forbidden / coupling-routed.
- [`scan_member_manifest`]: read a member's manifest text and return
  every edge classified.

All functions are pure and fixture-testable in isolation; the
conformance-scan integration in `scripts/atlas-conformance.py` is the
only caller in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


# Continuum-balance domain packages — the packages that own a conserved
# quantity's balance operator (ADR 0055 table). Each entry is the
# `Cargo.toml` `[package] name` of the package, which is what the
# runtime-dependency table keys on.
#
# `ares` registered its Phase 0 on 2026-09-04 and is listed here;
# `prometheus` joins at its own registration phase.
#
# Two names for one crate, because the scan reads the two endpoints from
# different places. A consumer is identified by its `[package] name`, so
# `ares` appears as `ares-solid`; a provider is read from a dependency
# table *key*, and downstream consumers write
# `ares = { package = "ares-solid" }`, so the same crate appears there as
# `ares`. Listing one form would leave the other silently unmatched.
#
# `ares-operator` is deliberately absent. It is the Athena operator seam
# (ares ADR 0001) and owns no balance; listing it would make the
# intra-repository `ares-operator -> ares` edge a balance-to-balance
# violation, which is the opposite of the rule's intent.
#
# `BALANCE_DOMAINS` names the *packages* that own balance semantics.
# The member-level view - which stack repositories own a balance
# operator - lives in [`MEMBER_BALANCE_DOMAINS`]. The two are linked:
# adding a member to `MEMBER_BALANCE_DOMAINS` is the *legal* act of
# declaring that member a balance owner; the per-package form exists
# because the scan reads both endpoints by package name. A future
# rename-resolving reader (ADR 0055 R7 follow-on) collapses the two
# names per crate into one; until then both forms are load-bearing.
BALANCE_DOMAINS: frozenset[str] = frozenset({"ares", "ares-solid"})

# Stack members that own a continuum-balance operator per ADR 0055's
# continuum-domain table. Distinct from [`BALANCE_DOMAINS`]: the
# former names repositories, the latter names crates. The scan derives
# the package-to-member mapping from each member's workspace layout
# (every `[package] name` under `repos/<member>/` belongs to that
# member), so the mapping is exact for single-crate members (one
# `[package] name` per member) and works for multi-crate workspaces
# (CFDrs has 12 crates, all members of the CFDrs member).
#
# Adding a member here is a one-line change but carries the
# same-repository exemption in [`classify_member_edge`]: intra-member
# edges between two crates of one balance repo are *not* forbidden,
# because a balance repo's own crates compose the same operator across
# their own decomposition.
MEMBER_BALANCE_DOMAINS: frozenset[str] = frozenset({
    "ares",  # solid momentum, registered 2026-09-04
    # Live balance owners named in ADR 0055's continuum-domain table.
    # Each is a multi-crate workspace; the per-package mapping is
    # populated by the scan from `repos/<member>/...`.
    "CFDrs", "kwavers", "helios", "hyperion", "asclepius",
})

# Coupling layers: stack packages sanctioned as the multi-balance
# coupling route (ADR 0055 R5/R7). Coupling between two balance domains
# through a non-coupling layer is the defect.
COUPLING_LAYERS: frozenset[str] = frozenset({"harmonia"})

# Closure-layer packages (ADR 0055's Proteus role) are never a balance
# domain, so a balance-to-closure edge is allowed by R7. The set is
# named for documentation and future rule expansion; it carries no
# runtime assertion today.
CLOSURE_DOMAINS: frozenset[str] = frozenset({"proteus"})


@dataclass(frozen=True)
class Edge:
    """A resolved direct runtime dependency edge from one stack package to another.

    `consumer` is the package whose `[dependencies]` table names
    `provider`; both names are the `[package] name` keys (i.e., what
    would appear in another member's `Cargo.toml` `[dependencies]`
    table). Edges are *direct* and *runtime* — dev, build, and
    workspace-declaration tables are excluded (see the substrate
    contract's `runtime_dependency_names` for the precise policy).
    """

    consumer: str
    provider: str


@dataclass(frozen=True)
class Finding:
    """One classified edge from the architecture scan.

    `kind` is one of `allowed`, `forbidden`, `closure_consumer`,
    `closure_provider`, `intra_member_allowed`, `external`. The
    package-level [`classify_edge`] returns the first four; the
    member-level [`classify_member_edge`] returns the last two as
    well. `intra_member_allowed` is a balance repo's own crates
    composing the same operator (composition, not coupling); `external`
    marks dependencies whose endpoint lives outside the registered
    stack (third-party crates or unregistered checkouts), which R7 does
    not scope.
    """

    edge: Edge
    kind: str

    def is_violation(self) -> bool:
        """Return whether this finding fails the architecture test.

        Only `forbidden` edges fail; `allowed`, `intra_member_allowed`,
        `external`, and edges to/from closure layers are recorded for
        the audit but never raise. The shape mirrors the substrate
        contract's
        `runtime_dependency_names` set, where the prohibition list and
        the comparison-baseline set are disjoint.
        """
        return self.kind == "forbidden"


def classify_edge(edge: Edge) -> Finding:
    """Classify one resolved edge against the R7 rule.

    The decision tree:

    1. If neither endpoint is a balance domain, the edge is `allowed`
       (no R7 implication). A balance-to-coupling-layer edge falls
       here too: the coupling layer is not itself a balance domain, so
       a single `ares -> harmonia` edge is *not* a balance-to-balance
       edge. Multi-balance coupling through `harmonia` is two edges
       (e.g. `CFDrs -> harmonia` plus `harmonia -> ares`), neither of
       which is R7-forbidden, and the routing property is observable
       from the edge set as a whole, not from a single edge.
    2. If the consumer is a closure domain and the provider is a
       balance domain, the edge is `closure_consumer` — a balance
       package correctly depending on the closure layer.
    3. If the consumer is a balance domain and the provider is a
       closure domain, the edge is `closure_provider` — a balance
       package correctly consuming its material closure.
    4. If both endpoints are balance domains, the edge is `forbidden`
       — the R7 defect. The coupling layer is never a balance domain,
       so the sanctioned route does not introduce any
       `coupling_routed` single-edge classification: the route is
       visible at the edge-set level, not per edge.

    The function is total: every edge lands in exactly one category.
    """
    consumer_is_balance = edge.consumer in BALANCE_DOMAINS
    provider_is_balance = edge.provider in BALANCE_DOMAINS
    consumer_is_closure = edge.consumer in CLOSURE_DOMAINS
    provider_is_closure = edge.provider in CLOSURE_DOMAINS

    if not consumer_is_balance and not provider_is_balance:
        return Finding(edge, "allowed")
    if consumer_is_closure and provider_is_balance:
        return Finding(edge, "closure_consumer")
    if consumer_is_balance and provider_is_closure:
        return Finding(edge, "closure_provider")
    if consumer_is_balance and provider_is_balance:
        return Finding(edge, "forbidden")
    # Balance-to-non-balance, non-closure: a balance package depending
    # on something other than its closure or its own kind (the
    # coupling-layer case above is one example). ADR 0055 does not
    # name these cases; treat them as allowed today and let a future
    # ADR add a sharper rule when one is needed.
    return Finding(edge, "allowed")


def forbidden_edges(
    consumer: str, providers: frozenset[str]
) -> list[Edge]:
    """Every direct runtime dependency edge from `consumer` that fails R7.

    `consumer` is the package whose `[dependencies]` table is being
    scanned; `providers` is the set of stack packages named in that
    table. The function returns the subset that fails R7 — the
    `forbidden` classification under [`classify_edge`]. All other
    classifications are intentionally excluded: a `coupling_routed`
    edge is sanctioned, an `allowed` edge is not in R7's scope.
    """
    out: list[Edge] = []
    for provider in sorted(providers):
        finding = classify_edge(Edge(consumer=consumer, provider=provider))
        if finding.is_violation():
            out.append(finding.edge)
    return out


def classify_member_edge(
    edge: Edge, member_for_package: Mapping[str, str]
) -> Finding:
    """R7 classification at the *member* level.

    Layered on top of [`classify_edge`]: when a balance owner is a
    multi-crate repository (CFDrs has 12 crates, kwavers 22, helios 9,
    ares 2), its own crates depend on each other for composition, not
    coupling. R7 forbids * *cross-balance-member* * edges; intra-member
    edges are composition and stay allowed. The same-repository
    exemption is the substance of the live-balance-domains item; without
    it, naming CFDrs as a balance domain would report every CFDrs
    crate-to-crate edge as an R7 violation.

    Decision tree:

    1. Either endpoint is unknown to the member mapping (lives outside
       the registered stack): return `external`. Cross-stack
       dependencies are not in R7's scope.
    2. Consumer and provider belong to the *same* member:
       `intra_member_allowed`. A balance repo's own crates are
       composition, not coupling.
    3. Consumer and provider belong to *different* members, both in
       [`MEMBER_BALANCE_DOMAINS`]: `forbidden` — the R7 defect. A
       `CFDrs -> kwavers` edge would be the textbook violation.
    4. The consumer's member is a balance domain and the provider's
       member is a closure domain: `closure_provider` — the balance
       package correctly composing its material closure.
    5. The consumer's member is a closure domain and the provider's
       member is a balance domain: `closure_consumer`.
    6. Otherwise (mixed balance + non-balance, non-closure; or
       neither balance): `allowed`.

    The function is total: every edge lands in exactly one category.
    """
    consumer_member = member_for_package.get(edge.consumer)
    provider_member = member_for_package.get(edge.provider)
    if consumer_member is None or provider_member is None:
        return Finding(edge, "external")
    if consumer_member == provider_member:
        return Finding(edge, "intra_member_allowed")
    consumer_is_balance = consumer_member in MEMBER_BALANCE_DOMAINS
    provider_is_balance = provider_member in MEMBER_BALANCE_DOMAINS
    consumer_is_closure = consumer_member in CLOSURE_DOMAINS
    provider_is_closure = provider_member in CLOSURE_DOMAINS
    if consumer_is_balance and provider_is_balance:
        return Finding(edge, "forbidden")
    if consumer_is_closure and provider_is_balance:
        return Finding(edge, "closure_consumer")
    if consumer_is_balance and provider_is_closure:
        return Finding(edge, "closure_provider")
    return Finding(edge, "allowed")


def member_balance_violations(
    consumer: str,
    providers: frozenset[str],
    member_for_package: Mapping[str, str],
) -> list[Edge]:
    """Every member-level forbidden edge from `consumer` to `providers`.

    Thin convenience over [`classify_member_edge`] returning the
    subset that fails R7 at the member level. The fixture tests and
    the conformance scan use this directly.
    """
    out: list[Edge] = []
    for provider in sorted(providers):
        finding = classify_member_edge(
            Edge(consumer=consumer, provider=provider),
            member_for_package,
        )
        if finding.is_violation():
            out.append(finding.edge)
    return out


def build_member_for_package(members: Mapping[str, frozenset[str]]) -> dict[str, str]:
    """Build the package-to-member mapping from a member-to-packages dict.

    Inverse direction: the scan reads every member's workspace and
    builds `{package_name: member_name}` from `{member_name: {packages}}`.
    The mapping is the single source of truth for *intra-repository*
    exemptions — every package name appears at most once (a crate
    belongs to exactly one member).
    """
    out: dict[str, str] = {}
    for member, packages in members.items():
        for package in packages:
            existing = out.get(package)
            if existing is not None and existing != member:
                raise ValueError(
                    f"package {package!r} belongs to both {existing!r} and {member!r}; "
                    "a package name must be unique across the stack"
                )
            out[package] = member
    return out


def scan_member_manifest(
    consumer: str, providers: frozenset[str]
) -> list[Finding]:
    """Classify every direct runtime edge from `consumer` to `providers`.

    Mirrors [`forbidden_edges`] but returns every classification rather
    than only the failing ones. Used by the conformance scan's
    ratchet class to record both the violation count and the
    audit trail of sanctioned/allowed edges.
    """
    return [classify_edge(Edge(consumer=consumer, provider=p)) for p in sorted(providers)]