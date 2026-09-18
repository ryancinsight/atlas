<a id="atlas-version-guard-001"></a>
## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — in-progress (sub-delivery 1 done)

- policy: git_discipline + architecture_scoping pin discipline. Incident
  `87ab265` (hermes) silently reverted a release version, stranding
  integrators ~10 hours — the motivating case for this guard.
- outcome: a per-repo CI guard on undeclared version/dependency changes plus
  a stack coherence check on first-party requirements, wired into member CI.
- delivered: sub-delivery 1 (guard skeleton, `c70af8b`) and sub-delivery 3
  (coherence tool) — 235 manifests/215 packages/898 requirements/0 defects
  on the current stack.
- next (sub-delivery 2, todo): wire the guard into each allowlisted
  member's CI on PRs/pushes touching its `*.toml`.
- acceptance: `87ab265` replay fails the guard; coherence check passes on
  current stack, fails on an injected backward-version fixture.
