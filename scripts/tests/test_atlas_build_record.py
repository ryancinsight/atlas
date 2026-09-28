#!/usr/bin/env python3
"""Tests for source identity record validation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
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
    check_workflow,
    git,
    identity,
    init_repo,
    records,
)


class RecordTestCase(BuildIdentityFixture):
    def test_dependency_record_variants_keep_source_identity_separate(self) -> None:
        common = {
            "id": "dep 0.1.0",
            "name": "dep",
            "version": "0.1.0",
            "features": [],
        }
        git_identity = {
            "root": str(self.base.resolve()),
            "revision": "a" * 40,
            "tree_digest": "b" * 64,
            "dirty": False,
        }

        def snapshot(package: dict[str, object]) -> dict[str, object]:
            value: dict[str, object] = {
                "root": "demo 0.1.0",
                "packages": [package],
                "edges": [],
                "clean_packages": ["dep"],
            }
            value["digest"] = hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            return value

        git_package = {
            **common,
            "kind": "git",
            "source": "git+https://example.invalid/dep#revision",
            "identity": git_identity,
        }
        registry_package = {
            **common,
            "kind": "registry",
            "source": "registry+https://example.invalid/index",
            "content_digest": "c" * 64,
        }
        self.assertTrue(records._dependency_record(snapshot(git_package)))
        self.assertTrue(records._dependency_record(snapshot(registry_package)))
        self.assertFalse(
            records._dependency_record(
                snapshot({
                    **common,
                    "kind": "git",
                    "source": "git+https://example.invalid/dep#revision",
                    "content_digest": "c" * 64,
                })
            )
        )
        self.assertFalse(
            records._dependency_record(
                snapshot({
                    **common,
                    "kind": "registry",
                    "source": "registry+https://example.invalid/index",
                    "identity": git_identity,
                })
            )
        )

    def test_malformed_records_fail_closed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
            record = records.record_path(spec)
            with TargetDirectory(self.target, create=True) as target:
                target.atomic_write(record, b'{"version": true}')
            with self.assertRaises(BuildIdentityError):
                check_workflow.check_record(
                    self.root,
                    "demo",
                    self.target,
                    artifact_paths=[self.artifact],
                    manifest=self.root / "Cargo.toml",
                    command=[sys.executable, str(self.build_script)],
                )

    def test_older_record_versions_are_stale(self) -> None:
        with TargetDirectory(self.target, create=True) as target:
            record = target.path / "old-record.json"
            for version in (1, 2, 3, 4, 5):
                target.atomic_write(
                    record, json.dumps({"version": version}).encode("utf-8")
                )
                self.assertIsNone(records.read_record(target, record))

    def test_git_dependency_record_round_trip_detects_checkout_root_changes(self) -> None:
        init_repo(self.root, "pub fn value() -> u8 { 1 }\n")
        dependency_root = self.base / "git-dependency"
        package_root = dependency_root / "crates" / "dep"
        (package_root / "src").mkdir(parents=True)
        (dependency_root / "shared.rs").write_text(
            "pub const VALUE: u8 = 1;\n", encoding="utf-8"
        )
        (dependency_root / "Cargo.toml").write_text(
            "[workspace]\nmembers = [\"crates/dep\"]\nresolver = \"3\"\n",
            encoding="utf-8",
        )
        (package_root / "Cargo.toml").write_text(
            "[package]\nname = \"dep\"\nversion = \"0.1.0\"\n"
            "edition = \"2024\"\n[lib]\npath = \"src/lib.rs\"\n",
            encoding="utf-8",
        )
        (package_root / "src/lib.rs").write_text(
            'include!("../../../shared.rs");\npub fn value() -> u8 { VALUE }\n',
            encoding="utf-8",
        )
        git(dependency_root, "init", "-q")
        git(dependency_root, "config", "user.name", "Atlas test")
        git(dependency_root, "config", "user.email", "atlas-test@example.invalid")
        git(dependency_root, "add", ".")
        git(dependency_root, "commit", "-q", "-m", "dependency")
        revision = git(dependency_root, "rev-parse", "HEAD")

        root_manifest = self.root / "Cargo.toml"
        root_manifest.write_text(
            "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n"
            "edition = \"2024\"\n[lib]\npath = \"src/lib.rs\"\n"
            "[dependencies]\n"
            f'dep = {{ git = "{dependency_root.as_uri()}", '
            f'rev = "{revision}", package = "dep" }}\n',
            encoding="utf-8",
        )
        (self.root / "src/lib.rs").write_text(
            "pub fn value() -> u8 { dep::value() }\n", encoding="utf-8"
        )
        cargo_home = self.base / "cargo-home"
        cargo_environment = os.environ.copy()
        cargo_environment.update(
            {
                "CARGO_HOME": str(cargo_home),
                "CARGO_NET_GIT_FETCH_WITH_CLI": "true",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "protocol.file.allow",
                "GIT_CONFIG_VALUE_0": "always",
            }
        )
        generation = subprocess.run(
            ["cargo", "generate-lockfile", "--manifest-path", str(root_manifest)],
            cwd=self.root,
            check=False,
            capture_output=True,
            timeout=60,
            env=cargo_environment,
        )
        self.assertEqual(
            generation.returncode, 0, generation.stderr.decode(errors="replace")
        )
        git(self.root, "add", ".")
        git(self.root, "commit", "-q", "-m", "declare local Git dependency")

        command = ["cargo", "build", "--manifest-path", str(root_manifest), "--locked"]
        with patch.dict(
            os.environ,
            {
                key: cargo_environment[key]
                for key in (
                    "CARGO_HOME",
                    "CARGO_NET_GIT_FETCH_WITH_CLI",
                    "GIT_CONFIG_COUNT",
                    "GIT_CONFIG_KEY_0",
                    "GIT_CONFIG_VALUE_0",
                )
            },
        ):
            result = build_workflow.run_build(
                self.root,
                root_manifest,
                "demo",
                self.target,
                command,
                command_key="git-dependency-record",
            )
            self.assertEqual(result.status, "rebuilt")
            matched_status, matched = check_workflow.check_record(
                self.root,
                "demo",
                self.target,
                manifest=root_manifest,
                command=command,
                command_key="git-dependency-record",
            )
            self.assertEqual((matched_status, matched["status"]), (0, "match"))

            metadata = artifacts._cargo_metadata(root_manifest, no_deps=False)
            dependency_package = next(
                package
                for package in metadata["packages"]
                if str(package.get("source", "")).startswith("git+file:")
            )
            checkout = Path(str(dependency_package["manifest_path"])).parent
            checkout_root = Path(git(checkout, "rev-parse", "--show-toplevel"))
            (checkout_root / "shared.rs").write_text(
                "pub const VALUE: u8 = 2;\n", encoding="utf-8"
            )
            stale_status, stale = check_workflow.check_record(
                self.root,
                "demo",
                self.target,
                manifest=root_manifest,
                command=command,
                command_key="git-dependency-record",
            )
        self.assertEqual((stale_status, stale["status"]), (2, "stale"))

