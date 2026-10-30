#!/usr/bin/env python3
"""Regression tests for canonical Atlas overlay discovery."""
from __future__ import annotations

import importlib.util
import os
import re
import tempfile
import tomllib
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from atlas_cargo_package_facts import (
    DependencyFact,
    PackageCatalog,
    PackageFact,
    ProviderIdentity,
)


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


def catalog(
    providers: dict[ProviderIdentity, tuple[Path, str]],
    edges: list[tuple[ProviderIdentity, str, str, Path]],
) -> PackageCatalog:
    """Build value-semantic Cargo facts for overlay policy tests."""
    facts = {
        identity: PackageFact(
            identity.package,
            version,
            PurePosixPath(path.as_posix(), "Cargo.toml"),
            (),
        )
        for identity, (path, version) in providers.items()
    }
    consumers = tuple(
        PackageFact(
            f"consumer-{index}",
            "0.1.0",
            PurePosixPath(manifest.as_posix()),
            (
                DependencyFact(
                    identity.package,
                    None,
                    f"git+{url}",
                    requirement,
                    None,
                    None,
                    identity,
                    url,
                ),
            ),
        )
        for index, (identity, url, requirement, manifest) in enumerate(edges)
    )
    return PackageCatalog((), tuple(facts.values()) + consumers, facts)


class LagAwarePatchEmissionTestCase(unittest.TestCase):
    """Compatible consumers share local candidates; lagging edges retain Git."""

    def facts(
        self,
        versions: dict[ProviderIdentity, tuple[Path, str]],
        dependencies: list[tuple[ProviderIdentity, str, str, Path]],
    ) -> PackageCatalog:
        return catalog(versions, dependencies)

    def test_generate_skips_incompatible_edge(self) -> None:
        identity = ProviderIdentity("ritk-image", "ritk")
        facts = self.facts(
            {identity: (Path("repos/ritk/crates/ritk-image"), "0.4.0")},
            [(identity, "https://github.com/ryancinsight/ritk", "^0.3.0",
              Path("repos/kwavers/Cargo.toml"))],
        )
        block, missing, lag = _overlay.build_overlay(facts)
        self.assertEqual((block, missing, len(lag)), ("\n", [], 1))
        self.assertIn("^0.3.0", lag[0])
        self.assertIn("0.4.0", lag[0])

    def test_generate_patches_compatible_edge_and_aliases(self) -> None:
        identity = ProviderIdentity("ritk-image", "ritk")
        facts = self.facts(
            {identity: (Path("repos/ritk/crates/ritk-image"), "0.4.0")},
            [(identity, "https://github.com/ryancinsight/ritk", "^0.4.0",
              Path("repos/kwavers/Cargo.toml"))],
        )
        block, missing, lag = _overlay.build_overlay(facts)
        self.assertEqual((missing, lag), ([], []))
        self.assertIn('[patch."https://github.com/ryancinsight/ritk"]', block)
        self.assertIn('[patch."https://github.com/ryancinsight/ritk.git"]', block)
        self.assertIn(
            'ritk-image = { path = "repos/ritk/crates/ritk-image" }', block
        )

    def test_current_edge_survives_older_requirement(self) -> None:
        identity = ProviderIdentity("ritk-image", "ritk")
        url = "https://github.com/ryancinsight/ritk"
        facts = self.facts(
            {identity: (Path("repos/ritk/crates/ritk-image"), "0.4.0")},
            [
                (identity, url, "^0.4.0", Path("repos/helios/Cargo.toml")),
                (identity, url, "^0.3.0", Path("repos/kwavers/Cargo.toml")),
            ],
        )
        block, _missing, lag = _overlay.build_overlay(facts)
        self.assertIn("ritk-image", block)
        self.assertEqual(len(lag), 1)

    def test_satisfying_sibling_survives_one_lagging_package(self) -> None:
        core = ProviderIdentity("ritk-core", "ritk")
        image = ProviderIdentity("ritk-image", "ritk")
        url = "https://github.com/ryancinsight/ritk"
        facts = self.facts(
            {
                core: (Path("repos/ritk/crates/ritk-core"), "0.4.0"),
                image: (Path("repos/ritk/crates/ritk-image"), "0.4.0"),
            },
            [
                (core, url, "^0.4.0", Path("repos/helios/Cargo.toml")),
                (image, url, "^0.3.0", Path("repos/kwavers/Cargo.toml")),
            ],
        )
        block, _missing, lag = _overlay.build_overlay(facts)
        self.assertEqual(len(lag), 1)
        self.assertIn("ritk-core", block)
        self.assertNotIn("ritk-image", block)

    def test_compatibility_is_selected_per_declared_source(self) -> None:
        identity = ProviderIdentity("provider", "provider")
        current = "https://github.com/ryancinsight/Provider"
        previous = "https://github.com/ryancinsight/provider"
        facts = self.facts(
            {identity: (Path("repos/provider"), "0.6.0")},
            [
                (identity, current, "^0.6", Path("repos/current/Cargo.toml")),
                (identity, previous, "^0.5", Path("repos/previous/Cargo.toml")),
            ],
        )
        block, missing, lag = _overlay.build_overlay(facts)
        self.assertIn(f'[patch."{current}"]', block)
        self.assertNotIn(f'[patch."{previous}"]', block)
        self.assertEqual((missing, len(lag)), ([], 1))

    def test_incompatible_provider_workspace_edge_quarantines_repository(self) -> None:
        provider = ProviderIdentity("provider", "provider")
        consumer = ProviderIdentity("consumer", "consumer")
        provider_fact = PackageFact(
            "provider", "0.43.0", Path("repos/provider/Cargo.toml"), ()
        )
        consumer_fact = PackageFact(
            "consumer",
            "1.0.0",
            Path("repos/consumer/crates/consumer/Cargo.toml"),
            (
                DependencyFact(
                    "provider", None,
                    "git+https://github.com/ryancinsight/provider",
                    "0.42.0", None, None, provider,
                    "https://github.com/ryancinsight/provider",
                ),
            ),
        )
        caller = PackageFact(
            "caller",
            "1.0.0",
            Path("repos/caller/Cargo.toml"),
            (
                DependencyFact(
                    "consumer", None,
                    "git+https://github.com/ryancinsight/consumer",
                    "^1.0.0", None, None, consumer,
                    "https://github.com/ryancinsight/consumer",
                ),
            ),
        )
        facts = PackageCatalog(
            (),
            (provider_fact, consumer_fact, caller),
            {provider: provider_fact, consumer: consumer_fact},
        )
        block, missing, lag = _overlay.build_overlay(facts)
        self.assertEqual((block, missing, len(lag)), ("\n", [], 1))
        self.assertIn("repos/consumer", lag[0])
        self.assertIn("provider 0.42.0", lag[0])

    def test_cargo_unifies_current_closure_and_retains_old_git_revision(self) -> None:
        channel = tomllib.loads((SCRIPT.parent.parent / "rust-toolchain.toml").read_text(
            encoding="utf-8"))["toolchain"]["channel"]
        version = re.match(r"\d+\.\d+\.\d+", channel)
        toolchain = version.group(0) if version else channel
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-resolution-") as directory:
            root = Path(directory)
            fixture = _fixture.CargoOverlayFixture(root)
            core = ProviderIdentity("overlay-core", "provider")
            transport = ProviderIdentity("overlay-transport", "provider")
            facts = self.facts(
                {
                    core: (Path("repos/provider/core"), "0.6.0"),
                    transport: (Path("repos/provider/transport"), "0.6.0"),
                },
                [
                    (core, fixture.url, "^0.5", Path("repos/old/Cargo.toml")),
                    (core, fixture.url, "^0.6", Path("repos/current/Cargo.toml")),
                    (transport, fixture.url, "^0.6", Path("repos/current/Cargo.toml")),
                ],
            )
            block, missing, lag = _overlay.build_overlay(facts)
            metadata = fixture.resolve(block, toolchain)
            cores = [package for package in metadata["packages"]
                     if package["name"] == "overlay-core"]
            self.assertEqual((missing, len(lag)), ([], 1))
            self.assertEqual(
                sorted(package["version"] for package in cores), ["0.5.0", "0.6.0"]
            )
            old, current = sorted(cores, key=lambda package: package["version"])
            self.assertTrue(old["source"].startswith("git+file:"))
            self.assertIsNone(current["source"])
            transport_package = next(
                package for package in metadata["packages"]
                if package["name"] == "overlay-transport"
            )
            nodes = {node["id"]: node for node in metadata["resolve"]["nodes"]}
            self.assertEqual(
                nodes[transport_package["id"]]["dependencies"], [current["id"]]
            )
            self.assertIn(current["id"], nodes[metadata["resolve"]["root"]]["dependencies"])
            fixture.check(toolchain)
            self.assertTrue((fixture.target / "CACHEDIR.TAG").is_file())
            self.assertFalse((fixture.consumer / "target").exists())
            self.assertFalse((fixture.source / "target").exists())

    def test_fixture_builds_in_its_own_target_not_the_shared_stack_cache(self) -> None:
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
            identity = ProviderIdentity("moirai-core", "moirai")
            facts = catalog(
                {identity: (Path("repos/moirai"), "0.6.0")},
                [
                    (
                        identity,
                        "https://github.com/ryancinsight/Moirai",
                        "^0.6.0",
                        Path("repos/registered/Cargo.toml"),
                    )
                ],
            )
            with patch.object(_overlay, "ATLAS_ROOT", root), patch.object(
                _overlay, "REPOS", root / "repos"
            ), patch.object(
                _overlay, "registered_member_names", return_value={"registered"}
            ):
                drift = _overlay.check_locks(facts, False)

            self.assertEqual(
                drift,
                ["repos/registered/Cargo.lock: `moirai-core` locked 0.5.0, local tree 0.6.0"],
            )

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

class CatalogRoutingTestCase(unittest.TestCase):
    """Working, pinned, and tip modes select the matching native fact owner."""

    def test_working_mode_includes_every_registered_repository(self) -> None:
        expected = PackageCatalog((), (), {})
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-working-") as root_text:
            root = Path(root_text)
            provider = root / "repos" / "provider"
            provider.mkdir(parents=True)
            with patch.object(_overlay, "REPOS", root / "repos"), patch.object(
                _overlay, "registered_member_names", return_value={"provider", "missing"}
            ), patch.object(_overlay, "load_working", return_value=expected) as working:
                actual = _overlay.load_catalog(False)
        self.assertIs(actual, expected)
        working.assert_called_once_with(
            {"missing": root / "repos" / "missing", "provider": provider}
        )

    def test_selected_modes_use_exact_revisions(self) -> None:
        for tips in (False, True):
            with self.subTest(tips=tips), tempfile.TemporaryDirectory(
                prefix="atlas-overlay-selected-"
            ) as root_text:
                root = Path(root_text)
                provider = root / "repos" / "provider"
                provider.mkdir(parents=True)
                revision = ("2" if tips else "1") * 40
                expected = PackageCatalog((("provider", revision),), (), {})
                revisions = {"provider": revision}
                selector = "member_tips" if tips else "member_pins"
                with patch.object(_overlay, "REPOS", root / "repos"), patch.object(
                    _overlay, "registered_member_names", return_value={"provider"}
                ), patch.object(
                    _overlay, selector, return_value=revisions
                ), patch.object(
                    _overlay, "load_selected", return_value=expected
                ) as selected:
                    actual = _overlay.load_catalog(not tips, tips)
                self.assertIs(actual, expected)
                selections, destination = selected.call_args.args
                self.assertEqual(selections["provider"].repository, provider)
                self.assertEqual(selections["provider"].revision, revision)
                self.assertEqual(destination.name, "cohort")

    def test_missing_selected_revision_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-overlay-selected-") as root_text:
            root = Path(root_text)
            provider = root / "repos" / "provider"
            provider.mkdir(parents=True)
            with patch.object(_overlay, "REPOS", root / "repos"), patch.object(
                _overlay, "registered_member_names", return_value={"provider"}
            ), patch.object(_overlay, "member_pins", return_value={}):
                with self.assertRaisesRegex(_overlay.PackageFactError, "provider"):
                    _overlay.load_catalog(True)


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
                problems = _overlay.check_overlay_freshness(PackageCatalog((), (), {}), [])

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
                problems = _overlay.check_overlay_freshness(
                    PackageCatalog((), (), {}), manifests
                )

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
                problems = _overlay.check_overlay_freshness(
                    PackageCatalog((), (), {}), self._manifests()
                )

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
                problems = _overlay.check_overlay_freshness(
                    PackageCatalog((), (), {}), self._manifests()
                )

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
                problems = _overlay.check_overlay_freshness(
                    PackageCatalog((), (), {}), self._manifests()
                )

            self.assertEqual(problems, [])


class CheckWiringTestCase(unittest.TestCase):
    """`check` must pass its own pinned flag to the lock scan.

    The function receives `pinned` as a parameter; referring to the CLI
    parser's `args` there raises NameError before any drift is reported, so
    the CI gate failed as a traceback rather than as its measured verdict.
    """

    def test_check_passes_pinned_to_check_locks(self) -> None:
        facts = PackageCatalog((), (), {})
        with patch.object(
            _overlay, "check_overlay_freshness", return_value=[]
        ), patch.object(
            _overlay, "check_locks", return_value=[]
        ) as locks:
            result = _overlay.check(facts, [], True)

        self.assertEqual(result, 0)
        locks.assert_called_once_with(facts, True)


if __name__ == "__main__":
    unittest.main()
