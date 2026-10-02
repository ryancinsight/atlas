<a id="atlas-identity-load-flakes"></a>
## ATLAS-IDENTITY-LOAD-FLAKES — Four identity tests fail under host load [patch] — todo
- Outcome: the build-identity suite passes with the stack's usual concurrent gates running, not only alone.
- Evidence (2026-10-01): at the ryancinsight/atlas#423 tree, a full `test_atlas_build_identity.py` + `test_atlas_pre_push_gate.py` run took 87 min and failed four tests that each pass alone: `test_a_fresh_gate_export_is_identified_without_rehashing_it` (fixture `git add` of 2,000 files exceeds its 30 s timeout), `test_the_wait_bound_covers_every_lease_of_a_run` (6.66 s against a 4.2 s bound), `test_a_reader_writing_new_variants_does_not_tear_another_readers_check` and `test_a_file_that_never_reads_the_same_twice_is_recorded_unverified` (count assertions). The first fails and passes alternately on origin/main 2c70152a5 run alone.
- Oracle: each test's bound is derived from the operation it measures, or the test synchronizes on events instead of wall time; ten consecutive full-suite runs beside a concurrent cargo build pass, and no test re-runs a failure.
- priority: verification
- needs: none
- scope: scripts/tests/test_atlas_build_identity.py
- Next step: profile the 2,000-file fixture's `git add` under load (Defender scan, index lock contention) and replace the fixed 30 s timeout with a derived budget or a smaller fixture that still exercises the no-rehash path.
