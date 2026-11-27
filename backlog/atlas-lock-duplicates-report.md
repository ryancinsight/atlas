<a id="atlas-lock-duplicates-report"></a>
## ATLAS-LOCK-DUPLICATES-REPORT — No command reports crate versions duplicated across member locks [verification] [patch] — todo
- outcome: one command reads each registered member's root `Cargo.lock` through the shared parser and prints each crate pinned at more than one version with the members on each.
- evidence (origin/main b334401f2fcf): `scripts/atlas-lock-duplicates.py` does not exist; `refs/pull/784/head` holds it (220 lines) and its test (157 lines, 7 tests).
- oracle: `python -m pytest scripts/tests/test_atlas_lock_duplicates.py -q` exits 0 (4 today); the tests assert one row per duplicated crate naming each version's members, none for a shared version, a missing lock skipped,
  an unparseable lock an error naming its member, `--json` rows, and `--fail-on-duplicates` exit 2.
- basis: b334401f2fcf; priority: verification; needs: none; scope: `scripts/atlas-lock-duplicates.py` and its test; next step: port the held files, run once over the registered locks, file each row.
