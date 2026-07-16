# Atlas gap audit

## META-001 — public default-branch alignment

- Evidence tier: Git object identity. The integration lane resolves each public
  submodule's `refs/remotes/origin/HEAD` after fetch and compares it directly
  with the Atlas gitlink.
- Initial finding: twelve public gitlinks lagged their resolved default branch;
  `apollo` and `consus` already matched.
- Conflict scan: no unmerged index entries and no exact Git conflict markers
  were present in the Atlas checkout during the audit.
- Residual risk: mutable peer worktrees remain outside this clean meta lane and
  are intentionally not modified by META-001.

## META-002 — concurrent Apollo advance

- Evidence tier: Git object identity. Apollo merged its provider-boundary PR
  after META-001's fetch and before the Atlas merge; the merged Atlas gitlink
  therefore referenced Apollo `e17de6f` while fetched `origin/HEAD` resolved to
  `466e18b`.
- Full follow-up comparison found no other public gitlink drift.

## META-003 — stale branch replacement

- Evidence tier: Git merge-tree and manifest inspection. Legacy Atlas PR #1
  conflicts in `README.md`, every coordination artifact, and eight gitlinks;
  its provider descriptions predate the current default branches.
- Resolution: register the current Kwavers and Helios defaults in a clean
  successor branch, retain the shared build-artifact policy, and exclude its
  obsolete Python codemod and stale provider descriptions.
