"""Actual Git/Cargo regressions for immutable snapshot confinement."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from atlas_cargo_snapshot import (  # noqa: E402
    CargoSnapshotError,
    SelectedRepository,
    create_snapshot,
)


class SnapshotFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repos = root / "origins" / "repos"
        self.repos.mkdir(parents=True)
        self.environment = dict(os.environ)
        self.environment["CARGO_HOME"] = str(root / "cargo-home")

    def run(self, command: list[str], cwd: Path) -> str:
        result = subprocess.run(command, cwd=cwd, env=self.environment, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=30)
        if result.returncode:
            raise AssertionError(f"{' '.join(command)} failed:\n{result.stderr}")
        return result.stdout

    def package(self, root: Path, name: str, extra: str = "") -> None:
        (root / "src").mkdir(parents=True)
        (root / "Cargo.toml").write_text(
            f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n{extra}',
            encoding="utf-8",
        )
        (root / "src" / "lib.rs").write_text("pub fn value() -> u32 { 1 }\n", encoding="utf-8")

    def commit(self, name: str, *, locks: tuple[Path, ...] = (), generate: bool = True) -> SelectedRepository:
        repo = self.repos / name
        if generate:
            for root in (repo, *locks):
                self.run(["cargo", "generate-lockfile", "--offline"], root)
        self.run(["git", "init", "--quiet"], repo)
        self.run(["git", "config", "user.name", "Snapshot fixture"], repo)
        self.run(["git", "config", "user.email", "fixture@example.invalid"], repo)
        self.run(["git", "add", "--all"], repo)
        self.run(["git", "commit", "--quiet", "-m", "Add fixture"], repo)
        revision = self.run(["git", "rev-parse", "HEAD"], repo).strip()
        return SelectedRepository(repo, revision)


class CargoSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = SnapshotFixture(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_snapshot_retains_basis_cross_member_paths_and_every_lock(self) -> None:
        provider = self.fixture.repos / "provider"
        self.fixture.package(provider, "provider")
        provider_selection = self.fixture.commit("provider")
        consumer = self.fixture.repos / "consumer"
        self.fixture.package(consumer, "consumer", '[dependencies]\nprovider={path="../provider"}\n')
        nested = consumer / "target" / "worktrees" / "leaf"
        self.fixture.package(nested, "tracked-leaf")
        consumer_selection = self.fixture.commit("consumer", locks=(nested,))

        snapshot = create_snapshot(
            {"provider": provider_selection, "consumer": consumer_selection},
            self.root / "snapshot",
        )

        self.assertEqual(snapshot.basis, (("consumer", consumer_selection.revision),
                                          ("provider", provider_selection.revision)))
        self.assertEqual(
            {str(lock) for lock in snapshot.locks},
            {"repos/consumer/Cargo.lock", "repos/consumer/target/worktrees/leaf/Cargo.lock",
             "repos/provider/Cargo.lock"},
        )
        self.assertEqual(dict(snapshot.lock_bytes)[snapshot.locks[0]],
                         snapshot.root.joinpath(snapshot.locks[0]).read_bytes())

    def test_member_names_and_revision_selectors_fail_before_export(self) -> None:
        repo = self.fixture.repos / "valid"
        self.fixture.package(repo, "valid")
        selected = self.fixture.commit("valid")
        for index, name in enumerate((r"..\escaped", r"..\..\escaped", "../escaped")):
            with self.subTest(name=name), self.assertRaisesRegex(CargoSnapshotError, "unsafe"):
                create_snapshot({name: selected}, self.root / f"unsafe-{index}")
        with self.assertRaisesRegex(CargoSnapshotError, "full commit ID"):
            create_snapshot({"valid": SelectedRepository(repo, "HEAD")}, self.root / "moving")

    def test_external_workspace_and_dependency_inputs_are_rejected(self) -> None:
        workspace = self.root / "live-workspace"
        package = self.fixture.repos / "workspace-reader"
        self.fixture.package(package, "workspace-reader")
        manifest = package / "Cargo.toml"
        manifest.write_text(
            f'[package]\nname="workspace-reader"\nversion.workspace=true\nedition="2024"\n'
            f'workspace="{workspace.as_posix()}"\n', encoding="utf-8"
        )
        workspace.mkdir()
        (workspace / "Cargo.toml").write_text(
            f'[workspace]\nmembers=["{package.as_posix()}"]\nresolver="3"\n'
            '[workspace.package]\nversion="0.1.0"\n', encoding="utf-8"
        )
        self.fixture.run(["cargo", "generate-lockfile", "--manifest-path", str(manifest)], package)
        (package / "Cargo.lock").write_bytes((workspace / "Cargo.lock").read_bytes())
        first = json.loads(self.fixture.run(
            ["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1",
             "--manifest-path", str(manifest)], package
        ))["packages"][0]["version"]
        (workspace / "Cargo.toml").write_text(
            f'[workspace]\nmembers=["{package.as_posix()}"]\nresolver="3"\n'
            '[workspace.package]\nversion="9.0.0"\n', encoding="utf-8"
        )
        second = json.loads(self.fixture.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1",
             "--manifest-path", str(manifest)], package
        ))["packages"][0]["version"]
        self.assertEqual((first, second), ("0.1.0", "9.0.0"))
        selected = self.fixture.commit("workspace-reader")
        with self.assertRaisesRegex(CargoSnapshotError, "absolute package.workspace"):
            create_snapshot({"workspace-reader": selected}, self.root / "workspace-snapshot")

        external = self.root / "external-dependency"
        self.fixture.package(external, "external-dependency")
        isolated = self.fixture.repos / "path-reader"
        self.fixture.package(isolated, "path-reader",
                             f'[dependencies]\nexternal-dependency={{path="{external.as_posix()}"}}\n')
        selected = self.fixture.commit("path-reader")
        with self.assertRaisesRegex(CargoSnapshotError, "absolute dependency"):
            create_snapshot({"path-reader": selected}, self.root / "path-snapshot")

        member_reader = self.fixture.repos / "member-reader"
        member_reader.mkdir()
        (member_reader / "Cargo.toml").write_text(
            f'[workspace]\nmembers=["{external.as_posix()}"]\nresolver="3"\n',
            encoding="utf-8",
        )
        (member_reader / "Cargo.lock").write_text("version = 4\n", encoding="utf-8")
        selected = self.fixture.commit("member-reader", generate=False)
        with self.assertRaisesRegex(CargoSnapshotError, "absolute workspace.members"):
            create_snapshot({"member-reader": selected}, self.root / "member-snapshot")


if __name__ == "__main__":
    unittest.main()
