"""Reject status-only semantic promotion and wrong-release replay caches."""

import copy
import hashlib
import importlib.util
import io
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


class CachedSourceManifestTests(unittest.TestCase):
    def fixture(self, root):
        raw = b"frozen source\n"
        (root / "source.py").write_bytes(raw)
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        manifest = {"revision": "c" * 40, "tree_truncated": False, "selected_count": 1, "verified_count": 1,
                    "files": [{"path": "source.py", "git_blob_sha": blob,
                               "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}]}
        tree = {"sha": "a" * 40, "truncated": False,
                "tree": [{"path": "source.py", "sha": blob, "type": "blob"}]}
        return manifest, tree

    def test_stale_self_consistent_cache_cannot_override_frozen_capture_or_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, tree = self.fixture(root)
            replay.source_files(root, manifest, manifest, tree, "a" * 40, "c" * 40)
            raw = b"other release\n"
            (root / "source.py").write_bytes(raw)
            stale = copy.deepcopy(manifest)
            stale["files"][0].update(git_blob_sha=hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
                                     sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
            with self.assertRaisesRegex(ValueError, "differs from canonical"):
                replay.source_files(root, stale, manifest, tree, "a" * 40, "c" * 40)
            with self.assertRaisesRegex(ValueError, "frozen tree/capture"):
                replay.source_files(root, stale, stale, tree, "a" * 40, "c" * 40)

    def test_undeclared_scanned_file_and_duplicate_manifest_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, tree = self.fixture(root)
            (root / "stale.py").write_bytes(b"stale inherited API")
            with self.assertRaisesRegex(ValueError, "undeclared"):
                replay.source_files(root, manifest, manifest, tree, "a" * 40, "c" * 40)
            (root / "stale.py").unlink()
            manifest["files"] *= 2
            manifest.update(selected_count=2, verified_count=2)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                replay.source_files(root, manifest, manifest, tree, "a" * 40, "c" * 40)

    def test_wrong_manifest_revision_or_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, tree = self.fixture(root)
            for mutation in ({"revision": "b" * 40}, {"selected_count": 0}, {"verified_count": 0}):
                changed = {**manifest, **mutation}
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "revision or selection"):
                    replay.source_files(root, changed, changed, tree, "a" * 40, "c" * 40)


class IsolatedReplayTests(unittest.TestCase):
    def test_relative_work_and_jax_cache_are_absolute_in_children(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(replay.os, "getcwd", return_value=str(root)), \
                    patch.object(replay.sys, "argv", [str(REPLAY), "jax", "--work", "relative", "--source-cache", "jax-cache"]), \
                    patch.object(replay.shutil, "copyfile"), patch.object(replay, "tree"), \
                    patch.object(replay.subprocess, "run") as calls:
                self.assertEqual(replay.main(), 0)
            self.assertEqual(len(calls.call_args_list), 4)
            for call in calls.call_args_list:
                self.assertEqual(call.kwargs["cwd"], root / "relative")
                self.assertEqual(call.kwargs["env"]["ATLAS_REFERENCE_SOURCE_CACHE"], str(root / "jax-cache"))
                self.assertTrue(Path(call.args[0][1]).is_absolute())

    def test_numpy_mirror_check_uses_flat_canonical_artifact(self):
        path = REPLAY.parent / "numpy/verify_closure.py"
        spec = importlib.util.spec_from_file_location("numpy_closure_checks", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["mirror-inventory-2.5.0.json", "source-comparison-2.5.0-to-2.5.4.json"]:
                (root / name).write_bytes((parity.DEFAULT / "reference/closure/numpy" / name).read_bytes())
            with patch.object(module, "ROOT", root):
                module.ResearchArtifactTests("test_old_official_inventory_is_not_relabeled_frozen_patch").debug()

    def test_tf_extra_fetch_helper_runs_entry_path_with_exact_mocked_sources(self):
        script = REPLAY.parent / "tf/fetch_extra.py"
        revision = "a481b10260dfdf833a1b16007eead49c1d7febf3"
        paths = ["tensorflow/core/framework/register_types.h", "tensorflow/core/framework/types.h",
                 "tensorflow/compiler/tf2xla/kernels/fill_op.cc"]
        payloads = {path: path.encode() for path in paths}
        tree = {"sha": revision, "truncated": False, "tree": []}
        for path, raw in payloads.items():
            tree["tree"].append({"path": path, "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tensorflow-tree.json").write_text(json.dumps(tree), encoding="utf-8")
            (root / "tensorflow-source-manifest.json").write_text(json.dumps({"files": []}), encoding="utf-8")
            def response(request, timeout):
                self.assertEqual(timeout, 30)
                return io.BytesIO(payloads[request.full_url.split(revision + "/", 1)[1]])
            with patch.object(replay.urllib.request, "urlopen", side_effect=response) as fetched:
                exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), {"__file__": str(root / script.name)})
            self.assertEqual(fetched.call_count, 3)
            manifest = json.loads((root / "tensorflow-source-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_count"], 3)
            self.assertEqual({row["path"] for row in manifest["files"]}, set(paths))


if __name__ == "__main__":
    unittest.main()
