#!/usr/bin/env python3
"""Unit tests for scripts/check_mdbook_links.py.

Each test builds a temporary mdBook fixture, runs the link checker, and asserts
on the returned exit code and/or detected links. This guards against regressions
in math/code masking and broken-link detection.
"""
from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import check_mdbook_links as cml


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "check_mdbook_links.py"

# The module prints its per-book counters in a fixed column layout; it no
# longer exports a FILE_MISSING_PREFIX constant, so the tests pin the
# rendered prefix directly.
FILE_MISSING_PREFIX = "  FILE_MISSING  : "


class ExtractLinksTestCase(unittest.TestCase):
    """Contract of `extract_links`.

    These previously targeted a `find_md_links` that returned filtered
    `(line, target, line_no)` tuples. That function no longer exists: the
    module now splits the job, with `extract_links` yielding raw href
    strings and classification living in `is_external` / `check_book`.
    The math and recurrence cases still hold, because `extract_links`
    itself drops LaTeX-command and single-character hrefs.
    """

    def test_detects_good_link(self) -> None:
        text = "See [the chapter](chapter.md) for details."
        self.assertEqual(list(cml.extract_links(text)), ["chapter.md"])

    def test_yields_external_links_for_caller_to_classify(self) -> None:
        # `extract_links` is deliberately unopinionated about scheme;
        # `is_external` is the filter, so both hrefs come through here.
        text = "Visit [example](https://example.com) and [mail](mailto:test@example.com)."
        self.assertEqual(
            list(cml.extract_links(text)),
            ["https://example.com", "mailto:test@example.com"],
        )
        self.assertTrue(cml.is_external("https://example.com"))
        self.assertTrue(cml.is_external("mailto:test@example.com"))
        self.assertFalse(cml.is_external("chapter.md"))

    def test_ignores_inline_math(self) -> None:
        text = r"The transform is $\mathcal{R}[p_0](\mathbf{r}_s, R)$ here."
        self.assertEqual(list(cml.extract_links(text)), [])

    def test_ignores_block_math(self) -> None:
        text = "$$\n\\mathcal{R}[p_0](\\mathbf{r}_s, R)\n$$"
        self.assertEqual(list(cml.extract_links(text)), [])

    def test_ignores_inline_code_recurrence(self) -> None:
        text = "Use `[n+1](x)` to index into the array."
        self.assertEqual(list(cml.extract_links(text)), [])

    def test_fenced_code_links_are_still_extracted(self) -> None:
        # Characterization, not an endorsement: there is no fence
        # stripping in the module, so a link inside a fenced block is
        # extracted and would be link-checked. Documented here so that
        # adding fence handling fails this test and prompts an update
        # rather than silently changing behaviour.
        text = "```\n# See [docs](missing.md)\n```"
        self.assertEqual(list(cml.extract_links(text)), ["missing.md"])

    def test_ignores_single_char_href(self) -> None:
        text = "The recurrence p[n+1](x) is defined as ..."
        self.assertEqual(list(cml.extract_links(text)), [])

    def test_ignores_latex_command_href(self) -> None:
        text = r"The force is [F(m)](\mathbf{r}_s, t)."
        self.assertEqual(list(cml.extract_links(text)), [])


class CheckBookTestCase(unittest.TestCase):
    """Contract of `check_book`.

    `check_book(book_root, name, allowlist=...)` returns a report dict
    rather than the list of link dataclasses these tests were originally
    written against. Broken file links land in `file_missing` as
    `(origin, href, resolved_target, allowlist_marker)` tuples.
    """

    @staticmethod
    def _report(book: Path) -> dict:
        return cml.check_book(str(book), book.name)

    def test_no_errors_for_valid_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("See [overview](README.md).\n", encoding="utf-8")
            (book / "README.md").write_text("# Overview\n", encoding="utf-8")
            self.assertEqual(self._report(book)["file_missing"], [])

    def test_reports_broken_link(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("See [missing](missing.md).\n", encoding="utf-8")
            missing = self._report(book)["file_missing"]
            self.assertEqual(len(missing), 1)
            origin, href, _resolved, _marker = missing[0]
            self.assertEqual(origin, "chapter.md")
            self.assertEqual(href, "missing.md")

    def test_ignores_math_and_code_false_positives(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text(
                "Math $\\mathcal{R}[p_0](\\mathbf{r}_s, R)$ and code `[n+1](x)`.\n",
                encoding="utf-8",
            )
            self.assertEqual(self._report(book)["file_missing"], [])

    def test_detects_bad_link_despite_valid_math(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text(
                "Math $\\mathcal{R}[p_0](\\mathbf{r}_s, R)$ and a [bad link](missing.md).\n",
                encoding="utf-8",
            )
            missing = self._report(book)["file_missing"]
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0][1], "missing.md")

    def test_anchored_link_to_existing_file_is_valid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("See [section](README.md#intro).\n", encoding="utf-8")
            (book / "README.md").write_text("# Intro\n", encoding="utf-8")
            self.assertEqual(self._report(book)["file_missing"], [])

    def test_root_absolute_link_resolves_against_the_book_root(self) -> None:
        # mdBook semantics: a leading `/` is book-root-relative. Guards
        # the `Path.__truediv__` trap, where an absolute right operand
        # discards the base and escapes to the drive root.
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("See [overview](/README.md).\n", encoding="utf-8")
            (book / "README.md").write_text("# Overview\n", encoding="utf-8")
            self.assertEqual(self._report(book)["file_missing"], [])

    def test_root_absolute_link_from_subdirectory_uses_book_root(self) -> None:
        # The distinguishing case: `/README.md` from a nested chapter
        # must reach the book root, not the chapter's own directory.
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "README.md").write_text("# Overview\n", encoding="utf-8")
            nested = book / "guide"
            nested.mkdir()
            (nested / "chapter.md").write_text("See [overview](/README.md).\n", encoding="utf-8")
            self.assertEqual(self._report(book)["file_missing"], [])

    def test_root_absolute_link_to_absent_file_is_still_reported(self) -> None:
        # The fix must not mask genuinely broken root-absolute links.
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("See [gone](/nope.md).\n", encoding="utf-8")
            missing = self._report(book)["file_missing"]
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0][1], "/nope.md")

    def test_broken_link_entry_names_origin_href_and_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("See [broken](missing.md).\n", encoding="utf-8")
            missing = self._report(book)["file_missing"]
            self.assertEqual(len(missing), 1)
            origin, href, resolved, marker = missing[0]
            self.assertEqual(origin, "chapter.md")
            self.assertEqual(href, "missing.md")
            self.assertTrue(resolved.endswith("missing.md"))
            self.assertIsNone(marker)

    def test_missing_directory_is_reported_as_error(self) -> None:
        # Replaces an older `SummaryNotFoundError` case: the module no
        # longer requires a SUMMARY.md (it walks *.md directly), so the
        # remaining structural failure is a non-existent book root.
        with tempfile.TemporaryDirectory(prefix="mdbook-") as parent:
            absent = Path(parent) / "no-such-book"
            report = cml.check_book(str(absent), "absent")
            self.assertIn("error", report)
            self.assertIn("directory not found", report["error"])


class MainTestCase(unittest.TestCase):
    def test_main_returns_one_for_broken_link(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "chapter.md").write_text("See [broken](missing.md).\n", encoding="utf-8")
            self.assertEqual(cml.main([str(book)]), 1)

    def test_main_returns_zero_for_valid_book(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "README.md").write_text("# Overview\n", encoding="utf-8")
            self.assertEqual(cml.main([str(book)]), 0)

    def test_book_without_summary_is_not_an_error(self) -> None:
        # The module walks *.md directly and no longer requires a
        # SUMMARY.md, so its absence is clean rather than exit 1.
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "chapter.md").write_text("No summary.\n", encoding="utf-8")
            self.assertEqual(cml.main([str(book)]), 0)

    def test_main_prints_broken_link_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "chapter.md").write_text("See [broken](missing.md).\n", encoding="utf-8")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = cml.main([str(book)])
            output = captured.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn(f"{FILE_MISSING_PREFIX}1", output)
            self.assertIn("in chapter.md: link [missing.md]", output)

    def test_main_returns_one_for_missing_book_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            missing = Path(book) / "does_not_exist"
            captured = io.StringIO()
            # A non-existent root is an invocation error (exit 2), and the
            # diagnostic goes to stderr, not stdout.
            with contextlib.redirect_stderr(captured):
                exit_code = cml.main([str(missing)])
            self.assertEqual(exit_code, 2)
            self.assertIn("directory not found", captured.getvalue())

    def test_cli_main_exits_with_zero_for_valid_book(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "README.md").write_text("# Overview\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(book)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn(f"{FILE_MISSING_PREFIX}0", result.stdout)

    def test_cli_main_exits_with_one_for_broken_link(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "chapter.md").write_text("See [broken](missing.md).\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(book)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"{FILE_MISSING_PREFIX}1", result.stdout)

    def test_main_prints_file_missing_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "chapter.md").write_text("See [broken](missing.md).\n", encoding="utf-8")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = cml.main([str(book)])
            output = captured.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn(f"{FILE_MISSING_PREFIX}1", output)

    def test_main_prints_file_missing_zero_for_valid_book(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as book:
            book = Path(book)
            (book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (book / "README.md").write_text("# Overview\n", encoding="utf-8")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = cml.main([str(book)])
            output = captured.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn(f"{FILE_MISSING_PREFIX}0", output)

    def test_main_aggregates_file_missing_across_multiple_books(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mdbook-") as tmp:
            tmp = Path(tmp)
            valid_book = tmp / "valid"
            valid_book.mkdir()
            (valid_book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (valid_book / "README.md").write_text("# Overview\n", encoding="utf-8")

            broken_book = tmp / "broken"
            broken_book.mkdir()
            (broken_book / "SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
            (broken_book / "chapter.md").write_text("See [missing](missing.md).\n", encoding="utf-8")

            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = cml.main([str(valid_book), str(broken_book)])
            output = captured.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn(f"{FILE_MISSING_PREFIX}1", output)


if __name__ == "__main__":
    unittest.main()
