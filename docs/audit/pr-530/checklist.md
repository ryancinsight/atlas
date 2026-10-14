## Atlas fleet reconciliation checklist [patch]

- priority: correctness; phase: Closure; target: Atlas integration patch, Consus 0.2.1 and Tyche 0.3.1; owner: Atlas integration.
- Outcome: every published provider edge satisfies its consumer requirement, every canonical lock matches its selected provider and every Atlas gitlink passes the unchanged drift and conformance checks.
- Specification and evidence: [source-bound audit](reconciliation.md), [revisions](revisions.json).
- [x] [patch] Reproduce 66 declaration lags, 17 lock-drift repositories and the default dependency DAG without altering primary component trees.
- [x] [patch] Publish verified Horae #98, Hyperion #82, Consus #172 and the history-preserving Tyche #109 update; 2,814 native tests, locked metadata, all features and warning-denying diagnostics pass.
- [x] [patch] Select 13 forward default gitlinks that pass conformance; preserve six holds and update the two existing waiver reasons to measured current defects.
- [x] [patch] Regenerate the development overlay from approved immutable defaults with the unchanged generator.
- [ ] [patch] Obtain current-head hosted review and default promotion for the four verified component corrections, then resolve downstream locks to their final merged revisions.
- [ ] [arch] Migrate Hermes's real conversion contract after Eunomia's CastFrom removal; obtain its provider review and native conversion equivalence evidence before the Leto adoption chain proceeds.
- [ ] [patch] Close Leto/Hephaestus/Apollo/Athena conformance regressions at their source; retire each existing waiver only after its new reopen condition holds.
- [ ] [minor] Adopt approved Moirai 0.9 in Leto -> Hephaestus -> Apollo -> Coeus -> Metis -> RITK -> CFDrs/Helios/Kwavers and re-resolve every owned lock.
- [ ] [patch] Reach a passing published-default overlay, version guard and unchanged pin-drift check before declaring fleet reconciliation complete.
- Boundary: Moirai #618 and Metis #503 stay separate, unmerged and blocked by provider recovery performance/review; no QUIC proposal enters Apple-host pins.
