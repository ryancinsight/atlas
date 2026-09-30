# ADR 0068: Crates publish when their manifest version changes

- Status: Accepted
- Date: 2026-09-30
- Item: ATLAS-PUB-009 (delivered by this ADR's PR; the caller rollout is [ATLAS-PUB-010](../../backlog.md#atlas-pub-010))
- Relates to: [ADR 0035](0035-shared-publication-pipelines.md),
  [ADR 0037](0037-facade-crates-and-registry-naming.md),
  [ADR 0060](0060-publish-order-optional-dependencies.md)

## Context

Every member publishes a crate through a GitHub Release named `crate-<package>-v<version>`: the release event starts the member's `rust-release.yml`, which runs the SemVer gate and then `crates-publish.yml` (ADR 0035) with OIDC trusted publishing. A manifest version bump therefore reaches crates.io only when someone creates one release per crate by hand.

A registry audit on 2026-09-30 read every member's fetched default branch against the crates.io sparse index. 29 crates carried a version bump that had not been published, some since the bump landed. The hand step also races dependency order: one release per crate starts one workflow run per crate, so a crate whose workspace sibling is still publishing fails resolution. That happened to one hermes run on 2026-08-11. The 2026-09-30 releases had to be driven layer by layer from outside CI.

## Decision

The member workflow that owns crate publishing also runs on pushes to the default branch and on a schedule. In that mode `crates-publish.yml` runs three jobs:

1. `plan` reads `cargo metadata` and selects every publishable package whose manifest version is absent from the crates.io sparse index. It runs `cargo package --no-verify` over that set, which resolves every dependency against the registry, and has three outcomes:
   - Nothing pending, or a name the index has never seen: skip. The never-seen case emits a notice, because crates.io accepts only an API token for a crate's first publish, which CI does not hold.
   - A dependency version from another repository not yet on the index: a warning and a skip. That repository's own pipeline publishes it, and the next push or schedule here retries.
   - Any other packaging failure: the run fails.
2. `semver` runs the shared SemVer release gate over the pending set against the registry baseline.
3. `publish-pending` publishes the set in one `cargo publish --package ...` invocation. Cargo orders the packages by their dependencies and waits for each to reach the index. The job then creates the existing `crate-<package>-v<version>` release for every version the index now holds, including after a partial failure. It runs in the `crates-io` environment under `id-token: write` and `contents: write`. Releases created with `GITHUB_TOKEN` start no workflow run, so the release-event path never publishes the same version a second time.

The release-event and `workflow_dispatch` paths stay unchanged. They remain the manual route and the dry-run route.

The caller filename stays `rust-release.yml`, the name every crates.io trusted publisher is registered under. Adopting the mode therefore needs no registry change.

## Rejected alternatives

- **release-plz `release`.** It performs the same selection and supports trusted publishing, but it would replace the caller shape ADR 0035 consolidated. It also does not materialize the Atlas path dependencies that `atlas-ref` callers need, and it cannot express the wait-on-upstream outcome. It remains the candidate if the stack adopts generated changelogs and release PRs.
- **Tag pushes as the trigger.** This keeps the manual step and only moves it from the release page to `git tag`.
- **One job per pending crate.** It reintroduces the ordering race between workspace siblings that one `cargo publish` invocation removes.

## Consequences

- A version bump merged to the default branch is the release decision. The PR that bumps a manifest version is where review of a release happens.
- Cross-repository order converges: a consumer bumped before its provider waits, and publishes on the first run after the provider's version is indexed. The schedule bounds that delay without a push.
- First publishes stay manual, one API-token publish per new crate, after which the trusted publisher applies (ATLAS-PUB-003).
- Python wheels still publish from release events. Moving them to the same trigger is a separate decision.

## Verification

- `scripts/tests/test_crates_publish_workflow.py` parses the workflow for job conditions, permissions, and environment. It also runs the plan job's own shell against stub `cargo` and `curl` executables for four cases: pending set selected, never-published and unpublishable skipped, upstream wait, and other failure red. Inverting the index check or the wait match fails the suite.
- On 2026-09-30 the plan step, run against exports of the hermes, moirai, and leto default branches and the live index, selected 5, 17, and 0 packages. Leto was waiting on hermes-simd 0.7.
- The first push-mode run in each converted member is the end-to-end check, recorded on ATLAS-PUB-010.

## Overturning evidence

This decision is revisited if a push-mode run publishes a version its release-event path would have rejected, or if crates.io admits trusted publishing for a first publish, which would remove the never-published skip.
