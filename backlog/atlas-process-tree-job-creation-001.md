<a id="atlas-process-tree-job-creation-001"></a>
## ATLAS-PROCESS-TREE-JOB-CREATION-001 — Close the caller-death gap before job assignment [correctness] — blocked
- priority: correctness
- outcome: a killed caller leaves no surviving process tree: creation and job assignment are atomic with respect to the parent's death.
- evidence: ADR 0067 records a 98–188 microsecond gap because `subprocess.Popen` does not expose process creation attributes.
- scope: scripts/process_tree.py, scripts/windows_process.py, scripts/tests/test_windows_process.py
- next: reproduce caller death in the CreateProcess-to-AssignProcessToJobObject interval, then use `CreateProcessW` with `PROC_THREAD_ATTRIBUTE_JOB_LIST`.
- needs: none
- basis: f21829ead6a2a30e3af0a7174a1abd15e5f655ba

Acceptance: the bounded Windows integration test kills the caller across the creation-to-assignment boundary and observes tree termination.

Blocker: kernel-level caller-death reproduction is unavailable on this host; re-open when a Windows run exercises the interval and proves termination.

Evidence: ADR 0067 records a 98–188 microsecond gap because `subprocess.Popen` does not expose process creation attributes.
