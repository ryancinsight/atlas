#!/usr/bin/env python3
"""Linked Atlas worktrees must keep member builds on the primary cache."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-member-target-dir.py"
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


if __name__ == "__main__":
    unittest.main()
