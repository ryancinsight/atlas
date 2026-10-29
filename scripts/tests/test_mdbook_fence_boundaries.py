"""Fence boundary regressions for the book link and heading validator."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import check_mdbook_links as checker


def chapter_with_false_closer(false_closer: str, fence: str = "```") -> str:
    return (
        f"{fence}markdown\n{false_closer}\n"
        "[example](example-only.md)\n# Example heading\n"
        f"{fence}\n[real](real.md)\n# Real heading\n"
    )


class FenceBoundaryTests(unittest.TestCase):
    def test_four_space_indentation_does_not_close(self):
        for fence in ("```", "~~~~"):
            with self.subTest(fence=fence):
                text = chapter_with_false_closer("    " + fence, fence)
                self.assertEqual(list(checker.extract_links(text)), ["real.md"])

    def test_tab_indentation_does_not_close(self):
        text = chapter_with_false_closer("\t```")
        self.assertEqual(list(checker.extract_links(text)), ["real.md"])

    def test_non_ascii_whitespace_is_not_closing_fence_padding(self):
        for false_closer in ("\u00a0```", "```\u00a0", "```\v", "```\f"):
            with self.subTest(false_closer=false_closer):
                text = chapter_with_false_closer(false_closer)
                self.assertEqual(list(checker.extract_links(text)), ["real.md"])

    def test_heading_extraction_uses_the_same_fence_boundary(self):
        text = chapter_with_false_closer("    ```")
        self.assertEqual(checker.heading_ids(text), ["real-heading"])

    def test_valid_closing_indents_padding_and_line_endings(self):
        for indent in range(4):
            for newline in ("\n", "\r\n"):
                with self.subTest(indent=indent, newline=newline):
                    text = newline.join([
                        "````markdown", "[example](example-only.md)",
                        " " * indent + "````` \t", "[real](real.md)", "",
                    ])
                    self.assertEqual(list(checker.extract_links(text)), ["real.md"])

    def test_valid_book_does_not_fail_on_links_shown_as_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chapter.md").write_text(
                chapter_with_false_closer("    ```"), encoding="utf-8"
            )
            (root / "real.md").write_text("# Real destination\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = checker.main([str(root)])
            self.assertEqual(code, 0, output.getvalue())
            self.assertIn("  FILE_MISSING  : 0", output.getvalue())

    def test_missing_real_destination_remains_a_gate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chapter.md").write_text(
                chapter_with_false_closer("    ```"), encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = checker.main([str(root)])
            self.assertEqual(code, 1)
            self.assertIn("real.md", output.getvalue())
            self.assertNotIn("example-only.md", output.getvalue())


if __name__ == "__main__":
    unittest.main()
