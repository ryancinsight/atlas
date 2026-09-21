<a id="atlas-run-output-segregation"></a>
## ATLAS-RUN-OUTPUT-SEGREGATION — Two output roots at the stack root, one of them tracked-visible [patch] — todo

outcome: one gitignored output root with a committed retention policy, so run
artifacts cannot be committed and cannot grow without a bound.

- Found 2026-09-20: `run-output/` held 327 MB at the stack root and was not
  ignored, so any `git add -A` would have committed it; `output/` beside it
  was already ignored. `run-output/` is now ignored too, which closes the
  commit risk and leaves the duplication.
- Also cleared in the same pass: `jv2target/` and `jv3target/` (120 MB and
  126 MB), two forked cargo caches at the stack root — `CACHEDIR.TAG` plus a
  `release/` tree in each — against the one-build-cache rule.
- Next: decide which root is canonical, move the other's contents under it or
  delete them, and give it the eviction policy the run-output rule requires
  (per-run directories with a manifest, evicted by committed age or size).
  The conformance scan should count a second output root the way it counts a
  forked target dir.
- Acceptance: one ignored output root, a committed retention rule, and a scan
  class that fails on a second one.
