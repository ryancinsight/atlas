<a id="atlas-process-tree-job-creation-001"></a>
# ATLAS-PROCESS-TREE-JOB-CREATION-001

priority: correctness
status: blocked
needs: none
scope: scripts/process_tree.py, scripts/windows_process.py, scripts/tests/test_windows_process.py
next step: reproduce caller death in the CreateProcess-to-AssignProcessToJobObject interval on Windows, then replace the `subprocess.Popen` launch with a `CreateProcessW` path using `PROC_THREAD_ATTRIBUTE_JOB_LIST`.
basis: f21829ead6a2a30e3af0a7174a1abd15e5f655ba

Acceptance: a caller death at any point after `CreateProcessW` returns leaves no
unowned root; the bounded integration test kills the caller across the creation
and assignment boundary and observes tree termination.

Blocker: the required kernel-level caller-death reproduction is unavailable on
the current host. Re-open when a Windows run can exercise that interval and
the bounded integration test proves termination.

Evidence: ADR 0067 records a 98–188 microsecond ownership gap because Python's
`subprocess.Popen` does not expose process creation attributes. The current
runner therefore cannot close this gap without changing its Windows launch
implementation.
