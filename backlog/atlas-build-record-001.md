<a id="atlas-build-record-001"></a>
## ATLAS-BUILD-RECORD-001 — Validate shared build identity records [patch] — todo
- outcome: shared-cache builds persist and validate the exact source, dependency, artifact, and process-boundary state used to produce them.
- acceptance: a local Git dependency build writes a record and matches on an unchanged checkout; changing a tracked checkout-root input outside the package directory makes the next check stale; Git records validate source identity, registry records validate content digests, and versions 1–5 are stale.
- priority: correctness
- needs: none
- scope: `scripts/atlas_build_*.py`, `scripts/atlas_git_process.py`, `scripts/tests/test_atlas_build_*.py`, `scripts/tests/test_atlas_git_process.py`, `scripts/tests/test_root_hook_guards.py`, ADR 0064, `gap_audit.md`, `backlog.md`.
- next: close the record schema mismatch and fixture failures, then verify the full source/target/lease/process workflow against the exact PR tree.
- verification: focused build-identity and process tests, the full Python suite, pre-push gate, conformance, ARCH-008 oracle, and pin-drift gate.
- basis: 745f66ffb099d1dd9f829dc248bf5dc526362cd2
