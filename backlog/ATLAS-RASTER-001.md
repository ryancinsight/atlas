<a id="ATLAS-RASTER-001"></a>
## ATLAS-RASTER-001 — Shared raster codec ownership [arch] - in-progress
- Status: in-progress; integrator: root; updated: 2026-09-20.
- Outcome: one bounded JPEG/EXIF provider without a RITK–Metis repository cycle.
- Decision: [ADR 0063](docs/adr/0063-raster-codec-ownership.md).
- Provider: [Consus](repos/consus/backlog.md#CONSUS-RASTER-001).
- Consumers: [RITK](repos/ritk/backlog.md#RITK-JPEG-001), [Metis](repos/metis/backlog.md#METIS-ASSETS-001).
- Acceptance: consumer decoder copies removed, lossless precision retained, progressive/orientation fixtures and bounded rejection pass, Windows V06 verified; scope excludes releases and unrelated formats.
- Integration gate: Consus [PR 77](https://github.com/ryancinsight/consus/pull/77) clears provider regressions. Consumer pointer advances remain blocked by pre-existing ratchet increases: Metis oversized files 0→5 and numeric names 0→4; RITK oversized files 45→48, existence assertions 0→2 and oversized images 26→30. Reopen when member counts return to baseline; do not raise baselines.
