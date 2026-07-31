#!/usr/bin/env python3
"""Regression tests for the detector smoke-test fixture.

The fixture in parity_artefacts/smoke_test_filters is designed to exercise
both false-positive filters (single-char href and LaTeX math href).  Running
the link checker over it must produce no bad links.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest.mock import patch

import check_mdbook_links as cml


REPO_ROOT = Path(__file__).resolve().parents[2]


class SmokeFixtureTestCase(unittest.TestCase):
    @staticmethod
    def _missing(fixture_dir) -> list:
        """Broken file links for `fixture_dir`.

        `check_book` now takes an explicit book name and returns a report
        dict; broken file links are `(origin, href, resolved, marker)`
        tuples under `file_missing`.
        """
        return cml.check_book(str(fixture_dir), "smoke_test_filters")["file_missing"]

    def test_smoke_test_filters_has_no_broken_links(self) -> None:
        """The consolidated smoke-test fixture must report zero bad links."""
        fixture_dir = REPO_ROOT / "parity_artefacts" / "smoke_test_filters"
        self.assertEqual(self._missing(fixture_dir), [])

    def test_smoke_fixture_produces_bad_links_when_filters_disabled(self) -> None:
        """Disabling the false-positive filters reveals the phantom bad links."""
        fixture_dir = REPO_ROOT / "parity_artefacts" / "smoke_test_filters"
        never_match = re.compile(r"^$")  # matches only empty strings → never matches fixture hrefs
        with (
            patch.object(cml, "SINGLE_CHAR_HREF_RE", never_match),
            patch.object(cml, "LATEX_HREF_RE", never_match),
        ):
            bad_links = self._missing(fixture_dir)

        self.assertTrue(bad_links, "expected phantom bad links when filters are disabled")
        targets = {href for _origin, href, _resolved, _marker in bad_links}
        # The fixture deliberately exercises single-character and LaTeX hrefs.
        single_char_targets = {t for t in targets if len(t) == 1 and t.isalpha()}
        latex_targets = {t for t in targets if t.startswith("\\")}
        self.assertTrue(single_char_targets, "expected single-char href false positives")
        self.assertTrue(latex_targets, "expected LaTeX href false positives")
        # The fixture deliberately exercises 6 single-char recurrence patterns
        # and 8 LaTeX-command math patterns.  We only need to prove the filters
        # are the reason the fixture passes, so a conservative lower bound is
        # enough to avoid passing on a single coincidental match.
        self.assertGreaterEqual(len(bad_links), 6)


if __name__ == "__main__":
    unittest.main()
