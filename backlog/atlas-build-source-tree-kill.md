<a id="atlas-build-source-tree-kill"></a>
## ATLAS-BUILD-SOURCE-TREE-KILL — End build-identity commands as a process tree [patch] — todo
- Outcome: `scripts/atlas_build_source.py` runs `git` and `rustc` through `atlas_git_process.execute_process`, so a command that outlives its 60 s deadline is ended with its descendants.
- Evidence: `_git` and `toolchain_identity` call `subprocess.run(timeout=60)`, which ends only the direct child on Windows; `communicate()` then blocks on any descendant holding the pipes (a 45 s child returned after 50.5 s against a 3 s deadline, measured on the `cargo metadata` call fixed in ryancinsight/atlas#461).
- Oracle: a real-process test puts a fake command whose child outlives the deadline on the call; it returns within the deadline plus a derived teardown margin and the child stops, as `TreeDeadlineTestCase` does for `run()` and `_cargo_outside`. `test_atlas_build_identity.py` passes unchanged.
- priority: correctness
- needs: none
- scope: scripts/atlas_build_source.py, scripts/tests/test_atlas_build_identity.py
- Next step: replace both `subprocess.run` calls with `execute`/`execute_process`, keep `BuildIdentityError` as the failure type, and update the tests that patch `build_source.subprocess.run`.
