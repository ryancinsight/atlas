#!/usr/bin/env python3
"""Tests for adr-index.py's `--directory` and `--strict` options.

`--directory` lets a member's own CI run the atlas generator against its
checkout through the shared guard; `--strict` adds the two checks the member
copies (apollo, kwavers, hermes) carried and the umbrella did not: a canonical
heading form and heading/filename number agreement. Strictness is opt-in
because twelve members do not conform yet, so the permissive default must be
provably unchanged by these additions.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "adr-index.py"
SPEC = importlib.util.spec_from_file_location("atlas_adr_index_strict", SCRIPT)
adr_index = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = adr_index
SPEC.loader.exec_module(adr_index)


def _write(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(text, encoding="utf-8", newline="\n")


CANONICAL = "# ADR 0001: Canonical heading\n\n## Status\n\nAccepted\n"
DASH_FORM = "# 0002 — Dash form heading\n\n- **Status:** Proposed\n"
BARE_TITLE = "# A heading with no number\n\n## Status\n\nAccepted\n"
MISMATCH = "# ADR 0009: Number disagrees with filename\n\n## Status\n\nAccepted\n"


class StrictModeTests(unittest.TestCase):
    def test_permissive_default_is_unchanged_by_the_strict_option(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-strict-") as temp:
            directory = Path(temp)
            _write(directory, "0001-canonical.md", CANONICAL)
            _write(directory, "0003-bare.md", BARE_TITLE)
            _write(directory, "0004-mismatch.md", MISMATCH)
            _, anomalies = adr_index.build_index(directory)
        self.assertEqual(anomalies, [], "permissive mode must accept every heading form")

    def test_strict_accepts_both_canonical_heading_forms(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-strict-") as temp:
            directory = Path(temp)
            _write(directory, "0001-canonical.md", CANONICAL)
            _write(directory, "0002-dash.md", DASH_FORM)
            _, anomalies = adr_index.build_index(directory, strict=True)
        self.assertEqual(anomalies, [])

    def test_strict_flags_a_bare_title(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-strict-") as temp:
            directory = Path(temp)
            _write(directory, "0003-bare.md", BARE_TITLE)
            _, anomalies = adr_index.build_index(directory, strict=True)
        self.assertEqual(anomalies, ["missing canonical ADR heading: 0003-bare.md"])

    def test_strict_flags_a_heading_number_that_disagrees_with_the_filename(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-strict-") as temp:
            directory = Path(temp)
            _write(directory, "0004-mismatch.md", MISMATCH)
            _, anomalies = adr_index.build_index(directory, strict=True)
        self.assertEqual(
            anomalies,
            ["heading number 0009 does not match filename 0004: 0004-mismatch.md"],
        )

    def test_three_digit_numbering_is_canonical_too(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-strict-") as temp:
            directory = Path(temp)
            _write(directory, "001-three.md", "# ADR 001: Three digits\n\n## Status\n\nAccepted\n")
            _, anomalies = adr_index.build_index(directory, strict=True)
        self.assertEqual(anomalies, [])


class TitleRenderingTests(unittest.TestCase):
    """The index has a number column; the title column must not repeat the number,
    whichever heading form carried it. Dash and dot forms once rendered as
    `0037 — Title` and `106. Title`, which read as drift against the members'
    own generators."""

    def _title(self, name: str, heading: str) -> str:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-title-") as temp:
            directory = Path(temp)
            _write(directory, name, heading + "\n\n## Status\n\nAccepted\n")
            content, _ = adr_index.build_index(directory)
        row = [line for line in content.splitlines() if line.startswith("| [")][0]
        return row.split(" | ")[1]

    def test_colon_form_strips_the_number(self) -> None:
        self.assertEqual(self._title("0001-a.md", "# ADR 0001: Colon form"), "Colon form")

    def test_dash_form_strips_the_own_number(self) -> None:
        self.assertEqual(self._title("0037-b.md", "# 0037 — Dash form"), "Dash form")

    def test_dot_form_strips_the_own_number(self) -> None:
        self.assertEqual(self._title("106-c.md", "# 106. Dot form"), "Dot form")

    def test_a_bare_title_is_kept_whole(self) -> None:
        self.assertEqual(
            self._title("0003-d.md", "# 3D transforms are titles, not numbers"),
            "3D transforms are titles, not numbers",
        )

    def test_leading_digits_that_are_not_the_own_number_are_title(self) -> None:
        # `1-D` is a title, not a number prefix: the ADR's number is 0005.
        self.assertEqual(self._title("0005-e.md", "# 1-D interpolation on a 2-D grid"), "1-D interpolation on a 2-D grid")


class HeaderProvenanceTests(unittest.TestCase):
    """The header is provenance prose; the table is the index."""

    OLD_HEADER = (
        "# ADR index\n\n<!-- Generated by scripts/adr-index.py — do not hand-edit.\n"
        "     Regenerate:  python scripts/adr-index.py generate\n"
        "     Check:       python scripts/adr-index.py check -->\n\n"
    )

    def test_generate_names_atlas_and_the_guard(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-header-") as temp:
            directory = Path(temp)
            _write(directory, "0001-canonical.md", CANONICAL)
            content, _ = adr_index.build_index(directory)
        self.assertIn("atlas scripts/adr-index.py", content)
        self.assertIn("adr-index-guard.yml", content)
        self.assertIn("--directory <this repo>/docs/adr", content)

    def test_an_index_with_the_old_header_and_a_current_table_passes_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-header-") as temp:
            directory = Path(temp)
            _write(directory, "0001-canonical.md", CANONICAL)
            content, _ = adr_index.build_index(directory)
            _write(directory, "README.md", self.OLD_HEADER + adr_index.index_body(content).split("\n\n", 2)[-1])
            check = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--directory", str(directory)],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            # A drifted table still fails whatever the header says.
            index = directory / "README.md"
            index.write_text(index.read_text(encoding="utf-8").replace("Accepted", "Proposed"), encoding="utf-8")
            drifted = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--directory", str(directory)],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(drifted.returncode, 0)

    def test_index_body_strips_exactly_the_provenance_comment(self) -> None:
        self.assertEqual(adr_index.index_body("# x\n\n<!-- a\n b -->\n\n| t |\n"), "# x\n\n\n\n| t |\n")
        self.assertEqual(adr_index.index_body("no comment\n"), "no comment\n")


class DirectoryOptionTests(unittest.TestCase):
    def test_directory_option_indexes_only_the_named_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-dir-") as temp:
            directory = Path(temp)
            _write(directory, "0001-canonical.md", CANONICAL)
            generate = subprocess.run(
                [sys.executable, str(SCRIPT), "generate", "--directory", str(directory)],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(generate.returncode, 0, generate.stdout + generate.stderr)
            self.assertTrue((directory / "README.md").is_file())
            check = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--directory", str(directory), "--strict"],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            # Desynchronise the index: the check must bite.
            index = directory / "README.md"
            index.write_text(index.read_text(encoding="utf-8").replace("Accepted", "Proposed"), encoding="utf-8")
            desynced = subprocess.run(
                [sys.executable, str(SCRIPT), "check", "--directory", str(directory)],
                capture_output=True, encoding="utf-8", errors="replace",
            )
            self.assertNotEqual(desynced.returncode, 0, "a drifted index must fail the check")

    def test_a_missing_directory_is_an_error_not_an_empty_success(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "check", "--directory", "/definitely/not/here"],
            capture_output=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
