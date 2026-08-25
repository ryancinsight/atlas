"""Focused tests for the advisory board delivery audit."""

from __future__ import annotations

import importlib.util
import sys
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "atlas-board-delivery-audit.py"
SPEC = importlib.util.spec_from_file_location("atlas_board_delivery_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class BoardDeliveryAuditTests(unittest.TestCase):
    """Verify citation, ownership, and classification semantics."""

    def test_completed_items_extract_hashes_and_ignore_run_ids(self) -> None:
        items = MODULE.parse_board(
            textwrap.dedent(
                """
                ## ATLAS-HERMES-1 — Landed change — done

                Commit `abc1234`; hosted run `32451694923` passed.

                ## ATLAS-HERMES-2 — Open change — todo

                Commit `def5678`.
                """
            )
        )

        completed = MODULE.completed_items(items)

        self.assertEqual([item.item_id for item in completed], ["ATLAS-HERMES-1"])
        self.assertEqual(completed[0].hashes, ("abc1234",))

    def test_hash_extraction_does_not_slice_hex_word_fragments(self) -> None:
        item = MODULE.BoardItem(
            "ATLAS-HERMES-1",
            "landed",
            "done",
            "The verification step succeeded; commit `abc1234` landed.",
        )

        self.assertEqual(item.hashes, ("abc1234",))

    def test_member_paths_follow_gitmodules_registration(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitmodules").write_text(
                '[submodule "repos/hermes"]\n'
                "\tpath = repos/hermes\n",
                encoding="utf-8",
            )
            (root / "repos" / "hermes" / ".git").mkdir(parents=True)
            (root / "repos" / "leoneuro-rs" / ".git").mkdir(parents=True)

            members = MODULE.member_paths(root)

        self.assertEqual(set(members), {"hermes"})

    def test_candidates_use_explicit_repo_path_and_provider_id(self) -> None:
        members = {"hermes": Path("repos/hermes"), "coeus": Path("repos/coeus")}
        explicit = MODULE.BoardItem(
            "ATLAS-DELIVERY-1", "landed", "done", "repos/hermes at abc1234"
        )
        provider_id = MODULE.BoardItem("ATLAS-COEUS-1", "landed", "done", "abc1234")

        self.assertEqual(MODULE.candidate_names(explicit, members), {"hermes"})
        self.assertEqual(MODULE.candidate_names(provider_id, members), {"coeus"})

    def test_classification_prefers_default_branch_ancestry(self) -> None:
        self.assertEqual(
            MODULE.classify(ancestor=True, rewritten=False, remote_branches=[]),
            "delivered",
        )

    def test_classification_recognizes_rewritten_delivery(self) -> None:
        self.assertEqual(
            MODULE.classify(ancestor=False, rewritten=True, remote_branches=[]),
            "delivered-rewritten",
        )

    def test_classification_keeps_published_unmerged_distinct(self) -> None:
        self.assertEqual(
            MODULE.classify(
                ancestor=False,
                rewritten=False,
                remote_branches=["origin/fix/delivery"],
            ),
            "published-not-merged",
        )

    def test_missing_default_branch_is_unverifiable(self) -> None:
        self.assertEqual(
            MODULE.classify(ancestor=None, rewritten=False, remote_branches=[]),
            "unverifiable",
        )

    def test_default_ref_falls_back_to_master(self) -> None:
        with patch.object(
            MODULE,
            "run_git",
            side_effect=((1, ""), (1, ""), (0, "")),
        ):
            self.assertEqual(
                MODULE.default_ref(Path("repos/hephaestus")), "origin/master"
            )


if __name__ == "__main__":
    unittest.main()
