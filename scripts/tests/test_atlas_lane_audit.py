#!/usr/bin/env python3
"""Focused tests for lane-root violation classification."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lane-audit.py"
SPEC = importlib.util.spec_from_file_location("atlas_lane_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
lane = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lane
SPEC.loader.exec_module(lane)


class LaneRootAuditTestCase(unittest.TestCase):
    def test_empty_non_linked_directory_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            (root / "orphan-empty").mkdir()
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(violations, [])

    def test_non_empty_non_linked_directory_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            child = root / "orphan-nonempty"
            child.mkdir()
            (child / "sentinel.txt").write_text("x", encoding="utf-8")
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(len(violations), 1)
        self.assertIn("worktrees/orphan-nonempty: not a linked worktree", violations[0])

    def test_gitdir_mirror_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            child = root / "mirror"
            child.mkdir()
            (child / ".git").write_text("gitdir: D:/atlas/repos/kwavers/.git\n", encoding="utf-8")
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(len(violations), 1)
        self.assertIn("hand-wired gitdir mirror", violations[0])


if __name__ == "__main__":
    unittest.main()
