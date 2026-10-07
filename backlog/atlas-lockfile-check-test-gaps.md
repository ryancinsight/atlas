<a id="atlas-lockfile-check-test-gaps"></a>
## ATLAS-LOCKFILE-CHECK-TEST-GAPS — Pin three behaviours of `--check` and `--regenerate` no test fails on [patch] — todo
- priority: verification
- outcome: each of three surviving mutants of `scripts/lockfile.py` is killed by a test that asserts the behaviour the code already has.
- evidence (basis: b2741da1b3d3, judge mutants K7, K8, K14 on atlas#476): K7, `disk_texts` returning 0 on an `OSError` instead of failing closed; K14, `regenerate` returning 0 without re-running `check()`, so a repair that leaves a nested stripped lock passes; K8, `os.walk(followlinks=True)`, so whether symlinked directories are judged is an untested choice (not following them is the defensible one).
- acceptance: the three mutants fail named tests: an unreadable file makes `--check` exit nonzero; `--regenerate` over a nested lock it cannot repair exits nonzero; a symlinked directory holding a flattened lock is not walked (skipped on a host that cannot create the link).
- scope: `scripts/lockfile.py`, `scripts/tests/test_lockfile_check.py`, `scripts/tests/test_lockfile_regenerate.py`.
- next step: add the three tests, then rerun the three mutants.
