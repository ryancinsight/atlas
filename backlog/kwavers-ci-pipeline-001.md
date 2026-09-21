<a id="kwavers-ci-pipeline-001"></a>
## KWAVERS-CI-PIPELINE-001 - Consolidate kwavers CI to one verification pipeline [ci] [patch] — todo
- Outcome: one workflow whose jobs carry the stage structure (build-once, cheapest-first, affected-scope filters); mdBook deploy off pull_request events; benchmark regression job removed (benchmarks run locally per policy - CI keeps the single-iteration bench smoke only).
- Evidence 2026-08-24: six sibling workflows fire per PR event and per main push; queue sat 6-15 min behind one busy runner; one main-push CI/CD Pipeline run ended cancelled, leaving that merge unverified.
