"""Structural coverage for the Atlas conformance aggregate."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import unittest

import process_tree

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE_PATH = ROOT / ".github/workflows/atlas-conformance.yml"
PYTHON_TESTS_PATH = ROOT / ".github/workflows/python-tests.yml"


def workflow(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


class AtlasWorkflowGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conformance_text = CONFORMANCE_PATH.read_text(encoding="utf-8")
        self.python_text = PYTHON_TESTS_PATH.read_text(encoding="utf-8")
        self.conformance = workflow(CONFORMANCE_PATH)
        self.python_tests = workflow(PYTHON_TESTS_PATH)

    def test_python_suite_has_one_parameterless_execution_owner(self) -> None:
        self.assertEqual(set(self.python_tests["on"]), {"workflow_call"})
        self.assertEqual(self.python_tests["on"]["workflow_call"], "")
        self.assertNotIn("concurrency", self.python_tests)
        conformance_runs = "\n".join(
            step.get("run", "")
            for job in self.conformance["jobs"].values()
            for step in job.get("steps", [])
        )
        self.assertNotIn("-m pytest", conformance_runs)
        self.assertEqual(self.python_text.count("output_mode=process_tree.OutputMode.INHERIT"), 2)

    def test_fast_and_slow_selectors_are_preserved_and_bounded(self) -> None:
        expected = {
            "pytest-fast": (
                'python - python -m pytest -v -p xdist.plugin -m "not slow" '
                "-n auto --maxprocesses=8 --max-worker-restart=0 --dist=worksteal"
            ),
            "pytest-slow": "python - python -m pytest -v -m slow",
        }
        jobs = self.python_tests["jobs"]
        self.assertEqual(set(jobs), set(expected))
        for job_name, command in expected.items():
            with self.subTest(job=job_name):
                step_name = "Run pytest (fast)" if job_name == "pytest-fast" else "Run pytest (slow)"
                step = next(item for item in jobs[job_name]["steps"] if item["name"] == step_name)
                self.assertIn(command, step["run"])
                self.assertIn("timeout=600", step["run"])
                self.assertIn("output_mode=process_tree.OutputMode.INHERIT", step["run"])
                self.assertIn("raise SystemExit(result.returncode)", step["run"])
                self.assertNotIn("buffer.write", step["run"])

    def test_conformance_calls_script_suite_once(self) -> None:
        jobs = self.conformance["jobs"]
        calls = [
            job for job in jobs.values()
            if job.get("uses") == "./.github/workflows/python-tests.yml"
        ]
        self.assertEqual(len(calls), 1)
        self.assertEqual(jobs["conformance-check"]["name"], "Debt-class inventory")
        self.assertEqual(jobs["conformance-check"]["timeout-minutes"], "10")

    def test_required_result_rejects_every_incomplete_verdict_and_draft(self) -> None:
        result = self.conformance["jobs"]["conformance-result"]
        self.assertEqual(
            result["name"],
            "Debt-class ratchet (counts non-increasing vs committed baseline)",
        )
        self.assertEqual(
            set(result["needs"]),
            set(self.conformance["jobs"]) - {"conformance-result"},
        )
        self.assertIn("always()", result["if"])
        step = result["steps"][0]
        self.assertEqual(
            set(step["env"]),
            {
                "PULL_REQUEST_DRAFT",
                "WORKFLOW_LINT_RESULT",
                "CONFORMANCE_RESULT",
                "SCRIPT_TESTS_RESULT",
                "STACK_OVERLAY_RESULT",
                "VERSION_COHERENCE_RESULT",
                "PIN_DRIFT_RESULT",
            },
        )
        self.assertIn('$PULL_REQUEST_DRAFT" = "true', step["run"])
        self.assertIn('$result" != "success', step["run"])

    def test_cohort_checks_have_one_execution_owner_at_recorded_pins(self) -> None:
        jobs = self.conformance["jobs"]
        for job, filename, triggers in (
            ("stack-overlay", "atlas-stack-overlay.yml", {"workflow_call"}),
            ("version-coherence", "version-guard.yml", {"workflow_call", "schedule"}),
        ):
            with self.subTest(job=job):
                owner = "./.github/workflows/" + filename
                self.assertEqual([name for name, value in jobs.items() if value.get("uses") == owner], [job])
                called = workflow(ROOT / ".github/workflows" / filename)
                self.assertEqual(set(called["on"]), triggers)
                runs = "\n".join(step.get("run", "") for value in called["jobs"].values() for step in value.get("steps", []))
                self.assertIn("submodule update --init --force --depth=1", runs)
                self.assertNotIn("submodule update --init --force --depth=1 --remote", runs)
                if job == "stack-overlay":
                    self.assertIn("atlas-stack-overlay.py check --pinned", runs)

    def test_aggregate_executes_failure_cancel_skip_and_draft_cases(self) -> None:
        step = self.conformance["jobs"]["conformance-result"]["steps"][0]
        bash = shutil.which("bash")
        self.assertIsNotNone(bash, "the workflow shell is required to execute its result policy")
        successful = {name: "success" for name in step["env"] if name != "PULL_REQUEST_DRAFT"}
        scenarios = [("green", {**successful, "PULL_REQUEST_DRAFT": "false"}, 0, b"")]
        for dependency in successful:
            for outcome in ("failure", "cancelled", "skipped", ""):
                scenarios.append((dependency + ":" + outcome, {**successful, "PULL_REQUEST_DRAFT": "false", dependency: outcome}, 1, b"A required conformance dependency"))
        scenarios.append(("draft", {**successful, "PULL_REQUEST_DRAFT": "true"}, 1, b"Draft pull requests"))
        for name, values, status, diagnostic in scenarios:
            with self.subTest(case=name):
                environment = {**os.environ, **values}
                for key in ("BASH_ENV", "ENV"):
                    environment.pop(key, None)
                result = process_tree.run([bash, "--noprofile", "--norc", "-c", step["run"]], env=environment, timeout=10)
                self.assertEqual(result.returncode, status, result.stderr)
                if status == 0:
                    self.assertEqual(result.stdout, b"")
                else:
                    self.assertIn(diagnostic, result.stdout)

    def test_trigger_union_covers_scripts_without_filtering_pull_requests(self) -> None:
        triggers = self.conformance["on"]
        self.assertNotIn("paths", triggers["pull_request"])
        self.assertEqual(
            set(triggers["pull_request"]["types"]),
            {"opened", "synchronize", "reopened", "ready_for_review"},
        )
        push_paths = set(triggers["push"]["paths"])
        self.assertTrue({".cargo/config.toml", "tools/_template/**", "tools/version-guard/**"} <= push_paths)
        self.assertIn("scripts/**", push_paths)
        self.assertIn(".github/workflows/**", push_paths)
        self.assertEqual(set(triggers["schedule"][0]), {"cron"})

    def test_schedule_excludes_every_job_except_pin_drift(self) -> None:
        jobs = self.conformance["jobs"]
        for name in ("workflow-lint", "conformance-check", "script-tests", "stack-overlay", "version-coherence", "conformance-result"):
            with self.subTest(job=name):
                self.assertIn("github.event_name != 'schedule'", jobs[name]["if"])
        self.assertNotIn("schedule", jobs["pin-drift"]["if"])
        for name in ("conformance-check", "script-tests", "stack-overlay", "version-coherence", "pin-drift"):
            self.assertIn("github.event.pull_request.draft == false", jobs[name]["if"])


if __name__ == "__main__":
    unittest.main()
