<a id="ATLAS-RASTER-001"></a>
## ATLAS-RASTER-001 — Shared raster codec ownership [arch] - in-progress
- Status: in-progress; integrator: root; updated: 2026-09-21.
- Outcome: one bounded JPEG/EXIF provider without a RITK–Metis repository cycle, governed by [ADR 0063](../docs/adr/0063-raster-codec-ownership.md).
- Members: [Consus](../repos/consus/backlog.md#CONSUS-RASTER-001), [Apollo](../repos/apollo/backlog.md#apollo-dct-core-001), [RITK](../repos/ritk/backlog.md#RITK-JPEG-001), [Metis](../repos/metis/backlog.md#METIS-ASSETS-001).
- Acceptance: consumer decoder copies removed, lossless precision retained, progressive/orientation fixtures and bounded rejection pass, Windows V06 verified; scope excludes releases and unrelated formats.
- Provider delivery: [Consus PR 80](https://github.com/ryancinsight/consus/pull/80) and [Apollo PR 526](https://github.com/ryancinsight/apollo/pull/526) merged; hook rollout follows [its owning item](hook-fleet-duplication.md).
- Consumer delivery: [RITK PR 561](https://github.com/ryancinsight/ritk/pull/561) merged; 1,356 debug and 392 release tests pass. [Metis PR 322](https://github.com/ryancinsight/metis/pull/322) merged after the full Windows and lockfile gates pass. [Helios PR 103](https://github.com/ryancinsight/helios/pull/103) merged with 47 package tests passing.
- Pointer gate: Metis passes; Apollo oversized files 41 to 43, Consus 81 to 82, and Helios 7 to 8 require source consolidation. RITK [PR 562](https://github.com/ryancinsight/ritk/pull/562) restores its counts and awaits landing. Remediation preserves all baselines.
