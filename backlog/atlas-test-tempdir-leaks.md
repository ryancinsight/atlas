<a id="atlas-test-tempdir-leaks"></a>
## ATLAS-TEST-TEMPDIR-LEAKS — Atlas Python tests leave temp directories behind [tightening] [patch] — todo
- priority: tightening
- outcome: no Atlas Python test leaves a directory under the OS temp directory after the suite ends, on success or failure.
- evidence: on 2026-10-03 `%TEMP%` held 1,060 `crlf-detector-*`, 158 `atlas-safety-census-repo-*` and 105 `atlas-gate-*` directories, the oldest from 2026-09-10; 1,236 were deleted by hand and 99 recent ones remain. Read at 3ea1f0629: `CrlfStoredBlobsTestCase._repo` (`test_atlas_conformance.py`) registers `shutil.rmtree(root, ignore_errors=True)`, which silently skips the read-only git object files Windows refuses to delete; `MainWalkTestCase._make_repo` (`test_safety_census.py`) calls `mkdtemp` and registers no cleanup. The `atlas-gate-*` leaks are partly traced: the ref-gate tests' `gate.kill()` kills only bash, the hook's children keep `push-1.txt` open, and Windows refuses the delete (fix in draft ryancinsight/atlas#460).
- oracle: every fixture creating a directory removes it on success and failure (`TemporaryDirectory` or `addCleanup`, with an `onexc` handler that clears the read-only bit for git objects, never `ignore_errors`); a test runs a fixture suite and asserts the set of prefixed temp directories is unchanged afterward.
- needs: none
- scope: scripts/tests/ (`test_atlas_conformance.py`, `test_safety_census.py`, `test_atlas_pre_push_gate.py`, and any other `mkdtemp` user: `git grep -n mkdtemp -- scripts/tests`)
- next: put one shared read-only-safe removal helper beside the test fixtures, convert the two traced leak sites to it, then sweep the remaining `mkdtemp` call sites; the `atlas-gate-*` process-tree half lands with #460.
- basis: 3ea1f062969718a419bceac2dca48d4437878513
