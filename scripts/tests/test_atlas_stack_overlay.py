#!/usr/bin/env python3
"""Regression tests for canonical Atlas overlay discovery."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-stack-overlay.py"
_SPEC = importlib.util.spec_from_file_location("atlas_stack_overlay", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_overlay = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_overlay)


class CanonicalOverlayDiscoveryTestCase(unittest.TestCase):
    def test_repo_manifests_excludes_worktrees(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            canonical = root / "repos" / "canonical" / "Cargo.toml"
            alternate = root / "worktrees" / "lane" / "Cargo.toml"
            canonical.parent.mkdir(parents=True)
            alternate.parent.mkdir(parents=True)
            canonical.write_text("[package]\nname = \"canonical\"\nversion = \"1.0.0\"\n", encoding="utf-8")
            alternate.write_text("[package]\nname = \"alternate\"\nversion = \"9.0.0\"\n", encoding="utf-8")

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(_overlay, "registered_member_names", return_value={"canonical"}):
                manifests = _overlay.repo_manifests()

            self.assertEqual(manifests, [canonical])

    def test_unregistered_repo_is_not_an_overlay_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            registered = root / "repos" / "registered" / "Cargo.toml"
            unregistered = root / "repos" / "unregistered" / "Cargo.toml"
            registered.parent.mkdir(parents=True)
            unregistered.parent.mkdir(parents=True)
            registered.write_text("[package]\nname = \"registered\"\nversion = \"1.0.0\"\n", encoding="utf-8")
            unregistered.write_text("[package]\nname = \"unregistered\"\nversion = \"9.0.0\"\n", encoding="utf-8")

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(_overlay, "registered_member_names", return_value={"registered"}):
                manifests = _overlay.repo_manifests()

            self.assertEqual(manifests, [registered])

    def test_workspace_inherited_version_is_resolved_from_registered_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            manifest = root / "repos" / "provider" / "Cargo.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "[package]\nname = \"provider\"\nversion = { workspace = true }\n\n"
                "[workspace]\nmembers = [\".\"]\n\n"
                "[workspace.package]\nversion = \"1.2.3\"\n",
                encoding="utf-8",
            )

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(_overlay, "registered_member_names", return_value={"provider"}):
                packages = _overlay.load_packages()

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.2.3"))

    def test_worktree_package_cannot_replace_canonical_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            canonical = root / "repos" / "provider" / "Cargo.toml"
            consumer = root / "repos" / "consumer" / "Cargo.toml"
            alternate = root / "worktrees" / "provider" / "Cargo.toml"
            for manifest in (canonical, consumer, alternate):
                manifest.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text("[package]\nname = \"provider\"\nversion = \"1.0.0\"\n", encoding="utf-8")
            alternate.write_text("[package]\nname = \"provider\"\nversion = \"9.0.0\"\n", encoding="utf-8")
            consumer.write_text(
                "[package]\nname = \"consumer\"\nversion = \"1.0.0\"\n\n"
                "[dependencies]\nprovider = { version = \"1.0.0\", git = \"https://github.com/ryancinsight/provider\" }\n",
                encoding="utf-8",
            )

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(_overlay, "registered_member_names", return_value={"provider", "consumer"}):
                packages = _overlay.load_packages()
                dependencies = _overlay.collect_first_party_deps()

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.0.0"))
            self.assertEqual(len(dependencies), 1)
            self.assertEqual(dependencies[0][0], "provider")
            self.assertEqual(dependencies[0][3], consumer)


if __name__ == "__main__":
    unittest.main()
