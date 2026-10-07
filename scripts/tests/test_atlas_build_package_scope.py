#!/usr/bin/env python3
"""A path package's record moves with its own files and the files it reads, never its repository."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_build_identity as identity
import atlas_build_inputs as build_inputs
from atlas_build_artifacts import UNVERIFIED
from atlas_build_package_identity import package_identities


B_SOURCE = "//! b\n#[path = \"../../common/m.rs\"]\nmod m;\n/// b\npub fn b() -> u32 { m::M }\n"


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True, timeout=60
    ).stdout.strip()


def init_repository(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    git(root, "init", "-q")
    for key, value in (
        ("user.name", "Atlas test"),
        ("user.email", "atlas-test@example.invalid"),
        ("gc.auto", "0"),
        ("maintenance.auto", "false"),
    ):
        git(root, "config", key, value)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "source")


def cleaned_names(command: list[str]) -> list[str] | None:
    if len(command) < 2 or command[1] != "clean":
        return None
    return [command[i + 1] for i, value in enumerate(command) if value == "-p"] or ["<whole target>"]


class PackageIdentityTestCase(unittest.TestCase):
    """`package_identities` without Cargo: a root package at the repository
    top and a member nested inside it."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-package-identity-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / "repo"
        init_repository(
            self.root,
            {"Cargo.toml": "[package]\n", "src/lib.rs": "", "c/Cargo.toml": "", "c/src/lib.rs": ""},
        )

    def identities(self) -> tuple[dict[str, str], dict[str, str]]:
        found = package_identities((self.root, self.root / "c"))
        return found[self.root], found[self.root / "c"]

    def test_a_nested_members_files_are_not_its_containers(self) -> None:
        root, member = self.identities()
        (self.root / "c" / "src" / "lib.rs").write_text("edit\n", encoding="utf-8")
        git(self.root, "commit", "-qam", "edit c")
        after_root, after_member = self.identities()
        self.assertEqual(after_root, root)
        self.assertNotEqual(after_member["files"], member["files"])

    def test_the_root_package_owns_the_files_no_member_does(self) -> None:
        root, member = self.identities()
        (self.root / "README.md").write_text("notes\n", encoding="utf-8")
        dirty_root, dirty_member = self.identities()
        self.assertNotEqual(dirty_root["dirty"], root["dirty"])
        self.assertEqual(dirty_member, member)
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-qm", "notes")
        committed_root, _ = self.identities()
        self.assertNotEqual(committed_root["files"], root["files"])
        self.assertEqual(committed_root["dirty"], "")

    def test_a_revision_alone_moves_no_identity(self) -> None:
        before = self.identities()
        git(self.root, "commit", "-q", "--allow-empty", "-m", "empty")
        self.assertEqual(self.identities(), before)

    def test_a_deleted_file_is_dirty(self) -> None:
        root, member = self.identities()
        (self.root / "c" / "src" / "lib.rs").unlink()
        self.assertEqual(self.identities()[0], root)
        self.assertNotEqual(self.identities()[1]["dirty"], member["dirty"])


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class PackageScopeTestCase(unittest.TestCase):
    """A clippy step's cleans, with real Cargo, in a virtual workspace: `a`
    depends on `b`, and `c` is independent. `a` reads `shared/x.txt` and
    `c/data.txt`; `b` takes a `#[path]` module from `common/m.rs`, and its
    build script watches `../proto`. Each run exports the source afresh, as
    the gate's first push to a new export path does, and each case's
    repeat push cleans nothing.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-package-scope-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.source = self.base / "src_repo"
        files = {
            "Cargo.toml": '[workspace]\nmembers = ["a", "b", "c"]\nresolver = "2"\n',
            "a/Cargo.toml": (
                '[package]\nname = "a"\nversion = "0.1.0"\nedition = "2021"\n'
                "[dependencies]\nb = { path = \"../b\" }\n"
            ),
            "a/src/lib.rs": (
                "//! a\n/// x\npub const X: &str = include_str!(\"../../shared/x.txt\");\n"
                "/// d\npub const D: &str = include_str!(\"../../c/data.txt\");\n"
                "/// a\npub fn a() -> u32 { b::b() + 1 }\n"
            ),
            "b/Cargo.toml": '[package]\nname = "b"\nversion = "0.1.0"\nedition = "2021"\n',
            "b/build.rs": (
                "fn main() {\n    println!(\"cargo:rerun-if-changed=../proto\");\n"
                "    println!(\"cargo:rerun-if-changed=build.rs\");\n}\n"
            ),
            "b/src/lib.rs": B_SOURCE,
            "c/Cargo.toml": '[package]\nname = "c"\nversion = "0.1.0"\nedition = "2021"\n',
            "c/src/lib.rs": "//! c\n/// c\npub fn c() -> u32 { 3 }\n",
            "c/data.txt": "data\n",
            "shared/x.txt": "x\n",
            "common/m.rs": "pub const M: u32 = 1;\n",
            "proto/p.txt": "p\n",
        }
        for relative, text in files.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        init_repository(self.source, {})
        self.target = self.base / "target"
        self.log = self.base / "cargo.log"
        # Logs every cargo the checker starts; after a clippy, writes the
        # file `PLANT` names (`<path>\n<content>`), as a peer could.
        self.wrapper = self.base / "cargo_log.py"
        self.wrapper.write_text(
            "import json, os, subprocess, sys\n"
            f"with open({str(self.log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(['cargo', *sys.argv[1:]]) + '\\n')\n"
            "code = subprocess.run(['cargo', *sys.argv[1:]]).returncode\n"
            "plant = os.environ.get('PLANT')\n"
            "if plant and sys.argv[1] == 'clippy':\n"
            "    path, content = plant.split('\\n', 1)\n"
            "    open(path, 'w', encoding='utf-8').write(content)\n"
            "raise SystemExit(code)\n",
            encoding="utf-8",
        )
        self.exports = 0

    def export(self, plant: dict[str, str] | None = None) -> Path:
        """A fresh export of the source, with `plant`'s untracked files written into it."""
        self.exports += 1
        export = self.base / f"gate{self.exports}" / "nested" / "ws"
        export.parent.mkdir(parents=True)
        subprocess.run(["git", "clone", "-q", str(self.source), str(export)], check=True)
        for relative, text in (plant or {}).items():
            (export / relative).write_text(text, encoding="utf-8")
        return export

    def run_step(
        self, export: Path, packages: tuple[str, ...], environment: dict[str, str] | None = None
    ) -> list[str]:
        """One clippy step over `packages`; the packages its one `cargo clean` named."""
        self.log.unlink(missing_ok=True)
        manifest = str(export / "Cargo.toml")
        with (
            patch.dict(os.environ, {**self.environment, **(environment or {})}, clear=True),
            patch.object(identity, "_cargo_command", return_value=(sys.executable, str(self.wrapper))),
        ):
            identity.run_build(
                export,
                export / "Cargo.toml",
                packages,
                self.target,
                ["cargo", "clippy", "-q", "--manifest-path", manifest, "--locked", "--offline",
                 *(argument for package in packages for argument in ("-p", package))],
                command_cwd=export,
                command_key="atlas-pre-push",
            )
        lines = self.log.read_text(encoding="utf-8").splitlines()
        cleans = [names for line in lines if (names := cleaned_names(json.loads(line))) is not None]
        self.assertLessEqual(len(cleans), 1, cleans)
        return cleans[0] if cleans else []

    def commit(self, files: dict[str, str], message: str = "edit") -> None:
        for relative, text in files.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "--allow-empty", "-m", message)

    def assert_cleans(
        self,
        expected: dict[str, list[str]],
        change: dict[str, str] | None = None,
        plant: dict[str, str] | None = None,
    ) -> None:
        """After a baseline push of `a` and `c`, a push of the commit
        writing `change` (or of `plant`'s untracked files) cleans `expected`
        per package; a repeat push of the same tree, nothing."""
        export = self.export()
        for package in ("a", "c"):
            self.run_step(export, (package,))
        if change is not None:
            self.commit(change)
        export = self.export(plant)
        self.assertEqual({package: self.run_step(export, (package,)) for package in expected}, expected)
        export = self.export(plant)
        self.assertEqual(
            {package: self.run_step(export, (package,)) for package in expected},
            {package: [] for package in expected},
        )

    def record(self, package: str) -> dict[str, object]:
        for path in (self.target / ".atlas" / "source-identity").glob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if value["build"]["package"] == package:
                return value
        raise AssertionError(f"no record for {package}")

    def test_a_commit_to_c_cleans_c_alone(self) -> None:
        self.assert_cleans(
            {"a": [], "c": ["c"]},
            change={"c/src/lib.rs": "//! c\n/// c\npub fn c() -> u32 { 4 }\n"},
        )

    def test_an_edit_to_b_cleans_b_under_a(self) -> None:
        self.assert_cleans(
            {"a": ["b"], "c": []},
            change={"b/src/lib.rs": B_SOURCE.replace("m::M }", "m::M + 1 }")},
        )

    def test_an_included_file_outside_every_package_cleans_its_reader(self) -> None:
        self.assert_cleans({"a": ["a"], "c": []}, change={"shared/x.txt": "y\n"})

    def test_an_included_file_in_another_package_cleans_both(self) -> None:
        self.assert_cleans({"a": ["a"], "c": ["c"]}, change={"c/data.txt": "other\n"})

    def test_a_path_module_outside_the_package_cleans_its_package(self) -> None:
        self.assert_cleans({"a": ["b"], "c": []}, change={"common/m.rs": "pub const M: u32 = 2;\n"})

    def test_a_file_added_under_a_watched_directory_cleans_the_build_scripts_package(self) -> None:
        self.assert_cleans({"a": ["b"], "c": []}, change={"proto/q.txt": "q\n"})

    def test_a_workspace_profile_edit_cleans_every_path_package(self) -> None:
        self.assert_cleans(
            {"a": ["a", "b"], "c": ["c"]},
            change={
                "Cargo.toml": '[workspace]\nmembers = ["a", "b", "c"]\nresolver = "2"\n'
                "[profile.dev]\nopt-level = 1\n"
            },
        )

    def test_an_untracked_file_in_c_cleans_nothing_under_a(self) -> None:
        self.assert_cleans({"a": [], "c": ["c"]}, plant={"c/notes.txt": "n\n"})

    def test_an_untracked_file_in_a_cleans_a(self) -> None:
        self.assert_cleans({"a": ["a"], "c": []}, plant={"a/src/notes.txt": "n\n"})

    def test_an_empty_commit_cleans_nothing(self) -> None:
        self.assert_cleans({"a": [], "c": []}, change={})

    def test_the_record_lists_each_packages_inputs_outside_its_directory(self) -> None:
        export = self.export()
        self.run_step(export, ("a",))
        inputs = self.record("a")["inputs"]
        self.assertEqual(set(inputs), {"a", "b"})
        # Clippy's dep-info also names the workspace manifest.
        self.assertEqual(set(inputs["a"]), {"Cargo.toml", "c/data.txt", "shared/x.txt"})
        self.assertEqual(set(inputs["b"]), {"Cargo.toml", "common/m.rs", "proto"})
        self.assertTrue(inputs["b"]["proto"].startswith("dir:"))

    def test_two_checkouts_differing_in_an_input_clean_its_reader(self) -> None:
        """Cargo trusts the other checkout's artifact of `a`: its fingerprint
        names that checkout's `shared/x.txt`, older than the artifact."""
        first = self.export()
        second = self.export()
        (second / "shared" / "x.txt").write_text("second\n", encoding="utf-8")
        git(second, "-c", "user.name=t", "-c", "user.email=t@e.invalid", "commit", "-qam", "x")
        self.run_step(first, ("a",))
        self.assertEqual(self.run_step(second, ("a",)), ["a"])
        self.assertEqual(self.run_step(first, ("a",)), ["a"])
        self.assertEqual(self.run_step(first, ("a",)), [])

    def test_an_earlier_version_record_cleans_every_path_package_once(self) -> None:
        self.run_step(self.export(), ("a",))
        for version in (5, 6):
            for path in (self.target / ".atlas" / "source-identity").glob("*.json"):
                value = json.loads(path.read_text(encoding="utf-8"))
                value["version"] = version
                path.write_text(json.dumps(value), encoding="utf-8")
            self.assertEqual(self.run_step(self.export(), ("a",)), ["a", "b"], version)
            self.assertEqual(self.run_step(self.export(), ("a",)), [], version)

    def test_a_dep_info_naming_a_foreign_file_leaves_the_package_unverified(self) -> None:
        foreign = self.base / "elsewhere" / "f.rs"
        planted = self.target / "debug" / "deps" / "a-0000000000000000.d"
        self.run_step(
            self.export(), ("a",), {"PLANT": f"{planted}\nunit: {foreign}\n"}
        )
        self.assertEqual(self.record("a")["inputs"]["a"], UNVERIFIED)
        self.assertIn("common/m.rs", self.record("a")["inputs"]["b"])
        self.assertEqual(self.run_step(self.export(), ("a",)), ["a"])
        self.assertEqual(self.run_step(self.export(), ("a",)), [])


class DeclaredArtifactTestCase(unittest.TestCase):
    """A run of declared artifact paths has no snapshot, so the repository's
    revision still decides: an empty commit cleans the package."""

    def test_an_empty_commit_still_cleans_a_declared_artifacts_package(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-declared-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        root = base / "repo"
        init_repository(root, {"Cargo.toml": "[package]\nname = \"demo\"\n", "src/lib.rs": ""})
        artifact = base / "target" / "debug" / "deps" / "libdemo-abcdef.rlib"
        log = base / "clean.log"

        def build() -> identity.BuildResult:
            with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
                return identity.run_build(
                    root,
                    root / "Cargo.toml",
                    ("demo",),
                    base / "target",
                    [sys.executable, "-c",
                     f"from pathlib import Path; p = Path({str(artifact)!r}); "
                     "p.parent.mkdir(parents=True, exist_ok=True); p.write_text('built')"],
                    artifact_paths=[artifact],
                    clean_command=[sys.executable, "-c",
                                   f"open({str(log)!r}, 'a').write('cleaned\\n')"],
                )[0]

        artifact.parent.mkdir(parents=True)
        build()
        log.unlink()
        self.assertEqual(build().status, "reused")
        self.assertFalse(log.exists())
        git(root, "commit", "-q", "--allow-empty", "-m", "empty")
        self.assertEqual(build().status, "rebuilt")
        self.assertEqual(log.read_text(encoding="utf-8"), "cleaned\n")
        record = json.loads(build().record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["inputs"], {})


if __name__ == "__main__":
    unittest.main()
