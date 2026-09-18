<a id="atlas-downstream-coordination-001"></a>
## ATLAS-DOWNSTREAM-COORDINATION-001 — Notify LeoNeuro-INC maintainers about local leoneuro-rs `50bfcd9` [chore] — todo

- Owner: unclaimed; scope: out-of-band coordination with the
  LeoNeuro-INC organization (separate GitHub org, NOT ryancinsight).
  No atlas-side edits in this scope.
- Outcome: the leoneuro-rs `50bfcd9` commit ("build(leoneuro-rs):
  Apply round-6a atlas-root path resolution — GRAND_TOTAL 0 across
  atlas") lives locally at `/d/atlas/repos/leoneuro-rs/` on the
  branch `codex/sim-ct-medium`. After atlas's closure cycle dropped
  the bogus 160000 gitlink in commit `d6827c2`, atlas parent no
  longer tracks leoneuro-rs's HEAD; the LeoNeuro-INC maintainers
  can land `50bfcd9` to their own org
  (`https://github.com/LeoNeuro-INC/leoneuro-rs.git`) on their own
  schedule via their own CI/dispatch pipeline.
- Acceptance: a downstream LeoNeuro-INC maintainer receives a short
  note pointing at the local SHA (`50bfcd9`) and the atlas-side
  commit history (see `D:/atlas/PATH_DEP_AUDIT_001_ENTRY.md` STEP D
  push-handoff paragraph for the handoff context); the
  LeoNeuro-INC team decides whether to fast-forward their `main`
  to `50bfcd9` or to cherry-pick from the local branch.
- Method: out-of-band contact through the existing LeoNeuro-INC
  internal channels; the atlas-side convey is a one-line pointer
  (no technical payload required). The atlas-side documentation
  states this deferral, but **no atlas code or Cargo.toml changes**
  are part of this ticket. The `50bfcd9` commit is preserved on the
  leoneuro-rs local branch (`codex/sim-ct-medium`) until the
  LeoNeuro-INC team decides its disposition.
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27)
  STEP D push-handoff paragraph codifies the deferral as
  documentation; this ticket is the corresponding **owner-assigned**
  follow-up so the deferral doesn't drift unowned. NAME SEMANTIC
  NOTE: "downstream" in this title refers to LeoNeuro-INC as
  downstream maintainer of the `50bfcd9` commit; this is distinct
  from atlas-side "downstream consumer" terminology used in
  per-submodule commit hygiene tickets.
- Risk/change class: `[chore]`; out-of-band coordination only.

