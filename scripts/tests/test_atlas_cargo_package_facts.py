"""Real Cargo/Git regressions for native package facts."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from atlas_cargo_package_facts import (  # noqa: E402
    PackageFactError, ProviderIdentity, SelectedRepository, load_selected, load_working,
)


class NativeFactsFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repos = root / "origins/repos"
        self.repos.mkdir(parents=True)
        cargo_home = root / "cargo-home"
        cargo_home.mkdir()
        (cargo_home / "config.toml").write_text("[net]\ngit-fetch-with-cli = true\n")
        self.environment = dict(os.environ, CARGO_HOME=str(cargo_home), GIT_CONFIG_NOSYSTEM="1")
        self.gitconfig = root / "gitconfig"
        self.environment["GIT_CONFIG_GLOBAL"] = str(self.gitconfig)
        self.gitconfig.write_text("")
        self._create_path_provider()
        self._create_provider()
        provider_uri = (self.repos / "provider").as_uri()
        self.gitconfig.write_text(
            f'[url "{provider_uri}"]\n\tinsteadOf = https://github.com/ryancinsight/provider.git\n'
        )
        self._create_consumer("consumer", "native-provider")
        self._create_cross_member()

    def run(self, command: list[str], cwd: Path) -> str:
        result = subprocess.run(command, cwd=cwd, env=self.environment, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=30)
        if result.returncode:
            raise AssertionError(f"{' '.join(command)} failed:\n{result.stderr}")
        return result.stdout.strip()

    def package(self, root: Path, name: str, extra: str = "") -> None:
        (root / "src").mkdir(parents=True)
        (root / "Cargo.toml").write_text(
            f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2024"\n{extra}'
        )
        (root / "src/lib.rs").write_text("pub fn identity(value: u32) -> u32 { value }\n")

    def commit(self, repo: Path, *, locked: bool = True) -> str:
        if locked:
            self.run(["cargo", "generate-lockfile"], repo)
        self.run(["git", "init", "--quiet"], repo)
        self.run(["git", "config", "user.name", "Native facts fixture"], repo)
        self.run(["git", "config", "user.email", "fixture@example.invalid"], repo)
        self.run(["git", "add", "--all"], repo)
        self.run(["git", "commit", "--quiet", "-m", "Add fixture"], repo)
        return self.run(["git", "rev-parse", "HEAD"], repo)

    def _create_path_provider(self) -> None:
        root = self.repos / "path-provider"
        self.package(root, "path-provider")
        self.commit(root)
        self.provider_branch = self.run(["git", "branch", "--show-current"], root)

    def _create_provider(self) -> None:
        root = self.repos / "provider"
        (root / "included").mkdir(parents=True)
        (root / "excluded").mkdir()
        (root / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["included"]\nexclude = ["excluded"]\nresolver = "3"\n'
        )
        self.package(root / "included", "native-provider")
        self.package(root / "excluded", "excluded-provider")
        self.commit(root)

    def _create_consumer(self, member: str, package: str) -> None:
        root = self.repos / member
        dependency = (f'{{ package = "{package}", '
                      f'git = "https://github.com/ryancinsight/provider.git", '
                      f'branch = "{self.provider_branch}", version = "^0.1" }}')
        (root / "crate").mkdir(parents=True)
        aliases = ("normal", "development", "build", "targeted")
        (root / "Cargo.toml").write_text(
            '[workspace]\nmembers = ["crate"]\nresolver = "3"\n[workspace.dependencies]\n'
            + "\n".join(f"{alias} = {dependency}" for alias in aliases) + "\n"
        )
        self.package(root / "crate", f"{member}-crate",
                     "[dependencies]\nnormal = { workspace = true }\n"
                     "[dev-dependencies]\ndevelopment = { workspace = true }\n"
                     "[build-dependencies]\nbuild = { workspace = true }\n"
                     "[target.'cfg(unix)'.dependencies]\ntargeted = { workspace = true }\n")
        self.commit(root)

    def _create_cross_member(self) -> None:
        root = self.repos / "cross-member"
        self.package(root, "cross-member",
                     '[dependencies]\npath-provider = { path = "../path-provider" }\n')
        self.commit(root)

    def selections(self, *names: str) -> dict[str, SelectedRepository]:
        return {name: SelectedRepository(
            self.repos / name, self.run(["git", "rev-parse", "HEAD"], self.repos / name)
        ) for name in names}


class NativePackageFactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.fixture = NativeFactsFixture(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_cargo_owns_inheritance_kinds_targets_and_paths(self) -> None:
        names = ("provider", "consumer", "path-provider", "cross-member")
        destination = self.root / "selected"
        catalog = load_selected(self.fixture.selections(*names), destination)
        identity = ProviderIdentity("native-provider", "provider")
        self.assertEqual(set(catalog.providers), {identity})
        self.assertEqual(catalog.providers[identity].manifest.parts[1], "provider")
        self.assertEqual(catalog.basis, tuple(
            (name, self.fixture.selections(name)[name].revision) for name in sorted(names)
        ))
        consumer = next(package for package in catalog.packages if package.name == "consumer-crate")
        self.assertEqual({dependency.provider for dependency in consumer.dependencies}, {identity})
        self.assertEqual({dependency.repository_url for dependency in consumer.dependencies},
                         {"https://github.com/ryancinsight/provider.git"})
        self.assertTrue(all("?branch=" in dependency.source for dependency in consumer.dependencies))
        self.assertEqual(
            {(dependency.rename, dependency.kind, dependency.target) for dependency in consumer.dependencies},
            {("normal", None, None), ("development", "dev", None),
             ("build", "build", None), ("targeted", None, "cfg(unix)")},
        )
        cross = next(package for package in catalog.packages if package.name == "cross-member")
        self.assertEqual((cross.dependencies[0].package, cross.dependencies[0].source),
                         ("path-provider", None))
        self.assertFalse(any(destination.rglob("target")))

    def test_consumed_provider_is_bound_to_its_declared_repository(self) -> None:
        self.fixture._create_consumer("excluded-consumer", "excluded-provider")
        with self.assertRaisesRegex(PackageFactError, "excluded-provider.*0 selected providers"):
            load_selected(self.fixture.selections("provider", "excluded-consumer"),
                          self.root / "missing-selected")
        duplicate = self.fixture.repos / "duplicate"
        self.fixture.package(duplicate, "native-provider")
        self.fixture.commit(duplicate)
        catalog = load_selected(self.fixture.selections("provider", "consumer", "duplicate"),
                                self.root / "unrelated-duplicate-selected")
        identity = ProviderIdentity("native-provider", "provider")
        self.assertEqual(catalog.providers[identity].manifest.parts[1], "provider")
        with self.assertRaisesRegex(PackageFactError, "native-provider.*0 selected providers"):
            load_selected({"consumer": self.fixture.selections("consumer")["consumer"],
                           "wrong": self.fixture.selections("duplicate")["duplicate"]},
                          self.root / "wrong-selected")
        ambiguous = self.fixture.repos / "ambiguous"
        self.fixture.package(ambiguous, "native-provider", '[workspace]\nexclude=["nested"]\n')
        self.fixture.package(ambiguous / "nested", "native-provider")
        self.fixture.run(["cargo", "generate-lockfile"], ambiguous / "nested")
        revision = self.fixture.commit(ambiguous)
        with self.assertRaisesRegex(PackageFactError, "native-provider.*2 selected providers"):
            load_selected({"provider": SelectedRepository(ambiguous, revision),
                           "consumer": self.fixture.selections("consumer")["consumer"]},
                          self.root / "ambiguous-selected")

    def test_working_facts_change_while_selected_facts_remain_pinned(self) -> None:
        names = ("provider", "consumer")
        selected = self.fixture.selections(*names)
        manifest = self.fixture.repos / "provider/included/Cargo.toml"
        manifest.write_text(manifest.read_text().replace('version = "0.1.0"', 'version = "0.2.0"'))
        self.fixture.run(["cargo", "generate-lockfile"], self.fixture.repos / "provider")
        working = load_working({name: self.fixture.repos / name for name in names})
        pinned = load_selected(selected, self.root / "still-selected")
        versions = lambda catalog: {package.version for package in catalog.packages
                                    if package.name == "native-provider"}
        self.assertEqual((versions(working), versions(pinned)), ({"0.2.0"}, {"0.1.0"}))
        self.assertEqual(working.basis, (("consumer", None), ("provider", None)))
