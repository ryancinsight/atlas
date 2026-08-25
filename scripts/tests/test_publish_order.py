#!/usr/bin/env python3
"""Tests for committed-gitlink publish graph attribution."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "publish-order.py"
SPEC = importlib.util.spec_from_file_location("publish_order", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
publish_order = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_order)


def _git(directory: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return process.stdout


class PublishOrderTestCase(unittest.TestCase):
    def test_exact_gitlinks_ignore_dirty_provider_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-order-") as temp:
            root = Path(temp) / "atlas"
            provider = root / "repos" / "demo"
            provider.mkdir(parents=True)
            _git(provider, "init", "-q")
            _git(provider, "config", "user.email", "test@example.invalid")
            _git(provider, "config", "user.name", "Atlas Test")
            manifest = provider / "Cargo.toml"
            manifest.write_text(
                '[package]\nname = "committed-demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            _git(provider, "add", "Cargo.toml")
            _git(provider, "commit", "-q", "-m", "initial")
            committed = _git(provider, "rev-parse", "HEAD").strip()

            root.mkdir(parents=True, exist_ok=True)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "test@example.invalid")
            _git(root, "config", "user.name", "Atlas Test")
            (root / ".gitmodules").write_text(
                '[submodule "demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n',
                encoding="utf-8",
            )
            _git(root, "add", ".gitmodules")
            _git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{committed},repos/demo",
            )
            _git(root, "commit", "-q", "-m", "record")
            (root / ".gitmodules").write_text(
                '[submodule "demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n'
                '[submodule "dirty"]\n\tpath = repos/dirty\n\turl = https://example.invalid/dirty.git\n',
                encoding="utf-8",
            )

            manifest.write_text(
                '[package]\nname = "dirty-demo"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            worktree_packages, *_ = publish_order.load_graph(root)
            exact_packages, *_ = publish_order.load_graph(root, exact_gitlinks=True)

            self.assertIn("dirty-demo", worktree_packages)
            self.assertNotIn("committed-demo", worktree_packages)
            self.assertIn("committed-demo", exact_packages)
            self.assertNotIn("dirty-demo", exact_packages)
            self.assertEqual(
                exact_packages["committed-demo"]["manifest"],
                "repos/demo/Cargo.toml",
            )


if __name__ == "__main__":
    unittest.main()
