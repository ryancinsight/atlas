#!/usr/bin/env python3
"""Real Git and Cargo coverage for atomic first-party source selection."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "atlas-lock-sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_lock_transaction", SCRIPT)
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)


class SourceTransactionTests(unittest.TestCase):
    A = "https://github.com/ryancinsight/Transaction-A.git"
    B = "https://github.com/ryancinsight/transaction-b"

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="lock-source-transaction-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repos = self.root / "repos"
        self.a = self.repos / "transaction-a"
        self.b = self.repos / "transaction-b"
        self.consumer = self.repos / "consumer"
        for repository in (self.a, self.b, self.consumer):
            repository.mkdir(parents=True)
            self.git(repository, "init", "-q", "-b", "main")
            self.git(repository, "config", "user.name", "Atlas Test")
            self.git(repository, "config", "user.email", "atlas@example.invalid")

        old_b = self.provider(self.b, "transaction-b", "0.1.0")
        old_a = self.provider(self.a, "transaction-a", "0.1.0", "=0.1.0")
        (self.consumer / "src").mkdir()
        (self.consumer / "src/lib.rs").write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
        (self.consumer / "Cargo.toml").write_text(
            '[package]\nname="transaction-consumer"\nversion="0.1.0"\nedition="2024"\n'
            f'[dependencies]\ntransaction-a={{git="{self.A}"}}\n'
            f'transaction-b={{git="{self.B}"}}\n', encoding="utf-8",
        )
        generated = sweep.lockfile.run_outside_the_overlay(
            ["--config", "net.git-fetch-with-cli=true", "generate-lockfile"],
            self.consumer / "Cargo.toml", env=self.transport(self.a, self.b), deadline=60,
        )
        self.assertEqual(generated.returncode, 0, generated.stderr)
        self.git(self.consumer, "add", "Cargo.toml", "Cargo.lock", "src/lib.rs")
        self.git(self.consumer, "commit", "-qm", "Record old graph")
        self.assertEqual(
            {package.rev for package in sweep.locked_packages(
                (self.consumer / "Cargo.lock").read_text(encoding="utf-8"))},
            {old_a, old_b},
        )

        self.selected_b = self.provider(self.b, "transaction-b", "0.2.0")
        self.selected_a = self.provider(self.a, "transaction-a", "0.2.0", "=0.2.0")
        self.later_b = self.provider(self.b, "transaction-b", "0.3.0")
        self.later_a = self.provider(self.a, "transaction-a", "0.3.0", "=0.1.0")
        self.targets = {"transaction-a": self.selected_a, "transaction-b": self.selected_b}

    def git(self, repository: Path, *arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments], check=True,
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()

    def provider(self, repository: Path, name: str, version: str,
                 requirement: str | None = None) -> str:
        (repository / "src").mkdir(exist_ok=True)
        (repository / "src/lib.rs").write_text(
            f"pub const VERSION: &str = \"{version}\";\n", encoding="utf-8"
        )
        manifest = f'[package]\nname="{name}"\nversion="{version}"\nedition="2024"\n'
        if requirement is not None:
            manifest += (f'[dependencies]\ntransaction-b={{git="{self.B}",'
                         f'version="{requirement}"}}\n')
        (repository / "Cargo.toml").write_text(manifest, encoding="utf-8")
        self.git(repository, "add", "Cargo.toml", "src/lib.rs")
        self.git(repository, "commit", "-qm", f"Record {version}")
        return self.git(repository, "rev-parse", "HEAD")

    def transport(self, a: Path, b: Path) -> dict[str, str]:
        return {
            **os.environ, "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": f"url.{a.resolve().as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": self.A,
            "GIT_CONFIG_KEY_1": f"url.{b.resolve().as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_1": self.B,
            "GIT_TERMINAL_PROMPT": "0",
        }

    def plan(self, lock: str, targets: dict[str, str]) -> object:
        return sweep.Plan(
            self.consumer, self.git(self.consumer, "rev-parse", "HEAD"),
            sweep.stale_packages(lock, targets),
        )

    def repository_state(self) -> tuple[dict[str, str], dict[str, bytes]]:
        refs = {path.name: self.git(path, "show-ref")
                for path in (self.a, self.b, self.consumer)}
        indexes = {path.name: (path / ".git/index").read_bytes()
                   for path in (self.a, self.b, self.consumer)}
        return refs, indexes

    def test_selected_heads_resolve_together_after_real_heads_diverge(self) -> None:
        lock_path = self.consumer / "Cargo.lock"
        before = lock_path.read_text(encoding="utf-8")
        refs, indexes = self.repository_state()
        manifest = (self.consumer / "Cargo.toml").read_bytes()
        inherited = dict(os.environ)
        self.assertIsNone(sweep.resolve_lock(self.plan(before, self.targets), self.targets,
                                             self.consumer))
        packages = {package.name: package for package in sweep.locked_packages(
            lock_path.read_text(encoding="utf-8"))}
        self.assertEqual(
            {(package.version, package.rev, package.url) for package in packages.values()},
            {("0.2.0", self.selected_a, self.A), ("0.2.0", self.selected_b, self.B)},
        )
        self.assertEqual(self.git(self.a, "rev-parse", "HEAD"), self.later_a)
        self.assertEqual(self.git(self.b, "rev-parse", "HEAD"), self.later_b)
        self.assertEqual((self.consumer / "Cargo.toml").read_bytes(), manifest)
        self.assertEqual(self.repository_state(), (refs, indexes))
        self.assertEqual(dict(os.environ), inherited)
        self.assertEqual(list(self.repos.glob("lock-sources-*")), [])

    def test_unavailable_and_incompatible_targets_leave_inputs_unchanged(self) -> None:
        source_lock = (self.consumer / "Cargo.lock").read_text(encoding="utf-8")
        old_a = next(package.rev for package in sweep.locked_packages(source_lock)
                     if package.provider == "transaction-a")
        cases = {
            "unavailable": ({**self.targets, "transaction-a": "f" * 40}, source_lock),
            "incompatible": ({"transaction-a": self.later_a,
                              "transaction-b": self.selected_b}, source_lock),
            "query": (self.targets, source_lock.replace(
                self.A + "#", self.A + f"?rev={old_a}#")),
        }
        refs, indexes = self.repository_state()
        for name, (targets, case_lock) in cases.items():
            with self.subTest(name=name):
                tree = self.root / name
                shutil.copytree(self.consumer, tree, ignore=shutil.ignore_patterns(".git", "target"))
                (tree / "Cargo.lock").write_text(case_lock, encoding="utf-8")
                manifest = (tree / "Cargo.toml").read_bytes()
                lock = (tree / "Cargo.lock").read_bytes()
                outcome = sweep.resolve_lock(self.plan(case_lock, targets), targets, tree)
                self.assertIsNotNone(outcome)
                self.assertFalse(outcome.ok)
                self.assertEqual((tree / "Cargo.toml").read_bytes(), manifest)
                self.assertEqual((tree / "Cargo.lock").read_bytes(), lock)
                self.assertEqual(self.repository_state(), (refs, indexes))
                self.assertEqual(list(self.root.glob("lock-sources-*")), [])


if __name__ == "__main__":
    unittest.main()
