<a id="atlas-arch-008"></a>
## ATLAS-ARCH-008 — Replace pointer-scattered containers on traversal paths [patch] — in-progress

outcome: production `Vec<Vec<_>>` on real traversal paths becomes a CSR-shaped
flat buffer + offset table, each conversion backed by a criterion win; jagged-
correct sites are recorded as such instead of converted.
- Oracle: `scripts/atlas_scattered_containers_classify.py` +
  `scripts/oracles/arch-008-production-sites.txt`, checked by
  `make verify-scattered-oracle`. Current: 243 production / 80 test-bench.
- next: pick the next site by traversal hotness (profile first — no single
  hotspot, a long tail of 3-10 occurrences per file) and convert with a
  criterion win, or record correct-as-jagged with the profiling rationale.
- Six conversions delivered (moirai, ritk-vtk, apollo x2, consus-zarr); one
  (CFDrs spectral assembly) reverted as correct-as-jagged (measured 1.2-1.6x
  slower). Continue one repo family per claim.
