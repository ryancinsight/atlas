<a id="atlas-consus-szip-bound-2026-08-20"></a>
## ATLAS-CONSUS-SZIP-BOUND-2026-08-20 — Bound SZIP allocation [security][patch] — in-progress

The SZIP decoder previously trusted a four-byte sample count from a seven-byte
header before checking the payload or reserving output storage. Malformed input
could therefore request an unbounded allocation and abort instead of returning
a typed error.

**Evidence:** Consus PR [#51](https://github.com/ryancinsight/consus/pull/51)
adds independent header-size and payload-capacity bounds plus
`try_reserve_exact`; its hosted package, MSRV, and fuzz checks pass. The exact
head `2e24e6adda663db67b4bf1d4e1614e2c3b06fc19` merged at default
`1000699fa740c74b8aea1b9cc5311f85d3d2a3cc`. Post-merge CI and Documentation
runs `32436374114` and `32436374130` are queued. RecurseML remains report-only.
The dirty Consus checkout and Atlas gitlink are unchanged until terminal
post-merge evidence is collected.

