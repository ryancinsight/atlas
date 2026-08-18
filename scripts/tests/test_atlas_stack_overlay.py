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


class LagAwarePatchEmissionTestCase(unittest.TestCase):
    """generate must not patch a git dep to a local version that conflicts
    with a member's manifest pin; lagging edges resolve from git instead."""

    def test_generate_skips_edge_that_violates_a_member_pin(self) -> None:
        packages = {"ritk-image": (Path("repos/ritk/crates/ritk-image"), "0.4.0")}
        deps = [
            (
                "ritk-image",
                "https://github.com/ryancinsight/ritk",
                "^0.3.0",
                Path("repos/kwavers/Cargo.toml"),
            )
        ]
        with patch.object(_overlay, "collect_first_party_deps", return_value=deps):
            block, missing, lag = _overlay.build_overlay(packages)
        self.assertEqual(block, "\n")
        self.assertEqual(missing, [])
        self.assertEqual(len(lag), 1)
        self.assertIn("ritk-image", lag[0])
        self.assertIn("^0.3.0", lag[0])
        self.assertIn("0.4.0", lag[0])

    def test_generate_patches_edge_satisfied_by_local_version(self) -> None:
        packages = {"ritk-image": (Path("repos/ritk/crates/ritk-image"), "0.4.0")}
        deps = [
            (
                "ritk-image",
                "https://github.com/ryancinsight/ritk",
                "^0.4.0",
                Path("repos/kwavers/Cargo.toml"),
            )
        ]
        with patch.object(_overlay, "collect_first_party_deps", return_value=deps):
            block, missing, lag = _overlay.build_overlay(packages)
        self.assertEqual(lag, [])
        self.assertEqual(missing, [])
        self.assertIn('[patch."https://github.com/ryancinsight/ritk"]', block)
        self.assertIn('[patch."https://github.com/ryancinsight/ritk.git"]', block)
        self.assertIn(
            'ritk-image = { path = "repos/ritk/crates/ritk-image" }', block
        )

    def test_generate_blocks_patch_when_any_declaration_is_unsatisfied(self) -> None:
        packages = {"ritk-image": (Path("repos/ritk/crates/ritk-image"), "0.4.0")}
        deps = [
            (
                "ritk-image",
                "https://github.com/ryancinsight/ritk",
                "^0.4.0",
                Path("repos/helios/Cargo.toml"),
            ),
            (
                "ritk-image",
                "https://github.com/ryancinsight/ritk",
                "^0.3.0",
                Path("repos/kwavers/Cargo.toml"),
            ),
        ]
        with patch.object(_overlay, "collect_first_party_deps", return_value=deps):
            block, missing, lag = _overlay.build_overlay(packages)
        self.assertEqual(block, "\n")
        self.assertEqual(len(lag), 1)

    def test_generate_keeps_satisfying_siblings_when_one_edge_lags(self) -> None:
        packages = {
            "ritk-core": (Path("repos/ritk/crates/ritk-core"), "0.4.0"),
            "ritk-image": (Path("repos/ritk/crates/ritk-image"), "0.4.0"),
        }
        deps = [
            (
                "ritk-core",
                "https://github.com/ryancinsight/ritk",
                "^0.4.0",
                Path("repos/helios/Cargo.toml"),
            ),
            (
                "ritk-image",
                "https://github.com/ryancinsight/ritk",
                "^0.3.0",
                Path("repos/kwavers/Cargo.toml"),
            ),
        ]
        with patch.object(_overlay, "collect_first_party_deps", return_value=deps):
            block, missing, lag = _overlay.build_overlay(packages)
        self.assertEqual(len(lag), 1)
        self.assertIn("ritk-core", block)
        self.assertNotIn("ritk-image", block)

    def test_generate_missing_package_still_reported(self) -> None:
        packages: dict[str, tuple[Path, str | None]] = {}
        deps = [
            (
                "ritk-image",
                "https://github.com/ryancinsight/ritk",
                "^0.4.0",
                Path("repos/helios/Cargo.toml"),
            )
        ]
        with patch.object(_overlay, "collect_first_party_deps", return_value=deps):
            block, missing, lag = _overlay.build_overlay(packages)
        self.assertEqual(block, "\n")
        self.assertEqual(len(missing), 1)
        self.assertEqual(lag, [])


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
