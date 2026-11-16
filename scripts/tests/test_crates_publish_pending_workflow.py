"""Structure of the version-change publish workflow (ADR 0068).

The selection logic is tested by value in test_crates_pending.py; these tests pin the
workflow properties that logic relies on: default-branch-only triggering, the SemVer gate
ahead of publishing, trusted publishing in the registry environment, and one pinned
revision for the shared action and gate.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "crates-publish-pending.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "crates-publish.yml"

PLAN_IF = ("github.event_name == 'schedule' || (github.event_name == 'push'\n"
           "    && github.ref == format('refs/heads/{0}', github.event.repository.default_branch))")
CHECKOUT = {"uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "with": {"persist-credentials": False}}
TOOLCHAIN = {"uses": "dtolnay/rust-toolchain@4cda84d5c5c54efe2404f9d843567869ab1699d4", "with": {"toolchain": "${{ inputs.rust-toolchain }}"}}
PENDING = "ryancinsight/atlas/.github/actions/crates-pending"
# Every step's wiring: which action or script it runs and every id, if, env, and with it carries.
# Any change to how an input, output, token, or outcome flows between steps changes this table.
EXPECTED_STEPS = {
    "plan": [
        CHECKOUT,
        {"if": "inputs.apt-packages != ''", "env": {"APT_PACKAGES": "${{ inputs.apt-packages }}"},
         "run": "sudo apt-get update\n"
                "# Word splitting is the input's contract: a space-separated list.\n"
                "# shellcheck disable=SC2086\n"
                "sudo apt-get install -y --no-install-recommends $APT_PACKAGES\n"},
        TOOLCHAIN,
        {"uses": PENDING, "id": "plan", "with": {"command": "plan", "owner": "${{ inputs.owner }}",
                                                "cohort-json": "${{ inputs.cohort-json }}"}},
    ],
    "publish": [
        CHECKOUT,
        TOOLCHAIN,
        {"uses": "rust-lang/crates-io-auth-action@c6f97d42243bad5fab37ca0427f495c86d5b1a18", "id": "auth"},
        {"uses": PENDING, "id": "publish", "env": {"CARGO_REGISTRY_TOKEN": "${{ steps.auth.outputs.token }}"},
         "with": {"command": "publish", "packages": "${{ needs.plan.outputs.packages }}",
                  "cohort-json": "${{ inputs.cohort-json }}"}},
        {"uses": PENDING, "if": "${{ !cancelled() && steps.auth.outcome == 'success' }}",
         "with": {"command": "tag", "packages": "${{ needs.plan.outputs.packages }}", "cohort-json": "${{ inputs.cohort-json }}",
                  "tag-prefix": "${{ inputs.tag-prefix }}", "publish-outcome": "${{ steps.publish.outcome }}"}},
    ],
}
EXPECTED_JOBS = {
    "plan": {"if": PLAN_IF, "runs-on": "ubuntu-latest", "timeout-minutes": 45,
             "permissions": {"contents": "read"},
             "outputs": {"packages": "${{ steps.plan.outputs.packages }}",
                         "count": "${{ steps.plan.outputs.count }}"}},
    "semver": {"needs": "plan", "if": "needs.plan.outputs.count != '0'",
               "uses": "ryancinsight/atlas/.github/workflows/semver-gate.yml",
               "permissions": {"contents": "read"},
               "with": {"release-gate": True, "package": "${{ needs.plan.outputs.packages }}",
                        "rust-toolchain": "${{ inputs.semver-toolchain || inputs.rust-toolchain }}",
                        "apt-packages": "${{ inputs.apt-packages }}",
                        "atlas-ref": "ff7bf4e8f56a55181ca343ae2a580c31b76471bf"}},
    "publish": {"needs": ["plan", "semver"], "if": "needs.plan.outputs.count != '0'",
                "runs-on": "ubuntu-latest", "timeout-minutes": 30,
                "concurrency": {"group": "crates-publish-pending-${{ github.repository }}",
                                "cancel-in-progress": False},
                "environment": {"name": "crates-io"},
                "permissions": {"contents": "write", "id-token": "write"}},
}


EXPECTED_INPUTS = {
    "rust-toolchain": {"required": True, "type": "string"},
    "semver-toolchain": {"required": False, "default": "", "type": "string"},
    "tag-prefix": {"required": False, "default": "", "type": "string"},
    "owner": {"required": False, "default": "ryancinsight", "type": "string"},
    "cohort-json": {"required": False, "default": "", "type": "string"},
    "apt-packages": {"required": False, "default": "", "type": "string"},
}


def wiring(entry: dict) -> dict:
    """An entry without its display name; atlas's own pins are reduced to the path they name.

    Atlas pins are tested apart (one revision, carrying this tree's content). Third-party pins
    stay whole: the auth action mints the registry token, so its commit is part of the wiring.
    """
    out = {k: v for k, v in entry.items() if k not in ("name", "steps")}
    if str(out.get("uses", "")).startswith("ryancinsight/atlas/"):
        out["uses"] = out["uses"].split("@", 1)[0]
    return out



class PendingWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.jobs = cls.workflow["jobs"]

    def step(self, job: str, name: str) -> dict:
        return next(s for s in self.jobs[job]["steps"] if s.get("name") == name)

    def test_the_callable_interface_is_exactly_the_specified_inputs(self) -> None:
        # yaml.safe_load reads the bare `on` key as the boolean True.
        self.assertEqual(set(self.workflow[True]), {"workflow_call"})
        inputs = self.workflow[True]["workflow_call"]["inputs"]
        self.assertEqual({name: {k: v for k, v in spec.items() if k != "description"}
                          for name, spec in inputs.items()}, EXPECTED_INPUTS)

    def test_every_job_and_step_is_wired_as_specified(self) -> None:
        self.assertEqual(set(self.jobs), set(EXPECTED_JOBS))
        for name, expected in EXPECTED_JOBS.items():
            self.assertEqual(wiring(self.jobs[name]), expected, name)
        for name, expected in EXPECTED_STEPS.items():
            self.assertEqual([wiring(step) for step in self.jobs[name]["steps"]], expected, name)

    def test_only_the_default_branch_or_a_schedule_plans(self) -> None:
        condition = " ".join(self.jobs["plan"]["if"].split())
        self.assertEqual(
            condition,
            "github.event_name == 'schedule' || (github.event_name == 'push' "
            "&& github.ref == format('refs/heads/{0}', github.event.repository.default_branch))")

    def test_semver_gate_precedes_publish_over_the_pending_set(self) -> None:
        self.assertEqual(self.jobs["semver"]["needs"], "plan")
        self.assertIs(self.jobs["semver"]["with"]["release-gate"], True)
        self.assertEqual(self.jobs["semver"]["with"]["package"], "${{ needs.plan.outputs.packages }}")
        self.assertEqual(self.jobs["publish"]["needs"], ["plan", "semver"])
        for job in ("semver", "publish"):
            self.assertEqual(self.jobs[job]["if"], "needs.plan.outputs.count != '0'")

    def test_publish_uses_trusted_publishing_with_least_privilege(self) -> None:
        job = self.jobs["publish"]
        self.assertEqual(job["environment"]["name"], "crates-io")
        self.assertEqual(job["permissions"], {"contents": "write", "id-token": "write"})
        self.assertEqual(self.jobs["plan"]["permissions"], {"contents": "read"})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertFalse(job["concurrency"]["cancel-in-progress"])
        for name in ("plan", "semver", "publish"):
            self.assertNotIn("continue-on-error", self.jobs[name])
        self.assertTrue(self.step("publish", "Request a short-lived crates.io token")["uses"]
                        .startswith("rust-lang/crates-io-auth-action@"))
        publish = self.step("publish", "Publish what is still pending")
        self.assertEqual(publish["env"]["CARGO_REGISTRY_TOKEN"], "${{ steps.auth.outputs.token }}")
        self.assertEqual(publish["with"]["command"], "publish")

    def test_tagging_survives_a_partial_publish(self) -> None:
        tag = self.step("publish", "Tag a release for each published version")
        self.assertEqual(tag["if"], "${{ !cancelled() && steps.auth.outcome == 'success' }}")
        self.assertEqual(tag["with"], {
            "command": "tag", "packages": "${{ needs.plan.outputs.packages }}",
            "cohort-json": "${{ inputs.cohort-json }}",
            "tag-prefix": "${{ inputs.tag-prefix }}", "publish-outcome": "${{ steps.publish.outcome }}"})
        self.assertEqual(self.step("publish", "Publish what is still pending")["id"], "publish")

    def test_plan_and_publish_receive_the_owner_and_the_planned_set(self) -> None:
        self.assertEqual(self.step("plan", "Select and verify the pending set")["with"],
                         {"command": "plan", "owner": "${{ inputs.owner }}", "cohort-json": "${{ inputs.cohort-json }}"})
        self.assertEqual(self.step("publish", "Publish what is still pending")["with"],
                         {"command": "publish", "packages": "${{ needs.plan.outputs.packages }}", "cohort-json": "${{ inputs.cohort-json }}"})
        self.assertEqual(self.jobs["plan"]["outputs"], {
            "packages": "${{ steps.plan.outputs.packages }}", "count": "${{ steps.plan.outputs.count }}"})

    def test_shared_action_and_gate_pin_one_full_revision(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        pins = set(re.findall(r"ryancinsight/atlas/\.github/(?:actions/crates-pending|workflows/semver-gate\.yml)@(\S+)", text))
        self.assertEqual(len(pins), 1, pins)
        pin = pins.pop()
        self.assertRegex(pin, r"^[0-9a-f]{40}$")
        self.assertEqual(self.jobs["semver"]["with"]["atlas-ref"], pin)

    def test_the_pinned_revision_carries_this_tree_s_action_and_gate(self) -> None:
        # CI runs the copies at the pin, not the files these tests read, so a pin
        # left on an older revision would ship code no test here exercised.
        text = WORKFLOW.read_text(encoding="utf-8")
        pin = re.search(r"ryancinsight/atlas/\.github/actions/crates-pending@(\S+)", text).group(1)
        probe = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{pin}^{{commit}}"],
                               capture_output=True)
        if probe.returncode:
            self.skipTest(f"pinned revision {pin} is not in this checkout (an export or shallow clone)")
        for path in (".github/actions/crates-pending/action.yml",
                     ".github/actions/crates-pending/crates_pending.py",
                     ".github/workflows/semver-gate.yml"):
            pinned = subprocess.run(["git", "-C", str(ROOT), "show", f"{pin}:{path}"],
                                    check=True, capture_output=True).stdout
            self.assertEqual(pinned.replace(b"\r\n", b"\n"),
                             (ROOT / path).read_bytes().replace(b"\r\n", b"\n"), path)

    def test_system_packages_reach_the_compiling_plan_and_the_gate(self) -> None:
        steps = [s.get("name") for s in self.jobs["plan"]["steps"]]
        install = steps.index("Install system packages the build scripts need")
        self.assertLess(install, steps.index("Select and verify the pending set"))
        self.assertEqual(self.step("plan", steps[install])["if"], "inputs.apt-packages != ''")
        self.assertEqual(self.jobs["semver"]["with"]["apt-packages"], "${{ inputs.apt-packages }}")

    def test_the_release_path_workflow_gains_no_permission(self) -> None:
        release = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
        scopes = [release.get("permissions", {})] + [job.get("permissions", {}) for job in release["jobs"].values()]
        granted = {p for scope in scopes for p, v in scope.items() if v == "write"}
        self.assertEqual(granted, {"id-token"})


# Minimal jq over the canned metadata the cargo stub emits: enough for the
# three fixed queries in the release-identity step (count, version, publish).
STUB_JQ = """\
import json
import sys
argv = sys.argv[1:]
package = argv[argv.index("--arg") + 2]
query = argv[-1]
metadata = json.load(sys.stdin)
matches = [p for p in metadata["packages"] if p.get("name") == package]
if "length" in query:
    print(len(matches))
elif "version" in query:
    print(matches[0]["version"])
else:
    publish = matches[0].get("publish")
    print("true" if (publish is None or "crates-io" in publish) else "false")
"""

STUB_CARGO = """\
#!/usr/bin/env bash
printf '%s' '{"packages":[{"name":"sample-pkg","version":"1.2.3","publish":null}]}'
"""


@unittest.skipUnless(shutil.which("bash"), "the release-identity step is a bash script")
class ReleaseTagResolutionTests(unittest.TestCase):
    """The release-event path resolves the package from either tag form (ATLAS-PUB-012).

    New tags carry no prefix (`<package>-v<version>`); the retired `crate-`
    prefix still resolves so existing releases keep working. The workflow's
    own script runs here against stubbed cargo/jq over canned metadata.
    """

    @classmethod
    def setUpClass(cls) -> None:
        release = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
        step = next(s for s in release["jobs"]["validate"]["steps"]
                    if s.get("name") == "Resolve and validate release identity")
        cls.script = step["run"]

    def run_resolve(self, tag: str, prefix: str = "") -> tuple[int, dict[str, str]]:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = os.path.join(tmp, "bin")
            os.mkdir(bin_dir)
            cargo = os.path.join(bin_dir, "cargo")
            with open(cargo, "w", encoding="utf-8", newline="\n") as out:
                out.write(STUB_CARGO)
            os.chmod(cargo, os.stat(cargo).st_mode | stat.S_IXUSR)
            jq_helper = os.path.join(tmp, "jq_stub.py")
            with open(jq_helper, "w", encoding="utf-8", newline="\n") as out:
                out.write(STUB_JQ)
            jq = os.path.join(bin_dir, "jq")
            with open(jq, "w", encoding="utf-8", newline="\n") as out:
                out.write(f'#!/usr/bin/env bash\nexec "{sys.executable}" "{jq_helper}" "$@"\n')
            os.chmod(jq, os.stat(jq).st_mode | stat.S_IXUSR)
            script = os.path.join(tmp, "resolve.sh")
            with open(script, "w", encoding="utf-8", newline="\n") as out:
                out.write(self.script)
            outputs = os.path.join(tmp, "outputs")
            env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"],
                       EVENT_NAME="release", INPUT_PACKAGE="", INPUT_VERSION="",
                       RELEASE_TAG=tag, TAG_PREFIX=prefix, GITHUB_OUTPUT=outputs)
            proc = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
            resolved = {}
            if os.path.exists(outputs):
                with open(outputs, encoding="utf-8") as recorded:
                    for line in recorded.read().splitlines():
                        key, _, value = line.partition("=")
                        resolved[key] = value
            return proc.returncode, resolved

    def test_the_new_prefix_free_form_resolves(self) -> None:
        code, resolved = self.run_resolve("sample-pkg-v1.2.3")
        self.assertEqual(code, 0)
        self.assertEqual(resolved, {"package": "sample-pkg", "version": "1.2.3"})

    def test_the_retired_crate_prefix_form_still_resolves(self) -> None:
        code, resolved = self.run_resolve("crate-sample-pkg-v1.2.3")
        self.assertEqual(code, 0)
        self.assertEqual(resolved, {"package": "sample-pkg", "version": "1.2.3"})

    def test_an_explicit_prefix_is_still_honored(self) -> None:
        code, resolved = self.run_resolve("crate-sample-pkg-v1.2.3", prefix="crate-")
        self.assertEqual(code, 0)
        self.assertEqual(resolved, {"package": "sample-pkg", "version": "1.2.3"})

    def test_a_non_release_tag_still_fails(self) -> None:
        code, _ = self.run_resolve("not-a-release")
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
