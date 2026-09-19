<a id="atlas-pub-001"></a>
## ATLAS-PUB-001 — Migrate 8 crate-release workflows to the Atlas-shared caller [patch] — blocked: fresh Kwavers current-default validation

outcome: all 8 packages' (`apollo, coeus, consus, hephaestus, kwavers, leto, moirai, ritk`) crate-release workflows become thin callers of `ryancinsight/atlas/.github/workflows/crates-publish.yml@<atlas-sha>`, duplicated 142-line bodies deleted, with the `crate-` tag-prefix gate preserved in the caller (needed — the shared workflow's validate job has no prefix check and `exit 1`s on a tag it can't parse). Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3.

status: source migration complete for all 8 (default-branch recheck 2026-08-13 — every fetched default carries the 39-line caller, no local `cargo publish` body). Hosted validation passes: Apollo `31534217702`, Coeus `31551729552`, Hephaestus `31532975062`, Leto `31531560175`, Moirai `31530550433`, RITK `31654707025`, Consus `29976636343`.

blocked: Kwavers dispatch validations `31316302910`/`31290138802` fail at the pre-repair lock state; no fresh validation exists after the git-source lock repair.

re-open trigger: fresh Kwavers `workflow_dispatch` validation run `31717782458` completes successfully at current default `7fee848d`.

note: the validation run exposed a blocking, stack-wide publish defect tracked separately as ATLAS-PUB-LOCK-1 — this migration is behavior-preserving (old and shared workflows use byte-identical `--locked` invocations) and is not the cause. Coeus's publish-stage failure is ATLAS-PUB-003's external registry-gate scope, not a caller-validation failure.
