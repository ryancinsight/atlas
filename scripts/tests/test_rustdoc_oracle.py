#!/usr/bin/env python3
"""Type-renderer and scan tests for the rustdoc JSON oracle tool.

The synthetic index mirrors the rustdoc JSON format_version 57 shape the
nightly toolchain emits: `paths` maps item id to {crate_id, path, kind}
and `index` maps item id to the item body carrying `span` and `inner`.
The type shapes exercised here are the variants present in the corpus.
"""
from __future__ import annotations

import unittest

import rustdoc_oracle as ro


class RenderTypeTestCase(unittest.TestCase):
    def test_primitive_and_generic(self) -> None:
        self.assertEqual(ro.render_type({"primitive": "u32"}), "u32")
        self.assertEqual(ro.render_type({"generic": "T"}), "T")

    def test_infer_and_never(self) -> None:
        self.assertEqual(ro.render_type({"infer": None}), "_")
        self.assertEqual(ro.render_type({"never": None}), "!")

    def test_slice(self) -> None:
        self.assertEqual(ro.render_type({"slice": {"primitive": "u8"}}), "[u8]")

    def test_borrowed_ref(self) -> None:
        ty = {"borrowed_ref": {"is_mutable": False, "lifetime": None, "type": {"primitive": "str"}}}
        self.assertEqual(ro.render_type(ty), "&str")
        mut = {"borrowed_ref": {"is_mutable": True, "lifetime": "'a", "type": {"generic": "T"}}}
        self.assertEqual(ro.render_type(mut), "&'a mut T")

    def test_raw_pointer(self) -> None:
        const = {"raw_pointer": {"is_mutable": False, "type": {"primitive": "u8"}}}
        mut = {"raw_pointer": {"is_mutable": True, "type": {"primitive": "u8"}}}
        self.assertEqual(ro.render_type(const), "*const u8")
        self.assertEqual(ro.render_type(mut), "*mut u8")

    def test_resolved_path(self) -> None:
        plain = {"resolved_path": {"path": "SparseLuSolver", "id": "7", "args": None}}
        self.assertEqual(ro.render_type(plain), "SparseLuSolver")
        generic = {"resolved_path": {"path": "Vec", "id": "8", "args": [{"primitive": "f32"}]}}
        self.assertEqual(ro.render_type(generic), "Vec<f32>")

    def test_tuple_and_array(self) -> None:
        self.assertEqual(
            ro.render_type({"tuple": [{"primitive": "f32"}, {"primitive": "f64"}]}), "(f32, f64)"
        )
        self.assertEqual(ro.render_type({"array": {"len": "4", "type": {"primitive": "f32"}}}), "[f32; 4]")

    def test_impl_trait(self) -> None:
        self.assertEqual(ro.render_type({"impl_trait": [{"generic": "T"}]}), "impl T")

    def test_unknown_variant_is_dumped_not_fabricated(self) -> None:
        self.assertEqual(ro.render_type({"mystery": {"x": 1}}), '{"mystery": {"x": 1}}')


class RenderSignatureTestCase(unittest.TestCase):
    def test_signature(self) -> None:
        sig = {
            "inputs": [["a", {"primitive": "u32"}], ["b", {"primitive": "f64"}]],
            "output": {"primitive": "bool"},
            "is_c_variadic": False,
        }
        self.assertEqual(ro.render_signature("foo", sig), "fn foo(a: u32, b: f64) -> bool")

    def test_signature_without_output(self) -> None:
        sig = {"inputs": [], "output": None, "is_c_variadic": False}
        self.assertEqual(ro.render_signature("bar", sig), "fn bar()")


class ScanCrateTestCase(unittest.TestCase):
    @staticmethod
    def _data() -> dict:
        return {
            "paths": {
                "0": {"crate_id": 0, "path": ["demo", "classify", "Direction"], "kind": "enum"},
                "1": {"crate_id": 0, "path": ["demo", "scan", "has_defect"], "kind": "function"},
                "2": {"crate_id": 5, "path": ["gimli", "read", "LineRow"], "kind": "struct"},
            },
            "index": {
                "1": {
                    "name": "has_defect",
                    "span": {"filename": "src/scan.rs", "begin": [262, 1], "end": [268, 2]},
                    "inner": {
                        "function": {
                            "sig": {
                                "inputs": [
                                    [
                                        "path",
                                        {
                                            "borrowed_ref": {
                                                "is_mutable": False,
                                                "lifetime": None,
                                                "type": {"resolved_path": {"path": "Path", "id": "9", "args": None}},
                                            }
                                        },
                                    ]
                                ],
                                "output": {"primitive": "bool"},
                                "is_c_variadic": False,
                            }
                        }
                    },
                }
            },
        }

    def test_substring_match_includes_signature(self) -> None:
        lines = ro.scan_crate(self._data(), "has_defect", exact=False)
        self.assertEqual(len(lines), 1)
        self.assertIn("::demo::scan::has_defect  function  src/scan.rs:262:1", lines[0])
        self.assertIn("fn has_defect(path: &Path) -> bool", lines[0])

    def test_exact_match(self) -> None:
        self.assertEqual(len(ro.scan_crate(self._data(), "demo::scan::has_defect", exact=True)), 1)
        self.assertEqual(ro.scan_crate(self._data(), "has_defect", exact=True), [])

    def test_no_match(self) -> None:
        self.assertEqual(ro.scan_crate(self._data(), "does_not_exist", exact=False), [])


if __name__ == "__main__":
    unittest.main()
