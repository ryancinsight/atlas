# Atlas checklist

Sprint phase: Closure
Target: META-001 and META-002 public default-branch alignment

## META-001

- [x] Create a clean integration lane from `origin/main`.
- [x] Fetch and resolve each public submodule's remote default branch.
- [x] Stage only gitlinks that lag their resolved default branch.
- [x] Verify staged gitlinks, whitespace, and conflict-marker absence.
- [x] Commit, push, review, and merge the integration lane.

## META-002

- [x] Detect the post-merge Apollo default-branch advance.
- [x] Create a follow-up lane from the merged Atlas default branch.
- [x] Advance the Apollo gitlink and re-verify every public gitlink.

## META-003

- [x] Audit the conflicting legacy Atlas PR and retain only evidence-current scope.
- [x] Register Kwavers and Helios and re-verify the complete public roster.
- [x] Enforce the cross-stack test-runner contract and validate both drivers.
