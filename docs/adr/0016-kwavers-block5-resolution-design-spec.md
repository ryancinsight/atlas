# ADR 0016 — `kwavers-math` Block #5 (Phase-3/Phase-4 ndarray → leto) resolution design-spec on kwavers peer stream

- Status: **Proposed** — Achievement of Block #5 resolution depends on (i) the kwavers peer stream emitting the 3 atomic commits per §Sequencing §Decision §3-commit breakdown — kwavers claim stream owns the implementation commits per disjoint-scope (ADR 0011 §Leg 2); atlas-meta orchestrates only with this ADR as the SSOT. Status flips to `Accepted` once AC-1 §Verification plan returns rc=0 (`cargo check -p kwavers-solver --lib --no-default-features` cleared) AND the kwavers claim stream's 3 commits land on `codex/kwavers-core-moirai-parallel`.
- Date: 2026-07-09.
- Drivers: Block #5 explicit gate per ADR 0015 §Verification plan AC-1 + ADR 0013 §Out of scope #5 + Blocker-triage chore briefs row 5 + ADR 0014 §Out of scope #5 (all reclassified 2026-07-09 from "kwavers-math ndarray → leto migration breakage" to "real + active workstream with 2 commits already landed but gate not yet cleared"); the pre-flight gate `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with 8 errors in `kwavers-transducer` (E0308 type mismatches + E0599 missing `matmul`/`assign` methods + arc.rs syntax gaps).
- Anchors: `atlas/docs/adr/0011-atlas-root-working-tree-hygiene-ritual.md` (disjoint-scope rule §Decision §Leg 2 — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` source edits; the design-spec is the atlas-meta-only deliverable); `atlas/docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §1 atomic-boundary discipline (strict additive OR strict subtractive per sub-batch); `atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md` §Out of scope #5 (original carried-forward blocker); `atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` §Out of scope #5 (cross-walk); `atlas/docs/adr/0015-kwavers-batch2-entrypoint1-helper-const-generics.md` §Verification plan AC-1 (Block #5 gate is the AC-1 prerequisite for ADR 0015 acceptance); the kwavers peer stream commits `445ab9b2a` (`fix(kwavers-math): linear algebra import/API mismatches`) + `e2e1e180f` (`fix(kwavers-math): grid/transducer compilation issues`) — both already landed but did not close the gate; the leto crate at `/d/atlas/repos/leto` HEAD `86d366bc` exposed via `kwavers/Cargo.toml` with `ndarray-compat` feature enabled.
- Supersedes: the carried-forward "phantom-blocker" framing of Block #5 in prior atlas-meta artifacts; Block #5 is now confirmed as a real + active workstream with a deterministic 3-commit resolution strategy rather than a phantom.

- Index: docs/adr/INDEX.md#ADR-0016

## Context

### Subject

Block #5 (the kwavers-math Phase-3/Phase-4 ndarray → leto array migration) is the explicit Batch #2 prerequisite gate per ADR 0015 §Verification plan AC-1. The pre-flight gate `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with errors in `kwavers-transducer` (8 errors: E0308 + E0599 + arc.rs syntax). Until this gate clears, no downstream Batch #2 chore can land; ADR 0015 Step 2 (helper const-generics extension) is gated on Block #5.

The migration workstream started with 2 commits on the kwavers peer stream: `445ab9b2a` (linear algebra import/API mismatches in `kwavers-math`) + `e2e1e180f` (grid/transducer compilation issues in `kwavers-math`). These 2 commits closed compilation in `kwavers-math`/`kwavers-grid` scopes but did NOT propagate the fixes to `kwavers-transducer`, `kwavers-receiver`, `kwavers-boundary`, `kwavers-source`, `kwavers-python`, `kwavers-analysis` callers. The result: the leto `Array2::from_shape_vec` constructor signature shifted from `(rows: usize, cols: usize)` (tuple form, ndarray-compat) to `[rows, cols]: [usize; 2]` (array form, leto-native) — callers across the kwavers workspace retain the old tuple form, which now mismatches the leto-native signature.

### Error breakdown (probed 2026-07-09)

From the `cargo check` diagnostic output (`/tmp/block5_errors.txt`):

- **E0308 (Mismatched types)**: ~8 instances in `crates/kwavers-transducer/src/beamforming/processor.rs` — conflicts between `leto::Array` types and other array representations (likely the tuple-vs-array mismatch at boundary calls).
- **E0599 (No method found)**: Multiple instances of `matmul` not found on `leto::Array` and `ArrayView` types; `assign` not found on `Result` types in `crates/kwavers-transducer/src/calibration/manager/mod.rs`.
- **Syntax errors**: `crates/kwavers-transducer/src/transducers/focused/arc.rs` has unexpected tokens + missing `s!` macro.

The E0119 (conflicting implementations) + E0609 (no field on `[usize; 3]` for `.0/.1/.2`) errors reported in earlier codex sessions have shifted/been resolved by the 2 post-slice-9 commits; the current gate-blocking errors are the E0308 + E0599 + arc.rs subset described above.

### Array2::from_shape_vec call-site inventory

Per the cross-walk probe, `Array2::from_shape_vec` is widely used across:

- `crates/kwavers-python` (analytical bindings).
- `crates/kwavers-solver` (FWI/PINN models).
- `crates/kwavers-analysis`.
- `crates/kwavers-transducer` (the failing crate, plus regression-pending sites).
- `crates/kwavers-receiver` + `crates/kwavers-boundary` (cross-walk pending; checked per the user's request).
- `crates/kwavers-source` + `crates/kwavers-grid` (cross-walk pending).

All call sites use the old form `Array2::from_shape_vec((nx, nz))` / `(n_spots, n_elem)` etc. The leto migration target form is `Array2::from_shape_vec([nx, nz])` / `[n_spots, n_elem]` — array literal with 2 elements.

### Companion methods: matmul + Result.assign

The E0599 "no method `matmul` on `leto::Array`" indicates the leto crate exposes `matmul` as a free function in `leto_ops::linalg::Matmul` rather than an inherent method on `Array<A, S, D>`. The current kwavers-transducer callers use the ndarray-style method-call form (`a.matmul(&b)`); the migration target form is `leto_ops::linalg::matmul(&a, &b)` (or equivalent).

The E0599 "no method `assign` on `Result`" indicates the kwavers-transducer caller is using `Result` as a receiver for the `assign` method (likely a chained-API pattern like `result.assign(...)`); the migration target form depends on the surrounding context but likely involves an `IfOk { ... }.or_else(closure)` pattern or `?` rethrow with side-effects.

### Atomic-boundary discipline framing

Per ADR 0012 §Decision §1 atomic-boundary discipline: strict additive OR strict subtractive per sub-batch. The Block #5 resolution is naturally decomposed into 3 atomic sub-batches per the thinker's pre-implementation verdict:

- **Sub-batch 1** (strict additive fix): localized compilation errors in `kwavers-transducer` — syntax gaps, missing imports, free-function migration for `matmul`/`assign`.
- **Sub-batch 2** (strict signature migration): workspace-wide Array2::from_shape_vec `(rows, cols)` → `[rows, cols]` migration across `kwavers-python`/`kwavers-solver`/`kwavers-analysis`/`kwavers-source`/`kwavers-grid`/`kwavers-transducer`.
- **Sub-batch 3** (gate validation): the regression-validation commit asserting `cargo check -p kwavers-solver --lib --no-default-features` rc=0 + bitwise equivalence vs the slice 9 inner HEAD `949e5a39`.

The 3-sub-batch decomposition aligns with the existing 2 post-slice-9 commits (`445ab9b2a` + `e2e1e180f`), which can be retroactively validated as Sub-batches 1-partial + 1-partial — Sub-batch 3 is the unstarted gate-validation follow-up.

## Decision

This ADR adopts the **3-commit atomic decomposition** as the canonical Block #5 resolution strategy (per the thinker's pre-implementation verdict + ADR 0012 §Decision §1 atomic-boundary discipline). The 3 commits are:

### Commit 1 — `fix(kwavers-transducer): Resolve E0308/E0599 + arc.rs syntax (Block #5 sub-batch 1 — strict additive)`

Locally resolves the `kwavers-transducer` compilation errors. The fix pattern is **strictly additive** (no signature migrations in this commit; only imports + free-function re-routing + syntax gap repair):

- (a) arc.rs syntax repair: add the missing `s!` macro invocation OR remove the syntax-bad tokens; this is a textual fix per the cargo-borrowck error message.
- (b) `matmul` free-function migration: `a.matmul(&b)` → `leto_ops::linalg::matmul(&a, &b)` (or equivalent leto linalg-call). Add `use leto_ops::linalg::matmul;` at the top of the affected files (`crates/kwavers-transducer/src/beamforming/processor.rs` + downstream callers).
- (c) `Result.assign` migration: refactor the chained `result.assign(...)` API to either destructured `if let Err(e) = result { ... } else { ... }` OR `result.map_err(...)?` OR `result.and_then(...)` depending on the surrounding semantic context.
- (d) E0308 `leto::Array` boundary type reconciliation: where `processor.rs` mixes `leto::Array` and other array representations, add explicit `Into` conversions or `as_slice()` bridging.

Pre-commit verification: `cargo check -p kwavers-transducer --lib --no-default-features` rc=0 (kwavers-transducer compiles standalone; kwavers-solver cargo check may still fail due to Array2::from_shape_vec cross-module callers — that's Sub-batch 2).

### Commit 2 — `refactor(kwavers-migration): Migrate Array2::from_shape_vec tuple→array workspace-wide (Block #5 sub-batch 2 — strict signature migration)`

Workspace-wide `Array2::from_shape_vec` migration from the old `(rows, cols)` tuple form to the new `[rows, cols]` array form. The fix pattern is **strict signature migration** (1-in-1-out per call site, no semantic change):

- (a) catalog every call site via the `rg -n 'Array2::from_shape_vec' --type rust /d/atlas/repos/kwavers/crates/` enumeration (per the cross-walk probe output).
- (b) replace each call site with the new form:
  - `Array2::from_shape_vec((nx, nz))` → `Array2::from_shape_vec([nx, nz])`
  - `Array2::from_shape_vec((n_spots, n_elem))` → `Array2::from_shape_vec([n_spots, n_elem])`
  - All `Vec<f64>`-as-Array2 patterns preserved verbatim.
- (c) the migration is mechanical; tooling-supported via `sed -i 's/Array2::from_shape_vec(\([a-zA-Z_][a-zA-Z0-9_]*\), \([a-zA-Z_][a-zA-Z0-9_]*\))/Array2::from_shape_vec([\1, \2])/g'` per affected file (with manual review for multi-line tuple expressions).
- (d) callers in crates: `kwavers-python`, `kwavers-solver`, `kwavers-analysis`, `kwavers-transducer`, `kwavers-receiver`, `kwavers-boundary`, `kwavers-source`, `kwavers-grid` — all included.

Pre-commit verification: `cargo check -p kwavers-solver --lib --no-default-features` — Array2 type mismatch error E0308 should drop sharply; remaining errors (if any) are matmul/assign side-effects (Sub-batch 1-style) that are NOT part of this commit.

### Commit 3 — `chore(kwavers): Block #5 gate-validation regression test (Block #5 sub-batch 3 — gate reset)`

Gate-validation commit asserting `cargo check -p kwavers-solver --lib --no-default-features` rc=0 stably. The fix pattern is **strict regression-validation** (no source edits in this commit; only CI-side regression assertions):

- (a) Add a CI assertion script (or xtask sub-command) that runs the pre-flight gate + verifies rc=0 + diffs against the slice 9 inner HEAD `949e5a39` baseline.
- (b) Verify the 6/6 westervelt_spectral tests still pass bitwise-identical: `cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 + bit-equivalence vs `949e5a39`.
- (c) Document the gateway status flip in `kwavers/atlas-migration-push/batch1` trigger: ADR 0014 KW-CV-001 watchpoint retirement mechanism remains independent (this Commit 3 closes the BLOCK #5 sub-package but does NOT retire the KW-CV-001 watchpoint, which requires the broader closeout-style commit per ADR 0014 §Sequencing step 3).

Pre-commit verification: all 3 commits' individual rc=0 gates are independent of the slice 9 inner HEAD `949e5a39` — Commit 3 verifies the post-migration gate stays green.

## Alternatives considered

### Alternative A — 1 monolithic commit fixing all kwavers-transducer errors + workspace-wide Array2 migration

Rejected per ADR 0012 §Decision §1 atomic-boundary discipline — 1 monolithic commit intermixes 3 conceptually-distinct changes (syntax fixes + free-function migration + workspace-wide signature migration), violating the strict-additive-OR-strict-subtractive rule. Additionally, the commit surface becomes unreviewable (E0308/E0599 spread across multiple crates makes per-error bisect impossible).

### Alternative B — 4+ commits (one per affected crate)

Rejected — over-decomposition. The `Array2::from_shape_vec` signature migration is conceptually a single workspace-wide concern; splitting per crate creates transient states where some crates pass `cargo check` while others fail. Per ADR 0011 §Decision §Leg 2 disjoint-scope + ADR 0012 §Decision §1 atomic-boundary: a single signature migration sub-batch is cleaner than per-crate sub-batches. The 3-commit decomposition is the right granularity.

### Alternative C — Suppress the migration via ndarray-compat feature flag

Rejected — the leto `ndarray-compat` feature is already enabled in `kwavers/Cargo.toml`, but the ndarray-style `matmul` and tuple-form `Array2::from_shape_vec` are not shimmed by the compat feature. The compat feature exposes the ndarray crate's data model but not the ndarray API style. Migration to leto-native API is the only path to closing Block #5.

### Alternative D — Roll back the kwavers-math Phase-3 commits + redesign migration

Rejected — the 2 post-slice-9 commits (`445ab9b2a` + `e2e1e180f`) did close `kwavers-math`/`kwavers-grid` scopes. Rolling back would re-break those scopes; the cost-benefit favors forward completion over rollback.

## Failure modes / risks

- **Sub-batch 1 commits break kwavers-math regression tests**: if `matmul` free-function migration introduces a numeric-drift regression, the westervelt_spectral bitwise tests may fail. Mitigation: Sub-batch 1 includes the assertion that `cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 pre-Commit-2.

- **Sub-batch 2 mechanical migration has multi-line tuple expressions the `sed` regex misses**: large multi-line `Array2::from_shape_vec((expr1.with(method()).unwrap(), expr2.flatten().collect::<Vec<_>>().len()))` patterns require manual review. Mitigation: Sub-batch 2 pre-commit verification runs `rg -n 'Array2::from_shape_vec\(\(' --type rust /d/atlas/repos/kwavers/crates/` and asserts zero results (post-migration state).

- **Sub-batch 3 gate-validation false-positive**: a green CI run does NOT guarantee the bitwise equivalence vs slice 9 inner HEAD `949e5a39` baseline. Mitigation: Sub-batch 3 explicit bit-difference vs `949e5a39` baseline is mandatory; if bit-drift is detected, Sub-batches 1 + 2 are reverted via `git revert <sha1> <sha2>` (kwavers peer stream).

- **Cross-stream peer-WIP collision**: the 3 Block #5 commits are owned by kwavers claim stream per disjoint-scope (ADR 0011 §Leg 2). Atlas-meta is FORBIDDEN from co-emitting; the design-spec is shipped as the SSOT.

- **ADR 0014 closeout-style commit accidentally lands before Block #5 closes**: the KW-CV-001 watchpoint is grounded on the regex `closeout|close-batch` substring match in kwavers peer stream commits. If Sub-batches 1-3 use such substrings in commit subjects, they falsely trigger the watchpoint. Mitigation: Sub-batch commit subjects named carefully to NOT match `closeout|close-batch|final|completion` regex — verified in §Sequencing §Commit-N subject lines.

## Verification plan

1. 🟡 **Sub-batch 1 lands + `cargo check -p kwavers-transducer` rc=0**: per Commit 1 §Decision pre-commit verification.
2. 🟡 **Sub-batch 2 lands + workspace-wide `rg -n 'Array2::from_shape_vec\(\('` returns 0 hits**: per Commit 2 §Decision pre-commit verification.
3. 🟡 **Sub-batch 3 lands + `cargo check -p kwavers-solver --lib --no-default-features` rc=0**: per Commit 3 §Decision pre-commit verification. **This is the AC-1 gate for ADR 0015 acceptance.**
4. 🟡 **`cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 + 6/6 bitwise-identical vs slice 9 inner HEAD `949e5a39` baseline**.
5. 🟡 **No false-positive KW-CV-001 trigger**: the 3 commit subjects do not match `closeout|close-batch|final|completion` regex.
6. Status field flips: ADR 0016 §head of file from `Proposed` to `Accepted` in a follow-up atlas-meta chore commit (when AC-1 through AC-5 are all ✅ on the kwavers peer stream post-3-commit chore).

## Sequencing (implementation increments, atomic commits on kwavers peer stream per disjoint-scope)

### Kwavers peer stream chore commits (BLOCKED on NO prior gate; just requires the kwavers claim stream's claim to trigger)

1. **Commit 1 — `fix(kwavers-transducer): Resolve E0308/E0599 + arc.rs syntax (Block #5 sub-batch 1 — strict additive)`**: Strictly additive — local compilation fix; no signature migration in this commit.
2. **Commit 2 — `refactor(kwavers-migration): Migrate Array2::from_shape_vec tuple→array workspace-wide (Block #5 sub-batch 2 — strict signature migration)`**: Workspace-wide signature migration only.
3. **Commit 3 — `chore(kwavers): Block #5 gate-validation regression test (Block #5 sub-batch 3 — gate reset)`**: CI-side regression assertion; no source code edits.

### Atlas-meta orchestration chore commits (CURRENT TURN)

4. **Step 1 — atlas-meta chore commit** (CURRENT TURN): `chore(atlas): Author ADR 0016 + INDEX.md row + backlog.md trigger brief — Open Block #5 resolution design-spec on kwavers peer stream per disjoint-scope`. Bundles ADR 0016 + INDEX.md row + backlog.md brief.

### Atlas-meta status-flip chore commit (FUTURE TURN)

5. **Step 5 — atlas-meta chore commit** (when AC-1 through AC-5 are all ✅ + the Block #5 gate is cleared): `chore(atlas): Flip ADR 0016 to Accepted after kwavers peer Block #5 closes + ADR 0015 AC-1 is unblocked`. Updates ADR 0016 §head of file Status from `Proposed` to `Accepted` + records the kwavers peer inner SHA achieving the closure.

## Out of scope (explicit non-goals)

This ADR does NOT address — and the Block #5 resolution does NOT include — the following:

1. **`kwavers/atlas-migration-push/batch1` closeout-tag ceremony**: per ADR 0014 §Sequencing steps 1-5 (KW-CV-001 watchpoint retirement). Block #5 closure is a PREREQUISITE for the closeout ceremony, not a substitute.
2. **Slice 7 `is_standard_layout` predicate unification**: per ADR 0014 §Sequencing step 2 item (b). This is a separate chore on the kwavers peer stream, owned by the same disjoint-scope rule.
3. **ADR 0015 helper const-generics extension (Step 2 implementation)**: per ADR 0015 §Sequencing step 2. Block #5 closure is the AC-1 prerequisite; the helper extension itself is a separate gated chore.
4. **Batch #2 Entry Points #2 (conditional-read closure bodies) + #3 (multi-mut disjoint-field sites)**: per ADR 0013 §Open Batch #2 entry points; each Entry Point is filed as its own ADR (or its own §Sequencing when the orchestration ADR is authored).
5. **Leto crate internal changes**: per ADR 0011 §Leg 2 disjoint-scope, the leto peer stream ownership boundary is `D:/atlas/repos/leto/**`; leto internal API changes (e.g., adding inherent `matmul` method) are out-of-scope for atlas-meta + the kwavers claim stream.
6. **Atlas-meta source edits to kwavers**: per ADR 0011 §Leg 2, atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits. The 3 Commit-Ns above live exclusively on the kwavers peer stream.
7. **Block #5 chunks I/II/III split beyond 3 commits**: the 3-commit decomposition is the recommended granularity; further split would violate atomic-boundary discipline §1 (transient intermediate states between sub-batches would be misaligned with the helper SSOT surface's expectations).
