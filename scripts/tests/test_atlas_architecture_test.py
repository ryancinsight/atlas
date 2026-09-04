"""Tests for the ADR 0055 architecture-test rule definitions.

The architecture test is preventive: every balance-domain boundary that
will be added (`ares`, `prometheus`) lands here at its registration
phase. Until then, the rule passes vacuously on the live stack — and
the test suite below proves the rule itself discriminates a forbidden
edge from a sanctioned coupling route, so a future boundary addition
cannot ship with a broken rule.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "atlas_architecture_test.py"
SPEC = importlib.util.spec_from_file_location("atlas_architecture_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
arch = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = arch
SPEC.loader.exec_module(arch)


class BoundaryTableTests(unittest.TestCase):
    """The boundary tables encode ADR 0055 directly. Drift here is an ADR break."""

    def test_balance_domains_is_a_frozenset(self) -> None:
        self.assertIsInstance(arch.BALANCE_DOMAINS, frozenset)

    def test_balance_domains_names_ares_under_both_of_its_names(self) -> None:
        # `ares` registered its Phase 0 on 2026-09-04. Both names are
        # required because the scan reads the two endpoints from
        # different places: a consumer from its `[package] name`
        # (`ares-solid`), a provider from a dependency table key, which
        # downstream is `ares` via the `package =` rename. Listing one
        # form leaves the other silently unmatched.
        self.assertEqual(arch.BALANCE_DOMAINS, frozenset({"ares", "ares-solid"}))

    def test_the_athena_seam_is_not_a_balance_domain(self) -> None:
        # `ares-athena` owns no balance; it adapts the assembled
        # operator to Athena's trait (ares ADR 0001). Listing it would
        # make the intra-repository `ares-athena -> ares` edge a
        # balance-to-balance violation, inverting the rule.
        self.assertNotIn("ares-athena", arch.BALANCE_DOMAINS)
        self.assertFalse(
            arch.classify_edge(
                arch.Edge(consumer="ares-athena", provider="ares")
            ).is_violation()
        )

    def test_prometheus_is_not_yet_a_balance_domain(self) -> None:
        # Chartered under ADR 0058 but not created. It joins at its own
        # registration phase, not before.
        self.assertNotIn("prometheus", arch.BALANCE_DOMAINS)

    def test_coupling_layers_names_harmonia(self) -> None:
        # ADR 0055 R5/R7: coupling routes through `harmonia`. Any other
        # package would be a re-invention of the coupling layer and
        # outside R7's sanctioned route.
        self.assertIn("harmonia", arch.COUPLING_LAYERS)

    def test_coupling_layers_is_a_frozenset(self) -> None:
        self.assertIsInstance(arch.COUPLING_LAYERS, frozenset)

    def test_closure_domains_names_proteus(self) -> None:
        # ADR 0055 names Proteus as the closure layer; balance packages
        # compose Proteus for their material response. The set is
        # documentation today and the seed for a future R3/R4 assertion.
        self.assertIn("proteus", arch.CLOSURE_DOMAINS)


class EdgeClassificationTests(unittest.TestCase):
    """Every edge classifies into exactly one kind; forbidden is unique."""

    def test_edge_is_frozen(self) -> None:
        edge = arch.Edge(consumer="a", provider="b")
        with self.assertRaises(Exception):
            edge.consumer = "c"  # type: ignore[misc]

    def test_finding_kind_is_total(self) -> None:
        # Every classify_edge call returns one of these kinds — never
        # another value, never None. Drift here is a rule break.
        allowed = {
            "allowed",
            "forbidden",
            "closure_consumer",
            "closure_provider",
        }
        for consumer in ("", "a", "x", "CFDrs"):
            for provider in ("", "a", "x", "CFDrs"):
                finding = arch.classify_edge(
                    arch.Edge(consumer=consumer, provider=provider)
                )
                self.assertIn(finding.kind, allowed, f"{consumer}->{provider}")
                self.assertIsInstance(finding, arch.Finding)

    def test_two_non_balance_packages_are_allowed(self) -> None:
        finding = arch.classify_edge(arch.Edge(consumer="kwavers", provider="proteus"))
        self.assertEqual(finding.kind, "allowed")
        self.assertFalse(finding.is_violation())

    def test_an_unlisted_pair_passes_regardless_of_the_balance_set(self) -> None:
        # Today BALANCE_DOMAINS is empty, so no consumer/provider pair
        # is a balance domain. Even an `ares -> CFDrs` edge classifies
        # as `allowed` because neither side is in the empty set. The
        # rule is *preventive*: the first balance-package addition
        # turns this same edge into `forbidden`.
        finding = arch.classify_edge(arch.Edge(consumer="ares", provider="CFDrs"))
        self.assertEqual(finding.kind, "allowed")
        self.assertFalse(finding.is_violation())


class FindingViolationTests(unittest.TestCase):
    """Only `forbidden` edges fail the architecture test."""

    def test_forbidden_is_a_violation(self) -> None:
        finding = arch.Finding(
            edge=arch.Edge(consumer="ares", provider="CFDrs"),
            kind="forbidden",
        )
        self.assertTrue(finding.is_violation())

    def test_allowed_is_not_a_violation(self) -> None:
        finding = arch.Finding(
            edge=arch.Edge(consumer="kwavers", provider="proteus"),
            kind="allowed",
        )
        self.assertFalse(finding.is_violation())

    def test_coupling_routed_is_not_a_violation(self) -> None:
        # A balance->coupling_layer edge is *allowed* because the
        # coupling layer is not itself a balance domain, so the edge
        # is not the R7 prohibition (a direct balance-to-balance
        # edge). Multi-balance coupling is two edges, neither
        # forbidden in isolation.
        finding = arch.Finding(
            edge=arch.Edge(consumer="ares", provider="harmonia"),
            kind="allowed",
        )
        self.assertFalse(finding.is_violation())

    def test_closure_consumer_is_not_a_violation(self) -> None:
        finding = arch.Finding(
            edge=arch.Edge(consumer="proteus", provider="CFDrs"),
            kind="closure_consumer",
        )
        self.assertFalse(finding.is_violation())

    def test_closure_provider_is_not_a_violation(self) -> None:
        finding = arch.Finding(
            edge=arch.Edge(consumer="CFDrs", provider="proteus"),
            kind="closure_provider",
        )
        self.assertFalse(finding.is_violation())


class ForbiddenEdgesTests(unittest.TestCase):
    """The fixture for the rule's failure mode lives here."""

    def test_empty_provider_set_yields_no_edges(self) -> None:
        self.assertEqual(arch.forbidden_edges("ares", frozenset()), [])

    def test_non_balance_consumer_yields_no_forbidden_edges(self) -> None:
        # `kwavers` is not in BALANCE_DOMAINS today; an edge to any
        # other non-balance provider is `allowed`.
        edges = arch.forbidden_edges(
            "kwavers", frozenset({"proteus", "hermes", "moirai"})
        )
        self.assertEqual(edges, [])

    def test_vacuous_passes_with_empty_boundary_table(self) -> None:
        # The empty BALANCE_DOMAINS makes every edge pass. A future
        # boundary addition would turn the same edge set into
        # failures, which is the rule's job — but the test pins the
        # current behaviour so the change is visible.
        edges = arch.forbidden_edges(
            "ares", frozenset({"CFDrs", "kwavers", "prometheus"})
        )
        self.assertEqual(edges, [])


class ScanMemberManifestTests(unittest.TestCase):
    """`scan_member_manifest` returns one Finding per provider, sorted."""

    def test_one_finding_per_provider(self) -> None:
        providers = frozenset({"proteus", "hermes", "moirai"})
        findings = arch.scan_member_manifest("kwavers", providers)
        self.assertEqual(len(findings), 3)

    def test_findings_are_sorted_by_provider(self) -> None:
        # Stable order matters for diffs in CI output: an unsorted
        # list would shuffle between runs and produce noise on every
        # build that has nothing wrong with it.
        providers = frozenset({"zeta", "alpha", "mu"})
        findings = arch.scan_member_manifest("kwavers", providers)
        providers_seen = [f.edge.provider for f in findings]
        self.assertEqual(providers_seen, sorted(providers_seen))

    def test_findings_have_finding_type(self) -> None:
        findings = arch.scan_member_manifest("kwavers", frozenset({"proteus"}))
        for finding in findings:
            self.assertIsInstance(finding, arch.Finding)


class FutureBoundarySimulationTests(unittest.TestCase):
    """Simulate the post-promotion boundary table in-process.

    The point of the test: once `ares` and `prometheus` land in
    `BALANCE_DOMAINS`, the rule must reject direct edges between any
    pair of balance domains and accept the `harmonia` route. The
    simulation builds the boundary table inside the test rather than
    modifying the production constant, so the production table's
    empty state is the source of truth and the test only proves the
    rule's discrimination.
    """

    def _simulate(self) -> tuple[frozenset[str], frozenset[str]]:
        # Replace the module-level sets with simulated values, then
        # restore on exit.
        saved_balance = arch.BALANCE_DOMAINS
        saved_closure = arch.CLOSURE_DOMAINS
        self.addCleanup(
            lambda: _restore_constants(arch, saved_balance, saved_closure)
        )
        arch.BALANCE_DOMAINS = frozenset({"ares", "prometheus", "CFDrs"})
        arch.CLOSURE_DOMAINS = frozenset({"proteus"})
        return arch.BALANCE_DOMAINS, arch.CLOSURE_DOMAINS

    def test_direct_balance_edge_is_forbidden(self) -> None:
        self._simulate()
        finding = arch.classify_edge(
            arch.Edge(consumer="ares", provider="CFDrs")
        )
        self.assertEqual(finding.kind, "forbidden")
        self.assertTrue(finding.is_violation())

    def test_prometheus_to_ares_is_forbidden(self) -> None:
        self._simulate()
        finding = arch.classify_edge(
            arch.Edge(consumer="prometheus", provider="ares")
        )
        self.assertEqual(finding.kind, "forbidden")
        self.assertTrue(finding.is_violation())

    def test_balance_to_coupling_layer_is_allowed(self) -> None:
        # A balance package depending on the coupling layer is
        # sanctioned: the edge is not R7-forbidden because the
        # coupling layer is not itself a balance domain. Multi-balance
        # coupling through `harmonia` is two edges — one from each
        # balance package — neither forbidden in isolation.
        self._simulate()
        finding = arch.classify_edge(
            arch.Edge(consumer="ares", provider="harmonia")
        )
        self.assertEqual(finding.kind, "allowed")
        self.assertFalse(finding.is_violation())

    def test_coupling_layer_to_balance_is_allowed(self) -> None:
        # The reverse direction — coupling layer depending on a balance
        # package — is the second half of the sanctioned route. A
        # `harmonia -> ares` edge is no more forbidden than its
        # mirror.
        self._simulate()
        finding = arch.classify_edge(
            arch.Edge(consumer="harmonia", provider="ares")
        )
        self.assertEqual(finding.kind, "allowed")
        self.assertFalse(finding.is_violation())

    def test_balance_to_closure_is_provider(self) -> None:
        # A balance package correctly composing its material closure.
        self._simulate()
        finding = arch.classify_edge(
            arch.Edge(consumer="CFDrs", provider="proteus")
        )
        self.assertEqual(finding.kind, "closure_provider")
        self.assertFalse(finding.is_violation())

    def test_closure_to_balance_is_consumer(self) -> None:
        # A closure package supplying a balance package's material.
        self._simulate()
        finding = arch.classify_edge(
            arch.Edge(consumer="proteus", provider="CFDrs")
        )
        self.assertEqual(finding.kind, "closure_consumer")
        self.assertFalse(finding.is_violation())

    def test_forbidden_edges_lists_all_violations(self) -> None:
        self._simulate()
        edges = arch.forbidden_edges(
            "ares",
            frozenset({"CFDrs", "prometheus", "harmonia", "proteus", "lethe"}),
        )
        # `ares -> CFDrs` and `ares -> prometheus` are forbidden; the
        # rest are either allowed (proteus), routed (harmonia), or
        # neither a balance nor closure domain (lethe).
        consumers_to_providers = {(e.consumer, e.provider) for e in edges}
        self.assertIn(("ares", "CFDrs"), consumers_to_providers)
        self.assertIn(("ares", "prometheus"), consumers_to_providers)
        self.assertEqual(len(edges), 2)


def _restore_constants(
    module: object, balance: frozenset[str], closure: frozenset[str]
) -> None:
    # `module` is the architecture-test module; reassigning its
    # top-level constants restores the production empty-state boundary
    # tables for subsequent tests in the same process.
    module.BALANCE_DOMAINS = balance  # type: ignore[attr-defined]
    module.CLOSURE_DOMAINS = closure  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()