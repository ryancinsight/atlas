"""Tests for `scripts/atlas-board-index.py`, the generator of the backlog index."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-board-index.py"
_SPEC = importlib.util.spec_from_file_location("atlas_board_index", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_index = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _index
_SPEC.loader.exec_module(_index)

ITEM = '<a id="atlas-one"></a>\n## ATLAS-ONE — The first item [patch] — todo\n- Outcome: one.\n'
PREAMBLE = "# atlas — backlog\n<!-- policy -->\n"
INDEX = '<a id="atlas-one"></a>- [ATLAS-ONE](backlog/atlas-one.md) — The first item [patch] — todo\n'


class BoardIndexTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-board-index-")
        self.root = Path(self._tmp.name)
        (self.root / "backlog").mkdir()
        (self.root / "backlog" / "atlas-one.md").write_bytes(ITEM.encode("utf-8"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def board(self, text: str) -> Path:
        path = self.root / "backlog.md"
        path.write_bytes(text.encode("utf-8"))
        return path

    def run_index(self, mode: str) -> tuple[int, str]:
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
            code = _index.main([mode, str(self.root)])
        return code, errors.getvalue()

    def test_generate_writes_one_line_per_item_and_check_then_agrees(self) -> None:
        path = self.board(PREAMBLE)
        self.assertEqual(self.run_index("generate"), (0, ""))
        self.assertEqual(path.read_bytes().decode("utf-8"), PREAMBLE + "\n" + INDEX)
        self.assertEqual(self.run_index("check"), (0, ""))

    def test_a_preamble_line_repeating_an_index_anchor_refuses_both_modes(self) -> None:
        # A separator re-encoded as cp1252 mojibake no longer matches the index
        # pattern, so the line falls into the preamble with the same anchor.
        stale = INDEX.replace("—", "â€”")
        text = PREAMBLE + stale + "\n" + INDEX
        path = self.board(text)
        for mode in ("generate", "check"):
            code, errors = self.run_index(mode)
            self.assertEqual(code, 1, mode)
            self.assertIn("line 3 atlas-one", errors, mode)
        self.assertEqual(path.read_bytes().decode("utf-8"), text)

    def test_a_preamble_anchor_no_item_owns_is_kept(self) -> None:
        preamble = PREAMBLE + '<a id="board-policy"></a>\n'
        path = self.board(preamble)
        self.assertEqual(self.run_index("generate"), (0, ""))
        self.assertEqual(path.read_bytes().decode("utf-8"), preamble + "\n" + INDEX)


if __name__ == "__main__":
    unittest.main()
