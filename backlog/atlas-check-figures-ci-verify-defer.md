<a id="atlas-check-figures-ci-verify-defer"></a>
## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — todo
- **outcome:** the wired `prebook check-figures` SSOT drift lint is verified end-to-end in hosted CI, incl. a captured `DRIFT_DOCS_NOT_IN_SPECS: N` log line on a deliberate drift fixture.
- priority: verification; needs: ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1
- helios prong landed: the closeout branch merged as helios PR #32 (merge commit `02d7a7755f7`), and helios `ci.yml` runs `xtask check-figures` on every PR.
- next: capture the `DRIFT_DOCS_NOT_IN_SPECS: N` line on a deliberate drift fixture, per ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 step (c).
- **evidence:** `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.
