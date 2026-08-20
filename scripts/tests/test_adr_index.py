#!/usr/bin/env python3
"""Regression tests for the Atlas ADR index generator."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "adr-index.py"
SPEC = importlib.util.spec_from_file_location("atlas_adr_index", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
adr_index = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adr_index
SPEC.loader.exec_module(adr_index)


class AdrIndexTestCase(unittest.TestCase):
    def test_navigation_index_is_not_parsed_as_an_adr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-adr-index-") as temp:
            directory = Path(temp)
            (directory / "INDEX.md").write_text(
                "# Navigation index\n\nThis is not an ADR.\n", encoding="utf-8"
            )
            (directory / "README.md").write_text("# Generated index\n", encoding="utf-8")
            (directory / "0001-example.md").write_text(
                "# ADR 0001: Example\n\nStatus: Accepted\n", encoding="utf-8"
            )

            content, anomalies = adr_index.build_index(directory)

        self.assertEqual(anomalies, [])
        self.assertIn("0001-example.md", content)
        self.assertNotIn("INDEX.md", content)

    def test_untracked_adr_is_flagged_and_kept_out_of_the_index(self) -> None:
        """An index entry must be satisfiable by a fresh clone, not by the
        author's disk.

        ADR 0045 was deleted from `HEAD` twice by unrelated commits while
        staying on disk untracked, and this gate reported the index clean
        both times — so CI was green over a dead link.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-adr-index-") as temp:
            directory = Path(temp)
            for name in ("0001-tracked.md", "0002-untracked.md"):
                (directory / name).write_text(
                    f"# ADR {name[:4]}: Example\n\nStatus: Accepted\n",
                    encoding="utf-8",
                )
            ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
            for argv in (
                ["init", "-q"],
                [*ident, "add", "0001-tracked.md"],
                # Committed, not merely staged: the check reads HEAD, because
                # that is what a fresh clone receives. An entry present in the
                # index but not in HEAD does not reach a reader.
                [*ident, "commit", "-q", "-m", "tracked"],
            ):
                subprocess.run(["git", "-C", str(directory), *argv], check=True)

            content, anomalies = adr_index.build_index(directory)

        self.assertIn("0002-untracked.md", " ".join(anomalies))
        self.assertNotIn("0002-untracked.md", content)
        self.assertIn("0001-tracked.md", content)

    def test_check_fails_when_index_matches_but_adr_is_untracked(self) -> None:
        """A clean index must not hide an ADR missing from ``HEAD``."""
        with tempfile.TemporaryDirectory(prefix="atlas-adr-index-") as temp:
            directory = Path(temp)
            (directory / "0001-tracked.md").write_text(
                "# ADR 0001: Example\n\nStatus: Accepted\n", encoding="utf-8"
            )
            (directory / "0002-untracked.md").write_text(
                "# ADR 0002: Example\n\nStatus: Accepted\n", encoding="utf-8"
            )
            ident = ["-c", "user.email=t@t", "-c", "user.name=t"]
            for argv in (
                ["init", "-q"],
                [*ident, "add", "0001-tracked.md"],
                [*ident, "commit", "-q", "-m", "tracked"],
            ):
                subprocess.run(["git", "-C", str(directory), *argv], check=True)
            content, _ = adr_index.build_index(directory)
            (directory / "README.md").write_text(content, encoding="utf-8")

            result = adr_index.check_indexes([directory], "check")

        self.assertEqual(result, 1)

    def test_a_non_git_directory_falls_back_to_the_on_disk_view(self) -> None:
        """Outside a repository — an unpacked tarball — every ADR would
        otherwise report as untracked, which is noise rather than a finding.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-adr-index-") as temp:
            directory = Path(temp)
            (directory / "0001-example.md").write_text(
                "# ADR 0001: Example\n\nStatus: Accepted\n", encoding="utf-8"
            )
            self.assertIsNone(adr_index.tracked_markdown(Path(temp) / "nonexistent"))
            content, anomalies = adr_index.build_index(directory)

        self.assertNotIn("untracked", " ".join(anomalies))
        self.assertIn("0001-example.md", content)


if __name__ == "__main__":
    unittest.main()
