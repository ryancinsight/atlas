# ADR 0005 — `eunomia::NumericElement` as the single scalar-vocabulary SSOT (CR-4)

- Status: **Accepted** (signed off under `interaction_policy` autonomy mode on 2026-07-04: the change is internally verifiable, a local refactor of provider-internal vocabulary with provider-only land; no security/privacy/permissions/data-loss dimension present; no external [`coeus-core`] consumer of the seven deleted trait methods exists in atlas per T1 grep). Implementation in progress on `codex/kwavers-atlas-integration` branch.
- Date: 2026-07-04.
- Drivers: kwavers/CFDrs/ritk Atlas migration (Batches #2/#3/#4 blocked on a single real-trait vocabulary); provider-stratification drift observed during `D:\atlas` Cross-repo Integration Audit (`docs/audit/2026-07-02-cross-repo-integration-audit.md`).
- Supersedes: the CR-4 design sketched in the cross-repo audit summary narrative (and the `atlas/checklist.md` CR-4 section), which proposed `Scalar: NumericElement + RealField`. The evidence gathered during this ADR's pre-implementation T1 read disproves that shape; see §Alternatives ⇒ Rejected variant A and the §Correction note in §Context.

## Context

Three independent backend `Scalar` traits redeclare vocabulary that already lives on `eunomia::NumericElement`:

| Trait | Site | Required methods that duplicate `NumericElement` vocabulary |
|-------|------|------------------------------------------------------------|
| `coeus_core::Scalar` | `repos/coeus/coeus-core/src/dtype/traits.rs:277-450` | `zero()`, `one()`, `to_f64()`, `from_f64()`, `from_usize()`, `sqrt_val()`, `abs_val()` (the body of the trait also carries the legitimate backend extension surface `add_slice`/…/`max_slice` — these are NOT duplicated on `NumericElement` and DO NOT move). |
| `leto_ops::Scalar` | `repos/leto/crates/leto-ops/src/domain/scalar.rs:12-177` | `from_usize(value: usize) -> Self` only (the slice-kernel surface is the legitimate backend extension; it stays). |
| `gaia::Scalar` | `repos/gaia/src/domain/core/scalar.rs:54-106` | `from_f64(v: f64) -> Self` only — already bound over `eunomia::RealField`. |

`eunomia::NumericElement` (at `repos/eunomia/crates/eunomia/src/traits/numeric.rs:7-110`) already exposes:

- Constants: `ZERO`, `ONE`, `NAN`, `INFINITY`, `ALL_ONES`, `SIGN_MASK`, `MIN_VALUE`, `MAX_VALUE`, `BYTE_WIDTH`.
- Methods: `abs(self) -> Self`, `scalar_fmadd(self, b, c) -> Self`, `sqrt(self) -> Self` (float IEEE; integer `isqrt`), `is_finite`, `is_nan`, `to_f64(self) -> f64`, `bitand/bitor/bitxor`, `count_ones`, default-bodied `min_scalar/max_scalar`.
- Supertrait set: `Copy + Default + Send + Sync + 'static + PartialOrd + PartialEq + Debug + Add<Output=Self> + AddAssign + Sub<Output=Self> + SubAssign + Mul<Output=Self> + MulAssign + Div<Output=Self> + CastFrom<i32>`. Sealed via `private::Sealed` (only the `eunomia` crate can add impls).
- Implemented for the full real+integer lattice: `f32`, `f64`, `f16`, `bf16`, signed integers (`i8`/`i16`/`i32`/`i64`), unsigned integers (`u8`/`u16`/`u32`/`u64`/`usize`). Confirmed by `repoS/eunomia/crates/eunomia/src/impls/primitives/{numeric.rs:5-99,float.rs:153-310}`.

`eunomia::FloatElement` adds `from_f32`/`from_f64`/`to_f32` and the transcendentals (`exp`/`ln`/`sin`/`cos`/…) — the `FloatElement` supertrait corresponds to `RealField`'s arithmetic base; `RealField` itself adds the ordered-field constants `PI`/`TAU`/`E`/`EPSILON`/etc.

### Correction note

The cross-repo audit summary narrative (and the derived `atlas/checklist.md` CR-4 section) proposed `pub trait Scalar: NumericElement + RealField {}` as the rebinding. Direct T1 source read of the three `Scalar` traits and their `Int`/`Float` companion subtraits disproves that shape:

- `coeus_core::Int: Scalar` (`traits.rs:552-569`) is implemented for `i8/i16/i32/i64/u8/u16/u32/u64` (Rustdoc line 551). `RealField` requires `FloatElement` and is therefore **float-only**; binding `Scalar: RealField` would orphan every integer `Int`-subtrait impl — a HARD integrity defect under the fake-generic and compatibility-soup rules (`integrity`: "Fake generics: a fn parameterized by `T: Scalar` that casts `T` to a concrete type" — and a missing supertrait cannot be papered over without a cast). The binding must be **`NumericElement` only**, the universal vocabulary that already covers ints and floats uniformly.
- `leto_ops::Scalar::from_usize(value: usize) -> Self` is a load-bearing required method used by the leto-ops linalg kernels (`bunch_kaufman/decompose.rs:67`, `col_piv_qr/decompose.rs:67`, `eigen.rs:33`, `full_piv_lu/decompose.rs:57`, etc.) — these use the `T::from_usize(n)` form, where `n` is an exact dimension count and must NOT route through `f64` (the audit narrative's "for initialization, etc." fails to honour the `coeus_core::Scalar::from_usize` Rustdoc at line 305-310 which requires the native-precision path for index-derived values). `NumericElement` does NOT currently expose `from_usize`; `from_usize` therefore STAYS as a required method on the leto-ops subtrait.
- `coeus_core::Scalar::sqrt_val` and `::abs_val` are NOT subsumed by `NumericElement::sqrt`/`NumericElement::abs` *as syntactically callable traits* — `NumericElement::sqrt` returns `Self` with a documented integer-floor (`isqrt`) contract, while `coeus_core::Scalar::sqrt_val` is used in the `Complex<T>` impl (`complex.rs:200-210`) where the semantics is complex-modulus square root. These are different contracts on different shapes. The rebase must delete the *real-float-shape* redeclarations (which are syntactic duplicates of `NumericElement`'s real surface) while preserving `Complex<T>::sqrt_val` as a `Complex`-inherent method or moving it to `ComplexField::sqrt`. See §Decision §3.

## Decision

Rebase the three backend `Scalar` traits over `eunomia::NumericElement` (the universal element vocabulary, NOT `RealField` — that excludes integers), and delete the per-backend redeclarations of vocabulary already on `NumericElement`. Backend-specific extensions (slice kernels, `from_usize`, `CpuUnaryDispatch`, `Pod`) stay where they are; only the duplicated vocabulary moves.

The single SSOT vocabulary lives on `eunomia::NumericElement`. Reach for `eunomia::RealField` only as the float-only subtrait (matching `gaia::Scalar`'s precedent); never as a `Scalar` supertrait.

### 1. `coeus_core::Scalar` — rebase and slim

Current shape (`traits.rs:277-293`):

```rust
pub trait Scalar:
    private::Sealed
    + Copy + Clone + Send + Sync + Debug + Pod + PartialOrd
    + CpuUnaryDispatch
    + Add<Output = Self> + Sub<Output = Self> + Mul<Output = Self> + Div<Output = Self> + Rem<Output = Self>
    + 'static
{
    fn zero() -> Self;
    fn one() -> Self;
    fn to_f64(self) -> f64;
    fn from_f64(v: f64) -> Self;
    fn from_usize(v: usize) -> Self;
    fn sqrt_val(self) -> Self;
    fn abs_val(self) -> Self;
    // … default-bodies slice kernel surface (add_slice, …, max_slice) — KEPT
}
```

Rebased shape:

```rust
pub trait Scalar:
    NumericElement          // SSOT — provides ZERO/ONE/to_f64/abs/sqrt/is_finite/is_nan/Copy/Send/Sync/Debug/PartialOrd/Add/Sub/Mul/Div/Assigns/CastFrom<i32>/Sealed
    + CpuUnaryDispatch      // backend-specific — coeus's CPU unary kernel dispatch
    + Pod                   // backend-specific — bytemuck host-device transfer contract
    + Rem<Output = Self>    // backend-specific — `Scalar::Rem` is NOT on NumericElement
    + Clone                 // implied by Copy; spelled because impl-site macros call `Clone::clone`
{
    // Note: `zero`, `one`, `to_f64`, `from_f64`, `from_usize`, `sqrt_val`, `abs_val` REMOVED.
    // Slice-kernel default methods (add_slice, …, max_slice) KEPT unchanged in body.
}
```

Dropped supertrait bounds (subsumed by `NumericElement`): `Copy`, `Send`, `Sync`, `Debug`, `PartialOrd`, `Add<...>`, `Sub<...>`, `Mul<...>`, `Div<...>`, `'static`. Kept (NOT subsumed by `NumericElement`): `CpuUnaryDispatch` (backend-specific kernel dispatch), `Pod` (bytemuck), `Rem<Output = Self>` (numeric but not on `NumericElement`), `Clone` (cheap-to-spell even where `Copy` would suffice). Removed AND deleted required-method form: `zero`, `one`, `to_f64`, `from_f64`, `from_usize`, `sqrt_val`, `abs_val`.

The `private::Sealed` supertrait is removed here because `NumericElement` is already sealed by `eunomia`'s `private::Sealed`; keeping a coeus-local second seal in addition to eunomia's would be redundant guarding. Existing concrete impls stay valid because they were already `NumericElement` (every `f16`/`bf16`/`f32`/`f64`/`i8`/…/`u64` is).

### 2. `Complex<T>` impl — inherent methods, not trait methods

`coeus_core::Scalar for Complex<T>` (`complex.rs:161-220`) currently fills `zero`, `one`, `to_f64`, `from_f64`, `from_usize`, `sqrt_val`, `abs_val`. After §1 these trait methods no longer exist. The complex-type operations `sqrt_val` (complex principal square root), `abs_val` (complex modulus), `from_f64` (real→complex embedding), `from_usize` (count→complex embedding) move to **inherent methods on `eunomia::Complex<T>`** in the `eunomia` crate (or, for `sqrt_val`, onto `eunomia::ComplexField` as a default method that already exists as `ComplexField::sqrt` per `field.rs:127-128` — this ADR proposes using the existing `ComplexField::sqrt` surface rather than a new method). `zero`/`one` for `Complex<T>` use `eunomia::ComplexField::from_real(NumericElement::ZERO)`/`from_real(ONE)` — i.e. they are derived from the field vocabulary, no redeclaration needed.

Concretely:

- `Complex<T>::zero` becomes `ComplexField::from_real(<T as NumericElement>::ZERO)` (a one-line default on `ComplexField`'s blanket impl — `eunomia` already ships a blanket `ComplexField for T: RealField` per `field.rs:96-99`).
- `Complex<T>::one` becomes `ComplexField::from_real(<T as NumericElement>::ONE)`.
- `Complex<T>::from_real` already exists on `eunomia::Complex` (its `re + 0i` constructor).
- `Complex<T>::sqrt_val` is replaced by `eunomia::ComplexField::sqrt` (already declared at `field.rs:128`).
- `Complex<T>::abs_val` becomes a one-line `modulus()` (`ComplexField::modulus`, `field.rs:117`) wrapped in `from_real(|z|)` — and is given as a default method `fn abs(self) -> Self { Self::from_real(self.modulus()) }` on `ComplexField` if not already present (verify during impl; if present just reuse).
- `Complex<T>::to_f64` becomes `self.re.to_f64()` inline at call sites — only one consumer today (`coeus_core::Scalar::to_f64` impl); inline directly at the `complex.rs` impl site.
- `Complex<T>::from_f64` becomes `Complex::from_real(<T as NumericElement>::from_f64_or_panic(v))` — wait, that introduces a new vocabulary. Re-derivation: `FloatElement::from_f64` already exists for the float subtrait (`float.rs:11`); `Complex<T>` requires `T: FloatElement` (i.e. extends the existing `T: Float` bound). Define `Complex<T>::from_f64` as `Complex { re: T::from_f64(v), im: <T as NumericElement>::ZERO }` directly — one inline impl. This stays an inherent method on `Complex<T>` because ints cannot `from_f64` and the method is only meaningful for floats.

Final `Complex<T>` `Scalar` impl after §1+§2 reduces to inheriting the default-bodies slice kernel surface (the §1 trait keeps these as default methods); nothing in this impl block remains required-method-shaped.

### 3. `leto_ops::Scalar` — rebase, keep `from_usize` as required

```rust
pub trait Scalar: NumericElement {
    /// Construct a scalar from a non-negative element count.
    /// Native-precision construction; does NOT route through `f64`.
    fn from_usize(value: usize) -> Self;

    // Slice-kernel default methods (add_slice, …, max_slice, jaccard_distance, hamming_distance,
    // axpy_rows, axpy_rows_batch, gemv_*, tiled_gemm) — KEPT unchanged in body.
}
```

The single required method `from_usize` stays. `impl Scalar for f32` (line 183-185) keeps `value as f32`; `f64` keeps `value as f64`. The `impl_scalar_plain!` macro (line 392-401) stays.

### 4. `gaia::Scalar` — already bound over `RealField`; no change

`gaia::Scalar` (at `scalar.rs:54-64`) is already correctly bound over `eunomia::RealField` for the float-only mesh-geometry surface. Its only required methods `tolerance()` and `from_f64(v: f64) -> Self` are NOT redeclarations of `NumericElement` vocabulary (`NumericElement` has no `tolerance`; `NumericElement::from_f64` does not exist; `FloatElement::from_f64` is the SSOT for floats and `from_f64` on `gaia::Scalar` is its delegate). **No change**. The `gaia` precedent's correctness validates the `RealField`-for-float-only, `NumericElement`-for-universal split that this ADR formalises.

### 5. `eunomia::NumericElement` extension: add `from_f64` and `from_usize` to the universal trait

During pre-implementation T1 read of `coeus-core/src/dtype/` impl macros, the transitive consequence of the §1 and §2 rebindings becomes clear: the dispatch-site callers in `int.rs`/`float/cpu_unary.rs`/`complex.rs` use `Self::zero()`/`Self::one()`/`Self::from_f64(...)`/`T::from_usize(...)` precisely because those trait methods exist on `coeus_core::Scalar`. Removing them entirely breaks compilation. The §5 paragraph in the originally-proposed ADR ("no additive change in this ADR") was overconfident — `NumericElement` already owns `abs`/`sqrt`/`to_f64`/etc., and `from_f64`/`from_usize` are the **only** two Scalar-side methods that float/int types *do not yet* find a home for on `NumericElement`.

This revision extends `eunomia::NumericElement` (in `eunomia/crates/eunomia/src/traits/numeric.rs`) with two methods that have `as Self`-backed defaults:

- `fn from_f64(v: f64) -> Self { v as Self }` — lossy cast; works at native default precision. Floats (`FloatElement` implementors) override with the precision-correct path (e.g. `Self::from_f64(v)` for half-precision types routed through `half::f16::from_f32`/`half::bf16::from_f32`).
- `fn from_usize(v: usize) -> Self { v as Self }` — likewise lossy cast; works for all primitive numeric types. Floats and signed/unsigned ints all accept.

These defaults compose correctly with the existing `FloatElement::from_f64` (which remains the precision-correct override for float types). The half/macro impls in `eunomia/crates/eunomia/src/impls/{wrappers,primitives}/numeric.rs` keep their existing `from_f64` overrides (they currently live on `FloatElement`, which is a `NumericElement` subtrait — Rust method resolution prefers the more specific subtrait impl when both are applicable).

This ADR now records a small additive extension to `eunomia::NumericElement`: two methods with `as Self` defaults, plus the corresponding `from_f64` `from_usize` slots in the `impl_numeric_element!` and `impl_numeric_element_{signed,unsigned}!` macros (additive; defaults fall back to `as Self` if not provided). The change is additive SSOT enlargement (no breaking change), not a removal.

### 5b. `coeus_core::Scalar` rebase — corrected plan after §5

Coefs from §1 + §5 net change: the redundant `Scalar::zero()`, `Scalar::one()`, `Scalar::to_f64()`, `Scalar::from_f64()`, `Scalar::from_usize()`, `Scalar::sqrt_val()`, `Scalar::abs_val()` are deleted; their semantics now live on `NumericElement` (the seven cross-cut methods) and `FloatElement::from_f64` (the precision-correct float override) and `ComplexField::sqrt`/`modulus` (the complex methods per §2). The slice-kernel surface in `coeus_core::Scalar` (lines 327-449) stays; the trait's supertrait set is widened as in §1.

The `impl Scalar for {f16, bf16, f32, f64, i8..u64}` blocks in `coeus-core/src/dtype/int.rs` and `coeus-core/src/dtype/float/{half,native}.rs` are emptied (no per-type redundant method bodies; the trait doesn't require them). All `CpuUnaryDispatch` macro bodies (in `coeus-core/src/dtype/int.rs:155-225` and `coeus-core/src/dtype/float/cpu_unary.rs`) have mechanical rewrites:

- `Self::zero()` → `<Self as eunomia::NumericElement>::ZERO`
- `Self::one()` → `<Self as eunomia::NumericElement>::ONE`
- `Self::from_f64(v)` → in float macro: `<Self as eunomia::FloatElement>::from_f64(v)`; in int macro: `v as Self` (literal truncating cast — no `FloatElement::from_f64` for ints)
- `x.sqrt_val()` → `eunomia::NumericElement::sqrt(x)` (semantically identical: float IEEE, int `isqrt`-floor; matches existing `int.rs` impl `(x as f64).sqrt() as $t` and `native.rs` `self.sqrt()`)
- `x.abs_val()` → `eunomia::NumericElement::abs(x)` (semantically identical: `int` built-in, float built-in)
- `T::from_usize(v)` → `v as T` literal cast (the existing `Scalar::from_usize(v)` is literally `v as $t` — the trait method form is degenerate)
- `<$t as Scalar>::from_f64(0.5)` in `float/native.rs:198-203` (GelU/GeluGrad/GeluTanh helpers) → `Self::from_f64(0.5)` after §5 routes to `NumericElement::from_f64`. Direct method form works through deref-of-supertrait at the dtype internal layer.

### 6. Consumer call-site migration

The doubled vocabulary lives almost exclusively in two sites: `coeus-core/src/dtype/complex.rs` (the `Complex<T>` impl block) and the impl macros of `leto-ops/src/domain/scalar.rs`. The reusable consumer-surface call-site evidence is:

- `Scalar::zero()/one()` trait-method form: **exactly two call sites** — `coeus-core/src/dtype/complex.rs:163-176` (`<T as Scalar>::zero()` in `Complex::zero`/`Complex::one`), updated per §2 above. Found zero `Scalar::zero()`/`Scalar::one()` call sites elsewhere in `repos/{coeus,leto,gaia,kwavers,CFDrs,ritk}` (verified by `rg`).
- `Scalar::sqrt_val`/`::abs_val` trait-method form: only inside `coeus-core/src/dtype/complex.rs:200-219` and the `CpuUnaryDispatch` impl's `Abs`/`Sqrt` match arms (`complex.rs:257-258`). Updated per §2 — these become `self.modulus().into_complex()` / `self.sqrt()` via `ComplexField`'s existing surface, or kept as `Complex<T>` inherent methods.
- `Scalar::from_f64`/`::from_usize`/`::to_f64` trait-method form across consumers: zero direct `Scalar::from_f64` sites; `T::from_usize` exists only inside leto-ops linalg kernels (§3 — kept). CFDrs uses the free-function helpers `scalar::from_f64::<T>(...)`/`scalar::to_f64`/`scalar::zero::<T>()`/`scalar::one::<T>()` (cfd-2d/fields.rs, cfd-2d/network/coupled.rs, cfd-3d/{bifurcation,serpentine,trifurcation,venturi}/types.rs etc.) — **these route through `eunomia::NumericElement::ZERO`/`::ONE`** in the existing implementation; they are unaffected by this change. `T::from_f64` in coeus-autograd ops (`node.rs`, `ops/activation/*`, `ops/nn/*`) already routes through `FloatElement::from_f64`, not `Scalar::from_f64`; unaffected.
- `: Scalar` bounds in `coeus-autograd`/`coeus-ops` (~hundreds of sites, all `T: Scalar` shape) and in `leto-ops` (~dozens of `T: Scalar`/`<T: Scalar>` sites) — these bounds keep the trait name `Scalar`; the *supertrait set* widens to include `NumericElement` (additive). CFDrs/ritk/kwavers `T: Scalar + RealField`/`T: Scalar + FloatElement` bounds narrow automatically once `Scalar: NumericElement` (the `RealField`+`FloatElement` supertraits do NOT become implied by `Scalar` — they remain separately written, which is correct because they are float-only and not every `T: Scalar` is a float).

### 7. Semver classification

`cargo-semver-checks` is authoritative per `versioning`. Predicted (to confirm with `cargo-semver-checks` before release):

- `coeus-core`: `[major]` — the `Scalar` trait loses seven required methods. Any downstream crate that called `<T as Scalar>::zero()`/etc. (none found in atlas; external consumers may exist) breaks. Public-release blocker. Requires major bump and a `BREAKING CHANGE:` footer.
- `leto-ops`: `[patch] or [minor]` — only a *supertrait set* widening (additive). Existing `T: Scalar` bounds continue to type-check; new required methods: zero. Public surface is enlargened (downstream's `T: Scalar` now also implies `T: NumericElement`); semver-checks typically treats supertrait additions as breaking for downstream `impl`s but additive for downstream `T: Scalar` bounds. Verify with `cargo-semver-checks`; default to `[minor]` if undetermined.
- `eunomia`: no change in this ADR.
- `gaia`: no change in this ADR.
- Cross-repo consequence for kwavers/CFDrs/ritk: zero new required-device-method signatures; bounds widen (no caller breaks). Active migration branches already pass `Scalar`-bounded sites through `NumericElement` vocabulary (CFDrs free-function helpers, kwavers `eunomia` direct usage). No version bump in consumer repos.

## Alternatives considered

### Rejected variant A — `Scalar: NumericElement + RealField` (the audit's proposed shape)

This is the design the cross-repo audit summary and `atlas/checklist.md` §CR-4 specify. Rejected because `RealField: FloatElement` is float-only — binding `Scalar` over `RealField` orphan's `coeus_core::Int: Scalar` for `i8/i16/i32/i64/u8/u16/u32/u64`. Evidence: `coeus-core/src/dtype/traits.rs:551-569` declares `pub trait Int: Scalar`, with concrete impls for all eight integer types referenced in the Rustdoc at line 551. This is a HARD integrity defect (fake-generic / alias-driven architecture) per `integrity`. The correct universal element vocabulary is `NumericElement` (verified impl set: f32/f64/f16/bf16/i8/.../u64 at `eunomia/src/impls/primitives`). Reach for `RealField` only as a *float-only* subtrait (e.g. `gaia::Scalar` for mesh geometry, which intentionally excludes integers).

### Rejected variant B — empty supertrait `pub trait Scalar: NumericElement + RealField {}` or `pub trait Scalar: NumericElement {}`

This is the form the audit summary narrative literally prescribes ("Empty-body trait (no methods)"). Rejected because it silently deletes the legitimate backend extension surface: `add_slice`/ `sub_slice`/ `mul_slice`/ `div_slice`/ `dot_slice`/ `scale_slice`/ `axpy_slice`/ `sum_slice`/ `min_slice`/ `max_slice` on `coeus_core::Scalar` are the **per-type seam onto the SIMD-effect SSOT** (`hermes-simd`) — eliminating these would strip every coeus array kernel of its slice-dispatch primitive. Same for `leto_ops::Scalar`'s `axpy_rows`/`gemv_*`/`tiled_gemm` (the leto linalg kernels' GEMM/GEMV dispatch surface) and `from_usize`. This would constitute a mock-per-silo-deletion under `integrity` ("match arms mapping all inputs to one output", "ignoring their inputs" — by extension, removing live compute surfaces). The rebase must keep the slice-kernel surface intact.

### Rejected variant C — additive-only: add `NumericElement` supertrait AND keep the duplicated `zero`/`one`/etc. as required methods

Preserves backward compatibility for any external consumer. Rejected under `integrity`: "Compatibility soup" / "Deprecated/obsolete code: remove immediately". The audit's whole point is that there is one SSOT for the vocabulary; keeping two parallel surfaces (NumericElement + the redeclared Scalar methods) is the **alias-driven architecture** `STRONG-DEFAULT` prohibition. Also rejected under `consolidation_discipline` (subtractive default): "the second occurrence is the trigger, because the second copy is where drift begins."

### Rejected variant D — add `zero()/one()/from_usize()/from_f64()` as *default methods* on `Scalar` that route to `NumericElement` constants

Same viability as Variant C in dataset terms (the trait body grows by 5+ method stubs that are one-line forwards). The stubs are not "compatibility shims" in the strict sense (they would compile to const-loads under monomorphization, so zero overhead), but they ARE redundant redeclarations of `NumericElement`'s vocabulary — same integrity rule violation. Rejected unless `cargo-semver-checks` reports a downstream breaking signature change in Variant §1, in which case Variant D as a one-release bridge is the single sanctioned exception per `integrity`'s compatibility-soup escape hatch ("when cumulative call-site updates would exceed the response token limit, a temporary deprecation layer is permitted only if a cleanup task is filed in backlog.md"). Decision tree for the implementer: try §1; if `cargo-semver-checks` reports external-API breakage AND downstream atlas consumers cannot absorb the change atomically, fall back to Variant D for one minor release with a filed cleanup task. Default: §1.

### Rejected variant E — move the slice-kernel surface to `eunomia::NumericElement`

This would put `add_slice`/`mul_slice`/etc. on the universal trait. Rejected because the slice kernels are **backend-specific dispatch surfaces** (the per-type SIMD-effect seam onto `hermes-simd` for coeus; the fallback-loop family for leto-ops). `eunomia` owns only the *element* vocabulary (per `eunomia/src/traits/field.rs:1-8`: "eunomia owns only the scalar field vocabulary"). Putting slice dispatch on `eunomia::NumericElement` would make eunomia depend on `hermes-simd`, breaking the vocabulary/substrate layering per `architecture_scoping` (vocabulary → infrastructure → domain).

## Failure modes / risks

- **External consumers of `<T as coeus_core::Scalar>::zero()` et al.** The atlas-internal scan finds zero such call sites. `coeus` is not yet published to crates.io (per `atlas/CHANGELOG.md` absence and `atlas/backlog.md` 1.0.0-not-released state). Risk is bounded to in-repo consumers; the §6 migration covers all of them. If `cargo-semver-checks` later finds external breakage, Variant D applies.
- **`Complex<T>` arithmetic-method drift.** Moving `sqrt_val` from `Scalar::sqrt_val` to `ComplexField::sqrt` is a contract move: the existing `ComplexField::sqrt` declaration (`field.rs:128`) has no documented body in the audit's head read, but a blanket impl over `Complex<T: RealField>` is implied (`field.rs:96-99` Rustdoc). The implementer T1-reads `eunomia/src/impls/wrappers/complex.rs` (or wherever `ComplexField for Complex<T>` is implemented) and verifies the complex principal square root matches the existing `complex.rs:200-210` body before deletion. Differential test: golden `Complex<f64>` `sqrt` cases against a hand-computed principal branch must stay bitwise-identical.
- **`leto_ops::Scalar::from_usize` and `NumericElement::CastFrom<i32>`.** `NumericElement: CastFrom<i32>` (per `numeric.rs:24`); signed `i32` impls already expose `try_from_i32`-shaped casts. `from_usize(usize)` on `leto_ops::Scalar` is a checked-widening (signed types) or checked-narrowing (smaller unsigned types) on platforms where `usize` exceeds the target type width. The existing `value as f32` / `value as f64` impls do silent truncation for `usize > i32::MAX` (but this is on the float impl, which by `as` semantics produces `+inf` for `usize` huge values — pre-existing behaviour, not in this ADR's scope). Document, do not change in this ADR.
- **Cfd-2d/cfd-3d free-function `scalar::*` helpers.** These already route through `NumericElement` vocabulary (the audit observed `<T as NumericElement>::abs`, `<T as NumericElement>::is_finite` etc); no migration needed. If the helpers internally call `<T as Scalar>::from_f64(v)`, that's a CFDrs-internal question answered during the consumer-side verification in §6 — but since `coeus_core::Scalar::from_f64` is being deleted, the CFDrs `scalar::from_f64::<T>` helper must route through `eunomia::FloatElement::from_f64` directly. The implementer greps the CFDrs `scalar` module for `Scalar::from_f64` users and updates them in the same change.

## Verification plan

Per `engineering_gates` (`local pre-merge gate`, `[arch]`-class change):

1. `cargo fmt --check` across `repos/{coeus,leto,gaia,eunomia,kwavers,CFDrs,ritk}`.
2. `cargo clippy --all-targets --all-features -- -D warnings` across touched repos.
3. `cargo nextest run` under the committed `.config/nextest.toml` (30s slow / 60s terminate), packages: `-p eunomia -p coeus-core -p coeus-autograd -p coeus-ops -p leto -p leto-ops -p gaia -p kwavers-math -p cfd-math -p ritk-core -p ritk-registration`.
4. `cargo test --doc -p coeus-core -p leto-ops -p eunomia` (doctests, which nextest does not execute).
5. `cargo doc --no-deps -p coeus-core -p leto-ops -p eunomia` (warning-clean per `#![deny(missing_docs)]`).
6. `cargo semver-checks release -p coeus-core -p leto-ops` (authoritative classification of the §7 prediction).
7. `rg -n "trait Scalar" repos/{coeus,leto,gaia,eunomia}` returns exactly 3 matches (the 3 backend `Scalar` traits); zero new `Scalar` redeclarations introduced.
8. `rg -n "<.+ as Scalar>::(zero|one|to_f64|from_f64|from_usize|sqrt_val|abs_val)\b" repos` returns zero matches (every duplicated call site migrated to `NumericElement`/`FloatElement`/inherent).
9. Property/differential: every existing `Complex<T>` test (`repos/coeus/coeus-core/tests` or wherever `Complex<T>` is exercised) passes value-semantically; principal `sqrt`, `abs`, `from_f64`, `to_f64` results bitwise-identical pre/post.
10. Visual/analytical verification (per `standards`): none required for this purely trait-shape change (no render/printable output). If any doctest renders numeric content, the values must match pre/post exactly (analytical oracle: the trait rebase moves methods, not implementations).

## Sequencing (implementation increments, atomic commits)

1. **[arch] coeus-core** — `Scalar` rebase (§1) + `Complex<T>` migration (§2). Verify with `cargo nextest run -p coeus-core` and `cargo test --doc -p coeus-core`. Atomic commit; `[major]` bump per §7 if `cargo-semver-checks` confirms external-API breakage.
2. **[patch or minor] leto-ops** — `Scalar` rebase, supertrait set widens (§3). Verify with `cargo nextest run -p leto -p leto-ops` and `cargo test --doc -p leto-ops`. Atomic commit.
3. **(no change) gaia** — verify `gaia::Scalar` continues to compile post-§2 (the `NumericElement` supertrait on `leto-ops::Scalar` propagates through `leto`'s public surface but should not affect `gaia`'s `RealField` binding). If `cargo nextest` reports a `gaia` regression caused by §1/§2, file a follow-up `[patch]` increment; do NOT fix in this ADR's change.
4. **(no change) eunomia** — no source change. Verify `cargo doc --no-deps -p eunomia` is warning-clean.
5. **PM artifact sync** (same commit as the §1 increment per `documentation_discipline` doc-impact check): mark `atlas/checklist.md` CR-4 as done; mark `atlas/gap_audit.md` CR-4 row CLOSED; resequence Batches #2/#3/#4 as Definition-of-Ready in `atlas/backlog.md`; record provider-repo backlog entries per `architecture_scoping` PM scope isolation (`repos/coeus/docs/backlog.md`, `repos/leto/backlog.md`).
6. **CHANGELOG** under `Breaking` in `repos/coeus/CHANGELOG.md` (subject to `cargo-semver-checks` final classification) and `repos/leto/CHANGELOG.md`.

## Out of scope (explicit non-goals)

- Adding `from_usize` or `from_f64` to `eunomia::NumericElement` directly (Variant-D-style SSOT enlargement). `NumericElement` is the universal element vocabulary; `from_usize` is a backend-specific count-construction that lives on `leto_ops::Scalar` by design.
- Migrating `Int` / `Float` coeus subtraits over `eunomia` surfaces. Those subtraits are consumers of `Scalar`; rebasing them is implicitly consistent once `Scalar: NumericElement` but is not load-bearing for any migration unblock and is deferred to a subsequent cleanup.
- Routing CFDrs free-function `scalar::*` helpers through `eunomia` directly (skipping `NumericElement`). They already do (audit confirmed `<T as NumericElement>::abs`/`is_finite` usage); verifying no `Scalar::from_f64`/etc. callers remain is in-scope but no re-route is required.
- The full nalgebra / burn / ndarray elimination in kwavers/CFDrs/ritk. CR-4 only unblocks Batches #2/#3/#4; it does not deliver them.
- The `apollo-ghostcell` decommissioning (CR-1) and the `#[global_allocator]` consolidation (CR-2). Those are sequenced after CR-4 per the `atlas/backlog.md` token-batch ordering.
