<a id="python-pipeline-pin-divergence"></a>
## ATLAS-PYTHON-PIPELINE-PINS-2026-09-04 - No published wheel covers ARM Linux or musl [patch] - in-progress

outcome: every member consuming the shared `python-wheels.yml` pins the same Atlas commit carrying the six-system platform matrix (glibc+musl Linux x86_64/aarch64, Windows, macOS); `ritk` stops hand-rolling its own release pipeline.

defect: `bfb720121` (2026-08-26) expanded the shared workflow from 3 to 6 wheel targets; all 9 consuming members are pinned before it (newest `5b43d5513`, 2026-08-20), so no Atlas PyPI wheel installs on ARM Linux or musl — `pip` falls back to sdist there, requiring a Rust toolchain. Measured 2026-09-06: 4 distinct workflow pins and 6 distinct `atlas-ref` values across 9 members (CFDrs, apollo, coeus, consus, helios, hephaestus, kwavers, leto, moirai); five resolve first-party providers through a gitlink graph a month stale.

separate finding: `ritk` runs its own hand-rolled `release.yml` (3-wheel matrix, MSYS2-dependent) instead of the shared workflow — the fleet-scale duplication defect, and why it missed the platform fix too.

acceptance: all consumers pin one identical SHA carrying `bfb720121`; `ritk/.github/workflows/release.yml` deleted in favor of the shared `workflow_call`; the conformance scan counts distinct pins across members so the next divergence fails the gate.

verification limit: these workflows fire on release publish only, so this cannot be dry-run — the first release per member is the verification, reviewed as a diff against the shared workflow's declared inputs.
