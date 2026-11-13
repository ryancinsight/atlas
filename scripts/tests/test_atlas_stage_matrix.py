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


def cell(kind: str, position: str, safe: bool, rebuilt: int, killed: bool = True, **more) -> dict:
    return {"shape": "single", "setup": "repush", "kind": kind, "position": position, "safe": safe, "rebuilt": rebuilt,
            "killed": killed, "landed": "tests" if killed else "rustdoc", "why": None if safe else "gen", **more}


class MatrixOracleTestCase(unittest.TestCase):
    def test_compare_names_every_loss_and_skips_the_timing_columns(self) -> None:
        parent = [cell("nextest", "P0", True, 7), cell("doc", "P0", True, 3), cell("data", "KT2", True, 7),
                  cell("none", "P0", True, 7), cell("clippy", "P1", True, 7), cell("none", "KR7", True, 7)]
        head = [cell("doc", "P0", True, 9), cell("data", "KT2", True, 7, killed=False), cell("none", "P0", False, 7),
                cell("clippy", "P1", True, 7, error="boom"), cell("none", "KR7", False, 9, killed=False)]
        self.assertEqual(
            matrix.compare(parent, head),
            ["single/repush/nextest/P0: dropped at the head",
             "single/repush/doc/P0: rebuilds 9 units, parent 3 (liveness)",
             "single/repush/data/KT2: the kill landed at the parent but missed at the head",
             "single/repush/none/P0: green at the parent, red at the head",
             "single/repush/clippy/P1: errored at the head: boom"],
        )


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo") and shutil.which("cargo-nextest"), "needs cargo and cargo-nextest")
class MatrixCellTestCase(unittest.TestCase):
    def test_a_peer_before_the_sequence_is_not_trusted_on_the_tree_under_test(self) -> None:
        result = matrix.Cell(SCRIPT.parents[1], "single", "repush", "nextest", "P0", 1000, None).execute()
        self.assertEqual((result["safe"], result["probe"], result["gens"]), (True, "27", [matrix.EXPECTED["gen"]]), result)
