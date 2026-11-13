#!/usr/bin/env python3
"""Tests for the stage-sequence matrix harness."""

from __future__ import annotations

import importlib.util
import shutil
import unittest
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "atlas_stage_matrix.py"
SPEC = importlib.util.spec_from_file_location("atlas_stage_matrix", SCRIPT)
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)


def cell(kind: str, position: str, safe: bool, rebuilt: int, killed: bool = True) -> dict:
    return {"shape": "single", "setup": "repush", "kind": kind, "position": position, "safe": safe,
            "rebuilt": rebuilt, "killed": killed, "probe": "27" if safe else "16"}


class MatrixOracleTestCase(unittest.TestCase):
    def test_compare_names_a_cell_that_turned_red_and_one_that_rebuilds_more(self) -> None:
        parent = [cell("nextest", "P0", True, 7), cell("doc", "P0", True, 3), cell("data", "P0", False, 2)]
        head = [cell("nextest", "P0", False, 7), cell("doc", "P0", True, 9), cell("data", "P0", True, 2)]
        self.assertEqual(
            matrix.compare(parent, head),
            ["single/repush/nextest/P0: green at the parent, red at the head",
             "single/repush/doc/P0: rebuilds 9 units, parent 3 (liveness)"],
        )

    def test_render_shows_the_probe_of_an_unsound_cell_and_marks_a_kill_that_did_not_land(self) -> None:
        table = matrix.render([cell("nextest", "P1", False, 3), cell("none", "KT7", True, 4, killed=False)])
        self.assertIn("nextest  X(16)/3", table)
        self.assertIn("ok/4~", table)


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo") and shutil.which("cargo-nextest"), "needs cargo and cargo-nextest")
class MatrixCellTestCase(unittest.TestCase):
    def test_a_peer_before_the_sequence_is_not_trusted_on_the_tree_under_test(self) -> None:
        tree = SCRIPT.parents[1]
        result = matrix.Cell(tree, "single", "repush", "nextest", "P0", 1000).execute()
        self.assertEqual((result["safe"], result["probe"], result["doc"]), (True, "27", "2"), result)
        self.assertGreater(result["rebuilt"], 0, "the peer's units were replaced, not trusted")


if __name__ == "__main__":
    unittest.main()
