<a id="atlas-python-wheel-attestation-context"></a>
## ATLAS-PYTHON-WHEEL-ATTESTATION-CONTEXT — Preserve read-only wheel verification [patch] — blocked
- priority: correctness; status: blocked; owner: Codex; scope: shared wheel workflow/tests and Leto's immutable recipe pin.
- basis: [Leto #365 review](https://github.com/ryancinsight/leto/pull/365) found unconditional attestation fails fork/Dependabot verification without OIDC/write credentials.
- repair: classify original actor/event/head repository after all validation/upload; skip unprivileged verification attestation; fail untrusted release mode closed.
- evidence: four regressions fail before; all 16 workflow tests pass after, including 12 credential-free actual shell contexts; no live fork PR created.
- preserved: permissions, matrices, value/source validation, attachment guard and limits; [Python floor follow-up](atlas-python-wheels-floor.md) remains separate.
- [x] Reproduce missing guard and pass original/new local regressions.
- [ ] Pass workflow lint and applicable exact-head Atlas CI.
- [ ] Pin Leto to the immutable repair and rerun affected exact-head gates.
- [ ] Obtain independent re-review; retain drafts and integration/policy holds.
