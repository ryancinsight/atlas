#!/usr/bin/env python3
"""Regression tests for canonical Atlas overlay discovery."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
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
            block, missing, lag = _overlay.build_overlay(packages, [])
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
            block, missing, lag = _overlay.build_overlay(packages, [])
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
            block, missing, lag = _overlay.build_overlay(packages, [])
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
            block, missing, lag = _overlay.build_overlay(packages, [])
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
            block, missing, lag = _overlay.build_overlay(packages, [])
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
            block, missing, lag = _overlay.build_overlay(packages, [])
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
            manifests = [
                (Path("repos/provider"), provider.read_text(encoding="utf-8")),
                (Path("repos/consumer"), consumer_root.read_text(encoding="utf-8")),
                (
                    Path("repos/consumer/crates/consumer"),
                    consumer.read_text(encoding="utf-8"),
                ),
            ]
            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "collect_first_party_deps", return_value=deps
            ):
                block, missing, lag = _overlay.build_overlay(packages, manifests)

            self.assertEqual(block, "\n")
            self.assertEqual(missing, [])
            self.assertEqual(len(lag), 1)
            self.assertIn("repos/consumer", lag[0])
            self.assertIn("provider 0.42.0", lag[0])

    def test_cargo_unifies_current_closure_and_retains_old_git_revision(self) -> None:
        channel = tomllib.loads((SCRIPT.parent.parent / "rust-toolchain.toml").read_text(
            encoding="utf-8"))["toolchain"]["channel"]
        # The repo pin carries the full Windows host triple so every local
        # worktree shares one compiler-versioned cache bucket
        # (ATLAS-TOOLCHAIN-TRIPLE-083), but a `cargo +<triple>` override
        # cannot provision on Ubuntu CI where this suite also runs.
        # Dependency resolution is version-determined, so use the bare
        # version and let rustup resolve it natively on each platform.
        version = re.match(r"\d+\.\d+\.\d+", channel)
        toolchain = version.group(0) if version else channel
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
                block, missing, lag = _overlay.build_overlay(packages, [])
            metadata = fixture.resolve(block, toolchain)
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
            fixture.check(toolchain)
            # The compile landed in the fixture's own cache, and nowhere in the
            # checkout. `CACHEDIR.TAG` is written by cargo at a target
            # directory's root, so its presence is evidence of a real cache
            # rather than of an empty directory a path assertion would accept.
            self.assertTrue((fixture.target / "CACHEDIR.TAG").is_file())
            self.assertFalse((fixture.consumer / "target").exists())
            self.assertFalse((fixture.source / "target").exists())

    def test_fixture_builds_in_its_own_target_not_the_shared_stack_cache(self) -> None:
        """A fixture run must not route into -- or wait on -- the stack cache.

        The stack's bootstrap scripts export `CARGO_TARGET_DIR`, and the root
        config accepts that concurrent builds serialize on its build lock, so a
        fixture that inherited either would make its own duration a function of
        whatever else is compiling on the machine.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-isolation-") as directory:
            root = Path(directory)
            with patch.dict(os.environ, {"CARGO_TARGET_DIR": str(root / "stack-target")}):
                fixture = _fixture.CargoOverlayFixture(root)
            self.assertEqual(fixture.target, root / "target")
            self.assertEqual(fixture.environment["CARGO_TARGET_DIR"], str(fixture.target))


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

    def test_check_locks_ignores_unregistered_private_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            registered = root / "repos" / "registered" / "Cargo.lock"
            unregistered = root / "repos" / "private" / "Cargo.lock"
            for lock in (registered, unregistered):
                lock.parent.mkdir(parents=True, exist_ok=True)
                lock.write_text(
                    "[[package]]\n"
                    'name = "moirai-core"\n'
                    'version = "0.5.0"\n'
                    'source = "git+https://github.com/ryancinsight/Moirai"\n',
                    encoding="utf-8",
                )
            packages = {
                "moirai-core": (Path("repos/moirai"), "0.6.0"),
            }
            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"registered"}
            ):
                drift = _overlay.check_locks(packages, False)

            self.assertEqual(
                drift,
                ["repos/registered/Cargo.lock: `moirai-core` locked 0.5.0, local tree 0.6.0"],
            )

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
                manifests = _overlay.read_manifests(False)
                packages = _overlay.load_packages(manifests)

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.2.3"))

    def test_package_workspace_selects_version_outside_nearest_ancestor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-workspace-") as root_text:
            root = Path(root_text)
            outer = root / "outer" / "Cargo.toml"
            selected = root / "selected" / "Cargo.toml"
            member = root / "outer" / "member" / "Cargo.toml"
            source = member.parent / "src" / "lib.rs"
            source.parent.mkdir(parents=True)
            outer.write_text(
                '[workspace]\nmembers = []\n\n[workspace.package]\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            selected.parent.mkdir()
            selected.write_text(
                '[workspace]\nresolver = "3"\nmembers = ["../outer/member"]\n\n'
                '[workspace.package]\nversion = "2.0.0"\n',
                encoding="utf-8",
            )
            member.write_text(
                '[package]\nname = "selected-member"\nversion.workspace = true\n'
                'edition = "2024"\nworkspace = "../../selected"\n',
                encoding="utf-8",
            )
            source.write_text("pub fn selected_version() {}\n", encoding="utf-8")

            metadata = subprocess.run(
                [
                    "cargo",
                    "metadata",
                    "--no-deps",
                    "--format-version",
                    "1",
                    "--manifest-path",
                    str(selected),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            self.assertEqual(metadata.returncode, 0, metadata.stderr)
            cargo_packages = json.loads(metadata.stdout)["packages"]
            self.assertEqual(
                [(package["name"], package["version"]) for package in cargo_packages],
                [("selected-member", "2.0.0")],
            )

            manifests = [
                (Path("repos/provider/outer"), outer.read_text(encoding="utf-8")),
                (Path("repos/provider/selected"), selected.read_text(encoding="utf-8")),
                (
                    Path("repos/provider/outer/member"),
                    member.read_text(encoding="utf-8"),
                ),
            ]
            facts = _overlay.load_package_facts(manifests)
            self.assertEqual(
                [(fact.name, fact.version) for fact in facts],
                [("selected-member", "2.0.0")],
            )

    def test_declared_workspace_member_requires_a_manifest(self) -> None:
        manifests = [
            (
                Path("repos/provider"),
                '[workspace]\nmembers = ["crates/missing"]\n',
            )
        ]
        with self.assertRaisesRegex(ValueError, "crates/missing.*without a manifest"):
            _overlay.load_package_facts(manifests)

    def test_local_path_dependency_manifests_form_a_complete_closure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-paths-") as root_text:
            root = Path(root_text)
            contents = {
                "Cargo.toml": (
                    '[workspace]\nresolver = "3"\nmembers = ["crates/app"]\n\n'
                    '[workspace.dependencies]\nshared = { path = "crates/shared" }\n'
                ),
                "crates/app/Cargo.toml": (
                    '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2024"\n'
                    '[dependencies]\ndirect = { path = "../direct" }\n'
                    '[build-dependencies]\nbuild = { path = "../build" }\n'
                    '[dev-dependencies]\ndev = { path = "../dev" }\n'
                    "[target.'cfg(windows)'.dependencies]\nshared = { workspace = true }\n"
                ),
            }
            for name in ("direct", "build", "dev", "shared"):
                contents[f"crates/{name}/Cargo.toml"] = (
                    f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2024"\n'
                )
                contents[f"crates/{name}/src/lib.rs"] = f"pub fn {name}() {{}}\n"
            contents["crates/app/src/lib.rs"] = "pub fn app() {}\n"
            for name, text in contents.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            metadata = subprocess.run(
                ["cargo", "metadata", "--no-deps", "--format-version", "1",
                 "--manifest-path", str(root / "Cargo.toml")],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
            )
            self.assertEqual(metadata.returncode, 0, metadata.stderr)
            cargo_names = sorted(package["name"] for package in json.loads(metadata.stdout)["packages"])
            self.assertEqual(cargo_names, ["app", "build", "dev", "direct", "shared"])

            manifests = [
                (Path(name).parent, text)
                for name, text in contents.items()
                if name.endswith("Cargo.toml")
            ]
            facts = _overlay.load_package_facts(manifests)
            self.assertEqual(sorted(fact.name for fact in facts), cargo_names)
            for missing in ("direct", "build", "dev", "shared"):
                incomplete = [item for item in manifests if item[0] != Path("crates") / missing]
                with self.subTest(missing=missing), self.assertRaisesRegex(
                    ValueError, rf"dependency '{missing}'.*without crates/{missing}/Cargo.toml"
                ):
                    _overlay.load_package_facts(incomplete)

    def test_consumed_path_requires_the_expected_package(self) -> None:
        cases = {
            "virtual": (
                '[workspace]\nmembers = []\n',
                "found a virtual manifest",
            ),
            "different": (
                (
                    '[package]\nname = "different"\nversion = "0.1.0"\n'
                    'edition = "2024"\n'
                ),
                "no matching package named `expected`",
            ),
        }
        for case, (dependency_manifest, cargo_error) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory(
                prefix="atlas-overlay-path-package-"
            ) as root_text:
                root = Path(root_text)
                contents = {
                    "Cargo.toml": (
                        '[workspace]\nresolver = "3"\nmembers = ["app"]\n'
                        'exclude = ["dep"]\n'
                    ),
                    "app/Cargo.toml": (
                        '[package]\nname = "app"\nversion = "0.1.0"\n'
                        'edition = "2024"\n[dependencies]\n'
                        'expected = { path = "../dep" }\n'
                    ),
                    "app/src/lib.rs": "pub fn app() {}\n",
                    "dep/Cargo.toml": dependency_manifest,
                    "dep/src/lib.rs": "pub fn dep() {}\n",
                }
                self._write_fixture(root, contents)
                metadata = self._cargo_metadata(root)
                self.assertNotEqual(metadata.returncode, 0)
                self.assertIn(cargo_error, metadata.stderr)
                with self.assertRaisesRegex(ValueError, "expected.*package"):
                    _overlay.load_package_facts(self._fixture_manifests(contents))

    def test_path_package_rename_matches_cargo(self) -> None:
        contents = {
            "Cargo.toml": '[workspace]\nresolver = "3"\nmembers = ["app"]\n',
            "app/Cargo.toml": (
                '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2024"\n'
                '[dependencies]\nalias = { package = "actual", path = "../dep" }\n'
            ),
            "app/src/lib.rs": "pub fn app() {}\n",
            "dep/Cargo.toml": (
                '[package]\nname = "actual"\nversion = "0.1.0"\nedition = "2024"\n'
            ),
            "dep/src/lib.rs": "pub fn dep() {}\n",
        }
        self._assert_cargo_and_owner_accept(contents, {"actual", "app"})

    def test_inherited_path_package_name_matches_cargo(self) -> None:
        contents = {
            "Cargo.toml": (
                '[workspace]\nresolver = "3"\nmembers = ["app"]\n'
                '[workspace.dependencies]\n'
                'alias = { package = "actual", path = "dep" }\n'
            ),
            "app/Cargo.toml": (
                '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2024"\n'
                '[dependencies]\nalias = { workspace = true }\n'
            ),
            "app/src/lib.rs": "pub fn app() {}\n",
            "dep/Cargo.toml": (
                '[package]\nname = "actual"\nversion = "0.1.0"\nedition = "2024"\n'
            ),
            "dep/src/lib.rs": "pub fn dep() {}\n",
        }
        self._assert_cargo_and_owner_accept(contents, {"actual", "app"})

    def test_unused_workspace_path_is_not_part_of_package_closure(self) -> None:
        contents = {
            "Cargo.toml": (
                '[workspace]\nresolver = "3"\nmembers = ["app"]\n'
                '[workspace.dependencies]\nunused = { path = "missing" }\n'
            ),
            "app/Cargo.toml": (
                '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2024"\n'
            ),
            "app/src/lib.rs": "pub fn app() {}\n",
        }
        self._assert_cargo_and_owner_accept(contents, {"app"})

    @staticmethod
    def _write_fixture(root: Path, contents: dict[str, str]) -> None:
        for name, text in contents.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    @staticmethod
    def _fixture_manifests(contents: dict[str, str]) -> list[tuple[Path, str]]:
        return [
            (Path(name).parent, text)
            for name, text in contents.items()
            if name.endswith("Cargo.toml")
        ]

    @staticmethod
    def _cargo_metadata(root: Path) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment.update(
            CARGO_HOME=str(root / "cargo-home"),
            CARGO_TARGET_DIR=str(root / "target"),
        )
        return subprocess.run(
            [
                "cargo",
                "metadata",
                "--offline",
                "--format-version",
                "1",
                "--manifest-path",
                str(root / "Cargo.toml"),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    def _assert_cargo_and_owner_accept(
        self, contents: dict[str, str], expected: set[str]
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-path-package-") as root_text:
            root = Path(root_text)
            self._write_fixture(root, contents)
            metadata = self._cargo_metadata(root)
            self.assertEqual(metadata.returncode, 0, metadata.stderr)
            cargo_names = {
                package["name"] for package in json.loads(metadata.stdout)["packages"]
            }
            self.assertEqual(cargo_names, expected)
            facts = _overlay.load_package_facts(self._fixture_manifests(contents))
            self.assertEqual({fact.name for fact in facts}, expected)

    def test_repeated_non_provider_names_remain_complete_and_unindexed(self) -> None:
        manifests = [
            (Path("repos/provider/one"), '[package]\nname = "shared"\nversion = "0.1.0"\n'),
            (Path("repos/provider/two"), '[package]\nname = "shared"\nversion = "9.9.9"\n'),
        ]
        facts = _overlay.load_package_facts(manifests)
        self.assertEqual(
            [(fact.name, fact.path, fact.version) for fact in facts],
            [
                ("shared", Path("repos/provider/one"), "0.1.0"),
                ("shared", Path("repos/provider/two"), "9.9.9"),
            ],
        )
        self.assertEqual(_overlay.package_versions(facts)["shared"], frozenset({"0.1.0", "9.9.9"}))
        self.assertEqual(_overlay.load_packages(manifests), {})

    def test_repeated_provider_name_cannot_enter_unique_overlay_index(self) -> None:
        manifests = [
            (Path("repos/provider/one"), '[package]\nname = "shared"\nversion = "0.1.0"\n'),
            (Path("repos/provider/two"), '[package]\nname = "shared"\nversion = "9.9.9"\n'),
            (
                Path("repos/consumer"),
                '[dependencies]\nshared = { version = "0.1.0", '
                'git = "https://github.com/ryancinsight/shared" }\n',
            ),
        ]
        with self.assertRaisesRegex(ValueError, "declared by both"):
            _overlay.load_packages(manifests)

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
                manifests = _overlay.read_manifests(False)
                packages = _overlay.load_packages(manifests)
                dependencies = _overlay.collect_first_party_deps(manifests)

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.0.0"))
            self.assertEqual(len(dependencies), 1)
            self.assertEqual(dependencies[0][0], "provider")
            self.assertEqual(dependencies[0][3], Path("repos/consumer"))

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
                manifests = _overlay.read_manifests(False)
                packages = _overlay.load_packages(manifests)

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.0.0"))


class PinnedAndTipsSourceTestCase(unittest.TestCase):
    """The overlay can be read from the recorded stack, not only the checkout.

    A generation taken from the working tree measures whichever branch a
    developer has parked a member on, so two developers on the same stack
    revision can produce two different overlays. The recorded gitlinks are
    the reproducible answer, and the members' default branches are what a
    gitlink advance would record.
    """

    def _member(self, root: Path, name: str, version: str) -> Path:
        member = root / "repos" / name
        member.mkdir(parents=True, exist_ok=True)
        (member / "Cargo.toml").write_text(
            f'[package]\nname = "{name}"\nversion = "{version}"\n', encoding="utf-8"
        )
        return member

    def _commit(self, member: Path, message: str) -> str:
        for command in (
            ["git", "init", "--quiet"],
            ["git", "config", "user.name", "Overlay test"],
            ["git", "config", "user.email", "overlay@example.invalid"],
            ["git", "add", "Cargo.toml"],
            ["git", "commit", "--quiet", "-m", message],
        ):
            subprocess.run(command, cwd=member, check=True, capture_output=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=member, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def test_pinned_reads_the_recorded_gitlink_not_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-pinned-") as root_text:
            root = Path(root_text)
            member = self._member(root, "provider", "1.0.0")
            pinned = self._commit(member, "pinned")
            # The checkout moves on; the recorded gitlink does not.
            self._member(root, "provider", "2.0.0")
            subprocess.run(["git", "add", "Cargo.toml"], cwd=member, check=True,
                           capture_output=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "ahead"], cwd=member, check=True,
                capture_output=True,
            )

            class _FakeGitlinks:
                def __call__(self) -> dict[str, str]:
                    return {"provider": pinned}

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"provider"}
            ), patch.object(_overlay, "member_pins", _FakeGitlinks()):
                manifests = _overlay.read_manifests(True)
                packages = _overlay.load_packages(manifests)

            self.assertEqual(packages["provider"], (Path("repos/provider"), "1.0.0"))

    def test_pinned_failure_is_loud_rather_than_an_empty_member(self) -> None:
        """A member that cannot be read must not quietly leave the overlay.

        An empty manifest set reads as "this member contributes nothing", so
        a whole member could leave the overlay behind a green generation. The
        failure has to name the member and the revision instead.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-pinned-") as root_text:
            root = Path(root_text)
            member = root / "repos" / "provider"
            member.mkdir(parents=True, exist_ok=True)
            (member / "Cargo.toml").write_text(
                '[package]\nname = "provider"\nversion = "1.0.0"\n', encoding="utf-8"
            )

            class _FakeGitlinks:
                def __call__(self) -> dict[str, str]:
                    return {"provider": "0" * 40}

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"provider"}
            ), patch.object(_overlay, "member_pins", _FakeGitlinks()):
                with self.assertRaises(SystemExit) as raised:
                    _overlay.read_manifests(True)

            self.assertIn("provider", str(raised.exception))

    def test_tips_reads_the_member_default_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-tips-") as root_text:
            root = Path(root_text)
            member = self._member(root, "provider", "1.0.0")
            self._commit(member, "first")
            self._member(root, "provider", "2.0.0")
            subprocess.run(["git", "add", "Cargo.toml"], cwd=member, check=True,
                           capture_output=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "second"], cwd=member, check=True,
                capture_output=True,
            )

            class _FakeTips:
                def __call__(self) -> dict[str, str]:
                    sha = subprocess.run(
                        ["git", "rev-parse", "HEAD"], cwd=member, check=True,
                        capture_output=True, text=True,
                    ).stdout.strip()
                    return {"provider": sha}

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"provider"}
            ), patch.object(_overlay, "member_tips", _FakeTips()):
                manifests = _overlay.read_manifests(False, True)
                packages = _overlay.load_packages(manifests)

            self.assertEqual(packages["provider"], (Path("repos/provider"), "2.0.0"))


class OverlayFreshnessTestCase(unittest.TestCase):
    """`check` must reject an overlay that no longer describes the layout.

    Both failures break every build in the stack before a crate compiles, and
    neither is visible to the lag and pin-drift checks that `check` ran before.
    """

    @staticmethod
    def _manifests() -> list[tuple[Path, str]]:
        """The manifest set a generation over `repos/p` would have read."""
        return [(Path("repos/p"), '[package]\nname = "p"\nversion = "1.0.0"\n')]

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
                problems = _overlay.check_overlay_freshness({}, [])

            self.assertEqual(len(problems), 1, problems)
            self.assertIn("dangling", problems[0])
            self.assertIn("repos/p", problems[0])

    def test_a_path_the_manifest_set_carries_is_not_dangling(self) -> None:
        """The dangling test reads the manifest set, not the filesystem.

        A pinned or tips read describes the recorded stack, so a path the
        recorded stack carries is present even when the checkout behind it does
        not have it. Testing the filesystem there reports a path as missing
        that the generation is right to emit.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-") as root_text:
            root = Path(root_text)
            block = '\n[patch."https://example.invalid/p"]\np = { path = "repos/p" }\n'
            config = self._config(root, block)
            manifests = [(Path("repos/p"), '[package]\nname = "p"\nversion = "1.0.0"\n')]

            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "CONFIG", config
            ), patch.object(_overlay, "build_overlay", return_value=(block, [], [])):
                problems = _overlay.check_overlay_freshness({}, manifests)

            self.assertEqual(problems, [])

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
                problems = _overlay.check_overlay_freshness({}, self._manifests())

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
                problems = _overlay.check_overlay_freshness({}, self._manifests())

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
                problems = _overlay.check_overlay_freshness({}, self._manifests())

            self.assertEqual(problems, [])


class CheckWiringTestCase(unittest.TestCase):
    """`check` must pass its own pinned flag to the lock scan.

    The function receives `pinned` as a parameter; referring to the CLI
    parser's `args` there raises NameError before any drift is reported, so
    the CI gate failed as a traceback rather than as its measured verdict.
    """

    def test_check_passes_pinned_to_check_locks(self) -> None:
        with patch.object(
            _overlay, "collect_first_party_deps", return_value=[]
        ), patch.object(
            _overlay, "check_overlay_freshness", return_value=[]
        ), patch.object(
            _overlay, "check_locks", return_value=[]
        ) as locks:
            result = _overlay.check({}, [], True)

        self.assertEqual(result, 0)
        locks.assert_called_once_with({}, True)


if __name__ == "__main__":
    unittest.main()
