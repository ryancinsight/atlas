<a id="atlas-provider-chain-quality-2026-08-27"></a>
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

