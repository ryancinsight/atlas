<a id="atlas-python-wheel-attestation-context"></a>
## ATLAS-PYTHON-WHEEL-ATTESTATION-CONTEXT — Preserve read-only wheel verification [patch] — blocked

- priority: correctness; status: blocked; owner: Codex.
- scope: shared `python-wheels.yml`, its behavioral workflow tests and Leto's
  immutable recipe pin; no token/access changes or unrelated caller migrations.
- basis: independent review of [Leto #365](https://github.com/ryancinsight/leto/pull/365)
  found unconditional attestation after otherwise valid verification. Standard
  fork/Dependabot contexts lack the required OIDC/attestation write credentials.
- implementation: classify the original actor/event/head repository after all
  build/value/source validation and artifact upload. Skip attestation only for
  unprivileged verification; require a trusted context for release attestation.
- evidence: four new regression tests fail against the original workflow;
  all 16 workflow tests pass after repair, including 12 executions of the actual
  shell step without GitHub/OIDC credentials. No live fork PR was created.
- preserved: permission declarations, all platform/interpreter rows, value and
  source validation, release attachment guard and existing time limits.
- related: [Python wheel floor follow-up](atlas-python-wheels-floor.md) remains
  separate; its broader floor/permission work is not marked complete here.

- [x] Reproduce the missing guard and pass original plus new local regressions.
- [ ] Pass workflow lint and applicable exact-head Atlas CI.
- [ ] Pin Leto to the immutable repair and rerun its affected exact-head gates.
- [ ] Obtain independent re-review; retain drafts and integration holds meanwhile.
