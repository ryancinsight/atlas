#!/usr/bin/env python3
"""Tests for Cargo artifact ownership and dependency snapshots."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_build_identity_test_support import (
    BuildIdentityError,
    BuildIdentityFixture,
    TargetDirectory,
    artifacts,
    build_workflow,
    git,
    identity,
    init_repo,
)


class ArtifactIdentityTestCase(BuildIdentityFixture):
    def test_artifact_paths_must_stay_inside_the_shared_target(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rlib"
        outside.write_text("outside", encoding="utf-8")
        with TargetDirectory(self.target, create=True) as target:
            with self.assertRaises(BuildIdentityError):
                artifacts.artifact_identity(
                    self.root,
                    target,
                    "demo",
                    "debug",
                    [outside],
                )

    def test_dependency_snapshot_tracks_reachable_path_sources(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency_root = self.base / "dependency"
        dependency_root.mkdir()
        (dependency_root / "Cargo.toml").write_text("[package]\nname = \"dep\"\n", encoding="utf-8")
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "path+dep 0.1.0",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((dependency_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "path+dep 0.1.0", "dep_kinds": []}]},
                    {"id": "path+dep 0.1.0", "deps": []},
                ]
            },
        }
        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "b"},
            )
        self.assertNotEqual(first["digest"], second["digest"])
        self.assertEqual(first["clean_packages"], ["demo", "dep"])

    def test_git_dependency_tracks_inputs_outside_its_package_directory(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency_root = self.base / "git-dependency"
        package_root = dependency_root / "crates" / "dep"
        (package_root / "src").mkdir(parents=True)
        (dependency_root / "Cargo.toml").write_text(
            "[workspace]\nmembers = [\"crates/dep\"]\nresolver = \"3\"\n",
            encoding="utf-8",
        )
        (package_root / "Cargo.toml").write_text(
            "[package]\nname = \"dep\"\nversion = \"0.1.0\"\n",
            encoding="utf-8",
        )
        (dependency_root / "shared.rs").write_text(
            "pub const VALUE: u8 = 1;\n", encoding="utf-8"
        )
        (package_root / "src" / "lib.rs").write_text(
            'include!("../../../shared.rs");\n', encoding="utf-8"
        )
        git(dependency_root, "init", "-q")
        git(dependency_root, "config", "user.name", "Atlas test")
        git(dependency_root, "config", "user.email", "atlas-test@example.invalid")
        git(dependency_root, "add", ".")
        git(dependency_root, "commit", "-q", "-m", "git dependency")
        source_text = "git+https://example.invalid/dep#revision"
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "git dep 0.1.0",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": source_text,
                    "manifest_path": str((package_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "git dep 0.1.0", "dep_kinds": []}]},
                    {"id": "git dep 0.1.0", "deps": []},
                ]
            },
        }

        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: identity.source_identity(path).as_dict(),
            )
            (dependency_root / "shared.rs").write_text(
                "pub const VALUE: u8 = 2;\n", encoding="utf-8"
            )
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: identity.source_identity(path).as_dict(),
            )

        self.assertNotEqual(first["digest"], second["digest"])
        git_dependency = next(
            value for value in first["packages"] if value["name"] == "dep"
        )
        self.assertEqual(git_dependency["kind"], "git")
        self.assertNotIn("content_digest", git_dependency)

    def test_discovery_normalizes_target_names_and_fingerprint_layout(self) -> None:
        deps = self.target / "debug" / "deps"
        fingerprint = (
            self.target / "debug" / ".fingerprint" / "my-pkg-0123456789abcdef"
        )
        build_output = (
            self.target / "debug" / "build" / "my_pkg-0123456789abcdef" / "out"
        )
        deps.mkdir(parents=True, exist_ok=True)
        fingerprint.mkdir(parents=True, exist_ok=True)
        build_output.mkdir(parents=True, exist_ok=True)
        artifact = deps / "libcustom_target-0123456789abcdef.rlib"
        output = fingerprint / "output"
        generated_source = build_output / "generated.rs"
        artifact.write_bytes(b"artifact")
        output.write_bytes(b"output")
        generated_source.write_bytes(b"pub const GENERATED: u8 = 1;\n")
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={"my-pkg": frozenset({"custom_target", "my_pkg"})},
        ):
            paths = artifacts.discover_artifacts(
                self.target, "my-pkg", "debug", manifest=self.root / "Cargo.toml"
            )
        self.assertEqual(
            set(paths), {artifact, output, generated_source}
        )

    def test_discovery_rejects_ambiguous_cargo_artifact_owner(self) -> None:
        deps = self.target / "debug" / "deps"
        deps.mkdir(parents=True, exist_ok=True)
        (deps / "libshared-0123456789abcdef.rlib").write_bytes(b"artifact")
        with (
            patch.object(
                artifacts,
                "_workspace_artifact_owners",
                return_value={
                    "demo": frozenset({"shared"}),
                    "other": frozenset({"shared"}),
                },
            ),
            self.assertRaisesRegex(BuildIdentityError, "ambiguous Cargo owners"),
        ):
            artifacts.discover_artifacts(
                self.target,
                "demo",
                "debug",
                manifest=self.root / "Cargo.toml",
            )

    def test_discovery_uses_target_triple_and_exact_package_name(self) -> None:
        deps = self.target / "x86_64-unknown-linux-gnu" / "debug" / "deps"
        deps.mkdir(parents=True)
        wanted = deps / "libdemo-0123456789abcdef.rlib"
        similar = deps / "libdemo-tools-0123456789abcdef.rlib"
        executable = deps / "demo-0123456789abcdef.exe"
        for path in (wanted, similar, executable):
            path.write_bytes(path.name.encode())
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={
                "demo": frozenset({"demo"}),
                "demo-tools": frozenset({"demo_tools"}),
            },
        ):
            paths = artifacts.discover_artifacts(
                self.target,
                "demo",
                "debug",
                "x86_64-unknown-linux-gnu",
                self.root / "Cargo.toml",
            )
        self.assertEqual(set(paths), {wanted, executable})

    def test_artifact_names_follow_rustc_prefix_and_hash_rules(self) -> None:
        owners = {
            "demo": frozenset({"demo"}),
            "libdemo": frozenset({"libdemo"}),
            "demo-tools": frozenset({"demo_tools"}),
        }
        self.assertEqual(artifacts._artifact_owner("libdemo.dll", owners, "libdemo"), "libdemo")
        self.assertIsNone(artifacts._artifact_owner("libdemo.dll", owners, "demo"))
        self.assertEqual(
            artifacts._artifact_owner("demo-0123456789abcdef.dll", owners, "demo"),
            "demo",
        )
        self.assertEqual(
            artifacts._artifact_owner("libdemo-0123456789abcdef.rlib", owners, "demo"),
            "demo",
        )
        self.assertEqual(
            artifacts._artifact_owner("liblibdemo-0123456789abcdef.rlib", owners, "libdemo"),
            "libdemo",
        )
        self.assertEqual(
            artifacts._artifact_owner(
                "libdemo_tools-0123456789abcdef.rlib", owners, "demo-tools"
            ),
            "demo-tools",
        )
        self.assertIsNone(
            artifacts._artifact_owner("libdemo_tools-0123456789abcdef.rlib", owners, "demo")
        )
        self.assertIsNone(
            artifacts._artifact_owner("libdemo_tools-0123456789abcdef-extra.rlib", owners, "demo-tools")
        )

    def test_discovery_includes_webassembly_library_artifacts(self) -> None:
        wasm = self.target / "wasm32-unknown-unknown" / "debug" / "demo.wasm"
        wasm.parent.mkdir(parents=True)
        wasm.write_bytes(b"\x00asm\x01\x00\x00\x00")
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={"demo": frozenset({"demo"})},
        ):
            paths = artifacts.discover_artifacts(
                self.target,
                "demo",
                "debug",
                "wasm32-unknown-unknown",
                self.root / "Cargo.toml",
            )

        self.assertIn(wasm, paths)
        self.assertEqual(artifacts._artifact_owner("demo.wasm", {"demo": frozenset({"demo"})}, "demo"), "demo")

    def test_webassembly_artifact_bytes_change_the_recorded_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        wasm = self.target / "wasm32-unknown-unknown" / "debug" / "demo.wasm"
        wasm.parent.mkdir(parents=True)
        wasm.write_bytes(b"\x00asm\x01\x00\x00\x00first")
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={"demo": frozenset({"demo"})},
        ):
            discovered = artifacts.discover_artifacts(
                self.target,
                "demo",
                "debug",
                "wasm32-unknown-unknown",
                self.root / "Cargo.toml",
            )
            with TargetDirectory(self.target, create=True) as target:
                before = artifacts.artifact_identity(
                    self.root,
                    target,
                    "demo",
                    "debug",
                    discovered,
                    "wasm32-unknown-unknown",
                )
                wasm.write_bytes(b"\x00asm\x01\x00\x00\x00second")
                after = artifacts.artifact_identity(
                    self.root,
                    target,
                    "demo",
                    "debug",
                    discovered,
                    "wasm32-unknown-unknown",
                )

        relative = wasm.relative_to(self.target).as_posix()
        self.assertEqual(set(before["files"]), {relative})
        self.assertNotEqual(before["files"][relative], after["files"][relative])
        self.assertNotEqual(before["digest"], after["digest"])

    def test_example_executable_bytes_change_the_recorded_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        example = self.target / "debug" / "examples" / "demo.exe"
        example.parent.mkdir(parents=True)
        example.write_bytes(b"first executable")
        marker = (
            self.target
            / "debug"
            / ".fingerprint"
            / "demo-0123456789abcdef"
            / "invoked.timestamp"
        )
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b"fingerprint")
        with (
            patch.object(
                artifacts,
                "_workspace_artifact_owners",
                return_value={"demo": frozenset({"demo"})},
            ),
            TargetDirectory(self.target, create=True) as target,
        ):
            before = artifacts.artifact_identity(
                self.root,
                target,
                "demo",
                "debug",
                (),
                manifest=self.root / "Cargo.toml",
            )
            example.write_bytes(b"second executable")
            after = artifacts.artifact_identity(
                self.root,
                target,
                "demo",
                "debug",
                (),
                manifest=self.root / "Cargo.toml",
            )

        self.assertIn("debug/examples/demo.exe", before["files"])
        self.assertNotEqual(before["digest"], after["digest"])

    def test_outside_artifact_is_rejected_before_cleaning(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rlib"
        outside.write_text("outside", encoding="utf-8")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            with self.assertRaises(BuildIdentityError):
                build_workflow.run_build(
                    self.root,
                    self.root / "Cargo.toml",
                    "demo",
                    self.target,
                    [sys.executable, str(self.build_script)],
                    artifact_paths=[outside],
                    clean_command=[sys.executable, str(self.clean_script)],
                )
        self.assertFalse(self.clean_log.exists())

    def test_registry_package_content_changes_change_the_dependency_snapshot(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        registry_root = self.base / "registry"
        (registry_root / "src").mkdir(parents=True)
        (registry_root / "Cargo.toml").write_text(
            "[package]\nname = \"dep\"\nversion = \"0.1.0\"\n", encoding="utf-8"
        )
        source = registry_root / "src" / "lib.rs"
        source.write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "registry dep",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": "registry+https://example.invalid/dep",
                    "manifest_path": str((registry_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "registry dep", "dep_kinds": []}]},
                    {"id": "registry dep", "deps": []},
                ]
            },
        }
        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
            source.write_text("pub fn value() -> u8 { 2 }\n", encoding="utf-8")
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
        self.assertNotEqual(first["digest"], second["digest"])
        first_registry = next(
            package for package in first["packages"] if package["name"] == "dep"
        )
        second_registry = next(
            package for package in second["packages"] if package["name"] == "dep"
        )
        self.assertNotEqual(
            first_registry["content_digest"],
            second_registry["content_digest"],
        )

    def test_extensionless_executable_keeps_a_package_name_starting_with_lib(self) -> None:
        deps = self.target / "debug" / "deps"
        deps.mkdir(parents=True, exist_ok=True)
        executable = deps / "libdemo-0123456789abcdef"
        executable.write_bytes(b"executable")
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={"libdemo": frozenset({"libdemo"})},
        ):
            paths = artifacts.discover_artifacts(
                self.target, "libdemo", "debug", manifest=self.root / "Cargo.toml"
            )
        self.assertEqual(set(paths), {executable})
