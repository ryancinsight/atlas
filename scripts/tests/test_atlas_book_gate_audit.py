#!/usr/bin/env python3
"""Regression tests for the committed Atlas book-gate audit."""

from __future__ import annotations

import io
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-book-gate-audit.py"
spec = importlib.util.spec_from_file_location("atlas_book_gate_audit", SCRIPT)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


class BookGateClassificationTestCase(unittest.TestCase):
    def test_shared_input_is_classified(self) -> None:
        workflow = """
        jobs:
          deploy:
            uses: ryancinsight/atlas/.github/workflows/book-pages.yml@abc
            with:
              mdbook-test: true
        """
        self.assertEqual(audit.classify_workflow(workflow)[0], "shared-input")

    def test_inline_direct_run_is_classified(self) -> None:
        workflow = """
        jobs:
          build:
            steps:
              - run: mdbook test docs/book
        """
        self.assertEqual(audit.classify_workflow(workflow)[0], "direct-command")

    def test_block_direct_run_is_classified(self) -> None:
        workflow = """
        jobs:
          build:
            steps:
              - name: Verify examples
                run: |
                  set -euo pipefail
                  mdbook test docs/book
        """
        self.assertEqual(audit.classify_workflow(workflow)[0], "direct-command")

    def test_comments_and_job_names_do_not_count(self) -> None:
        workflow = """
        # mdbook test docs/book is documented here, not executed.
        jobs:
          mdbook test docs/book:
            steps:
              - run: echo "book build only"
        """
        self.assertEqual(audit.classify_workflow(workflow)[0], "none")

    def test_echoed_command_text_does_not_count(self) -> None:
        workflow = """
        jobs:
          build:
            steps:
              - run: echo "mdbook test docs/book"
        """
        self.assertEqual(audit.classify_workflow(workflow)[0], "none")

    def test_shared_input_takes_precedence_over_direct_command(self) -> None:
        workflow = """
        jobs:
          deploy:
            uses: ryancinsight/atlas/.github/workflows/book-pages.yml@abc
            with:
              mdbook-test: true
          extra:
            steps:
              - run: mdbook test docs/book
        """
        self.assertEqual(audit.classify_workflow(workflow)[0], "shared-input")

    def test_combined_check_reports_missing_gate(self) -> None:
        result = audit.BookGate("apollo", "abc123", True, True, "none", "no gate")
        stderr = io.StringIO()
        with patch.object(audit, "audit", return_value=[result]), patch(
            "sys.stderr", stderr
        ):
            self.assertEqual(audit.main(["--check", "--require-gates"]), 1)
        self.assertIn("lack an executable gate", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
