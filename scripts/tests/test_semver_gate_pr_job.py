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
# Each git call here works on a one-file repository: at most 0.25 s measured on this host
# (init, add, commit). The hosted runner is about 15x slower, 3.75 s; 30 s is 8x that.
GIT_DEADLINE_SECONDS = 30
# The comparison step runs only after both setup steps succeed, and the fallback reports a
# setup failure or a comparison that ended neither updated-required (100) nor failed (101).
SEMVER_IF = "steps.tool.outcome == 'success' && steps.atlas.outcome == 'success'"
FALLBACK_IF = ("steps.tool.outcome == 'failure' || steps.atlas.outcome == 'failure' || "
               "(steps.semver.outcome == 'failure' && steps.semver.outputs.exit != '100' && "
               "steps.semver.outputs.exit != '101')")
# The step publishes its status as an output, then exits with it so the step outcome follows.
SEMVER_RUN_TAIL = ['echo "exit=$status" >> "$GITHUB_OUTPUT"', 'exit "$status"']


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
        self.assertEqual(steps["semver"]["if"], SEMVER_IF)
        self.assertEqual(steps["semver"]["run"].splitlines()[-2:], SEMVER_RUN_TAIL)
        report = next(s for s in job_steps("semver-pr") if "did not complete" in s.get("name", ""))
        self.assertEqual(report["if"], FALLBACK_IF)


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
                subprocess.run(["git", *argv], cwd=repo, check=True, capture_output=True,
                               timeout=GIT_DEADLINE_SECONDS)
            real, metadata, builds = gate.run, [], []

            def fake(argv, cwd, env):
                if argv[1] == "metadata":
                    metadata.append(argv)
                    return real(argv, cwd, env)
                builds.append(argv)
                return types.SimpleNamespace(returncode=1, stdout=b"", stderr=b"stub")

            summary = Path(directory) / "summary.md"
            with contextlib.chdir(repo), mock.patch.object(gate, "run", fake):
                code = gate.main(["--repo", ".", "--base", "HEAD", "--manifest-path",
                                  "crates/a/Cargo.toml", "--package", "a",
                                  "--rustdoc-toolchain", "nightly-pin", "--summary", str(summary)])
            text = summary.read_text(encoding="utf-8")
        # The head manifest is the only path built from `--repo`; the base one lies in the export.
        self.assertEqual(len(metadata), 2, text)
        head = Path(metadata[1][metadata[1].index("--manifest-path") + 1])
        self.assertEqual(head, repo.resolve() / "crates" / "a" / "Cargo.toml")
        self.assertEqual(code, 101, text)
        self.assertIn("base rustdoc unavailable", text)
        self.assertEqual(len(builds), 1)


if __name__ == "__main__":
    unittest.main()
