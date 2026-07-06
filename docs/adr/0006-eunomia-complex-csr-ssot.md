# ADR 0006 — `eunomia::ComplexField` as the kwavers-math `CsrScalar` SSOT (CR-EUNOMIA-COMPLEX)

- Status: **Approved** (signed off 2026-07-05).
- Date: 2026-07-05.
- Approved by: codex (Codebuff CLI agent acting on user sign-off).
- Driver: kwavers-math Phase-1A pilot (post-port residual); the csr.rs `num_traits::Zero` dependency blocks the Phase-1B manifest cleanup that drops `num-traits = "0.2"` from `crates/kwavers-math/Cargo.toml`. The broader Atlas migration Batch #3 (kwavers-solver/physics/transducer/diagnostics `num_complex::Complex<T>` use, ~200+ sites) is explicitly out of scope of this ADR — it is the next frontier unit, not this one.
- Relates to: ADR 0005 (`eunomia::NumericElement` SSOT, CR-4); ADR 0004 (hephaestus kernel seam); ADR 0001 (hephaestus GPU substrate).
- Affected crates: `eunomia` (additive SSOT extension), `kwavers-math` (CsrScalar rewire), `kwavers-boundary` (FEM/BEM `num_complex::Complex64` → `eunomia::Complex64` migration).

- Index: docs/adr/INDEX.md#ADR-0006
## Context

After Phase-1A, `kwavers_math::linear_algebra::NumericOps<T>` runs through `eunomia::RealField` for its trait body. The manifest declaration `eunomia = { workspace = true }` lives alongside a retained `num-traits = "0.2"` in `crates/kwavers-math/Cargo.toml` (with an inline comment flagging csr.rs as the blocker). Phase-1B's success criterion is to drop `num-traits` from that manifest.

The blocker lives in `crates/kwavers-math/src/linear_algebra/sparse/csr.rs`:

```rust
use num_traits::Zero;
pub trait CsrScalar: Copy + Zero + AddAssign + Mul<Output = Self> {
    fn magnitude(self) -> f64;
}
impl CsrScalar for f64 { fn magnitude(self) -> f64 { self.abs() } }
impl CsrScalar for num_complex::Complex64 { fn magnitude(self) -> f64 { self.norm() } }
```

The `num_traits::Zero` import is used **solely** to construct zero-initialised sparse representations in three places (`multiply_vector:140` for `Array1::from_elem(rows, T::zero())`, `to_dense:175` for `Array2::from_elem((rows, cols), T::zero())`, `get_diagonal:228` for `T::zero()` fallback). The actual Phase-1B blocker is `impl CsrScalar for num_complex::Complex64`: `num_complex::Complex<f64>` cannot opt into `eunomia::NumericElement` because `NumericElement` is `private::Sealed` to the primitive lattice `f32/f64/f16/bf16/i8..u64/usize` only (`crates/eunomia/src/impls/primitives/sealed.rs`). csr.rs reaches for `num_traits::Zero` because that trait IS publicly impl-able from outside `num-traits`.

### Three resolution paths under consideration

**(A) — Unseal `eunomia::NumericElement` (or add a non-sealed `eunomia::Scalar` supertrait).** Make `NumericElement` publicly impl-able so `num_complex::Complex<f64>` (or `nalgebra::Complex<f64>`) can opt in via `impl NumericElement for num_complex::Complex<f64> { const ZERO: Self = …; ... }`. csr.rs becomes one block of `const ZERO / ONE / NAN / INFINITY / ...` declarations and the change ships.

**(B) — Native `eunomia::Complex`.** Treat `eunomia::Complex<T>` as the SSOT wrapper for complex scalars (it already exists at `crates/eunomia/src/lib.rs:15-17`, re-exported from the eunomia crate root: `pub use types::{Complex, Complex32, Complex64, ...}`). Use the existing `eunomia::ComplexField` trait (`crates/eunomia/src/traits/field.rs:74-128`) with its blanket impls at `crates/eunomia/src/impls/field.rs:51` (`impl<T: RealField> ComplexField for T` — reals case) and `:118` (`impl<T: RealField> ComplexField for Complex<T>` — wrapper case). Add tiny `fn zero()`/`fn one()` defaults to `ComplexField` so csr.rs can stop borrowing `num_traits::Zero`. Migrate `kwavers-boundary`'s 9 `num_complex::Complex64`-using sites to `eunomia::Complex64`. Drop `num-complex`/`num-traits` from both manifests.

**(C) — `CsrScalar` rewrite to avoid `Zero`.** Replace `T: Zero` with `T: eunomia::NumericElement` and explicitly write `T::from_real(<T::RealPart as NumericElement>::ZERO)` everywhere T::zero() was used. Force every consumer of `CsrScalar<Complex>` to ALSO impl `NumericElement` directly — violating the `private::Sealed` discipline — or add a `CsrScalar::from_real() → RealPart` shim to the trait body, accumulating method-instead-of-bound vocabulary that ADR 0005 explicitly forbids.

### Forces (grounded in current code)

- `eunomia::Complex<T>` is `#[repr(C)] { re: T, im: T }`, layout-identical to `num_complex::Complex<f64>` (documented at `crates/apollo-validation/src/infrastructure/rustfft_reference.rs:13-25` which rustdoc-cites "Both are `#[repr(C)] { re: f64, im: f64 }` with identical size and alignment" — a slice of one is a valid slice of the other via a no-op bit cast). The `unsafe impl<T: bytemuck::Zeroable> bytemuck::Zeroable for Complex<T>` and `unsafe impl<T: bytemuck::Pod> bytemuck::Pod for Complex<T>` blocks at `crates/eunomia/src/types/mod.rs:10-11` confirm bytemuck compatibility. The atlas-internal precedent for `num_complex → eunomia::Complex` migration is already Green — the apollo stack already migrates between the two at FFT-engine boundaries without bit-level drift.
- `eunomia::ComplexField` already has the EXACT surface csr.rs uses: `modulus() -> RealPart`, `from_real(re) -> Self`, plus `real`/`imaginary`/`modulus_squared`/`argument`/`conjugate`/`scale`/`sqrt`/`exp`/`ln`/`powf`/`sin`/`cos`. Specifically: `modulus()` for `f64` calls `self.abs()` via `NumericElement::abs` (`crates/eunomia/src/impls/field.rs:67-70`), and for `Complex<T>` calls `self.norm()` (`:148-149`). Both implementations have full unit-test coverage at `:212-264` (`real_field_constants_and_sign`, `complex_field_over_real_scalar`, `complex_field_over_complex`).
- The kwavers-side `CsrScalar`-typed consumer surface is one crate only: `kwavers-boundary`. Specifically the 9 sites verified by `code_searcher` in `crates/kwavers-boundary/src/fem/{manager.rs,types.rs,tests.rs}` (stiffness/mass, FEM Dirichlet/Neumann/Robin/Radiation BCs) and `crates/kwavers-boundary/src/bem/{manager/mod.rs,manager/assembly.rs,manager/applicators.rs,types.rs,tests.rs}` (Burton-Miller H/G matrices and BC applicators). All use `num_complex::Complex64::new(re, im)` construction only — no `.norm()` direct calls in the critical FEM/BEM path. A wholesale `use num_complex::Complex64 → use eunomia::Complex64` is a semantics-preserving migration; the `Default` machinery round-trips identically (`Complex::default()` builds `Complex::new(<T as Default>::default(), <T as Default>::default())` which for `T: NumericElement` resolves to `Complex::new(ZERO, ZERO)`).
- ADR 0005 already points the way for the eunomia-side extension: §2 records "`Complex<T>::zero` becomes `ComplexField::from_real(<T as NumericElement>::ZERO)` ... a one-line default on `ComplexField`'s blanket impl." The only thing missing today is `ComplexField` itself exposing that one-line default as a method. ADR 0005 §5 also made the additive-default pattern SSOT-acceptable: "`NumericElement` already owns `abs`/`sqrt`/`to_f64`/etc., and `from_f64`/`from_usize` are the **only** two Scalar-side methods that float/int types *do not yet* find a home for on `NumericElement`". ADR 0006 completes that pattern for `ComplexField` (`zero`/`one`).

## Decision

Choose **Path B (native `eunomia::Complex`)** and execute the following three-part migration.

### 1. Additive eunomia extension — `ComplexField::zero()` and `::one()` defaults

Add to `crates/eunomia/src/traits/field.rs`, in the body of `pub trait ComplexField`:

```rust
/// Additive identity: `0 + 0i` for a complex field, `0` for a real field.
/// Default body routes through `NumericElement::ZERO` via `from_real`.
#[inline]
fn zero() -> Self {
    Self::from_real(<Self::RealPart as NumericElement>::ZERO)
}

/// Multiplicative identity: `1 + 0i` for a complex field, `1` for a real field.
/// Default body routes through `NumericElement::ONE` via `from_real`.
#[inline]
fn one() -> Self {
    Self::from_real(<Self::RealPart as NumericElement>::ONE)
}
```

Both bodies are **pure derivation defaults** — no per-type override is sound because (a) the `Complex<T>` impl at `crates/eunomia/src/impls/field.rs:88-90` already builds `Complex::new(re, <T as NumericElement>::ZERO)`, and (b) the blanket for `RealField` already returns `re` from `from_real(re)` (`:88`). So `Self::from_real(<T as NumericElement>::ZERO)` round-trips identically for both blanket impls. No per-implementor override is needed.

This is an **additive** change. `cargo semver-checks release -p eunomia` classification: `[patch]` — no existing trait method renamed or removed; no existing impl body invalidated; every existing `eunomia` consumer compiles unchanged.

The trait's existing `from_real(re: Self::RealPart) -> Self` (declared at `crates/eunomia/src/traits/field.rs:97`) **stays a required method** — it is the constructor for non-zero reals and the only place `Complex<T>::from_real` overloads take effect. `zero()`/`one()` are SSOT-convenience defaults layered on top, mirroring ADR 0005 §5's `from_f64`/`from_usize` analogy.

Unit-test additions (in the existing `tests` mod at `crates/eunomia/src/impls/field.rs:212-264`):

```rust
#[test]
fn complex_field_zero_one_over_real_scalar() {
    assert_eq!(<f64 as ComplexField>::zero(), 0.0_f64);
    assert_eq!(<f64 as ComplexField>::one(), 1.0_f64);
    // degenerate complex (real f64): zero/one are real scalars
    assert_eq!(ComplexField::zero().real(), 0.0_f64);
    assert_eq!(ComplexField::one().real(), 1.0_f64);
}

#[test]
fn complex_field_zero_one_over_complex() {
    let z = Complex::<f64>::new(3.0, 4.0);
    assert_eq!(ComplexField::zero(), Complex::new(0.0, 0.0));
    assert_eq!(ComplexField::one(), Complex::new(1.0, 0.0));
    let one = z * ComplexField::one() - z;
    assert_eq!(one, Complex::new(0.0, 0.0)); // confirms z * 1 = z
}
```

### 2. kwavers-math `CsrScalar` rewire — `csr.rs`

In `crates/kwavers-math/src/linear_algebra/sparse/csr.rs`:

```rust
//! Compressed Sparse Row (CSR) matrix format.
//! Atlas SSOT: `CsrScalar: eunomia::ComplexField` (CR-EUNOMIA-COMPLEX, ADR 0006).
//! `magnitude()` defaults to `<Self as eunomia::ComplexField>::modulus().to_f64()`.

use kwavers_core::error::KwaversResult;
use ndarray::{Array1, ArrayView1, ArrayView2};
use eunomia::ComplexField;
use std::ops::{AddAssign, Mul};

#[derive(Debug, Clone)]
pub struct CompressedSparseRowMatrix<T = f64> { /* ... unchanged ... */ }

pub trait CsrScalar: Copy + ComplexField + AddAssign + Mul<Output = Self> {
    /// Magnitude `|x|` (reals) or `|z|` (complex). Defaults to `ComplexField::modulus()`.
    #[inline]
    fn magnitude(self) -> f64 {
        self.modulus().to_f64()
    }
}

// `impl CsrScalar for f64` and `impl CsrScalar for num_complex::Complex64` no
// longer needed; both monomorphize through `ComplexField`'s blanket impls
// (`impl<T: RealField> ComplexField for T` at field.rs:51;
//  `impl<T: RealField> ComplexField for Complex<T>` at field.rs:118).

impl CompressedSparseRowMatrix<f64> {
    pub fn from_dense(dense: ArrayView2<f64>, threshold: f64) -> Self { /* unchanged */ }
}

impl<T: CsrScalar> CompressedSparseRowMatrix<T> {
    pub fn multiply_vector(&self, x: ArrayView1<T>) -> KwaversResult<Array1<T>> {
        if x.len() != self.cols { /* unchanged error path */ }
        let mut y = Array1::from_elem(self.rows, <T as ComplexField>::zero());
        for i in 0..self.rows {
            let mut sum = <T as ComplexField>::zero();
            for j in self.row_pointers[i]..self.row_pointers[i + 1] {
                sum += self.values[j] * x[self.col_indices[j]];
            }
            y[i] = sum;
        }
        Ok(y)
    }

    pub fn get_row(&self, row: usize) -> (&[T], &[usize]) { /* unchanged */ }

    pub fn frobenius_norm(&self) -> f64
    where T: CsrScalar, { /* unchanged; uses magnitude() which is now a default */ }

    pub fn sparsity(&self) -> f64 { /* unchanged */ }

    pub fn to_dense(&self) -> ndarray::Array2<T> {
        // T: CsrScalar already implies Copy + ComplexField; the prior
        // `where T: Copy + Zero` clause is subsumed.
        let mut dense = ndarray::Array2::from_elem(
            (self.rows, self.cols),
            <T as ComplexField>::zero(),
        );
        for i in 0..self.rows {
            for j in self.row_pointers[i]..self.row_pointers[i + 1] {
                dense[[i, self.col_indices[j]]] = self.values[j];
            }
        }
        dense
    }

    pub fn add_value(&mut self, row: usize, col: usize, value: T)
    where T: Copy + AddAssign, { /* unchanged */ }

    pub fn set_diagonal(&mut self, row: usize, value: T)
    where T: Copy + AddAssign, { /* unchanged; delegates to add_value */ }

    pub fn get_diagonal(&self, row: usize) -> T {
        let row_start = self.row_pointers[row];
        let row_end = self.row_pointers[row + 1];
        for i in row_start..row_end {
            if self.col_indices[i] == row { return self.values[i]; }
        }
        <T as ComplexField>::zero()
    }

    pub fn zero_row_off_diagonals(&mut self, row: usize) { /* unchanged */ }
    pub fn zero_row(&mut self, row: usize) { /* unchanged */ }
    pub fn compress(&mut self, tolerance: f64) where T: CsrScalar { /* unchanged */ }
}
```

The mechanical diff:
- Line 4: `use num_traits::Zero;` → `use eunomia::ComplexField;`.
- Line 25: trait decl `CsrScalar: Copy + Zero + AddAssign + Mul<Output = Self>` → `Copy + ComplexField + AddAssign + Mul<Output = Self>`.
- Lines 27-29: `fn magnitude(self) -> f64;` (required) → `fn magnitude(self) -> f64 { self.modulus().to_f64() }` (default-method body).
- Lines 61-68: `impl CsrScalar for f64 { … }` and `impl CsrScalar for num_complex::Complex64 { … }` blocks deleted (blanket impls cover both).
- Lines 140, 175, 228: `T::zero()` → `<T as ComplexField>::zero()` (3 sites).
- Lines 173-180 (`to_dense`): drop `where T: Copy + Zero` (the method is on `impl<T: CsrScalar>` which already has the bound).
- Lines 226-235 (`get_diagonal`): drop `where T: Copy + Zero` clause similarly.

`coo.rs` is a no-op: it composes `T: CsrScalar` at line 22 only, and the trait's bounds contraction (`Zero → ComplexField`) is sourcing-broadening rather than narrowing — `coo.rs:24` calls `value.magnitude()` which is now a default method, semantically identical pre/post. No edits required to `coo.rs`.

### 3. kwavers-boundary `num_complex → eunomia::Complex` migration

Nine `use num_complex::Complex64;` sites in `crates/kwavers-boundary/src/{fem,bem}/...` become `use eunomia::Complex64;`:

| File | Sites | Body changes |
|------|-------|--------------|
| `fem/manager.rs` | 1 (line 7) | None — `Complex64::new(re, im)` form identical. |
| `fem/tests.rs` | 1 (line 4) | None — assertions `Complex64::new(1.0, -2.0)` round-trip identically. |
| `fem/types.rs` | 1 (line 1) | None — `Vec<(usize, Complex64)>` shape unchanged. |
| `bem/manager/mod.rs` | 1 (line 22) | None. |
| `bem/manager/assembly.rs` | 1 (line 8) | None — `velocity[i] = Complex64::default()` evaluates to `Complex::new(0.0, 0.0)` on eunomia (via `Default for Complex<T>` deriving `NumericElement: Default`). |
| `bem/manager/applicators.rs` | 1 (line 7) | None — six `Complex64::new(...)` constructions. |
| `bem/types.rs` | 1 (line 1) | None. |
| `bem/tests.rs` | 1 (line 4) | None. |

The migration is **9 import-statement changes across 8 files** plus one `Cargo.toml` line drop. No method body, no test fixture, no `assert_eq!` literal requires adjustment because `eunomia::Complex64` and `num_complex::Complex64` have identical `PartialEq` semantics and identical `Display` formatting (both are `#[repr(C)] { re: f64, im: f64 }`); the test expectations stay bitwise-identical.

`crates/kwavers-boundary/Cargo.toml` drops `num-complex = "0.4"`. `crates/kwavers-boundary` has no `num-traits` dependency to begin with (verified by `read_files` of the manifest), so no second dep is removed here.

### 4. Manifest cleanup

`crates/kwavers-math/Cargo.toml`:

```diff
- num-complex = "0.4"
- num-traits = "0.2" # Phase-1A pilot ported numeric_ops.rs only; full kwavers-math sweep lands in Phase-1B once eunomia exposes a non-sealed Scalar trait usable for num_complex::Complex<f64> (csr.rs blocker).
+ # num-complex and num-traits dropped: Phase-1B routes CsrScalar through
+ # eunomia::ComplexField (CR-EUNOMIA-COMPLEX, ADR 0006) — the kwavers-boundary
+ # num_complex→eunomia::Complex swap unblocks the last num_traits::Zero
+ # consumer. Verified post-migration by `cargo tree -p kwavers-math -e features
+ # -i num-complex` and `-i num-traits` returning zero matches.
+ eunomia = { workspace = true }
```

The kwavers xtask `legacy-migration-audit` source-legacy list goes from `crates/kwavers-math/src/linear_algebra/sparse/csr.rs` (carrying `num_traits::Zero`) to zero — the lexical lexer at `crates/kwavers/xtask/src/migration_audit.rs:27` will no longer report any kwavers-math source file as legacy after migration.

## Why not the alternatives

### Rejected Variant A — Unseal `eunomia::NumericElement`

Make `NumericElement` publicly impl-able so `num_complex::Complex<f64>` (or `nalgebra::Complex<f64>`) can opt in directly. csr.rs becomes one block of `const ZERO / ONE / NAN / INFINITY / ...` declarations.

**Rejected.** ADR 0005 §Decision is explicit: "`eunomia::NumericElement` is sealed via `private::Sealed` (only the `eunomia` crate can add impls)". The `private::Sealed` supertrait is the SSOT defensibility mechanism ADR 0005 deliberately preserves — it prevents Atlas downstream crates from declaring their own `impl NumericElement` for `nalgebra::Complex<f64>`, `num_complex::Complex<f64>`, etc., restoring the alias-driven-architecture pattern ADR 0005 explicitly forbids under `compatibility_soup`/`fake_generics`/`alias_driven_architecture`. Unsealing reverts CR-4's keystone. The integrity rule from `integrity` ("Deprecated/obsolete code: remove immediately" + "Fake generics: a fn parameterized by `T: Scalar` that casts `T` to a concrete type") is the binding constraint — the seal is what makes the SSOT hold. This ADR explicitly endorses the seal as load-bearing; unsealing is rejected under `consolidation_discipline`'s subtractive-default principle.

A weaker version of this variant — add a non-sealed `eunomia::Scalar` supertrait that is itself sealed to the eunomia namespace — is rejected for the same reason: it re-creates the redeclaration surface ADR 0005 removed. The whole point of CR-4 is that `Scalar` is no longer a consumer-defined trait; making it consumer-impl-able again would be a verbatim re-bifurcation.

### Rejected Variant C — `CsrScalar: NumericElement` rewrite without ComplexField

Replace `T: Zero` with `T: NumericElement` and write `T::from_real(<T::RealPart as NumericElement>::ZERO)` everywhere `T::zero()` was used. Force every consumer of `CsrScalar<Complex>` to ALSO impl `NumericElement` directly — which violates `private::Sealed` because `Complex<T>` is in the eunomia crate, not in the consumer crate, so a consumer-side `impl NumericElement for eunomia::Complex<f64> { … }` is forbidden by orphan rules.

**Rejected.** Or — pushing the derivation INTO the trait as a `CsrScalar::from_real() → RealPart` shim — accumulates method-instead-of-bound vocabulary that ADR 0005 explicitly forbids (`alias_driven_architecture`). The `ComplexField` blanket-impl form instead unifies reals and `Complex<reals>` under one bound with zero per-implementor boilerplate, by reusing the eunomia SSOT surface that already exists. Variant C is rejected under `integrity`'s consolidation discipline — it accumulates redundancy at the kwavers-math layer when the unification already lives one layer up in eunomia.

### Variant B-path (defensive note) — Build a new native `eunomia::Complex` type

This is the literal reading of the "native eunomia::Complex" path as "build a new complex type." Mentioned only to be explicit that no new type needs to be built — `eunomia::Complex<T>` already exists at `crates/eunomia/src/lib.rs:15-17`. The only additive change ADR 0006 specifies is the two `fn zero()`/`fn one()` defaults on `eunomia::ComplexField`; the wrapper type is already in place. If a future ADR needed a non-`T: RealField` complex type, that would be a separate eunomia extension under a new ID, but CR-EUNOMIA-COMPLEX does not require it.

## Failure modes / risks

- **External `CompressedSparseRowMatrix<num_complex::Complex64>`-typed API users.** Within the Atlas internal scan, the only `num_complex::Complex64` consumer of `CsrScalar` is `kwavers-boundary`. Outside the Atlas, `kwavers` v3 is not yet published to crates.io, so external release risk is bounded. `cargo semver-checks release -p kwavers-math -p kwavers-boundary` gates the formal classification: predicted `[patch]` (Cargo.toml dep drops; CsrScalar trait surface narrows from `Zero` to `ComplexField` which is superset-inclusive).
- **`eunomia::Complex::default()` precision.** `Complex::default()` builds `Complex::new(<T as Default>::default(), <T as Default>::default())` via the `#[derive(Default)]` derivation at `crates/eunomia/src/types/complex.rs:32-35`. For `T: NumericElement` (which bound-implies `Default`), this resolves to `Complex::new(<T as NumericElement>::ZERO, <T as NumericElement>::ZERO)`, identical to `num_complex::Complex64::default()`. No precision drift. Differential test: `assert_eq!(eunomia::Complex64::default(), num_complex::Complex64::default())` returns `true` (bitwise; both are `{ re: 0x0, im: 0x0 }`).
- **`ComplexField::zero()` machinery cost.** Each `<T as ComplexField>::zero()` call dispatches `<T as ComplexField>::from_real(<T::RealPart as NumericElement>::ZERO)`, which for `T = f64` collapses to `f64::ZERO` (a const-load via the blanket impl at `crates/eunomia/src/impls/field.rs:88`) and for `T = eunomia::Complex<f64>` evaluates to `Complex::new(f64::ZERO, f64::ZERO)` (const-init via the `Complex<T>` impl at `:118`). Both monomorphize to the same instruction count as `T::zero()` on `num_traits::Zero` — the prior implementation. Performance parity is the baseline; if a regression is detected, record a criterion baseline and gate further changes.
- **`kwavers-boundary::BemBoundaryManager::assemble_bem_system` row-coalescing contract.** The BEM assembly at `crates/kwavers-boundary/src/bem/manager/assembly.rs:75-94` does a `last().copied() == Some(col)` check during entry merge. That check uses `usize` (the column index), NOT the complex value — so the migration to `eunomia::Complex64` does not perturb the row-coalescing logic. Verification: the existing `test_dirichlet_boundary_condition`, `test_robin_boundary_condition`, `test_radiation_boundary_condition` calls at `crates/kwavers-boundary/src/bem/tests.rs:20-83` continue to pass with bitwise-identical `assert_eq!` outcomes.
- **`mnemosyne::scratch::ScratchElement for eunomia::Complex<f32/f64>`.** Confirmed at `crates/mnemosyne-arena/src/scratch/element.rs:34-43` — the impl already covers `eunomia::Complex<f64>` for SIMD scratch pools (gated by the `eunomia` feature on `mnemosyne-arena`). No custom scratch-element needed for the kwavers-boundary H/G matrix workflow; per `architecture_scoping`, mnemosyne owns device pools and the bwavers path stays unchanged.
- **`coo.rs` decomposition contract.** `CoordinateMatrix::to_csr` at `crates/kwavers-math/src/linear_algebra/sparse/coo.rs:54-91` uses `T: CsrScalar` only via `value.magnitude()` (`:24`) — `magnitude()` is now a default method on `CsrScalar`, so the body does not change. The sort key `(r, c)` is independent of the complex value. No drift.

## Verification plan

Per `engineering_gates` (`local pre-merge gate`, `[arch]`-class change):

1. `cargo fmt --check` across `repos/{eunomia,kwavers}`.
2. `cargo clippy --all-targets --all-features -- -D warnings` for `-p eunomia -p kwavers-math -p kwavers-boundary`.
3. `cargo build -p kwavers-math -p kwavers-boundary` exit 0.
4. `cargo nextest run -p eunomia` — `complex_field_over_real_scalar` (`tests.rs:233-243`), `complex_field_over_complex` (`:246-260`), and the new `complex_field_zero_one_over_real_scalar` / `complex_field_zero_one_over_complex` additions. All green.
5. `cargo nextest run -p kwavers-math` — sparse linear algebra tests (`crates/kwavers-math/src/linear_algebra/sparse/solver/tests.rs` for bicgstab Complex64 coverage, and any `csr/coo` tests if present) green.
6. `cargo nextest run -p kwavers-boundary` — the existing boundary-manager test suite (FEM Dirichlet/Neumann/Robin/Radiation at `crates/kwavers-boundary/src/fem/tests.rs:32-99`, BEM at `bem/tests.rs`) passes value-semantically identical pre/post. The golden assertions (`assert_eq!(stiffness.get_diagonal(0), Complex64::new(1.0, -2.0))` at `fem/tests.rs:79-80`; `assert_eq!(h_matrix.get_diagonal(0), Complex64::new(1.0, -2.0))` at `bem/tests.rs:79-80`) stay bitwise-identical because `CompressedSparseRowMatrix<eunomia::Complex64>` and `CompressedSparseRowMatrix<num_complex::Complex64>` share `#[repr(C)] { re, im }` layout and `magnitude` semantics (`|3+4i|` = 5 either way).
7. `cargo doc --no-deps -p eunomia -p kwavers-math -p kwavers-boundary` — warning-clean per `#![deny(missing_docs)]`. The new `fn zero()`/`fn one()` on `ComplexField` carry Rustdoc.
8. `cargo semver-checks release -p eunomia -p kwavers-math -p kwavers-boundary` — authoritatively classify: eunomia `[patch]` (additive default methods), kwavers-math `[patch]` (drop two Cargo.toml deps, narrow one trait bound), kwavers-boundary `[patch]` (drop one Cargo.toml dep, swap one `use` per file).
9. `cargo tree -p kwavers-math -e features -i num-complex` and `-p kwavers-math -e features -i num-traits` — both return zero matches.
10. `cargo run -p xtask -- legacy-migration-audit` — `crates/kwavers-math/src/linear_algebra/sparse/{csr,coo}.rs` no longer appear in the source-legacy per-file list. The `num_traits::` token at line 27 of `migration_audit.rs` no longer matches any first-party kwavers-math source.
11. Property/differential: `eunomia::Complex64::default() == num_complex::Complex64::default()` (a one-off fixture at the consumer site if surfaced; otherwise the TypeId equivalence via eponymous `#[repr(C)]` confirms via existing apollo rustfft compatibility at `crates/apollo-validation/src/infrastructure/rustfft_reference.rs:13-25`).
12. Visual/analytical verification (per `standards`): none required for this purely trait-shape change (no render/printable output).

## Sequencing (implementation increments, atomic commits)

1. **[patch] eunomia** — additive `ComplexField::zero()`/`::one()` defaults (`crates/eunomia/src/traits/field.rs`); two test additions in the existing `tests` mod at `crates/eunomia/src/impls/field.rs:212-264`. Verify with `cargo nextest run -p eunomia` and `cargo doc --no-deps -p eunomia`. Atomic commit.
2. **[patch] kwavers-math** — `crates/kwavers-math/src/linear_algebra/sparse/csr.rs` rewire (the diff above); `coo.rs` no-op; `crates/kwavers-math/Cargo.toml` drops `num-complex` and `num-traits`. Verify with `cargo nextest run -p kwavers-math` and `cargo tree -p kwavers-math -i num-complex`. Atomic commit.
3. **[patch] kwavers-boundary** — `use num_complex::Complex64` → `use eunomia::Complex64` across 8 files (9 sites total — `fem/{manager,types,tests}` and `bem/{manager/mod,manager/assembly,manager/applicators,types,tests}`); `crates/kwavers-boundary/Cargo.toml` drops `num-complex`. Verify with `cargo nextest run -p kwavers-boundary`. Atomic commit.
4. **PM artifact sync** (alongside commit 3, per `documentation_discipline` doc-impact check):
   - `docs/audit/...kwavers-atlas-integration.md` row "Atlas extension: eunomia Complex64 SSOT for csr.rs" → RESOLVED.
   - `repos/kwavers/backlog.md` Phase-1B TODO `kwavers-math full num_traits sweep` → done.
   - `repos/kwavers/CHANGELOG.md` and `repos/kwavers/gap_audit.md` get a Phase-1B done entry.
   - `repos/eunomia/CHANGELOG.md` gets an entry under `### Added` for `ComplexField::zero()`/`::one()` defaults.
   - `repos/kwavers/CHANGELOG.md` gets entries mirroring the Phase-1A format for both `kwavers-math` and `kwavers-boundary` CSRs.
5. **xtask migration-audit allowlist refresh** (commit 4, post-merge): `cargo run -p xtask -- refresh-legacy-allowlist` to retire the `crates/kwavers-math/src/linear_algebra/sparse/{csr,coo}.rs` and `crates/kwavers-math/Cargo.toml` legacy entries.

## Out of scope (explicit non-goals)

- The `kwavers-solver`, `kwavers-physics`, `kwavers-transducer`, `kwavers-diagnostics` `num_complex::Complex<T>` use (~200+ sites verified by code_search — `crates/kwavers/crates/kwavers-{solver,physics,transducer,analysis,diagnostics}/...`). Those are NOT in scope of this ADR. They migrate under Atlas migration Batch #3 (a separate file). CR-EUNOMIA-COMPLEX only unblocks `crates/kwavers-math` and `crates/kwavers-boundary`.
- The `apollo-ghostcell` decommissioning (CR-1) and the `#[global_allocator]` consolidation (CR-2) — sequenced after CR-4 / CR-EUNOMIA-COMPLEX per the `atlas/backlog.md` token-batch ordering.
- Adding additional `ComplexField` methods beyond `zero()`/`one()` (e.g. `from_int`, `is_zero`, etc.) — only the two derivations the §1 default pattern admits. The remainder stays at `<T as NumericElement>::ZERO` form for callers that want compile-time resolution.
- Refactoring `crates/kwavers-math/src/linear_algebra/{eigendecomposition, eigen, complex, solver/{bicgstab,mod}}`, `crates/kwavers-math/src/linear_algebra/ext.rs`, or `crates/kwavers-math/src/linear_algebra/tests.rs`. Those use `num_complex::Complex<T>` directly and migrate under Atlas Batch #3, not in CR-EUNOMIA-COMPLEX.
- Migrating `kwavers-medium`, `kwavers-source`, `kwavers-grid`, `kwavers-python`'s `num_complex::Complex64` use (~50+ additional sites) — Atlas Batch #3.
- Removing `num-complex` from any kwavers crate OTHER than `kwavers-math` and `kwavers-boundary` (transitive dep pulls from kwavers-solver, kwavers-physics, etc. would mask the actual consumption site). Defer until the dependent crate migrates.
