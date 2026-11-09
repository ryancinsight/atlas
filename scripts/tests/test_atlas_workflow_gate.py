"""Structural coverage for the Atlas conformance aggregate."""

from __future__ import annotations

from pathlib import Path
import unittest

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
            {"workflow-lint", "conformance-check", "script-tests"},
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
            },
        )
        self.assertIn('$PULL_REQUEST_DRAFT" = "true', step["run"])
        self.assertIn('$result" != "success', step["run"])

    def test_trigger_union_covers_scripts_without_filtering_pull_requests(self) -> None:
        triggers = self.conformance["on"]
        self.assertNotIn("paths", triggers["pull_request"])
        self.assertEqual(
            set(triggers["pull_request"]["types"]),
            {"opened", "synchronize", "reopened", "ready_for_review"},
        )
        push_paths = set(triggers["push"]["paths"])
        self.assertIn("scripts/**", push_paths)
        self.assertIn(".github/workflows/**", push_paths)
        self.assertEqual(set(triggers["schedule"][0]), {"cron"})

    def test_schedule_excludes_every_job_except_pin_drift(self) -> None:
        jobs = self.conformance["jobs"]
        for name in ("workflow-lint", "conformance-check", "script-tests", "conformance-result"):
            with self.subTest(job=name):
                self.assertIn("github.event_name != 'schedule'", jobs[name]["if"])
        self.assertNotIn("if", jobs["pin-drift"])
        for name in ("conformance-check", "script-tests"):
            self.assertIn("github.event.pull_request.draft == false", jobs[name]["if"])


if __name__ == "__main__":
    unittest.main()
