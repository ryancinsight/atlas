"""Keep source-selection, packaging and parser facts separate from parity."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import atlas_parity as parity
from atlas_parity_dispositions import validate_dispositions
from atlas_parity_schema import ParityError


class SourceDispositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = parity.DEFAULT / "reference/closure"
        cls.index = json.loads((root / "index.json").read_text(encoding="utf-8"))
        cls.data = {row["path"].removeprefix("reference/closure/"):
                    json.loads((parity.DEFAULT / row["path"]).read_text(encoding="utf-8"))
                    for row in cls.index["artifacts"]}

    def validate(self, name=None, mutate=None):
        changed = copy.deepcopy(self.data[name]) if name else None
        if mutate:
            mutate(changed)
        return validate_dispositions(lambda key: changed if key == name else self.data[key], self.index["baselines"])

    def test_bounded_findings_retain_names_and_have_no_parity_credit(self):
        result = self.validate()
        self.assertEqual(sum(result["jax_retained_selector_classes"].values()), 22)
        self.assertEqual(result["keras_saving_retained_names"], 14)
        self.assertEqual(result["semantic_closures"], 0)
        self.assertFalse(result["execution_qualification"])

    def test_jax_filtered_candidate_cannot_be_removed_or_excluded(self):
        for mutate in (lambda d: d["rows"].pop(),
                       lambda d: d["rows"][0].update(public_scope_action="exclude unsupported candidate")):
            with self.assertRaisesRegex(ParityError, "dropped|exclusion"):
                self.validate("jax-selection/selection-dispositions.json", mutate)

    def test_torch_documented_copy_or_runtime_claim_cannot_replace_source_boundary(self):
        for mutate in (lambda d: d["builtin_signature"].update(universal_copy_proven=True),
                       lambda d: d.update(public_api_mapping_complete=True)):
            with self.assertRaisesRegex(ParityError, "contradiction|qualification"):
                self.validate("torch-new-tensor/contract.json", mutate)
        with self.assertRaisesRegex(ParityError, "qualification"):
            self.validate("torch-new-tensor/acceptance-cases.json", lambda d: d["cases"][0].update(status="passed"))

    def test_keras_packaging_does_not_close_import_or_alias_semantics(self):
        for mutate in (lambda d: d["endpoints"].pop(),
                       lambda d: d["endpoints"][1].update(semantic_equivalence_asserted=True),
                       lambda d: d["public_workflow_status"].update(actual_runtime_importability_qualified=True)):
            with self.assertRaisesRegex(ParityError, "dropped|equivalence"):
                self.validate("keras-saving/saving-endpoint-resolution.json", mutate)

    def test_source_audit_cannot_advance_frozen_reference(self):
        with self.assertRaisesRegex(ParityError, "baseline drift"):
            self.validate("jax-selection/selection-dispositions.json", lambda d: d.update(version="99.0"))

    def test_numpy_declaration_cross_products_cannot_hide_missing_or_merged_workflows(self):
        for mutate in (lambda d: d["object_member_expansions"].pop(),
                       lambda d: d["object_member_expansions"][0].update(semantic_merge=True),
                       lambda d: d["public_spelling_member_expansions"].pop()):
            with self.assertRaisesRegex(ParityError, "cross-product|expansion lost"):
                self.validate("numpy-ufunc/ufunc-expansions.json", mutate)

    def test_numpy_private_or_underscored_source_names_cannot_disappear(self):
        for name, mutate in [("numpy-ufunc/ufunc-objects.json", lambda d: d["objects"].pop()),
                             ("numpy-ufunc/ufunc-members.json", lambda d: d["members"].pop())]:
            with self.assertRaisesRegex(ParityError, "count drift"):
                self.validate(name, mutate)

    def test_numpy_source_only_flag_cannot_become_verification(self):
        with self.assertRaisesRegex(ParityError, "cannot qualify parity"):
            self.validate("numpy-ufunc/bounded-completeness.json", lambda d: d.update(implementation_or_runtime_evidence=True))

    def test_active_new_tensor_mapping_binds_correction_instead_of_historical_copy_claim(self):
        bundle = parity.load()
        row = bundle["mappings"]["pytorch-create-tensor-new-tensor"]
        self.assertEqual(row["source_contract"]["path"], "reference/closure/torch-new-tensor/contract.json")
        self.assertEqual(row["status"]["mapping"], "partial")
        self.assertIn("prevent a universal", row["variants"][0]["semantics"])

    def test_replay_seed_rejects_stale_primary_bytes(self):
        path = Path(__file__).resolve().parents[1] / "parity/dispositions/reproduce.py"
        spec = importlib.util.spec_from_file_location("disposition_reproduce", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / "source", root / "cache"
            source.write_bytes(b"frozen")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            module.seed(source, destination, expected)
            destination.write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError, "differs from versioned source receipt"):
                module.seed(source, destination, expected)


if __name__ == "__main__":
    unittest.main()
