# atlas — cross-repository integration backlog

<a id="atlas-board-control-characters-2026-09-18"></a>
## ATLAS-BOARD-CONTROL-CHARACTERS-2026-09-18 — Board text carried control characters from escaped Windows paths [patch] — done
- `scripts/atlas-board-lint.py` fails on any C0 control character or DEL other than LF/CR line endings, naming the line; the 7 lines in `backlog.md` and 3 in `gap_audit.md` are restored. Delivered in the board-compaction PR.



<a id="atlas-hephaestus-host-seam-coverage"></a>
## ATLAS-HEPHAESTUS-HOST-SEAM-COVERAGE — `hephaestus-host` implements every seam the conformance suite is generic over [arch][major] — in-progress
- Outcome: `assert_backend_contract` runs against the host reference device on a GPU-less runner, every clause included (ADR 0046 §5, atlas ADR 0038 coverage table).
- Landed: DenseProduct (hephaestus#300), DenseVector (#301), SparseOperator + BatchSubmit (#302); enqueued: RandomInit (#304); in review, stacked: RayIntegral (#305), Stencil + Staggered3D (#306), CrossEntropy and checked views (#307).
- Remaining value seams: Attention, Convolution. Seven operator-generic families (full/axis reduction, scan, elementwise, typed elementwise, parameterized unary, stateful update) implement [hephaestus ADR 0061](repos/hephaestus/docs/adr/0061-operator-value-semantics.md): eunomia's 13 scalar functions first, then the core value traits and Host dialect, then the host impls.
- Acceptance: the host instantiates the aggregate entry point; ADR 0038's host row records every clause; rendering corrections tracked in `repos/hephaestus/backlog.md#heph-kernel-tail-accuracy`.
- Integrator: claude session c15a9301; lane `worktrees/hephaestus-host-dense-product`; last-update: 2026-09-18.

<a id="atlas-hooks-follow-checkout-2026-09-18"></a>
## ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18 — The installed atlas hooks are whatever branch the shared tree holds [patch] — todo
- Evidence: `core.hooksPath=.githooks` resolves in the working tree, so the atlas pre-push gate that runs is the checked-out branch's copy. On 2026-09-18 the tree held a peer branch whose `.githooks/pre-push` predated the pushed-range fix; three pushes of main-based branches were refused for a moirai pin they did not touch, and were pushed through origin/main's hook via a transient `-c core.hooksPath`.
- Acceptance: the gate that runs on any push is the default branch's committed hook (for example a tracked trampoline that executes `git show origin/<default>:.githooks/pre-push`, or hooks installed outside the tree by the setup path), with a fixture test where the checked-out branch carries an older hook.
- Dependencies: none. Risk: a stale gate refuses valid pushes (bypass pressure) or passes invalid ones.
- Last-update: 2026-09-18.


<a id="atlas-solver-ownership-consolidation"></a>
## ATLAS-SOLVER-OWNERSHIP-CONSOLIDATION — Complete ADR 0033: the Krylov forks and the only multigrid in the stack live in CFDrs [arch][major] — todo

Decision: [ADR 0062](docs/adr/0062-iterative-solver-and-preconditioner-ownership.md),
**Accepted 2026-09-10** — Phase 1 carries a sequencing condition: the relocations
touch `repos/CFDrs` and `repos/kwavers`, both on the forced Moirai 0.6.0 sweep order,
so they execute once that sweep lands. Board opened from the
[2026-09-09 foundation audit](docs/audit/2026-09-09-foundation-layer-next-steps.md)
finding F1.

- **Outcome:** `athena` owns iterative policy and preconditioner composition,
  `leto` owns the sparse kernels, and no integrator keeps a local copy.
- **Measured 2026-09-09.** ADR 0033 is Accepted and its first two legs landed:
  `athena` owns `Cg`, `Gmres<_, RESTART>`, `BiCgStab`, `Lsqr` and the
  `Preconditioner` trait; `leto` has no `Preconditioner` and no iterative
  module. The third leg did not: `cfd-math/src/linear_solver/` still carries
  `krylov.rs`, `preconditioners/{ilu,multigrid}`, `block_preconditioner.rs`,
  `direct_solver.rs`, `chain.rs`, `dense_bridge.rs`, and `kwavers` carries one
  further Krylov file.
- **Why it is worse than ordinary duplication.** `multigrid` occurs **zero**
  times in `athena`, `leto`, and `coeus` — it exists only in `cfd-math`. The
  member chartered to own solver policy cannot offer it to anyone. And the
  forks can drift: ADR 0055's P2-B evidence already records `cfd-core` and
  `kwavers-medium` disagreeing on aluminium (70 GPa against 69 GPa).
- **Scope discipline.** Per ADR 0011 §Leg 2 the source edits are consumer-claim
  work in `repos/CFDrs` and `repos/kwavers`; this row tracks them. Phase 1 is a
  **move with a differential oracle**, not a rewrite — anything that cannot
  reproduce current CFDrs output on existing fixtures was an algorithm change
  and does not belong in it.
- **Acceptance:** `cfd-math/src/linear_solver/` is gone and its callers re-point
  at `athena` + `leto`; the `kwavers` Krylov file is gone; the false doc comment
  at `leto-ops/src/application/linalg/mod.rs` is deleted; every relocated solver
  reproduces its prior output on existing fixtures at `f32` and `f64`.
- **Phase 2** (new construction, gated per ADR 0056 on analytical oracles, not
  on a second consumer): `athena` gains MINRES, FGMRES, Chebyshev,
  deflation/recycling. **Phase 3** deferred: algebraic multigrid needs a
  grid-hierarchy owner, since prolongation/restriction is interpolation and
  ADR 0055 R6 assigns that to geometry.
- **Dependencies:** none on other open items. Not blocked by the Apollo Moirai
  `rev` quarantine, though CI cannot confirm Phase 1 while the stack overlay is
  red.

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

<a id="atlas-coeus-branch-inventory-2026-09-09"></a>

## ATLAS-COEUS-BRANCH-INVENTORY-2026-09-09 — Fifteen coeus branches hold unique work nobody is finishing [patch] — in-progress

- **Integrator:** claude-opus-5 (2026-09-10); **lease:** `repos/coeus` refs only
  -- no source regions, so a peer editing coeus files collides with nothing here.
- **Outcome:** every coeus branch maps to an open item or an enqueued pull
  request, per the branch-inventory rule.
- **Measured 2026-09-09** in `repos/coeus`, after deleting the four branches
  already merged into `main`: **15 unmerged local branches**, ages 2 days to
  **6 weeks**. `git cherry origin/main <branch>` reports **zero** commits
  superseded by an equivalent patch on any of them, so none can be dropped as
  already-landed -- each holds work that exists nowhere else.
  - Largest deltas: `codex/coeus-comparison-parity-comparisons` (5 commits,
    560 files, 6 weeks), `fix/coeus-autograd-honest-cache` (4 commits, 246
    files, 3 weeks), `perf/coeus-ops-index-decode` (2 commits, 234 files, 4
    weeks).
  - `refactor/coeus-autodiff-cache-leaves` is hours old and also on origin:
    live peer work, not debt.
- **Five existed only on this disk** -- `coeus-frobenius-v2`,
  `docs/coeus-book-closure-audit`, `fix/coeus-autograd-honest-cache`,
  `fix/coeus-linear-init`, `pr-344` -- carrying 12 unique commits between them
  with no remote copy, weeks old. **Pushed to origin as preservation** (no
  merge, no pull request), because a local-only branch is one cleanup script
  away from gone and this stack has lost lanes that way before.
- **Not a sweep item.** Each branch is its own takeover, worked
  closest-to-done first: rebase onto a current base, verify, integrate under
  its item -- or establish it is superseded and delete it. The 6-week-old
  560-file one is the likeliest to be genuinely obsolete and the likeliest to
  be expensive to prove so.
- **Acceptance:** zero coeus branches without an open item or enqueued pull
  request, each closed by integration or by a recorded supersession.
- **Seven closed 2026-09-10, 15 -> 8 local.** Each verdict names what
  superseded it, so the next sweep reads rather than re-derives.
  - `refactor/coeus-autodiff-cache-leaves` -- **integrated** as PR #389, with
    three review findings fixed on the way in (a non-atomic `reset_stats`, an
    eviction that ran after the purge already freed the room, and a
    fingerprint blind to repeated creator edges).
  - `refactor/coeus-autodiff-cache-modules` -- **superseded twice over.** Its
    decomposition of `autodiff_cache.rs` is answered by main's leaf set
    (`cache`, `config`, `fingerprint`, `key`, `plan`, `plans`, `stats`), and
    its cutile 0.3.1 pin raise by main deleting the direct `cutile`,
    `cuda-core` and `cuda-async` dependencies from `coeus-cuda` outright --
    CUDA now routes through `hephaestus-cuda/cuda`, so there is no pin to
    raise. Deleted local and remote.
  - `rescue/coeus-cache-wip` -- **superseded.** A verbatim snapshot of the
    pre-split `autodiff_cache.rs` (1021 lines) and `backward_cache.rs` (727),
    both since landed and then split; `var.rs`'s thread-local cache accessors
    are on main; the two loss ops moved *further* on main than the snapshot.
    Its one genuinely unique hunk is an uncommitted workflow overlay setting
    `defaults.run.timeout-minutes`, which is not a key GitHub Actions accepts.
  - `fix/adr-canonicalize` -- **superseded.** Main carries 42 ADRs, every one
    `Status: Accepted`, and zero duplicate numbers; the branch's renumbering
    also conflicts, since main resolved the five collisions to different
    targets (`0063` is the comparison providers there, the parity record
    here).
  - `fix/coeus-linear-init` -- **superseded.** ADR 0067 is on main at 139
    lines, Accepted, carrying measured results; the branch holds the 96-line
    Proposed draft.
  - `pr-344` -- **superseded.** Its premise ("this repository ran no general
    verification") is two weeks stale: `.github/workflows/ci.yml` is on main,
    and so are all seven `[fn@gradcheck]` disambiguations it carried.
  - `codex/coeus-unary-math-parity` -- **dropped.** One commit, adding four
    more `[patch]` path entries to the committed root `Cargo.toml`. That is
    the overlay leaking into a member mainline, a counted class; the branch
    deepens it rather than closing it.
- **One filed rather than ported: `coeus-frobenius-v2`.** Its `81f5573c`
  measured a real defect (dropping a `TcpStream` on Windows with unread buffer
  data sends RST, aborting the peer's receive; idle Moirai workers accumulate
  because the runtime is never stopped) and fixed it three prohibited ways --
  a `block_on` in `Drop`, a committed `RUST_TEST_THREADS=1`, and a sleep for
  "TCP state to settle". The diagnosis is what survives, filed as
  `COEUS-TCPMESH-GRACEFUL-SHUTDOWN` (Coeus PR #391) with the shape the fix has
  to take; the branch stays until that closes, which satisfies acceptance. Its
  sibling commit is already satisfied on main --
  `coeus_ops::frobenius_norm_batched` composes on `BackendOps` per ADR 0060.
- **All eight remaining closed the same day, 15 -> 5, every survivor mapped.**
  - `codex/coeus-provider-deletion-cuda` and `-wgpu` -- **superseded.** Every
    file they delete (`coeus-cuda/src/backend/ops/math/elementwise*`,
    `kernels/launch_ops*`) is already absent from main, whose
    `backend/ops/impls/elementwise.rs` routes through `ElementwiseProvider`
    and `hephaestus_cuda` exactly as the branches proposed; both bridge
    error-mapping tests the wgpu branch adds are on main verbatim.
  - `docs/coeus-book-closure-audit` -- **superseded.** Its ten rewritten book
    chapters are byte-identical to main's.
  - `codex/coeus-frobenius-provider` -- **superseded.** Main's `huber.rs` is
    strictly further along (provider-resident quadratic mask, retained shape
    and mean scale, 238 lines differing), and its batched-norm commit was
    already satisfied per ADR 0060.
  - `codex/coeus-comparison-parity-comparisons` -- **superseded**, the
    six-week 560-file one the item expected to be expensive. It was not: each
    of its five subjects corresponds to a decision Accepted *and* delivered on
    main -- fallible provider boundary (ADR 0042/0045, `Var::backward` returns
    `Result`), device-local COW (ADR 0036, coeus PR #384). The cheap proof was
    the ADR index plus the board's own outcome lines, not a 560-file diff.
  - `fix/coeus-clippy-get-first` -- **superseded.** Main's CI already runs
    `clippy --workspace --all-targets -- -D warnings` and is green.
  - `feat/coeus-ctc-alignedvec` -- **superseded**, and misnamed: all six
    commits are mnemosyne `rev` advances, no CTC work. Main is already past
    them (`e8e825f4` against the branch's `e26ee02`).
  - `refactor/coeus-hephaestus-wgpu-001` -- **merged**; zero commits ahead.
  - `fix/coeus-autograd-honest-cache` and `perf/coeus-ops-index-decode` --
    their one still-valid commit is re-derived rather than ported, as
    [Coeus PR #392](https://github.com/ryancinsight/Coeus/pull/392); both
    delete when it lands. `b40bf9b8`'s own subject no longer describes main:
    the "dead cache stub" is now a live `topological_sort_with_cache` call and
    the "30% overhead" README claim it corrects is already gone.
- **Survivors, all mapped:** `ci/sync-stack-hooks` (PR #385, analysis
  recorded on it), `coeus-frobenius-v2` (COEUS-TCPMESH-GRACEFUL-SHUTDOWN),
  `docs/coeus-tcpmesh-shutdown-item` (PR #391), `fix/coeus-pedantic-floor`
  (PR #392), and the two above. Acceptance is met.
- **Adjacent finding, filed here rather than acted on.** Coeus's root manifest
  pins `mnemosyne` by `rev` (`e8e825f4`) alongside its version requirement.
  A `rev` pin is explicit quarantine and carries a removal trigger; this one
  has none, and a first-party dependency should resolve by git+version so the
  overlay and the co-evolution sweep can move it. Same class as
  the apollo quarantine (apollo#385), one member
  further; dropping it changes resolution, so it wants its own increment with
  a lock update and a verified build rather than a drive-by edit.
- **Method note for the remaining eight.** A three-dot diff
  (`origin/main...branch`) shows the branch against the *merge base*, so a
  removed line in it is what the base had, not what main has. Read that way,
  `fix/adr-canonicalize` looks like unlanded work against a main that lost
  it; measured against main directly, it is entirely landed. Every verdict
  above was taken against `origin/main` content, not against a three-dot stat.
- **Remaining, oldest and largest last:** `perf/coeus-ops-index-decode` (2
  commits), `codex/coeus-provider-deletion-cuda` (1),
  `codex/coeus-provider-deletion-wgpu` (3), `docs/coeus-book-closure-audit`
  (4), `fix/coeus-autograd-honest-cache` (4),
  `codex/coeus-frobenius-provider` (5, one commit already ruled landed),
  `codex/coeus-comparison-parity-comparisons` (5, 6 weeks). Three exist only
  on origin and were not in the local count: `feat/coeus-ctc-alignedvec`,
  `fix/coeus-clippy-get-first`, `refactor/coeus-hephaestus-wgpu-001`.

<a id="atlas-cwd-config-cost-2026-09-16"></a>
## ATLAS-CWD-CONFIG-COST-2026-09-16 — Cargo config discovery is all-or-nothing: the shared `target-dir` arrives with the whole-stack `[patch]` overlay [patch] — in-progress

- **Same generator as
  `ATLAS-TARGET-FORK-REGRESSION-2026-09-09`,
  opposite outcome.** Cargo resolves configuration by walking up from the
  working directory. Every case in that item *lost* the stack config and forked
  a target; this is the first one that *kept* it — and inherited a 136-row
  overlay it had no use for. That item's guard ("an invocation that leaves the
  overlay carries `CARGO_TARGET_DIR`") does not cover this direction, because
  nothing left the overlay.
- **Observed 2026-09-16 in `test_atlas_stack_overlay.py::LagAwarePatchEmissionTestCase::test_cargo_unifies_current_closure_and_retains_old_git_revision`.**
  `CargoOverlayFixture` ran cargo with `cwd` = the Atlas root *on purpose*, so
  the fixture would inherit the stack's single shared `target/`. One literal
  `timeout=30` bounded both `cargo metadata` (resolves in about a third of a
  second) and `cargo check` (compiles), so the compile tripped a
  resolution-sized bound and the test failed as though it had hung.
- **What the cwd choice actually did, measured.** The same `cwd` that supplies
  `target-dir` also applies the root `.cargo/config.toml` in full: **46
  `[patch]` tables, 136 patched package rows, 23 member roots**, against a
  fixture graph of two dependency-free packages that share none of it. There is
  no `cwd` that yields one key of the stack config and not the other.

  | cwd | `CARGO_TARGET_DIR` | `target_directory` |
  | --- | --- | --- |
  | `/d/atlas` | unset | `D:\atlas\target` |
  | fixture tmpdir | unset | `<tmpdir>\target` |
  | fixture tmpdir | `D:/atlas/target` | `D:/atlas/target` |

- **Correction: the 362.89s first reported here is not the cwd's doing, and the
  cwd change buys no time.** Re-running the old arm (cwd = Atlas root, no
  `CARGO_TARGET_DIR`, budgets unchanged) measures **1.28s**; the arm shipped at
  that point (fixture `cwd`, `CARGO_TARGET_DIR` = the shared `target/`) measures
  **1.60s**, and the module then passed its 19 tests in 1.23s. None of the
  overlay's patched sources occur in the fixture's graph, so its patch registry
  is never consulted and the overlay costs nothing here. The attribution
  written into the fixture comment at the time ("minutes of unrelated
  resolution per run") is withdrawn by that measurement; the comment now says
  what was measured.
- **What the 362.89s and the 30s failure most plausibly were — unverified.**
  Both arms build into `D:\atlas\target`, the stack-wide cache the root config
  documents as serializing concurrent builds. A fixed bound on a command that
  can block on another process's build lock reports contention as a defect,
  which is the shape of the failure that opened this item. Recorded as the
  leading explanation because no reproduction of the stall was obtained — not
  as a finding. Provided for anything else that builds in that cache; the
  fixture stopped building there on 2026-09-16, per the residual below.
- **Fixed in the tree 2026-09-16.** `resolve`/`check` run from the fixture's own
  directory, so the stack overlay no longer applies. Budgets split per operation
  (`RESOLUTION_TIMEOUT_SECONDS = 30`, `COMPILE_TIMEOUT_SECONDS = 120`), and an
  over-budget command raises the fixture's own `AssertionError` naming the
  budget and the command. No assertion, package selection or lock check was
  relaxed, and no timeout was raised to cover slowness.
- **Residual closed 2026-09-16 — the fixture no longer builds into the shared
  cache at all.** The first cut pinned `CARGO_TARGET_DIR` to the shared
  `target/`, which bought the isolation from `cwd` at the price of the very
  property that raised this item: the fixture's duration stayed a function of
  every other cargo build on the machine, so a fixed bound on its compile could
  still report another process's build lock as a defect. The fixture now owns a
  `target` inside the tempdir it already owns (`CargoOverlayFixture.target`),
  set in its environment beside the `CARGO_HOME` and Git config it already
  redirected, so its scope is uniform: nothing it invokes reads or contends for
  machine-global state. It also *pins* the value rather than inheriting it, which
  matters because the stack's own bootstrap scripts export `CARGO_TARGET_DIR` —
  an unpinned fixture in a developer shell lands back in the shared cache.
- **Measured 2026-09-16 with that export in place** (`CARGO_TARGET_DIR=D:/atlas/target`):
  the shared cache gains no `overlay*` entry and the fixture passes; the module's
  20 tests pass in 2.0-2.4s across runs, `check`'s build is 1.5s and cold every run by
  construction, so the fixture's duration no longer depends on other cargo
  activity. The added second of wall time against the shared-cache arm (1.23s) is
  the price of owning the cache, paid per run.
- **No route back.** `stack_root` is gone from `resolve`/`check` and the
  `target_dir` override from `run`, so pointing the fixture at the shared cache
  again requires reintroducing the argument, not just changing a default. A
  regression test (`test_fixture_builds_in_its_own_target_not_the_shared_stack_cache`)
  constructs the fixture under a decoy `CARGO_TARGET_DIR` and asserts the pinned
  one wins; the cargo test additionally asserts its build produced a real cache
  there (`CACHEDIR.TAG`) and that no `target` appeared under `consumer`/`source`.
- **Acceptance:** no fixture or test invocation in the meta-repo depends on
  `cwd` for a stack config key it needs — target directory included — and a
  cargo command in this suite either owns its target directory or sizes its
  bound as a hang guard rather than a performance assertion.
- **Verified 2026-09-16:** `pytest scripts/tests/test_atlas_stack_overlay.py` →
  20 passed in 2.35s, 2.19s of it with `CARGO_TARGET_DIR` exported as the
  bootstrap scripts do; `pytest scripts/tests` → 702 passed, 3 skipped, 89
  subtests.

<a id="atlas-third-party-check-always-red"></a>
## ATLAS-THIRD-PARTY-CHECK-ALWAYS-RED-2026-09-09 — A check that fails on every pull request [patch] — blocked (decided 2026-09-10; awaiting the uninstall)

- **Integrator:** unclaimed; **lease:** none.
- **Measured 2026-09-09.** The most recently merged pull request in nine of ten
  sampled members — CFDrs #422, consus #71, helios #95, hephaestus #295, leto
  #179, kwavers #751, ares #2, asclepius #40, ritk #246 — carries a failing
  `recurseml/analysis`, every one reporting "Error occurred during analysis".
  The tenth (coeus #384) does not. It is a third-party app, not a committed
  gate, and it is not a required check, so nothing was blocked.
- **Why it is worth an item anyway.** Every pull request in the fleet displays a
  red X that means nothing, and the judgement each reviewer then has to make —
  human or agent — is "which red do I ignore". That is the habit the merge gate
  depends on not existing. Six pull requests were merged in this session over
  exactly this signal, each after opening the check list to confirm the
  committed gates were green; the confirmation is the cost.
- **Acceptance:** either the app reports a real verdict on Rust workspaces of
  this size, or its integration is removed from the members so the check list
  carries only checks whose colour is load-bearing.
- **Absorbed `ATLAS-RECURSEML-STATUS-ERROR-2026-09-03`,** which measured the
  same thing from the other end and is deleted below. What it established and
  this did not: the failure is a *commit status*, not a check run -- no
  output, no summary, no log, and a target URL pointing at the PR files page
  rather than at a run, so there is nothing to read and nothing to act on. It
  also predates any branch it appears on (aequitas `a65ade0c`, CFDrs
  `2561f8d0` and `39a0f45a`, all on their default branches), which is what
  rules out "a finding about this diff" without having to trust the message.
- **Still true 2026-09-10,** on every pull request opened today: mnemosyne
  #139 and #140, atlas #159 and #160. Each merged on the committed gates after
  opening the check list to confirm which red meant something.
- **The attempt, and why this is blocked rather than todo.** Removing or
  reconfiguring the app is an installation change, and the session's token
  cannot see installations at all:

      gh api user/installations
      403: You must authenticate with an access token authorized to a
      GitHub App in order to list installations

  That is an authorization failure on the attempt, not a judgement call, so
  it files as the request rather than as more analysis.
- **The request, one of three, in preference order.** (1) Uninstall the
  `recurseml` GitHub App from the `ryancinsight` account -- Settings ->
  Applications -> Installed GitHub Apps -> recurseml -> Uninstall; it gates
  nothing, so nothing is lost. (2) Keep it and restrict its repository access
  to a single member, so one repository carries the noise and the other
  twenty-seven do not. (3) Raise the analyzer error with the vendor and leave
  it installed meanwhile, accepting that every check list keeps a red X that
  means nothing. Recommendation is (1): a status that cannot pass trains
  reviewers to skim red, which is the one habit a merge gate cannot survive.
- **Re-open trigger:** the app is uninstalled or scoped, or the vendor's
  analyzer starts returning a verdict on a member workspace.
- **Decided 2026-09-10: option (1), uninstall.** The question was put with all
  three options and the 403 that made it a request rather than a judgement
  call; the answer was to uninstall the app from the account. Nothing in the
  repositories changes -- the check gates nothing, so there is no required
  status to unwire first, and no member workflow references it.
- **Not executable by an agent session.** Uninstalling is an account-level
  GitHub App operation and this session's token is not authorized to a GitHub
  App at all, so it cannot even enumerate installations. The step is
  Settings -> Applications -> Installed GitHub Apps -> recurseml -> Uninstall.
- **Close when** a pull request opened after the uninstall shows no
  `recurseml/analysis` entry in `gh pr checks`. Until then the item stays open
  so the next session does not re-litigate a settled decision.
- **Risk / change class:** [patch]; repository integration settings only.

<a id="atlas-build-source-identity"></a>
## ATLAS-BUILD-SOURCE-IDENTITY — Detect stale artifacts across source trees [patch] — todo
- **Outcome:** shared-cache gates consume artifacts from their recorded source tree and revision.
- **Scope:** Atlas build entry points and checkout coordination; preserve one shared target directory and peer work.
- **Evidence:** Apollo's release macro DLL contains a scratch-checkout path and the old parser diagnostic while the canonical source accepts `scheduled_pairs`; [retained artifacts](output/apollo-square-transpose/integration/composite-schedules/macro-artifact/) establish the mismatch.
- **Acceptance:** reproduce the source-tree transition, detect stale package artifacts before accepting a gate, rebuild only affected packages, and retain source/artifact identities without changing workloads or cache roots.
- **Dependencies:** reconcile the live scratch-checkout producer without discarding its unique work; [Apollo integration](repos/apollo/backlog.md#apollo-codelet-schedule-controls) repairs its affected release artifact now.
- **Verification:** deterministic source-transition regression, ordinary shared-cache reuse, and concurrent-owner preservation checks.

## ATLAS-KWAVERS-ELASTIC-COLLISION-2026-09-03 - Step 2b is peer-owned; I collided with it [patch] - stood down <a id="kwavers-elastic-collision"></a>

A peer is already migrating the kwavers elastic copy, further along than this
session and with a better design. I started the same work and overwrote a file
in their region before noticing.

**What the peer has, uncommitted in `repos/kwavers` on branch
`refactor/elastic-ssot-consumer`:**

- `properties/elastic/constructors.rs` - fully delegating to
  `proteus::elastic::IsotropicModuli` via `from_lame`, `from_young_poisson`,
  and `from_wave_speeds`, with the widened `lambda < 0` domain documented at
  the constructor rather than only in a commit message.
- `elastic.rs` - `lame_from_speeds` **deleted outright** rather than kept as a
  delegating adapter, with the module doc redirecting to the provider. This is
  the better call and mine was worse: an adapter that only forwards is the
  compatibility shim the integrity rules refuse, and keeping it would have left
  a second entry point to the same algebra.

**What I did wrong.** I read `git status` at the start of the turn, saw
`kwavers-medium` clean, and edited `computed.rs` several minutes later without
re-checking. The peer's work landed in that window. The lease protocol exists
for exactly this: check the target region immediately before the first edit,
not once at orientation. I checked at orientation only.

**Damage: none.** I reverted `computed.rs`, and the restored content is
byte-identical to what I had read, which proves the peer had not modified that
file - I overwrote my own read, not their work. `elastic.rs` and
`constructors.rs` were never touched by me.

**Standing down from step 2b.** The peer owns it. `computed.rs` still carries
all six duplicated derived formulas (`youngs_modulus`, `poisson_ratio`,
`bulk_modulus`, `shear_modulus`, `p_wave_speed`, `s_wave_speed`, each identical
to the `IsotropicModuli` accessor), so their migration is incomplete - but that
file is inside their item, not disjoint periphery, and a second collision costs
more than the wait.

**Claimable periphery for this session, if the peer stays on the core:** the
kwavers CHANGELOG entry recording the accepted break, and the kwavers lock
advance past the proteus elastic merge - the two things CFDrs #414 needed and
discovered from CI rather than up front.

- **re-open trigger:** the peer commits their kwavers elastic work, or their
  claim goes stale by the measured window.

## ATLAS-ARES-PROMOTION-2026-09-03 - Create and register `ares` (solid momentum balance) [arch][minor] - in-progress <a id="ares-promotion"></a>

Charter: [ADR 0057](docs/adr/0057-ares-phase-0-charter.md). Path:
[ADR 0056](docs/adr/0056-new-construction-promotion-path.md) new-construction.
Boundary: [ADR 0055](docs/adr/0055-continuum-domain-decomposition.md).
Execution steps: `checklist.md` `ATLAS-ARES-PROMOTION-2026-09-03`.

- **outcome:** `ares` owns small-strain linear elastostatics on Gaia meshes,
  closed by Proteus and solved by Athena, verified against analytical oracles.
- **non-goals:** plasticity, contact, finite deformation, dynamics, fracture,
  fatigue, anisotropy, buckling. No integrator dependency, no material
  constants, no direct edge to another balance domain.
- **registry name:** `ares-solid`, import path `ares` via `[lib] name`. Verify
  availability on crates.io before creating the repository.
- **required authority:** repository creation (A2) and publication (A9) sit
  outside the standing Change grant.

| Phase | Deliverable | Acceptance oracle | Depends on |
| --- | --- | --- | --- |
| A0 | Prerequisites: Proteus elastic consumer deletions; aequitas stress semantics marker | both closed | `#aequitas-mechanics-semantics` |
| A1 | Repository scaffold at the full lint and gate floor | fmt, clippy, nextest, doc green; conformance scan clean | A0 |
| A2 | **Ask-User:** create `ryancinsight/ares` | repository exists, name reserved | A1 |
| A3 | Kinematics: symmetric tensors, invariants, small strain | rigid-body motion gives exactly zero strain | A2 |
| A4 | Constitutive coupling: isotropic Hooke over `IsotropicModuli`; Cauchy, von Mises, principal stresses | closed-form stress from a known `(E, nu)`; no material constant in `ares` | A3 |
| A5 | FEM assembly: linear simplices, isoparametric mapping, quadrature, Dirichlet and Neumann, Athena assembly | **patch test exact to machine precision**; hand-computed element matrices | A4 |
| A6 | Solve and end-to-end verification | Lame cylinder; cantilever tip deflection; MMS; `O(h^2)` L2 convergence; strain energy equals external work | A5 |
| A7 | Register in atlas: gitmodules, stack table, naming, roadmap, dependency order, architecture test | inward-only edges asserted | A6 |
| A8 | First consumer: CFDrs FSI structural side across Harmonia per [ADR 0050](docs/adr/0050-typed-physical-field-exchange.md) | interface work conserved | A7 |
| A9 | **Ask-User:** publish `ares-solid` | registry install and smoke; docs.rs builds | A8 |

- **integrator:** claude-opus-5. **A0-A6 done 2026-09-04**, pushed to
  `ryancinsight/ares` main through `f8cb9eb`. Gate green: fmt, clippy at the
  pedantic floor, 96 tests, doctests, `cargo doc`.
- **A5 acceptance met.** Patch test exact to machine precision on distorted 2-D
  and 3-D patches, under pure shear and pure dilation, at `f32` and `f64`;
  element stiffness columns agree with hand computation through the Voigt
  `B^T D B` route, which shares no code with the tensor formulation used.
- **A6 acceptance met.** Manufactured solution at rates 1.65, 1.88, 1.97
  approaching second order; Lame cylinder; cantilever approaching beam theory
  from below; strain energy equals external work. Accuracy and identity oracles
  also run at `f32` - the rate studies do not, because `f32` reaches its
  precision floor before the study leaves the asymptotic regime.
- **[arch] `ares` is now a workspace** ([ares ADR 0001]): `crates/ares` is the
  `no_std` allocation-free core, `crates/ares-operator` the operator seam.
  Athena's `LinearOperator` fixes the error to `B::Error` and its views are
  backend-associated, so the seam is implementable only against a named
  backend, and the only host backend links `std`. A7's architecture test must
  assert the split's edge set, not a single-crate one.
- **A7 done 2026-09-04.** `.gitmodules` (26 packages), stack table, classical
  -names table, provisional note, suite-coverage row, dependency order, and the
  R7 boundary set, at gitlink `8ca1f52`. The oracle is met mechanically: the
  conformance scan reports `balance_domain_edges = 0` and
  `substrate_contract_violations = 0` for `ares`, and every other class zero,
  so the member enters the ratchet with no debt. Two gaps found and filed:
  R7 still omits the live balance owners (`#archtest-live-balance-domains`),
  since closed by a peer; and the book gap (`#ares-book`), closed 2026-09-04.
- **A8 done 2026-09-04** at ares `64a12f6`: `ares-coupling` presents the
  structural solve as a Harmonia `Partition`, with no edge to CFDrs or any
  other balance domain. Interface work conservation is exact and mutation
  -measured - a lumped load of the same resultant force breaks it and nothing
  else. Two findings against ADR 0059 and Harmonia recorded below.
- **A9 in progress**, authorised 2026-09-04. An earlier note here said the
  chain needed "the whole first-party stack" published; that was wrong, and it
  was wrong in a way that made A9 look far larger than it is. It counted the
  *sizes* of publish waves 0-3 rather than `ares-solid`'s dependency closure.
  The closure is **five crates**:
  `eunomia-derive -> eunomia -> aequitas -> proteus-mat -> ares-solid`.
- **Of those, `eunomia` 0.8.0 and `aequitas` 0.2.0 are already on crates.io**,
  published 2026-08-02 from this account. `proteus-mat` is the only unpublished
  link, and `cargo publish --dry-run -p proteus-mat` packages and verifies
  cleanly against the published `eunomia` and `aequitas`. The optional-edge
  cycle (`#publish-order-optional-edges`) does not touch this closure, so it
  does not gate A9 either - an earlier note said it did.
- **Delivered toward A9:** `rust-release.yml` in `proteus` (`2092f43`) and in
  `ares` (`30707d7`), matching the pipeline `eunomia` and `aequitas` already
  run: release-gate SemVer, `--dry-run` validation, and OIDC trusted publishing
  rather than a stored token. The `crates-io` deployment environment now exists
  on both repositories. `ares` needed a tag-parsing `identify` job because it
  ships three crates and the SemVer gate's package cannot be a constant.
- **Found by running the pipeline: the release SemVer gate could not pass a
  first publication.** It baselines against the latest published version, so
  for a crate not yet on crates.io `cargo-semver-checks` fails with "not found
  in registry" — making the gate unpassable for exactly one release per crate,
  its first, with the only ways past being to delete it or publish around it.
  Fixed in the shared workflow at atlas `744acdf83`: the gate asks crates.io
  whether the crate exists and skips only in that case. It asks rather than
  catching the failure, because "not published" and "registry unreachable"
  produce the same failure and must not produce the same decision. Both member
  pins advanced to pick it up (`proteus` `98eade5`, `ares` `677dc84`).
- **Pipelines verified end to end by dispatch, 2026-09-04.** `proteus-mat`'s
  release validation is **green**: the SemVer gate skips as a first
  publication and `cargo publish --dry-run` packages and verifies it, so it is
  publish-ready. `ares-solid`'s validation reaches the same gate green and
  fails only at `no matching package named proteus-mat`, which is the registry
  link and not a pipeline defect. A deliberate bad-tag dispatch confirmed
  `identify` rejects a package this repository does not ship and skips every
  downstream job.
- **Remaining, and Trusted Publishing cannot be the first step.** crates.io's
  own documentation states the prerequisite outright: *"Your crate must already
  be published to crates.io (initial publish requires an API token)"*. There is
  no pending-publisher concept as PyPI has, so a not-yet-published name cannot
  be configured.
- **This was already documented, and I did not read it.** The atlas README's
  Publication section carries the same fact in a two-registry comparison table
  — crates.io "**No.** The crate must already exist; the first publish requires
  an API token", against PyPI's "**Yes**, through a *pending publisher*". I
  established it from the crates.io source after two failed documentation
  fetches instead of reading the stack's own map first, which is the first rung
  of the comprehension ladder. The finding is right; the route to it was waste,
  and the same table answers the Python-side ordering question directly.
- **Therefore the order is:** one token-authenticated first publish per new
  crate — `cargo publish -p proteus-mat`, then once that is on the index
  `cargo publish -p ares-solid` — performed by the account owner, since no
  credential exists in this environment and entering one is out of scope. Then
  Trusted Publishing is configured on each crate's Settings page (owner
  `ryancinsight`, repository `proteus` / `ares`, workflow `rust-release.yml`,
  environment `crates-io`), and every release from the second onward runs
  through the pipelines already built and validated.
- **The pipelines are not wasted work by that ordering.** Their `--dry-run`
  validation is what establishes the package is publishable, and it is green
  for `proteus-mat` today; they are the mechanism for every subsequent release
  and for `ares-operator` and `ares-coupling` when those become publishable.
- **`ares-operator` and `ares-coupling` are not part of A9** and cannot publish
  yet regardless: `ares-coupling` depends on `harmonia`, which the publish scan
  reports as `publish = false`.
- **ADR 0059 correction owed:** it states the marshalling contract as
  "interface node index major, component minor" throughout. That is right for
  displacement and wrong for traction, which is per facet because the fluid
  side computes one per face. The implementation carries both orderings and the
  ADR should be revised to match rather than the code bent to it.
- **Harmonia finding:** `Substep` has no public constructor, so an external
  partition's `advance` is reachable only through Harmonia's own two-partition
  driver. `ares-coupling` routes the work through an inherent method so a test
  about the physics need not stand up a driver first; a public test constructor
  or a single-partition driver would remove the workaround.
- **known gap closed:** CI, hooks, and the lockfile guard landed at `45f3eec`
  under `#ares-ci-floor`, which is in review pending its first hosted run.

[ares ADR 0001]: https://github.com/ryancinsight/ares/blob/main/docs/adr/0001-athena-seam-as-a-separate-crate.md

- **risk:** analytical oracles are the only safety net; no reference
  implementation exists to difference against. Mitigated by oracle breadth and
  by the exactness of the patch and rigid-body tests.
- Kwavers elastic-wave migration is Phase 1; Phase 0 does not block on it.

## ATLAS-PUBLISH-ORDER-OPTIONAL-EDGES-2026-09-04 - Decide whether optional dependencies constrain publish order [patch] - in-progress <a id="publish-order-optional-edges"></a>

- **outcome:** a recorded decision, and a publish order that emits a usable
  sequence for the whole stack rather than a 61-package cycle.
- **found:** `#publish-order-workspace-deps` restored dependency edges the
  order had been dropping, and the restored graph is cyclic - but only through
  optional edges. `moirai-gpu` optionally depends on `hephaestus-wgpu`/`-cuda`,
  which reach `moirai-runtime`, closing a loop that no build ever realizes
  because the features are not co-enabled. Recomputed without optional
  dependencies the graph is acyclic and every crate orders.
- **the question:** `cargo publish` records optional dependencies in the
  registry index, so an optional first-party dependency arguably must publish
  first; but an optional edge that closes a cycle cannot be satisfied in any
  order, so treating them as ordering constraints makes first publication
  impossible. Both readings cannot hold.
- **acceptance:** an ADR recording the decision; the tool emits a total order
  under it; a fixture cyclic-through-optional graph is handled as the ADR says.
- **class:** `[patch]`. **risk:** medium - it gates any first publication of
  the stack, and therefore Ares A9. **depends on:** nothing.

- **integrator:** claude-opus-5 (this session). **Drafting ADR 0060
  `0060-publish-order-optional-dependencies.md`**; the decision is that
  optional dependencies are *not* ordering constraints for first publication
  because (a) `cargo publish` does not require an optional dependency to be on
  the registry at publish time — the published metadata records the dep string
  and an `optional` flag, and the dependency is unresolved while the feature
  is off, which is the entire purpose of `optional = true`; (b) the
  cycle-through-optional is a fixture of feature co-activation patterns that
  no real build ever co-enables (the peer-recorded case is `moirai-gpu →
  hephaestus-wgpu → moirai-runtime`, where `moirai-gpu`'s GPU feature and
  `moirai-runtime`'s GPU transport are independently gated and never on in
  the same `cargo build`); (c) the required-only graph is already acyclic, so
  the cycle only exists when feature-gated edges are *counted* as ordering
  constraints. The script's exit code should be 0 when the only unresolved
  SCCs are reachable exclusively through optional dependencies; today it is
  1, which makes the tool refuse the legitimate order it printed.

- **expected fixture behavior:** the optional-edges cycle's member count is
  `len(order_edges[n] & selected) > 0` for every `n in unresolved`, AND every
  edge in the SCC carries `optional = true` in its source manifest. The
  script separates the two cases today (it prints different messages for
  required-only vs required-and-optional cycles); it just does not act on
  the separation at the exit code.

## ATLAS-PROMETHEUS-PROMOTION-2026-09-03 - Create and register `prometheus` (species mass balance) [arch][minor] - in-progress <a id="prometheus-promotion"></a>

Charter: [ADR 0058](docs/adr/0058-prometheus-phase-0-charter.md). Path:
[ADR 0056](docs/adr/0056-new-construction-promotion-path.md).
Execution steps: `checklist.md` `ATLAS-PROMETHEUS-PROMOTION-2026-09-03`.

- **outcome:** `prometheus` owns homogeneous reaction networks - species,
  stoichiometry, mass-action rate laws, Arrhenius through Proteus, net
  production rates, reaction enthalpy - integrated 0-D through Horae.
- **non-goals:** reactive-transport discretization (stays with the balance
  owner of the field), combustion closure, surface and heterogeneous reactions,
  plasma chemistry, electrochemistry, phase equilibrium.
- **registry name:** `prometheus-kinetics`; bare `prometheus` on crates.io is
  the metrics client and is unavailable. Verified free (HTTP 404) 2026-09-04.

| Phase | Deliverable | Acceptance oracle | Depends on |
| --- | --- | --- | --- |
| P0 | aequitas gains `ReactionRate` and `MolarFlux` | `MolarConcentration / Time == ReactionRate` at the type level | `#aequitas-reaction-quantities` |
| P1 | Repository scaffold, same floor as A1 | same gate | P0 |
| P2 | **Ask-User:** create `ryancinsight/prometheus` | repository exists | P1 |
| P3 | Species and stoichiometry over Leto | transpose(nu) times M equals zero, structurally, for a balanced network | P2 |
| P4 | Rate laws; Arrhenius via `proteus::TemperatureResponse` | first and second-order closed forms; ln k against 1/T recovers Ea and A | P3 |
| P5 | Net production and reaction enthalpy | hand-computed networks | P4 |
| P6 | 0-D integration through Horae, including the stiff path | equilibrium reaches K_eq; **Robertson benchmark**; mass conserved; no negative concentrations; integrator order recovered | P5 |
| P7 | Register in atlas, as A7 | architecture test green | P6 |
| P8 | First consumer: Kwavers sonodynamic species kinetics across Harmonia | coupled therapy case runs | P7 |
| P9 | **Ask-User:** publish `prometheus-kinetics` | registry install and smoke; docs.rs | P8 |

- **status 2026-09-04:** P0 done (aequitas `#50`). The local `repos/prometheus/`
  tree carries the full Phase 0 computation — P1 floor, P3
  species/concentration/stoichiometry, P4 typed mass-action rates, P5
  net-production/reaction-enthalpy, P6 integration (first-/second-order decay,
  reversible equilibrium, convergence order, conservation, non-negativity, and
  the Robertson stiff benchmark against cited INdAM-Bari reference values via
  the Horae implicit seam). Gate green: fmt, clippy `-D warnings`, 33 tests,
  doc `-D warnings`. Eleven local commits `aea52ff..4c176ef`. **P2 (create
  `ryancinsight/prometheus`) is still Ask-User**; the commits push once it
  exists. Phase 0 computation is complete; the remainder is P2/P7/P9 delivery
  and the P8 Kwavers consumer.
- **P8 audit 2026-09-06 (corrected):** the two-file claim was a partial search.
  The real network is `kwavers-physics/src/chemistry/` — a full hand-rolled
  implementation: `reactions.rs` (`ChemicalReaction`, `Species`, `ReactionRate`
  as raw structs), `reaction_kinetics/`, `integrator/` (bespoke),
  `ros_species/` (a `ROSSpecies` enum + `ROSConcentrations` of `Array3` fields),
  `photochemistry/`, `radical_initiation/`, `ros_plasma/`, `validation/`.
  Prometheus replaces the network layer (`Species`, `ChemicalReaction` →
  `ReactionNetwork`, kinetics → mass-action + Arrhenius through
  `proteus::TemperatureResponse`, integrator → Horae); Kwavers keeps the
  transport layer (`Array3` spatial fields, `diffusion/` — the field owner's
  discretization per ADR 0058). The raw `constants/chemistry.rs` values and the
  bubble-dynamics Arrhenius are two inputs to the same module, not the whole.
  Consumer closure (the Species swap must convert atomically): the `chemistry/`
  network files themselves, two `kwavers-physics` callers (bubble-dynamics
  `chemical_reaction.rs`, sonoluminescence `spectrum.rs`), and the
  `kwavers-therapy` orchestrator (`chemical.rs`, `initialization/modalities.rs`).
  `diffusion/` and the `Array3` transport stay in Kwavers.
  **Queued:** the migration lands in a Kwavers lane, but Kwavers is at the
  two-tree bound — main plus a live `kwavers-elastic-computed` lane on
  `docs/kw-branch-inventory` (active seconds ago). Re-open when that lane's
  item completes or goes stale.
- **historical prerequisite retired:** the Kwavers reaction-vocabulary
  consolidation existed to produce a deletion ledger; under ADR 0056 that
  ledger arrives with the P8 consumer migration. It remains worthwhile on its
  own merits but no longer blocks.
- Prometheus is the first embedded-stepping consumer for Horae, retiring a
  capability recorded as consumer-gated with no caller.

## ATLAS-NEXT-STEPS-2026-09-03 - Sequenced plan toward the suite [arch] - planning <a id="next-steps"></a>

Atlas is a shared location; members compose as needed.

**First-party boundary.** First-party ownership targets **stack concerns** -
scalars, quantities, arrays, allocation, scheduling, placement, accelerators,
numerics, physics - where a third-party dependency costs correctness control
and the ability to fix upstream. It does **not** target the **shell boundary**:
a frontend framework (Tauri, egui) is ecosystem-solved, sits outside the
safety-relevant core, and reimplementing one enlarges the verification surface
of a regulated product for no gain. The dual frontend and backend split is the
asset - it puts document state, validation, units, and solver orchestration on
the Rust side of the IPC line. That is per-product integrator work, not a stack
package. The same reasoning admits `wgpu`, DICOM, and format libraries at their
boundaries and refuses `nalgebra`, `ndarray`, `rayon`, and `num-traits` inside
the stack (ADR 0055 substrate contract).

| # | Increment | Repo | Class | Status |
| --- | --- | --- | --- | --- |
| 1 | Delete the CFDrs elastic copy; compose `proteus::IsotropicSolid` | CFDrs | `[patch]` | done (`f063be4b`) |
| 2 | Delete the kwavers elastic copy | kwavers | `[minor]` | done for A0 (`1f86a9172`); residual `computed.rs` formulas |
| 3 | aequitas stress semantics marker | aequitas | `[minor]` | done (`#50`) |
| 4 | aequitas `ReactionRate` and `MolarFlux` | aequitas | `[minor]` | done (`#50`) |
| 5 | Architecture test R7 and `cargo deny bans` substrate list | atlas | `[patch]` | delivered 2026-09-04 (`4a574a801`); live-balance enum in WT |
| 6 | Ares A1 through A9 | ares | `[arch]` | A0-A8 done; A9 blocked on unpublished `proteus-mat` |
| 7 | Prometheus P1 through P9 | prometheus | `[arch]` | Phase 0 computation done (11 commits, Robertson included via the Horae implicit seam); **Ask-User** for `ryancinsight/prometheus` |

Steps 1 to 5 are mutually independent and can run concurrently on disjoint
scopes.

**Not in this plan:** no GUI package, no universal model tree, no in-stack UI
framework. The application layer stays per product behind the IPC boundary of
each tool.

## ATLAS-SUBSTRATE-CONTRACT-MEASURED-2026-09-03 - The contract is already satisfied; the guard is preventive [patch] - todo <a id="substrate-contract-measured"></a>

Measurement before mechanization, per ADR 0055's substrate contract.

**Current violations across all 25 registered members: zero.** Scanning every
`Cargo.toml` in every member for `nalgebra`, `ndarray`, `rayon`, and
`num-traits` returns two hits, and neither is a violation:

| Hit | Verdict |
| --- | --- |
| `moirai` | `rayon` appears only in `[dev-dependencies]` of `moirai-parallel` and in comparison benchmarks and examples (`moirai_vs_tokio_rayon_comparison`, `rayon_parallel_patterns`). This is the sanctioned interop-or-comparison-target role: rayon is the baseline the first-party provider is measured against. |
| `leoneuro-rs` | Not a registered stack member; absent from `.gitmodules`. Outside the contract's scope. |

So the guard is **preventive, not remedial** - it locks in a property the stack
already has rather than opening a burn-down. That also fixes its shape: deny
these crates in runtime `[dependencies]` only, and permit `[dev-dependencies]`,
benches, and examples, because forbidding the comparison baseline would forbid
measuring the first-party provider against the thing it replaces.

**Implementation is not a new tool.** `cargo deny` already performs exactly this
check through a `[bans]` section, every member already carries a `deny.toml`,
and CI already runs a supply-chain job. Building a bespoke checker would
duplicate a capability the stack has.

**Blocked on region occupancy, not on design.** The two candidate homes are
both under live peer edit: `scripts/atlas-conformance.py` and its test file are
dirty, and `tools/version-guard/` likewise. A per-member `deny.toml` sweep is
the remaining route, but 25 near-identical `deny.toml` files are themselves the
fleet-scale duplication defect the conformance scan exists to catch - so the
sweep should land one stack-level `[bans]` definition that members inherit,
which is a decision about shared-config ownership rather than a mechanical
edit.

- **re-open trigger:** the conformance script leaves peer hands, or a decision
  on where the shared `[bans]` definition lives.
- **note:** this supersedes nothing in `#archtest-balance-edges`; R7 (no
  balance-to-balance edge) still needs the architecture test, and no such test
  exists in `tools/` today - the tools are `_template`,
  `checkout-path-dependencies`, `criterion-regression`, `gitlink-coherence`,
  and `version-guard`.

## ATLAS-ARCHTEST-BALANCE-EDGES-2026-09-03 — Mechanize the ADR 0055 boundary rules [patch] — substrate delivered 2026-09-03; R7 delivered 2026-09-04 <a id="archtest-balance-edges"></a>

- **outcome:** ADR 0055's rules fail the build instead of awaiting review.
  Extend the existing `cargo metadata` architecture test with R7 (no
  balance-to-balance dependency edge; coupling routes through `harmonia`), and
  extend `cargo deny bans` with the substrate-contract prohibition list
  (`nalgebra`, `ndarray`, `rayon`, `num-traits`) for the continuum packages.
- **scope:** the atlas architecture test and the shared `deny.toml` surface.
- **acceptance oracle:** a fixture edge from a balance package to another
  balance package fails the test; the current stack passes unchanged.
- **risk/class:** `[patch]`. **dependencies:** none — the rules are checkable
  against the present stack even before Ares or Prometheus exist, which is the
  point: the guard predates the code it guards.

**Substrate contract: delivered** at `f15418551` as the
`substrate_contract_violations` ratchet class in the conformance scan, with 11
tests and a mutation check. Zero violations fleet-wide, so it is preventive.
Implemented in the scan rather than as `cargo deny [bans]`: cargo-deny has no
config-include mechanism, so a bans list would need copying into 25 member
`deny.toml` files - the fleet-scale duplication defect the scan exists to
catch. The scan checks the property itself (a member's resolved runtime
dependency tables) rather than checking that 25 config files agree.

**R7 — delivered 2026-09-04 at `4a574a801` (this session).** The prior
deferral was a recommendation, not a prohibition, and the substrate-contract
delivery proved the preventive pattern. The check lives in
`scripts/atlas_architecture_test.py` alongside the substrate scan, exposed as
the `balance_domain_edges` ratchet class inside `atlas-conformance`, sharing
the existing manifest-parsing machinery. The boundary tables encode ADR 0055
directly: `BALANCE_DOMAINS` (empty today; grows at `ares`/`prometheus`
registration), `COUPLING_LAYERS` (`harmonia`), `CLOSURE_DOMAINS` (`proteus`).
Acceptance oracles all green:

- fixture `ares -> CFDrs` edge fails the rule (simulated in
  `FutureBoundarySimulationTests`);
- the live stack (no balance packages exist yet) passes vacuously;
- coupling-routing assertion forbids any direct cross-balance edge and
  names `harmonia` as the sanctioned multi-balance coupling layer.

Verification artifact:
[`docs/audit/2026-09-04-r7-architecture-test.md`](docs/audit/2026-09-04-r7-architecture-test.md).
Test totals: 27 architecture-test cases, 64 conformance cases (unchanged),
91 cases pass. End-to-end `report --worktree` and `check --worktree --json`
both green at zero violations across 25 members. `render_baseline` reproduces
the committed baseline byte-for-byte (generator contract preserved).

**Future boundary additions.** When `ares` lands, add its `[package] name`
to `BALANCE_DOMAINS` in `scripts/atlas_architecture_test.py`; the same
applies to `prometheus`. Both add one line; the rule's discrimination is
proved in isolation by the simulation class above.

- **note:** R1 and R2 are grep-shaped and belong in the conformance scan
  (`scripts/atlas-conformance.py`) rather than the architecture test.

## ATLAS-PROTEUS-ELASTIC-SSOT-2026-09-03 — Proteus owns the isotropic modulus conversion contract [minor] — in-progress <a id="proteus-elastic-ssot"></a>

- **integrator:** claude-opus-5 (this session)
- **regions:** `repos/proteus/src/elastic/**`, `repos/proteus/tests/elastic.rs`
  (provider). Consumer regions are unleased and unclaimed; both consumer trees
  verified clean (`git status -s` empty in each).
- **outcome:** the `(E, nu) <-> (lambda, mu) <-> (c_p, c_s)` contract and the
  named isotropic-solid catalog land in Proteus, and CFDrs plus Kwavers delete
  their copies. This is the recorded P2-B `ares` prerequisite in the stack map
  (README "Required consolidation result"), not a repository promotion.
- **acceptance oracle:** zero isotropic modulus-conversion arithmetic outside
  `proteus::elastic`; consumer differentials agree with the provider inside the
  derived tolerance; `rg 'lame_from_speeds|E / \(2 \* \(1'` returns provider
  hits only.

### Provider slice — merged

`ryancinsight/proteus` PR #29, merged to `main` as `1726082`. Local gate at the
identical tree: `cargo fmt --check` clean; `cargo clippy --all-targets` clean at
the pedantic floor; `cargo nextest run` 44/44 (24 new, 20 pre-existing
unaffected); `cargo test --doc` 2/2; `cargo doc --no-deps` clean.

**Collection pending:** the merge-gate CI run on proteus `main` was still queued
at hand-off; collect it at the next orientation and treat a red as the priority
item.

**Infrastructure finding — proteus has no required status checks.** `gh pr merge
--auto` landed #29 immediately while `verify`, `MSRV`, `SemVer gate`,
`supply-chain`, and `Lockfile integrity` were all still QUEUED, so the merge gate
did not gate anything. This is the same class as
`ATLAS-SEMVER-GATE-FLEETWIDE-2026-08-28` (checks adopted fleet-wide) but at the
branch-protection layer: adopting the workflow does not enforce it. Ruleset
configuration is a Change-grant merge-mechanic via `gh api`; audit every member
for the same gap rather than fixing proteus alone.

**Atlas gitlink:** `repos/proteus` still points at `930208f` and needs advancing
to `1726082`. Not done here — the meta-repo gitlinks are mid-flight under a live
peer (`MM repos/*` staged at 2026-09-03 14:30).

### Evidence correction to the stack map

**SUPERSEDED 2026-09-03 by a fuller source audit — see the correction note at
the end of this section.** The original text follows.

The README P2-B `ares` row records that "CFDrs and Kwavers duplicate isotropic
modulus conversions **and steel/aluminum catalogs**". The first half holds; the
second does not. The catalogs name **different alloys**:

| | CFDrs `ElasticSolid` | Kwavers `constants/implants.rs` |
| --- | --- | --- |
| "steel" | plain carbon steel, rho 7850, E 200 GPa, nu 0.30 | stainless 316L, rho 8000, c 5960 m/s |
| aluminium | 6061, rho 2700, E 70 GPa | alumina (a ceramic), rho 3970 |

Kwavers's implant constants carry density and sound speed, not `(E, nu)`, so
they are not elastic-catalog duplicates at all. Consolidating the two catalogs
under one "steel" entry would have silently substituted alloy constants. The
provider therefore keys entries by grade (`CarbonSteel`, `StainlessSteel316L`,
`Aluminium6061`, `TitaniumGrade5`) and a regression test asserts the two steel
grades stay distinct. **The genuine duplication is the conversion algebra
only.** The stack-map row should be corrected when the consumer slices land.

### Remaining — consumer deletion slices

1. `CFDrs`: `crates/cfd-core/src/physics/material/{solid.rs,traits.rs}` — delete
   the `shear_modulus` default and the `steel()`/`aluminum()` elastic constants;
   `ElasticSolid` composes `proteus::IsotropicModuli`.
2. `kwavers`: `crates/kwavers-medium/src/elastic.rs` `lame_from_speeds` and
   `crates/kwavers-medium/src/properties/elastic/constructors.rs`
   `try_from_engineering`/`new` — delegate to the provider, keeping the
   `ElasticProperties`/`ElasticArrayAccess` grid traits, which are operators and
   stay consumer-side.

**Ordering constraint (co-evolution protocol):** both consumers depend on
`proteus-mat` by `git`+`version`, so the provider branch must merge to proteus
`main` before either slice can resolve standalone or in CI. Under the stack
development overlay the local tree already resolves, which would hide the gap —
so the slices are sequenced after the provider merge, not run against the
overlay.

Blast radius measured, not assumed: `cfd-core` already declares
`proteus.workspace = true`, and `ElasticSolid`/`SolidProperties` have exactly
one caller outside their defining module
(`crates/cfd-core/src/physics/mod.rs:81`, a re-export). Slice 2 additionally
needs a review pass: the provider's positive-definite domain admits `lambda < 0`
where Kwavers's `ElasticPropertyData::new` rejects it, so any Kwavers caller
relying on that rejection changes behaviour.

### Non-goals

Creating `prometheus` or `ares`. `prometheus` is the stack's reaction-network
candidate, not the structural-mechanics one; `ares` is the solid-mechanics
candidate and its gate stays unmet until a second integrator can consume the
same solid-kinematics or balance operator. See ADR 0030 and the README P2-B
table.

### Kwavers slice — pushed

`ryancinsight/kwavers` branch `refactor/elastic-ssot-consumer`, commits
`ab9ddf8fb` and `051afb1e2` (Cargo.lock regen), PR #707 open. Deletes
`lame_from_speeds` in `kwavers-medium/src/elastic.rs`; delegates
`ElasticPropertyData::new` to `IsotropicModuli::from_lame` and
`try_from_engineering` to `from_young_poisson`; updates the three call
sites in `homogeneous/implementation/constructors.rs`,
`heterogeneous/factory/general/elastic.rs`, and the elastic_plugin test.
The `elastic_homogeneous` constructor preserves its `c_shear * c_shear *
2.0 > c_compression * c_compression` rejection (kept at the call site,
not delegated) so auxetic solids stay rejected there; the heterogeneous
constructor's per-voxel rejection agrees on the same boundary; the fluid
limit `c_s = 0 ⇒ μ = 0, λ = ρ·c_p²` short-circuits before the provider
because `from_wave_speeds` requires finite-positive shear-wave speed.
`ElasticPropertyData::new` accepts `lambda < 0` (provider's positive-
definite domain is `K = lambda + 2mu/3 > 0`, wider than kwavers's old
`lambda >= 0`); callers that need the stricter bound check at the call
site or use `set_lame_parameters`, which still rejects. Gates: 215/215
`kwavers-medium` tests, 1562/1562 `kwavers-physics` tests, 4/4
`elastic_plugin` tests. Acceptance oracle `rg 'lame_from_speeds|E /
\(2 \* \(1'` in `repos/kwavers/crates` and `repos/CFDrs/crates` returns
zero hits; the only remaining reference is the kwavers-bodied
differential test comment in `proteus/tests/elastic.rs` (kwavers's
`lame_from_speeds` body that this test replaced).

### Collection pending — CFDrs slice + atlas gitlinks

The CFDrs slice (`f063be4b refactor(cfd-core): Delete the elastic copy;
compose Proteus`) sits on `refactor/elastic-ssot-consumer` in
`ryancinsight/CFDrs`, unmerged to CFDrs `main`. Atlas's recorded
`repos/CFDrs` pin is still pre-slice (`f7fb9b5f`); advancing it requires
the CFDrs PR to merge first. The atlas gitlink for `repos/proteus`
already advanced to `1726082` via `7224f505f chore(atlas): Advance the
members that moved`. Both atlas pin advances land in the same co-
evolution unit when CFDrs merges.


## ATLAS-RUNNER-STARVATION-2026-09-02 — Hosted runner queue starves every verification run [infra] — todo (Ask-User)

- **Re-measured 2026-09-09 17:48 UTC -- the queue is no longer slow, it is
  stopped.** Every one of the last nine kwavers runs is `queued` with zero jobs
  started; the oldest was created 16:44 and had waited **64 minutes** at the
  time of reading, the newest 17 minutes. The only non-queued run in the window
  is `cancelled`. `gh api repos/ryancinsight/kwavers/actions/runners` reports
  `total_count: 0`, so nothing self-hosted can absorb this, and every workflow
  targets `ubuntu-latest`. The 2026-09-02 numbers below measured a slow queue;
  this is a stationary one, which reads as a spending cap, a billing stop, or a
  platform outage rather than depth -- `gh` cannot tell which, because the
  billing endpoint needs a `user` token scope this session does not carry
  (refreshing auth scope is itself an Ask-User change).
- **Consequence for delivery, per the standing unavailability rule:** the venue
  is down, not the verification. Code work continues on the local pre-push gate
  (kwavers#754 landed it: fmt, clippy, and affected tests in 9s). The exception
  is a change *to* a workflow, whose only real gate is CI itself -- kwavers#755
  is held open rather than admin-merged for exactly that reason, since no local
  evidence can stand in for it.
- **Ask-User, second question alongside the runner registration below:** is
  there a spending cap or billing stop on the account? Nothing merges through
  hosted verification until it lifts.
- **Measured 2026-09-02 17:40 UTC, job-level queue wait (job `started_at` minus run `created_at`), 56 jobs across atlas and kwavers:**
  median 447 s, p90 2146 s, max 44.7 min. The longest waits are kwavers's own gates — Memory Safety (Miri) and Solver Validation Suite
  both 44.7 min, Heavy Validation 39.7, Code Quality 37.4. Stack-wide at that moment: 10 runs queued, 3 running.
- **What that costs:** the workflow-hygiene target is five minutes of *runtime* per verification job, and the median job waits longer than
  that before it starts. Today's seventeen SemVer-gate adoption pull requests took over an hour to clear the queue, and this session's
  merge waiters spent their time on queue rather than on checks. A job queued past its own runtime target is starvation by the standing
  rule, cured by capacity or by load-shedding, not by waiting.
- **The decision is still the user's** (registering a runner is an access change): a self-hosted runner on the local machine would take
  both the queue wait and the metered minutes to zero for private repositories, and the same registration with a `cuda` label would
  un-dark kwavers's GPU parity oracles, whose scheduled run is cancelled every night having never been assigned a runner.

- **Finding (2026-09-02):** with ~25 small PRs and the peers' pushes in flight, every job across the organization sat `queued` for tens of minutes to over an hour: kwavers#687 timed out a 60-minute merge gate with 27/29 checks green and two still queued; kwavers#691 shows 21 of 29 checks pending after an hour; atlas's own conformance runs queued for hours (`fb616d9f`, `7264f91e`). The queue-time rule (engineering_gates: workflow hygiene) makes a job queued past its runtime target an infrastructure defect, not agent waiting — and it is what turned today's shared-group cancellation into a class (`ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02`): pending runs superseding each other only bites when nothing ever starts.
- **Cure:** capacity or load-shedding. Load-shedding already applied today: path-filtered adoption workflows, staged waves. Load-shedding still owed by members: consus runs 81 checks per pull request (Check × 15 packages, Test × packages, MSRV × 15, fuzz builds) — a matrix that recompiles per cell instead of one archive sharded across runners (engineering_gates: build-once topology); a consus row. Capacity is the standing policy for private repositories and trusted-contributor stacks: a self-hosted runner on owned hardware with a persistent warm `CARGO_TARGET_DIR`/sccache, so no run pays cold setup or a metered minute. **Ask-User:** register one or more self-hosted runners at the organization level (labels `self-hosted, linux, x64`; the RTX 5080 host can also carry the `cuda` label the kwavers GPU-parity schedule already targets) — `gh` cannot register runners (hosting/security setting). Until then the waves stay staged and merge gates re-launch at their cap.
- **Acceptance oracle:** `gh run list --json createdAt,startedAt` across the stack shows median queue time under the five-minute job target; the kwavers `GPU Parity (scheduled)` row in `ATLAS-DEFAULT-BRANCH-REDS-2026-09-02` turns green.

<a id="atlas-overlay-worktree-keyed"></a>

## ATLAS-OVERLAY-WORKTREE-KEYED-2026-09-06 — The overlay gate compares a committed artifact against a generation from uncommitted inputs [arch] — review

- **Integrator:** claude-opus-5; **branch:** none (atlas main);
  **lease:** `scripts/atlas-stack-overlay.py` 2026-09-06T21:40Z.
- **Last-update:** 2026-09-06.
- **Measured.** `atlas-stack-overlay` has failed on main at `57e2a81b`,
  `81dc17a9` and `be2d1444`, every time with the same body: `OVERLAY: overlay
  differs from a fresh generation`, `0 lagging requirement(s), 0 repo(s) with
  pin drift`. Regenerating locally and committing the result (`81dc17a9`, which
  added the missing Moirai `[patch]` sections) did not clear it.
- **Why it cannot clear.** The generator discovers the closure by globbing
  `**/Cargo.toml` under each `repos/<member>` **worktree**, and emits a patch
  entry only where the local version satisfies the consumer requirement
  (`LagAwarePatchEmissionTestCase`). CI checks the submodules out at their
  recorded gitlinks. Every member tree ahead of its gitlink — the normal state
  during development; nine of ten were ahead when this was measured — feeds the
  generator different versions than CI validates against, so a developer's
  regeneration and CI's disagree by construction. The gate is unsatisfiable in
  steady state, and each gitlink advance re-reds it.
- **Outcome.** Key the closure to the revision, as `atlas-conformance.py`
  already does with `--revision`: read each member's manifests at its recorded
  gitlink (`git show <sha>:<path>`) rather than from its worktree, so the
  overlay is a pure function of the superproject commit and both CI and any
  developer generate the same bytes. The emitted paths stay `repos/<name>` —
  the overlay still points at local trees, which is its purpose; only closure
  *discovery* becomes revision-keyed.
- **The stated outcome was built and falsified, 2026-09-06.** Revision-keyed
  closure was implemented (manifests via `git show <gitlink>:<path>`, listing
  via `ls-tree`, worktree fallback on an unreadable gitlink) and generated a
  deterministic overlay — 104 lines different from the committed one, because
  at the gitlinks Moirai is 0.5.0 where the worktree is 0.6.0, which flips
  every lag verdict that depends on it.
  
  That determinism is bought at the cost of the overlay's purpose. Its emission
  decision is "can the local tree satisfy this requirement", and cargo answers
  that question against the **worktree** when it resolves. Keying the decision
  to the gitlink makes the file describe a state cargo does not see: it can
  emit a patch the worktree cannot unify (a resolution failure) and, more
  commonly, withhold a patch that would have worked — so the overlay stops
  pointing at local trees exactly while those trees are being developed, which
  is the one case it exists for. The change is reverted, unlanded.
- **The unsatisfiability premise is falsified, 2026-09-09.** The claim above
  was that dev worktrees feed the generator different versions than CI
  validates against, so the gate can never clear. Measured directly across all
  26 members — every non-output `Cargo.toml`, worktree content against the same
  path at the member's `origin/HEAD`, comparing the generator's actual inputs
  (manifest path, package name, version) — **zero members differ**, with several
  trees sitting on feature branches at the time. Feature work does not move
  package versions or manifest paths; only a deliberate release bump does, and
  a bump is pushed. So developer and CI regenerations agree, and the earlier
  gitlink-keyed experiment was falsified for the right reason but generalized
  to the wrong conclusion: the gate is keyed to member *default heads*
  (`submodule update --remote`), not to gitlinks, and default heads are what
  the worktrees track.
- **What the gate was actually reporting.** The committed overlay carried no
  `[patch]` section for leto, ritk, coeus, hephaestus, consus or tyche. Each had
  been withheld by lag-aware emission while its local tree could not satisfy a
  consumer requirement, and nothing regenerated the file once the Moirai sweep
  made them satisfiable. Every local build in the stack was therefore resolving
  those six providers from git rather than the local trees — the overlay not
  applying to six of the providers it exists for, silently. Regenerated and
  committed at `49d633852`; the equality clause is kept, because it is the only
  clause that detects this state.
- **Standing risk this leaves.** A developer holding an unpushed version bump
  regenerates differently from CI. That is the gate working — the bump has to
  be pushed — not a contradiction, and it is transient by construction.
- **Confirmed by the gate itself, 2026-09-09.** The run on `49d633852` no
  longer emits the `OVERLAY:` clause at all; its failure is now one requirement
  lag and eight locks, both revision-meaningful and both owned by
  the apollo pin (apollo#385). CI's regeneration and
  the worktree regeneration agree byte for byte, which is what the equality
  clause asserts — so it is kept. Dropping it, as this item previously
  recommended, would have removed the only clause that detects an overlay
  silently withholding providers.
- **Risk / change class:** [arch] [patch]; derived-state definition, no
  member change.

## ATLAS-DEFAULT-BRANCH-REDS-2026-09-02 — Member default-branch workflows red with no collector [patch] — todo

- **Finding (first `atlas-red-workflows.py` pass, 2026-09-02):** each row is a default-branch workflow whose newest completed run is not green; nobody had collected any of them. Each row is claimable on its own: classify (stale release attempt, rotted job, starved schedule), fix the component or retire the job, and the collector's next pass is the oracle.

| repo | workflow | conclusion | run | note |
| --- | --- | --- | --- | --- |
| gaia | Crates.io Release | failure | [`a5b0fe72` 2026-08-11](https://github.com/ryancinsight/gaia/actions/runs/31462176421) | manual `workflow_dispatch` release attempt; log carries no failing step. Release is the user's action; the workflow itself is `ATLAS-PUB-001` scope (blocked) |
| iris | Crates.io Release | failure | [`ab3eea28` 2026-08-11](https://github.com/ryancinsight/iris/actions/runs/31462174822) | same class as gaia's: manual dispatch 2026-08-11, `ATLAS-PUB-001` scope |
| kwavers | Crates.io Release | failure | [`278af2ea` 2026-08-09](https://github.com/ryancinsight/kwavers/actions/runs/31316302910) | same class: a stale release dispatch, `ATLAS-PUB-001` scope |
| kwavers | GPU Parity (scheduled) | cancelled | [`bd7e6fa6` 2026-09-01](https://github.com/ryancinsight/kwavers/actions/runs/33463119860) | runner starvation: `runs-on: [self-hosted, linux, x64, cuda]` and no such runner is registered online, so every nightly run (`17 2 * * *`) queues 24 h and GitHub expires it — cancelled 08-30, 08-31, 09-01; 09-02 queued now. **Ask-User:** register a self-hosted CUDA runner for kwavers on the RTX 5080 host (`gh` cannot register runners; hosting/security setting), or pause the schedule until one exists |
| mnemosyne | Fuzz | failure | [`247057ed` 2026-09-02 (#97's new workflow, first run)](https://github.com/ryancinsight/Mnemosyne/actions/runs/33591989913) | `E0463: can't find crate for core` — `cargo fuzz` builds std via `-Zbuild-std`, which needs the `rust-src` component dtolnay's action omits; fix mnemosyne#102 merged; the next default-branch `Fuzz` run is the oracle **RESOLVED:** `Fuzz` run `33600789737 success` at `fdf6654` (2026-09-02); the row no longer appears in `atlas-red-workflows.py` |
| apollo | ci | failure | [`6d205280` 2026-09-02](https://github.com/ryancinsight/apollo/actions/runs/33592017580) | the SemVer gate the user's #266 wired in fails on public-surface breaks of `WgpuError` in `apollo-mellin` (vs published 0.11.0) and `apollo-ntt` (vs 0.9.0) — the gate working as designed. **Ask-User:** breaking changes under a non-major version: bump `apollo-mellin`/`apollo-ntt` to their next major (release authority) or record a gate baseline for the intended break; the gate's `informational` twin already skips |
| kwavers, mnemosyne, apollo | CI / Architecture Validation / pages-build-deployment | cancelled | `0d0a9d45`, `96c9ef6d`, `0bdbbe57` 2026-09-02 | not defects in the trees: default-branch runs superseded while pending by the next merge's run — the class filed as `ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02` |
| kwavers | Integration Suite (in `CI/CD Pipeline`) | failure | kwavers#691 run, 2026-09-02 | member test defects, not the workflow change: `pstd_finite_window_born::source_phasing_is_frechet_derivative` panics `no compatible accelerator adapter` on a CPU runner (a GPU-requiring integration test must select its backend by capability, typed absence on CPU — standards: runtime capability detection); `property_based_tests::test_grid_convergence` and `test_plane_wave_injection::test_plane_wave_boundary_injection_timing` hit the 60 s nextest termination bound (a performance defect in the system under test or an oversized workload — engineering_gates: test budgets). kwavers#691 landed on a later run (the suite passed), so these are nondeterministic. Root cause read from the source: `kwavers-diagnostics/.../breast_ust_fwi/dataset.rs` selects the PSTD backend at *compile time* — `#[cfg(feature = "gpu")]` runs `run_gpu_pstd_transmit` unconditionally and the CPU `PSTDSolver` path is compiled only without the feature — so `--all-features` on a runner without an adapter panics inside a test. Adapter absence reaches kwavers stringly typed (`KwaversError::InvalidInput("GPU device init failed: … no compatible accelerator adapter available")`, mapped from hephaestus in `kwavers-gpu`'s `map_hephaestus_error`). **DoR for kwavers:** (1) `kwavers-gpu` maps hephaestus's adapter-absence error to a typed `SystemError::ResourceUnavailable { resource: "GPU adapter" }` (every other GPU fault keeps its class); (2) the dataset generator compiles both paths under `gpu`, runs the GPU path and, on that typed absence only, surfaces the selection (`tracing`) and runs the CPU path — a present-but-failing device propagates; (3) a unit test of the selection on an injected absence, and the integration test then runs on CPU runners. The two 60 s timeouts (`test_grid_convergence`, `…_timing`) are the runtime-budget rule: profile the system under test, never widen the bound |
| horae | verify (Book tests) | failure | horae#31 run, 2026-09-02 | `mdbook test` fails `E0464: multiple candidates for rmeta dependency aequitas` — the rust-cache restore leaves two aequitas rlibs in `target/debug/deps`, and rustdoc's `-L` cannot pick; `main`'s last verify was green before aequitas moved. Deterministic (re-run reproduced it): three aequitas artifacts at different hashes — `.rmeta` from cached check/clippy runs beside the build's `.rlib`. Fix open as horae#32: stage the newest `.rlib`/proc-macro `.so` per crate into `target/booklibs` and point `mdbook test -L` there; horae#31 rebases onto it |
| athena | verify (allocation contracts) | failure | athena#26 run 33615456338, 2026-09-02 | `athena-leto/tests/allocation.rs:72` `repeated_cpu_solves_allocate_nothing_after_initialization` fails on a PR touching only `book-pages.yml`; `main`'s last two `verify` runs green — an allocation-count contract that is not deterministic under shared-runner load (see memory: allocation oracles under load). Member defect; the re-run passed (nondeterminism confirmed), athena#26 landed. Same class as the already-`#[ignore]`d GMRES sibling in that file ("Linux allocation flake (4 allocs, 900B retained) — warm solves allocate on hosted Linux but not Windows"): a lazily initialised per-thread structure in the warm path that only a Linux allocation trace can name; root cause is athena's, on a Linux host — a second `#[ignore]` would hide it, not fix it |
| mnemosyne | CI (SemVer gate, release gate) | failure | [`fdf66542` 2026-09-02](https://github.com/ryancinsight/Mnemosyne/actions/runs/33600786453) | the user's #107 merge; the release SemVer gate reports a public-surface break under a non-major version — the apollo class; it reds every `main` push since (seen again on the pin-bump merge `3b5a7857`). **Ask-User:** major bump or gate baseline |
| helios | benchmark regression check | failure | helios#81 run, 2026-09-02 | a workflow-only PR (guard adoption) flagged a "replicated regression" of +1.7 % then +0.4 % whose two run orders disagree in sign: identical code cannot regress, so this is the identical-code false-positive class apollo closed with `scripts/bench_executable_identity.py` (compare code sections; skip the timing gate when candidate and baseline binaries match). Fix: the comparer now lives in atlas (`scripts/bench_executable_identity.py`, `12a92b53`, ELF64-synthesizing tests); helios#83 records each `cargo bench --no-run` executable, compares baseline and candidate before timing, and skips the comparison (smoke still runs) when identical — its own gate is the oracle — first run: every pair `CODE IDENTICAL`, the measure step exited at its notice, and the replication classifier then failed on reports that were never written; second commit gates the classifier on the same output; landed `49950e89` with its own gate reporting identical code. helios#81 and #82 rebuilt onto it (#82 regenerated from current `main` by the cancel fixer — a whole-blob API rebase had carried the pre-#83 `ci.yml`, which would have reverted the gate; caught before any waiter ran); apollo#279 (merged; its identity gate reported identical code and skipped the pairs) retires apollo's vendored copy — one comparer stack-wide, run from the pinned atlas checkout in both gates |

- **Revision (2026-09-02):** gaia `Examples` dropped — that workflow no longer exists on `main`; the collector now reports active workflows only (`9235e47d`). mnemosyne `Fuzz` added.
- **Acceptance oracle:** `scripts/atlas-red-workflows.py` reports no member rows (atlas's own cancelled rows are the concurrency finding above, tracked there).
- **kwavers PSTD row — in progress (2026-09-02, integrator: claude-fable session 5050c72a; lane `worktrees/kwavers-pstd-backend`, branch `fix/kwavers-pstd-backend-by-capability`).** Design as built: hephaestus `AdapterUnavailable` maps to the existing typed `SystemError::GpuNotAvailable` (search before adding — the DoR's `ResourceUnavailable { resource: "GPU adapter" }` would have been a second, stringly spelling of a variant kwavers-core already owns) at one `map_hephaestus_error` boundary; the two other hephaestus boundaries (`GpuDevice::acquire_with_requirements`, the 3-D beamforming provider) that filed every fault as `ResourceUnavailable` consolidate onto it; `PstdAutoDeviceProvider::acquire_auto_context` and `with_auto_device` carry `KwaversError` instead of `String`; the dataset generator compiles both PSTD paths under `gpu` and `select_pstd_backend` runs the CPU path on that typed absence only. Both `pstd_finite_window_born` entries in kwavers's `.config/integration-test-baseline.txt` share this root cause (both call the dataset generator) and leave the baseline with the fix.
- **kwavers PSTD row — landed:** kwavers#694 (`78a1771e9`, rebase-merged 2026-09-02 13:48 UTC). Both `pstd_finite_window_born` entries left the known-failure baseline (now empty).
- **kwavers 60 s timeouts — in progress (same lane, branch `perf/kwavers-fdtd-staggered-kernels`).** Measured here: `test_grid_convergence` 19.4 s, `test_plane_wave_boundary_injection_timing` 24.9 s (the hosted runner is ~15x slower). Both bottom out in `FdtdSolver::step_forward`: 32.7 ms per 64³ step in release, the same at the tests' opt-level 1 — structural, not the profile: `StaggeredLeapfrogOperator::{gradient_into,divergence_into}` addressed every tap through bounds-checked linear indices and the staggered velocity update gathered neighbour densities per component per cell. Fix: slice-form kernels (windows along the contiguous axis, block zips along the others, `reflect` for walls, indexed path kept as the differential reference — gradient and wall cells bit-identical, gathered interior within `2·halo·ε`) plus face densities precomputed once. criterion (release, 64³): order 2 32.7 → 2.3 ms/step, order 4 33.7 → 3.4 ms/step. Instruments: `test_grid_convergence` enumerates its 16-point domain once (was 256 proptest draws); the plane-wave test monitors the window its assertion reads (was +500 steps). Re-timed: 0.34 s and 1.0 s; 85 solver FDTD tests and 25 FDTD integration tests green. The FDTD propagation bench was unregistered and rotted (no `criterion_main!`) — registered and repaired, 64³ step group added.
- **horae row — resolved upstream:** the failing run (07:11 UTC) predates horae `468a900` ("ci: Link the book tests against one artifact per crate"), which stages one rlib per crate into `target/booklibs`; main's CI at `28a13302` (09:46 UTC) is green. No atlas action.
- **athena row — blocked (2026-09-02):** root cause needs an allocation trace on a Linux host; this host has none (the WSL Ubuntu instance's disk image is missing — `ERROR_PATH_NOT_FOUND` on attach). Re-open trigger: a Linux host with cargo, or the flake recurring on main. The `#[ignore]`d GMRES sibling in `athena-leto/tests/allocation.rs` is the same defect.

- **Second collector pass (2026-09-10, basis atlas `1efd2f11e`):** ten rows, of which two were live member defects and both are fixed.
  - horae `CI` — `SolveError::NonConvergence` documented a link to the private `MAX_NEWTON_ITERATIONS`, so `cargo doc` under `-D warnings` failed `rustdoc::private_intra_doc_links`; red since 2026-09-09. Publishing the constant would be the wrong cure — its own doc says the bound is a guard, not a tuning knob — so the variant states the condition and marks the value an implementation detail. [horae#44](https://github.com/ryancinsight/horae/pull/44), merged.
  - kwavers `ADR index` — `docs/adr/130-…` opened `# 130. Title`, which matches neither canonical form (`# ADR NNN:` or `# NNN —`); every other ADR there uses the first. Red since #752 merged. The generated index does not change, because its title extraction already strips a leading `NNN.` — which is why the drift stayed invisible until the strict heading check ran over it. [kwavers#767](https://github.com/ryancinsight/kwavers/pull/767), enqueued.
  - moirai `Python Bindings` — already fixed on main by `5f901c47` (the oversized-open refusal is asserted per platform); the row survives only because that workflow has not run since. **Finding:** the collector reports each workflow's newest completed run, so a path-filtered workflow keeps a stale red row after its fix lands. The oracle is honest only if a row also carries whether a newer default-branch commit exists that the workflow never ran on.
  - ritk `CI` — mine, and an escaped defect: `cargo fmt` ran before the last of five file splits, so the commit I pushed was never gated and rustfmt rejected a double blank line. A peer landed the correction as `6a09f8ecf` twelve minutes later. ritk's committed `pre-push` hook gained its `cargo fmt --check` about an hour after that push, under [ATLAS-PREPUSH-HOOK-FORKED-ACROSS-MEMBERS-2026-09-09](#atlas-prepush-hook-forked-across-members-2026-09-09) — the generator is already being closed there.
  - Unchanged and not defects in the trees: atlas `CodeQL` and kwavers `GPU Parity` (both starved infrastructure), and the `Crates.io Release` rows for ares, gaia, leto, and ritk (stale manual dispatches; release is the user's authority).

## ATLAS-PROVIDER-CHAIN-QUALITY-2026-08-27 — Perf/memory/stability/safety audit + fix wave: apollo provider chain [patch]..[minor] — in-progress

- **Outcome:** adjudicated audit of apollo, hephaestus, leto, hermes, moirai,
  mnemosyne on four axes (performance, memory efficiency, stability, safety);
  accepted findings implemented per-repo as vertical increments (branch → gate
  → PR → merge), rejected/deferred findings filed with reasons on the owning
  member boards.
- **Integrator:** claude-fable session 03d80d33 (this claim). Audit fan-out is
  read-only (6 subagent sweeps, complete). Implementation claims land on each
  member's own board before that repo's source is touched; atlas-level entry
  tracks the campaign only.
- **Delivered 2026-08-29 (session continuation).**
  - apollo PR #194/#195/#196 — every FFT length routes correctly. Three faults
    (dispatcher fall-through, four mis-factored static radix entries, eleven
    naming an unexecutable radix), Bluestein as the terminal route, a
    naive-DFT sweep sharded to fit its budget, two structural table tests.
    Closes the highest-severity finding of this campaign: a silent wrong
    answer from a published transform.
  - apollo PR #197 — DCT-I, DCT-IV, DST-I, DST-IV reach O(N log N); the
    Type-IV pair shares one 2N-point FFT. 5.3 ms -> 38.6 us at N = 4096.
    Was blocked on the routing fix.
  - apollo branch inventory swept to zero (eleven branches classified and
    disposed); the Hephaestus cutover item closed by stale-claim takeover
    after re-running its own acceptance scan.
  - hephaestus PR #235 — device-side LU split; host-device traffic for the
    split falls from 3n^2*4 bytes to zero in each direction.
- **Constraints honored:** apollo `components/{base128,resident,batched,
  codelet}` + `test_support.rs` under live lease (ATLAS-APOLLO-BASE-BUTTERFLY-
  128) — findings there file to apollo's board, no direct edits; hermes tree
  held by live codex CI claim — hermes source work rides its current branch or
  a lane, `.github/` untouched.
- **Acceptance:** per-repo fix PRs merged green under member gates, or
  findings filed as DoR items with evidence; this entry closes with the ledger
  of merges + filings.
- **Progress 2026-08-28:** hephaestus HEPH-WGPU-STAGING-POOL-DECAY delivered
  (PR #229, merge `a3553d7`): staging-pool idle decay with a derived 10 s
  deadline, shadow retained-byte bound + hit/miss counters riding the
  acquire/recycle paths, sustained hit-rate and idle-decay evidence tests;
  member CI green (lockfile, host verification, WGPU contracts). hermes #97
  merged (SPMV short-row masked fix) at head `6382336`. Provider-chain repins
  after the hermes merge: leto #131 merged (hermes `bbc7bdb5`→`6382336`,
  Mnemosyne/themis cascade) and coeus #353 merged (hermes/leto/hephaestus/
  apollo all → current heads, merge `3875a8e`; every prior pin verified an
  ancestor — clean repins).
  Remaining repin consumers (CFDrs, athena, asclepius, ritk, helios, gaia,
  kwavers) hold worktrees on live lanes of parallel sessions — recorded here
  as pending follow-up, untouched to avoid collisions.
- **Progress 2026-08-28 (integrator session 03d80d33), sixth repo closed:**
  mnemosyne PR #79 enqueued — the four retag/provenance/cold-branch
  stragglers (MN-458), each the surviving instance of a pattern the
  MN-437..MN-456 sweep removed elsewhere. Evidence: Clippy `-D warnings`,
  `fmt --check`, nextest 289/289, doctests 5/5, and Miri under **both** borrow
  models over `mnemosyne-local` (84/84) and `mnemosyne-memory-core` (18/18).
  All six audited repos have now landed or enqueued their fix wave.
- **Root cause worth keeping (defect generator, not instance):** the surviving
  `mnemosyne-heap` copy of the int-to-ptr + `&mut Page`-across-segment pattern
  is explained by that crate sitting **outside the Miri gate** — the sweep that
  fixed every gated sibling could not see it. Filed as `MN-459` with its
  blocker measured on unmodified `main`: three pre-existing Miri failures in
  the crate's *own test helpers*. The general lesson for this stack: a
  miri/loom/sanitizer-driven sweep is bounded by the gate's crate list, so the
  sweep's closure claim must be read against that list, not the workspace.
- **Second process defect, cured:** the local gate sequence used through this
  campaign omitted `cargo fmt --check`, which reddened leto main once and
  moirai PR #171 once (both cured fix-forward, `d16542c` / `0584fb0`). `fmt`
  is now first in every gate invocation and in every agent brief. CI confirms;
  it must not discover.
- **Performance wave dispatched 2026-08-28 (three lanes, in flight):** moirai
  `MOI-PAR-TERMINALS-2026-08-28` (the flagship `par_iter().map(f).sum()` and
  most terminals run single-threaded through `seq_items()`, plus `Vec::split_off`
  splitting at O(n log n) copy traffic and non-short-circuiting `find_any`);
  hermes `HS-SIMD-PERF-2026-08-28` (transpose permute networks for AVX2 f32,
  AVX-512 f32/f64, NEON f32; F16 dispatch probe hoist per ADR 009); leto
  `ATLAS-LETO-OP-PERF-2026-08-28` (operator chains allocate n−1 arrays with no
  owned-lhs reuse; `reduce_axis` zero-fills a fully-overwritten output). Each
  carries a measurement requirement with the hybrid-core pinning caveat and an
  allocation/instruction-count signal, since wall-clock alone can invert
  verdicts on this host.
- **Apollo algorithmic items remain filed, blocked on tree capacity, not
  merit:** `ATLAS-APOLLO-CWT-FFT-CONVOLUTION` (O(scales·n²) with n
  transcendental evaluations *per coefficient* → O(scales·n log n)),
  `ATLAS-APOLLO-SHT-FFT-FACTORIZATION`, and `ATLAS-APOLLO-DCTDST-FAST-KINDS`
  (four of eight kinds are O(N²) at every size while the method docs claim
  O(N log N)) are the largest algorithmic wins the audit found. Apollo is at
  its two-tree bound with two live peers (main tree on
  `perf/apollo-base128-arith`, lane on `perf/apollo-dif-stages`, both edited
  within the last 20 minutes at the time of writing), so no third tree was
  opened. Re-open trigger: either apollo tree frees.
- **Consumer contract risk traced and routed:** leto #129's new panics on
  shared-window views reach a real consumer — kwavers filters the **columns**
  of a C-order array (`photoacoustic/filters/core.rs:168`), which are exactly
  the interleaved views now gated, and calls `to_contiguous()` + `assign()` on
  them. Both are paths the change routes through per-element access, so the
  shape is expected to hold, but it is unproven; a contract test pinning that
  consumer shape is being added to leto's own suite rather than left to
  kwavers' next lock sweep to discover.
- **Performance wave results (2026-08-28, two of three lanes landed):**
  - **leto #133 merged** (`a7dccf26`): owned-receiver `Add`/`Sub`/`Mul`/`Div`/
    `Neg` reuse the lhs allocation — 3-term chain 2 allocations → **1**, 5-term
    4 → **1**, owned scalar+neg 3 → **0**, borrowed tier pinned unchanged.
    Pinned timing (P-cores, both forms in one run): 3-term 64×64 −12%, 5-term
    −32% with disjoint CIs; **3-term 256×256 unchanged within CI and reported
    as such** — it is bandwidth-bound, so the allocation win does not show.
    Two corrections to this campaign's own filed evidence, both measured:
    (1) `owned + &b` never compiled before (rustc does not autoref an
    operator's lhs, `E0369`), so the impls are strictly additive with no
    coherence risk; (2) **`ATLAS-LETO-REDUCE-SINGLE-WRITE`'s cost premise was
    wrong** — `VecStorage::fill` is `vec![v; n]`, which hits std's
    `SpecFromElem`, so a zeroed output is a `calloc` and a large fresh
    allocation pays no memset at all. The item stays filed, reclassified
    `[minor]`, with its coverage proof recorded so nobody re-derives it.
  - **hermes #100 merged** (`5c50d1de`): most of the filed SIMD work had
    already been delivered by peers (#94 networks, #95 the F16 probe hoist via
    an `Avx2F16Frame` marker, #98 the AVX-512 f64 network), so the lane wrote
    only the genuinely missing **AVX-512 f32 16×16 network** — the exact item
    #98 recorded as its "Not done" follow-on. The larger win was unbriefed and
    came out of the required codegen inspection: **both** AVX-512 networks
    indexed their tile as a slice under a `debug_assert`, leaving a panic path
    per access (24 `ud2` for f32, 30 for f64) where AVX2/NEON already used the
    `try_into` fixed-array idiom; adopting it drops both to **1** and collapses
    the f64 body from ~3400 asm lines to **64**. The bit-exactness oracle was
    falsified before use (a no-op `_mm256_add_ps` injection fails it).
  - **Evidence standard for un-runnable ISA paths, settled rather than
    re-litigated:** #94 excluded AVX-512 networks for want of a real-silicon
    baseline; #98 landed one anyway. That reads as a contradiction but is not
    — this development host is an Arrow Lake Ultra 9 285K reporting
    `avx512f: false`, so no AVX-512 timing is *ever* possible here, and
    requiring it would mean the stack never ships an AVX-512 kernel. The
    operative split is: a **semantic** claim is verifiable (symbolic
    permutation algebra + the CI SDE job executing the real intrinsics) and a
    **performance** claim is not, so the latter is withheld explicitly rather
    than asserted. Both merged networks state their limits in-tree.
- **Gitlink hazard hit and corrected in the same cycle:** `git add repos/leto`
  stages the *submodule worktree HEAD*, which under concurrent agents was a
  peer's in-flight `perf/leto-matmul-parity-verdict` (`a8d9ae93`), not the
  merged head — and it silently skipped hermes, whose worktree trailed its
  published head. Corrected in `15292cb5` by setting both from `origin/main`
  via `update-index --cacheinfo` and verifying with `ls-tree`. Advancing a
  gitlink from a worktree HEAD is how an unmerged peer branch becomes the
  recorded stack revision.
- **Downstream integration verified, not assumed:** coeus `3875a8e1` is green
  on `main` with leto pinned at `14394eff`, which contains both leto soundness
  PRs — so the injectivity gates and window-exclusivity panics hold for the
  stack's largest leto consumer. The narrower kwavers risk (it filters the
  **columns** of a C-order array, exactly the interleaved views now gated) is
  closed by a contract test now in leto's own suite naming kwavers and its two
  file paths; both shapes pass, no leto defect surfaced.
- **Public-surface audit of the campaign's own output (2026-08-28):** ran
  `cargo semver-checks` over every crate this campaign touched, against each
  repo's pre-campaign baseline. `leto`, `leto-ops`, `hermes-simd`, and
  `hermes-simd-core` all report *no semver update required*. One real break:
  MN-458's removal of `Segment::is_owned_by` from the publishable
  `mnemosyne-memory-core` is `inherent_method_missing` — *"semver requires new
  major version"* — and it shipped labelled `[patch]`. Corrected in mnemosyne
  #80: recorded under CHANGELOG *Unreleased → Breaking* with the caller
  migration, item reclassified `[minor]`, no manifest bump (a completed item
  does not authorize a release). The removal itself stands — a forwarding
  wrapper keeps the whole-header retag reachable, which is the defect — and a
  stack-wide source scan finds no caller in any member.
  The generator is filed as **MN-460**: the repo publishes a crate but runs no
  semver gate. The item carries why it is not a one-line job — the Unreleased
  section already holds accepted breaking changes, so a gate diffing `main`
  against the published baseline is red on its first run and gets ignored; it
  must compare against the last release tag and fail only when the manifest
  version does not cover the detected class. Worth checking whether the other
  publishable members share this gap.
- **Third performance lane landed — the campaign's largest win (moirai #193):**
  the `ParallelIterator` terminal set stopped routing through `seq_items()`,
  which collected the whole stream and then ran a std sequential pass. At
  131072 elements, pinned to 8 P-cores: `par_iter().map(f).sum()`
  **391.25 µs → 11.18 µs (35×)**, `find_any` with an early match
  **412.92 µs → 5.13 µs (80×)**, `count`+`min`+`max` **1.156 ms → 36.93 µs
  (31×)**. The flagship rayon-displacement call was single-threaded with an
  O(n) allocation; the green comparison benchmarks had never covered it,
  because they exercise `map_reduce_indexed`, a different API.
  Terminals left sequential are recorded with reasons rather than quietly
  skipped (`fold`/`try_reduce` have one threaded accumulator and a doc-stated
  ordering contract; `position_*` cannot be given a correct logical offset
  because `Consumer::split_at` carries a *source* split point that a
  length-changing adapter invalidates). `sum`/`product` merge in index order,
  so results stay reproducible, but they are re-associated and therefore not
  bit-identical for floats — stated, not glossed.
  Measurement discipline worth keeping: the lane **quantified the noise band
  before claiming anything** (two runs of identical code differed by up to
  32%, so every ≤1.6× movement in that PR is unresolved and the headline
  numbers are one to two orders outside it), and **two optimizations were
  reverted because measurement rejected them** — an `Option`-slot owned split
  (2.79× slower: `Option<u64>` is 16 bytes where `u64` is 8) and folding
  `partition`/`unzip` across shards (2.3–2.4× slower, and slower even below
  the dispatch threshold, locating the cost in the accumulator rather than in
  parallelism). Both are recorded in-code so the attempts are not repeated.
- **Audit-contract change reviewed, not waved through:** that PR edited
  `benchmarks/tests/benchmark_contracts`, which pins parallel-iterator source
  text — the kind of edit that can quietly retire the guard for the defect
  being fixed. Verified: the removed markers pinned the *old* shape
  (`split_off(mid)`, the single-element base case, the reference-vector
  materialization) and their replacements pin the new one, with the
  reference-vector rebuild now explicitly prohibited. The `FoldConsumer` ban
  was narrowed rather than dodged by a rename: `8cd4286` is confirmed to have
  introduced `pub struct FoldConsumer<T, F>` as a two-field placeholder with
  **zero** `Consumer` impls, and the contract now bans that exact shape while
  *requiring* the trait implementation — strictly stronger than the name ban
  it replaced.
- **Moirai `main` was intermittently red before this wave, now fixed
  (moirai #194):** `scheduler_join_waits_for_queued_and_active_work` asserted
  `has_work()` after scheduling eight atomic increments on a two-worker pool,
  with nothing ordering the assertion before the workers drained them. It
  failed PR #191's merge run at `tests.rs:994`, and SHA `ff41a098` appears in
  the run list as both a success and a failure. The jobs now park on a gate
  the test holds until it has observed the work. Local repetition could not
  prove the race (60/60 on this 24-CPU host, which wins where a 2-core runner
  loses), so the variable was isolated instead: an identical 50 ms delay
  before the assertion makes the original **fail** and the gated version
  **pass**.
- **Last update:** 2026-08-28 22:20 EDT (session 03d80d33).

## ATLAS-PROVIDER-API-REPINS-2026-08-26 [integration] - Apollo/Hermes LaneKernel migration completed

Hermes now owns the capability-argument `LaneKernel::call(self, simd)` API,
and Apollo's merged `be10c9f2` implementation matches it. The downstream
consumer locks for Apollo, CFDrs, Coeus, Asclepius, Athena, Helios, Hephaestus,
Leto, and Ritk were repinned to Apollo `be10c9f27010435ee1fae2e08284a3e64e5971c3`
and Hermes `bbc7bdb593dc0bc95de7c6fb7840f92199c86fea`. The consumer scan found
no direct downstream `LaneKernel` implementations requiring source edits.

## ATLAS-APOLLO-FFT-LANEKERNEL-SIGNATURE-2026-08-26 [patch] - BatchedStages now matches the capability-arg trait

`apollo-fft` `BatchedStages::call` was implemented with one parameter; the
`hermes_simd::LaneKernel::call` trait now requires two
(`fn call(self, simd: Simd<T, A>) -> Self::Output;`). Every consumer that
compiled against `hermes_simd::vectorize(BatchedStages { ... })` on the new
trait signature broke at this single mismatch
(`error[E0050]: method 'call' has 1 parameter but the declaration in trait
'hermes_simd::LaneKernel::call' has 2`), so the kwavers-solver, hephaestus,
and coeus provider graphs all stopped compiling on top of the recent
`81e7de3a4fb36dce87cc2dc25e99420cb7165fd3` Apollo repin. Long-running PRs on
those providers were already blocked by the queue, and the signature
mismatch was the next wall behind it.

**Fix (commit `e9e5da80`, merged into apollo main at `2a447209`):** accept
the `simd: Simd<T, A>` capability token and use it. The implementation was
already pure-load/pure-store via `Vector::<T, A>::load_unaligned` and
`store_unaligned`, so the token is the only missing argument. The merge with
upstream apollo PR #121 (which was independently fixing the same trait
mismatch) replaced the placeholder with `simd.splat(twr)` for the
twiddle broadcasts — a clean improvement that the same diff carries.

**Local evidence at `2a447209`:** `apollo-fft --lib` 400/400 pass, all
`apollo-fft --tests` (5/5) pass, `cargo check -p apollo-fft --lib` clean,
`cargo check -p kwavers-solver --tests` clean, `cargo check -p kwavers
--tests --features full` clean. The Windows MSVC linker error in
`kwavers-solver` test build (`unresolved external symbol ... leto::iter`)
is a pre-existing kwavers-vs-leto integration issue, not caused by this
change — `cargo check` and the apollo-fft suite both pass on the same tree.

**Atlas integration:** atlas `repos/apollo` gitlink unchanged from its
existing `2a447209`; the apollo-fft fix rides the merge that already
absorbed PR #121.

Standalone lock guards pass for all affected consumers, with first-party source
counts of `64` (CFDrs), `41` (Coeus), `41` (Asclepius), `35` (Athena), `59`
(Helios), `33` (Hephaestus), `30` (Leto), and `51` (Ritk). Live-overlay checks
also pass for CFDrs `cfd-3d` trifurcation tests (`2 passed`), Coeus
`coeus-autograd/core/ops`, Asclepius, Athena, Helios, Hephaestus, Leto, and
Ritk focused package surfaces. No solver workload, timeout, numerical assertion,
or feature budget changed. Hosted full-workspace verification remains the
normal follow-up after these provider revisions are consumed in CI.

## ATLAS-CI-RUNNER-SATURATION-2026-08-25 — Hosted-runner queue depth delays every merge gate [patch] — in-progress

- **Outcome:** a merge-gate run starts within its own runtime target, so a merge
  to a default branch is verified in minutes rather than landing unverified for
  the length of a queue.
- **Still unmet, measured 2026-09-09 10:46 EDT.** Nine atlas runs queued and
  none started, the oldest waiting sixteen minutes — against the five-minute
  per-job target, the queue is longer than the work. Every push in this
  session's atlas sequence (`8631521a`, `ed333d5b`, `9a94bd74`) sits behind it,
  so `atlas-stack-overlay`, `atlas-conformance` and `version-guard` verify the
  landed tree well after it lands. Six member merges in this session proceeded
  on committed-gate evidence read from the pull requests rather than on a
  merge-gate run, which is the sanctioned path when the venue is unavailable
  and is also the measurement: unavailability here is a queue, not an outage.
- **Claim (2026-08-25, second session):** measurement instrument first.
  `scripts/atlas-ci-queue-report.py` pulls per-repository workflow-run metrics
  (queue minutes = created→run_started_at, run minutes = started→updated,
  event mix, conclusion mix) over a window and writes a gitignored report plus
  a stdout summary; the capacity-vs-load-shedding decision consumes its output.
  Kwavers CI scope itself stays with the first session's claims (PRs #641/#642).
- **Measured, full week ending 2026-08-25T21:00Z (`report-20260825T210157Z.json`,
  gitignored run output; stdout table reproducible via the script):**
  - Fleet total **3,164 runs / 491,507 work-minutes (~8,190 runner-hours)**;
    queue starvation is real but bursty: **4,796 queue-minutes**, concentrated
    in consus (3,142m), CFDrs (747m), kwavers (629m across 10 runs queued >5m),
    ritk (92m), Moirai (105m).
  - **kwavers alone burns ~330,900 work-minutes/week — 67% of the fleet** on
    ≥1,000 runs. Its consolidation is the first session's live claim (#641/#642
    preflight stack); no second actor enters that scope.
  - Next consumers with no active claim: hephaestus 14.2kh, Moirai 11.8kh,
    CFDrs 9.6kh, eunomia 9.3kh, tyche/horae/helios ~7–7.7kh each.
  - Event mix: pull_request 1,413 + push 1,195 (+553 dynamic-class); the PR
    matrix is the dominant consumer, matching load-shedding levers
    (path filters, draft skipping, scheduled heavy suites) before capacity.
- **Decision inputs now exist; next increment:** pick one non-kwavers heavy
  consumer and apply the cheapest lever with before/after numbers from this
  report as the baseline.
- **First lever applied (2026-08-25):** hephaestus — the largest unclaimed
  consumer (14.2kh/wk) — path-filters its four hardware workflows to their own
  crate + core + manifests + workflow file
  ([hephaestus PR #220](https://github.com/ryancinsight/hephaestus/pull/220) at
  `9977801`). Hosted runners skip hardware execution but were compiling each
  backend stack per unrelated PR (~26 min/PR across four workflows per #218
  evidence). workflow_dispatch retained for on-demand self-hosted runs;
  common-surface gates untouched. Before/after rides the report's weekly rerun.
- **Collected:** Mnemosyne PR #70 merged at `e9adfe8` (all real checks green;
  only recurseml report-only); Atlas mnemosyne gitlink advanced (`0a926abe3`).
  leto #123 merged (`1d4d687`, gitlink since advanced past it to `98486ebd`).
- **Second lever wave merged 2026-08-26:** CFDrs **#374** (concurrency
  cancel — its queue-to-work ratio was the fleet's worst at 828m queued vs
  741m worked) at `7df28ccd`; Moirai **#167** (Python-bindings path filter,
  was 61 runs × ~22 min/wk on Rust-only changes) at `a63a7153`; ritk **#209**
  (leto-linalg chapter → Athena, closing the ADR-0033 residue-scan doc drift)
  at `f444f3b3`. All three gitlinks advanced in one batch
  (`c259ddb58`). kwavers **#642** closed-superseded by the first session's
  #641 stack; its `Cargo.toml` O3 coverage-profile half is on kwavers main
  (confirmed `opt-level = 3` under `[profile.coverage]`), and the workflow
  wiring rides the peer's open #641 consolidation.
- **Measured 2026-08-25, ~20:00Z:** 27 runs queued across the fleet with one in
  progress — kwavers 14, hermes 7, helios 3, ritk 2, CFDrs 1. Hermes CI on
  `main` sat queued for over 50 minutes. Three merges landed during that window
  with their gate runs still unstarted.
- **Finding:** this is the queue-time rule's case — a job queued past its own
  runtime target is runner starvation, cured by capacity or load-shedding, and
  filed rather than absorbed as agent waiting. The dominant consumer is
  `pull_request`-triggered: kwavers alone had 3 Architecture Validation, 2
  benchmark regression, 2 Legacy Migration Audit, 2 Deploy mdBook, and 2 CI/CD
  Pipeline runs queued, several of them on the same PRs.
- **Third lever (2026-08-26): helios** — the board's next unclaimed consumer
  (~7–7.7kh/wk). Step-level measurement of its "slow" main runs shows the
  wall time is queue starvation *inside* the run, not compute: run 32436531185
  created 01:30Z with first job started 03:02Z — **92 queued minutes for ~5.7
  minutes of compute** across both jobs; run 32892598325's book build took
  2.6 minutes and its Pages deploy waited ~57 minutes to publish. Helios
  `ci.yml` carried no concurrency group, so superseded pipelines held queue
  positions behind live ones. The CFDrs-#374 lever applied verbatim:
  [helios PR #74](https://github.com/ryancinsight/helios/pull/74)
  (`ci/helios-ci-concurrency`, head `eb08279`), `group: ci-${{ github.ref }}`
  + cancel-in-progress; no gate, job, timeout, or trigger changes; all four
  PR checks green at open. Before/after rides the weekly report rerun.
- **Build-cache lever, fourth wave (2026-08-26): shared-key rust-cache.** The
  queue/load levers above cut queue time; this cuts the *work* time inside a
  green run. The destructive pattern is `actions/cache` keyed on
  `hashFiles('**/Cargo.lock')` caching `target/`: any first-party repin wipes
  the whole build cache and forces a full workspace rebuild on exactly the
  routine dependency-bump PRs. Mirrors the CFDrs #375 precedent
  (`Swatinem/rust-cache@6323deb1`, `shared-key`, `save-if` on `main` only).
  Applied to the two highest-remaining CI-gate consumers:
  - **ritk PR #211** (`perf/ritk-shared-rust-cache`, head `625ba675`): the
    3-OS nextest matrix (5,675 tests, 14.6kh/wk on the 2026-08-25 report)
    used the destructive lockfile-hash cache; now shared-key rust-cache with
    `workspaces: ritk` (checkout is a subdir).
  - **helios PR #75** (`perf/helios-shared-rust-cache`, head `e6de680`): the
    rust workspace job (~12 min build) used the destructive cache; now
    shared-key with `workspaces: .` (root checkout). Adds to #74's
    concurrency lever.
  - Already converged / correctly scoped elsewhere: Coeus (`6323deb1`,
    save-if), CFDrs (#375), python_ci rust-cache; apollo benchmark and helios
    benchmark keep their lockfile-keyed *source-only* caches (registry+git
    only, no `target/` wipe — correct for benchmark-baseline reproducibility);
    kwavers CI is peer-held (#641 consolidation).
  - **Starvation event 2026-08-26, ~16:00Z:** both ritk #211 and helios #75
    first check-runs died to `startup_failure`/`cancelled` with **every job
    `started_at: null` and no logs** — pure runner starvation, no check ever
    started, no code touched. This is the queue-time rule's case, not a PR
    defect; GitHub's auto-requeue has since re-enqueued both runs. Converge
    only on a terminal green after a runner is actually acquired.
  - **Recheck 16:35Z:** both PR runs (helios 32985441518, ritk 32985093134)
    still `queued`, but `ritk main`'s Deploy mdBook and Python CI completed in
    the same window — capacity is draining unevenly (main-push ahead of PR).
    Both PRs are MERGEABLE, CodeRabbit-passed, single-file workflow changes
    with validated YAML; convergence needs only runner capacity, no further
    code. Merge on terminal green, then delete both `perf/*-shared-rust-cache`
    lanes/branches.
  - **Fleet-wide build-cache audit complete (2026-08-26):** the shared-key
    rust-cache / `save-if` on-main pattern is now correct across every
    non-peer-held member — CFDrs #375, Coeus, apollo (with its deliberate
    `cache-targets: false`), plus the in-flight ritk #211 and helios #75.
    `hashFiles('Cargo.lock')`-keyed `target/`-wiping caches remain only in
    the correctly-scoped benchmark baselines (apollo, helios — source-only,
    no `target/`) and kwavers (peer-held #641).
  - **Build-cache wave delivered (2026-08-26, ~19:20Z):** both re-triggered
    (amended SHA against the drained fleet) and merged green on default:
    - **ritk #211** merged `7b6f22157`; post-merge `main` CI `33002036618`
      and Python CI `33002034936` both `success` (the cancelled `33000606*`
      legs were earlier starvation, auto-re-ran on the merged default).
    - **helios #75** merged `850db7bf`; post-merge gates green (rust
      workspace, python bindings, Lockfile).
    Lanes and remote/local branches (`perf/*-shared-rust-cache`) reclaimed.
    Both defaults now warm their shared-key caches from `main`, so the next
    first-party dependency-bump PR on each avoids a full `target/` rebuild.
    Atlas gitlink advancement for ritk/helios is the provider-graph step, done
    after the recorded post-merge CI is confirmed terminal.
  - **Fifth lever (2026-08-26): helios CI job split.** The `rust` job was a
    monolith running 11 sequential steps (fmt → clippy → tests → doctests →
    docs → book-check → mdbook-test → audit → deny) in one job, wall time
    ~27 minutes. Split into three parallel jobs sharing `shared-key: helios`
    cache:
    - `fast-lint` (timeout 10m): fmt, clippy, audit, deny — fails in ~3min,
      surfaces lint/dependency issues immediately.
    - `tests` (timeout 30m): nextest + doctests — the heavy path, writes
      cache from main only.
    - `docs` (timeout 15m): documentation + book-figure check + mdbook test.
    All three share one `Swatinem/rust-cache` entry via `shared-key: helios`;
    only `tests` writes (`save-if` on main). Wall time drops from ~27min
    sequential to ~18min (tests-bounded). Removed unnecessary `fetch-depth: 0`
    from all jobs (nothing reads git history). `python-bindings` and
    `benchmark-regression` unchanged.
  - **Sixth lever (2026-08-26): kwavers parallel-suite split.** The
    Architecture Validation `test-coverage` job serially ran the full test
    suite (lib 1224s + integration baseline 1017s) inside one 2284s ~38min
    job. Split into two parallel jobs — `test-coverage` (the lib suite) and a
    new `integration-suite` job — each keyed to the shared `kwavers` cache, so
    the integration baseline and unit coverage run concurrently. Expected wall
    ~21min from ~38min. [kwavers PR #661](https://github.com/ryancinsight/kwavers/pull/661)
    merged `e2485a03e`; distinct from the peer-held #641 consolidation
    (build-matrix/duplication work), which remains theirs. kwavers build-matrix
    (~17min) and CUDA (~11min) jobs are follow-up candidates after #661 lands
    green.
  - **Seventh lever wave (2026-08-27): the next unclaimed consumers.** The
    queue report's remaining heavy consumers without a lever were eunomia
    (9.3kh/wk) and tyche/horae (~7-7.7kh/wk each). eunomia's cache was
    default-keyed Swatinem (destructive on any lockfile repin) and tyche/horae
    had **no cache at all** — every PR rebuilt from scratch. All three got the
    shared-key rust-cache lever (one entry per repo, `save-if` on main only):
    eunomia #74, tyche #39, horae #29. themis #32 (the same lever on its
    two-OS verify job) was the fleet's only open PR at session start and merged
    green — gitlink advanced to `8c2e2cd`. All four merged same-session;
    eunomia's numpy job also gained the shared entry (it cold-compiled the
    workspace).
  - **Eighth lever (2026-08-27): consus shared-key rust-cache.** The weekly
    report rerun (`run-wall`) put consus as the fleet's **worst queue consumer —
    3,374 queue-minutes/wk** (ahead of kwavers' 1,207) plus ~7.7k work-min, the
    next heavy consumer without a lever (kwavers/hephaestus/CFDrs/Moirai/ritk/
    helios/eunomia/tyche/horae/themis all already claimed). consus's CI had a
    `concurrency` group already, but all six `Swatinem/rust-cache` sites were
    **default-keyed** — the default key hashes `Cargo.lock`, so every first-party
    provider repin (which consus does routinely via its "Normalize lock onto
    current provider heads" steps) wiped `target/` and forced a full 15-package
    rebuild across the 3-OS test matrix on exactly the routine dependency-bump
    PRs. Applied the shared-key lever (main-only `save-if`): root matrices
    (`check`/`test`/`msrv`/`test-mat-features`) → `shared-key: consus`, fuzz
    workspace (`fuzz-build`/`fuzz-run`) → `shared-key: consus-fuzz`
    ([consus PR #59](https://github.com/ryancinsight/consus/pull/59), head
    `808c816`, branch `perf/consus-shared-rust-cache`). YAML validated;
    `recurseml/analysis` report-only, gate jobs pending on the starved runner
    pool (the queue-time rule; converge on terminal green). Before/after rides
    the weekly report rerun.
- **Scope:** measure per-repository queue depth and minutes over a week, then
  choose between capacity (a self-hosted runner on owned hardware, which the
  workflow-hygiene rule already prefers for private repositories and would also
  give a warm shared `CARGO_TARGET_DIR`) and load-shedding (path- and
  scope-filtered triggers, draft-PR skipping, moving heavy suites to schedule).
  **Non-goals:** disabling a gate to shorten a queue.
- **Acceptance oracle:** queue time for a merge-gate run stays under its own
  runtime target on a normal fleet day, with the per-repository minutes report
  showing where the reduction came from.
- **Risk / change class:** [patch], infrastructure. **Dependencies:** none.
- **Note:** every increment delivered today was verified locally against its
  exact tree with the sanctioned runners, so the queue delayed confirmation
  rather than blocking delivery. That is the tolerable case; a red gate
  discovered an hour after merge would not be.

## ATLAS-HERMES-CONSUMER-ENTRY-2026-08-25 — Restore Hermes as the stack's lane-kernel owner [arch] — in progress

- **Outcome:** a consumer anywhere in the stack writes one generic lane kernel
  against `hermes-simd` and gets per-ISA machine code for it, so the provider
  table's assignment of "CPU lane-parallel kernels and ISA dispatch" to `hermes`
  holds in fact and not only on paper.
- **Finding:** four members carry lane-parallel ISA kernels outside Hermes —
  `apollo` (28 files, 90 `#[target_feature]`), `kwavers` (AVX-512 FDTD
  stencils), `CFDrs` (`cfd-core/src/compute/simd/`), and `moirai`
  (`moirai-utils/src/simd/arch/`). The common cause is upstream and is not a
  preference: Hermes exports no route into a `#[target_feature]` scope, so a
  consumer's generic kernel compiles at baseline features — the outcome Hermes
  ADR 009 exists to prevent. Full scan and per-file classification in
  `gap_audit.md`, finding 2026-08-25.
- **Sequence** (upstream first; a consumer migrated before the capability exists
  would have to invent a second abstraction over the first):
  1. `HS-FEARLESS-TOKEN-2026-08-25` in `hermes` — value-carrying capability
     token, a `vectorize`-class entry, and a safe operation surface over the
     existing facets. Filed, hermes PR #62 merged the audit that drives it.
  2. `ATLAS-APOLLO-ISA-FORK-2026-08-25` in `apollo` — largest consumer, filed
     and blocked on step 1.
  3. `kwavers` and `CFDrs` — file per-repo items once step 1 lands and step 2
     has established the migration shape. Not filed yet on purpose: their
     migration pattern should follow a worked example, not precede it.
  4. `moirai` — blocked on a topology question, not on step 1. The README
     places `moirai` below `hermes`, so it cannot take that edge without
     inverting the documented order, and neither crate depends on the other
     today. Settle the direction first; an ADR revision may be the deliverable
     rather than a migration.
- **Open ownership question:** `eunomia`'s packed-unpack intrinsics
  (`packed/unpack/intrinsics/{avx2,avx512,neon}.rs`) sit in Eunomia while the
  provider table gives packed-lane representation to Hermes, which re-exports
  them. Resolve when step 1 lands; Eunomia's F16C conversion path is its own
  bounded context and is not in question.
- **Acceptance oracle:** the `core::arch` and `#[target_feature]` census in the
  finding above is re-run and every consumer row is zero or a recorded
  sanctioned remainder, with each migrated family carrying differential tests
  against its scalar path and no benchmark regression against a recorded
  baseline. The census is the tracked metric and ratchets downward.
- **Risk / change class:** [arch] at stack level; each member's own increment is
  classified in that member.
- **Required authority:** Change on allowlisted repositories; no release.
- **Status 2026-08-25:** **step 1 delivered** — hermes PR #63 merged as
  `85655c05`, gitlink advanced. `hermes_simd::vectorize` plus `LaneKernel<T>`
  give a consumer one route into a `#[target_feature]` scope, and nine safe
  operations (`mul_add` and the cross-lane permutes) complete `Vector`'s
  surface for multiply-accumulate kernels. Codegen measured: 41 ymm-bearing
  instructions including `vfmadd213ps` with no call into the backend
  operations through the entry, against zero ymm and five outlined calls
  without it. ADR 016.

  Two things narrowed against the filed plan, both recorded in the hermes audit
  amendment: the safe surface already existed on `Vector` so only FMA and the
  permutes were missing, and ADR 011 needed no revision because it already puts
  the safe layer above unsafe facets. One unforeseen blocker was cleared on the
  way: `#[runtime_dispatch]` dropped doc comments, which is why no dispatcher in
  that crate could be `pub`.

  **Step 2 ran, and changed the campaign.** `apollo-fwht` was migrated onto the
  entry, measured, and reverted: 1.6x to 8.8x slower than the code it would
  replace across three dispatch placements (apollo PR #112, measurements in
  `repos/apollo/gap_audit.md#fwht-vectorize-negative`). Two structural
  mechanisms, now recorded upstream in hermes ADR 016 and its README:

  - The `#[target_feature]` scope does not follow a closure onto another thread,
    so wrapping a work-partitioning call applies the ADR 009 penalty by way of
    the mechanism meant to remove it.
  - Hermes' `Scalar` backend is a plain array loop the optimizer inlines and
    auto-vectorizes at the build's baseline ISA. For a bandwidth-bound
    elementwise kernel it beats an explicit backend path, because there is no
    arithmetic for wider registers to save and the dispatch boundary is pure
    overhead.

  **This item is therefore rescoped from a census to a measurement gate.** The
  `core::arch` counts identify candidates; they do not establish that migrating
  one is an improvement. Each family needs a before/after measurement, and a
  family that measures slower stays as it is with the measurement recorded.

  On that criterion `kwavers`' AVX-512 FDTD stencils are the most promising
  remaining candidate — compute-dense, large per-call work units — and `CFDrs`'
  elementwise `cfd-core` kernels the least. Steps 3 and 4 stay unfiled: filing
  them as migrations would presume the conclusion this measurement removed.
  Step 4 (`moirai`) remains gated on the layering question, not on the
  capability.

  The acceptance oracle above is revised accordingly: the census ratchets toward
  zero only for families a measurement supports converting, and a recorded
  sanctioned remainder now includes "measured slower under the entry".

## ATLAS-ATHENA-ALLOCATION-CONTRACT — warm solves allocate 4-6 small buffers per call on Linux [patch] — reopened 2026-08-26 (instrument PR open)

- **Owner:** current session (investigation + closure); pre-existing on `main`
  (4c8a9dc); blocked ryancinsight/athena#18 only by sharing the `verify` job.
  Unrelated to the LSQR damping work.
- **Symptom.** `crates/athena-leto/tests/allocation.rs`:
  ```
  repeated_cpu_solves_allocate_nothing_after_initialization     FAILED
  repeated_bicgstab_solves_allocate_nothing_after_initialization FAILED
  repeated_gmres_solves_allocate_nothing_after_initialization    FAILED
  ```
  Each failure reports `Stats { allocations: 4-6, deallocations: 17,
  reallocations: 2-6, bytes_allocated: 9-11 KB, bytes_deallocated: 881 }`.
  Local Windows runs of the same tests in isolation pass; the failure
  appears on the Linux hosted runner. The test contract is "warm solves
  must not touch the heap after the first call", which the GMRES and
  BiCGSTAB solvers do not currently satisfy.
- **Where to look first.** `crates/athena-core/src/solver/gmres/cycle.rs`
  (Arnoldi basis construction) and
  `crates/athena-core/src/solver/bicgstab/algorithm.rs` are the
  candidates; a `debug_assert!`-gated path or a small per-iteration
  allocation (rotation scratch, Givens pair, observer state) is the
  likely source. The exact `4-6 allocations` and `17 deallocations`
  pattern suggests a `Drop`-driven cycle (every iter creates and drops
  one or two small heap objects).
- **Acceptance.** The three `repeated_*_solves_allocate_nothing_...`  tests pass on the hosted Linux runner with `0, 0, 0` allocations,  deallocations, reallocations. CI gate green.
- **Investigation 2026-08-25 — verdict: no solve-path allocation exists.**
  - Line-level audit of `athena-core/src/solver/gmres/` (workspace.rs
    allocates once in `GmresWorkspace::new`; algorithm.rs only reads/writes
    pre-allocated fields: `hessenberg`, `cosine`/`sine`, `transformed_residual`,
    `coefficients`, block views; reset_cycle/rotation/back_substitute are
    index arithmetic) and `bicgstab/algorithm.rs` (same pattern): every warm
    call is statically zero-alloc on the happy path.
  - Backend primitives (`LetoBackend` copy/scale/axpy/dot/norm/residual) are
    plain slice loops with no Vec/alloc; `LetoVectorBlock` views are always
    contiguous (`as_slice` succeeds; `to_contiguous()` materialization in
    `spmv_into` is dead); `Identity` preconditioner is a passthrough;
    `residual_noise_floor` is scalar math. No `debug_assert!`-gated heap
    path, no Drop-driven per-iteration allocation anywhere in the measured
    region.
  - Local runs on Windows: `repeated_cpu…`, `repeated_bicgstab…` 0-alloc
    pass; `repeated_gmres…` 0-alloc passes at `--run-ignored` in both debug
    and release. The `4-6 allocs / 17 deallocations` Linux signature has
    more frees than allocs, which no drop cycle of owned buffers can
    produce — it is allocator-internal churn (glibc per-thread arenas)
    observed via `stats_alloc::Region` under a multi-threaded nextest
    runner, not solver-heap traffic.
  - CI at the merged head `21318ae` (post-PR #18) is green (`success`),
    with the GMRES test `#[ignore]`d per `fce0f5b` (`ATLAS-ATHENA-ALLOC-001`);
    the flake is gone from the hosted gate. The original acceptance oracle
    (0/0/0 on the hosted runner) is not independently re-verifiable from
    this Windows host, so the ignore remains the safe gate until a Linux
    runner confirms it.
- **Not in scope of ATLAS-LSQR-STAGE-C-INCOMPLETE.** Closed with the
  evidence above; reopen only if a hosted Linux run re-reports non-zero
  allocations (then instrument with `MALLOC_ARENA_MAX=1` / trace before
  touching solver code).
- **Reopened 2026-08-26 — the closed state was gate-vacuous, and the reopen
  trigger fired.** Two findings:
  1. **Vacuity:** with the GMRES contract `#[ignore]`d, hosted CI reported
     "80 passed, 1 skipped" — the skip *is* this contract, so the allocation
     guarantee had no hosted coverage between 2026-08-25 and today. The
     prior closure's own condition ("safe gate until a Linux runner
     confirms it") was never discharged because no job ran the test.
  2. **Trigger:** the 2026-08-26 instrument rerun (below) passed the strict
     contract — confirming nondeterminism — but nothing in the gate would
     have caught a recurrence.
- **Correction delivered (athena PR
  [#20](https://github.com/ryancinsight/athena/pull/20), head `9963804`):
  instrument, don't guess.**
  - Classifier test `warm_solve_heap_traffic_is_bounded_and_not_retained`:
    measures 16 then 32 warm solves in separate regions; fails only when
    traffic *scales* with repetitions (solve-path allocation) or bytes are
    *retained* (leak). An environment-fixed burst passes with its shape in
    the report. This operationalizes the glibc-arena verdict: if that
    verdict is wrong and a solve path allocates, the doubling measurement
    catches it; if it is right, the burst stays fixed-size and balanced.
  - New `allocation-instrument` CI job runs both ignored contracts with
    `--run-ignored ignored-only`, so the strict zero-traffic expectation
    and the bounded-noise classification are both permanent hosted evidence
    on every push instead of skipped silently.
- **Hosted evidence at PR head:** Allocation instrument job green on Linux —
  including the strict zero-traffic GMRES contract, which reproduced no
  allocations on this rerun. Combined with the original failure and the
  Windows passes, this confirms the flake is nondeterministic environment
  noise, now permanently discriminated from a real defect by the classifier
  without human triage. Local Windows at `9963804`: default suite 2/2,
  ignored suite 2/2, clippy `-D warnings` clean, YAML validated.
- **Acceptance update:** strict contract enforced on hosted Linux every
  push via the instrument job; classifier red = real defect, classifier
  green + strict red = bounded environment burst (shape recorded).
  Unconditional re-enable of the strict test remains blocked until the
  environment cause is named (`MALLOC_ARENA_MAX=1` experiment still the
  first probe).
- **Investigation 2026-08-31 — full root-cause audit, solver path exonerated.**
  Line-level audit of every allocation site the warm solve can reach:
  - `athena-core` is `#![no_std]`; `GmresWorkspace::new` allocates once
    (hessenberg, cosine, sine, transformed_residual, coefficients, work_basis_dot);
    `reset_cycle` fills in place; `SolveReport` and `Termination` are
    `#[derive(Copy)]`; `ConvergencePolicy` is `#[derive(Copy)]`; `SolveError`
    is a stack enum with no `Vec`/`String`; `NoObserver` is a ZST.
  - `athena-leto` backend: `LetoPreparedDot`/`LetoPreparedNorm` are ZSTs;
    `copy`/`scale`/`axpy`/`dot_prepared`/`norm_l2_prepared`/`residual`/
    `fused_cg_update`/`combine_direction` are plain slice loops with no `Vec`/
    `format!`/`Box` on the happy path. `LetoVectorBlock` is `VecStorage<T>`
    (plain `Vec<T>`); `view`/`view_mut` return `as_slice` slices — no alloc.
  - `leto_ops::dot`: shape comparison is stack (`[usize; N]`), `as_slice`
    path calls `T::dot_slice`; `ShapeMismatch` allocates `Vec<usize>` only on
    the error path, never taken in warm solves.
  - `leto_ops::spmv_into`: shape checks allocate only on error; happy path
    goes to `spmv_slice_into` (plain row loop); `to_contiguous()` fallback
    is dead for workspace vectors (always contiguous).
  - `hermes_simd::dot` via `#[runtime_dispatch]`: generates
    `std::is_x86_feature_detected!` per dispatch site, cached in
    `OnceLock<bool>` — no heap allocation (inline storage). `SimdView::new`
    stores a pointer + `PhantomData`; `is_runtime_supported` calls CPUID
    directly on x86_64 — no allocation.
  - `stats_alloc::Region` and `Stats` are `#[derive(Copy)]`; `StatsAlloc`
    wraps `System::alloc`/`dealloc` with atomic counter increments — no
    allocation from the instrumentation itself.
  - **Verdict:** the solver path is provably zero-allocation. The 17
    deallocs with only 4 allocs (more frees than allocs) cannot be produced
    by any `Drop` cycle of owned buffers — it is glibc per-thread arena
    cleanup of pre-region allocations observed through the `stats_alloc`
    global wrapper. The companion classifier test already discriminates
    correctly: fixed-size burst = environment noise, scaling = real defect.
  - **Experiment delivered:** `MALLOC_ARENA_MAX=1` env var added to the
    `allocation-instrument` CI job (athena `.github/workflows/ci.yml`).
    Pinning glibc to a single arena eliminates per-thread tcache churn.
    If the strict zero-traffic contract passes under this pin on hosted
    Linux, it names glibc arena churn as the environment cause and clears
    the way for unconditionally re-enabling the strict test. If it still
    reports non-zero traffic, the investigation reopens with a named
    non-arena source to trace.
  - **Local Windows verification** at `d433d34`: default suite 2/2,
    ignored suite 2/2 (both GMRES strict + classifier), YAML validated.

## ATLAS-KWAVERS-CI-COVERAGE-OPT-2026-08-25 — Bound full-workspace test topology [perf][patch] — hosted verification pending

- **Owner:** current session; lane `worktrees/kwavers-ci-coverage-opt`,
  branch `perf/kwavers-test-coverage-profile`, PR
  [#642](https://github.com/ryancinsight/kwavers/pull/642) at `e1ecdd231`,
  stacked on PR #641 head `84ba553ef`.
- **Evidence (measured on ryancinsight/kwavers main, successful runs):**
  Architecture Validation wall 33–67m across recent runs, with the job's
  own queueing adding ~30m beyond its longest member; inside it,
  **Test Suite Coverage 35m19s** dominates (next: feature-matrix jobs
  9–14m each, Validate Clean Architecture 11m41s). CI/CD Pipeline runs
  ~37m. All far past the five-minute verification target.
- **Root causes found in Test Suite Coverage:** it had no rust-cache, serialized
  independent tests to one process, and rebuilt the disjoint full-feature
  doctest graph after the large workspace suite.
- **Hosted falsification and correction:** head `5c49bb2c` completed the
  5,759-test suite in 9m43s after an 18m53s cold compile, PINN in 4m01s,
  and bounded full-grid simulations in 4m26s, then exhausted the unchanged
  45-minute cap rebuilding the disjoint full-feature doctest graph. Commits
  `63513fca1` + `ed44d3d52` first moved that doctest to Documentation and
  bounded nextest/Rayon concurrency. Commit `27c88e88b` then corrected the
  profile strategy: Test Suite Coverage stays on the shared dev graph, both
  initial nextest invocations run at two processes with two Rayon workers,
  bounded full-grid binaries retain the default profile's complete
  `full-grid-sim` grouping, and artifact measurement remains `target/debug`.
- **Correctness correction (workload/timeout unchanged):** the proposed O3
  coverage-profile change is removed. Rust instrumentation coverage warns that
  optimized-out functions can make coverage results unprocessable, so an O3
  timing win is not coverage-correctness evidence. `Cargo.toml` has no remaining
  behavior delta; speed comes from the pinned shared cache, bounded 2x2
  concurrency, and eliminating duplicate doctest compilation. YAML, locked
  metadata, diff checks, and independent static review pass.
- **Next:** collect PR #642's hosted rerun; if green, record the new
  Test Suite Coverage duration and tighten the 45-minute timeout toward
  measured + 20% variance in a follow-up commit (bound tightening follows
  evidence, never precedes it).
- **Follow-up sweep 2026-08-25 — full pipeline job-time baseline measured**
  (CI/CD Pipeline run `32877332731`, the successful proteus-mat adoption
  run; own times, sorted):
  | job | own time |
  |---|---|
  | Heavy Validation (reviewed profile) | 41.6 m |
  | Code Coverage | 33.4 m |
  | Build & Test (beta) | 20.2 m |
  | Build & Test (nightly) | 18.6 m |
  | Build & Test (stable) | 17.4 m |
  | PINN Convergence / Benchmark Smoke / Solver Validation / PINN Feature | 11.5–12.9 m each |
  | Code Quality / Miri / Security Audit / Lockfile / Python Surface | 0.9–5.0 m |
  Pipeline wall 136 m, Architecture Validation wall 110 m on the same
  evening — both dominated by hosted-runner queueing (24+ ubuntu-latest
  jobs per PR across the two workflows), not by any single job's work.
  Live confirmation the same hour: PR #647's ci.yml run sat queued
  26 minutes and PR #642's Architecture Validation run 34 minutes
  before their first job started — with every workflow already carrying
  cancel-in-progress concurrency. The residual lever is structural:
  consolidate jobs or add runners; that is a user decision. A same-hour
  snapshot found **25 active workflow runs across seven concurrent peer
  branches** (`fix/kwavers-run-compiled-tests`, `test/kwavers-spectral-
  laplacian`, `ci/kwavers-build-matrix-timings`, and this session's three)
  — the queue is contention between parallel agent lanes on one repo, so
  lane scheduling is part of the fix alongside any job consolidation.
  Two cache defects found and fixed:
  - **Heavy Validation** used a private branch-scoped `actions/cache`
    whose key never matches on PR checkouts — every PR run recompiled the
    workspace from an empty `target/`, which is exactly the cold-cache
    budget its 45 m timeout was sized against (the 2026-08-23 note).
    Switched to the shared-key rust-cache (PR #647, `7cb10de8f`); timeout
    deliberately unchanged until a warm-cache measurement confirms.
  - **Code Coverage** had no cache at all: every run compiled tarpaulin
    0.37.0 from source and refetched registry/git before the instrumented
    build. Added a coverage-dedicated actions/cache (registry + git +
    tarpaulin binary, key separate from the uninstrumented shared key) and
    skip-if-installed (PR #648, `135d1ab89`).
- nextest timeout topology (`nextest.toml`) audited in the same sweep:
  default 60 s per-test / 15 m suite, ci 10 m, heavy 300 s with a
  documented 600 s override for `nl_swe_workflow` — already evidence-based,
  no change.
- **Outcome 2026-08-25 late:** PR #647 (Heavy Validation shared rust-cache)
  merged at `e78a4e8`; its first hosted run already showed Heavy Validation
  41.6 m → 33.6 m with the shared entry restored. PR #642 was folded into the
  peer lane #641 by its owner (`ea504bf`) to avoid a duplicate CI matrix —
  workload preserved. PR #648 (coverage cache) was briefly auto-closed in the
  #647 merge race and reopened; checks re-running.
- **Queue-time quantified across members 2026-08-25 night.** The bottleneck is
  not job duration anywhere anymore — it is hosted-runner wait:
  - athena: wall 30.4 m, own work 3.3 m (queue 15–30 m per job);
  - CFDrs: max queue 59 m against 15 m of own work;
  - ritk: max queue 74 m;
  - coeus: 60 m queue on a single-job run;
  - kwavers: PR #650's checks sat queued 36+ minutes before first start.
  Every workflow already carries cancel-in-progress. The levers are (a) job
  consolidation across the per-member matrices, (b) larger runner quota or
  self-hosted runners, and (c) lane-scheduling discipline between concurrent
  agent sessions. All three are user decisions; the data above is the input.
  Cache fixes like #647/#648/#375 remove the *work* side; queueing now
  dominates every member's PR wall time.
## ATLAS-KWAVERS-SWE3D-BASELINE-REGRESSION-2026-08-26 — integration oracle regression on main [major] — diagnosed locally 2026-08-26

- **Owner:** unclaimed; scope: `repos/kwavers` (integration baseline + SWE 3D
  validation test).
- **Symptom.** Architecture Validation → Test Suite Coverage on **main**
  fails with: `integration regression: kwavers::swe_3d_validation
  volumetric_tracking_covers_non_pml_domain` (1 of 681 integration tests;
  "Refresh with: scripts/integration_tests.py --update" suggested by the
  gate). Present in main runs 32921558574 and 32914486868 — the check has
  been red on the default branch across at least two runs.
- **Not caused by any open PR:** kwavers PR #650 (CSR interpolator) shows the
  identical failure while its 5,764-test lib suite passes; evidence comment
  recorded on the PR.
- **Decision needed before mechanical refresh:** the gate offers
  `--update`, but refreshing an oracle to make a red gate green hides a real
  numerical change if one occurred. First diff the stored baseline against a
  local run of `volumetric_tracking_covers_non_pml_domain`: if the delta is a
  genuine solver-behavior change, find the merging commit that moved it
  (`git bisect` over recent main merges: #622 run-compiled-tests, #638 viz
  config unify, #640 learning-rate schedule are candidates); if it is
  platform noise (the baseline was regenerated on a different runner), then
  `--update` is the correct fix and should note that in its commit.
- **Local diagnosis 2026-08-26:** the current Kwavers main tree has an empty
  integration baseline, and the focused test passes unchanged:
  `volumetric_tracking_covers_non_pml_domain` reports `100.0%` coverage and
  `12,544` valid points, matching `(40 - 2*6) * (40 - 2*6) * (28 - 2*6)`.
  The failure is therefore not reproducible from the current source and no
  baseline refresh is justified. The hosted runs remain historical evidence;
  the item stays open until a fresh full hosted integration run confirms the
  baseline is green.
- **Full local integration run 2026-08-26 (head `9982b37f`, the merge that
  absorbed the right-sized-grid fix `252d86716`):** `cargo nextest run -p kwavers
  --tests --no-default-features --features full --test-threads=1 --no-fail-fast`
  reports `681 tests run: 681 passed (9 slow), 27 skipped`, `Summary [266.087s]`,
  zero `FAIL` and zero `TIMEOUT` lines. The 60×60×40 grid that timed out hosted
  runners is gone; the 40×40×28 grid keeps every non-PML voxel asserted by the
  test and the sweep runs in 4 m 26 s locally, comfortably below the 25-minute
  script bound and the 45-minute coverage job bound. The local
  `scripts/integration_tests.py` cannot enforce here because the Atlas overlay
  Cargo.lock is stale against the `--locked` flag it carries; that is an
  environment blocker, not a regression.
- **Status:** local evidence closes the diagnosis; the item stays open until a
  fresh hosted integration run at the merge head returns `success`. A
  `--update` is not justified, because no test is currently failing and an
  empty baseline is the correct shape.
- **Local escape restored (kwavers PR #653 at `8165488c2`, merged 2026-08-26):**
  `scripts/integration_tests.py` was made unconditionally `--locked` when the
  baseline was eliminated, which makes the gate unrunnable on a tree under
  the Atlas development overlay (the overlay redirects first-party crates to
  local paths, so cargo refuses before the suite starts). The PR adds an
  `--unlocked` flag that drops the flag for local runs; CI keeps the locked
  default, so the committed-lockfile check is unchanged. All 24 real hosted
  checks pass on the exact head (lockfile 1m36s, audit burn 8m, audit legacy
  2m, all feature combinations 5–19m, build stable/beta/nightly 1–7m, CUDA
  10m, code coverage 32m, code quality 10m, doc 14m, heavy validation split
  legs 7–14m, integration runner windows 1m, layer boundary 21s, miri 4m, PINN
  feature 12m, python typed 1m, security 2m, solver validation 6m, test suite
  coverage 40m, validate clean architecture 3m). The local `--unlocked` run
  reproduces the canonical evidence from the prior diagnosis:
  `integration suite: 681 tests run, 0 failed; no regressions; 0 known
  failures unchanged` (matching the empty baseline). The command-form check
  that earned its place — splitting `--color --locked` at the wrong index
  produces a silent nonsense value with no `--locked` — is now part of the
  test surface. `recurseml/analysis` is the always-report-only error.
- **Acceptance:** main's Test Suite Coverage green; either the baseline is
  refreshed with a justification, or the solver change that moved the result
  is identified and reviewed. The local escape is now in place so the next
  hosted regression can be diagnosed against the same gate the CI runs,
  without reconstructing the command by hand.
- **Two new integration regressions observed locally 2026-08-26** at
  the post-`#653` / `apollo-fft`-signature-fix tip `dddb75c12` (the same
  tip the SWE 3D sweep is run from):
  1. `pstd_finite_window_born source_phasing_is_frechet_derivative`
     panics with `full=6.675873e-3, half=1.121181e-2`. The test asserts
     `half.normalized_residual < full.normalized_residual` (Born residual
     must converge under contrast refinement) and the half-resolution
     residual is now larger than the full. The test was added in commit
     `586f16858 fix(kwavers): Eliminate integration baseline` and has no
     history of passing, but no prior sweep caught it because the
     integration runner was only running four named binaries before
     #653. The PSTD solver has had six recent refactors
     (`b2cd15d37 fix(kwavers-physics): a caller's absorption coefficient
     reach the solver`, `b20158763 fix(kwavers-solver): give plugins the
     sources they are handed`, `247b0e97c refactor(kwavers-solver): slice
     fill for CPML scratch`, `4ea703892 refactor(kwavers-solver): remove
     elastic config placeholder`, `a81f8a6e6 refactor(kwavers-solver):
     complete debug field coverage`, plus the elastic/config placeholder
     removal); one of these likely changed the source-phasing path
     without the Born contrast test catching it because the prior runner
     was only running `swe_3d_validation`/`nl_swe_workflow`/`kuznetsov`/
     `absorption_decay`. Bisect is the next step, not a `--update`.
  2. `pinn_ic_validation test_ic_combined_loss_decreases` panics on
     `kwavers-solver` link errors under the dev overlay — the Windows
     rust-lld 17.1 link line and `pyo3-ffi 0.29.2` symbol resolution
     cannot produce the test binary in the local 60s window. The
     integration runner invokes the same `cargo nextest run` invocation
     that compiles the test binary, so the same link error is what
     the CI runner hits. A separate clean-room build with no
     overlay resolves it; the defect is the overlay, not the test.
- **Optimisation lever applied in this item: kwavers PR
  [#664](https://github.com/ryancinsight/kwavers/pull/664) at head
  `03ca874b` switches `scripts/integration_tests.py` from
  `--test-threads=1` to `--profile ci --no-fail-fast`. The committed `ci`
  profile carries `test-threads=4`, the `integration` group cap of
  `max-threads=2`, and the `full-grid-sim` / `gpu` groups'
  `max-threads=1`. The 4-core hosted runner's 681-test sweep went from
  17m28s to (projected) ~8m; the local run was 4m26s of which all but
  2s was the single-threaded serialization. The no-fail-fast intent is
  preserved (`--no-fail-fast` overrides the profile's `fail-fast=true`).
  Re-enable trigger: the test pair above must be passing on the
  current main before the lever can land.

- **ARCH-008 gaia CSG assessment 2026-08-25 — recorded correct-as-jagged.**
  `gaia/src/application/csg/boolean/indexed.rs` sites (`remap_binary_face_soups`
  :254, `components` :1130/:1304) are per-operand face-soup groupings built
  once per boolean operation, each operand's list growing independently — the
  moirai `channel_fusion` pattern. No traversal-hot path; conversion would add
  complexity without a win. Not claimed.
- **ARCH-008 seventh conversion opened off this sweep** — kwavers conservative
  interpolator transfer matrix → CSR (PR #650). The bench's byte-parity gate
  caught that `leto::Array3` indexing is x-major before any timing ran; the
  per-entry unravel stays. Measured: −22% at refine_4, +5% at refine_2
  (win grows with entries-per-row), recorded honestly on the PR.

## ATLAS-KWAVERS-HEPHAESTUS-CONTRACT-2026-08-21 — Define the neutral visualization handoff [major][arch] — in progress

- **Owner:** Atlas integration coordination with Hephaestus provider review.
- **Decision record:** `docs/adr/0054-kwavers-hephaestus-visualization-contract.md`.
- **Current evidence:** Kwavers `kwavers-analysis` still constructs WGPU
  instances, adapters, devices, queues, buffers, and `pollster` waits in its
  visualization transfer/renderer modules. Hephaestus exposes backend-neutral
  `ComputeDevice` and backend-specific WGPU implementations, but no existing
  visualization-specific role contract was found.
- **Contract increment:** the proposed seam is limited to backend acquisition,
  typed field upload, dimensions/range metadata, transfer receipts, and typed
  unavailable-capability errors. It deliberately excludes renderer/shader API,
  CPU fallback, and raw device/resource handles.
- **Ownership:** analysis computes neutral field metadata; Hephaestus owns all
  concrete WGPU objects and synchronization. The implementation must be placed
  at the deepest existing shared contract boundary to avoid the current
  `kwavers-gpu -> kwavers-analysis` dependency cycle.
- **Next gate:** provider owners must review the role signatures and create
  clean lanes from fetched defaults before any provider source edit. No dirty
  checkout, branch, lockfile, or Atlas gitlink is changed by this design step.

## ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 — Pilot deny(missing_docs) [patch] — in progress

The `missing_deny_docs` assessment found 114 of 118 flagged crates have
undocumented public items, so the directive cannot be safely added without
per-crate provider work. This pilot picks the one crate that is trivially
safe — `kwavers-alloc-probe` — a single-file crate (no submodules) with
every public item already documented, to demonstrate the pattern and drop
the count by one.

**Scope:** `crates/kwavers-alloc-probe/src/lib.rs` on a clean lane based on
fetched `origin/main` `377a98c8`, plus root PM records.

**Acceptance:** `#![deny(missing_docs)]` compiles without missing-docs errors;
format, check, warning-denied Clippy, nextest, doctests, and rustdoc pass;
the branch is published for review.

**Implementation evidence (2026-08-21):** clean lane branch
`fix/kwavers-alloc-probe-deny-docs` is based on fetched `origin/main`
`377a98c8670bb4c8c2750a032b1418ceeab60172` and publishes commit
`aa5ab2bc` — one line added after the existing
`#![doc = include_str!("../README.md")]` attribute. Format, check, clippy
(`-D warnings`), nextest (0 tests — probe library), doctests (1 ignored),
and rustdoc all pass on the clean lane.

Published as PR
[#598](https://github.com/ryancinsight/kwavers/pull/598) at exact head
`aa5ab2bc94ba31dbd5f7438aaef41195e9bf5c8e`. Hosted checks are the
acceptance oracle; merge only at the exact PR head after terminal required
checks. The dirty primary Kwavers checkout and Atlas gitlink remain
unchanged.

- **Hosted hold (2026-08-21):** PR #598 is `MERGEABLE` but `UNSTABLE`; all
  25 workflow runs (CI/CD Pipeline `32521893944`, Architecture Validation
  `32521893980`, benchmark regression `32521893996`, Legacy Migration Audit
  `32521894011`, Deploy mdBook `32521894392`) remain `queued` after 56
  minutes of observation across two re-check cycles. CodeRabbit passed;
  `recurseml/analysis` is errored (report-only). No runner has picked up a
  single job. No pointer advance or bypass is authorized; re-open on
  terminal provider checks or a hosted state transition.

## ATLAS-KWAVERS-PYTHON-GENERATOR-2026-08-21 — Add defaults and NumPy protocols [minor] — in progress

- The generator now records PyO3 defaults and keyword-only markers, translates
  registered NumPy array parameters/results to `numpy.ndarray`, and records
  unresolved defaults explicitly in the inventory.
- The generated surface covers 384 functions and 25 module-registered
  classes with class method/property surfaces including `Grid` constructors
  and getters. It has zero unresolved defaults, contains no `Any` or ellipsis
  placeholders, and the facade now has zero missing registered imports or
  `__all__` exports; only intentional `__author__`/`__version__` metadata
  extras remain.
- Generator-focused pytest passes `5/5` without loading the unavailable native
  extension. Native wheel smoke and runtime export execution remain open.

## ATLAS-KWAVERS-PYTHON-GIL-2026-08-21 — Detach Simulation.run [minor] — in progress

- `Simulation::run` now accepts the hidden PyO3 `Python<'_>` token, clones the
  backend-neutral grid/medium/config inputs, and executes `SimulationRunner::run`
  inside `py.detach`. The detached closure captures no pyclass or Python handle.
- Added `tests/test_simulation_gil.py`, an event-based Python-thread regression
  that requires concurrent Python progress and verifies the returned result's
  time-step count, sensor shape, and finite values.
- Provider `cargo check -p kwavers-python --lib` passes. The full provider
  formatter remains blocked by pre-existing peer-owned formatting drift in
  `kwavers-medium/src/absorption/stokes.rs`; no unrelated formatting was
  applied. Native wheel/runtime execution remains pending until a built
  extension is available.

## ATLAS-BOOK-FIGURE-CLOSURE-2026-08-21 — Restore generated validation figures [patch] — in progress

- **Audit evidence:** the independent provider generator dry-run found expected
  figure artifacts absent from the committed provider trees: RITK `77`,
  Kwavers `99`, Eunomia `17`, Coeus `12`, and Horae `8`. Tyche has a separate
  seven-figure gap. Helios's inspected generator dry-run found all `46`
  expected artifacts. The root Markdown-link check is a separate oracle and
  currently reports `missing-figures=0` at the committed Atlas gitlinks.
- **Acceptance:** each referenced figure is produced by the provider's
  canonical generator, committed at the provider source head, and covered by
  a deterministic existence check in the provider's book gate. No hand-made
  or placeholder assets are accepted.
- **Execution:** Tyche's isolated sidecar completed provider commit `4cd0899`
  and opened PR [#36](https://github.com/ryancinsight/tyche/pull/36) at that
  exact head. The Atlas gitlink commit `4ee9128` is held until the provider PR
  merges and its hosted checks complete; the remaining provider sets follow as
  disjoint increments.
- Eunomia's disjoint provider slice is committed at `01179a9` on branch
  `docs/eunomia-book-figures` and opened as PR
  [#73](https://github.com/ryancinsight/eunomia/pull/73). The commit adds the
  17 expected deterministic SVG outputs, one canonical generator, a local
  reference checker, reproducibility/negative tests, and a deployment
  prerequisite for the figure gate. Local generator/checker tests and
  `mdbook build docs/book` pass. The peer-dirty Eunomia main checkout remains
  untouched; the Atlas gitlink is held pending exact-head hosted checks and
  merge.
- Local `mdbook test` and `cargo build --locked -p eunomia` remain
  environment-blocked in the isolated lane because the inherited Atlas
  development overlay re-resolves the provider under `--locked`; this is
  recorded as a verification limit, not treated as a provider failure.
- **Eunomia hosted hold:** PR #73 is open at exact head
  `01179a9d98e7d3ccbf118b38b65e5c1c675490b8`, based on `834bd3b443dd050e9a1ec0c5d837645db33ac787`.
  It is `MERGEABLE` but `UNSTABLE`; figure, Rust, NumPy, supply-chain, and
  related checks remain queued, while `recurseml/analysis` is terminal error.
  Pages still serves the prior merged default `22a02b1`; no provider merge or
  Atlas pointer advance is authorized.
- **Eunomia merged and gitlink advanced (2026-08-23):** PR #73 reached
  terminal-success on figure, Rust, NumPy, and supply-chain checks at the
  exact head (`01179a9d98...`) and was merged at `35158d1`. Post-merge CI and
  Pages at the merged default are terminal (6/6 targets green) and the live
  book is HTTP 200. The Atlas eunomia gitlink advances `22a02b1` →
  `35158d1` (index-level pointer move; peer-dirty checkout untouched).
  Eunomia's set of the book-figure closure is closed by this increment.
- **Hosted hold:** PR #36 remains open at
  `4cd0899a301db4a934ae32bf40db00bb56836c64`; Deploy mdBook run
  `32492568641` and CI run `32492568124` are queued, with `recurseml/analysis`
  error and CodeRabbit pending. The live site is HTTP 200 but its
  `figures/ch01/fig01_1_parameter_spaces.svg` URL is HTTP 404 and its
  `Last-Modified` predates the PR, so no pointer advance is authorized.
- **Tyche merged and gitlink advanced (2026-08-23):** PR #36 reached
  terminal success on all required hosted checks at the exact head
  (`4cd0899a30`: Check book figures, verify, supply-chain, deploy/Build book)
  and was merged at `e5c6a39`. Post-merge CI and Pages at the merged default
  are terminal (8/8 checks green) and the live book is HTTP 200. The Atlas
  tyche gitlink advances `7d636471` → `e5c6a39` (index-level pointer move;
  peer-dirty checkout untouched). Tyche's set of ATLAS-BOOK-FIGURE-CLOSURE
  is closed by this commit.

## ATLAS-CFDRS-PYTHON-GIL-2026-08-21 — Complete PyO3 solver GIL boundaries [minor] — in progress

- Provider commit `575375e85ef0e4344461e3eb2635d28d10ad5997` adds
  `Python::detach` around every remaining input-sensitive cfd-python solver
  computation, keeps NumPy conversion under the GIL, and adds bounded
  Python-thread regression coverage. Local formatting, locked check, warning
  denied Clippy, Rustdoc, abi3 wheel build, and the new concurrency test pass.
- Full wheel tests pass `4`; one pre-existing dirty-main mismatch remains at
  the Casson/Newtonian branch constant (`0.0035` versus a peer expectation of
  `0.00345`). Mypy is unavailable and cdylib doctests are unsupported.
- PR [#365](https://github.com/ryancinsight/CFDrs/pull/365) is published at
  that exact head. The worker temporarily reused the clean CFDrs format lane;
  after publishing, the lane was restored to `fix/cfdrs-format-gate` at
  `c1e4fdcf`, preserving PR #361's scope. Atlas's CFDrs pointer is unchanged.
- **Hosted hold:** PR #365 is `mergeable=false`/`dirty` with no Actions runs
  returned for the exact head; `recurseml/analysis` is errored and CodeRabbit
  is rate-limited. The live Pages book is HTTP 200, but docs.rs/crates.io have
  no `cfd-python` artifact and the existing PyPI name belongs to an unrelated
  package, so release identity remains unresolved. The stale `0.0035` versus
  `0.00345` test expectation and an unrelated existing Clippy blocker remain
  provider-side residuals.
- **Verification residual:** the new Python-thread test detects progress with
  bounded waits and a large deterministic workload, but does not yet meet the
  repository's event/barrier-only synchronization preference. Re-open on a
  clean CFDrs lane; do not displace PR #361's restored format lane.

## ATLAS-KWAVERS-VIS-CONFIG-2026-08-25 — Make visualization selection and quality single-source [major] — blocked

- **Owner:** current session. **Scope:** Kwavers visualization configuration,
  renderer quality propagation, focused tests, Rustdoc/README/CHANGELOG, and an
  indexed Kwavers ADR. **Non-goals:** no provider ownership change, fallback,
  rendering algorithm change, or backend-specific configuration in
  `kwavers-analysis`.
- **Outcome:** top-level Kwavers `VisualizationBackend::{Leto, Hephaestus}` is
  the only backend-selection source. The ignored `gpu_enabled` boolean and
  duplicate `render_quality` field are deleted; adaptive quality changes the
  renderer configuration that subsequent frames use.
- **Acceptance oracle:** stack-wide search finds no `gpu_enabled` or
  `render_quality`; backend conformance and real Hephaestus pipeline tests
  remain value-correct; focused analysis tests prove quality transition and
  renderer propagation; formatting, warning-denied Clippy, Nextest, doctests,
  Rustdoc, and SemVer classification pass on the exact delivered revision.
- **Risk/dependencies:** `[major]` because two public configuration fields are
  removed. The active Proteus package-rename branch touches only manifests and
  lockfiles; visualization source remains disjoint. No release is authorized.
- **Delivered evidence:** Kwavers PR #638 merged as `00455130f` from reviewed
  head `b2a156215`; the independent judge found and then cleared one stale
  disabled-test block. Nextest passes 783 GPU-feature analysis tests, 744
  default analysis tests, and the four focused quality regressions after the
  judge fix. Formatting, doctests, warning-denied Rustdoc, standalone locked
  metadata, ADR-index validation, and the current-default real Hephaestus
  hardware test pass. `cargo-semver-checks` against the buildable
  dependency-only prerequisite baseline reports exactly the two removed fields
  as a required major change. The post-merge matrix is terminal with 33 passes,
  two expected skips, zero failures, and one cancellation: GPU and CUDA builds,
  all feature combinations, stable/beta/nightly, Miri, security, docs, coverage,
  quality, and validation pass; `Benchmark Runtime Smoke` spent 29 minutes in
  its Criterion command and hit the job's 30-minute timeout. Atlas gitlink
  `repos/kwavers` remains at `8ef48975c`. **Blocker/re-open trigger:** correct
  the cold-build benchmark-smoke instrument without raising its bound, then
  obtain a terminal green run and advance the gitlink to that fix.

## ATLAS-KWAVERS-BENCH-SMOKE-2026-08-25 — Bound cold-build benchmark smoke [patch] — hosted verification pending

- **Owner:** current session; lane `worktrees/kwavers-ci-opt`, branch
  `ci/kwavers-build-matrix-timings`, PR #641 at `84ba553ef`. **Scope:**
  Kwavers benchmark-smoke command and its
  directly required CI/cache structure. **Non-goals:** no timeout increase,
  benchmark deletion, reduced target coverage, or production-kernel change
  without profile evidence.
- **Outcome:** every plotting-eligible Criterion target executes once under the
  existing finite bound on a cold hosted runner; compilation and execution are
  separated or consolidated so setup cost cannot consume the smoke budget.
- **Acceptance oracle:** reproduce run `32867271654`, retain the full target
  set, build the bench binaries once as a separately bounded artifact, verify
  the cold build and bounded smoke phases independently, and obtain a terminal
  green hosted plotting feature-matrix leg containing both benchmark steps.
- **Risk/dependencies:** `[patch]`; the completed log proves no Criterion target
  executed: the release-profile compile was still building `proptest` at 29
  minutes and the 30-minute job bound then killed Cargo and Rustc. The
  visualization implementation is unchanged. Completion re-opens
  `ATLAS-KWAVERS-VIS-CONFIG-2026-08-25` for its gitlink advance.
- **Fix:** delete the standalone benchmark job and run one bounded dev-profile
  build plus one bounded `--test` execution in the already-cached plotting
  feature-matrix leg. The leg reuses checkout, toolchain, dependency cache, and
  the exact `--no-default-features --features plotting` graph; static manifest
  enumeration retains all 19 plotting-eligible targets. Cargo's
  `--no-fail-fast` keeps later targets executing after an individual failure.
  Independent review found no remaining issue after duplicate-step,
  feature-fingerprint, and complete-failure-reporting checks.

## ATLAS-KWAVERS-PYTHON-SURFACE-2026-08-21 — Complete typed and concurrent PyO3 surface [minor] — in progress

- **Owner:** Atlas integration. **Claimed files:** `backlog.md` and
  `checklist.md`; provider source is claimed by the isolated Banach coding
  worktree for the first core-simulation vertical slice. The shared dirty
  checkout and active PR scopes remain untouched.
- **Current claim:** `crates/kwavers-python/pyproject.toml`,
  `python/pykwavers/__init__.py`, typed package artifacts, the core
  `Simulation.run` binding module and focused binding tests. The claim excludes
  open PR #439 simulated-GPU files, open PR #443 core-log files, the separate
  analysis-owned WGPU migration, and all unrelated binding families.
- **Outcome:** the Kwavers Python wheel exposes every registered Rust class and
  function through one generated, typed package surface; the wheel ships
  `py.typed` and `.pyi` files; long-running binding calls release the GIL; and
  the package facade exports exactly the registered public symbols.
- **Audit evidence:** the current registration surface contains 25 classes and
  384 top-level functions, while the facade reexports 400 extension symbols
  but omits nine registered functions and four imported symbols from
  `__all__`. No `py.typed` or `.pyi` files exist. Static inspection identifies
  synchronous solver, thermal, GPU-session, bubble, cavitation-monitor, and
  chirp/sweep paths that still hold the GIL. Evidence source: the independent
  Kwavers binding audit at `crates/kwavers-python/src/lib.rs`,
  `python/pykwavers/__init__.py`, and the affected binding modules.
- **Acceptance:** a deterministic Rust registration-driven generator emits
  real signatures, defaults, classes, properties, NumPy arrays, optionals,
  tuples, mappings, and metadata without `Any`/ellipsis placeholders; CI
  regenerates and diffs the stubs; the installed wheel contains the extension,
  package facade, stubs, and marker; a strict typed consumer passes; an
  independent Python-thread regression proves each migrated long-running call
  releases the GIL while returned values remain correct; and the runtime
  inventory has no missing or extra public exports. Run the affected locked
  Rust gates, Python tests, doctests, Rustdoc, and wheel smoke at one exact
  provider head.
- **Sequencing:** first land the generator and exact registration inventory,
  then migrate one complete `Simulation::run` slice with the concurrency
  oracle, followed by thermal, GPU-session, bubble, monitor, and chirp families
  as separate vertical increments. Do not hand-author a partial stub or claim
  GIL coverage from static `.detach` counts alone.
- **Non-goals:** no domain logic in Python, no runtime introspection as the
  source of truth, no facade compatibility aliases, and no unrelated solver
  redesign.
- **First vertical slice:** isolated commit
  `db49f2f09cba6b24381156a8404cd08942a44f52` adds the typed package marker and
  stubs, releases the GIL around the core `Simulation.run` computation, and
  adds value-sensitive Python binding/thread-pool tests. The test oracle does
  not claim overlap or GIL proof; `py.detach` at the binding boundary is the
  static GIL-release evidence. Focused Rust,
  Nextest (21/21), Python (4/4), abi3 wheel, install, and smoke checks pass.
  PR [#590](https://github.com/ryancinsight/kwavers/pull/590) was opened at
  that head; strict mypy/Ruff/Black are unavailable and locked Cargo gates are
  blocked by the inherited Atlas overlay re-resolving the lockfile.
- The test-oracle correction is commit
  `124ef839e27aba71a8f3749c33acaf7d0ae1ee93`, now the PR head. Its focused
  Rust and wheel-backed tests pass; the previously collected hosted run set
  at `db49f2f09cba...` is stale and must not be attributed to the corrected
  head.
- **Hosted hold at the superseded head:** PR #590 was mergeable but `unstable`; CI/CD
  `32492642895`, legacy audit `32492642913`, Python wheel smoke
  `32492642908`, architecture validation `32492642942`, and Deploy mdBook
  `32492643372` remain queued. `recurseml/analysis` is errored and CodeRabbit
  is rate-limited. The live Pages site is reachable but older than the PR and
  is not evidence for either head; fresh checks for `124ef839e27a...` are
  required. No pointer advance or bypass is used.
- **Type-mapping increment (commit `60e871bad`, new PR #590 head):** every
  duck-typed `Bound<'_, PyAny>` parameter resolves through an audited
  `DUCK_TYPES` table keyed by `(class, function, parameter)` with per-entry
  extraction-code provenance; unaudited PyAny parameters fail the generator
  closed instead of emitting bare `object`. The stub honors
  `#[pyfunction(name = ...)]` renames (recovering the previously missing
  `run_standing_wave_suppression`), escapes Python keyword parameters
  PyO3-style (`lambda` -> `lambda_`), and types string-keyed result dicts as
  `Dict[str, object]` (422/422 literal-key `set_item` sites verified).
  Zero bare `object` parameters remain; an AST guard test enforces the
  invariant and the strict typed-consumer fixture exercises each mapped
  union. Focused suite 23 passed / 1 skipped with a freshly built abi3 wheel
  (`kwavers_python-0.1.0-cp38-abi3-win_amd64.whl`) installed. Pre-existing
  finding recorded, not caused by this increment:
  `get_array_weighted_mask` returns all zeros for annular elements at lane
  head `124ef839e27a` (`test_kwave_array_per_element_superposition_reduces_to_shared_signal`
  fails against the freshly built extension); the Rust binding needs its own
  defect increment. All prior hosted evidence is stale at the new head.
- **Annular-mask finding resolved (commit `38b54ce82`, PR #590 head):** not a
  Rust defect. Bowl/annulus surfaces lie one radius from `position` (the
  focus), matching k-wave-python; the test had placed the focus mid-grid with
  R = 10 mm on a 14.4 mm grid so the cap fell outside the domain and the BLI
  horizon correctly rejected every sample. Test now places the focus one
  radius past mid-grid and asserts both annuli contribute disjoint radial
  bands. Also fixed in-test: "Rectangular" → canonical "Uniform" alias
  round-trip expectation in `test_transducer_array.py`. Full local suite
  triage (898 passed / 90 failed / 62 skipped): remaining failures are
  environmental (missing external k-wave example utils, long-physics
  timeouts), no regressions from this lane.
- **Continuation refinements (uncommitted at `60e871bad`, part of this
  increment):** the generated stubs now pass mypy `--strict` — array aliases
  are `TypeAlias`-annotated, `__init__` returns `None` (PEP 484), and
  `__eq__` takes `other: object` (Liskov); the facade stub splits the eight
  `kwave_parity` helpers from the extension import and declares
  `__author__`/`__version__`. CI wiring: a `python-surface` job in `ci.yml`
  runs `tools/generate_surface.py --check` (regen-and-diff gate) plus the
  generator/typed-consumer tests with mypy installed; the wheel-smoke
  `kwave-comparison` job runs the runtime export-inventory oracle against the
  installed wheel (`KWAVERS_PYTHON_PACKAGE=installed`). The tracked abi3
  `.whl` build artifact is removed from git. Local gates: `--check` passes,
  generator staleness / typed-consumer / runtime-inventory tests pass (21
  passed, 3 skipped in source mode; runtime oracle 16/16 against the installed
  wheel).
- **Thermal GIL family (lane rebased onto `origin/main` `377a98c86`):**
  `ThermalSimulation::run` now runs its entire diffusion time loop inside
  `py.detach`, mirroring the `Simulation::run` contract (GIL-phase setup /
  owned-Rust-data time loop / GIL-phase PyArray assembly). Added the runtime
  overlap oracle `test_thermal_simulation_run_releases_gil_with_returned_value_correctness`
  on `test_bindings_surface.py`: a 48³ grid with a constant heat source holds
  a solve window well past the 0.5 s floor while the main thread exceeds 1M
  pure-Python GIL increments; returned-value correctness shows bit-identical
  temperature fields for identical inputs and a doubled heat source raises the
  temperature rise by exactly 2× (linear diffusion, ratio 1.0 within 1e-6).
  Wheel-backed: 16 passed / 1 skipped in `test_bindings_surface.py`; fmt,
  clippy `-D warnings`, nextest 21/21 clean. The `Simulation::run` slice
  (PR #590) and the WGPU provider migration (PR #602) are both completed;
  thermal is the first of the remaining GIL families (thermal, GPU-session,
  bubble, monitor, chirp).
- **Bubble ODE GIL family (same lane, next vertical increment):**
  `solve_rayleigh_plesset`, `solve_keller_miksis` (and the Keller–Herring
  delegation), `solve_gilmore`, and `solve_hodgkin_huxley_like` now run their
  RK4 / ODE integration compute inside `py.detach`, mirroring the
  `Simulation::run` / thermal contract. Added the runtime overlap oracle
  `test_bubble_ode_releases_gil_with_returned_value_correctness`: a 10M-step
  `solve_keller_miksis` holds a ~1s solve window while the main thread exceeds
  1M pure-Python GIL increments; returned-value correctness shows bit-identical
  outputs for identical inputs and a doubled driving amplitude swings the wall
  strictly farther (higher max / lower min radius). Wheel-backed: 17 passed /
  1 skipped in `test_bindings_surface.py`; fmt, clippy `-D warnings`, nextest
  21/21, generator `--check` clean.
- **Published at the rebased lane head (2026-08-22):** the lane (rebased onto
  `origin/main` `377a98c86`, carrying the thermal and bubble-ODE GIL
  increments) force-published to PR #590 with a lease guard against the
  superseded head `6616c904`; PR head is now `a2a3878b` and `MERGEABLE`.
  Hosted runs are executing rather than queued: Python wheel smoke
  `32588842603` and Legacy Migration Audit `32588842587` in progress, CI/CD
  `32588842609` and Deploy mdBook `32588842869` queued. All prior hosted
  evidence remains stale; merge only at exact head after terminal required
  checks.
- **Collection and blocker fix (2026-08-23):** wheel smoke, Legacy Migration
  Audit, and Deploy mdBook are terminal success; CI/CD Pipeline failed on its
  `Python Typed Surface` job: the crate's declared pytest addopts pass
  `--timeout/--benchmark-disable`, whose plugins (pytest-timeout,
  pytest-benchmark) the job did not install. Head `d1281f990` installs both
  declared dependencies; replacement runs pending.
- **Closed (2026-08-23):** replacement run set at `d1281f990` terminal:
  CI/CD Pipeline (incl. Python Typed Surface), Python wheel smoke, Deploy
  mdBook, and Legacy Migration Audit all success. The only failing check is
  Architecture Validation — the pre-existing repo-wide defect filed below,
  failing identically on every PR head, not required by any branch
  protection. PR [#590](https://github.com/ryancinsight/kwavers/pull/590)
  merged with the expected-head guard at default `ca5c9c93`; post-merge
  default runs in progress before any Atlas gitlink advance.
  **Not this PR's regression:** the Architecture Validation job fails on every
  open PR head across the repository (12 consecutive failures on unrelated
  branches, main's own post-merge runs cancelled with no terminal baseline).
  Local reproduction attributes it to ~2,850 warnings across 103
  example/test/bench files under `-D warnings --all-targets` — a ratchet-scale
  burn-down filed below as its own item.

## ATLAS-TYCHE-RELEASE-VERIFICATION-2026-08-21 — Record release gates [patch] — in progress

Tyche PR #35 documents the completed release/package verification slice. The
provider branch passed formatting, warning-denied Clippy, Nextest (51/51),
doctests (18/18), Rustdoc, the reproducible study example, benchmark smoke,
and `cargo publish --dry-run` before merging at default commit
`7d6364716f0a1929f5d2156a6f2d3c6962dd3b92`. The hosted PR verify and
supply-chain checks passed; `recurseml/analysis` remains report-only.

Post-merge CI `32474994136` and Pages `32474992974` are queued. Registry
publication and GitHub Release creation remain explicitly outside this item;
the Tyche Atlas pointer is unchanged until default CI/Pages and live-page
evidence are terminal.

**Ninth pointer batch (2026-08-23, atlas commit to be named):** the hold
cleared — `7d6364716f` has terminal `CI` and `pages-build-deployment` runs at
the exact head, and the live site returns HTTP 200 with title `Tyche | tyche`.
The Atlas gitlink advances to `7d6364716f`; `recurseml/analysis` remains
report-only.

## ATLAS-ASCLEPIUS-GEUD-GRADIENT-2026-08-20 — Add an independent Coeus gradient oracle [patch] — in progress

The Asclepius Coeus adapter test currently compares its reverse-mode gradient
with a second hand-coded power-mean derivative. That is a useful algebraic
check but not an independent behavioral oracle: the same formula can be wrong
in both places. The provider backlog already identifies a central-difference
check for this seam as `ASC-VER-018`.

**Scope:** Asclepius `crates/asclepius-coeus/tests/equivalent_uniform_dose.rs`
on a clean lane based on fetched `origin/main`, plus root PM entries. Add a
finite-difference value oracle for the existing dose fixture and derive its
step/tolerance from floating-point scale and central-difference truncation.
Do not alter the adapter implementation, peer-owned book/PM files, or the
Atlas Iris lane.

**Acceptance:** the test evaluates the adapter at independently perturbed dose
vectors, compares central differences with the reverse-mode gradient under a
documented bound, covers every dose coordinate, and fails under a mutation of
the adapter's gradient path; focused/full provider gates pass and the exact
branch is published for review.

**Owner:** current Atlas session. **Claimed files:** Asclepius
`crates/asclepius-coeus/tests/equivalent_uniform_dose.rs` in
`worktrees/asclepius-geud-gradient`; root `backlog.md` and `checklist.md`.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/asclepius-geud-gradient` is based on `origin/main`
`2f6959b52c36c91169e4f30ad4a7ce8e45d6e901` and publishes one commit,
`390a3ff`. The test evaluates independently perturbed adapter values for every
dose coordinate, uses central differences at two scales with Richardson
extrapolation, and derives truncation plus roundoff bounds from the step and
`f64::EPSILON`. Locked all-target check, full nextest (`20/20`), focused
nextest (`6/6`), Clippy with `-D warnings`, doctests, and Rustdoc pass. A
value-preserving mutation that detaches the adapter input gradient fails four
gradient/value-contract tests, including both independent gradient tests.

The implementation is published as PR
[#24](https://github.com/ryancinsight/asclepius/pull/24) at exact head
`390a3ff60344034a841b0735d9c059231e7f0a8a`, based on merged default
`ce3fea355f0989dcc92a321a1f923f6f30749da4`. PR CI passed at run
`32436064353`; PR #24 is merged. Post-merge default CI passed at
`a38b8b50d1de1d23c08478e4b60d9e7bbd8eacf4` in run `32441333616`; Pages build
`32441332866` remains queued. The dirty primary Asclepius checkout and Atlas
gitlink remain unchanged until Pages and live-page verification are terminal.
The merged lane and remote branch were removed after ancestry verification.

**Ninth pointer batch (2026-08-23, atlas commit to be named):** the Pages
hold cleared — `a38b8b50d1` has terminal `ci` and `pages-build-deployment`
runs at the exact head, and the live site returns HTTP 200 with title
`Asclepius | asclepius`. The Atlas gitlink advances to `a38b8b50d1`;
`recurseml/analysis` remains report-only.

## ATLAS-THEMIS-REGION-MODULE-2026-08-20 — Split branded region implementation [arch][patch] — in progress

Themis `src/branded/region/mod.rs` is a 481-line implementation file. It
contains the `SyncRegionPlacement` capability, its NUMA-tag proof helper, scope
construction, and tests, so the module manifest is not a manifest and the
conformance scan records one `manifest_implementation` violation.

**Scope:** Themis `src/branded/region/` only, plus the provider ADR/index and
owner-local PM records. Move the existing implementation into a focused leaf
module, retain `region/mod.rs` as the module manifest, and preserve every
public path and safety argument. Do not touch the peer-owned primary checkout
or unrelated platform/book changes.

**Acceptance:** public exports and behavior remain unchanged; the region
module manifest contains only module declarations and curated re-exports; the
provider ADR index is synchronized; format, locked all-target check, warning-
denied Clippy, nextest, doctests, and Rustdoc pass; the conformance scan drops
Themis `manifest_implementation` by one without raising any class.

**Owner:** current Atlas session. **Claimed files:** Themis
`src/branded/region/`, provider ADR/index, and root `backlog.md`/`checklist.md`.
The clean lane must be based on fetched Themis `origin/main` after the primary
checkout's five-commit lag is reconciled by using a new lane, not by editing
the dirty primary.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/themis-region-module` is based on `origin/main`
`c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` and publishes commits `7b30088`
and `32c40a7`. `region/mod.rs` is now a manifest with curated re-exports and
the implementation/tests are in `region/scope.rs`; ADR 0003 and the provider
backlog/gap audit are synchronized. Locked all-target check, format,
warning-denied Clippy, nextest (`25/25`), doctests (`5/5`), and Rustdoc pass.
The lane conformance scan reports `manifest_implementation: 1` versus `2` on
the fetched provider default, with every other Themis class unchanged.

The implementation was published as PR
[#29](https://github.com/ryancinsight/themis/pull/29) at exact head
`32c40a7b21fd9a6e81505e8741d54884ab1d2e59`, based on merged default
`c441acffc71ebeb24b77dd2d23a90856352d2f48`, and merged with the expected-head
guard at default merge commit `2c0749873c4860257ba912ff8494937021a79aa1`.
The PR's Ubuntu, Windows, MSRV, Miri, compile-fail, Clippy, Nextest, doctest,
and Rustdoc checks are terminal-successful. Post-merge default runs are
queued: MSRV `32473974344`, CI `32473974353`, and Pages
`32473973059`. The dirty primary Themis checkout and Atlas gitlink remain
unchanged until those runs and the live-page check are terminal. The merged
clean lane and its local branch were removed after the PR merge.

## ATLAS-HELIOS-RADON-ORACLE-2026-08-20 — Remove existence-only sinogram assertion [patch] — in progress

`helios-imaging/src/radon.rs` asserts only `Sinogram::from_readings(...).is_ok()`
and then unwraps the same result. This is an existence-only assertion and does
not verify the constructed value; the later mapped-reading assertions are the
actual geometry/value oracle.

**Scope:** Helios `crates/helios-imaging/src/radon.rs` and provider PM records
on a clean lane based on fetched `origin/main`. Replace the vacuous assertion
with an invariant-preserving typed extraction, retain the existing negative
length case and value-semantic map/geometry assertions, and do not touch the
peer-owned Helios primary checkout or unrelated Python/workflow/book files.

**Acceptance:** the test contains no existence-only assertion for this path;
the valid construction is consumed with a precise invariant message, the
invalid length remains asserted as a typed failure, provider format/locked
all-target check/Clippy/nextest/doctest/Rustdoc pass, and the conformance scan
reduces `existence_only_assertions` by one without another class increasing.

**Owner:** current Atlas session. **Claimed files:** Helios
`crates/helios-imaging/src/radon.rs`, provider PM, and root PM. The branch is
published separately from the provider's dirty primary checkout.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/helios-radon-assertion` is based on `origin/main`
`7ff72e37889594b6592e1f8b8b169834765f7851` and publishes `fdfe61a`. The
success path now consumes the validated `Sinogram`; the error path matches
`HeliosError::InvalidDomainValue` and checks its field, rejected value, and
reason. The lane conformance scan reports `existence_only_assertions: 0`
versus `1` on the fetched provider default. Locked workspace all-target check,
format, warning-denied Clippy, nextest (`262/262`, 9 skipped), doctests, and
Rustdoc pass.

The implementation was published as PR
[#69](https://github.com/ryancinsight/helios/pull/69), initially at
`fdfe61aa61a92493e643b76033a7ba72e8fda68c` and now at stacked head
`7a97333158bcaa134054eef9b254798d64c394de`, based on merged default
`7ff72e37889594b6592e1f8b8b169834765f7851`. The current stack also carries
the typed Python metadata and one executable Compton book oracle; its Rust,
Python, benchmark, and mdBook checks are queued. The dirty detached primary
Helios checkout and Atlas gitlink remain unchanged until the current PR head's
checks are terminal.

## ATLAS-ADR0033-STAGES — Krylov ownership unwind, measured status [arch] — in progress

Re-measured 2026-08-20 against the trees rather than the board. ADR 0033's
four-stage plan is further along in places and wider in others than recorded.

**Stage A — close Athena's capability gap: DONE.**
`athena-core` ships `Cg<B>`, `BiCgStab<B>`, `Gmres<B, const RESTART>`, and
`Lsqr<B>` (`crates/athena-core/src/solver/*/algorithm.rs`), and `athena-leto`
ships Jacobi, ILU, and SOR/SSOR preconditioners over `LetoBackend`. Residual gap,
not part of stage A but blocking backend-generic solving: **no preconditioner
exists for the Hephaestus backend**, so accelerator PCG is unpreconditioned CG
(`crates/athena-hephaestus/src/lib.rs` versus the three `athena-leto` impls).

**Stage B — migrate CFDrs: substantially done, remainder in flight.**
Production CFDrs already solves through Athena. `cfd-math/src/linear_solver/
krylov.rs` (613 LOC) builds a `LetoBackend` and `BorrowedCsrOperator` and
dispatches Athena's solvers; it is a legitimate adapter, not a shim, because
Athena's `Gmres<B, const RESTART>` is const-generic while CFDrs selects restart
at runtime. There are no `GMRES::new`/`BiCGSTAB::new`/`ConjugateGradient::new`
call sites in `crates/*/src` at all — the single occurrence is inside a doc
comment.

What remains is the re-export shim `pub mod iterative { pub use leto_ops::{...} }`
in `cfd-math/src/lib.rs`, whose own doc calls leto-ops "the SSOT iterative-solver
types" in direct contradiction of this ADR. It keeps the Leto family alive and so
blocks stage D. The concrete duplication it sustains: `DiagJacobi<T>` in
`cfd-1d/src/solver/core/linear_system.rs` implements **both** preconditioner
traits — leto's at line 301 and `athena_core::Preconditioner` at line 311 —
exactly the duplication stage D names. Remaining consumers are five test/bench
files plus `IterativeSolverConfig` (56 references).

**Stage B increment (2026-08-22):** PR
[#363](https://github.com/ryancinsight/CFDrs/pull/363) at head `27338e95`,
rebased onto the merged format-gate default `a70faea6`. The branch deletes the
`pub mod iterative` re-export shim and migrates its callers; the `DiagJacobi`
dual-trait duplication is already resolved on the branch — only the
`athena_core::Preconditioner<LetoBackend>` impl remains. Local evidence:
`cargo fmt --all --check` clean; nextest `-p cfd-math -p cfd-validation`
675/675; warning-denied Clippy clean for cfd-math, cfd-validation, and
cfd-1d (the two `needless_update` warnings in `cfd-3d` are pre-existing
default debt the branch does not touch).

**Rebase and blocker fix (2026-08-23):** hosted run `32590225522` failed on
exactly those two `needless_update` sites — with every other debt class
cleared stack-wide they became the only remaining `-D warnings` errors, i.e.
delivery-blocking. Commit `05c025e8` deletes the two no-effect
`..Default::default()` bases (all three struct fields are specified at both
sites). Local: workspace clippy `-D warnings` reports zero errors, cfd-3d
nextest 400/400, fmt clean.

**Stage B closed (2026-08-23):** replacement gate terminal success at
`05c025e8`; PR #363 merged with the expected-head guard at default `c5f9fa2c`;
post-merge CI `32611718091` collected before further solver work on this
default.

**Stage C scoping confirmed (2026-08-23):** the Leto Krylov family now has
**zero stack-wide consumers** (`linalg::iterative` imports: helios, ritk,
coeus, harmonia, CFDrs, kwavers, moirai, tyche all scan zero), so Stage D's
consumer precondition is met and only ADR 0033's sequencing (C before D)
holds deletion. Stage C scope verified present at kwavers origin/main:
`kwavers-solver/src/forward/bem/gmres.rs` (334 LOC, f64-hardcoded dense
GMRES), `kwavers-solver/src/integration/nonlinear/gmres/` (419 LOC), and the
matrix-free operator whose `jacobian_vector_product`
(`multiphysics/monolithic/residual/jvp.rs:17`) needs the `&mut self` →
`&self` refactor (scratch-buffer cache is its only mutation). Kwavers uses
`leto_ops` only for matvec/dot primitives elsewhere — legitimate array ops,
not Krylov recurrences.

**Stage C claim blocked on lane availability:** all seven registered Kwavers
worktree lanes hold live published PR branches (#598, #590, #602, and peers);
the two-tree bound forbids minting a ninth tree, and the primary checkout is
detached and dirty. This is a genuine contention deferral: re-open when any
lane completes its hosted collection and merges (its tree then re-points),
or when a peer releases a lane. DoR is otherwise complete: outcome (one
Athena-backed Krylov implementation; delete the three Kwavers duplicates),
acceptance oracle (ADR 0033 Stage C/D acceptance — residue scan finds no
Krylov recurrence outside Athena; every consumer suite passes against
Athena), change class `[minor]` breaking internal seam per the ADR.

**Stage C — migrate Kwavers: not started, and wider than the ADR recorded.**
Kwavers declares no `athena` dependency in any manifest. It carries **three**
iterative implementations, where ADR 0033 anticipated one:

- `kwavers-solver/src/forward/bem/gmres.rs` — 334 LOC dense GMRES, `f64`-hardcoded
  (29 `f64` occurrences), Modified Gram-Schmidt Arnoldi with Givens rotations.
- `kwavers-solver/src/integration/nonlinear/gmres/` — 419 LOC (solver 249,
  tests 110).
- The matrix-free operator feeding the monolithic multiphysics residual.

The ADR's stated prerequisite holds exactly as written: `jacobian_vector_product`
at `kwavers-solver/src/multiphysics/monolithic/residual/jvp.rs:17` takes
`&mut self`, and its only mutation is the `jvp_state_scratch` buffer cache, so it
can satisfy `LinearOperator::apply(&self, ...)` once that scratch moves to
caller-owned workspace or interior mutability.

**Stage D — delete `leto-ops/src/application/linalg/iterative/`: blocked on B and
C.** Consumer check across the stack found no other repository importing the Leto
iterative family — helios, ritk, coeus, and harmonia are all clean. CFDrs and
Kwavers are the only two holding it alive.

Sequencing is unchanged from the ADR: B, then C, then D, each converting its
consumers in the same change, with no compatibility layer at any stage.

## ATLAS-BOOK-STAGING-2026-08-20 — Preserve Cargo artifact identity in mdBook gates [patch] — in progress

The shared `book-pages.yml` workflow currently strips Cargo metadata hashes and
keeps the first artifact for each crate name. RITK's exact default book run
`32404089897` disproves that selection rule: its locked graph contains
`rand_core` 0.6.4, 0.9.5, and 0.10.1, and the staged `rand_core` metadata does
not match `ritk_statistics`, producing `E0460` before the book example runs.

**Scope:** root `.github/workflows/book-pages.yml`, ADR 0035, and this item's
owner-local checklist entry. No provider source, lockfile, or book content.

**Acceptance:** the reusable workflow stages the exact hash-suffixed Cargo
artifacts without collapsing duplicate crate versions; a local RITK mdBook
probe with duplicate `rand_core` artifacts passes; YAML/whitespace checks pass;
the changed workflow is adopted by a rerun of the RITK default book gate.

**Owner:** current Atlas session. **Claimed files:**
`.github/workflows/book-pages.yml`, `docs/adr/0035-shared-publication-pipelines.md`,
`backlog.md`, `checklist.md`. RITK PR
[#204](https://github.com/ryancinsight/ritk/pull/204) merged from exact head
`9bc47d42f0d6050f4a68661c01d45806d41e583f` at default
`b35c93313c06ea55fffa680a430378dda1df8e41`. Its CI and book checks pass;
the current default CI and Pages deployment pass, and live Pages returns HTTP
200 with the expected RITK title. The Atlas pointer advances to `b35c9331`.
`recurseml/analysis` is report-only.

Themis's corresponding post-merge evidence is terminal for the build jobs:
default head `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` has successful CI
`32402753573`, MSRV `32402753617`, and `deploy / Build book` job
`96534588862` in run `32402754181`. The Pages deployment remains queued in
run `32402752669` (job `96545229314`); this is deployment-pending evidence,
not a live Pages claim.

The exact-head collection also confirms Helios default
`7ff72e37889594b6592e1f8b8b169834765f7851` with successful CI
`32393592276` and mdBook deployment `32393593050`, and Tyche default
`10410f2de1ce1529ecbff50fa740b23a1c8f77b9` with successful CI
`32394888136` and Pages deployment `32394886461`. Kwavers currently resolves
to `78af725e749c8ec4fd756d55091d557ea635aac2`; its latest hosted workflow
set targets the predecessor `b5b4fb0614ad3238ab95ff092cebd5977a201b22`, so
those runs cannot authorize the stale Atlas pointer `459f18ce`.

## ATLAS-BOOK-CALLER-PINS-2026-08-20 — Repin provider mdBook callers [patch] — in progress

**Coordinator claim (2026-08-21):** Atlas-Codex owns the root-only pointer and
evidence synchronization for Proteus, Aequitas, and Hermes. Claimed scope is
`repos/proteus`, `repos/aequitas`, `repos/hermes`, and this item in
`backlog.md`; provider source, nested checkout work, and peer PM files are
excluded.

The provider workflow audit found 20 current `main` callers still pinned to
pre-fix revisions of the reusable Atlas book workflow. Apollo and Coeus now
carry the repin on their merged defaults; Hephaestus and RITK carry it in
their active PRs. The
remaining 16 provider-scoped workflow PRs are published from each current
default without touching the dirty nested checkouts:

- Aequitas [#38](https://github.com/ryancinsight/aequitas/pull/38),
  Asclepius [#23](https://github.com/ryancinsight/asclepius/pull/23),
  Athena [#16](https://github.com/ryancinsight/athena/pull/16),
  Consus [#52](https://github.com/ryancinsight/consus/pull/52),
  Eunomia [#71](https://github.com/ryancinsight/eunomia/pull/71),
  Harmonia [#8](https://github.com/ryancinsight/harmonia/pull/8),
  Hermes [#58](https://github.com/ryancinsight/hermes/pull/58),
  Horae [#24](https://github.com/ryancinsight/horae/pull/24),
  Hyperion [#22](https://github.com/ryancinsight/hyperion/pull/22),
  Iris [#17](https://github.com/ryancinsight/iris/pull/17),
  Melinoe [#19](https://github.com/ryancinsight/melinoe/pull/19),
  Mnemosyne [#67](https://github.com/ryancinsight/Mnemosyne/pull/67),
  Moirai [#146](https://github.com/ryancinsight/Moirai/pull/146),
  Proteus [#16](https://github.com/ryancinsight/proteus/pull/16),
  Themis [#28](https://github.com/ryancinsight/themis/pull/28), and
  Tyche [#33](https://github.com/ryancinsight/tyche/pull/33).

**Acceptance:** every registered provider workflow resolves the exact shared
staging implementation `20c9398`; each provider's required hosted book gate
is terminal green; then close the PRs and record the merged defaults before
advancing any Atlas pointer. No source or book behavior changes are in scope.

**Exact-head collection (2026-08-20):** Horae #24 at
`a3b79fb` has CI `32418584339` and Deploy mdBook `32418584938` green;
Hyperion #22 at `7dca41e` has CI `32418586348` and Deploy mdBook `32418586803`
green; Themis #28 at `28bf210` has CI `32418600576` and Deploy mdBook
`32418601066` green; Proteus #16 at `653772e` has CI `32418598026` and Deploy
mdBook `32418598676` green; and Tyche #34 at `c481e05` has CI `32425417532`
and Deploy mdBook `32425418118` green. These results are bound to the exact
PR heads and do not authorize default-pointer updates.

**Integration:** the authenticated GitHub CLI merged all five exact-green PRs
with expected-head guards: Horae #24 → `d014929`, Hyperion #22 → `91df53e`,
Themis #28 → `c441acf`, Proteus #16 → `73c6c81`, and Tyche #34 → `89194f3`.
The connector's parallel merge calls returned HTTP 403, but no merge was
claimed until the authenticated merge results were verified. Post-merge CI,
Deploy mdBook, and Pages runs are queued at each exact merge commit:
Horae `32434846095`/`32434846467`/`32434845162`, Hyperion
`32434851255`/`32434851473`/`32434850406`, Themis
`32434855247`/`32434855744`/`32434854004`, Proteus
`32434859559`/`32434860258`/`32434857538`, and Tyche
`32434861620`/`32434862314`/`32434860567`. No Atlas pointer is advanced until
these post-merge runs are terminal and the deployed pages are verified.
Tyche's superseded duplicate PR #33 was closed and its branch deleted.

**Second integration batch (2026-08-20):** exact-head green PRs merged with
expected-head guards: Mnemosyne #67 → `9da9f92`, Aequitas #38 → `14fdd44`,
Asclepius #23 → `ce3fea3`, Eunomia #70 (NumPy feature contract) → `c7435a2`
followed by #71 (workflow pin) → `22a02b1`, and Moirai #145 (positioned I/O)
→ `c186fd9` followed by #146 (workflow pin) → `7f75f5e`. Post-merge runs are
queued at the exact defaults: Mnemosyne CI/Deploy `32435012042`/
`32435012409`, Aequitas CI/Deploy/Pages `32435015846`/`32435016154`/
`32435015448`, Asclepius CI/Deploy/Pages `32435020135`/`32435020483`/
`32435018341`, Eunomia CI/Deploy `32435024973`/`32435025288`, and Moirai
Python/Deploy `32435032989`/`32435033356`. Atlas pointers remain unchanged
until terminal post-merge evidence is collected.

**Third integration batch (2026-08-20):** the stacked RITK pipeline was
merged in dependency order: #201 → `3bf61e3`, #203 was retargeted from the
merged feature branch to `main` and then merged → `8196809`. Hephaestus #214
→ `7e09efa`, Hermes #58 → `c647368`, Iris #17 → `8700418`, and Melinoe #19
→ `8a67d14` also merged with expected-head guards. Post-merge runs are queued:
RITK CI/Python/Deploy `32435204760`/`32435204737`/`32435205077`, Hephaestus
WGPU/Metal/ROCm/CUDA/Deploy `32435207406`/`32435207407`/`32435207414`/
`32435207429`/`32435207800`, Hermes CI/Deploy/Pages
`32435209980`/`32435210250`/`32435209388`, Iris CI/Deploy/Pages
`32435213271`/`32435213613`/`32435212802`, and Melinoe Deploy/Pages
`32435216434`/`32435215430`. Atlas pointers remain unchanged until those
default-head gates are terminal and live pages are checked.

RITK's stacked book adoption is now the same merged-default gate: the prior
`8196809` snapshot was superseded by #204's `b35c9331`; its three post-merge
runs above remain uncollected.

**Helios caller integration:** workflow PR
[#64](https://github.com/ryancinsight/helios/pull/64) was marked ready after
its Rust workspace, Python bindings, benchmark, and book-build checks passed,
then merged from exact head `9a590ffaa65b3afc61b36f0aec2239014b6d17ae` at
default `e886754d369c56925bab558dae7c6cebf94a0df1`. The post-merge CI run
`32436531185` is queued. The workflow-only change did not trigger a new Pages
run; the next default book deployment remains the required live-page check.

**Fourth integration batch (2026-08-21):** the post-merge default gates for
Proteus, Aequitas, and Hermes are terminal-successful. Proteus run
`32434857538`, Aequitas run `32435015448`, and Hermes run `32435209388` have
completed CI, book deployment, and reporting jobs successfully. Their live
Pages endpoints return HTTP 200 with the expected titles at
`https://ryancinsight.github.io/proteus/`,
`https://ryancinsight.github.io/aequitas/`, and
`https://ryancinsight.github.io/hermes/`. Atlas advances the three gitlinks to
the exact current defaults `73c6c813`, `14fdd44c`, and `c6473688` respectively.
No provider source or nested checkout is changed. Themis has terminal build
jobs but its live endpoint could not complete TLS verification in the audit;
Horae, Hyperion, Asclepius, Melinoe, Leto, and Iris still have queued deploy
jobs, while Mnemosyne and Moirai returned 404 at their Pages endpoints. None
of those pointers advances in this increment.

**Coordinator claim (2026-08-21, second slice):** Atlas-Codex now owns the
root-only pointer and evidence synchronization for Themis, Consus, and
Eunomia. Claimed scope is their three root gitlinks plus this item in
`backlog.md`; no provider source, nested checkout, or Consus peer checklist is
included.

**Fifth integration batch (2026-08-21):** exact current-default evidence is
now terminal for Themis, Consus, and Eunomia. Themis CI, book, and Pages runs
`32434855247`, `32434855744`, and `32434854004` all succeeded; Consus CI,
documentation, and Pages runs `32436374114`, `32436374130`, and
`32436372915` all satisfied their jobs; Eunomia CI and book/Pages runs
`32435024973` and `32435025288` succeeded. Live Pages checks return HTTP 200
with expected titles for `https://ryancinsight.github.io/themis/`,
`https://ryancinsight.github.io/consus/`, and
`https://ryancinsight.github.io/eunomia/`. Atlas advances their gitlinks to
`c441acff`, `1000699f`, and `22a02b18`. No nested checkout or provider source
is changed. The remaining queued or 404 endpoints stay unadvanced.

**Live URL correction (2026-08-21):** the prior lowercase probes for Mnemosyne
and Moirai were not canonical GitHub Pages paths. Their repository names are
case-sensitive in the deployed paths: `/Mnemosyne/` and `/Moirai/` return HTTP
200 with the expected book titles. The earlier 404 observation is retained as
the lowercase-probe result, not as a deployment failure.

**Coordinator claim (2026-08-21, third slice):** Atlas-Codex owns the
root-only pointer and evidence synchronization for Mnemosyne and Moirai.
Claimed scope is their two root gitlinks plus this item in `backlog.md`; no
provider source, nested checkout, or peer PM file is included.

**Sixth integration batch (2026-08-21):** Mnemosyne's Rust verification run
`32435012042` and book/Pages run `32435012409` completed all jobs
successfully; Moirai's binding checks `32435032989` and book/Pages run
`32435033356` also completed successfully. Canonical live Pages checks return
HTTP 200 with the expected titles at
`https://ryancinsight.github.io/Mnemosyne/` and
`https://ryancinsight.github.io/Moirai/`. Atlas advances the two gitlinks to
`9da9f92e3` and `7f75f5e6`. No provider source or nested checkout changes.

**Residual exact-head sweep (2026-08-21):** after refreshing all provider
remotes, the exact-head audit reports 13 intentional drifts. The held defaults
are Horae `d1332267`, Hyperion `3bc0e43d`, Themis `2c074987`, Tyche
`7d636471`, Helios `e886754d`, Harmonia `c762c8ad`, Asclepius `a38b8b50`,
Eunomia `834bd3b4`, Moirai `ff56d602`, Leto `fc0648ee`, Apollo `fd9ecd02`,
Iris `636a2613`, and Kwavers `4d61dbfb`. The merged-default required runs for
Themis, Tyche, Eunomia, Moirai, and Apollo are queued; Harmonia CI remains
queued while its Pages run `32474560873` is cancelled. The earlier Horae,
Hyperion, Asclepius, Leto, and Iris Pages runs remain the only evidence for
those held defaults. Helios's default CI
`32436531185` is terminal, but its current source PR #69 is at stacked head
`7a973331` and remains queued. Kwavers current-default workflows
remain unverified at `4d61dbfb`; the earlier workflows at `8fc69970` and
older heads do not prove the current default. No pointer advances until each
provider's exact hosted evidence and canonical live-page check satisfy the
acceptance oracle.

**Eighth integration batch (2026-08-23):** Horae `abe42e5d`, Hyperion
`3bc0e43d`, Leto `fc0648ee`, and Iris `636a2613` each carry terminal CI and
Pages deployment success at the exact current head with live Pages HTTP 200
and expected titles; Atlas advanced all four gitlinks (commit `d9e7315`).
CFDrs advanced separately to `a70faea6` (commit `43fe895`) and, after Stage B
merged, awaits post-merge CI `32611718091` before advancing to `c5f9fa2c`.

**Seventh integration batch (2026-08-22):** Gaia PR #33 merged at default
`9b476fec` (post-merge CI + mesh book terminal, live Pages 200 with expected
title) and Harmonia's repin default `c762c8ad` reached terminal main CI,
Deploy mdBook, and pages-build-deployment success (live Pages 200 with
expected title). Atlas advanced both gitlinks in commit `0f58972`. A peer's
staged Moirai pointer to `bd70d29b` was left uncommitted: that default has no
hosted runs yet and fails its acceptance oracle. Athena `1c7a7f94` still
holds: its Deploy mdBook succeeded but its push CI run is cancelled with no
successor. Eunomia `834bd3b4`: MSRV and Deploy mdBook terminal success, but
its push CI is cancelled with no successor; Apollo `fd9ecd02`: ci terminal
success but the dynamic pages-build-deployment was cancelled.
The same refresh's structural-only audit remains `status: ok` with zero
issues across all 22 registered providers; the failure is pointer/hosted
evidence state, not a detected registration or coherence defect.

**Athena workflow repin (2026-08-21):** Athena PR #16 merged with the exact
head guard at provider default `1c7a7f94`. The change only updates the shared
book workflow reference. Post-merge CI `32476210608` and Pages `32476211063`
are queued; the nested Atlas pointer remains unchanged until those runs and
the canonical live-page check are terminal.

**Harmonia workflow repin (2026-08-21):** Harmonia PR #8 merged with the exact
head guard at provider default `c762c8ad`. The provider's post-merge CI
`32476381283`, mdBook build `32476382038`, and Pages run `32476380137` are
queued; the nested Atlas pointer remains unchanged until the current default
evidence and canonical live-page check are terminal.

## ATLAS-CONSUS-SZIP-BOUND-2026-08-20 — Bound SZIP allocation [security][patch] — in progress

The SZIP decoder previously trusted a four-byte sample count from a seven-byte
header before checking the payload or reserving output storage. Malformed input
could therefore request an unbounded allocation and abort instead of returning
a typed error.

**Evidence:** Consus PR [#51](https://github.com/ryancinsight/consus/pull/51)
adds independent header-size and payload-capacity bounds plus
`try_reserve_exact`; its hosted package, MSRV, and fuzz checks pass. The exact
head `2e24e6adda663db67b4bf1d4e1614e2c3b06fc19` merged at default
`1000699fa740c74b8aea1b9cc5311f85d3d2a3cc`. Post-merge CI and Documentation
runs `32436374114` and `32436374130` are queued. RecurseML remains report-only.
The dirty Consus checkout and Atlas gitlink are unchanged until terminal
post-merge evidence is collected.


## ATLAS-APOLLO-PYTHON-SURFACE-2026-08-20 — Ship the typed Python surface [patch] — in progress

The Apollo Python package currently exposes its symbols through `__init__.py`
but has no `py.typed` marker or `.pyi` surface. The active Apollo book lane is
clean and its executable-book PR is already merged; this follow-up is confined
to the repointed lane and does not touch the dirty primary checkout.

**Scope:** `crates/apollo-python/python/pyapollofft/py.typed`, the matching
stub surface, `crates/apollo-python/pyproject.toml`, and installed-wheel typing
tests. **Non-goals:** changing FFT algorithms or adding a second Python API.

**Acceptance:** the stub surface covers every re-exported binding and plan,
the package metadata declares typing-inclusive classifiers and project links,
the built wheel contains `py.typed`, and the installed-wheel test resolves the
public names with a value-semantic FFT smoke. Rust binding compute paths already
use `Python::detach` in the clean lane; any newly found heavy path must retain
that GIL-release contract.

**Owner:** current Atlas session. **Claimed files:** the clean Apollo book lane
repointed from its merged branch, the root item, and this PM record.

**Implementation:** Apollo commit `4e055407` was pushed on
`fix/apollo-python-surface` as PR
[#109](https://github.com/ryancinsight/apollo/pull/109) and merged with the
expected-head guard at default commit
`fd9ecd0206c2b4ee3993a42eec65a1703d592ac2`. Local evidence includes the
formatting, locked check, clippy, nextest, release `cp38-abi3` wheel build,
and 35 installed-wheel pytest cases. Hosted PR Rust and Python checks are
terminal-successful; `recurseml/analysis` is the existing report-only error.
Post-merge CI `32474434108` and Pages `32474432640` are queued. The dirty
primary Apollo checkout and Atlas gitlink remain unchanged until those default
runs and the live-page check are terminal. The merged clean lane and its local
branch were removed after the PR merge.

## ATLAS-HARMONIA-FIELD-EXCHANGE-050-2026-08-21 — Add typed physical-field exchange [major] [arch] — in progress

The current Harmonia boundary exchanges scalar slices with only runtime
dimension and time checks. That permits CFDrs, Kwavers, and Helios adapters to
connect fields with incompatible physical quantities or grid frames.

**Scope:** a clean Harmonia lane based on `origin/main`; add a no-unsafe,
zero-copy field envelope whose values are `aequitas::Quantity<T, D>`, validated
grid shape/spacing/origin/orientation metadata, and transfer validation tests.
The first slice owns the contract only; consumer adapters and numerical source
terms follow as dependency-ordered items. **Non-goals:** changing solver
algorithms, inventing unit conversions, or editing peer-dirty provider trees.

**Acceptance:** the public constructor rejects zero dimensions, non-finite or
non-positive spacing, non-finite origins/directions, non-orthonormal direction
cosines, and value-count mismatches; a valid envelope borrows the caller's
quantity slice without allocation; compile-time quantity dimensions prevent an
`Intensity`/`VolumetricPowerDensity` interchange; property and boundary tests
cover the validation partitions and orientation identity/round-trip laws.

**ADR claim:** `docs/adr/0050-typed-physical-field-exchange.md` is reserved for
this decision. The ADR must record Harmonia as the orchestration owner,
Aequitas as quantity SSOT, and the later CFDrs/Kwavers/Helios adapter path.

**Owner:** current Atlas session. **Claimed files:** this root item and the
Harmonia clean lane only. The Apollo hosted-gate monitor remains separate.

**Current increment:** Harmonia commit `5b1bc28` (on top of
`944eafebb5045a24b8353964d1a0700a2cb62098`) implemented the contract and
merged through [PR #9](https://github.com/ryancinsight/harmonia/pull/9) with
the expected-head guard at default commit
`542b80b65628d8c4a16fdfd4113a2ff029116a96`. The follow-up adds negative and
non-finite spacing cases, a valid rotated-frame round-trip assertion, and
exact shape/origin/direction compatibility failures. The clean lane passed
`cargo clippy --all-targets --all-features --locked -- -D warnings`,
`cargo nextest run --locked` (31 passed, 0 skipped),
`cargo test --doc --locked`, `cargo doc --no-deps --locked`, and
`cargo check --release --locked`. The root ADR and generated index are in
`c39f12a`; the root commit is pushed. Post-merge CI `32474562236` and Pages
`32474560873` are queued. No consumer adapter or Atlas pointer advance is
authorized until those default runs and the live-page check are terminal.
The merged clean provider lane and its local branch were removed after the PR
merge; the dirty primary checkout remains untouched.
An independent exact-head review found no implementation or ADR blocker. It
also records a verification limit: the provider CI omits `--locked` and does
not run MSRV, release, or SemVer checks; those limits are not replaced by the
local locked gates or by the queued default runs.

## ATLAS-MOIRAI-ACCELERATOR-ROUTE-2026-08-21 — Execute accelerator routes [major] [arch] — in-progress

The current Moirai route contract preserves an accelerator label only as
metadata: `moirai-transport/src/route.rs` maps accelerator routes to the local
address, and `DevicePayloadRegion` retains a host `Vec<u8>` without device
allocation or dispatch. Moirai's own gap analysis records that no GPU/TPU/NPU
backend consumes `SchedulerRoute::Accelerator`.

Scope: a clean, dependency-ordered Hephaestus/Themis integration edge that
resolves an `AcceleratorId`, dispatches one existing kernel family, and proves
CPU/WGPU value equivalence plus unavailable-device failure. Preserve the DAG:
Hephaestus consumes Moirai route/planner contracts; Moirai does not depend on
Hephaestus. Non-goals: a new accelerator runtime in Moirai, Melinoe stream
ownership, or broad scheduler redesign.

Current slice: replace Moirai transport's metadata-only accelerator address
resolution with a typed resolution that preserves the scheduler route and
accelerator identity while retaining a transport address for the later
Hephaestus edge. The package lane is `worktrees/moirai-package`, claimed for
`moirai-transport` route source/tests, benchmark source contracts, the public
facade re-export, and synchronized provider ADR/checklist artifacts. Dispatch
and CPU/WGPU execution remain a later Hephaestus/Themis slice after their bases
are refreshed; this slice does not claim device execution.

Current-slice outcome: Moirai commit `2355d42a39ff85fd3efb075075c9a916f52fc8be`
(`feat(moirai): Retain accelerator identity`) merged through PR
https://github.com/ryancinsight/Moirai/pull/147 with the expected-head guard at
default commit `ff56d60218b6f418d8db0e42c30da8185b90b6bd`. `RouteResolution`
keeps the full `SchedulerRoute`, transport `Address`, and accelerator
placement together; `RoutedArchivedSender::send_route` returns that
resolution. Exact local verification: 807/807 nextest tests passed with 6
skipped, clippy passed, format check passed, doctests passed, and rustdoc
passed. `cargo-semver-checks` is unavailable in the environment. Post-merge
Rust Workspace `32475134603` and Python Bindings `32475134582` are queued; no
submodule-pointer advance is claimed until those default checks are terminal.
The merged clean package lane and its local branch were removed after the PR
merge; the dirty detached primary checkout remains untouched.

Acceptance: accelerator identity survives route resolution; a present device
executes a real kernel and returns its value-semantic result; a missing device
returns a typed error; CPU/WGPU differential tests, route-identity tests, and
a bounded transfer/dispatch smoke pass. Claim only after refreshing the
provider defaults and reconciling the existing dirty/detached checkouts.

Owner: codex-primary. Claimed scope: `worktrees/moirai-package`,
`moirai-transport/src/route.rs`, `moirai-transport/src/route/tests.rs`,
`benchmarks/tests/benchmark_contracts/`, `moirai/src/lib.rs`, and the provider
ADR/checklist artifacts needed for this route-contract replacement.
Dependencies: current Moirai origin route contract; Hephaestus/Themis clean
bases remain a dependency for the subsequent dispatch slice. Risk/change class:
`[major] [arch]`. Last update: 2026-08-21.

**Outcome:** close the remaining cross-cutting correctness and evidence
deficits in the order below, so that a green gate means what it claims.

**Non-goals:** raising per-repository completeness scores as such; peer-owned
in-flight PR work; any capability expansion. Every item is evidence or
correctness, not new scope.

- **P0 delivery-blocking correctness** (independent, dispatchable now):
  1. Kwavers `swe/gpu/solver.rs:92` `propagate_waves_gpu` ignores its inputs,
     launches no kernel, and returns hardcoded-constant timings. Acceptance:
     either a real kernel dispatch with a CPU-differential oracle, or the
     production-named surface is withdrawn and the performance model renamed and
     moved out of the solver path. `[major]`
  2. CFDrs `cfd-validation/src/benchmarking/memory.rs:93` ungated
     `#[global_allocator]` in a library crate. Acceptance: allocator confined to
     a bench/bin target or `cfg`-gated; a consumer crate declaring its own
     allocator compiles. `[major]`
  3. Consus `consus-compression/src/codec/szip.rs:226` reserves from an
     unvalidated `u32` reachable via HDF5 filter id 4. Acceptance: length bounded
     against remaining input, `try_reserve`, typed error, plus a fuzz target over
     a malformed corpus. `[patch]`
  4. Consus `-C target-cpu=native` in committed `.cargo/config.toml`. Acceptance:
     removed; runtime ISA detection is the dispatch mechanism. `[patch]`

  Consus PR [#51](https://github.com/ryancinsight/consus/pull/51) is the
  existing owner for P0-3/P0-4 at exact head
  `2e24e6adda663db67b4bf1d4e1614e2c3b06fc19`; its repository matrix remains
  queued in run `32408174545`. Do not start a competing patch. The dead
  `.cargo/config.toml` `xtask` alias remains a separate cleanup residual after
  this PR.

- **P1 make the accelerator seam verifiable** (the audit's single largest
  evidence gap, four independent confirmations):
  5. Hephaestus host/CPU reference device implements 1 of 18 operation seams:
     `HostDecompositionOps` is the only arithmetic-family implementation.
     The shared conformance crate exports 20 clauses, while the host invokes
     only the decomposition and transfer assertions; no host conformance job
     is present in the current backend workflows. Coeus binds ten operation
     families, Athena binds dense/sparse vector families, and Kwavers binds
     `Fdtd3dOps`, so the seam gap is consumer-reachable. Acceptance: host impls
     for the seams consumers bind, and a shared conformance suite running
     GPU-vs-CPU differential cases with tolerances derived per
     `numerical_discipline`. `[minor]` — unblocks 6 and 7. The next bounded
     slice is `SUBSTRATE-003`: consolidate the nine decomposition differential
     helpers into one parameterized clause, reconcile the stale 14-versus-15
     method count, and add an exact host gate for the complete decomposition
     surface. Evidence: fetched Hephaestus `origin/master`
     `607ce3f`; current hosted results were not queried.
  6. Apollo, Coeus, and Kwavers GPU suites report green having executed nothing.
     Acceptance: an executed-case counter that fails the job at zero, plus a
     software adapter (`lavapipe`/WARP) or an explicit recorded skip that is
     visible in the gate result rather than silent.
  7. RITK `GpuFieldSmoother`/`CpuOrGpu` have no reachable GPU backend and carry
     unbacked speedup claims. Acceptance: wired to the Hephaestus seam, or the
     claims withdrawn pending it. `[minor]`

- **P2 retire vacuous gates** (cheap, high signal-to-noise):
  8. `mdbook test` coverage is uneven. Gaia's direct gate is vacuous because
     its book has zero Rust fences; Tyche, Proteus, Mnemosyne, Asclepius, and
     Iris execute real samples but retain 37 ignored Rust fences across the
     audited books. Acceptance: Gaia gains one value-semantic executable book
     example, and ignored snippets are converted to `text` or real executable
     examples where their chapter claims a workflow. The shared gate itself is
     not removed. Book chapters documenting non-existent APIs (Hephaestus,
     Mnemosyne, Helios) were corrected in this sweep; re-verify at merge.
  9. Themis `tests/topology/cpu.rs` orphaned target (14 tests never compiled);
     CFDrs 54 files / 10,543 LOC under root `examples|benches|tests` in no cargo
     target; Hermes ADR-005 generator that deletes 14 shipped kernels when run.
     Acceptance: each either wired into a target and green, or deleted.

- **P3 adjudicate the open decisions** (blocking, not mechanical):
  10. Leto/Athena solver ownership is decided: root ADR 0033 is Accepted and
      names Athena as the Krylov owner. The remaining work is deletion of the
      duplicate Leto implementation and caller migration, not a decision
      question. Acceptance: revise the affected ADRs with the dated decision,
      delete the loser, and migrate callers in one change. `[arch]`
  11. The root corpus has 48 ADRs: 15 `Proposed`, 30 `Accepted`, and 3
      `Rejected`; six Proposed records are Kwavers-related. Acceptance: each
      Proposed record is Accepted with an as-built rationale, Rejected, or
      deleted with its reason in the commit. `[patch]`
  12. Centralized ADR indexing is closed as a blocker: the root generator scans
      the Atlas root plus 23 provider ADR directories, and root conformance CI
      runs the check. Provider index dirt remains a separate peer-owned
      cleanup, not a missing generator. `[patch]`
  13. Eighteen registered-provider root manifests (19 including the RITK member
      manifest) declare `rust-version = "1.95"`; nine providers lack an
      explicit 1.95 workflow pin: Aequitas, Apollo, Harmonia, Helios, Hermes,
      Horae, Hyperion, Proteus, and RITK. Acceptance: add an MSRV job at the
      declared floor or correct the declared floor to the toolchain actually
      built. `[patch]`

**Dependencies:** 6 and 7 depend on 5. 1 through 4 are independent. 10 gates any
further Leto or Athena solver work.

**Risk:** items 1, 2, and 10 are `[major]`; 1 and 10 need an ADR before
implementation per `versioning`.

**Verification plan:** each item's acceptance oracle above, run through the
owning repository's committed gate. No stack-wide claim is made until the
per-repository gates run; this audit executed none.

**Meta-repository residual:** 16 of 25 submodule checkouts drift from their
committed gitlink; kwavers (5), consus (3), and helios (3) exceed the two-tree
lane bound; 8 empty `worktrees/kwavers-*` orphans remain. Filed here rather than
actioned, since every one of those trees holds peer state.

## ATLAS-GAIA-BOOK-GATE-2026-08-20 — Add value-semantic book execution [patch] — in progress

The fetched Gaia default `dbed97a63434a21b1b9dcd01d634276aaec99e37` invokes
`mdbook test docs/book`, but the book contains zero Rust fences. Its mesh-gallery
generator is executable but does not provide mdBook contract coverage. This is
a bounded documentation/test increment; it does not change mesh algorithms,
figures, or the peer-owned Gaia README, CHECKLIST, or untracked backlog.

**Owner:** current Atlas session. **Claimed lane:**
`D:\\atlas\\worktrees\\gaia-book-gate`. **Claimed files:** one existing Gaia
book chapter, one included example source if the book convention requires it,
and Gaia's owner-local PM entry. **Acceptance:** one real input-sensitive Gaia
API example is included by the book, `mdbook test docs/book` executes it with a
value-semantic assertion, strict links and `mdbook build` pass, and the change
is published and verified at its exact provider head. No `rust,ignore` or
existence-only assertion satisfies the item. PR [#33](https://github.com/ryancinsight/gaia/pull/33)
is published at exact head `39a4f7fb0349bbd427fd12ddd99b0acc6baa654c` after
repairing the book workflow to capture only the current Cargo compiler-artifact
paths before staging them for mdBook. The earlier book run `32417028130`
tested the pre-repair merge ref and failed with `E0463: can't find crate for
gaia`; the intermediate run `32459250549` is superseded because its broad
staging step could select multiple cached Gaia revisions. A local run against
the shared Atlas cache reproduced that cache-sensitive `E0464: multiple
candidates` condition. The exact-one-library guard is now also enforced.
Replacement CI run `32473606516` is pending and book run `32473606617` is
queued at the exact current head; the earlier replacement runs
`32473502019`/`32473502075` are superseded. Hosted clean-runner execution
remains the required staging evidence. Local `mdbook build docs/book` and link
checking pass at the repaired lane head.
`recurseml/analysis` is report-only.
- **Closed (2026-08-22):** PR #33 merged at Gaia default `9b476fec` with the
  expected-head guard; both exact-head runs `32473606516`/`32473606617`
  terminal success, post-merge main CI and mesh book runs terminal success,
  and live Pages returns HTTP 200 with the expected title. The Atlas gitlink
  advanced to `9b476fec` (commit `0f58972`).

## ATLAS-CFDRS-FORMAT-GATE-2026-08-20 — Restore exact-default formatting gate [patch] — in progress

The exact CFDrs default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97` has a red
hosted CI run `32323543129`; the failure is formatting-only in
`crates/cfd-2d/src/solvers/cell_tracking/tracker.rs`,
`crates/cfd-core/src/management/aggregates/parameters.rs`, and
`crates/cfd-core/src/physics/cavitation/number.rs`. The canonical checkout is
peer-owned and dirty, so the bounded lane owns those three source files plus
the provider validation caller required to repair the hosted runtime failure.

**Acceptance:** the exact three-file format correction and the provider-side
validation repair are committed and pushed; the provider's exact-head Rust and
Pages gates are terminal green, with no peer source or lockfile state included.
This slice does not claim broader CFDrs closure until those gates pass.

The current Atlas session owns the bounded lane
`D:\\atlas\\worktrees\\CFDrs-format-gate`, PR
[#361](https://github.com/ryancinsight/CFDrs/pull/361). The exact-head provider
CI run `32408413904` at the formatting-only head is terminal failure. The
provider repair now has local exact nine-test numerical-fidelity evidence.

**Timeout increment (2026-08-22, head `c993b906`):** the replacement hosted run
`32449587886` at `c1e4fdcf` failed on the committed 30s nextest termination
bound — `cross_fidelity_trifurcation_dominance` terminated at 30.008s. Local
instrumentation attributes the cost to the Picard assembly/Krylov path (~9s)
plus SDF meshing (~1s) spread across first-party FEM code and provider-external
numeric crates (`gaia-mesh`, `leto`, `nalgebra`), so named-package opt-level
raises measured no effect. Raising the test profile to `opt-level = 2`
measures 11.4s → 2.0s locally (5.5×), restoring hosted headroom; dev/debug
profiles are unchanged and no test or workload was reduced. Local evidence at
`c993b906`: `cfd-validation` nextest 435/435 (10.3s total), doctests 4 passed,
`cargo fmt --all --check` clean. **Closed (2026-08-23):** replacement hosted run
`32588697868` terminal success at `c993b906`; PR #361 merged with the
expected-head guard at default `a70faea6`; default CI run `32589906080`
terminal success; live Pages HTTP 200 (the merge touched no book content, so
no Pages deployment is expected). The Atlas gitlink advanced to `a70faea6`
(commit `43fe895`).

## ATLAS-CFDRS-ALLOCATOR-2026-08-20 — Remove library global allocator [major][arch] — in progress

The CFDrs provider audit confirms `cfd-validation` installs a process-wide
`#[global_allocator]` from library code. This contaminates downstream
allocation measurements and prevents consumers from declaring their own
allocator. The current session claims only the cfd-validation memory profiling
surface, its opt-in benchmark harness, its consumer-allocator regression test,
and the provider ADR/PM records; unrelated CFDrs peer edits remain untouched.

Acceptance: the library has no global allocator; the tracking allocator is
constructed only by an explicit benchmark/test harness; a downstream-style
integration test declares `System` as its allocator; and the provider's locked
workspace all-target gate passes. This is a public breaking change and follows
the provider's recorded allocator decision.

Evidence: provider commit `d1305ee2` removes the library allocator, makes the
tracking counter explicit in `MemoryProfiler` and `CfdMemoryProfiler`, adds the
`memory_profiling` benchmark and `allocator_compat` integration test, and records
the decision in `repos/CFDrs/docs/adr.md`. Direct rustfmt, focused clippy, a
non-locked diagnostic check, `cargo nextest run -p cfd-validation --lib`
(187/187), the focused allocator nextest (1/1), and benchmark compilation pass.
The required locked check is still open: the Atlas overlay makes Cargo request
a provider `Cargo.lock` rewrite under `--locked`; that lockfile is peer-dirty
and was not modified or staged by this session.
The exact provider commit is now the head of open CFDrs PR
[#360](https://github.com/ryancinsight/CFDrs/pull/360); Rust workspace and
figure checks are queued there.

## ATLAS-SUBSTRATE-003-2026-08-20 — Give the Leto/Hephaestus decomposition pair one seam and one oracle [minor][arch] — in progress

The Hephaestus audit found nine duplicated Leto differential helpers in the
decomposition conformance module, a stale 14-method count against the current
15-method `DecompositionOps` seam, and no exact host gate for the complete
surface. This session claims only the provider conformance module, its host
decomposition test, the required provider ADR/index update, and these Atlas PM
records. Other Hephaestus peer edits remain untouched.

Acceptance: one parameterized differential clause covers all current
decomposition methods with tolerances derived from the existing numerical
contract; the stale count is corrected; the host runs the same clause as the
GPU backends; and focused provider formatting, warning-denied checks, and
nextest pass. The exact hosted provider gate remains required before the Atlas
gitlink advances.

Evidence: Hephaestus commit `d24513a` routes the nine Leto differential cases
through `assert_leto_differential_contract`, corrects the host and ADR 0046
count to fifteen, and preserves the shared host clause. Local checks pass:
focused compile, host decomposition nextest (1/1), warning-denied Clippy,
doctests, and direct rustfmt/diff checks. The exact commit is the head of draft
Hephaestus PR [#215](https://github.com/ryancinsight/hephaestus/pull/215);
CUDA, Metal, ROCm, and WGPU hosted checks are queued. The local locked check
remains blocked by the Atlas overlay requesting a dirty provider lockfile
rewrite.

## ATLAS-PROVIDER-CLOSURE-2026-08-20 — Complete active provider slices [major][arch] — in progress

- **Themis executable book gate:** current Atlas session claims the provider
  workflow caller only, on the reusable `themis-book-test` lane. The existing
  book already has two included executable examples; acceptance is a provider
  PR adding the shared `mdbook-test` inputs, exact-head hosted book success,
  and post-merge default verification. PR [#27](https://github.com/ryancinsight/themis/pull/27)
  merged at default `c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` after exact
  PR CI `32399070177`, MSRV `32399070178`, and book build `32399070626`
  passed. Post-merge CI `32402753573`, MSRV `32402753617`, and Pages/book
  run `32402752669` now pass, including deployment job `96545229314`; the
  live page returns HTTP 200. The Atlas gitlink equals that merged default.

- **RITK executable book gate:** current Atlas session claims the provider
  workflow caller and existing executable samples only, on the reusable
  `ritk-book-test` lane. Open PR #201 owns source, lockfile, and connectome
  chapter changes; this item does not overlap those paths. PR #202 merged at
  default `ad5085257b6dee9110375bbca29e20d676c83f58` from exact head
  `dc9bf9cda2fd007597205312645038bc48727d0c`; local mdBook build and strict
  links pass, but the PR provider CI, Python, and book runs
  `32402257906`/`32402258085`/`32402259004` were still queued at merge. Default
  CI, Python, and book runs `32404089256`/`32404089147`/`32404089897` are now
  queued. Acceptance remains terminal passing evidence on the merged default;
  Atlas does not advance the gitlink from `d4a978f` until then. The book run
  failed with `E0460` because the shared workflow selected a hashless
  dependency artifact by directory order; root `20c9398` preserves Cargo
  artifact hashes, and RITK PR [#204](https://github.com/ryancinsight/ritk/pull/204)
  adopts it at `9bc47d42`. Its CI and book runs `32410451435`/`32410452203`
  pass; the current default `b35c9331` has terminal CI and Pages deployment
  success, and live Pages returns HTTP 200. The Atlas pointer advances from
  `d4a978f` to `b35c9331` without switching the dirty primary checkout.

- **Apollo executable book gate:** current Atlas session claims only
  `apollo/.github/workflows/book-pages.yml` on a clean `apollo-book-test` lane.
  The existing FFT round-trip and Parseval examples are included by the book
  and already carry value-semantic assertions. Acceptance is the shared
  `mdbook-test` caller against `apollo-fft`, exact hosted book evidence, and
  post-merge default verification. Apollo's peer-owned Cargo.lock, backlog,
  and CHANGELOG work remain outside this item; the hosted gate is sequenced
  after the active RITK collection. Local commit `27f0c4c3` passes mdBook build,
  strict links across 14 Markdown files, and workflow-shape checks. PR
  [#108](https://github.com/ryancinsight/apollo/pull/108) merged after its
  exact-head Rust/Python, benchmark, and book runs passed. The provider default
  is now `a0c3da9`; post-merge CI `32421484168`, mdBook `32421484508`, and
  Pages `32421483175` are terminal `success` at the merged default. The Atlas
  gitlink is advanced from `0c6ffb9` to `a0c3da9` without switching the dirty
  primary checkout.

- **Hyperion chromophore provenance:** the source audit disproved the
  unsupported ×4 premise: OMLC presents the retained hemoglobin values as
  molar extinction coefficients using 64,500 g/mol hemoglobin, so the provider
  uses those values directly. Commit `0213f947` adds the resolvable OMLC
  locator, independent source-knot oracle, accepted ownership ADR, and
  synchronized docs. Local formatting, ADR-index, mdBook-build, and strict-link
  checks pass; locked Cargo gates stop before compilation at the shared overlay
  lock-form mismatch. PR [#21](https://github.com/ryancinsight/hyperion/pull/21)
  merged at provider default `4df62f63`. Post-merge CI run
  `32415389400`, mdBook run `32415390244`, and Pages workflow
  `32415388456` are queued. The Atlas pointer remains at `e2dbc9b` until the
  merged-default gates are terminal and the deployed page is verified.

- **Hephaestus executable book gate:** the current Atlas session owned only
  `hephaestus/.github/workflows/book-pages.yml` and the included HostDevice
  and capabilities examples. The exact-head fix added the missing explicit
  crate declarations, removed two unused imports, and repinned Atlas staging
  to `20c9398`; local diff-check, mdBook build, strict links (14 files/13
  links), and workflow-shape checks passed. PR [#214](https://github.com/ryancinsight/hephaestus/pull/214)
  merged at provider `master` `7e09efa`. Post-merge provider jobs for WGPU,
  CUDA, ROCm, and Metal pass; the mdBook build and Pages deployment pass; and
  live Pages returns HTTP 200 with the expected Hephaestus title. The Atlas
  pointer advances to `7e09efa` without switching the dirty primary checkout.

- **Coeus executable book gate:** current Atlas session claims only
  `coeus/.github/workflows/book-pages.yml` on a clean `coeus-book-test` lane
  based on provider `origin/main`. The existing Tensor Basics and Matrix
  Multiplication examples are real included programs; acceptance is the shared
  `mdbook-test` caller for `coeus-ops`, exact hosted book evidence, and
  post-merge default verification. The detached primary checkout's provider
  implementation, lockfile, and PM dirt remain outside this item. Local lane
  commit `fc05cb75453bbb36d0f5b59f73b40dea0c432f44` passes diff-check, mdBook
  build, strict links (14 files/13 links), and workflow-shape checks. The
  locked package build is blocked before compilation by the shared Atlas
  overlay resolving primary-tree patches from the clean lane; hosted Linux is
  the package gate. Push and hosted collection remain sequenced behind the
  active merged-default runs.
  The failed exact-head book job was caused by missing explicit crate
  declarations in the included examples. The lane now adds those declarations
  and repins Atlas staging to `20c9398`. PR
  [#340](https://github.com/ryancinsight/Coeus/pull/340) merged after its
  provider-contract and book runs passed. The provider default is now
  `5108ed0082fc5c5ed02bc95c4bfa4ad9cdf8133b`; post-merge backend parity
  `32421487491` and mdBook `32421487793` are terminal `success` at the merged
  default. The Atlas gitlink is advanced from `5adc2d1` to `5108ed00` without
  switching the detached dirty primary checkout.

- **Live-tree conformance residual:** the local `python
  scripts/atlas-conformance.py check --worktree` sweep at audit revision
  `72cc6eb` plus live peer state exits 1 with 13 regressions and 27
  tightening classes against the committed baseline. The regressions are
  CFDrs oversized files and existence-only assertions; stale Consus classes
  from a checkout 49 commits behind origin; Moirai production `SeqCst`; and
  stale RITK implementation, type-suffixed, and commented-code classes from a
  checkout five commits behind origin. The run raises no baseline and does
  not discard peer or derived state.

- **Stack formatting sweep:** `scripts/atlas-fmt-check.py` passes for 23 of 24
  registered members. CFDrs reports 42 pre-existing unformatted files on the
  peer-owned `codex/cfdrs-tvd-test-integration` branch; no formatting rewrite
  was applied across that dirty claim. The corrected environment also passes
  toolchain preflight, version coherence, standalone lock-form (27 locks),
  registry metadata (253 manifests), board-ID lint, and strict book links.
  The full Atlas script suite passes `278` tests and `74` subtests in `8.77s`.
  The lane audit now ignores sanctioned `worktrees/.archive` metadata after
  pruning the stale Helios reference; only Kwavers's three peer-held trees
  remain reported.

- **Kwavers moving default:** fetched `origin/main` is now
  `0e786481cbcf3adad41ccb1f3efa6c94f6dc3f53`, after merged PR #436. Earlier
  hosted runs at `58b51ef3` cannot authorize the stale Atlas pointer
  `459f18ce8248ea91ace62a2f8f89a02b861a56fe`. Current PR #439 remains at
  exact head `2fa5f4d8a88d2ff16df866f15c5a1c4dd5d58b44` and is now `CLEAN` after
  a merge commit that preserves KW-CI-115 beside KW-GPU-200/201/202. No
  provider source or dirty worktree was overwritten.  The merged-default
  Pages run `32419107056`, CI run `32419106520`, architecture run
  `32419106681`, and legacy audit run `32419106514` are all terminal
  `success` at `0e786481`, and the live page returns HTTP 200. The Atlas
  pointer is advanced `459f18ce`→`0e786481` without switching or modifying
  the dirty primary checkout.
  Full exact-head/coherence audit now reports one remaining pointer drift:
  RITK `d4a978f`→`ad508525` (held: its merged-default Deploy mdBook gate
  `32404089897` is red on the E0460 hashless-artifact staging defect; the fix
  is RITK PR #204 at `9bc47d42` adopting Atlas `20c9398`, still open). Hermes
  PR #55 merged at `05441dd1`; its post-merge CI `32418079699` and Pages
  `32418078426` are terminal `success`, and the Atlas Hermes pointer is
  advanced `c5e4c2dc`→`05441dd1`.

- **RITK DTI frame contract:** PR [#198](https://github.com/ryancinsight/ritk/pull/198)
  merged at default `2d159850636a6539db61109533f399d31cc7c6f4`. Post-merge CI
  `32387951529`, Python CI `32387951635`, and Pages `32387952289` all pass.
  Live Pages `https://ryancinsight.github.io/ritk/` returns HTTP 200 with title
  `Introduction - atlas/RITK: Medical Image Processing and Registration`.
  PM closure PR [#199](https://github.com/ryancinsight/ritk/pull/199) merged at
  `ee76393fff7aaeae1a0c9f2712bcf8b8062c5303`; its docs-only closure records
  the same hosted evidence. Follow-up safety PR [#200](https://github.com/ryancinsight/ritk/pull/200)
  merged at `d4a978fce40f37b3668afa5d98783626aaf74cff`; post-merge Rust/Python
  CI `32395213485`/`32395213488` pass. Atlas advances its gitlink to the
  verified current default.
- **Tyche publication boundary:** PR
  [#30](https://github.com/ryancinsight/tyche/pull/30) merged at provider
  default `bfe6ab72915ff1d29357dd6895c39a11baecfbc0`. Post-merge CI
  `32386013998` and dynamic Pages `32386011656` both pass. Atlas gitlink
  advances to `bfe6ab72`. The facade, Consus-adapter, and Moirai-adapter
  packages are explicitly private; `tyche-core` remains the only publishable
  package. External registry/release configuration remains a separate residual.
- **Kwavers distributed queue:** PR
  [#427](https://github.com/ryancinsight/kwavers/pull/427) merged at
  `33a980acb4695500dd154111aa05a2947af4ad4d`. All 28 non-null CI gates pass;
  `WorkQueue::wait_all` waits for both queued and executing tasks; workers
  block on scheduler state notification. Atlas gitlink advances to the merged
  default.
- **Consus ADR-0045 P4 benchmark gate:** PR
  [#50](https://github.com/ryancinsight/consus/pull/50) merged at
  `e121b9d4258bab09144dfda68813aa9178090c0c`. All non-infra gates pass on
  rerun. Atlas gitlink advances to the merged default.
- **Helios Apollo lock sweep:** branch `codex/helios-apollo-lock-sweep` at
  `25f04b6` published as PR [#68](https://github.com/ryancinsight/helios/pull/68).
  Advances Apollo `d585e0f5`→`0c6ffb91`, Moirai `3d5d4c66`→`3b812865`, Themis
  `d0fcce7a`→`0484a333` in `Cargo.lock`; no Helios source or manifest change.
  Exact-head MSVC verification passes: format, locked metadata, full workspace
  check, warning-denied workspace Clippy, and Nextest run
  `4bfa9901-c55a-4cc1-a23f-b90d8f1542f8` with 262/262 tests and 9 skips.
  Hosted PR #68 required checks pass: Rust workspace, Python bindings, book
  build, and benchmark regression check. The `recurseml/analysis` context is
  report-only and remains an analysis error. PR #68 merged as
  `7ff72e37889594b6592e1f8b8b169834765f7851`; Atlas advances its gitlink to
  that merged default.
- **Tyche checklist reconciliation:** docs-only PRs #31 and #32 close stale
  TYCHE-006 and TYCHE-004 checklist entries; the merged default is
  `10410f2de1ce1529ecbff50fa740b23a1c8f77b9`. Pages run `32394886461` passes;
  current default CI `32394888136` passes at the same exact head. Atlas advances
  its gitlink to the merged default; no Tyche hosted verification residual
  remains for this item.
- **Requested-provider structural recheck:** at root commit `2fb4409`,
  `python scripts/atlas-provider-integration-audit.py --structural-only
  --provider-set requested-2026-08-14 --format json` reports `status: ok`,
  `provider_count: 20`, and `issues: []`. This validates registration and
  integration markers only; exact remote heads, checkout cleanliness, and
  hosted workflow terminality remain separate evidence classes.
- **Requested-provider exact-head recheck:** the bounded remote run at the
  same root revision exits non-zero with six pointer drifts: Hyperion, Hermes,
  RITK, Coeus, Apollo, and Kwavers. No Atlas gitlink advances are authorized
  from this run; each requires terminal hosted evidence at the fetched default
  before pointer reconciliation.

## ATLAS-KWAVERS-DISTRIBUTED-QUEUE-2026-08-20 — close queue completion and deadline contracts [patch] — in progress

- **Owner:** current Atlas session; detached Kwavers checkout with a disjoint
  distributed-scheduler scope while Aequitas hosted book gates run.
- **Claimed scope:** `crates/kwavers-analysis/src/distributed/{queue,scheduler,task,mod}.rs`;
  preserve the checkout's peer-owned medium, physics, and ADR changes.
- **Baseline findings:** `wait_all` observes only queued work after workers
  remove tasks, so it can return while the last task is executing; worker idle
  handling polls with a fixed sleep; deadline construction wraps on
  `u64::MAX` overflow.
- **Acceptance:** queue completion waits for both queued and executing work;
  workers block on scheduler state notification; overflowing deadlines return
  the existing typed invalid-input error; deterministic value-semantic tests
  cover active-task completion and the overflow boundary; focused locked
  format, Clippy, nextest, doctest, and rustdoc evidence is collected or the
  exact shared-cache blocker is recorded.
- **Landed provider increment:** Kwavers commits `073a5adbb` and `7245db7e4`
  implement and document the slice. PR [#427](https://github.com/ryancinsight/kwavers/pull/427)
  is open at exact head `7245db7e44a7f461a34ff2d67e5b7f1a76bc69c1`; local
  focused evidence passes, while repository-hosted CI/Architecture runs have
  not yet attached to the reopened PR event.
- **Non-goals:** no changes to the existing peer-owned Kwavers medium,
  physics, visualization, workflow, lockfile, or documentation edits.

## ATLAS-CFDRS-HOSTED-FMT-2026-08-20 — repair required Rust format gate [patch] — in progress

- **Owner:** current Atlas session; peer-assist claim on the clean files only.
- **Scope:** `repos/CFDrs/crates/cfd-2d/src/solvers/cell_tracking/tracker.rs`,
  `repos/CFDrs/crates/cfd-core/src/management/aggregates/parameters.rs`, and
  `repos/CFDrs/crates/cfd-core/src/physics/cavitation/number.rs`.
- **Acceptance:** the three files pass the repository formatter, the staged
  diff contains only formatter output in those files, and the focused provider
  check records the exact branch head. Unrelated peer-owned CFDrs dirt remains
  outside this item.
- **Evidence:** hosted CFDrs run `32323543129` reports the same three files as
  the Rust workspace formatting failure. This item fixes that concrete gate
  defect without changing tests, workloads, tolerances, or budgets.
- **Landed:** CFDrs commit `cd56f744` (`fix(cfd): Restore hosted formatter
  compliance`) is pushed to `codex/cfdrs-tvd-test-integration`; PR #360 open.
  Exact-file `rustfmt --edition 2024 --check` passes, and the overlay-free locked package
  check for `cfd-core` and `cfd-2d` passes.
- **Verification residual:** focused `cargo nextest` run
  `fdf1abe0-d650-4346-b1d2-e82fd96e3eed` reaches 55 passes and 27 configured
  skips before the first failure in peer-dirty
  `cfd-2d::physics::acoustics::gorkov::tests::f1_f2_analytical_values`
  (`0.19151009397460816` vs `0.2315809676184497`, bound `1e-10`); 800 tests
  were cancelled by fail-fast. The peer edit in `gorkov.rs` changed
  `typical_rbc()` from the test's `1000/1500` values to blood constants. This
  item does not modify that peer-owned file; the hosted gate remains open until
  the owning change reconciles the oracle and a clean default-head rerun passes.

## ATLAS-HOSTED-RECHECK-2026-08-19-2 — current provider state [patch]

- **Moirai packaging and scheduler repair:** the provider branch
  `fix/moirai-package-manifest` is pushed at `5ccd72944ab31adf55e020931e969cbecb3a6f4e`
  and carries the standalone package cleanup, complete metadata/examples,
  allocation-free Chase-Lev generation claims, strong arbitration CAS, and
  Miri-valid SplitDeque provenance. Local evidence at that exact head is
  `cargo package --workspace --locked` for every member with no warnings,
  `cargo nextest run --workspace --all-features --locked` 801/801 with 6
  configured skips, warning-denied workspace Clippy, doctests 19 passed/1
  ignored, rustdoc, Loom 1/1 (exact final-head run
  `d6ff0225-9353-45ef-84cc-492d74eb39bf`), and deque-focused Miri 16/16.
  The Loom invocation ran outside the Atlas development overlay while using
  the shared `D:\atlas\target` cache because the overlay resolves Moirai
  patches to the main checkout rather than this bounded lane; the standalone
  package, workspace, and value gates remain locked evidence at the lane
  head. Full-crate Miri reaches the Themis Windows NUMA FFI test, which is
  unsupported by Miri; no deque failure remains. Existing PR #143 is open,
  mergeable, and hosted Rust and book checks pass; the Ubuntu wheel smoke test
  remains pending (`32328186717`), so Atlas retains its default gitlink until
  the hosted matrix completes and the PR merges.
- **Kwavers:** fetched `origin/main` is
  `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`, the merge of PR #418 after
  ADR 112 was committed with its required Aequitas `Degree` surface. Atlas
  now points at this head in root commit `178e598`. The exact-head audit,
  overlay check, registry metadata scan (`252` manifests, `0` violations,
  `0` unverified), and standalone lock-form check (`27` locks plus the
  documented in-tree Melinoe fixture exemption) pass against this state.
- **Aequitas:** provider commit `809fc973f5df8c0bc0810161851466535efa74db`
  splits the derived SI units into six domain-named leaves and leaves
  `derived/mod.rs` as a manifest/re-export surface. The clean-provider
  conformance residual `manifest_implementation=1` is now `0`, with every
  other class unchanged at zero. Pinned-MSVC Clippy passes, Nextest passes
  `127/127`, doctests pass `17 + 9` compile-fail cases with one ignored, and
  rustdoc completes; the current Atlas pointer is advanced in this increment.
  Hosted CI `32325130976` and Pages `32325130273` pass at this exact head.
- **RITK:** PR #194 merged at `337f0dc5` after hosted CI
  `32323289141` and Python CI `32323289137` completed successfully; the
  report-only `recurseml/analysis` error does not block delivery. Fetched
  `origin/main` and the Atlas gitlink already resolve to `65bee2c2`, so no
  pointer mutation is required.
- **Standalone package gate:** running `cargo package --workspace --locked`
  outside the Atlas overlay packages the preceding RITK crates, then stops at
  `ritk-block-matching`: its `apollo-fft = ^0.27.0` requirement has no matching
  crates.io candidate (`0.26.0` and `0.25.0` are the available versions).
  This is a release-order blocker requiring Apollo 0.27 publication before the
  RITK workspace can claim complete crates.io package evidence; the dependency
  is not weakened and no release is performed without release authority.
- **Hyperion package gate:** the standalone locked package attempt fails while
  resolving crates.io Proteus: available `proteus 0.1.x` versions do not expose
  the `std` feature requested by Hyperion, although the current git provider
  does (`proteus/Cargo.toml:23-25`). This is registry publication/version
  coherence, not a reason to remove `proteus/std` from Hyperion; Hyperion and
  its downstream consumers remain release-blocked until Proteus is published
  with the matching feature surface.
- **Asclepius package gate:** standalone `cargo package --workspace --locked`
  passes for both `asclepius` and `asclepius-coeus`, including verification in
  the unpacked registry. Its dependency graph resolves published Apollo FFT
  `0.26.0`, providing a positive package result and independently confirming
  that RITK's Apollo `0.27.0` requirement is the registry-order blocker.
- **Horae package gate:** standalone `cargo package --workspace --locked`
  packages and verifies `horae v0.1.0` successfully outside the Atlas overlay.
  The package result is valid crates.io content evidence; publication remains
  governed by the provider's occupied-name/release-authority constraints.
- **Moirai package gate:** standalone `cargo package --workspace --locked`
  reaches manifest verification and stops at `benchmarks/Cargo.toml`: its
  path-only internal dependencies have no version requirements, which Cargo
  rejects for packaging (`dependency moirai-runtime does not specify a
  version`). The same manifest is present on fetched `origin/main`; this is a
  provider packaging defect, not a reason to weaken the runtime dependency
  graph. The benchmark README path and out-of-package example paths also emit
  packaging warnings and require the same provider-owned cleanup.
- **Horae:** the exact `--all-features` native gate passes `23/23`, and its CI
  and Pages callers enable the book test. The local Windows `mdbook test`
  invocation reaches rustdoc but fails with a GNU/MSVC artifact mismatch
  (`E0461`); no chapter-content failure is inferred.
- **Helios:** draft PyPI PR #67 remains open at `f31f2619`; its Rust, Python,
  benchmark, and book-build checks pass while Pages deployment is skipped. The
  checkout retains peer-owned manifest dirt.
- **Apollo:** PR #107 remains open with Rust and benchmark failures. The
  benchmark audit localizes the regression to the four const twiddle-cache
  initializers in `crates/apollo-fft/src/application/execution/kernel/mixed_radix/caches/twiddle.rs:26-29`.
- **Root worktree:** exact provider/integrator heads, overlay, registry
  metadata (`252` manifests, `0` violations), and 27 standalone lock forms
  pass locally. The intentional dirty-tree conformance snapshot reports
  `609` oversized files, `674` implementation-bearing manifests, `1,196`
  production unwraps, `518` allow sites, `803` existence-only assertions, and
  `4` excess-worktree sites; these remain peer-owned ratchet debt rather than
  reproducible clean-tree gate results.

## ATLAS-RITK-DEFAULT-RECONCILIATION-2026-08-19 — docs-only merge [patch]

- RITK default advanced from `01175d67874724eee72a88ba1ee9dd56a52d7c79`
  to merge commit `52f9d3b008269017297c4679792391958a561f7f` through PR #189.
  The merge changes only `backlog.md` and `checklist.md`; Atlas advances the
  gitlink without modifying the peer-dirty RITK checkout.
- The CI and Python runs attached to `01175d6` remain queued and do not prove
  the new docs merge. No hosted closure is claimed; the next exact-head run
  must bind to `52f9d3b` before the RITK gate is closed.

## ATLAS-PROVIDER-MERGE-RECONCILIATION-2026-08-19 — verified provider slices [patch]

- **Hyperion:** PR #18 merged at provider default merge commit
  `af28f5ac8ed56584a666e05e7fc1f28dc927e232`. The source delta is the
  provider recheck record in `checklist.md` and `gap_audit.md`; hosted
  `verify` and `supply-chain` passed at exact head `3d064ac`, and CodeRabbit
  passed. RecurseML remains an external report-only error. Atlas now records
  the merged default gitlink rather than the pre-merge branch head.
- **Asclepius:** PR #21 merged at provider default merge commit
  `f5b5fb832660a7696a0893f9abf1fc543d29fa2d`. The package/book/CI source
  delta is retained in the provider history; hosted book build, `verify`,
  and `supply-chain` passed at exact head `943c83c`, and CodeRabbit passed.
  RecurseML remains an external report-only error. Atlas now records the
  merged default gitlink.
- **Residual:** these merges close the two provider-slice delivery gates but
  do not close the stack-wide audit. Kwavers exact-head hosted runs, Apollo
  benchmark failure, Helios PR #67 hosted gates, Mnemosyne moving-default
  reconciliation, CFDrs PR #355, and RITK lock-form cleanup remain open.

## ATLAS-HORAE-CONSUMER-AUDIT-2026-08-19 — boundary finding [patch]

- **Result:** Horae's current production integration is limited to Harmonia's
  typed-time/subcycling contracts and Helios's validated `StepSize` boundary.
  `ExplicitSystem`, `step_into`, and `step_embedded_into` occur only in Horae
  tests/examples; no CFDrs or Kwavers production call site currently consumes
  the stepping API.
- **Decision:** No implicit or nonlinear solver is added to Horae. Its
  explicit-only boundary remains governed by provider ADR 0001, and Athena's
  roadmap requires a second concrete residual/Jacobian consumer before a
  shared nonlinear policy is defined. This is a consumer-gated follow-up,
  not a missing implementation to fill speculatively.
- **Residual:** CFDrs/Kwavers stepping migration is not complete and remains
  with their peer-owned worktrees; the exact production call-site migration,
  analytical oracle, and consumer gates must land before claiming full Horae
  stepping integration.

## ATLAS-HOSTED-RECHECK-2026-08-19 — moving-default evidence

- **Kwavers:** `origin/main` advanced to `9e7e5e95`; Architecture Validation
  `32282670417`, Legacy Migration Audit `32282670463`, and CI/CD Pipeline
  `32282670360` are queued. Atlas retains the previously verified gitlink
  `0a9842a` until those exact-head gates complete. The structural audit reports
  this one expected pointer mismatch and no other provider mismatch.
- **Apollo:** PR #107 head `d408c738` remains open; benchmark run `32217561595`
  fails 19 counterbalanced cases, while Python bindings pass and the Rust job
  is cancelled. No performance claim or pointer advance is made.
- **Helios:** PR #55 head `83f5ccea` has a failed Rust gate but passing Python
  and benchmark checks. The provider checkout contains peer-owned manifest dirt.
- **Mnemosyne:** default `b883cd1` has CI `32281506800` queued; Atlas retains
  that pointer while the local checkout remains peer-owned and dirty.
- **CFDrs:** default `834340f7` has completed CI `32230993545` successfully;
  the historical PR #355 failure is not treated as current default evidence.

## ATLAS-PUBLISH-GRAPH-2026-08-19 — crates.io dependency closure

- `scripts/publish-order.py --json` resolves 182 publishable packages across
  34 dependency layers with zero unresolved edges and no contested names.
- Fourteen publishable packages remain blocked by unpublishable foundations:
  `hyperion` blocks CFDrs, Helios, and Kwavers consumers; `proteus` blocks
  CFDrs, Helios, and Kwavers consumers; `horae` blocks `helios-domain`; and
  `asclepius-coeus` blocks `helios-planning`. These are release-topology
  blockers, not compilation evidence.
- The provider manifests intentionally retain `publish = false`; Horae’s
  board records its occupied registry name, while `hyperion` and `proteus`
  have occupied crates.io names. Renaming/flipping them is a breaking,
  release-authority change and remains an explicit follow-up rather than an
  implicit compatibility rename.

## ATLAS-PROVIDER-INTEGRATION-2026-08-18-CURRENT — superseding recheck [patch]

- **Kwavers metadata correction:** provider commit `308d91594` separates the
  MATLAB-free `k-wave-python` comparison extra from the MATLAB Engine extra,
  repairs the repository-root `maturin` commands, and is recorded by Atlas
  pointer commit `ad977c6`. The compiled extension and hosted comparator remain
  open.
- **Kwavers guidance cleanup:** provider commit `498f38a3e` removes the last
  stale `cd pykwavers` and `pykwavers-*.whl` instructions from test diagnostics
  and examples; Atlas records the pointer in `0a3e2dd`. The compiled extension
  and hosted comparator remain open.
- **Kwavers workflow closure:** provider commit `2bc5dd161` repins the book,
  Python-wheel, and crates.io callers to Atlas reusable-workflow revision
  `2f17abc`; the Python `atlas-ref` now names the pushed provider graph. Atlas
  records the exact provider head in `55d8b8d`. YAML parsing passes; the local
  extension and hosted comparator remain open.
- **Kwavers comparator gate:** provider commit `4e0135c76` adds a bounded
  Ubuntu/Python 3.10 wheel job that installs the declared k-Wave Python range
  and executes the real comparison suite with slow tests enabled. Atlas records
  the provider head in `2e00759`; closure is pending its value-semantic result.
- **Kwavers comparator dispatch:** provider commit `a10183c80` adds an explicit
  manual trigger to the wheel-smoke workflow, and Atlas records the exact head
  in `4073b1f`. The hosted parity run is still pending.
- **CFDrs rerun:** PR #358 now points at `5e13018a` after a hosted Clippy
  failure found and the provider fixed `clippy::inconsistent_struct_constructor`
  in `newton_fallback.rs`. Rust and figure jobs are pending; the pointer stays
  at the prior verified integration head until both pass.
- **Status:** Tyche cleanup, Aequitas integration, and the Aequitas/Themis
  hosted closures are complete for this increment. The remaining integration
  residuals are Apollo PR #107's rerun, Mnemosyne's moving default, CFDrs's
  figure/hosted closure, Kwavers's missing local Python extension, Helios's
  provider PM drift, and four peer-owned lane-topology violations. The
  structural provider audit, overlay, and standalone lock-form gates pass;
  exact-head is blocked only by Mnemosyne's unadvanced default.
- **Tyche evidence:** provider commit `de925e6` consolidates the shared
  Latin-hypercube/Sobol checked index conversions, removes five production
  type-suffixed helper names, and merged through PR #26 at default
  `7e55ff8f`. Nextest 51/51, doctests 18/18, warning-denied Clippy, rustdoc,
  and the conformance report all pass; every tracked conformance class is
  zero.
- **Atlas evidence:** the root pointer now matches fetched RITK default
  `9fa4981e`, a docs-only merge on top of the audited `f9d04a79`. Lock-form
  passes for 27 standalone locks and conformance passes 12/12. The latest
  exact-head audit is `OK` and the overlay reports aligned requirements and
  locks; the earlier RITK Apollo/Hermes local residual is superseded by the
  current peer checkout state.
- **Hephaestus evidence:** its default branch is `master`; head `607ce3f`
  passes CUDA `32083561386`, WGPU `32083561356`, ROCm `32083561357`, and Metal
  `32083561389`. The prior absence-of-run classification is superseded.
- **Coeus evidence:** PR #339 merged its Apollo FFT 0.27 lock resolution at
  default `5adc2d1649bfd2bf68c529b011308e150375810d`; Atlas stages that exact
  gitlink without touching the dirty primary checkout. The former backend
  parity failure at `79f05dfd` is superseded by the merged provider closure.
- **CFDrs evidence:** PR #355 carries provider commit `1bebb5e1`. The
  previous Rust-gate timeout is addressed by caching the normalized parabolic
  inlet profile once per solve. Exact-head run `32197696210` now fails in the
  hosted Clippy job at `cfd-2d/src/solvers/ns_fvm/solver/solve.rs:218` for
  `clippy::if_not_else`; the book-figure job passes. The provider branch needs
  that warning-denied correction before merge; no CFDrs checkout was changed.
- **Aequitas evidence:** PR #35 merged the provider structure cleanup at
  default `260ad10dd5480eef8c82958d1d148199656db59e`; its verify,
  supply-chain, post-merge CI `32198085105`, and Pages
  `32198084983` checks pass, with RecurseML report-only. Atlas advances the
  Aequitas gitlink to the exact merge commit without modifying the provider
  checkout.
- **RITK evidence:** fetched default `9fa4981e` is the docs-only merge of PR
  #176 (`backlog.md` correction). The Atlas gitlink is staged to that exact
  commit; the previously collected CI/Python runs remain attached to `f9d04a79`
  and do not establish the new default head. No run is currently attached to
  `9fa4981e`.
- **Gaia polyline/direction evidence:** Atlas now advances the gitlink to
  merged provider default `dbed97a63434a21b1b9dcd01d634276aaec99e37`, which
  contains the validated `gaia::Polyline` contract and the new
  `UnitSphereDirectionSet` backed by the existing `GeodesicSphere` and Leto
  `UnitVector3`; RITK's TCK/TRX consumers import Gaia's canonical type
  directly. Provider local nextest 972/972, warning-denied Clippy, doctests
  9/9, format, and Rustdoc pass. PR #32 hosted CI `32206596573` and mesh-book
  verification `32206596795` pass; CodeRabbit passes and `recurseml/analysis`
  remains report-only error.
- **Mnemosyne evidence:** PR #62 source head `0022926` passed Rust
  verification, MSRV, Loom, Miri, aarch64, ThreadSanitizer, and CodeRabbit;
  `recurseml/analysis` is report-only. The provider default moved from
  `43cdf047` to `cbccb7ee826b387e4e0ccc4499beb57a88bb51c7` after the first
  exact-head run `32206977029` failed Miri compilation on the missing
  `SEGMENT_SIZE` import. Exact-head run `32208332797` is now in progress for
  the provider's corrected Miri-gate topology; Loom, aarch64, and
  ThreadSanitizer are green while Rust verification and Miri remain
  uncollected. Atlas remains at `64f0d2e` until that exact default-head run
  completes.
- **Hosted recheck:** Aequitas CI `32198085105` and Pages `32198084983` pass
  at `260ad10`; Themis CI `32194584768`, MSRV `32194584736`, and Pages
  `32194583598` pass at `0484a333`. CFDrs run `32197696210` fails only in
  Clippy at the provider source location recorded above.
- **Acceptance:** collect Apollo PR #107's rerun, the corrected CFDrs exact-head
  run, the absent RITK default run classification, Horae PR #19's exact-head
  checks, and Mnemosyne run `32208332797`; then reconcile only verified
  provider heads. The overlay and standalone lock-form gates pass; the current
  exact-head gate is blocked by the unadvanced Mnemosyne default. Preserve
  peer-owned checkout and lane state.
- **Documentation evidence:** the stack-wide link detector passes for all 23
  registered provider books with zero missing files, missing anchors, or read
  failures. Its fixture regression suite passes 43/43 with the intentional
  missing-link case covered.
- **Automation cleanup:** the committed fast Python tier had one collection
  defect because `test_atlas_scattered_containers_classify.py` imported through
  `scripts.*` while `pytest.ini` exposes `scripts` as the module root. The
  import now matches the configured namespace; the fast tier passes 225 tests,
  17 deselected tests, and 74 subtests in 13.75 seconds.
- The committed slow Python/book tier also passes 17/17 in 1.62 seconds;
  documentation helper coverage is green at the delivered root revision.
- **Horae result:** provider lock commit `9cc9fd8` plus PM synchronization
  `aefe641` and evidence-boundary correction `91a020c` pass post-merge CI
  `32202560133` (`verify` and `supply-chain`) and Pages deployment
  `32202559349` at exact default `1ed6a172aa1ef57765c4d07ae740e6c297913567`.
  Local-graph format, locked metadata, both feature configurations, Clippy,
  20/20 Nextest, doctest, rustdoc, and cargo-deny pass; the root gitlink now
  records the merged default. The root-overlay rejection remains a
  development diagnostic rather than standalone proof.
- **Hyperion lock slice:** provider commit `880eb8c` refreshes the clean
  standalone lock to Aequitas `260ad10`, Eunomia `85e590b`, and Proteus
  `f612c99`; hosted `verify` and `supply-chain` pass at exact head
  `880eb8cce28d1e887942fbeb185a1cf4173c776a`, and PR #15 merged at default
  `0156f59f78aba1e3b06d4511ffb1ce30d5c0c6d4`. Local format and locked
  all-feature metadata pass. The root-overlay `cargo check --locked` rejection
  remains a pre-compilation development-overlay diagnostic, so Atlas advances
  only to the verified provider merge commit. Provider-local HYPERION-006
  closeout passed hosted `verify` and `supply-chain` at exact head
  `86486139120243e0b6cae84143d7a914eb51a8a3`; PM-only PR #16 merged at
  default `93157c235d1bfabd88a4720b4a02370ff2a00cc2`.
- **Clean-checkout evidence:** after fast-forwarding the owned Horae and
  Hyperion checkouts to their merged defaults, the fresh
  `--require-clean-checkouts` audit reports 23 findings across 17 peer-owned
  provider checkouts. Head drift is present in Themis, Tyche, Aequitas,
  Moirai, RITK, Hephaestus, Coeus, and Apollo; tracked or untracked dirt is
  present in Themis, Proteus, Consus, Helios, Harmonia, Eunomia, Moirai,
  Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. RITK also has
  an `apollo-fft 0.26.0` requirement that does not accept the current 0.27.0
  package. No peer checkout was changed.

**Current lane residual:** `python scripts/atlas-lane-audit.py` reports five
violations: Consus has four trees plus a lane outside the canonical root,
Kwavers has four trees with a detached lane, and RITK has four trees. These
are peer coordination state; no lane or checkout was changed by this pass.

**Cache-fork residual:** the fresh provider conformance scan reports one real
Cargo cache fork at `repos/horae/target` (`.rustc_info.json` present). The
configured shared target is `D:\atlas\target`; the repo-local cache is derived
state, not source. Its exact recursive deletion was refused by the shell safety
policy in this pass, so it remains open under ATLAS-CACHE-FORK-055.

## ATLAS-MNEMOSYNE-CONFORMANCE-001 — NUMA bucket helper consolidation [patch]

- **Status:** provider implementation complete at `0022926`; PR #62 merged at
  default `553499056ae37f3aa9f249cc507a0a09e55fd08d`, followed by provider
  TSan documentation commits `9754ebc`, `1c79909`, and `64f0d2e`. The Atlas
  gitlink is advanced to current default
  `64f0d2ebe58e14705ca2345cad2c705f99a6b611`.
- **Scope:** `crates/mnemosyne-arena/src/segment/pool/numa_bucket.rs` and its
  two callers; no allocator algorithm or public API change.
- **Acceptance:** replace the two type-suffixed production bucket helpers with
  one domain-named conversion, preserve NUMA bucket behavior through focused
  value-semantic tests, and reduce Mnemosyne's conformance
  `type_suffixed_fns` count from 2 to 0 without increasing any debt class.
- **Verification:** local format, package Clippy, sanctioned nextest 65/65,
  doctest compilation, warning-free rustdoc, and the provider conformance
  report pass at the exact commit. Hosted checks passed before advancing the
  Atlas gitlink to the provider merge commit.
- **Hosted state:** PR #62 head `0022926` has Rust verification
  `32196541600`, MSRV `32196541558`, Loom, Miri, aarch64, ThreadSanitizer,
  and CodeRabbit passing; `recurseml/analysis` is report-only. The provider
  merge commit is `553499056ae37f3aa9f249cc507a0a09e55fd08d`; the current
  fetched default is `64f0d2ebe58e14705ca2345cad2c705f99a6b611` after the TSan
  and backlog closeout documentation commits.

**Instrument correction, applied before anything else was measured.**
`scripts/atlas-conformance.py:131` classified a file as test code only when a
*path part* matched `tests`/`benches`/`examples`/`fuzz`. `Path.parts` yields
`tests.rs` as a filename, never `tests`, and `split_test_region` only splits on
an *in-file* `#[cfg(test)]` — so every co-located `src/**/tests.rs` sidecar was
scanned as production. Four audits reached that conclusion independently
(consus, moirai, ritk, apollo). Fixed by matching directory parts only plus a
new `declared_cfg_test` check that reads the parent module's
`#[cfg(test)] mod <stem>;` declaration; the baseline was regenerated in the same
change per the generator contract. Effect: stack `unwrap_production`
4713 → 1460 (kwavers 2630 → 259, consus 709 → 334), with the counts moving into
the test-region classes where they belong (`existence_only_assertions`
598 → 807, `sleep_synced_tests` 117 → 132). **Every burn-down target recorded
before this fix was aimed by a broken instrument and must be re-derived.**

**Root checkout repair (2026-08-17):** four Atlas workflows failed before
their gates because the Athena gitlink named an unreachable provider commit
`638ca74f`; the root pointer is repaired to fetched Athena `origin/main`
`bd9346f6`. The nested Athena checkout remains peer-owned and untouched. The
failure class is submodule reachability, not provider implementation evidence.

**Second checkout repair (2026-08-17):** the same recursive checkout audit
reached Gaia and found root gitlink `fa35887e` absent from the provider remote;
Gaia `origin/main` is `9595668`. Atlas repairs the root pointer only. The
nested Gaia checkout is clean but behind its fetched default, so it remains
provider-owned state rather than an Atlas source edit.

## ATLAS-HOSTED-STATE-2026-08-18-2230 — exact-head gate recheck [patch]

- **Themis:** default `d0fcce7a` has MSRV and Pages success, Windows CI
  success, and Ubuntu CI failure at `src/query/platform.rs:55` for Clippy's
  `borrow_as_ptr` pedantic lint. The provider-owned fix is to use the explicit
  raw-pointer form required by the current lint floor; no local checkout edit
  was made because Themis contains peer-owned staged and unstaged work.
- **Themis resolution:** PR #26 merged at provider default `0484a333` after
  its Ubuntu/Windows CI, MSRV, nightly compile-fail, Miri, and CodeRabbit
  checks all passed. Atlas stages only this gitlink advance; the dirty primary
  checkout remains at the prior head and is untouched.
- **Post-merge gate:** Themis default-branch MSRV `32194584736`, CI
  `32194584768`, and Pages `32194583598` pass at `0484a333`.
- **RITK:** current default `f9d04a79` CI `32192759850` and Python CI
  `32192759832` remain queued. The preceding Python run `32184697093` passed
  its Rust, Clippy, Rustfmt, and platform test jobs but failed three
  SimpleITK inverse-displacement parity assertions; this is behavioral
  evidence, not a reason to widen tolerances.
- **RITK source resolution:** the Apollo 0.27 consumer sweep itself is already
  merged as PR #167 at default `f9d04a79`; its Rustfmt, dependency-alignment,
  Clippy, Python wheel, and platform checks all passed. The remaining local
  exact/overlay failure is the stale initialized checkout at `86bd9fba` and
  its old lock, not an unmerged RITK source change.
- **Consus:** Documentation `32184845179` still fails before rustdoc because
  `consus-zarr` declares a missing `s3_rusoto_moirai` benchmark target; the
  current CI run remains queued and Pages success does not close it.
- **Coeus:** Backend parity `32147262055` still fails all provider-contract
  jobs before tests because the locked graph asks for Apollo FFT 0.27 while
  the Apollo revision supplies 0.26. The lock/requirement closure remains
  provider-owned and no compatibility path is added.
- **Hephaestus:** no default-branch Actions run exists in this sweep. The
  absence of a run is an evidence gap, not a passing gate.

## ATLAS-MULTIPHYSICS-ADOPTION-100 — CFDrs/Kwavers/Helios provider adoption and suite closure [major] [arch] — in progress

- **Completed claim (atlas coordinator, 2026-08-21):** exact committed-gitlink
  source mode for `scripts/atlas-multiphysics-audit.py` and its tests is
  implemented and verified. The claimed files were that script, its focused
  test, and this item. Peer-owned source, consumer, and lane checkouts remain
  out of scope.
- **RITK release-workflow closeout (fresh recheck):** PR [#194](https://github.com/ryancinsight/ritk/pull/194)
  merged at `337f0dc5` with merge commit `65bee2c2`. The fetched RITK default
  is `b35c93313c06ea55fffa680a430378dda1df8e41`, exactly matching the Atlas
  gitlink. The hosted connector returned no workflow records for the merge
  SHA, so this closes the merged workflow-only claim but does not assert
  post-merge CI, Pages, or live-release evidence.
- **RITK claim closeout:** `RITK-DOC-GATE-210` is fixed in provider commit
  `9e1c276a`, which adds a warning-denied rustdoc CI job and corrects five
  public-doc/private-link or broken-link defects. Exact workspace rustdoc
  generates 40 targets, focused nextest passes `817/817`, and focused clippy
  passes with `-D warnings`; this increment advances the Atlas `repos/ritk`
  pointer to `9e1c276a`.
- **Horae claim closeout:** clean default `0df563a69693418b267f337fa4bc9dfb7c1aeb1b`
  passes the exact `--all-features` native gate `23/23`. Horae CI already runs
  `mdbook test`, and its Pages workflow enables the shared `mdbook-test` gate.
  The local Windows `mdbook test` invocation stops before chapter assertions
  with `E0461` because mdBook selects GNU rustdoc while the shared stack
  artifacts are MSVC; no Horae source or pointer change is warranted, and the
  hosted Linux book gate remains the configured cross-platform book evidence.
- **Kwavers pointer reconciliation:** the fetched provider default is
  `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`, while Atlas still points at
  `b571927442b074fb0622beabdf3f2535dff1951a`. This increment advances only
  the root gitlink to the fetched default; the peer-owned Kwavers checkout is
  dirty on `ff4dc868` and remains untouched.
- **Integration recheck closeout:** root `a1fd1e4` passes the exact-head audit
  for all 22 providers and CFDrs/Kwavers/Helios, the stack overlay check, the
  registry metadata scan (`252` manifests, `0` violations), and the standalone
  lock-form check (`27` locks, one documented in-tree Melinoe fixture
  exemption). The lane audit remains red only for Consus (`3` worktrees) and
  Kwavers (`5` worktrees); no lane was switched, deleted, or overwritten.
- **Live conformance evidence:** the intentional `--worktree` scan remains a
  dirty-tree snapshot, not a reproducible gate. It reports `609` oversized
  files, `675` implementation-bearing manifests, `1,196` production unwraps,
  `518` allow sites, `803` existence-only assertions, and `4` excess-worktree
  sites; these counts are peer-owned ratchet debt and are not silently reset
  by the Atlas coordinator.
- **Checkout ownership boundary:** Gaia's apparently clean checkout is in an
  interactive rebase on `cascade/provider-042`; switching it to the recorded
  root gitlink was refused and no rebase state was touched.
- **Hosted residual recheck (2026-08-20):** [CFDrs PR #357](https://github.com/ryancinsight/CFDrs/pull/357)
  has passing Rust and figure jobs in run `32225060679`; only its RecurseML
  analyzer reports an error. [Apollo PR #107](https://github.com/ryancinsight/apollo/pull/107)
  remains red: benchmark run `32217561595` and Rust run `32217561627` fail;
  the independent benchmark audit localizes the regression to the four
  const twiddle-cache initializers in `twiddle.rs:26-29`, with the required
  repair being a single-variable revert in
  `crates/apollo-fft/src/application/execution/kernel/mixed_radix/caches/twiddle.rs:26-29`
  with the benchmark instrument unchanged.
- **Hosted completion boundaries:** [Helios PR #67](https://github.com/ryancinsight/helios/pull/67)
  is draft but its Rust, Python, benchmark, and book-build jobs pass in runs
  `32284640806` and `32284641544`; Pages deployment is skipped. [RITK PR #190](https://github.com/ryancinsight/ritk/pull/190)
  is draft with Rust, Python, wheel, and book-build gates passing in runs
  `32297172555` and `32297173130`; Pages deployment is skipped. Hermes PR #55
  has green substantive gates in `32255618310` but remains draft; RecurseML
  errors remain analyzer-only. Kwavers PR #417 has a fully green substantive
  matrix in runs `32316400677`, `32316400868`, `32316401011`, and
  `32316401183`, with Pages deployment skipped; PRs #420, #421, and #422 have
  pending matrices and are not completion evidence.
- **RITK release-workflow slice:** provider commit `337f0dc5` on branch
  `ci/ritk-release-timeout` adds `timeout-minutes: 30` to the wheel-build job
  and `timeout-minutes: 10` to the trusted PyPI publish job. PR #194 is draft;
  YAML parsing and the local conformance scan pass (`workflow_missing_timeout`
  `1 -> 0`), while its Rust, Rustdoc, Python, wheel, and dependency-alignment
  checks are pending. RecurseML reports an analyzer error only. Atlas remains
  at RITK `9e1c276a` until the provider default advances; no hosted success is
  inferred from pending checks.
- **Kwavers PR #418 closeout:** the ADR and convex-array rasterizer seam merged
  at provider default `64b982bdbfc2b7e36f11971947f5bdd8ed59d1f1`. The fresh
  default contains ADR 112, its index row, and the Aequitas `Degree` surface;
  no stale architecture record remains in the provider default. Atlas advances
  its gitlink in this integration increment while the primary checkout remains
  dirty on peer branch `feat/aperture-sir-seam` and is not switched.
- **Kwavers PR #417 closeout:** the typed `Degree` adoption merged at provider
  default `b571927442b074fb0622beabdf3f2535dff1951a`. Its Rust, Python-wheel,
  benchmark, feature, Miri, security, documentation, k-Wave, and architecture
  checks passed; Pages deployment was skipped and RecurseML remained
  report-only. The Atlas pointer advances to this merge commit in the
  integration increment below; the primary Kwavers checkout remains dirty on
  peer branch `feat/aperture-sir-seam` and is not switched.
- **Kwavers post-merge integration closeout:** Atlas root `a00a0d1` advances
  the Kwavers pointer to `b5719274`; exact provider/integrator heads, the stack
  overlay, registry metadata, and 27 standalone lock forms pass. The lane
  audit remains limited to Consus (3 trees) and Kwavers (5 trees), with all
  peer-owned lanes preserved.
- **CFDrs PR #357 closeout:** the hosted-closure documentation increment merged
  at provider default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97`. The Rust and
  figure jobs passed at the documented exact source head; Pages and PyPI remain
  explicitly open. The Atlas pointer advances to this merge commit in the
  integration increment below; the primary CFDrs checkout remains dirty on
  peer branch `codex/cfdrs-tvd-test-integration` and is not switched.
- **CFDrs post-merge integration closeout:** Atlas root `c721c3e` advances the
  CFDrs pointer to `aa54f5cd`; exact provider/integrator heads, the stack
  overlay, registry metadata, and 27 standalone lock forms pass. The open
  Pages/PyPI items remain provider-owned delivery work and are not inferred
  from this documentation merge.
- **Aequitas claim closeout:** dimensional-law tests were split into named
  angle and complex-value modules in provider commit `c908af1`; the focused
  nextest gate passes `40/40`, clippy passes with `-D warnings`, and Atlas
  records the pointer in commit `84eb033`.
- **RITK claim reconciliation:** `ATLAS-RITK-TRANSFORM-DIRECTION-081` was
  already fixed in provider commit `3aa73ba0`, an ancestor of RITK default
  `ebf2f499`. The focused `ritk-filter`/`ritk-diffusion` gate passes
  `1,284/1,284` tests (11 skipped) and clippy with `-D warnings`; oblique grid,
  inverse-displacement, and marching-cubes regressions are present.
  `FodVolume` intentionally documents an axis-aligned frame contract, so no
  RITK source change was warranted.

The active product boundary is a multiphysics simulation suite built from the
CFDrs, Kwavers, and Helios integrators. The provider set is `horae`,
`hyperion`, `harmonia`, `themis`, `tyche`, `proteus`, `mnemosyne`, `consus`,
`helios`, `aequitas`, `asclepius`, `eunomia`, `moirai`, `ritk`, `melinoe`,
`leto`, `hephaestus`, `coeus`, `apollo`, `gaia`, `hermes`, and `iris`.
`tyche` is the canonical spelling; `tychee` is retained only as a historical
alias in audit text. Atlas owns the provider graph, exact gitlinks, overlay,
cross-repository gates, and integration documentation; each member owns its
source implementation and provider-local tests.

- **Current slice:** Helios PR #59 carries the caller-side `mdbook test`
  enablement, CFDrs PR #347 carries the pressure-cache, hemolysis-error, and
  book-fence slices,
  and Apollo merged default `ed6d6905` carries the provider-owned public
  `PlanScratch` bound required by CFDrs. Helios PR #59 is merged at default
  `679402ae` with Rust, Python, benchmark, and book gates passing; CFDrs PR #347
  merged provider source head `f7bc741184a000338a5f4d4edf261a6dcfa266c8` into
  default as `84499e957d3d0c8ce50b9573185a1f55885f38e2`. Exact-head Rust run
  `32046526277` passes format, check, ordinary tests, numerical fidelity (14/14,
  3036 skipped, 8 slow; 247.309 s), and doctests; figure job `95435610232` and
  book build `95435671291` pass. Post-merge Pages run `32047447199` passes build
  and deployment. Post-merge Rust run `32047446607` passes format, check, and
  ordinary tests but fails numerical fidelity with 12/14 passed and timeouts in
  `microventuri_35um_case_produces_converged_informative_2d_result` and
  `cross_fidelity_trifurcation_dominance` at 30.006 s. The preceding Rust run failed before checkout on a
  GitHub 503/429 action-download response (`32043533301`, job `95426903063`).
  The preceding Pages run (`32043533628`, job `95426905897`) reached the
  package build and exposed the missing `fontconfig.pc` system dependency.
  Atlas shared workflow `bb505e5` now installs the required headers and the
  CFDrs caller pins that commit. New exact-head CI and Pages runs
  `32044071453` and `32044071732` were infrastructure-red. PM-only and
  source-correctness heads were superseded by `f7bc7411`; Rust job
  `95430179027` and Pages job `95430210781` in runs `32044765872` and
  `32044766414` failed before checkout on codeload 503/429. The figure job
  `95430179037` passed; the Pages retry `95430855675` passed the prior exact
  head. CodeRabbit and all required PR checks are successful; the PR is merged.
  The Atlas gitlink sweep below is complete for moving Mnemosyne,
  Aequitas, Leto, and CFDrs defaults;
  while Helios is already at merged default `679402ae`. Kwavers PR #402 carries
  the current provider FDTD and uninitialized-GPU-resource correction at exact
  source head `e1648019`; its hosted matrix is pending. PR #386 remains historical
  evidence for the earlier multi-field field-preservation closure, not current
  exact-head proof. The
  existing CFDrs decision to remove its newly introduced legacy-Clippy step is
  a documented gate-boundary decision, not a lint-debt closure; the remaining
  lint floor stays in the Atlas conformance ratchet.

**Moving-default reconciliation (2026-08-17):** Atlas is advancing fourteen
fetched provider defaults in the current root commit: Themis `f61173bc`, Tyche
`5eeaba95`, Proteus `cb70021b`, Mnemosyne `d1144f74`, Consus `2dcf05a8`,
Helios `39a24992`, Hermes `dd4cb129`, Aequitas `c74b662c`, Asclepius
`5de8a48c`, Moirai `3d5d4c66`, RITK `ae23d4b2`, Coeus `b14777d8`, Apollo
`df8999f9`, and Iris `da210d2f`. This pointer evidence is separate from
provider hosted-gate evidence. The nested primary checkouts remain peer-owned.
The CFDrs follow-up is pushed at `e6633964` on
`codex/cfdrs-runtime-residual` and is carried by PR #348. Its final local
value-semantic gates pass; the exact-head hosted Rust and Pages gates remain
the delivery gate.

**Live exact-head sweep (2026-08-17):** fetched provider defaults advanced
Mnemosyne to `924cdcce`, Aequitas to `c74b662c`, and Leto to `d966e32c`. Their
root gitlinks are advanced to those fetched default heads; the primary
checkouts remain peer-owned and may be on separate branches with dirty
lockfiles or artifacts. Only the root gitlinks are advanced here. The
the exact requested 20-provider audit, lane audit, and nine conformance tests
pass after this pointer sweep.

**Expanded audit refresh (2026-08-18):** the active product scope is the
22-provider set named above, not the earlier twenty-provider snapshot. The
Atlas structural audit now includes Harmonia and the corrected Tyche spelling
and checks active registration, fetched-default gitlinks, and exact-head
workers. Apollo PR #104 has merged into provider default `d585e0f5`; the
provider package is now `apollo-fft 0.27.0`. The latest root source head
`c049d26` passes hosted Atlas conformance run `32159744862`, while hosted
overlay run `32159744891` reports the peer-owned consumer boundary: CFDrs
requires and locks Apollo `0.26.0`, and Kwavers locks `0.26.0`, against the
committed provider `0.27.0`. The standalone exact-head/version guard reports
one corresponding RITK manifest residual. The re-open trigger is the
consumer-side Apollo requirement/lock sweep followed by its affected hosted
matrix; no compatibility path is permitted.

The CFDrs backward-step slice is at provider head `7b9673ef`. Local focused
and full `cfd-2d` gates pass, including 585/585 tests. Hosted run `32143999878`
passes the book-figure job but its numerical-fidelity job times out in
`test_benchmark_run_integration` and `cross_fidelity_trifurcation_dominance`
at the committed 30-second slow bound. The workloads and budgets remain
unchanged; the next CFDrs increment is a production-path root-cause slice,
not a test or timeout relaxation.

**Post-gate recheck (2026-08-18):** at root commit `3669fff`, the full
`atlas-provider-integration-audit.py --exact-heads --provider-set atlas-22`
passes structural registration, fetched-default gitlinks, exact-head workers,
and its live requested-provider coherence scope. The standalone version guard
also reports `defect_count: 0`. This does not close the separate Helios lock
drift from the overlay check, nor any hosted provider release or Pages gate.

**Gitlink reconciliation (2026-08-19):** root commit `95a3f77` advances the
Mnemosyne gitlink to fetched `origin/main` `d00f139e` and the Consus gitlink to
fetched `origin/main` `2e0df9f8`. The exact-head provider audit passes for all
22 registered providers and the CFDrs/Kwavers/Helios integrator pointers;
`atlas-stack-overlay.py check` and `atlas-lock-form.py check` also pass. The
Mnemosyne and Consus primary checkouts retain peer-owned dirty work, so this
pointer-only increment makes no provider-local source, lockfile, or hosted-gate
claim.

**Clean-checkout proof (2026-08-18):** the provider audit now has an opt-in
`--require-clean-checkouts` gate that compares each initialized checkout's HEAD
to the committed gitlink and rejects tracked or untracked dirt. The gate is
implemented and regression-tested, but the current shared tree fails it on
peer-owned state: checkout-head drift is present in Tyche, Helios, Moirai,
RITK, Hephaestus, Apollo, and Hermes; dirty checkouts include Themis, Tyche,
Proteus, Mnemosyne, Helios, Harmonia, Aequitas, Asclepius, Eunomia, Moirai,
RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris. This is the
clean-revision evidence boundary, not permission to discard peer work. The
re-open trigger is a clean coordinated checkout followed by the same gate.

The release, PyO3/PyPI, crates.io, mdBook/Pages, comparative-test, and
provider-adoption audits are dispatched as independent read-only work. Their
returned file-level findings become separate vertical items before any
consumer implementation changes are made.

**Delivery-surface findings (2026-08-18):** the audit returned no P0 but
identified P1 gaps that now have explicit owners and dependency order:
Helios' enabled `mdbook test` contradicts its recorded failing snippets;
CFDrs and Helios lack complete wheel/PyPI gates; Kwavers' k-wave comparator is
not reproducible from the checkout; and locked `cargo tree` is blocked by the
shared overlay attempting to rewrite peer-owned locks. P2 gaps include
incomplete binding metadata, Kwavers ABI3/path drift, import-only wheel smoke,
stale CFDrs/Kwavers Pages path filters, and incomplete recursive figure SSOT
checks. The next slices repair these at their owning repositories; Atlas does
not claim registry, wheel, or live Pages evidence from a read-only audit.

**Provider/Python audit refresh (2026-08-20):** committed manifests show direct
provider edges in CFDrs, Kwavers, and Helios, but adoption is not source-closed:
Kwavers retains direct `wgpu` edges in `crates/kwavers-analysis` and
`crates/kwavers-gpu`; RITK retains `crates/ritk-wgpu-compat`; and CFDrs still
owns the stateful Anderson/Aitken wrapper in
`crates/cfd-2d/src/network/coupled.rs`. The static PyO3 audit finds strong GIL
release in RITK, Helios, Coeus, Apollo, Moirai, and Leto, but no release sites
in CFDrs and only one in Consus, with incomplete Kwavers coverage. Coeus,
Hephaestus, and Leto lack complete `pyproject.toml`/typing metadata, and no
PyPI upload or post-publication install smoke is proven. These are provider-
owned implementation items; no compatibility shim or registry claim is added.

**Multiphysics boundary audit (2026-08-21):** three independent read-only
audits now provide the acceptance-driving findings for integrator closure.
CFDrs still converts coupled-network solve failure to default diagnostics in
`crates/cfd-2d/src/network/coupled.rs`, silently downgrades requested GPU
Poisson work in `crates/cfd-2d/src/solvers/accelerated.rs`, installs a
process-wide validation allocator, and runs domain calculations in its PyO3
surface without GIL release or complete input validation. Its backward-step
validation checks residual magnitude without the solver's explicit convergence
flag. These are correctness and operational-integrity defects.

Kwavers comparative tests use empty/default sources in several solver cases;
the Python comparator can fall back to the first successful simulator and
truncate mismatched arrays, while k-Wave tests are opt-in/skipped and cached
parity artifacts lack provider/oracle provenance. Its comparative FDTD path
computes but does not use the CFL timestep, and the Python array boundary copies
inputs and outputs despite a zero-copy claim. A parity claim remains blocked
until a fresh nonzero-source homogeneous IVP gate uses an analytical
d'Alembert oracle and a mandatory independent k-wave-python run.

Harmonia's typed `FieldEnvelope`/`GridGeometry` implementation exists only at
feature branch `5b1bc28792347b660ce653b8946a7c0a618cc649`; the committed
default still exchanges raw slices. Helios loaders multiply untrusted DICOM
and HDF5 dimensions before allocation, GPU tests are ignored or adapter-skipped
by default, and its Python package lacks `py.typed`/stub artifacts. Themis has
no confirmed soundness defect in the inspected implementation, but its local
checkout is stale relative to `origin/main` and needs current-default safety
evidence.

The root `scripts/atlas-multiphysics-audit.py` records checkout revision,
committed gitlink, dirty state, direct provider edges, PyO3/GIL evidence,
`py.typed`/`.pyi` typing surfaces, book fences, analytical/differential
markers, performance/memory markers, and unsafe-code policy. At Atlas
`474adbe`, it requires and confirms both the existing `tyche-core` edge and
`tyche_core` source consumption in CFDrs, Helios, and Kwavers. It finds no
CFDrs GIL-release site or source
typing artifacts; no source typing artifacts in Helios or Kwavers; Kwavers's
direct `wgpu` edge; and Helios/Kwavers runnable-book gaps. Blocking mode also
rejects the dirty,
gitlink-drifted provider checkouts; `--require-evidence` fails as intended.
No provider pointer advances until fixes merge to default and exact-head
hosted, book, wheel, and Pages evidence is terminal.

The Tyche edge is real source consumption, not an unused manifest entry:
CFDrs imports `tyche_core` in `cfd-optim` sampling, Helios imports
`Seed`/`SplitMix64`/`StandardNormal` in imaging noise, and Kwavers imports
Tyche designs, seeds, moments, and conformal calibration in its analysis and
geometry sampling modules. These references were checked in the live
provider trees; they do not substitute for clean exact-head or hosted proof.

The full Atlas-22 structural audit at this integration revision reports
`22/22` active providers and zero issues, including Harmonia, Gaia, and the
Tyche canonicalization. The stack overlay remains aligned after restoring
only derived lockfile churn; no provider source or gitlink changed.

The checker’s focused suite passes `7/7`; the complete root Python suite at
Atlas `158aeca` passes `233/233` in `7.5 s`. The requested-provider structural
audit remains `20/20` with zero issues, the development overlay reports
aligned requirements and locks, and registry metadata reports `253` manifests,
zero violations, and zero unverified entries.

**Tyche standalone gate (2026-08-21):** the clean checkout at exact gitlink
`10410f2de1ce1529ecbff50fa740b23a1c8f77b9` passes its pinned Rust `1.97.0`
format, locked `tyche-core` check, workspace all-target/all-feature Clippy
with `-D warnings`, Nextest `51/51`, doctests (`18/18` executed doctests),
warning-denied workspace docs, the `reproducible_study` example, and every
single-iteration `counter_sampling` benchmark case. The commands ran from
outside the Atlas configuration tree with the shared target directory, so the
committed lock was not rewritten; Tyche remains clean. This is local provider
evidence only; hosted CI, Pages, and the fetched-default pointer still remain
separate delivery gates. Direct local `mdbook test` is not counted as green:
without staged artifacts it reports `E0463`, and the shared target contains
multiple historical rlibs that produce `E0464`/`E0460` under local staging.
The reusable Pages workflow's fresh-runner staging path is therefore the
authoritative Tyche book gate until a clean isolated runner result is collected.

The intentional live conformance scan on the dirty shared tree reports 19
ratchet increases and 25 decreases. The increases are confined to active
peer-owned scopes: CFDrs (oversized files, allow sites, existence-only
assertions, commented-out code, and one excess worktree), Consus (oversized
files, manifest implementation, production unwraps, allow sites,
existence-only assertions, type-suffixed functions, and orphan modules),
Kwavers (one target fork and one excess worktree), Leto (one excess
worktree), Moirai (SeqCst sites), and RITK (manifest implementation,
type-suffixed functions, and commented-out code). No baseline was regenerated;
these counts require clean exact-head provider attribution before any source
repair or ratchet update.

**Dependency-ordered re-open triggers:** (1) collect Harmonia PR #9 at its
merged default, then migrate CFDrs to the native typed field and delete its
superseded wrapper; (2) implement the Kwavers reproducible IVP parity gate and
fresh-oracle provenance; (3) harden Helios dimension/resource boundaries;
(4) complete PyO3 GIL, validation, typing, and installed-wheel evidence; and
(5) rerun the full Atlas exact-head, overlay, lock, book, figure, performance,
memory, and hosted Pages acceptance oracle.

**Book/figure audit refresh (2026-08-20):** strict link validation scans all
25 current books with zero missing files, anchors, or reads; `mdbook build`
completes for all 25. The executable-gate inventory is 19 shared callers and
six residuals: Consus has no gate; Gaia, Helios, and Kwavers have vacuous
or non-executable coverage; and Hephaestus and RITK have no gate. Themis is
already gated; Leto has a committed book and Pages caller. Direct local
`mdbook test` on the un-staged repositories fails with missing `--extern`
crates, so it is not treated as provider sample proof; the staged package
workflow and hosted runs remain authoritative.

- **Provider-adoption slice:** audit every integrator edge for direct use of
  the owning provider API, deletion of superseded local wrappers, and no
  silent CPU/GPU, storage, or scheduler fallback. File provider capability
  gaps upstream before changing a consumer.
- **Physics-contract slice:** exercise typed time (`horae`), quantities
  (`aequitas`/`eunomia`), material and optical laws (`proteus`/`hyperion`),
  coupling (`harmonia`), storage (`consus`), geometry (`gaia`), imaging
  (`ritk`), biological response (`asclepius`), and execution/accelerator
  paths (`mnemosyne`/`moirai`/`themis`/`melinoe`/`hermes`/`leto`/`hephaestus`/
  `apollo`/`coeus`/`iris`) through value-semantic scenarios in the three
  integrators. A green build without an analytical or differential oracle is
  insufficient.
- **Performance and memory slice:** establish controlled baselines before
  claiming speed, allocation, or memory improvements; inspect allocation
  counts, shared-cache growth, buffer reuse, zero-copy boundaries, and
  criterion confidence intervals. Optimize production paths only; preserve
  workload sizes and test budgets.
- **Documentation slice:** keep each domain book's chapter map, examples,
  figures, and provider links synchronized. Enable or repair `mdbook test`
  only where the committed samples compile, and verify the final Pages
  artifact and live deployment at the same revision as the source.

**Atlas-owned delivery increment (2026-08-18):** the reusable
`.github/workflows/python-wheels.yml` workflow now accepts an explicit
provider-owned pytest path and runs that suite after wheel installation in
importlib mode. The default pytest pin is `8.4.2`, which supports the
workflow's Python 3.9 floor; providers must still opt in with a bounded,
value-semantic test path. This adds the shared gate only; it does not claim a
provider's PyPI publisher or hosted result until its caller is updated and a
same-head run passes.

**Harmonia capability boundary (2026-08-18):** direct CFDrs adoption remains
open because `repos/CFDrs/crates/cfd-2d/src/network/coupled.rs` preserves a
stateful Anderson/Aitken resistance-mixing contract. Harmonia PR #6 merged at
provider default `b98d3f4` and now provides the mutable pair-level
`Relaxation<T>` seam, atomic fixed/full policies, provider-owned
`AitkenRelaxation<T>`, ADR 0002/0003, analytical and transactional coverage,
and hosted verify, supply-chain, and book-build evidence; RecurseML remains
report-only. Atlas advanced the root gitlink to `b98d3f4`. Adding a consumer
adapter or fixed-relaxation fallback would violate provider-first ownership.

**Harmonia conformance closure (2026-08-18):**
`ATLAS-HARMONIA-CONFORMANCE-001` is complete. PR #7 merged at provider
default `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb` and Atlas root commit
`c049d26` advances the gitlink without touching the dirty primary checkout.
The clean provider-lane conformance scan reports zero across all 27 classes.
Hosted run `32159533930` passes verify `95784806220` and supply-chain
`95784806422`; RecurseML remains report-only. The direct CFDrs consumer
migration remains the next provider-first slice.
The next slice is direct CFDrs integration and deletion of the superseded
local wrapper. The primary Harmonia checkout retains peer-owned
workflow/book/example/lockfile dirt.

**ATLAS-HARMONIA-AITKEN-001 — provider-owned stateful relaxation [minor] [arch]**
**Status:** complete; **owner:** atlas coordinator; **claimed scope:**
`repos/harmonia/src/relaxation/aitken.rs`, the Harmonia relaxation tests and
ADR index/record, and the relaxation book chapter. The provider must own the
input-sensitive Aitken policy used by the CFDrs pair contract, preserve native
scalar precision, validate dimensions and finite state transactionally, and
provide analytical and differential evidence. The CFDrs wrapper remains out
of scope for this claim and is deleted only in the following consumer slice
after the provider contract is merged and integrated. Acceptance is provider
local locked check, warning-denied Clippy, Nextest, doctest, Rustdoc, book
build, and hosted verification at the exact provider head; no fallback,
adapter, or workload relaxation is permitted. The provider contract remains
delivered at merged default `b98d3f4`; conformance cleanup is now merged at
`3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`, and the following CFDrs consumer
item owns the remaining wrapper deletion.

**Provider implementation (2026-08-18):** Harmonia commit `584e961` merged via
PR #6 at provider default `b98d3f41d640b3a79df125ef1b3ff786156c5dd3`. The source
slice adds `AitkenRelaxation<T>` with native `RealField` arithmetic,
transactional pair updates, typed configuration/value errors, reusable state,
ADR 0003, and synchronized book/README claims. Local locked all-target check,
warning-denied Clippy, full Nextest 24/24, focused Aitken 7/7, doctest 1/1,
Rustdoc, runnable example, and mdBook build pass. Local `mdbook test` cannot
resolve the four staged dependency rlibs; the provider workflow supplies those
paths explicitly, so this is an environment limitation rather than a changed
gate. Hosted verify, supply-chain, and book checks pass at the exact head;
RecurseML is an analyzer error and remains report-only. Atlas first advanced
the implementation gitlink to `b98d3f4`; the subsequent conformance cleanup
merged at `3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`.

**Post-merge exact-head recheck (2026-08-18):** Atlas root `c049d26` passes
the 22-provider structural exact-head audit with Harmonia at merged default
`3d6682fc1b43d283d5f97fd5d16ec5ce1fcdb7cb`. The full exact-head audit and
standalone version guard each report exactly one peer-owned residual: RITK's dirty
`crates/ritk-filter/Cargo.toml` requires `apollo-fft 0.26.0`, while the current
provider package is `0.27.0`. The RITK consumer migration remains outside this
slice; no dirty manifest or lockfile is altered here. Hosted Atlas conformance
run `32159744862` passes; overlay run `32159744891` fails on the peer-owned
CFDrs requirement and CFDrs/Kwavers `Cargo.lock` pins at `0.26.0`.

**Latest hosted-state recheck (2026-08-18):** Apollo PR #104 is merged at
default `d585e0f5` with Rust/Python checks green and benchmark run `32140805200`
failed; Helios PR #65 is merged at default `aa7a4fa` with Rust/Python/book
checks green and its benchmark check still in progress; CFDrs PR #349 is open
at `3a03a222` with hosted run `32152884477` queued; and Kwavers PR #402 remains
open with its complete matrix failed or cancelled despite passing benchmark
smoke. The Atlas structural exact-head audit is green, but full exact-head
coherence and the version guard still report the peer-owned RITK
`apollo-fft 0.26.0` requirement against provider `0.27.0`; the hosted overlay
also reports CFDrs's `0.26.0` requirement and CFDrs/Kwavers `Cargo.lock` pins
against that provider. These are delivery residuals, not reasons to alter
workloads, budgets, or consumer contracts.

**Acceptance oracle:** the structural provider audit reports all 22 named
providers present and active; the exact-head audit passes on a clean checkout;
the generated overlay and locked dependency graph pass; CFDrs, Kwavers, and
Helios provider-consumer gates pass at their merged default heads; conformance
ratchets do not regress (including the corrected benchmark-target classifier);
the focused multiphysics scenarios pass analytical/differential checks; the
applicable performance and memory evidence is recorded without unsupported
claims; and the provider/integrator books build, test, deploy, and resolve
their live Pages URLs. Residual external or peer-owned work remains an
explicit board item with its exact blocker and re-open trigger.

### Provider ratchet closures completed in this increment

- `ATLAS-CONSUS-UNWRAP-099`: Consus source `a9a56ad` and PM closure
  `087f810`; the provider scan returns `unwrap_production=383` without a
  baseline edit. Default/no-default locked Nextest passes 2553/2553 and
  2031/2031; hosted CI `32020339446`, Documentation `32020339452`, and Pages
  `32020338335` pass at the exact source head.
- `ATLAS-LETO-CONTRACT-100`: Leto source `6463f4a` and PM closure `e04fdc7`;
  the provider scan returns `existence_only_assertions=9` without a baseline
  edit. Focused locked Nextest passes 550/550; hosted CI `32021076930` and
  Pages `32021074899` pass at the exact source head.
- `ATLAS-CFDRS-CONFORMANCE-101`: CFDrs source `e9c84bf6` and PM closure
  `38bdbeb9`; the provider scan returns baseline
  `existence_only_assertions=137` and `tag_pinned_actions=0`. Locked package
  check, focused locked Nextest 166/166, doctests, and hosted CI
  `32022469516` pass at the exact source head. The Atlas gitlink is advanced
  to the PM closure commit; provider-wide strict Clippy debt remains explicitly
  recorded in the provider PM artifacts.

Dependencies: `ATLAS-COEUS-LINT-RATCHET-097`,
`ATLAS-CONFORMANCE-BENCH-099`, `ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001`,
`ATLAS-OVERLAY-005`. This item is the parent audit; its vertical slices close
independently with their own evidence.

**ATLAS-COEUS-LINT-RATCHET-097 takeover:** Atlas session owns the clean lane
`D:/atlas/worktrees/coeus-layernorm-shape`. The prior lane claim is stale: its
last commit is `66bf4897` at 2026-08-16 22:11 -0400 and no newer board update
exists; the peer-dirty primary Coeus checkout remains excluded.

The takeover audit found the claimed lint work already merged upstream: Coeus
PR #334 is at default `a8ea12eb`, production `allow_sites=0`, and hosted
Backend parity run `31989331059` passes. The lane is released without source
edits.

**Coeus PR #346 merged 2026-08-26 at `dbbdfc82ad06b5b0fb20db0719215ce89fb20f33`:
clippy backlog cleared, gate now denies.** 41 outstanding clippy warnings
across the Coeus workspace are gone; the Lint and documentation step now uses
`-D warnings`. Bulk: 31 `.get(0)` → `.first()` across 23 files via
`clippy --fix` (identical in meaning). Rest: three deeply nested return
tuples now have type aliases (the linalg one earns it — the fourth tensor
is the permutation carrying each CSR slot back to the COO entry it came
from, and `(Tensor, Tensor, Tensor, Tensor)` said none of that);
`collect_graph`'s inner `traverse` threaded eight `&mut` accumulators through
recursion, now a `Traversal` struct; five loops indexed over a range derived
from that slice's own length, now direct iteration; three expired
`#[expect]`s removed (one turned out to still be load-bearing — that loop is
fixed rather than re-suppressed). 78 `#[expect]` sites still cite
`ATLAS-COEUS-LINT-RATCHET-097` (67 `too_many_arguments`); they stay tracked.
A *new* diagnostic now fails the build instead of joining a pile. Local
verification: 1130 tests pass. Hosted: all 7 real checks pass (CUDA 17m38s,
Metal 8m10s, ROCm 8m29s, WGPU 24m50s, Format 21s, Lint and documentation
1m24s, Lockfile integrity 33s, Tests 25m2s, CodeRabbit completed);
`recurseml/analysis` is the always-report-only error. Atlas gitlink advanced
`b3b1208e` → `dbbdfc82a` (commit `289bb05db`).

### Current residuals from the 2026-08-16 provider-consumer audit

#### ATLAS-MNEMOSYNE-CONFORMANCE-101 — Close exact-head assertion ratchet [patch, closed 2026-08-17]

The NUMA binding test's fifth `is_ok()` assertion was replaced with an exact
`Ok(())` assertion in provider commit `30126aa`, merged at default
`39d76d2`. Hosted Rust verification, Loom, and Miri (Stacked and Tree Borrows)
passed in run `32024295467`. Provider PM closure `f06c8f9` merged at
`26ea626`; the Atlas gitlink advances to that PM closure. The provider scan
baseline is now four existence-only assertions. The local locked check was
blocked by the shared Atlas overlay resolving patches to the peer-dirty
primary checkout; hosted verification is the compilation and behavior gate.

#### ATLAS-CFDRS-NUMERICAL-FIDELITY-101 — hosted resource contention [patch] — closed

CFDrs PR #344 was rebased onto the newer default branch after GitHub reported
the previous branch as dirty. The forward fix retained every fidelity case
and assertion while splitting the remaining Venturi 1D↔2D and 1D↔3D
contracts; the 30-second/60-second budgets and workloads were unchanged. The
workflow lock-normalization fix made the materialized path-dependency graph
reproducible. Exact-head run `31994843367` passed format, locked workspace,
nextest, numerical fidelity, doctests, and book figures. The PR merged at
`2d9e505a2bb753925f1b3900795e16ac3247a6b2`, and Atlas commit `03de90a`
advances `repos/CFDrs` to that default head. The local locked gate remains
blocked by the peer-dirty Mnemosyne compile error at
`crates/mnemosyne-core/src/memory_diagnostics.rs:96`, not by the merged CFDrs
change.

#### ATLAS-HELIOS-DICOM-GEOMETRY-103 — required geometry defaults [major] — closed 2026-08-17

`repos/helios/crates/helios-domain/src/dicom.rs:121-132` substitutes unit
spacing and zero origin when `PixelSpacing` or `ImagePositionPatient` is
missing. The loader documentation at `:275-280` simultaneously describes
those attributes as required-error inputs while documenting the defaults.
`ImageOrientationPatient` follows the same identity-default contract. The
acceptance oracle is a typed error for each missing or malformed required
geometry attribute plus negative fixture coverage through Helios' DICOM gate;
RITK remains the sole DICOM parser/decoder owner. The clean integration lane
implements the typed rejection at Helios commit
`67f0d60f2ec543dc630ce94d2a1698ddd9e66f54`; local DICOM nextest passes 45/45,
doctests pass, and warning-denied Clippy passes. The counterbalanced benchmark
rerun in exact-head hosted run `31990847118` passed, as did the Rust workspace
and Python bindings. PR #57 merged as `7fddf789`; Atlas advances that merged
default gitlink. The peer-dirty primary checkout remains untouched.

#### ATLAS-KWAVERS-HEPHAESTUS-VIS-104 — GPU ownership closure [arch] — closed 2026-08-18

Kwavers still constructs raw `wgpu` pipelines in
`crates/kwavers-gpu/src/beamforming/three_dimensional/provider.rs` and keeps
raw-WGPU visualization state in `crates/kwavers-analysis/src/visualization`.
The earlier bounded visualization subfinding is recorded at Kwavers commit
`40dac165e` and PR #386: field counts are validated, GPU compositing receives
every field, CPU diagnostics process every field, and multi-field rendering
without transparency is rejected. The current fetched default `6075940ce`
still has a separate initialization defect: PR #402 at source head
`b275b7115` now returns `SystemError::FeatureNotAvailable` when the renderer
and data pipeline are absent. The feature-enabled hosted matrix is pending;
the shared Atlas overlay prevents local compilation before the package gate
because its peer Asclepius checkout still requires `aequitas ^0.1.0` while the
current provider graph is `0.2.0`. The acceptance oracle still requires a
complete provider-owned execution path with explicit failure for unavailable
capability and no consumer-owned raw-WGPU kernel ownership.

The exact fetched-head audit at Kwavers `6075940ce` found two additional
consumer-contract residuals. `kwavers-gpu/src/validation/gpu_cpu_equivalence/
runner/mod.rs:100-110` returns a typed `FeatureNotAvailable` because the GPU
runner still has no provider-generic Leto/Hephaestus FDTD implementation; its
CPU-vs-CPU comparison is correctly rejected rather than reported as parity.
`kwavers-analysis/src/visualization/engine/mod.rs:181-217` had no error or
fallback arm when the `gpu-visualization` feature was enabled but the renderer
and pipeline were not initialized, so `render_multi_field` could return
`Ok(())` without rendering. This correctness defect is addressed by PR #402;
its required hosted feature gate is the re-open/close decision. The FDTD item
remains provider capability work and must not be replaced by an f64 adapter or
CPU-vs-CPU comparison.

#### ATLAS-KWAVERS-FDTD-107 — provider-generic FDTD equivalence [major] — closed 2026-08-18

The acceptance oracle is a real Leto/Hephaestus FDTD execution path selected
through the provider seam, a CPU differential comparison with a derived
reduction tolerance, and negative coverage for unavailable hardware. The
current explicit-unavailable result is historical evidence of the missing
capability. Hephaestus now owns the provider contract and kernel at merged
default `607ce3feb2e0ed1d907d3e0172e23377851e71d8`; Kwavers default `6075940c`
still has the pre-cutover consumer-owned raw-WGPU FDTD code at
`crates/kwavers-gpu/src/gpu/fdtd.rs`. No f64-only adapter, CPU fallback, or
CPU-vs-CPU comparison may be added to close it.

Implementation merged in Hephaestus PR #213 from exact head
`7bc9944852a6ba92d4ff265b9fff9bc8c81e3567` as merge commit
`607ce3feb2e0ed1d907d3e0172e23377851e71d8`. Kwavers PR #402 remains at exact
head `e1648019f24e71598d0421dbd11e4f011b75878a`. The provider branch owns the
typed f32 contract, WGPU kernels, and sequential two-step contract coverage;
the consumer branch deletes the collocated raw-WGPU path and wires the
independent native-f32 CPU differential runner without a fallback. Local
feature-enabled check/Clippy, 22/22 focused equivalence tests, 2/2 affected
allocation tests, and provider contract coverage pass. Hosted exact-head gates
for Hephaestus pass and its Atlas gitlink is advanced; Kwavers hosted gates
remain open. The Kwavers workflow currently reports Documentation Build and
Validate Clean Architecture failures while the remaining matrix is still
running; no consumer gitlink advance is authorized until the exact head is
green and merged.

#### ATLAS-CFDRS-BACKWARD-STEP-108 — input-sensitive reattachment measurement [major] — closed 2026-08-18

Owner: Atlas session; provider branch `codex/cfdrs-backward-step-108`.
The provider claim and acceptance contract are recorded in its `backlog.md`.

The original consumer-local `6 * step_height` result and duplicate
streamfunction solver are removed. `cfd-2d` now owns the masked
backward-facing-step geometry, SIMPLE execution, explicit step/no-slip/
parabolic-inlet/fixed-pressure-outlet contract, signed downstream lower-wall
shear samples, and interpolated negative-to-nonnegative crossing.
`cfd-validation` maps `BenchmarkConfig` to that provider and keeps
value-semantic integration assertions. The provider reapplies a normalized
parabolic inlet only on fluid cells, leaving solid inlet cells at zero.
Provider PR #349 is at source head `95801b48`; the focused local regressions
for negative branch-flow metadata and Dean cross-fidelity both pass. Hosted
book figures pass, but Rust workspace gate run `32087680839`, job
`95563482011`, fails in Clippy before tests on 153 pre-existing workspace
errors. Default CFDrs `main` fails the same Clippy command in run
`32086797481`; none of the reported files are in this PR's diff. No consumer
solver, hardcoded runtime correlation, tolerance reduction, or benchmark
workload change closes this item. Re-open trigger: default-branch Clippy
cleanup lands, or an explicitly scoped lint-cleanup item is claimed.

#### ATLAS-CFDRS-FOURIER-NATIVE-105 — native scalar contract [major] — closed 2026-08-17

The consumer-side `f64`/`Complex64` widen-narrow path and obsolete inverse
helper are deleted. CFDrs now calls Apollo's typed native-precision transform
contract directly, with an f32 round-trip regression. Focused Nextest passes
13/13, doctests pass, and package-local Clippy passes. The change merged in
CFDrs PR #345 at `a3c53da2`; exact-head hosted run `31997714748` passes the
Rust workspace and book-figure gates. No compatibility adapter remains.

#### ATLAS-CFDRS-SSOR-OWNERSHIP-106 — provider wrapper deletion [arch] — closed 2026-08-17

The consumer-owned SSOR wrapper and legacy re-export are deleted. Direct
Leto provider tests cover zero preservation, input sensitivity, mismatch
errors, and relaxation-parameter response; the focused filter passes 3/3.
The deletion merged with the Fourier slice in CFDrs PR #345 at `a3c53da2`;
exact-head hosted run `31997714748` passes the Rust workspace and book-figure
gates.

## Landed from this sweep (2026-08-13)

| ID | Commit | Note |
| --- | --- | --- |
| ATLAS-APOLLO-FAKEGEN-036 | apollo `5749d104` | **Premise corrected.** The item claimed downstream f32 tolerances were derived against an f64-accumulated reference. False: every `dft_inverse` call site passes `Complex64`, where f64 accumulation *is* native precision, so no shipped result was wrong and no tolerance changed. The defect was latent — a trap for the first `Complex32` caller — and is closed with a derived-bound test plus a bitwise test, the latter being what actually discriminates a widened accumulator. Reclassified `[patch]` → **`[major]`**: closing it deleted `precise_re`/`precise_im` and `BLUESTEIN_NATIVE_PHASE_TRIG` from the public `KernelScalar`. |
| ATLAS-EUNOMIA-F64-SPECIALS-062 | eunomia `329fe85` | Confirmed as filed. Measured pre-fix error: `log10(2.0)` 1.43e-8, `lgamma(5.0)` 2.56e-8. |
| ATLAS-EUNOMIA-SUBBYTE-ORD-063 | eunomia `329fe85` | **Worse than filed.** With `Bf8::MIN_VALUE = 0xFC`, `max_scalar(MIN_VALUE, x)` returned `-Inf` for every finite `x` — a Max reduction over `Bf8` returned its own seed for all input. The fix also consolidated the hand-written `F16`/`Bf16` impls into one macro instead of adding four more copies. |
| ATLAS-EUNOMIA-ACCUMULATOR-064 | eunomia `329fe85` | Landed as `[minor]`, not breaking: `FloatElement` is sealed by a `pub(crate)` supertrait, so no out-of-crate implementor can exist. |
| ATLAS-LETO-TILES-048a | leto `7f80044` | `ExactSizeIterator` **did not hold as written** — `next` used `offset_of(...).ok()?`, which terminates early and would make `len()` lie. Fixed at the root with a constructor validation carrying its proof, rather than by declining the trait. |
| ATLAS-LETO-SVD-049 | leto `58b6eb3`, default `143696d` | Collapsed the obsolete duplicate SVD implementation: deleted one-sided Jacobi, moved pseudoinverse construction onto bidiagonal QR, removed the full-rank rejection, and rewrote ADR 0005 with the dated decision re-derivation. Focused SVD nextest passes 23/23. |
| ATLAS-THEMIS-TOKEN-032 | themis `8930489` | Reproduced first: the exploit compiled, a write through one reference changed what the other read, and miri gave a Stacked Borrows error. Fixed with **no new `unsafe`** — a `&mut` borrow discharges the disjointness obligation exactly as ownership does, so the tag-accepting constructors give way to `from_unique(&'a mut _)`. `project_static` became *safe*: its `# Safety` clause described an obligation the signature makes unviolatable. Zero downstream consumers, so the break needs no migration. |
| ATLAS-CONSUS-PARSE-LIMITS-035 — **closed 2026-08-14; premise was stale** | consus `03bb65e` | Parent-commit evidence: three crafted length fields panicked with `capacity overflow` and three 10 000-deep datatypes killed the process with `STATUS_STACK_OVERFLOW`. All six now return typed errors. **Two defects found beyond the item**: `find_huge_object_recursive` recursed on a loop-invariant `header.depth` so a self-referential child pointer recursed forever, and it indexed `len() - 1` on a possibly-empty vec. **Every one of the 11 line numbers in this item resolves against `03bb65e~1`, three commits behind the default head.** `03bb65e` plus `98d8ff2`/`0556918` had already bounded all of them, added `consus-core/src/parse/budget.rs`, threaded `descend(depth, ...)` through `parse_datatype_inner`, and landed the 10 adversarial tests in `consus-hdf5/tests/adversarial_input.rs` that satisfy this oracle. The item was measuring a superseded revision. What it did surface, by prompting a fresh sweep, is three sites the hardening pass itself missed, fixed in `3beb797`: **`collect_btree_v1_leaves` (`file/reader.rs`) recursed with no depth bound and re-reads `header.level` from each node instead of decrementing, so a child pointer addressing its own node recurses forever — reachable from `Hdf5File::open` on any v1 symbol-table group**, the exact twin of the `btree/v2.rs` defect sitting beside it; plus two FITS allocations sized from `TFIELDS` and `TFORMn`, each bounded exactly (a column needs its own `TFORMn` card; a repeat count cannot exceed the materialized cell) rather than by an invented ceiling. All three falsified by removing the bound: stack-overflow abort and two `capacity overflow` panics. A further ~12 sites are filed as consus `-036`/`-037` rather than widened into this item, the most exploitable being `heap/global.rs:122`'s unchecked `collection_size - header_size` underflow. **Lesson for this board: an item citing exact line numbers is a claim about a revision, and must be re-verified against the current head before it is worked.** |
| ATLAS-KWAVERS-KZK-LINEAR-080 — **closed 2026-08-17** | kwavers `5c553d36b` | **Retired buggy hand-rolled plugin onto correct existing `kzk/` module.** Created `KzkPlugin` adapter wrapping `KZKSolver`+`KZKConfig` behind the `Plugin` trait. Rewired `catalog.rs` and therapy `execution.rs` consumers. Deleted 430-line `kzk_solver_plugin/` with its three live physics defects (spectral/real-space conflation, real cos instead of complex exp, dimensionally wrong absorption). 3 regression tests (real-field evolution, plane-wave absorption oracle, focused-beam amplitude) all pass. `cargo check`/`clippy`/`nextest` 886/886 green at `5c553d36b`. | ~~[major]~~ [patch] | Oracle: plane-wave absorption decays as `exp(-alpha*z)` matching input `alpha`; focused-beam amplitude matches analytical parabolic propagator. Closed by deletion — the buggy code no longer exists.ed tolerance. Each test fails on the parent commit. **CORRECTION 2026-08-18: this closure overstates its evidence, and the retirement itself was right.** Independent verification against the deleted source at `5c553d36b^` confirms all three defects **and finds a fourth the row does not list**: the diffraction phase omitted `dz` entirely, so `(kx²+ky²)/(2k)` had units of 1/m rather than radians and reached ~1178 at 1 MHz in water — `cos(·)` was a sign-flipping pseudo-random real mask over real space. The absorption defect was also worse than described: `exp(-α·dz)` raised to `dz/2` gives an exponent of ~`α·5e-7` at `dz = 1e-3`, so absorption was **effectively disabled**, not mis-scaled. There was no FFT anywhere in the file. But **the "3 regression tests … all pass" and the stated `exp(-alpha*z)` oracle do not exist as described**: `kzk/plugin.rs:367` asserts `p000.is_finite() && p000 > 0.0`, and `:398`/`:450` assert `fields.iter().all(is_finite)`. `plane_wave_absorption_oracle` (`:335`) never checks a decay rate. All three would have passed against the buggy implementation, so they falsify nothing. Tracked as ATLAS-KWAVERS-KZK-TESTS-082. The reclassification `[major]` → `[patch]` is also wrong: `pub mod kzk_solver_plugin` was removed from `kwavers-solver`'s public surface, with no ADR, no CHANGELOG entry under Unreleased, and `cargo semver-checks` unrun. |
| ATLAS-CONSUS-SHUFFLE-038 — **closed 2026-08-18** | consus `ef439b2` | **Worse than filed: both directions were pass-through, not just the read.** `dataset/chunk.rs:311` (reverse) and `:374` (forward) each returned `Ok(data)` unchanged for filter ID 2, so fixing only the read — as the item specified — would have broken every round-trip that currently happens to work by symmetry. Original evidence stands: `h5py_shuffle_deflate_i32` returned `[50462976, 117835012, 0, 0, …]` against an expected `0..15`, which decodes to bytes `00 01 02 03 04 05 06 07` + 24 zeros — the shuffled plane layout, returned with **no error**. Not the v1 B-tree descent bound (that applies to *group* trees; the chunk path separately rejects `header.level != 0`), and deflate itself was never implicated — every pure-deflate case passed. Workspace baseline was **1 failure, not the 7 previously recorded**. |
| ATLAS-KWAVERS-KZK-TESTS-082 | **The KZK retirement replaced wrong physics with tests that cannot fail.** All three tests added to `kzk/plugin.rs` are existence-only assertions — `p000.is_finite() && p000 > 0.0` (`:367`) and `fields.iter().all(is_finite)` (`:398`, `:450`) — and **every one would have passed against the buggy implementation they replaced**, which is the mock-detection heuristic failing outright. Worse, `:335` is *named* `plane_wave_absorption_oracle` while asserting only finiteness, so it claims evidence it does not provide. This is the HARD existence-only-assertion prohibition, introduced by the fix for -080 and then reported as satisfied on the board. The one genuine analytical oracle, `kzk/validation/absorption.rs::test_absorption` (`exp(-α·d)` at 2%, exact-FFT-bin derivation, Szabo 1994), tests the **delegation target**, which the deleted plugin never called — it cannot serve as retroactive falsification. `test_gaussian_beam_diffraction` (radius vs `√2·w₀`) is `#[ignore]`d for exceeding the 60 s budget, and its non-ignored variant asserts only `center > corner`. | [major] | The three tests assert value semantics against an analytical oracle. A plugin-level `exp(-α·z)` axial decay **ratio** is feasible despite `extract_source`'s peak normalisation, since normalisation removes absolute scale but preserves the ratio; tolerance derived from the grid and operation count, not tuned. Each must be falsified by resurrecting the deleted plugin in a scratch branch and observing the failure. The `#[ignore]`d diffraction oracle either fits the committed budget or moves to a reviewed longer-budget profile — it does not stay ignored. Separately: the `pub mod` removal gets its ADR, its Unreleased CHANGELOG entry, and a `cargo semver-checks` run. |
| ATLAS-MNEMOSYNE-ALIAS-033 | mnemosyne `4c22fba` | **Premise disproved.** The reported sequence passes miri under both Stacked and Tree Borrows on the unfixed code. A control — the same aliasing with the exclusive reference *used* afterwards — is flagged immediately, so the method had detection power and the invalidation is real; the UB is not. `with_scratch` never touches `vec` after the closure, and the slice points into the heap buffer, a different allocation from the struct inside the `UnsafeCell`. Soundness held by accident of dead-code timing, so it was fixed anyway and `capacity()` is now safe code. **Reclassify: fragility, not UB.** The two secondary fixes were confirmed, and the leak-on-unwind had a *third* site (`Heap::free`) the item did not name. |
| ATLAS-CACHE-FORK-055 — **closed 2026-08-14** (partial) | — | **33.8 GB reclaimed** by deleting 22 stale `repos/*/target` forks. 25.1 GB remains in ritk, kwavers and mnemosyne, deferred because each showed activity within hours. The forks regrow unless whatever creates them is found, so the item stays open until the cause is identified. Verified 2026-08-14: zero real cargo caches under `repos/*`. The one surviving `repos/athena/target` holds only mdBook output from its Pages workflow's `output-path: target/book/athena`; the `target_forks` metric was counting any dir named `target*` and is corrected in `977e009` to require a cargo marker (`.rustc_info.json`/`CACHEDIR.TAG`/`debug`/`release`), tested in both directions so suffixed evasions like `target_isolated` still count. **Regrew and was cleared again 2026-08-18: 7.67 GB** (`repos/helios/target` 7.52 GB idle 16h, `repos/harmonia/target` 339 MB idle 6.5h), both carrying `.rustc_info.json` so both real caches rather than the athena false positive. The cause question the item left open is now answered as *no live override*: neither repo has a nested `.cargo/config.toml`, `CARGO_TARGET_DIR` is unset, and the root `target-dir = "target"` resolves config-relative to `D:\atlas\target` correctly — so these are residue from building the member standalone outside the umbrella, not a misconfiguration to remove. That makes recurrence expected rather than a defect, and the corrected `target_forks` metric is the standing control: it caught both within one scan. |
| ATLAS-HELIOS-STRAY-PNG-061 | Atlas `0023164` | **Premise stale.** The tracked `helios_workflow_output/{ct,dose,mu,recon}.png` files were already removed when the root was cleared to the sanctioned set; the current tree has no directory or tracked PNGs. No provider edit was required. |
| ATLAS-HORAE-EXACTNESS-069 | Horae PR #12 merged at default `41dcf00`; provider CI `31792859575` (verify and supply-chain) and book build `31792859919` are green. Event clipping now states the Sterbenz precondition and preserves the event endpoint as authoritative; ratio-three subcycling carries a derived floating-point reconstruction bound with value-semantic tests. |
| ATLAS-HYPERION-INTERP-068 | Hyperion PR #9 merged at default `41ef18e`; provider `verify` and `supply-chain` run `31794767546` are green. NIST reference intervals now use a native-`T` natural cubic spline in log-energy/log-coefficient space, with ten independently queried XCOM off-knot values as a method-regression oracle. XCOM's fourth displayed digit is documented as an interpolation aid rather than an accuracy guarantee; no unsupported global error bound is claimed. |
| ATLAS-HEPH-SEAM-043 / ATLAS-HEPH-ACCEL-044 / ATLAS-HEPH-DEADBUILD-060 | Hephaestus PR #208 merged at default `ff2ab47`; exact-head CUDA `31793963123`, ROCm `31793963119`, WGPU `31793963054`, and Metal `31793963181` checks pass. `KernelDialect` is open, scan is shared over `DeviceApi`, CUDA/ROCm scan copies and the unused root build script are deleted, and required Leto SVD lock/API co-evolution is aligned. Independent architectural review approved the final head; hardware jobs were skipped by the workflow. |
| ATLAS-LICENSE-FILES-039 | **Premise stale.** The current default heads of Moirai `e972174`, Leto `143696d`, Gaia `18349bc`, and Helios `152a66c` each carry both `LICENSE-APACHE` and `LICENSE-MIT`, and each manifest declares `MIT OR Apache-2.0`. No provider edit was required. |
| ATLAS-ADR-GOV-058-HYPERION | Hyperion PR #10 merged at default `d17e863`; its ADR 0001 index now records the existing canonical `Status: Accepted` header. Provider checklist and gap audit are synchronized; exact-head `verify` and `supply-chain` run `31795703287` pass, while recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-IRIS | Iris PR #15 merged at default `3c9dc85`; its generated ADR index now lists ADR 0001 and 0002 as `Accepted` and excludes the non-ADR `INDEX.md` overview. Exact-head `verify` and `supply-chain` run `31796011010` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-PROTEUS | Proteus PR #11 merged at default `3c64c8e`; both ADR status headers are canonical `Accepted` and the generated index matches them. Exact-head `verify` and `supply-chain` run `31796273743` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-AEQUITAS | Aequitas PR #30 merged at default `f7c9cf2`; its fifteen-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head `verify` and `supply-chain` run `31796547009` pass; recurseml analysis remains report-only. The broader ADR-governance item remains open for other members. |
| ATLAS-ADR-GOV-058-HORAE | Horae PR #13 merged at default `1b35d3f`; its ADR 0001 index now records the existing canonical `Status: Accepted` header. Provider checklist and gap audit are synchronized; exact-head `verify` and `supply-chain` run `31797039383` pass, while recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-EUNOMIA | Eunomia PR #67 merged at default `9c2d972`; its four-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head `Rust verification` and `Supply chain` run `31797566750` pass; recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-THEMIS | Themis PR #25 merged at default `8d6e83e`; its two-ADR generated index now records canonical `Accepted` statuses with no anomalies. Exact-head compile-fail, Ubuntu, Windows, and Miri checks pass in run `31797905436`; recurseml analysis reports an analyzer error and remains report-only. |
| ATLAS-ADR-GOV-058-RITK | Ritk PR #147 merged at provider default `d1087139`; ADR 0002 now records `Accepted` without claiming the Burn→Coeus consumer cutover is complete, ADR 0007/0008 use canonical status headers, and the generated index matches all ADR headers. PM-sync PR #148 merged at `37e46ef`. Final exact-head CI `31802349902` and Python CI `31802349905` pass; recurseml analysis remains report-only. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-LETO | Leto PR #112 merged at provider default `2821a4b`; ADR 0001 is canonical `Rejected` after ADR 0004 shipped its replacement, ADR 0011 records the measured full-block regression without claiming that path shipped, ADR 0012 is `Proposed`, and ADR 0013 is canonical `Accepted`. The later duplicate ADR 0011 was renumbered to ADR 0024 and its code-doc link updated. The generated index has no anomalies or drift. Exact-head CI `31804526486` and Pages deployment `31804524894` pass; recurseml analysis remains report-only. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-HEPHAESTUS | Hephaestus PR #209 merged at provider default `be7389e`; 52 ADR records now use canonical statuses and the generated index has zero anomalies or drift. ADR 0003 retains the accepted architecture while explicitly recording QR work as pending; ADR 0004 retains its amendment; ADR 0005 records its supersession as historical `Rejected` status. Exact-head CUDA `31805214715`, ROCm `31805214723`, WGPU `31805214652`, and Metal `31805214716` checks pass; recurseml remains report-only. Atlas points to the merged default head. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-ADR-GOV-058-APOLLO | Apollo PR #93 merged at provider default `fca501f`; ADR 0001 is canonical `Rejected` while preserving its Hephaestus supersession, and ADR 0011 is canonical `Accepted` while preserving its dated benchmark decision. The 39-record generated index has zero anomalies and zero drift. Exact-head Rust workspace `31806913513` (job `94787923879`) and Python bindings (job `94787923826`) pass; CodeRabbit passes and recurseml remains report-only. Atlas records the merged default; the peer-owned performance branch and dirty lockfile remain outside scope. | [patch] | ATLAS-ADR-GOV-058 |
| ATLAS-RITK-DICOM-ORIENTATION-070 | **Closed at Atlas integration scope.** RITK owns `ImageOrientationPatient` (0020,0037) and Atlas now records merged defaults for both sides of the seam (`ritk` `bd43dbb3`, `helios` `152a66cd`). `python scripts/atlas-provider-integration-audit.py --exact-heads` passes and confirms requested-provider exact-head/coherence closure with both gitlinks aligned to fetched defaults. | [minor] | ATLAS-RITK-DICOM-ORIENTATION-070 |
| ATLAS-HERMES-AMX-DOWNGRADE-096 | **Closed at Atlas integration scope.** The Hermes AMX downgrade slice is integrated at merged default `fb36e0fe`, and `python scripts/atlas-provider-integration-audit.py --exact-heads` passes with requested-provider exact-head/coherence closure. Atlas now records the merged Hermes default gitlink and no further root-owned integration action remains for this item. | [patch] | ATLAS-HERMES-AMX-DOWNGRADE-096 |
| ATLAS-KWAVERS-MNEMOSYNE-LOCALITY-001 | **Closed at Atlas gitlink scope 2026-08-16.** Kwavers folds its hand-rolled NUMA memory-policy execution (`bind_memory_to_node` / `allocate_interleaved_memory` / `first_touch_memory` in `arena/numa/memory.rs`) onto mnemosyne-heap: commit `152c4a7d1` on `codex/kwavers-mnemosyne-numa` (head `08df5730f`) deletes the duplication (net −235 lines) and routes `NumaAwareAllocator` / `SoAFieldBuffer` / `first_touch_memory_parallel` through `mnemosyne_heap::numa::{bind_to_node, first_touch}`. Mnemosyne `5ca0461` owns the execution (`mnemosyne-heap::numa` + `TieredHeap::alloc` routing `PlacementHint::Numa` through `bind_to_node`); Themis owns the vocabulary; Moirai owns the parallel fan-out. PR #382 merges the fold and PR #383 normalizes the ADR statuses; Atlas now records merged Kwavers default `1d7c6899` (gitlink-only advance; the peer-dirty `codex/kwavers-floatelement-roots` working tree is left untouched per the concurrent-agents rule). The stale clean `kwavers-mnemosyne-numa` lane is removed and the lane audit is clean. | [patch] | ATLAS-KWAVERS-MNEMOSYNE-LOCALITY-001 |
| ATLAS-MOIRAI-ORDERING-052-PM-SYNC | Moirai PR #134 merged at provider default `9125837`; `CHECKLIST.md` now closes the SPSC, async wake-dedup, PAL reactor, and connection-pool reservation slices with their exact merged heads and hosted evidence. The provider remains clean and no production source changed. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-INSTRUMENT | Atlas-side instrument correction: the conformance scanner counted path-redirected `#[cfg(test)]` sidecars as production (`declared_cfg_test` missed sibling-directory `#[path]` declarers; moirai-iter gates `../async_iter_tests.rs` from `src/async_iter/mod.rs`). Fixed at `9828ee8` with three regression tests; moirai `seqcst_production` ratchet drops 101 to 85, its honest value. Remaining production sites are documented decisions: the Chase-Lev thief gate needs one total order across increment/recheck versus the resizer drain (a Relaxed increment has no SC-order position, so relaxation requires protocol restructuring for no measured win on a locked-CAS path), and idle/blocking form the documented Dekker store-buffer pair. Full family sweep complete: worker.rs, scheduler/core.rs, futex_mutex.rs, and the mpmc waiter-count adds (channel.rs:172,261 - register-before-recheck Dekker halves, independently derived) are all recorded KEEP decisions; zero undocumented production sites remain and the item closes with no source change. Ritk follow-up candidate under its own claim: `crates/ritk-vtk/src/domain/mtime.rs:46` monotonic tick admits Relaxed. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-SPSC | Moirai PR #130 merged at default `ac111b3`; the SPSC ring model uses a capacity-two wrap-around, three FIFO values, and preemption bound four. Hosted `Loom channel models` passes in run `31798789797`; the external recurseml analyzer error remains report-only. |
| ATLAS-MOIRAI-ORDERING-052-WAKER | Moirai PR #131 merged at default `fd517fe`; async `is_queued` clear/swap now use Relaxed ordering, with a Loom dequeue/clear versus wake/swap model. Exact-head workflow `31800148163` passes Loom and workspace gates; `31800148178` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. The first model revision failed on a non-contractual cross-atomic observer assertion and was corrected before the passing head. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-REACTOR | Moirai PR #132 merged at default `8830f1b` (change head `098e266`); the PAL reactor's three `running` accesses now use Relaxed ordering because the flag carries loop control only and `stop()` separately wakes the platform poller. Exact-head workflow `31800607186` passes Loom and workspace gates; `31800607152` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. | [patch] | ATLAS-MOIRAI-ORDERING-052 |
| ATLAS-MOIRAI-ORDERING-052-POOL | Moirai PR #133 merged at default `f766c6d` (change head `04dc26e`); `ConnectionPool::reserved_connections` admission/release accounting now uses Relaxed operations, with a bounded Loom model covering two serialized admissions racing one paired cancellation. Exact-head workflow `31801180700` passes Loom and workspace gates; `31801180691` passes bindings and all wheel smoke tests; recurseml analysis remains report-only. | [patch] | ATLAS-MOIRAI-ORDERING-052 |

Completed provider slices from this sweep are recorded here so the residual
rows below retain their original audit scope:

| ID | Commit | Closed scope |
| --- | --- | --- |
| ATLAS-COEUS-LAYERNORM-SHAPE-031 | coeus `a2638c03` | Multi-dimensional trailing-shape LayerNorm across Rust core, autograd, GPU provider contracts, and thin Python bindings; provider workflows and book passed. |
| ATLAS-IRIS-COLORSPACE-072 | iris `eec98186` | Explicit sRGB encoded/linear-light RGB and opacity-alpha contract with byte round-trip coverage. |
| ATLAS-PROTEUS-DOMAIN-073 | proteus `6b9bd0b` | Temperature validity-domain newtype, finite-positive validation, typed errors, and boundary tests. |
| ATLAS-ASCLEPIUS-PARAM-074 (typed-parameter slice) | asclepius `5d528d2` | Closed: distinct `Gamma50` and `LymanSlope` types have compile-fail swap coverage; the proposed CEM43 restriction was withdrawn because sub-43 °C behavior is part of the canonical law contract. |
| ATLAS-THEMIS-CONFORMANCE-083 | themis `b1b671c`; Atlas `0922c58` | Replaced Themis's duplicate thread cache with Melinoe's `thread_cached!` provider, split the oversized static-cell leaf, and closed the value-semantic assertion and safety-comment findings. Hosted Ubuntu/Windows, Miri, compile-fail, documentation, and CodeRabbit checks pass. |
| ATLAS-POSTMERGE-HEAD-084 | Atlas `73974ee` | Advanced the Ritk and Eunomia gitlinks to fetched defaults `3f30cddf` and `2e0d724c` while preserving dirty provider worktrees. Ritk hosted CI is green; Eunomia's Rust and supply-chain checks are green and its external `recurseml/analysis` status remains report-only. |
| ATLAS-HELIOS-BENCHMARK-085 | Helios `152a66c` | Helios PR #54's benchmark regression job completed successfully; the merged default head is fully green across book, Rust, Python, and benchmark checks. The Atlas gitlink remains peer-owned at its staged integration head. |
| ATLAS-THEMIS-STD-FEATURE-086 | Themis PR #22; merged default `f879e71` | Fixed the optional-dependency feature closure: `themis/std` now activates Melinoe before referring to its `std` feature. Ubuntu, Windows, compile-fail, branded Miri, and local strict Clippy are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-STABLE-PROOFS-088 | Themis PR #23; merged default `fa8dc29` | Added stable trybuild enforcement for invalid shared-cell construction (`E0599`) and overlapping mutable borrows (`E0499`) with committed stderr fixtures. Ubuntu, Windows, compile-fail nightly, and branded Miri are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-GITATTRIBUTES-092 | Themis PR #24; merged default `17d3647` | Reconciled the stale provider PM claim: the tracked `.gitattributes` already contains `* text=auto`; no source or tree-wide renormalization was required. |
| ATLAS-AEQUITAS-CI-093 | Aequitas PRs #27–#29; merged default `770a369` | Replaced unlocked lock normalization with locked metadata verification, refreshed the standalone lock to Eunomia `b6f001a`, removed overlay-only patch entries, and reconciled the delivered 0.2.0 comparison label. Default-head CI `31786185235` is green. |
| ATLAS-PROTEUS-CI-094 | Proteus PR #10; merged default `671c9fa` | Added finite CI timeouts and concurrency, converted all lock-sensitive verification commands to `--locked`, synchronized the README, and refreshed the standalone lock to Aequitas `770a369` plus Eunomia `b6f001a`. Default-head CI `31786562412` is green. |
| ATLAS-MOIRAI-NUMA-095 | Moirai PR #128 plus PM closeout PR #129; merged default `e972174` | Forwarded `MoiraiBuilder::numa_aware` through the existing core/executor feature seams and one scheduler construction path. Default topology-aware behavior remains; explicit disablement skips worker NUMA assignment construction. Default-head Rust Workspace `31787962637` and Python Bindings `31787962649` are green. |
| ATLAS-HERMES-AMX-CONFIG-087 | Hermes PR #40 merged at `b95d19d` (head `5a8d718`) | Corrected the AMX irregular-width configuration and repacked row-major GEMM right-hand panels into the VNNI layouts required by the dot-product instructions: `K/4 × 4N` for INT8 and `K/2 × 2N` BF16 elements. The provider-owned packer covers fixed-tile and blocked-GEMM paths with independent value-semantic four-byte and two-element grouping tests. Follow-up cleanup closes Hermes `must_use_candidate` 162→0, `elidable_lifetime_names` 131→0, `missing_errors_doc` 83→0, `missing_safety_doc` 8→0, `semicolon_if_nothing_returned` 92→0, and `unreadable_literal` 180→0 with a documented generated-table exception, splits the SIMD view-cast and `SimdOps` blanket-implementation leaves, scopes the macro's unreachable-code expectation to Neon with a regression test, rejects zero NTT moduli with a typed error, validates bitboard squares before shift arithmetic, removes the conformance ratchet regressions introduced by the lint cleanup, and canonicalizes NTT residues before subtraction. The current local Hermes workspace all-target Clippy gate is clean, nextest is 454/454, the Hermes/core doctest gate is 18/18 with 7 ignored, and the benchmark-target smoke gate passes. Hosted run 31779776851 is green across all seven jobs. |

**Current exact-head status (2026-08-14):** the structural and exact-head
provider audits are clean. Moirai is advanced to hosted-green `e972174`, and
Leto is advanced to hosted-green `143696d`. Aequitas, Proteus, Helios,
Iris, Ritk, Eunomia, Gaia, Melinoe, Tyche, and Hermes now match
their fetched default heads. Helios PR #54 is merged at `152a66c` and its
benchmark regression job is green. Themis's stable-proof PR #23 is merged at
`fa8dc29`. Hermes PR #40 carries the AMX VNNI packer and follow-up
lint/docs/structure cleanup, merged at `b95d19d`; local contract gates and all
seven hosted checks are green at head `5a8d718`. Proteus and Iris default-head
checks are green across build, verification, deployment, and supply-chain
jobs. Moirai default-head Rust Workspace and Python Bindings runs
`31782344026` and `31782344151` are green. Leto default-head Rust verification
run `31782827546` and Pages deployment run `31782826144` are green. The prior
benchmark and Intel SDE AMX differential checks are green. Gaia's exact
default-head CI run `31784028179` is green at `18349bc`; Melinoe's default
head `0bc287a` carries the hosted MSRV run `31785253730` green at source head
`6e6a181`; the book run
`31783965823` is green at source head `c06504c`, and the replacement head only
adds documentation to the test crate outside the book workflow's source paths.
Themis's stable-proof source remains at `fa8dc29`; its PM closeout is merged at
default head `17d3647`. Aequitas's lock-gate PR #29 default is `770a369`; its
exact default-head CI run `31786185235` passes verify and supply-chain.
Proteus's bounded locked-gate PR #10 default is `671c9fa`; exact default-head
CI run `31786562412` passes verify and supply-chain. Moirai's NUMA policy PR #128
and PM closeout PR #129 are merged at default `e972174`; exact default-head Rust
Workspace run `31787962637` and Python Bindings run `31787962649` pass.
Horae PR #12 is merged at default `41dcf00`; exact-head CI run `31792859575`
passes verify and supply-chain, and the book build `31792859919` is green.
Hyperion PR #9 is merged at default `41ef18e`; exact-head CI run `31794767546`
passes verify and supply-chain. Its external `recurseml/analysis` status is
report-only and failed without affecting the provider-owned gates.

## Tier 0 — unsoundness and wrong numbers shipping

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LETO-LAYOUT-034 — **closed 2026-08-15** | `Layout` (`crates/leto/src/domain/layout/mod.rs:13-20`) exposes `pub shape`/`pub strides`/`pub offset` with a non-validating `pub const fn new` (`:24`) and no `#[non_exhaustive]`. **84 `unsafe` blocks** in leto and every array in kwavers/CFDrs/ritk/gaia/coeus rest on its invariant; safe downstream code can construct an out-of-bounds layout today. | [major] | Zero `pub` fields on `Layout`; a validating `try_new`/`TryFrom` is the only construction path; adversarial tests per invalid class return a typed error; all five consumers build **The oracle in this row would not have fixed the defect it was filed for, and that is the finding.** Sealing `Layout` closes nothing on its own: a `Layout` carries no pointer and no length, so "fits the buffer" is not a property it can express. A proof-of-concept written before any code change had safe Rust read ~4 KiB past a 16-byte buffer **using a `Layout` from the validating `c_contiguous` constructor** - `c_contiguous([1000])` is perfectly self-consistent and simply does not fit a 4-element buffer. The real breaks, fixed in leto `580c859`: `ArrayViewMut`'s four `Index`/`IndexMut` impls dereferenced a computed offset with no `offset < len` check their `get`/`get_mut` siblings perform, and `trace`, `kron`'s strided branch and `matmul`'s `copy_back_to_out` reached `get_unchecked`/raw writes unvalidated - the last an operand mixup, validating the *scratch* view while writing through the caller's `dst`. The premise's other half was also off: the 84 unsafe blocks are exact, but about half are unrelated to layout and the layout-dependent ones rest on `validate_storage_len` at constructor/dispatch sites, not on `Layout`'s invariant. **The consumer list was wrong in both directions** - CFDrs, ritk and gaia have zero `leto::Layout` usage and were never affected; hephaestus (~270 sites), athena and apollo were, and none was listed. Sealing still shipped and still earns its place, making `size`/`min_max_offsets`/`offset_of` total: private fields, `#[non_exhaustive]`, `try_new`/`TryFrom` the only public path, validated `Deserialize`, and no struct literal anywhere outside a `pub(crate) from_parts_unchecked` serving ~15 internal derivations in hot iterator bodies. 27 adversarial tests each assert a typed `LetoError` with a positive control; the original PoC is pinned as three `#[should_panic]` regressions. **miri 182/182 clean.** `cargo semver-checks` reports 4 major breaks, declared in the CHANGELOG migration recipe and ADR 0025, not hidden. **Remainder filed, not half-done:** `ArrayView::new`/`ArrayViewMut::new` stay safe and non-validating, so today's safety is an enumeration over the current tree rather than a type-system guarantee - converting them to `unsafe fn new_unchecked` is 69 call sites across 7 repos and a second `[major]`, recorded in ADR 0025. |
| ATLAS-KWAVERS-REAL-COMPUTE-028 — **closed 2026-08-15** | *(already open — now with a fifth site and exact locations)* Five production paths return their input unchanged, three under real citations: `mixed_domain.rs:158-170` and `:219-231` (Hamilton & Blackstock 1998), `kzk_solver_plugin/solver.rs:301-310` (Jing et al. 2012), `transfer_learning/learner.rs:137-143` (live at `:43`), and newly found `kwavers-math/src/simd/interpolation_ops.rs:129-141` — an `avx2` `#[target_feature]` fn with a 5-line SAFETY comment whose body calls the scalar function. | [major] [arch] | `rg "Ok\(field\.clone\(\)\)" crates/kwavers-solver/src` → 0; each site has a differential/analytical test that **fails when the body is reverted to the clone**, demonstrated in the PR **Closed by deletion, because none of the five was a production path.** A repo-wide search over every `.rs` including examples, benches and tests, plus the plugin catalog, found **zero callers** for any of them - so there was no live call site whose physics to implement, and writing physics into uncalled code would have added ungrounded derivations rather than fixing a defect. A sixth unlisted identity mock (`DomainAdapter::adapt`, citing Ganin 2016 and Raissi 2019) went with them, and two citation attributions in this row were wrong. Removed in kwavers `7bf8eca48`. `mixed_domain` was deleted whole rather than repaired: its *remaining* method computes `k = 2*pi/(c*dt)` independent of the spectral index, so it applies one constant phase to every k-bin - a scalar attenuation dressed as an angular-spectrum propagator - and fixing only the two clones would have left that beside them. The AVX2 site was deleted rather than vectorized: its `#[target_feature]` body called the scalar function, making its five-line SAFETY comment false, and the dispatch was dead anyway on AVX-512 hosts. **The falsification evidence this oracle demands cannot exist and was not faked** - with no caller there is nothing to observe the difference, and no test was written that would have passed with the mock in place. nextest 6136/6136. **The live defect these mocks were sitting next to is filed as ATLAS-KWAVERS-KZK-LINEAR-080.** |
| ATLAS-CONSUS-PARSE-LIMITS-035 | HDF5 parse paths reachable from `Hdf5File::open` allocate on unbounded file-supplied lengths — `btree/v2.rs:685,761` (`with_capacity(total_records as usize)`, u64 straight from the header), `dataset/chunk.rs:110,126,166`, `datatype/compound.rs:336,522,550`, `consus-fits/src/table/data.rs:153,187,188` — and `parse_datatype_inner` (`datatype/compound.rs:80→329→360→446`) recurses with **no depth parameter anywhere in the chain**, so a nested compound overflows the stack (uncatchable abort). `try_reserve` appears once in the whole tree. | [minor] | A `total_records = u64::MAX` header, an oversized chunk size, and a 10 000-deep nested compound each return a typed error, not a panic or abort; each test fails on the parent commit |

The removed rows are closed findings, retained in the landed table above: Themis
`ATLAS-THEMIS-TOKEN-032`, Mnemosyne `ATLAS-MNEMOSYNE-ALIAS-033`, Apollo
`ATLAS-APOLLO-FAKEGEN-036`, and Eunomia `ATLAS-EUNOMIA-F64-SPECIALS-062`,
`ATLAS-EUNOMIA-SUBBYTE-ORD-063`, and `ATLAS-EUNOMIA-ACCUMULATOR-064`.
Their current provider source and evidence are not active Tier 0 work.

## Tier 3 — mechanical floor and stack hygiene

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LINT-FLOOR-054 — **closed 2026-08-14** | **17 of 25 members have no `[workspace.lints]`.** Where a floor is declared it is then nullified: CFDrs correctly inherits `unwrap_used`/`print_stdout`/`print_stderr`/`dbg_macro` at deny in all 12 manifests, against **288 crate-level `#![allow]` and 5 `#[expect]` repo-wide, none with a ratchet reason** — which is why 402 library print sites survive a deny. coeus has 117 allow lines with **zero** `reason=`. | [patch] | **Complete: 25 of 25 members deny `clippy::pedantic`, none at `warn`, none without** - from zero at sweep start. Every floor carries a grouped allow-list recording total and production counts per class, so debt is measured rather than tolerated; blanket crate-level `#![allow]` is **zero stack-wide** (CFDrs 299 -> 0, apollo 47 -> 0, ritk 34 -> 0, coeus 22 -> 0, kwavers 13 -> 0), and surviving suppressions are `#[expect(..., reason = "ratchet <id>")]` that expire with their last site. **Two premises in the outcome column were wrong:** several "missing `[workspace.lints]`" members are single-package repos where a package-level `[lints]` table is the only correct home, and most members' CI already passed `-D warnings`, so `warn` was already a hard floor there - the promotion mattered locally, not in CI. **The exception was CFDrs, which had no clippy step in CI at all**, plus ten crates carrying in-source `#![warn(clippy::pedantic)]` that overrides manifest `--allow` flags and made its allow-list inert; a `lint` job was added in `c9073496`. **The floors paid for themselves in real defects:** a reachable hang in kwavers' driver manifest parser (unbounded `(len()..)` range, verified by falsification - reverting the fix times the new regression test out at 60s), reachable `Instant` panics in kwavers' clinical safety monitor and moirai's registry, an overflowing manual ceiling division in hermes, case-sensitive extension matching in hephaestus (`.DLL`) and kwavers (8 sites routing `.NII`/`.DCM` to "unsupported"), 353 dead imports in apollo behind a blanket allow, three ritk `#[expect(dead_code)]` masking genuinely dead production code, four discarded `SolveReport`s in CFDrs, and a CFDrs test file holding two empty `#[ignore]`d functions. **Three mechanics worth reusing:** a file-level `#![expect(clippy::unwrap_used)]` in a `src/` file whose unwraps are all `#[cfg(test)]` fails as `unfulfilled_lint_expectations`, so those need `#![cfg_attr(test, expect(...))]`; a member with its own `[lints.rust]` table cannot also inherit; and publishing a member's `[lints] workspace = true` before the root table exists breaks manifest parsing for the whole stack through the overlay. Census at `warn`, never `deny` - at `deny` clippy aborts each crate on its first error and undercounts. |
| ATLAS-COEUS-LINT-RATCHET-097 — **closed 2026-08-17 — already merged** | The stale floor finding is closed by Coeus PR #334, merged at provider default `a8ea12eb`. The production conformance scan at the lint-ratchet head reports `allow_sites=0`; exact-head hosted Backend parity run `31989331059` passes, and Atlas already records `a8ea12eb`. The stale lane claim is released without source edits. | [patch] | Production `#[allow(...)]` residue is zero at the merged default; provider and Atlas exact-head evidence is recorded. |
| ATLAS-CACHE-FORK-055 | **Mostly stale.** Only 2 trivially small target dirs remain (athena 1.7 MB, harmonia 1.4 MB — mdbook output, not build caches). All other 23 repos have zero target directory. Deleted in this sweep. | [patch] | Closed — 58.9 GB fork state reduced to near-zero |
| ATLAS-GITLINK-DRIFT-056 | **24 of 25 submodules are checked out off the commit atlas records** (only gaia matches), and 11 sit on `codex/*` or feature branches. **The drift direction is uniform: the recorded gitlinks are AHEAD of the working trees** — athena's gitlink is 3 commits ahead of HEAD, harmonia's 2, horae's 6, hyperion's 5, and leto's tree is 17 behind both `origin/main` and its pin. These are members behind atlas, not atlas behind members, so every local verification run tests superseded state. Two sub-cases need opposite handling: athena and harmonia sit on branches with **zero** unique commits (exhausted, deletable — re-point to `main`), while horae and hyperion each carry small real deltas that are green and mergeable now, hyperion's including an actual parallel-test-race fix (`35006fd`). | [patch] | Per member: exhausted branches deleted and re-pointed to `main`; real deltas merged and the gitlink advanced; a committed check fails when HEAD ≠ gitlink without a recorded reason |
| ATLAS-ROOT-SPRAWL-057 — **closed 2026-08-14** | Meta-root held 7 unfiled report-genre files. **Not all are deletable** — `scripts/check_mdbook_links.py:15,53,66,99,181,194,565` and `fix_link_depth.py:2` cite `MDBOOK_*.md` as the normative Pattern A–F taxonomy, `scripts/tests/test_smoke_fixture.py:34,46` reads `parity_artefacts/smoke_test_filters` as a live fixture, and `.github/workflows/docs.yml:19,20` path-filters both. `PATH_DEP_AUDIT_001_ENTRY.md` is a duplicate of the board entry at `backlog.md` with 367 unique lines that must merge first. | [patch] | All four clauses verified. The tracked root manifest is now exactly `README.md`, `CHANGELOG.md`, `backlog.md`, `checklist.md`, `gap_audit.md`, `Makefile`, `pytest.ini` and the four dotfiles — no report-genre file remains. The mdBook taxonomy lives under `docs/mdbook/` with zero `MDBOOK_` citations left in `scripts/*.py`. The smoke fixture moved to `scripts/tests/fixtures/smoke_test_filters/` in `42d1607`, all seven citations re-pointed (two test constants, four `docs.yml` sites, and the prose in the fixture README, its two chapters, and `docs/mdbook/detector-parity.md`); the move broke the fixture's own `../../../` root-relative links and the test caught it, re-depthed to `../../../../../` with each of the four targets resolved on disk. `pytest scripts/tests/` 183 passed / 74 subtests, the workflow's verbatim command reports `FILE_MISSING : 0`, and the pre-commit hook's stack-wide check passed all 24 books at zero. **Deliberately out of scope:** the rest of `parity_artefacts/` is the parity stream's archive, cited from two `docs/mdbook/` chapters, and this board already records its disposal as that stream's closure increment rather than a coordinator's unilateral commit. |
| ATLAS-ADR-GOV-058 — **closed 2026-08-14** | **Corrected against `scripts/adr-index.py check`, which is authoritative — my earlier grep-based count was wrong.** The meta-repo's own ADRs and index are **clean**. At the merged provider defaults, **9 of 24 member indexes are stale or missing**; remaining member anomalies include non-canonical status headers, duplicate or missing ADR numbers, and index drift in Asclepius, Coeus, Gaia, Harmonia, Helios, Horae, Kwavers, Melinoe, Mnemosyne, and Tyche. The generator already exists and reports all of this; what is missing is the burn-down plus a CI gate on `check`. Hyperion, Iris, Proteus, Aequitas, Horae, Eunomia, Themis, Ritk, Leto, Hephaestus, and Apollo slices are landed as their corresponding `ATLAS-ADR-GOV-058-*` entries; the remaining member anomalies stay open. | [patch] | **All four clauses met.** 62 anomalies burned to 0 — 27 status casing, 27 non-canonical status, 7 duplicate number, 1 missing status. (The "9 stale/missing indexes" in the outcome column did not reproduce: `check` already exited 0 on that class.) `check` now exits 0 with **zero stdout**, verified independently of the burn-down agent; `generate` run twice more is a silent no-op; an independent scan finds no repeated ADR number in any member; `scripts/tests/test_adr_index.py` still passes. Landed as `3775ac7` (asclepius), `d30a167` (harmonia), `3db1090` (helios), `7e27727` (tyche), `7d671c0e` (coeus), `f0cc9c9a8` (kwavers), `be2d19d` (mnemosyne); apollo's two were fixed by a peer mid-run. The two supersessions were decided per file, not by rule: kwavers 037 was **rewritten in place** because grepping ADR 040 for `FeatureNotAvailable`/`SimulationRunner`/`runner` returns zero hits, so 037 still solely owns the no-zero-arrays adapter contract; mnemosyne 0002 was **deleted** because ADR 0003 removes `WgpuStagingBackend` outright and no symbol from it survives anywhere in `.rs`. CI gate added to `atlas-conformance.yml` in `af3532e`, gating on exit code **or any stdout** — `check` exits 0 for duplicate numbers and bad statuses, so an exit-code-only gate would have caught none of the 62. **Two findings filed rather than fixed:** `repos/moirai` has no `docs/adr/` directory so the checker never scans it at all (see ATLAS-CONSUS-ADR015-076, respecified), and the pre-existing ratchet step's `… \| tee` masked its own exit status, fixed in the same commit. |
| ATLAS-KS9-SUPERSEDED-059 — **closed 2026-08-14** | `backlog.md` `[KS-9]` stood **done** asserting the decision to *retain* `hephaestus-metal`, superseded by Accepted ADR 0047 which retires it — the board asserted both positions. Its recorded rationale ("would be a breaking public-surface change") was also a prohibited tiebreaker. Separately: ATLAS-ARCH-011 needs **nothing from hephaestus** — removal was executed and verified green, then reverted solely for `repos/coeus`; it unblocks via ATLAS-SUBSTRATE-002. | [patch] | Both oracle clauses verified met at `repos/hephaestus` HEAD (committed, not working-tree state): `backlog.md:3187` carries the dated **Revision 2026-08-14** note pointing at ADR 0047, and additionally records that the crate never owned a native Metal path — `MetalDevice` is a newtype over `WgpuDevice::try_metal` with zero native Metal API calls across 5 449 lines — and that the breaking-surface rationale is a prohibited tiebreaker. ATLAS-ARCH-011's dependency reads `ATLAS-SUBSTRATE-002` with the blocker narrative naming `repos/coeus`/`coeus-metal`; hephaestus appears nowhere as a blocker. |

### ATLAS-APOLLO-PRINT-098 — **closed 2026-08-17 — premise false** [patch]

The hosted `apollo/print_dbg: 6 -> 9` finding is not an Apollo library defect.
The eight call sites are benchmark executable targets, and
`BenchmarkSuite::emit` is their shared output boundary; deleting it would break
real benchmark artifacts. The Atlas scanner classifies only `main.rs` and
`bin/` paths as executable, so it incorrectly counts `benches/` output as
production library output. No Apollo source change is authorized by this
finding; the instrument correction is tracked separately.

## ATLAS-HEPHAESTUS-CONFORMANCE-101 — attention structure ratchet closure [patch, closed 2026-08-17]

Hephaestus source `702eba8` split the provider attention contract's shared
download assertion into `src/attention/assertions.rs`, reducing the exact
provider conformance scan's `oversized_files` count from 39 to 38. The source
merged at provider default `4714b8c`; the PM closure merged at `300b9e9`.
Exact-head CUDA `32027773223`, ROCm `32027773309`, WGPU `32027773340`, and
Metal `32027773250` pass. The direct Coeus attention cutover remains open under
the provider's `HEPH-ATTENTION-PROVIDER-1` item. Atlas advances the gitlink to
the PM closure without touching the peer-dirty primary checkout.

## ATLAS-RITK-CONFORMANCE-101 — diffusion binding structure ratchet closure [patch, closed 2026-08-17]

RITK source `81f510f6` split the diffusion Python binding manifest from its
`PyDiffusionMaps` and fitting implementation leaves, reducing the exact clean
provider `manifest_implementation` count from 112 to 111. The source merged at
provider default `7ae4b69b`; PM closure `62efbd79` merged at `f23a6acd`. The
provider-owned Rust, formatting, clippy, dependency-alignment, three-platform
Nextest, Python 3.9–3.13, and wheel smoke gates are green in
`32026464996`, `32026464796`, and PM run `32028306807`/`32028306813`.
The external `recurseml/analysis` result is report-only. Atlas advances the
gitlink to the PM closure without touching the peer-dirty primary checkout.

### ATLAS-CONFORMANCE-BENCH-099 — closed 2026-08-17 [patch]

Corrected `scripts/atlas-conformance.py` so Rust files under `benches/` are
classified as executable targets for `print_dbg` and related production-only
classes. The corrected instrument also recognizes exact test regions,
executable support modules, target-cache markers, and literal or manifest-rooted
`include!` edges. The focused scanner suite passes 37 tests; the baseline
records Apollo's clean orphan count as 0; hosted run `32031997052` passes the
exact delivered root with 0 regressions and 23 tightening candidates. The
tightening candidates are non-regressing follow-up cleanup, not a classifier
failure.

Takeover owner: Atlas session. The existing dirty classifier/test diff was last
written 2026-08-16 21:52–21:37 -0400 with no newer board claim or commit; its
target-fork correction is retained and reviewed as part of this item.

## Tier 2b — small domain repos (athena, harmonia, horae, hyperion)

These four are the cleanest in the stack on every mechanical axis — zero `dyn`
in any `src/`, zero fake-generic casts, zero `todo!()`, zero non-test `unwrap`,
`unsafe_code = "forbid"` and `missing_docs = "deny"` throughout, and both
LICENSE texts present and matching the manifest in all four. The findings are
about documentation truth and numerical evidence, not debt.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-ATHENA-UNDOC-066 — **closed 2026-08-14** | **athena ships two undocumented solver families.** BiCGStab (575 lines) and LSQR (487) are implemented and publicly re-exported from `athena-core/src/lib.rs`, yet appear **zero times** in the README, whose headline (`:5`) calls PCG and GMRES "its complete vertical contracts". Compounding it, the architecture tree names a crate that does not exist (`:62` `athena-wgpu` vs the real `athena-hephaestus`), a feature that does not exist (`:71` `wgpu` vs the real `accelerator`), and asserts a 500-line ceiling (`:69`) that BiCGStab breaks. | [patch] | `rg 'athena-wgpu' README.md` → 0; README documents BiCGStab and LSQR; the line-count claim is removed or true per `wc -l` Verified 2026-08-14 at athena HEAD: `rg 'athena-wgpu' README.md` = 0, BiCGStab and LSQR both documented, and the line-count claim now names `bicgstab/algorithm.rs` (575 lines) as the sole stated exception. |
| ATLAS-BOOK-PLACEHOLDER-067 — **closed 2026-08-14** | **Placeholder chapters are shipped as books.** athena has 6 chapters and harmonia 3 — every one is the 3-line string `*Chapter prose deferred.*`. A placeholder chapter is documentation's mock: a chapter exists when its teaching content does. Separately, the shared Pages callers default `mdbook-test` to `false`, so books without a compiled-sample gate can rot. | [patch] | No `Chapter prose deferred` anywhere; athena and harmonia now contain source-grounded prose. The placeholder half is closed: athena's six stubs plus a seventh LSQR chapter landed in `39b6f0b`, harmonia's three plus its two-line introduction in `10e15ae`, and the stack scan is zero. Sample-gate work remains tracked independently in ATLAS-PUB-005; callers are not represented as tested unless they pass `mdbook-test: true`. |
| ATLAS-ATHENA-KRYLOV-070 — **closed 2026-08-14** | `gmres/workspace.rs:15-16` holds the Arnoldi basis as `Vec<B::Vector>` — on Leto that is `2·RESTART+1` scattered allocations, while every scalar array in the same struct is already flat (`hessenberg` is one `Vec<Scalar>` with an index fn). The only pointer-scattering instance found across these four repos. Allocated once at construction and natural per-buffer on WGPU, so this is a CPU-side layout defect, not a hot-loop allocation. Also: non-convergence returns `Ok(SolveReport)` with `Termination::MaxIterations` rather than a typed error, `SolveError` carries no residual history, and stagnation/divergence detection is absent entirely. | [minor] | `Vec<B::Vector>` gone from `gmres/workspace.rs` behind the existing `KrylovBackend` seam; the existing allocation-stability and f32/f64 contract tests unchanged and green; a stalling operator yields a `Termination::Stagnated`-class value with non-empty history Closed 2026-08-14. The layout half landed earlier in `d3a4afe` behind `KrylovBackend::VectorBlock`; the only remaining `Vec<B::Vector>` in `gmres/workspace.rs` is a doc comment explaining the type is no longer that. The correctness half landed in `39b6f0b`: `Termination::Stagnated`/`Diverged` detected per restart cycle against a derived floor `sqrt(n)*eps*||b||`, with the two rejected sub-requests argued in ADR 0004. |

## ATLAS-CFDRS-CRLF-085 — CFDrs commits CRLF with no `.gitattributes` [patch] — blocked 2026-08-14

The repository stores CRLF line endings and has no `.gitattributes`, so any
tool that writes LF — rustfmt, a Python edit, most editors on non-Windows —
reflows whole files. During the scalar consolidation this turned a real 10k-line
diff into 128k lines until the endings were restored file by file, which is
both unreviewable and a merge-conflict generator for every concurrent agent.

`engineering_gates` requires `* text=auto` so every host hashes identical blobs;
the conformance scan already counts this as `gitattributes_missing`. CFDrs is
the case where the cost is now measured rather than theoretical.

**Acceptance oracle:** `.gitattributes` normalizes source to LF, the tree is
renormalized in one dedicated commit, and `gitattributes_missing` is 0 for
CFDrs.

**Status → blocked 2026-08-14; re-open trigger: the CFDrs working branch is
merged to `main` and no second lane is live.**

**Blocker re-verified 2026-08-18 and it still holds** — the trigger has not
fired. `worktrees/CFDrs-runtime-budget` is live on
`codex/cfdrs-backward-step-108`, and `origin` carries ten-plus branches
unmerged into `main`. Renormalizing the tree now would conflict with every one
of them, which is precisely the cost the item describes. Its scale is filed
separately as `-208`. The underlying defect was re-confirmed unchanged today:
`.gitattributes` still absent, `core.autocrlf=true`, and the same directory
still mixes stored endings — `crates/cfd-1d/Cargo.toml` LF against
`crates/cfd-python/Cargo.toml` and `crates/cfd-schematics/Cargo.toml` CRLF.

Confirmed and worse than filed.
`core.autocrlf=true` is set globally while committed blobs are *inconsistent*:
`crates/cfd-1d/Cargo.toml` is stored LF, `crates/cfd-python/Cargo.toml` and
`crates/cfd-schematics/Cargo.toml` are stored CRLF, in one directory. With
autocrlf on, `git add` LF-normalizes unconditionally, so a one-line edit to
either CRLF-stored file stages as a whole-file rewrite — measured while landing
ATLAS-CFDRS-GPU-DEFAULT-084, where a three-line change first staged as 238
changed lines. The workaround used there (`git hash-object --no-filters` plus
`git update-index --cacheinfo` to stage a CRLF-preserving blob) restores a
reviewable diff but is not a policy.

The renormalization itself is **not** safe to run now, for reasons the filing
did not anticipate. 1,702 of 2,411 tracked files are CRLF in the working tree,
so the sweep touches ~70% of the repository — and the checkout sits on the peer
branch `codex/cfdrs-legacy-approx-cleanup`, which is 2 commits ahead of and
**11 commits behind** `origin/main`, with a second live lane at
`worktrees/cfdrs-ci-workspace-rust` on `feat/cfdrs-ci-workspace-rust`.
Renormalizing there would conflict with both the unmerged `main` commits and
the sibling lane across every touched file. Creating `.gitattributes` alone is
also rejected as a half-measure: git reads it from the working tree whether or
not it is tracked, so it would start LF-normalizing files one at a time on
every subsequent `add`, producing the same churn as drip rather than as one
reviewable commit.

**Required sequence when unblocked:** land on `main`, not a feature branch —
add `.gitattributes` (`* text=auto`) and `git add --renormalize .` as a single
commit containing nothing else, with every lane closed or rebased across it.

## Deferred with a recorded reason

- **ATLAS-PRIVACY-NAMING-1** stays open and unchanged. `repos/leoneuro-rs` is a
  separate organisation's repository holding local commits `1b71a79` and
  `50bfcd9` on a branch whose remote is **gone**, so it carries unique unpushed
  work and must not be deleted. It is correctly gitignored; the violation is
  that it is *named* in board items, which is a rewrite of existing entries, not
  a tree change.
- **Detector residuals.** The `declared_cfg_test` fix does not yet recognise
  test modules gated through a `#[cfg(feature = "…")]` wrapper around a
  `#[cfg(test)]` block. consus still reports 334 production unwraps against an
  audited estimate near 34, so a second refinement pass is warranted before that
  number drives any burn-down.

## RITK-VIEWS-047 — Collapse seven data accessors to two [major] — pushed, merge held 2026-08-18

Landed on `refactor/ritk-two-accessors-047` (`cfba6507`), **not merged**: a
breaking public-API removal is `[major]`, so it holds for an independent
verdict rather than self-review.

The deferral that kept this open was arithmetic, not difficulty. ADR 0019's
"681 call sites across ~250 files" counted every call to any of the seven
accessors — including the 565 on `data_slice`, one of the two that *survive*.
The accessors that had to go carried **60 sites**; all 60 migrated, with no
re-export, `#[deprecated]`, or forwarding wrapper. ADR 0019 now carries a
dated revision note correcting the figure; ADR 0021 records the decision.

Survivors chosen on caller evidence: `data_slice() -> Result<&[T]>` (565 sites
want a contiguous borrow and already handle the strided failure) and
`data_cow_on(&B) -> Cow<[T]>` (59 want the layout-independent form; the 50
wanting ownership get it from either). The removed five were a
default-backend axis crossed with an ownership axis. The `try_` pair was
worse than redundant — its own Rustdoc said extraction "succeeds for every
valid image", so **28 sites carried a `?` on a branch that cannot be taken**.

Transform consolidation rode along: `CartesianGridGeometry` promoted from
`pub(crate)` in ritk-filter to public in ritk-spatial and generic over rank,
with a typed `NonCartesianGrid` error replacing a message that named its
first caller. Four sites became consumers rather than an eighteenth
implementation; both `apply`/`apply_native` core pairs were verified
byte-identical by `diff` before extraction (`inverse_displacement` 738→583,
`iterative_inverse_displacement` 393→263). Net **−529/+655 across 47 tracked
files plus 3 new** — a reduction while adding a public module and 3 tests.

**Gates** (`+1.97.0-x86_64-pc-windows-msvc`, exit codes from files not pipes):
fmt 0 · clippy `--workspace --all-targets -D warnings` 0 · nextest
**5332 passed / 25 skipped**, 298s, 0 slow · doctests 0 · `semver-checks
--baseline-rev bacfe1f6` **195 pass / 1 fail**, the failure being
`inherent_method_missing` naming exactly the five removed methods and nothing
else.

Two evidence caveats recorded rather than smoothed: the crates.io
semver run is **vacuous** (0 checks / 253 skipped) because ritk-image's
0.3.0→0.4.0 bump predates this work and makes the major lints unrunnable —
the `--baseline-rev` run is the real evidence; and the confirmatory nextest
re-run stalled at 4730/5332 under peer build contention with **zero
failures**, so the green figure above is from the run before the final
rustfmt-whitespace and documentation edits.

**Acceptance for merge:** an agent that did not author it confirms the five
removals are the complete break set, the 28 deleted `?` sites were genuinely
unreachable, and the two extracted cores are equivalent. Then merge and
advance the gitlink.

## RITK-SHARED-TREE-STALE-BASIS-213 — ritk's shared tree is checked out 58 commits behind origin [patch] — open 2026-08-18

- Mid-session a peer switched `repos/ritk` off `refactor/ritk-two-accessors-047`
  onto a local `main` sitting **58 behind `origin/main` and 2 ahead**. In a
  shared tree a branch switch moves the branch for everyone, so this landed
  under an in-flight verification without warning.
- **This is the mechanism behind the stale-basis reverts seen repeatedly this
  sweep.** Any commit authored from this checkout is built on a 58-commit-old
  base; a whole-file write or artefact regeneration from it silently reverts
  everything landed since, passes the author's own gates, and surfaces later
  as unrelated deletions. Filing rather than fixing: the two local commits are
  safe (both mine, 4 days old, preserved on
  `origin/feat/tract-output-formats`), so nothing is stranded, but moving a
  branch a peer just checked out is not mine to do while they may be mid-work.
- It also produced two false readings in this session, both corrected below
  under `-210`.
- Acceptance: the tree is on a branch at or ahead of `origin/main`, and the
  2 local commits are confirmed merged or dropped. Re-open trigger: any
  commit lands in ritk from a base more than one sweep behind origin.

## RITK-DOC-GATE-210 — `cargo doc` is red on ritk's default branch [patch] — open 2026-08-18

- Found because `-047`'s evidence table had no rustdoc step.
  `cargo doc --workspace --no-deps` under `RUSTDOCFLAGS=-D warnings` fails at
  HEAD, independent of any branch work.
- Six links repaired in `5a5de0ef` (unresolved `[Image]`, `[Point<D>]`, a
  matrix written as `rows [0,-1,0], [1,0,0], [0,0,1]` that parsed as three
  link targets, and two public-to-private links to
  `non_negative_information`). **The gate is still red**: ritk-io fails on
  `MAX_SEQUENCE_DEPTH`, same public-to-private class.
- A repo sweep finds ~41 further candidates of that class. They are *not*
  all defects — rustdoc only errors when a **public** item's docs link a
  private one, and the sweep over-matches trait methods and test-only items.
  Fixing them blind would be churn, so the item is the sweep-then-verify,
  not a bulk edit.
- Acceptance: `cargo doc --workspace --no-deps` exits 0 under
  `-D warnings`, and a rustdoc step joins ritk's CI so it cannot go red
  unobserved again — the absence of that step is the actual defect here.

**Progress 2026-08-18: seven links fixed, gate still unconfirmed.**
`MAX_SEQUENCE_DEPTH` is delinked from `anonymize_object` in `4c55c57c`,
landed onto the branch through a private index so the shared tree's
checked-out branch was never touched. The two remaining references to that
const (lines 338, 376) are on private items and resolve fine.

The confirming run could not be made: partway through, `-213` moved the
shared tree onto a 58-behind `main`, which reverted the working copies of
the earlier fixes and the lockfile. **Two readings taken after that point
were wrong and are corrected here rather than left in the record:**

1. I reported ritk's `apollo-fft` requirement as still `^0.26` with my bump
   "orphaned". False — `origin/main` and this branch both carry `^0.27.0`.
   I was reading the peer's stale `main`. There is no requirement lag and
   nothing to re-apply.
2. I attributed the resulting `hermes-simd-core ^0.6` resolver failure to
   that lag. It was entirely the stale checkout: the 58-behind base pins
   `apollo-fft 0.26`, whose transitive `^0.6` cannot unify with the
   overlay's local hermes 0.7.

Both edits made under the mistaken reading were reverted; they were my own,
no peer state was touched. The remaining work is one clean run of the gate
from a current checkout, then the CI step.

## ATLAS-CRATE-LEVEL-ALLOWS-217 — 502 blanket suppressions the ratchet never counted [major] — open 2026-08-18, specified 2026-08-19 (CFDrs, kwavers, consus members delivered 2026-08-25)

**Specified 2026-08-19, and the severity in the original filing was
overstated.** Measured with the scanner's own classification rather than a
grep: `missing_docs` (243 mentions) and `clippy::unwrap_used` (31) are
**almost entirely test-scoped** — inner attributes inside
`#[cfg(test)] mod tests`, which is the correct way to scope a test exemption,
and which `split_test_region` already excludes from the count. The seven
`unwrap_used` sites I first flagged as production are six `src/**/tests.rs`
sidecars plus one correctly-scoped test module. **Zero production violations
of the unwrap ban.** My grep counted test files; the committed detector does
not, and the detector was right.

What production actually holds, and it is **not** one pile of 502:

**CFDrs carries 349 of the ~433 production sites, in 62 files, and its
workspace already has a curated 53-entry `[workspace.lints]` table.** Against
that table:

| pile | mentions | disposition |
|---|---|---|
| already `allow` workspace-wide | **204** | pure redundancy — delete, zero behavioural change |
| `clippy::print_stdout` | **42** | overrides a workspace **`deny`**, in library crates — the real violation |
| everything else | ~105 | per-crate escalations needing individual judgement |

So the bulk is not debt at all, it is duplication of a decision already
recorded once at the workspace level — the same SSOT failure as any other
copied constant. And the genuine finding is small and sharp: **42 blanket
allows silently re-enabling `print_stdout` in library crates whose own
workspace table denies it**, spread over cfd-validation (21), cfd-core (10),
cfd-2d (10), cfd-3d (5), cfd-1d (4), cfd-schematics (1) — all libraries, so
the CLI exemption does not apply.

**Root cause found 2026-08-19, and it inverts the plan. The "redundant"
mentions are not redundant — they are load-bearing, because the workspace
table is inert.**

moirai-core and moirai-gpu both carried `#![warn(clippy::all)]` and
`#![warn(clippy::pedantic)]` **in source**. A source attribute outranks the
manifest `[lints]` table, which cargo delivers as command-line flags, so the
workspace allow-list had no effect on those crates despite
`[lints] workspace = true` — and the per-crate `#![allow(...)]` lines were
the only thing suppressing pedantic. Deleting them alone reddened clippy with
**92 diagnostics**; that is how the premise was caught.

The same in-source escalation is present in **nine CFDrs crates** (cfd-1d,
-2d, -3d, -core, -io, -math, -optim, -python, -validation), which is where
349 of the ~433 sites live. So the CFDrs "204 redundant" figure above is
wrong for exactly those crates, and the correct order is inverted: **remove
the in-source `warn(all)`/`warn(pedantic)` first**, which makes the table
authoritative, and only then are the per-crate allows genuinely deletable.

**Second member done: apollo** (`style/apollo-butterfly-lint-consolidation-217`,
pushed). Different shape, because apollo has **no** in-source escalation — its
table was already authoritative, so the redundancy analysis held. Two
butterfly modules each carried the same pair of blanket allows;
`too_many_arguments` was already in the table (pure duplication) and
`many_single_char_names` moved into it with its reason recorded once —
butterfly kernels name radix inputs a, b, c, d after the signal-flow diagrams
they implement. **Four blanket file allows → one reviewed table entry.**

Verified with `clippy -p apollo-fft --all-targets -D warnings`: nine errors
remain and **none** names either removed lint. All nine are
`missing_const_for_thread_local` in cache/scratch/twiddle modules this change
does not touch — the documented windows-gnu false positive, filed below.

**Apollo residual, found in passing:** three `thread_local!` sites
(`radix_composite/cache.rs:119`, `mixed_radix/caches/scratch.rs:10`,
`mixed_radix/caches/twiddle.rs:16`) lack the `#[expect(clippy::missing_const_for_thread_local)]`
that `adaptive.rs`, `winograd/traits.rs` and `orchestration/cache/plans.rs`
already carry, so apollo's clippy is red on gnu independently of this item.
Two of the three already use `const { … }` initializers, making the lint a
false positive there; `twiddle.rs` allocates via
`with_capacity_and_hasher`, so its case is a real design question rather than
a suppression. Left alone deliberately: that is a kernel-cache decision on a
peer's tree, not part of a lint-hygiene item.

**First member done: moirai** (`0746861`, branch
`style/moirai-workspace-lint-authority-217`, pushed). `crate_level_allows`
**39 → 20**, clippy `--all-targets -D warnings` 0, nextest 104/104. The floor
gets *stricter*, not laxer: the workspace table sets
`pedantic = { level = "deny" }` where the source attribute said `warn`.

- Revised sequence: (1) per member, drop the in-source `warn(all)` /
  `warn(pedantic)` so `[workspace.lints]` governs, then delete the
  now-genuinely-redundant allows — verified by clippy, which is what proves
  redundancy;
  (2) fix or justify the 42 `print_stdout` sites, since a per-crate allow
  overriding a workspace deny is the strongest form of the pattern the floor
  prohibits; (3) adjudicate the ~105 remainder, promoting recurring ones into
  the workspace table with a comment and converting the rest to per-site
  `#[expect(..., reason)]`.
- Non-CFDrs remainder is small and can follow: moirai 39, coeus 17, apollo 8,
  consus 6.
- The lesson, again: an ad-hoc grep and the committed instrument disagreed by
  nearly 2×, and the instrument was correct both times. Measure with the
  scanner.

Detector fixed in `d9c8c60`; the debt itself is the open work.

`allow_sites` counts the substring `#[allow(`, and `#![allow(` does not
contain it — the `!` breaks the match. So the **blanket form was invisible**,
which is precisely the form the lint floor singles out as never acceptable:
"suppressions are per-site `#[expect(lint, reason = "...")]`, never blanket or
crate-level". An inner attribute silences a lint across every item in its
module or crate, *including code written after it*, so it cannot be reviewed
where it takes effect — strictly worse than the per-item form the ratchet did
count.

Production-code counts now seeded into the baseline (502 total):

| CFDrs | moirai | apollo | coeus | consus | kwavers | ritk | gaia | mnemosyne | hermes | leto |
|---|---|---|---|---|---|---|---|---|---|---|
| 367 | 47 | 34 | 18 | 10 | 10 | 8 | 4 | 2 | 1 | 1 |

Found while checking `e31065b`, which raised CFDrs `allow_sites` 88→90 to
absorb a Clippy PR that added `#![allow(...)]` attributes — the ratchet
recorded the two per-item allows and none of the crate-level ones. CFDrs'
`crates/cfd-1d/src/lib.rs` alone opens with a run of ten, several carrying
justifications that read as deferrals ("Error documentation deferred for
internal APIs").

- Acceptance: ratchet burn-down, CFDrs first. Each removal either fixes the
  underlying lint or converts to a per-site `#[expect(lint, reason = "...")]`
  that expires when the site is fixed. No `--accept-raises`.

**CFDrs member — steps 1–2/3 delivered 2026-08-25** (branch
  `fix/cfdrs-lint-authority-217`, CFDrs PR #372 at head `0155d8f4`,
  MERGEABLE):

  - **Step 1** (`2244e3a1`): removed the in-source `#![warn(clippy::all)]` /
    `#![warn(clippy::pedantic)]` escalation in **all ten** crates (the
    previously-claimed nine plus cfd-schematics in combined form), making the
    47-entry `[workspace.lints.clippy]` table the single authority — the
    moirai-verified shape. Then deleted **108 blind allow lines across 31
    files** whose every lint is already workspace-allowed (pure copies;
    lines mixing rust lints like `missing_docs` kept). Clippy-verified as
    the redundancy oracle: all-targets zero real warnings, nextest
    3256/3256, fmt clean, 31 files / 125 pure deletions, CRLF byte-preserved.
  - **Step 2** (`0155d8f4`): the `print_stdout`/`print_stderr` blanket
    overrides of the workspace deny → self-expiring `#[expect]`. The
    detector's "42 sites" undercounted once more (the real surface is
    ~100 files once tests/examples are included), so each file was
    classified: src test-sidecars and integration tests narrowed to the
    lint that actually fires (`print_stderr` for `eprintln!` skip-notes,
    both where stdout prints exist); cfd-3d `bifurcation/validation.rs` +
    `venturi/analysis.rs` keep an unconditional file-level expect because
    `print_summary`/flow diagnostics are real library report APIs;
    files whose prints live only in doc comments dropped the attribute
    entirely. Clippy 0 warnings (expects are self-expiring — any stale
    suppression surfaces as an unfulfilled-expect warning), nextest
    3256/3256, fmt clean.
  - Remaining: step 3 (~105 per-crate escalations needing individual
    adjudication, separate PR).

**kwavers member delivered 2026-08-25** (branch
  `fix/kwavers-lint-leftover-217`, PR #646 at head `f9c124c53`, MERGEABLE):
  the last 4 crate-level allows — 3 were pure duplicates of the workspace
  table (`doc_markdown`, `module_inception`, `needless_range_loop`, all
  already `allow` in `[workspace.lints.clippy]`) and were deleted; the
  python-binding `type_complexity` allow became a self-expiring
  `#[expect]` with the binding-surface reason (`too_many_arguments` stays
  allowed — documented Python mirror surface). Clippy 0 warnings, fmt
  clean; the single `pstd_finite_window_born` failure reproduces at main
  (pre-existing, unrelated).

**consus member removed 2026-08-25** (branch
  `fix/consus-lint-expect-217`, PR #55 at head `2c97deb`, MERGEABLE):
  consus's floor is `pedantic = deny`, so every remaining crate-level
  allow suppresses a genuinely firing lint — converted all 6 to
  self-expiring `#[expect]` with the documented reason
  (`empty_line_after_doc_comments`, `too_many_arguments` ×2,
  `needless_range_loop`, `collapsible_match`, `useless_conversion`).
  `budget.rs` untouched (already the correct test-scoped pattern). Clippy
  0 warnings, nextest 2582/2582, fmt clean (CRLF preserved).

  Remaining members: coeus 18 (peer branch `codex/coeus-lint-ratchet`
  claims it — not actionable), ritk 8, gaia 4, mnemosyne 2, hermes 1,
  leto 1.

  **Merge status 2026-08-25 (hosted checks, exact-head policy — nothing
  merged yet):** CFDrs #372: lockfile pass, Rust-workspace-gate + book
  figures still pending. kwavers #641 (`84ba553ef`) and stacked #642
  (`e1ecdd231`) each expose five initial preflight/review checks rather than 26
  immediately queued jobs; duplicate
  coverage PR #645 is closed as superseded, releasing its queued matrix.
  kwavers #646: no checks observed (fresh push).
  consus #55: no checks observed. kwavers #644 (gpu ratchet): **21/31
  checks SUCCESS** — only the 8 long legs remain pending (Build & Test
  stable/beta, Heavy Validation, Miri, Lockfile integrity, PINN
  Convergence, Benchmark smoke, feature-combination plotting); heads all
  confirmed unchanged and MERGEABLE. Merge each at its exact head the
  moment its checks go terminal.

## ATLAS-LANE-SPRAWL-222 — 26 lane directories against a two-per-repo bound [patch] — open 2026-08-19

Found while needing one lane for `-221`. `git_discipline: Worktrees` bounds a
repository to **two** working trees (main plus one lane), and the bound is a
creation precondition, not an aspiration.

| repo | trees | bound |
|---|---|---|
| kwavers | 5 | 2 |

`worktrees/` currently holds **16 directories**, including the sanctioned
`.archive` metadata directory. The former empty Consus lane directory and
two empty root Consus husks were removed after confirming zero children. The
remaining structural violation is the clean detached Kwavers lane at
`D:/tmp/kw-verify`, outside the single canonical lane root; it remains
unremoved because it is an external checkout whose ownership is not
established by this tree.

The remaining external lane is clean, but its owning process and intended
lifecycle are not established from Atlas. It remains a recorded residual,
not a deletion target.

The rule already names the cause: "sprawl is friction's product", and the
prescribed fix is a committed lane tool making create/re-point/close one
command each, with the tree-count precondition enforced in `create`. Without
it the compliant path is more work than the workaround, which is exactly the
state here.

- Acceptance: a committed lane tool enforcing the two-tree precondition, the
  canonical root, and the naming convention; every member at or under two
  trees; the misplaced consus lane consolidated (`git worktree move`); the
  husks cleared once their holders exit. ~~A conformance class counting trees
  per member so the bound is measured rather than remembered.~~

**Measurement half done 2026-08-19 — and built twice.** A peer landed
`count_excess_worktrees` in `dbb1a4e` while I was writing the same class, and
their commit swept my uncommitted definition in alongside theirs, so HEAD
briefly carried **two definitions**, the second shadowing the first. Nothing
failed, because both were correct and produced identical counts
(consus 1, kwavers 2, ritk 3). Deduplicated in `febe7d5`, keeping theirs and
porting two fixes: the bound now comes from `WORKTREE_BOUND` rather than a
bare literal, and the docstring's claim to read "the packed-refs mechanism"
is corrected to what it does read — `.git/worktrees/` entries, one per linked
worktree, which is why the bound is reduced by one before subtracting.

Behavioural tests cover whichever implementation survives: they build a real
repository, add lanes one at a time, and assert the count crosses at the third
tree. The ratchet now refuses a third tree exactly as it refuses any other
debt increase, so the bound is enforced rather than remembered.

The collision is itself the lesson worth keeping — two agents built the same
detector within an hour because neither claim was visible to the other until
it landed.
- **Not** a blocker for anything: at cap the existing lane is the next work,
  which is how `-221` proceeded — the stale `consus-zarr-fix` lane held a
  branch already merged as PR #47, so it was re-pointed rather than adding a
  fourth tree.

## RITK-PEER-RATCHET-211 — Peer commits regressed three ratchet classes on ritk [patch] — open 2026-08-18

- `print_dbg 12 → 17`, `oversized_files 43 → 44`,
  `manifest_implementation 104 → 105`.
- Attribution is unambiguous: the counts are **identical at HEAD and in the
  dirty worktree**, so they came from the peer commits (#171–#173) that moved
  ritk's HEAD from `bacfe1f6` to `0f0b5c56` mid-session, not from the
  accessor work, which is ratchet-neutral.
- `print_dbg +5` is the one to look at first — five new print/`dbg!` sites in
  library code is a lint-floor breach, not drift.
- Acceptance: each class back at or below baseline, or the baseline
  regenerated with a recorded justification per the generator contract.

## ATLAS-ARCH-008-RUNNING-IN-PLACE-225 — The conversion converts and re-accumulates at the same rate [patch] — open 2026-08-19

`atlas_scattered_containers_classify.py` has a gate mode
(`--verify-oracle`) and a committed oracle
(`scripts/oracles/arch-008-production-sites.txt`, 243 sites). Running it for
what appears to be the first time:

> **35 sites now in production but missing from the oracle; 36 oracle sites
> no longer in production.**

Net **−1**. The interesting number is not the total, it is the pair: 36 sites
were genuinely converted while 35 new pointer-scattered containers landed. So
`ATLAS-ARCH-008` is not stalled and not regressing — it is **running in
place**, and has been doing so unobserved because nothing ran the verifier.
The inflow is spread across seven members: consus 8, gaia 7, CFDrs 7, coeus 5,
ritk 4, moirai 2, kwavers 2.

A conversion item cannot converge while new instances arrive at the
conversion rate. Wiring the verifier is what stops the inflow, and it matters
more than clearing the backlog.

**Deliberately not wired yet, and deliberately not regenerated.** Wiring it
now reds CI on 35 pre-existing sites; regenerating the oracle to make it pass
would absorb 35 new production sites into the accepted set, which is exactly
the baseline laundering fixed in `-216` this same day. The order is: justify
or convert the 35, then wire.

Also worth noting: every write of this oracle has landed inside an unrelated
chore commit — it was created by `5956d02` ("chore(gitlinks): Advance ritk
…"), the same scope-creep commit that duplicated `parity_artefacts`, and
touched before that by two more gitlink commits. Derived state has been
riding along in commits whose messages do not mention it.

- Acceptance: the 35 are converted or individually justified in the oracle;
  ~~`--verify-oracle` wired into `atlas-conformance.yml`~~ **done by a peer,
  2026-08-19**; the oracle only ever regenerated in a commit whose subject
  says so.

**A peer wired the gate while this was being written, and did it the right
way round.** `atlas-conformance.yml` now runs `--verify-oracle`, with the
oracle path and the classifier added to the trigger list. Critically they
**did not regenerate the oracle** to make the new gate pass — it is still 243
lines and still reports the same 35 — so the gate goes red and forces the
conversion instead of absorbing it. That is the opposite of the `e9c5821`
baseline-raise, and the right call.

Their step comment also corrects an assumption in my measurement: CI scans a
**clean checkout** pinned to the root gitlinks, while my numbers came from
live worktrees carrying peer WIP. I checked the 20 sampled drift sites and
all are **tracked and clean** — real committed content, not WIP — so the
drift is genuine, though the exact CI count may differ where a member's
worktree and its recorded gitlink disagree. The next PR run is the
authoritative number.

## ATLAS-UNWIRED-GATES-224 — Instruments that exist, pass, and are never run [patch] — partly fixed 2026-08-19

**`atlas-registry-metadata.py` had never been invoked by any workflow.** It
was written, committed, and green — and on the single day it was run by hand
it found kwavers declaring six keywords against a cap of five, plus the
category slug `medical`, which does not exist in the crates.io taxonomy.
crates.io enforces both **at upload**, after the version number is spent, so
the rejection is not retryable under that version. Wired in `572a585`; the
defect it found is fixed in kwavers `1aa24beb7`.

An unreachable taxonomy degrades to `UNVERIFIED` at exit 0 and the slug
snapshot is committed, so it cannot flake on crates.io availability.

**`atlas-lane-audit.py` is deliberately left unwired.** It already implements
`-222`'s whole audit half — tree bound, canonical lane root, named branch,
prune freshness, standalone-clone detection — and currently reports the same
four violations. But a CI clone has one working tree, so in CI it would pass
unconditionally and prove nothing. It is an orient-time and
replenishment-time check by its own contract; its findings belong on the
board, which is where `-222` now carries them.

- Residual: `atlas_scattered_containers_classify.py` is also unwired. Assess
  whether it is CI-valid (like the registry check) or inherently local (like
  the lane audit) before deciding — those are the only two answers, and
  "wire everything" is the wrong one.
- The pattern, worth keeping: **a gate that has never failed may never have
  run.** Three instruments were built during this sweep; one was silently
  inert. Checking `grep -ohE "scripts/[a-z-]+\.py" .github/workflows/*.yml`
  against `ls scripts/*.py` is the ten-second version of that audit.

## ATLAS-STALE-CHECKOUT-FINDINGS-223 — Gates measure the checkout, and 8 of 25 members are behind [patch] — partly fixed 2026-08-19

**Four false findings this session trace to one cause.** Gates read whichever
revision happens to be checked out. A survey today found **8 of 25 members
behind their origin**: CFDrs 5, coeus 6, consus 3, gaia 2, themis 2,
aequitas 1, apollo 1, tyche 1.

The four, all reported as defects before being traced:

1. ritk's `apollo-fft` requirement read as lagging at `^0.26` with my bump
   orphaned — I was reading a `main` 58 commits behind (`-213`).
2. The `hermes-simd-core ^0.6` resolver failure attributed to that lag; it
   was the stale base.
3. Three ADRs reported untracked — that one was the *index* rather than the
   checkout, but the same shape (`-219`).
4. coeus reporting a drifted ADR index, where `origin/main` had carried the
   missing row for six commits. I regenerated it and nearly committed the
   redundant change before checking upstream.

Fixed in `7481561` for the ADR gate: findings now state how far behind the
checkout is. The fallback to `origin/main` is the case that matters, not an
edge — a detached HEAD has no `@{upstream}`, and detached checkouts are
exactly the stale ones.

- Residual: `atlas-conformance.py --worktree` has the same exposure. It does
  guard the default path (`check_clean_revision` requires a clean tree with
  matching gitlinks), but `--worktree` bypasses that and is what gets run
  while peers hold dirty trees — every conformance number in this session
  came from it.
- Acceptance: any gate reporting against a checkout states that checkout's
  distance from its upstream, or refuses to report; and the members above are
  brought current, which is `-213`'s territory.

## RITK-ACCESSOR-FOLLOWUPS-212 — Two consequences the accessor migration exposed [patch] — open 2026-08-18, specified 2026-08-19

**Sharpened: the `Result` is now provably uninhabited, and the sibling makes
it explicit.** On `refactor/ritk-two-accessors-047`, `extract_vec`'s body is
`image.data_cow_on(&B::default()).into_owned()` — infallible — while its
signature is still `anyhow::Result<(Vec<f32>, [usize; D])>`. There is no
longer any fallible operation inside the wrapper at all.

Beside it sits `extract_vec_infallible`, which does the **identical** thing
without the wrapper, and whose own Rustdoc states the truth: "canonical Coeus
host extraction is infallible". So the codebase already contains the
correction — added as an additive `_infallible`-suffixed sibling rather than
applied to the original, which is the marker-naming and compatibility-soup
pattern in one.

The fix is one function, not two: `extract_vec` becomes infallible,
`extract_vec_infallible` is deleted, callers drop their `?`.

**Scoped as its own atomic `[patch]`, to land immediately after `-047`
merges.** The two names carry **518 call sites** (183 + 335). Folding that
into `-047` would triple a branch already held for review and is precisely
the "branch grows past its item" pattern — the same call made for apollo's
827-site `precise`/`reduced` rename. Sequenced after the merge because `-047`
is what removes the last fallible operation; before it, the `Result` is
merely near-dead rather than provably dead.

- Second half unchanged: ~14 `.into_owned()` sites can drop the copy, since
  `Cow` derefs. Same commit is fine — both are mechanical over the same
  surface.
- Acceptance: zero `_infallible`-suffixed siblings; `extract_vec` returns a
  tuple; no call site carries `?` on it; workspace green.

- `ritk_tensor_ops::extract_vec` now has a **visibly fake `Result`**. It is
  pre-existing, but was hidden one level down inside `try_data_vec`; removing
  that wrapper surfaced it. A `Result` whose error branch is unreachable is
  the same defect the `try_` pair carried.
- ~14 `.into_owned()` sites can drop the copy entirely, since `Cow` derefs.
  Kept out of `-047` deliberately: that migration was held
  semantics-preserving, and turning it into a performance change mid-flight
  would have made the semver evidence harder to read.

## ATLAS-CFDRS-LANE-DIVERGED-208 — CFDrs lane holds 99 unpushed commits and is 18 behind its own remote [patch] — open 2026-08-18

- Found while re-verifying `-085`'s blocker. `worktrees/CFDrs-runtime-budget`
  sits on `codex/cfdrs-backward-step-108` at `7b9673ef` (8 hours stale, so
  reclaimable under the one-hour sweep), **99 commits ahead of `origin/main`
  and 99 ahead of its own remote branch, while 18 behind it** — the local lane
  and its pushed ref have diverged, not merely drifted.
- Rescued non-destructively: `7b9673ef` pushed to
  `origin/ci/cfdrs-lane-rescue-208`. No force-push over
  `origin/codex/cfdrs-backward-step-108`, so the peer's 18 remote-only commits
  are untouched. The 99 commits are now fleet-visible rather than living only
  in one working tree.
- The 99 are substantive, not churn: lint-residual closures across cfd-1d and
  cfd-2d, a masked-step metric fix, a parabolic-inlet allocation reuse, and a
  manual workspace gate.
- Acceptance: the two heads are reconciled into one branch (the 18 remote-only
  commits merged in, not dropped), gates green, merged to `main`, both the lane
  branch and the rescue ref deleted. Until then the rescue ref is quarantine,
  not a second home — it carries no independent development.
- Note this is why `-085` stays blocked: its re-open trigger requires no second
  lane live, and this lane is both live and the largest single body of
  unmerged CFDrs work.

## ATLAS-APOLLO-LINT-EXPECT-ROT-001 — Remove obsolete Windows Clippy expectations [patch] — in-progress

- Owner: codex coordinator; scope: Apollo source files containing the 42
  `#[cfg_attr(windows, expect(clippy::missing_const_for_thread_local, ...))]`
  sites across 28 files. Non-goals: Apollo's peer-owned `Cargo.lock` and
  `backlog.md`, the Stockham policy work, and unrelated provider consumers.
- Acceptance: the expectations are removed or narrowed only if the pinned
  toolchain still emits the lint; Apollo's workspace Clippy gate passes with
  `-D warnings` and no `-A` override, with value-semantic tests unchanged.
- Verification: record the exact provider revision, focused tests, doctests,
  Clippy, rustfmt, and rustdoc results before closing; update the provider
  item without staging its peer-owned working-tree changes.

## ATLAS-APOLLO-STOCKHAM-POLICY-050C — Parameterize the dispatch-policy matrix [minor] — open 2026-08-18

- Three parallel type families cover the same (scalar × ISA) axis inside
  `stockham`: `StockhamAvxBackend` (4 impls), `StockhamPrecision` (6
  hand-written ZST markers = {Precise,Reduced} × {scalar, AvxFma, Avx512},
  the 1240 lines of `precision/{precise,reduced}.rs`), and `StockhamKernel`
  (2 impls, on the *scalar* axis — the 050B census mis-filed this one).
- `StockhamPrecision` is a dispatch-policy matrix written per cell; it can be
  parameterized over `B: StockhamAvxBackend`. Type-level, no numerics risk,
  real reduction — unlike 050A.
- Also here: `StockhamAvxBackend` gives three methods provided bodies that are
  `unreachable!("Not implemented for this precision")`. A panicking default is
  a mock-shaped seam — the differing fused-stage sets belong in a capability
  const or a split trait.
- Acceptance: `precision/{precise,reduced}.rs` line count materially reduced
  with the ZST marker set derived rather than enumerated; zero
  `unreachable!` provided bodies on the backend trait; bit-identical FFT
  outputs against the pre-change build on the existing differential suite.

## ATLAS-APOLLO-COMPLEX-SEAM-050B — Element-parameterize the complex seams [minor] — open 2026-08-18

- Census corrected on re-run; the original count of eight was wrong.
  `FftPrecision` and `TwiddleOutput` already carry **three** impls including
  `Complex<f16>` — a seam admitting three element types is element-parameterized
  already, not a `Complex64`/`Complex32` fork. `StockhamKernel` is on the scalar
  axis and belongs to 050C.
- Genuine two-impl complex pairs: **five** — `KernelScalar`, `PlanScratch`,
  `TwiddleStore`, `NormalizeSlice`, `ScratchDispatch`.
- Independent of 050A: type-level and crate-wide versus x86 leaf codegen.

## ATLAS-KWAVERS-REAL-COMPUTE-028 — Remove Kwavers production identity paths [major] [arch] — open

- Owner: Kwavers provider owner; Atlas scope is the audit record and consumer
  integration gate. Kwavers source files are peer-owned in the active checkout.
- Findings: realtime GPU scan conversion, mixed-domain time propagation and
  nonlinear correction, KZK retarded-time application, and PINN domain
  adaptation all contain identity-return paths on the fetched default. Exact
  evidence and locations: `gap_audit.md#atlas-kwavers-real-compute-028`.
- Acceptance: each seam performs input-sensitive computation or is removed or
  narrowed; the corresponding analytical/differential tests fail under the old
  identity body; focused provider gates and the full Kwavers integration gate
  pass; no clone-only implementation remains at the named locations.
- Re-open trigger: a clean committed Kwavers source increment lands on
  `origin/main` or a peer claim becomes stale under the one-hour sweep.

## ATLAS-USCT-FWI-024 — Transmission-USCT FWI parity [minor] — open 2026-08-13

Audit and evidence: `gap_audit.md#atlas-usct-fwi-024`. kwavers leads the
reference on forward-model and optimizer machinery; these close the deltas.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| FWI-024-A | Replace fixed-step backtracking in `frequency_domain/inversion.rs` with the linearized exact line search `α = −⟨g,d⟩/⟨d,Hd⟩`, reusing the matrix-free Hessian action for the curvature. | [minor] | done — kwavers `912fe1983`, merged to main via cascade/provider-042; content verified on origin/main | Claude | Met. `⟨d,Hd⟩` reuses the existing `hessian_vector` (moved to `gradient.rs`, one implementation for both consumers) rather than adding a second forward-projection path. New test recovers a weak anomaly with the seed set 200× too large; falsified by forcing the old behaviour (fails with a one-entry objective history). 44/44 frequency-domain tests, clippy/doc/fmt clean in scope |
| FWI-024-B | Cap the NLCG β with Fletcher–Reeves: `β = min(max(β_PR,0), β_FR)` (Gilbert–Nocedal). | [patch] | **done 2026-08-19** — kwavers PR #406 merged at `53b3f984`; content verified on `origin/main` | Claude | Met. Convergence on the existing inversion tests is monotone and no worse than `β_PR⁺`; a case where unbounded `β_PR` overshoots is added as a regression test. Architecture Validation `Validate Clean Architecture` and `Test Suite Coverage` reported failures that were infrastructure-only; benchmark, Miri, build-matrix, and Code Quality passed. |
| FWI-024-C | Angular-spectrum split-step implementation of the existing `HelmholtzForwardOperator` seam, reusing the phase-screen code rather than a second copy. | [minor] | **done 2026-08-19** — kwavers PR #415 merged at `1f37ec907`, verified on origin/main by content (`as_operator.rs`, +680 lines). Its two failing benchmark gates were a stale branch base, not a regression: the branch predated `.github/actions/install-system-dependencies` on main, and `benchmark regression check` was cascading from `complete benchmark smoke`. Updated from main; all 27 checks pass. Earlier state: — kwavers PR #415 @ `dc9d61bd0` (`feat/kwavers-fwi-asm-split-step`): `AngularSpectrumSplitStepOperator` with phase-screen toggle + source taper; forward/backward propagation from transmit z-plane; receiver sampling on propagated planes | — | Differential against CBS on a weak-contrast phantom within a derived bound; documented divergence where reflections matter (ASM is one-way). 50/50 frequency_domain tests, clippy `-D warnings`, fmt clean locally |
| FWI-024-D | Transmission-USCT acquisition: two opposed linear arrays on a rotation stage, per-view interpolation between a fixed reconstruction grid and view-aligned simulation grids, gradient accumulation across views. | [minor] [arch] | **increment 1 done 2026-08-20 — kwavers PR #420 merged at `b20eb48b`, Atlas gitlink in `fdf9981`; increment 2 in review 2026-08-20** — increment 1: kwavers PR #420 (acquisition seam, ADR 115), auto-merge set after all CI passes. Increment 2: kwavers PR #424 (`RotatingOpposedLinearArray` + `RotatingAcquisition` + ADR 116), targets PR #420 base. ADR 116 settles route (a) — per-view element-position rotation on one fixed grid. Route (b) — per-view model interpolation — rejected because it puts systematic interpolation error inside the gradient. Finite-window PSTD excluded from rotating acquisition (requires on-grid coords; extension deferred). Increment 3 is the inversion integration test (phantom recovery oracle). Earlier context: the acquisition seam is kwavers PR #420, recorded as ADR 113 (PR #418). Behaviour-preserving: 54/54 frequency-domain incl. the Ali 2025 parity gate, 1009/1009 solver, 721/721 downstream, all callers and PyO3 bindings updated with no shim. With the seam in place, the rotating acquisition splits into a design fork worth settling before code. Two routes, and the cheap one does not fully work:  **(a) Rotate the geometry on one fixed grid.** The acquisition simply reports rotated element positions per view — which is what the seam already expresses, with no interpolation anywhere. The Green's-function operators accept continuous coordinates, and `cbs/projection.rs` already carries band-limited interpolation for off-grid sampling (`sample_field_with_bli`, `source_density_from_bli`), so Born and CBS take rotated positions directly.  It fails on one operator. The PSTD finite-window path resolves receivers through `exact_grid_index`, whose `exact_axis_index` rejects any coordinate more than `1e-9` off a grid node. A linear array rotated by anything but a multiple of 90° lands off-node on essentially every element, so that operator would reject every view — not silently degrade, which is at least honest, but it means route (a) covers only part of the operator set.  **(b) Rotate the model per view** — the route the item description assumed ("per-view interpolation between a fixed reconstruction grid and view-aligned simulation grids"). Works for every operator, since each view simulates on an axis-aligned grid. The cost is real: resampling the slowness volume per view, and resampling the gradient back, puts interpolation error inside the gradient that the inversion then descends on. That error is systematic, not noise — it correlates with view angle — so it needs a derived bound and a round-trip test (rotate by θ, rotate by −θ, compare against identity within that bound) before any recovered phantom means anything.  **Not settled here.** The choice is [arch] and belongs in an ADR alongside 115, with the rejected option recorded: whether to extend the finite-window operator to BLI receivers (making (a) universal) or to accept per-view resampling. The sizing point is that increment 2 is not "add a rotating acquisition" — the acquisition type itself is a few dozen lines on top of the seam. The work is whichever of those two problems is chosen. Two findings on the way in: the ADR first specified a generic seam and was corrected to `&dyn` before merge (Config holds `Arc<dyn HelmholtzForwardOperator>`, so a generic method is not dyn-compatible); and `receiver_indices_on_grid` was hoisted out of the transmit loop at three sites, correct only under a ring’s rotational symmetry and silently wrong for every rotated view but the first. Original sizing note: The frequency-domain FWI is hard-bound to `MultiRowRingArray`, not merely parameterized by it: 36 references across all six modules (`forward`, `gradient`, `gauss_newton`, `operator`, `finite_window`, `inversion`), consuming ring-specific API (`circumferential_elements`, `cylindrical_source`). A rotating opposed-linear-array acquisition cannot be expressed through it, so D needs an acquisition seam extracted first — an [arch] change with an ADR as its first step, per versioning. Sizing before starting: the seam is the item, and the rotation-stage geometry rides on it. | — | Recovers the sound-speed phantom from a simulated 360°/2° sweep within a derived tolerance; per-view rotation round-trips to identity |

## ATLAS-US-CAPABILITY-023 — ITKUltrasound capability parity [arch] — open 2026-08-13

Audit and evidence: `gap_audit.md#atlas-us-capability-023`. Items are
DoR-shaped and dependency-ordered; US-023-A gates the clean form of B and D.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| US-023-A | ADR: non-Cartesian acquisition images as a coordinate seam in ritk (curvilinear, 3-D phased array, slice series) — index→physical map carried by the image type so existing resamplers/filters apply unchanged; decide ritk-vs-kwavers ownership for G2 and G4. | [arch] | done 2026-08-13 — ADR 0042 Accepted | Claude | Met. Enum-dispatched `CoordinateMap` selected over a fourth type parameter; G2 and G4 both owned by ritk |
| US-023-A1 | Implement the ADR 0042 seam in `ritk-image`: `CoordinateMap` with `Cartesian` + `CurvilinearArray`, carried on `Image`, dispatched by both batch and both single-point transforms. | [major] | done 2026-08-13 — ritk PR #128 merged as `c608f758` | Claude | Met. Cartesian path bit-identical (pinned by test); curvilinear round-trip, fan symmetry/curvature, out-of-fan NaN, dimensionality rejection all covered. 1173 tests, clippy `-D warnings`, rustdoc, fmt clean. |
| RITK-CI-1 | Restore SimpleITK parity for `InverseDisplacementField` 2-D/3-D and `IterativeInverseDisplacementField`. **Diagnosed** (`gap_audit.md#atlas-ritk-ci-diag-035`): introduced by `3aa73ba0` (ADR 0020); the 2-D case is ~27x worse than 3-D, and the new Gram-Schmidt in-plane basis path runs *only* for the 2-D-embedded shape. Under identity direction it must reduce to the world axes exactly — the parity break proves it does not. | [major] | todo — owner is 3aa73ba0's author; diagnosis recorded | — | The three `test_simpleitk_cmake_data.py` parity tests pass |
| RITK-CI-2 | Test Suite (ubuntu-latest) exceeds the 30-minute job cap during 'Install LLVM and Clang'. | [patch] | **done 2026-08-19** — ritk PR #178 skips apt-get when clang already present | — | Ubuntu job completes inside budget |
| US-023-D2 | Block-matching follow-ons: multi-resolution search-region sources and block-radius calculators, FFT-accelerated NCC, Bayesian-regularized and strain-window displacement calculators, and an end-to-end pipeline over a block grid. | [minor] | **done 2026-08-19** — verified on ritk `origin/main` by content, not by claim: PR #187 (volume pipeline), PR #191 (strain-window rejection filter), PR #192 (the follow-ons, rescued per ATLAS-RITK-D2-STRANDED-100). Earlier history: — ritk PR #187 merged at `40618f84` (volume pipeline) is on main; the follow-ons are **not**: `c110664b` was never pushed, its branch no longer exists on the remote, and no PR was opened. See ATLAS-RITK-D2-STRANDED-100. Landed separately: strain-window *rejection* filter (ritk PR #191). The stranded commit adds: `OwnedPyramid` (nearest/min-max), block-radius calculators, FFT-NCC via apollo-fft (`fft` feature), `BayesianDisplacementPrior`, `StrainWindowRegularizer`, `DisplacementPipeline` | Claude | track_volume recovers known shift; strain recovers 2% compression exactly; pipeline recovers known compression strain within derived bound; 46/46 tests, clippy `-D warnings`, fmt clean |
| US-023-D4 | Move `block_matching` into a dependency-light crate; parameterize its sample type; reuse one candidate buffer across the search. | [arch] | done — ritk PR #183 merged (21/21 green) | Claude | Met. `cargo tree` = one edge (`anyhow`); 9 tests incl. cross-precision and 1-D line; ritk-registration 375 green |
| US-023-D3 | Consolidate kwavers' NCC + parabolic speckle-tracking kernel onto the block-matching seam and delete the duplicate. | [minor] | done — kwavers PR #409 merged (31/31 green) | Claude | Met. Both duplicates deleted, net -75 lines; 1551/1551 kwavers-physics tests pass through the seam; verified on origin/main by content |
| KW-GPU-SCANCONV | Remove the no-op `scan_conversion` stage from the kwavers-gpu realtime pipeline, which reported a scan-converted frame it never converted. | [patch] | **done 2026-08-19** — kwavers PR #405 merged at `ba1803e9`; the no-op call and stub are deleted from `realtime.rs`, `process_frame` ends at `log_compression` | Claude | CI green; behaviour unchanged (the removed call was the identity); content confirmed present in `origin/main` |
| US-023-A2 | `PhasedArray3D` variant on the ADR 0042 seam. | [minor] | **review** — ritk PR #188 `fix/phased-array-origin-direction`: batch and single-point transforms compose with image origin/direction | Claude | Non-zero origin correctly offsets world point; round-trip with origin; batch/single agree; 65/65 tests pass |
| US-023-A4 | `SliceSeries` variant on the ADR 0042 seam. Design settled by **ADR 0047**: owned per-slice rigid transform list (memory budget is three orders below the image it describes), composition with `Direction`, forward clamp / inverse reject out of range. `CoordinateMap` stops being `Copy`, so it lands as a breaking change. | [arch] | **done 2026-08-19** — ritk PR #180 merged at `40618f84` | Claude | Met. Round-trip within 1e-9; pure-translation sweep reproduces Cartesian exactly; single-slice degenerate; forward clamp; inverse rejection; 6 new tests; 5351/5351 workspace tests pass |
| US-023-A5 | Move `CoordinateMap`/`CurvilinearArray`/`PhasedArray3D` from `ritk-image` to `ritk-spatial` (pure `f64` geometry, no tensor coupling); `ritk-image` re-exports and keeps using them. | [minor] | **done 2026-08-13** — ritk PR #132 merged at `9ae68b45` | Claude | Met. Static review clean; no new P0/P1. `ritk-spatial` gains no new dependency. |
| US-023-A7 | Give `CurvilinearArray` an explicit `first_lateral_angle` instead of ITK's implied centre-on-boresight. Implemented in `ritk-spatial` via `try_new(first_lateral_angle)` + `centred()` helper for ITK compat. Geometry methods do not take `lateral_count`. | [major] | **done 2026-08-13** — implemented in ritk-spatial when PR #132 merged | — | Met. `try_new()` takes explicit `first_lateral_angle`; `centred()` provides ITK `-(n-1)/2·Δ` convention; no geometry method takes `lateral_count`. |
| US-023-A3 | kwavers `ScanConverter` delegates its polar math to the `ritk-spatial` geometry SSOT, keeping Leto storage and Aequitas typed geometry; the duplicated formulas in `b_mode/scan_conversion.rs` are deleted. | [minor] | done 2026-08-13 — kwavers `6731f8f32` on `codex/kwavers-floatelement-roots` | Claude | Met. Differential oracle replays the pre-migration formulas across the whole raster within a derived `1e-9` bound (`atan2` vs `atan` rounding; observed worst case `8e-12`, and a mis-indexed pixel would differ by `>= 1`). No polar formula remains in kwavers. 731 tests, clippy `-D warnings`, fmt clean |
| US-023-A6 | Decide whether B-mode moves behind the `kwavers` ritk bridge so scan conversion becomes a true `resample` through the seam and the converter is deleted outright. Splits the B-mode pipeline across crates, so it is a recorded decision, not an incidental one. | [arch] | **done 2026-08-20** — ADR 0048 Accepted; kwavers main at `b20eb48b` uses `ritk_spatial::CurvilinearArray` (the geometry SSOT per ADR 0042) directly in `ScanConverter::convert`. No bespoke polar arithmetic remains. PR #412 (ritk-image approach) closed as superseded: adding `ritk-image`/`coeus-core` to `kwavers-analysis` violates the architecture constraint that the analysis layer not depend on the tensor stack. The ritk-spatial path satisfies the ADR 0048 intent without that violation. | Claude | Met. No bespoke polar arithmetic in kwavers-analysis; `index_from_cartesian` on `CurvilinearArray` is the geometry SSOT; differential oracle test present in the b_mode suite. |
| US-023-B | QUS spectral tissue characterization — **increment 1 of 2**: gated Welch spectra, reference-phantom normalization, and Lizzi-Feleppa parameters (slope, intercept, midband). | [minor] | done 2026-08-13 — kwavers `33f4ce637` on main | Claude | Recovers known slope/intercept/attenuation from a synthesized RF phantom with an analytically derived tolerance; differential check against the forward scattering/attenuation physics kwavers already models |
| US-023-B2 | QUS increment 2: spectral-difference attenuation estimation (dB/MHz/cm). **Not ported from ITK**: implements Yao/Zagzebski/Madsen (1990) eq. (3) (stays in dB domain). | [minor] | **done 2026-08-19** — kwavers PR #404 merged at `8003eeaa`; `attenuation_from_spectra()` in `qus/attenuation.rs` | Claude | Met. Zero-attenuation oracle exact; known-attenuation recovery (slope 0.5, intercept 0.1 dB/(MHz·cm)) exact. 10/10 tests pass. |
| US-023-C | SRAD (Yu & Acton) speckle-reducing anisotropic diffusion in `ritk-filter/src/diffusion/`. | [minor] | done — ritk PR #169 merged | Claude | Value-semantic parity against the published formulation on a speckled phantom; edge-preservation asserted against Perona–Malik on the same input |
| US-023-D | Block-matching elastography framework — **increment 1**: metric-image and displacement-calculator seams, direct NCC, and max-pixel / parabolic / cosine refinement. | [arch] [minor] | **done 2026-08-18** — ritk PR #173 merged at `0f0b5c56` | Claude | Met. Exact integer translations recovered exactly; half-voxel shift lands strictly between integers and beats the integer estimate; gain/offset invariance asserted. 382 tests, clippy, fmt clean |
| US-023-E | Directional 1-D FFT frequency-domain filter over N-D images with a pluggable frequency-response function seam. | [minor] | **done 2026-08-19** — ritk PR #175 merged at 63e165ad | Claude | Met. 9/9 tests pass. |
| US-023-E2 | Ultrasound IO **increment 1**: persist the acquisition coordinate map through NRRD read/write, so beam data does not reload as a raster. | [minor] | done — ritk PR #174 merged | Claude |
| US-023-F | Ultrasound IO remainder: ITK's HDF5 ultrasound layout. **Decided: declined** — ADR 0046. ritk gains no HDF5/C dependency; NRRD carries acquisition geometry, and ITK/h5py convert at the boundary. Revisit trigger is a real acquisition source that emits only that format. | [arch] | done — ADR 0046 Accepted | Claude |

Review evidence for US-023-A2: the phased-array implementation is only exercised
with zero origin and identity direction. `Image::transform_*` and
`physical_points_to_continuous_indices` remain Cartesian-only, while the new
native and scalar phased branches ignore `Image` origin/direction metadata.
The geometry also converts generic scalar indices to `f64`, performs the
trigonometry there, and narrows back to `T`. PR #131 merged at `9ae68b45`, but
these source-level findings remain open against that default; the Atlas gitlink
tracks the merged head without treating merge as capability closure.

US-023-A3 audit note: the current kwavers `ScanConverter` accepts an arbitrary
`angle_min`, while the RITK curvilinear map centers the fan from the image beam
count. The cutover must either preserve that acquisition convention through a
validated map parameter or reject non-centred geometry before deleting the
converter; the existing bilinear differential remains the acceptance oracle.

## ATLAS-EUNOMIA-FLOAT-CBRT-014 — Land sign-preserving FloatElement::cbrt SSOT [feat]

- Owner: Atlas integration.
- Outcome: close the ATLAS-AEQUITAS-ROOT-OPS-012 SSOT follow-up. Eunomia now
  owns `FloatElement::cbrt` — `libm::cbrtf` default (correct reduced-precision
  path for `F16`/`Bf16`) with native `libm::cbrt` overrides for primitive
  `f64` and the `F64` wrapper — on `codex/eunomia-float-cbrt` (`bba10b6`).
  Aequitas' `Quantity::cbrt` switched off its `powf(1/3)` workaround onto the
  new SSOT seam (`cbrt(-8 m³) == -2 m`, no longer NaN) on
  `codex/aequitas-root-ops-closure` (`071538c`); the NaN-domain test is now a
  sign-preservation test. Both provider gate sets green: eunomia fmt, `-D
  warnings` all-targets, clippy, nextest 109/109, doctests; aequitas fmt,
  `-D warnings` all-targets, clippy, nextest 85/85, doctests, no-default.
- Status: delivered; both branches pushed. The final ATLAS-AEQUITAS-ROOT-OPS-012
  follow-up — semantics-marked dimension tuples (`ReciprocalVolume`,
  `Angle`) — is now closed too (see ATLAS-AEQUITAS-ROOT-OPS-012, `3ce7b03`).

## ATLAS-MNEMOSYNE-CONSUS-REFRESH-013 — Reconcile merged provider PM closeouts [patch]

- Owner: Atlas integration.
- Outcome: advance the Mnemosyne and Consus gitlinks to their merged default
  heads and synchronize the root evidence for the stale provider PM items.
- Acceptance: Mnemosyne `e57e2d6` and Consus `5163eb1` are recorded exactly;
  provider-owned Rust, Miri, package, platform, and documentation evidence is
  cited; exact-head, structural integration, and lane audits pass without
  staging peer-owned provider checkout changes.
- Status: complete in this root increment. Mnemosyne PR #44 merged after Rust
  verification plus Miri arena, Stacked Borrows, and Tree Borrows passed;
  Consus PR #21 merged with all repository-owned package, MSRV, platform,
  MinIO, and feature-matrix checks passing. The recurring `recurseml/analysis`
  result remains an external analyzer integration failure.

## ATLAS-AEQUITAS-ROOT-OPS-012 — Land aequitas rational-power sqrt/cbrt increment [feat]

- Owner: Atlas integration.
- Outcome: the pre-existing scalar-operator WIP (MulAssign/DivAssign, scalar
  * quantity) was already merged upstream via PR #21 (commit `dd0b8e1`,
  merge `0052b80`) with 9 value-semantic tests — verified complete in the
  current aequitas default; no further action needed for that axis. The
  remaining in-flight worktree WIP — type-level `SqrtDimension`/
  `CbrtDimension` plus `Quantity::sqrt`/`cbrt` through the `FloatElement`
  power surface — was reconciled with concurrent peer edits and landed as a
  completed, tested increment on `codex/aequitas-root-ops-closure`
  (`72ef8b4`): concrete exponent-tuple impls (8 sqrt shapes, 3 cbrt
  shapes), module wiring, 12 value-semantic tests, CHANGELOG, and review
  corrections (number-density tuple accuracy, `Div`-projection doc,
  `float_cmp` lint). All canonical gates green: fmt, `-D warnings`
  all-targets check, clippy `-D warnings` all-targets/`--all-features`,
  nextest 80/80, doctests 13/13, `--no-default-features` check.
- Status: delivered; aequitas branch pushed. Cargo.lock tooling residue
  (config-level `[patch]` overlay drift) left as pre-existing dirt.
- Tracked follow-ups (outside this increment): (1) SSOT — eunomia
  `FloatElement` gained a libm-backed sign-preserving `cbrt`
  (`libm::cbrtf`/`libm::cbrt`) and aequitas dropped the `powf(1/3)` path
  (ATLAS-EUNOMIA-FLOAT-CBRT-014: `bba10b6` + `071538c`). (2) semantics-marked
  dimensions (`ReciprocalVolume`, `Angle`) now have sqrt/cbrt impls — the
  tuple macros accept an input semantics type and normalize the output to
  `BaseSemantics` (`Angle::sqrt` → dimensionless, `ReciprocalVolume::cbrt` →
  reciprocal length), landed `3ce7b03` on
  `codex/aequitas-root-ops-closure` with 2 value-semantic tests. (3) a
  sign-preserving cbrt for negative operands is resolved by (1). All three
  follow-ups closed.

## ATLAS-TYCHE-REFRESH-011 — Reconcile merged Tyche PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Tyche gitlink to merged PM-closeout head `5efaee7` and
  record exact-head evidence for the completed consumer documentation slice.
- Status: complete; the root pointer now records `5efaee7`, and the exact-head
  audit scope is ready for final verification.

## ATLAS-LETO-PM-REFRESH-010 — Reconcile merged Leto PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Leto gitlink to the merged PM-closeout head and retain
  exact provider-head evidence without staging peer-owned Leto changes.
- Status: complete; Leto PR #107 merged as `e525d8d`, the root gitlink now
  records the exact default, and the pointer evidence is synchronized.

## ATLAS-LETO-CONVOLUTION-012 — Close provider convolution contract [major] [arch]

- Owner: Atlas integration.
- Outcome: close the stale Leto convolution-provider record after the generic
  CPU contract and Coeus direct consumer integration are both merged and
  exact-head verified.
- Status: complete; Leto PR #108 source `7172b338463c72faa2a561a3c84bda26d827351a`
  merged as default `a722fbc81cd1d82df74ef9e5acc1d9997d340d9d`. PR #108's
  exact provider run `31690152639` and post-merge default run `31690301356`
  pass. Coeus default `a4063be1` retains the direct consumer contract after
  PM-only PR #325; the root pointer is advanced without staging peer-owned
  checkout dirt.
- Residual: 33 pre-existing Leto Rustdoc broken/private-link warnings; no
  convolution-specific diagnostic. Hephaestus owns accelerator execution.

## ATLAS-MOIRAI-PM-REFRESH-009 — Reconcile merged Moirai default [patch]

- Owner: Atlas integration.
- Outcome: advance the Moirai gitlink to the merged PM-closeout head and
  synchronize the exact-head evidence for the full twenty-provider inventory.
- Scope: root `repos/moirai` gitlink plus current Atlas checklist/backlog/gap
  audit records; peer-owned Moirai checkout edits remain untouched.
- Status: complete; Moirai PR #125 merged as `ae9a5df`, the root gitlink now
  records that exact default, and the twenty-provider exact-head audit passes.

## ATLAS-LIVE-HEAD-SWEEP-008 — Reconcile moving provider defaults [patch]

- Owner: Atlas integration.
- Outcome: refresh the root gitlinks for provider defaults that advanced after
  the preceding exact-head check and preserve current hosted evidence.
- Scope: root `repos/mnemosyne` and `repos/hermes` gitlinks plus synchronized
  Atlas PM records; provider source, locks, and peer-owned checkouts are
  excluded.
- Acceptance: Mnemosyne `1ad5819` and Hermes `5785143` exact-head hosted CI
  passes; both committed gitlinks match fetched defaults; the root exact-head,
  coherence, and lane audits pass.
- Status: complete after exact-head CI; the pointer and evidence commit are
  delivered in this integration increment.

## ATLAS-HEPHAESTUS-REFRESH-007 — Integrate cross-entropy PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Hephaestus root gitlink and root evidence after the
  provider merged its cross-entropy PM closeout.
- Scope: root `repos/hephaestus` gitlink and synchronized Atlas PM records;
  preserve the provider checkout's peer-owned dirty `Cargo.lock`.
- Acceptance: fetched `origin/master` hosted WGPU, CUDA, ROCm, and Metal runs
  pass at the merged provider head; the root gitlink equals that head; the
  provider PM closure and exact-head root checks are recorded.
- Status: complete at provider head `9385686`; the Atlas pointer and evidence
  are delivered in this integration increment.

## ATLAS-PROVIDER-DRIFT-005 — Post-merge exact-head convergence [patch]

- Owner: Atlas integration.
- Outcome: advance the two provider gitlinks that moved after the prior
  integration closure and make the committed audit guard verify fetched
  default heads when requested.
- Scope: root `repos/mnemosyne` and `repos/ritk` gitlinks, the provider
  integration audit script and its tests, and synchronized root PM records.
  Provider source, locks, and peer-owned working-tree changes are excluded.
- Acceptance: both gitlinks equal their fetched default heads (`32524e3` and
  `53bb013`), exact-head mode detects mismatch and supports non-`main`
  defaults, focused script tests pass, and the item records hosted evidence.
- Status: complete at Atlas `062afef` (branch `codex/atlas-provider-drift-005`).
  Exact-head structural mode and the focused eight-test regression suite pass.

## ATLAS-PROVIDER-INTEGRATION-004 — Twenty-one-provider audit and cleanup [major]

- Owner: Atlas integration plus provider-owned cleanup follow-ups.
- Outcome: keep all 21 requested provider gitlinks, hosted evidence, audit
  inventory, book content, workflow security, and worktree topology coherent.
- Acceptance: exact gitlinks match fetched default heads; the committed audit
  reports 21 providers; provider book placeholders are absent from delivered
  heads; substantive hosted gates pass; mutable action refs and non-linked
  worktree directories are either fixed or recorded with an owner and trigger.
- Status: exact-head integration closure at Atlas `48a257d`; provider source
  follow-ups remain tracked below. Consus book closure merged as
  PR #19; Coeus book and reusable-workflow closures merged as PRs #321 and
  #322. Provider workflow action pinning and reusable-workflow refreshes are
  merged. Exact gitlinks, hosted gates, workflow scans, book scan, and lane
  audit are green.

## ATLAS-RITK-EUNOMIA-001 — RITK Eunomia 0.8 local closure — 2026-08-10

- RITK's workspace manifest and standalone lock now resolve Eunomia `0.8.0`
  with `rkyv 0.8.17`; no active RITK manifest requests Eunomia 0.7.
- Removed the stale Windows-only `missing_const_for_thread_local` expectation
  from `repos/ritk/crates/ritk-filter/src/morphology/mod.rs`. The initializer
  was already const-compatible under Rust 1.97; the expectation itself failed
  under `-D warnings` as unfulfilled. No morphology behavior changed.
- RITK repository-owned validation is green at the reconciled standalone lock:
  locked metadata, formatting, strict all-target/all-feature Clippy, workspace
  doctests, and workspace Rustdoc pass; full Nextest passes 5,137/5,137 with
  24 configured skips, and the focused `ritk-filter` suite passes 1,123/1,123.
- The Atlas overlay was bypassed only for standalone lock/gate verification and
  restored afterward. Existing RITK peer dirt in `CHANGELOG.md`, `Cargo.lock`,
  filter/interpolation/Python sources remains preserved; no child reset, clean,
  commit, push, or gitlink advance was performed.
- Local closure is complete. Hosted security, exact-head owner review, package
  archive verification, crates.io/PyPI indexing/publication, trusted-publisher
  enforcement, and merge remain external release gates; the broader RITK
  historical backlog is not claimed complete by this slice.

### Melinoe/Mnemosyne/Apollo boundary adoption — 2026-08-10

- Apollo validation now has a test-only `mnemosyne-memory` workspace dependency
  and a focused `BrandedVec -> BrandedCell<[T]>` boundary contract in
  `crates/apollo-validation/src/application/suite/tests.rs`. The contract
  validates branded allocation, token-gated slice borrowing, mutation, and
  post-mutation reads through Mnemosyne's public facade; Apollo does not reach
  into Melinoe internals for this memory boundary.
- `rustfmt --check` and the focused Apollo test pass (`1/1`). The initial link
  attempt was blocked by the absent `D:/msys64/tmp` directory; the required
  environment directory was created and the final link/test run passes. Apollo's
  lockfile was reconciled from the final manifest: the `apollo-validation`
  package now records its `mnemosyne-memory` dev edge and the standalone locked
  focused test plus `--lib` check pass with the Atlas overlay bypassed. The
  reconciliation also materialized the workspace's git sources and removed
  overlay-only `[[patch.unused]]` noise; it is broader than a one-line Melinoe
  edit and remains uncommitted alongside existing Apollo peer state.
- The slice is intentionally test-only: Mnemosyne remains the memory SSOT,
  Melinoe remains the generativity SSOT, and no provider, Moirai, or Apollo
  runtime source was changed.

### Melinoe/Moirai partition-result adoption — 2026-08-10

- Added `moirai-parallel/src/tests.rs::test_par_partition_map_preserves_partition_order`
  as a consumer contract for the existing Melinoe-backed
  `par_partition_map` bridge. The test proves that disjoint branded shards can
  return ordered per-partition results while the original cells remain readable
  through the brand token.
- The change is intentionally test-only and leaves Moirai scheduler queue
  ownership, the Melinoe provider, and the peer-dirty executor bridge untouched.
  `rustfmt --check` and `git diff --check` pass; the reconciled standalone
  lockfile now pins Melinoe to delivered `47863b12aa0cd4e65cb9556b2c9bbf1353a5ee26`.
  Locked metadata and library check pass, and the Melinoe-enabled focused suite
  passes 33/33 with the Atlas overlay bypassed. The broad generated lock diff
  remains uncommitted with peer work.
- The Moirai test change and reconciled Cargo.lock remain uncommitted in the
  peer worktree; no provider reset, cleanup, commit, push, or gitlink advance
  was performed.

## ATLAS-ARCH-011 — Retire hephaestus-metal per ADR 0047 [arch] [major] — blocked

- Owner: claude/fable-loop (claimed 2026-08-03); scope: `repos/hephaestus`
  (`crates/hephaestus-metal`, the
  workspace member list, the `hephaestus` facade's `metal` feature, and the
  conformance suite's Metal instantiation). Coeus is **out of scope** — see
  the note under ATLAS-SUBSTRATE-002.
- Outcome: the crate and its 5 449 forwarding lines plus 2 606 test lines are
  deleted. Metal targeting survives unchanged as
  `WgpuDevice::try_metal(...)`, and the vendor identity as
  `device.adapter_info().map(|i| i.backend)`.
- The facade's `metal` feature is **kept and re-pointed**, so consumers'
  spelling of intent survives the removal: it comes to mean "acquire a
  Metal-preferring `WgpuDevice`" instead of "compile a second copy of the
  operation surface".
- Acceptance oracle: (a) `cargo nextest run` green for the hephaestus
  workspace at `--all-targets` with the member entry gone, and the `metal`
  feature seam building in its re-pointed form; (b) the conformance suite
  passes with the Metal instantiation removed and no clause left
  unreferenced; (c) a stack-wide grep finds no `hephaestus_metal` reference
  outside Coeus's tracked item; (d) the two CFDrs `backend_name()`
  assertions still pass, confirming no observable contract moved.
- Risk/change class: `[major]` — a published crate is removed. Needs a
  CHANGELOG entry under Unreleased with the one-line migration
  (`MetalDevice::try_default` → `WgpuDevice::try_metal`). Release itself
  stays outside this item's authority.
- Verification note: coverage is not lost. The Metal instantiation ran the
  same clauses over the same code path as the WGPU one, so it asserted
  nothing WGPU does not already assert; Metal-*adapter* coverage is a
  question of which adapter CI acquires, not of which crate the suite names.
- Dependencies: **ATLAS-SUBSTRATE-002** (see the blocker below). ADR 0047 is
  Accepted; the decision is not in question, only its sequencing.
- **BLOCKED 2026-08-03, discovered by executing it.** The hephaestus-side
  removal is mechanically complete and was verified to that point — member
  entry, workspace dep, the facade's optional dep and its three `?/` feature
  entries, the `metal` feature re-pointed to `["wgpu"]`, the
  `pub use hephaestus_metal as metal` re-export, and the crate itself, with
  `cargo metadata` green and **zero** residual `hephaestus_metal` references
  in any `.rs`/`.toml` under `repos/hephaestus`. It was then reverted, for
  the reason below.
- **`repos/coeus` depends on `hephaestus-metal`** (`coeus/Cargo.toml:59`, and
  `coeus/crates/coeus-metal/` consumes it). The ADR scoped Coeus out on the
  grounds that its collapse is SUBSTRATE-002's business — that scoping was
  wrong, and the stack overlay is what proves it: the overlay is generated
  from the *dependency closure*, so while any member declares
  `hephaestus-metal`, it emits a `[patch]` pointing at the deleted crate
  directory and **every build beneath the stack root fails**, not just
  Coeus's. Upstream removal and the consumer edge are one co-evolution unit.
- Cutting that edge is not available: `repos/coeus` is on a live peer's
  `codex/coeus-publish-cycle` branch, and the Coeus board claims
  `coeus-hephaestus`, `coeus-rocm`, `coeus-metal` under Codex
  (`coeus/docs/backlog.md:464`) — a fresh, commit-backed claim over exactly
  the files this needs, mid-publish-cycle. Deleting a crate out from under a
  publish cycle is the one thing not to do here.
- Re-open trigger: `repos/coeus` no longer declares `hephaestus-metal` —
  i.e. ATLAS-SUBSTRATE-002 deletes `coeus-metal`, or the peer's publish cycle
  completes and its claim is released. Then re-apply the hephaestus removal
  (it is a ~15-minute mechanical replay of the list above) and land both
  repos as one unit.
- Sizing note for whoever takes SUBSTRATE-002's metal slice: `coeus-metal` is
  1 233 lines with **zero in-repo dependents** — no manifest outside the
  workspace member list names it, and the only code references are its own
  tests. It is a file-for-file copy of `coeus-rocm` (per-file diffs of 0, 0,
  0, 2, 17, 25 lines after normalizing the vendor token), and
  `coeus-hephaestus` already implements the whole op surface generically for
  `HephaestusBackend<P>`. The only content not reproducible from a ~56-line
  provider marker is one `fill_zero` override.

## ATLAS-OVERLAY-GEN-STALE-1 — Cross-repo path deps on member mainlines [arch] — todo (needs user decision)

- Owner: unclaimed; scope: `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`,
  and the member manifests listed below. **Held for a user decision** — see the
  conflict at the end.
- **My 2026-08-03 diagnosis on this item was wrong and is corrected here.** I
  filed it as "the generator is stale against the package renames". It is not.
  Run twice in a row the generator is byte-identical (`cmp` clean), and it emits
  the same 38-line reduction against the committed overlay each time. It is
  idempotent and its output is *correct*.
- The real cause: the generator derives the overlay from the **git**-dependency
  closure, and six members no longer declare git dependencies — they were
  migrated to cross-repo path dependencies. So the generator rightly stops
  emitting patches for them, and the committed overlay is what is stale,
  carrying dead entries (`apollo-nufft`, `apollo-sht`, `asclepius-coeus`,
  `athena-leto`, and an entire `[patch."…/coeus"]` section).
- Measured 2026-08-03, path deps that **escape their own repo** (intra-workspace
  **(CORRECTED below — this measured worktrees, not committed state.)**
  `../sibling` paths excluded by resolving each path against its repo root):
  athena 36, and 25 in a private consumer — those two are the only ones
  actually committed. The kwavers/helios/ritk/CFDrs counts in the original
  measurement were uncommitted worktree edits and are withdrawn.
- **Correction 2026-08-03.** My original figure of 163 across six members read
  working trees. Committed state across the whole stack is: **athena 36** (the
  sole tracked member carrying committed cross-repo path deps, and red on CI
  for exactly that), plus 25 in the untracked private consumer. Every other
  member's committed manifests are clean `git + version`.
- That shrinks the decision considerably: it is about athena, not about a
  stack-wide cutover. athena's `[patch]` at `Cargo.toml:119-120` plus its
  path deps are what keep its CI red.
- Method note for anyone re-measuring — this is the second time I generalized
  from worktree state (the first was the lockfile survey under
  ATLAS-PUB-LOCK-1). Under the overlay, working trees routinely diverge from
  HEAD. Always read `git show HEAD:<path>`, and for anything about how a
  consumer or runner sees the repo, clone it in isolation:
  `git clone --depth 1 file:///D:/atlas/repos/<name> /d/tmp/isolated/<name>`.
  athena 36, kwavers 31, helios 29, ritk 22, CFDrs 20, plus 25 in a private
  downstream consumer —
  **163 total**. Example: `repos/kwavers/Cargo.toml` → `../../repos/aequitas`.
- These landed deliberately in `b2ee610` ("Migrate kwavers/cfdrs/helios/ritk to
  local path deps", authored by a non-Claude agent). Two notes on that commit:
  its body claims the migration covers manifests whose recorded gitlinks do not
  in fact contain it, and it states plainly that it landed with builds still
  failing ("remaining build failures are pre-existing code errors").
- **The conflict, which is why this is not being fixed unilaterally.** Standing
  stack policy is that member manifests keep `git + version` sources and the
  root `[patch]` overlay owns local resolution — a member carrying path deps is
  unconsumable as a git dependency, and the two mechanisms now contradict each
  other. The mechanical fix is to convert all 163 back and regenerate. But that
  is a 6-repo revert of another agent's deliberate, stated intent, and three of
  those repos currently have live peer branches (`coeus` mid-publish-cycle,
  `CFDrs` on a codex branch, `ritk` on a feature branch). Reverting a peer's
  intentional migration at that blast radius is a call for the user, not for an
  autonomous tick.
- Whichever way it goes, one of the two mechanisms should be retired rather than
  left in contradiction: either the path deps convert back and the overlay stays
  authoritative, or the overlay is deliberately narrowed and the generator's
  freshness check updated so `generate` stops looking like a regression.
- **Concrete consequence found 2026-08-03: this breaks CI, not just theory.**
  `athena` has been red for five days with
  `failed to load source for dependency themis` / `unable to update
  /github/themis`. Its manifest carries a committed
  `[patch."https://github.com/ryancinsight/themis"] themis = { path = "../themis" }`
  (`athena/Cargo.toml:119-120`). That resolves inside the Atlas tree and cannot
  resolve on a runner that checks out one repo — which is exactly the property
  that makes a member unconsumable as a git dependency.
- So the cost of leaving this unresolved is now measurable: at least one member
  is permanently red, and any repo that gains cross-repo path deps joins it.
  athena is deliberately **not** fixed here — removing that `[patch]` is the
  decision this item is waiting on, and athena additionally needs the
  ATLAS-PUB-LOCK-1 lock repair, so its CI will not go green from either fix
  alone.
- Note for whoever measures this again: a naive `grep 'path = "\.\./'` is
  useless here — it counts ordinary intra-workspace sibling paths and reported
  473. Resolve each path against its repo root and keep only the escapes.


## ATLAS-ARCH-005 — Replace closed-set dyn dispatch in per-timestep paths [arch] — in-progress

- Owner: opencode-2026-08-05 (ADR phase delivered, ADR 0041; execution slice parked —
  both scope repos peer-held today: kwavers `refactor/retire-kwavers-optics`
  `e4e9966b6`, CFDrs `deps/eunomia-0.8`). scope: `repos/kwavers` first (largest), then
  `repos/CFDrs`.
  One operation family per claim.
- Outcome: dispatch-site counts are `kwavers` 665, `CFDrs` 352, `gaia` 104,
  `coeus` 98, `moirai` 83, `consus` 66. Sampling the kwavers solver shows the
  pattern is not type erasure of an open plugin set but vtable dispatch over
  closed design-time sets: `sources: &[Box<dyn Source>]` inside
  `forward/nonlinear/westervelt/update.rs` (evaluated per timestep),
  `boundary: Box<dyn Boundary>` held in the solver struct, plus `Box<dyn Signal>`
  and `Box<dyn Solver>`.
- Decision rule: a closed implementor set dispatched per timestep converts to an
  exhaustiveness-checked enum — static dispatch, still runtime-selectable, no
  vtable. Genuinely open plugin boundaries on cold paths keep `dyn` with the
  applicable exception annotated inline.
- Acceptance: per family, the count of `dyn` sites on the timestep path reaches
  zero; the enum is exhaustively matched with no catch-all arm; a criterion
  comparison on the affected kernel accompanies the change, since this is a
  performance-motivated claim and must carry performance evidence.
- Non-goals: mass-converting all 1 368 sites. Hot paths first, evidence per family.

## ATLAS-ARCH-008 — Replace pointer-scattered containers on traversal paths [patch] — in progress (2026-08-18)

- Owner: current session; scope for this increment is the root classifier and
  its focused tests, not provider source or the hotness-ranked conversions.
  The scanner currently traverses `repos/consus/worktrees/*`, so a peer lane is
  counted as a second provider source and makes the live site set depend on
  lane topology.
- **Current increment evidence:** the focused classifier suite is 44/44 after
  adding a lane-exclusion regression. The live scan is now 242 production and
  98 test/bench sites with zero `worktrees/` paths. The committed oracle still
  reports 35 additions and 36 removals because peer provider edits and line
  shifts are present in the shared tree; it is not regenerated from that
  unstable state.
- Outcome: 318 `Vec<Vec<_>>` occurrences across package sources, led by
  `consus-compression/src/chunking/iterator.rs` (10),
  `gaia/src/domain/topology/adjacency.rs` (8), and
  `coeus-autograd/src/ops/nn/loss/ctc.rs` (6). Adjacency and chunk iteration are
  prefetch-sensitive; a jagged per-row allocation defeats it.
- Acceptance: the contiguous form is a flat buffer plus an offset table
  (CSR-shaped) or an arena span, with a criterion comparison on the traversal
  showing the change is a win. A site where the jagged shape is genuinely correct
  is recorded as such rather than converted.
- **Evidence re-measured 2026-08-03; two of the three named sites are wrong.**
  Verify before claiming — as written this item would send someone to rewrite
  test code.
  - `consus-compression/src/chunking/iterator.rs` (listed as the worst, 10
    occurrences): **all 10 are test-local.** `#[cfg(test)] mod tests` opens at
    line 156 of a 400-line file and every occurrence is at lines 167-383, each
    a `let coords: Vec<Vec<usize>> = ChunkIterator::new(..).collect()`
    collecting an iterator's output for an assertion. That is not a container
    on a traversal path; it is a test binding, and converting it would be
    rewriting tests to suit a metric.
  - `gaia/src/domain/topology/adjacency.rs` (listed at 8): now **zero**
    occurrences. The file is 679 lines and no longer contains the pattern.
  - The raw stack-wide count is ~370, up from the recorded 318, so the
    headline number is not shrinking even though its named exemplars have
    evaporated — which is the signal that the count is measuring the pattern,
    not the defect.
- What the item still needs before it is claimable: a classifier that
  separates production containers from `#[cfg(test)]`-local and
  `tests/`/`benches/` bindings. I wrote one and do not trust it — it
  mis-classified `kwavers-math/.../lsqr/tests.rs` as production, so its
  per-repo split is not recorded here rather than recorded wrongly. The
  two corrections above were each confirmed by reading the file.
- Re-scoped acceptance: the deliverable is first a *correct site list* —
  production-only, ranked by traversal hotness rather than raw count — and
  only then the CSR conversions with their criterion evidence. A raw
  `Vec<Vec<` count is not a defect list.
- **Site list delivered 2026-08-03.** A classifier now separates production
  containers from `#[cfg(test)]`-guarded and `tests/`/`benches/`/`examples/`
  bindings, and it carries two self-checks derived from files read by hand —
  it refuses to print numbers unless it reproduces both. That gate earned its
  keep: the first version failed, because it matched only the bare
  `#[cfg(test)]` and the consus module is gated
  `#[cfg(all(test, feature = "alloc"))]`. Any cfg predicate carrying a bare
  `test` token now counts, with string literals stripped first so a
  `feature = "test-utils"` value cannot pose as the predicate.
- Verified totals: **297 production, 73 test/bench-local** (370 raw). So ~20%
  of the recorded 318 was never a defect.
- **There is no hotspot, and that changes how this item should be worked.**
  Production counts per repo are ritk 81, kwavers 70, CFDrs 46, gaia 37,
  consus 24, coeus 12, apollo 6, moirai 5, leto 2 — but the top *file* has 10
  (in a private downstream consumer, out of stack scope), the next has 6, and
  everything after is a tail of 4s and 3s across unrelated subsystems
  (`coeus-autograd/.../ctc.rs` 6; `ritk-vtk/.../poly_data.rs`,
  `ritk-filter/.../anti_alias_binary/solver.rs`,
  `cfd-optim/.../search/genetic.rs`, `consus/src/sync/mod.rs` 4 each).
  There is no "fix the top three files" increment available.
- Consequence for the acceptance oracle: ranking by *count* is worthless here.
  A claimant should pick sites by traversal hotness — profile first, per the
  measurement-first rule — and convert the ones that a profile implicates,
  recording the rest as correct-as-jagged. The classifier lives in the session
  scratchpad; it should be committed under `scripts/` if this item is claimed,
  since re-deriving it is the expensive part (toil automation).
- **Delivered 2026-08-05 — classifier committed, site list refreshed.**
  `scripts/atlas_scattered_containers_classify.py` is the committed,
  reproducible form (underscore-named and importable, matching the
  testable-script convention), with pytest coverage in
  `scripts/tests/test_atlas_scattered_containers_classify.py` (24 tests:
  production vs test/bench/example split, `#[cfg(test)]`/`mod tests`
  brace-depth tracking, comment/string/char/raw-literal stripping with
  char-vs-lifetime disambiguation and multiline-string state, `cfg(not(test))`
  and `feature = "test-utils"` exclusions, filename heuristics, semicolon-line
  leak guard, determinism). It scans only the `.gitmodules`-registered members via
  `atlas_stack.registered_members()`, so the git-ignored private consumer
  never surfaces. Refreshed verification totals on the 2026-08-05 tree:
  **260 production / 65 test-bench / 325 total**, per member — CFDrs 42/11,
  apollo 6/2, coeus 12/0, consus 20/15, gaia 34/2, kwavers 63/5, leto 3/13,
  mnemosyne 0/1, moirai 6/9, ritk 74/7. The delta vs the 2026-08-03 recording
  (297/73/370) is tree drift plus method differences: this implementation
  strips comments, string/char/raw literals and block comments before any
  matching (so a `feature = "test-utils"` value or a `"mod tests {"` template
  string cannot arm a predicate and commented `Vec<Vec<` sites are not
  counted), narrows the test-filename heuristic to `tests.rs`/`*_test.rs`/
  `bench.rs`-style names (so `test_utils.rs` helpers stay production), and
  emits root-relative site paths; the committed script is the reproducible
  oracle going forward. The production-only site list is
  regenerated with
  `python scripts/atlas_scattered_containers_classify.py --site-list
  scripts/oracles/arch-008-production-sites.txt` (see the gate bullet
  below). Ranking by traversal hotness
  (profile-first) and the conversions themselves remain the open work — this
  item stays `todo`.
- **First conversion delivered 2026-08-05 — moirai collective family.**
  `repos/moirai` `moirai-core/src/communication/collective.rs`:
  `CollectiveOps::{scatter,gather,all_to_all}` now build and traverse a
  CSR-shaped `ChunkedVec<T>` (contiguous flat buffer + chunk-offset table)
  instead of jagged `Vec<Vec<T>>`. Semantics preserved exactly (chunk tiling,
  all-to-all column truncation at the chunk count); the empty-input / zero-
  participant edge returns an empty buffer rather than the historical
  `chunks(0)` panic. Consumers were verified tests-only, so the signature
  change is contained. Criterion
  (`benchmarks/benches/collective_ops_comparison.rs`, `harness = false`,
  jagged baselines kept inline, 32/128 participants × 4096/8192 items):
  gather **~10–13×** faster (O(1) hand-off), traverse **~1.6×**, scatter
  **~1.1–2.2×**, all_to_all **~1.3–3.2×** — a win on every measured path.
  moirai-core gate: check 0, collective nextest 4/4 (round-trip, empty/
  zero-participant, all-to-all parity), strict clippy 0.
  `channel_fusion` per-channel buffers are recorded as **correct-as-jagged**:
  each channel grows and flushes independently, so a shared flat buffer would
  add reallocation complexity without a traversal win. `owned_chunks`
  (hybrid.rs) stays owned-per-worker by contract (parallel ownership model);
  it is a candidate only if its consumers move to borrowed chunks. The next
  conversion should be picked from a different repo family per the
  one-family-per-claim rule.
- **Oracle gate wired 2026-08-05 — the split can no longer drift silently.**
  `scripts/atlas_scattered_containers_classify.py --verify-oracle
  scripts/oracles/arch-008-production-sites.txt` re-verifies the current
  production split against the committed oracle (read-only; exit 0 = match,
  1 = drift, 2 = unreadable oracle), wired as `make verify-scattered-oracle`
  following the `fmt-check`/`board-lint` convention. `outputs/` is gitignored
  by design (derived state), so the oracle now lives at the tracked path
  `scripts/oracles/arch-008-production-sites.txt` and is regenerated
  deliberately with `--site-list` and committed in the same change that
  caused the drift. Oracle refresh after the moirai conversion:
  **256 production / 71 test-bench / 327 total** (per member — CFDrs 42/11,
  apollo 6/2, coeus 12/0, consus 20/15, gaia 34/2, kwavers 63/5, leto 3/13,
  mnemosyne 0/1, moirai 2/15, ritk 74/7). The sole delta vs the recorded
  260/65/325 is the moirai conversion: −4 production sites (the
  `collective.rs` family left the scattered set) and +6 test-local sites
  (the new parity tests build jagged vectors). The 2 remaining moirai
  production sites are `channel_fusion` and `owned_chunks`, both recorded
  correct-as-jagged / owned-by-contract above. Verify-mode coverage:
  `scripts/tests/test_atlas_scattered_containers_classify.py` gained
  oracle-parse, added/removed drift, blank/member-suffix tolerance, and CLI
  exit-code (0/1/2) tests (classifier suite now 32; full scripts suite 92 +
  20 subtests).
- **Spot-check 2026-08-05 — classifier matches a manual read.** Hand-verified
  the top per-member production files and the complete discrepancy set for
  ritk (74), kwavers (63), CFDrs (42): all 33 production sites in the top 3
  files per member match the oracle exactly (raw `Vec<Vec<` lines == oracle
  claims, same lines), and all 39 occurrences the classifier excluded from
  production were confirmed by hand to be comment/doc text (16 — stripped,
  never counted) or test/bench/example code (23 — counted test-local, e.g.
  the `#[cfg(test)]`-guarded `clahe_2d` in interpolate.rs:168 and the
  `#[cfg(test)] mod tests` VOF reconstruction.rs cases exercise the
  brace-depth path; `tests.rs`/`tests/`/`examples/` paths exercise the
  heuristics). Zero production code misclassified as test and zero test code
  counted as production. Read-only; no tree edits.
- **Spot-check 2026-08-05 — mid-count members + claimed-sites sweep; classifier
  extended; oracle corrected 256/71 → 250/77.** Hand-verified the six remaining
  members (gaia 34, consus 20, coeus 12, apollo 6, leto 3, mnemosyne 0) with
  the same discrepancy-set method: every top-file raw `Vec<Vec<` line matches
  the oracle claims (all 34 gaia, 20 consus, 12 coeus, 6 apollo, 3 leto
  claims), every excluded occurrence (doc comments, in-file `#[cfg(test)]` /
  `mod tests` regions, `tests/`/`examples/` paths) confirmed non-production,
  and a reverse stale-check confirmed all 75 mid-count claims point at live
  `Vec<Vec<` lines. The claimed-sites direction then surfaced a genuine
  classifier blind spot: it could not see **include-site gates**
  (`#[cfg(test)] mod <name>;` declared in a parent module) or bare
  `#[test]`/`proptest!` regions, so whole test-only files were misreported as
  production. The earlier top-member spot-check verified the excluded-direction
  only; the claimed-sites sweep here is what caught the remaining sites.
- **Classifier fix.** `compute_test_regions` now also treats `#[test]`
  attributes and `proptest! {` blocks as test regions, and `classify_file`
  gains `_is_include_gated`: it locates the file's `mod <name>;` declaration
  (`dir/mod.rs`, sibling `dir.rs`, `src/lib.rs`/`src/main.rs`, or crate-root
  `mod <dir>;` for `dir/mod.rs`) and checks the stacked attributes directly
  above it, stopping at the first non-attribute line so a cfg attribute of a
  *previous* declaration never leaks (the `boolean_csg` regression: its
  `#[cfg(test)]` belongs to the neighbouring `adversarial_tests_2`, and its
  claims are genuinely production). Files loaded under an arbitrary module
  name via `#[path = "..."]` (e.g. `#[cfg(test)] #[path = "tests_ply.rs"]
  mod tests;`) are covered by a per-member `#[path]`-declaration map keyed by
  the *resolved* target path (`#[path]` is relative to the declaring file's
  directory) — a basename key would collide on the many `mod.rs` modules and
  wrongly gate unrelated production files (caught live: the MGH reader, DICOM
  directory scanner and DICOM Association SCU `mod.rs` files are production
  and stay claimed). 11 new unit tests (classifier suite now 43) cover
  include-gated module, plain include, previous-declaration leak, dir module,
  `#[test]` fn, `#[test]` non-leak, `proptest!` block, and the `#[path]` map
  + stacked-attribute gate. Residual, deliberately-conservative blind spots
  (test code kept as production, never the reverse): a `mod foo;` nested
  inside an in-file `#[cfg(test)]` block of the parent, a `//` comment between
  the attribute and the `mod` declaration, `#[cfg_attr(test, ...)]`, and
  parenthesized `proptest!(...)`.
- **Corrected oracle: 250 production / 77 test-bench / 327 total** (was
  256/71 — total unchanged, pure reclassification). Six sites moved
  production → test-local, all hand-verified genuine test code: consus
  `reader_proptest.rs:151` and `tests_extra.rs:101` (include-gated), and ritk
  `tests_staple.rs:142,243` (include-gated) and `tests_ply.rs:89,123`
  (include-gated via stacked `#[path]` attribute, plus `#[test]` regions).
  Corrected per-member split: CFDrs 42/11, apollo 6/2, coeus 12/0, consus
  18/17, gaia 34/2, kwavers 63/5, leto 3/13, mnemosyne 0/1, moirai 2/15,
  ritk 70/11. Final independent verification: all 250 committed claims are
  live `Vec<Vec<` lines and none classify as test under the committed logic;
  `make verify-scattered-oracle` passes on the corrected oracle.
- **Second conversion 2026-08-05 — ritk-vtk Laplacian adjacency family.**
  `repos/ritk` `ritk-vtk/src/domain/filters/smooth.rs`: the smoothing
  filter's `build_adjacency`/`laplacian_step` now use a CSR-shaped
  `Adjacency` (contiguous `neighbors` buffer + per-vertex `offsets` table —
  the VTK `VtkCellArray` layout) instead of jagged `Vec<Vec<u32>>`. The
  build is jagged-free (degree count → prefix-sum offsets → direct flat fill
  → in-place sort+dedup per run), so the oracle site `smooth.rs:133`
  disappears rather than moves; the sorted/deduped layout is fully
  deterministic where the old `HashSet` build left neighbor order
  implementation-defined. Neighbor *sets* are unchanged, so filter results
  are preserved to within the existing 1e-5 test tolerance; a parity test
  pins the CSR runs against the sorted jagged reference (polygon + line
  edges, an isolated vertex, and a quad-grid interior vertex with its four
  edge-sharing neighbors sorted/deduped). `Adjacency` and `Adjacency::build`
  become documented public API (the only API change; `laplacian_step` stays
  private) so the criterion bench measures the production path. Criterion
  (`crates/ritk-vtk/benches/smooth_adjacency_comparison.rs`, `harness =
  false`, jagged baseline kept inline, 4096/16384-vertex quad grids): build
  **~7.8× at 4096 / ~8.5× at 16384** faster (857.7→110.5 µs / 3.523→0.415
  ms) — the CSR build replaces one `HashSet` allocation per vertex with a
  single flat buffer; traversal **~1.07× at 16384** (78.5→73.2 µs) and
  statistically flat at 4096, the short degree-4 runs amortizing the layout
  win — the honest headline is the build, which runs once per filter
  invocation while traversal runs once per iteration. Oracle regenerated to
  **249/78/327** (ritk 69/12): the smooth.rs production claim moved to the
  bench baseline, where the pre-conversion formulation lives by design
  (mirroring the moirai bench precedent). Gate: `ritk-vtk` nextest 258/258,
  warning-denied Clippy, fmt clean, `make verify-scattered-oracle` exit 0.
  The other named ritk families were assessed and deliberately left
  unclaimed this slice: `ritk-filter/.../anti_alias_binary/solver.rs`
  layers are a push-front/pop-front work-queue — CSR would turn every front
  insert into an O(n) memmove across all layers (**correct-as-jagged**),
  and `ritk-vtk poly_data.rs` cell arrays are the native CSR end state but a
  ~225-reference data-model migration that warrants its own dedicated claim.
- **Third conversion 2026-08-05 — Apollo CWT output buffer.**
  `repos/apollo/crates/apollo-wavelet/src/application/execution/plan/cwt.rs`
  now collects the row-major `(scales, signal_len)` coefficient matrix through
  `moirai::map_collect_index_with::<moirai::Adaptive>` into one flat buffer,
  then reshapes it into the existing `leto::Array2`. This removes the
  per-scale `Vec<Vec<f64>>` intermediate and its row allocations while
  preserving indexed output order, adaptive parallel execution, and the public
  `CwtCoefficients` API. The flattened dimension is checked with `checked_mul`
  and returns `CoefficientShapeMismatch` on overflow. The selected production
  site is gone rather than moved; no DWT coefficient API was changed because
  those vectors represent intentionally level-shaped detail bands and remain
  correct-as-jagged for this slice. Evidence: Apollo `cargo check -p
  apollo-wavelet`, rustfmt, strict Clippy, doctests, and `cargo nextest run -p
  apollo-wavelet --lib` **21/21** pass; `git diff --check` and the targeted
  no-`Vec<Vec<` residue scan are clean. The separate oracle gate reports the
  expected single stale claim at `cwt.rs:72` (current split **248 production /
  78 test-bench / 326 total**); oracle refresh is intentionally deferred because
  `scripts/atlas_scattered_containers_classify.py` and
  `scripts/oracles/arch-008-production-sites.txt` are pre-existing untracked
  artifacts owned by the concurrent root oracle stream. Re-run
  `--site-list` and `make verify-scattered-oracle` when that stream lands the
  derived artifacts.
- **Fourth conversion 2026-08-05 — Apollo prime-pair macro tables.**
  `repos/apollo/crates/apollo-fft-macros/src/prime_pair_tables.rs` now keeps
  expansion-time cosine/sine values in flat `Vec<f64>` buffers and chunks them
  only while emitting the unchanged fixed-size `[[T; H]; H]` token arrays. This
  removes the nested `Vec<Vec<f64>>` allocation and preserves row-major token
  order and the `PrimePairTable<N, H>` API. Zero-height inputs avoid
  `chunks_exact(0)`; zero `N` and `H × H` overflow return deliberate procedural
  macro compile errors. Evidence: macro/FFT checks, rustfmt, strict Clippy,
  doctests, and `cargo nextest run -p apollo-fft --lib` **394/394** pass;
  targeted diff and nested-vector residue checks are clean. The ARCH-008 oracle
  remains deferred exactly as recorded above because its classifier/oracle files
  are owned untracked artifacts in the concurrent root stream.
- **Site investigated and recorded correct-as-jagged 2026-08-07 — CFDrs
  spectral-element global assembly.** Converted
  `repos/CFDrs/crates/cfd-math/src/high_order/spectral/assembly.rs`
  (`GlobalAssembly.element_dofs` + `SpectralMesh.element_connectivity`,
  oracle sites `assembly.rs:14,25,140`) to CSR-shaped flat offset+index
  storage with the input shape preserved, then measured it. The criterion
  comparison (DOF-traversal read, 2 000×8 / 2 000×32 / 500×128 elements×DOFs)
  showed the flat buffer is consistently **~1.2–1.6× slower** than the jagged
  rows for the isolated read (CSR 3.5/7.2/6.2 µs vs jagged 2.1/6.0/5.5 µs):
  the fixed-size spectral rows are small and cache-resident either way, and
  the flat slice window pays two bounds checks the direct `Vec` row does not.
  The whole-`add_element_matrix` variant was dominated by unbounded COO
  accumulation (bench-design noise), not DOF access. The conversion was
  **reverted** and the site is recorded as correct-as-jagged: no traversal
  hotness, no criterion win — converting it would trade memory for a
  measurable slowdown. No oracle change needed (the sites remain live
  `Vec<Vec<` occurrences, correctly classified as production).
- **Fifth conversion 2026-08-07 — Leto L-BFGS ring buffer.**
  `repos/leto/crates/leto-ops/src/application/optimization/lbfgs.rs`
  `LbfgsMemory` now keeps correction pairs in two CSR-shaped flat ring
  buffers `s_buf`/`y_buf` (capacity `memory * n`) plus a scalar
  `rho_buf` (capacity `memory`) addressed by a single `head` index
  modulo `memory`, replacing the previous `Vec<Vec<f64>>` history
  with `Vec::remove(0)` eviction. The public API
  (`new`/`len`/`is_empty`/`direction`/`push`) is preserved; downstream
  `kwavers-solver` FWI callers (`elastic_fwi/inversion.rs`,
  `time_domain/quasi_newton.rs`) recompile against the new API without
  changes. The two-loop recursion in `direction` was re-derived against
  Nocedal & Wright Alg. 7.5: under the ring's logical-index convention
  (`pair_slot(0)` = newest, `pair_slot(k-1)` = oldest), the first pass
  walks `0..k` (newest→oldest) and the second pass `(0..k).rev()`
  (oldest→newest); a self-authored regression test
  (`direction_preserves_two_loop_after_wrap`) verifies value-semantic
  agreement with an independent jagged-reference implementation after a
  full ring wrap, and a saturation test verifies oldest-pair eviction.
  Criterion baseline comparison over the acceptance-oracle grid
  `{8,32}×{100,1000}` (median [lo hi], µs):

  | config | ring (new) | jagged (baseline) |
  |---|---|---|
  | m8_n100   | 1.71 [1.65 1.79]  | 1.78 [1.71 1.88] |
  | m32_n100  | 6.68 [6.31 7.04]  | 7.48 [7.14 7.79] |
  | m8_n1000  | 15.42 [14.61 16.24] | 16.36 [15.79 16.87] |
  | m32_n1000 | 75.00 [71.45 79.08] | 66.19 [63.35 70.11] |

  The flat ring wins at small dim (≤+13% over jagged, fewer allocations),
  is parity at `m8_n1000` (memory traffic dominates over allocation
  savings), and is **~13% slower** at `m32_n1000`: the large memory plus
  large dim regime has the ring doing `% memory` slot resolution per
  two-loop step against two big contiguous buffers while jagged has
  `memory` individual `Vec` allocations with one prefetcher-tight inner
  scan per row. The conversion's primary win is allocation/eviction
  elimination (no `Vec::remove(0)`, one allocation at construction
  instead of per-`push`), not raw throughput at high `m × n` — that is
  the honest baseline and is recorded here per the performance gate.
  Evidence: `cargo nextest run -p leto-ops --lib` **178/178** (176
  baseline + 2 new regression tests), `cargo test --doc -p leto-ops`
  20/20 + 1 ignored, `cargo clippy -p leto-ops --lib -- -D warnings`
  clean, `cargo fmt -p leto-ops -- --check` clean,
  `cargo check -p kwavers-solver --no-default-features` clean. The
  criterion bench `crates/leto-ops/benches/lbfgs.rs` is registered with
  `harness = false` and smoke-runs in single-iteration mode (`-- --test`)
  within the test budget; full timing runs fit the 300s/binary budget.
- **Delivery**: leto PR #96 (`fix/leto-ops-lbfgs-ring-buffer`), commit
  `1ed166a`, branch pushed to origin. **Not merged — blocked on a leto CI
  infrastructure defect at `db9a63c` (origin/main HEAD)**: Codex's Aug-7
  commit replaced the `git = "..."` workspace declarations for `mnemosyne`/
  `moirai`/`hermes-simd`/`eunomia`/`aequitas`/`themis` with `path =
  "../..."` for local meta-repo convenience, which resolves locally (meta-
  repo `.cargo/config.toml` `[patch]` overlay redirects the URL sources to
  local paths either way) but is unresolvable in leto's standalone CI
  checkout (`cargo metadata` fails to read `../aequitas/Cargo.toml`).
  Pre-existing in main, unrelated to this PR — leto's prior main CI run was
  already red for the same reason. Codex's `LETO-INTO-ITERATOR-1` dirty
  state is present in the leto working tree iterating on `leto/array.rs`,
  `leto/src/application/iter/*`, `leto/src/lib.rs`, `leto/tests/core/
  iteration.rs`, plus unrelated `leto-ops/{lu_symbolic.rs, sparse/mod.rs,
  parallel.rs, lib.rs}` files — the workspace `Cargo.toml` is theirs by
  precedent and outside the file-disjoint scope of this lbfgs slice.
  Per `concurrent_agents: Contention response order`, PR #96 stays open
  with the peer's landing as its re-open trigger. **Re-open trigger**:
  leto CI on main turns green (Codex lands the CI fix forward), OR a
  future disjoint slice puts me in a position where
  `repos/leto/Cargo.toml` workspace section falls under my scope.
- **Out-of-scope finding recorded** (kwavers-math `optimization/lbfgs.rs`
  is a full duplicate `LbfgsMemory` implementation, not the re-export the
  ATLAS-MATH-SSOT-CONSOLIDATION-1 Lane B residual table records; see Lane
  B residual (5)). Not converted in this slice: out of the leto-local
  file-disjoint scope, peer-active territory.
- **Sixth conversion 2026-08-08 — consus-zarr chunk selection indices.**
  `repos/consus` `consus-zarr/src/chunk/ops.rs` `selection_indices`
  (`Vec<Vec<u64>>`, one allocation per selection dimension) is replaced by a
  CSR-shaped `SelectionIndices` (`flat: Vec<u64>` contiguous buffer +
  `offsets: Vec<usize>` offset table) built once per read/write call; both
  copy helpers (`copy_chunk_selection_to_output`, `copy_selection_input_to_chunk`)
  hoist `dims: Vec<&[u64]>` per call so the traversal hot loop does one
  indirection (`dims[dim][selection_position[dim]]`) instead of two, and all
  three call sites (`read_array`, `write_array_selection`, `read_array_sharded`)
  use the same `SelectionIndices::build`. Criterion
  (`crates/consus-zarr/benches/zarr_selection_copy.rs`, `harness = false`,
  faithful jagged replica of the non-sharded `read_array` kept inline as a
  baseline; byte-parity assertion pins the replica to production output
  before timing; 2d 256×256 / 2d 512×512 / 3d 64³ strided×2 selections on a
  populated `InMemoryStore`): CSR is a win on every case — **−4.7% /
  −6.5% / −10.9% time vs jagged** (criterion `change`, p < 0.05; within-run
  medians 6.50/25.75/33.8 ms vs 6.96/26.40/36.6 ms). Gate: `cargo clippy -p
  consus-zarr --all-features --all-targets -- -D warnings` clean, nextest
  `303/303`, doctests clean, fmt clean; CI `--all-features` clippy+check
  green on PR #13. **Oracle refreshed to 243 production / 80 test-bench /
  323 total**: the consus-zarr `ops.rs` production site is gone; coeus
  `ctc.rs` 408-410 → 353-355 (line shift from a peer PR, same sites); leto
  `lbfgs.rs:79,80` added (genuine `Vec<Vec<f64>>` in `LbfgsMemory`,
  hand-verified; the conversion's ring buffers are flat so the site moved,
  it did not stay). `--verify-oracle` exit 0 on the refreshed oracle.
  Delivery: consus PR #13, branch `refactor/consus-zarr-csr-selection-indices`
  (commits `3ce79b0` conversion + `d3d5b19` mechanical rustfmt of two
  pre-existing-dirty consus-core book examples that had kept the
  workspace-wide Format CI job red at HEAD, blocking the Check job for every
  PR). Residual: pre-existing untracked meta-repo scratch (`.commandcode/`,
  `libtest_*.rlib`) and peer-held `version-guard`/`gitlink-coherence` changes
  are untouched.

## ATLAS-PRIVACY-NAMING-1 — Private consumer named throughout stack artifacts [chore] — todo (needs user decision)

- Owner: unclaimed; scope: `backlog.md`, `gap_audit.md`,
  `docs/adr/0036-neuroimaging-and-mr-ownership.md`, and
  `PATH_DEP_AUDIT_001_ENTRY.md`.
- The consumer at `repos/leoneuro-rs/` is a private external org's code drop:
  gitignored at `.gitignore:60`, no `.gitmodules` entry, no
  `submodule.*` keys, remote on a different GitHub org. ATLAS-GIT-HYGIENE-001
  confirmed that arrangement is deliberate design, not a stale rule.
- Standing policy for such a consumer is that it stays out of the stack map
  entirely — the gitignore entry is the only sanctioned trace, and upstream
  items it motivates cite "a downstream consumer" generically. Its name is
  currently in four tracked artifacts, including an ADR and the closed
  audit ledger, across roughly a dozen references.
- I redacted only the one reference I added myself (in
  ATLAS-OVERLAY-GEN-STALE-1's measurement). The rest is **not** being swept
  unilaterally: several sit in closed items' audit trails and an Accepted ADR,
  where a blind rename would break the traceability those records exist to
  provide, and peers reference those item names.
- The decision needed: does this consumer's name count as confidential for
  artifact purposes? If yes, the sweep should be one deliberate pass that
  rewrites references generically and preserves each record's meaning
  (git history keeps the old text either way — the redaction is forward-only).
  If no, the standing rule should be recorded as not applying here, so this
  keeps being re-raised.
- Adjacent, unrelated to the naming question: `PATH_DEP_AUDIT_001_ENTRY.md` sits
  at the repository root, where the root-manifest rule admits no loose report
  files. Its content belongs in the closed item it serves.

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

## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — in-progress

- Owner: current session (Atlas coordination); scope: reusable-workflow
  evidence and the CFDrs caller's backend input. Other provider caller files
  and peer-owned working-tree changes are excluded.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5.
- Outcome: each book workflow becomes a caller of
  `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only
  `output-path`.
- **Closed sub-item (2026-07-28):** `ritk` now joins the Atlas cross-book gate —
  `.github/workflows/docs.yml` runs the strict detector and an `mdbook build`
  over all four books. The same change dropped the three per-book HTML artefact
  uploads, leaving `detector.log` as the only retained artefact; that is a
  deliberate narrowing, not a regression, since Pages deployment is the book's
  delivery path and the artefacts were diagnostic only.
- Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books
  (ATLAS-BOOK-001).
- Acceptance: four callers, each passing its audited output path
  (`target/book/cfdrs`, `target/book/helios`, `target/book`,
  `target/book/ritk`); each package's Pages deployment succeeds once through the
  shared workflow.
- **Hosted residual 2026-08-13, closed:** CFDrs run `31716368183` failed during
  the shared build because `book.toml` declares a non-optional
  `[output.linkcheck2]` renderer and the pinned Atlas workflow `d875348` did
  not install it. Root commits `042e448` and `4c31dd7` added the opt-in
  installer and pinned the stable Rust toolchain before `cargo install`. CFDrs
  PRs #339/#340 merged the full root pin, `mdbook-linkcheck2-version: 0.12.2`,
  and `target/book/cfdrs/html`; obsolete PR #338 was closed after verification.
- Helios `31716457700` and Kwavers `31716399219` now have successful Deploy
  mdBook conclusions at their recorded provider heads. RITK `31716974169`
  remains queued at the historical head `f98a9191`, so RITK still requires a
  current-pin run after its caller PR merges. The four current caller PRs must
  still merge and produce fresh deployment evidence before this item closes.

## ATLAS-PUB-003 — Register trusted publishers and remove the unused PyPI token [chore] — todo

- Owner: user-gated — registry and GitHub settings changes are Ask-User actions;
  an agent prepares the values and verifies the result, it does not perform the
  registration.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §4.
- Outcome: every publishing package has a trusted publisher registered on the
  target registry, so no long-lived registry credential exists anywhere in the
  stack. Values per package: owner `ryancinsight`; repository = the package
  repository; workflow filename = the **caller's** filename
  (`rust-release.yml` / `python-release.yml`), because the OIDC claim carries the
  caller's identity, not the Atlas reusable workflow's; environment `crates-io` /
  `pypi`.
- Registry verification 2026-07-28: crates.io **cannot bootstrap** a new crate
  through trusted publishing — the crate must already exist and the first publish
  requires an API token. PyPI **can** bootstrap through a pending publisher
  configured under the account sidebar.
- **Registry state re-verified 2026-09-04; the 2026-07-28 line "no Atlas crate is
  published" is stale.** On crates.io: `eunomia` 0.8.0 and `aequitas` 0.2.0 are
  published from this account, both dated 2026-08-02. On PyPI, **eight of the ten
  binding distributions are live**: `cfd-python` 0.1.6, `apollo-fft` 0.2.0,
  `coeus-python` 0.9.0, `consus-python` 0.1.0, `hephaestus-python` 0.18.0,
  `kwavers-python` 0.1.0, `leto-python` 0.41.0, `moirai-python` 0.4.0. Not
  published: `helios-python` and `ritk`. So the bootstrap question is settled for
  most of the stack and the open work is metadata quality, not first publication
  — see `#python-blank-pypi-pages`.
- Sequence per crate, therefore: (1) resolve its registry name (ATLAS-PUB-006 for
  the twelve collisions); (2) one manual publish from the local Cargo credential
  store, in workspace dependency order; (3) register the trusted publisher;
  (4) enable trusted-publishing-only enforcement. PyPI distributions skip step 2.
- Acceptance: one trusted-publishing release succeeds per package; the API token
  in the `pypi` environment is deleted afterwards; trusted-publishing-only
  enforcement is enabled in each registry's settings once its pipeline is proven.
- Residual risk: an unregistered package fails closed at the auth step. That is
  the intended failure mode, not a regression. A pending PyPI publisher does not
  reserve the project name until first use, so a name can be lost in between.

## ATLAS-PUB-006 — Stand up one facade crate per package [minor] — todo

- Owner: unclaimed; scope: one package per claim, in that package's repository.
  The `mnemosyne-core` rename is a cross-repo co-evolution unit and is claimed as
  a single item spanning `mnemosyne`, `leto`, `hephaestus`, and `moirai`.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md).
  Naming is settled; nothing here waits on a user answer.
- Outcome: every package presents one facade crate that re-exports its
  sub-crates, so a user depends on `coeus`, not `coeus-core` — the shape `burn`,
  `bevy`, and `polars` use. The facade holds no logic: re-exports with
  `#[doc(inline)]`, feature gates selecting optional backend sub-crates, and the
  crate-level overview. Lockstep versioning at the workspace version.
- Audit 2026-07-28 — 14 of 25 packages cannot present a facade today:
  - **author a facade** (workspace root is virtual, no entry crate exists):
    `apollo` → `apollo-transforms`, `CFDrs` → `cfdrs`, `coeus` → `coeus`,
    `helios` → `helios-radiation`, ~~`hephaestus` → `hephaestus`~~ **delivered**,
    `ritk` → `ritk`;
  - `hephaestus` facade landed in `repos/hephaestus/crates/hephaestus`
    (`bf24b87`): flat `#[doc(inline)]` re-export of the contract layer, backends
    under `hephaestus::{wgpu,cuda,rocm,metal}` behind features, no backend
    enabled by default (a default backend would make every trait consumer pull a
    device stack, and `cuda`/`rocm` need vendor toolkits at build time). Two
    design facts worth carrying to the remaining five:
    `default-features = false` cannot override a workspace-inherited dependency,
    so a facade declares its contract-layer dep directly; and weak feature refs
    (`dep?/feature`) are required so forwarding `parallel` does not silently
    enable an unrequested backend.
  - Verification complete — all four configurations pass: default `cargo check`,
    `--no-default-features`, the doctest, and `--features wgpu,decomposition,sparse`
    (11 m 32 s, queued behind a peer's build-directory lock). The `bf24b87`
    commit message recorded the wgpu set as unconfirmed because it was still
    building at commit time; this entry supersedes that.
  - Evidence limit: those checks ran against a working tree carrying a peer's
    uncommitted edits to `hephaestus-core/src/{lib.rs,domain/vector.rs}` and
    `hephaestus-wgpu/src/application/vector/mod.rs`. They prove the facade
    compiles against the tree as it stood, not against committed state. The glob
    re-export is robust to surface additions, but re-verify on a clean tree once
    that peer work lands.
  - Not verified: that a backend is unnameable without its feature. That follows
    directly from `#[cfg(feature = ...)]` on the re-export, and a `compile_fail`
    doctest asserting it would itself pass or fail depending on which features
    the test run enables — a fragile test of language semantics rather than of
    this contract, so none was added.
  - **flip `publish`** (facade exists, excluded from publishing): `aequitas`,
    `asclepius`, `horae`, `hermes-simd` — names already free;
  - **rename and flip `publish`**: `harmonia` → `harmonia-coupling`,
    `hyperion` → `hyperion-photon`, `moirai` → `moirai-runtime`,
    `proteus` → `proteus-materials`;
  - **rename only** (publishable under a colliding name): `athena` →
    `athena-solvers`, `gaia` → `gaia-geometry`, `mnemosyne` →
    `mnemosyne-alloc`, `themis` → `themis-placement`, `tyche` → `tyche-uq`;
  - **ready, no action**: `consus`, `eunomia`, `iris`, `kwavers`, `leto`,
    `melinoe`.
- Non-goals: repository names, submodule paths, directory names, module paths,
  and the classical-name mapping in the stack README. This is registry identity
  only. Also out of scope: negotiating a colliding name from its current owner —
  permitted, but no publish waits on it (ADR 0037 §7).
- Acceptance per package: the facade's `src/lib.rs` contains no logic; `cargo doc`
  shows re-exported items inline at facade paths; `--no-default-features` builds
  and no backend is reachable without its feature; `cargo publish --dry-run`
  passes after the sub-crates; the facade name returns 404 from the registry
  immediately before first publish, since availability decays.
- Non-blocking: ATLAS-PUB-001, -002, -004, and -005 proceed independently — a
  caller passes a package name, so every rename here is a manifest change.
- **Correction 2026-07-28 — do not flip `publish = false` ahead of dependencies.**
  An earlier reading of this item treated the eight guards as oversights. They are
  correct ordering guards: `cargo package` on `aequitas` fails with
  `no matching package named 'eunomia' found`, because a crate can only publish
  once its first-party dependencies are on the registry. Cargo *does* rewrite a
  `{ version, git }` dependency to a registry dependency, so git sources are not
  the blocker (`hermes-simd`'s manifest comment overstates it) — dependency order
  is. Each flip is the final step of that crate's own bootstrap publish, in the
  order `scripts/publish-order.py` derives. Four flips were attempted and reverted
  on this evidence; see [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §4.
- **Registry re-measure 2026-08-24 — README is stale, and the naming diverged from
  ADR 0037 in four places.** A live crates.io check plus the committed manifests
  correct the record:
  - **Already published (user's crates):** `aequitas` 0.2.0, `eunomia` 0.8.0,
    `asclepius` 0.1.0, `leto`+`leto-ops` 0.42.0, `melinoe` 0.9.0, `apollo-fft`
    0.26.0, `apollo-fft-macros` 0.2.0, `moirai-core`+`runtime` 0.5.0,
    `coeus-core`+`tensor`+`ops` 0.10.0, `mnemosyne-core` 0.2.0, `mnemosyne-heap`
    0.4.0, `themis` 0.14.0, `tyche-core` 0.2.0, `gaia-mesh` 0.4.0, `hermes-simd`
    0.6.0, `hephaestus-core`+`host`+`wgpu` 0.19.0, `ritk-core` 0.10.0,
    `ritk-image` 0.3.0, `consus` 0.1.0. The README line "No Atlas crate is
    published yet" (line 1084) is false and must be corrected.
  - **Naming deviations from ADR 0037, found in the manifests (not the README):**
    - athena's facade is `athena-krylov` (`[lib] name = "athena"`, `publish =
      true`), not `athena-solvers` as the README table lists.
    - iris's package is `iris-viz`, not `iris`; gaia's is `gaia-mesh` (already
      published 0.4.0), not `gaia-geometry`.
    - themis's package is `themis-topology` (`[lib] name = "themis"`, publishable),
      not `themis-placement`; `leto` publishes under the bare name 0.42.0.
    - tyche root is `publish = false`; mnemosyne root publish is unset.
  - **Third-party name collisions confirmed:** `hyperion` (patrickisgreige
    LSystem), `proteus` (rust-playground JSON), `harmonia` (sogh music theory),
    `gaia` (ucarion terrain), `mnemosyne-core` (bballer03 JVM analyzer), `athena`
    (unrelated). All five unblocker repos (hyperion, proteus, harmonia, horae,
    asclepius) are clean at their recorded gitlinks and `publish = false`.
  - **The unblocker chain is the critical path:** proteus → `proteus-materials`,
    hyperion → `hyperion-photon` (repoint its `proteus` dep), horae (name free),
    harmonia → `harmonia-coupling` (repoint `horae`+`athena-core` deps), then
    asclepius-coeus; athena's family must publish before harmonia.
  - **Delivery 2026-08-25 — first link merged across the stack; publish itself
    still pending.** All five PRs merged to their default branches:
    proteus #19 (`cd93e67`, later main `cb00193`), CFDrs #371 (`5ebbf1f`),
    hyperion #25 (`017a669`), kwavers #637 (`f5a996c` → main `cf5852f`),
    helios #71 (`c2cf177`). Atlas gitlinks advanced in `5c9efcac8` (+ hermes
    `4a1228ce`); overlay regenerated (44 sections, stack aligned);
    `atlas-provider-integration-audit.py --exact-heads` green.
  - **Lockfile lesson (kwavers/helios):** a committed lockfile must be generated
    *without* the Atlas overlay — the overlay's `[patch]` redirects strip the
    git `source =` lines from lock entries and inject `[[patch.unused]]`
    sections, both of which break CI's `--locked` resolution. Helios now enforces
    this at push time via its pre-push hook (`scripts/lockfile.py --regenerate`).
    Remaining: the actual `cargo publish` of `proteus-mat` (release authority),
    then the next links: hyperion → `hyperion-ph`, horae, harmonia →
    `harmonia-cpl`.
- Peer-held at this revision, so not claimable without a staleness sweep:
  `coeus` (`codex/coeus-error-function-parity`, 24 dirty), `ritk`
  (`codex/docs-ritk-n4-figure-only`, 11 dirty, active), `leto`
  (`codex/leto-real-sparse-lu`, 25 dirty), `mnemosyne`
  (`codex/mnemosyne-tier-selection`, clean). The `coeus` facade — the flagship
  case for this item — is among them.

## ATLAS-PUB-008 — Audit facade names immediately before each first publish [chore] — todo

- Owner: unclaimed; scope: the pre-publish check only.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §3,
  verification item 1.
- Outcome: name availability is a point-in-time observation and decays — 165 of
  173 names were free on 2026-07-28, and first-come means any of them can be
  claimed by a third party before the stack publishes. Each first publish
  re-checks its own name.
- Acceptance: `GET /api/v1/crates/<name>` returns 404 immediately before the
  publish, recorded in the release evidence. A collision discovered here is
  resolved by ADR 0037 §3's rule, not by an ad-hoc name.

## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — in progress

- Owner: current Atlas session; active claim: Iris; scope: one book per claim,
  in the owning repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- Outcome: every published book runs `mdbook test` in CI so chapters cannot rot.
  The shared workflow defaults `mdbook-test` to `false` as a staging mechanism,
  not an accepted end state. The committed provider defaults currently have
  seventeen shared callers plus Gaia's direct command gate; the six named
  residual callers remain untested until their samples compile.
- Claim status (updated 2026-08-20):
  - **melinoe** — DONE: all fenced samples compilable; blocks referencing the
    crate carry `extern crate melinoe;` and link through a staged plain-named
    rlib (`mdbook test --library-path`), signature illustrations `ignore`d, the
    cross-brand rejection sample `compile_fail`; caller passes `mdbook-test:
    true` + `cargo-package: melinoe`; the shared workflow's broken
    `RUSTDOCFLAGS` mechanism replaced with the staging + `--library-path` path.
    Merged via melinoe PR #11; main CI green (all 11 chapters tested), Pages
    deploy green; workflow fix on atlas main (`70c6c6b`, PR #100) makes the
    caller's full-SHA pin durable.
  - **eunomia** — DONE: caller passes `mdbook-test: true` and its hosted book
    gate is part of the provider's merged workflow.
  - **helios** — OPEN: H-103. The current book contains illustrative Rust
    fragments that fail direct `mdbook test docs/book` because they omit setup,
    use unresolved provider imports, or fence diagrams/commands as Rust. H-102
    repaired source-change triggers and enabled linkcheck2; H-103 must convert
    the snippets before the caller can pass `mdbook-test: true`.
  - **iris** — LANDED at provider `9672fc0`: the Pages caller pins the shared
    workflow fix `1fcd17c` and enables `mdbook-test: true`, Rust `1.97.0`, and
    `cargo-package: iris-viz`; the
    included example declares `extern crate iris`, and the stack-position
    topology diagram is fenced as `text`. Local format, locked all-target
    check, Clippy, nextest (`17/17`), doctests (`3/3`), package verification,
    `mdbook build`, and `mdbook test` pass. Push-triggered hosted runs are
    `32332860859` (CI), `32332861158` (Deploy mdBook), and `32332859993`
    (Pages build/deployment) remain queued at the time of recording. The prior
    run at `8224dba` exposed the package/library-name mismatch and was replaced
    by this explicit-crate revision. Peer-owned Iris lockfile work remains
    untouched.
- Acceptance per book: samples compile against the package; the caller passes
  `mdbook-test: true` and, where samples need providers, `atlas-ref`; the flip
  commit demonstrates the gate failing on a deliberately broken sample before
  landing green.
- Dependencies: ATLAS-PUB-002 for that package.

## ATLAS-MODALITY-003 — Optical-transport and RF/EM promotion watchpoint [arch] — blocked

- Owner: unclaimed; scope: watchpoint only — no edits until the trigger fires.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §1, §2, §6.
- Blocker: promotion gate conditions 1, 4, and 6 are unmet. Source audit
  2026-07-27: Kwavers is the sole consumer of the diffusion/Monte-Carlo-RTE
  optical transport solvers (CFDrs has no radiative/optical/photon module;
  ritk has none; Helios consumes Hyperion at MeV, a different regime). No RF
  integrator or second electromagnetics consumer exists.
- Re-open trigger: a second production consumer can delete a matching transport
  implementation in the extraction change. At that point the target is
  `hyperion-transport` as a second crate in a promoted Hyperion workspace — not
  a new package — so the `no_std` law crate keeps its dependency set and Helios
  and CFDrs inherit no array substrate.
- Standing note: sonoluminescence (3 006 LOC) and photoacoustics (653 LOC) are
  Kwavers-intrinsic and are excluded from any extraction scope. A photomedicine
  integrator peer to Helios is a separate, demand-gated decision and is out of
  scope here.
- Refinement 2026-07-28 —
  [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §5: "RF" names two
  unrelated concerns and this watchpoint covers only the first. RF power
  deposition and SAR belong on the shared deposition spine (ATLAS-MODALITY-002),
  where the transport stage is a modality slot and the stages behind it are
  shared. RF at the Larmor frequency for spatial encoding belongs to MR
  acquisition simulation, which is a closed, demand-gated *integrator* question —
  not part of this trigger and not a RITK concern. A proposal that merges the two
  is rejected on bounded-context grounds before the gate is even applied.

## ATLAS-OVERLAY-005 — Clear first-party rev pins across the stack [patch] — in-progress

- Owner: session-808504af. Decision: pin discipline (`architecture_scoping`) —
  a `rev =` is quarantine with a removal trigger, not a durable source form.
- Root cause: a rev-qualified git source is a **distinct package** to Cargo, so
  the stack `[patch]` overlay — which matches the bare URL — can never unify it.
  Sixteen first-party pins had accumulated across five repos at three different
  `aequitas` commits and two `eunomia` commits, so any crate reaching a provider
  by both forms received two incompatible copies of the same trait. Hyperion
  could not multiply two `Quantity` values for exactly this reason.
- ✅ Cleared and pushed: proteus `9a8655d` (also restored its manifest from a
  local path-dep leak to git+version), asclepius `ccffb6b`, tyche `996b649`,
  kwavers `df9008d93`.
- **Current residual**: `python scripts/atlas-stack-overlay.py check` now
  reports one coherence defect: Athena's peer-dirty checkout is three commits
  behind `origin/main` and its lock still pins the five-package Hermes
  `0.6.0` closure while the local provider is `0.7.0`. Athena is outside this
  named provider set and is not edited through the Atlas integration slice.
  The former CFDrs requirement lag is cleared at the current provider closure;
  re-run the check after CFDrs merges and when Athena's own work is
  reconciled.
- **Mechanism worth mechanizing**: depinning alone is insufficient. Every lock
  move needs `python scripts/atlas-stack-overlay.py generate` to re-derive the
  patch block, otherwise the graph keeps a local-vs-git split. This is the
  mechanism behind the recurring "local X cannot replace git-sourced Y" failures
  on this board. `atlas-stack-overlay.py check` already exits nonzero on lag, so
  wiring it into CI would catch the class at the source.
- Evidence: `cargo tree -d` in kwavers reports no duplicate first-party crates;
  the current overlay check provides the two residuals above rather than an
  aligned result.

## ATLAS-OVERLAY-004 — Worktree sprawl breaks stack dependency resolution [patch] — in-progress

- Owner: unclaimed; scope: `worktrees/`, the root `.cargo/config.toml`, and the
  13 lane-local `.cargo/config.toml` files. **Not** the lane branches' source.
- Blocker evidence (2026-07-27): `cargo check -p kwavers-physics` fails before
  compiling anything:
  - `failed to select a version for smallvec` — `hephaestus-wgpu v0.18.0` at
    `worktrees/hephaestus-unary-math-parity` requires `^1.15.2`; the kwavers lock
    pins `1.15.1`.
  - `cargo update -p smallvec --precise 1.15.2` then fails harder:
    `package collision in the lockfile: packages aequitas v0.1.0
    (D:/atlas/worktrees/aequitas) and aequitas v0.1.0
    (D:/atlas/worktrees/aequitas-energy-temperature) are different, but only
    one can be written to lockfile unambiguously`.
- Two distinct defects behind it:
  1. ✅ **resolved 2026-07-28** — `worktrees/aequitas` was an **orphaned linked
     worktree**, not a standalone clone: its `.git` file pointed at
     `repos/aequitas/.git/worktrees/aequitas`, whose admin directory had been
     pruned, leaving the checkout on disk with no git registration. Cargo still
     discovered it as a path source, giving two providers for `aequitas v0.1.0`.
     Contents were byte-identical to `repos/aequitas` (`diff -r` clean excluding
     `target`, `Cargo.lock`, `.git`), so nothing unique was lost. Removed with
     user authorization; `git worktree prune` run. `cargo check` across
     kwavers-physics and kwavers-solver resolves again, and the `smallvec`
     conflict cleared with it.
  2. **13 lane-local `.cargo/config.toml` files.** Config-layer ownership
     (`performance_engineering`) puts `target-dir` and the `[patch]` overlay at
     the stack root only; a nested config re-declaring either forks resolution
     and, as here, resolves a relative provider path into a second copy.
- Also: `worktrees/` holds 28 entries against a documented bound of one main
  tree plus one lane per repository. aequitas, coeus, hephaestus, kwavers, and
  ritk each have two or more.
- Acceptance: `cargo check -p kwavers-physics` resolves; `git worktree list` per
  repo is within bound; no lane-local `.cargo/config.toml` re-declares
  `target-dir` or `[patch]`; `worktrees/aequitas` removed after confirming no
  unique commits.
- **Ask-User gate**: removing `worktrees/aequitas` and other agents' lane
  directories is destructive to possibly-live peer setups. Confirm before
  deleting rather than reconciling unilaterally.

## ATLAS-DOWNSTREAM-COORDINATION-001 — Notify LeoNeuro-INC maintainers about local leoneuro-rs `50bfcd9` [chore] — todo

- Owner: unclaimed; scope: out-of-band coordination with the
  LeoNeuro-INC organization (separate GitHub org, NOT ryancinsight).
  No atlas-side edits in this scope.
- Outcome: the leoneuro-rs `50bfcd9` commit ("build(leoneuro-rs):
  Apply round-6a atlas-root path resolution — GRAND_TOTAL 0 across
  atlas") lives locally at `/d/atlas/repos/leoneuro-rs/` on the
  branch `codex/sim-ct-medium`. After atlas's closure cycle dropped
  the bogus 160000 gitlink in commit `d6827c2`, atlas parent no
  longer tracks leoneuro-rs's HEAD; the LeoNeuro-INC maintainers
  can land `50bfcd9` to their own org
  (`https://github.com/LeoNeuro-INC/leoneuro-rs.git`) on their own
  schedule via their own CI/dispatch pipeline.
- Acceptance: a downstream LeoNeuro-INC maintainer receives a short
  note pointing at the local SHA (`50bfcd9`) and the atlas-side
  commit history (see `D:/atlas/PATH_DEP_AUDIT_001_ENTRY.md` STEP D
  push-handoff paragraph for the handoff context); the
  LeoNeuro-INC team decides whether to fast-forward their `main`
  to `50bfcd9` or to cherry-pick from the local branch.
- Method: out-of-band contact through the existing LeoNeuro-INC
  internal channels; the atlas-side convey is a one-line pointer
  (no technical payload required). The atlas-side documentation
  states this deferral, but **no atlas code or Cargo.toml changes**
  are part of this ticket. The `50bfcd9` commit is preserved on the
  leoneuro-rs local branch (`codex/sim-ct-medium`) until the
  LeoNeuro-INC team decides its disposition.
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27)
  STEP D push-handoff paragraph codifies the deferral as
  documentation; this ticket is the corresponding **owner-assigned**
  follow-up so the deferral doesn't drift unowned. NAME SEMANTIC
  NOTE: "downstream" in this title refers to LeoNeuro-INC as
  downstream maintainer of the `50bfcd9` commit; this is distinct
  from atlas-side "downstream consumer" terminology used in
  per-submodule commit hygiene tickets.
- Risk/change class: `[chore]`; out-of-band coordination only.

## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: re-flag from `done` to `in-progress` after empirical
  drift-fixture probe retry (throwaway PR `ryancinsight/CFDrs#319`
  on commit `a163ef55`, ci.yml run `30109405652` / job `89534706116`)
  revealed a NEW upstream cargo-side blocker distinct from the
  COEQ one the prior turn's predicate anticipated.

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
  + new `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  + PR #31 (HELIOS) management.

- Outcome: PARTIAL e2e CI verification of the wired `prebook check-figures`
  SSOT drift lint. The local lint (SSOT_IN_SYNC 7/7 green + drift detection
  at L101) + YAML validation + action pin alignment + clippy `-D warnings`
  clean + `mdbook build` exit 0 are proven signals documented in
  `ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`. **PR #31 (HELIOS closeout →
  main at run ID `30059559064`) was the actual e2e attempt**: the
  `Check book figures` step fired in the GitHub Actions runner, but
  PR #31 produced 5 failed/concluded-with-error jobs and the conditional
  auto-merge (`gh pr merge --squash --delete-branch`) correctly
  short-circuited (FAIL_COUNT=5 ≠ 0). The full verbatim failure
  diagnostic + root-cause ranking + fix-up recovery plan is captured in
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.

- Failure inventory (PR #31, run `30059559064`):
  - `rust workspace` job failure: `cargo fmt -- --check` saw **6 `Diff in`
    blocks across 3 new files** in the closeout xtask crate —
    `xtask/src/check_figures.rs` (lines 47, 97, 131 — chain-method
    re-formatting), `xtask/src/main.rs` (line 40 — three match arms
    `LegacyMigrationAudit`, `RefreshLegacyAllowlist`,
    `BurnMigrationAudit` consolidated to expression bodies), and `xtask/src/prebook.rs` (lines 139, 154
    — chain-method re-formatting on `fs::read` and `serde_json::to_string`).
    All 6 diffs are chain-method consolidation; trivially fixable via
    `cargo fmt -p xtask && git commit --amend`.
  - `python bindings` and `benchmark regression check` job failures:
    BOTH caused by the same root cause — `--locked` flag (maturin for
    `python bindings`, `cargo bench --no-run` for benchmark regression)
    conflicts with `Updating git repository tyche / eunomia / apollo`
    run by Cargo's metadata step. Fix: drop `--locked` for these two
    CI invocations (intent is preserved via existing `atlas_ref` pin
    in ci.yml); alternative — commit a regenerated `Cargo.lock` that
    captures the submodules' new SHAs.
  - `recurseml/analysis` job error: external research bot, not part of
    GitHub-hosted CI (out-of-scope noise). Confirmed no GitHub-hosted
    job matched the name in
    `gh api repos/ryancinsight/helios/actions/runs/30059559064/jobs`.
  - `deploy` job skipped: intentional (path-filtered `book-pages.yml`).
  - **False positive from prior summary**: `Install Rust verification
    tools` step actually succeeded; the prior summary's "error marker"
    was the `printf '::error::install-action:'` line inside
    `taiki-e/install-action`'s bash `bail()` function declaration.
    Confirmed verbatim in §3.4 of the run-evidence file.

- Main HEAD baseline (independent verification): `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b`
  was independently verified GREEN (3 latest CI runs all `success`).
  → All 4 substantive failures are PR #31-specific, NOT pre-existing on
  `main`. The closeout commits are causal.

- Acceptance: the `Check book figures` step fired in the runner; the
  explicit `SSOT_IN_SYNC: N/N` log line is captured in the run log at
  the relevant step output for verification. Auto-merge correctly
  short-circuited (fail-closed design verified). The full e2e gate
  validation (`DRIFT_DOCS_NOT_IN_SPECS: N` log capture on a
  deliberate drift fixture) remains deferred until the fix-up PR lands.

- Risk/change class: `[minor]`; deferred evidence-only, no production-code
  change on this turn. The fix-up iteration is a separate `[patch]`
  workflow tweak (CI config) + trivial `cargo fmt` commit.

- Dependencies: depends on the `codex/helios-book-figures-closeout`
  branch (currently SHA `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b` on
  `ryancinsight/helios` origin) receiving a fix-up commit addressing
  the 3 substantive failures above, then a follow-up PR (likely #32
  or higher) re-running the CI to validate green-pass. Verifiable now
  via `git ls-remote origin codex/helios-book-figures-closeout`.

- Sub-task (open): `cargo fmt -p xtask` + amend the closeout commits
  on the branch, then drop `--locked` flags from `Build Python
  extension` (maturin) and `Compile benchmark binaries` (cargo bench
  --no-run) invocations in `repos/helios/.github/workflows/ci.yml`.
  Re-push the branch; open a follow-up PR; expect PR CI to flow
  through `Check book figures` with the SSOT_IN_SYNC log line captured.

- Evidence limit: VERBATIM run-30059559064 log excerpts at
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  (sections 3.1–3.4). The `DRIFT_DOCS_NOT_IN_SPECS` log-line capture
  remains deferred to the follow-up PR's CI run. No release argument,
  no performance argument, no production-code delta.

## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-26;
  scope: `repos/CFDrs/.github/workflows/ci.yml` + `repos/CFDrs/.github/workflows/book-pages.yml`
  + `repos/CFDrs/docs/book/SUMMARY.md` (Appendix F cross-reference); the
  parent atlas `D:/atlas/parity_artefacts/INDEX.md` is the canonical
  sibling artifact cf. `ATLAS-PARITY-HTML-RETIRE-1`.
- Context: throwaway drift-fixture probe PR #320 (run `30217224003`)
  revealed TWO runner-side defects on the post-SIBLING-CHECKOUT-1 +
  post-COEQ-BLOCKER-1 CFDrs `origin/main` HEAD `1a7aa1d6`:
  - **(i)** `ci.yml` is registered (workflow id `319648723`, `state='active'`)
    but silently drops at queue time. GH Actions does NOT create a
    `ci.yml` run for PR #320, despite `pull_request` event firing the
    `book-pages.yml` sibling workflow on the same DRAFT PR. Most likely
    cause: the cross-repo composite action
    `ryancinsight/atlas/.github/actions/checkout-path-dependencies@51d8600cf3077e6ad6aafa5603b3289444b1719f`
    requires explicit allow-listing under CFDrs repo Settings -> Actions
    -> General when the consuming repo is not on the same plan tier.
    GH silently drops runs that reference unallowed private actions.
  - **(ii)** `book-pages.yml`'s `Build book` (mdbook build) step fails
    with `ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
    -- os error 2` because the runner's clean clone of `ryancinsight/CFDrs`
    ships ONLY the CFDrs source tree; the parent atlas's `parity_artefacts/INDEX.md`
    is not materialized (the existing `checkout-path-dependencies`
    action only materializes sibling sub-repo crates, NOT the parent
    atlas directory). This is the 3rd instance of the "sibling cross-reference
    missing in clean runner clone" class after the cargo path-dep
    (`ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`) issue and the older local
    coeus-core path-dep (`ATLAS-CFDRS-COEQ-BLOCKER-1`).
- Acceptance:
  - (a) **[ADMIN-GATED]** Repo-admin Settings -> Actions -> General
    confirms `ryancinsight/atlas/.github/actions/checkout-path-dependencies`
    is allow-listed, OR the workflow invocation is rewritten to use a
    non-private-org composite action. The throwaway re-run produces a
    visible `ci.yml` run in the runs API for the branch (not zero).
  - (b) **[LOCALLY-VERIFIABLE]** `book-pages.yml` gains a pre-step that
    materializes `parity_artefacts/INDEX.md` in the runner workspace
    (via `actions/checkout` of the parent atlas repo with
    `path: ../parity_artefacts/` + `sparse-checkout: INDEX.md`, OR
    via `curl`-based raw download from the GitHub raw content URL
    against a pinned commit). Throwaway re-run shows `Build book` step
    conclude `success` (no `os error 2`).
  - (c) **[DEPENDS ON (a)+(b)]** The throwaway re-run produces the
    verbatim
    `DRIFT_DOCS_NOT_IN_SPECS: N docs figure link(s) missing from FIGURE_SPECS:`
    log line at the `ci.yml` `Check book figures` step. Captured log
    line ends the ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER gate.
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin. (c) inherits from (a)+(b).
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin.
- Risk/change class: `[patch]`; CI scaffolding only, no production-code
  change on the CFDrs application tree or on the parent atlas's
  `parity_artefacts/INDEX.md` (the canonical parity archive remains the
  consumer).
- Dependencies: tracks `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (downstream
  consumer; the verbatim `DRIFT_DOCS_NOT_IN_SPECS: N` log capture gate).
  Follows `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` (cargo path-dep closure)
  + `ATLAS-CFDRS-COEQ-BLOCKER-1` (coeus gitlink closure).
- Discovered-by: throwaway probe PR `ryancinsight/CFDrs#320`,
  run `30217224003`, 2026-07-26 (this delivery). Capture archive at
  `D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-*/build/5_Build book.txt`.
- Evidence limit: per-step `conclusion=failure` JSON + verbatim mdbook
  error log; no production-code delta, no perf claim.
- Delivery (2026-07-27):
  - (b) closed: third-iteration curl pre-step landed in
    `D:/atlas/repos/CFDrs/.github/workflows/book-pages.yml`; runner-defensive
    invariants (`set -euo pipefail`, `curl --max-time 60 --retry 3 --retry-delay 5`,
    `printf | sha256sum -c` against certificate
    `18b7d9def0625f312776e15b2f70b681f38cbcb8838c9a9fd0b6ffb38af50a5a`). Pinned
    ref `51d8600cf3077e6ad6aafa5603b3289444b1719f` consistent with `ci.yml`
    atlas_ref. Code-reviewer-minimax-m3 returned GO for closing (b).
    End-to-end local emulation passes (`curl_exit=0`, `sha256_exit=0`).
  - (a) admin-gated remains open: `ci.yml` silent-drop on Ryancinsight
    DRAFT PRs unconfirmed root cause; tracked via
    `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (the (c) follow-on requires
    both (a) + (b) closures).

## ATLAS-WORKTREE-001 — Canonical lane root consolidation [patch] — in progress

- Owner: Codex `/root` (stale-claim takeover 2026-07-22); scope: worktree lane
  locations only, no member-repo code.
- Done 2026-07-21: 24 verified-duplicate standalone clones (12 at
  `D:\worktrees`, 12 at `D:\atlas\worktrees`; all detached, clean, HEADs
  contained, zero local branches), the SHA-keyed `.atlas-provider-checkout`
  cache, and the empty `D:\worktrees\atlas` were removed; stray
  `report/figures` SVG was rescued to `repos/report/figures/`.
- Done 2026-07-22: the legacy `D:\worktrees` root is absent, 16 redundant
  junction aliases are removed, and the former scratch scripts are absent.
  The only remaining lanes are the active Atlas RITK graph lane and Kwavers
  portability lane under the canonical `D:\atlas\worktrees/` root. Each repo
  remains within the main-tree-plus-one-lane bound.
- Done 2026-08-18: revalidated seven clean linked lanes against their provider
  defaults and removed them with `git worktree remove`: Asclepius ADR,
  Consus ADR, Iris color-space, both Mnemosyne audit lanes, and both Tyche
  cleanup lanes. Each lane had zero dirty paths and its tip was an ancestor of
  the provider default; its local branch was then deleted. No active lane or
  peer WIP was touched.
- Residual: the 2026-08-19 `scripts/atlas-lane-audit.py` probe reports four
  topology violations: Consus has four trees and one lane outside the
  canonical root, Kwavers has four trees, and RITK has four trees. Their extra
  lanes are active peer scopes or carry dirty state and require the owning
  streams to complete before further reclamation. The clean-lane cleanup
  increment is complete; no source or provider pointer changed.

## ATLAS-TARGET-001 — One build cache, one debug budget [patch] — in-progress (residual)

- Owner: Codex `/root`; last-update: 2026-07-22; scope: cache trees and
  profile sections only, no simulation logic.
- Done 2026-07-21: 18 stale cache forks deleted (repo-local `target/`, `target_isolated`, `target_benches`, nested crate `target/`) reclaiming 177.8 GB; `moirai` dev/test profiles aligned to line-tables-only/deps-none (was `debug = true`, pushed `946b4a7`); root `.cargo/config.toml` gains `[profile.dev.build-override] debug = false`. Policy: AGENTS.md performance_engineering "one build cache per stack" — a discovered fork is disposable derived state.
- Done 2026-07-22: the root test profile now matches the development profile:
  workspace test crates retain line tables, while dependencies, build scripts,
  and procedural macros emit no test debuginfo. This closes the configuration
  path through which Nextest could repopulate the shared cache with full
  symbols.
- Done 2026-07-22: removed two abandoned full-target `du` scans that had
  traversed the cache for about 2.5 hours, then pruned the idle incremental
  tree. Its 27,085 session directories occupied 525,183,672,320 bytes
  (approximately 489 GiB); the five-minute deletion preserved shared
  dependencies and linked artifacts, and a subsequent build recreated only
  three current session directories. This is operational reclamation, not a
  clean-build footprint claim.
- Done 2026-07-22: Kwavers PR #307 merges as `0602c1fd4`. Its broad
  dependency graph inherits development `opt-level = 1` instead of wildcard
  `opt-level = 3`, restoring exported generic sharing. Uncached feature-build
  steps fall 18–45%; exact head `909bcdfc7` passes 26 hosted checks, full-grid
  PSTD remains below 25 seconds, and a clean debug tree measures
  16,771,464,617 bytes across 6,109 files. Cargo removes the formerly blocked
  `repos/kwavers/target_isolated` plus six other obsolete private targets:
  9,363 files and approximately 4.49 GiB, without touching `D:/atlas/target`.
  Atlas-meta format and warning-denied Clippy pass; checkout-path Nextest passes
  11/11 in 3.746 seconds and doctests pass 1/1 in 1.93 seconds from the primary
  root against the shared cache.
- Done 2026-07-22: a stack-wide sweep removed 13 additional disposable target
  forks and reclaimed 18.465 GiB; no repository-local target directory
  remains. Before the remaining hosted checks, `cargo clean` against the
  canonical `D:/atlas/target` removed 68,854 files and 20.7 GiB. The configured
  shared cache then measured 0 bytes, below the 10-GiB operating budget; the
  final sweep must repeat after any later local gate.
- Residual: audit member workspaces with their own `[profile.*]` or `.cargo`
  sections (helios, hermes, CFDrs, coeus, ritk, mnemosyne). CFDrs currently
  compiles workspace tests at `opt-level = 2`; its dirty peer-owned workspace
  and active full test build preclude an unmeasured profile edit. Re-open that
  member as a separate measured increment after the peer work integrates,
  retaining only runtime- or profiling-justified deviations. Atlas-meta root
  worktrees copy `.cargo/config.toml` and therefore resolve a lane-local target;
  run meta-tool verification from the primary root until a portable route to
  the canonical cache is implemented and tested. One live sample found three
  independent top-level builds, five Cargo processes, and 23 concurrent `rustc`
  processes on a 24-thread/31.7-GiB host. Compare unchanged single- and
  concurrent-build workloads before selecting a global jobs cap; the sample
  proves oversubscription exposure, not an optimal cap.

## ATLAS-BENCH-BUDGET-001 — Wall-clock budgets for benches and examples [patch] — in-progress (enforcement merged; sweep residual)

- Owner: Claude (user-directed claim 2026-07-22); home: tools/criterion-regression (ADR 0024); policy: AGENTS.md engineering_gates "Runtime budgets" + performance_engineering "Benchmark time budget".
- Outcome: no bench binary or CI example exceeds its committed bound; suite time is designed, not emergent.
- Scope: (1) gate smoke — bench binaries run single-iteration (criterion `--test`) under the standard 30s/60s budget; (2) timing runs — per-binary wall-clock bound (default 300s) enforced in the criterion-regression runner/CI; (3) CI-safe examples complete within the test budget as scaled demos; (4) audit the 164 bench files (moirai 47, CFDrs 29, kwavers 22, hermes 12, ritk 10, rest ≤8) against the analytical time model — zero suites declare measurement_time/sample_size today, i.e. all run unbudgeted criterion defaults with sweeps; apply flat sampling for slow iterations, geometric sweeps, smallest regime-exercising inputs; where a single iteration is genuinely slow, profile and optimize the production kernel (farsight), never delete the bench or raise the bound in the offending diff.
- Acceptance: budget enforcement merged in the runner + full-stack bench sweep completes within per-binary bounds; breaches root-caused and fixed or filed with derivation.
- Done 2026-07-22: `enforce-budget` subcommand in tools/criterion-regression — modes smoke (bench single-iteration, 60s), timing (full measurement, 300s), examples (60s), `--bound-seconds`/`--skip` overrides. Compiles unbounded, executes binaries directly (killing cargo would orphan the bench grandchild) with CARGO_TARGET_DIR pinned to the shared target (no minted repo-local target/), fail-closed exit. Validated: themis smoke/timing clean; eunomia timing at 5s bound → breach terminated mid-measurement, exit 1. Gates: clippy pedantic clean, 21/21 nextest, doc clean.
- Residual: full-stack sweep at committed bounds (probe per repo; live peer scopes deferred to their completion), CI wiring per repo workflow convention, and suite resizing per breach (flat sampling, geometric sweeps) or kernel optimization per farsight.
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in progress

- Owner: Codex `/root`; last-update: 2026-07-23; completed vertical slice:
  `repos/coeus/coeus-ops/tests/**` only. Peer-owned member profiles and other
  repository test trees remain out of scope.
- Aequitas vertical slice: provider PR #35 on source `5428584` splits the
  private derived-unit and dimension-law test leaves, retaining all 38 law
  tests. It is a provider branch awaiting hosted gates; Atlas does not advance
  the Aequitas gitlink until the PR merges.
- Claim: consolidate the 36 flat `coeus-ops` Rust integration-test binaries
  into one hierarchical `tests/ops.rs` harness with `tests/ops/*.rs` modules,
  preserving all 87 test functions and their value-semantic assertions. The
  target-count reduction and test-count parity are the acceptance oracle.

- Policy: AGENTS.md performance_engineering "Debug-tree and compile-time structure" + "Compiler-last optimization order". Monomorphization stays the design default — an instantiation codegens identically to its hand-written equivalent; the debug-tree multiplier is leaf-binary count and duplicate paths, never genericity.
- Evidence 2026-07-22: ~950 leaf binaries stack-wide, each a full link with own incremental cache and PDB — tests/examples per repo: CFDrs 118/66, coeus 110/2, kwavers 94/62, consus 55/0, ritk 28/7, hermes 20/4, moirai 15/22, melinoe 15/1, others <=11. Dev-profile audit: helios declares wildcard `[profile.dev.package."*"] opt-level = 3` (the pattern removed from kwavers in PR #307); kwavers `opt-level = 1` with documented 5-10x PSTD justification is the sanctioned named-and-measured form. The shared incremental tree reached 27,085 session directories and approximately 489 GiB in five days, making leaf-target consolidation and CI `CARGO_INCREMENTAL=0` the next measured size levers.
- Scope: (1) consolidate each repo's tests/*.rs into one-or-few area harness binaries (`tests/<area>/main.rs` with modules) — nextest still isolates per test function in its own process, so coverage and isolation are unchanged while link count, incremental caches, and debug artifacts drop by the file count; worst offenders first (CFDrs, coeus, kwavers, consus, ritk, hermes); (2) merge near-duplicate examples per consolidation_discipline; (3) replace wildcard dev dependency opt raises with named, measured, per-package exceptions (helios first, peer-held — coordinate via board); (4) record per-repo binary-target count and debug-tree size before/after as the acceptance measurement.
- Acceptance: binary-target census reduced and recorded per repo; debug-tree size delta measured against the shared cache; test function count unchanged (no coverage loss); no wildcard dev opt-level overrides remain without a named measured justification.
- Completed vertical slice: Coeus `coeus-ops/tests` moved from 36 flat
  integration targets to one `ops` target with ten operation-family
  directories. The harness exposes 87 integration tests and the exact
  package Nextest run passes 196/196; whole-workspace debug-tree measurement
  remains a later bounded slice.
- Evidence: warning-denied Clippy, package check, format, and diff checks pass
  on Coeus commit `f67789c4`; the 87 harness tests are unchanged by source
  count and all 196 package tests pass. This item is closed for the bounded
  Coeus slice; the broader stack-wide debug-tree delta remains open work.
- Coeus-NN slice complete at provider commit `95bb9090`: the existing
  `nn_tests.rs` harness and its already hierarchical `tests/nn/` modules stay
  intact while the 33 other direct test binaries move behind one `nn_ops`
  harness, preserving the 268 total package tests. The 34 direct test targets
  reduced to 2 (`nn_ops` and `nn_tests`); the exact package run passes
  268/268 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `f8f6d665`: the existing
  `autograd_tests.rs` harness and `tests/autograd/` module tree remain intact
  while the three other direct targets move behind one `autograd_ops` harness.
  The four integration targets reduce to two; the exact package run passes
  94/94 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-tensor slice complete at provider commit `49bb5858`: the 13 flat
  integration targets move under six operation-family directories behind one
  `tensor_ops` harness. Locked metadata reports one integration target; the
  source census remains 53 annotated integration tests, and the exact package
  Nextest run passes 58/58 with 0 skipped, including five library unit tests.
  Production tensor code and all leaf test bodies remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-sparse slice complete at provider commit `81cb68a6`: the three flat
  integration targets move under conversion, differential, and invariant
  directories behind one `sparse_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 19/19 with 0
  skipped in 0.713 seconds. Production sparse code and all leaf test bodies
  remain unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-core slice complete at provider commit `88dfd38f`: the four flat
  integration targets move under storage, dependency-policy, and scalar
  directories behind one `core_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 21/21 with 0
  skipped, comprising 14 integration cases and seven unchanged library unit
  tests. Production core code and all leaf test bodies remain unchanged.
  Whole-workspace debug-tree measurement remains open.
- Coeus-CUDA slice complete at provider commit `573ad35e`: the three flat
  feature-gated integration targets move under device and fallback directories
  behind one `cuda_ops` harness, retaining the existing nested `tests/cuda/`
  tree through an explicit path. Default Nextest passes 3/3 with 0 skipped;
  all-features check and Clippy pass. All-features executable coverage remains
  host-blocked because the GNU linker cannot find
  `/usr/local/cuda-11.3/lib64/libcuda`. Whole-workspace debug-tree measurement
  remains open.
- Coeus-Python slice complete at provider commit `8851c5f5`: the six flat Rust
  integration targets move under activation, distributed, NN, operation,
  optimizer, and autodiff directories behind one `binding_ops` harness. The
  shared `tests/common` lock module is owned once at the harness root. Exact
  all-features Nextest passes 75/75 with 0 skipped; production PyO3, Python
  parity scripts, and generated artifacts remain unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-WGPU slice complete at provider commit `c507683e`: the two flat
  integration targets now share one hierarchical `wgpu_ops` harness, with
  fused operations under `fusion.rs` and the existing WGPU operation tree under
  `backend/wgpu/`. Exact package Nextest passes 85/85 with 0 skipped; the moved
  source files are content-identical renames and production GPU code is
  unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-WGPU parity split complete at provider commit `149aadb5`: the 808-line
  multi-family leaf is now a shared oracle manifest plus seven operation-family
  modules. The pre/post source-name census remains 47 unique parity identifiers;
  exact package Nextest passes 85/85 with 0 skipped. Every new leaf is below
  500 lines; production kernels and fixtures are unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto slice complete at provider commit `8d3b9082`: the two flat
  integration targets now share one hierarchical `leto_ops` harness with
  contract and sparse-dispatch operation families. Locked metadata reports one
  integration target; exact package Nextest passes 28/28 with 0 skipped in
  1.064 seconds. The live census is 26 contract tests plus 2 sparse-dispatch
  tests, correcting the prior 26-test tracking claim. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `24a52be5`: the established
  `tests/autograd/` module tree and standalone operation families now share one
  hierarchical `autograd_ops` harness; the redundant `autograd_tests.rs`
  manifest is removed. Locked metadata reports one integration target instead
  of two; exact package Nextest passes 94/94 with 0 skipped in 1.535 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass. Whole-
  workspace debug-tree measurement remains open.
- Coeus-NN slice complete at provider commit `5c416e12`: the established
  `tests/nn/` module tree and operation-family modules now share one
  hierarchical `nn_ops` harness; the redundant `nn_tests.rs` manifest is
  removed. Locked metadata reports one integration target; exact package
  Nextest passes 268/268 with 0 skipped in 4.463 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-NN tensor parity split complete at provider commit `ee5be32f`: the
  1,317-line multi-family parity leaf is now a shared assertion manifest plus
  attention, convolution, embedding, linear/normalization, losses, and
  regularization operation-family modules. The pre/post source-name census
  remains 11 unique parity test functions; exact package Nextest passes 268/268
  with 0 skipped in 2.816 seconds. The largest new leaf is `attention.rs` at
  664 lines; the other five leaves are below 250 lines. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-CUDA parity split complete at provider commit `abe9211d`: the live
  1,672-line multi-family parity leaf is now a shared oracle manifest plus
  seven operation-family modules. The pre/post source-name census remains 29
  unique parity test functions; every new leaf is below 500 lines, with
  `convolution.rs` the largest at 365 lines. Default package Nextest passes
  3/3 with 0 skipped; default and `--features cuda` package checks and
  warning-denied Clippy pass. Feature-enabled Nextest cannot link because
  `x86_64-w64-mingw32-gcc` cannot find `-lcuda` while searching
  `/usr/local/cuda-11.3/lib64/`; no live CUDA parity execution is claimed.
  Whole-workspace debug-tree measurement remains open.
- Coeus-Python operation binding split complete at provider commit `0d8784c1`:
  the live 3,160-line `binding_tests_ops.rs` leaf is now fourteen
  operation-family leaves with nested NN functional and module directories.
  The pre/post source census remains 61 unique test functions and all 61
  extracted Rust function bodies compare equal. The largest test-family leaf is
  `reductions.rs` at 391 lines; every leaf is below 400 lines. Exact package
  Nextest passes 75/75 with 0 skipped in 8.079 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production PyO3,
  Python parity scripts, and generated artifacts remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-dist distributed-contract split complete at provider commit `c7838d90`:
  the live 1,262-line `dist_tests.rs` leaf is now one `dist_ops` manifest with
  local and TCP transport subtrees, separated into collective, reduction,
  invalid-input, and mesh-boundary families. The pre/post source census remains
  64 unique test functions, all 64 `#[test]` attributes remain present, and
  all 64 extracted Rust function bodies compare equal. The largest new leaf is
  `distributed/tcp/errors/collective.rs` at 464 lines; every leaf is below 500
  lines. Exact package Nextest passes 64/64 with 0 skipped in 0.444 seconds,
  with no slow tests. Package check, warning-denied Clippy, format, and diff
  checks pass. Whole-workspace debug-tree measurement remains open.
- Coeus-NN loss-contract split complete at provider commit `37bf8d9b`:
  the live 902-line `nn_loss_tests.rs` leaf is now a nested manifest with
  binary, classification, distance, and distribution operation families. The
  pre/post source census remains 24 unique test functions and all 24 extracted
  Rust function bodies compare equal. The largest new leaf is `distance.rs` at
  315 lines; every new leaf is below 500 lines. Exact package Nextest passes
  268/268 with 0 skipped in 2.270 seconds. Package check, warning-denied
  Clippy, format, and diff checks pass. Production NN code, fixtures, and
  tolerances remain unchanged; whole-workspace debug-tree measurement remains
  open.
- Coeus-optim contract-family split complete at provider commit `b27d492f`:
  the live 676-line `optim_tests.rs` leaf is now one `optim_ops` manifest with
  optimizer, scheduler, convergence, and gradient-clipping family modules.
  The pre/post source census remains 20 unique test functions and all 20
  extracted Rust function bodies compare equal. Locked metadata reports one
  `optim_ops` integration target. The largest new leaf is `convergence.rs` at
  239 lines; every new leaf is below 250. Exact package Nextest passes 20/20
  with 0 skipped in 0.188 seconds. Package check, warning-denied Clippy,
  format, and diff checks pass. Production optimizer code and all test oracles
  remain unchanged; whole-workspace debug-tree measurement remains open.
- Coeus-NN extended activation split complete at provider commit `d800be8c`:
  the live 648-line `act_extended_tests.rs` leaf is now one `act_extended`
  manifest with piecewise, parameterized, module-smoke, and smooth families.
  The pre/post source census remains 17 unique test functions and all 17
  extracted Rust test function bodies compare equal. The largest new leaf is
  `piecewise.rs` at 354 lines; every new leaf is below 360. Exact package
  Nextest passes 268/268 with 0 skipped in 3.155 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production NN code,
  fixtures, formulas, and tolerances remain unchanged; whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto contract-family split complete at provider commit `97d94566`:
  the live 505-line `leto_ops/contract.rs` leaf is now a manifest with
  arithmetic, reductions, matmul, layout, and accumulation families under
  `coeus-leto/tests/leto_ops/contract/`. The pre/post source census remains
  26 unique contract tests and all 26 extracted Rust test function bodies
  compare equal. The largest new leaf is `layout.rs` at 197 lines; every new
  leaf is below 200 lines. Locked metadata reports one `leto_ops` integration
  target. Exact package Nextest passes 28/28 with 0 skipped in 0.325 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass.
  Production Leto dispatch code and test oracles remain unchanged; whole-
  workspace debug-tree measurement remains open.
- Next claimed slice: run a fresh structural audit of the remaining Coeus test
  tree and take the next real family-boundary increment, if a live leaf exceeds
  the hierarchy trigger without violating test cohesion.

## ATLAS-PUBLISH-001 — OIDC publish pipelines and Pages alignment [patch] — in progress

- Policy: AGENTS.md engineering_gates "Publish pipelines". Wiring is agent work; registry-side toggles are user actions.
- Scope: (1) crates.io — add tag-triggered, environment-gated trusted-publishing workflows (`rust-lang/crates-io-auth-action`, `id-token: write`) to publishable stack crates, dependency-ordered with `cargo package` dry-run and semver gates; record per-crate "enforce trusted publishing" as a user checklist once each pipeline is green (disables token publishing registry-side). (2) PyPI — for the Python-binding crates, maturin-action matrix (manylinux2014 floor, `--compatibility pypi`, abi3 where the surface permits, sdist) with install/import/pytest wheel smoke before upload via the PyPI trusted-publisher flow. (3) Books — align CFDrs/kwavers/helios book workflows to the artifact flow (build + `mdbook test` → upload-pages-artifact → deploy-pages) if any still push a gh-pages branch or skip the test gate; new books inherit the same workflow.
- Acceptance: no long-lived registry token referenced in any CI secret; each wired pipeline dry-run green; book deployments artifact-based with the test gate; user-action list (registry enforcement toggles) recorded on the board.

### ATLAS-PUBLISH-001-CFDRS-PYPI — Add CFDrs abi3 PyPI trusted-publishing caller [patch] — in progress

- Owner: Atlas coordinator; claimed 2026-08-18.
- Scope: `repos/CFDrs/.github/workflows/python-release.yml`,
  `repos/CFDrs/crates/cfd-python/tests/`, the binding version surface, and the
  shared root `.github/workflows/python-wheels.yml` release-distribution
  contract. The caller uses the shared workflow at the exact Atlas graph
  revision and the provider's declared `cfd_python` import surface.
- Acceptance: the release-tag caller builds abi3 wheels with the manifest's
  PyO3 floor plus one validated source distribution, installs/imports the
  wheel, runs bounded value-semantic Python tests, and hands validated release
  artifacts to PyPI Trusted Publishing; no registry token or untested
  import-only path is introduced.
- Non-goals: registry-side trusted-publisher enforcement, a local publish,
  release/version changes, and unrelated CFDrs Rust or workflow cleanup.
- Verification: inspect the workflow's pinned actions and exact `atlas-ref`,
  run provider formatting and focused Rust checks, compile the binding test
  contract where the local Python/maturin toolchain permits, and validate the
  workflow statically.
- Provider implementation status: CFDrs commit `e7a1c9e8` on PR #360 already
  ships the abi3 typed boundary and GIL-release changes. Provider-local
  evidence is a release wheel containing `cfd_python.pyi` and `py.typed`,
  installed-wheel pytest `4/4`, strict mypy consumer validation, and complete
  runtime export coverage. Follow-up commit `a5a92bfc` pins the caller's
  `atlas-ref` to Atlas `ad22ec5e`. Hosted exact-head verification, merge, and
  post-merge evidence remain open; the Atlas CFDrs gitlink is unchanged.

### ATLAS-HELIOS-BOOK-TEST-002 — Enable Helios `mdbook test` in the shared Pages caller [patch] — done 2026-08-17

- Owner: Atlas coordinator; scope is the clean Helios workflow caller only.
- Evidence: clean-lane source `30a842cd7d7dee5ca9bda3e04e97fad966cebeee`
  enables the shared caller's `mdbook-test` input and merges at Helios default
  `679402ae166ce2b227d8d629bab877f1dcc45131`.
- Acceptance: met. The exact clean Helios book and hosted Pages build pass;
  hosted Rust, Python, and benchmark checks also pass. The external
  `recurseml/analysis` error remains report-only.
- Non-goals: peer-owned Helios source edits, book prose, generated figures,
  and the Kwavers/CFDrs caller sub-scopes.
- Re-open trigger: a book sample failure, shared workflow contract change, or
  provider caller that disables the test input.

## ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001 — Cross-book `mdbook test` gate alignment [patch] — peer-coordinated (filed by Session 18)

Coordinator-owned evidence record (this entry) under
eer-coordinated execution: kwavers peer on branch
`codex/kwavers-book-migration-eviction` (peer mid-flight on
`ATLAS-BOOK-002` eviction). CFDrs peer on `main` branch, 1 ahead of
`origin/main f04b1d75` (autest sub-task, see
`ATLAS-CFDRS-COEQ-BLOCKER-1`). Helios peer on
`origin/main 433ddb6`. Each member-repo peer owns their own workflow
`book-pages.yml`; coordinator cannot edit those files per
`concurrent_agents` disjoint-scope primitive — this entry surfaces the
shared gap and per-repo sub-scopes so each peer claims the disjoint slice
against their own repo. Coordinator verification of the shared gap was
performed against each repo's `origin/main` HEAD.

- Policy: AGENTS.md engineering_gates "Publish pipelines" — book
  workflows run build + `mdbook test` → `upload-pages-artifact` →
  `deploy-pages` (the test gate is the test-suite coverage for
  documentation samples, preventing rotted non-compiling example code
  from deploying).
- Discovery evidence (verified at Session 18 via `git show
  origin/main:.github/workflows/book-pages.yml` on each repo):
  - **kwavers** (`origin/main c19134ec`): steps `Configure Pages`,
    `Install mdBook`, `Build book` (runs `mdbook build docs/book`
    only), `Upload Pages artifact`, `Deploy to GitHub Pages`. No
    `mdbook test` step.
  - **CFDrs** (`origin/main f04b1d75`): identical step shape
    (`Configure Pages` → `Install mdBook` → `Build book` running
    `mdbook build` only → `Upload Pages artifact` → `Deploy to GitHub
    Pages`). No `mdbook test` step.
  - **helios** (`origin/main 433ddb6`): identical step shape. No
    `mdbook test` step. (Cited as residual (a) in
    `ATLAS-HELIOS-BOOK-001` Session 18 closure.)
  - All three deploy via `actions/upload-pages-artifact@v4` →
    `actions/deploy-pages@v4` with `pages: write` + `id-token: write`
    on the `deploy` job and deploy gated on
    `github.event_name != 'pull_request'` (main-only). The artifact
    flow is already compliant; only the `mdbook test` step is missing.
- Outcome: each per-repo peer-coordinated sub-slice lands one PR
  inserting a `Build book`→`Test book samples` step (running
  `mdbook test docs/book`) between `Install mdBook` and
  `Upload Pages artifact`, fail-closed on doctest failure. The (1)/(2)
  crates.io/PyPI scopes of `ATLAS-PUBLISH-001` remain separate and
  unowned — this sub-slice addresses only the (3) Books test-gate
  gap. Per-repo sub-scope (peer-coordinated):
  (a) **repos/kwavers/.github/workflows/book-pages.yml** — peer-kwavers
      holds active eviction branch (`codex/kwavers-book-migration-eviction`,
      1 ahead of `origin/main c19134ec`); the `mdbook test` step landing
      is complementary to eviction (examples must compile for `mdbook
      test` to pass, and eviction is removing the migration-reference
      examples that are least doctest-fit), so sequencing eviction first
      is the cleanest order. Awaiting peer eviction merge to `origin/main`.
  (b) **repos/CFDrs/.github/workflows/book-pages.yml** — peer-CFDrs
      on `main` ahead 1 of `origin/main f04b1d75`; lands after the
      `ATLAS-CFDRS-COEQ-BLOCKER-1` workspace-restore + check-figures
      re-verification so the local `mdbook test` pre-flight is backed by
      a fully-resolved Cargo graph (the coeus-core path-dependency
      gap currently stops local cargo metadata resolution).
  (c) **repos/helios/.github/workflows/book-pages.yml** — peer-helios
      at `origin/main 433ddb6`, book content ready to test. No known
      pre-requisite for the `mdbook test` step landing; cleanest
      per-repo increment of the three.
- Acceptance: each `book-pages.yml` carries a `mdbook test docs/book`
  step running doctests on committed sample code; book deploy still
  artifact-based with the test gate; user-action list (registry
  enforcement toggles) recorded on the board remains the same.
- Risk/change class: `[patch]` CI-only; no production-code delta.
- Dependencies: ATLAS-PUBLISH-001 (parent),
  ATLAS-BOOK-002 (kwavers eviction sub-scope ordering);
  ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs cargo-graph restore).
- Evidence limit: workflow-step inspection on each `origin/main`;
  no performance claim, no production-code delta.
- Refs: backlog.md#ATLAS-PUBLISH-001 (parent slice),
  backlog.md#ATLAS-BOOK-002 (kwavers peer eviction),
  backlog.md#ATLAS-HELIOS-BOOK-001 (Session 18 closure residual (a)),
  backlog.md#ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs workspace restore).

## Session 17 closure (2026-07-23) — ATLAS-LETO-OPS-SPARSE-LU-001 → ✅ closed

- Owner: atlas-meta coordinator (codex agent); status flipped todo → ✅ closed.
- Outcome: real CSC sparse LU + partial-pivoting numeric phase in leto-ops
  landed at leto `origin/main` `687b670` via PR #74 squash-merge
  (`refactor(leto-ops): Remove ndarray/nalgebra, native iterative solvers
  (LETO-NDARRAY-BOUNDARY-1) (#74)`).
  The PR diff (41 files) bundled the ndarray/nalgebra dev-dep removal (peer
  origin-main HEAD `9346413` declared no production deps on ndarray/ndarray-rand/
  nalgebra; only parity examples consumed them) AND the in-place upgrade of
  `SparsLuSolver` to the real algorithm class.  Public surface preserved:
  `SparseLuSolver::solve_view`, `CscMatrix`, `CsrMatrix`, `CooMatrix`, and the
  re-exported `factor_numeric` / `factor_symbolic` / `NumericLu` API paths.
- Algorithm spec (matches ADR 0031 Option A): symbolic factorization is the
  sequential left-looking Gilbert/Peierls reach over CSC, computing the
  static L/U pattern (L rows strictly `> j`, U rows `≤ j` per column j) under
  natural column ordering for v0.40.0; numeric factorization is the
  slot-indexed left-looking phase with partial-pivoting row swaps against
  `row_perm[slot] = original row` (matches the dense
  `LuDecomposition::pivots` convention so downstream CFDrs
  `DirectSparseSolver` composes unchanged); solve =
  `P·A·x = L·U·x = P·b` ⟺ forward sub `Ly = Pb` then back sub `Ux = y`.
- Density-gated dispatch (per ADR 0031): `SparseLuSolver` carries a
  `small_switch = 32` and `density_threshold = 0.1` pair; small or near-dense
  matrices route to a dense-fallback path; large sparse matrices route to
  the new symbolic→numeric sparse path.
- Verification evidence (Windows ucrt64, rustc 1.95.0, eunomia
  https://github.com/ryancinsight/eunomnia#f6cd644b):
  - `cargo check -p leto-ops --tests` ✅ clean (Finished in 2m 15s).
  - `cargo nextest run --no-fail-fast -p leto-ops` ✅ 339/339 pass in 3.17s
    (well under the 30s slow-timeout hard cap; no threshold relaxation, no
    test shrinkage).
  - `cargo test --doc -p leto-ops` ✅ 11/11 pass in 54.64s.
  - Sparse-LU-targeted suite ✅ 16/16 pass:
    `factor_poisson_1d_laplacian_n16_roundtrip` 0.064s,
    `factor_banded_5_diagonal_n32` 0.026s,
    `factor_random_sparse_n64_diff_dense` 0.252s,
    `sparse_path_routes_correctly_for_tridiagonal_n64` 0.269s,
    `factor_f32_generic` 0.051s,
    `singular_matrix_yields_storage_error` 0.240s,
    `solver_is_generic_over_f32` 0.071s, plus 9 inherited solver-routing tests.
  - Differential cross-check: `factor_random_sparse_n64_diff_dense` asserts
    value-semantic equivalence between sparse and dense LU on a randomly
    populated 64×64 matrix at residual < ε (not existence-only).
- Residual / not-covered-in-this-closure (per ADR 0031 Consequences):
  (a) AMD (Approximate Minimum Degree) ordering deferred to
      `ATLAS-LETO-OPS-AMD-ORDERING-001` [patch] — natural ordering ships for
      v0.40.0; AMD ~300-line impl exceeds this session's context budget and
      a partial implementation would risk numerical defects per ADR 0031
      "AMD scope risk".
  (b) CFDrs `DirectSparseSolver` migration to the landed
      `SparseLuSolver::solve_view` is the follow-up
      `ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001` — depends on aequitas pin
      coherence and a leto bump at CFDrs; not in scope for Session 17.
  (c) Local clippy `-D warnings` against the FULL leto workspace cannot run
      clean on this coordinator's working tree because peer's untracked
      uncommitted sibling verticals
      (`crates/leto-ops/src/application/{diff,interpolation,quadrature}/`)
      contain `assign_op_pattern` and `complex_type` lint failures. PR
      #74's CI status (both `recurseml/analysis` post-push and
      `CodeRabbit`) was CLEAN before squash-merge; the merged commit's
      leto-ops scope is clippy-pedantic clean modulo peer-held untracked
      files not in the merged tree.
- Concurrent-agent record: peer session active on the same `codex/leto-real-sparse-lu`
  working tree during this closure, creating untracked siblings for diff/
  interpolation/ quadrature operation families (ts 21:53-22:02).  Per
  `concurrent_agents` assist-ladder rule: peer files skipped, not collided with.
  Coordinator scope-strictly-committed only `sparse/lu_numeric.rs` and
  `sparse/lu_symbolic.rs` (doctest-fixture correction + rustfmt-only reflow of
  pre-existing `for ... take().skip()` chains); peer's `Cargo.{lock,toml}`,
  `lib.rs`, `application/mod.rs`, `application/linalg/mod.rs`, and the new
  `diff/`/`interpolation/`/`quadrature/` untracked modules remained unstaged.
- Gitlink-state: atlas-meta's `repos/leto` gitlink advances to
  `687b67079c4e122264c17fd2eb3fd850d876a39f` in the same commit that
  synchronizes this backlog entry and ADR 0031's status flip.
- Refs: backlog.md#CFDRS-PERF-SLOW-001 (Session 13 upstream-cause filing),
  backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (this item), ATLAS-LETO-OPS-AMD-ORDERING-001 [patch] (new follow-up below).

## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — partial closure (2026-07-23 Session 17: doc-migration slice landed via PR #316 `5ac713b3`); cfd-3d end-to-end re-profile and direct_threshold re-evaluation deferred

Filed as follow-up per Session 17 closure of `ATLAS-LETO-OPS-SPARSE-LU-001`.
Now that real sparse LU + partial pivoting has landed at leto `687b670`,
the CFDrs downstream consumer should adopt the upstream-native solver.

- Owner: unclaimed. Depends on CFDrs leto version bump (currently
  `aequitas = { path = "../aequitas" }` and leto path-pinned at
  atlas-meta level).
- Outcome: replace `crates/cfd-math/src/linear_solver/direct_solver.rs`
  body with calls to `leto_ops::application::sparse::SparseLuSolver::solve_view`
  on real CSC-typed inputs; remove any `with_direct_threshold(512)`-
  regime mats that exist purely to route medium saddle-point FEM
  matrices to GMRES (Brezzi 1974 indefinite saddle — sparse LU is now
  correct for it, not a misnomer).
- Acceptance: (1) CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs`
  no longer documents itself as "atlas-native sparse direct solver backed
  by dense partial-pivoting LU" (cf. the doc-runtime contradiction),
  (2) CFDrs cfd-3d suite verifies end-to-end (`validate_poiseuille_flow`
  PR #311 root-caused fix continues to PASS under the new upstream
  matrix-as-sparse path; re-profile runs `<1s` per Session 13 closure
  baseline), (3) `direct_threshold` parameter either removed from the
  CFDrs FEM solver or re-evaluated with new evidence (filed as a follow-up
  board item against CFDrs perf, not this slice).
- Risk/change class: `[minor]` (additive public-API call-site
  migration; no break to CFDrs public surface).
- Dependencies: leto version bump at CFDrs; aequitas pin coherence
  (Session 12 documented the eunomia dual-source-ID recurring risk
  when consumers pin eunomia differently; align all atlas consumers
  on URL-only form).
- Refs: backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed),
  leto origin/main `687b670`.

## Session 17 partial closure (2026-07-23) — ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 → partial closure

Coordinator (Session 17 follow-up) landed the doc-comment migration of
`crates/cfd-math/src/linear_solver/direct_solver.rs` to reflect the
real CSC sparse LU per ADR 0031 + leto origin/main `687b670` (PR #74
squash-merge).

- **CFDrs PR**: ryancinsight/CFDrs#316 — title
  "docs(cfdrs-math): Migrate direct_solver doc to ADR 0031 real sparse LU
  (ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial)" — squash-merged as
  `5ac713b3fdf5fd45dbd295f3887c6f58b88c63f8` on CFDrs origin/main at
  2026-07-24T03:43:21Z.
- **Diff surface**: +25/-6 in
  `crates/cfd-math/src/linear_solver/direct_solver.rs` — module doc
  rewrite + `ordering` field doc correction + convergence composition
  with peer's pending `..Default::default()` adaptation to the
  upstream `SparseLuSolver` struct expansion (`small_switch` +
  `density_threshold` fields per ADR 0031).
- **Doc claim corrected**: the pre-merge module doc claimed the
  atlas-native solver was "backed by dense partial-pivoting LU" — that
  misnomer was filed for the Session 13 `CFDRS-PERF-SLOW-001` timeout
  closure root cause; it is now stale per ADR 0031 since leto PR #74
  landed the real CSC sparse LU (symbolic = sequential left-looking
  Gilbert–Peierls reach per Davis 2006 §6.1; numeric = slot-indexed
  left-looking with row_perm[slot]=original-row matching dense
  `LuDecomposition::pivots`; density-gated dispatch `small_switch=32`,
  `density_threshold=0.1` in `SparseLuSolver`).
- **Safety net preserved**: the CFDrs-side `dense_threshold=1024`
  retry at `DirectSparseSolver::retry_dense_or_error` is preserved as
  the orthogonal catch case for the `max_size`-cap + small-`n`
  user-intent safety net; NOT a duplicate of the upstream internal
  fallback (which handles only `NumericalBreakdown` mid-sparse-path).

Gitlink: atlas-meta `repos/CFDrs` advances from `1b2c901` to
`5ac713b3` (submodule local working tree left at local main HEAD
`354266c0` with peer's WIP unmodified per concurrent_agents
preservation; the gitlink records the squash-merged origin/main tip).

Refs: backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (above; this
entry closes the partial slice),
docs/adr/0031-leto-ops-real-sparse-lu.md (atlas-meta, Accepted),
leto PR #74 squash-merged as `687b670` (origin/main),
CFDrs PR #316 squash-merged as `5ac713b3` (origin/main).


## Session 18 closure (2026-07-24) — ATLAS-HELIOS-BOOK-001 → ✅ closed

- Owner: peer-helios (delivered the book across multiple PRs landing at
  `origin/main 433ddb6`); atlas-meta coordinator (this Session 18
  closure records the verification matrix and flips the backlog status
  from `todo` to `✅ closed`). No member-repo file edits by this agent —
  per `concurrent_agents` disjoint-scope primitive, peer-helios owns
  `repos/helios/...` files.
- Outcome: full multichapter mdBook at `repos/helios/docs/book/`, mapped
  onto the canonical kwavers Domain-book contract (governing equations
  → numerics → API mapping → worked examples with deterministic 
  figures). Spec verified via local inspection of `origin/main`:
  - `docs/book/SUMMARY.md` manifest: 8 Parts (I Foundations, II CT
    Imaging, III Dose, IV Treatment Delivery, V End-to-End Clinical
    Workflows, VI GPU Acceleration, VII Validation, VIII Atlas Stack
    Integration Migration Reference) across 37 chapters + 4 appendices
    (A Dependencies, B Glossary, C API Reference, D Changelog) +
    `BOOK_ORGANIZATION.md` forward roadmap.
  - 18 example markdown files under `docs/book/examples/` span the
    chapter families (validate_foundation_units, voxel_grid_construction,
    photon_attenuation, radon_sinogram, fbp_reconstruction, sirt_
    reconstruction, mvct_registration, compton_physics, collapsed_cone_3d,
    dvh_analysis, dvh_optimization, gamma_index, tomotherapy_workflow,
    linac_dose_accumulation, adaptive_rt_workflow, gpu_attenuation_
    projection, validation_regression, validation_clinical).
  - 7 deterministic SVG figures under `docs/book/figures/`
    (architecture_stack, ct_calibration_curve, dose_slice_heatmap,
    dvh_curve, helical_mlc_fluence, photon_attenuation_depth,
    radon_sinogram_disk) + `MANIFEST.json` byte-determinism registry.
  - `docs/book/book.toml` configured with `/helios/` site-url + MathJax.
  - `README.md` carries the canonical `[Published Helios book]
    (https://ryancinsight.github.io/helios/)` link.
- Acceptance verification (evidence match per ATLAS-HELIOS-BOOK-001 L2506–L2509):
  - (a) `mdbook build docs/book` exit 0 — verified locally via
    `mdbook v0.5.4` on the helios checkout at `433ddb6`; HTML written
    to `target/book/helios/index.html`. ✅
  - (b) SUMMARY.md entries each map to a committed chapter stub with
    H1 (`# Chapter N — …`) + `## Further Reading` backlink. Verified
    by sampling chapters across all 8 Parts (foundations Part I,
    dose_attenuation Part III, planning_mlc Part IV,
    workflow_tomotherapy Part V, gpu_dose Part VI, migration_arrays
    Part VIII). ✅
  - (c) Book deploys to GitHub Pages through the artifact flow.
    `repos/helios/.github/workflows/book-pages.yml` uses
    `actions/upload-pages-artifact@v4` → `actions/deploy-pages@v4`,
    with `pages: write` + `id-token: write` on the `deploy` job, and
    deploy gated on `github.event_name != 'pull_request'` (main-only). ✅
  - (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/
    docs.yml` `docs-invariant` job runs dead-link detector +
    `mdbook build` on all three books) — green. ✅
- Helmholtz-style residual / not-covered-in-this-closure (peer-coordinated,
  NOT claimed by Session 18 — coordinator cannot edit member-repo
  workflow files per `concurrent_agents` disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 residual — `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test`.
      engineering_gates publish-pipelines mandate the mdbook test gate
      for the book-deploy workflow (ATLAS-PUBLISH-001 acceptance item).
      Peer-helios owns the workflow file; filed as a peer-coordinated
      sub-slice of ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-002 residual — the Part VIII Atlas-Stack Integration
      (Migration Reference) section in `repos/helios/docs/book/SUMMARY.md`
      (chapters 26–37) is in-scope for the cross-book migration-content
      evictionunder ATLAS-BOOK-002 (peer-kwavers holds the active
       eviction branch). Filed as a helios-side peer-coordinated
      sub-slice of ATLAS-BOOK-002.
  (c) Atlas-meta `repos/helios` gitlink stays at `433ddb6` (== `origin/main`).
      No gitlink advancement is required or performed by this closure
      — causal chain: peer-delivered → published on origin →
      coordinator verifies → backlog status flips. No regression
      surface.
- Concurrent-agent record: prior-session coordinator work committed as
  `04dee5c "docs(atlas): Close Aequitas metric audit gaps"` advanced the
  book-CI verification slice (now `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER`
  status `in-progress` after HELIOS PR #31 root-cause analysis). This
  Session 18 closure is disjoint in scope from that WIP slice — it touches
  only the `ATLAS-HELIOS-BOOK-001` section + this new Session 18 closure
  section, leaving the prior-session WIP + `ATLAS-CFDRS-COEQ-BLOCKER-1`
  + `ATLAS-PARITY-HTML-RETIRE-1` and all uncommitted peer-WIP untouched.
- Gitlink-state: atlas-meta's `repos/helios` gitlink remains at
  `433ddb6` — already equals `origin/main` so this closure makes no
  `backlog.md`-internal gitlink advancement. Diff signature: `backlog.md`
  only (no `.gitmodules`, no `gap_audit.md`, no member-repo path).
- Refs:
  - backlog.md#ATLAS-HELIOS-BOOK-001 (this closure)
  - backlog.md#ATLAS-BOOK-002 (kwavers master eviction scope — residual filed, not closed)
  - backlog.md#ATLAS-PUBLISH-001 (mdbook test gate peer-coordinated — residual filed, not closed)
  - helios `origin/main 433ddb6` `docs/book/` +
    `.github/workflows/book-pages.yml` + `README.md` (artifact evidence)
  - https://ryancinsight.github.io/helios/ (published book URL)

## Session 19 closure (2026-07-24) — ATLAS-AEQUITAS-001 gitlink advance + criterion-gate continuous verification

- Owner: atlas-meta coordinator (this Session 19 closure records the
  gitlink advance and the criterion-gate re-audit). No member-repo
  files touched per `concurrent_agents` disjoint-scope primitive.
- Outcome:
  (1) ATLAS-AEQUITAS-001 above — atlas-meta gitlink for
      `repos/aequitas` advances from `b86a55d` to `19fc384` (origin/main
      HEAD). Three peer commits, all CI-green via `gh api`. Linear
      advance (no merge-bubble), `[minor]` additive.
  (2) ATLAS-BENCH-BUDGET-001 continuous-verification re-audit of the
      meta-owned `tools/criterion-regression` tool:
      - `cargo check --all-targets` Finished clean.
      - `cargo clippy --all-targets -- -D warnings` clean (pedantic +
        `clippy::unwrap_used`).
      - `cargo fmt --check` clean.
      - `cargo nextest run --no-fail-fast` 21/21 pass (max 0.451s;
        well under the 30s slow / 60s terminate budget).
      - `cargo test --doc` 2/2 pass.
      The tool remains green for peer consumption; the residual
      full-stack sweep (164 benches across moirai/CFDrs/kwavers/hermes/
      ritk + per-repo CI wiring per `ATLAS-BENCH-BUDGET-001`) stays
      deferred until the live peer scopes integrate.
  (3) Stale-claim sweep + origin-sync-first per `concurrent_agents`:
      all five drifted gitlinks (CFDrs, coeus, aequitas, consus, kwavers)
      audited via authenticated `gh api` panel dispatched as a parallel
      subagent panel inspecting per-repo states via `git ls-remote`,
      `git --git-dir`, and authenticated `gh api` check-runs / status
      queries. Session 19 takes the single evidence-backable advance
      (aequitas); the other four are correctly rejected above with the
      recorded reason.
- Concurrent-agent record: peer-helios at `origin/main 433ddb6`
  (unchanged from Session 18 closeout). Peer-CFDrs at `origin/main
  99318bc` (advanced past Session 18 but CI red on check-figures job —
  same `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` residual; the Venturi metric
  closure `ATLAS-CFDRS-PERF-045` already recorded separately on main).
  Peer-mnemosyne already integrated per Session 18's gitlink advance.
  Peer-aequitas freshly advanced now. Other peer activity: peer-leto at
  `origin/main 687b670` (stable — sparse LU landed Session 17). Peer
  kwavers eviction remains local-only (PR #325 DIRTY, eviction branch
  unpushed). Stale-claim sweep used the actual peer's published origin
  + `gh api` for CI conclusions; no speculative merges or assumptions
  about peer intent beyond their published state.
- Diff signature: `repos/aequitas` gitlink only (index-staged) + this
  backlog.md section. No `.gitmodules` URL change, no `gap_audit.md`
  edit (currency-current via Session 18 closeout), no member-repo files,
  no `tools/*` build (the continuous-verification re-audit ran
  read-only against the existing tool tree and produced no source delta).
- Refs: backlog.md#ATLAS-AEQUITAS-001 (the gitlink advance this closure
  records), backlog.md#ATLAS-PUBLISH-001 (mdbook test gate per-repo
  peers — unaffected), backlog.md#ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1
  (CFDrs advance blocker), backlog.md#ATLAS-LETO-OPS-AMD-ORDERING-001
  (leto peer work — peer-held, unclaimed here),
  backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (CFDrs cfd-3d
  re-profile — partial closure, peer-held).
- Coordinator exhaustion reached after this advance: no further
  actionable gitlink atlases capable of evidence-backable advance at
  this session; all `in-progress`/`todo` items either peer-held
  (Codes `/root` peer) or peer-blocked on member-repo source files,
  per `concurrent_agents` disjoint-scope primitive. Next wake triggers
  documented at each rejected-advance entry above.

## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — in-progress (sub-delivery 1 done)

- **Sub-delivery 3 (coherence) peer-held 2026-08-07.** A live peer is
  building the offline stack-coherence scan in the same tool: new
  `tools/version-guard/src/coherence.rs` (`CoherenceFinding`,
  `CoherenceReport`, `scan_atlas` reading `.gitmodules` + checked-in
  manifests, no Cargo/registry), wired into `lib.rs`/`main.rs`/`error.rs`
  as a `coherence --atlas-root` subcommand. Working-tree changes only,
  uncommitted as of this record; the tree compiles and 52 tests pass
  (including `coherence::tests::injected_backward_fixture_is_reported`).
  Builds on the committed `a92a3c6` base. **Do not touch**
  `tools/version-guard/src/coherence.rs` or the other version-guard files
  while the peer is mid-edit; claim the sub-delivery-3 closure only after
  the peer commits or the edit goes stale.
- **Fail-closed intent validation committed 2026-08-07** as `a92a3c6`
  (`fix(version-guard): Fail closed on declared release with no forward
  movement`). The slice was previously recorded delivered but sat stranded
  uncommitted at the atlas root; the 2026-08-07 session landed it with the
  sibling tooling slices. Gates re-verified at commit time: 48 lib + 3 bin
  tests pass, `cargo clippy --all-targets -- -D warnings` clean.
- **Fail-closed intent validation 2026-08-06 (root tool slice).**
  `tools/version-guard` now treats a declared release/bump intent with no
  forward version movement as a defect, including an empty manifest diff or
  an identical-only reformat. The same intent-aware predicate drives the CLI
  exit code and human/JSON reports, so no alternate "clean" interpretation
  can mask a missed package release. Backward movement remains an unconditional
  defect, and undeclared forward movement remains rejected. Added regressions
  for empty and identical-only declared releases plus report parity. Scope is
  root tooling only; no provider checkout, consumer source, manifest,
  lockfile, or dependency changed.

- Policy: AGENTS.md git_discipline (version-bearing red-flag hunks) + architecture_scoping pin discipline (version metadata is sweep-triggering state). Motivating incident: `87ab265` (hermes) — a sed dep-conversion silently reverted the workspace release `0.5.0 -> 0.4.1` and internal requirements to `0.4.0`, unmentioned in its message; origin lied about versions for ~10 hours while integrators failed resolution, and coeus stacked 18 commits on the undeliverable base.
- Scope: (1) per-repo guard — CI step (and optional pre-commit hook) failing when a diff changes `version =` or first-party dependency version requirements without a declared release/bump intent (commit type `chore(release)`/`build(deps)` or an explicit footer); backward version movement always fails without the declaration; (2) stack coherence check — a meta-level check (home: tools/, sibling to criterion-regression) verifying every first-party requirement across allowlisted members resolves against the stack's current workspace versions, run in the integration sweep and on any version-touching commit; (3) wire both into member CI per repository convention.
- Acceptance: replaying `87ab265` against the guard fails it; coherence check passes on the current stack and fails on an injected backward-version fixture; guards live in committed CI/config, not agent memory.
- Sub-delivery 1 — per-member guard tool skeleton: **done 2026-07-31** at `
  c70af8b` (`fix(tools,scripts): Make version-guard build and retarget link tests`).
  `tools/version-guard/` (`atlas-version-guard`) parses both bare
  `version = "X"` lines and inline-table `dep = { ..., version = "X" }`
  entries from `git diff <range> -- '*.toml'`, pairs `+`/`-` per file by
  ordered position, classifies each as Identical / Forward / Backward, and
  flags a finding as a defect when backward (always) or forward-undeclared.
  Borrow-checker errors that surfaced in Session 32 (E0382 borrow-after-move
  of `v` in `scan_diff`; E0499 double `&mut` in `files_entry`) were
  resolved by capturing the side before the move and indexing the per-file
  slot, respectively (ownership fix, not a workaround). Live acceptance replay
  on `87ab265` produces **9 backward findings across 5 files**
  (`Cargo.toml` + `hermes-simd-core` + `hermes-simd-intrinsics` +
  `hermes-simd-types` + `hermes-simd`), exit 1. Tests 47/47 (44 lib + 3
  bin). Skeleton-scope: `[package].version` + inline-table first-party deps;
  third-party shorthand (`dep = "X.Y.Z"`) without surrounding `{...}` and
  TOML-section tracking (`[workspace.package]` vs `[package]`) deferred to
  sub-delivery 2.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.
- **Sub-delivery 3 — stack coherence check tool delivered 2026-08-07** in
  the root working tree (`tools/version-guard/src/coherence.rs`, with the
  `coherence --atlas-root <path> [--format human|json]` CLI subcommand).
  The scanner is offline and read-only: `.gitmodules` is the allowlist, and
  checked-in Cargo manifests are the package/version SSOT. It walks 235
  manifests, resolves `version.workspace = true`, dotted/workspace dependency
  inheritance, package aliases, multiline inline tables, and Cargo-style
  caret/tilde/comparator/wildcard requirements. It checks only path/git
  sources resolving to registered Atlas members, rejects missing member
  manifests, ambiguous package versions, unsupported prerelease/hyphen ranges,
  and malformed version components rather than reporting a false clean.
  Human and JSON reports share the same defect predicate; missing
  `--atlas-root` is an invocation error (exit 2).
- Sub-delivery 3 acceptance evidence: current Atlas scan is clean at
  **235 manifests / 215 packages / 898 first-party requirements / 0 defects**
  (human and JSON modes, exit 0); an injected backward-version fixture is
  detected; the missing-root CLI case exits 2. `cargo fmt --check`, strict
  `cargo clippy --all-targets --offline -- -D warnings`, `cargo nextest run`
  (59/59), `cargo test --doc --offline`, and `git diff --check` pass with
  ambient `RUSTC`/`RUSTDOC` overrides removed. Resolver-generated
  `Cargo.lock` patch churn was discarded; no lockfile or provider tree is
  part of this root tooling slice.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.

Toolchain-template drift corrected 2026-08-03 (Session 33 closure): the
peer's `1.95.0 -> 1.97.0` pin advance (ATLAS-TOOLCHAIN-COHERENCE-001
resolution) had been propagated to the three existing consumers but not to
`tools/_template/template-rust-toolchain.toml` (still `1.95.0`), so the
Session-32 version-guard skeleton copied the stale pin. Both files now
match `1.97.0`, `check-drift.sh` extended to a fourth consumer
(`tools/version-guard/`), and `template-Cargo.toml` / README consumers
list updated. `check-drift.sh` reports `4 consumers clean`.

## ATLAS-OVERLAY-001 — Generated [patch] overlay for local-vs-git coherence [patch] — in-progress

- Policy: AGENTS.md architecture_scoping "Development overlay". Motivating blockers: local mnemosyne 0.6 vs git moirai requirement ^0.5 (requirement lag — patch cannot unify across an unsatisfied requirement), and the provider manifest missing the apollo -> eunomia edge (hand-curated derived state rotting as edges appear).
- Scope: (1) extend tools/checkout-path-dependencies (it already computes the graph) to emit a stack-level `[patch."<git-url>"]` overlay into the root `.cargo/config.toml` from the `cargo metadata` closure of all allowlisted members — regenerated by command, never hand-edited; every first-party crate maps to its local tree per source URL; (2) forward-sweep integration — a first-party version bump runs the requirement sweep (every in-stack requirement and lock on the bumped crate advances in the same co-evolution unit), composing with the ATLAS-VERSION-GUARD-001 coherence check; (3) regenerate on graph change: adding a first-party dependency edge re-emits the overlay in the same increment.
- Acceptance: both motivating blockers reproduce against the pre-overlay state and resolve after (moirai builds against local mnemosyne once requirements sweep; apollo resolves eunomia from the generated closure); the overlay file carries a generated-do-not-edit header naming the regenerating command; member manifests unchanged (git+version sources intact for CI/standalone). Update 2026-07-24: generator landed as scripts/atlas-stack-overlay.py; suffix doubling fixed at the stem (zero .git.git keys, regeneration idempotent, check mode green); AGENTS.md now carries the generator contract (canonicalized inputs, closure validation, regenerate-and-diff freshness) and the meta-lane prohibition that supersedes the "build from primary root" workaround. **Update 2026-07-28 (Session 30):** check mode wired into CI as `.github/workflows/atlas-stack-overlay.yml` (gate on PRs/pushes touching `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`, `repos/**/Cargo.{toml,lock}`, `repos/**/pyproject.toml`). Sub-delivery (3) regenerate-on-graph-change absorbed: the `paths:` filter above fires on any consumer `Cargo.toml`/lock edit, which is precisely the trigger for overlay regeneration (script is one `python scripts/atlas-stack-overlay.py generate` call). Forward-sweep integration (sub-delivery 2) requires per-member guard at the atlas-coordinator boundary; that is the scope of ATLAS-VERSION-GUARD-001.

## ATLAS-WORKTREE-CLONES-001 — Reconcile standalone clones under `worktrees/` [patch] — in-progress

- **2026-09-02:** the lane audit's one remaining violation is `worktrees/kwavers-log` — not a clone: an empty folder skeleton (0 files) left by a removed lane, whose `crates/kwavers-python/.pytest_cache` is held open by five live peer processes and refuses deletion. Re-open trigger: those handles release (or a peer session ends); then `rm -rf worktrees/kwavers-log` and the audit reads 0, closing this item and `ATLAS-LANE-AUDIT-001`. Everything else is clean: no standalone clone under `worktrees/`, every member at or under two trees.

- Census 2026-07-30 (mechanized: `scripts/atlas-lane-audit.py`, exit-nonzero local gate for orient/replenishment — filed by fable-prompt-session as peer-assist evidence): 17 hand-wired gitdir mirrors are back under `worktrees/` (aequitas, apollo, coeus, consus, eunomia, gaia, hermes, hyperion, iris, leto, melinoe, mnemosyne, moirai, proteus, ritk, themis, tyche — each `.git` file points at the member's primary `.git/modules/...` gitdir, sharing its index), plus the `worktrees/hephaestus` standalone clone, three bare non-worktree dirs (hephaestus-unary-math-parity, kwavers-aequitas-vessel-metrics, ritk-book-complete), and kwavers at 3 working trees. The prior purge did not hold — something regenerates the mirrors. SPIKE (unclaimed): identify the generator (peer tooling or an agent habit materializing `worktrees/<member>`), evidence budget one session, deliverable = generator named and fixed or a defect filed on its owner; re-deletion without that finding repeats the cycle. Legitimate submodule lanes (gitdir under `.git/modules/<path>/worktrees/<lane>`) pass the audit.
- Live-regeneration evidence 2026-07-30: the violation count moved 22 -> 29 within ~2h of the first audit run — lane-root timestamps show a peer serially creating `hephaestus-j1e2` … `hephaestus-j5` plus `ritk-pr-split` during the session (lane-per-subtask sprawl; the two-tree bound and one-item-per-lane rules ignored). The spike's generator question now has a live specimen: whatever workflow drives the `-jN` series is creating a lane per job. Differential note for auditors: `scripts/atlas-lane-audit.py` counts are environment-dependent by design (local git state) — never baseline them in conformance JSON.
- Evidence: `D:/atlas/worktrees/` holds directories named after stack repos
  (`leto`, `eunomia`, `moirai`, `ritk`, …) that are **standalone clones**, not
  linked worktrees — `worktrees/eunomia/.git` is a full repo directory, and
  `git worktree list` in `repos/eunomia` shows only `repos/eunomia`.
- Impact: this is the prohibited repo-copy pattern (forked history, duplicated
  disk). It also actively breaks lanes: a real worktree placed under
  `worktrees/` resolves a member's `../<repo>` path dependencies to these
  clones, producing `package collision in the lockfile` — encountered while
  trying to lane the kwavers GMRES work.
- Scope: per clone, rescue-commit any dirty state, fetch unique branches and
  commits into the authoritative repo under `repos/`, then delete. Confirm
  `git worktree list` per repo stays within the two-tree bound afterwards.
- Non-goal: touching genuine linked worktrees.

### Session 29 partial reconciliation (2026-07-27)

Inventory at session open: 8 standalone clones (full `.git` dir at
`worktrees/<repo>`): `aequitas`, `asclepius`, `eunomia`, `hephaestus`,
`hermes`, `iris`, `leto`, `themis`.

- **Reconciled and deleted this session**: `worktrees/iris`.
  Safety verification satisfied byte-for-byte: WT HEAD `c3cc43b` ==
  `worktrees/iris`'s `origin/main` == atlas-meta gitlink pin ==
  `repos/iris` HEAD == `repos/iris`'s `origin/main`; zero unpushed commits
  (`origin/main..HEAD` empty); clean WT (no dirty files, no untracked,
  no stashes); single local branch `main`; not a linked worktree
  (`git worktree list` in `repos/iris` lists only the main tree). 3 days
  stale (well past the 1h staleness sweep threshold).
- **Intentionally NOT touched (peer mid-flight or unique content)**:
  - `leto` — last commit 18 min prior to close (actively in flight).
  - `aequitas` — dirty WT (`CHANGELOG.md`, `Cargo.lock`, `README.md`,
    `src/systems/si/*.rs`, `tests/*.rs`), 5h staleness. Mid-flight peer work;
    deletion would trigger `interaction_policy` Ask-User (irreversible loss
    of uncommitted unique work).
  - `themis` — dirty `Cargo.toml` containing **ATLAS-PATH-DEP-AUDIT-2 /
    ATLAS-OVERLAY-001 generated `[patch]` overlay content** (comment
    `Last delivery: 2026-07-27 closure cycle`). This is the peer-attributed
    draft of the ATLAS-OVERLAY-001 deliverable; deletion would destroy
    unique peer-authored state.
  - `asclepius`, `eunomia`, `hephaestus`, `hermes` — 6h staleness,
    not exhaustively safety-verified this session. Hephaestus clone HEAD
    matches the active peer-hephaestus feature branch, currently the focus
    of the persistent `no-origin-main` defect.
- **Next-session action**: re-safety-verify the 6h-stale and 3-day-stale
  clones (`asclepius`, `eunomia`, `hermes`) using the iris verification
  protocol (HEAD == origin/main AND clean WT AND no local-only branches AND
  no unpushed commits AND not a linked worktree) and delete each that passes.
  `aequitas` and `themis` require the user or the owning peer to rescue the
  dirty state before the clone can be deleted. `leto` is freshly active and
  should not be touched.

## Session 27 closure (2026-07-27) — peer-coordinator ATLAS-MODALITY advance + the persistent gitlink defect set

Re-oriented against `origin/main` at session open. The standing "next action"
from the Session 26 handoff (append Session 26 closure to `backlog.md`) had
already landed under peer-coordinator attribution: commit `1da7cea docs(pm):
Close GMRES fork ports; record athena zero-consumer evidence` wrote the
`## Session 26 closure` section at L4785. The math-SSOT audit content I drafted
in Session 26 also survived intact at L4542 (`ATLAS-MATH-SSOT-CONSOLIDATION-1`)
and the audit-pattern template in `gap_audit.md` at L5178 — peer commit
`fad8c9e` reused my commit subject but its diff was a CFDrs gitlink advance;
no content clobber. Same attribution-absorption pattern as Session 25
`e519928`; no remediation needed because the content is correct DoR-level PM
state.

### Peer-coordinator landings during the inter-session gap (10 commits, b3106f4..20b03b8)

A peer-coordinator session (same Ryan Clanton attribution) ran during the
~90-minute gap and landed 10 commits, of which 7 are substantive coordinator-
scope work on the modality-boundaries workstream and the CFDrs metric closure:

| Commit | Subject summary |
| :--- | :--- |
| `20b03b8` | Advance CFDrs gitlink to its consumer-side metric closure |
| `a802e0c` | Close CFDrs MET22 transient-composition metric gap in `gap_audit.md` |
| `b804449` | Split `ATLAS-MODALITY-002` — 2a (kwavers bioheat boundary) closed, 2b (SpecificAbsorptionRate provider-side gap) blocked on peer |
| `8571cc1` | Refresh Aequitas metric audit (reconcile CFDrs/Helios/Kwavers consumer closures) |
| `5711c0c` | Advance aequitas gitlink — `ATLAS-MODALITY-002` phase 1 |
| `537b22c` | Claim `ATLAS-MODALITY-002` phase 1 in aequitas |
| `35f41e9` | Record modality boundaries (optics / RF / photomedicine) in the stack map + kwavers bioheat deposition spine |
| `1da7cea` | (Session 26 carry-over) Close GMRES fork ports; record athena zero-consumer evidence; file `ATLAS-WORKTREE-CLONES-001` |
| `fad8c9e` | (Session 26 carry-over, peer-reused subject) CFDrs gitlink advance |
| `b3106f4` | (Session 26 close, peer-reused subject) Math SSOT audit pattern filed in `gap_audit.md` |

These landings are accepted (peer-coordinator authority is granted by the
standing Change intent on this allowlisted meta-repo; no clobber of my
Session 26 work). They advance `ATLAS-MODALITY-002` from `todo` to
`in-progress` (phase 1 delivered, phases 2b-4 open).

### Residual gitlink defects (re-probed this session)

`target/release/gitlink-coherence.exe audit` reports **5 defects + 1
stale-advanceable + 19 clean** (down from Session 26's 11 defects — peers
published `origin/main` for apollo/athena/gaia/helios/hermes/asclepius during
the gap, resolving the cat-a class).

Persistent defects, each blocked on peer recovery action the coordinator
cannot execute (no write access to `repos/<name>/...`):

| Repo | Category | Pin | origin/main | WT HEAD | Branch | Last commit | Recovery (peer-owned) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| coeus | cat-c | cdaf769 | e26ba668 | cdaf769 | `codex/coeus-error-function-parity` | 3h ago | peer-coeus: publish origin/main |
| hephaestus | no-origin-main | 47ca84a | (none) | 47ca84a | `codex/hephaestus-product-axis-reduction-parity` | 3h ago | peer-hephaestus: create `origin/main` (4-session persistent defect) |
| kwavers | cat-b | 81a40071 | dce38e26 | **a7922bcc** | `codex/kwavers-book-migration-eviction` | **59 min ago** | peer-kwavers: merge/rebase feature to origin/main OR roll WT to main; coordinator NOT advancing — peer is actively committing |
| leto | cat-b | c6ced81 | 5ba88cc | dcc5d54 | `codex/leto-real-sparse-lu` | 5h ago | peer-leto: merge feature to origin/main |
| ritk | cat-c | 65035908 | c05f84d5 | 65035908 | `codex/docs-ritk-n4-figure-only` | 3h ago | peer-ritk: merge feature + publish origin/main |

Stale-advanceable (still NOT safely advanceable):

- `mnemosyne`: pin=00c3f6d, origin-main=905909b, WT HEAD=ec1c000 on
  `codex/mnemosyne-tier-selection` (7h ago). `git add` would capture the
  feature-branch HEAD `ec1c000`, not `origin/main` `905909b`. Per pitfall #2,
  this remains blocked until peer-mnemosyne either publishes `origin/main`
  or rolls WT back to `main`.

### Assist-ladder actions taken this session

- **Audit recovery**: Verified peer-coordinator's Session 26 closure (L4785)
  and the math-SSOT inventory (L4542) survived intact — no remediation
  required.
- **No gitlink advances**: Every defect row is either a structurally
  peer-only recovery (publish `origin/main`, merge feature branch) or has
  the working tree on a feature branch that would capture the wrong SHA.
  `kwavers` peer committed 59 minutes ago — active, not stale; coordinator
  escalation inappropriate per `concurrent_agents` assist-or-skip rules.
- **Closure written**: This section.
- **No new board entries**: The 5 defect rows above are already covered by
  their prior-session backlog items; a louder board restate is not warranted
  until a true stale-claim (1h+ no commit signal) develops. Three defects
  (hephaestus, kwavers PR, leto) are at 3+ sessions persistence and would
  become candidates for user-direction escalation if they persist into
  Session 28.

### Stale-memory re-verification (this session)

- `rust-toolchain.toml` pinned, MSRV unchanged.
- `target/release/gitlink-coherence.exe` present and unchanged.
- 25 submodules in `.gitmodules` unchanged.
- Shared `target-dir = "target"` at `/d/atlas/.cargo/config.toml` unchanged.
- Re-confirmed: `repos/<name>/.git` is a `gitdir:` indirection file for the
  submodule members (except `leto`/`hephaestus`, which are full directories);
  the gitlink pin is what `atlas-meta`'s git index records, and it can differ
  from `repos/<name>` WT HEAD when a peer has moved their WT onto a feature
  branch without the coordinator committing the advance.

### Next-session handoff

- Re-fetch + re-probe at session open (utility `gitlink-coherence.exe audit`
  is the canonical state read).
- Watch for peer-kwavers landing the feature branch — if `origin/main`
  advances, the gitlink is a one-step advance.
- Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  merges — same one-step advance opportunity.
- Watch for peer-hephaestus publishing `origin/main` — would close the
  4-session persistent `no-origin-main` defect.
- If 3 of the 5 persistent defects are unchanged by Session 28 open,
  escalate to user with a single batched message naming the 2-3 worst
  blockers (likely hephaestus + the most-active-of-the-rest) and request
  direction on peer-side remediation.
- Stand-alone next coordinator items still `todo`:
  `ATLAS-OVERLAY-001` (generated patch overlay), `ATLAS-VERSION-GUARD-001`
  (manifest version guard), `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit filed;
  execution owned by peer-leto/peer-physics-crate), `ATLAS-WORKTREE-CLONES-001`
  (rescue the standalone clones under `worktrees/`). Review whether any
  becomes urgent next session.

## Session 28 closure (2026-07-27) — ADR 0033/0034 (Krylov/Accelerator re-architecture), coeus cat-b promotion, 1 defect escalation

Short session: re-oriented after peer-coordinator landings, integrated two new
ADRs into PM state, escalated the standing 4-session hephaestus defect as a
cross-referenced blocker on `ATLAS-ATHENA-ACCEL-BACKEND-001`, ended with no
new gitlink advances (5 defects + 1 stale-advanceable + 19 clean unchanged
this session).

### Peer-coordinator landings during the inter-session gap (6 commits, 5ed51fa..2cd4c01)

| Commit | Subject summary |
| :--- | :--- |
| `2cd4c01` | Propose one Hephaestus-backed Athena accelerator backend (ADR 0034, status `Proposed`) |
| `a454976` | Record `ATLAS-MODALITY-002` 2b progress + the unified heat-source field defect |
| `12d3fdf` | Reserve `ATLAS-DOWNSTREAM-COORDINATION-001` ticket for LeoNeuro-INC `50bfcd9` hand-off |
| `051d1af` | Reaffirm Athena as the Krylov owner (ADR 0033, `Accepted`, `[major] [arch]`) |
| `b23271b` / `eb3cdb9` | Refine STEP D axes table + alternatives-rejected grounds (PATH_DEP_AUDIT_001_ENTRY.md) |
| `1fd57ae` | Clarify STEP D orthogonal axes + alternatives rejected + push-handoff |

ADR 0033 supersedes the iterative-solver lane of my Session 26
`ATLAS-MATH-SSOT-CONSOLIDATION-1` audit (L4542). ADR 0033's reasoning is
correct: adoption-count inversion of a ratified boundary (ADR 0022 named
Athena Krylov SSOT; leto-ops's `ee6582d` reintroduction is a regression, not
a new SSOT, regardless of which has more current consumers). The
`ATLAS-MATH-SSOT-CONSOLIDATION-1` row's direct-decomposition lane (LU/QR/
Cholesky/SVD/eigen/Schur/Bunch-Kaufman/UDU — definitively leto-ops's
ownership per ADR 0033 §2) and sparse-interpolation-quadrature lanes remain
valid; only the iterative-solver recommendation is superseded by
ATLAS-ATHENA-KRYLOV-CAPABILITY-001 / ATLAS-GMRES-FORK-CONVERGE-001 /
ATLAS-ATHENA-ACCEL-BACKEND-001. The audit-inventory table itself (ssot-
baseline + cross-capability matrix) is unmodified and remains useful as the
broader cross-repon math consolidation inventory; it's just that one slice
of its recommended action set has been overtaken by a more authoritative
ADR.

### Gitlink state re-probed (post-peer-landings)

`target/release/gitlink-coherence.exe audit`: **5 defects + 1
stale-advanceable + 19 clean** (Session 27 had identical counts; this
session's only movement is the `coeus` defect upgrading from cat-c → cat-b).

| Repo | Category | Pin | origin/main | Movement vs Session 27 |
| :--- | :--- | :--- | :--- | :--- |
| coeus | cat-b | cdaf769 | 971fab9 | **upgraded** from cat-c: peer-coeus pushed `codex/coeus-error-function-parity` to a tracked remote branch (`origin/codex/coeus-error-function-parity`); still not merged to `origin/main` |
| hephaestus | no-origin-main | 47ca84a | (none) | unchanged (5-session persistent) |
| kwavers | cat-b | 81a40071 | dce38e26 | unchanged; WT HEAD moved to `a7922bcc` (peer kwavers-book-migration-eviction, 59 min ago at session open — peer is actively committing in their feature branch) |
| leto | cat-b | c6ced81 | 5ba88cc | unchanged |
| ritk | cat-c | 65035908 | c05f84d5 | unchanged |
| mnemosyne | stale-advanceable | 00c3f6d | 905909b | unchanged; WT on `codex/mnemosyne-tier-selection` |

### Assisted ACCEL-BACKEND row with the hephaestus-`origin/main` cross-reference

Appended a "Blocking upstream state" note at `ATLAS-ATHENA-ACCEL-BACKEND-001`
(L5127→L5137) naming the hephaestus 5-session persistent `no-origin-main`
defect as the upstream unblock for that [arch] item's deletion of
`athena-wgpu` and Hephaestus kernel additions. Recommend the user direct
peer-hephaestus to publish `origin/main` (or merge the feature branch) as
the unblock for both this row and the 4-session-persistent defect.

### Assist-ladder actions taken this session

- **No gitlink advances**: every defect is structurally peer-only recovery
  (publish/merge) or has the WT on a feature branch that would capture the
  wrong SHA per pitfall #2.
- **Doc-sync (anti-orphaning)**: cross-referenced the new ADR 0033/
  0034 chain into the existing `ATLAS-MATH-SSOT-CONSOLIDATION-1` audit row's
  recommendation set (no edit to that row, but the new PM state above makes
  the supersedence traceable); appended the blocking-upstream note to
  ACCEL-BACKEND.
- **Closure written**: this section.

### Next-session handoff

- **Highest-priority unblock**: peer-hephaestus publishing `origin/main` or
  merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  closes a 5-session persistent defect AND unlocks `ATLAS-ATHENA-ACCEL-
  BACKEND-001` execution. Recommend the user message peer-hephaestus
  directly if the defect is unchanged at Session 29 open.
- **Watch for peer-kwavers feature-branch merge**: kwavers peer is actively
  committing to `codex/kwavers-book-migration-eviction`. Once it lands on
  `origin/main`, the gitlink is a one-step advance.
- **Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  branch merges** — same one-step advance opportunities.
- **3+ session persistence threshold**: hephaestus now in its 5th session;
  kwavers PR #325 (codex/kwavers-book-migration-eviction) and leto branch
  (codex/leto-real-sparse-lu) at 3+ sessions each. At Session 29, if
  hephaestus is still `no-origin-main`, escalate to user with batched
  message naming hephaestus as the worst blocker.
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`, `ATLAS-WORKTREE-CLONES-001`,
  `ATLAS-DOWNSTREAM-COORDINATION-001` (new, peer-filed), `ATLAS-MATH-SSOT-
  CONSOLIDATION-1` (audit filed; execution owned by peer-leto/peer-physics-
  crate and now partially overtaken by ADR 0033's Krylov sequence).

## Session 29 closure (2026-07-27) — athena gitlink advance + hephaestus 6-session escalation threshold

### Re-orientation findings

- HEAD moved from Session 28 close (`73d3042`) to `ac20857` before this session
  opened via two peer-coordinator commits:
  - `3df60c1 build(atlas): Advance kwavers gitlink — ATLAS-MODALITY-002 phase
    2b closed` (peer-coordinator carried kwavers ATLAS-MODALITY-002 phase 2b
    close forward; kwavers gitlink was not actually advanced — see defect
    table below — the commit message subject and the kwavers gitlink advance
    it claimed did not coincide: pin remained `37d50b96`)
  - `ac20857 docs(pm): Record BiCGSTAB landing in Athena stage A` advanced
    the **leto** gitlink to `78d9e9e0` (peer-leto merged
    `codex/leto-real-sparse-lu` to `origin/main`, landing 17 commits since
    prior pin `c6ced81e`, including the boundary execution
    `687b670 refactor(leto-ops): Remove ndarray/nalgebra, native iterative
    solvers (LETO-NDARRAY-BOUNDARY-1)` — directly advancing the standing
    migration goal and aligning with ADR 0033's Krylov-ownership reaffirmation
    by retiring leto-ops native iterative solvers)
- Re-audited gitlink coherence: **4 defects | 2 stale-advanceable | 19
  clean**. Compared to Session 28 close: leto resolved (cat-b → advanced);
  athena newly stale-advanceable (peer-athena landed BiCGSTAB).

### Assist-ladder action executed: athena gitlink advance

- Verified: pin `a5fd8061` ancestral to origin/main `e965a95d` via
  `merge-base --is-ancestor`; **WT HEAD == origin/main byte-for-byte**;
  WT clean (`## main...origin/main`, no dirty files, not on feature branch).
  Pitfall #2 satisfied.
- Selective-staging discipline executed: `git reset HEAD -- .` →
  `git add repos/athena` → verified staged SHA == athena origin/main →
  verified only `repos/athena` staged (`git diff --cached --name-only` →
  CLEAN).
- Committed as `c38ca61 build(atlas): Advance athena gitlink to e965a95d`,
  pushed same cycle (`ac20857..c38ca61 main -> main`). Aligns with ADR 0033
  (Athena owns Krylov) and ATLAS-ATHENA-KRYLOV-CAPABILITY-001.

### Hephaestus `no-origin-main` — now 6-session persistent, escalation exercised

- Re-probed 2026-07-27 Session 29: hephaestus HEAD `47ca84a8`, last commit
  2026-07-27T12:22:02-04:00 (~6h prior). WT on
  `codex/hephaestus-product-axis-reduction-parity`, **ahead 1** of
  `origin/codex/hephaestus-product-axis-reduction-parity` with dirty
  `Cargo.lock`. Remote has only feature branches — **`origin/main` ref
  does not exist**; the structural cause is peer-hephaestus works
  exclusively on feature-branch flow and never publishes `main`.
- Per the standing ATLAS-ATHENA-ACCEL-BACKEND-001 cross-reference
  (L5139+) and the Session 28 next-session handoff instruction, the
  5-session threshold having been crossed at Session 28 close, Session 29
  confirms the defect is now **6-session persistent**.
- Coordinator authority (assist-ladder) does not authorize executing peer
  pushes. The escalation route is a **batched user-facing message** naming
  peer-hephaestus as the worst blocker; the cluster trio
  (`hephaestus`, `kwavers PR #325`, `ritk` `codex/docs-ritk-n4-figure-only`)
  as the user-actionable remediation set; and the gating relationship to
  `ATLAS-ATHENA-ACCEL-BACKEND-001` ([arch]) as the consequence of continued
  blockage. This message is delivered in the session response (not as a
  PM artifact, per no-report-file genre).

### Post-push gitlink-coherence state

| # | Repo | Category | Pin | origin/main | Last commit | Recovery (peer-owned) |
|---|---|---|---|---|---|---|
| 1 | coeus | cat-b | `cdaf769` | `971fab9` | 3h ago | peer-coeus: merge `codex/coeus-error-function-parity` to origin/main |
| 2 | hephaestus | no-origin-main | `47ca84a` | (none) | 6h ago | peer-hephaestus: publish origin/main — **6-session persistent, gating ACCEL-BACKEND-001** |
| 3 | kwavers | cat-b | `37d50b96` | `dce38e26` | <1h ago | peer-kwavers: merge/rebase `codex/kwavers-book-migration-eviction` (PR #325) |
| 4 | ritk | cat-c | `65035908` | `c05f84d5` | 3h ago | peer-ritk: merge `codex/docs-ritk-n4-figure-only` + publish origin/main |

**Stale-advanceable (this session close)**: `mnemosyne` only — pin `00c3f6d`,
origin/main `905909b`, WT on `codex/mnemosyne-tier-selection` HEAD
`ec1c000` (dirty `Cargo.lock`/`Cargo.toml`). NOT safely advanceable per
pitfall #2 (would capture peer's feature-branch HEAD, not origin/main).

**Athena — captured in two advances this session**:
- `c38ca61` advanced athena to `e965a95d` for the right-preconditioned
  BiCGSTAB landing.
- `24ad6ea` advanced athena again to `fef782cb` for the incomplete-LU /
  SuccessiveOverRelaxation preconditioner landing in `athena-leto`, which
  pairs with the Krylov family covered by ADR 0033. (Pin `e965a95d`
  stayed ancestral to `fef782cb`, so the second advance remained a clean
  one-step `git add` after verifying `WT HEAD == origin/main`.)
Both advances are attestable; the table above lists only the
still-defective and still-stale-advanceable rows.

### Next-session handoff

- **Primary escalation (carried)**: peer-hephaestus publishing `origin/main`
  or merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  now closes a 6-session persistent defect AND unlocks
  `ATLAS-ATHENA-ACCEL-BACKEND-001` execution. A direct user → peer-hephaestus
  nudge is now warranted prior to a 7th session.
- **Cluster escalation (carried)**: kwavers PR #325 /
  `codex/kwavers-book-migration-eviction` (3+ sessions), ritk
  `codex/docs-ritk-n4-figure-only` (3+ sessions), coeus
  `codex/coeus-error-function-parity` (3+ sessions). Batch a single
  user-facing message if all are unchanged at Session 30 open.
- **Watch for one-step gitlink advance opportunities**: peer-mnemosyne,
  peer-coeus, peer-kwavers, peer-ritk if their feature branches merge to
  origin/main (verify `WT HEAD == origin/main` before `git add` per
  pitfall #2).
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`,
  `ATLAS-WORKTREE-CLONES-001`, `ATLAS-DOWNSTREAM-COORDINATION-001`,
  `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit-only, partially overtaken by
  ADR 0033 Krylov sequence).

## ATLAS-LETO-PEER-WIP — Leto uncommitted peer WIP [patch] — blocked (peer-owned)

- Owner: peer session (codex); scope: `repos/leto/crates/leto-ops/`,
  `repos/leto/Cargo.toml`.
- Status: active peer WIP on `codex/leto-real-sparse-lu`. Contains:
  - `special_legendre.rs` (new Legendre polynomial module, 111 lines, 3 tests)
  - `Cargo.toml` path-dep overlay patches
  - `special.rs` formatting normalization
  - `lib.rs`/`mod.rs` module tree updates
  - `bessel_k0` test tolerance fix (1e-7 → 1e-6, already applied)
- Evidence: 425 leto-ops tests pass.
- Blocker: peer-owned; not committed by this session per concurrent_agents policy.
- Re-open trigger: the peer lands the branch or the one-hour stale-claim sweep
  finds no board/commit update; then reclaim the scope and complete the
  integration from the committed branch state.

## ATLAS-HYGIENE-BASELINE-001 — Eleven-class conformance baseline and namespace hygiene [patch] — in-progress

- Owner: fable-prompt-session (claimed 2026-07-30). Claimed scope: `scripts/atlas-conformance.py`, `scripts/conformance-baseline.json`, this entry. Burn-down (scopes 2-4) stays unclaimed for peers.
- **Current increment (2026-08-21):** the scanner previously aborted on the
  provider-local `helios-python/.pytest_cache` with `PermissionError`. The
  walker now prunes common derived Python cache/environment directories, and
  the focused scanner suite passes 21/21. The live worktree scan completes;
  its zero `workflow_missing_permissions` result is not a baseline update
  because provider workflow fixes remain uncommitted at their parent gitlinks.
- **Correctness reconciliation (2026-08-21):** the Athena audit's prior
  `athena-hephaestus-jacobi` worktree claim was not reproducible. The current
  checkout is detached at the parent-recorded gitlink and exposes only its
  primary worktree. `gap_audit.md` marks the earlier provenance inference
  historical and keeps only the observed checkout shape as current evidence.
- Scope 1 DELIVERED 2026-07-30: `scripts/atlas-conformance.py` (report/generate/check; 19 classes = the eleven recorded plus reexport_shims, sleep_synced_tests, commented_out_code, target_forks, gitattributes_missing, nextest_budget_missing, workspace_lints_missing, member_namespace_pollution), committed baseline `scripts/conformance-baseline.json` (supersedes the 2026-07-25 ad-hoc grep counts — heuristics differ, the instrument is now the SSOT), CI ratchet gate `.github/workflows/atlas-conformance.yml` (fails on any per-repo class increase; triggers on gitlink advances). Scan universe is `.gitmodules`-registered members only; git-ignored unregistered directories are skipped silently (private-consumer rule) and other unregistered directories count as unnamed `member_namespace_pollution` (currently 1 — the scope-3 run-output dump).
- New-class findings for burn-down (baseline totals): target_forks 5 (CFDrs, helios, hephaestus +2 — delete tree and creating override per performance_engineering "one build cache per stack"); gitattributes_missing 17/25 and workspace_lints_missing 17 (retrofit sweeps — mechanical, one commit per member); sleep_synced_tests 125 (moirai 105 — its scheduler tests wall-clock-sync; candidate for injected-clock rework); commented_out_code 109 (kwavers 51); reexport_shims 39; markers 13; nextest_budget_missing 1 (gaia). Also observed, outside scanner classes: workflow actions are tag-pinned across all six meta workflows (SHA-pin sweep per engineering_gates "Workflow hygiene") and `scripts/` retains the closed path-dep audit's r2-r6b iteration series (obsolete-artifact deletion candidate).
- Scope 1 extension 2026-07-30: five workflow/lock classes added — tag_pinned_actions 218 stack-wide (kwavers 66, hermes 21, ritk 21; the SHA-pin sweep is now measured, not just observed), workflow_missing_timeout 23, workflow_missing_permissions 7, pull_request_target_use 0 (clean), missing_cargo_lock 1 (themis — a foundation member without a committed lock) — baseline regenerated in the same change (generator contract); 24 classes total. Companion local gate `scripts/atlas-lane-audit.py` mechanizes the worktree-lane rules (two-tree bound, canonical lane roots, named branches, gitdir-mirror and standalone-clone detection) for orient and the replenishment audit — CI cannot see local worktrees, so it gates locally; census filed on ATLAS-WORKTREE-CLONES-001. The seven obsolete r-series audit scripts are deleted and the meta root adopts `* text=auto` `.gitattributes` (renormalization no-op — index already LF).
- Correction 2026-08-14: Themis's committed `Cargo.lock` landed in provider commit `09b2252`; the current `missing_cargo_lock` count is 0 for the requested provider set.
- Consolidation 2026-07-30: the scan-universe definition now has one owner — `scripts/atlas_stack.py` (registered members from `.gitmodules`, git helpers, ignore checks) imported by both the conformance scanner and the lane audit; the duplicated `registered_members()` pair and the scanner's twice-implemented root-sprawl/LF checks are collapsed (behavior-preservation proven by old-vs-new differential on stable members). Defect finding — **fixed 2026-08-02** (umbrella, this commit's parent): `atlas-toolchain-preflight.py` now imports `atlas_stack.registered_members()`; the glob-over-everything derivation is gone and the run resolves 25 member pins.
- Preflight side-finding 2026-08-02: this agent's shell environment carries ambient `RUSTC`/`RUSTDOC` exports pointing at the rustup PROXIES (`~/.cargo/bin/*`), which the preflight rightly fails. Proxy targets honor the pins, so the session's builds were coherent (single compiler identity confirmed once the overrides are cleared), but the exports should be removed from whatever profile sets them — an override pointing anywhere non-proxy would silently poison the shared cache.
- Lane-series clarification (re the 2026-07-30 sprawl evidence naming `hephaestus-j1e2`…`-j5`): those lanes were SERIAL, one claimed item each, each removed on its merge — the two-tree bound held at every instant (`git worktree list` never exceeded main + one lane) and the creation-rate spike measured throughput, not concurrent trees. Two removals hit Windows Permission-denied on first attempt and were pruned + rm-rf'd in the same cycle; if the audit counts orphan directories, that transient is the residue to look for.
- **Board-sweep sub-slice delivered 2026-08-07.** `scripts/atlas-board-sweep.py`
  parses the lenient level-two heading format, normalizes `in progress` /
  `in-progress`, reports explicit owner and claim-date context, and identifies
  blocked items lacking a `Re-open trigger` (including qualified forms such as
  `Re-open trigger (for the claiming session):`). It is report-only: findings
  never fail the command or mutate the board, while missing/unreadable input
  returns 2. Focused unittest coverage is in
  `scripts/tests/test_atlas_board_sweep.py` (6/6); `py_compile`, board lint,
  and `git diff --check` pass. The live root report scans 244 items, finds 27
  in-progress claims, and surfaces 3 blocked items without a re-open trigger:
  `ATLAS-SUBSTRATE-002`, `ATLAS-LETO-PEER-WIP`, and
  `ATLAS-CFDRS-TEST-BUDGET`. Claim freshness and remediation remain operator
  decisions; this tool does not reclaim or edit claims.
- Policy: AGENTS.md engineering_gates conformance scan (now enumerating all eleven debt classes), documentation_discipline "Root manifest", architecture_scoping "Member namespace hygiene".
- Baseline 2026-07-25 (per-repo counts recorded; the ratchet gate holds these non-increasing): files >500 lines: 574 (CFDrs 137, kwavers 91, consus 89); implementation-bearing lib.rs/mod.rs: 402 (kwavers 145); production `unwrap()`: 5833 (kwavers 3119, ritk 719); `#[allow]`: 798 (kwavers 330); print/dbg in src: 1082 (CFDrs 428); existence-only assertions: 444 (coeus 104, leto 79); type-suffixed fns: 380 (apollo 111); junk-drawer modules: 66 (kwavers 28); crates missing deny(missing_docs): 107/208; unsanctioned root files: 120 (kwavers 40); markers: 18.
- Scope: (1) extend the committed conformance scan script to all eleven classes and record this baseline as its first output; (2) burn-down items per repo by triage (kwavers is the epicenter: unwraps, fat manifests, junk modules, root clutter); (3) `repos/parity_artefacts` (untracked run-output dump in the member namespace — det_*.log, url/target lists) relocates to a gitignored verification output root or deletes at the parity stream's item completion (owner: parity stream; regenerable evidence, rescue-first if any file proves unique); (4) kwavers root files triage per the Root manifest rule.
- Acceptance: scan script covers all eleven classes with committed baseline; member namespace holds registered members only; per-repo burn-down items filed DoR-shaped.
- **Burn-down 2026-09-08 (peer contribution, scope 2).** Against the
  committed baseline the fleet stands at **13 regressions**, down from 26 on
  2026-09-06. (An earlier line here read "0 regressions": that number came
  from `check` run against the owner's uncommitted baseline regeneration,
  which had already absorbed all thirteen. Measuring against a baseline
  being rewritten in the working tree is the same defect recorded on
  2026-09-06; the committed file is the ratchet.) This session closed
  `moirai/crate_level_allows` (20 -> 16, Moirai #295) and deleted a stale
  539 MB `repos/aequitas/target` fork created by a cargo invocation that ran
  outside the overlay. Landing #295 required first restoring moirai's gate:
  main's CI had been red on `cargo fmt --all -- --check` (140 files
  unformatted since the edition-2024 move), a stale ADR index, and an
  example that no longer compiled under 2024 match ergonomics (Moirai #293,
  #294). Reconciliation: the atlas advance `4887c3191` claimed the
  lint-floor repair but recorded a gitlink predating it -- that branch had
  never been opened as a PR and its reported number belonged to an
  unrelated peer PR; `020a2f4da` records the correction.
- **Burn-down 2026-09-08 continued.** 13 -> 8 regressions. Closed:
  `moirai/{manifest_implementation 27->25, oversized_files 35->33}` (#296,
  splitting `schedule/queue/mod.rs`, `process/windows/mod.rs`, and the two
  largest test modules), `helios/target_forks` (5.6 GB stale tree deleted;
  no nested cargo config -- an ad-hoc invocation outside the overlay, same
  generator as the aequitas fork), and `mnemosyne/{seqcst_production 2->0,
  manifest_implementation 9->8}` (Mnemosyne #134). Remaining eight:
  `apollo/existence_only_assertions`, `hephaestus/{allow_sites,
  manifest_implementation}`, `kwavers/oversized_files`,
  `mnemosyne/{oversized_files, reexport_shims}`, `ritk/{oversized_files,
  type_suffixed_fns}`.
- **Generator finding 2026-09-08 (scope 1, owner's file) — corrected.** An
  earlier revision of this entry read that the wholesale `generate` in
  `a123358c1` "absorbed eight open regressions". Re-measured, that is
  wrong for most of them: running the instrument at the gitlinks recorded
  by `bbdbf3ae9` shows the committed baseline of that same commit already
  disagreed with its own revision -- apollo/existence_only 0 recorded vs 1
  measured, kwavers/oversized_files 107 vs 108, mnemosyne/oversized_files
  6 vs 10, mnemosyne/reexport_shims 2 vs 3, ritk 69/44 vs 76/45, and in
  the other direction kwavers/existence_only 73 recorded vs 13 measured.
  The baseline had drifted from the instrument in both directions, so the
  regeneration corrected stale rows rather than absorbing new debt, and
  the later restore to the lower numbers put the fiction back. ritk's rows
  are the clearest case: its source is byte-identical across the two
  gitlinks (the only commits between them touch `.githooks/`), so the
  69 -> 76 move cannot be code growth.
  The real defects are narrower and both mechanical:
  1. `check` reads `scripts/conformance-baseline.json` from the working
     copy (`BASELINE = ROOT / ...`), so a run right after `generate`
     compares the tree against itself and reports zero. Every commit that
     moved rows today states "none regressed" for that reason. `check`
     should read the committed blob or refuse to run against a dirty
     baseline.
  2. `generate` cannot distinguish correcting a stale row from absorbing
     new debt. It should print every row it raises with its previous
     value, so the commit that runs it carries the evidence a reviewer
     needs -- the rule "the baseline only decreases" is unenforceable
     while the generator is silent about increases.
  Until (1) lands, measure with `git show HEAD:scripts/conformance-baseline.json`
  rather than the working copy; three separate readings in this session
  were wrong for exactly that reason.
- **Burn-down close 2026-09-08.** Fleet check (committed instrument,
  committed baseline) stands at 6 violations, from 26 on 2026-09-06 and 16
  at this session's start. Closed this session: moirai `crate_level_allows`
  20->16, `manifest_implementation` 27->25, `oversized_files` 35->33
  (Moirai #295, #296); mnemosyne `seqcst_production` 2->0,
  `manifest_implementation` 9->8, `oversized_files` 10->6 (Mnemosyne #134,
  #135); hephaestus `allow_sites` 14->8, `manifest_implementation` 15->14
  (hephaestus #292); aequitas `manifest_implementation` 2->0 (aequitas
  #60); helios and aequitas `target_forks` (6.1 GB of stale trees, both
  from cargo invocations outside the overlay); CFDrs `excess_worktrees`
  (a four-day-stale lane whose branch had no delta). Landing the moirai
  rows first required restoring that repo's gate: main was red on
  `cargo fmt --all -- --check` (140 files unformatted since the edition-2024
  move), a stale ADR index, and an example that no longer compiled under
  2024 match ergonomics (Moirai #293, #294).
  The six that remain, with why each is not closable from here:
  `ritk/{oversized_files, type_suffixed_fns}` — proven stale baseline: the
  ritk source is byte-identical across the two gitlinks whose recorded
  counts differ, and most `type_suffixed_fns` hits are byte-format
  accessors (`read_u16`, `write_le_f32`) whose type is the format contract,
  which the naming rule exempts; `kwavers/oversized_files` — one of the two
  is the same staleness, the other real, and kwavers holds two trees with a
  live peer in the lane; `kwavers/target_forks` — a live peer's build
  directory, not disposable while they build; `apollo/{manifest_implementation,
  existence_only_assertions}` — apollo holds two trees, one live (last
  commit 32 minutes before this note) and one carrying a dead session's
  uncommitted board edit, so there is no lane to take and no clean tree to
  branch in. Skip recorded per the peer-assist ladder rather than opening a
  third tree.
- **Detector finding 2026-09-08 (scope 1, owner's file).** `reexport_shims`
  counts `cfg`-exclusive arms of one alias once per arm:
  mnemosyne's `backends/mod.rs` declares `DefaultBackend` three times
  (windows/unix/wasm32), of which exactly one compiles per target, and the
  row moved 2 -> 3 when the wasm arm landed. That is one alias, not three
  shims, and it is a legitimate platform-selection seam rather than the
  compat alias the class targets. The fix belongs in the detector (count a
  `cfg`-gated re-export group once), with the baseline regenerated in the
  same change; churning the code to satisfy the regex would be gaming.
- Observed 2026-09-08, not acted on (owner's claimed scope): the working
  tree carries uncommitted scanner work adding `bare_git_dependency` and
  `cache_retention_policy_missing` with a regenerated baseline. It runs and
  its counts are self-consistent, but `TARGET_DIR_SETTING` is defined twice
  from a double paste, and the regeneration predates today's tightenings
  (apollo/allow_sites 23->19, apollo/existence_only_assertions 2->1,
  kwavers and ritk excess_worktrees 1->0, moirai/crate_level_allows 20->16).

## Session 30 closure (2026-07-28) — atlas-stack-overlay CI wiring + peer math-SSOT PR 0008 audit artifacts tracked

Re-oriented against `origin/main` at session open; HEAD had moved from `d2e0ac9` to `182f346` through peer-coordinator landings during the inter-session gap. The persistent gitlink defect set shifted: hephaestus 8-session `no-origin-main` defect narrowed (peer published an `origin/main` ref, pin advanced to `bf24b873`), but the 4-defect cluster (coeus cat-b, hephaestus no-origin-main, kwavers cat-b, ritk cat-c) persists and remains blocked on peer-side branch merges.

### Landed

- `599ddca build(atlas): Advance athena/proteus/tyche/asclepius gitlinks` — four stale-advanceables cleared: athena `fef782cb` -> `1d24c643` (ADR 0034 stage 3 merge of feat/athena-hephaestus-backend, advancing the device-neutral accelerator backend per ADR 0034), proteus `9d7c1a8c` -> `9a8655d3`, tyche `1527964c` -> `996b649d`, asclepius `bbf38400` -> `ccffb6bc`. Each followed the safe-advance protocol (pin ancestor of origin/main, WT on `main` with HEAD == origin/main, single Cargo.lock dirt in each not captured by submodule gitlink staging). Reduces stale-advanceable from 6 to 2 (mnemosyne on feature branch, kwavers on cat-b).

### Tracked (peer-authored artifacts staged for review)

- `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` (138 lines, peer-drafted PR description for the math-SSOT consolidation; covers ADRs 0031/0032/0033 closure into leto-ops SSOT; cross-repo consumers `cfd-math`, `kwavers-math`, `kwavers-solver`; reserved tag `atlas/math-ssot-adr-0031-0033-closure`; per-ADR sign-off checklist spanning CFDrs / Kwavers / leto-ops module owners). Stage-only; substantive source changes in `repos/CFDrs/crates/cfd-math/...` and `repos/kwavers/crates/kwavers-{math,solver}/...` are peer-owned and out of coordinator scope.
- `docs/audit/math-ssot-ledger.md` (753 lines, peer-authored audit ledger documenting the leto SSOT surface and per-consumer redundancy inventory; provider-side already landed in leto-ops `StaggeredForward`/`StaggeredBackward`, `complex_solve`/`complex_inv`, `FiniteDifference3D`). Stage-only.

### Next-session handoff

- ATLAS-MATH-SSOT-CONSOLIDATION-1 closure gate: peer-CFDrs must commit and merge the `cfd-math` wrapper deletion (`cfd-math/src/differentiation/` removed, `fd_extensions` re-export added) before coordinator can advance the CFDrs gitlink and close the audit row. The CFDrs WT is at origin/main HEAD `c90e6840` but dirty (36 files, peer-cfdrs mid-flight on `CFDRS-AEQ-MET-25` cavitation work). When the CFDrs gitlink advances, the audit row can mark the math-SSOT consolidation phase as delivered and PR 0008 can be reviewed/merged by module owners. The same dependency applies to kwavers (`codex/kwavers-book-migration-eviction` feature branch at `df9008d9`) and leto (`codex/leto-real-sparse-lu` at `1d24c643`+3); none is safely advanceable until peer returns WT to `main` and merges to `origin/main`.
- Standing coordinator-scope `todo` items unchanged: `ATLAS-OVERLAY-001` (sub-deliveries 1/2 still open), `ATLAS-VERSION-GUARD-001` (sub-delivery 1: per-member guard tool skeleton), `ATLAS-WORKTREE-CLONES-001` (asclepius/hephaestus/leto WTs are peer-active mid-flight; remaining clones re-evaluate on next session).
- ~~The `repos/parity_artefacts/` directory has been physically removed from the working tree but the deletion is not staged~~ — **superseded 2026-08-18.** The removal did not hold: commit `5956d02`, a gitlink advance whose message describes a ritk `region.rs` split, re-added it as scope creep along with a second copy at the meta-repo root — 899 lines, 18 files, two archives where there should be one. Now resolved rather than re-deferred, because the deferral rationale ("belongs with the parity stream's closure increment") is what let it regrow: the duplicate is deleted, `INDEX.md` moved to the root copy with its relative links re-anchored one level up and verified to resolve, and `docs/mdbook/detector-parity.md` plus `gap_audit.md` corrected. The tracked pairs were byte-identical apart from line endings, so nothing unique was lost. Two truth defects were fixed alongside: INDEX.md claimed the archive "survives repo re-clones" when 33 of its 43 files are gitignored `*.log`, and the report claimed the `SUMMARY.md` path "resolves correctly" without the in-context-build qualifier that its own recorded CI failure contradicts.

### Post-session peer advances (attribution-absorption pattern)

Between my `599ddca` and the close of this session, peer landed a chain that absorbed the Session 30 closure intent and advanced the persistent defect set further:

- `9f92d94 docs(atlas): Refresh Aequitas gap audit` — peer-committed `docs/audit/math-ssot-ledger.md` and `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` under their subject. Content identical to what this session would have committed. Pattern matches the Session 25/26/28 attribution-absorption; no remediation needed because the content is correct.
- `d1f2e2c docs(atlas): Record Aequitas consumer closure` — gap audit refresh.
- `c2cad74 build(atlas): Advance CFDrs Aequitas closure` — CFDrs gitlink advanced to `109aec63`; CFDrs now reads as clean in the gitlink-coherence audit (down from stale-advanceable). MET-25 closure intent is now realized at the CFDrs WT HEAD; the math-SSOT PR 0008 cfd-math deletion gate (peer-cf must commit + push) remains the only outstanding dependency.
- `485b3dd docs(pm): Root-cause the gaia git-dep break blocking helios tests` — closes the gaia blocker; helios tests can now run against canonical gaia.
- `f793735 docs(adr): Correct ADR 0037's lockstep versioning mandate` — ADR 0037 mandate tightened.
- `86cb19a docs(pm): Record the generic-instantiation pattern; revert the blocked edit` — reverts a blocked edit and records the generic-instantiation pattern.

Final gitlink-coherence state at Session 30 close: **25 probed | 4 defects | 1 stale-advanceable | 20 clean.**

- **Defects (4):** coeus cat-b (peer `codex/coeus-error-function-parity` not merged); hephaestus no-origin-main (default branch is `master` at remote `14b73d56`, WT HEAD `7897c13f` is mid-flight on `ATLAS-HEPHAESTUS-SPARSE-SEAM-001` sparse-seam work, last commit 77 min ago — peer-active, leave alone); kwavers cat-b (`codex/kwavers-book-migration-eviction` not merged); ritk cat-c (`codex/docs-ritk-n4-figure-only` local-only, not pushed).
- **Stale-advanceable (1):** mnemosyne `00c3f6de` -> `905909be` — WT on divergent feature branch `codex/mnemosyne-tier-selection` (HEAD `ec1c000` not ancestor of origin/main), 30h since last commit; peer-mnemosyne is mid-flight on tier-selection work.

### Session 30 / Atlas-meta delivery summary

| Increment | SHA | Type | Coordinator-authored? |
|---|---|---|---|
| Advance athena/proteus/tyche/asclepius gitlinks | `599ddca` | build(atlas) | Yes — full content + protocol verification |
| Track PR 0008 + math-SSOT ledger | `9f92d94` | docs(atlas) | Peer-absorbed (content preserved) |
| Session 30 closure in backlog | `9f92d94` + `485b3dd` | docs(pm) | Yes — full text + peer addendum |
| CFDrs Aequitas closure advance | `c2cad74` | build(atlas) | Peer-owned |

## ATLAS-LANE-AUDIT-001 — Lane-root sweep results and residuals [patch] — in-progress (residual)

- Policy: AGENTS.md git_discipline Worktrees (lanes are swept claim surfaces; created only by `git worktree add`) + concurrent_agents (gitdir-mirror checkouts prohibited — a `.git` file pointing at another tree's gitdir shares its index and corrupts both trees' status).
- Audit 2026-07-26 of `D:\atlas\worktrees` (26 entries): 4 compliant live lanes (coeus-backend-parity, hephaestus-mixed-reduction-batch, kwavers-aequitas-vessel-metrics, ritk-ebcot-magnitude-view); 13 gitdir-mirror checkouts on main (the improvised-provider species); 7 standalone clones; 3 bare directories; 1 broken meta lane. Legacy root `D:\worktrees` now empty — its lanes completed and dissolved per ATLAS-WORKTREE-001.
- Done: `report` re-mint deleted (SVG already rescued to repos/report/figures); broken `atlas-final-integration` meta lane deleted + `worktree prune` (meta lanes prohibited); 5 stale clones rescue-fetched into their authoritative repos under `refs/rescue-worktrees/<name>/*` then deleted (leto incl. codex/leto-real-sparse-lu); 13 gitdir-mirrors deleted — and regenerated within seconds: a live process on pre-fix instructions re-mints the mirror farm (signature: `.git` file -> `../../.git/modules/repos/<r>`, checkout on main). Self-resolves as sessions roll onto current instructions; re-audit the root then and delete survivors.
- Residuals: (1) `hephaestus-unary-math-parity` — git-less source snapshot with real unique deltas (6/12 sampled files differ from authoritative): reconcile into a branch of repos/hephaestus (diff, salvage, commit under the unary-math-parity item), then delete the snapshot; (2) `ritk-book-complete` — near-duplicate snapshot (11/12 identical): verify the delta, salvage if real, delete; (3) stale lanes `coeus` (codex/coeus-error-function-parity, 30h) and `mnemosyne` (codex/mnemosyne-tier-selection, 33h) — takeover material: complete their items or confirm branches landed, then remove the lanes; (4) fresh clones `aequitas`/`eunomia` left in place (regenerator-owned) — delete at re-audit.
- Re-audit 2026-08-14: Ritk is now compliant with two trees (`main` and
  `ritk-fix`) after `8a1c6ac`. The current probe reports four Kwavers
  violations: three trees, one detached temporary lane outside the canonical
  lane root, and the unlinked `worktrees/kwavers-cascade-provider-042`
  directory. The temporary checkout carries fresh unique `Cargo.toml` and
  `Cargo.lock` changes for the `ritk-image` 0.4.0 integration; the canonical
  lane carries dirty PM work. The empty unlinked directory was checked before
  removal, but Windows retained an open handle and refused deletion. No
  peer-owned work or unique state was removed; re-open deletion after the
  temporary owner releases or rescues its changes and the handle closes.

- Re-audit 2026-08-17: the live Kwavers tree is now the main checkout plus
  `worktrees/kwavers-doc557` at detached commit `df818b9a1`. The lane is clean
  but detached, so `python scripts/atlas-lane-audit.py` reports one violation.
  It remains peer coordination state; no branch switch or lane deletion is
  authorized until its owner reconciles the documentation run.
- The completed CFDrs Fourier/SSOR lane and Apollo public-plan lane were removed
  after their PRs merged; their local feature branches were deleted. The current
  audit therefore reports only the detached Kwavers documentation lane above.

## ATLAS-CFDRS-ATHENA-MIGRATION-001 — Stage B: CFDrs to Athena [major] [arch] — in-progress

Surveyed 2026-07-28 before starting. This is a redesign of the CFDrs
linear-solver architecture, not a port, and two of the mismatches change a
public CFDrs API — recording them rather than deciding unilaterally.

### Scale

56 files and 242 references across six crates (`cfd-1d`, `cfd-2d`, `cfd-3d`,
`cfd-core`, `cfd-math`, `cfd-validation`), of which **24 are production solver
construction sites** in 8 files; the rest are tests, benches, and re-exports.

`cfd_math::iterative` is currently a pure re-export of the `leto-ops` family
(`lib.rs:179`), so every consumer reaches the solvers through one facade.

### Structural mismatches

1. **Const-generic restart vs runtime config.** `Gmres<B, RESTART>` fixes the
   restart width at compile time. `LinearSolverChain` carries
   `krylov_restart: usize` as a runtime field with a builder
   (`with_krylov_restart`) and clamps it per solve:
   `min(self.krylov_restart, n_total_dof.max(1))`. A const generic cannot take
   that value. **Decision needed** (see below).
2. **Dynamic solver selection.** Four sites hold `Box<dyn LinearSolver<T>>`,
   including `cfd-validation` which builds a `Vec` of boxed solvers to compare
   CG against BiCGSTAB on the same system. Athena's solvers are ZST markers
   with static `solve_into`; `KrylovBackend` has GATs and `Gmres` a const
   generic, so none of it is dyn-compatible. The sanctioned replacement is
   enum dispatch over the closed solver set — I can decide this one, it is
   what the standards prescribe before reaching for `dyn`.
3. **Preconditioner trait.** CFDrs preconditioners — `AlgebraicMultigrid`,
   `BlockDiagonalPreconditioner`, `SimplePreconditioner`, `IncompleteLU`,
   `DiagJacobi` — implement `leto_ops::Preconditioner<T>`. Each needs an
   `athena_core::Preconditioner<LetoBackend<T>>` implementation instead.
   Mechanical, but touches every preconditioner.
4. **Caller-owned workspaces.** CFDrs solvers allocate internally per call;
   Athena requires a workspace owned by the caller and sized to the system, so
   every call site gains workspace lifetime management. This is the property
   that makes Athena allocation-free, so it is a real improvement rather than
   friction to work around — but it is a call-site change everywhere.
5. **Config to policy.** `IterativeSolverConfig { max_iterations, tolerance,
   relative_tolerance }` maps onto the validated `ConvergencePolicy`, which
   also carries a check interval and rejects invalid tolerances at
   construction. Mechanical.

### Decisions needed

**D1 — restart width.** Either (a) make `krylov_restart` a const parameter on
`LinearSolverChain`, a breaking change to a public CFDrs API; or (b) keep the
runtime field and dispatch across a small fixed set of `RESTART` instantiations
by enum, paying monomorphisation for each; or (c) fix one restart width and
delete the knob, checking first whether any caller sets it to a non-default
value. Recommend (c) if the knob is unused in practice, else (b).

**D2 — migration shape.** Either (a) convert all six crates in one change,
green only at the end; or (b) convert crate by crate while `cfd_math::iterative`
still re-exports `leto-ops`, deleting the facade last. (b) keeps the tree green
per commit and is not a shim — the old path stays only until its last consumer
is gone, which is what the anti-shim rule prescribes for a migration of this
size. Recommend (b), ordered `cfd-math` internals, then `cfd-2d`, `cfd-3d`,
`cfd-1d`, `cfd-validation`, then facade deletion.

### Not started

No CFDrs code changed. Nothing was added that would sit unused pending the
decisions above.

### Stage B progress 2026-07-28 — foundation landed, D1 corrected

**D1 was answered (c), and the check that answer depended on disproved it.**
`krylov_restart` is not an unused knob: `cfd-3d/fem/solver.rs` sets
`min(200, n)` at two sites, `cfd-1d/newton_fallback.rs` derives it from
`max_krylov_iterations`, and `cfd-math/nonlinear_solver/jfnk.rs` carries it in
its own config with 30 and 10 in tests and `min(n)` at runtime; the direct
`GMRES::new` sites use 30 and 100. Fixing one width would have silently
changed four solver configurations, so I took the fallback named in the same
decision — **(b), a fixed ladder with dispatch**.

- athena `f24dded`: `BorrowedCsrOperator`. `CsrOperator` takes ownership,
  which would force a per-solve `O(nnz)` sparse clone in a chain that tries
  several preconditioners against one system. Mirrors `BorrowedDenseOperator`.
- CFDrs `6a13a672`: `cfd_math::linear_solver::krylov` — the restart ladder
  (8/16/32/64/128/256, smallest covering width), `ConvergencePolicy`
  translation, and `gmres`/`gmres_preconditioned`/`bicgstab` entry points over
  Athena. Additive per D2(b): the `iterative` facade still re-exports leto-ops,
  so no consumer changed and the tree stays green per commit.
- Also repaired two cfd-math benches that had not compiled since `8aee5e59`
  left a stray brace in their imports.

Verification: cfd-math library compiles, clippy clean on the library, both
ladder cases pass, fmt clean. The package `--all-targets` gate is red for
reasons predating this change — unused imports and a dead struct in cfd-math
tests from the in-flight SSOT migration.

### Contention on the next increment

`chain.rs` is the next conversion target and a peer is **actively working in
it**: commit `16096fbc` ("resolve Quantity type mismatches in cfd-1d examples
and chain.rs") landed at 19:05 today and its rewrite of
`linear_solver/mod.rs` dropped the `pub mod krylov;` registration I had added,
leaving my file an orphan until I restored it. Converting `chain.rs` now would
collide directly.

Next increment should either wait for that scope to go quiet, or start at a
crate the peer is not in — `cfd-2d/src/physics/momentum/solver.rs` and
`cfd-2d/src/pressure_velocity/pressure.rs` are independent of `chain.rs` and
carry four of the twenty-four construction sites.

Remaining conversion order: `cfd-math` internals (`chain.rs`, multigrid),
`cfd-2d`, `cfd-3d`, `cfd-1d`, `cfd-validation`, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

Note for `cfd-validation`: four sites hold `Box<dyn LinearSolver<T>>` to
compare solvers on one system. Athena's markers are not dyn-compatible, so
that becomes enum dispatch over the closed solver set, per the standards.

### Stage B progress 2026-07-29 — cfd-2d converted

`58f6caab` momentum, `10fdd86e` pressure correction. cfd-2d is off the leto-ops
iterative family; the `cfd_math::iterative` facade still serves the other
crates, per D2(b).

- **Stateful solver objects removed.** Both consumers stored solver instances —
  `MomentumSolver` one GMRES, `PressureCorrectionSolver` three of which at most
  one was ever used, since `solver_type` already selected the recurrence.
  Athena solvers are stateless markers with caller-owned workspaces, so each
  collapses to the configuration it carried.
- **Triplicated policy consolidated.** `correction.rs` repeated the same
  solve-then-retry block verbatim per recurrence: solve with AMG, and on
  breakdown retry unpreconditioned, because a hierarchy built for a stale
  stencil can break the recurrence while the bare operator stays solvable.
  Written once now, with one dispatch over the closed solver set.
- **A real regression, caught and fixed at the right level.** Momentum assembly
  omits the diagonal of rows with no self-coupling. Athena's SOR rejects that;
  the leto-ops one had been *silently* defaulting those rows to a unit pivot.
  Rather than loosen the default, athena `461cdd5` added
  `from_csr_with_identity_rows` — same behaviour, opted into visibly at the
  call site, with a test pinning it.
- athena `f24dded` `BorrowedCsrOperator` removes a per-solve `O(nnz)` clone;
  the Athena SOR likewise borrows where the previous one took ownership, which
  matters because momentum rebuilds it after every coefficient update.
- `AlgebraicMultigrid` gained an Athena preconditioner implementation. Its
  V-cycle recurses over owned vectors while Athena passes borrowed views, so
  the boundary copies through cached buffers rather than allocating per
  application. Two `O(n)` passes against the cycle's `O(nnz)` sweeps.
  **Follow-up: rework the V-cycle onto slices to remove them.**

Verification: cfd-2d 570/571 nextest at both increments; the timeout is a
cross-fidelity tree test with no solver involvement that times out identically
without these changes. Clippy ran clean on the libraries for the first
increment; for the second it could not run — an in-flight `gaia` change removed
the `cfdrs-integration` feature cfd-2d depends on, breaking resolution for
unrelated reasons. **Re-run clippy on cfd-2d once gaia settles.**

## ATLAS-CODE-INDEX-001 — Search-ladder infrastructure for context economy [patch] — in-progress

- Owner: opencode-2026-08-05; scope: the atlas meta-repo and its `repos/*` members
  (tooling and generator contract only — no member Cargo.toml/manifest edits).
  Host tooling verified: `rust-analyzer` and nightly toolchain present; `ast-grep`
  absent (install is scope item 1).

- Policy: AGENTS.md context_and_memory "Code-search ladder". Motivation: 325 tool-output truncations and 66 compactions across eight recent fleet sessions — agents read where they should search; the fleet-recommended tools were researched and the ladder chosen over them where they misfit (agent-memory graph stores such as Graphiti duplicate the board/ADR/git memory layer and are rejected — one curated memory, one archive).
- Scope: (1) ast-grep availability as committed tooling (structural queries, stateless per tree — worktree-safe by construction); (2) SCIP emission per member repo (`rust-analyzer scip`), revision-keyed under a gitignored index directory with a generator-contract freshness check, plus a thin lookup wrapper (scip CLI) so agents resolve definitions/references without full-file reads; (3) rustdoc JSON as the machine-readable API oracle for the anti-hallucination check, emitted under the nightly verification toolchain like miri; (4) evaluate a Zoekt trigram server over the shared gitdirs only if per-tree tooling proves insufficient at fleet scale — standing infrastructure needs the toil-automation justification; (5) wire ladder usage guidance into each repo agent-facing docs if repo convention keeps local instructions.
- Acceptance: spot-check — an agent locates three symbol definitions and one API signature across repos it has not read this session using only ladder queries (no full-file reads); index freshness check green in the sweep.

## ATLAS-CFDRS-CHAIN-LADDER-001 — Consolidate the two tiered ladders [patch] — in-progress

`LinearSolverChain::solve` and `solve_with_state` run the same five tiers with
three deliberate differences: log prefix, an iterate reset between tiers, and
the warm path skipping the unpreconditioned tier once a block preconditioner
was built but stalled. Express the ladder once with those as parameters, and
decide explicitly whether the cold path should adopt the skip policy — it is
an improvement the warm path received and the cold one did not, and adopting
it changes which solver answers a given system.

Remaining stage B: cfd-3d, cfd-1d, cfd-validation, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (evening) — cfd-3d deferred, cfd-validation converted

**cfd-3d was not attempted.** Both its solver files were being edited live:
`crates/cfd-3d/src/fem/solver.rs` had a modification timestamp one minute
before I began, alongside 17 other dirty cfd-3d files from a peer's Quantity
migration. Editing there would have collided destructively, so the scope was
skipped rather than taken. **Re-open trigger: cfd-3d/src/fem goes quiet.**

Its two sites when it does: `projection_solver.rs` holds a `GMRES` and a
`ConjugateGradient` field, and `solver.rs` holds `_linear_solver: GMRES<T>` —
note the underscore, it is already dead and should be deleted rather than
converted. `solver.rs` also drives `LinearSolverChain`, which is already on
Athena.

**cfd-validation converted instead**, `f8634e43` — a clean, disjoint file.

- `Vec<(&str, Box<dyn LinearSolver<T>>)>` becomes `SolverKind`, the closed-set
  enum dispatch decided earlier. Athena's markers carry const generics and
  backend GATs and are not object-safe, so this was the one site that could
  not be a mechanical swap.
- Same correction `chain.rs` needed: Athena reports a stalled or broken-down
  solve in the report, not as `Err`, so a bare match would have **recorded a
  non-converged iterate as a validation result**.
- The split between fatal and tolerated failure is preserved deliberately: the
  ill-conditioned Hilbert case is expected to break down; the diagonal and
  Poisson cases are not.
- `SolverKind` lives in cfd-math beside the other entry points so the
  pressure-velocity dispatch can adopt it rather than keep its own match —
  **follow-up**.

Verification: `cargo check` clean for cfd-validation and cfd-math. Tests could
not run — `repos/hephaestus` is mid-rebase onto a branch four commits behind
master, so `hephaestus-core` does not compile in the shared tree. **Re-run the
cfd-validation suite once that settles.**

Note the compounding cost: three consecutive increments have now had a gate
blocked by shared-tree churn — clippy twice by `ATLAS-TOOLCHAIN-COHERENCE-001`,
tests once by a mid-rebase hephaestus. The verification debt is tracked, not
silently absorbed.

Remaining stage B: cfd-3d (blocked), cfd-1d, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (late) — cfd-1d converted

`4ca6518d`. The network solver's iterative tier is on Athena.

- The CG and BiCGSTAB arms were identical apart from the recurrence, so they
  collapse onto `SolverKind`. `LinearSolverMethod` stays as the domain-facing
  choice and maps onto it.
- `DiagJacobi` gained an Athena implementation that applies straight over the
  borrowed views — elementwise, so no scratch and no copy, unlike the AMG
  boundary which must buffer.
- The post-solve residual check is kept, with its reason now explicit: the
  solve runs on the **row-equilibrated** matrix, so meeting the tolerance
  there does not bound the residual of the original system. Athena reporting
  convergence is one of two acceptance conditions, not the only one.

Verification: cfd-1d **736/736** nextest including the primary-solve
reliability cases that exercise this path, `cargo check` clean.

### Correction to an earlier claim

I recorded after `40ef080c` that "cfd-math is fully off the leto-ops iterative
family". True as stated, but incomplete as an impression: `cfd-math`
`nonlinear_solver/jfnk.rs` carries its **own hand-rolled matrix-free
restarted GMRES** (`gmres_matrix_free`), which never used leto-ops. It is a
fifth GMRES in the stack after leto-ops, the deleted CFDrs copy, kwavers, and
Athena. Filed below.

## ATLAS-JFNK-MATRIX-FREE-GMRES-001 — Converge JFNK onto Athena [minor] — todo

- `cfd-math/src/nonlinear_solver/jfnk.rs` implements restarted GMRES inline for
  Jacobian-free Newton-Krylov, using only matrix-vector products.
- Migrating it needs Athena's `LinearOperator` over a Jacobian-vector closure.
  Check first whether that closure needs `&mut self` — if so it hits the same
  blocker as Kwavers stage C (`ATLAS-GMRES-FORK-CONVERGE-001`), and the two
  should be solved together rather than separately.
- `cfd-1d/src/solver/core/newton_fallback.rs:223` feeds `krylov_restart` into
  this config, so it is the last cfd-1d reference to a non-Athena solver.

Remaining stage B: cfd-3d (blocked on peer activity in `cfd-3d/src/fem`), JFNK,
then delete the `cfd_math::iterative` facade and the leto-ops iterative
dependency.

### Verification debt review 2026-07-30

**cfd-3d is still not clear.** Peer commit `63e49604` landed at 01:40, twelve
minutes before the check, and `projection_solver.rs` carries their uncommitted
continuation of the same Quantity migration (`.into_base()` conversions).
Fresh and commit-backed, so the scope stays blocked. `solver.rs` is clean now,
but it is the same live scope. Re-check later.

**cfd-validation tests: discharged.** The hephaestus rebase finished, so the
suite ran: **184/187 passed, 3 timed out** in
`numerical::venturi_cross_fidelity`.

Those three were investigated rather than assumed pre-existing, because they
drive `cfd_2d::solvers::ns_fvm` SIMPLE and could plausibly have been a
convergence regression from the pressure-correction migration. They are not:
`ns_fvm` solves its pressure-correction Poisson with **its own hand-rolled SOR
sweep** (`solvers/ns_fvm/solver/pressure/poisson.rs`), never reaching
`PressureCorrectionSolver` or any Krylov solver in this migration. Running one
case without a timeout shows SIMPLEC continuity stagnant at ~4.59e2 across ten
iterations and still running past 400s, which is that SOR failing to converge
on a micro-scale geometry. The file is also peer-dirty. Filed below.

**Clippy: still blocked**, third consecutive attempt, now surfacing on
`cfd-io` whose dependencies were built by a different rustc. Note the tests
passed minutes earlier under the same toolchain — the poisoned artifact set
differs by which crates a command pulls, which is exactly why this presents as
moving, unrelated breakage. `ATLAS-TOOLCHAIN-COHERENCE-001` is the blocker and
is now the single largest drag on verification.

## ATLAS-STACK-LETO-CHURN-017 — Upstream working-tree churn blocks consumer verification — todo

Third occurrence on 2026-07-31 of the same pattern, now costing real delivery
time, so it is recorded as its own item rather than re-diagnosed each session.

- **Symptom**: a consumer repo's `cargo check`/`nextest` fails inside
  `repos/leto` with errors that change between consecutive runs and reference
  code the consumer never touched.
- **Cause**: the stack `[patch]` overlay resolves first-party dependencies to
  local working trees, so a peer's *uncommitted, mid-edit* state in an upstream
  repo reaches every downstream consumer immediately. Observed today in
  `leto-ops/src/application/attention/` (cleared on retry) and
  `leto-ops/src/application/zip.rs` (still red; file modified seconds before
  each check).
- **Not a defect in either repo.** The overlay behaving as designed, plus
  normal peer activity. Same class as ATLAS-RITK-MODULE-FORWARD-000.
- **Cost**: any consumer increment depending on the churning crate cannot be
  verified, so it cannot be committed. ATLAS-COEUS-NLLS-004 parked on exactly
  this for roughly 25 minutes, clearing only when the peer committed `zip.rs`.
  The park was the correct call — the errors changed between consecutive runs,
  so retrying would have chased a moving target — but it is dead time that
  option (b) would remove.
- **Candidate directions, needing a decision rather than more diagnosis**:
  (a) accept it and treat upstream redness as a park-and-switch signal, which is
  current practice and what the contention response order already prescribes;
  (b) have the overlay resolve to each member's last *committed* revision rather
  than its working tree, making peer WIP invisible until committed — this is the
  real fix but changes the development overlay contract in
  architecture_scoping and needs an ADR;
  (c) narrow the overlay per session to the repos an agent actually edits.
  Option (b) is the recommendation: an uncommitted edit is not a published
  state, and the overlay currently makes it one for the whole stack.
- **Class**: `[arch]` if (b) is taken, since it revises the development overlay.
- **Fourth occurrence 2026-08-13 falsifies option (c).** Verifying one RITK
  branch, four consecutive attempts minutes apart each failed in a *different*
  upstream repo: `eunomia` (duplicate `PartialEq` — macro added before the
  manual impls were removed), `apollo-fft` (`BLUESTEIN_NATIVE_PHASE_TRIG` used
  in impls before the trait declared it), `eunomia` again (`FloatElement`
  gaining an `Accumulator` associated type, trait ahead of impls), and
  `consus-hdf5` (arity mismatch mid-signature-change). Every one is a normal
  half-finished edit; none is a defect.
  Option (c) assumed churn localizes to the repos an agent is near, so a
  narrowed overlay would dodge it. It does not: the churn was spread across
  four repos the RITK branch never touched, and narrowing enough to avoid them
  would exclude most of the stack, which defeats the overlay. That leaves (a)
  and (b), and (b) remains the recommendation.
  Retrying is also not free-but-harmless: because the failing crate *moves*,
  a green run is a peer-quiet window rather than evidence, so a consumer needs
  a retry loop that distinguishes upstream churn from its own redness before
  any result means anything.

## ATLAS-DMRI-IO-001 — Rank-generic acquisition-series I/O [minor] — in-progress

**Claim 2026-08-11 — Codex current session:** own the next vertical
`ritk-nrrd` increment on branch `codex/ritk-nrrd-series` in the reclaimed
`worktrees/ritk-book-wf` lane. Claimed files are the NRRD reader/writer,
their co-located tests, and the package-local documentation needed for rank-4
acquisition-series round trips. Non-goals are MGH, DICOM, `ritk-io` dispatch,
and the peer-dirty ADR index in the primary RITK checkout.

**Re-audit closure 2026-08-11:** no NRRD implementation was added because
`origin/main` already carries the complete `d3d3d811` series implementation:
leading and trailing acquisition-axis decoding, rank-4 writing, shared-grid
validation, and value-semantic tests. RITK PR #119 merged at
`0a1a4dc98ec541ea2caa952dd2385c9ebfac583b` with its hosted Rust, Python,
workspace-alignment, and platform test jobs green. The local `--locked` gate
was blocked before compilation by the separately tracked provider drift
(`hermes-simd` 0.5.0 and `moirai-runtime` 0.4.0 locks versus current provider
heads); RITK PR #118 owns the overlay-free release-lock repair. The NRRD
sub-scope therefore closes as an evidence-backed stale-gap correction, while
MGH, DICOM, and `ritk-io` dispatch remain open sub-increments of this item.

**`ritk-nifti` increment delivered** at `ritk` `2a4b1f62`, pushed to
`codex/perf-ritk-mgh-stream-book` (PR #78, a peer's branch — the scopes are
disjoint, `ritk-nifti` vs the peer's `ritk-mgh` streaming slice, so the increment
rides that branch per the shared-branch model rather than opening a second PR).

Rank 3 and rank 4 both parse; the payload byte range spans every declared volume
instead of one; `read_nifti_series` / `read_nifti_series_from_bytes` /
`write_nifti_series` / `write_nifti2_series` are the series surface. The writer
selects rank from the volume count, so a one-volume series stays a rank-3 file
byte-identical to `write_nifti`, and it validates that every volume shares one
grid rather than emitting a file whose sform covers only part of its content.
`read_nifti` and `read_nifti_labels` now name the volume count and fail on a
rank-4 file instead of decoding volume 0 — the MGH defect class, caught before it
could ship in a second codec.

Verified: 49/49 `ritk-nifti` (0.564s), 370/370 `ritk-io` + `ritk-analyze`
downstream, clippy `--all-targets -D warnings` clean, `RUSTDOCFLAGS=-D warnings
cargo doc` clean.

Design decision recorded here rather than an ADR, being reversible and internal:
the series surface returns `Vec<Image<f32, B, 3>>` rather than a new
`ImageSeries` domain type. Volumes on one grid is what the format states, it
needs no cross-crate public API, and it does not prejudge the type
ATLAS-DMRI-SCHEME-003 actually needs — which carries the gradient scheme
alongside the volumes and is where the per-voxel-across-volumes access pattern
will be known. A contiguous layout stays open behind that type.

Remaining sub-increments: `ritk-mgh` series read (currently fails loudly per
ATLAS-DMRI-MGH-FRAMES-002, so this is an extension not a fix), `ritk-dicom`
multi-frame/series assembly, and the `ritk-io` dispatch tail. The NRRD
increment is closed by `d3d3d811` on the merged RITK head.

## ATLAS-DMRI-IO-001 original specification

- **Outcome**: `ritk-nifti`, `ritk-nrrd`, and `ritk-dicom` read and write a
  series carrying an acquisition axis, and `ritk-io` dispatches it.
- **Evidence of gap at item creation**: `ritk-nifti/src/header/validate.rs:74`
  bailed on `dim[0] != 3`; `ritk-nrrd` rejected acquisition-series headers;
  and `ritk-io/src/lib.rs:164` fixed `NativeImage = Image<f32, NativeBackend,
  3>`. The NRRD rejection was closed by `d3d3d811`; MGH, DICOM, and dispatch
  remain the live gaps.
- **Non-goals**: no change to `Image<T, B, D>`, which is already rank-generic;
  no arbitrary-rank generalization beyond one acquisition axis.
- **Design note**: a DWI series is 3 spatial axes plus 1 acquisition axis, not a
  4-D image. `Point<4>`/`Spacing<4>`/`Direction<4>` would assert direction
  cosines over the acquisition axis, which is meaningless. The type carries 3-D
  spatial metadata plus a per-volume scheme (ATLAS-DMRI-SCHEME-003), so the
  metadata stays 3-D and only storage gains the axis.
- **Acceptance**: round-trip a synthesized N-volume series through each codec
  recovering voxels and spatial metadata exactly; the existing 3-D entry points
  keep their signatures and tests.
- **Class**: `[minor]` — additive public surface.
- **Sequencing note (2026-07-31)**: no longer split — the `ritk-io` block
  cleared when ATLAS-RITK-MODULE-FORWARD-000 resolved. The `ritk-nifti` and
  `ritk-nrrd` increments are now closed on `origin/main`. The next increments
  are the `ritk-io` dispatch tail and the `ritk-mgh` series extension; MGH
  already fails loudly on a multi-frame file per ATLAS-DMRI-MGH-FRAMES-002, so
  its series read is an extension rather than a defect fix.

## ATLAS-COEUS-NLLS-004 original specification

- **Evidence of gap**: `coeus-optim` ships `SGD`, `Adam`, `AdamW`, `RMSProp`,
  and `Adagrad` only — all first-order stochastic, sized for network training.
- **Why it blocks**: per-voxel diffusion fitting is millions of independent
  small dense residual problems. A damped Gauss-Newton step with an analytic
  Jacobian converges in single-digit iterations; a first-order stochastic
  optimizer is the wrong instrument by orders of magnitude. Log-linear DTI is
  unaffected — it routes through `leto-ops` (`pinv`, `qr_decompose`,
  `cholesky_solve`), which already exist.
- **Blocks**: DKI, NODDI, IVIM, free-water, and every other nonlinear model.
- **Acceptance**: batched over a leading problem axis; verified against an
  analytical oracle with a known minimum and against a published test problem
  set; convergence criterion is a derived relative-residual bound, never a fixed
  iteration count.
- **Class**: `[minor]`, repository `repos/coeus`.

## ATLAS-APOLLO-REALSH-005 original specification

- **Evidence of gap**: `apollo-sht` owns complex SH on Gauss-Legendre product
  grids. `infrastructure/kernel/spherical_harmonic.rs:234` exposes
  `spherical_harmonic(degree, order, theta, phi) -> Complex64`, so pointwise
  evaluation at an arbitrary direction already exists; the real, even-order,
  antipodally symmetric basis, the design matrix over a scattered direction set,
  and Laplace-Beltrami regularization do not.
- **Why Apollo and not RITK**: Apollo owns the transform bounded context. A
  RITK-local associated-Legendre or normalization path forks the SH dimension
  and is the exact failure mode ADR 0036 decision 2 exists to prevent.
- **Convention pinning**: the basis has several published orderings and
  normalizations (Descoteaux and Tournier differ). The implementation declares
  one, and a reference-case test asserts it against published coefficients.
- **Blocks**: every ODF/FOD model in `ritk-diffusion`.
- **Class**: `[minor]`, repository `repos/apollo`.

## ATLAS-DMRI-DENOISE-008 — MP-PCA denoising and Gibbs unringing [minor] — todo

- **Outcome**: `ritk-filter` gains Marchenko-Pastur PCA denoising and subvoxel
  Gibbs ringing removal — the `dwidenoise` and `mrdegibbs` roles, and the first
  two stages of every current dMRI pipeline.
- **Evidence of gap**: `ritk-filter` has bilateral, patch-based, median, rank,
  and anisotropic-diffusion denoising; none is the MP-PCA estimator, which
  derives its threshold from random-matrix theory rather than a tuned parameter.
  `ritk-statistics/src/noise_estimation.rs` is MAD over additive Gaussian noise —
  correct as written, but not the Rician/noncentral-chi model magnitude DWI
  actually follows.
- **Related**: Rician bias correction is a third item in the same crate, split
  out if MP-PCA outgrows its acceptance criteria.
- **Acceptance**: the MP-PCA threshold is derived from the Marchenko-Pastur
  distribution and the patch geometry, never an empirical constant; verified on
  a synthesized field with a known noise level.
- **Class**: `[minor]`.

## ATLAS-DMRI-CORRECT-009 — Motion, eddy-current, and susceptibility correction [minor] — review

**PR mapping (2026-08-01).** PR #82 grew to four commits and ~1,700 lines, past
a reviewable unit, and also carried four unrelated JPEG 2000 commits inherited
from its base. Split into four PRs cut fresh from `origin/main`, each verified
standalone; #82 closed. References to "PR #82" below predate the split.

| PR | Scope | Base | Standalone verification |
| --- | --- | --- | --- |
| #84 | `ritk-diffusion-scheme` per-volume reorientation | `main` | 23/23 |
| #85 | `ritk-spatial` rotation extraction | `main` | 54/54 + doctest |
| #86 | `ritk-registration` series alignment | **#85** | 352/352 |
| #87 | `ritk-registration` EPI distortion model | `main` | 367/367 |

#86 targets #85 because it consumes `rotation_from_linear`; GitHub retargets it
to `main` on merge. The other three are independent and may merge in any order.

The split was done in a bounded worktree lane rather than the main tree, which
was dirty with peer edits — branch switches there had been aborting. The lane is
deregistered; its directory at `worktrees/ritk-pr-split` could not be deleted
(held by another process) and needs sweeping once that releases.

**Scheme-side reorientation delivered**: `ritk` `660783da` on
`feat/per-volume-gradient-reorientation`, PR #82.
`GradientScheme::reorient_per_volume` applies one rotation per volume in
acquisition order, with an exact count match and whole-list validation before
any rotation is applied. 22/22 `ritk-diffusion-scheme` tests, clippy and doc
gates clean.

A peer had already landed the single-rotation `GradientScheme::reorient` and the
FSL codecs in `ritk-diffusion-scheme`. That method applies one rotation to the
whole scheme — correct for a fixed frame change, unusable for correction, where
each volume is registered independently. Nothing in the workspace called
`reorient` at all before this.

**Remaining, in dependency order:**

1. ~~**Rotation extraction from an affine.**~~ **Delivered**: `ritk` `216f21f7`,
   same branch and PR #82. `ritk_spatial::rotation::rotation_from_linear`
   returns the orthogonal polar factor.

   Placement resolved to `ritk-spatial`, and the open question dissolved on
   inspection: `ritk-spatial` already depends on `leto`, so there was no new
   dependency to weigh. The operation is geometry rather than diffusion, and its
   consumers (gradient reorientation, tensor and ODF reorientation, resampled
   grid orientation) all already depend on that crate.

   **Numerical finding worth keeping.** The eigen route alone
   (`S = (AᵀA)^{1/2}` via leto's `symmetric_eigen`) is least accurate at the
   input that matters most: when `A` is already a rotation, `AᵀA = I` has a
   triple eigenvalue and the analytic cubic derives eigenvectors from cross
   products of a near-zero matrix. Measured drift was ~3.8e-9 — *above* the
   1e-9 orthonormality bar `reorient_per_volume` enforces, so the undistorted
   case would have been rejected downstream. One Newton step of Higham's polar
   iteration (`X ← ½(X + X⁻ᵀ)`) is a fixed point at an exactly orthogonal
   matrix and converges quadratically, restoring machine precision. Any future
   consumer of `symmetric_eigen` on a near-degenerate matrix faces the same
   thing.

   Reflections are rejected rather than repaired to the nearest proper rotation:
   the Kabsch sign flip suits fitting to noisy point correspondences, but a
   handedness reversal between two images of one subject means the transform is
   wrong, and repairing it would hide the defect.
2. ~~**The series correction driver**~~ **Delivered**: `ritk` `4633b5e3`, same
   branch and PR #82. `ritk_registration::series::register_series` fits each
   volume to a reference and reports the transform plus the proper rotation it
   carries. The `ritk-io` gate cleared — a peer landed
   `read_image_series_native`.

   **Layering decision.** The module carries no diffusion vocabulary. Motion
   correction is the same operation whether volumes vary by gradient,
   timepoint, or inversion time, and a diffusion consumer depends on
   registration rather than the reverse. `SeriesAlignment::rotations()` returns
   exactly the shape `GradientScheme::reorient_per_volume` consumes, so the two
   compose without `ritk-registration` ever depending on
   `ritk-diffusion-scheme`.

   **Two contract choices worth keeping.** The reference is assigned the
   identity rather than registered to itself — self-registration returns a
   near-identity fit perturbed by optimizer noise, injecting a spurious rotation
   into the one volume known to need none. Its `quality` is `None` rather than a
   zeroed metrics struct, which would claim a mutual information and correlation
   of zero for a registration that never ran.

   Rigid is the default model: it cannot deform anatomy, so a caller who has not
   considered eddy currents does not silently receive a shape-changing fit.
   `SeriesTransformModel::Affine` admits the extra freedom eddy-current
   distortion needs.

   **Not yet wired end to end.** `register_series` reports what moved; applying
   the transforms to resample the volumes is the caller's step and no composed
   `correct_diffusion_series` entry point exists. That composition belongs with
   the diffusion consumer and is the natural next increment once
   `ritk-diffusion` settles.
3. **Susceptibility distortion** — the `topup` role. **Model delivered**:
   `ritk` `3042601f`, same branch and PR #82.
   `ritk_registration::epi::{distort, unwarp}` with `PhaseEncoding`
   (axis + polarity). The forward model is what field estimation later fits
   against; `unwarp` solves the observed-to-true map per line rather than
   assuming small displacements, so the round trip is exact.

   Convention pinned in the module docs (per numerical_discipline): for field
   `f` in voxels and polarity sign `s`,
   `observed(y) = true(y + s·f(y)) · |1 + s·∂f/∂y|`. Toolchains differ here, so
   it is stated rather than assumed.

   A folding field is rejected, not clamped: where the Jacobian reaches zero,
   distinct true positions map to one observed position and their signal is
   summed, which no unwarping separates.

   **Two test-oracle corrections worth keeping**, both cases where the first
   assertion was wrong rather than the code:
   - Signal conservation is an identity over the *mapped* range, not the grid.
     A ramp field with non-zero boundary value stretches the domain and
     legitimately raises the grid total — measured at exactly 10% for slope
     0.1, which is the Jacobian working. The test now uses a
     boundary-vanishing field, where the map is onto the grid and conservation
     is exact.
   - The warp/unwarp round trip cannot be exact on a step edge: two linear
     interpolations do not reconstruct a discontinuity. That is a property of
     resampling, not of the model. The test uses a linear image, which linear
     interpolation reproduces exactly, isolating the geometry and Jacobian
     bookkeeping.

   **Remaining**: field *estimation* from a reversed-polarity pair. That is a
   regularized nonlinear fit over a field parameterization (spline coefficients
   or per-voxel with a smoothness penalty) — thousands of parameters, so the
   dense `coeus-optim` Levenberg-Marquardt from ATLAS-COEUS-NLLS-004 is the
   wrong instrument and a large-scale or sparse-Jacobian path is needed first.
   Size and owner of that solver is an open question, not a scheduled item.

**Acceptance oracle is still unbuildable here.** ADR 0036 verification condition
7 needs a synthesized anisotropic tensor field fitted after correction, which
needs `ritk-diffusion`'s tensor fit — peer-owned and in flight. The tests in
PR #82 verify the reorientation contract directly (per-volume indexing, the
`R`/`Rᵀ` round trip that catches a transposed application, rejection of
non-orthonormal and improper matrices); the end-to-end eigenvector oracle
attaches once the tensor fit lands.

## ATLAS-DMRI-CORRECT-009 original specification

- **Outcome**: a series-level correction driver in `ritk-registration` — the
  `eddy` and `topup` roles.
- **Present**: rigid, affine, B-Spline FFD, Demons, SyN, and LDDMM registration
  all exist; `ritk-filter/src/bias/n4` covers B1 bias. The registration machinery
  is not the gap.
- **Gap**: (a) no driver that registers volume-to-volume across an acquisition
  axis, which ATLAS-DMRI-IO-001 gates; (b) **no gradient reorientation** — the
  rotational part of each correction must be applied to that volume gradient
  direction. A correction that omits this yields a silently wrong tensor field
  and is the most common defect class in this domain; (c) no
  susceptibility-distortion path (reversed-phase-encode fieldmap estimation).
- **Acceptance**: ADR 0036 verification condition 7 — a synthesized anisotropic
  tensor field rotated by a known transform recovers its principal eigenvector
  after correction, and the same test fails when reorientation is skipped.
- **Class**: `[minor]`.

## ATLAS-RITK-FSSURF-013 — FreeSurfer surface formats and label table [minor] — todo

- **Outcome**: RITK reads the FreeSurfer surface family — surface binaries
  (`lh.white`, `pial`, `inflated`), `curv`, `label`, `annot` — plus the color
  LUT, and GIFTI as the interchange equivalent.
- **Evidence of gap**: `ritk-mgh` covers FreeSurfer *volumes* only; no surface,
  annotation, or LUT reader exists in the workspace.
- **Why it is a prerequisite, not an optional format**: surface parcellations are
  how connectome nodes are conventionally defined, so ATLAS-RITK-CONNECTOME-012
  depends on it.
- **Deletion ledger** (promotion-gate condition 4, satisfied): the FreeSurfer
  `aseg` and Desikan `aparc` label table is hand-rolled in a downstream consumer
  at `repos/leoneuro-rs/crates/leoneuro-gui/src/freesurfer.rs` (137 lines). The
  RITK owner first increment deletes it and repoints that consumer.
- **Open**: CIFTI is deferred until a consumer needs HCP-convention data.
- **Class**: `[minor]`.

## ATLAS-DMRI-TRACTOGRAM-FMT-014 — Tractogram container ownership [arch] — todo

- **Decision needed**: MRtrix `.tck`, TrackVis `.trk`, and TRX are published
  byte-level interchange specifications, which is the RITK format-crate pattern;
  ADR 0036 decision 2 routes derived-array persistence to Consus. The two rules
  point at different owners for the same artifact.
- **Recommended resolution** (per bias-to-completion, proceed on this unless
  overridden): an interchange format that other toolchains read is a RITK format
  crate; a derived-array store for Atlas-internal persistence is Consus. A
  streamline set written for MRtrix or TrackVis to read is interchange.
- **Also open**: MRtrix `.mif` / `.mif.gz`, which is both an image container and
  an embedded gradient-scheme carrier, so it spans 001 and 003.
- **Deliverable**: ADR 0036 revision recording the resolution, or a new ADR if it
  generalizes beyond this artifact.
- **Class**: `[arch]`, no public-surface break — `[patch]` on the SemVer axis.

## ATLAS-CFDRS-LINT-FLOOR-001 — Adopt canonical Atlas lint floor in CFDrs workspace [patch] — in-progress

- Owner: current session; scope: `repos/CFDrs/Cargo.toml` top-level
  `[workspace.lints]` block and per-site `#[expect]` ratchet insertions
  across `crates/cfd-*/src/**` and `xtask/src/**`.  Claimed 2026-08-06.
- Outcome: CFDrs `Cargo.toml` carries the canonical Atlas `[workspace.lints]`
  floor matching `repos/apollo/Cargo.toml` L88-L107 (template SSOT):
  `[workspace.lints.rust] missing_docs = "warn"` (warn floor; `#![deny(missing_docs)]`
  is the per-crate strict escalation choice, not set workspace-wide so existing
  crates without missing-docs discipline stay warning-only until per-crate
  promotion). `[workspace.lints.clippy]` adopts apollo's `all = warn, prio -1` +
  `pedantic = warn, prio -1` and the same `allow` set (`module_name_repetitions`,
  `must_use_candidate`, `similar_names`, `too_many_lines`,
  `default_constructed_unit_structs`, `doc_lazy_continuation`,
  `needless_range_loop`, `too_many_arguments`, `manual_is_multiple_of`,
  `manual_div_ceil`, `manual_slice_size_calculation`, `len_zero`,
  `cast_possible_truncation`, `cast_precision_loss`, `cast_sign_loss`,
  `cast_possible_wrap`, `items_after_statements`, `range_minus_one`,
  `default_trait_access`, `useless_conversion`). Adds the Atlas-canonical library
  hygiene `deny` tier (`unwrap_used`, `print_stderr`, `print_stdout`,
  `dbg_macro`) so consumer-tree library and CLI crates enforce the same floor
  kwavers/helios/apollo already carry — `#[expect]` permitting pre-existing
  sites to remain on a non-increasing ratchet baseline, not silent `allow`.
- Scope: idempotent bulk `#[expect(lint, reason="ratchet cfd-<crate>-<count>")]`
  insertion per violation emitted by `cargo clippy --all-targets
  --workspace --json -- -D warnings -W clippy::pedantic
  -W clippy::unwrap_used -W clippy::print_stderr -W clippy::print_stdout
  -W clippy::dbg_macro`. **Mechanical transform only** per `git_discipline`:
  no logic edits, no refactor, no removed `println!` from `xtask` at large —
  per-site `#[expect]` carries the ratchet signal for future root-cause work.
- Non-goals: no public-API rewrites, no `print!` removal from `xtask` source
  (xtask is a build tool, not a library; per-site `#[expect]` preserves the
  ratchet signal per `engineering_gates` brownfield rule), no logic fixes for
  surfaced `unwrap_used` (the ratchet baseline only decreases — a future
  root-cause slice removes the offending `unwrap` and its `#[expect]` together).
- Disjoint from peer's `ATLAS-CFDRS-ATHENA-MIGRATION-001` chain.rs scope:
  peer's last chain.rs touch was 2026-07-30 (`63e49604`); 7+ days stale,
  reclaimable takeover material. Converge-friendly by construction — `#[expect]`
  is semantics-preserving against any in-flight peer chain.rs work; if peer
  pushes new chain.rs commits during this slice, fall through `concurrent_agents`
  Detect-and-reconcile (compose around peer's diff).
- Lane: reclaimed per-repo 2-tree cap slot by removing the post-merge
  `codex/cfdrs-audit-refresh` worktree lane (peer's PR #327 fully merged at
  `50fa243b`, lane = `D:/atlas/worktrees/CFDrs-audit-refresh` exactly at peer's
  merged tip, tree clean) and adding `feat/cfdrs-lint-floor` lane off
  `origin/main 50fa243b`.
- Acceptance: `cargo clippy --all-targets --workspace -- -D warnings
  -W clippy::pedantic -W clippy::unwrap_used -W clippy::print_stderr
  -W clippy::print_stdout -W clippy::dbg_macro` rc=0; `cargo nextest run
  --workspace` rc=0 (or reduced focused subset if workspace test suite
  budget blocked per `engineering_gates` runtime budgets — root-cause
  any hang, never bypass); `cargo test --doc --workspace` rc=0; `cargo fmt
  --all --check` rc=0.
- Re-open trigger: a new lint violation reaches `repos/CFDrs/origin/main`
  past the floor without an accompanying `#[expect]` carrying its ratchet
  rationale; or the floor is removed/relaxed in `Cargo.toml`.
- Residual recorded, NOT closed in this slice: per-repo `backlog.md` and
  `gap_audit.md` entries for CFDrs lint-floor closure; CFDrs-level
  per-crate `#![deny(missing_docs)]` promotion is deferred to a later
  per-crate slice (each crate's surface decides its own missing-docs tier).
- Current CFDrs increment: commit `cd9580fc` on pushed branch
  `feat/cfdrs-lint-floor` wires every workspace package and `xtask` to the
  floor, removes the cfd-core plugin resolver unwrap, and records the local
  PM state. Evidence: focused `xtask` and cfd-core library Clippy pass;
  cfd-core Nextest 246/246; cfd-core doctests 3/3; explicit migration audit
  reports zero legacy dependencies, zero legacy source tokens, and a clean
  allowlist. Full workspace acceptance remains open on the recorded
  cfd-math, cfd-schematics, cfd-core test/bench, and format debt.
- Follow-up CFDrs commit `e3e88a60` is pushed on the same branch: multigrid
  coarsening now uses deterministic NaN-safe ordering, with a value-semantic
  regression test. cfd-math Nextest passes 198/198; focused cfd-math library
  Clippy residue decreases from 51 to 48 diagnostics.
- Follow-up CFDrs commit `f31176b1` is pushed: multigrid hierarchy and
  interpolation state use invariant-checked expectations, while JFNK and
  spectral kernels centralize C-contiguous storage assumptions. cfd-math
  Nextest remains 198/198; focused library Clippy residue is 22 diagnostics.
- Follow-up CFDrs commit `9e52454a` is pushed: performance-monitor mutex and
  calibration output now use invariant diagnostics and tracing, and DG progress
  output is structured tracing. cfd-math library Clippy and Nextest pass;
  workspace closure still has cfd-schematics, cfd-core test/bench, and format
  debt.
- Follow-up CFDrs commit `c83affee` is pushed: the exported
  `cfd-schematics::topology::model` contract now documents its types, fields,
  variants, aliases, and lookup methods. cfd-schematics library Nextest passes
  164/164 and doctests 16/16; package Clippy residue decreases 712 to 611.
- Follow-up CFDrs commits `ddc04a32` and `8584dd26` are pushed: configuration
  constants, public config manifests, and the route-spec contract now carry
  API documentation. cfd-schematics library Nextest remains 164/164 and
  doctests 16/16; package Clippy residue decreases 611 to 534.
- Follow-up CFDrs commit `322787ae` is pushed: the public node and channel
  geometry-builder setters now carry API documentation. cfd-schematics library
  Nextest remains 164/164 and doctests 16/16; package Clippy residue decreases
  534 to 524.
- Follow-up CFDrs commit `eae43768` is pushed: geometry-generator metadata,
  entry points, and builder methods now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; package Clippy residue
  decreases 524 to 508.
- Follow-up CFDrs commit `c0d53bd5` is pushed: series and parallel geometry
  generators now carry API documentation. cfd-schematics library Nextest
  remains 164/164 and doctests 16/16; this slice reduces its package Clippy
  residual from 508 to 506. The working tree reports 492 with peer-owned
  `analysis_impl.rs` documentation changes also present and uncommitted.
- Follow-up CFDrs commit `f27f86dd` is pushed: selective-tree path, topology,
  request, and generator contracts now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; this slice reduces the
  package Clippy residual from 506 to 468. The working tree reports 454 with
  the peer-owned `analysis_impl.rs` documentation changes still uncommitted.
- Follow-up CFDrs commit `468cc617` is pushed: the `NetworkBlueprint` analysis
  impl (`crates/cfd-schematics/src/domain/model/blueprint/analysis_impl.rs`)
  now carries inline Rustdoc for its 14 undocumented pub methods (node/pipe
  counters, length aggregates, Venturi lookup, overlap analysis/resolution,
  validate, describe). cfd-schematics library Nextest remains 164/164 and
  doctests 16/16. File-disjoint from peer commits on the same branch per
  `concurrent_agents` disjoint-scope rule; peer's prior bullet had already
  flagged this `analysis_impl.rs` work as the uncommitted peer residual, and
  the slice now closes that residual. cfd-schematics distinct missing_docs
  sites in `analysis_impl.rs` fall from 14 to 0; crate-wide distinct
  sites fall from 468 to 454.
- Follow-up CFDrs commit `357debf3` is pushed: the `NetworkBlueprint`
  metadata impl (`crates/cfd-schematics/src/domain/model/blueprint/metadata_impl.rs`)
  now carries inline Rustdoc for its 19 undocumented pub methods/associated
  functions covering the deprecated default constructor, the
  explicit-position constructor, render-hint and metadata builders/accessors,
  topology and lineage attachments, JSON (de)serialization, and
  node/channel addition methods. cfd-schematics library Nextest remains
  164/164 and doctests 16/16. File-disjoint sibling of the just-merged
  analysis_impl.rs closure in the same `domain/model/blueprint/` subtree,
  owned by this session; no peer commits touched this file.
  cfd-schematics distinct missing_docs sites in `metadata_impl.rs` fall
  from 19 to 0; crate-wide distinct sites fall from 454 to 435.

## ATLAS-CFDRS-CI-WORKSPACE-RUST-001 — Add Rust workspace CI gate to CFDrs [patch] — in-progress

- Owner: current session (claimed 2026-08-10). Pairs with
  ATLAS-CFDRS-LINT-FLOOR-001 to make the floor mechanically enforced.
- Outcome: CFDrs `.github/workflows/ci.yml` carries a `rust-workspace` job
  that runs `cargo check --workspace --all-targets`, `cargo nextest run
  --workspace` (or `cargo test --workspace --no-fail-fast` fallback gated
  on `nextest` install via `taiki-e/install-action`), `cargo clippy
  --all-targets -- -D warnings`, `cargo fmt --all --check`, `cargo test
  --doc --workspace`. Mirrors `.github/workflows/ci.yml` patterns in
  `repos/apollo`, `repos/hephaestus`, `repos/helios`, and `repos/kwavers`.
- Scope: `.github/workflows/ci.yml` only; disjoint from peer's helios/ritk
  release-workflow consolidation `ci/migrate-release-workflow-to-shared-caller`.
- Acceptance: the new job runs in CI on the next PR; `cargo check --workspace
  --all-targets` and `cargo clippy` fail on a regression injected locally.
- Re-open trigger: the rust-workspace job is removed or its gate commands
  are weakened below the canonical Atlas floor.
- Dependency: ATLAS-CFDRS-LINT-FLOOR-001 must land first (or in the same
  PR) so `cargo clippy -- -D warnings` does not fail at the ~160 pre-existing
  baseline. Sequence behind it.

## ATLAS-MOIRAI-DEFAULT-REFRESH-2026-08-18 — reconcile fetched provider default

- Status: complete. Moirai hosted Rust Workspace run `32175287434` and Python
  Bindings run `32175287255` both completed successfully at provider default
  `6a98f3f7bd834f46c8120c291362eb260f6cf875`.
- The Atlas `repos/moirai` gitlink advances to that exact fetched `origin/main`
  commit. The primary Moirai checkout remains peer-dirty and is not modified.
- This is a pointer/PM reconciliation only; it does not claim that the live
  Moirai SeqCst audit or peer-owned source work is complete.

## ATLAS-FINAL-PROVIDER-AUDIT-2026-08-18 — exact residuals

- The pushed Atlas root passes the committed lock-form audit: 27 locks resolve
  standalone, with only the sanctioned Melinoe in-tree fixture exempted.
- The exact-head structural audit for the requested provider set has two
  residuals: Consus gitlink `34b2507` versus provider `origin/main` `ef439b2`
  (the merged shuffle correction's unverified default), and Mnemosyne gitlink
  `1c38a1a` versus provider `origin/main` `638ddab`. Consus default CI,
  Documentation, and Pages runs `32184845212`, `32184845179`, and
  `32184843457`, and Mnemosyne CI `32183974171`, are queued. Neither pointer
  is silently advanced.
- The clean-checkout audit remains red only on peer-owned moving or dirty
  checkouts, including Themis, Tyche, Proteus, Consus, Helios, Harmonia,
  Eunomia, RITK, Melinoe, Leto, Hephaestus, Coeus, Apollo, Hermes, and Iris.
  The lane audit records six live peer violations across CFDrs, Coeus, Consus,
  Kwavers, and RITK; one clean, merged Kwavers orphan lane, one clean, merged
  CFDrs lane, and two clean, merged RITK lanes were removed after verifying
  empty status, while peer dirty checkouts and live lanes were preserved.

## ATLAS-CONFORMANCE-LINT-TABLE-2026-08-18 — correct nested workspace-lint detection

- Status: complete in root commit `eaa32fd`.
- The conformance detector now recognizes valid nested
  `[workspace.lints.rust]` and `[workspace.lints.clippy]` tables; it no longer
  reports Aequitas or Apollo as missing workspace lint inheritance. The
  committed baseline was regenerated for this detector change from the
  recorded provider objects; only Coeus and RITK retain this class.
- The regression test covers a nested table and the conformance unit suite
  passes 12/12. Provider source, locks, and peer checkouts were not changed.

## ATLAS-KWAVERS-DEFAULT-RECHECK-2026-08-18 — moving default remains open

- Kwavers PR #400's orphan-module cleanup is merged at
  `23f53284d789ba9b15788b51b3e83e40d301caf3`; its formatting prerequisite PR
  #403 is merged at `15c12732f5841125a5d65b6c3da2adc0f7c0793a`. The clean
  `kwavers-orphan-096` lane had no uncommitted state and was removed; its
  branch ref remains recoverable.
- The provider default now includes the Atlas wheel-parity closure at
  `e6fb53b90798f498e87d2c1fed275944a5cbe4b6`. Hosted run `32237250724`
  passes the complete wheel matrix and installed-wheel k-Wave comparator at
  its preceding source head `56bded6fa`; the Atlas pointer advances to the
  documented current default for exact-head coherence.
- PR #402 is not the current default proof: it is open at
  `d8886b032c50c7ebbcc2f12ebaceacabe95e19f1` with `mergeStateStatus=CONFLICTING`.
  Its earlier `69478221f` evidence is stale. Re-open the consumer integration
  and pointer advance only after the peer-owned branch is reconciled or the
  provider default independently satisfies the hosted matrix.

## ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-18 — moving default remains open

- Mnemosyne `origin/main` advanced to
  `43cdf04769d4ab8701dea657b282c4a189175d48`. The Atlas gitlink remains at
  the previously verified `64f0d2ebe58e14705ca2345cad2c705f99a6b611`.
- Default CI run `32206977029` has Rust verification, Rust 1.95, Loom,
  aarch64, and ThreadSanitizer successful; Miri remains in progress. Do not
  advance the pointer until that exact default-head run completes; the
  peer-dirty primary checkout remains untouched.

## ATLAS-MNEMOSYNE-DEFAULT-RECHECK-2026-08-19 — moving default remains open

- Mnemosyne `origin/main` advanced again to `baf4f235d2b04db2d6a9203dbc38b3f39aa12fa2`
  with `fix(mnemosyne-core)!: Make the pool stack's node link atomic`.
- The exact default-head CI run `32281506800` and MSRV run `32280939845` are
  queued; the preceding run at `baf4f23` was cancelled before verification.
- Atlas remains at the last verified Mnemosyne pointer `d00f139e`. Advance only
  after the exact default-head Rust and MSRV evidence completes; preserve the
  peer-owned provider checkout and its lockfile dirt.

## ATLAS-LIVE-HEAD-SWEEP-2026-08-18-2055 — exact-head residual refresh

- Consus `origin/main` advanced to
  `ef439b2f5668b90fdbbed7097c3c6a44143c6ce4`, which contains the shuffle
  correction. Its CI, Documentation, and Pages runs `32184845212`,
  `32184845179`, and `32184843457` are queued. Atlas remains at the previously
  verified `34b25075` until those exact default-head gates complete; PR #46 is
  still open and conflicting against its former base.
- Mnemosyne remains a moving default residual at `638ddab` with CI
  `32183974171` queued; Atlas remains at `1c38a1a`.
- RITK PR #173 and CI-skip PR #172 are merged into provider default
  `0f0b5c5689a58a35fde30f07c62b7d94f5495004`, and Atlas now records that
  pointer. Its CI and Python CI runs `32184697093` and `32184697087` are
  queued, so hosted verification is pending even though exact-head equality
  holds.
- The clean merged CFDrs `cfd2d-fix` lane and clean merged RITK PR #173 and
  PR #168 lanes were removed after empty status checks; their branch refs
  remain available. Dirty runtime/lock lanes and open or peer-owned lanes
  remain.

## ATLAS-INTEGRATOR-HEAD-2026-08-19 - exact integrator audit checkpoint

- Root commit `bd79803` extends the exact-head and clean-checkout audit scope
  to CFDrs, Kwavers, and Helios. The live `atlas-22` exact-head audit passes:
  all 22 provider gitlinks and all three integrator gitlinks match fetched
  default heads, and the requested-provider coherence scope is clean.
- CFDrs is recorded at merged default `931ee3a0130a5238461a1ee9547e12aef11e90bf`.
  Hosted run `32221669165` passes the Rust workspace gate and the book-figure
  gate. A standalone `cargo package --locked` remains blocked before
  packaging by the Atlas development-overlay lock mismatch; this is not
  treated as package evidence.
- Root fast scripts pass: 234 tests, 17 deselected, and 74 subtests. The
  stack overlay and 27 committed standalone lock forms also pass. The clean
  checkout audit and lane audit still report peer-owned checkout dirt and
  excess lanes; those trees remain untouched. Apollo's benchmark regression,
  Kwavers' missing local Python extension, and Helios H-103 remain open.

## ATLAS-CFDRS-HOSTED-2026-08-19 — exact default-head evidence

- CFDrs default `931ee3a0130a5238461a1ee9547e12aef11e90bf` passes hosted run
  `32222487306`: Rust workspace format, check, Clippy, tests,
  numerical-fidelity tests, doctests, and native fontconfig setup all pass;
  the figure SSOT job also passes.
- Provider PM synchronization is pushed as `f601d827` on PR #357. Its hosted
  checks are in progress; no result is claimed from that new docs-only head.
  Pages deployment, PyPI release dry-run, and standalone locked package
  evidence remain separate open gates.

## ATLAS-CFDRS-JFNK-OPEN-033-2026-08-19 — provider source closure complete

- CFDrs PR #358 carries provider commit `0a5076c6034d735dd23d63a91453fea7d63702d0`:
  `cfd-1d` now reaches the retained Newton/JFNK fallback from the live solver
  graph, derives the recovery budget from `SolverConfig.max_iterations`, and
  propagates callback failures through checked JFNK evaluation.
- Hosted run `32225861309` reached the compiler and exposed the missing
  `FnMut` bound for the workspace-reusing residual closure. Provider commits
  `bc18b095` and `5e13018a` changed the checked JFNK seam to accept mutable
  callbacks, corrected the constructor field order, and retained the value
  regression. Replacement run `32229463775` passes the Rust workspace and
  figure SSOT gates. PR #358 merged at provider default `834340f7`; Atlas now
  tracks that exact merged head.

## ATLAS-HELIOS-H103-2026-08-19 — recheck stale documentation residual

- Helios merged checkout `f8ebe42f2a9c72f9da177cf5f96e15029b8a6d54` now passes
  `mdbook test docs/book` across every listed chapter and example. The prior
  H-103 failure description is stale at this head; no provider source change
  is required from the Atlas audit.
- The Helios primary checkout remains detached with peer-owned
  `crates/helios-python/Cargo.toml` dirt, and its sole lane is occupied by a
  peer Apollo-lock task. Preserve both trees until the owning work completes.
## ATLAS-KWAVERS-DELIVERY-2026-08-19 — wheel and book gate closure

- Kwavers commit `261fe8cf8` adds the existing
  `crates/kwavers-python/tests` suite to the shared Python-wheel workflow and
  enables `mdbook test` in the shared Pages workflow. The commit is pushed to
  `origin/main`; Atlas tracks it at root commit `3ed3813`.
- The exact-head provider audit, stack overlay, 27 standalone lock forms,
  board lint, and 234 fast root script tests pass after the pointer advance.
- The peer-owned untracked `docs/ADR/111-retire-kzk-solver-plugin-surface.md`
  remains untouched; the comparative K-Wave validation gap remains separate.

## ATLAS-KWAVERS-METADATA-2026-08-19 — Python surface consistency

- Kwavers commit `e62d529e6` removes the unused workspace `pyo3` ABI3
  declaration, keeps the binding and release floor consistently at Python 3.8,
  repairs the Python documentation URL, and makes Pages rebuild on source and
  manifest changes. Atlas tracks it at root commit `a2f46dc`.
- `cargo fmt --all -- --check`, `git diff --check`, and locked metadata
  inspection pass. The provider `cargo check -p kwavers-python --locked` is
  blocked before compilation by the shared Atlas overlay requesting lockfile
  updates for unused local patches; no source failure is inferred.

## ATLAS-CFDRS-JFNK-RERUN-2026-08-19 — hosted infrastructure retry

- Replacement run `32226998372` first failed in the runner's native-fontconfig
  setup after three bounded `apt-get` attempts against unreachable Ubuntu
  mirrors; no Rust or JFNK diagnostic ran. The failed job was rerun and is
  currently executing at the same provider head `bc18b095`.
- Atlas remains at CFDrs default `931ee3a0`; no hosted source result is claimed
  until the rerun reaches the Rust and figure gates.

## ATLAS-CFDRS-JFNK-MERGE-2026-08-19 — exact-head hosted closure

- CFDrs PR #358 merged at `834340f7` after required Rust workspace and figure
  SSOT checks passed in run `32229463775`. The Atlas gitlink advances from
  `931ee3a0` to that fetched default head; the provider checkout remains on a
  peer branch and is not switched or cleaned.

## ATLAS-CACHE-FORK-055 — Horae repo-local target cleanup complete

- The conformance audit identified `repos/horae/target` as a derived cache fork
  beside the shared `D:\\atlas\\target`. The exact directory contained the
  Cargo `.rustc_info.json` marker and was removed after path verification.
- Re-running the provider conformance scan for Horae reports `target_forks: 0`;
  no source, lockfile, or provider checkout state changed.

## ATLAS-KWAVERS-BOOK-FENCE-2026-08-19 — restore truthful mdBook fence semantics [patch] — in progress

- Kwavers commit `cbf99272b4265b720b4e4d597515f91ba944fefa` changes the
  affected book fences to `text` or `rust,ignore` according to their actual
  content and corrects the stale `DENSITY_WATER_NOMINAL` excerpt.
- `mdbook test docs/book` and `mdbook build docs/book` pass at that exact
  provider head. This closes the prior 286-failure book-gate defect without
  pretending that workspace-dependent excerpts are standalone examples.
- The linked source examples still need `cargo check -p kwavers --examples
  --locked` after the shared Atlas overlay lock mismatch is repaired. The
  current command stops before compilation because `--locked` refuses the
  overlay's requested lockfile update; no Rust-source result is claimed.

## ATLAS-CONFORMANCE-SUBMODULE-STATUS-2026-08-19 — classify provider dirt after root status [patch] — in progress

- Hosted conformance runs `32247752034` and `32248848495` failed before the
  ratchet scan with the generic `root worktree is dirty` error, while the
  hosted checkout was clean at the root revision. The scanner's root status
  query included nested submodule summaries and therefore hid the provider
  boundary that its next checks own.
- `scripts/atlas-conformance.py` now uses `--ignore-submodules=all` for the
  root status query and retains the per-provider status checks. Its focused
  regression suite passes 18/18, including the provider-dirt classification.
- The next exact-head hosted run must pass the scanner and lock-form gates;
  local execution remains intentionally blocked by peer-dirty provider trees.

## ATLAS-CONFORMANCE-RATCHET-2026-08-19 — exact provider regressions [patch] — blocked

- Hosted conformance run `32250014209` reached the exact root head `a4f24ee`
  after the root line-ending and submodule-status fixes. It reports three
  source regressions; the committed baseline remains unchanged.
- Exact gitlink attribution is CFDrs `834340f7`:
  `crates/cfd-1d/src/solver/core/network_solver.rs` crossed 500 lines
  (`500 -> 568`); Consus `2e0df9f8`:
  `crates/consus-zarr/src/codec/mod.rs` crossed 500 lines (`439 -> 643`);
  and Coeus `5adc2d16`:
  `crates/coeus-autograd/src/lib.rs` contributes the counted crate-level
  `#![allow(...)]` surface (`18 -> 19`).
- No baseline raise is authorized. The source repairs require provider-owned
  edits, focused gates, hosted conformance, and an exact-head pointer sweep.
  The current provider checkouts/lanes are peer-owned and dirty; re-open when
  those claims land or become stale and reclaimable.
- Fresh clean-checkout run `32389729879` at root `dfc0184` confirms the same
  defect class with six current regressions: `CFDrs/oversized_files` 134 ->
  135, `coeus/crate_level_allows` 18 -> 19, `consus/oversized_files` 82 ->
  83, `moirai/seqcst_production` 101 -> 107, `ritk/manifest_implementation`
  105 -> 106, and `ritk/commented_out_code` 8 -> 9. The run also reports 15
  tightenings; none authorizes a baseline increase. These counts bind to the
  committed provider gitlinks and remain blocked on provider-owned source
  repairs, not on the Atlas book-gate change.
- The next exact root run at `f621c1d` reduced the class to five regressions:
  CFDrs `oversized_files` 134 -> 135, Coeus `crate_level_allows` 18 -> 19,
  Moirai `seqcst_production` 101 -> 107, and RITK
  `manifest_implementation` 105 -> 106 plus `commented_out_code` 8 -> 9.
  Consus no longer regresses after Atlas corrected its gitlink to merged
  default `e121b9d4`. The concurrent overlay run `32391551896` exposed two
  stale `moirai-http` entries caused by dirty local Moirai state; root commit
  `f621c1d` removes them from the generated block. No baseline raise is
  authorized; the next hosted run must collect both fixes.
Re-open trigger: CFDrs, Coeus, Moirai, or RITK lands the named source repair,
or its provider claim becomes stale and is reclaimed for a focused repair.

## ATLAS-WORKTREE-TAKEOVER-107 — stale-lane sweep across the stack [patch] — in progress 2026-08-20

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

## ATLAS-ADR-UNTRACKED-105 — completed ADRs left untracked [patch] — in progress 2026-08-19 (kwavers closed; coeus + hephaestus open)

`kwavers/docs/adr/112-convex-array-rasterizer-seam.md` is complete (110 lines,
full context/decision/consequences, Status: Accepted) and its item **COV-3 is
recorded done** on the kwavers board — but the file was never `git add`ed. It
exists only in the shared working tree.

Same class as ATLAS-RITK-D2-STRANDED-100: the work happened, the record did not
ship. It is worse in one way — an ADR *is* the deliverable, so an untracked ADR
means the decision has no durable existence at all, and a fresh clone shows a
decision that was made and then lost.

`scripts/adr-index.py` detects this, reports "untracked, so absent from a fresh
clone", and excludes the file from the generated index — correctly, since the
index records what a clone would have. The check now returns nonzero for that
anomaly, so a matching generated index cannot pass while the ADR is absent from
`HEAD`.

**Swept 2026-08-19 — it is systematic, three members.**
`git ls-files --others --exclude-standard docs/adr/` across every member:

| member | untracked ADR | lines | status |
| --- | --- | --- | --- |
| kwavers | `112-convex-array-rasterizer-seam.md` | 110 | **committed** via PR #418; index and corpus now agree on main |
| coeus | `0066-provider-owned-dense-product-bridge.md` | 108 | header carries no status line |
| hephaestus | `0052-device-neutral-sliding-window-seam.md` | 216 | Proposed |

All three are full records with six sections each, not scaffolding — 434 lines
of decision rationale that no clone of these repositories contains. Both coeus
and hephaestus also carry a dirty `docs/adr/README.md`, consistent with an index
regenerated against a file that was then never committed.

**Fix.** Per member: commit the ADR (noting it was found untracked), regenerate
the index, push. Two need a header decision first — coeus 0066 has no `Status`
line at all, and hephaestus 0052 is `Proposed`, so whether either is Accepted
needs its author or its evidence, not my assumption.

**Mechanization landed 2026-08-20.** `check_indexes` treats every tracked-tree
anomaly as a gate failure; the focused regression suite passes 4/4. The
provider ADR commits and their regenerated indexes remain external to this
root-only increment and stay open until their owning streams commit them.

**It got worse before it got better.** While PR #418 was in review, peer PR #419
"restored the missing 112 index row" — committing the row but not the file. For
a few hours `main` advertised 112 in its index while a fresh clone got a dead
link, which is strictly worse than the file merely being absent: the index
asserted a record that did not exist. PR #418 committed the file the row refers
to; verified on `origin/main` by resolving every indexed link against the tree.

**Mechanization.** The detection already exists and already ran: `adr-index.py`
prints "untracked, so absent from a fresh clone" and correctly excludes the
file. It exits nonzero only for index drift, so an untracked ADR alone is a
message nobody fails on. Making that condition part of the nonzero exit is a
one-line change and turns a passed-over log line into a gate.


- **ATLAS-HERMES-CODEGEN-SSOT-2026-08-21** Resolve SIMD codegen source of truth [arch][minor] (2026-08-23; hermes PR #59 merged `78b8745` after all hosted gates passed at exact head `569ed00`; lane removed, branch deleted) — `78b8745`, `569ed00`

## ATLAS-CROSS-MEMBER-SWEEP-108 — cross-member staleness and dirt sweep [patch] (2026-08-23) — in progress

Liveness-measured sweep of all 28 member checkouts. Findings:

- **moirai**: LIVE peer (tree modified mid-sweep) — excluded, never touched.
- **CFDrs**: the largest anomaly — 53-commit validation/binding series
  (Sprints 1.96.200-204 try_new validation, typed cfd-python boundary)
  pushed to `codex/cfdrs-tvd-test-integration` but never merged; main moved
  20 commits independently; 56 dirty files atop. Uncommitted WIP rescued to
  `origin/rescue/cfdrs-wip-20260821`; the series is now up for integration
  as **CFDrs PR #360**. Integration resolved locally 2026-08-23: two-file
  conflict (CHANGELOG unioned; cfd-validation Cargo.toml = series deps +
  main's athena-leto dev-dep), workspace check/clippy clean, 436+1738 tests
  green, doctests green, fmt applied. Pushed to the PR branch at `b512f778`;
  hosted CI running.
- **16 dead-session dirt patches** (aequitas, asclepius, eunomia, gaia,
  harmonia, horae, hyperion, iris, leto, melinoe, proteus, themis from the
  2026-08-20 ~14:2x session; helios/apollo/consus from ~16:55; ritk from
  08-21): PM-artifact updates (+30..+688 lines each), rescue-committed
  verbatim and pushed to `rescue/pm-sweep-20260820` per member; working
  trees restored clean at their prior heads. Port-or-drop parked with
  their author.
- **A downstream private consumer**: RESOLVED 2026-08-23. The stranded
  series was not the problem — it FIXES the default branch's redness (stale
  first-party path deps left the workspace unresolvable). Series merged to
  the consumer's default and the follow-up typed-quantity port delivered via
  its PR #7 (`3439842`): MODALITY-002 debt discharged, 27 errors to zero,
  nextest 525 passed on the stack toolchain, fmt/clippy clean. Named per
  ATLAS-PRIVACY-NAMING-1 only in that org's own tracker, not here.
- Clean but stale checkouts (behind origin, no dirt): apollo, consus,
  eunomia, gaia, harmonia, horae, hyperion, melinoe, ritk, themis, tyche,
  athena — fast-forward at next touch of each member.

**CFDrs PR #360 delivered 2026-08-24.** Hosted workspace gate green
(15m25s) after one CI-only clippy fix (DES rejection test now constructs
its config with struct-update syntax; local gates must run with
`RUSTFLAGS="-D warnings"` to match the hosted floor). Merge `eee77aa2`.
Lane cleanup: five stale worktrees removed, 24 fully-merged local branches
deleted, 14 unmerged branches remain — all tips pushed to origin, each a
stranded series needing per-branch judgment (filed as follow-up).
Local-only tips preserved via push before any deletion.

**Branch-judgment sweep closed 2026-08-24.** All 14 unmerged branches
adjudicated: every series conflicts with the lint/tracing/validation
refactors main absorbed (PRs #349-#367+), and origin/main passes the
hosted -D warnings workspace gate today — the acceptance target those
series were driving toward. Verified content-level: the allocator-gate,
GIL-boundary, and blueprint-lint fixes all exist on main in evolved form
(the test-module-scoped allocator replaced the ungated library static).
All local branch tips deleted; remote branches retained as archive.
CFDrs now carries exactly one local branch (main) at the merged head.

**Takeover completed 2026-08-24 (author grant).** All rescue branches
adjudicated and delivered or retired:
- kwavers SWE volumetric WIP: integrated via PR #627 (`7bb84b3a`); the
  fmt gate it tripped is fixed on main (`0e1c92753`).
- CFDrs post-series WIP: integrated via PR #369 — LF-normalizing
  .gitattributes landed stack-side, clippy --fix discharged residual
  findings, 3256 tests green pre-fixup.
- kwavers imaging ratchet slice: delivered via PR #629 (`bde986c1`);
  the transducer lint-floor commit was already superseded on main.
- coeus cache residue: loss-revert hunks rejected (recorded); PM-doc
  residue superseded by the merged cache delivery — branch retired.
- PM-sweep snapshots: 8 members merged to defaults directly (asclepius,
  gaia, harmonia, iris, proteus, helios, ritk + athena untracked set);
  8 members' snapshots judged stale against heavily-advanced defaults
  (conflict magnitude/direction evidence) — branches deleted, remotes
  retained.
All local+remote rescue refs are gone; every verdict recorded here.

New defect filed by the sweep: asclepius pins aequitas ^0.1.0 / coeus
^0.9.0 — both no longer resolvable (aequitas serves only 0.2.0; coeus
dropped aequitas and moved to 0.10.0). Overlay builds of asclepius are
red for everyone. Filed as the next DoR item: advance asclepius's
first-party deps through the 0.9→0.10 API surface.

**PR-fleet takeover 2026-08-24.** 25 open PRs audited across 14 members:
- MERGED: leto #121 (draft → ready → merged), iris #19 (docs record);
  kwavers #596/#450 and CFDrs #362 closed superseded (verified landed via
  #629 / #442+556741e / test-module-scoped allocator respectively).
- DEFECT FOUND + FIXED on asclepius main: the PM-sweep rescue snapshot
  swept the documented-untracked local Atlas overlay (.cargo/config.toml
  with absolute D:/atlas target-dir) into git, leaking the host path into
  CI test binaries and breaking Verify. Untracked + ignored (f8fcea6);
  CI re-running.  ritk has the same leak class with D:/msys64 compiler
  paths — older (July), pre-existing; fix pushed as ritk PR #207.
- **ritk overlay leak fixed 2026-08-24:** PR #207 merged at `e875f2b4`
  (base `a974573e`, the PM-stranded-snapshot default). `.cargo/config.toml`
  untracked + ignored; post-merge CI and Python CI both terminal success at
  `e875f2b4`; live Pages HTTP 200. Atlas gitlink advanced `6daf72b0` →
  `e875f2b4` (the prior pointer referenced the unmerged fix branch tip, not
  a main commit).
- **leto advanced 2026-08-24:** gitlink `fc0648ee9` → `7d6ac26ff` (PR #121
  iterative-solver family deletion; hosted CI + pages-build-deployment green
  at head). Closes ATLAS-LETO-BOOK's pending Pages clause.
- **ritk overlay leak fixed 2026-08-24:** PR #207 merged at `e875f2b4`
  (base `a974573e`, the PM-stranded-snapshot default). `.cargo/config.toml`
  untracked + ignored; post-merge CI and Python CI both terminal success at
  `e875f2b4`; live Pages HTTP 200. Atlas gitlink advanced `6daf72b0` →
  `e875f2b4` (the prior pointer referenced the unmerged fix branch tip, not
  a main commit).
- **leto advanced 2026-08-24:** gitlink `fc0648ee9` → `7d6ac26ff` (PR #121
  iterative-solver family deletion; hosted CI + pages-build-deployment green
  at head). Closes ATLAS-LETO-BOOK's pending Pages clause.
- Lockfile-guard promotion PRs (asclepius #26, athena #17, CFDrs #368,
  consus #54, helios #70, moirai #162, proteus #18): branches updated
  with main to absorb fixes; CI re-running.
- Remaining open feature PRs (kwavers #424/#439/#440/#443/#617/#620/
  #622–#624, helios #55/#69, proteus #17, hephaestus #216, ritk #144)
  are genuinely diverged series needing per-PR integration engineering;
  their old CI runs died at the 24h wall.

**kwavers #424 delivered 2026-08-25** (oldest diverged PR, taken over):
the FWI-024-D rotating opposed-linear-array acquisition — the geometry
ATLAS-FWI-PSTD-BLI-106's BLI extensions were built for. Integrated with
current main; ADR 116 renumbered to ADR 122 (slot collision with the
clippy-floor ADR). Its strict-clippy fixups converged with a peer's
9d8c5f370 on main. Merged as kwavers #634 (c11dffcf).

**kwavers #443 delivered 2026-08-26** (taken over): console log sink →
stderr. Integration required two rounds against a moving main — the
first CI run exposed a real 60 s TIMEOUT regression in
swe_3d_validation::volumetric_tracking_covers_non_pml_domain; fixed by
right-sizing the coverage grid to 40×40×28 / PML 6
(resolution-independent property, 3× speedup) rather than raising the
timeout. Second run green; merged (9982b37). CI-duration observation:
the Test Suite Coverage job ran 38–43 min even green — see
KWAVERS-CI-PIPELINE-001 for the consolidation fix.

**helios #55 delivered 2026-08-25** (taken over): typed-slopes series
(RITK orientation-tag consumption in helios-domain, deny-pedantic floor
with 11 lint classes fixed outright, ADR casing, package description).
Integration surfaced that the branch's new floor exposed pre-existing
main-side findings; all resolved (or-patterns, test-module unwraps →
expect with invariants, trivially-copy pass-by-ref with a scoped expect
at its borrow-boundary reason, doc backticks). Workspace clippy clean
under --all-features, 262 tests green. Merged (ddf282a). Remaining
diverged: helios #69 (delivered 8/25), proteus #17 (delivered 8/25),
hephaestus #216 (delivered 8/25), ritk #144, kwavers #439/#440/#443/
#617/#620/#622-#624. ritk #144 trial: semantic divergence — main's
dti/volume eigen evolution (diffusion_eigen/symmetric_eigen) superseded
the branch's decompose_3x3_symmetric route; the series needs a real
rebase onto that evolution, not marker resolution. Trial reset;
branch preserved on origin. **Verdict finalized 2026-08-25**: all four
commits verified content-level superseded — DirectionInterpolation/
Trilinear lives in maps/volume.rs, svd_decompose replaced the retired
SVD entry points, the borrowed voxel-view seam evolved into
ritk-image/src/region/{voxel,rows,iter}.rs, and the CLI
OrientationSamplingMode is in ritk-cli tract.rs. PR #144 closed
superseded with that evidence; ritk main verified 5675 tests green.

**ritk #154 delivered 2026-08-25** (taken over): tract output-format
series (.trk/.trx writers, Kabsch svd_decompose migration, pedantic
floor). Integrated with current main across ~90 conflicted files —
conflicts were uniformly the branch's ratchet-reason annotations vs
main's plain forms; branch side kept as the ratchet superset. Three
real gaps fixed during integration: undeclared example submodules,
unpopulated phantom ground-truth fields, and a bulk-resolution casualty
(restored main's B-spline dispatch manifest).

**Tooling defect recorded**: rustc E0583 "file not found for module"
fires for example submodules under \?\-prefixed worktree paths
(D:/atlas/worktrees/*) while the same tree builds from the canonical
checkout — a Windows UNC-path rustc limitation to note for all future
lane-based verification (verify from repos/<member> when example
submodules are involved).

**helios #69 delivered 2026-08-25** (taken over): Radon input-error
assertions + executable book oracle + typed extension metadata. Clean
fast-forward of the series with current main; 284 tests green.
Merged (9499501).

**Lane census 2026-08-25**: stack worktree lanes reduced 26 → 15; all
MERGED lanes removed, unmerged/active lanes retained. A peer's
proteus-mat-adoption campaign left four member gitlinks pinned to
unpushed local branches (cat-C: unreachable from any clone) — every
referenced branch has been pushed to its origin so all atlas pins now
resolve. Their merges remain that campaign's follow-up; coherence audit:
0 stale-advanceable, remaining defects are reachable cat-B pins only.

**CFDrs #368 delivered 2026-08-25** (taken over): lockfile-guard
promotion integrated with current main (one trivial conflict — both
sides had fixed the erasing 0*nx index in the LBM streaming test).
Hosted workspace gate green 16m15s. Merged (14fc2c0). The seven
lockfile-guard promotions are now all landed stack-wide.
clippy-floor ADR). Its strict-clippy fixups converged with a peer's
9d8c5f370 on main. Merged as kwavers #634 (`c11dffcf`). Remaining
diverged feature PRs: helios #55/#69, proteus #17, hephaestus #216,
ritk #144, kwavers #439/#440/#443/#617/#620/#622-#624.

Re-open triggers: CFDrs PR #360 verdict [collected]; author decisions on the rescue
branches; moirai re-check after its live peer's commit lands.

## ATLAS-LINT-CALIB - Calibrate the board-reference lint to corpus conventions [pm-hygiene] [patch] [S]

- Outcome: `scripts/atlas-board-lint.py` fails loudly on references that
  matter without burying them under archive noise.
- Measured + triaged 2026-08-24. 565 mentions / 329 unique ids in
  live-item prose, classified by containing item:
  CROSS-MEMBER-SWEEP-108 inventory 230, MULTIPHYSICS-ADOPTION-100 101,
  GPU-ACQUISITION-POINTER-ADVANCE 91, remaining sweeps/books <60 total.
  Verdict: ~95 percent are scan-inventory listings inside active sweep
  items - data, not broken pointers - and those blocks leave the lint's
  scope when the sweeps close. Zero actionable file-it/fix-ref cases.
- Also fixed en route: ATLAS-KWAVERS-STALE-TREE-107 recorded twice with
  identical bodies; second block removed (34 lines), ids unique again.
- Diagnostic note for posterity: two rounds chased "U+FFFD mojibake" that
  did not exist in the files - it was terminal codepage rendering of em
  dashes inside python repr output. Verify suspected encoding damage with
  a character count in python, never by console appearance.
- Disposition: reference findings stay report-only by design while
  sweep-style inventory items are a living pattern; the duplicate-id gate
  stays hard. Revisit enforcing mode only if a non-inventory dangling ref
  class appears.
- Status: done (2026-08-24)


## ATLAS-CFDRS-STALE-EXAMPLE-PAGES-001 - Book example pages for deleted examples [docs] [patch] [S]

- Outcome: docs/book/example pages reference sources that exist and run.
- Found 2026-08-24: the strict pre-commit dead-link gate flags
  cfd_demo.md and matrix_free_demo.md linking
  ../../../examples/{cfd,matrix_free}_demo.rs - both .rs files no longer
  exist, so their Run commands fail too. Pages carry generated-figure
  markers, so the fix belongs in the generating pipeline (skip examples
  whose source file is absent), not in hand-edited markdown.
- Status: todo

## ATLAS-BOARD-CLOSURE-CANON-001 - Canonicalize historical closure markers [pm-hygiene] [patch] [M]

- Outcome: every closed item carries the one canonical heading marker so
  atlas-board-compact.py archives at full power and
  atlas-board-lint.py's reference scope stays accurate.
- Measured 2026-08-24: compact dry-run archived only 18 of 236 backlog
  items (8 percent) because closure markers vary by era - heading
  "- closed DATE", body Status lines, checkmark bullets, unmarked.
  Full-power archival would collapse thousands of archive-prose lines;
  today they remain live-scope and feed the 323 reference mentions the
  lint reports.
- Scope: pick the canonical form (heading `- closed YYYY-MM-DD`);
  script a reviewed one-pass normalization; rerun compaction; then flip
  ATLAS-LINT-CALIB's reference report toward enforcing for items that
  stay live after normalization.
- Status: in-progress (integrator: claude session; lease: scripts/atlas-board-canonicalize.py, backlog.md, checklist.md, focused tests)

## KWAVERS-CI-PIPELINE-001 - Consolidate kwavers CI to one verification pipeline [ci] [patch]

- Outcome: one workflow whose jobs carry the stage structure (build-once,
  cheapest-first, affected-scope filters); mdBook deploy off pull_request
  events; benchmark regression job removed (benchmarks run locally per
  policy - CI keeps the single-iteration bench smoke only).
- Evidence 2026-08-24: six sibling workflows fire per PR event and per
  main push; queue sat 6-15 min behind one busy runner; one main-push
  CI/CD Pipeline run ended cancelled, leaving that merge unverified.
- Status: todo

## ATLAS-RUNNER-CAPACITY-001 - Size runner slots to fleet width [infra] [patch]

- Outcome: no verification job queued past its own runtime target; runner
  slots sized to fleet width x per-event jobs, or per-event jobs shrunk by
  affected-scope filters (KWAVERS-CI-PIPELINE-001 is the largest shed).
- Evidence 2026-08-24: kwavers queue depth ~10 with one in_progress.
- Status: todo

## ATLAS-BRANCH-INVENTORY-001 - Burn down stack branch inventories [git-hygiene] [patch]

- Outcome: every member's local branches map to an open item or enqueued
  PR (orient rule); measured 2026-08-26: kwavers 65 (12 merged, 6 gone),
  moirai 30 (24 merged, 15 gone), coeus 21, apollo 17, hermes 14,
  helios 16. Merged/gone prune mechanically; the unmerged remainder
  classifies by patch-id against origin default (rebase/squash-landed
  deletes as landed; unique deltas salvage per takeover) — one
  mechanical sweep per member, proportionate triage.
- Sweep done 2026-08-26 — 125 branches deleted across 26 members (merged
  into origin default, or gone-upstream with cherry-verified empty delta);
  kwavers stashes cleared by peer.
- kwavers classified 2026-08-26: 56 -> 35 refs (21 more landed branches
  deleted; every survivor verified to hold real content deltas vs main —
  content-supersession test on touched files, not just patch-id).
  Survivor families, takeover material closest-to-done-first: 8
  PR-scratch (pr-622/623/624/633/646, fix622/fix622-work/fix622b, small
  deltas); 5 merged-PR leftovers (+1..+8 past merged tips: #364 #434
  #443 #609, remove-simulated-gpu-swe); 7 recent seams/docs/ci (Aug
  19-25); 12 July-era codex/* WIP (aequitas family, +3..+138 commits —
  largest recoverable value, oldest basis, naming-rule renames due at
  takeover).
- ritk classified 2026-08-26: 33 -> 19 refs (15 deleted: merged tips,
  cherry-landed, merged). 17 survivors with real deltas: 5 merged-PR
  tails (+1..+3 past #54 #80 #116 #154 #166); 4 large Aug 1-7 WIP
  (release-workflow-caller +35, coeus-publishability +29,
  reconcile-model-coeus +26, gradient-reorientation +20); 8 small
  recent fixes/docs (Aug 11-19, +1..+3).
- Mechanical phase closed 2026-08-26, stack-wide: coeus 21->17 (note the
  coeus-frobenius provider/cherry/rebase/v2 sibling family — consolidate
  at takeover), gaia 19->2 (cascade/provider-042 held by the tree's
  checkout bookkeeping), apollo 16->12, and 50 more deletions across the
  other 21 members (consus 13->5, helios 14->7, moirai 7->4, ...).
  Session total: ~236 branches deleted, every deletion evidence-backed
  (merged / cherry-landed / merged-PR tip / content-superseded).
  Remaining work: ~98 survivor branches with real deltas are takeover
  material, familied above for kwavers/ritk/coeus/apollo; per-item
  takeover increments, not a sweep.
- Settings done 2026-08-26 (user-authorized): delete_branch_on_merge=true
  on all 26 members; allow_auto_merge=true on 25/26 — leoneuro-rs
  declines auto-merge (plan/visibility limit), enqueue falls back to
  merge-on-green there.
- Status: in-progress (mechanical phase done stack-wide; survivor takeovers unclaimed, closest-to-done-first)

## ATLAS-CROSS-BALANCE-EDGE-REMEDIATION-2026-09-04 - Route the four cross-balance edges through harmonia [minor] - todo <a id="cross-balance-remediation"></a>

Parent: `#archtest-live-balance-domains`.

- **outcome:** the four cross-balance edges surfaced by ADR 0055 R7
  route through `harmonia`'s coupling surface — or, where the shared
  type is genuinely a single-field dependency, the shared type moves
  to a non-balance substrate crate the way `proteus` already carries
  material closures. After remediation the live stack reports
  `balance_domain_edges = 0` and the ratchet tightens to that floor.
- **surfaced by:** `#archtest-live-balance-domains`
  at `9e9dbe785` on 2026-09-04. The current counts are baseline (the
  rule's correctness outcome); any *new* violation above the floor
  fails the gate.
- **the four edges:**

  | Consumer | Provider | Member pair | Notes |
  | --- | --- | --- | --- |
  | `helios-analysis` | `asclepius` | helios × asclepius | bio-effect scoring in therapy plan evaluation |
  | `helios-planning` | `asclepius` | helios × asclepius | bio-effect scoring in dose planning |
  | `kwavers-physics` | `asclepius` | kwavers × asclepius | bio-thermal acoustic coupling |
  | `kwavers-therapy` | `asclepius` | kwavers × asclepius | bio-effect scoring in therapy protocols |

- **two remediation paths are admissible** per ADR 0055:
  1. **Route through harmonia** — the dependency becomes a
     `harmonia::Partition` consumer; the field exchange routes through
     typed field envelopes per [ADR 0050](docs/adr/0050-typed-physical-field-exchange.md).
     This is the canonical path for true coupling.
  2. **Extract the shared type** — if `asclepius` is only being used
     for one type (e.g. an effect-score quantity), the type moves to
     `aequitas` (the shared quantities layer ADR 0055 places alongside
     the balance owners) and the edge disappears. This is the path
     for *non*-coupling dependencies that were routed through
     `asclepius` for convenience.

- **decision per edge** belongs to the *consumer* repository's owner:
  helios's `helios-analysis` and `helios-planning` edits live on
  helios's tree (lane `perf/helios-ci-concurrency` per the latest
  sync, or a fresh branch); kwavers's `kwavers-physics` and
  `kwavers-therapy` edits live on kwavers's tree (lane
  `refactor/elastic-ssot-consumer` per the latest sync). The asclepius
  side is unaffected — asclepius publishes the coupling surface the
  consumer reads, and ADR 0055 R5 names `harmonia` as the route.

- **acceptance:** the live conformance scan reports `balance_domain_edges = 0`
  across all 26 members; the four edges are removed; the ratchet baseline
  reflects the new floor; kwavers's elastic SSOT work (in flight under
  `[#proteus-elastic-ssot](backlog.md#proteus-elastic-ssot)`) and
  the kwavers→ares→athena first-consumer path remain green.
- **class:** `[minor]` (architectural cleanup; not blocking publish).
  **risk:** low — the existing `kwavers-analysis -> asclepius` and
  `kwavers-simulation -> asclepius` edges (dev-dependency-only) are
  outside R7's scope and unaffected. **depends on:** nothing.

## ATLAS-SIBLING-NAMED-CRATES-2026-09-04 - Nine crates are named after a sibling member, not a concern [arch] [major] - todo <a id="sibling-named-crates"></a>

- **outcome:** no crate in the stack carries a `<host>-<sibling>` name, and
  the required-dependency graph over publishable crates is closed and
  acyclic. Each renamed crate is named for the concern it owns; the
  dependency stays a manifest fact.
- **conflict, stated:** AGENTS.md `standards: Naming prohibition` and
  `architecture_scoping: Upstream ownership` prohibit the
  `<host>-<sibling>` shape, and `engineering_gates: Publish pipelines`
  makes a `publish = true` crate depending on a `publish = false` crate a
  topology defect. Both rules postdate the crates below and ares
  [ADR 0001](repos/ares/docs/adr/0001-athena-seam-as-a-separate-crate.md),
  which records `ares-athena` by name. Per `instruction_hierarchy` the
  higher-priority source wins and the ADR is revised, not the rule.
- **the nine, measured** (`scripts/publish-order.py` + crate-name scan, `769b044`):

  | Crate | Host | Sibling | Also closure-blocked |
  | --- | --- | --- | --- |
  | ~~`ares-athena`~~ → `ares-operator` | ares | athena | no — **renamed** |
  | ~~`ares-harmonia`~~ → `ares-coupling` | ares | harmonia | yes (`harmonia` is `publish = false`) — **renamed**; closure open |
  | `asclepius-coeus` | asclepius | coeus | no |
  | `athena-hephaestus` | athena | hephaestus | no |
  | `athena-leto` | athena | leto | no |
  | `coeus-hephaestus` | coeus | hephaestus | no |
  | `coeus-leto` | coeus | leto | no |
  | `tyche-consus` | tyche | consus | no |
  | `tyche-moirai` | tyche | moirai | no |

- **closure defect is wider than the naming one:** 14 publishable crates
  depend on a `publish = false` crate — `ares-harmonia`, `cfd-2d`,
  `cfd-optim`, five `helios-*`, five `kwavers-*` — blocked on `harmonia`,
  `hyperion`, `horae`, and `asclepius-coeus`. Graduating those four
  providers resolves 13 of the 14 without any rename.
- **acceptance:** the crate-name scan reports zero `<host>-<sibling>`
  names; `publish-order.py` reports an empty BLOCKED section; both
  checks land in `scripts/atlas-conformance.py` as counted classes so the
  ratchet holds them at zero.
- **method:** meta ADR first (the rename is a public-API break for any
  published member and the graduation decision per provider is not
  mechanical), then per-member items in dependency order. `ares` is the
  first increment — both its seam crates were created 2026-09-04 in this
  session, are unpublished, and have no external consumers, so they
  rename at zero migration cost.
- **ares delivered 2026-09-05:** `ares-athena` → `ares-operator` (it presents
  a linear operator), `ares-harmonia` → `ares-coupling` (it presents a coupling
  partition). Item names were already concern-named and did not move. ares
  ADR 0001 carries a dated revision note; the atlas architecture test, its
  fixtures, the stack diagram, and this board moved with it. Full ares gate
  green — fmt, no-default-features check, clippy `-D warnings`, 102 nextest,
  doctests, warning-clean rustdoc, `cargo deny`, mdbook build and link check —
  and the lock regenerated in standalone form.
- **remaining:** seven crates in `asclepius`, `athena`, `coeus`, and `tyche`,
  each with published or consuming surface, so each needs the meta ADR first.
  Plus the closure work: graduate `harmonia`, `hyperion`, `horae`, and
  `asclepius-coeus` to publishable, which clears 13 of the 14 blocked crates.

## ATLAS-PYTHON-PIPELINE-PINS-2026-09-04 - No published wheel covers ARM Linux or musl [patch] - in-progress <a id="python-pipeline-pin-divergence"></a>

- **outcome:** every member consuming the shared `python-wheels.yml` pins the
  same Atlas commit, and that commit carries the platform matrix. `ritk` stops
  carrying its own copy of the pipeline.
- **the defect is coverage, not tidiness.** `bfb720121` (2026-08-26) expanded
  the shared workflow from three wheels — glibc Linux x86_64, Windows x86_64,
  macOS universal2 — to six systems: glibc and musl Linux on x86_64 and
  aarch64, plus Windows and macOS. **All nine consuming members are pinned
  before it**, newest `5b43d5513` on 2026-08-20. So no Atlas wheel on PyPI
  installs on ARM Linux or on musl; `pip` there falls back to the sdist and
  needs a Rust toolchain.
- **measured 2026-09-06** at `877955f94`. Four distinct workflow pins and six
  distinct `atlas-ref` values across nine members:

  | Member | `python-wheels.yml@` | `atlas-ref` |
  | --- | --- | --- |
  | CFDrs | `5936303396` (08-18) | `ad22ec5eec` (08-21) |
  | apollo | `5b43d55135` (08-20) | `5b43d55135` (08-20) |
  | coeus | `4c31dd753f` (08-13) | `1a7cdca730` (08-09) |
  | consus | `4c31dd753f` | `1a7cdca730` |
  | helios | `5936303396` | `4c07ce3d11` (08-19) |
  | hephaestus | `4c31dd753f` | `1a7cdca730` |
  | kwavers | `2f17abc735` (08-19) | `2f17abc735` |
  | leto | `4c31dd753f` | `1a7cdca730` |
  | moirai | `4c31dd753f` | `1a7cdca730` |

  `atlas-ref` is "the exact Atlas commit that owns the provider gitlink graph",
  so five members resolve their first-party providers through a gitlink graph
  from 2026-08-09 — a month stale.

- **`ritk` runs its own `release.yml`** rather than the shared workflow: a
  hand-rolled three-wheel matrix that also assumes MSYS2 on the Windows runner.
  That is the duplication defect at fleet scale (`consolidation_discipline`) and
  it is why `ritk` did not get the platform fix either.
- **acceptance:** all consumers pin one identical SHA carrying `bfb720121`;
  `ritk/.github/workflows/release.yml` is deleted in favour of the shared
  `workflow_call`; the conformance scan counts distinct pins across members so
  the next divergence fails rather than accumulating.
- **verification limit, stated:** these workflows fire on release publish only,
  so the sweep cannot be dry-run. The first release per member is the
  verification, and the pin change is reviewed as a diff against the shared
  workflow's declared inputs.

## ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06 - Twenty-two hand-maintained copies of two git hooks [patch] - in-progress <a id="hook-fleet-duplication"></a>

- **outcome:** `scripts/git-hooks/` is the one source for the member-side
  `pre-commit` and `pre-push` guards, deployed outward by
  `atlas-lock-form.py sync-hooks` under the generator contract, with
  `sync-hooks --check` failing CI on drift.
- **measured 2026-09-06:** 22 members carry `.githooks/pre-push` in **two**
  versions and `.githooks/pre-commit` in **two** versions. In both cases the
  minority version is `hephaestus`, and in both cases hephaestus is the one
  that is *correct*: it injects `safe.directory` so the hook's child git calls
  work in a checkout owned by a different filesystem account. Twenty-one
  members are missing that fix. The copies were the divergence, and the
  canonical copy in `scripts/git-hooks/` was staler than all of them — its
  `pre-commit` was 34 lines against the members' 61, missing the whole
  commit-time guard added under
  `ATLAS-LOCKFILE-POISONING-GENERATOR-2026-08-26`.
- **why the copies cannot simply be deleted:** `install-hooks` points
  `core.hooksPath` at the Atlas tree, which only resolves inside the stack
  checkout. A member cloned standalone would then run no hooks at all. So the
  copies stay and stop being *authored*: one source, written outward,
  drift-checked.
- **a behaviour fix rides with it.** `pre-push` ran `lockfile.py --check`
  against the *working tree* on every push, regardless of what the push
  contained. Those differ whenever the pushed commits were not checked out — a
  plumbing push, or a push from a tree sitting on another branch — and the hook
  then refused a push on the strength of state that push did not contain. It
  blocked four of the nine wheel-pin pushes today
  ([`#python-pipeline-pin-divergence`](backlog.md#python-pipeline-pin-divergence)),
  none of which touched a manifest or a lock. It now reads the revision range
  git supplies on stdin and skips when nothing in it is a `Cargo.toml` or
  `Cargo.lock`. Verified both directions: a workflow-only range skips, a range
  containing a lockfile change runs the real check, a branch deletion skips.
- **deployed 2026-09-08.** Twenty-three members synced and three more
  (`eunomia`, `iris`, `melinoe`) given hooks they had never had. Twenty landed
  immediately; `apollo`, `coeus`, `hephaestus` and the three new ones are
  enqueued behind required checks. Verified against each member's *default
  branch* rather than its working tree — 20 of 23 confirmed byte-identical to
  `scripts/git-hooks/` at the time of writing.
- **a verification trap worth recording.** `sync-hooks --check` reads working
  trees, and most member trees sit on peer branches, so it still reported 45
  drifted files after twenty deliveries had merged. The instrument was
  measuring checkouts, not delivered state — the same class of blind spot as
  the conformance ratchet measuring pinned gitlinks. Confirming delivery took
  comparing blob hashes at `origin/<default>` directly.
- **and a shell trap under it.** The first such comparison reported *zero*
  members in sync, because Git Bash rewrote `origin/main:.githooks/pre-push`
  into `origin\main;.githooks\pre-push` — MSYS path conversion mangling the
  revision:path argument. Every `rev-parse` failed and the loop counted the
  failures as mismatches. `MSYS_NO_PATHCONV=1` fixes it. A measurement that
  reports total failure deserves suspicion before its subject does.
- **`metis` and `prometheus`** are unregistered members without remotes and are
  out of scope until `#metis-unregistered-member` (`161354f`)
  clears.
- **acceptance:** `atlas-lock-form.py sync-hooks --check` exits zero across the
  fleet and runs in CI.

## ATLAS-MNEMOSYNE-PIN-CAMPAIGN-STRANDED-2026-09-06 - A provider-pin campaign stalled undelivered in five members [patch] - todo <a id="mnemosyne-pin-campaign-stranded"></a>

- **outcome:** the mnemosyne pin advances land on each member's default branch,
  or are deliberately discarded as superseded. No member sits on an unmerged
  provider-pin branch, and the atlas gitlinks that depend on them stop being
  unpushable.
- **surfaced from the far end.** An atlas commit advancing gaia's gitlink pinned
  `8060ef0e`, which is on `fix/gaia-lock-stale-rev` and not on gaia's
  `origin/main`. The meta-repo's gitlink guard refused the push — correctly: a
  gitlink naming a commit outside the member's default branch breaks resolution
  for every consumer. The pin was not the defect; the undelivered branch was.
- **measured 2026-09-06**, pushed branches with no merge:

  | Member | Branch | Commits ahead of main | PR |
  | --- | --- | --- | --- |
  | gaia | `fix/gaia-lock-stale-rev` | 25 | [#47](https://github.com/ryancinsight/gaia/pull/47) opened 2026-09-06, **conflicting** |
  | hermes | `build/mnemosyne-phase12` | 17 | none |
  | leto | `build/leto-mnemosyne-source-identity` | 17 | none |
  | kwavers | `chore/kwavers-xtask-mnemosyne-allocator` | 8 | none |
  | athena | `feat/mnemosyne-global-allocator-integration` | 2 | none |

  69 commits of provider-pin work across five members, none of it delivered,
  four of them without even a pull request. `git_discipline: cadence` calls an
  unmerged branch integration debt precisely because it compounds: gaia's is
  now conflicting with its own `main`, so the first cost of the delay is a
  rebase that did not exist when the work was done.
- **the shape is one campaign, not five coincidences.** Each branch is a run of
  `build(deps): Advance mnemosyne rev to <sha> (Phase N)` commits. Advancing a
  provider across the stack is a co-evolution sweep
  (`architecture_scoping`: pin discipline) — it lands per member in dependency
  order or it is not a sweep, and a per-member branch that accumulates phases
  without merging is the sweep's defect output.
- **correction, 2026-09-06: the framing above is wrong for gaia, and the
  rebase is what showed it.** gaia's branch chased `f532b0e`, the pre-merge tip
  of mnemosyne's `perf/mnemosyne-scratch-release`. That branch has since landed
  — mnemosyne PR #128, merged to `main` as `e8e825f` — and gaia's `main`
  already pins `e8e825f`. So the single `Cargo.toml` conflict was `main`
  holding the published commit against the branch holding an unpublished
  ancestor of it, and merging would have moved gaia *off* mnemosyne's default
  branch. gaia#47 is closed, the branch deleted, the atlas gitlink repointed at
  gaia `origin/main` (`ba5a8fd83`). Nothing lost: every earlier phase is an
  ancestor of the same landed work.
- **the real defect the campaign left behind.** Two members' *default branches*
  pin a mnemosyne rev that is not on mnemosyne's `main`:

  | Member | Pinned rev | Lives on |
  | --- | --- | --- |
  | `coeus` | `03fe32f4` | `feat/phase10-improvements`, unmerged |
  | `kwavers` | `03fe32f4` | `feat/phase10-improvements`, unmerged |

  This is the metis and gaia-gitlink defect one level down: a dependency
  resolving to a commit outside the provider's default branch. Either
  mnemosyne's `feat/phase10-improvements` lands, or both members repoint at
  `e8e825f`. Each repoint carries a lockfile regeneration.
- **resolved 2026-09-06.** mnemosyne #123 is *closed*, not pending, so there
  was nothing to wait for. Both members repointed to `e8e825f4`:
  [Coeus#376](https://github.com/ryancinsight/Coeus/pull/376) and
  [kwavers#723](https://github.com/ryancinsight/kwavers/pull/723), each with its
  lock regenerated outside the overlay and verified under `--locked`.
- **the kwavers pin was breaking the build, not only the provenance.** Resolving
  `03fe32f4` needed a network fetch that libgit2 could not complete, so
  `cargo check -p kwavers-medium` failed with `class=Net (12); code=Eof (-20)`
  while `git ls-remote` against the same URL succeeded. The error named the
  network; the cause was a rev on a dead branch. Worth recording as a
  diagnostic signature: a cargo transport error on a first-party git source is
  a pin question before it is a connectivity question.
- **a two-day-old increment was recovered on the way.** Both kwavers checkouts
  held byte-identical uncommitted work delegating the six derived elastic
  identities to `proteus::elastic::IsotropicModuli` — the residual copy
  [`#proteus-elastic-ssot`](backlog.md#proteus-elastic-ssot) is about.
  Rebased onto the repointed `main` and delivered as
  [kwavers#724](https://github.com/ryancinsight/kwavers/pull/724). Only
  `CHANGELOG.md` conflicted — an append against an append — and both entries
  were kept. The gate it could never run then passes now: clippy clean, 215
  nextest, 4 doctests.

  Clippy earned its place on the way. Delegating made the accessors
  fallible-underneath, so six public functions gained a reachable panic and
  none documented it; `missing_panics_doc` caught the two with `expect`
  directly in their own body, and the other four differ only in that the panic
  is one call deeper. All six now carry `# Panics`. The duplicate copy in the
  second kwavers checkout was verified superseded by what landed — a strict
  subset — and cleared.
- **remaining branches** (`hermes` 17, `leto` 17, `athena` 2, and kwavers's 23)
  are phase series with no PR. gaia's turned out to be superseded rather than
  stalled, so each of these needs the same check — does `main` already pin the
  merged result? — before anyone rebases 17 commits.
- **then:** a PR per remaining member, in dependency order, each gated by its
  own lockfile check — these branches change dependency resolution, so that
  check is the one that matters and must not be skipped.
- **open question for the ADR:** whether these advances should ride per-member
  branches at all, or be produced by the mechanized integration sweep
  (`toil automation`) that pin discipline already calls for. Five stalled
  branches is evidence for the latter.

## ATLAS-SLOP-BURNDOWN-2026-09-06 - Measured debt burn-down against the conformance ratchet [patch] - in-progress <a id="slop-burndown"></a>

Parent: [`#atlas-hygiene-baseline-001`](backlog.md#atlas-hygiene-baseline-001).

- **outcome:** every class in `scripts/atlas-conformance.py` sits at or below
  its recorded baseline, and the scan runs in CI so the next increase fails
  rather than accumulating behind a stale pin.
- **measured 2026-09-06** at `d15afbf5a`, 26 members, ~4,000 sites. The four
  largest classes are `unwrap_production` 724, `manifest_implementation` 662,
  `oversized_files` 614, and `allow_sites` 508; `kwavers` alone holds 260, 286,
  107, and 322 of those. This is a programme, not an increment.
- **resolved 2026-09-06:**

  | Class | Where | What |
  | --- | --- | --- |
  | `target_forks` | apollo, consus, leto | Repo-local `target/` trees forking the shared build cache; deleted |
  | `root_sprawl` | apollo, `<meta>` | Detector corrected for `.provider-identity-baseline`; scratch file relocated |
  | `member_namespace_pollution` | `<meta>` | `repos/prometheus` ignored until its remote exists |
  | `crate_level_allows` | moirai | Nine example `#![allow(dead_code)]` → `#![expect(…, reason)]` ([#263](https://github.com/ryancinsight/Moirai/pull/263)) |
  | `manifest_implementation`, `oversized_files` | leto | `leto-python/src/lib.rs` 576 → 21 lines; tests split beside their subjects ([#174](https://github.com/ryancinsight/leto/pull/174)) |
  | `reexport_shims` | coeus | `RandomScalar` and `FiniteDifferenceAxis` aliases deleted, 51 call sites moved ([#378](https://github.com/ryancinsight/Coeus/pull/378)) |

- **a finding worth more than the fixes.** Several apparent regressions were
  not new debt: measured at each member's *pinned gitlink*, `ritk`'s
  `type_suffixed_fns` was already 71 against a baseline of 69, and `mnemosyne`'s
  pin equals its `main`, so both of its violations were arithmetically
  impossible to have been caused by any commit. **The baseline was recorded
  against revisions the gitlinks had since moved past, so the ratchet was
  measuring stale trees and could not see debt landing behind them.** Advancing
  nine gitlinks immediately surfaced `kwavers` +2 oversized files and +3
  existence-only assertions, and `hephaestus` +1 allow site, none of which the
  gate had reported.
- **so the first fix is the instrument, not the counts.** The ratchet must
  measure what is actually on each member's default branch, and the gitlink
  advance must be routine rather than an occasional sweep — otherwise the gate
  reports on history. Until then a "clean" ratchet run means nothing.
- **`type_suffixed_fns` needs a rule, not a burn-down.** `ritk` has 71, and
  many are protocol-fixed: `read_u8`/`read_u32` on a JPEG-2000 codestream
  reader are operations on a wire format that fixes the type, which
  `standards` explicitly exempts ("a concrete signature is correct when the
  … protocol, storage, I/O, or FFI contract fixes the type"). Renaming them
  would be worse code. The detector cannot tell those from a forked generic
  dimension, so this class needs an exemption mechanism before its count means
  anything.
- **`coeus/target_forks` is resolved, and not the way it was first recorded.**
  It was written up as deferred because 37 GB of it was being written to by
  live `cargo` processes. That judgement was correct but arrived late: a
  background deletion launched before it had already been running and completed
  the removal. All four forks are gone. No harm done — a build cache is derived
  state and any interrupted build re-runs — but the deferral note was wrong
  about what had happened, and the sequencing error is the real lesson: a
  destructive action was in flight while the decision not to take it was being
  made.
- **`apollo/excess_worktrees` genuinely stands:** three trees, two held by peers
  with commits in the last twenty minutes. A lane migrates at its item's
  completion, never under a running process.
- **the shared cache is 779 GB.** `performance_engineering` makes build and
  artifact size a tracked budget with eviction on a committed cadence, and
  there is no such cadence here — the four forks were the visible symptom of an
  unbounded store, not the store itself. Filed as
  `#shared-cache-unbounded`.


## ATLAS-KWAVERS-ELASTIC-CONSTRUCTORS-2026-09-06 - kwavers#707 is red on real errors and conflicting [patch] - todo <a id="kwavers-elastic-constructors"></a>

Parent: [`#proteus-elastic-ssot`](backlog.md#proteus-elastic-ssot).

- **outcome:** the construction half of the Proteus elastic delegation lands,
  completing the item whose accessor half landed as
  [kwavers#724](https://github.com/ryancinsight/kwavers/pull/724).
- **state:** [kwavers#707](https://github.com/ryancinsight/kwavers/pull/707),
  open since 2026-09-04, `CONFLICTING`, every CI job red. It covers
  `constructors.rs`, `elastic.rs`, the heterogeneous factory, and the
  homogeneous implementation — disjoint from #724's `computed.rs` and
  `mod.rs`, so the two are complementary halves rather than duplicates.
- **the red is not the pin.** It was worth checking, since the dead mnemosyne
  rev broke every kwavers build until #723; but the log shows real compile
  errors: `E0277` (`T: eunomia::traits::field::RealField` unsatisfied) and
  several `E0034` (multiple applicable items in scope). The second is the
  characteristic hazard of exactly this delegation — provider trait methods
  colliding with the type's inherent methods of the same name — so the
  diagnosis points at the design, not at the environment.
- **method:** rebase onto current `main` (which now carries both the repoint
  and #724), then resolve `E0034` by choosing at each site whether the inherent
  or the provider method is the intended one rather than disambiguating
  mechanically. The bound failure is likely a missing `RealField` on a generic
  parameter the delegation newly requires.
- **taken over 2026-09-06** as
  [kwavers#727](https://github.com/ryancinsight/kwavers/pull/727); #707 closed
  with the diagnosis recorded on it.
- **the red was against a stale base, not a defect in the change.** Rebased
  onto current `main` — which now carries the mnemosyne repoint (#723) and the
  accessor half (#724) — the `E0277` and `E0034` errors are gone. Worth
  recording as a pattern: a long-open PR's red is a claim about a base that no
  longer exists, and re-measuring it costs one rebase.
- **merged 2026-09-08.** #727 was a draft because `cargo clippy --all-targets`
  could not run at all: its dev-dependencies reach `ritk`, whose resolution
  failed on the Moirai requirement lag. That same lag was what the SemVer gate
  failed on — that job runs `cargo update` per crate, and every crate failed
  identically. Once kwavers' sweep leg landed on `main`, merging the base in
  (not rebasing, so the PR history stayed reviewable) picked up the `0.6.0`
  requirement and unblocked both. Full gate then: check, `clippy --all-targets
  -- -D warnings`, 215 tests, fmt — all clean, including the check that had
  never been able to run.
- **the two halves of `#proteus-elastic-ssot` are now both on kwavers `main`**,
  so `lame_from_speeds` and the duplicated Lamé conversion algebra are gone
  from the consumer.
- **the seven mnemosyne phase commits were not carried over:** they chase
  revisions on a closed pull request's branch and `main` pins the merged
  result, the same finding as gaia's series.

## ATLAS-MOIRAI-06-SWEEP-2026-09-06 - Moirai 0.6.0 landed without its forward sweep [patch] - in-progress <a id="moirai-06-sweep"></a>

- **outcome:** every first-party requirement on a `moirai-*` crate resolves
  against Moirai's current workspace version, and each member's lock is
  regenerated and green.
- **the defect:** Moirai's workspace version is **0.6.0**; members still
  require `^0.5.0`, so the resolver rejects the only version that exists.
  `architecture_scoping` (pin discipline) makes the forward sweep part of the
  same co-evolution unit as the version advance, precisely because "a patch
  unifies only when the local version satisfies the declared requirement".
  It never fired. The second cost is quieter: under the stack overlay a local
  crate replaces a git one only when the version satisfies the requirement, so
  the lag silently disables the `[patch]` beneath it.
- **measured 2026-09-06, third attempt, and the first two were wrong.** Scan
  one read only root manifests (6 members). Scan two added nested manifests but
  its pattern required `version` immediately after `{`, so it missed every
  dependency written `git = ..., version = ...` — including coeus, the one
  blocking three others (10 members). An order-independent parse of every
  `Cargo.toml` in every member's default branch gives the real set. Recording
  the method, not just the number, because the number moves as peers land legs:

  | Member | Requirements | State |
  | --- | --- | --- |
  | leto | `moirai-runtime` | landed, [leto#176](https://github.com/ryancinsight/leto/pull/176) |
  | coeus | `moirai-runtime`, `moirai-async` | peer holds it, bump applied uncommitted |
  | helios | `moirai-runtime`, `moirai-parallel` | bumped `75aab40`, blocked on coeus |
  | ritk | `moirai-runtime` | bumped `7b1cc5b3`, blocked on coeus |
  | kwavers | `moirai-parallel` | landed |
  | CFDrs | `moirai-runtime` | landed, [CFDrs#419](https://github.com/ryancinsight/CFDrs/pull/419) |
  | apollo | `moirai-runtime` | **not sweep debt — see below** |

  gaia, hephaestus, consus, tyche were in an earlier count and are already
  clean — peers swept them in parallel.

- **2026-09-08: two members remain, and one of them should not be swept.**
  `apollo` pins `rev = "83aa411"` under a comment that names its own removal
  trigger: *"Temporary co-evolution pin for the worker-idle reclamation seam;
  remove `rev` after Moirai's hook lands on main."* That commit is not on
  moirai's `main`, and the pull request carrying it —
  [moirai#257](https://github.com/ryancinsight/Moirai/pull/257), open since
  2026-09-04 — is `CONFLICTING` with no CI ever run. So apollo is a documented
  quarantine whose trigger has not fired, exactly as pin discipline prescribes,
  and bumping it would break its dependency on an unlanded hook. Counting it as
  sweep debt was my error: the scan cannot tell a quarantine from a lag, and I
  did not read the comment above the line before listing it as unclaimed.
- **the real remaining work is moirai#257**, not apollo. Landing it fires
  apollo's trigger; until then apollo is correct as it stands.
- **helios** carries the last plain lag: the requirement bump and lock are
  committed on `build/helios-moirai-06` ([helios#92](https://github.com/ryancinsight/helios/pull/92)),
  held by one remaining `helios-gpu` error that a peer is mid-edit on.
- **the order is forced, not a preference.** A member's lock resolves its
  first-party git dependencies from their `origin/main`, so a bump cannot be
  verified until every dependency it pulls has landed its own. Bumping `ritk`
  alone fails on `coeus-core`'s `^0.5.0`; bumping `kwavers` alone fails on
  `ritk-io`'s; bumping `helios` alone fails on `coeus-core`'s. **coeus unblocks
  three of the remaining five.**
- **bumps are committed before they can be verified**, deliberately: the
  manifest edit is the executable remainder and the lock regeneration is the
  blocked substep. Leaving the edit as uncommitted state in a shared tree is
  what produced the two-day-old duplicated dirt found in kwavers earlier today.
- **it is blocking real work:** kwavers cannot advance its resolved `ritk`
  revision, so it cannot pick up ritk#238, so `cargo check --workspace` on
  kwavers `main` is red and
  [kwavers#727](https://github.com/ryancinsight/kwavers/pull/727) cannot run
  `clippy --all-targets` and stays draft.
- **Corrected 2026-09-08 (kwavers#725 landed):** the rev-advance path is open
  *now*, without waiting on the Moirai 0.6 sweep. [ritk#238](https://github.com/ryancinsight/ritk/pull/238)
  merged (`1b9d4d86`) and [kwavers#725](https://github.com/ryancinsight/kwavers/pull/725)
  pinned the fixed rev and landed (`56ea403d`); kwavers `main` CI is green at
  `96819eae`, Integration Suite included. The blocker above applies to
  *version-requirement* bumps (Moirai `^0.5.0` → `0.6.0`), which do force
  global re-resolution; a bare git *rev* re-selection moves one source and
  leaves the rest of the lock untouched, so it clears the `RandomScalar`
  break independently of the sweep. kwavers#727's premise should be
  re-judged against the green main.

## ATLAS-BARE-GIT-PIN-STALENESS-2026-09-08 - A version-less git dependency freezes at its first resolution [patch] - todo <a id="bare-git-pin-staleness"></a>

Parent: [`#slop-burndown`](backlog.md#slop-burndown).

- **outcome:** no first-party dependency is declared as a bare `git = "..."`
  without a version requirement, so `cargo update` can advance it and the
  conformance scan counts any that reappear.
- **the mechanism:** `helios` declared `eunomia = { git = "..." }` with no
  `version`. Cargo then locks whatever revision resolved first and has no
  requirement that would ever make it move — not stale by a sweep's neglect but
  by construction. It sat at `3a8836e3`, a revision predating the
  `eunomia-derive` crate: helios's lock contained **no `eunomia-derive` entry
  at all**.
- **what it looked like from the outside.** `hephaestus-core` had moved on to
  using eunomia's `Pod`/`Zeroable` derive macros, so helios's build failed
  *inside a dependency* with `cannot find derive macro Pod in this scope`. That
  reads as a broken upstream, and it is not one — `hephaestus-core` compiles in
  its own tree at default features and at `--no-default-features`. Four
  diagnostic steps went past hephaestus before the lock was the suspect. Worth
  recording as a signature: **a derive macro missing from a dependency's build
  is a resolution question, not an upstream defect**, and the cheap check is
  whether the providing crate appears in the lock at all.
- **`cargo update -p eunomia`** advances it to `8e18d6d8`, adds
  `eunomia-derive`, and clears four of five errors in `helios-gpu`
  (`b525e8a`).
- **the class, not the instance:** a bare `git =` requirement is the pin-width
  rule's other failure mode. `architecture_scoping` covers over-tight (`=`)
  requirements manufacturing resolver conflicts; this is the opposite — no
  requirement at all, so nothing ever forces movement, and the divergence is
  invisible until a consumer needs something the frozen revision lacks. Both
  are the same defect in width. The scan should count version-less first-party
  git dependencies, and the sweep should treat them as it treats an `=` pin.

## ATLAS-APOLLO-QUARANTINE-LIFT-2026-09-08 - Apollo's moirai rev pin can now be removed [patch] - todo <a id="apollo-quarantine-lift"></a>

Parent: [`#moirai-06-sweep`](backlog.md#moirai-06-sweep).

- **outcome:** `apollo/Cargo.toml` drops `rev = "83aa411"` from its `moirai`
  dependency, requires `0.6.0`, and regenerates its lock — closing the last
  item in the Moirai 0.6 sweep.
- **the trigger has fired.** The pin's own comment says *"remove `rev` after
  Moirai's hook lands on main and regenerate Cargo.lock."* The hook landed as
  [moirai#290](https://github.com/ryancinsight/Moirai/pull/290) on 2026-09-08,
  a takeover of #257 which had sat four days behind a CI webhook that never
  delivered.
- **this is a quarantine expiring on schedule, not debt.** Worth recording as
  the positive case: the pin carried its removal trigger in a comment beside
  it, so lifting it required reading one line rather than reconstructing intent
  — which is exactly why pin discipline asks for the trigger to be written
  down.
- **blocked on a lease, not on a tree.** Both apollo trees are held by live
  peers, and the lane's board block explicitly leases its regions to
  `codex/main_integration` with a contributor lease inside it, dated
  2026-09-08. More to the point, that item's own dependency line reads
  *"preserve each tree's dependency lock"* — and this lift is exactly a
  manifest edit plus a lock regeneration. Taking it now would break the
  condition their in-flight work states it needs.
- **re-open trigger:** `APOLLO-CODELET-SCHEDULE-CONTROLS` completes, or its
  integrator confirms the lock may move. This is a genuine wait on a peer's
  stated precondition rather than a scheduling inconvenience, so it parks
  rather than being worked around.

## ATLAS-CRLF-STORED-BLOBS-2026-09-08 - Committed blobs contradict the declared line-ending policy [patch] - in-progress 2026-09-08 (renormalizations in review) <a id="crlf-stored-blobs"></a>

Parent: [`#slop-burndown`](backlog.md#slop-burndown).

- **outcome:** every member's stored blobs match its `.gitattributes`, so an
  edit renders as the change it is rather than as a whole-file rewrite.
- **measured 2026-09-08 in CFDrs:** `.gitattributes` declares
  `* text=auto eol=lf`, and **61 of 141 `cfd-1d/src` `.rs` files are stored
  with CRLF**. The policy exists; the blobs predate it and were never
  renormalised.
- **the cost is review, not correctness.** Editing one such file with any
  LF-writing tool turns an 83-line change into a 1253-line diff. That is not a
  cosmetic annoyance: a reviewer cannot see the change, and an over-broad
  staging sweeps whole-file rewrites into unrelated commits. It is also the
  source of the CRLF warnings on nearly every commit in this stack.
- **the fix is one command per member** — `git add --renormalize .` — but it
  must land as its *own* change, on a quiet tree, because it touches every
  affected file and would swallow anything committed with it. That is the
  opposite of the situation it creates today, where it swallows things
  silently.
- **check the other members first:** the conformance scan reports
  `gitattributes_missing = 0` fleet-wide, so every member declares a policy.
  Whether the blobs match it is a different question and is not currently
  measured. Worth adding as a counted class before doing the renormalisation,
  so the ratchet holds it at zero afterwards.
- **measured fleet-wide 2026-09-08 (`git ls-files --eol`, index form):**
  **1,596 blobs across 7 members** — CFDrs 1,588 (the incident), leto 3,
  consus/helios/hephaestus/moirai/kwavers 1 each (the copy-propagated
  `.github/workflows/python-release.yml` template). The meta repo is clean.
- **counted class delivered:** `crlf_stored_blobs` in `atlas-conformance.py`,
  measured from the index, not the worktree. On the recorded-revision scan
  path it reads the pinned tree through a temporary `GIT_INDEX_FILE` against
  the live object store, so archived snapshots (which carry a resolving-nowhere
  `.git` marker) and behind/dirty checkouts both measure correctly — the first
  implementation read 0 for every archived member, which is exactly the kind
  of silent materialization-path dependence the fleet scan must not have.
  Baseline ratcheted at 1,596 via `--accept-raises` (new class, first
  measurement). moirai and kwavers carried live peer edits at scan time and
  are counted from their pinned revisions like everyone else.
- **renormalizations in review (one standalone PR per member, `git add
  --renormalize .` only, zero content change, must land alone):**
  CFDrs#422 (1,588 files, 945,678 lines each way, `--ignore-cr-at-eol` diff
  empty), consus#71, helios#95, hephaestus#294 (default branch is `master`),
  leto#179. moirai and kwavers follow once their trees go quiet.

## ATLAS-RATCHET-REGRESSION-SET-2026-09-08 - Seven ratchet regressions arrived with peers' merges [patch] - todo <a id="ratchet-regression-set"></a>

Parent: [`#slop-burndown`](backlog.md#slop-burndown).

- **outcome:** the fleet ratchet returns to zero regressions, by fixing the
  debt rather than by raising the baseline.
- **surfaced by advancing twenty-three gitlinks** at `49db31fc9`. These counts
  were already on the members' default branches; the meta-repo simply could not
  see them while its pins were behind. That is the ratchet's blind spot,
  recorded earlier in this item, doing its damage in the other direction: debt
  lands invisibly and then arrives all at once.

  | Member / class | Was | Now |
  | --- | --- | --- |
  | aequitas / `manifest_implementation` | 0 | 2 |
  | apollo / `existence_only_assertions` | 0 | 1 |
  | apollo / `manifest_implementation` | 24 | 25 |
  | kwavers / `oversized_files` | 107 | 109 |
  | kwavers / `target_forks` | 0 | 1 |
  | ritk / `oversized_files` | 44 | 45 |
  | ritk / `type_suffixed_fns` | 69 | 76 |

- **`aequitas` and `apollo` going 0 → n matters most.** A class at zero is a
  floor someone reached; crossing back is worse than never having been clean,
  because the ratchet's guarantee is exactly that it does not happen.
- **the instrument behaved correctly and I misread it once.** `generate`
  refuses to raise, printing the refusal on stderr. Having redirected stderr, I
  saw it write nothing while `check` reported violations and concluded the two
  modes disagreed. They do not: one was declining to launder the other's
  findings. Worth recording because "the tool is broken" was the wrong
  conclusion from a real observation, and the check that settled it was running
  the same command without the redirect.
- **`kwavers/target_forks` is regrowth, not a new instance.** Three
  repo-local `target/` trees were deleted earlier today and one is back at
  7.5 GB with cargo processes live in it. The generator survives the cleanup,
  which `context_and_memory` (slop pattern library) says makes finding the
  generator the priority defect rather than repeating the sweep. Not deleted
  this time: a build is running in it.
