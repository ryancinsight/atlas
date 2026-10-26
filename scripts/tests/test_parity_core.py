"""Adversarial source/status joins for bounded semantic definitions."""

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from atlas_parity import load, program_structure
from atlas_parity_core import no_credit, validate_core_tensor
from atlas_parity_schema import ParityError, finite_number, read_json

ROOT = Path(__file__).resolve().parents[2] / "docs/parity"


class CoreContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load(ROOT)

    def validate(self, mutate=None):
        def altered_read(path):
            data = read_json(path)
            if mutate:
                mutate(path.relative_to(ROOT).as_posix(), data)
            return data
        b = self.bundle
        with patch("atlas_parity_core.read_json", side_effect=altered_read):
            return validate_core_tensor(ROOT, b["program"]["files"]["core_tensor_contracts"],
                b["program"], b["capabilities"], b["repositories"], b["references"],
                b["mappings"], b["assigned"], b["packages"])

    def test_complete_slice_counts_do_not_grant_runtime_credit(self):
        result, _ = self.validate()
        self.assertEqual(result["partial_source_endpoints"], 39)
        self.assertEqual(result["analytical_witnesses"], 8)
        self.assertEqual(result["wrong_value_probes_rejected"], 8)
        self.assertEqual(result["framework_execution_credit"], 0)
        self.assertEqual(result["whole_api_closure_credit"], 0)
        self.assertGreater(result["unrun_acceptance_cases"], result["distinct_unrun_source_programs"])

    def test_typed_status_cannot_hide_promotion_in_zero_like_values(self):
        status = read_json(ROOT / "core-tensor/model.json")["status"]
        for key, value in status.items():
            changed = copy.deepcopy(status)
            changed[key] = 1 if type(value) is int else 0
            with self.subTest(key=key), self.assertRaises(ParityError):
                no_credit(changed)

    def test_owner_identity_case_and_math_mutations_fail_closed(self):
        changes = [
            ("core-tensor/contracts.json", lambda d: d["contracts"][0].update({"owner": "atlas"})),
            ("core-tensor/contracts.json", lambda d: d["contracts"][0].update({"reference_id": "unadmitted"})),
            ("core-tensor/contracts.json", lambda d: d["contracts"][0]["source_endpoint"]["entry"].__setitem__(1, 1)),
            ("core-tensor/contracts.json", lambda d: d["contracts"].pop()),
            ("core-tensor/contracts.json", lambda d: d["contracts"][0].update({"case_ids": []})),
            ("core-tensor/contracts.json", lambda d: d["contracts"][0].update({"semantics": "invented"})),
            ("core-tensor/cases.json", lambda d: d["cases"][0].update({"provider_evidence": "imaginary"})),
            ("core-tensor/cases.json", lambda d: d["cases"][0].update({"source_endpoint_id": "another-api"})),
            ("core-tensor/cases.json", lambda d: d["cases"][0]["original"].update({"expected": "wrong"})),
            ("core-tensor/cases.json", lambda d: d.update({"distinct_source_programs": 999})),
            ("core-tensor/analytical-fixtures.json", lambda d: d["fixtures"][0].update({"expected": [2, 4, 3]})),
            ("core-tensor/analytical-fixtures.json", lambda d: d.update({"framework_execution_credit": True})),
            ("core-tensor/model.json", lambda d: d["clauses"].pop()),
            ("core-tensor/implementation-program.json", lambda d: d["packages"][0]["dependencies"].append("CTWP-05")),
            ("core-tensor/implementation-program.json", lambda d: d["packages"][0].update({"owner": "atlas"})),
            ("core-tensor/implementation-program.json", lambda d: d["packages"][0].update({"done_is_whole_framework_parity": True})),
            ("core-tensor/implementation-program.json", lambda d: d.update({"remaining_full_scope_not_reduced": False})),
            ("core-tensor/implementation-program.json", lambda d: d["packages"][0]["estimate"].update({"engineer_weeks_high": float("inf")})),
        ]
        for path, change in changes:
            with self.subTest(path=path), self.assertRaises(ParityError):
                self.validate(lambda name, data: change(data) if name == path else None)

    def test_pinned_sources_bounds_and_capture_membership_cannot_drift(self):
        changes = [
            ("core-tensor/index.json", lambda d: d.update({"research_captures": []})),
            ("core-tensor/numpy-jax/source-receipts.json", lambda d: next(iter(d["sources"].values())).update({"revision": "f" * 40})),
            ("core-tensor/numpy-jax/source-witnesses.json", lambda d: next(iter(d["witnesses"].values())).update({"text": "invented"})),
            ("core-tensor/torch-tf/line-witnesses.json", lambda d: d["records"][0].update({"line_end": 10 ** 6})),
            ("core-tensor/torch-tf/source-provenance-registry.json", lambda d: d["records"][0].update({"sha256": "f" * 64})),
            ("core-tensor/core-tensor-boundaries.json", lambda d: d["contracts"][0]["status"].update({"design_ADR_approved": True})),
            ("core-tensor/core-tensor-boundaries.json", lambda d: d["source_files"][0].update({"revision": "f" * 40})),
            ("core-tensor/provider-source-witnesses.json", lambda d: d["sources"][0].update({"lines": 1})),
            ("core-tensor/independent-review/torch-tf-core-final-review.json", lambda d: d.update({"reviewed_manifest_sha256": "f" * 64})),
            ("core-tensor/independent-review/torch-tf-core-final-review.json", lambda d: d.update({"blocking_findings": ["unresolved"]})),
        ]
        for path, change in changes:
            with self.subTest(path=path), self.assertRaises(ParityError):
                self.validate(lambda name, data: change(data) if name == path else None)

    def test_manifest_role_and_source_case_conservation_reject_coordinated_edits(self):
        def manifest_role(name, document):
            if name == "core-tensor/numpy-jax/capture.json":
                next(row for row in document["captured"] if row["original_path"] == "benchmarks.json")["original_path"] = "manifest.json"
        with self.assertRaisesRegex(ParityError, "role/path"):
            self.validate(manifest_role)
        first = read_json(ROOT / "core-tensor/cases.json")["cases"][0]

        def drop_source_case(name, document):
            if name == "core-tensor/contracts.json":
                for row in document["contracts"]:
                    row["case_ids"] = [identity for identity in row["case_ids"] if identity != first["id"]]
            elif name == "core-tensor/cases.json":
                document["cases"] = [row for row in document["cases"] if row["id"] != first["id"]]
                document["api_target_views"] -= 1
                document["distinct_source_programs"] -= 1
        with self.assertRaisesRegex(ParityError, "source case views lost"):
            self.validate(drop_source_case)

    def test_all_program_estimates_must_be_finite(self):
        for value in [float("inf"), float("-inf"), float("nan"), True, None, "3"]:
            self.assertFalse(finite_number(value))
        self.assertTrue(finite_number(10 ** 1000))
        changed = copy.deepcopy(self.bundle["packages"])
        changed["WP-005"]["estimate"]["engineer_weeks_high"] = float("inf")
        with self.assertRaisesRegex(ParityError, "estimate range"):
            program_structure(self.bundle["program"], self.bundle["capabilities"], self.bundle["repositories"], changed)

    def test_mapping_test_links_cannot_dangle(self):
        b = self.bundle
        changed = copy.deepcopy(b["mappings"])
        mapping = next(row for row in changed.values() if row["source_contract"]["path"] == "core-tensor/contracts.json")
        mapping["variants"][0]["analytical_tests"] = ["nonexistent-core-case"]
        with self.assertRaisesRegex(ParityError, "mapping case links drift"):
            validate_core_tensor(ROOT, b["program"]["files"]["core_tensor_contracts"], b["program"],
                b["capabilities"], b["repositories"], b["references"], changed, b["assigned"], b["packages"])


if __name__ == "__main__":
    unittest.main()
