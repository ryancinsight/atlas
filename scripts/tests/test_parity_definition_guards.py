"""Reject status-only semantic promotion and wrong-release replay caches."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import atlas_parity as parity
from atlas_parity_evidence import validate_mappings, validate_source_definition
from atlas_parity_schema import ParityError

REPLAY = Path(__file__).resolve().parents[1] / "parity/closure/reproduce.py"
SPEC = importlib.util.spec_from_file_location("parity_closure_reproduce", REPLAY)
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)


class DefinitionPromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = parity.load()

    def test_size_cannot_be_promoted_with_its_unresolved_count_contract(self):
        row = copy.deepcopy(self.bundle["mappings"]["numpy-metadata-size"])
        row["status"]["mapping"] = "specified"
        with self.assertRaisesRegex(ParityError, "retains unresolved obligations"):
            validate_mappings([row], self.bundle["capabilities"],
                              self.bundle["references"], self.bundle["repositories"])

    def test_removing_obligations_does_not_override_bound_source(self):
        for original in self.bundle["mappings"].values():
            row = copy.deepcopy(original)
            row["unresolved_obligations"] = []
            row["status"]["mapping"] = "specified"
            contract = row["source_contract"]
            source = json.loads((parity.DEFAULT / contract["path"]).read_text(encoding="utf-8"))
            for key in contract["entry"]:
                source = source[key]
            with self.subTest(mapping=row["id"]):
                if original["status"]["mapping"] == "partial":
                    with self.assertRaisesRegex(ParityError, "partial or undefined"):
                        validate_source_definition(row, source)
                else:
                    validate_source_definition(row, source)

    def test_removing_source_pointer_cannot_bypass_its_partial_definition(self):
        row = copy.deepcopy(self.bundle["mappings"]["numpy-metadata-size"])
        row["status"]["mapping"] = "specified"
        row["unresolved_obligations"] = []
        del row["source_contract"]
        with self.assertRaisesRegex(ParityError, "source_contract"):
            validate_mappings([row], self.bundle["capabilities"],
                              self.bundle["references"], self.bundle["repositories"])


class FrozenReplayTreeTests(unittest.TestCase):
    def test_cached_and_legacy_tree_identity_is_required_without_network(self):
        expected = "a" * 40
        for legacy in (False, True):
            for actual in (expected, "b" * 40):
                with self.subTest(legacy=legacy, actual=actual), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    destination = root / ("legacy.json" if legacy else "tree.json")
                    destination.write_text(json.dumps({"sha": actual, "truncated": False,
                                                       "tree": [{"path": "source.py"}]}), encoding="utf-8")
                    with patch.object(replay.urllib.request, "urlopen", side_effect=AssertionError("network called")):
                        if actual == expected:
                            replay.tree(root, "tree.json", "example/repo", expected, False,
                                        destination if legacy else None)
                        else:
                            with self.assertRaisesRegex(ValueError, "Frozen source tree mismatch"):
                                replay.tree(root, "tree.json", "example/repo", expected, False,
                                            destination if legacy else None)

    def test_incomplete_cached_tree_cannot_be_accepted(self):
        expected = "a" * 40
        for mutation in ({"truncated": True}, {"truncated": None}, {"tree": []}, {"tree": None}):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = {"sha": expected, "truncated": False, "tree": [{"path": "source.py"}], **mutation}
                (root / "tree.json").write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Truncated source tree"):
                    replay.tree(root, "tree.json", "example/repo", expected, False)


if __name__ == "__main__":
    unittest.main()
