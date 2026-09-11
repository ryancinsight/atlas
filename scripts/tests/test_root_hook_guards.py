"""Pin the root hook guards against silent removal.

`.githooks/pre-push` carries the pin-advance debt gate beside the coherence
report, and `.githooks/pre-commit` references the detector-parity rationale
that justifies its strict dead-link gate. Both were once dropped from the
working tree without a board item; these cases fail on that state.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRE_PUSH = ROOT / ".githooks" / "pre-push"
PRE_COMMIT = ROOT / ".githooks" / "pre-commit"


class RootHookGuardTests(unittest.TestCase):
    def test_pre_push_runs_the_pin_advance_debt_gate(self) -> None:
        text = PRE_PUSH.read_text(encoding="utf-8")
        self.assertIn("debt_gate()", text)
        self.assertIn("debt_gate || exit 1", text)

    def test_pre_commit_cites_the_detector_parity_rationale(self) -> None:
        text = PRE_COMMIT.read_text(encoding="utf-8")
        self.assertIn("docs/mdbook/detector-parity.md", text)
        self.assertNotIn("MDBOOK_DETECTOR_PARITY.md", text)


if __name__ == "__main__":
    unittest.main()
