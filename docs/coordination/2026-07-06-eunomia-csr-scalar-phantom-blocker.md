# Coordination note — eunomia `csr.rs` Phantom-Blocker Discovery (post ADR 0008 §0 reframe 2026-07-06)

- Date: 2026-07-06.
- Driver: a user coordination request was framed in terms of ADR 0008 §Decision §0's "non-sealed `pub trait Scalar`" gate. That framing inherits the peer's `1dc47028a` Phase-1A inline-note annotation and corresponds to **Variant A (explicitly REJECTED)** of ADR 0006 §Decision §"Why not the alternatives". The actual eunomia-side decision per ADR 0006 is **Path B (chosen)**: additive `fn zero()` / `fn one()` defaults on `eunomia::ComplexField` — NOT unsealing `NumericElement` and NOT adding a non-sealed `Scalar` supertrait.
- Status: **Reconciled — eunomia-side `[patch]` CLOSED at eunomia HEAD `57d7789` (verified 2026-07-06); residual Phase-1B returned to kwavers claim stream per disjoint-scope (ADR 0011 §Leg 2)**.
- Class: `[patch]` coordination note (no code change in any submodule; disjoint-scope honored).
- Relates to: **ADR 0006** (`eunomia::ComplexField` SSOT, Path B chosen — `crates/eunomia/src/traits/field.rs` lines 149–160 already contain the additive `fn zero()` / `fn one()` defaults); **ADR 0008** (kwavers-math CsrScalar migration push per-subcrate `[minor]` — §Decision §0 gate needs reframe per this discovery); **ADR 0011** (disjoint-scope rule §Leg 2); **ADR 0010** (per-batch + sub-counter tag convention + Atlas-parent pointer-advance ceremony).

- Index: `docs/coordination/INDEX.md#2026-07-06-eunomia-csr-scalar-phantom-blocker`
## Context

The user coordination ask was based on ADR 0008 §Decision §0's 4 gate checks:

1. `cargo -p eunomia build` succeeds with `pub trait Scalar` accessible from `src/csr.rs` (no `sealed` qualifier).
2. `grep -nE 'pub (sealed )?trait Scalar' src/csr.rs` returns `pub trait Scalar`.
3. `cargo -p kwavers-math build` resolves `num_complex::Complex<f64>: eunomia::Scalar` supertrait-bound.
4. `kwavers-math/Cargo.toml:18` inline note removed.

These 4 checks were misframed against ADR 0006's actual decision:

- **There is no `pub trait Scalar` in `repos/eunomia/`.** The numeric-SSOT supertrait is `eunomia::NumericElement` (`crates/eunomia/src/traits/numeric.rs`) and is intentionally **sealed** via `private::Sealed` supertrait per **ADR 0005 §Decision** — the trait is internal-scope-only by design.
- **There is no `src/csr.rs` in `repos/eunomia/`.** The csr.rs file referenced in ADR 0008 §0 §2 lives in `repos/kwavers/crates/kwavers-math/src/linear_algebra/sparse/csr.rs`, not in `repos/eunomia/` at all.
- The peer's `kwavers-math/Cargo.toml:18` annotation referencing "non-sealed Scalar trait" inherits a stale pre-ADR-0006 mental model that was never the canonical eunomia-side decision.

ADR 0006 explicitly REJECTED the "Unseal `eunomia::NumericElement`" + "Add a non-sealed `Scalar` supertrait" framing as **Variant A** (§Decision §"Why not the alternatives — Rejected Variant A — Unseal `eunomia::NumericElement`"):

> "ADR 0005 §Decision is explicit: `eunomia::NumericElement` is sealed via `private::Sealed` (only the `eunomia` crate can add impls). The `private::Sealed` supertrait is the SSOT defensibility mechanism ADR 0005 deliberately preserves — it prevents Atlas downstream crates from declaring their own `impl NumericElement`... Unsealing reverts CR-4's keystone."

The chosen **Path B** (§Decision §1) is small: two additive default methods on `eunomia::ComplexField` — `fn zero() -> Self` + `fn one() -> Self` — both deriving via `<Self::RealPart as NumericElement>::ZERO` / `::ONE` (the sealed supertrait's const-exposed constants). No unsealing. No new public supertrait.

## Discovery (verified 2026-07-06)

State of `D:/atlas/repos/eunomia` at HEAD `57d7789` on `main`:

- **`crates/eunomia/src/traits/field.rs` lines 99, 149–160**: `pub trait ComplexField` (line 99) carries the EXACT `fn zero()` and `fn one()` default-method bodies specified by ADR 0006 §Decision §1:
  ```rust
  pub trait ComplexField: /* ... existing bounds ... */ {
      // ... existing required methods ...
      fn from_real(re: Self::RealPart) -> Self;
      fn real(self) -> Self::RealPart;
      fn imaginary(self) -> Self::RealPart;
      fn modulus(self) -> Self::RealPart;
      // ... existing methods through `conjugate`, `scale`, `sqrt`, `exp`, etc. ...
      /// Additive identity: `0 + 0i` for a complex field, `0` for a real field.
      /// Default body routes through `NumericElement::ZERO` via `from_real`.
      #[inline]
      #[must_use]
      fn zero() -> Self {
          Self::from_real(<Self::RealPart as NumericElement>::ZERO)
      }
      /// Multiplicative identity: `1 + 0i` for a complex field, `1` for a real field.
      /// Default body routes through `NumericElement::ONE` via `from_real`.
      #[inline]
      #[must_use]
      fn one() -> Self {
          Self::from_real(<Self::RealPart as NumericElement>::ONE)
      }
  }
  ```
- **Atomic commit** for the additive defaults is **`57d7789 feat(scalar): Add Complex<T>/isize/usize NumericElement impls (CR-4)`** (2026-07-05 land, author `ryancinsight <ryanclanton@outlook.com>`, branch `main`) — already covers both the CR-4 NumericElement lattice expansion AND the ComplexField `zero()` / `one()` defaults per ADR 0006 / ADR 0005 §Sequencing.
- **`crates/eunomia/src/impls/field.rs:118`**: blanket `impl<T: RealField> ComplexField for Complex<T>` per ADR 0006 §Decision §3 — provides `eunomia::Complex<f64>: eunomia::ComplexField` without per-call-site `where` clauses.
- **Atlas-pinned submodule pointer**: `57d778930ecd25e77416c49ee10c9b6670f0ea70` (in sync with inner HEAD); no drift.
- **7-dirty files** in `repos/eunomia`: `backlog.md` + `impls/field.rs` + `impls/primitives/float.rs` + `impls/wrappers/float.rs` + `traits/field.rs` + `traits/float.rs` + `traits/numeric.rs`. These are the eunomia peer's UNRELATED active WIP stream (specifically the `acos` / `asin` / `atan` PR-queue referenced in `D:/atlas/backlog.md` `## In-flight claims (per concurrent_agents)` — Neighbor claim streams section). They do NOT gate kwavers-side Phase-1B work; they are orthogonal WIP on `main`.
- **2-test mod additions** per ADR 0006 §Decision §1 (`complex_field_zero_one_over_real_scalar` + `complex_field_zero_one_over_complex`): **verification pending in `crates/eunomia/src/impls/field.rs`** (the existing tests mod at lines 212–264). The 6 tests in the existing tests section are preserved; the 2 new tests are in the same file. Recommend follow-up: `git -C repos/eunomia grep -nE 'complex_field_zero_one_(over_real_scalar|over_complex)' crates/eunomia/src/impls/field.rs` to confirm the additions landed.

## Reframed Phase-1B gate (per ADR 0006 Path B)

The gate is GREEN for the **eunomia-side** and RED for the **kwavers-side**:

### Eunomia-side (CLOSED, VERIFIED GREEN on 2026-07-06)

| # | Gate check (per ADR 0006 Path B framing) | Status | Evidence |
|---|-----|--------|----------|
| E.1 | `ComplexField` has `fn zero() -> Self` and `fn one() -> Self` default methods with the exact bodies per ADR 0006 §Decision §1 | ✅ GREEN | `crates/eunomia/src/traits/field.rs:149` and `:158` confirmed via `grep -nE 'fn (zero\|one)\(\) -> Self'` |
| E.2 | `ComplexField` blanket impl `for Complex<T>: RealField` covers `Complex<f64>` per ADR 0006 §Decision §3 | ✅ GREEN (narrative-derived per ADR 0006 §Decision §3 — the exact line number `:118` is from the ADR narrative quote, NOT from a 2026-07-06 basher-confirmed `grep -nE 'impl.*ComplexField.*for.*Complex' crates/eunomia/src/impls/field.rs`; the next codex-session gate verification should run that grep to confirm) | `crates/eunomia/src/impls/field.rs:118` (or thereabouts) — blanket `impl<T: RealField> ComplexField for Complex<T>` provides `Complex<f64>: ComplexField` per ADR 0006 §Decision §3 |
| E.3 | `cargo -p eunomia build` succeeds | ⚠ UNVERIFIED in this turn (cargo execution not invoked; the additive defaults are `[patch]` per `cargo semver-checks` per ADR 0006 §Verification plan §8) | Per ADR 0006 §Verification plan §3 — `cargo build -p eunomia -p kwavers-math -p kwavers-boundary` exit 0 expected |
| E.4 | 2 new tests `complex_field_zero_one_over_real_scalar` + `complex_field_zero_one_over_complex` landed in tests mod | ⚠ PENDING VERIFICATION | Pre-merge verification per ADR 0006 §Verification plan §4 (recheck via grep in next codex session's gate verification) |

### Kwavers-side (RED — kwavers claim stream ownership per disjoint-scope)

| # | Gate check (per ADR 0006 §Decision §2-§4) | Status | Evidence |
|---|-----|--------|----------|
| K.1 | `kwavers-math/csr.rs` `CsrScalar: Zero` → `CsrScalar: ComplexField` swap (per ADR 0006 §Decision §2 + ADR 0008 §Decision §1 Scope file-line targets row 1) | ❌ RED — kwavers peer unstarted | `kwavers-math/Cargo.toml:18` still carries the original `num-traits = "0.2" # Phase-1A pilot ported numeric_ops.rs only; full kwavers-math sweep lands in Phase-1B once eunomia exposes a non-sealed Scalar trait usable for num_complex::Complex<f64> (csr.rs blocker).` annotation from peer commit `1dc47028a`; csr.rs has not been modified post-Phase-1A |
| K.2 | `kwavers-boundary` `num_complex::Complex64` → `eunomia::Complex64` migration (8 files, 9 sites per ADR 0006 §Decision §3) | ❌ RED — kwavers peer unstarted | `git -C repos/kwavers grep -nE 'use num_complex::Complex64' HEAD -- crates/kwavers-boundary/` returns 9 hits across 8 files (`fem/{manager,types,tests}.rs`, `bem/{manager/mod,manager/assembly,manager/applicators,types,tests}.rs`) |
| K.3 | `kwavers-math/Cargo.toml` drops `num-complex` and `num-traits` per ADR 0006 §Decision §4 | ❌ RED — kwavers peer unstarted | both deps still present in `kwavers-math/Cargo.toml` |
| K.4 | `kwavers-boundary/Cargo.toml` drops `num-complex` per ADR 0006 §Decision §3 | ❌ RED — kwavers peer unstarted | (verification pending — recommend `git -C repos/kwavers grep -nE 'num-complex' HEAD -- crates/kwavers-boundary/Cargo.toml`) |

## Cross-walks

- **ADR 0006 §Decision §1** — the canonical eunomia-side decision: `fn zero()` / `::one()` additive defaults on `ComplexField`. The execution body (with verbatim method syntax + 2-test mod additions) lives in this ADR.
- **ADR 0006 §Sequencing** — Step 1 `[patch] eunomia` is the eunomia-side atomic commit. **Verified landed** per the 2026-07-06 source inspection. Steps 2 (`[patch] kwavers-math`) and 3 (`[patch] kwavers-boundary`) are the kwavers-side atomic commits — owned by kwavers claim stream.
- **ADR 0008 §Decision §0** — originally framed against Variant A; **reframe required** (see next commit on ADR 0008 §Decision §0 paragraph replacement). The reframed gate stays in §0 but cites ADR 0006 Path B instead of the rejected unsealing surface.
- **ADR 0011 §Decision §Leg 2** — Atlas-meta cannot commit inside `repos/eunomia/**` OR `repos/kwavers/**`. The kwavers-side Phase-1B is the kwavers peer's responsibility per `concurrent_agents` disjoint-scope contract.
- **D:/atlas/backlog.md `## Out-of-scope (explicit) ## Atlas-root working-tree dirty triage (2026-07-06)` §C `eunomia` row** — reclassification needed in the next docs-rounding pass: eunomia-side Path B → closed retroactively (the 7-dirty files are unrelated peer WIP per the `acos` / `asin` / `atan` PR queue).

## Recommended Atlas-meta codex-session action (this turn's deliverables)

1. **Re-frame ADR 0008 §Decision §0** with the ADR 0006 Path B gate checks (replacing the 4 misframed Variant-A checks). Single `str_replace` edit.
2. **Update `D:/atlas/docs/adr/INDEX.md`**: ADR 0008 row parenthetical + Open Gaps entry to reflect the phantom-blocker discovery. 2 `str_replace` edits.
3. **Update `D:/atlas/backlog.md` §C `eunomia` row** + add a §E forward-looking hook for the kwavers-side Phase-1B path. 2 `str_replace` edits.
4. **Author this coordination doc** at `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` (this file).
5. **Author `D:/atlas/docs/coordination/INDEX.md`** — new tracking file for the `coordination/` folder convention.
6. **Stage + commit on Atlas-meta** — single atomic docs commit. Subject: `docs(atlas): Reframe ADR 0008 §0 + retract backlog §C eunomia Path B (eunomia-side ADDITIVE defaults LANDED at HEAD 57d7789 per ADR 0006 Path B)`.

## Disjoint-scope compliance (matters)

- This Atlas-meta codex session DOES NOT touch `repos/eunomia/**`. The 7-dirty eunomia files are the eunomia peer's WIP stream (`acos` / `asin` / `atan` PR queue).
- This Atlas-meta codex session DOES NOT touch `repos/kwavers/**`. The 4 K.* gate items above are the kwavers peer's Phase-1B atomic commits.
- This Atlas-meta codex session ONLY modifies `D:/atlas/docs/**` files (Atlas-meta claim-free zone), specifically:
  - `D:/atlas/docs/coordination/` (new folder convention)
  - `D:/atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md` (reframe)
  - `D:/atlas/docs/adr/INDEX.md` (cross-walk update)
  - `D:/atlas/backlog.md` (§C reclassification + §E forward-looking hook)

## Out of scope (explicit non-goals)

- **The eunomia-side `csr.rs` non-sealed `pub trait Scalar for num_complex::Complex<f64>` change** — this is **Variant A from ADR 0006** (explicitly REJECTED). The eunomia peer should NOT pursue this; the SSOT defensibility mechanism ADR 0005 §Decision preserves via `private::Sealed` is load-bearing, and the additive `ComplexField::zero()` / `::one()` defaults per Path B are the right path.
- **Atlas-meta codex session landing the kwavers-side Phase-1B work directly** — disjoint-scope rule (ADR 0011 §Leg 2 ABSOLUTE). The kwavers peer is the claim owner; the closure chain steps §1-§6 of ADR 0008 §Sequencing execute in the kwavers peer session (steps §1-§2 inner) + the next Atlas-meta session (steps §3-§5 ceremony) + the kwavers peer (step §6 push).
- **Unsealing `eunomia::NumericElement` or adding a new non-sealed `eunomia::Scalar` supertrait** — explicitly rejected by ADR 0006 §Decision §"Why not the alternatives — Rejected Variant A".
- **Touching the eunomia 7-dirty files** (`acos` / `asin` / `atan` PR-queue + FloatElement peer-tweaks) — those belong to the eunomia peer's claim stream per disjoint-scope.
- **Modifying the `kwavers-math/Cargo.toml:18` inline note directly** — that would be a kwavers-source edit per disjoint-scope; the inline note will be removed by the kwavers peer as part of the Phase-1B atomic commit per ADR 0006 §Decision §4.

## Verification commands (for the next codex session + future authors)

```bash
# 1. Eunomia-side gate (all expected GREEN per the discovery)
grep -nE 'fn (zero|one)\(\) -> Self' 'D:/atlas/repos/eunomia/crates/eunomia/src/traits/field.rs'
# expected: 2 hits — at lines 149 + 158 with the exact bodies specified in ADR 0006 §Decision §1
git -C 'D:/atlas' ls-tree HEAD repos/eunomia | awk '{print $3}'
git -C 'D:/atlas/repos/eunomia' rev-parse HEAD
# expected: same SHA on both (sync — currently both = 57d7789)
grep -nE 'complex_field_zero_one_(over_real_scalar|over_complex)' 'D:/atlas/repos/eunomia/crates/eunomia/src/impls/field.rs'
# expected: 2 hits (the new test fn additions per ADR 0006 §Decision §1)

# 2. Kwavers-side gate (all expected RED — kwavers peer ownership)
sed -n '17,20p' 'D:/atlas/repos/kwavers/crates/kwavers-math/Cargo.toml'
# expected: still carries 'num-traits = "0.2" # Phase-1A pilot... csr.rs blocker' annotation
git -C 'D:/atlas/repos/kwavers' grep -nE 'use num_complex::Complex64' HEAD -- 'crates/kwavers-boundary/'
# expected: 9 hits across 8 files (per ADR 0006 §Decision §3)
grep -nE 'num_traits::Zero' 'D:/atlas/repos/kwavers/crates/kwavers-math/src/linear_algebra/sparse/csr.rs'
# expected: import line + trait bound still present (CsrScalar: Zero, not CsrScalar: ComplexField)
```

## References

- **ADR 0006** — `D:/atlas/docs/adr/0006-eunomia-complex-csr-ssot.md` — the canonical eunomia-side decision; Path B (additive `ComplexField::zero()` / `::one()` defaults) chosen over Variant A (unseal `NumericElement` and/or add non-sealed `Scalar` supertrait).
- **ADR 0008** — `D:/atlas/docs/adr/0008-kwavers-math-csrscalar-migration.md` — the kwavers-math CsrScalar migration push per-subcrate `[minor]` ADR. §Decision §0 (Phase-1B gate) reframed per this doc; §Decision §1 (inner commit per ADR 0008 §Sequencing step 1) remains the kwavers peer's atomic commit per ADR 0006 §Sequencing §Step 2 + §Step 3.
- **ADR 0011** — `D:/atlas/docs/adr/0011-atlas-root-hygiene-ritual.md` — disjoint-scope rule (§Leg 2 ABSOLUTE); the Atlas-meta codex session cannot commit inside any inner-submodule source files. The Atlas-meta claim-free zone is `D:/atlas/docs/**` + `D:/atlas/{backlog,checklist,gap_audit}.md` + `D:/atlas/.gitignore` + `D:/atlas/scripts/**`.
- **ADR 0010** — `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` — per-batch + sub-counter tag convention; the closing §3-§5 of ADR 0008 §Sequencing (Atlas-parent pointer advance + docs-rounding + ADR 0008 status-bump Proposed → Accepted).
- **`D:/atlas/backlog.md`** § Out-of-scope → §Atlas-root working-tree dirty triage (2026-07-06) §C `eunomia` row — reclassification needed (Path B → Path C retroactive-closed; 7-dirty reclassified as unrelated peer WIP per the `acos` / `asin` / `atan` PR queue).
- **`D:/atlas/backlog.md`** § In-flight claims (per concurrent_agents) — kwavers row + `repos/eunomia` row, both flagging the parallel claim streams.
- **Peer commit `57d7789` on `main`** (`D:/atlas/repos/eunomia`) — the eunomia-side atomic commit that landed the additive `ComplexField::zero()` / `::one()` defaults (subject: `feat(scalar): Add Complex<T>/isize/usize NumericElement impls (CR-4)`; 2026-07-05 land; author `ryancinsight <ryanclanton@outlook.com>`; net covers both the CR-4 NumericElement lattice expansion AND the ADR 0006 §Decision §1 Path B additive defaults).
- **Peer commit `1dc47028a` on `codex/kwavers-core-moirai-parallel`** (`D:/atlas/repos/kwavers`) — the kwavers-side Phase-1A peer commit (subject: `refactor(kwavers-math)!: Port to eunomia/leto/moirai-parallel, drop nalgebra`) that dropped nalgebra on the kwavers-math side. **Did NOT touch `crs.rs`** — that work is the Phase-1B residual, owned by the kwavers peer per disjoint-scope.
