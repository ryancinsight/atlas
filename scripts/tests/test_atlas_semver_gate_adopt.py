#!/usr/bin/env python3
"""Tests for atlas-semver-gate-adopt.py's workflow edits and package selection.

The adoption must produce a workflow the caller's YAML parser accepts, keep
the release gate ahead of the jobs it gates, exclude crates the stack marks
unpublishable, and hold the release list to crates the registry carries.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "atlas_semver_gate_adopt", SCRIPTS / "atlas-semver-gate-adopt.py"
)
adopt = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = adopt
SPEC.loader.exec_module(adopt)

CI = (
    "name: CI\n"
    "on:\n"
    "  pull_request:\n"
    "  push:\n"
    "    branches: [main]\n"
    "\n"
    "jobs:\n"
    "  verify:\n"
    "    name: Rust verification\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: cargo test\n"
)
RELEASE = (
    "name: Crates.io Release\n"
    "on:\n"
    "  release:\n"
    "    types: [published]\n"
    "  workflow_dispatch:\n"
    "\n"
    "jobs:\n"
    "  publish:\n"
    "    if: >-\n"
    "      github.event_name == 'workflow_dispatch' ||\n"
    "      startsWith(github.event.release.tag_name, 'crate-')\n"
    "    uses: ryancinsight/atlas/.github/workflows/crates-publish.yml@abc\n"
    "    with:\n"
    "      rust-toolchain: \"1.97.0\"\n"
    "  announce:\n"
    "    needs: publish\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - run: echo done\n"
)


def informational(packages=("alpha", "beta"), toolchain="1.97.0"):
    return adopt.job_block(
        name="semver", packages=list(packages), atlas_ref="a" * 40, toolchain=toolchain,
        guard=None, release=False, comment="informational",
    )


class PackageSelectionTests(unittest.TestCase):
    def test_unpublishable_crates_are_excluded(self) -> None:
        manifests = {
            "Cargo.toml": "[workspace]\nmembers = ['crates/*']\n",
            "crates/alpha/Cargo.toml": "[package]\nname = 'alpha'\nversion = '0.1.0'\n",
            "crates/guard/Cargo.toml": "[package]\nname = 'guard'\npublish = false\n",
            "crates/empty/Cargo.toml": "[package]\nname = 'empty'\npublish = []\n",
            "crates/registry/Cargo.toml": "[package]\nname = 'reg'\npublish = ['crates-io']\n",
            "crates/broken/Cargo.toml": "[package\nname = ",
        }
        self.assertEqual(adopt.publishable_packages(manifests), ["alpha", "reg"])

    def test_sparse_index_paths_follow_cargos_layout(self) -> None:
        self.assertEqual(adopt.sparse_index_path("a"), "1/a")
        self.assertEqual(adopt.sparse_index_path("ab"), "2/ab")
        self.assertEqual(adopt.sparse_index_path("abc"), "3/a/abc")
        self.assertEqual(adopt.sparse_index_path("leto-ops"), "le/to/leto-ops")
        self.assertEqual(adopt.sparse_index_path("Hermes-SIMD"), "he/rm/hermes-simd")

    def test_only_crates_the_registry_carries_are_published(self) -> None:
        class Response:
            def __init__(self, status): self.status = status
            def __enter__(self): return self
            def __exit__(self, *_): return False

        def opener(request, timeout=None):
            if request.full_url.endswith("/al/ph/alpha"):
                return Response(200)
            raise OSError("404")

        self.assertEqual(adopt.published(["alpha", "beta"], opener=opener), {"alpha"})
        self.assertEqual(adopt.published([], opener=opener), set())


class WorkflowEditTests(unittest.TestCase):
    def test_the_informational_job_parses_and_carries_its_inputs(self) -> None:
        text = adopt.insert_job(CI, informational())
        parsed = yaml.safe_load(text)
        self.assertEqual(set(parsed["jobs"]), {"semver", "verify"})
        job = parsed["jobs"]["semver"]
        self.assertEqual(job["uses"], f"{adopt.SHARED}@{'a' * 40}")
        self.assertEqual(job["with"]["package"], "alpha,beta")
        self.assertEqual(job["with"]["rust-toolchain"], "1.97.0")
        self.assertNotIn("release-gate", job["with"])
        self.assertEqual(job["permissions"], {"contents": "read"})
        self.assertEqual(parsed["jobs"]["verify"], yaml.safe_load(CI)["jobs"]["verify"],
                         "the existing job is untouched")

    def test_a_member_without_a_toolchain_pin_omits_the_input(self) -> None:
        job = yaml.safe_load(adopt.insert_job(CI, informational(toolchain=None)))["jobs"]["semver"]
        self.assertNotIn("rust-toolchain", job["with"])

    def test_the_release_gate_shares_the_workflows_guard_and_gates_its_jobs(self) -> None:
        guard = adopt.guard_of(RELEASE)
        self.assertEqual(
            guard,
            "github.event_name == 'workflow_dispatch' ||\n"
            "startsWith(github.event.release.tag_name, 'crate-')",
        )
        block = adopt.job_block(
            name="semver", packages=["alpha"], atlas_ref="b" * 40, toolchain="1.97.0",
            guard=guard, release=True, comment="release",
        )
        parsed = yaml.safe_load(adopt.add_needs(adopt.insert_job(RELEASE, block), "semver"))
        self.assertTrue(parsed["jobs"]["semver"]["with"]["release-gate"])
        self.assertEqual(parsed["jobs"]["semver"]["if"], parsed["jobs"]["publish"]["if"],
                         "the gate runs on exactly the events the release does")
        self.assertEqual(parsed["jobs"]["publish"]["needs"], "semver",
                         "the entry job waits for the gate instead of racing it")
        self.assertEqual(parsed["jobs"]["announce"]["needs"], "publish",
                         "a job already downstream keeps its own dependency")

    def test_a_workflow_without_jobs_is_reported_not_mangled(self) -> None:
        with self.assertRaisesRegex(ValueError, "no top-level `jobs:` key"):
            adopt.insert_job("name: CI\non: [push]\n", informational())

    def test_crlf_workflows_keep_their_line_endings(self) -> None:
        text = adopt.add_needs(adopt.insert_job(RELEASE.replace("\n", "\r\n"), informational()),
                               "semver")
        self.assertIn("    needs: semver\r\n", text)
        self.assertIsNotNone(yaml.safe_load(text))


class PullRequestOpeningTests(unittest.TestCase):
    url = "https://github.com/ryancinsight/leto/pull/7"

    def runner(self, merge_code: int = 0):
        calls: list[list[str]] = []

        def run(argv, cwd=None, **_options):
            calls.append(argv)
            if argv[:3] == ["gh", "pr", "create"]:
                return subprocess.CompletedProcess(argv, 0, self.url + "\n", "")
            return subprocess.CompletedProcess(argv, merge_code, "", "auto merge is not allowed")

        return run, calls

    def test_the_adoption_pr_is_created_then_auto_merged_with_an_explicit_merge_method(self) -> None:
        run, calls = self.runner()
        status = adopt.open_adoption_pull_request("ryancinsight/leto", "main", "body", "leto: 1 workflow(s)", run=run)
        self.assertEqual(status, 0)
        self.assertEqual(
            calls[0],
            ["gh", "pr", "create", "-R", "ryancinsight/leto", "--base", "main", "--head", adopt.BRANCH,
             "--title", "ci: Adopt the shared SemVer gate", "--body", "body"],
        )
        self.assertEqual(calls[1], ["gh", "pr", "merge", self.url, "--auto", "--merge", "--delete-branch"])
        self.assertEqual(len(calls), 2)

    def test_a_pr_whose_auto_merge_failed_exits_non_zero_naming_the_pr(self) -> None:
        run, _ = self.runner(merge_code=1)
        with patch("sys.stderr") as stderr:
            status = adopt.open_adoption_pull_request("ryancinsight/leto", "main", "body", "leto: 1", run=run)
        self.assertEqual(status, 1)
        self.assertIn(self.url, "".join(call.args[0] for call in stderr.write.call_args_list))


if __name__ == "__main__":
    unittest.main()
