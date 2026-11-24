"""The PR SemVer comparison builds its baseline from the base's own lock (hephaestus PR 537)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

import atlas_semver_pr as gate
import process_tree


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
SEMVER_CHECKS_TOOL = "cargo-semver-checks 0.51.0"
# `skipUnless` below is evaluated when the module is imported, so a probe that
# stalls here blocks collection of the whole file before any test's own budget
# applies. Measured on a development host, ten runs each on 2026-11-24:
# `cargo semver-checks --version` 0.09 s median and 0.10 s maximum, `rustup
# toolchain list` 0.04 s. No hosted-runner figure exists for either probe. The
# CI-to-host slowdown recorded in process_tree.py is 15x, measured on compute-bound
# work, so it bounds a startup probe only loosely. 60 s is therefore a finite stall
# detector, 600x the warm answer, not a derived limit; a probe past it reads as
# not ready.
PROBE_TIMEOUT_SECONDS = 60
TOOLS = ("cargo", "git", "cargo-semver-checks", "rustup")
PROBES = (["cargo", "semver-checks", "--version"], ["rustup", "toolchain", "list"])


def probe(argv: list[str]) -> tuple[str | None, str]:
    """The probe's stdout, or why it did not answer: a stall is not a verdict."""
    try:
        done = process_tree.run(argv, timeout=PROBE_TIMEOUT_SECONDS)
    except process_tree.ProcessTreeTimeout:
        return None, f"`{' '.join(argv)}` did not answer within {PROBE_TIMEOUT_SECONDS:g} s"
    except process_tree.ProcessTreeCleanupError as error:
        return None, f"`{' '.join(argv)}` left a process tree it could not retire: {error.cleanup_error}"
    except OSError as error:
        return None, f"`{' '.join(argv)}` could not run: {error.strerror}"
    return done.stdout.decode("utf-8", "replace"), ""


def tool_ready() -> tuple[bool, str]:
    """Whether this host can run the slow test, and the reason when it cannot."""
    missing = [tool for tool in TOOLS if not shutil.which(tool)]
    if missing:
        return False, f"needs {', '.join(TOOLS)}; not on PATH: {', '.join(missing)}"
    version, reason = probe(PROBES[0])
    if reason:
        return False, reason
    installed, reason = probe(PROBES[1])
    if reason:
        return False, reason
    if version.strip() != SEMVER_CHECKS_TOOL:
        return False, f"needs {SEMVER_CHECKS_TOOL}, found {version.strip() or 'no version'}"
    if PINNED not in installed:
        return False, f"needs the pinned toolchain {PINNED}"
    return True, ""


READY, READY_REASON = tool_ready()


class ReadinessTests(unittest.TestCase):
    """The import-time probe is bounded, so collecting this file cannot hang."""

    def readiness(self, run, which=lambda tool: f"/bin/{tool}"):
        """`tool_ready()` with the host replaced: no probe here touches the tools."""
        with mock.patch.object(process_tree, "run", run), mock.patch.object(shutil, "which", which):
            return tool_ready()

    def test_each_probe_carries_the_one_deadline(self) -> None:
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            answer = SEMVER_CHECKS_TOOL if argv == PROBES[0] else PINNED
            return types.SimpleNamespace(stdout=(answer + "\n").encode())

        self.assertEqual(self.readiness(run), (True, ""))
        self.assertEqual([kwargs.get("timeout") for _, kwargs in calls],
                         [PROBE_TIMEOUT_SECONDS] * len(PROBES))
        self.assertEqual([argv for argv, _ in calls], list(PROBES))

    def test_a_stalled_probe_is_not_ready_and_names_itself(self) -> None:
        for stalled in PROBES:
            with self.subTest(probe=" ".join(stalled)):
                def run(argv, **kwargs):
                    if argv == stalled:
                        raise process_tree.ProcessTreeTimeout(argv, kwargs["timeout"], None, None, None)
                    return types.SimpleNamespace(stdout=b"")
                ready, reason = self.readiness(run)
                self.assertFalse(ready)
                self.assertIn(f"`{' '.join(stalled)}` did not answer within", reason)

    def test_the_deadline_ends_a_child_that_leaves_a_grandchild_holding_the_pipe(self) -> None:
        """A bare `subprocess.run(timeout=)` waits for the grandchild on Windows.

        Its kill reaches the child only, and the `communicate()` that follows
        returns when every holder of the stdout pipe has closed it: the
        grandchild's whole sleep. The runner owns the tree, so the probe returns
        within the deadline plus the runner's bounded cleanup.
        """
        deadline = 3.0
        bound = deadline + process_tree.PROCESS_TREE_CLEANUP_SECONDS
        grandchild_seconds = 3 * bound
        with tempfile.TemporaryDirectory() as scratch:
            spawned = Path(scratch) / "grandchild-spawned"
            child = (
                "import pathlib, subprocess, sys, time\n"
                f"subprocess.Popen([sys.executable, '-c', 'import time; time.sleep({grandchild_seconds})'])\n"
                f"pathlib.Path({str(spawned)!r}).write_bytes(b'')\n"
                f"time.sleep({grandchild_seconds})\n")
            started = time.monotonic()
            with mock.patch.object(sys.modules[__name__], "PROBE_TIMEOUT_SECONDS", deadline):
                stdout, reason = probe([sys.executable, "-c", child])
            elapsed = time.monotonic() - started
            self.assertTrue(spawned.is_file(), "the child was killed before it spawned the grandchild")
        self.assertIsNone(stdout)
        self.assertIn(f"did not answer within {deadline:g} s", reason)
        self.assertLess(elapsed, bound)

    def test_every_other_not_ready_answer_says_why(self) -> None:
        def answer(version=SEMVER_CHECKS_TOOL, installed=PINNED):
            return lambda argv, **kwargs: types.SimpleNamespace(
                stdout=((version if argv == PROBES[0] else installed) + "\n").encode())

        cases = {
            "not on PATH: rustup": (
                answer(), lambda tool: None if tool == "rustup" else "/bin/x"),
            "found cargo-semver-checks 0.50.0": (
                answer(version="cargo-semver-checks 0.50.0"), None),
            f"pinned toolchain {PINNED}": (
                answer(installed="stable-x86_64-unknown-linux-gnu"), None),
        }
        for expected, (run, which) in cases.items():
            with self.subTest(expected):
                ready, reason = self.readiness(run, which) if which else self.readiness(run)
                self.assertFalse(ready)
                self.assertIn(expected, reason)

    def test_a_tree_the_runner_cannot_retire_is_not_ready(self) -> None:
        def run(argv, **kwargs):
            raise process_tree.ProcessTreeCleanupError("job still holds a process")
        ready, reason = self.readiness(run)
        self.assertFalse(ready)
        self.assertIn("could not retire: job still holds a process", reason)

    def test_a_probe_that_cannot_start_is_not_ready(self) -> None:
        def run(argv, **kwargs):
            raise FileNotFoundError(2, "No such file or directory", argv[0])
        ready, reason = self.readiness(run)
        self.assertFalse(ready)
        self.assertIn("could not run", reason)


@pytest.mark.slow
@unittest.skipUnless(READY, READY_REASON)
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
