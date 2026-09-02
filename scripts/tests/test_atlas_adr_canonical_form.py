#!/usr/bin/env python3
"""Tests for atlas-adr-canonical-form.py.

Each observed heading shape maps to `# ADR <filename-number>: Title`; nothing
past the first heading changes; unnumbered files are reported, not rewritten.
"""

from __future__ import annotations

import importlib.util
import io
import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-adr-canonical-form.py"
SPEC = importlib.util.spec_from_file_location("atlas_adr_canonical_form", SCRIPT)
form = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = form
SPEC.loader.exec_module(form)

BODY = "\n\n- Status: Accepted\n\n## Context\n\nThe `ADR-0003:` string in prose stays.\n"


class HeadingFormTests(unittest.TestCase):
    def test_every_observed_shape_normalizes_to_the_colon_form(self) -> None:
        cases = {
            "# ADR-0001: Hyphenated prefix": "# ADR 0001: Hyphenated prefix",
            "# ADR 0001 — Em-dash form": "# ADR 0001: Em-dash form",
            "# ADR 0001 – En-dash form": "# ADR 0001: En-dash form",
            "# ADR 0001 - Hyphen separator": "# ADR 0001: Hyphen separator",
            "# 0001 — Bare number, em dash": "# ADR 0001: Bare number, em dash",
            "# 001. Dot form": "# ADR 0001: Dot form",
            "# ADR 0001 (hephaestus): Repo-tagged": "# ADR 0001: Repo-tagged",
            "# ADR-001: Heading number narrower than the filename": (
                "# ADR 0001: Heading number narrower than the filename"
            ),
            "#   ADR 0001:   Extra spacing   ": "# ADR 0001: Extra spacing",
            "# Provider default source and MSRV": "# ADR 0001: Provider default source and MSRV",
        }
        for heading, expected in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(form.canonical_heading(heading, "0001"), expected)

    def test_a_canonical_heading_is_left_byte_identical(self) -> None:
        line = "# ADR 0042: Already canonical"
        self.assertEqual(form.canonical_heading(line, "0042"), line)

    def test_a_canonical_heading_with_the_wrong_number_takes_the_filename_number(self) -> None:
        self.assertEqual(form.canonical_heading("# ADR 0009: Mismatched", "0004"), "# ADR 0004: Mismatched")

    def test_a_title_beginning_with_digits_is_not_mistaken_for_a_number(self) -> None:
        # `3D` is title text; the ADR's number comes from the filename.
        self.assertEqual(
            form.canonical_heading("# 3D transforms in one seam", "0007"),
            "# ADR 0007: 3D transforms in one seam",
        )

    def test_a_crlf_heading_keeps_its_carriage_return(self) -> None:
        self.assertEqual(form.canonical_heading("# ADR-0001: Windows file\r", "0001"), "# ADR 0001: Windows file\r")

    def test_a_non_heading_first_line_is_not_a_heading(self) -> None:
        self.assertIsNone(form.canonical_heading("Status: Accepted", "0001"))


class NormalizeTests(unittest.TestCase):
    def test_only_the_first_heading_changes(self) -> None:
        text = "# ADR-0003: Title" + BODY
        self.assertEqual(form.normalize(text, "0003"), "# ADR 0003: Title" + BODY)

    def test_leading_blank_lines_are_tolerated(self) -> None:
        text = "\n# 0003 — Title" + BODY
        self.assertEqual(form.normalize(text, "0003"), "\n# ADR 0003: Title" + BODY)

    def test_a_file_that_does_not_open_with_a_heading_is_untouched(self) -> None:
        text = "Preamble paragraph.\n\n# 0003 — Title" + BODY
        self.assertEqual(form.normalize(text, "0003"), text)

    def test_conforming_text_is_a_fixed_point(self) -> None:
        text = "# ADR 0003: Title" + BODY
        self.assertEqual(form.normalize(form.normalize(text, "0003"), "0003"), text)


class RunTests(unittest.TestCase):
    def _run(self, directory: Path, write: bool) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = form.run([directory], write=write)
        return code, out.getvalue()

    def test_check_reports_and_write_rewrites(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-form-") as temp:
            directory = Path(temp)
            (directory / "0001-a.md").write_text("# ADR-0001: A" + BODY, encoding="utf-8")
            (directory / "0002-b.md").write_text("# ADR 0002: B" + BODY, encoding="utf-8")
            (directory / "README.md").write_text("# ADR-index: not an ADR\n", encoding="utf-8")
            code, output = self._run(directory, write=False)
            self.assertEqual(code, 1)
            self.assertIn("0001-a.md", output)
            self.assertNotIn("0002-b.md", output)
            self.assertNotIn("README.md", output)
            code, _ = self._run(directory, write=True)
            self.assertEqual(code, 0)
            self.assertEqual((directory / "0001-a.md").read_text(encoding="utf-8"), "# ADR 0001: A" + BODY)
            self.assertEqual((directory / "README.md").read_text(encoding="utf-8"), "# ADR-index: not an ADR\n")
            self.assertEqual(self._run(directory, write=False), (0, ""))

    def test_an_unnumbered_file_is_reported_and_never_rewritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-form-") as temp:
            directory = Path(temp)
            (directory / "sparse-support-design.md").write_text("# Sparse support" + BODY, encoding="utf-8")
            code, output = self._run(directory, write=True)
            self.assertEqual(code, 0)
            self.assertIn("unnumbered", output)
            self.assertEqual(
                (directory / "sparse-support-design.md").read_text(encoding="utf-8"), "# Sparse support" + BODY
            )
            code, _ = self._run(directory, write=False)
            self.assertEqual(code, 1, "an unnumbered file keeps the directory nonconforming")

    def test_crlf_files_keep_their_line_endings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-form-") as temp:
            directory = Path(temp)
            path = directory / "0001-a.md"
            path.write_bytes(b"# ADR-0001: A\r\n\r\n- Status: Accepted\r\n")
            form.run([directory], write=True)
            self.assertEqual(path.read_bytes(), b"# ADR 0001: A\r\n\r\n- Status: Accepted\r\n")


if __name__ == "__main__":
    unittest.main()
