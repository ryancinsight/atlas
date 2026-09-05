#!/usr/bin/env python3
"""Regression tests for canonical Atlas overlay discovery."""
from __future__ import annotations

import importlib.util
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-stack-overlay.py"
_SPEC = importlib.util.spec_from_file_location("atlas_stack_overlay", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_overlay = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_overlay)

_FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "overlay_resolution", Path(__file__).parent / "fixtures" / "overlay_resolution.py"
)
assert _FIXTURE_SPEC is not None and _FIXTURE_SPEC.loader is not None
_fixture = importlib.util.module_from_spec(_FIXTURE_SPEC)
_FIXTURE_SPEC.loader.exec_module(_fixture)


class LagAwarePatchEmissionTestCase(unittest.TestCase):
    """Compatible consumers share local candidates; lagging edges retain Git."""

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

    def test_generate_keeps_patch_for_current_consumer_despite_older_requirement(self) -> None:
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
        self.assertIn('ritk-image = { path = "repos/ritk/crates/ritk-image" }', block)
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

    def test_compatibility_is_selected_per_declared_source(self) -> None:
        packages = {"provider": (Path("repos/provider"), "0.6.0")}
        current = "https://github.com/ryancinsight/Provider"
        previous = "https://github.com/ryancinsight/provider"
        dependencies = [("provider", current, "^0.6", Path("repos/current/Cargo.toml")),
                        ("provider", previous, "^0.5", Path("repos/previous/Cargo.toml"))]
        with patch.object(_overlay, "collect_first_party_deps", return_value=dependencies):
            block, missing, lag = _overlay.build_overlay(packages)
        self.assertIn(f'[patch."{current}"]', block)
        self.assertNotIn(f'[patch."{previous}"]', block)
        self.assertEqual(missing, [])
        self.assertEqual(len(lag), 1)
        self.assertIn(previous, lag[0])

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

    def test_generate_skips_repository_with_incompatible_workspace_edge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            provider = root / "repos" / "provider" / "Cargo.toml"
            consumer_root = root / "repos" / "consumer" / "Cargo.toml"
            consumer = root / "repos" / "consumer" / "crates" / "consumer" / "Cargo.toml"
            provider.parent.mkdir(parents=True)
            consumer.parent.mkdir(parents=True)
            provider.write_text(
                '[package]\nname = "provider"\nversion = "0.43.0"\n',
                encoding="utf-8",
            )
            consumer_root.write_text(
                '[workspace]\nmembers = ["crates/consumer"]\n\n'
                '[workspace.dependencies]\nprovider = { version = "0.42.0", git = "https://github.com/ryancinsight/provider" }\n',
                encoding="utf-8",
            )
            consumer.write_text(
                '[package]\nname = "consumer"\nversion = "1.0.0"\n\n'
                '[dependencies]\nprovider = { workspace = true }\n',
                encoding="utf-8",
            )
            packages = {
                "provider": (Path("repos/provider"), "0.43.0"),
                "consumer": (Path("repos/consumer/crates/consumer"), "1.0.0"),
            }
            deps = [
                (
                    "consumer",
                    "https://github.com/ryancinsight/consumer",
                    "^1.0.0",
                    consumer,
                )
            ]
            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "collect_first_party_deps", return_value=deps
            ):
                block, missing, lag = _overlay.build_overlay(packages)

            self.assertEqual(block, "\n")
            self.assertEqual(missing, [])
            self.assertEqual(len(lag), 1)
            self.assertIn("repos/consumer", lag[0])
            self.assertIn("provider 0.42.0", lag[0])

    def test_cargo_unifies_current_closure_and_retains_old_git_revision(self) -> None:
        toolchain = tomllib.loads((SCRIPT.parent.parent / "rust-toolchain.toml").read_text(
            encoding="utf-8"))["toolchain"]["channel"]
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-resolution-") as directory:
            root = Path(directory)
            fixture = _fixture.CargoOverlayFixture(root)
            packages = {f"overlay-{name}": (Path(f"repos/provider/{name}"), "0.6.0")
                        for name in ("core", "transport")}
            dependencies = [("overlay-core", fixture.url, "^0.5", fixture.consumer / "Cargo.toml"),
                            ("overlay-core", fixture.url, "^0.6", fixture.consumer / "Cargo.toml"),
                            ("overlay-transport", fixture.url, "^0.6", fixture.consumer / "Cargo.toml")]
            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "collect_first_party_deps", return_value=dependencies
            ):
                block, missing, lag = _overlay.build_overlay(packages)
            metadata = fixture.resolve(block, toolchain, SCRIPT.parent.parent)
            cores = [package for package in metadata["packages"] if package["name"] == "overlay-core"]
            self.assertEqual(missing, [])
            self.assertEqual(len(lag), 1)
            self.assertEqual(sorted(package["version"] for package in cores), ["0.5.0", "0.6.0"])
            old, current = sorted(cores, key=lambda package: package["version"])
            self.assertTrue(old["source"].startswith("git+file:"))
            self.assertIsNone(current["source"])
            transport = next(package for package in metadata["packages"] if package["name"] == "overlay-transport")
            nodes = {node["id"]: node for node in metadata["resolve"]["nodes"]}
            self.assertEqual(nodes[transport["id"]]["dependencies"], [current["id"]])
            self.assertIn(current["id"], nodes[metadata["resolve"]["root"]]["dependencies"])
            fixture.check(toolchain, SCRIPT.parent.parent)


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

    def test_repo_manifests_excludes_a_lane_inside_a_member_repo(self) -> None:
        """A lane under ``repos/<member>/worktrees`` is the case that broke.

        The sibling-of-``repos/`` layout the other tests use cannot fail here:
        ``repo_manifests`` globs from ``REPOS / member``, so such a lane is
        already outside the search root. A lane opened *inside* the member is
        under that root, and sorts after ``crates/`` — so before ``_skip``
        filtered ``worktrees`` it overwrote the canonical entry, and the
        committed overlay pinned the stack to a lane that later vanished.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            canonical = root / "repos" / "provider" / "crates" / "core" / "Cargo.toml"
            lane = (
                root
                / "repos"
                / "provider"
                / "worktrees"
                / "some-lane"
                / "crates"
                / "core"
                / "Cargo.toml"
            )
            for manifest in (canonical, lane):
                manifest.parent.mkdir(parents=True, exist_ok=True)
                manifest.write_text(
                    '[package]\nname = "core"\nversion = "1.0.0"\n', encoding="utf-8"
                )

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"provider"}
            ):
                manifests = _overlay.repo_manifests()

            self.assertEqual(manifests, [canonical])

    def test_in_repo_lane_package_cannot_replace_canonical_package(self) -> None:
        """The emitted path must be the canonical tree, not the lane copy."""
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            canonical = root / "repos" / "provider" / "Cargo.toml"
            lane = root / "repos" / "provider" / "worktrees" / "lane" / "Cargo.toml"
            for manifest in (canonical, lane):
                manifest.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text(
                '[package]\nname = "provider"\nversion = "1.0.0"\n', encoding="utf-8"
            )
            lane.write_text(
                '[package]\nname = "provider"\nversion = "9.0.0"\n', encoding="utf-8"
            )

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"provider"}
            ):
                packages = _overlay.load_packages()

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.0.0"))


class OverlayFreshnessTestCase(unittest.TestCase):
    """`check` must reject an overlay that no longer describes the layout.

    Both failures break every build in the stack before a crate compiles, and
    neither is visible to the lag and pin-drift checks that `check` ran before.
    """

    def _config(self, root: Path, block: str) -> Path:
        config = root / "config.toml"
        config.write_text(
            f"{_overlay.HEADER}{block}{_overlay.END}\n", encoding="utf-8"
        )
        return config

    def test_dangling_path_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            block = '\n[patch."https://example.invalid/p"]\np = { path = "repos/p" }\n'
            config = self._config(root, block)

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "CONFIG", config
            ), patch.object(_overlay, "build_overlay", return_value=(block, [], [])):
                problems = _overlay.check_overlay_freshness({})

            self.assertEqual(len(problems), 1, problems)
            self.assertIn("dangling", problems[0])
            self.assertIn("repos/p", problems[0])

    def test_drift_from_a_fresh_generation_is_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            (root / "repos" / "p").mkdir(parents=True)
            (root / "repos" / "p" / "Cargo.toml").write_text("", encoding="utf-8")
            committed = '\n[patch."https://example.invalid/p"]\np = { path = "repos/p" }\n'
            regenerated = committed.replace("example.invalid", "example.test")
            config = self._config(root, committed)

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "CONFIG", config
            ), patch.object(
                _overlay, "build_overlay", return_value=(regenerated, [], [])
            ):
                problems = _overlay.check_overlay_freshness({})

            self.assertEqual(len(problems), 1, problems)
            self.assertIn("fresh generation", problems[0])

    def test_current_overlay_is_reported_clean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            (root / "repos" / "p").mkdir(parents=True)
            (root / "repos" / "p" / "Cargo.toml").write_text("", encoding="utf-8")
            block = '\n[patch."https://example.invalid/p"]\np = { path = "repos/p" }\n'
            config = self._config(root, block)

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "CONFIG", config
            ), patch.object(_overlay, "build_overlay", return_value=(block, [], [])):
                problems = _overlay.check_overlay_freshness({})

            self.assertEqual(problems, [])

    def test_a_disabled_overlay_is_not_stale(self) -> None:
        """`off` comments the block out; that is a state, not drift."""
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            (root / "repos" / "p").mkdir(parents=True)
            (root / "repos" / "p" / "Cargo.toml").write_text("", encoding="utf-8")
            enabled = '\n[patch."https://example.invalid/p"]\np = { path = "repos/p" }\n'
            config = self._config(root, enabled)

            with patch.object(_overlay, "CONFIG", config):
                _overlay.set_enabled(False)
            self.assertIn("#OFF#", config.read_text(encoding="utf-8"))

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "CONFIG", config
            ), patch.object(_overlay, "build_overlay", return_value=(enabled, [], [])):
                problems = _overlay.check_overlay_freshness({})

            self.assertEqual(problems, [])

if __name__ == "__main__":
    unittest.main()
