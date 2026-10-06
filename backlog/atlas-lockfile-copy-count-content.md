<a id="atlas-lockfile-copy-count-content"></a>
## ATLAS-LOCKFILE-COPY-COUNT-CONTENT — Count member lockfile checkers by content, not by path [patch] — todo
- priority: verification
- outcome: the conformance class `member_lockfile_copies` counts a member's lockfile checker wherever it sits, so moving `scripts/lockfile.py` does not lower the ratchet and only deleting it does.
- evidence (basis: b2741da1b3d3, judge verdict on atlas#476): `scripts/atlas-conformance.py:2121` is `int((repo / "scripts" / "lockfile.py").is_file())`. The class comment says a copy moved elsewhere reads 0, which satisfies the baseline while the copy still exists.
- acceptance: a fixture member whose checker was moved to another directory, and one whose copy was renamed, each count 1; a member with none counts 0; the committed baseline rows are unchanged at the 28 recorded gitlinks.
- needs: ATLAS-LOCKFILE-CHECKER-SINGLE-SOURCE is the consumer that lowers the count; this item can land before it.
- scope: `scripts/atlas-conformance.py`, `scripts/tests/test_atlas_conformance.py`.
- next step: key the count on content that identifies the checker (its `--check-staged` entry point and the standalone-lock rule's functions) over the member's tracked `.py` files, and compare against the baseline rows.
