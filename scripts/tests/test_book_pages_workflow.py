"""Static contracts for book validation and caller-authorized publication.

These assertions bind the reviewed predicates to the real workflow. GitHub
retains its implicit success() gate through `needs: build`; no deployment is
performed by this suite.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/book-pages.yml"


class BookPagesWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.jobs = cls.workflow["jobs"]

    def step(self, name: str) -> dict:
        return next(step for step in self.jobs["build"]["steps"] if step.get("name") == name)

    def test_existing_callers_retain_the_deployment_default(self) -> None:
        contract = self.workflow[True]["workflow_call"]["inputs"]["deploy"]
        self.assertEqual(contract["type"], "boolean")
        self.assertIs(contract["required"], False)
        self.assertIs(contract["default"], True)

    def test_deployment_requires_caller_authorization_and_rejects_pull_requests(self) -> None:
        self.assertEqual(
            self.jobs["deploy"]["if"],
            "inputs.deploy && github.event_name != 'pull_request'",
        )
        self.assertEqual(self.jobs["deploy"]["needs"], "build")
        self.assertNotIn("continue-on-error", self.jobs["build"])
        self.assertNotIn("continue-on-error", self.jobs["deploy"])

    def test_validation_is_independent_of_publication(self) -> None:
        self.assertEqual(set(self.jobs), {"build", "deploy"})
        self.assertNotIn("if", self.jobs["build"])
        self.assertNotIn("if", self.step("Build book"))
        samples = self.step("Test book code samples")
        self.assertEqual(samples["if"], "inputs.mdbook-test")
        self.assertIn("mdbook test", samples["run"])
        self.assertNotIn("continue-on-error", samples)
        self.assertIn("mdbook build", self.step("Build book")["run"])
        self.assertIn('"$OUTPUT_PATH/index.html"', self.step("Build book")["run"])

    def test_validation_does_not_require_pages_configuration(self) -> None:
        configure = self.step("Configure Pages")
        self.assertEqual(configure["if"], "inputs.deploy")
        self.assertEqual(
            configure["uses"],
            "actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b",
        )

    def test_every_successful_build_retains_its_pages_artifact(self) -> None:
        upload = self.step("Upload Pages artifact")
        self.assertNotIn("if", upload)
        self.assertEqual(
            upload["uses"],
            "actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b",
        )
        self.assertEqual(upload["with"], {"path": "${{ inputs.output-path }}"})
        self.assertNotIn("continue-on-error", upload)
        self.assertLess(
            self.jobs["build"]["steps"].index(self.step("Build book")),
            self.jobs["build"]["steps"].index(upload),
        )

    def test_permissions_environment_and_deployer_are_preserved(self) -> None:
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertNotIn("permissions", self.jobs["build"])
        deploy = self.jobs["deploy"]
        self.assertEqual(deploy["permissions"], {"pages": "write", "id-token": "write"})
        self.assertEqual(deploy["environment"], {
            "name": "github-pages", "url": "${{ steps.deployment.outputs.page_url }}",
        })
        self.assertEqual(deploy["steps"], [{
            "name": "Deploy to GitHub Pages", "id": "deployment",
            "uses": "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
        }])
        self.assertEqual(self.jobs["build"]["timeout-minutes"], 25)
        self.assertEqual(deploy["timeout-minutes"], 10)


if __name__ == "__main__":
    unittest.main()
