#!/usr/bin/env python3
"""Unit tests for provider integration benchmark scenario setup."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / ".benchmarks"
    / "provider-integration-audit-benchmark.py"
)
SPEC = importlib.util.spec_from_file_location("provider_integration_audit_benchmark", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
bench = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bench
SPEC.loader.exec_module(bench)


class ProviderIntegrationAuditBenchmarkTestCase(unittest.TestCase):
    def test_parse_args_defaults_iterations_to_three(self) -> None:
        parsed = bench.parse_args([])
        self.assertEqual(parsed.iterations, 3)

    def test_iterations_must_be_positive(self) -> None:
        with self.assertRaises(SystemExit):
            bench.parse_args(["--iterations", "0"])

    def test_build_scenarios_matrix(self) -> None:
        scenarios = bench.build_scenarios()
        self.assertEqual(len(scenarios), 3)
        self.assertEqual(
            [scenario.name for scenario in scenarios],
            [
                "requested-2026-08-14 structural-only",
                "requested-2026-08-14 exact-heads (default workers)",
                "requested-2026-08-14 exact-heads (workers=1)",
            ],
        )
        self.assertIn("--structural-only", scenarios[0].command)
        self.assertIn("--exact-heads", scenarios[1].command)
        self.assertNotIn("--exact-head-workers", scenarios[1].command)
        self.assertEqual(scenarios[2].command[-2:], ("--exact-head-workers", "1"))


if __name__ == "__main__":
    unittest.main()
