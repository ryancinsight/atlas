#!/usr/bin/env python3
"""Decoder and lookup tests for the SCIP search-ladder index tool.

The wire-format fixture is a hand-computed fixed byte string keyed to the
current SCIP protocol (scip-code/scip scip.proto): Index.documents = 2,
Document.relative_path = 1 / occurrences = 2, Occurrence.range = 1
(packed int32) / symbol = 2 / symbol_roles = 3. It is an independent
oracle - the module under test has no encoder, so a wrong field number or
varint rule surfaces as a decode mismatch.
"""
from __future__ import annotations

import gzip
import unittest

import search_ladder_index as sli

# One occurrence: range [10, 20, 25] (0-based line 10, cols 20..25),
# symbol "rust-analyzer cargo test-crate 0.1.0 scan/", roles = Definition.
SYMBOL = b"rust-analyzer cargo test-crate 0.1.0 scan/"
OCCURRENCE = (
    b"\x0a\x03\x0a\x14\x19"  # field 1: packed range 10, 20, 25
    b"\x12\x2a" + SYMBOL  # field 2: symbol (len 42)
    + b"\x18\x01"  # field 3: symbol_roles = 1 (Definition)
)
DOCUMENT = (
    b"\x0a\x0a" + b"src/lib.rs"  # field 1: relative_path
    b"\x12\x33" + OCCURRENCE  # field 2: one occurrence (len 51)
)
INDEX = (
    b"\x12\x41" + DOCUMENT  # field 2: one document (len 65)
)


class DecodeTestCase(unittest.TestCase):
    def test_synthetic_index_decodes(self) -> None:
        docs = sli.decode_index(INDEX)
        self.assertEqual(len(docs), 1)
        path, occs = docs[0]
        self.assertEqual(path, "src/lib.rs")
        self.assertEqual(occs, [(10, 20, 25, "rust-analyzer cargo test-crate 0.1.0 scan/", 1)])

    def test_gzip_framed_index_decodes(self) -> None:
        docs = sli.decode_index(gzip.compress(INDEX))
        self.assertEqual(docs, [( "src/lib.rs", [(10, 20, 25, "rust-analyzer cargo test-crate 0.1.0 scan/", 1)])])

    def test_role_label(self) -> None:
        self.assertEqual(sli.role_label(0x1), "def")
        self.assertEqual(sli.role_label(0), "ref")
        self.assertEqual(sli.role_label(0x9), "def,read")
        self.assertEqual(sli.role_label(0x40), "forward-def")


class FilterTestCase(unittest.TestCase):
    @staticmethod
    def _docs():
        return sli.decode_index(INDEX)

    def test_token_present(self) -> None:
        matches = sli.filter_occurrences(self._docs(), "test-crate", defs_only=False)
        self.assertEqual(len(matches), 1)
        relpath, line, col, symbol, roles = matches[0]
        self.assertEqual((relpath, line, col, symbol, roles), ("src/lib.rs", 10, 20, "rust-analyzer cargo test-crate 0.1.0 scan/", 1))

    def test_token_absent(self) -> None:
        self.assertEqual(sli.filter_occurrences(self._docs(), "no-such-symbol", defs_only=False), [])

    def test_defs_only_keeps_definition(self) -> None:
        matches = sli.filter_occurrences(self._docs(), "test-crate", defs_only=True)
        self.assertEqual(len(matches), 1)

    def test_defs_only_drops_reference(self) -> None:
        # A reference occurrence (roles = 0) must be filtered out.
        occ_ref = b"\x0a\x03\x0a\x14\x19" b"\x12\x2a" + SYMBOL + b"\x18\x00"
        doc_ref = b"\x0a\x0a" + b"src/lib.rs" b"\x12\x33" + occ_ref
        docs = sli.decode_index(b"\x12\x41" + doc_ref)
        self.assertEqual(sli.filter_occurrences(docs, "test-crate", defs_only=True), [])

    def test_format_occurrence(self) -> None:
        line = sli.format_occurrence("leto", "src/lib.rs", 10, 20, "rust-analyzer cargo test-crate 0.1.0 scan/", 1)
        # Role column is right-aligned to width 12; assert the structural parts.
        self.assertTrue(line.startswith("leto  src/lib.rs:11:21"))
        self.assertIn("def", line)
        self.assertTrue(line.endswith("rust-analyzer cargo test-crate 0.1.0 scan/"))


if __name__ == "__main__":
    unittest.main()
