# ATLAS-PUB-EXPLICIT-COHORT-001 — Exact release cohorts [minor]

- status: todo
- priority: P1
- basis: RITK PR836's release preflight selects 29 owned unpublished versions,
  including unrelated dependency-free ritk-wgpu-compat0.2.1, which independently
  passes package verification. Main's publisher has no bounded plan input.
- correction: optional exact package/version JSON cohort through plan, publish
  and tag. Explicit `{}` is unarmed; malformed/duplicate/null maps, unknown or
  private names, changed versions and unexpected planned names fail closed.
  A held selected package never falls back to an unrelated ready package.
- invariants: retain package verification, SemVer, ownership, first-upload,
  least-privilege environment/token scopes, retries and time limits.
- tests: current-main regressions fail before implementation; value-level
  scope/identity and no-side-effect assertions, real CLI empty-cohort execution,
  shell argument forwarding, unchanged legacy behavior and workflow guards.
- installation: shared Atlas workflow remains workflow_call-only. Member
  adoption must pin reviewed code with explicit `{}` before arming a coherent
  graph; inspect older in-flight publishers. No member workflow is changed or
  dispatched by this draft. Atlas #540 owns SemVer work in the same workflow;
  source pins require reconciliation before integration, without editing its
  branch. PR503 is a preservation rescue, not a release-selection implementation.
- RITK: keep PR836 unmerged. Its finite-inverse code/tests must be carried into
  the provider plan's spatial0.5.0 boundary; do not publish the older0.4.1 graph.
- next: independent review, final source-pin/gate checks, and separate unarmed
  caller adoption only after owner/pin reconciliation. Provider factory/version
  decisions and raster first-upload authentication remain separate blockers.
