<a id="atlas-identity-suite-runtime"></a>
## ATLAS-IDENTITY-SUITE-RUNTIME — Five build-identity tests run for minutes against a 60 s budget [tightening] [patch] — todo
- priority: tightening
- outcome: every test in `scripts/tests/test_atlas_build_identity.py` fits the committed 30 s slow / 60 s terminate budget, unsimplified; a test crossing its bound by 3x to 6x of the 60 s bound is a slow component in the identity code or fixture construction, never a reason to shrink the workload or raise the bound.
- evidence: the full file at `-n 6` took 213 s, 416 s, 418 s, 863 s and 1580 s across the ryancinsight/atlas#444 judge and fix runs on 2026-10-02 and 2026-10-03, varying with host load. Slowest at `-n 6` before #444: `MultiPackageRunTestCase.test_steps_of_one_selection_share_their_records` 347.52 s, `SharedCommandKeyThreeStepTestCase.test_the_three_steps_share_one_record_across_pushes` 324.68 s, `CrossRepositoryPathDependencyTestCase.test_a_feature_moved_in_a_dependency_manifest_cleans_every_path_package` 192.31 s, `GitDependencyTestCase.test_an_edited_checkout_cleans_its_package_until_restored` 187.92 s, `SharedCommandKeyThreeStepTestCase.test_a_rustflags_change_is_still_detected_under_the_shared_key` 187.35 s.
- oracle: each named test passes alone and at `-n 6` inside 30 s, with its assertions and fixtures unchanged in what they cover; `pytest.ini` carries no per-test timeout today, so the run records durations (`--durations=20`) before and after.
- needs: none
- scope: scripts/tests/test_atlas_build_identity.py, scripts/atlas_build_identity.py, scripts/atlas_build_inputs.py, scripts/atlas_build_snapshot.py, scripts/atlas_build_stamps.py
- next: run each named test alone with `cProfile` or per-step timestamps and attribute the time to real `cargo` builds of fixture crates, repeated cold builds, shared-target contention, or per-step identity hashing; fix the dominant component first.
- links: ryancinsight/atlas#444 (merged; bounded the load-sensitive tests by events, left runtime), [ATLAS-IDENTITY-LEASE-STARVATION](atlas-identity-lease-starvation.md) (gate wall time under fleet load).
- basis: 3ea1f062969718a419bceac2dca48d4437878513
