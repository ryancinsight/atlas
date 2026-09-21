<a id="ATLAS-RASTER-001"></a>
## ATLAS-RASTER-001 — Shared raster codec ownership [arch] - done
- Status: done; integrator: root; updated: 2026-09-21; delivery: this pointer increment.
- Outcome: one bounded JPEG/EXIF provider without a RITK–Metis repository cycle, governed by [ADR 0063](../docs/adr/0063-raster-codec-ownership.md).
- Members: [Consus](../repos/consus/backlog.md#CONSUS-RASTER-001), [Apollo](../repos/apollo/backlog.md#apollo-dct-core-001), [RITK](../repos/ritk/backlog.md#RITK-JPEG-001), [Metis](../repos/metis/backlog.md#METIS-ASSETS-001).
- Acceptance: consumer decoder copies removed, lossless precision retained, progressive/orientation fixtures and bounded rejection pass, Windows V06 verified; scope excludes releases and unrelated formats.
- Provider delivery: Consus main `dd058480bfb380dc0d4b572de56b2030da6f3dc4` (PRs 80/81) and Apollo main `56bdec2ef2a1cfee4584b4faf9e5e3618dedeb5c` (PRs 526/530) own JPEG arithmetic/precision and reusable DCT.
- Consumer delivery: RITK main `2e346c0dd29d6f711e387167f43df029437eccd2` (PRs 561/562), Metis main `08785d8f05d7ff5795c4a3692d5478c44a7ba2c0` (PRs 322/324/326/327), and Helios main `ebb54c3ccfb30bb62ad7efa61147c015298ed7b0` (PRs 103/104) are pinned below.
- Pointer gate: all five member scans report zero regressions; Apollo oversized files 41→39, Consus PM lines 444→89, and Metis tracked images 7→0 are recorded baseline tightenings. Metis run 35623156489 passed all 27 stages; native V06 compared 464,000 client pixels with zero differences.
