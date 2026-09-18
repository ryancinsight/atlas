<a id="atlas-worktree-takeover-107"></a>
## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in-progress

Audited every worktree in every member (30 trees), ranked by branch-tip age, and
measured delivery state — ahead of `origin/main`, pushed, merged — rather than
inferring it from the branch name.

**Four branches held unpushed commits.** Same failure as
ATLAS-RITK-D2-STRANDED-100: authored, never delivered, invisible to every peer.
All four are now pushed; none merged, so nothing was decided on their behalf.

| repo | branch | unpushed | content |
| --- | --- | --- | --- |
| consus | `fix/consus-zarr-endian-hardening-221` | 1 | crc32c codec, "close three silent-swap paths" — a correctness fix |
| consus | `codex/adr-0045-p4-benchmark-parser` | 11 | breaking: remove package-owned S3, centralize async I/O in Moirai |
| kwavers | `refactor/seismic-example-structure` | 13 | seismic DICOM/quality sharing, transcranial FWI partition (45 files) |
| mnemosyne | `codex/mnemosyne-board-cleanup` | 1 | board closure docs |

**Correction: one entry in that table was wrong.** `feat/qus-attenuation-b2` was
listed here as undelivered because its local branch was unpushed. The work had in
fact landed — merged as `8003eeaa3` via PR #404 on 2026-08-19. A squash re-authors
the hash, so the local branch still looked ahead of main. This is precisely the
false positive ATLAS-BOARD-DELIVERY-AUDIT-101 measured at 3-in-4, and checking the
PR rather than the hash is what catches it. Pushing it was harmless but redundant;
the lane is now closed as delivered. `refactor/seismic-example-structure` replaces
it in the table — 13 commits, 45 files, no PR, genuinely unpushed until this sweep.

**Six lanes closed**, all verified delivered by PR and holding only overlay
lockfile churn: `coeus-layernorm-shape`, `apollo-root-cleanup`,
`CFDrs-runtime-budget`, `helios-lock-027`, `asclepius-lock-027`,
`kwavers-qus-attenuation`. Four of those had **merged** PRs while their local
branches still read as ahead of main — the same re-authoring effect. coeus,
apollo, CFDrs, helios and asclepius are each back to a single tree.

**One stalled PR unblocked.** hermes #55 ("Close orphan cleanup evidence") sat
CONFLICTING and untouched for 29h. Its conflict was a PM-artifact collision:
main had inserted a new board item directly above the one the commit flips from
`in progress` to `done`. Resolved as a union — both items kept, the status change
applied — rebased, force-pushed with lease; the PR is MERGEABLE again.

**The find: a stranded upstream capability with a downstream consumer already
built against it.**

Taking over the consus `adr-0045-p4-benchmark` lane, its tests failed to compile.
The cause was not that lane's uncommitted work — which is complete and good: an
offset-overflow guard placed *before* allocation in `read_at_bounded`, with a
test that drives `u64::MAX` through it. The cause was upstream:

- moirai `b548bc9` "add positioned I/O contracts" defines `AsyncReadAt` and
  `AsyncLength`.
- It is **not an ancestor of moirai `main`**. Pushed to
  `codex/moirai-positioned-io`, no PR ever opened, now 1 ahead / **14 behind**.
- consus `main` imports those traits in five modules and pins them **by
  revision**: its committed lockfile carries
  `git+https://github.com/ryancinsight/Moirai?rev=b548bc9`.

**Correction.** I first recorded that consus "cannot compile at all". It
compiles fine in CI — the rev pin resolves, because the commit is pushed. The
build failures I hit came from the Atlas development overlay redirecting
`moirai-*` to the local tree, which sits on a branch without these contracts.
That was my local setup, not a consus defect, and the earlier note said
otherwise.

The real problem is narrower and still worth fixing: a `rev` pin onto an
unmerged commit is quarantine, not a dependency. It freezes consus 14 commits
behind moirai `main` and it cannot take any moirai change without moving to
another unmerged rev. Landing the commit is what lets consus return to an
ordinary version requirement.

Landed as moirai PR #145: cherry-picked onto current `main`, applied cleanly
across the 14 intervening commits, authorship preserved. 90/90 `moirai-async`
tests, fmt clean, zero clippy findings. Merging it unblocks the consus branch;
consus itself is untouched, per co-evolution (upstream first).

**Why this class keeps appearing.** Four unpushed branches, eleven stashes, three
untracked ADRs, and one stranded upstream commit — all found in one day, none
detectable by any gate, because every gate inspects what is presented to it. The
common shape is work that exists only in one machine's local state. The cheap
detectors are known and now recorded: `git rev-list origin/main..<branch>` per
local branch, `git stash list`, `git ls-files --others docs/adr/`, and
`git merge-base --is-ancestor` for cited commits (ATLAS-BOARD-DELIVERY-AUDIT-101).

**Remaining, not actioned.** Pushed-but-unmerged branches with real divergence —
CFDrs `codex/cfdrs-backward-step-108` (99 ahead), helios and asclepius both on
`fix/apollo-lock-0.27` (3 and 2 ahead, a coordinated cross-repo lock sweep),
hephaestus `codex/hephaestus-fdtd-107`, hermes `codex/hermes-orphan-closure`.
These are visible on their remotes, so they are not at risk; triaging whether
each is in-flight or abandoned needs their owners or a PR check, not a takeover.

