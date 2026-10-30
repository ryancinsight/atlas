"""Exact analytical acceptance is distinct from executing a framework scenario."""

import copy
import unittest
from pathlib import Path

from atlas_parity_schema import ParityError, read_json
from atlas_parity_workflow_math import negative_fixture_checks, verify_fixture_truth
from atlas_parity_workflows import instruction_policy, no_execution

ROOT = Path(__file__).resolve().parents[2] / "docs/parity/workflows"


class WorkflowTests(unittest.TestCase):
    def test_independent_rational_fixtures_and_all_malformed_probes(self):
        rows = read_json(ROOT / "analytical-fixtures.json")["fixtures"]
        fixtures = {row["id"]: row for row in rows}
        self.assertEqual(len(fixtures), 14)
        verify_fixture_truth(fixtures)
        rejected = negative_fixture_checks(fixtures)
        self.assertEqual(len(rejected), 12)
        self.assertTrue(all(row["incorrect_fixture_rejected"] for row in rejected))

    def test_source_scenario_cannot_claim_execution_or_mapping_closure(self):
        source = read_json(ROOT / "workflow-contracts.json")
        no_execution(source, "fixture")
        for key, value in {"framework_cases_executed": 1, "api_mapping_credit": 1,
                           "public_surface_complete": True, "semantic_mapping_complete": True}.items():
            changed = copy.deepcopy(source)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ParityError):
                no_execution(changed, "fixture")

    def test_boolean_execution_count_is_not_integer_evidence(self):
        source = read_json(ROOT / "workflow-contracts.json")
        source["framework_cases_executed"] = False
        with self.assertRaisesRegex(ParityError, "expected int"):
            no_execution(source, "fixture")

    def test_trailing_or_mismatched_mathematical_inputs_rejected(self):
        rows = read_json(ROOT / "analytical-fixtures.json")["fixtures"]
        fixtures = {row["id"]: row for row in rows}
        changes = [lambda fx: fx["FX-ARRAY"]["column_offset"].append(7),
                   lambda fx: fx["FX-SCATTER"]["indices"].append(99999),
                   lambda fx: fx["FX-AD"]["v"].append("7"),
                   lambda fx: fx["FX-SOLVE"]["M"].append([1, 2]),
                   lambda fx: fx["FX-INFER"]["X"][0].append(9),
                   lambda fx: fx["FX-COUNTER"]["calls"].clear()]
        for change in changes:
            altered = copy.deepcopy(fixtures)
            change(altered)
            with self.assertRaises(AssertionError):
                verify_fixture_truth(altered)

    def test_unregistered_fixture_cannot_increase_verified_count(self):
        rows = read_json(ROOT / "analytical-fixtures.json")["fixtures"]
        fixtures = {row["id"]: row for row in rows}
        fixtures["FX-NO-TRUTH-CHECK"] = {"id": "FX-NO-TRUTH-CHECK"}
        with self.assertRaisesRegex(AssertionError, "no registered"):
            verify_fixture_truth(fixtures)

    def test_scenario_requires_computation_and_assertion_stages(self):
        self.assertEqual(instruction_policy("WF01", {"id": "WF01-C1"}), ["construct", "compute", "assert"])
        self.assertIn("differentiate", instruction_policy("WF07", {"id": "WF07-C1"}))


if __name__ == "__main__":
    unittest.main()
