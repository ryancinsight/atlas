#!/usr/bin/env python3
"""Linked Atlas worktrees must keep member builds on the primary cache."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-member-target-dir.py"
sys.path.insert(0, str(SCRIPT.parent))
import atlas_target_dir  # noqa: E402
SPEC = importlib.util.spec_from_file_location("atlas_member_target_dir", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target_dir = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target_dir)


def git(directory: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


class SharedTargetWorktreeTestCase(unittest.TestCase):
    @staticmethod
    def cargo_target(lane: Path) -> Path:
        result = subprocess.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1", "--offline"],
            cwd=lane,
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(json.loads(result.stdout)["target_directory"]).resolve()

    def test_generated_member_pin_targets_the_primary_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-worktree-") as temp:
            root = Path(temp) / "primary"
            lane = Path(temp) / "worktrees" / "lane"
            root.mkdir(parents=True)
            git(root, "init", "--quiet")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (root / "README.md").write_text("fixture\n", encoding="utf-8")
            git(root, "add", "README.md")
            git(root, "commit", "--quiet", "-m", "Initialize fixture")
            lane.parent.mkdir(parents=True)
            git(root, "worktree", "add", "--quiet", "--detach", str(lane), "HEAD")
            try:
                expected = target_dir.shared_target_for(root)
                actual = target_dir.shared_target_for(lane)
                self.assertEqual(actual, expected)
                self.assertTrue(os.path.samefile(actual.parent, root))
                self.assertIn(
                    f'target-dir = "{expected.as_posix()}"', target_dir.desired(lane)
                )
            finally:
                git(root, "worktree", "remove", str(lane))

    def test_non_repository_checkout_returns_a_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-outside-") as temp:
            with self.assertRaisesRegex(RuntimeError, "cannot resolve Git common directory"):
                target_dir.shared_target_for(Path(temp))

    def test_lane_config_detects_missing_stale_and_foreign_states(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-lane-") as temp:
            root = Path(temp) / "stack"
            root.mkdir(parents=True)
            git(root, "init", "--quiet", "-b", "main")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (root / "seed").write_text("seed\n", encoding="utf-8")
            git(root, "add", "seed")
            git(root, "commit", "--quiet", "-m", "seed")
            lane_config = root / "worktrees" / ".cargo" / "config.toml"
            with patch.object(target_dir, "ATLAS_ROOT", root), patch.object(
                target_dir, "LANE_CONFIG", lane_config
            ):
                self.assertEqual(target_dir.lane_state(), "missing")
                target_dir.ensure_lane_config(root)
                self.assertEqual(target_dir.lane_state(), "current")
                lane_config.write_text("[build]\ntarget-dir = 'foreign'\n", encoding="utf-8")
                self.assertEqual(target_dir.lane_state(), "foreign")
                lane_config.write_text(target_dir.lane_config_text(root) + "\n", encoding="utf-8")
                self.assertEqual(target_dir.lane_state(), "stale")

    def test_lane_state_rejects_local_and_legacy_target_overrides(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-override-") as temp:
            root = Path(temp) / "stack"
            root.mkdir(parents=True)
            git(root, "init", "--quiet", "-b", "main")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (root / "seed").write_text("seed\n", encoding="utf-8")
            git(root, "add", "seed")
            git(root, "commit", "--quiet", "-m", "seed")
            lane_path = root / "worktrees" / "demo-lane" / ".cargo"
            lane_path.mkdir(parents=True)
            with patch.object(target_dir, "ATLAS_ROOT", root), patch.object(
                target_dir, "LANE_CONFIG", root / "worktrees" / ".cargo" / "config.toml"
            ):
                (lane_path / "config.toml").write_text(
                    "[build]\ntarget-dir = 'escape-toml'\n", encoding="utf-8"
                )
                self.assertEqual(target_dir.lane_state(), "override")
                (lane_path / "config.toml").unlink()
                (lane_path / "config").write_text(
                    "[build]\ntarget-dir = 'escape-legacy'\n", encoding="utf-8"
                )
                self.assertEqual(target_dir.lane_state(), "override")
                (lane_path / "config").unlink()
                legacy = root / "worktrees" / ".cargo" / "config"
                legacy.parent.mkdir(parents=True, exist_ok=True)
                legacy.write_text("[build]\ntarget-dir = 'escape-root-legacy'\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "shadows"):
                    target_dir.ensure_lane_config(root)

    def test_cargo_resolves_all_target_dir_spellings_and_shared_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-target-spellings-") as temp:
            root = Path(temp) / "stack"
            lane = root / "worktrees" / "demo"
            lane.mkdir(parents=True)
            git(root, "init", "--quiet", "-b", "main")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            (lane / "Cargo.toml").write_text(
                "[package]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
                encoding="utf-8",
            )
            (lane / "src").mkdir()
            (lane / "src" / "lib.rs").write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
            target_dir.ensure_lane_config(root)
            shared = target_dir.shared_target_for(root).resolve()
            generated = (root / "worktrees" / ".cargo" / "config.toml").read_text(
                encoding="utf-8"
            )
            target_dir.ensure_lane_config(root)
            self.assertEqual(
                generated,
                (root / "worktrees" / ".cargo" / "config.toml").read_text(encoding="utf-8"),
            )
            self.assertEqual(self.cargo_target(lane), shared)

            spellings = (
                "build.target-dir = 'escape-dotted'\n",
                "[build]\n\"target-dir\" = 'escape-quoted'\n",
                "build = { \"target-dir\" = 'escape-inline' }\n",
            )
            for index, spelling in enumerate(spellings):
                config = lane / ".cargo" / "config.toml"
                config.parent.mkdir(exist_ok=True)
                config.write_text(spelling, encoding="utf-8")
                self.assertEqual(atlas_target_dir.target_dir_override_paths(lane), [config])
                self.assertEqual(
                    self.cargo_target(lane),
                    (lane / f"escape-{('dotted', 'quoted', 'inline')[index]}").resolve(),
                )
                config.unlink()

            legacy = root / "worktrees" / ".cargo" / "config"
            legacy.write_text("[net]\noffline = true\n", encoding="utf-8")
            self.assertEqual(self.cargo_target(lane), (lane / "target").resolve())
            with self.assertRaisesRegex(RuntimeError, "shadows"):
                target_dir.ensure_lane_config(root)


if __name__ == "__main__":
    unittest.main()
