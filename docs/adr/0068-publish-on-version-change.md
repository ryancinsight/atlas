# ADR 0068: Crates publish when their manifest version changes

- Status: Accepted
- Date: 2026-09-30
- Item: ATLAS-PUB-009 (delivered by this ADR's PR; the caller rollout is [ATLAS-PUB-010](../../backlog.md#atlas-pub-010))
- Relates to: [ADR 0035](0035-shared-publication-pipelines.md),
  [ADR 0037](0037-facade-crates-and-registry-naming.md),
  [ADR 0060](0060-publish-order-optional-dependencies.md)

## Context

Every member publishes crates through a GitHub Release named `crate-<package>-v<version>`. The release event starts the member's `rust-release.yml`, which runs the SemVer gate (`semver-gate.yml`) and then publishes under OIDC trusted publishing. Fourteen members call `crates-publish.yml` (ADR 0035) for that step, and twelve still carry an inline copy of it. A manifest version bump therefore reaches crates.io only after someone creates one release per crate by hand.

On 2026-09-30, a registry audit compared every member's fetched `origin/main` manifests against the crates.io sparse index. It found 29 publishable crates that have earlier versions on crates.io but whose current manifest version is missing there; one of them, `horae`, is a name owned by another account. The hand step also races dependency order: each release starts its own workflow run, so a crate fails to resolve while a workspace sibling it depends on is still publishing. The 2026-09-30 releases had to be driven layer by layer from outside CI.

The same audit found a defect in `semver-gate.yml`. Its release gate asked crates.io about the comma-joined `package` input as if it were a single crate name. Every multi-crate caller got a 404, which the gate reads as a first publication, so it skipped the comparison.

## Decision

A version bump that merges to the default branch triggers its own publication.

1. **Shared action `crates-pending`** (`.github/actions/crates-pending`, Python standard library only). It holds all the selection, verification, publish, and tag logic once:
   - `plan` selects each publishable package whose manifest version is missing from the sparse index and whose crates.io owners include `owner`.
   - It then runs `cargo package --locked --no-verify` over that set, which resolves every dependency against the registry without compiling.
     - A missing version of a dependency that `owner` publishes from another repository is a wait, per package: the packages that depend on it, directly or through other pending packages and through any dependency kind except a dev-dependency without a version (which `cargo package` strips), are held back with a notice, and the rest are resolved again without them. That repository's pipeline publishes the version, and the next push or schedule here retries the held packages. The dependency is read from cargo's error, whether it names an unmet version requirement or a requirement no published version satisfies (a feature the published versions lack, or a conflict); the owners lookup keeps the crawler interval.
     - A dependency with no index entry at all (cargo's "no matching package"), a missing version of a workspace member outside the pending set, or one of a crate another account owns, needs a person: a first token publish, or a requirement fix. It is a warning naming the dependency, and it still holds back only the packages that need it, so one stuck dependency never stops unrelated releases. Any other resolution failure fails the run.
   - Last, it runs `cargo package --locked`, which compiles the packages that are not waiting. Only those reach the publish job.
   - A name with no index entry at all gets a notice and is skipped: crates.io accepts only an API token for a crate's first publish. A name owned by another account gets a warning and is skipped, because it needs its own registry name (ADR 0037 §3).
   - Any registry answer other than found or not found fails the run. An outage must never read as "nothing pending" or as "never published".
   - `publish` re-reads the index, then runs one `cargo publish --no-verify --package …` over whatever is still pending. Cargo orders the packages by their dependencies and waits for each one to reach the index. Verification already happened in the plan job, so the token's 30-minute lifetime ([crates.io trusted publishing](https://crates.io/docs/trusted-publishing)) is spent only on uploads.
   - `tag` creates the existing `crate-<package>-v<version>` release for each planned version the index now holds. `cargo publish` waits 60 s for its uploads to appear and then exits 0 even if they have not, so after a successful publish `tag` polls the index for up to five more minutes. It fails the run if a planned version is still missing, which keeps a lost release recoverable.
2. **Reusable workflow `crates-publish-pending.yml`** runs three jobs:
   - `plan` runs only on a `schedule` event or a `push` to the repository's default branch, under `contents: read`. It installs the caller's `apt-packages` before compiling, and forwards them to the gate.
   - `semver` is the shared release gate over the pending set.
   - `publish` runs in the `crates-io` environment under `id-token: write` and `contents: write`. Its tag step runs even after a partial publish failure, because a version that reached the index is no longer pending at the next plan. A run that fails before every release exists, including after that index poll, recovers by re-running its failed jobs: the plan's outputs persist, `publish` re-filters to nothing, and `tag` creates the missing releases.

   Releases created with `GITHUB_TOKEN` start no workflow run, so the release-event path never publishes the same version a second time.
3. **Member callers.** Each member's `rust-release.yml` adds `push` (default branch) and a daily `schedule` to its triggers, and calls `crates-publish-pending.yml` from a job of its own. That job alone grants `contents: write`. The release-event and `workflow_dispatch` jobs keep calling `crates-publish.yml` unchanged, so the manual route and the dry-run route keep their permissions. Trusted publishers are keyed by the caller's filename, and on 2026-09-30 every sampled registration, ritk's included, named `rust-release.yml`. Adopting the new path therefore needs no registry change.
4. **SemVer gate fix.** The release gate asks crates.io once per listed name, spaced one second apart (the crawler policy). It checks the subset that is already published, gives a notice for each first publication, and fails on any other status. The new workflow pins the commit that carries this fix.

## Rejected alternatives

- **Add the push mode to `crates-publish.yml`.** A nested reusable workflow can only narrow its caller's permissions. The release-event caller job would have to grant `contents: write` for a mode it never runs.
- **release-plz `release`.** It performs the same selection and supports trusted publishing. But it replaces the caller shape ADR 0035 consolidated and has no wait-on-upstream outcome. It remains the candidate if the stack adopts generated changelogs and release PRs.
- **Tagging every indexed version that lacks a release.** This would recover lost releases without a re-run, but it tags the current commit. For a version published from older source (100 drifted crates on 2026-09-30, ATLAS-PUB-011), the release would name source that was never published.
- **Tag pushes as the trigger.** This only moves the manual step from the release page to `git tag`.
- **One job per pending crate.** This brings back the ordering race between workspace siblings that one `cargo publish` invocation removes.

## Consequences

- Merging a version bump to the default branch is the release decision, so release review happens in the PR that bumps a manifest.
- Cross-repository order converges without coordination. A consumer bumped before its provider waits, and publishes on the first run after the provider's version is indexed. The daily schedule bounds that delay when no push arrives.
- First publishes stay manual: one API-token publish per new name, after which the trusted publisher applies (ATLAS-PUB-003).
- The gate compares versions only. Source that changed under an unchanged, already-published version is invisible to it; ATLAS-PUB-011 carries that guard.
- Publishing several packages in one `cargo publish` needs cargo 1.90 or later. Every member pins a toolchain above that floor, and a caller's `rust-toolchain` input must stay there.
- Python wheels still publish from release events. Moving them to the same trigger is a separate decision.

## Verification

- `scripts/tests/test_crates_pending.py` runs the action against fake registry and cargo doubles, and against a patched `urlopen` for the HTTP layer. It covers:
  - selection, index paths, and the owner check;
  - outages of the index, the owners API, and the network;
  - notice versus warning by dependency owner and workspace membership, and which packages a missing version holds back;
  - the crawler interval and the index-poll budget against their published bounds;
  - re-filtering before publish;
  - tagging only indexed versions, the bounded index poll after a successful publish, and failing on a failed release creation;
  - the command-line entry point and its outputs, and the composite action's shell (every input reaches its argument; a failing command fails the step).

  Mutation sweeps over the action, the workflow wiring, the release job and the gate's request are recorded with their counts in the delivering PR (#408). Every listed variant fails a suite.
- `scripts/tests/test_semver_gate_baseline.py` runs the gate's baseline step against stub `curl` and `sleep`, and pins the release job's wiring. The `curl` stub answers only the step's exact argument list (flags in order, the gate's User-Agent, one crates.io crate URL) and exits 99 on any other, so a malformed request cannot pass as a 404. Its seven stub cases cover a published subset, a single published crate, all first publications, a 503, a 403 and a 429, curl failing before any HTTP answer, and an empty list entry; all seven fail against the pre-fix gate.
- `scripts/tests/test_crates_publish_pending_workflow.py` parses the workflow for:
  - the default-branch condition;
  - the gate running ahead of publish;
  - permissions and environment;
  - the tag step's condition;
  - a single full-length pin shared by the action and the gate, whose `action.yml`, `crates_pending.py` and `semver-gate.yml` match this tree byte for byte (skipped where the pinned commit is absent, as in an export);
  - the release-path workflow granting no new permission.
- The first push-mode run in each converted member is the end-to-end check, and its run ID is recorded on ATLAS-PUB-010.

## Overturning evidence

Revisit this decision if:

- a push-mode run publishes a version that the release-event path would have rejected; or
- crates.io allows trusted publishing for a crate's first publish, which would remove the never-published skip.
