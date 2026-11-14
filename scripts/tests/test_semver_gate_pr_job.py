"""The pull-request SemVer job runs the locked comparison the way its workflow invokes it."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import yaml

import atlas_semver_pr as gate

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "semver-gate.yml"


def job_steps(name: str) -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][name]["steps"]


class WiringTests(unittest.TestCase):
    def test_the_job_runs_the_locked_comparison_script_without_the_action(self) -> None:
        steps = job_steps("semver-pr")
        self.assertFalse([s for s in steps if "cargo-semver-checks-action" in s.get("uses", "")])
        semver = next(s for s in steps if s.get("id") == "semver")
        self.assertIs(semver["continue-on-error"], True)
        self.assertIn("atlas_semver_pr.py", semver["run"])
        self.assertIn('--rustdoc-toolchain "$RUSTDOC_TOOLCHAIN"', semver["run"])
        self.assertNotIn("baseline-rev", semver["run"])
        atlas = next(s for s in steps if s.get("with", {}).get("path") == "_atlas")
        self.assertLess(steps.index(atlas), steps.index(semver))

    def test_a_setup_failure_stays_informational_and_is_reported(self) -> None:
        steps = {s["id"]: s for s in job_steps("semver-pr") if "id" in s}
        for name in ("tool", "atlas"):
            self.assertIs(steps[name]["continue-on-error"], True, name)
            self.assertIn(f"steps.{name}.outcome == 'success'", steps["semver"]["if"])
        report = next(s for s in job_steps("semver-pr") if "did not complete" in s.get("name", ""))
        for clause in ("steps.tool.outcome == 'failure'", "steps.atlas.outcome == 'failure'",
                       "steps.semver.outcome == 'failure'", "outputs.exit != '100'",
                       "outputs.exit != '101'"):
            self.assertIn(clause, report["if"])


@unittest.skipUnless(shutil.which("cargo") and shutil.which("git"), "needs cargo and git")
class NestedManifestTests(unittest.TestCase):
    """The workflow passes `--repo .` with the caller's `manifest-path`, which may be nested."""

    def test_a_nested_manifest_resolves_against_a_relative_repo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            crate = repo / "crates" / "a"
            (crate / "src").mkdir(parents=True)
            (crate / "Cargo.toml").write_text(
                '[package]\nname = "a"\nversion = "0.1.0"\nedition = "2021"\n', encoding="utf-8")
            (crate / "src" / "lib.rs").write_text("", encoding="utf-8")
            for argv in (("init", "-q"), ("add", "-A"), ("-c", "user.name=t", "-c",
                         "user.email=t@example.test", "commit", "-qm", "base")):
                subprocess.run(["git", *argv], cwd=repo, check=True, capture_output=True)
            real, builds = gate.run, []

            def fake(argv, cwd, env):
                if argv[1] == "metadata":
                    return real(argv, cwd, env)
                builds.append(argv)
                return types.SimpleNamespace(returncode=1, stdout=b"", stderr=b"stub")

            summary = Path(directory) / "summary.md"
            with contextlib.chdir(repo), mock.patch.object(gate, "run", fake):
                code = gate.main(["--repo", ".", "--base", "HEAD", "--manifest-path",
                                  "crates/a/Cargo.toml", "--package", "a",
                                  "--rustdoc-toolchain", "nightly-pin", "--summary", str(summary)])
            text = summary.read_text(encoding="utf-8")
        self.assertEqual(code, 101, text)
        self.assertIn("base rustdoc unavailable", text)
        self.assertEqual(len(builds), 1)
        self.assertTrue(Path(builds[0][builds[0].index("--manifest-path") + 1]).is_absolute())


if __name__ == "__main__":
    unittest.main()
