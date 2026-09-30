"""Validate the shared crate workflow's version-change publish contract (ADR 0068).

The structural tests read the parsed workflow. The plan tests execute the plan
job's own shell against stub `cargo` and `curl` executables, so the selection
of pending packages is checked by value without network or registry state.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "crates-publish.yml"


def plan_script(workflow: dict) -> str:
    return next(step for step in workflow["jobs"]["plan"]["steps"] if step.get("id") == "plan")["run"]


class CratesPublishStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.jobs = cls.workflow["jobs"]

    def test_version_change_jobs_run_only_on_push_or_schedule(self) -> None:
        self.assertEqual(
            self.jobs["plan"]["if"],
            "github.event_name == 'push' || github.event_name == 'schedule'",
        )
        for job in ("semver", "publish-pending"):
            self.assertEqual(self.jobs[job]["if"], "needs.plan.outputs.count != '0'")
        self.assertEqual(self.jobs["publish-pending"]["needs"], ["plan", "semver"])

    def test_release_and_dispatch_paths_exclude_push(self) -> None:
        self.assertEqual(
            self.jobs["validate"]["if"],
            "github.event_name == 'release' || github.event_name == 'workflow_dispatch'",
        )
        self.assertEqual(self.jobs["publish"]["if"], "github.event_name == 'release'")

    def test_pending_publish_uses_trusted_publishing_in_the_registry_environment(self) -> None:
        job = self.jobs["publish-pending"]
        self.assertEqual(job["environment"]["name"], "crates-io")
        self.assertEqual(job["permissions"], {"contents": "write", "id-token": "write"})
        self.assertFalse(job["concurrency"]["cancel-in-progress"])
        uses = [step.get("uses", "") for step in job["steps"]]
        self.assertTrue(any(u.startswith("rust-lang/crates-io-auth-action@") for u in uses))
        publish = next(s for s in job["steps"] if s.get("name") == "Publish the pending packages in dependency order")
        self.assertEqual(publish["env"]["CARGO_REGISTRY_TOKEN"], "${{ steps.auth.outputs.token }}")

    def test_release_tags_survive_a_partial_publish(self) -> None:
        tag = next(s for s in self.jobs["publish-pending"]["steps"] if s.get("name") == "Tag a release for each published version")
        self.assertEqual(tag["if"], "${{ !cancelled() && steps.auth.outcome == 'success' }}")
        self.assertIn("index.crates.io", tag["run"])

    def test_semver_gate_blocks_on_the_pending_set(self) -> None:
        semver = self.jobs["semver"]
        self.assertTrue(semver["uses"].startswith("ryancinsight/atlas/.github/workflows/semver-gate.yml@"))
        self.assertIs(semver["with"]["release-gate"], True)
        self.assertEqual(semver["with"]["package"], "${{ needs.plan.outputs.packages }}")


STUB_CARGO = """\
#!/usr/bin/env bash
case "$1" in
  metadata) cat "$STUB_DIR/metadata.json" ;;
  package)
    if [[ -f "$STUB_DIR/package.err" ]]; then cat "$STUB_DIR/package.err" >&2; exit 101; fi
    echo "$@" > "$STUB_DIR/package.args" ;;
  *) exit 2 ;;
esac
"""

# curl -sS -o <file> -w '%{http_code}' <url>: write the index body, print the status.
STUB_CURL = """\
#!/usr/bin/env bash
out=""; url=""
while [[ $# -gt 0 ]]; do
  case "$1" in -o) out="$2"; shift 2 ;; -w|-sS) [[ "$1" == -w ]] && shift; shift ;; *) url="$1"; shift ;; esac
done
name="${url##*/}"
if [[ -f "$STUB_DIR/index/$name" ]]; then cp "$STUB_DIR/index/$name" "$out"; printf 200
else : > "$out"; printf 404; fi
"""


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq"), "plan script needs bash and jq")
class CratesPublishPlanTests(unittest.TestCase):
    def run_plan(self, packages: list[dict], index: dict[str, list[str]], package_err: str | None = None):
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stubs = root / "bin"
            (root / "index").mkdir()
            stubs.mkdir()
            for name, body in (("cargo", STUB_CARGO), ("curl", STUB_CURL)):
                path = stubs / name
                path.write_text(body, encoding="utf-8", newline="\n")
                path.chmod(path.stat().st_mode | stat.S_IXUSR)
            (root / "metadata.json").write_text(json.dumps({"packages": packages}), encoding="utf-8")
            for name, versions in index.items():
                lines = "".join(json.dumps({"name": name, "vers": v}) + "\n" for v in versions)
                (root / "index" / name).write_text(lines, encoding="utf-8", newline="\n")
            if package_err is not None:
                (root / "package.err").write_text(package_err, encoding="utf-8")
            script = root / "plan.sh"
            script.write_text(plan_script(workflow), encoding="utf-8", newline="\n")
            output = root / "github_output"
            env = dict(os.environ, PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}",
                       STUB_DIR=str(root), GITHUB_OUTPUT=str(output))
            proc = subprocess.run(["bash", str(script)], cwd=root, env=env, capture_output=True, text=True)
            outputs = dict(line.split("=", 1) for line in output.read_text().splitlines()) if output.exists() else {}
            args = (root / "package.args").read_text().split() if (root / "package.args").exists() else []
            return proc, outputs, args

    @staticmethod
    def pkg(name: str, version: str, publish=None) -> dict:
        return {"name": name, "version": version, "publish": publish}

    def test_selects_only_versions_absent_from_the_index(self) -> None:
        proc, outputs, args = self.run_plan(
            [self.pkg("alpha-core", "0.7.0"), self.pkg("alpha", "0.7.0"), self.pkg("alpha-macros", "0.6.0")],
            {"alpha-core": ["0.6.0"], "alpha": ["0.6.0"], "alpha-macros": ["0.6.0"]},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(outputs, {"packages": "alpha-core,alpha", "count": "2"})
        self.assertEqual(args, ["package", "--locked", "--no-verify", "--package", "alpha-core", "--package", "alpha"])

    def test_never_published_and_unpublishable_packages_are_skipped(self) -> None:
        proc, outputs, _ = self.run_plan(
            [self.pkg("beta-new", "0.1.0"), self.pkg("beta-internal", "0.1.0", publish=[])],
            {},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(outputs, {"count": "0"})
        self.assertIn("beta-new has never been published", proc.stdout)
        self.assertNotIn("beta-internal", proc.stdout)

    def test_missing_upstream_version_waits_instead_of_failing(self) -> None:
        proc, outputs, _ = self.run_plan(
            [self.pkg("gamma", "0.43.0")],
            {"gamma": ["0.42.0"]},
            package_err="error: failed to select a version for the requirement `hermes-simd = \"^0.7.0\"`\n",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(outputs, {"count": "0"})
        self.assertIn("::warning::pending packages (gamma)", proc.stdout)

    def test_other_packaging_failures_fail_the_plan(self) -> None:
        proc, outputs, _ = self.run_plan(
            [self.pkg("delta", "1.1.0")],
            {"delta": ["1.0.0"]},
            package_err="error: failed to verify manifest: missing license\n",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("count", outputs)


if __name__ == "__main__":
    unittest.main()
