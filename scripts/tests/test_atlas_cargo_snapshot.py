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
from atlas_cargo_snapshot import CargoSnapshotError, SelectedRepository, create_snapshot  # noqa: E402


class SnapshotFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.repos = root / "origins" / "repos"
        self.repos.mkdir(parents=True)
        self.environment = dict(os.environ, CARGO_HOME=str(root / "cargo-home"))

    def result(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(command, cwd=cwd, env=self.environment, capture_output=True,
                              timeout=30, check=False)

    def run(self, command: list[str], cwd: Path) -> str:
        result = self.result(command, cwd)
        if result.returncode:
            raise AssertionError(f"{' '.join(command)} failed:\n{result.stderr.decode(errors='replace')}")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def package(self, root: Path, name: str, extra: str = "") -> None:
        (root / "src").mkdir(parents=True)
        (root / "Cargo.toml").write_text(
            f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n{extra}',
            encoding="utf-8",
        )
        (root / "src/lib.rs").write_text("pub fn value() -> u32 { 1 }\n", encoding="utf-8")

    def lock(self, root: Path, name: str) -> None:
        (root / "Cargo.lock").write_text(
            f'version = 4\n\n[[package]]\nname = "{name}"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )

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
        return SelectedRepository(repo, self.run(["git", "rev-parse", "HEAD"], repo))


class CargoSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = SnapshotFixture(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_raw_snapshot_retains_basis_paths_modes_and_every_lock(self) -> None:
        provider = self.fixture.repos / "provider"
        self.fixture.package(provider, "provider")
        provider_selection = self.fixture.commit("provider")
        consumer = self.fixture.repos / "consumer"
        self.fixture.package(consumer, "consumer", '[dependencies]\nprovider={path="../provider"}\n')
        nested = consumer / "target/worktrees/leaf"
        self.fixture.package(nested, "tracked-leaf")
        consumer_selection = self.fixture.commit("consumer", locks=(nested,))
        (consumer / ".gitattributes").write_text("target/worktrees export-ignore\n", encoding="utf-8")
        consumer_selection = self.fixture.commit("consumer", locks=(nested,))
        filter_script = self.root / "smudge.py"
        filter_script.write_text(
            "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read().replace(b'0.1.0',b'9.0.0'))",
            encoding="utf-8",
        )
        self.fixture.run(["git", "config", "core.autocrlf", "true"], consumer)
        (consumer / ".git/info/attributes").write_text("Cargo.toml filter=boundary\n")
        self.fixture.run(["git", "config", "filter.boundary.smudge",
                          f'"{sys.executable}" "{filter_script}"'], consumer)
        snapshot = create_snapshot(
            {"provider": provider_selection, "consumer": consumer_selection},
            self.root / "snapshot",
        )
        self.assertEqual(snapshot.basis, (("consumer", consumer_selection.revision),
                                          ("provider", provider_selection.revision)))
        self.assertEqual({str(lock) for lock in snapshot.locks}, {
            "repos/consumer/Cargo.lock", "repos/consumer/target/worktrees/leaf/Cargo.lock",
            "repos/provider/Cargo.lock",
        })
        for name in ("Cargo.toml", "Cargo.lock"):
            raw = self.fixture.result(
                ["git", "--no-replace-objects", "show", f"{consumer_selection.revision}:{name}"],
                consumer,
            ).stdout
            self.assertEqual(snapshot.root.joinpath("repos/consumer", name).read_bytes(), raw)
        self.assertEqual(dict(snapshot.lock_bytes)[snapshot.locks[0]],
                         snapshot.root.joinpath(snapshot.locks[0]).read_bytes())

    def test_member_revision_and_tree_entry_boundaries_fail_closed(self) -> None:
        repo = self.fixture.repos / "valid"
        self.fixture.package(repo, "valid")
        selected = self.fixture.commit("valid")
        for index, name in enumerate((r"..\escaped", r"..\..\escaped", "../escaped")):
            with self.subTest(name=name), self.assertRaisesRegex(CargoSnapshotError, "unsafe"):
                create_snapshot({name: selected}, self.root / f"unsafe-{index}")
        with self.assertRaisesRegex(CargoSnapshotError, "full commit ID"):
            create_snapshot({"valid": SelectedRepository(repo, "HEAD")}, self.root / "moving")
        manifest = repo / "Cargo.toml"
        manifest.write_text(manifest.read_text().replace('name="valid"', 'name="replacement"'))
        replacement = self.fixture.commit("valid")
        self.fixture.run(["git", "replace", selected.revision, replacement.revision], repo)
        snapshot = create_snapshot({"valid": selected}, self.root / "replace-neutral")
        self.assertIn('name="valid"', snapshot.root.joinpath("repos/valid/Cargo.toml").read_text())
        link_data = self.root / "link-target"
        link_data.write_text("Cargo.toml")
        blob = self.fixture.run(["git", "hash-object", "-w", str(link_data)], repo)
        self.fixture.run(["git", "update-index", "--add", "--cacheinfo", f"120000,{blob},linked"], repo)
        self.fixture.run(["git", "commit", "--quiet", "-m", "Add symlink"], repo)
        with self.assertRaisesRegex(CargoSnapshotError, "unsupported entry"):
            revision = self.fixture.run(["git", "rev-parse", "HEAD"], repo)
            create_snapshot({"valid": SelectedRepository(repo, revision)}, self.root / "symlink")
        unlocked = self.fixture.repos / "unlocked"
        self.fixture.package(unlocked, "unlocked")
        with self.assertRaisesRegex(CargoSnapshotError, "root Cargo.lock"):
            create_snapshot({"unlocked": self.fixture.commit("unlocked", generate=False)},
                            self.root / "unlocked")

    def test_external_workspace_dependency_and_target_paths_are_rejected(self) -> None:
        external = self.root / "external.rs"
        external.write_text("pub fn external() {}\n")
        cases = {
            "dependency": f'[dependencies]\nx={{path="{external.as_posix()}"}}\n',
            "patch": f'[patch.crates-io]\nx={{path="{external.as_posix()}"}}\n',
            "build": f'build="{external.as_posix()}"\n',
            "lib": f'[lib]\npath="{external.as_posix()}"\n',
            **{field: f'[[{field}]]\nname="x"\npath="{external.as_posix()}"\n'
               for field in ("bin", "test", "bench", "example")},
        }
        for name, extra in cases.items():
            root = self.fixture.repos / name
            self.fixture.package(root, name, extra)
            self.fixture.lock(root, name)
            selected = self.fixture.commit(name, generate=False)
            with self.subTest(name=name), self.assertRaisesRegex(CargoSnapshotError, "absolute"):
                create_snapshot({name: selected}, self.root / f"{name}-snapshot")

        origins = self.root / "origins"
        origins.joinpath("Cargo.toml").write_text(
            '[workspace]\nmembers=["repos/implicit"]\nresolver="3"\n'
            '[workspace.package]\nversion="0.1.0"\n', encoding="utf-8",
        )
        implicit = self.fixture.repos / "implicit"
        self.fixture.package(implicit, "implicit")
        manifest = implicit / "Cargo.toml"
        manifest.write_text(manifest.read_text().replace('version="0.1.0"', "version.workspace=true"))
        selected = self.fixture.commit("implicit")
        command = ["cargo", "metadata", "--no-deps", "--format-version", "1",
                   "--manifest-path", str(manifest)]
        first = json.loads(self.fixture.run([*command[:2], "--locked", *command[2:]], implicit))["packages"][0]["version"]
        origins.joinpath("Cargo.toml").write_text(
            origins.joinpath("Cargo.toml").read_text().replace("0.1.0", "9.0.0")
        )
        second = json.loads(self.fixture.run(command, implicit))["packages"][0]["version"]
        self.assertEqual((first, second), ("0.1.0", "9.0.0"))
        with self.assertRaisesRegex(CargoSnapshotError, "external workspace ancestor"):
            create_snapshot({"implicit": selected}, origins / "snapshot")
