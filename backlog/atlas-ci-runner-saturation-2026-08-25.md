<a id="atlas-ci-runner-saturation-2026-08-25"></a>
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

