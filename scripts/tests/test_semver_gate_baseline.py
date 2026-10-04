"""The SemVer release gate checks each listed crate's registry baseline, not the joined list.

Before the split, `package: a,b` asked crates.io for the crate named "a,b", got 404, read it
as a first publication, and skipped cargo-semver-checks for every multi-crate caller.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "semver-gate.yml"

# curl -sS -o /dev/null -w '%{http_code}' -H <ua> <url>: print the fixture status for the crate.
# The stub answers only that exact argument list, the gate's User-Agent included, and exits
# 99 on anything else -- an extra or repeated flag, another endpoint -- so the gate cannot
# read a malformed request's 404 as a first publication.
STUB_CURL = """\
#!/usr/bin/env bash
expected=(-sS -o /dev/null -w '%{http_code}' -H 'User-Agent: atlas-semver-gate (github.com/ryancinsight/atlas)')
[[ $# -eq $(( ${#expected[@]} + 1 )) ]] || exit 99
for i in "${!expected[@]}"; do
  [[ "${@:i+1:1}" == "${expected[i]}" ]] || exit 99
done
url="${@: -1}"
name="${url#https://crates.io/api/v1/crates/}"
if [[ "$name" == "$url" || ! "$name" =~ ^[A-Za-z0-9_-]+$ ]]; then exit 99; fi
echo "$name" >> "$STUB_DIR/asked"
if [[ ! -f "$STUB_DIR/status/$name" ]]; then printf 404; exit 0; fi
status="$(cat "$STUB_DIR/status/$name")"
# `fail`: no HTTP answer (DNS, TLS, reset). Real curl still writes `000` for
# `%{http_code}` before it exits nonzero.
if [[ "$status" == fail ]]; then printf 000; exit 7; fi
printf '%s' "$status"
"""


# sleep SECONDS: record the interval the crawler policy asks for.
STUB_SLEEP = """\
#!/usr/bin/env bash
echo "$1" >> "$STUB_DIR/slept"
"""


RELEASE_JOB = {
    "if": "inputs.release-gate || github.event_name == 'release' || (github.event_name == 'push' && "
          "startsWith(github.ref, 'refs/tags/'))",
    "runs-on": "ubuntu-latest",
    "timeout-minutes": 20,
}
# Every release-gate step's wiring: what it runs and every id, if, env, and with it carries.
# A `continue-on-error` on the job or any step, or a changed condition, changes this table.
RELEASE_STEPS = [
    {"uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "with": {"fetch-depth": 0}},
    {"id": "checkable",
     "env": {"PACKAGE": "${{ inputs.package }}", "MANIFEST": "${{ inputs.manifest-path }}"}},
    {"if": "inputs.apt-packages != ''"},
    {"id": "baseline-exists", "if": "inputs.baseline-source == 'registry'",
     "env": {"PACKAGE": "${{ steps.checkable.outputs.packages }}"}},
    {"id": "baseline", "if": "inputs.baseline-source == 'tag'"},
    {"uses": "obi1kenobi/cargo-semver-checks-action@6b69fcf40e9b5fb17adeb57e4b6ecd020649a239",
     "if": "steps.checkable.outputs.packages != '' && (inputs.baseline-source != 'registry' "
           "|| steps.baseline-exists.outputs.published == 'true')",
     "with": {
         "package": "${{ inputs.baseline-source == 'registry' && steps.baseline-exists.outputs.packages "
                    "|| steps.checkable.outputs.packages }}",
         "manifest-path": "${{ inputs.manifest-path }}",
         "rust-toolchain": "${{ inputs.rust-toolchain }}",
         "baseline-rev": "${{ inputs.baseline-source == 'tag' && steps.baseline.outputs.baseline || '' }}",
         "verbose": True,
     }},
]


class ReleaseJobWiringTests(unittest.TestCase):
    def test_the_release_job_and_every_step_are_wired_as_specified(self) -> None:
        job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["semver-release"]
        self.assertEqual({k: v for k, v in job.items() if k not in ("name", "steps")}, RELEASE_JOB)
        self.assertEqual([{k: v for k, v in step.items() if k not in ("name", "run")}
                          for step in job["steps"]], RELEASE_STEPS)


@unittest.skipUnless(shutil.which("bash"), "the gate step is a bash script")
class BaselineSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["semver-release"]["steps"]
        cls.step = next(s for s in steps if s.get("id") == "baseline-exists")

    def run_step(self, package: str, status: dict[str, str]):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "status").mkdir()
            for name, body in (("curl", STUB_CURL), ("sleep", STUB_SLEEP)):
                path = root / "bin" / name
                path.write_text(body, encoding="utf-8", newline="\n")
                path.chmod(path.stat().st_mode | stat.S_IXUSR)
            for name, code in status.items():
                (root / "status" / name).write_text(code, encoding="utf-8")
            script = root / "step.sh"
            script.write_text(self.step["run"], encoding="utf-8", newline="\n")
            output = root / "out"
            env = dict(os.environ, PATH=f"{root / 'bin'}{os.pathsep}{os.environ['PATH']}",
                       STUB_DIR=str(root), GITHUB_OUTPUT=str(output), PACKAGE=package)
            proc = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
            outputs = dict(l.split("=", 1) for l in output.read_text().splitlines()) if output.exists() else {}
            asked = (root / "asked").read_text().split() if (root / "asked").exists() else []
            self.slept = (root / "slept").read_text().split() if (root / "slept").exists() else []
            return proc, outputs, asked

    def test_each_name_is_asked_and_the_published_subset_is_gated(self) -> None:
        proc, outputs, asked = self.run_step("hermes-simd, hermes-simd-core,fresh", {"hermes-simd": "200", "hermes-simd-core": "200"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(asked, ["hermes-simd", "hermes-simd-core", "fresh"])
        self.assertEqual(outputs, {"published": "true", "packages": "hermes-simd,hermes-simd-core"})
        self.assertIn("fresh is not on crates.io", proc.stdout)
        self.assertEqual(self.slept, ["1", "1", "1"])

    def test_all_first_publications_skip_the_comparison(self) -> None:
        proc, outputs, _ = self.run_step("fresh-a,fresh-b", {})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(outputs, {"published": "false"})

    def test_an_outage_fails_the_gate(self) -> None:
        proc, outputs, asked = self.run_step("a,b", {"a": "200", "b": "503"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("crates.io returned HTTP 503 for b", proc.stderr)
        self.assertEqual((asked, outputs), (["a", "b"], {}))

    def test_a_refusal_or_rate_limit_fails_the_gate(self) -> None:
        # Only 404 means "not on crates.io"; 403 and 429 are the registry refusing to answer.
        for status in ("403", "429"):
            with self.subTest(status=status):
                proc, outputs, asked = self.run_step("a", {"a": status})
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(f"crates.io returned HTTP {status} for a", proc.stderr)
                self.assertEqual((asked, outputs), (["a"], {}))

    def test_a_single_published_crate_is_gated(self) -> None:
        proc, outputs, asked = self.run_step("a", {"a": "200"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((asked, outputs), (["a"], {"published": "true", "packages": "a"}))

    def test_a_failed_curl_fails_the_gate(self) -> None:
        # No HTTP answer at all must not read as "not on crates.io".
        proc, outputs, asked = self.run_step("a", {"a": "fail"})
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("crates.io returned HTTP 000 for a", proc.stderr)
        self.assertEqual((asked, outputs), (["a"], {}))

    def test_empty_list_entries_are_skipped(self) -> None:
        proc, outputs, asked = self.run_step("a,, ,b", {"a": "200", "b": "200"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(asked, ["a", "b"])
        self.assertEqual(outputs, {"published": "true", "packages": "a,b"})


# cargo metadata --no-deps --format-version 1 --manifest-path MANIFEST: print the fixture
# workspace. Anything else exits 99 so the selection cannot pass on an unexpected query.
STUB_CARGO = """\
#!/usr/bin/env bash
[[ "$#" -eq 6 && "$1" == metadata && "$2" == --no-deps && "$3" == --format-version \
&& "$4" == 1 && "$5" == --manifest-path ]] || exit 99
cat "$STUB_DIR/metadata.json"
"""


# A library, a proc-macro, a binary, a cdylib-only, and a crate whose proc-macro
# target sits beside a library one -- the shapes the pending sets actually carry.
FIXTURE_METADATA = """\
{"packages": [
  {"name": "lib-crate", "targets": [{"kind": ["lib"]}]},
  {"name": "macro-crate", "targets": [{"kind": ["proc-macro"]}]},
  {"name": "bin-crate", "targets": [{"kind": ["bin"]}]},
  {"name": "cdylib-crate", "targets": [{"kind": ["cdylib"]}]},
  {"name": "two-target-crate", "targets": [{"kind": ["proc-macro"]}, {"kind": ["lib"]}]}
]}
"""


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"),
                     "the step resolves its `cargo` stub through a POSIX PATH")
class LibraryTargetSelectionTests(unittest.TestCase):
    """A selection with no library target skips the comparison instead of failing the release.

    cargo-semver-checks renders a verdict from rustdoc-documented API surfaces and exits 101 on
    a selection where every crate lacks one (a proc-macro-only pending set), so the gate selects
    the library-bearing names itself and skips -- with a notice -- when none remain.
    """

    @classmethod
    def setUpClass(cls) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.steps = {job: next(s for s in spec["steps"] if s.get("id") == "checkable")
                     for job, spec in workflow["jobs"].items()}

    def run_step(self, job: str, package: str, metadata: str = FIXTURE_METADATA):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            stub = root / "bin" / "cargo"
            stub.write_text(STUB_CARGO, encoding="utf-8", newline="\n")
            stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
            (root / "metadata.json").write_text(metadata, encoding="utf-8")
            script = root / "step.sh"
            script.write_text(self.steps[job]["run"], encoding="utf-8", newline="\n")
            output, summary = root / "out", root / "summary"
            env = dict(os.environ, PATH=f"{root / 'bin'}{os.pathsep}{os.environ['PATH']}",
                       STUB_DIR=str(root), GITHUB_OUTPUT=str(output),
                       GITHUB_STEP_SUMMARY=str(summary), PACKAGE=package, MANIFEST="Cargo.toml")
            proc = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
            outputs = dict(l.split("=", 1) for l in output.read_text().splitlines()) if output.exists() else {}
            return proc, outputs, summary.read_text() if summary.exists() else ""

    def test_the_library_bearing_subset_is_selected_in_the_caller_s_order(self) -> None:
        proc, outputs, summary = self.run_step(
            "semver-release", "lib-crate, macro-crate,bin-crate,cdylib-crate,two-target-crate,absent")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(outputs, {"packages": "lib-crate,cdylib-crate,two-target-crate"})
        self.assertNotIn("::notice::", proc.stdout)
        self.assertEqual(summary, "")

    def test_a_surface_less_selection_skips_with_a_notice_and_a_summary(self) -> None:
        proc, outputs, summary = self.run_step("semver-release", "macro-crate,bin-crate")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(outputs, {"packages": ""})
        self.assertIn("::notice::none of macro-crate,bin-crate has a library target", proc.stdout)
        self.assertIn("SemVer: not compared", summary)

    def test_a_metadata_query_that_cannot_run_fails_the_step(self) -> None:
        # A workspace whose metadata cargo cannot produce must fail closed, not
        # read as "no library targets" and skip the release gate.
        proc, outputs, _ = self.run_step("semver-release", "lib-crate", metadata="not json")
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(outputs, {})

    def test_both_jobs_select_with_the_same_step(self) -> None:
        self.assertEqual(self.steps["semver-pr"]["run"], self.steps["semver-release"]["run"])


if __name__ == "__main__":
    unittest.main()
