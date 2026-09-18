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

