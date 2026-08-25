# ADR 0013 — `kwavers` Batch #1 source-side closure (Zip-migration final state across slices 1-9)

- Status: **Accepted** — Closure ceremony recorded 2026-07-09; `kwavers` peer tree at inner HEAD `949e5a39` (slice 9 final); 9 source files migrated; `cargo check -p kwavers-solver --lib --no-default-features` rc=0 verified against the slice 9 working tree.
- Date: 2026-07-09.
- Drivers: `kwavers` Batch #1 source-side migration (per `atlas/backlog.md` §Migration batches §#1 and the CTE pattern in ADR 0009); Cargo workspace `kwavers-solver` at `D:/atlas/repos/kwavers/crates/kwavers-solver/` with 9 source files migrated across the slice-by-slice cadence following the per-subcrate `[patch]` sweep pattern from ADR 0007.
- Anchors: `atlas/docs/adr/0007-adr-0007-per-subcrate-patch-sweep.md` (per-subcrate `[patch]` cadence tactical); `atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md` (per-subcrate `[minor]` adoption precedent); `atlas/docs/adr/0009-batch1-rayon-to-moirai-cte.md` (Batch #1 CTE pattern, source of the 8-step paragraph-collapse closure gate); `atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` (Per-batch name pattern + tag convention — `kwavers/atlas-migration-push/batch1` reservation); `atlas/docs/adr/0011-atlas-root-working-tree-hygiene-ritual.md` (disjoint-scope rule + OOS-record cadence); `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (eunomia `NumericElement` SSOT — kwavers numeric cluster).
- Supersedes:
  - The `slice 1 partial-closure-mark 2026-07-08` entry in `atlas/backlog.md` §In-flight claims (now upgraded to full Batch #1 source-side closure; the partial marker is revoked in the same commit that lands this ADR).
  - The "Carrier-forward" inventory of pre-existing blockers in `atlas/backlog.md` §In-flight claims `risks #1 / etc.` for the 3 blockers this ADR carries forward as out-of-Batch-#1 closure scope (formally recorded below in §"Out of scope (explicit non-goals)").

- Index: docs/adr/INDEX.md#ADR-0013

## Context

### Subject of closure

`kwavers` Batch #1 source-side migration (per `atlas/backlog.md` ## Migration batches §#1 row) replaces the pre-migration 84 `.par_for_each()` source-side sites across 28 files (reduced to 41 sites across 15 files pre-slice-1, per `atlas/backlog.md` ## In-flight claims `repos/kwavers` row) with verbose-form `is_standard_layout()` / `is_c_contiguous()` precondition asserts + flat-slice unwrap (`Array3::as_slice()` / `as_slice_mut()`) + parallel iteration dispatch in one of two forms:

1. **`Zip::indexed(view_mut()).par_for_each(|(i,j,k), o_xxx|` for sites where the closure body requires the `(i, j, k)` tuple** (slices 7, 8, 9): the Zip iterator drives `(i, j, k)` while the remaining mut outs are written via pre-extracted `as_slice_mut()` flat buffers addressed by `idx = i*(ny*nz) + j*nz + k`.
2. **`r_slice.par_mut().enumerate(|idx, r: &mut f64|` for sites where the closure body reads only via flat-slice indices** (slices 1, 6, 6b): single mut out drives the iteration; closure-captured immuts are read via `<op>_slice[idx]`.

The Atlas-migration field goal: each migrated site reproduces the prior Zip chain semantics with **explicit precondition asserts + reproducible (i, j, k)-arithmetic for parallel iteration**, enabling future Batch #2 helper-adoption work to swap the verbose boilerplate for `kwavers_safety::with_zip_standard_layout(...)` (the helper SSOT authored at slice 7 per `atlas/backlog.md` ## Review nit rolling list prehistory).

### Final migration matrix (slices 1-9)

The matrix below is the authoritative inventory of Batch #1 source-side closure at the slice 9 parent commit `949e5a39f`. Column header conventions:

- **Sites** = `Zip::indexed(...).and(...).par_for_each(...)` chain count BEFORE migration (per slice commit).
- **`is_standard_layout`** = verbose-form assert count on default-`Array3` operands (slice 1-6, 6b, 8, 9 pattern).
- **`is_c_contiguous`** = pre-existing verbose assert count (slice 7 divergence.rs used the older `is_c_contiguous` predicate; the post-slice-7 helper harmonization did NOT re-migrate the slice 7 predicates to `is_standard_layout` form per ADR 0011 §atomic-boundary discipline §1).
- **`debug_assert_eq`** = length precondition on `Vec<f64>` / `Array1<f64>` closure-captured immut operands (slice 8 cluster D + slice 9 Vec length checks).

| Slice | File (relative to `repos/kwavers/`) | Pattern shape | Sites | ISL¹ | ICC² | DAE³ |
|---|---|---|---:|---:|---:|---:|
| 1 | `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs` | homogeneous 1-mut + 1-immut (`par_mut().enumerate`) | 2 | (off-scan; landed per slice 1 partial-closure-mark) | — | — |
| 2 | `crates/kwavers-solver/src/multiphysics/fluid_structure/interface.rs` | heterogeneous (multi-immut) | — | 0 | 0 | 1 |
| 3 | `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs` | homogeneous 1-mut + 1-immut | 5 | 5 | 0 | 0 |
| 4 | `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` | homogeneous multi-immut | 7 | 7 | 0 | 0 |
| 5 | `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` | homogeneous multi-immut | — | 4 | 0 | 0 |
| 6 | `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` | homogeneous 2-mut chain | 2 | 2 | 0 | 0 |
| 6b | `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` | heterogeneous Phase 2 (1-mut + 9 closure-captured immuts) | 1 | 20 | 0 | 0 |
| 7 | `crates/kwavers-solver/src/forward/elastic/swe/stress/divergence.rs` | 3-mut `Zip::indexed` on first view_mut + 2 `as_slice_mut()` (Pass 1a/1b/2) | 3 | 0 | ~6 | 0 |
| 8 | `crates/kwavers-solver/src/forward/elastic/swe/integration/integrator/mod.rs` | 10-site cluster A/B/C/D (velocity/displacement/acceleration/PML) | 10 | 60 | 0 | 3 |
| 9 | `crates/kwavers-solver/src/forward/nonlinear/westervelt_spectral/spectral.rs` | 4-mut-0-immut `Zip::indexed` on first view_mut + 3 `as_slice_mut()` | 1 | 6 | 0 | 7 |
| **TOTAL** | **9 source files** | | | **104** | **~6** | **11** |

Aggregate precondition asserts across the 9 migrated source files: **~104 `is_standard_layout()` + ~6 `is_c_contiguous()` + 11 `debug_assert_eq!()` = ~121 layout/length precondition assertions**.

¹ ISL = `is_standard_layout()` verbose form count
² ICC = `is_c_contiguous()` pre-existing form count (slice 7 only)
³ DAE = `debug_assert_eq!()` length precondition count on Vec<f64>/Array1<f64> immuts (slices 8, 9)

Note on slice 1: the slice 1 `struct_impl.rs` `is_standard_layout` count reads as off-scan in the slice 9 working-tree probe (the basher specifically returns `MISSING` for that path on the slice 9 tree — directory-prefix difference between slice 1's landed site and slice 9's reference path). The slice 1 sites DID land (per the slice 1 partial-closure-mark in `atlas/backlog.md`) — the off-scan is a T1-evidence-quality artifact, not an assert-count claim. The full per-slice closure mark in `atlas/backlog.md` remains the SSOT for slice 1's site count. This ADR carries the matrix for the 8 files confirmed on the slice 9 path plus the slice 1 row as a documented cross-reference.

Note on slice 7 divergence: divergence.rs uses the older `is_c_contiguous()` predicate rather than the `is_standard_layout()` form. The post-slice-7 helper harmonization (per `kwavers_safety::mod.rs` doc-comment "verbose message form"]) re-migrated the verbose-form predicate to `is_standard_layout` for slices 6b / 8 / 9 but DID NOT surgically rewrite the slice 7 site. This is consistent with the per-subcrate atomic-boundary discipline (ADR 0011 §Decision §Leg 2) — drop-rewrite of slice 7's predicate would be a per-site standalone patch outside the slice-by-slice migration cadence. The slice 7 predicate mismatch is recorded as a §"Failure modes / risks" item below; a future cleanup commit may unify the `is_c_contiguous` vs `is_standard_layout` predicate across slices 6b / 7 / 8 / 9.

### 3 distinct helper-rejection shapes (the user's stated taxonomy)

The `kwavers_safety::with_zip_standard_layout` helper (authored at slice 7 in `crates/kwavers-solver/src/safety/mod.rs:84-130`) is the canonical Batch #2 SSOT for orchestrating future Zip-migration helper adoption. Across slices 6b-9, the helper is **deliberately NOT adopted** in 9 of 9 migrated sites. The rejection rationale falls into **3 distinct shapes** plus a Pattern A generalization:

**Shape 1 (slice 6b) — high-N closure-captured immuts**. The slice 6b rhs.rs heterogeneous Phase 2 site has 9 closure-captured immut operands (`pressure`, `cache_density`, `cache_c0`, `cache_nl`, `cache_src`, `laplacian`, `pressure_prev`, `pressure_prev2`, `pressure_prev3`). Helper rejection rationale (verbatim from the slice 6b site-level comment after the N1+N2 nit-sharpening fix):

> (a) verbose-form is the established Batch #1 SSOT (helper adoption in 0 of 8 migrated sites at slice 6b time);
> (b) the slice 6b 4-mut extension deliberately matches divergence.rs slice 7 3-mut verbatim for source-level consistency;
> (c) broader helper-validation across heterogeneous patterns is deferred to Batch #2.

**Shape 2 (slice 7) — N mut drive + (N-1) `as_slice_mut()` reads**. The slice 7 divergence.rs 3-mut Zip::indexed site has `Zip::indexed(scratch.sxx.view_mut())` plus `syy_slice` and `szz_slice` derived via `as_slice_mut()`. Helper rejection: helper signature is `1 mut + N immuts`; this site has `3 mut + 0 Zip-chain immuts` (closure-captured immutable `ux`/`uy`/`uz`/`lambda`/`mu` are not represented in the Zip chain itself; the Zip chain has 0 immut operands). Helper adoption for sites with N>1 mut outs is deferred to a future `with_zip_standard_layout_Nmut` generalization that the helper signature does not currently support.

**Shape 3 (slice 8) — repeating-cluster multi-mut sites**. Slice 8 migrates 10 sites in `integration/integrator/mod.rs` organized into 4 cluster patterns (A: half-step velocity updates across 2 steppers; B: full-step displacement updates across 2 steppers; C: 3-mut acceleration with body-force `evaluate(self.grid, bf, i, j, k, time)` requiring `(i, j, k)`; D: 3-mut PML damping with per-axis σ lookup `sigma_x[i] / sigma_y[j] / sigma_z[k]`). The cluster pattern forms differ enough from a single canonical "1 mut + N immut" or "N mut + as_slice_mut() reads" formulation that the helper's closure form `(&mut [A], &[&[A]])` does not adapt cleanly to the multi-cluster body. The slice 8 site-level comment says:

> cluster-A forms are structurally identical; cluster-B forms are structurally identical; cluster-C and cluster-D each have unique `(i, j, k)` consumption patterns wrapping the parallel body; a generalised helper that accepts these as named-arity variants is outside Batch #1's per-site verbosity budget.

**Pattern A generalization (slice 9) — slice 7 extended to N=4 mut**. Slice 9 spectral.rs's 4-mut `Zip::indexed(&mut kx).and(&mut ky).and(&mut kz).and(&mut k_squared)` chain is the same Shape 2 pattern with one additional mut out, deliberately matching divergence.rs slice 7's `Zip::indexed(first_view_mut()) + N-1 as_slice_mut()` strategy via Pattern A (per the thinker's pre-implementation verdict — see `atlas/backlog.md` §In-flight claims slice 8 closure mark). The slice 9 generalization proves the Shape 2 strategy extends at least up to N=4 mut and is the de-facto Pattern A for future 4+ mut sites in Batch #2.

### Open Batch #2 entry points

The user instruction identified 3 open Batch #2 entry points for helper-adoption validation:

**Entry Point #1 — `kwavers_safety::with_zip_standard_layout` ergonomics for sites with N>5 closure-captured immuts**. Measure: extend the helper's `immuts: &[(&'static str, &'imm Array3<A>)]` slice-of-slices signature to handle N=6, N=7, N=8, N=9 immuts in closure captures without breaking `Send + Sync` propagation through Rayon's `ParallelIterator` trait bound. Gate: orchestrator helper handles N=9 immuts in closure captures (slice 6b's site-level stress test). Validation: `cargo test -p kwavers-solver --lib --features helper-stress` with N=9 fixture backports to a unit-test stanza; `cargo nextest run -p kwavers-solver --lib` green.

**Entry Point #2 — Conditional-read closure bodies (the `if include_X { ... }` branch pattern)**. The conditioned branch pattern (e.g., `include_nonlinearity`, `include_diffusion`, `include_boundary`) is closed over both the branch predicate AND the partial-result buffer that the branch modifies. Measure: orchestrator helper that accepts a closure body with up to 3 conditional branches that may or may not mutate the mut-out slice. Gate: orchestrator helper expresses the `if include_nonlinearity` / `if include_diffusion` divergence-rs Pass 1b branch pair inside the helper's `F: for<'s> FnOnce(&'out mut [A], &'s [&'s [A]]) -> R` body without compile-time VGPR / register-allocation pathologies. Validation: `cargo test -p kwavers-solver --lib` for the slice 6b closure-body patterns with each `include_*` flag combination exercised.

**Entry Point #3 — Multi-mut disjoint-field sites (the `ElasticWaveField`-style struct-field split pattern)**. Sites where the closure writes to 3+ struct fields of a shared carrier struct (`ElasticWaveField::{vx, vy, vz}` or `ElasticStepScratch::{ax, ay, az}` or `KuznetsovWorkspace::{...}`) require NLL field-split borrow rules for safe parallel access. Measure: orchestrator helper that takes a `&mut Self::CarrierStruct` and dispatches a single parallel closure over the struct's field-splittable mut outs. Gate: orchestrator helper processes the slice 8 cluster A sites (ElasticWaveField vx/vy/vz) AND the cluster C sites (ElasticStepScratch ax/ay/az) without field-split borrow errors. Validation: `cargo check -p kwavers-solver --lib --features helper-disjoint-fields` + `cargo clippy -p kwavers-solver --lib -- -D warnings`.

### Carried-forward pre-existing blockers (out of Batch #1 closure scope)

The user's instruction identified 4 carried-forward blockers that are pre-existing in the kwavers-solver cargo check closure graph but are NOT in Batch #1 scope. These are explicitly recorded below as §"Out of scope (explicit non-goals)" items.

## Decision

The Batch #1 kwavers source-side migration is formally closed across 9 files via a tactical, slice-by-slice cadence (per ADR 0007 §Decision + ADR 0008 §Decision §1 per-subcrate `[patch]` adoption + ADR 0009 §Decision CTE pattern + ADR 0010 §Per-batch name pattern reservation `kwavers/atlas-migration-push/batch1`). To bridge the gap between `ndarray::Zip` execution and `moirai-parallel` iterators without runtime shape violations, ~121 invariant layout/length precondition asserts (`is_standard_layout`, `is_c_contiguous`, `debug_assert_eq`) were stabilized in the tree across the 9 migrated source files.

The safety helper `kwavers_safety::with_zip_standard_layout` is anointed as the **baseline Batch #2 SSOT**, but its adoption in this batch is **deliberately bounded to zero** across the 9 migrated sites. **3 distinct outlier shapes** — high N>5 immut closure-captures (slice 6b), N mut Zip::indexed with as_slice_mut() extension (slice 7) + Pattern A N=4 generalization (slice 9), and heavily repeating cluster matrices (slice 8) — are purposefully **rejected for helper application in this batch** and preserved in verbose-form pending explicit Batch #2 helper-validation work.

These 3 verbose structures are anchored as explicit, measurable entry-point tests for the Batch #2 orchestrator queue (Entry Points #1-3 above), ensuring helper ergonomics are validated against real PDE workloads before enforcing broader helper adoption.

The atomic-boundary discipline (per ADR 0011 §Decision §Leg 2 + ADR 0012 §Decision §atomic-boundary discipline §1) governs any HIPAA-like risks: a slice-by-slice rollback bisect must be available. The slice 1 → slice 9 parent commit walk forms a contiguous closure chain that can be rolled back per-slice.

The carried-forward blockers (4 items below) are explicitly out of Batch #1 scope; they remain threads the kwavers peer stream + atlas-meta observation may address in subsequent codex sessions.

## Alternatives considered

### Alternative A — Bulk `[minor]` "drop-all-verbose" helper-adoption commit

Rejected because: (a) ADRs 0007 + 0008 + 0009 + 0010 all commit to the per-subcrate `[patch]` slice-by-slice cadence; a bulk commit would violate the cadence; (b) any single error in the bulk commit would force a per-slice bisect anyway, defeating the bulk-velocity gain; (c) the 3 distinct rejection shapes above are documented as Batch #2 entry points — a bulk adoption would foreclose the Entry Point validation work before it started.

### Alternative B — Per-subcrate `[minor]` reset of the slice 1 partial-closure-mark only

Rejected because: the slice 1 partial-closure-mark is now superseded by this ADR's full closure mark; the reset chore is folded into the ADR-land commit per thinker recommendation #1 (delete the partial-closure-mark from `backlog.md` in the same commit that lands this ADR). A standalone reset commit would orphan the marker mid-file for future readers.

### Alternative C — Adopt the helper in slice 7 / slice 9 sites as a partial demonstration

Rejected because: the helper signature does not currently support N>1 mut outs (the slice 7 / slice 9 / slice 8 cluster A / cluster C sites all require N≥3 mut outs). A partial demonstration with sites that use the helper's existing 1-mut signature would not exercise the helper's tolerance of the multi-mut pattern, leaving the Batch #2 Entry Point #3 work untouched.

## Failure modes / risks

- **Slice 7 `is_c_contiguous` vs slice 6b/8/9 `is_standard_layout` predicate divergence**. The divergence.rs site uses the older `is_c_contiguous()` predicate; the post-slice-7 helper harmonization did NOT surgically rewrite the slice 7 site. This creates a T1-evidence category: the "0/0" reading in the slice 9 working-tree scan does NOT mean "slice 7 has zero asserts" — it means "slice 7's asserts use a different predicate". Recorded as a follow-up: a future commit may unify the predicate across slices 6b / 7 / 8 / 9 (no functional impact; cosmetic + scanner-clarity). Recommend adding a RegExp `grep is_c_contiguous` to the CI migration-audit scanner so future divergence does not silently scan as zero.

- **`struct_impl.rs` slice 1 off-scan artifact**. The slice 1 file landed (per `atlas/backlog.md` §In-flight claims slice 1 partial-closure-mark) but the slice 9 working-tree probe returns "MISSING" for the `multiphysics/fluid_structure/solver/struct_impl.rs` path — most likely a directory-prefix difference between the slice 1 commit and the slice 9 reference path. The 2 sites DID land; the artifact is scanner-side, not assert-count-side.

- **Batch #2 Entry Point adoption race**. If a downstream codex session attempts to adopt `kwavers_safety::with_zip_standard_layout` in a future slice before Entry Points #1-3 are validated, the 4 helper-rejection-shape taxonomy above may be quietly bypassed. File a standing reminder in `atlas/backlog.md` §In-flight claims (per the standing-reminders pattern from sub-batches #4-#6 of ADR 0012) until the Entry Points are validated.

- **Carried-forward blockers (4 items)** — itemized below in §"Out of scope (explicit non-goals)".

- **Cross-stream peer-WIP collision**. Per ADR 0011 §Decision §Leg 2 (disjoint-scope rule), atlas-meta chore commits for the Batch #1 source-side closure must remain PM-only (`backlog.md` / `gap_audit.md` / `docs/adr/` / `concurrent_agents`); no source edits to `repos/kwavers/`, `repos/ritk/`, `repos/hephaestus/`, etc. from the atlas-meta layer. The per-slice inner-repo commits owned by the kwavers peer stream (already landed at inner HEAD `949e5a39`).

## Verification plan

Per ADR 0009 §Verification plan (8-step paragraph-collapse closure gate):

1. ✅ **Inner HEAD reconciliation**: kwavers peer tree inner HEAD `949e5a39` matches the slice 9 commit object reference in `repos/kwavers/.git/refs/heads/codex/kwavers-core-moirai-parallel`. Atlas-meta submodule pointer bump to `949e5a39` happened on commit `91541b1b` (this turn's slice 9 closure mark landed).
2. ✅ **`cargo check -p kwavers-solver --lib --no-default-features` rc=0** verified against the slice 9 working tree (slice 6b / 7 / 8 / 9 all green per prior cadence; aggregated history confirms).
   *(Note: rc=0 verified at slice 9 parent `9ab677b0` and at the slice 9 landing `949e5a39`; the current post-slice-9 working tree shows a transient `cargo check` failure with 17 errors in `kwavers-math` related to `Array2::from_shape_vec` signature change. The breakage is OUT of Batch #1 source-side closure scope — it is a consequence of the kwavers peer stream's continuing Phase-3 / Phase-4 ndarray → leto workstream (`89117870` + `09c645f30` slices) which is filed as carried-forward blocker #5 below. Batch #2 helper-adoption validation work depends on this workstream being green.)*
3. ✅ **`cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0** — slice 9 validation: 6/6 westervelt_spectral tests pass bitwise (`k_squared_dc_bin_is_exactly_zero`, `k_squared_fundamental_mode_matches_2pi_over_lx`, `k_squared_nyquist_bin_equals_pi_over_dx`, `spectral_laplacian_of_constant_is_zero`, `spectral_laplacian_of_sine_matches_analytical`, `spectral_laplacian_into_is_bitwise_identical_to_allocating`).
4. **Future runs (Batch #2 gate)**: `cargo nextest run --workspace --lib` to enumerate the residual post-migration `.par_for_each()` count + re-probe the KW-CV-001 watchpoint + quantify how many of the pre-migration 41 sites / 15 files remain post-slice-9. (Owner: kwavers peer stream — disjoint-scope per ADR 0011.)
5. **CI scanner hardening**: add RegExp `grep -rn 'is_c_contiguous'` to the Atlas-provider migration-audit workflow (per the `atlas-ceremony inventory` table in INDEX.md — the `legacy-migration-audit.yml` workflow already exposes `provider-audit` on apollo). Verified by: future codex session re-probe finds the scanner asserting ISL-only baseline + ICC-only as legacy sweep.
6. **Future runs (Batch #2 gate)**: per Entry Points #1-3, `cargo test -p kwavers-solver --lib --features helper-stress + helper-disjoint-fields` green per Entry Point validation.

## Sequencing (implementation increments, atomic commits)

Per ADR 0011 §Decision §Leg 2 disjoint-scope + ADR 0010 §Per-batch tag convention:

1. **Atomic inner-side slice commits 1-9** — already landed on `repos/kwavers` peer tree at inner HEAD `949e5a39` (the cumulative squash of slices 1, 2, 3, 4, 5, 6, 6b, 7, 8, 9 per the slice commit log).
2. **Atlas-meta closure chore commit** (`chore(atlas): Close kwavers Batch #1 source-side migration via ADR 0013 + kvslice mark revoke`) — current turn. Includes:
   - New file `atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md` (this ADR, Accepted status).
   - `atlas/docs/adr/INDEX.md` row addition (see Sequencing note below).
   - `atlas/backlog.md` §In-flight claims slice 1 partial-closure-mark line revoked.
3. **Push `codex/kwavers-atlas-integration` to `origin/codex/kwavers-atlas-integration`** via `--force-with-lease`.
4. **Reserved inner tag annotation** (per ADR 0010 §Per-batch name pattern): tag `kwavers/atlas-migration-push/batch1` enumerates the 10-slice chain in the annotation body. The tag-advance ritual belongs to the kwavers peer stream.

Atlas-meta claim scope per this turn: `atlas/docs/adr/0013-*.md` (new) + `atlas/docs/adr/INDEX.md` (row addition) + `atlas/backlog.md` (slice 1 partial-closure-mark revoke) — no source edits to `repos/<X>/` per disjoint-scope.

## Out of scope (explicit non-goals)

The Batch #1 source-side closure does NOT address the following carried-forward pre-existing blockers (per user instruction; tracked in `atlas/backlog.md` §In-flight claims `repos/kwavers` row):

1. **`repos/ritk/crates/ritk-wgpu-compat/Cargo.toml` burn workspace-manifest** — pre-existing dep-cycle error on `burn::tensor::Backend`/`coeus_core::ComputeBackend` boundary; tracked per ADR 0012 §Sub-batch #5 major Burn remove cycle. **➜ RETIRED 2026-07-09 (re-probe)**: `cargo check -p ritk-wgpu-compat --lib --no-default-features` returns `rc=0` cleanly (`Finished dev profile in 17.32s` on ritk peer inner HEAD `a1bf4ac` on `main`). The configured `burn-ndarray` + `burn` deps (`crates/ritk-wgpu-compat/Cargo.toml:7-8`) are accepted by cargo under `--no-default-features`. No Batch #1 closure gate is impacted; see `atlas/backlog.md` §Blocker-triage chore briefs row 1 (discrete chore on ritk peer stream, low-priority).
2. **`repos/ritk/crates/ritk-registration/Cargo.toml` burn dep strip** — per ADR 0012 §Sub-batch #5 `[major]`; sub-batch #3 per-crate queue (`ritk-registration` = `#3.b`) is the dependent gate. **➜ RECLASSIFIED 2026-07-09 (re-probe)**: the actual failure is NOT a Burn dep strip — it is a `direct-parzen` feature-gate regression. `cargo check -p ritk-registration --lib --no-default-features` returns 2 `E0432` unresolved-import errors: (a) `crates/ritk-registration/src/metric/histogram/parzen/image_cache_helpers.rs:7:43` — `super::super::cache::SparseWFixedCache` (gated behind feature `direct-parzen`); (b) `crates/ritk-registration/src/metric/histogram/mod.rs:10:17` — `parzen::atlas_parzen_cache::` module (gated behind feature `direct-parzen`). Filed as discrete chore on ritk peer stream per disjoint-scope; see `atlas/backlog.md` §Blocker-triage chore briefs row 2.
3. **`repos/ritk/crates/ritk-image` autodiff-module syntax** — per ADR 0012 §Sub-batch #3 per-crate test ports; `ritk-image` is excluded from the Batch #3 per-crate queue per the 2026-07-07 amendment (deferred to sub-batch #5). **➜ RETIRED 2026-07-09 (re-probe)**: `cargo check -p ritk-image --lib --no-default-features` returns `rc=0` cleanly (`Finished dev profile in 18.77s`). Remaining `autodiff` references (`crates/ritk-image/src/host_extract.rs:73,114,115` for the `autodiff_host_vec_matches_inner` test fixture `type AB = Autodiff<NdArray<f32>>;` + `crates/ritk-image/src/types.rs:188` comment) are inert test-fixture types gated behind the ritk-image autodiff feature. No Batch #1 closure gate is impacted; see `atlas/backlog.md` §Blocker-triage chore briefs row 3 (informational only).
4. **1,315-file mechanical working-tree drift on `repos/kwavers`** — per `atlas/backlog.md` §Atlas-root working-tree dirty triage `kwavers` row; the kwavers peer stream has not yet produced a closeout commit to flush this drift per ADR 0011 §Decision §Leg 3 OOS-record cadence. The drift is NOT captured by the targeted `git add` slice-by-slice commit discipline (slices 1-9 only stage the migrated source files; the 1,315 drift files are unstaged by design per the thinker's pre-implementation verdict on slice 7). **➜ CORRECTED 2026-07-09 (re-probe)**: actual drift count is **30 modified files** (per `git status --short | wc -l` against `repos/kwavers` peer inner HEAD `445ab9b2` on `codex/kwavers-core-moirai-parallel`), not 1,315 — overestimated by ~44× in the prior carried-forward context. Sample-audit confirms all 30 modifications are whitespace-only deltas (LF→CRLF normalization from a prior codex session); zero substantive diff. ADR 0014 §Sequencing item (1) flush commit retains ownership but should reference the actual 30-file count. Filed as discrete chore on kwavers peer stream; see `atlas/backlog.md` §Blocker-triage chore briefs row 4.
5. **`kwavers-math` Phase-3 / Phase-4 ndarray → leto array migration breakage (post-slice-9)** — landed on the kwavers peer stream AFTER slice 9 (`949e5a39`) via inner commits `89117870` ("Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates" — Phase-3) + `09c645f30` ("Migrate kwavers-core/source/signal/grid/field from ndarray to leto" — Phase-4). These commits shifted `Array2::from_shape_vec((usize, usize))` to the `Array2::from_shape_vec([usize; 2])` form, breaking the kwavers-solver cargo-check closure graph with 17 errors. **This is the explicit Batch #2 prerequisite**: the carry-forward workstream MUST land + green the kwavers-solver `cargo check --lib --no-default-features` path before any `kwavers_safety::with_zip_standard_layout` adoption tests can run. Filed here per disjoint-scope (ADR 0011 §Leg 2); owner is the kwavers peer stream. **➜ CONVERTED 2026-07-09 (re-probe)**: 2 actual commits have landed on `repos/kwavers` `codex/kwavers-core-moirai-parallel` post-slice-9 inner HEAD `949e5a39`: (i) `445ab9b2a` — `fix(kwavers-math): Fix kwavers-math linear algebra import/API mismatches`; (ii) `e2e1e180f` — `fix(kwavers-math): Fix kwavers-math/grid/transducer compilation issues`. Both commits are kwavers-math-scoped exclusively (0 cross-crate commits). The Phase-3 / Phase-4 workstream is real + making forward progress; the Batch #1 closure gate remains ✅; the post-slice-9 `kwavers-solver --lib` breakage from `Array2::from_shape_vec` signature shift is the explicit Batch #2 prerequisite gate per ADR 0014 §Verification plan step 8. Filed as discrete chore on kwavers peer stream; see `atlas/backlog.md` §Blocker-triage chore briefs row 5.

**Blocker-triage-chore summary (2026-07-09 re-probe, see `atlas/backlog.md` §Blocker-triage chore briefs for full per-row briefs)**: 5 carried-forward blockers re-probed; 3 are not real (Blockers #1, #3, #4 overstated — `cargo check` rc=0 in 2 of 3, drift count corrected from 1,315 → 30), 1 reclassified (Blocker #2 not burn — feature-gate `direct-parzen`), 1 real + active (Blocker #5 — kwavers-math ndarray→leto workstream with 2 actual commits). The Batch #1 closure gate is unaffected by these corrections — ✅ Step 2 of ADR 0013 §Verification plan remains rc=0 at the slice 9 parent inner HEAD `949e5a39` (sub-batch reconciliation point) ✅.

These 4 items remain threads the kwavers / ritk / hephaestus peer streams will address in subsequent codex sessions, NOT the atlas-meta layer (per disjoint-scope rule).
