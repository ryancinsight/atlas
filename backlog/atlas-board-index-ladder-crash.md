<a id="atlas-board-index-ladder-crash"></a>
## ATLAS-BOARD-INDEX-LADDER-CRASH — The board index tool aborts on the milestone ladder file [patch] — todo
- Outcome: `scripts/atlas-board-index.py` `check` and `generate` never end in a traceback: `backlog/milestones.md` is skipped as a ladder, and any other per-item file without a `## ` heading is reported as a `BoardIndexError` naming its path.
- Evidence (origin/main 12708acf3ae4892d4443627f0d6d5016ddeb29d7; `python scripts/atlas-board-index.py check <archive of the member's backlog.md and backlog/>`, exit 1): `item_fields_from_file` raises `ValueError: ... no '## ' heading found` (line 96), which `main` does not catch because it catches only `BoardIndexError`. Reproduced on mnemosyne e05b61001 (`backlog/milestones.md`), leto a1568745 (`backlog/leto-spmv-finite-range-20261020.md`, whose heading is `# `, then `backlog/milestones.md`) and the head of hermes#282 (closed).
- No atlas workflow or hook runs `check` (`git grep board-index -- .github scripts/git-hooks .githooks Makefile` is empty), so the crash shows only when a member runs it by hand.
- Oracle: tests in `scripts/tests/test_atlas_board_index.py`: a tree with a ladder file `backlog/milestones.md` (no `## `) checks and generates with exit 0 and no index line for it; a tree with a per-item file lacking `## ` exits 1 with that path on stderr and no traceback.
- basis: 12708acf3ae4892d4443627f0d6d5016ddeb29d7; priority: verification; needs: none
- scope: `scripts/atlas-board-index.py`, `scripts/atlas_board_items.py`, `scripts/tests/test_atlas_board_index.py`
- Next step: write the two failing tests, then convert `ValueError` into `BoardIndexError` and skip the ladder file by name.
