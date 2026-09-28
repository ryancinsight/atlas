# Performance, memory-efficiency, safety and cleanup audit — Atlas member repos

Date: 2026-09-26
Scope: the six highest-debt members of the Atlas meta-repository, plus a
stack-wide census of all 28.
Method: the authoritative conformance scanner, calibrated per-file
inventories reproducing the committed baseline exactly (0 failures over 15
repos), and an independent reviewer instrument that never reads an agent's
own numbers.

## 1. Census (all 28 members)

Measured with `python scripts/atlas-conformance.py report --worktree --json`
against `scripts/conformance-baseline.json` as it then stood.

### Genuine raises

| repo | class | baseline | live |
|---|---|---|---|
| **apollo** | `unwrap_production` | 25 | **72** |
| **kwavers** | `junk_drawer_modules` | 3 | **22** |
| **mnemosyne** | `manifest_implementation` | 8 | **16** |
| ritk | `oversized_files` | 43 | 46 |
| ritk | `existence_only_assertions` | 0 | 2 |
| gaia | `oversized_files` | 39 | 40 |
| gaia | `manifest_implementation` | 7 | 8 |
| hermes | `manifest_implementation` | 11 | 12 |
| kwavers | `oversized_files` | 107 | 108 |
| kwavers | `crlf_stored_blobs` | 1 | 2 |
| leto | `allow_sites` | 11 | 12 |
| melinoe | `oversized_files` | 2 | 3 |
| mnemosyne | `print_dbg` | 2 | 3 |
| moirai | `seqcst_production` | 79 | 80 |
| eunomia | `manifest_implementation` | 2 | 3 |
| horae | `type_suffixed_fns` | 0 | 1 |

Three of these carry an explanation rather than being new debt:

- **apollo `unwrap_production` 25 → 72** is the stale-checkout artifact of
  §5: the baseline reflects a revision apollo's local `main` was 108 commits
  behind, so the comparison is against newer code than the tree held.
- **kwavers `junk_drawer_modules` 3 → 22** is a detector-tightening effect.
  The previous baseline recorded 22 and the current one records 3, so the
  tree did not change — the floor moved down under it.
- **ritk's two `existence_only_assertions`** are `assert!(...is_some())` in
  new test code on an in-flight lane.

`mnemosyne` doubling its module-root count, 8 → 16, is the largest raise that
is none of those three.

The ratchet fails on any `value > was`, so a pin advance was rejected on
apollo, kwavers, mnemosyne, ritk, gaia, hermes, leto, melinoe, moirai, eunomia
and horae until they returned to baseline.

### Largest banked reductions

`coeus unwrap_production 77 → 0`, `gaia oversized_files 44 → 40`,
`CFDrs oversized_files 139 → 130`, `CFDrs manifest_implementation 82 → 71`,
`hermes oversized_files 28 → 23`, `leto oversized_files 23 → 21`,
`kwavers allow_sites 320 → 316`, `apollo crate_level_allows 30 → 21`,
`moirai unwrap_production 126 → 120`, `ritk type_suffixed_fns 73 → 62`.

## 2. Defects in the audit tooling itself

All three shipped in `fix/atlas-conformance-code-token-precision`. Each is a
detector reading a text region that does not match the class's definition, and
each inflated a ratchet floor — the floor sat above the truth, so the member
could add the suppressed debt and still pass.

### 2.1 A whole-file `#![cfg(test)]` is not recognised as test code

`gaia/src/application/csg/boolean/indexed_tests.rs` opens with the inner
attribute `#![cfg(test)]` and is declared via `#[path = "indexed_tests.rs"]
mod indexed_tests;` from `indexed.rs`, whose `mod` declaration carries no
`#[cfg(test)]`. `declared_cfg_test()` therefore returns `False`, the file
name is the `<name>_tests` suffix form the scanner does not recognise, and
`split_test_region()` matched only *outer* `#[cfg(test)]`.

That file is 1042 lines with 663 body lines and **34 `.unwrap()`**, all
counted as production. **gaia's recorded `unwrap_production = 36` is 34 false
positives; the true count is 2.** Re-measured after the fix: 36 → 2.

An inner attribute is file-scoped, so the fix classifies the whole file as
test text and returns before `_item_end` would stop at the first top-level
`;`.

Cleared as a non-issue: `apollo` has four whole-file `#![cfg(test)]` modules
(`apollo-{sht,qft,gft,czt}/…/gpu/verification/mod.rs`) but they are 12–16 line
re-export shims with zero body lines and zero unwraps, so they inflate
nothing.

### 2.2 `seqcst_production` counts comment prose

`atlas-conformance.py` counted the literal token `SeqCst` over `prod` — the
production text region *including* comments — where the sibling
`unwrap_production` class counted over `prod_code`, a comment-stripped
region. The asymmetry is a defect, not a policy: a doc comment that *argues
against* using `SeqCst` raised the count.

Measured on `moirai` at `562e886e`:

```
seqcst_production (scanner)          80
  in code (non-comment)              35
  in // and /// comment prose        45   (56%)
```

Representative prose hits, all three in `moirai-async/src/executor/core.rs`:
`:100` ("…lost under any ordering (SeqCst included)…"), `:110` ("the SeqCst it
replaces…"), `:144` ("SeqCst would additionally…"). Each describes why `SeqCst`
is *not* used at that site, and each was counted against the repo.

Consequence for the ratchet: the class could not reach zero by any code change
without deleting the ordering-rationale comments, which is the opposite of the
desired direction. The floor was inflated for every repo whose synchronization
prose names the ordering; moirai is simply the one measured.

Fix: `unwrap_production`, `seqcst_production` and `print_dbg` now all read one
comment-free `prod_code`, so the rule cannot be re-introduced on a fourth
class. moirai re-measures 79 → 35.

The comment strip is offset-preserving and literal-aware, both load-bearing.
`_walk_mods` indexes back into the matched text for the `#[path = ..]`
attribute belonging to a declaration, so a strip that shortened the string
would slide the attribute out from under it. And `"https://host"` or
`r#"a // b"#` contain `//` that a naive scan reads as a line comment; blanking
to the newline there erases the rest of the line's real code. That failure is
silent and runs the wrong way for a ratchet — an undercount is a floor that no
longer holds — so string literals, raw-string hashes, char literals and `'a`
lifetimes are scanned past rather than blanked.

### 2.3 `MOD_DECL` matches commented-out module declarations

`MOD_DECL` has no line-start anchor and no comment guard, and `_walk_mods()`
ran it over raw file text, so a commented-out declaration read as a live
module edge: `// pub mod poiseuille_bifurcation;` matches. Two faces, both
measured on `CFDrs`:

| revision | `orphan_modules` | why |
|---|---:|---|
| `3e662fcae` (base) | **0** | `benchmarks/mod.rs:22` still held the commented line, so the walk "reached" the file |
| `4d370c18` (audit commit) | **1** | that line was deleted by the `commented_out_code` cleanup (4 → 0) |

- **False negative at base.** `crates/cfd-validation/src/benchmarks/poiseuille_bifurcation.rs`
  (386 lines) was *already uncompiled* — rustc never built it. The class exists
  precisely to surface such files, and a comment defeated it.
- **Phantom raise.** Deleting commented-out code — a cleanup — *raises* the
  class, so the ratchet penalises the correct action. `CFDrs`' committed floor
  is `orphan_modules = 0`, so that commit would have failed `check`.

Fix: the walk reads `strip_comments` output. `CFDrs` measures 0 → 1 at the
current pin, which is the honest number: the dead file is real and the audit
commit on `audit-CFDrs-20260926` deletes it, taking the class to 0 for a real
reason rather than through this false negative.

Also found: `_cached_text` keys a global cache **by path only**, so scanning
two revisions of the same tree in one process returns the first revision's
text. Measure each revision in a fresh process — this produced a transient
"0, 0" reading for the two `CFDrs` revisions before it was caught.

## 3. Lane divergence

| repo | local head | live default tip | relation |
|---|---|---|---|
| apollo | `9694add9d` (`main`) | `7b4f805d6` | **behind 108, ahead 0** |
| moirai | `562e886e` | `520756d7` | diverged: ahead 85, behind 7 |
| CFDrs | `3e662fcae` (`main`) | `38dedb614` | diverged: ahead 34, behind 12 |
| kwavers | `9fbecb908` | `60568c2fe` | diverged: ahead 67, behind 12 |
| ritk | `de32e1114` | `33cfa0c27` | diverged: ahead 53, behind 12 |
| consus | `ad81bb776` | `9e3c9cfa` | diverged: ahead 23, behind 7 |

apollo's checkout was stale `main` with zero unique work, so its audit base was
re-based to the live tip. The other five are genuine in-flight lanes. Every
local head is ahead of its gitlink, so the pins were stale for all six — the
tracked item `ATLAS-GITLINK-DRIFT-056`, whose recorded target shas no longer
matched the pins in the tree for CFDrs, kwavers and ritk.

## 4. Pre-existing flattened locks

Uncommitted `Cargo.lock` files with mtimes of 2026-09-25 — peer state, not
damage from this audit:

| repo | `source = "git+` lines |
|---|---|
| kwavers | **0** (fully flattened) |
| moirai | **0** (fully flattened) |
| CFDrs | 4 |
| ritk | 1 |

kwavers and moirai could not pass a `--locked` build from their live trees
until the locks were restored.

## 5. Per-repo findings

### kwavers — 316 allow-sites, and 69% of them are one lint

`clippy::too_many_arguments` accounts for **260 of 316** sites. Also present:
`dead_code` x53, `clippy::type_complexity` x15, `clippy::needless_range_loop`
x11, `unused` x10, and **4 x `#[allow(unsafe_code)]`** (suppressing the unsafe
lint makes those sites invisible to an unsafe audit). Removing the
`too_many_arguments` allows requires parameter structs, not deletion — it is
the highest-leverage cleanup in the stack.

Largest files: `kwavers-physics/src/analytical/imaging.rs` (2152 lines),
`kwavers-therapy/…/cavitation_cloud.rs` (1773),
`kwavers-solver/…/fdtd/solver/tests.rs` (1607).
Largest module roots: `kwavers-phantom/src/scatterers/mod.rs` (body 423),
`kwavers-physics/…/transducer/mod.rs` (body 342).

**Audit commit** `9fbecb908a` → `6433a8a984`, 104 files (16 renames + 87
modified + 1 added), no lock change. Reductions, none raised:
`commented_out_code` 27 → 0, `junk_drawer_modules` 22 → 6,
`seqcst_production` 10 → 0, `print_dbg` 9 → 6, `manifest_implementation`
277 → 276. `allow_sites` stays 316 — the 260 `too_many_arguments` sites need
parameter structs, and no allow was added back.

Two defects in the preserved work were caught and repaired before it landed: a
blanket rename had changed `mod helpers;` to `mod signal_types;` in
`simulation_py/run/mod.rs`, naming the *directory* module rather than the
renamed sibling — that orphaned 4 files and was a hard compile error; and the
longer module names broke `cargo fmt --check`, fixed without touching the one
file whose drift was pre-existing and outside the audit.

`seqcst_production` 10 → 0 is a **concurrency-semantics change**, not a
cleanup, and the one reduction here that needed adversarial review. All ten
sites were audited individually and every one is a pure counter:

- 4 × `static COUNTER.fetch_add(1, …)` in
  `kwavers-therapy/src/patient_management/{consent,demographics,encounter,treatment}.rs`
  feeding `format!("CONSENT_{:08}", id)` and siblings — ID generation, where
  `fetch_add` returns a unique value under any ordering.
- 4 × `submitted` / `completed` / `failed` in
  `kwavers-analysis/src/distributed/{scheduler,queue}.rs` — metrics, read only
  via `load(Ordering::Relaxed)`.
- 2 × `allocated` in `kwavers-core/src/arena/pool/pool_impl.rs` — a statistics
  counter read via `allocated.load(Ordering::Relaxed)` in `stats()`; the
  free-list CAS already uses `Release`/`Acquire`, and `peak_allocated` in the
  same function was already `Relaxed`.

No site carried a happens-before requirement, so the downgrade is correct and
is a real gain on aarch64, where a `Relaxed` RMW avoids the SeqCst fence. It
is recorded because an unexplained ordering change is indistinguishable from a
bug — the standard moirai's audit applied (state the invariant, or do not
weaken) is the standard this change had to meet.

**Out-of-scope finding: `kwavers-solver` does not compile at base.** At
`9fbecb908a`, `forward/pstd/propagator/pressure/density_cartesian/update.rs:5`
imports `crate::forward::lanes::axis_factor`, which `lanes.rs` does not define
(E0432), and `velocity.rs` passes `&Arc<FftPlan3D<f64>>` where only
`FftPlan3D<f64>: Fft3dInOutExt` (6 × E0277). Every file involved is
byte-identical to base, so this is pre-existing and not audit damage; the
consequence is that this commit's `kwavers-solver` edits are only statically
checked.

### moirai — `sleep_synced_tests = 78` is 90% example-demo pacing

Measured at `562e886e` with the scanner's own `rust_files` /
`split_test_region`:

| count | where | what it is |
|---:|---|---|
| **70** | `examples/` | demo pacing — simulated latency, periodic loops |
| 4 | `tests/` | incl. 2 in `spin_budget_bench.rs`, a `#[ignore]`d timing instrument where the sleep *is* the independent variable |
| 3 | `benches/` | benchmark pacing |
| 1 | `src` inline `#[cfg(test)]` | — |

Only **2** were genuine test-synchronization sleeps, both in
`examples/basic_usage.rs`, and both were fixed (78 → 76). Verified at source:
`examples/realtime_chat_server.rs` sleeps `from_millis(latency_ms)` and
`from_secs(30) // Run every 30 seconds` — a demo simulating a chat server. The
real remediation surface is 2 sites, not 78.

The scanner counts the whole file as the test region for `examples/`,
`benches/` and `tests/` paths, which is why demo pacing is classified as test
debt.

`seqcst_production = 80` — of which **35 are code and 45 are comment prose**
(§2.2). The 35 code sites are concentrated on the scheduler core:
`worker.rs` (14), `scheduler/core.rs` (13), `idle.rs` (11), `chase_lev.rs` (9),
`futex_mutex.rs` (7), `worker/wait.rs` (7). Each carries a written
happens-before invariant and three of the four protocols have a loom model
(`loom_join_quiescence.rs`, `loom_mpmc_waiter.rs`); none was weakened, because
a downgrade without a passing loom counterexample run is a correctness change,
not a cleanup. That audit is `ATLAS-MOIRAI-SEQCST-002`.

### CFDrs — prior constants work confirmed present

The recorded `cfd-schematics` work is intact at this revision:
`config/constants/mod.rs` is exactly 276 lines, `ConfigurableParameter` count
is 0, `primitives.rs` exists as the extracted sibling, and
`DEFAULT_CHANNEL_HEIGHT = 0.5`. It must not be redone.

Largest files: `cfd-1d/…/transient/composition/simulator.rs` (3157 lines),
`cfd-schematic-mesh/src/blueprint_mesh.rs` (2138), `cfd-core/src/error.rs`
(1613).

The audit commit is `3e662fcae` → `4c007d9995` (single commit, 94 files) and
reduces seven classes: `manifest_implementation` 71 → 53, `missing_deny_docs`
11 → 1, `commented_out_code` 4 → 0, `crate_level_allows` 5 → 1,
`reexport_shims` 9 → 5, `print_dbg` 2 → 0, `root_sprawl` 4 → 3. No class rose,
and test integrity is intact under the reachability-aware invariant (§6).

Two defects in the first attempt were caught and corrected before it landed:

- **A temporary measurement probe had been committed.**
  `crates/cfd-schematics/examples/alloc_probe.rs` (108 lines) was in the tree;
  the history was rewritten so it was never committed.
- **The first attempted fix for `orphan_modules` was scanner-gaming.** It
  re-added the line `// pub mod poiseuille_bifurcation;`, which re-hides the
  dead file rather than removing it. Rejected. Instead
  `crates/cfd-validation/src/benchmarks/poiseuille_bifurcation.rs` (386 lines)
  was **deleted**: it was uncompiled at base — the declaration was already
  commented out — so rustc, clippy and nextest never built it and its `#[test]`
  had never executed. `git show 3e662fcae:<path>` recovers the file if the
  module is re-enabled pending the cfd-1d/cfd-2d API alignment.

Workspace gate: `fmt` / `check` / `clippy -D warnings` / `test` / `nextest` all
green under `--locked` — 3356 tests passed, 0 failed, 42 ignored.

### consus — the only repo with a measured allocation win

Committed as `ef45254c` (base `ad81bb776`), 18 files, no lock touched. Four
classes reduced, all independently re-measured:

| class | before | after |
|---|---:|---:|
| `unwrap_production` | 9 | **0** |
| `missing_deny_docs` | 14 | **9** |
| `type_suffixed_fns` | 42 | **39** |
| `allow_sites` | 11 | **5** |

The `unwrap_production` fix is the notable one: five
`NonZeroUsize::new(<literal>).unwrap()` sites became one `bit_width(bits)`
helper with a single documented `.expect("datatype bit width is non-zero")` —
five silent unwraps collapsed to one stated invariant, which also collapsed
three per-type helpers (`type_suffixed_fns`).

The allocation work is the strongest memory result in the audit, and is
measured rather than argued. `consus_zarr::chunk::ops::chunk_key_for_array`
built its key with `Vec<String>` + `join` + `format!`; rebuilding it into one
`String::with_capacity(…)` with `write!` gives:

| case | allocs/call before → after | bytes/call before → after |
|---|---|---|
| v2 3-D `arr/[3,1,4]` | 7 → **1** | 104 → 68 |
| v3 3-D `arr/[3,1,4]` | 9 → **1** | 116 → 68 |
| v2 4-D root `[12,300,4,7]` | 6 → **1** | 113 → 87 |
| v3 4-D root `[12,300,4,7]` | 8 → **1** | 129 → 86 |

The scaling law was established before the fix, over `dims ∈ {1,2,4,8}`:
allocations grew **linearly in dimensionality** (one `String` per coordinate
plus three fixed), and are now **constant 1 per call**. Behaviour is held by
the existing exact-string tests in `chunk/ops/tests/coords.rs`;
`cargo test -p consus-zarr` = 319 passed / 1 ignored both before and after. No
timing claim is made — the sandbox's timing is too noisy to be evidence, so the
allocation count is the stable signal.

### apollo — `mod.rs` → sibling conversion, and 18 crate-level allows removed

Commit `9694add9d` → `bacbb2c566`, 58 files (17 renames with zero content
change, 41 modified), +90/−490, no lock change. Five classes reduced, none
raised:

| class | before | after |
|---|---:|---:|
| `missing_deny_docs` | 21 | **0** |
| `crate_level_allows` | 21 | **3** |
| `unwrap_production` | 72 | **51** |
| `manifest_implementation` | 24 | **6** |
| `reexport_shims` | 1 | **0** |

The conversion is the sanctioned `src/<dir>/mod.rs` → `src/<dir>.rs` layout,
which is why `manifest_implementation` falls by 18 without any code moving: a
file-plus-directory module root is not a `mod.rs`, so the detector never counts
it. Verification covered the failure modes this conversion actually has: every
parent still declares each renamed child, every renamed root resolves its
children including `#[cfg(test)]` sidecars, no `#[path]` attribute was left
pointing at an old name, no `foo/mod.rs` remains, and the reachability walk
reports **0 unreachable `src` files on both base and commit**.

The 21-unwrap reduction is real, not relocated. `unwrap_production` fell 72 → 51
while `.expect()` stayed at 2922, so an independent whole-tree count ruled out
unwraps being moved into test regions: total `.unwrap()` over every `.rs` file
fell by exactly 21 (498 → 477) with the file count unchanged at 1006.

Gate: `cargo check --locked`, `clippy --all-targets -D warnings` (zero
diagnostics) and `nextest --profile ci --workspace --all-features --exclude
apollo-python` (1641 passed / 51 skipped) all pass.

One judgement call worth recording: the preserved work had added
`#[inline(always)]` plus a new item-level `#[expect(clippy::inline_always)]` on
three Stockham lane files. That was **reverted** rather than landed, because
the new suppression moves the `#[allow]`/`#[expect]` invariant 194 → 197 and
there is no way to write `inline(always)` under `pedantic = deny` without one.
`lane_kernel_uninlined` therefore stays 3, recorded as an unfixed finding with
its mechanism rather than bought with a suppression.

### ritk — unwrap debt converted to stated invariants

Commit `de32e1114` → `bb8b2596`, 37 files, no lock change. Seven classes
reduced, none raised: `unwrap_production` 61 → 22, `manifest_implementation`
104 → 100, `oversized_files` 44 → 40, `reexport_shims` 3 → 0,
`seqcst_production` 2 → 0, `sleep_synced_tests` 1 → 0, `junk_drawer_modules`
1 → 0.

**`unwrap_production` 61 → 22 is a diagnosability change, not panic removal.**
Measured tree-wide: `.unwrap()` 1323 → 1284 (−39) while `.expect(` 6232 → 6270
(+38) — so 38 unwraps became `.expect("<invariant>")` and one was deleted. The
reasons are specific rather than restatements: `"invariant: contiguous host
storage"`, `"invariant: fixture tensor has the declared rank"`,
`"a rotation is invertible"`, `"fixed-width byte field"`. The class counts
`.unwrap()` only, so the metric falls while the panic count is essentially
unchanged. The gain is that each remaining panic states its precondition, not
that panics were eliminated.

One genuine improvement among the vanishings: the DICOM SCP loopback tests had
a hand-rolled `poll_instance` helper that polled `try_recv` in a loop; it was
replaced by the crate's own blocking `StoreScpHandle::recv_timeout`. A local
reimplementation gave way to the first-party API, tests and assertions intact.

**A finding about the reviewer instrument:** the ritk auditor noticed that
`verify_commit.py`'s check 5 was vacuous — `FN_DEF` lacked `re.MULTILINE`, so
`^` matched only at the start of a file and the check matched at most one `fn`
per file. It was vacuous on *every* commit until that fix.

### leto / gaia — unwrap debt is highly concentrated

`leto`'s 72 production unwraps are in **2 files**
(`leto-ops/…/diff/three_dimensional/central.rs` and `staggered.rs`, 36 each).
`gaia`'s true count is 2 (§2.1).

## 6. Independent verification of the landed commits

Every agent commit is re-verified by a reviewer instrument that never reads
the agent's own numbers. It:

1. resolves the base and asserts ancestry plus the size of the commit range — a
   multi-commit audit branch is verified as a whole;
2. rejects any `Cargo.lock` change;
3. re-runs the authoritative scanner on the commit's tree and diffs it against
   the orchestrator's own before-scan, comparing only the **intersection** of
   class keys;
4. checks **tree-level test-integrity invariants**, base vs commit, with
   comment-aware counting: `#[test]` attributes must not fall, and `#[ignore]`
   / `#[allow]` / `#[expect]` must not rise, while assertions and `.expect()`
   calls must not fall;
5. asserts definition-set equality for every changed `.rs` file.

Step 4 is the decisive instrument, and it replaced naive diff-regex scanning
because that scan is wrong in both directions. Over CFDrs' 93-file commit a
diff-regex scan reports "154 deleted `#[test]`, 111 deleted test fns, 315
removed assert lines" — all of them **moves**, which a line-oriented diff cannot
distinguish from deletions. The tree-level counts are unchanged (3370 → 3370
`#[test]`; 6130 → 6130 assertions), and all 171 "deleted" fn names still exist
in the new tree. The one genuinely dropped assert line was
`// assert_eq!(current_widths, center_widths);` — a comment, removed by the
intended `commented_out_code` fix, which is why the counter is comment-aware.

| member | base → commit | files | lock | class deltas | invariants | verdict |
|---|---|---:|---|---|---|---|
| moirai | `562e886e` → `55cc9e96` | 5 | no | −3 | clean (`#[test]` 1216→1216) | **clean** |
| consus | `ad81bb776` → `ef45254c` | 18 | no | −4 | clean (`#[allow]` 13→7) | **clean** |
| CFDrs | `3e662fcae` → `4c007d9995` | 94 | no | −7, no raise | clean (`#[test]` 3369→3369) | **clean** |
| apollo | `9694add9d` → `bacbb2c566` | 58 | no | −5, no raise | clean (`#[test]` 1693→1693) | **clean** |
| kwavers | `9fbecb908a` → `6433a8a984` | 104 | no | −5, no raise | clean (`#[test]` 7244→7244) | **clean** |
| ritk | `de32e1114` → `bb8b2596` | 37 | no | −7, no raise | clean (`#[test]` 6207→6207) | **clean** |

**Six of six verified clean.** Check 5 was also measuring the wrong shape: it
was per-file, but a split legitimately moves functions into a sibling and a
rename makes the old path unreadable at base, so both produced false "lost
function" reports. It now compares whole-tree name sets and reports vanishings
as informational, because legitimate losses exist. Check 4 remains the hard
gate.

Tree-wide function-name preservation across the six commits:

| member | base fns | commit fns | vanished | explanation |
|---|---:|---:|---:|---|
| moirai | 3858 | 3855 | 4 | `read_u8/u16/u32/u64` collapsed into one generic `read_array<const N>` |
| consus | 4332 | 4331 | 4 | `i64/u64/f64_le_dt` → generic `int_le_dt`/`float_le_dt`; `backend` was dead |
| CFDrs | 8117 | 8113 | 5 | 4 internal to the deleted uncompiled file; `print_divergence_stats` went with its only call site (the `print_dbg` cleanup) |
| apollo | 4120 | 4121 | 0 | — |
| kwavers | 17064 | 17064 | 0 | — |
| ritk | 11379 | 11380 | 1 | `poll_instance` replaced by the first-party `StoreScpHandle::recv_timeout` |

**Check 4 is reachability-aware, and that mattered.** It counts only files a
crate root actually reaches — computed per revision from a comment-aware module
walk — because a `#[test]` inside a module the compiler never builds has never
executed and contributes no coverage. CFDrs' deletion of the uncompiled
`poiseuille_bifurcation.rs` is correctly **not** a loss; the instrument reports
it explicitly as `unreachable src files excluded: base=1 commit=0`. A naive
whole-tree count would instead report a false regression of −1 `#[test]`, −2
assertions and −1 `.expect()`. Deleting a *reachable* test still registers, as
does breaking a module declaration so that a file becomes unreachable.

The check was also measuring the wrong thing in two other ways, both fixed: it
ran `git checkout` inside the shared audit worktrees (now it materializes each
revision into a private temp dir via `git archive`), and it compared a
worktree-derived stored before-scan against a blob-derived after-scan, which
manufactured a spurious `crlf_stored_blobs 1 → 0` reduction for moirai. Both
sides are now measured identically, and any residual disagreement with the
stored scan is printed rather than silently folded into a delta.

## 7. Method, and the limits of these numbers

`pm_lines_over_budget` reports 0 under both `--member-path` and `--worktree`
because it reads atlas-level policy data. It is **unmeasured** here, never 0.

**Baseline rows are pin-keyed, and therefore drift.** A row is recorded against
whatever revision the member's gitlink pointed at when the row was written — not
against the member's current head, and not against the revision the next audit
will use. `ritk` is the clearest case, measured with the instrument's own
`scan_repo`:

| revision | `type_suffixed_fns` | `oversized_files` | `oversized_tracked_images` | `pm_lines_over_budget` |
|---|---:|---:|---:|---:|
| row in the brief (atlas `5d9c2a257`, ritk pin `2e346c0d`) | 73 | 45 | 26 | 18352 |
| current committed row (pin `5950857874`) | 62 | 43 | 25 | 0 |
| ritk lane head `de32e1114` | 63 | 44 | 25 | 0 |

The current committed row reproduces **exactly** at `5950857874` across all 12
classes, so the instrument is right and the brief's numbers are older than the
pin. A delta computed against the brief's row would be wrong by ~11 on
`type_suffixed_fns` alone.

Consequence for method: every before/after pair in this report is measured with
**one instrument at one revision** — never against the recorded row, and never
across two revisions in one process (§2.3). Where an agent's base re-measure
disagrees with the committed row, the committed row is the stale one, and the
report says so rather than trying to match it.

**The scanner changed underneath this audit.** The umbrella working tree was
fast-forwarded to `origin/main` at 20:29:29 mid-audit, and
`scripts/atlas-conformance.py` was rewritten in that move: `CLASSES` grew from
42 to 48 entries, adding `unresolved_references`, `second_output_root` and the
four board classes. Figures taken before that span **two scanner revisions**.
The 42 classes common to both are directly comparable; the six new classes were
not measured in the earlier pass and are reported only from the later one. An
early parallel scan run produced 42-key JSON and a later one 48, so a diff tool
reading a missing key as 0 reports six phantom raises — the verification
harness compares only the intersection of keys.

`pull_request_target_use` was also retracted as a live defect: the scanner
tested `"workflow_run" in text` against the raw workflow file, and `metis`
tripped it only because `ci.yml:105,107` reads the API's `workflow_run` **field**
inside an embedded provenance script — not a trigger. A peer session landed
`93e1234ae fix(conformance): Count workflow triggers, not text` while this audit
was running; the current revision parses the YAML and re-measures `metis
pull_request_target_use = 0`.

This is the shared-worktree hazard observed live: another session can move the
tree and the tooling while you measure.
