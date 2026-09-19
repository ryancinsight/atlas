<a id="atlas-helios-bench-local-instrument-2026-09-18"></a>
## ATLAS-HELIOS-BENCH-LOCAL-INSTRUMENT-2026-09-18 — helios runs wall-clock benchmark regression on hosted CI [arch] — todo
- Evidence: helios `ci.yml` job `benchmark-regression` times eight A/B legs on one hosted runner and hits its 60-minute cap (PR #88, exit 124). helios#90 (draft) splits it across four runners. Timing on shared runners is noise, not evidence, so the job cannot produce what it gates on.
- Outcome: helios ADR 0003 is revised in place. The paired A B B A / B A A B schedule runs as the local pre-merge instrument, with its baseline comparison attached to the PR, and CI keeps only a single-iteration bench smoke. The `benchmark-regression` job is deleted and helios#90 closes.
- Acceptance: the ADR revision records the evidence and is judged; CI runs `cargo test --benches` (or criterion `--test`) within the standard test budget; a committed local runner reproduces the paired schedule under the 300 s suite bound.
- Last-update: 2026-09-18.
