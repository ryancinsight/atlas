#!/usr/bin/env python3
"""Regression tests for the Atlas ADR index generator."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "adr-index.py"
SPEC = importlib.util.spec_from_file_location("atlas_adr_index", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
adr_index = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adr_index
SPEC.loader.exec_module(adr_index)


class AdrIndexTestCase(unittest.TestCase):
    def test_navigation_index_is_not_parsed_as_an_adr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-index-") as temp:
            directory = Path(temp)
            (directory / "INDEX.md").write_text(
                "# Navigation index\n\nThis is not an ADR.\n", encoding="utf-8"
            )
            (directory / "README.md").write_text("# Generated index\n", encoding="utf-8")
            (directory / "0001-example.md").write_text(
                "# ADR 0001: Example\n\nStatus: Accepted\n", encoding="utf-8"
            )

            content, anomalies = adr_index.build_index(directory)

        self.assertEqual(anomalies, [])
        self.assertIn("0001-example.md", content)
        self.assertNotIn("INDEX.md", content)


if __name__ == "__main__":
    unittest.main()
