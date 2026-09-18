<a id="atlas-hygiene-baseline-001"></a>
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

