# ADR 0015 — `kwavers-solver` Batch #2 Entry Point #1: `with_zip_standard_layout` const-generics arity extension (N=6/7/8/9 immuts)

- Status: **Proposed** — Achievement of the Entry Point #1 acceptance criteria depends on (i) Block #5 (kwavers-math Phase-3/Phase-4 ndarray → leto migration) gate clearance (per ADR 0013 §Out of scope #5 + ADR 0014 §Out of scope #5, reclassified 2026-07-09 per Blocker-triage chore briefs row 5), AND (ii) the kwavers peer stream emitting the helper extension commit + slice 6b backport fixture per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` source edits). Status flips to `Accepted` once Block #5 gate clears + the acceptance criteria in §Verification plan all return rc=0 + bitwise-identical.
- Date: 2026-07-09.
- Drivers: ADR 0013 §Open Batch #2 Entry Point #1 (`kwavers_safety::with_zip_standard_layout` ergonomics for sites with N>5 closure-captured immuts); the helper SSOT at `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs:84-130` currently uses dynamic `&'imm [(&'static str, &'imm Array3<A>)]` immut slices which forces runtime indexing at high-N sites (slice 6b rhs.rs uses 9 immuts and cannot destructure them in the closure body without `Vec` allocation overhead + local-lifetime friction).
- Anchors: `atlas/docs/adr/0011-atlas-root-working-tree-hygiene-ritual.md` (disjoint-scope rule §Decision §Leg 2 — atlas-meta is PM-only across this chore; source work lives on kwavers peer stream); `atlas/docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §1 atomic-boundary discipline (strict additive OR strict subtractive per sub-batch); `atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md` (immediate predecessor — captures the slice 1-9 source-side closure mark + Entry Point #1 narrative); `atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` (Block #5 gate explicit prerequisite for Batch #2 start); the helper SSOT surface itself at `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs:84-130` (current signature); the slice 6b 9-immut heterogeneous Phase 2 site at `D:/atlas/repos/kwavers/crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs:compute_rhs` (`is_heterogeneous` branch — Phase 2 closure body).
- Supersedes: ADR 0013 §Open Batch #2 Entry Point #1 (the high-level entry-point narrative) is refined (not replaced) by this ADR with a concrete const-generics arity design + acceptance criteria + dispatch discipline. ADR 0013 Entry Point #1 paragraph stays as the strategic framing; this ADR extends it with the tactical implementation contract.

- Index: docs/adr/INDEX.md#ADR-0015

## Context

### Subject

Batch #2 Entry Point #1 is the post-Batch-#1 ergonomic-validation workstream that tests whether the `with_zip_standard_layout` helper (Slice 7 SSOT) supports high-N immut closure captures (N=6/7/8/9) without breaking `Send + Sync` propagation through Rayon's `ParallelIterator` trait bound. The current helper signature handles N immuts via a dynamic slice-of-tuples:

```rust
pub fn with_zip_standard_layout<'out, 'imm, A, F, R>(
    out_name: &'static str,
    out: &'out mut Array3<A>,
    immuts: &'imm [(&'static str, &'imm Array3<A>)],
    f: F,
) -> R
where
    A: Copy + Send + Sync,
    F: for<'s> FnOnce(&'out mut [A], &'s [&'s [A]]) -> R,
```

The dynamic slice forces the closure body to perform fragile runtime indexing (`immuts_slice[0]`, `immuts_slice[8]`) and allocates a local `Vec<&'imm [A]>` inside the helper which conflicts with Rayon's parallel-borrow rules when the closure body calls `r_slice.par_mut().enumerate(|idx, r| { ... })` — Rayon's `par_mut` reborrows `r_slice`, but the local `Vec` lifetime is shorter than the helper's `'imm` lifetime, requiring the higher-rank trait bound `F: for<'s> FnOnce(&'out mut [A], &'s [&'s [A]]) -> R`.

At N=9 (slice 6b rhs.rs Phase 2 site), this ergonomic friction is significant: the verbose-form migration kept 9 immut operands as named `&Array3<f64>` borrows + 9 separate `as_slice()` reads + 9 `is_standard_layout()` asserts at the call site. The helper, if adopted, would consolidate the 18-per-call boilerplate (9 asserts + 9 unwraps) into a single helper invocation + a 9-element closure argument.

### Helper ergonomics problem at N=9

The current signature's ergonomic friction manifests in 3 places:

1. **Local `Vec` allocation** in helper body: `let immut_slices: Vec<&'imm [A]> = immuts.iter().map(...).collect();` — the heap-allocated `Vec` lifetime is strictly shorter than the helper's `'imm` (the helper's `'imm` outlives the helper invocation; the local `Vec` is bound to the helper invocation). Compiler-correct today (the `'s` HRTB puns over this), but generates a 9-element `Vec` allocation per call which is wasteful for sites that already know their N at compile time.

2. **Closure body runtime indexing**: the closure receives `&'s [&'s [A]]` (slice of slices) and must index into it: `immut_slices[0]`, `immut_slices[1]`, `immut_slices[8]`. Compiler cannot elide bounds checks at compile-time even when N is known statically.

3. **No compile-time N verification**: if a caller passes 7 immuts but the closure body uses `immut_slices[8]`, the bug surfaces as a runtime panic at the migration site, not as a compile-time type error.

### Slice 6b as canonical 9-immut unit-test fixture

The slice 6b site (`rhs.rs::compute_rhs` `is_heterogeneous` branch) is the canonical 9-immut Phase 2 unit-test fixture candidate for Entry Point #1 acceptance validation because:

- It already has 9 separate verbose-form `is_standard_layout()` asserts + 9 `as_slice()` unwraps (matching the helper pattern exactly).
- It has 1 mut (`rhs`) which matches the helper's 1-mut invariant.
- It exercises the conditional-branch pattern (`include_nonlinearity`, `include_diffusion`) within the closure body — a forward-compat test for Entry Point #2.
- The existing 6/6 westervelt_spectral tests + cargo-check baseline at kwavers peer inner HEAD `949e5a39` provide the bitwise-equivalence reference.

### Block #5 explicit prerequisite

Per ADR 0013 §Out of scope #5 (reclassified 2026-07-09 per Blocker-triage chore briefs row 5; current state: 2 actual commits landed on kwavers peer stream: `445ab9b2` + `e2e1e180f`), the kwavers-math Phase-3/Phase-4 ndarray → leto migration workstream is the explicit Batch #2 prerequisite gate. The current pre-flight `cargo check -p kwavers-solver --lib --no-default-features` returns multiple `E0119` (conflicting implementations for `leto::Array<f64, VecStorage<f64>, 3>` + `leto::Array<bool, VecStorage<bool>, 3>`) + `E0609` (no field on `[usize; 3]` for `.0/.1/.2` field access) errors in `kwavers-receiver` + `kwavers-boundary`. Entry Point #1 work cannot land until Block #5 gate clears.

## Decision

This ADR adopts the **const-generics arity extension** as the canonical helper signature change for Entry Point #1. The design replaces the dynamic slice-of-tuples with a const-generic array `[(&'static str, &'imm Array3<A>); N]` so that:

1. **No `Vec` allocation** in helper body: the immut slices are pre-extracted via the iterator and collected into a stack-allocated `[&'imm [A]; N]` array instead of a heap-allocated `Vec<&'imm [A]>`.
2. **Compile-time N verification**: the array length is part of the helper's type signature; passing `[("a", arr1), ("b", arr2)]` (2 immuts) vs `[..., ......, 9 arrays]` produces distinct monomorphizations rather than runtime-length-checked slice.
3. **Direct closure destructuring**: the closure receives `[&'s [A]; N]` and can destructure inline: `|r_slice, [p_slice, cd_slice, c0_slice, nl_slice, src_slice, lap_slice, pp_slice, pp2_slice, pp3_slice]| { ... }`.

The proposed new signature:

```rust
pub fn with_zip_standard_layout<'out, 'imm, A, F, R, const N: usize>(
    out_name: &'static str,
    out: &'out mut Array3<A>,
    immuts: [(&'static str, &'imm Array3<A>); N],
    f: F,
) -> R
where
    A: Copy + Send + Sync,
    F: FnOnce(&'out mut [A], [&'s [A]; N]) -> R,
```

Notes on the changes:

- `const N: usize` is added as a const-generic parameter; per Rust 2021 const-generics, this is monomorphized at each call site producing minimal binary impact (N=6/7/8/9 each get their own `with_zip_standard_layout` instantiation).
- The HRTB `for<'s>` may or may not be needed depending on how the immut-slice lifetime extends; the canonical design lifts the local-`Vec`-lifetime issue entirely, allowing the simpler `F: FnOnce(&'out mut [A], [&'s [A]; N]) -> R` (the `'s` is inferred at call-site from the closure body lifetime).
- `A: Copy + Send + Sync` constraint is preserved (verbatim from the current helper); the const-N change does NOT relax these bounds — the Send + Sync guarantee is the explicit Entry Point #1 acceptance criterion for Rayon compatibility.

The acceptance criteria for this ADR's `Accepted` status flip are:

- **AC-1**: `cargo check -p kwavers-solver --lib --no-default-features` rc=0 (Block #5 gate cleared).
- **AC-2**: `cargo test -p kwavers-solver --lib` rc=0 (existing tests pass bitwise).
- **AC-3**: The 6/6 westervelt_spectral tests pass bitwise-identical vs the slice 9 inner HEAD `949e5a39` baseline (no numerical drift).
- **AC-4**: A new `helper-stress` test fixture (or a `#[cfg(test)]` stanza) backports the slice 6b 9-immut Phase 2 site as a unit test exercising the `with_zip_standard_layout` const-generics API with N=9; the fixture's bitwise output matches the verbose-form RHS computation at all (i, j, k) grid points within `f64` epsilon.
- **AC-5**: The slice 6b site itself (or a backport) demonstrates the const-generics helper ergonomics by adopting the helper in-place and re-running AC-2/AC-3/AC-4 to confirm the adoption preserves bitwise equivalence.

## Alternatives considered

### Alternative A — Macro-based arity (`with_zip_standard_layout_N!` macro family)

Rejected because: (a) macros hide the type signature, complicating future readers' audit surface; (b) the `[(&str, &Array3<A>); N]` const-generics form retains type-system integration (the macro form does not); (c) compiler-generated docs (rustdoc) on the const-generics form are auto-generated per arity; the macro family cannot produce rustdoc per-arity without doc-comment rewriting.

### Alternative B — Generic tuple driven by macro_rules repetition

Rejected because: (a) tuples of 6/7/8/9 `(name, &arr)` pairs are unwieldy and do not interact well with HRTBs; (b) the helper's caller would still need a macro to construct the tuple at the call site, yielding the macro-form problems again.

### Alternative C — Keep dynamic slice signature; add `N: usize` compile-time hint via associated `const`

Rejected because: (a) the associated constant cannot be examined by the helper signature to elide `Vec` allocation — the helper must still collect into a vector because the slice length is dynamic at the function-call level; (b) does not solve the closure-body runtime-indexing problem.

### Alternative D — Variadic tuples via `extern "C"` variadic functions or nightly `#![feature(variadic_tuple)]`

Rejected because: (a) variadic functions in Rust are nightly-only and unsuitable for stable-channel production code; (b) the const-generics form is fully stable since Rust 1.51 (March 2021).

## Failure modes / risks

- **Block #5 gate persists**: kwavers-math ndarray → leto migration may not clear before the kwavers peer stream's next codex session, leaving the const-generics extension blocked at the pre-flight gate. Mitigation: Block #5 is owned by kwavers claim stream per disjoint-scope; atlas-meta's only mitigation is to flag the standing reminder in `atlas/backlog.md` §In-flight claims row.

- **Const-N monomorphization bloat**: each distinct `N` produces its own compiler-monomorphized helper instantiation, growing code size at compile time. Mitigation: at expected call-site N distribution (N=0 through N=9 typical), the bloat is bounded (≤ 10 monomorphizations × ~3 KB of IR per monomorphization = ~30 KB binary impact). For sites using N=1 through N=5 (the common case after slice migrations 1-8), the bloat is negligible.

- **`[&'s [A]; N]` lifetime conflict with `par_mut`**: Rayon's `par_mut().enumerate(|idx, r| ...)` borrows `r_slice` for `'r_mut`, but the immut-slice array `[&[A]; N]` is captured by the closure. The borrow checker must verify no overlap. Mitigation: the const-N design pre-extracts the immut slices BEFORE the closure is constructed, separating the immut-borrow lifetime from the par_mut-borrow lifetime; this is structurally sound under Rust 2021 disjoint-capture rules (a closure auto-captures only what it uses).

- **Slice 6b backport fixture bitwise mismatch**: the slice 6b site has conditional branches (`if include_nonlinearity`, `if include_diffusion`) that the helper invocation must expose through the closure body without semantic change. Mitigation: AC-4 mandates bitwise-equivalence validation against the verbose-form RHS at all (i, j, k) grid points; the fixture test asserts `|r_helper - r_verbose| < f64::EPSILON` for every grid point.

- **Atlas-meta accidentally co-emits a kwavers source change**: violates disjoint-scope (ADR 0011 §Leg 2). Mitigation: atlas-meta's chore commits are restricted to `atlas/docs/adr/**` + `atlas/backlog.md` + `atlas/.gitmodules`; the implementation commits live exclusively on `D:/atlas/repos/kwavers/**`.

## Verification plan

1. 🟡 **Block #5 gate cleared**: `cargo check -p kwavers-solver --lib --no-default-features` returns rc=0 against the kwavers peer stream's post-`445ab9b2`/`e2e1e180f` HEAD. Re-probe owner: `repos/kwavers` claim stream per disjoint-scope.
2. 🟡 **Helper const-generics extension commit lands on kwavers peer stream**: `git log --oneline -5 -- crates/kwavers-solver/src/safety/mod.rs` enumerates a commit titled `feat(kwavers-safety): Extend with_zip_standard_layout with const-generics arity for N=6/7/8/9 immuts` (or equivalent). The helper signature changes from `&[(&str, &Array3<A>)]` to `[(&str, &Array3<A>); N]` with `const N: usize`.
3. 🟡 **Slice 6b backport fixture**: a `helper-stress` test (or `#[cfg(test)]` stanza) in `crates/kwavers-solver/tests/` exercises the const-generics helper with N=9 on the slice 6b rhs.rs Phase 2 fixture. The test asserts bitwise equivalence vs the verbose-form RHS at all grid points within `f64::EPSILON`.
4. 🟡 **`cargo test -p kwavers-solver --lib --features helper-stress rc=0`**: all tests pass, including the 6 existing westervelt_spectral tests + the new helper-stress fixture.
5. 🟡 **6/6 westervelt_spectral tests remain bitwise-identical**: against the kwavers peer stream HEAD before vs after the helper extension commit. Comparison method: rerun the tests at the post-extension HEAD and diff the outputs against the slice 9 inner HEAD `949e5a39` baseline.
6. 🟡 **Slice 6b site adoption**: the rhs.rs heterogeneous Phase 2 site adopts the helper in-place (replacing the 9 verbose-form asserts + 9 `as_slice()` unwraps + 9 named slice variables with a single `with_zip_standard_layout(...)` call). Rerun AC-4 against the adopted site; passes bitwise.
7. Status field flips: ADR 0015 §head of file from `Proposed` to `Accepted` in a follow-up atlas-meta chore commit (when AC-1 through AC-6 are all ✅ + the helper-stress fixture passes across multiple `(nx, ny, nz)` grid configurations to confirm const-N monomorphization correctness).

## Sequencing (implementation increments, atomic commits)

### Atlas-meta orchestration chore commit (CURRENT TURN, COMPLETED 2026-07-09 commit `7f1e2b2`)

0. **Step 1 — atlas-meta chore commit**: `chore(atlas): Author ADR 0015 + INDEX.md row + backlog.md trigger-chore brief — Open Batch #2 Entry Point #1 helper const-generics extension on kwavers peer stream per disjoint-scope`. Bundles:
   - New file `atlas/docs/adr/0015-kwavers-batch2-entrypoint1-helper-const-generics.md` (this ADR, Status `Proposed`).
   - `atlas/docs/adr/INDEX.md` row addition between ADR 0014 + ADR 0016 (sort-order by ID).
   - `atlas/backlog.md` §In-flight claims forward-looking note recording the standing reminder + the kwavers-claim-stream trigger condition.

### Atlas-meta Step 2 design-spec chore commit (CURRENT TURN, 2026-07-09 — Step 2 cannot execute, design-spec only)

0a. **Step 2 — atlas-meta design-spec chore commit** (this turn): land the detailed Step 2 design-spec in this ADR's `### Step 2 detailed design specification` section (appended below). The implementation commit is FORBIDDEN from atlas-meta per disjoint-scope (ADR 0011 §Leg 2). The design-spec is the SSOT that the kwavers claim stream picks up once Block #5 clears.

### Kwavers peer stream chore commit (BLOCKED on Block #5 + disjoint-scope ownership)

2. **Step 2 — kwavers peer stream atomic commit** (gated on Block #5 + disjoint-scope + this ADR's design-spec): `feat(kwavers-safety): Extend with_zip_standard_layout with const-generics arity` on `D:/atlas/repos/kwavers/` `codex/kwavers-core-moirai-parallel`. Implementation per the detailed design spec below (§§equencing §Step 2 detailed design specification). Pre-flight gate must be clear (Block #5 closed); owner is kwavers claim stream per disjoint-scope.
3. **Step 3 — kwavers peer stream atomic commit**: `test(kwavers-solver): Backport slice 6b rhs.rs as helper-stress unit-test fixture (N=9)`. Adds a `helper-stress` integration test asserting const-generics helper ergonomics presence + bit-wise equivalence vs verbose-form RHS at all (i, j, k) grid points.
4. **Step 4 — kwavers peer stream atomic commit**: `refactor(kwavers-solver): Adopt with_zip_standard_layout_<const N> in slice 6b rhs.rs heterogeneous Phase 2`. Replaces the 9 verbose-form asserts + 9 `as_slice()` unwraps + 9 named slice variables with the const-generics helper call.

### Atlas-meta status-flip chore commit (FUTURE TURN)

5. **Step 5 — atlas-meta chore commit** (when AC-1 through AC-6 are all ✅): `chore(atlas): Flip ADR 0015 to Accepted after kwavers peer Batch #2 Entry Point #1 acceptance validation`. Updates ADR 0015 §head of file Status from `Proposed` to `Accepted` + records the kwavers peer inner SHA accepting the closure.

### Step 2 detailed design specification (atlas-meta SSOT for the kwavers claim stream)

**Target file (NEVER EDIT FROM ATLAS-META — for documentation only)**: `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs` (current signature at L84-130).

**Modifications to apply on the kwavers peer stream** (per thinker's pre-implementation verdict for the const-generics arity extension; replacement of the existing dynamic-slice form):

1. Add the const-generic parameter `const N: usize` to `with_zip_standard_layout`.
2. Change the `immuts` parameter type from a dynamic slice `&'imm [(&'static str, &'imm Array3<A>)]` to a const-sized array `[(&'static str, &'imm Array3<A>); N]`.
3. Replace the closure trait bound `F`'s second argument expectation from `&'s [&'s [A]]` to `[&'s [A]; N]` (HRTB `for<'s>` may be retained if caller lifetimes justify it; otherwise plain `FnOnce` with inferred `'s`).
4. Replace the internal `Vec` allocation with `std::array::from_fn`.

**Target signature and body** (verbatim — copy into the kwavers peer stream commit):

```rust
pub fn with_zip_standard_layout<'out, 'imm, A, F, R, const N: usize>(
    out_name: &'static str,
    out: &'out mut Array3<A>,
    immuts: [(&'static str, &'imm Array3<A>); N],
    f: F,
) -> R
where
    A: Copy + Send + Sync,
    F: for<'s> FnOnce(&'out mut [A], [&'s [A]; N]) -> R,
{
    assert!(
        out.is_standard_layout(),
        "{out_name} must be C-contiguous (default Array3 layout) for the Zip migration",
    );
    let out_slice = out
        .as_slice_mut()
        .expect("standard-layout asserted just above; layout matched");

    // Replace previous heap-allocated Vec mapping with const-sized stack array.
    let immut_slices = std::array::from_fn(|i| {
        let (name, arr) = immuts[i];
        assert!(
            arr.is_standard_layout(),
            "{name} must be C-contiguous (default Array3 layout) for the Zip migration",
        );
        arr.as_slice()
            .expect("standard-layout asserted just above; layout matched")
    });

    f(out_slice, immut_slices)
}
```

**Constraint surface (preserved verbatim from current helper)**:

- `A: Copy + Send + Sync` is preserved verbatim (no relaxation; required for Rayon `ParallelIterator` parallel body execution).
- The `'static` bound on `A` is consciously omitted (carries forward Nit 1 fix per code-reviewer-minimax-m3; helper never allocates or returns owned `A`).
- The verbose panic message form `"{name} must be C-contiguous (default Array3 layout) for the Zip migration"` is preserved verbatim.
- The `'out` lifetime on `out_slice` is preserved (fixed relative to helper's reborrow of `out`).

**Monomorphization analysis**:

- Each distinct `N` produces its own monomorphized helper instantiation (N=0, 1, 2, ..., 9 are the typical call-site arities across the kwavers-solver surface).
- Per-arity binary impact: ~3 KB of IR per monomorphization. With N up to 9 expected at call sites, total binary impact is bounded at ~30 KB.
- The const-N shift is a STABLE-feature in Rust since 1.51 (March 2021); no nightly channel needed.

**Backwards-compatibility strategy**:

- This is an additive shift. The helper signature changes from `&'imm [(&str, &Array3<A>)]` to `[(&str, &Array3<A>); N]`. Existing call sites that pass slice-literal immuts must be migrated to array-literal form.
- Atlas-meta does NOT mandate an automatic migration tool — the call-site migration is part of Step 4 (`refactor(kwavers-solver): Adopt with_zip_standard_layout_<const N> in slice 6b rhs.rs heterogeneous Phase 2`).
- Slice 6b's 9-immut heterogeneous Phase 2 site is the canonical backport candidate for Step 4 + the canonical unit-test fixture for Step 3.

**Acceptance criteria for Step 2** (subset of ADR 0015 §Verification plan):

- AC-2a: `cargo check -p kwavers-solver --lib --no-default-features` rc=0 post-Step-2 commit (Block #5 gate cleared; this is the prerequisite for AC-1 already).
- AC-2b: All existing call sites where the helper is used continue to compile (the helper is currently NOT adopted in any of the 9 batch-#1-migrated sites, so this is a vacuous check; if the kwavers claim stream has speculatively adopted the helper elsewhere, those calls must also be migrated to array-literal form or the commit fails to compile).
- AC-2c: `cargo build -p kwavers-safety` rc=0 (the helper SSOT crate builds standalone).

**Send + Sync propagation analysis**:

- `A: Copy + Send + Sync` unchanged.
- The closure-bound immut capture is `[&'s [A]; N]`: N references to `[A]` slices via HRTB `&'s`. The HRTB allows the helper to construct the slice-array at any lifetime `'s` shorter than or equal to the helper's invocation, satisfying Rayon's parallel body lifetime requirements.
- `Send + Sync` propagation through Rayon's `ParallelIterator` works because each closure invocation sees `r_slice: &'r_mut [A]` + `[&'s [A]; N]` where the immut borrows are shared (Rayon's `par_mut` reborrows `r_slice` separately) — disjoint-capture-rule safe under Rust 2021.

**HRTB retention vs lift**:

- The current helper uses `F: for<'s> FnOnce(&'out mut [A], &'s [&'s [A]]) -> R` (HRTB required because the local `Vec` lifetime is shorter than the helper's `'imm`).
- The const-generics design eliminates the local `Vec` allocation; the immut-slice array is built into a stack-allocated `[&'imm [A]; N]` BEFORE the closure is invoked. The HRTB `for<'s>` may therefore be lifted to a simple lifetime bound `F: FnOnce(&'out mut [A], [&'imm [A]; N]) -> R`.
- Recommendation per the thinker's verdict: KEEP the HRTB `for<'s>` form in the new signature for forward-compat with future sites that may have non-uniform caller lifetimes (e.g., sites where immuts are reborrowed from outer-scoped variables); the HRTB is a zero-cost extension (Rust 2021 monomorphizes cleanly). Net code change: signature modification is purely additive (adds const N + changes array form; HRTB stays).

**Reviewing checklist for the kwavers claim stream pre-commit**:

- Per ADR 0012 §Decision §1 atomic-boundary discipline: the const-N signature change + body rewrite is one atomic commit; intermixing with Step 3 (test fixture) or Step 4 (slice 6b adoption) violates §1.
- Per ADR 0011 §Decision §Leg 2 disjoint-scope: the implementation commit lives EXCLUSIVELY on `D:/atlas/repos/kwavers/**`; atlas-meta does NOT co-emit.
- Per ADR 0009 §Verification plan (paragraph-collapse closure gate, slices): `cargo check -p kwavers-solver --lib --no-default-features rc=0` is the primary compile-gate; the `cargo test -p kwavers-solver --lib` rc=0 progresses the layout-equivalence validation forward.
- Code-reviewer-minimax-m3 verdict required pre-commit per atlas-meta's standard discipline (the kwavers claim stream applies its own review).

**Status reaffirmation (probed 2026-07-09)**:

- Block #5 pre-flight gate: STILL BLOCKED. `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with E0308 + E0599 errors in `kwavers-transducer` (`ArrayBase` vs `Array` type mismatches + missing `matmul` methods + missing `assign` methods + arc/transducer syntax issues).
- Step 2 cannot land until Block #5 closes.
- The design-spec is the SSOT the kwavers claim stream picks up once the gate clears.

## Out of scope (explicit non-goals)

This ADR does NOT address — and the const-generics extension does NOT depend on — the following:

1. **Block #5 (kwavers-math ndarray → leto migration) resolution**: per ADR 0013 §Out of scope #5 + ADR 0014 §Out of scope #5; the kwavers peer stream continues the Phase-3/Phase-4 workstream per disjoint-scope. The const-generics extension cannot land until Block #5 closes.
2. **Atlas-meta source edits to kwavers**: per ADR 0011 §Leg 2 disjoint-scope rule, atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits. The const-generics extension implementation commits (Steps 2-4 above) live on the kwavers peer stream.
3. **Slice 7 predicate unification** (ADR 0014 §Sequencing step 2 item (b)): this is a different chore on the kwavers peer stream, owned by the same disjoint-scope rule. The const-generics extension does NOT depend on the predicate unification; both are needed for the cleanup-tag ceremony but are independent in terms of compile correctness.
4. **Entry Point #2 (conditional-read closure bodies) + Entry Point #3 (multi-mut disjoint-field sites)**: per ADR 0013 §Open Batch #2 entry points; each Entry Point has its own ADR (or its own §Sequencing within this ADR). Const-generics extension is the prerequisite for Entry Point #2 (the conditional-read branch ergonomics build on the const-N closure body destructuring) but not for Entry Point #1 alone.
5. **Helper ergonomics for N>9 immuts**: sites with N>9 immuts in closure captures are not currently in the kwavers-solver source surface; const-N=9 is the current practical limit. Future sites may extend the helper signature, but this ADR's AC validates N=6/7/8/9 specifically.
6. **`kwavers-math/Array2` migration breakage from `Array2::from_shape_vec` signature shift**: per Block #5 + ADR 0013 §Out of scope #5. The const-generics extension operates on the helper SSOT surface which is `crates/kwavers-solver/src/safety/mod.rs` and does NOT touch the kwavers-math crate; this is a different workstream owned by the kwavers peer stream.

## Standing reminder (kwavers claim stream visibility surface)

Per disjoint-scope (ADR 0011 §Leg 2), the kwavers claim stream owns Steps 2-4 above. Atlas-meta's only persistent visibility mechanism is the §In-flight claims row in `atlas/backlog.md`, which records:

- Current kwavers peer inner HEAD: `445ab9b2` (supplements slice 9 `949e5a39` with 2 post-slice-9 commits).
- Pre-flight gate state: BLOCKED on Block #5.
- Acceptance criteria: AC-1 through AC-6 per §Verification plan.
- Trigger condition for Step 5: Block #5 closes + Steps 2-4 land + AC-2/AC-3/AC-4 pass bitwise.

The standing reminder rotates through the `atlas/backlog.md` §In-flight claims row until acceptance. At Step 5, the row is retired via DELETE per ADR 0014 §Sequencing withdrawal block discipline (cross-applied by analogy).
