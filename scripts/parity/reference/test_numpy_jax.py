"""Focused extraction-contract tests; no framework imports or network."""

import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location("numpy_jax", Path(__file__).with_name("numpy_jax.py"))
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)


class DocumentationDeclarationTests(unittest.TestCase):
    def parse(self, text):
        return INVENTORY.parse_document(text, "docs/jax.export.rst", "jax")

    def test_automodule_qualifies_following_autosummary(self):
        records, gaps = self.parse(".. automodule:: jax.export\n\n.. autosummary::\n   :toctree: generated/\n\n   export\n   Exported\n")
        self.assertEqual([record["symbol"] for record in records], ["jax.export", "jax.export.export", "jax.export.Exported"])
        self.assertEqual(gaps[0]["reason"], "autodoc-member-expansion-not-executed")

    def test_explicit_module_and_inline_summary_description(self):
        records, gaps = INVENTORY.parse_document(".. module:: numpy.fft\n\n.. autosummary::\n\n   fft    Discrete Fourier transform.\n   ifft\n\nNext\n----\n", "numpy/fft/__init__.py", "numpy")
        self.assertEqual([record["symbol"] for record in records], ["numpy.fft", "numpy.fft.fft", "numpy.fft.ifft"])
        self.assertEqual(gaps, [])

    def test_c_macros_and_multiline_function_have_stable_names(self):
        records, gaps = INVENTORY.parse_document(".. c:macro:: NPY_ARRAY_OWNDATA\n\n.. c:function:: int PyArray_Pack( \\\n   const PyArray_Descr *descr, void *item, const PyObject *value)\n", "doc/source/reference/c-api/array.rst", "numpy")
        self.assertEqual([record["symbol"] for record in records], ["NPY_ARRAY_OWNDATA", "PyArray_Pack"])
        self.assertEqual(gaps, [])
        self.assertIn("const PyArray_Descr", records[1]["declaration"])

    def test_unparsed_signature_is_a_gap_not_silently_dropped(self):
        records, gaps = self.parse(".. currentmodule:: jax\n.. function:: invalid signature\n")
        self.assertEqual(records, [])
        self.assertEqual(gaps[0]["argument"], "invalid signature")

    def test_autosummary_does_not_consume_following_directive(self):
        records, gaps = self.parse(".. currentmodule:: jax\n.. autosummary::\n\n   grad\n\n.. function:: vjp\n")
        self.assertEqual([record["symbol"] for record in records], ["jax.grad", "jax.vjp"])
        self.assertEqual(gaps, [])

    def test_experimental_and_private_records_are_classified(self):
        self.assertEqual(INVENTORY.stability("jax.experimental.sparse.BCOO"), "experimental-release-documented")
        self.assertEqual(INVENTORY.stability("jax._src.core.Primitive"), "private-name-release-documented")
        self.assertEqual(INVENTORY.stability("numpy.ndarray.__array__"), "release-documented-stability-unreviewed")

    def test_relative_framework_submodule_is_not_external_numpy(self):
        records, gaps = self.parse(".. currentmodule:: jax\n.. autosummary::\n\n   numpy.vectorize\n")
        self.assertEqual(records[0]["symbol"], "jax.numpy.vectorize")
        self.assertEqual(gaps, [])

    def test_explicit_numpydoc_module_separator(self):
        records, gaps = INVENTORY.parse_document(".. autoattribute:: numpy::ma.MaskedArray.data\n", "reference/maskedarray.baseclass.rst", "numpy")
        self.assertEqual(records[0]["symbol"], "numpy.ma.MaskedArray.data")
        self.assertEqual(gaps, [])

    def test_release_arrfuncs_callbacks_and_struct_members_keep_their_identities(self):
        fixture = Path(__file__).with_name("fixtures") / "numpy-native-declarators.rst"
        records, gaps = INVENTORY.parse_document(fixture.read_text(), str(fixture), "numpy")
        symbols = {record["symbol"] for record in records}
        callback_names = {
            "getitem", "setitem", "copyswapn", "copyswap", "compare", "argmax",
            "dotfunc", "scanfunc", "fromstr", "nonzero", "fill", "fillwithscalar",
            "sort", "argsort", "scalarkind", "argmin",
        }
        self.assertTrue({"PyArray_ArrFuncs." + name for name in callback_names} <= symbols)
        self.assertTrue({"PyArrayObject.flags", "PyArrayMethod_Spec.flags",
                         "PyArrayObject.base", "PyArray_DatetimeMetaData.base"} <= symbols)
        self.assertIn("PyArrayMethod_StridedLoop", symbols)
        self.assertNotIn("arr", symbols)
        self.assertNotIn("auxdata", symbols)
        self.assertEqual(len(records), len(symbols))
        self.assertEqual(gaps, [])

    def test_unscoped_members_remain_distinct_source_occurrences_and_gaps(self):
        records, gaps = INVENTORY.parse_document(
            ".. c:member:: PyObject *getitem(void *data, void *arr)\n\n"
            ".. c:member:: int setitem(PyObject *item, void *data, void *arr)\n\n"
            ".. c:member:: int flags\n\n.. c:member:: npy_uint64 flags\n",
            "native.rst", "numpy")
        self.assertEqual([record["native_name"] for record in records], ["getitem", "setitem", "flags", "flags"])
        self.assertEqual(len({record["symbol"] for record in records}), 4)
        self.assertTrue(all(record["scope_resolution"] == "unresolved-source-occurrence" for record in records))
        self.assertEqual([gap["reason"] for gap in gaps], ["native-member-scope-unresolved"] * 4)

    def test_native_scope_ends_when_rst_returns_to_outer_indentation(self):
        records, gaps = INVENTORY.parse_document(
            ".. c:struct:: First\n\n   .. c:member:: int flags\n\n"
            "Unscoped section\n================\n\n.. c:member:: int flags\n",
            "native.rst", "numpy")
        self.assertEqual(records[1]["symbol"], "First.flags")
        self.assertEqual(records[2]["native_name"], "flags")
        self.assertEqual(records[2]["scope_resolution"], "unresolved-source-occurrence")
        self.assertEqual(len(gaps), 1)

    def test_c_callback_pointer_name_and_array_member_not_parameter_or_extent(self):
        records, gaps = INVENTORY.parse_document(
            ".. c:struct:: Callbacks\n\n"
            "   .. c:member:: PyObject *(*getitem)(void *data, void *arr)\n\n"
            "   .. c:member:: int (*setitem)(PyObject *item, void *data, void *arr)\n\n"
            "   .. c:member:: PyArray_VectorUnaryFunc *cast[NPY_NTYPES_LEGACY]\n",
            "native.rst", "numpy")
        self.assertEqual([record["symbol"] for record in records],
                         ["Callbacks", "Callbacks.getitem", "Callbacks.setitem", "Callbacks.cast"])
        self.assertEqual(gaps, [])

    def test_generated_native_inventory_does_not_merge_declaring_types(self):
        # This fails against the reviewed pre-fix artifact: arr held 16 callbacks,
        # while flags/base combined unrelated structures and typedefs lost names.
        import json
        inventory_path = INVENTORY.ROOT / "docs/parity/reference/numpy.json"
        inventory = json.loads(inventory_path.read_text())
        records = {(record["kind"], record["symbol"]): record for record in inventory["records"]}
        self.assertFalse(("c:member", "arr") in records, "callback parameters must not become member identities")
        for symbol in ("PyArray_ArrFuncs.getitem", "PyArray_ArrFuncs.setitem",
                       "PyArray_ArrFuncs.argmin", "PyArrayObject.flags",
                       "PyArrayMethod_Spec.flags", "PyArray_DatetimeMetaData.base"):
            self.assertTrue(("c:member", symbol) in records, symbol)
        self.assertTrue(("c:type", "PyArrayMethod_StridedLoop") in records)
        for (kind, _), record in records.items():
            if kind == "c:member":
                identities = {(item["native_scope"], item["native_name"])
                              for item in record["occurrences"]}
                self.assertEqual(len(identities), 1)


if __name__ == "__main__":
    unittest.main()
