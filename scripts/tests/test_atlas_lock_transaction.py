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
    C = "https://github.com/ryancinsight/transaction-c"
    C_ALTERNATE = "https://github.com/ryancinsight/Transaction-C"
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="lock-source-transaction-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repos = self.root / "repos"
        self.a, self.b, self.c, self.consumer = (
            self.repos / name for name in ("transaction-a", "transaction-b",
                                           "transaction-c", "consumer"))
        for repository in (self.a, self.b, self.c, self.consumer):
            repository.mkdir(parents=True)
            self.git(repository, "init", "-q", "-b", "main")
            self.git(repository, "config", "user.name", "Atlas Test")
            self.git(repository, "config", "user.email", "atlas@example.invalid")
        (self.root / ".gitmodules").write_text("".join(
            f'[submodule "repos/{name}"]\n\tpath = repos/{name}\n\turl = {url}\n'
            for name, url in (("transaction-a", self.A), ("transaction-b", self.B),
                              ("transaction-c", self.C), ("consumer", self.A + "-consumer"))
        ), encoding="utf-8")
        old_b = self.provider(self.b, "transaction-b", "0.1.0")
        old_a = self.provider(self.a, "transaction-a", "0.1.0",
                              (("transaction-b", self.B, "=0.1.0"),))
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
        self.selected_c = self.provider(self.c, "transaction-c", "0.1.0")
        self.selected_b = self.provider(self.b, "transaction-b", "0.2.0")
        self.selected_a = self.provider(self.a, "transaction-a", "0.2.0", (
            ("transaction-b", self.B, "=0.2.0"),
            ("transaction-c", self.C, "=0.1.0"),
        ))
        self.identity_a = self.provider(self.a, "transaction-a", "0.2.1", (
            ("transaction-b", self.B, "=0.2.0"),
            ("transaction-c", self.C_ALTERNATE, "*"),
        ))
        self.later_c = self.provider(self.c, "transaction-c", "0.2.0")
        self.later_b = self.provider(self.b, "transaction-b", "0.3.0")
        self.later_a = self.provider(self.a, "transaction-a", "0.3.0",
                                     (("transaction-b", self.B, "=0.1.0"),))
        self.targets = dict((name, revision) for name, revision in (
            ("transaction-a", self.selected_a), ("transaction-b", self.selected_b),
            ("transaction-c", self.selected_c)))
        for repository in (self.a, self.b, self.c, self.consumer):
            self.git(repository, "remote", "add", "origin", repository.resolve().as_uri())
            self.git(repository, "fetch", "-q", "origin")
    def git(self, repository: Path, *arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments], check=True,
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    def provider(self, repository: Path, name: str, version: str,
                 dependencies: tuple[tuple[str, str, str], ...] = ()) -> str:
        (repository / "src").mkdir(exist_ok=True)
        (repository / "src/lib.rs").write_text(
            f"pub const VERSION: &str = \"{version}\";\n", encoding="utf-8")
        manifest = f'[package]\nname="{name}"\nversion="{version}"\nedition="2024"\n'
        if dependencies:
            manifest += "[dependencies]\n" + "".join(
                f'{package}={{git="{url}",version="{requirement}"}}\n'
                for package, url, requirement in dependencies)
        (repository / "Cargo.toml").write_text(manifest, encoding="utf-8")
        self.git(repository, "add", "Cargo.toml", "src/lib.rs")
        self.git(repository, "commit", "-qm", f"Record {version}")
        return self.git(repository, "rev-parse", "HEAD")
    def transport(self, a: Path, b: Path) -> dict[str, str]:
        return {**os.environ, "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": f"url.{a.resolve().as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": self.A,
            "GIT_CONFIG_KEY_1": f"url.{b.resolve().as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_1": self.B,
            "GIT_TERMINAL_PROMPT": "0"}
    def plan(self, lock: str, targets: dict[str, str]) -> object:
        return sweep.Plan(self.consumer, self.git(self.consumer, "rev-parse", "HEAD"),
                          sweep.stale_packages(lock, targets))
    def repository_state(self) -> tuple[dict[str, str], dict[str, bytes]]:
        repositories = (self.a, self.b, self.c, self.consumer)
        return ({path.name: self.git(path, "show-ref") for path in repositories},
                {path.name: (path / ".git/index").read_bytes() for path in repositories})
    def test_selected_heads_resolve_together_after_real_heads_diverge(self) -> None:
        lock_path = self.consumer / "Cargo.lock"
        before = lock_path.read_text(encoding="utf-8")
        refs, indexes = self.repository_state()
        manifest = (self.consumer / "Cargo.toml").read_bytes()
        inherited = dict(os.environ)
        self.assertIsNone(sweep.resolve_lock(self.plan(before, self.targets), self.targets,
                                             self.consumer, self.transport(self.a, self.b)))
        packages = {package.name: package for package in sweep.locked_packages(
            lock_path.read_text(encoding="utf-8"))}
        self.assertEqual(
            {(package.version, package.rev, package.url) for package in packages.values()},
            {("0.2.0", self.selected_a, self.A), ("0.2.0", self.selected_b, self.B),
             ("0.1.0", self.selected_c, self.C)},
        )
        self.assertEqual({self.git(repo, "rev-parse", "HEAD") for repo in (self.a, self.b, self.c)},
                         {self.later_a, self.later_b, self.later_c})
        self.assertEqual((self.consumer / "Cargo.toml").read_bytes(), manifest)
        self.assertEqual(self.repository_state(), (refs, indexes))
        self.assertEqual(dict(os.environ), inherited)
        self.assertEqual(list(self.repos.glob("lock-sources-*")), [])
    def test_unavailable_and_incompatible_targets_leave_inputs_unchanged(self) -> None:
        source_lock = (self.consumer / "Cargo.lock").read_text(encoding="utf-8")
        old_a = next(p.rev for p in sweep.locked_packages(source_lock)
                     if p.provider == "transaction-a")
        inherited = self.transport(self.a, self.b)
        inherited.update({"GIT_CONFIG_COUNT": "3",
                          "GIT_CONFIG_KEY_2": f"url.{self.c.resolve().as_uri()}.insteadOf",
                          "GIT_CONFIG_VALUE_2": self.C_ALTERNATE})
        cases = {
            "unavailable": ({**self.targets, "transaction-a": "f" * 40}, source_lock, None),
            "incompatible": ({"transaction-a": self.later_a,
                              "transaction-b": self.selected_b,
                              "transaction-c": self.selected_c}, source_lock, None),
            "query": (self.targets, source_lock.replace(
                self.A + "#", self.A + f"?rev={old_a}#"), None),
            "identity": ({"transaction-a": self.identity_a,
                          "transaction-b": self.selected_b,
                          "transaction-c": self.later_c}, source_lock, inherited),
        }
        refs, indexes = self.repository_state()
        for name, (targets, case_lock, environment) in cases.items():
            with self.subTest(name=name):
                tree = self.root / name
                shutil.copytree(self.consumer, tree, ignore=shutil.ignore_patterns(".git", "target"))
                (tree / "Cargo.lock").write_text(case_lock, encoding="utf-8")
                manifest = (tree / "Cargo.toml").read_bytes()
                lock = (tree / "Cargo.lock").read_bytes()
                outcome = sweep.resolve_lock(
                    self.plan(case_lock, targets), targets, tree, environment)
                self.assertIsInstance(outcome, sweep.Outcome)
                self.assertFalse(outcome.ok)
                if name == "identity":
                    self.assertIn("unsupported selected source URL", outcome.detail)
                self.assertEqual((tree / "Cargo.toml").read_bytes(), manifest)
                self.assertEqual((tree / "Cargo.lock").read_bytes(), lock)
                self.assertEqual(self.repository_state(), (refs, indexes))
                self.assertEqual(list(self.root.glob("lock-sources-*")), [])
    def test_cli_rejects_queried_targets_before_current_classification(self) -> None:
        lock = self.consumer / "Cargo.lock"
        lock.write_text(lock.read_text(encoding="utf-8").replace(
            self.A + "#", self.A + "?branch=main#").replace(
            self.B + "#", self.B + "?branch=main#"), encoding="utf-8")
        self.git(self.consumer, "add", "Cargo.lock")
        self.git(self.consumer, "commit", "-qm", "Record queried sources")
        command = [sys.executable, "-I", str(SCRIPT), "--members", "consumer",
                   "--target", f"transaction-a={self.selected_a}",
                   "--target", f"transaction-b={self.selected_b}"]
        result = subprocess.run(command,
            cwd=self.root, env={**os.environ, "ATLAS_STACK_ROOT": str(self.root),
                               "CARGO_TARGET_DIR": str(self.root / "target")},
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("query constraint", result.stdout)
        self.assertNotIn("every targeted source at its target", result.stdout)
if __name__ == "__main__":
    unittest.main()
