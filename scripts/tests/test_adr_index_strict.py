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
