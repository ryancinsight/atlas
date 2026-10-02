#!/usr/bin/env python3
"""Focused tests for lane-root violation classification."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lane-audit.py"
SPEC = importlib.util.spec_from_file_location("atlas_lane_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
lane = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lane
SPEC.loader.exec_module(lane)


class LaneRootAuditTestCase(unittest.TestCase):
    def test_target_config_reports_missing_stale_and_foreign(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-config-") as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            config = root / "worktrees" / ".cargo" / "config.toml"
            violations: list[str] = []
            with patch.object(lane, "ROOT", root):
                lane.audit_target_config(violations)
                self.assertIn("missing", violations[0])
                config.parent.mkdir(parents=True)
                config.write_text("[build]\ntarget-dir = 'foreign'\n", encoding="utf-8")
                violations.clear()
                lane.audit_target_config(violations)
                self.assertIn("foreign", violations[0])
                config.write_text(lane.lane_config_text(root) + "\n", encoding="utf-8")
                violations.clear()
                lane.audit_target_config(violations)
                self.assertIn("stale", violations[0])

                legacy = root / "worktrees" / ".cargo" / "config"
                legacy.write_text("[build]\ntarget-dir = 'escape-legacy'\n", encoding="utf-8")
                violations.clear()
                lane.audit_target_config(violations)
                self.assertTrue(any("target config override" in item for item in violations))

    def test_lane_local_toml_and_legacy_configs_cannot_override_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-override-") as temp:
            root = Path(temp)
            lane_path = root / "demo-lane"
            (lane_path / ".cargo").mkdir(parents=True)
            violations: list[str] = []
            (lane_path / ".cargo" / "config.toml").write_text(
                "[build]\ntarget-dir = 'escape-toml'\n", encoding="utf-8"
            )
            lane.audit_lane_target_config(lane_path, violations)
            self.assertIn("config.toml", violations[0])
            violations.clear()
            (lane_path / ".cargo" / "config.toml").unlink()
            (lane_path / ".cargo" / "config").write_text(
                "[build]\ntarget-dir = 'escape-legacy'\n", encoding="utf-8"
            )
            lane.audit_lane_target_config(lane_path, violations)
            self.assertIn("config", violations[0])
    def test_archive_directory_is_sanctioned_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lane-") as temp:
            root = Path(temp)
            (root / lane.ARCHIVE_ROOT_NAME).mkdir()
            (root / lane.ARCHIVE_ROOT_NAME / "MANIFEST.txt").write_text(
                "archived lane\n", encoding="utf-8"
            )
            with patch.object(lane, "LANE_ROOT", root):
                violations: list[str] = []
                lane.audit_lane_root(violations)
        self.assertEqual(violations, [])

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
