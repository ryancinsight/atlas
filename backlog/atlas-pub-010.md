<a id="atlas-pub-010"></a>
## ATLAS-PUB-010 — Convert member crate callers to version-change publishing [patch] — todo
- outcome: every member `rust-release.yml` is a thin caller of `crates-publish.yml` at the ADR 0068 commit, triggered on `push` to the default branch, a daily `schedule`, `release`, and `workflow_dispatch`. Its job `if` admits push and schedule, and its `permissions` grant `contents: write` + `id-token: write`. Kwavers also passes `atlas-ref`.
- scope: `repos/*/.github/workflows/rust-release.yml` (ritk: `release.yml`). 14 members already call the shared workflow; 12 carry an inline copy of its body (aequitas, asclepius, CFDrs, eunomia, gaia, helios, hermes, iris, melinoe, mnemosyne, themis, tyche) and convert to the caller in the same change.
- acceptance: per member, the first push-mode run completes. It is green with `count=0` when nothing is pending, or it publishes and tags the pending set. The run ID is recorded in the member PR body.
- order: hermes, leto, moirai first (their 0.7/0.43/0.6 bumps are the live test), then the rest in any order. One PR per member, dispatched one agent per repository.
- needs: ADR 0068's PR merged (the caller pins its commit).
- links: [ADR 0068](docs/adr/0068-publish-on-version-change.md), [ATLAS-PUB-003](../backlog.md#atlas-pub-003).
