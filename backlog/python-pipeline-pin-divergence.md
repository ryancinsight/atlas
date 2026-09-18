<a id="python-pipeline-pin-divergence"></a>
## ATLAS-PYTHON-PIPELINE-PINS-2026-09-04 - No published wheel covers ARM Linux or musl [patch] - in-progress

- **outcome:** every member consuming the shared `python-wheels.yml` pins the
  same Atlas commit, and that commit carries the platform matrix. `ritk` stops
  carrying its own copy of the pipeline.
- **the defect is coverage, not tidiness.** `bfb720121` (2026-08-26) expanded
  the shared workflow from three wheels — glibc Linux x86_64, Windows x86_64,
  macOS universal2 — to six systems: glibc and musl Linux on x86_64 and
  aarch64, plus Windows and macOS. **All nine consuming members are pinned
  before it**, newest `5b43d5513` on 2026-08-20. So no Atlas wheel on PyPI
  installs on ARM Linux or on musl; `pip` there falls back to the sdist and
  needs a Rust toolchain.
- **measured 2026-09-06** at `877955f94`. Four distinct workflow pins and six
  distinct `atlas-ref` values across nine members:

  | Member | `python-wheels.yml@` | `atlas-ref` |
  | --- | --- | --- |
  | CFDrs | `5936303396` (08-18) | `ad22ec5eec` (08-21) |
  | apollo | `5b43d55135` (08-20) | `5b43d55135` (08-20) |
  | coeus | `4c31dd753f` (08-13) | `1a7cdca730` (08-09) |
  | consus | `4c31dd753f` | `1a7cdca730` |
  | helios | `5936303396` | `4c07ce3d11` (08-19) |
  | hephaestus | `4c31dd753f` | `1a7cdca730` |
  | kwavers | `2f17abc735` (08-19) | `2f17abc735` |
  | leto | `4c31dd753f` | `1a7cdca730` |
  | moirai | `4c31dd753f` | `1a7cdca730` |

  `atlas-ref` is "the exact Atlas commit that owns the provider gitlink graph",
  so five members resolve their first-party providers through a gitlink graph
  from 2026-08-09 — a month stale.

- **`ritk` runs its own `release.yml`** rather than the shared workflow: a
  hand-rolled three-wheel matrix that also assumes MSYS2 on the Windows runner.
  That is the duplication defect at fleet scale (`consolidation_discipline`) and
  it is why `ritk` did not get the platform fix either.
- **acceptance:** all consumers pin one identical SHA carrying `bfb720121`;
  `ritk/.github/workflows/release.yml` is deleted in favour of the shared
  `workflow_call`; the conformance scan counts distinct pins across members so
  the next divergence fails rather than accumulating.
- **verification limit, stated:** these workflows fire on release publish only,
  so the sweep cannot be dry-run. The first release per member is the
  verification, and the pin change is reviewed as a diff against the shared
  workflow's declared inputs.

