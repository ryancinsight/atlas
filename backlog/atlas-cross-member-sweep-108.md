<a id="atlas-cross-member-sweep-108"></a>
## ATLAS-CROSS-MEMBER-SWEEP-108 — cross-member staleness and dirt sweep [patch] (2026-08-23) — in-progress

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

