#!/usr/bin/env python3
"""Tests for atlas-board-compact.py archive preservation.

The compaction script must preserve an existing `## Archive — closed items`
section's body verbatim across successive runs. Without this property, a
second invocation rolls the prior archive's many one-line entries into a
single `(unnumbered) Archive` line and loses the per-item navigability
the AGENTS compaction rule is meant to preserve.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-board-compact.py"
_SPEC = importlib.util.spec_from_file_location("atlas_board_compact", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_compact = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _compact
_SPEC.loader.exec_module(_compact)


ARCHIVE_HEADING = "## Archive — closed items"


def _fixture(prior_archive: str) -> str:
    """A minimal backlog with one live item and a populated archive."""
    return textwrap.dedent(
        f"""\
        # atlas — backlog

        ## ATLAS-LIVE-001 — active work [patch] — in-progress

        - Some live prose.

        {ARCHIVE_HEADING}

        Closed items, one line each. Full prose is in git history; commit
        SHAs below are the entry points.

        {prior_archive}
        """
    )


class ArchivePreservationTestCase(unittest.TestCase):
    def test_prior_archive_body_is_preserved_verbatim(self) -> None:
        prior = (
            "- **ATLAS-OLD-001** item one [patch] (2026-08-01) — `aaaaaaa`\n"
            "- **ATLAS-OLD-002** item two [minor] (2026-08-02) — `bbbbbbb`, `ccccccc`\n"
        )
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            path = Path(root) / "backlog.md"
            path.write_text(_fixture(prior), encoding="utf-8")
            _compact.compact(path, ARCHIVE_HEADING)
            text = path.read_text(encoding="utf-8")
            self.assertIn("- **ATLAS-OLD-001** item one [patch]", text)
            self.assertIn("- **ATLAS-OLD-002** item two [minor]", text)
            # SHAs must survive intact
            self.assertIn("`aaaaaaa`", text)
            self.assertIn("`bbbbbbb`", text)
            self.assertIn("`ccccccc`", text)

    def test_second_run_is_idempotent(self) -> None:
        prior = "- **ATLAS-OLD-001** item [patch] (2026-08-01) — `aaaaaaa`\n"
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            path = Path(root) / "backlog.md"
            path.write_text(_fixture(prior), encoding="utf-8")
            _compact.compact(path, ARCHIVE_HEADING)
            first = path.read_text(encoding="utf-8")
            _compact.compact(path, ARCHIVE_HEADING)
            second = path.read_text(encoding="utf-8")
            self.assertEqual(first, second, "second run must not accumulate padding")

    def test_required_audit_record_survives_compaction(self) -> None:
        """The provider-integration audit requires
        `ATLAS-PROVIDER-INTEGRATION-AUDIT-001` in both root records; the
        archive-preservation rule is what keeps it intact across runs."""
        prior = (
            "- **ATLAS-PROVIDER-INTEGRATION-AUDIT-001** twenty-one provider "
            "audit (closed 2026-08-16) — `2918e5a`, `182083f1aa95ad30`\n"
        )
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            path = Path(root) / "checklist.md"
            text = (
                "# atlas — checklist\n\n"
                "## ATLAS-LIVE-001 — active work [patch] — in-progress\n\n"
                "- Some live prose.\n\n"
                "## Archive — closed checklists\n\n"
                "Closed items, one line each. Full prose is in git history.\n\n"
                f"{prior}"
            )
            path.write_text(text, encoding="utf-8")
            _compact.compact(path, "## Archive — closed checklists")
            out = path.read_text(encoding="utf-8")
            self.assertIn("ATLAS-PROVIDER-INTEGRATION-AUDIT-001", out)
            self.assertIn("`2918e5a`", out)
            self.assertIn("`182083f1aa95ad30`", out)

    def test_freshly_classified_closed_item_is_archived(self) -> None:
        """When a previously-live item becomes closed, it must enter the
        archive; the prior archive's items stay in place."""
        text = textwrap.dedent(
            f"""\
            # atlas — backlog

            ## ATLAS-NEWLY-CLOSED-001 — done thing [patch] — done 2026-08-21

            - body
            """
        )
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            path = Path(root) / "backlog.md"
            path.write_text(text, encoding="utf-8")
            _compact.compact(path, ARCHIVE_HEADING)
            out = path.read_text(encoding="utf-8")
            self.assertIn("**ATLAS-NEWLY-CLOSED-001**", out)
            self.assertIn("done thing", out)

    def test_idempotent_on_archive_with_many_items(self) -> None:
        prior_lines = "\n".join(
            f"- **ATLAS-OLD-{i:03d}** old item {i} [patch] (2026-08-01) — `{i:07x}`"
            for i in range(50)
        )
        prior = prior_lines + "\n"
        with tempfile.TemporaryDirectory(prefix="atlas-compact-") as root:
            path = Path(root) / "backlog.md"
            path.write_text(_fixture(prior), encoding="utf-8")
            _compact.compact(path, ARCHIVE_HEADING)
            first = path.read_text(encoding="utf-8")
            for _ in range(3):
                _compact.compact(path, ARCHIVE_HEADING)
            final = path.read_text(encoding="utf-8")
            self.assertEqual(first, final)


if __name__ == "__main__":
    unittest.main()
