"""The PR SemVer comparison builds its baseline from the base's own lock (hephaestus PR 537)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

import atlas_semver_pr as gate


class ComparisonTests(unittest.TestCase):
    NIGHTLY = "nightly-pin"

    def compare(self, code: int, names=("alpha", "beta")):
        crate = {"name": "alpha", "features": {"default": [], "nightly": []},
                 "targets": [{"kind": ["lib"], "name": "alpha"}]}
        calls = []

        def fake(argv, cwd, env):
            calls.append((argv, env))
            if argv[1] == "doc" and code == 0:
                out = Path(argv[argv.index("--target-dir") + 1]) / "doc"
                out.mkdir(parents=True)
                (out / "alpha.json").write_text("{}", encoding="utf-8")
            return types.SimpleNamespace(returncode=code, stdout=b"", stderr=b"boom")

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(gate, "run", fake):
            root = Path(directory)
            packages = ({n: dict(crate, name=n, workspace_root=str(root)) for n in names[:1]},
                        {n: dict(crate, workspace_root=str(root)) for n in names})
            return [gate.compare_package(n, (root / "b.toml", root / "h.toml"), packages,
                                         root / "doc", {}, self.NIGHTLY) for n in names], calls

    def test_both_sides_build_locked_on_the_pinned_nightly_and_feed_the_checker(self) -> None:
        (outcome, absent), calls = self.compare(0)
        self.assertEqual((outcome.status, absent.status), ("clean", "skipped"))
        builds = [c for c in calls if c[0][1] == "doc"]
        self.assertEqual(len(builds), 2)
        for argv, env in builds:
            self.assertEqual(env["RUSTUP_TOOLCHAIN"], self.NIGHTLY)
            self.assertNotIn("RUSTC_BOOTSTRAP", env)
            self.assertIn("--output-format=json", env["RUSTDOCFLAGS"])
            self.assertEqual(argv[argv.index("--features") + 1], "default")
        # No Cargo.lock beside the base manifest: that side resolves freshly.
        self.assertEqual(["--locked" in argv for argv, _ in builds], [False, False])
        check = next(argv for argv, _ in calls if argv[1] == "semver-checks")
        self.assertTrue({"--baseline-rustdoc", "--current-rustdoc"} <= set(check))
        # Each of these makes the tool re-resolve the baseline without its lock.
        self.assertFalse({"--baseline-rev", "--baseline-root", "--baseline-version"} & set(check))

    def test_a_committed_lock_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "Cargo.lock").write_text("", encoding="utf-8")
            calls = []
            fake = lambda argv, cwd, env: calls.append(argv) or types.SimpleNamespace(  # noqa: E731
                returncode=1, stdout=b"", stderr=b"")
            crate = {"name": "alpha", "features": {}, "workspace_root": directory,
                     "targets": [{"kind": ["lib"], "name": "alpha"}]}
            with mock.patch.object(gate, "run", fake):
                outcome = gate.compare_package(
                    "alpha", (Path("b"), Path("h")), ({"alpha": crate},) * 2, Path("d"), {}, "n")
        self.assertIn("--locked", calls[0])
        self.assertEqual(outcome.status, "failed")
        self.assertIn("base rustdoc unavailable", outcome.detail)
        self.assertEqual([gate.classify(c) for c in (0, 100, 101, 2)],
                         ["clean", "update-required", "failed", "failed"])

    def test_a_timeout_fails_only_the_crate_that_hit_it(self) -> None:
        def fake(argv, cwd, env):
            package = argv[argv.index("--package") + 1]
            if (argv[1], package) in (("doc", "alpha"), ("semver-checks", "beta")):
                raise gate.process_tree.ProcessTreeTimeout(argv, 600, None, None, None)
            if argv[1] == "doc":
                out = Path(argv[argv.index("--target-dir") + 1]) / "doc"
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{package}.json").write_text("{}", encoding="utf-8")
            return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(gate, "run", fake):
            root = Path(directory)
            names = ("gamma", "alpha", "beta")
            packages = ({n: {"name": n, "features": {}, "workspace_root": directory,
                             "targets": [{"kind": ["lib"], "name": n}]} for n in names},) * 2
            outcomes = [gate.compare_package(n, (root / "b.toml", root / "h.toml"), packages,
                                             root / "doc", {}, self.NIGHTLY) for n in names]
        self.assertEqual([o.status for o in outcomes], ["clean", "failed", "failed"])
        self.assertIn("base rustdoc unavailable", outcomes[1].detail)
        self.assertIn("cargo-semver-checks did not finish", outcomes[2].detail)


class SummaryTests(unittest.TestCase):
    def test_a_failure_detail_stays_inside_its_table_cell(self) -> None:
        text = gate.render([gate.Outcome("a", "failed", "cargo failed:\nerror: x | y")], "0" * 40)
        self.assertIn("| `a` | FAILED to run | cargo failed: error: x \\| y |", text)

    def test_a_tool_failure_is_never_reported_as_a_version_bump(self) -> None:
        text = gate.render([gate.Outcome("a", "failed", "no verdict"),
                            gate.Outcome("b", "clean", "ok"), gate.Outcome("c", "skipped", "x")],
                           "0" * 40)
        self.assertIn("**Tool failure** for `a`", text)
        self.assertNotIn("version update is required", text)
        for row in ("| `a` | FAILED to run |", "| `b` | compared |", "| `c` | not compared |"):
            self.assertIn(row, text)
        self.assertIn("A version update is required for `d`",
                      gate.render([gate.Outcome("d", "update-required", "")], "0" * 40))

    def test_exit_status_separates_failure_from_verdict(self) -> None:
        argv = ["--repo", ".", "--base", "x", "--package", "a", "--rustdoc-toolchain", "n"]
        for kinds, code in ((("clean", "skipped"), 0), (("update-required",), 100),
                            (("update-required", "failed"), 101)):
            outcomes = [gate.Outcome("p", kind, "") for kind in kinds]
            with mock.patch.object(gate, "compare_all", return_value=outcomes):
                self.assertEqual(gate.main(argv), code)
        with mock.patch.object(gate, "compare_all", side_effect=RuntimeError("git archive")):
            self.assertEqual(gate.main(argv), 101)


PINNED = "nightly-2026-08-01"


def tool_ready() -> bool:
    if not all(shutil.which(tool) for tool in ("cargo", "git", "cargo-semver-checks")):
        return False
    version = subprocess.run(["cargo", "semver-checks", "--version"], capture_output=True, text=True)
    installed = subprocess.run(["rustup", "toolchain", "list"], capture_output=True, text=True)
    return version.stdout.strip() == "cargo-semver-checks 0.51.0" and PINNED in installed.stdout


@pytest.mark.slow
@unittest.skipUnless(tool_ready(), "needs git, cargo, cargo-semver-checks 0.51.0 and the pinned nightly")
class MovedGitDependencyTests(unittest.TestCase):
    """The base requires `^0.11.0` of a git dependency whose head is now 0.12.0."""

    def sh(self, cwd: Path, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(argv, cwd=cwd, env=self.env, capture_output=True, text=True)

    def crate(self, root: Path, name: str, version: str, dependency: str, source: str) -> None:
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "Cargo.toml").write_text(
            f'[package]\nname = "{name}"\nversion = "{version}"\nedition = "2021"\n'
            f"[dependencies]\n{dependency}", encoding="utf-8")
        (root / "src" / "lib.rs").write_text(source, encoding="utf-8")

    def commit(self, root: Path, message: str) -> None:
        for argv in (("git", "add", "-A"), ("git", "-c", "user.name=t", "-c",
                     "user.email=t@example.test", "commit", "-qm", message)):
            self.assertEqual(self.sh(root, *argv).returncode, 0)

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.env = {**os.environ, "CARGO_TARGET_DIR": str(root / "target")}
        provider, self.ws = root / "provider", root / "ws"
        for path in (provider, self.ws):
            path.mkdir()
            self.sh(path, "git", "init", "-q")
        dependency = lambda version: (  # noqa: E731
            f'movedep = {{ version = "{version}", git = "{provider.as_uri()}" }}\n')
        self.crate(provider, "movedep", "0.11.3", "", "")
        self.commit(provider, "0.11.3")
        self.crate(self.ws, "alpha", "0.1.0", dependency("0.11.0"), "pub fn a() {}\npub fn b() {}\n")
        self.assertEqual(self.sh(self.ws, "cargo", "generate-lockfile").returncode, 0)
        self.commit(self.ws, "base")
        self.base = self.sh(self.ws, "git", "rev-parse", "HEAD").stdout.strip()
        self.crate(provider, "movedep", "0.12.0", "", "")
        self.commit(provider, "0.12.0")
        self.crate(self.ws, "alpha", "0.1.0", dependency("0.12.0"), "pub fn a() {}\n")
        self.assertEqual(self.sh(self.ws, "cargo", "update").returncode, 0)
        self.commit(self.ws, "head")

    def test_the_native_baseline_cannot_resolve_but_the_locked_one_compares(self) -> None:
        native = self.sh(self.ws, "cargo", "semver-checks", "--package", "alpha",
                         "--baseline-rev", self.base)
        self.assertEqual(native.returncode, 101, native.stderr)
        self.assertIn("failed to select a version", native.stderr)
        summary = self.ws.parent / "summary.md"
        with mock.patch.dict(os.environ, self.env):
            code = gate.main(["--repo", str(self.ws), "--base", self.base, "--package", "alpha",
                              "--rustdoc-toolchain", PINNED, "--summary", str(summary)])
        self.assertEqual(code, 100, summary.read_text(encoding="utf-8"))
        self.assertIn("| `alpha` | compared |", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
