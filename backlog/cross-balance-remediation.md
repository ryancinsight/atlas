<a id="cross-balance-remediation"></a>
## ATLAS-CROSS-BALANCE-EDGE-REMEDIATION-2026-09-04 - Route the four cross-balance edges through harmonia [minor] - todo
Parent: `#archtest-live-balance-domains`, surfaced at `9e9dbe785` on 2026-09-04.
- outcome: the four edges (helios-analysis, helios-planning, kwavers-physics, kwavers-therapy, each -> asclepius) route through `harmonia` via typed field envelopes ([ADR 0050](docs/adr/0050-typed-physical-field-exchange.md)), or move the shared type to `aequitas` where genuinely single-field, reaching `balance_domain_edges = 0`. Owner: helios on lane `perf/helios-ci-concurrency`; kwavers on `refactor/elastic-ssot-consumer`.
- acceptance: scan reports `balance_domain_edges = 0` across all 26 members; `[#proteus-elastic-ssot](backlog.md#proteus-elastic-ssot)` and the kwavers->ares->athena path stay green.
- risk: low — dev-only `kwavers-analysis`/`-simulation` edges out of scope.
