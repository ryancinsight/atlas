"""Real Git/Cargo/rustdoc integration for the locked SemVer source contract."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "atlas_semver_locked.py"
SPEC = importlib.util.spec_from_file_location("atlas_semver_locked", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VersionContract(unittest.TestCase):
    def test_declared_changes_cover_exact_semver_classes(self):
        cases = [
            ("1.2.3", "1.2.3", "patch"), ("1.2.3", "1.2.4", "patch"),
            ("1.2.3", "1.3.0", "minor"), ("1.2.3", "2.0.0", "major"),
            ("0.16.0", "0.17.0", "major"), ("0.16.0", "0.16.1", "patch"),
        ]
        for old, new, expected in cases:
            with self.subTest(old=old, new=new):
                self.assertEqual(MODULE.release_type(old, new), expected)
        with self.assertRaisesRegex(ValueError, "version decreases"):
            MODULE.release_type("1.2.3", "1.2.2")
        with self.assertRaisesRegex(ValueError, "unsupported version"):
            MODULE.release_type("broken", "1.2.3")


@pytest.mark.slow
class CargoGitContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="semver-contract-test-")
        cls.root = Path(cls.directory.name)
        cls.env = dict(os.environ, RUSTUP_TOOLCHAIN="1.97.0")
        cls.provider = cls.root / "provider"
        cls.consumer = cls.root / "consumer"
        for path in (cls.provider, cls.consumer):
            (path / "src").mkdir(parents=True)
            (path / ".gitignore").write_text("/target/\n")
            cls.command(["git", "init", "-b", "main"], path)
            cls.command(["git", "config", "user.email", "contract@example.invalid"], path)
            cls.command(["git", "config", "user.name", "Contract test"], path)
        cls.provider.joinpath("Cargo.toml").write_text(
            '[package]\nname="provider"\nversion="0.1.0"\nedition="2021"\n')
        cls.provider.joinpath("src/lib.rs").write_text(
            '/// An integer quantity shared across the public seam.\n'
            '#[derive(Clone, Copy)]\npub struct Value(pub i32);\n')
        cls.commit(cls.provider, "provider 0.1")
        cls.consumer.joinpath("Cargo.toml").write_text(
            '[package]\nname="contract"\nversion="1.0.0"\nedition="2021"\n'
            '[dependencies]\nprovider={version="0.1",git="' + cls.provider.as_uri() + '"}\n')
        cls.consumer.joinpath("src/lib.rs").write_text(
            '/// The provider quantity remains part of the public API.\n'
            'pub use provider::Value;\n'
            '/// Double a quantity, rejecting signed overflow.\n'
            'pub fn doubled(value: Value) -> Value { Value(value.0.checked_mul(2).expect("overflow")) }\n')
        cls.command(["cargo", "generate-lockfile"], cls.consumer)
        cls.base = cls.commit(cls.consumer, "locked contract")
        cls.head = cls.commit(cls.consumer, "unchanged API", empty=True)
        # The real Git provider moves to an incompatible version. No stub tool,
        # patched Cargo, or fake rustdoc output participates in the regression.
        cls.provider.joinpath("Cargo.toml").write_text(
            '[package]\nname="provider"\nversion="0.2.0"\nedition="2021"\n')
        cls.commit(cls.provider, "provider advances past consumer requirement")

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @classmethod
    def command(cls, argv, cwd, check=True):
        return subprocess.run(argv, cwd=cwd, env=cls.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              check=check, timeout=180)

    @classmethod
    def commit(cls, repo, message, empty=False):
        cls.command(["git", "add", "."], repo)
        args = ["git", "commit", "-m", message]
        if empty:
            args.append("--allow-empty")
        cls.command(args, repo)
        return cls.command(["git", "rev-parse", "HEAD"], repo).stdout.strip()

    def compare(self, head, filename):
        report = self.root / filename
        result = self.command(
            [sys.executable, str(SCRIPT), "--repo", str(self.consumer),
             "--base", self.base, "--head", head, "--package", "contract",
             "--toolchain", "1.97.0", "--report", str(report)],
            self.consumer, check=False,
        )
        return result, json.loads(report.read_text())

    def test_locked_graph_survives_provider_default_branch_advance(self):
        fresh = self.command(
            ["cargo", "semver-checks", "--baseline-rev", self.base,
             "--package", "contract"], self.consumer, check=False,
        )
        self.assertNotEqual(fresh.returncode, 0, fresh.stdout)
        self.assertIn('failed to select a version', fresh.stdout)
        before = self.consumer.joinpath("Cargo.lock").read_bytes()
        result, report = self.compare(self.head, "unchanged.json")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(report["completed"])
        self.assertEqual(report["base"], self.base)
        self.assertEqual(report["head"], self.head)
        entry = report["packages"][0]
        self.assertEqual(entry["name"], "contract")
        self.assertEqual(entry["release_type"], "patch")
        self.assertEqual(entry["base_lock_sha256"], entry["head_lock_sha256"])
        self.assertEqual(before, self.consumer.joinpath("Cargo.lock").read_bytes())

    def test_real_unbumped_api_removal_stays_red(self):
        self.consumer.joinpath("src/lib.rs").write_text(
            '/// The provider quantity remains part of the public API.\n'
            'pub use provider::Value;\n')
        head = self.commit(self.consumer, "remove public operation without bump")
        result, report = self.compare(head, "breaking.json")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("doubled", result.stdout)
        self.assertIn("major", result.stdout.lower())
        self.assertFalse(report["completed"])
        self.assertEqual(report["packages"], [])


if __name__ == "__main__":
    unittest.main()
