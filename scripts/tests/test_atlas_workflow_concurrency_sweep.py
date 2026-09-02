#!/usr/bin/env python3
"""Tests for atlas-workflow-concurrency-sweep.py's rewrite.

The rewrite must produce the conforming form the conformance detector accepts
(verification: per-commit group on the default branch, pull-request-only
cancellation; deploy: `cancel-in-progress: false`), keep a CRLF file CRLF, and
report rather than absorb the shapes it cannot rewrite.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("atlas_workflow_concurrency_sweep", SCRIPTS / "atlas-workflow-concurrency-sweep.py")
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)
CONF = importlib.util.spec_from_file_location("atlas_conformance_for_sweep", SCRIPTS / "atlas-conformance.py")
conformance = importlib.util.module_from_spec(CONF)
sys.modules[CONF.name] = conformance
CONF.loader.exec_module(conformance)

VERIFICATION = (
    "name: ci\non:\n  push:\n    branches: [main]\n  pull_request:\n"
    "concurrency:\n  group: ci-${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n\n"
    "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps: []\n"
)
DEPLOY = VERIFICATION.replace("name: ci", "name: Deploy mdBook")


class RewriteTests(unittest.TestCase):
    def test_verification_workflow_takes_the_per_commit_form_the_detector_accepts(self) -> None:
        self.assertTrue(conformance.cancels_default_branch_runs(VERIFICATION))
        text, kind = sweep.rewrite(".github/workflows/ci.yml", VERIFICATION)
        self.assertEqual(kind, "verification")
        self.assertIn("group: ci-${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.sha }}", text)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", text)
        self.assertFalse(conformance.cancels_default_branch_runs(text))
        self.assertIn("\n\njobs:", text, "the blank line after the block survives")

    def test_deploy_workflow_by_file_name_queues_instead_of_cancelling(self) -> None:
        text, kind = sweep.rewrite(".github/workflows/book-pages.yml", DEPLOY)
        self.assertEqual(kind, "deploy")
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("group: ci-${{ github.workflow }}-${{ github.ref }}", text, "deploys keep the per-ref group")
        self.assertFalse(conformance.cancels_default_branch_runs(text))

    def test_tool_words_inside_ordinary_ci_do_not_make_it_a_deploy(self) -> None:
        # ritk's and moirai's CI workflows mention maturin; that is a build step, not a deploy.
        text = VERIFICATION.replace("steps: []", "steps:\n      - run: maturin build && cargo publish --dry-run")
        self.assertEqual(sweep.rewrite(".github/workflows/python-ci.yml", text)[1], "verification")

    def test_a_pages_deploy_action_marks_a_deploy_whatever_the_file_name(self) -> None:
        text = VERIFICATION.replace("steps: []", "steps:\n      - uses: actions/deploy-pages@abc")
        self.assertEqual(sweep.rewrite(".github/workflows/ci.yml", text)[1], "deploy")

    def test_crlf_files_stay_crlf(self) -> None:
        crlf = VERIFICATION.replace("\n", "\r\n")
        self.assertTrue(conformance.cancels_default_branch_runs(crlf))
        text, kind = sweep.rewrite(".github/workflows/ci.yml", crlf)
        self.assertEqual(kind, "verification")
        self.assertNotIn("\n", text.replace("\r\n", ""), "every newline is CRLF")
        self.assertFalse(conformance.cancels_default_branch_runs(text))

    def test_shapes_it_cannot_rewrite_are_reported_not_absorbed(self) -> None:
        no_ref = VERIFICATION.replace("group: ci-${{ github.workflow }}-${{ github.ref }}", "group: fixed-name")
        text, kind = sweep.rewrite(".github/workflows/ci.yml", no_ref)
        self.assertEqual((text, kind), (no_ref, "skip: group line without github.ref"))
        already = VERIFICATION.replace("${{ github.ref }}", "${{ github.sha }}")
        self.assertEqual(sweep.rewrite(".github/workflows/ci.yml", already)[1], "skip: group already keyed per commit")


if __name__ == "__main__":
    unittest.main()
