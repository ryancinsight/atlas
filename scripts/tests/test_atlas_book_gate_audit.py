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

    def test_workflow_with_no_executable_rust_fence_is_vacuous(self) -> None:
        gate, reason = audit.classify_coverage(
            "shared-input", "mdbook-test: true", 0
        )
        self.assertEqual(gate, "vacuous-shared-input")
        self.assertIn("no executable Rust book fence", reason)

    def test_ignored_and_no_run_fences_do_not_count_as_executable(self) -> None:
        contents = """
```rust,ignore
fn ignored() {}
```
```rust,no_run
fn compiled_only() {}
```
```rust
fn executes() {}
```
"""
        fences = [
            audit.RUST_FENCE_RE.match(line)
            for line in contents.splitlines()
            if audit.RUST_FENCE_RE.match(line)
        ]
        self.assertEqual(len(fences), 3)
        executable = sum(
            not {
                value.strip().lower()
                for value in match.group("attributes").lstrip(",").split(",")
                if value.strip()
            }.intersection({"ignore", "no_run"})
            for match in fences
        )
        self.assertEqual(executable, 1)

    def test_summary_sources_exclude_orphaned_and_external_documents(self) -> None:
        summary = """
# Summary
- [Included](chapter.md)
  - [Nested](examples/sample.md#result)
- [External](https://example.com/chapter.md)
- [Anchor](#local)
- [Parent](../outside.md)
"""
        self.assertEqual(
            audit._summary_sources(summary),
            ("docs/book/SUMMARY.md", "docs/book/chapter.md",
             "docs/book/examples/sample.md"),
        )

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
