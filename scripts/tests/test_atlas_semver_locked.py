"""Real CLI coverage for the locked SemVer evidence contract."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas_semver_locked.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_semver_locked", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
from process_tree_support import EXPIRY_HOLD_SECONDS, NEVER_ENDS


class NativeContract(unittest.TestCase):
    def command(self, argv, cwd):
        return subprocess.run(argv, cwd=cwd, check=True, capture_output=True,
                              text=True, timeout=120)

    def commit(self, repo, message):
        self.command(["git", "add", "Cargo.toml", "Cargo.lock", "src/lib.rs"], repo)
        self.command(["git", "commit", "-m", message], repo)
        return self.command(["git", "rev-parse", "HEAD"], repo).stdout.strip()

    def initialize(self, repo):
        for argv in (["git", "init", "-b", "main"],
                     ["git", "config", "user.email", "test@example.invalid"],
                     ["git", "config", "user.name", "Contract test"]):
            self.command(argv, repo)

    def package(self, repo):
        return repo.name.replace("-", "_")

    def run_contract(self, repo, base, head, report, change="patch"):
        target = next(line[6:] for line in self.command(["rustc", "+1.97.0", "-vV"], repo).stdout.splitlines()
                      if line.startswith("host: "))
        args = argparse.Namespace(
            repo=repo, base=base, head=head, manifest_path="Cargo.toml",
            packages=[self.package(repo)], toolchain="1.97.0", change_class=change,
            feature_policy="all", features=[], target=target,
            report=report,
        )
        target_dir = os.environ.get("CARGO_TARGET_DIR", str(SCRIPT.parents[1] / "target"))
        with patch.dict(os.environ, {"CARGO_TARGET_DIR": target_dir}):
            code = MODULE.compare(args)
        return code, json.loads(report.read_text(encoding="utf-8"))

    def test_native_pass_deny_and_manifest_permission_are_distinct(self):
        for baseline, current, expected in (
            ("1.2.3", "1.2.4", "patch"), ("1.2.3", "1.3.0", "minor"),
            ("1.2.3", "2.0.0", "major"), ("0.1.0", "0.1.1", "patch"),
            ("0.1.0", "0.2.0", "major"), ("0.0.1", "0.0.2", "major")):
            self.assertEqual(MODULE.permission(baseline, current), expected)
        with tempfile.TemporaryDirectory(prefix="semver-native-") as directory:
            repo = Path(directory)
            (repo / "src").mkdir()
            (repo / "Cargo.toml").write_text(
                f'[package]\nname="{self.package(repo)}"\nversion="0.1.0"\nedition="2024"\n',
                encoding="utf-8")
            (repo / "src/lib.rs").write_text("pub fn retained() {}\npub fn removed() {}\n", encoding="utf-8")
            self.initialize(repo)
            self.command(["cargo", "generate-lockfile"], repo)
            base = self.commit(repo, "base")
            self.command(["git", "commit", "--allow-empty", "-m", "unchanged"], repo)
            head = self.command(["git", "rev-parse", "HEAD"], repo).stdout.strip()
            code, report = self.run_contract(repo, base, head, repo / "pass.json")
            self.assertEqual((code, report["packages"][0]["native"]["status"]), (0, "pass"))
            code, report = self.run_contract(repo, base, head, repo / "major.json", "major")
            self.assertEqual(report["packages"][0]["native"]["status"], "pass")
            self.assertEqual((code, report["packages"][0]["manifest_error"]),
                             (101, "declared change class exceeds manifest boundary"))
            (repo / "src/lib.rs").write_text("pub fn retained() {}\n", encoding="utf-8")
            head = self.commit(repo, "remove API")
            code, report = self.run_contract(repo, base, head, repo / "deny.json")
            native = report["packages"][0]["native"]
            self.assertEqual((code, native["exit_code"], native["status"], report["packages"][0]["name"]),
                             (100, 100, "deny_findings", self.package(repo)))
            self.assertIn("--baseline-rev", native["command"])
            self.assertEqual(report["configuration"]["feature_policy"], "all")
            (repo / "src/lib.rs").write_text("pub fn broken( {\n", encoding="utf-8")
            head = self.commit(repo, "break compilation")
            code, report = self.run_contract(repo, base, head, repo / "error.json")
            entry = report["packages"][0]
            self.assertEqual(
                (code, entry["native"]["status"], entry["known_resolution_limitation"],
                 "supplemental" in entry),
                (101, "execution_error", False, False),
            )

    def test_provider_advance_records_locked_evidence_without_an_api_verdict(self):
        with (tempfile.TemporaryDirectory(prefix="semver-provider-") as provider_directory,
              tempfile.TemporaryDirectory(prefix="semver-consumer-") as consumer_directory):
            provider, consumer = Path(provider_directory), Path(consumer_directory)
            provider_name = self.package(provider)
            for repo in (provider, consumer):
                (repo / "src").mkdir()
                self.initialize(repo)
            (provider / "Cargo.toml").write_text(
                f'[package]\nname="{provider_name}"\nversion="0.1.0"\nedition="2024"\n',
                encoding="utf-8")
            (provider / "src/lib.rs").write_text(
                "pub fn value() -> usize { 1 }\n", encoding="utf-8")
            self.command(["cargo", "generate-lockfile"], provider)
            old_provider = self.commit(provider, "provider 0.1")
            (consumer / "Cargo.toml").write_text(
                f'[package]\nname="{self.package(consumer)}"\nversion="0.1.0"\nedition="2024"\n'
                f'[dependencies]\n{provider_name} = {{ git = "{provider.as_uri()}", version = "^0.1" }}\n',
                encoding="utf-8")
            (consumer / "src/lib.rs").write_text(
                f"pub fn value() -> usize {{ {provider_name}::value() }}\n", encoding="utf-8")
            self.command(["cargo", "generate-lockfile"], consumer)
            base = self.commit(consumer, "consumer baseline")
            working_lock_hash = MODULE.digest(consumer / "Cargo.lock")
            self.command(["git", "commit", "--allow-empty", "-m", "consumer candidate"], consumer)
            head = self.command(["git", "rev-parse", "HEAD"], consumer).stdout.strip()
            (provider / "Cargo.toml").write_text(
                f'[package]\nname="{provider_name}"\nversion="0.2.0"\nedition="2024"\n',
                encoding="utf-8")
            self.command(["cargo", "generate-lockfile"], provider)
            self.commit(provider, "provider 0.2")
            code, report = self.run_contract(
                consumer, base, head, consumer / "provider-advance.json",
            )
            entry = report["packages"][0]
            native, evidence = entry["native"], entry["supplemental"]
            self.assertEqual(
                (code, native["exit_code"], native["status"],
                 entry["known_resolution_limitation"], evidence["api_comparison"]),
                (101, 101, "execution_error", True, "unsupported"),
            )
            self.assertEqual(
                [item["status"] for item in evidence["consumer_contract"]["compilation"]],
                ["pass", "pass"],
            )
            selected = [
                next(item for item in packages if item["name"] == provider_name)
                for packages in evidence["consumer_contract"]
                ["compiled_dependencies"]
            ]
            self.assertEqual(
                [(item["version"], item["source"].rsplit("#", 1)[-1]) for item in selected],
                [("0.1.0", old_provider), ("0.1.0", old_provider)],
            )
            self.assertEqual(
                [provider.as_uri().lower() in item["source"].lower() for item in selected],
                [True, True],
            )
            self.assertEqual(evidence["baseline_lock_sha256"], evidence["current_lock_sha256"])
            self.assertEqual(MODULE.digest(consumer / "Cargo.lock"), working_lock_hash)
            self.assertEqual(
                MODULE.digest_bytes(native["diagnostics"].encode()), native["diagnostics_sha256"],
            )
            for fragment in MODULE.KNOWN_RESOLUTION_DIAGNOSTICS:
                self.assertIn(fragment, native["diagnostics"])

    def test_dependency_evidence_matches_features_and_target(self):
        with (tempfile.TemporaryDirectory(prefix="semver-features-") as consumer_directory,
              tempfile.TemporaryDirectory(prefix="semver-optional-") as optional_directory,
              tempfile.TemporaryDirectory(prefix="semver-platform-") as platform_directory,
              tempfile.TemporaryDirectory(prefix="semver-excluded-") as excluded_directory):
            consumer = Path(consumer_directory)
            optional = Path(optional_directory)
            platform = Path(platform_directory)
            excluded = Path(excluded_directory)
            for repo in (consumer, optional, platform, excluded):
                (repo / "src").mkdir()
                self.initialize(repo)
            for provider in (optional, platform, excluded):
                (provider / "Cargo.toml").write_text(
                    f'[package]\nname="{self.package(provider)}"\n'
                    'version="0.1.0"\nedition="2024"\n', encoding="utf-8")
                (provider / "src/lib.rs").write_text(
                    "pub fn value() -> usize { 1 }\n", encoding="utf-8")
                self.command(["cargo", "generate-lockfile"], provider)
                self.commit(provider, "provider")
            optional_name = self.package(optional)
            platform_name = self.package(platform)
            excluded_name = self.package(excluded)
            consumer_name = self.package(consumer)
            (consumer / "Cargo.toml").write_text(
                f'[package]\nname="{consumer_name}"\nversion="0.1.0"\nedition="2024"\n'
                f'[features]\ndefault=["extra"]\nextra=["dep:{optional_name}"]\n'
                f'[dependencies]\n{optional_name}={{git="{optional.as_uri()}",optional=true}}\n'
                f'[target.\'cfg(target_os = "windows")\'.dependencies]\n'
                f'{platform_name}={{git="{platform.as_uri()}"}}\n'
                f'[target.\'cfg(target_os = "linux")\'.dependencies]\n'
                f'{excluded_name}={{git="{excluded.as_uri()}"}}\n', encoding="utf-8")
            (consumer / "src/lib.rs").write_text(
                f'#[cfg(feature="extra")]\npub fn extra() -> usize {{ {optional_name}::value() }}\n'
                f'#[cfg(target_os="windows")]\npub fn platform() -> usize {{ {platform_name}::value() }}\n',
                encoding="utf-8")
            self.command(["cargo", "generate-lockfile"], consumer)
            self.commit(consumer, "consumer")
            host = next(line[6:] for line in self.command(
                ["rustc", "+1.97.0", "-vV"], consumer).stdout.splitlines()
                        if line.startswith("host: "))
            env = dict(os.environ, RUSTUP_TOOLCHAIN="1.97.0")
            env["CARGO_TARGET_DIR"] = os.environ.get(
                "CARGO_TARGET_DIR", str(SCRIPT.parents[1] / "target"))
            cases = (
                ("default", [], {optional_name, platform_name}),
                ("explicit", [], {platform_name}),
                ("explicit", ["extra"], {optional_name, platform_name}),
                ("all", [], {optional_name, platform_name}),
            )
            for policy, features, expected in cases:
                config = {"feature_policy": policy, "features": features, "target": host}
                check, resolved = MODULE.compiled_packages(
                    consumer / "Cargo.toml", consumer_name, env, config)
                self.assertEqual(check["status"], "pass")
                self.assertNotIn("evidence_error", check)
                self.assertEqual({item["name"] for item in resolved}, expected)
                self.assertNotIn(excluded_name, {item["name"] for item in resolved})

    def test_compiled_packages_ignore_workspace_feature_unification(self):
        with tempfile.TemporaryDirectory(prefix="semver-workspace-") as directory:
            root = Path(directory)
            names = ("a", "b", "common", "helper", "optional")
            dependencies = {
                "a": '[dependencies]\ncommon={path="../common"}\nhelper={path="../helper"}\n',
                "b": '[dependencies]\ncommon={path="../common",features=["extra"]}\n',
                "common": ('[features]\nextra=["dep:optional"]\n'
                           '[dependencies]\noptional={path="../optional",optional=true}\n'),
            }
            (root / "Cargo.toml").write_text(
                '[workspace]\nresolver="3"\nmembers=["a","b","common","helper","optional"]\n',
                encoding="utf-8")
            for name in names:
                crate = root / name
                (crate / "src").mkdir(parents=True)
                (crate / "Cargo.toml").write_text(
                    f'[package]\nname="{name}"\nversion="0.1.0"\nedition="2024"\n'
                    f'{dependencies.get(name, "")}',
                    encoding="utf-8")
                (crate / "src/lib.rs").write_text(
                    "pub fn value() -> usize { 1 }\n", encoding="utf-8")
            (root / "a" / "src/lib.rs").write_text(
                "pub fn value() -> usize { common::value() + helper::value() }\n",
                encoding="utf-8")
            self.command(["cargo", "generate-lockfile"], root)
            host = next(line[6:] for line in self.command(
                ["rustc", "+1.97.0", "-vV"], root).stdout.splitlines()
                        if line.startswith("host: "))
            env = dict(os.environ, RUSTUP_TOOLCHAIN="1.97.0")
            env["CARGO_TARGET_DIR"] = os.environ.get(
                "CARGO_TARGET_DIR", str(SCRIPT.parents[1] / "target"))
            config = {"feature_policy": "explicit", "features": [], "target": host}
            check, compiled = MODULE.compiled_packages(
                root / "Cargo.toml", "a", env, config)
            self.assertEqual(check["status"], "pass")
            self.assertNotIn("evidence_error", check)
            emitted = set(check["compiler_artifact_package_ids"])
            reported = {item["id"] for item in compiled}
            self.assertEqual(reported, emitted - {check["selected_package_id"]})
            self.assertEqual({item["name"] for item in compiled}, {"common", "helper"})

    def test_timeout_uses_the_canonical_process_tree_deadline(self):
        command = [sys.executable, "-I", "-c", NEVER_ENDS]
        record = MODULE.attempt(
            command, Path.cwd(), dict(os.environ), timeout=EXPIRY_HOLD_SECONDS,
        )
        self.assertEqual(record["status"], "timeout")
        self.assertEqual(record["diagnostics"], "")
