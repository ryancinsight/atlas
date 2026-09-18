<a id="atlas-pub-001"></a>
## ATLAS-PUB-001 — Migrate 8 crate-release workflows to the Atlas-shared caller [patch] — blocked: fresh Kwavers current-default validation

- Owner: current session (Atlas coordination); scope: root publication records and
  exact default-branch evidence for
  `repos/{apollo,coeus,consus,hephaestus,kwavers,leto,moirai,ritk}/.github/workflows/rust-release.yml`.
  The separate `repos/ritk/.github/workflows/release.yml` is the wheel publisher,
  not the crate caller. One package per claim — the
  scopes are disjoint by repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3.
- Outcome: each package's crate-release workflow becomes a thin caller of
  `ryancinsight/atlas/.github/workflows/crates-publish.yml@<atlas-sha>`, and the
  duplicated 142-line body is deleted in the same change. Audit 2026-07-28: four
  of the seven `rust-release.yml` files are byte-identical; the only real
  variation is `RUST_TOOLCHAIN` (1.95.0 / 1.97.0 / 1.97.1) and whether the
  package needs Atlas path dependencies (only `kwavers`).
- Non-goals: changing any package's toolchain pin; changing tag conventions;
  touching the already-shared wheel pipeline.
- Acceptance per package: caller under 40 lines; the package's existing toolchain
  value passed as `rust-toolchain`; `kwavers` passes `atlas-ref`; the old body
  deleted, not kept beside the caller; one `workflow_dispatch` validation run
  green before the next release.
- Dependencies: none. ATLAS-PUB-003 must be complete for that package before its
  next real publish, but the migration itself does not wait on it.
- **hephaestus slice done 2026-08-03** (`38f36bc`): 142-line body → 39-line
  caller pinned to atlas `9772542`, toolchain 1.95.0 preserved, `crate-` tag
  convention unchanged. Acceptance met including the validation run —
  `workflow_dispatch` run 30795798452 is green, with the validate job passing
  in 1m3s and the publish job correctly skipped (it gates on
  `github.event_name == 'release'`, so a dispatch cannot publish).
- **leto and moirai slices done (prior session)**: both migrated to 39-line callers.
- **apollo, coeus, consus, ritk PRs open 2026-08-04**: apollo PR #75, coeus PR #289, consus PR #11, ritk PR #107 — 142-line bodies → 39-line callers, format/lock fixes applied, CIs running.
- **Carry this into the remaining seven migrations: the tag gate must stay in
  the caller.** The audit's "byte-identical apart from the toolchain" reading
  misses it. Each package's current workflow skips non-`crate-` releases via a
  job-level `if`, but the shared workflow's validate job has **no** prefix
  check and `exit 1`s on a tag it cannot parse. Porting without the gate
  converts today's silent skip of a legacy `<package>-v<version>` release into
  a red CI run.
- Evidence that this is live, not theoretical: hephaestus's two most recent
  release events (`hephaestus-metal-v0.18.0`, `hephaestus-host-v0.18.0`, both
  2026-08-02) show `skipped` in the run list. Legacy-convention tags are still
  being cut, so the gate is doing real work today.
- Tag-convention state, surveyed 2026-08-03 across all eight packages: every
  one gates on `crate-`, and there is exactly **one** matching tag in the whole
  stack — apollo's `crate-apollo-fft-macros-v0.2.0`, cut 2026-08-02. So
  `crate-` is the newly adopted convention rather than a dead gate, and the
  default `tag-prefix` is correct for these callers. Worth stating explicitly
  because the raw numbers (1 matching tag out of 77) read like dead automation
  until the dates are checked.
- Separate observation, not part of this item: because those 0.18.0 release
  events skipped, they were not published by this pipeline. Whether the crates
  reached crates.io by another route is a question for ATLAS-PUB-003, which
  owns publisher registration.
- **leto slice done 2026-08-03** (`c42b87d`), plus `bf7bf2b` fixing four unused
  imports that the earlier `520f248` decomposition left behind — CI denies
  warnings, so that would have failed the gate regardless of this item.
- **moirai slice done 2026-08-03** (`08d5095`): identical caller with its own
  toolchain (1.97.0) passed through; the repo's workflow differed from the
  others only in that value. Validation run 30811438728 green, and its
  `--locked` step passing independently confirms moirai's lock is sound.
  Repository CI also green, covering the three refactor commits the push
  carried.
- **3 of 8 done** (hephaestus, leto, moirai). The five left — apollo, coeus,
  consus, kwavers, ritk — are all currently on live peer branches, so their
  slices wait for those branches rather than for anything in this item.
- **Default-branch recheck 2026-08-13.** All eight fetched crate defaults now
  carry the 39-line Atlas caller with no local `cargo publish` body: Apollo,
  Coeus, Consus, Hephaestus (`origin/master`), Kwavers, Leto, Moirai, and RITK.
  The source migration is therefore complete; the old `3 of 8` count is
  historical.
- Hosted validation evidence is mixed and remains open for the release gate:
  Apollo release validation `31534217702`, Coeus release validation
  `31551729552`, Hephaestus release validation `31532975062`, Leto release
  validation `31531560175`, Moirai release validation `31530550433`, and RITK
  release validation `31654707025` pass. Consus dispatch validation
  `29976636343` passes on its recorded head. Kwavers dispatch validations
  `31316302910` and `31290138802` fail at the pre-repair lock state; no fresh
  validation exists yet for the current default after the git-source lock
  repair. Coeus publish-stage failure is the external registry gate owned by
  ATLAS-PUB-003, not a caller-validation failure.
- Re-open trigger: fresh Kwavers `workflow_dispatch` validation run
  `31717782458` completes successfully at current default `7fee848d`.
- Practical note for the remaining slices: pass `version` from the workspace
  table, not a grep of the member manifest. Members use
  `version.workspace = true`, so a naive extraction sends the literal string
  (or an empty value) to `workflow_dispatch` and the run fails on a version
  mismatch that looks like a pipeline defect but is just a bad argument. It
  cost a wasted run on both leto and moirai.
- **The validation run then exposed a blocking, stack-wide publish defect.**
  See ATLAS-PUB-LOCK-1 below. The leto migration itself is behavior-preserving
  and correct — the old and shared workflows use byte-identical `--locked`
  invocations, so this failure predates the migration and would have hit the
  first real release either way. The migration is what made it visible.

