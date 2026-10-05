<a id="atlas-process-tree-job-creation-001"></a>
# ATLAS-PROCESS-TREE-JOB-CREATION-001

priority: correctness
status: blocked
needs: none
scope: scripts/process_tree.py, scripts/windows_process.py, scripts/tests/test_windows_process.py
next step: reproduce caller death in the CreateProcess-to-AssignProcessToJobObject interval, then use `CreateProcessW` with `PROC_THREAD_ATTRIBUTE_JOB_LIST`.
basis: f21829ead6a2a30e3af0a7174a1abd15e5f655ba

Acceptance: the bounded Windows integration test kills the caller across the creation-to-assignment boundary and observes tree termination.

Blocker: kernel-level caller-death reproduction is unavailable on this host; re-open when a Windows run exercises the interval and proves termination.

Evidence: ADR 0067 records a 98–188 microsecond gap because `subprocess.Popen` does not expose process creation attributes.
