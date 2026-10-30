"""Pin the native workflow-lint deployment boundary."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github" / "actions" / "workflow-lint" / "action.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "workflow-lint.yml"


class WorkflowLintDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.action_source = ACTION.read_text(encoding="utf-8")
        cls.action = yaml.safe_load(cls.action_source)
        cls.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    def test_workflow_calls_the_same_revision_action_for_the_candidate(self) -> None:
        self.assertIsNone(self.workflow[True]["workflow_call"])
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        job = self.workflow["jobs"]["workflow-lint"]
        self.assertEqual(job["runs-on"], "ubuntu-latest")
        self.assertEqual(job["timeout-minutes"], 5)
        self.assertEqual(
            job["steps"],
            [
                {
                    "uses": "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                    "with": {"persist-credentials": False},
                },
                {
                    "name": "Run the native workflow analyzers",
                    "uses": "$/.github/actions/workflow-lint",
                    "with": {"candidate": "${{ github.sha }}"},
                },
            ],
        )

    def test_action_pins_all_analyzers_and_archive_digests(self) -> None:
        self.assertEqual(
            self.action["inputs"],
            {
                "candidate": {
                    "description": "Exact candidate commit checked out in the workspace",
                    "required": True,
                }
            },
        )
        install = self.action["runs"]["steps"][0]
        self.assertEqual(
            install["env"],
            {
                "ACTIONLINT_VERSION": "1.7.12",
                "ACTIONLINT_SHA256": "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
                "SHELLCHECK_VERSION": "0.11.0",
                "SHELLCHECK_SHA256": "8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198",
            },
        )
        command = install["run"]
        self.assertIn('"PyYAML==6.0.3" "pyflakes==4.0.0"', command)
        self.assertEqual(command.count("sha256sum --check --strict"), 2)
        for version in ("ACTIONLINT_VERSION", "SHELLCHECK_VERSION"):
            self.assertIn(version, command)
        self.assertNotIn("continue-on-error", self.action_source)

    def test_test_and_lint_commands_use_the_closed_source_bundle(self) -> None:
        test_step, lint_step = self.action["runs"]["steps"][1:]
        for step in (test_step, lint_step):
            command = step["run"]
            self.assertIn('python_source_loader.py"', command)
            for module in ("process_tree", "windows_process", "darwin_process"):
                self.assertIn(f'--module "{module}=$scripts/{module}.py"', command)
            self.assertEqual(
                set(step["env"]),
                {"ACTIONLINT", "SHELLCHECK", "PYFLAKES", "PYTHON"},
            )
        self.assertIn(
            '--module "atlas_workflow_lint=$scripts/atlas_workflow_lint.py"',
            test_step["run"],
        )
        self.assertIn('tests/test_atlas_workflow_lint.py"', test_step["run"])
        for option, variable in (
            ("actionlint", "ACTIONLINT"),
            ("shellcheck", "SHELLCHECK"),
            ("pyflakes", "PYFLAKES"),
        ):
            self.assertIn(f'--{option} "${variable}"', lint_step["run"])
        self.assertIn('--candidate "${{ inputs.candidate }}"', lint_step["run"])
        self.assertNotIn("-ignore", lint_step["run"])


if __name__ == "__main__":
    unittest.main()
