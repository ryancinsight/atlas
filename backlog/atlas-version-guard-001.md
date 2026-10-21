<a id="atlas-version-guard-001"></a>
## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — todo
- policy: git_discipline + architecture_scoping pin discipline. Incident `87ab265` (hermes) silently reverted a release version, stranding integrators ~10 hours — the motivating case for this guard.
- outcome: a per-repo CI guard on undeclared version/dependency changes plus a stack coherence check on first-party requirements, wired into member CI.
- next (sub-delivery 2, todo): wire the guard into each allowlisted member's CI on PRs/pushes touching its `*.toml`.
- acceptance: `87ab265` replay fails the guard; coherence check passes on current stack, fails on an injected backward-version fixture.
- reproduced 2026-10-21 at `c8a23496`: the name-only package index rejects independent repository-local `xtask` versions; a dependency targeting a provider without the named package can instead use another provider's package. The separate tool correction keys packages and dependency lookups by registered provider plus name, retaining same-provider conflicts and nearest-workspace declaration bases.
- bounded acceptance: [x] independent helper versions and source-specific path/Git aliases; [x] actual incompatible requirements still reported; [x] same-provider conflicting versions still rejected; [x] registry-only exclusion and no cross-provider fallback; [x] remote-tree and nested-workspace boundaries. See [tool contract and regression coverage](../tools/version-guard/README.md).
- remaining: the overall item stays todo. This tool correction does not repair PR #551's overlay/consumer requirement or lock drift, PR #559's missing overlay target, or the Hermes pin gap; those retain their separate ownership and qualification gates.
