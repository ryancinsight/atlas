<a id="atlas-prepush-hook-forked-across-members-2026-09-09"></a>
## ATLAS-PREPUSH-HOOK-FORKED-ACROSS-MEMBERS-2026-09-09 — One gate, twenty-three copies, six versions [patch] [ci] — in-progress

- **Outcome:** the member `pre-push` gate has one stack-level owner the members
  consume, so a fix to it reaches every member instead of one.
- **Measured 2026-09-09**, `sha256` of `repos/*/.githooks/pre-push`, 23 members
  carrying six distinct versions of the same file:
  - 118 lines, 12 members (CFDrs, aequitas, ares, consus, eunomia, helios,
    hephaestus, horae, leto, moirai, proteus, ritk)
  - 118 lines, a second variant, 2 members (apollo, hermes)
  - 73 lines, 5 members (asclepius, gaia, hyperion, mnemosyne, themis)
  - 73 lines, a second variant, 2 members (athena, tyche)
  - 2 lines, 1 member (coeus) -- a stub, so coeus has no gate at all
  - 323 lines, 1 member (kwavers)
- **Why it matters now:** kwavers#754 gave the hook the fmt/clippy/test gate it
  was missing, after two defects escaped a lockfile-only hook in one merge
  (#749, #750). Twenty-two members still run the lockfile-only version, and the
  73-line variants predate even that. The fix landed once; the defect class it
  closes is open everywhere else.
- **Same generator as the workflow copies:** this is the fleet-scale
  duplication the lint floor already counts for workflows and scripts -- one
  owner in the meta-repo's `scripts/`, consumed by members, rather than a
  per-repo hand-rolled copy.
- **Risk:** the 73-line variants may lack the lockfile guard entirely; confirm
  before assuming a uniform upgrade, and coeus needs a gate, not a merge.
- **Found 2026-09-09 while pushing the consus sweep: the lockfile guard is
  vacuous on every new-branch push, in all six versions that carry it.** For a
  new branch the remote sha is zero, and the hook then computes its comparison
  base as `git merge-base "$local_sha" HEAD`. Pushing the branch you are on
  makes `local_sha` equal `HEAD`, so the base is the pushed tip itself, the
  range is empty, and the hook reports "no Cargo.lock or Cargo.toml in the
  pushed range" and exits 0. Measured on consus `797b1b4`: that base yields 0
  changed files where `origin/main` yields 7, all of them manifests. The gate
  section kwavers added gets this right at its own line 203
  (`merge-base "$origin_main" HEAD`); the lockfile guard above it does not.
  So the escapes this item cites had a lockfile guard that could not have run.
- **Integrator:** unclaimed; **lease released 2026-09-09.** A peer already
  holds `scripts/git-hooks/pre-push` and `scripts/tests/test_atlas_pre_push_gate.py`
  uncommitted, and their working copy already carries the base-computation fix
  recorded above. I withdrew a duplicate shell harness on finding their
  387-line Python one, and hand over three measured results instead.
- **Measured against three hook versions** by driving each with a real stdin
  ref line in throwaway repositories (reproduction kept out of tree; it is
  three cases their existing fixture can absorb):

  | | lockfile base | gate reached on a source-only push | gate base on a non-`main` default |
  |---|---|---|---|
  | committed `scripts/git-hooks/pre-push` | **broken** | no gate | no gate |
  | `repos/kwavers/.githooks/pre-push` | **broken** | ok | **broken** |
  | peer's uncommitted working copy | ok | **broken** | **broken** |

  The two live versions are complementary -- each has what the other lacks --
  and both share the third defect.
- **Two defects the in-flight fix does not close:**
  1. **The gate half resolves only `origin/main`.** `gate_base` tries
     `@{upstream}`, then `origin/main`, then prints
     `no upstream or origin/main to diff against; local gate skipped` and
     exits 0. A first push has no upstream yet, so on a repository whose
     default branch is not `main` the gate runs nothing at all -- no fmt, no
     clippy, no tests. **hephaestus's default branch is `master`**, confirmed
     2026-09-09. Unlike the lockfile half, an unresolved base here fails
     *open*. `origin/HEAD` resolves the real default; `origin/main` is an
     assumption the fleet does not satisfy.
  2. **The lockfile half still `exit 0`s** at its "not needed" and
     "not present" paths (lines 96 and 125 of the working copy), so a push
     that changes no manifest never reaches the gate -- the common case.
     kwavers' copy already restructured these to `return`, and its own comment
     names this as "the one that has escaped"; the port has not carried it
     across yet.
- **The peer's test cannot catch the first of these:** its fixture pushes
  `HEAD:main` and sets upstream to `origin/main` throughout, so every case runs
  on a `main` default. One more fixture parameterised on the default branch
  covers it.
- **Acceptance:** one owned gate script in the meta-repo; every member's
  `.githooks/pre-push` resolves to it; the conformance scan counts distinct
  member gate versions and the count is 1; coeus included; and a new-branch
  push whose range changes a manifest runs the lockfile check rather than
  skipping it.
- **Status:** in-progress; **Integrator:** prepush-slice2 (regions:
  `scripts/git-hooks/pre-push`, `scripts/tests/test_atlas_pre_push_gate.py`,
  `scripts/atlas-conformance.py`, `scripts/conformance-baseline.json`).
- **2026-09-10 slice:** defect 2 (lockfile-half `exit 0`) closed by
  `a4673d25a` (fall-through, kwavers' `return` shape in port); defect 1
  (gate base assumes `origin/main`) closed by resolving `origin/HEAD` first
  through one `default_branch_base` helper shared by both halves, with a
  `master`-default fixture case that fails on the old hook (8/8 gate tests).
  `member_gate_versions` counts distinct hook contents -- members plus owned
  source, CRLF-blind so a clean Windows checkout and an archive of one pin
  never count twice -- and enters the baseline at 5: 22 members share one
  version, coeus and kwavers one each, 4 hookless (iris, melinoe, metis,
  prometheus), owned source distinct from all. `sync-hooks --check` reports
  32 differing hooks. Rollout (sync into members, 23 member commits) open.
- **Rollout slice claimed 2026-09-10T20:10Z** by claude-opus-5; **regions:**
  `repos/*/.githooks/**` only -- disjoint from prepush-slice2, which holds the
  owned source, its test and the conformance scan. Verified before claiming:
  the landed hook passes all six cases of the independent reproduction that
  first surfaced these two defects (a `master`-default fixture and a
  source-only push, driven through real stdin ref lines), and **0 of 24**
  member copies match it, so no member yet runs either fix.
- **Rollout order:** one member first, with a real push exercising the gate,
  before the fleet -- the hook runs fmt, clippy and tests on every push, so a
  fault in it stops 23 repositories rather than one.
- **Rollout done 2026-09-10 for 19 of 28 members.** leto was the pilot
  ([#189](https://github.com/ryancinsight/leto/pull/189)); its push printed
  both `lockfile check not needed` **and** `local gate not needed`, and the
  second line is the fall-through fix -- the old hook exited after the first
  and never reached the gate. Every deployed copy was then checked to be
  byte-identical to the owned source, line endings aside. 4 merged
  (asclepius, athena, consus, gaia); 15 enqueued on auto-merge behind a queue
  that had not started a run 20 minutes in.
- **Nine members not deployed, each for a stated reason:**
  - **eunomia -- blocked, and this one is a finding.** The owned `pre-commit`
    now *fails closed* when `scripts/lockfile.py` is missing, so installing it
    in a member that lacks that script refuses every commit there. eunomia is
    the only member with a `.githooks/` directory and no checker; the deploy
    refused its own commit, which is how this surfaced. The member copies of
    `lockfile.py` are **not** stack-synced -- all five sampled differ from the
    meta-repo's -- so it cannot be supplied by copying. eunomia needs a
    member-appropriate checker before the fail-closed guard can land there.
  - **iris, melinoe, prometheus** -- no `.githooks/` directory, and all three
    also lack `scripts/lockfile.py`, so they need the checker first for the
    same reason.
  - **CFDrs, kwavers, metis, mnemosyne, moirai** -- uncommitted work in the
    tree when the rollout ran; deploying would have swept a peer's changes
    into the hook commit. Re-run the sync for these when their trees are
    clean.
- **coeus is not a drift case, and its PR was closed unmerged**
  ([Coeus #395](https://github.com/ryancinsight/Coeus/pull/395)). Its hooks
  source a shared `.githooks/lockfile.sh` and are covered by its own
  `scripts/tests/test_hooks.py`, which asserts that *both* hooks reject when
  the checker, the shared entry, or the interpreter is missing. Syncing the
  owned copy over them removed that design and failed 8 of those tests -- the
  only real failure in the whole rollout, and it surfaced because coeus is the
  only member that tests its hooks at all. Checked: no other member has
  `test_hooks.py` or `lockfile.sh`, so the rest of the rollout is unaffected.
  **This needs a decision, not a sync:** either coeus adopts the owned hook and
  retires its shared entry and tests, or the owned hook absorbs the
  shared-entry design coeus already has. The second is worth weighing -- coeus
  is the one member that noticed the guard could fail open, and its tests are
  the only executable statement of what the guard owes its caller.
- **`member_gate_versions` will not reach 1 until eunomia, the four hookless
  members and the coeus decision are resolved**, so the acceptance above needs
  the checker question answered, not just the sync repeated.
- **Merged so far:** asclepius, athena, consus, gaia, leto, aequitas, apollo,
  ares. Ten more are enqueued on auto-merge behind pending checks
  (harmonia, helios, hephaestus, hermes, horae, hyperion, proteus, ritk,
  themis, tyche); the three merged administratively had every owned check green
  with only the always-red third-party check failing
  ([its item](#atlas-third-party-check-always-red-2026-09-09) is decided and
  awaiting the uninstall).

