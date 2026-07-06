# feat(eunomia): additive `ComplexField::zero()` / `ComplexField::one()` defaults (CR-EUNOMIA-COMPLEX §1)

- **Branch**: `codex/eunomia-complex-field-zero-one` (eunomia fork)
- **Target**: `eunomia` `main`
- **Author**: codex (Codebuff CLI agent acting on user sign-off, per interaction_policy)
- **Depends on**: none (additive; no kwavers-* consumer code lands in this PR)
- **Blocks**: ADR 0006 §3 (`kwavers-math` csr.rs SSOT rebind) acceptance gate, and the follow-up ADR 0007 (solver/* + `kwavers-{physics,transducer,diagnostics,analysis}` `num_complex::Complex<T>` → `eunomia::Complex<T>` migration).

## Summary

Adds two **additive default methods** to `eunomia::ComplexField`:

```rust
#[inline]
#[must_use]
fn zero() -> Self {
    Self::from_real(<Self::RealPart as NumericElement>::ZERO)
}

#[inline]
#[must_use]
fn one() -> Self {
    Self::from_real(<Self::RealPart as NumericElement>::ONE)
}
```

Both bodies are **pure derivation defaults** — `<Self::RealPart as NumericElement>::ZERO` / `::ONE` already exist on `eunomia::NumericElement` (the universal element vocabulary), and `ComplexField::from_real` is already a required method on `ComplexField`. This satisfies `kwavers-math`'s `csr.rs:140,175,228` `T::zero()` call sites without un‐sealing `NumericElement` or introducing a new wrapper type.

## Context (per ADR 0006 `docs/adr/0006-eunomia-complex-csr-ssot.md`)

The `kwavers-math` Phase-1B backlog calls out a manifest-level `[patch]` blocker (`repos/kwavers/backlog.md` "TODO: kwavers-math full num_traits sweep (Phase-1B)"):

> `crates/kwavers-math/src/linear_algebra/sparse/csr.rs` is blocked from dropping legacy dependencies because `impl CsrScalar for num_complex::Complex64` requires `num_traits::Zero`, but Eunomia's generic float traits (`NumericElement` / `FloatElement`) are sealed. Requesting either an unsealed `Scalar` supertrait in Eunomia or a native `eunomia::Complex` integration that supports magnitude/norm derivations to satisfy sparse CSR bounds.

ADR 0006 (Approved 2026-07-05) chose **Path B (native `eunomia::Complex`)** and authored the §1 additive on `ComplexField`. This PR realizes that additive on disk and locks it down with unit-test fixtures so the kwavers-side csr.rs rebind (also authored under ADR 0006 §3) becomes the proving site for `ComplexField::zero()` and `ComplexField::one()` against real `num_complex::Complex<f64>` consumers via the existing blanket impl `impl<T: RealField> ComplexField for Complex<T>` (`crates/eunomia/src/impls/field.rs:90-135`).

## API contract (exact trait change site)

**File**: `crates/eunomia/src/traits/field.rs:117-141`.

```rust
pub trait ComplexField:
    Copy
    + Add<Output = Self>
    + Sub<Output = Self>
    + Mul<Output = Self>
    + Div<Output = Self>
    + Neg<Output = Self>
{
    type RealPart: RealField;
    /* ... existing methods unchanged ... */

    /// Additive identity: `0 + 0i` for a complex field, `0` for a real field.
    /// Default body routes through `NumericElement::ZERO` via `from_real`.
    /// Per ADR 0006 §1 (CR-EUNOMIA-COMPLEX): no per-implementor override is
    /// sound because the real blanket impl returns `re` from
    /// `from_real(re)` and the `Complex<T>` blanket impl returns
    /// `Complex::new(re, <T as NumericElement>::ZERO)`; both round-trip
    /// identically through `Self::from_real(<Self::RealPart as NumericElement>::ZERO)`.
    #[inline]
    #[must_use]
    fn zero() -> Self {
        Self::from_real(<Self::RealPart as NumericElement>::ZERO)
    }

    /// Multiplicative identity: ...
    /// See [`zero`](Self::zero) for the routing rationale.
    #[inline]
    #[must_use]
    fn one() -> Self {
        Self::from_real(<Self::RealPart as NumericElement>::ONE)
    }
}
```

The `from_real` method stays required (it is the constructor for reals and the only place `Complex<T>::from_real` overloads take effect). `zero()` / `one()` are SSOT convenience defaults layered on top, mirroring ADR 0005 §5's `from_f64` / `from_usize` derivation pattern for `NumericElement`.

## Files changed

| File | Type | Substance |
|------|------|-----------|
| `crates/eunomia/src/traits/field.rs` (lines 117-141) | Implementation | Add `fn zero()` / `fn one()` defaults with Rustdoc citing ADR 0006 §1. |
| `crates/eunomia/src/impls/field.rs` (lines 273-303, five `#[test]` fns) | Tests | Five unit-test fixtures (already present post-merge in this branch); ensure they keep running as green. |
| `crates/eunomia/src/impls/field.rs` (lines 252-263, three `#[test]` fns `eunomia_complex*default*`) | Tests | Pin `Complex::default()` to `{ re: 0, im: 0 }` so the additive defaults don't drift later. |
| `crates/eunomia/CHANGELOG.md` | Changelog | New entry under `### Added`: "Additive `ComplexField::zero()` / `::one()` defaults routing through `NumericElement::ZERO` / `::ONE` via `from_real` (CR-EUNOMIA-COMPLEX, ADR 0006 §1)." |

## Tests

Five `#[test]` fixtures in `crates/eunomia/src/impls/field.rs` already cover the additive:

1. `complex_field_zero_over_real_scalar_f64` — `<f64 as ComplexField>::zero() == 0.0_f64`, `<f32 as ComplexField>::zero() == 0.0_f32`.
2. `complex_field_one_over_real_scalar_f64` — `<f64 as ComplexField>::one() == 1.0_f64`, `<f32 as ComplexField>::one() == 1.0_f32`.
3. `complex_field_zero_over_complex_via_default` — `<Complex<f64> as ComplexField>::zero() == Complex::<f64>::new(0.0, 0.0)`, `Complex<f32>` likewise.
4. `complex_field_one_over_complex_via_default` — `<Complex<f64> as ComplexField>::one() == Complex::<f64>::new(1.0, 0.0)`, `Complex<f32>` likewise.
5. `complex_field_zero_routes_through_numeric_element_zero` — full contract pin: the default bodies of `zero()` / `one()` MUST equal `from_real(<Self::RealPart as NumericElement>::ZERO / ::ONE)`.

Plus three pre-existing `eunomia_complex*default*` fixtures (`eunomia_complex64_default_is_zero`, `eunomia_complex32_default_is_zero`, `eunomia_complex64_default_has_zero_modulus`) — they pin `Complex::<f64>::default() == Complex::new(0.0, 0.0)` so the `derive(Default) → ZERO` resolution is preserved at the type layer.

## Semver

**`[patch]`** per ADR 0006 §7 prediction. Two new methods with concrete body defaults on an existing trait. No existing implementor is invalidated (no concrete impl block redeclares `zero()` / `one()`); no consumer's `T: ComplexField` bound is broken (additive); `from_real` stays the single required constructor for non-trivial values.

## Alternative explicitly rejected: unseal `eunomia::NumericElement` (or add a non-sealed `Scalar` supertrait)

The user's `_TODO` Atlas extension memo verbatim offers both shapes. ADR 0005 §Decision is binding:

> `eunomia::NumericElement` is sealed via `private::Sealed` (only the `eunomia` crate can add impls). The `private::Sealed` supertrait is the SSOT defensibility mechanism ADR 0005 deliberately preserves — it prevents Atlas downstream crates from declaring their own `impl NumericElement` for `nalgebra::Complex<f64>`, `num_complex::Complex<f64>`, etc., restoring the alias-driven-architecture pattern ADR 0005 explicitly forbids under `compatibility_soup` / `fake_generics` / `alias_driven_architecture`.

ADR 0006 §"Why not the alternatives" makes the rejection ledger explicit (reproduced verbatim, abbreviated):

> **Rejected Variant A — Unseal `eunomia::NumericElement`.** Make `NumericElement` publicly impl-able so `num_complex::Complex<f64>` (or `nalgebra::Complex<f64>`) can opt in directly. csr.rs becomes one block of `const ZERO / ONE / NAN / INFINITY / ...` declarations. **Rejected.** The `private::Sealed` is what makes the SSOT hold; unsealing reverts CR-4 keystone. A weaker "non-sealed `Scalar` supertrait" variant is rejected for the same reason — re-bifurcates Atlas trait vocabulary.

The CR-EUNOMIA-COMPLEX decision tree landed on Path B (additive `ComplexField` defaults). This PR is the on-disk realization of that decision.

## Verification (per `engineering_gates` `local pre-merge gate`, `[arch]`-class change)

1. `cargo fmt --check` on `repos/eunomia`.
2. `cargo clippy --all-targets --all-features -- -D warnings` on `repos/eunomia`.
3. `cargo nextest run -p eunomia` — all five green: `complex_field_zero_over_real_scalar_f64`, `complex_field_one_over_real_scalar_f64`, `complex_field_zero_over_complex_via_default`, `complex_field_one_over_complex_via_default`, `complex_field_zero_routes_through_numeric_element_zero`, plus the existing `complex_field_over_real_scalar` / `complex_field_over_complex` / `eunomia_complex*default*` / `real_field_constants_and_sign` fixtures.
4. `cargo doc --no-deps -p eunomia` — warning-clean (the two new `#[must_use]` defaults carry Rustdoc pinning ADR 0006 §1 rationale).
5. `cargo semver-checks release -p eunomia` — confirm `[patch]` (additive trait defaults).
6. `rg -n "fn zero\(\)" crates/eunomia/src/traits/field.rs` returns exactly the two new defaults (no per-implementor override elsewhere).
7. Differential oracle: `assert_eq!(<Complex<f64> as ComplexField>::zero(), eunomia::Complex64::default())` — bitwise identical because `Complex::default()` derives to `Complex::new(<f64 as NumericElement>::ZERO, <f64 as NumericElement>::ZERO)` via the `#[derive(Default)]` derivation at `crates/eunomia/src/types/complex/mod.rs:32-35`, identical to the additive `from_real(<f64 as NumericElement>::ZERO)` body.

## Risk + rollback

- **External `<eunomia::ComplexField>::zero()` consumers**: none exist outside the Atlas at PR time (`eunomia` v0.5.x is not yet published to crates.io per the Atlas ADR notes).
- **Atlas-internal consumers**: the only required downstream change is `kwavers-boundary`'s 9 `num_complex::Complex64` sites (per ADR 0006 §3) and the broader solver/* + kwavers-{solver, physics, transducer, diagnostics, analysis, medium, source, grid} migration (per the proposed ADR 0007 follow-up).
- **Rollback path**: revert this commit and the trait returns to "must manually call `from_real(<T as NumericElement>::ZERO)` everywhere"; no consumer-required blast radius because the trait regresses to its pre-PR state.

## PR-template checklists (eunomia)

- [x] Implements CR-EUNOMIA-COMPLEX §1.
- [x] Semver-checks classified `[patch]` (additive).
- [x] ADR 0006 §1 rationale is in-code (Rustdoc) and in this description.
- [x] No new public API beyond the two additive defaults.
- [x] The unseal-Scalar alternative is rejected with verbatim citation of ADR 0005 + ADR 0006.
- [x] All five `complex_field_zero*` and `eunomia_complex*default*` fixtures pass.
- [x] CHANGELOG entry queued.
- [x] PM artifact: `repos/eunomia/gap_audit.md` §"Atlas dependency cleanup" gets a "CR-EUNOMIA-COMPLEX §1 RESOLVED" row.

