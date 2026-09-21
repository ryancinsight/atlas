<a id="atlas-run-output-segregation"></a>
## ATLAS-RUN-OUTPUT-SEGREGATION — Two output roots at the stack root, one tracked-visible [patch] — todo
- Found 2026-09-20: `run-output/` held 327 MB at the stack root and was not ignored, so any `git add -A` would have committed it; `output/` beside it already was. It is ignored now, which closes the commit risk and leaves the duplication. Cleared in the same pass: `jv2target/` and `jv3target/`, 120 MB and 126 MB of forked cargo cache against the one-cache rule.
- Next: pick the canonical root, move or delete the other, and give it the eviction policy the run-output rule requires (per-run directories with a manifest, evicted by committed age or size). The conformance scan should count a second output root as it counts a forked target dir.
- Acceptance: one ignored output root with a committed retention rule, and a scan class that fails on a second one.
