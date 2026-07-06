# ADR 0007 — `eunomia::Complex<T>` as the kwavers-solver / `kwavers-{physics,transducer,diagnostics,analysis}` `num_complex::Complex<T>` SSOT (CR-EUNOMIA-COMPLEX §3 follow-up)

- **Status**: Proposed (drafted 2026-07-06, awaiting user sign-off).
- **Date**: 2026-07-06.
- **Approved by**: pending.
- **Driver**: Atlas extension memo `D:/atlas/repos/kwavers/backlog.md` "TODO: kwavers-math full num_traits sweep (Phase-1B)" — the §3 incremental delivery (`csr.rs` SSOT rebind under ADR 0006) is the precondition; this ADR picks up the §3-follow-up scope that ADR 0006 declared **explicitly out-of-scope** ("the broader Atlas migration Batch #3 (`kwavers-solver`/`physics`/`transducer`/`diagnostics` `num_complex::Complex<T>` use, ~200+ sites) is the next frontier unit, not this one").
- **Relates to**: ADR 0006 (`eunomia::ComplexField` SSOT, CR-EUNOMIA-COMPLEX, Approved 2026-07-05); ADR 0005 (`eunomia::NumericElement` SSOT, CR-4, Accepted 2026-07-04); ADR 0004 (hephaestus kernel seam); ADR 0010 (Atlas-parent pointer advance + tag, Accepted 2026-07-05) — adopts the `*atlas-migration-push/batchN*` annotated-tag convention from ADR 0010 once the kwavers-math Phase-1B §3 csr.rs rebind (and the §7-follow-up bulk migration this ADR scopes) lands; per-subcrate atomic `[patch]` commits will be tagged `kwavers/atlas-migration-push/batch<n>` on the inner kwavers branch.
- **Depends on**: ADR 0006 §3 must be **merged** before this ADR can land (the csr.rs rewire establishes the per-`CsrScalar<T>` blanket impl `impl<T: eunomia::ComplexField> ...` that the migration here reuses at the kwavers-solver surface).
- **Affected crates**: `kwavers-solver`, `kwavers-physics`, `kwavers-transducer`, `kwavers-diagnostics`, `kwavers-analysis`, `kwavers-medium`, `kwavers-source`, `kwavers-grid`, `kwavers-boundary` (the latter for the residual `num_complex::Complex64` sites not covered by §3).

## Context

`repos/kwavers/Cargo.toml` declares `kwavers` as a workspace with 24 members spanning the photoacoustic / thermoacoustic / photoacoustic-imaging compute stack. The Phase-1A pilot closed `kwavers_math::linear_algebra::NumericOps<T>` against the eunomia numeric SSOT (`eunomia::RealField` + `NumericElement::ZERO`); see `repos/kwavers/CHANGELOG.md` "Phase-1A pilot (2026-07-05)" and `repos/kwavers/backlog.md` "TODO: kwavers-math full num_traits sweep (Phase-1B)".

The Phase-1B DoR is explicit:

> Phase-1B DoR: choose one of the three Atlas-extension paths for the csr.rs blocker and document the choice in an ADR before the csr.rs edit.

ADR 0006 made and documented that choice (Path B / native `eunomia::Complex` extension), realising it via the §1 additive `ComplexField::zero()` / `::one()` defaults (now on disk at `crates/eunomia/src/traits/field.rs:117-141`, with the five `complex_field_zero*` fixtures at `crates/eunomia/src/impls/field.rs:273-303`) and the §3 `kwavers-math` csr.rs rewire (`CsrScalar: eunomia::ComplexField` + blanket impls synthesized from `impl<T: RealField> ComplexField for T` + `impl<T: RealField> ComplexField for Complex<T>`).

The present state of the Atlas, **as of 2026-07-05**, per `repos/kwavers/CHANGELOG.md` track record and `repos/kwavers/backlog.md` "TODO kwavers-math full num_traits sweep (Phase-1B)" memo:

1. `kwavers-math/sparse/csr.rs` (rebind pending per ADR 0006 §3, the §3 incremental is queued on the `codex/kwavers-atlas-integration` branch);
2. `kwavers-boundary` FEM/BEM legacy `num_complex::Complex64` use (the 9 sites enumerated in ADR 0006 §3);
3. The bulk of remaining `num_complex::Complex<T>` use is inbound on `kwavers-solver`, `kwavers-physics`, `kwavers-transducer`, `kwavers-diagnostics`, `kwavers-analysis`, `kwavers-medium`, `kwavers-source`, `kwavers-grid` — ~200+ sites total in the §"Out of scope" estimate of ADR 0006.

This ADR frames the §3.5 sweep as the **second of two CR-EUNOMIA-COMPLEX increments**: §1 (additive `ComplexField::zero()` / `::one()` defaults) + §3 (`kwavers-math` csr.rs SSOT bind) ship as the seams-class increment; §7 (this ADR) ships the bulk-class migration.

### Naming + layer alignment

- The user's briefing calls the immediate enabler "kwavers-math Phase-1B §3" (i.e., item 3 of the kwavers Phase-1B checklist); that item's body is the csr.rs SSOT rebind, which is exactly ADR 0006 §3.
- This ADR references "CR-EUNOMIA-COMPLEX §3" to mean **the same csr.rs SSOT rebind work**, treated as a hard precondition.
- ADR 0007 has the user-facing posture that the Phase-1B bulk migration patches into the same `eunomia::Complex<T>` / `eunomia::ComplexField::zero()` / `::modulus()` seam that §3 just established.

## Decision

Extend the CR-EUNOMIA-COMPLEX Path B into the residual kwavers surface. **Per-subcrate atomic `[patch]` commits** that:

1. Replace `num_complex::Complex<f32>` / `num_complex::Complex64` (and `<T as num_traits::Num>` `<T as num_traits::Zero>` etc.) with `eunomia::Complex<T>` / `eunomia::ComplexField::{zero,one,modulus,modulus_squared,sqrt,from_real,real,imaginary,conjugate,scale,exp,ln,powf,sin,cos}` surface, picking the relevant method-by-method.
2. Drop `num-complex` and `num-traits` from each affected subcrate's `Cargo.toml`.
3. Re-verify the migration via per-subcrate `cargo nextest run`, then `cargo tree -p <subcrate> -e features -i num-complex`, then `cargo clippy --all-targets --all-features -- -D warnings`.
4. Sequentially fan the migration in the order enumerated below so the kwavers-solver Krylov/direct clusters (the deepest stack-user) validate after the kwavers-physics propagation layer validates after the kwavers-boundary FEM/BEM validates after the kwavers-math csr.rs validates (the seed).

### §1. `kwavers-solver` (largest residual surface)

Replace `num_complex::Complex<T>` with `eunomia::Complex<T>` across:

- `crates/kwavers-solver/src/krylov/{gmres, bicgstab, cg}.rs` — single-precision Krylov arithmetic uses `Complex<f32>` working precision; complex linear-combination kernels, inner-product reductions, and restart-orthogonalization routes through `<eunomia::Complex<f32> as ComplexField>::conjugate()` / `::scale()` / `::from_real()`.
- `crates/kwavers-solver/src/direct/{lu, cholesky, qr, svd, bidiagonalize}.rs` — complex factor kernels route through `ComplexField::sqrt` (already on the trait) for the complex pivot square root and through `ComplexField::modulus_squared` for the column-norm inner products. `num_complex::Complex::cauchy` static helpers get replaced by the eunomia blanket-impl path.
- `crates/kwavers-solver/src/eigen/{schur, qr_algorithm, lanczos}.rs` — the Schur rotation uses `ComplexField::exp(iθ) == from_real(cos θ) + i sin θ`; the lanczos tridiagonal complex form uses `ComplexField::modulus`.
- `crates/kwavers-solver/src/solver/krylov/mod.rs` + `crates/kwavers-solver/src/solver/direct/mod.rs` — type aliases `type Complex64 = eunomia::Complex64;` and `type Complex32 = eunomia::Complex32;` (re-exports consolidated under `crates/kwavers-solver/src/solver/mod.rs::reexport`).
- `crates/kwavers-solver/src/solver/iterative.rs`, `crates/kwavers-solver/src/core/state.rs` — the iterative residual tolerance checks route through `ComplexField::modulus_squared` to avoid per-step `sqrt`.
- All propagated shape: `(re, im)` test fixtures stay bitwise-identical (eunomia's `Complex<T>` is `#[repr(C)] { re: T, im: T }`, layout-compatible with `num_complex::Complex` per ADR 0006 Context).

Cargo.toml: drop `num-complex = { workspace = true }` and (if any) `num-traits = { workspace = true }`. Legacy `nalgebra` retention stays scoped to the leto/Coeus rebalance — out of scope here, no change.

### §2. `kwavers-physics`

`crates/kwavers-physics/src/{acoustics, optics, waves}/{fft, helmholtz, wave_equation, scattering}.rs` consumes `num_complex::Complex64` for spectral Helmholtz solves and complex-plane wave propagation kernels. Migration surface:

- Initialise complex frequency-domain arrays as `eunomia::Complex64` (alias `eunomia::Complex<f64>`, declared `#[repr(C)] { re: f64, im: f64 }` at `crates/eunomia/src/types/complex/mod.rs:25-27`).
- Replace `num_complex::Complex64::new(re, im)` with `eunomia::Complex64::new(re, im)` (identical API, identical layout, identical `PartialEq` / `Display` semantics).
- Replace `<num_complex::Complex64 as num_traits::Zero>::zero()` with `<eunomia::Complex64 as ComplexField>::zero()` — pin: `assert_eq!(<eunomia::Complex64 as ComplexField>::zero(), eunomia::Complex64::new(0.0, 0.0))`.
- Replace `.norm()` / `.norm_sqr()` (num_complex) with `<eunomia::Complex64 as ComplexField>::modulus()` / `::modulus_squared()` (eunomia trait surface).

Cargo.toml: drop `num-complex` (and `num-traits` if held). Apollo-routed FFT prefix-sum/k-space fragment operators stay on Apollo / `kwavers-math` interfaces — those already migrated in Phase-1A (`apollo-validation` referenced `repr(C)` layout-equivalence at `crates/apollo-validation/src/infrastructure/rustfft_reference.rs:13-25`, the apollo-FFT ↔ eunomia cross-walk precedent).

### §3. `kwavers-transducer`

`crates/kwavers-transducer/src/{aperture, beamforming, delay_law}.rs`:

- Multi-element array-factor sums with complex exponentials: `ComplexField::exp(i · k · d)` (`exp` already on the trait), no per-call body in `ComplexField` itself; the application layer constructs `i · k · d == ComplexField::from_real(<RealField as NumericElement>::ZERO) + i · <RealField as NumericElement>::from_f64(phi)` and uses `ComplexField::exp`.
- Band-limited-interpolation (BLI) coefficient tables stay as `Array1<eunomia::Complex<f32>>` / `Array2<eunomia::Complex<f32>>` (migration pre-Phase-1A already brought these to Leto per `crates/kwavers-transducer/Cargo.toml` workspace dep).
- Beam-pattern products / steering-delay inner products route through `ComplexField::modulus_squared` / `::conjugate`.
- No method-body change beyond `use num_complex::Complex64 → use eunomia::Complex64` swaps.

Cargo.toml: drop `num-complex`. The crate's ndarray/Rayon / moirai-parallel migration is independent (already closed in the kwavers-transducer Rayon/ndarray blocker stack per CHANGELOG entries 2026-07-01).

### §4. `kwavers-diagnostics`

`crates/kwavers-diagnostics/src/{coherence, pam, psd, rtm}.rs`:

- Passive acoustic map (PAM) coherence kernels emit complex eigenspace covariances; migration rule is identical to `kwavers-transducer`'s array-factor rule: `ComplexField::modulus_squared` / `::real` / `::imaginary` / `::conjugate` per consumer site.
- Coherence-grade calibration uses `<Complex64 as ComplexField>::modulus` for the off-diagonal interferometric magnitude. Eigenspace decompositions route through `kwavers-solver`'s rebalanced eigen module (post-§1) — **the dependency direction must stay acyclic**; `kwavers-diagnostics` cannot import `kwavers-solver` internals, so its high-level eigenspace compute uses a local real-symmetric Schur reduce via `ComplexField::sqrt` + `ComplexField::modulus_squared` for off-diagonal magnitudes, calling `kwavers-solver::eigen::schur_real` only where the dep is justified (the diagnostics crate already lists `kwavers-solver` as a workspace dep, see `crates/kwavers-diagnostics/Cargo.toml`).
- RTM (reverse-time migration) imaging-condition imaging product: `ComplexField::real(φ · conj(g))` for the broadband image, `ComplexField::modulus` for the migrated envelope; identical API to `kwavers-physics` Helmholtz path, no Surface changes.

Cargo.toml: drop `num-complex` and `num-traits` (if held for legacy num_complex use). The crate's remaining `Moirai` / RTM GPU coherence test surface stays unchanged.

### §5. `kwavers-analysis`

`crates/kwavers-analysis/src/{beamforming,signal_processing,safe_vectorization,visualization,ml}.rs`:

- DAS / MVDR beamforming kernel output is `Array4<f32>` / `Array3<f32>` (real-valued per CHANGELOG migration 2026-07-03 "realtime imaging Leto frame buffers"); complex internals live in the BLI / Eigenvalue / SLSC subtrees, where `num_complex` usage is bounded to:
  - `crates/kwavers-analysis/src/beamforming/covariance.rs` — Hermitian sub-block eigenspace compute; routes through `ComplexField::modulus` / `::modulus_squared`.
  - `crates/kwavers-analysis/src/beamforming/pam/spectrum.rs` — Lorentzian model + f-binning; `ComplexField::exp(2πift)`.
  - `crates/kwavers-analysis/src/ml/uncertainty.rs` — Bayesian dropout log-likelihood ratio on complex-valued beamformed outputs; no `num_complex` direct usage remains after the analysis-side Burn compatibility impl was deleted (2026-07-04).

Cargo.toml: confirm `num-complex` is absent (analysis crate is Rust-only post-Phase-1A); re-affirm the `BurnDAS` removal as the lock-in for this migration slice.

### §6. `kwavers-medium` / `kwavers-source` / `kwavers-grid` (residual scoped)

Per the §"Out of scope" estimate of ADR 0006, these three crates' direct `num_complex::Complex<T>` use is sparse (mostly confined to k-space Chromak / wave-equation / pseudo-spectral slices). Phase-1B-2 verifies the residual scoping:

- `crates/kwavers-medium/src/{medium_field, sound_speed_shift, attenuation_brem}.rs` — confirm via `rg -n "num_complex" crates/kwavers-medium/src` that only the pre-existing k-space wave-equation `(c × iω)` uses stay; those should re-route through `ComplexField::from_real(c × iω)`. If direct usage > 100 sites, file a follow-up batch ADR (§7.5) before further split.
- `crates/kwavers-source/src/{source_field, source_kappa}.rs` — moves surface is real-valued (`f64` mass-flux); residual `num_complex` use is bounded to legacy interpolation fixtures; one-line `use num_complex::Complex64 → use eunomia::Complex64` per file.
- `crates/kwavers-grid/src/{grid_laplacian, grid_geometry}.rs` — grid cell metrics are real-valued; one-line imports max.

Cargo.toml: all three drop `num-complex` (retaining `num-traits` is not needed and is a separate task already considered in `kwavers-physics`'s CHANGELOG entry cleanup).

### §7. `kwavers-boundary` (residual beyond ADR 0006 §3)

ADR 0006 §3 covered 9 `num_complex::Complex64` sites in `crates/kwavers-boundary/src/{fem, bem}/*`. The residual scope in this ADR §7 covers:

- `crates/kwavers-boundary/src/{tests, material_db, viscoelastic_hysteresis}.rs` — fixtures that use `num_complex::Complex64::default()` and `::new(re, im)`; route through `eunomia::Complex64`.
- `crates/kwavers-boundary/src/python_bindings/*.rs` — PyO3-bound FEM matrix outputs typed as `num_complex::Complex64`; surface-renamed to `eunomia::Complex64`.

Cargo.toml: drop `num-complex` (already done in ADR 0006 §3).

## Sequencing (atomic commits, one per subcrate)

1. **[patch] `kwavers-math`** — depends on the eunomia PR (the `ComplexField::zero()` / `::one()` additive) AND on the new eunomia cross-impl ADR (TBD; see `D:/atlas/repos/kwavers/backlog.md` `## TODO: kwavers-math Phase-1B §3 deferral`); rebinds `csr.rs` per ADR 0006 §3, drops `num-complex` + `num-traits` from `crates/kwavers-math/Cargo.toml`. Migration rubric per `repos/kwavers/CHANGELOG.md` "Phase-1A pilot" entry. Verify with `cargo nextest run -p kwavers-math` + `cargo tree -p kwavers-math -e features -i num-complex → zero`. ([deps: ADR 0006 §1 eunomia PR + eunomia cross-impl ADR; both must land before step #1 begins])
2. **[patch] `kwavers-boundary`** — completes the §3 9-site migration (already authored as part of ADR 0006 §3 deliverable) plus the §7 residual FEM/BEM materials + PyO3 bindings. Verify with `cargo nextest run -p kwavers-boundary`. ([deps: kwavers-math merge])
3. **[patch] `kwavers-physics`** — spectral Helmholtz + wave-equation + scattering migration per §2. Verify with `cargo nextest run -p kwavers-physics` + FFT + Helmholtz focused nextest. ([deps: kwavers-math])
4. **[patch] `kwavers-transducer`** — array-factor + BLI + delay-law migration per §3. Verify with `cargo nextest run -p kwavers-transducer` + beam-pattern focused nextest. ([deps: kwavers-math, kwavers-physics])
5. **[patch] `kwavers-solver`** — krylov + direct + eigen + iterative migration per §1 (largest residual). Verify with `cargo nextest run -p kwavers-solver` + Krylov + direct + eigen focused nextest. ([deps: kwavers-math, kwavers-physics, kwavers-transducer])
6. **[patch] `kwavers-diagnostics`** — coherence + PAM + PSD + RTM migration per §4. Verify with `cargo nextest run -p kwavers-diagnostics` + PAM + RTM focused nextest. ([deps: kwavers-solver])
7. **[patch] `kwavers-analysis`** — covariance + PAM-spectrum + ml/uncertainty migration per §5. Verify with `cargo nextest run -p kwavers-analysis`. ([deps: kwavers-solver, kwavers-diagnostics])
8. **[patch] `kwavers-medium` + `kwavers-source` + `kwavers-grid`** — residual scoping per §6. Verify with `cargo nextest run` per crate + `rg` returning zero (no residual `num_complex` hit). ([deps: kwavers-math, kwavers-physics])
9. **PM artifact sync** (alongside commit 8, per `documentation_discipline` doc-impact check): the Atlas backlog `repos/kwavers/backlog.md` "TODO kwavers-math full num_traits sweep (Phase-1B)" entry transitions from `todo` → `done`; `repos/kwavers/CHANGELOG.md` gets a composite `### Changed (2026-07-06) - Atlas Complex SSOT Phase-1B done [patch]` entry; per-subcrate `repos/kwavers/{solver, physics, transducer, diagnostics, analysis, medium, source, grid}/CHANGELOG.md` receive analogous entries; `repos/eunomia/CHANGELOG.md` gets an `### Refs` entry referencing this ADR by ID.
10. **xtask / CI** — `cargo run -p xtask -- refresh-legacy-allowlist` retires the kwavers-* source-legacy entries that include `num_complex` or `num_traits` after the migration. CI gate: `cargo tree -p kwavers --workspace -e features -i num-complex` returns zero matches; `cargo tree -p kwavers --workspace -e features -i num-traits` returns zero matches.

## Verification (per `engineering_gates` `local pre-merge gate`, `[arch]`-class change)

Per-subcrate atomic commit verification:

1. `cargo fmt --check` on `repos/kwavers`.
2. `cargo clippy --all-targets --all-features -- -D warnings` on the affected crate(s).
3. `cargo nextest run -p <crate> <focused-test-set>` — focused nextest filter per affected subtree (FFT/k-space for kwavers-math; FEM/BEM for kwavers-boundary; Helmholtz/wave-equation for kwavers-physics; beam-pattern for kwavers-transducer; Krylov/direct for kwavers-solver; PAM/RTM for kwavers-diagnostics; covariance/uncertainty for kwavers-analysis; k-space for kwavers-medium; fixtures for kwavers-source/grid).
4. `cargo tree -p <crate> -e features -i num-complex` — zero matches per migrated subcrate.
5. `cargo tree -p <crate> -e features -i num-traits` — zero matches per migrated subcrate (where applicable).
6. `cargo doc --no-deps -p <crate>` — warning-clean per `#![deny(missing_docs)]`.

Whole-workspace verification (after step 8 of sequencing):

7. `cargo build -p kwavers --workspace --all-features` exit 0.
8. `cargo nextest run -p kwavers --workspace` exit 0 (with documentation_skip flag for unreadied fixtures).
9. `cargo semver-checks release -p <crate>` per migrated subcrate — confirm `[patch]` (drop-in import rename + drop of `num-complex` is additive for kwavers internals, non-public-API).

Differential / property:

10. Pin `assert_eq!(<eunomia::Complex64 as ComplexField>::zero(), eunomia::Complex64::new(0.0, 0.0))` (already in `complex_field_zero_over_complex_via_default` fixture) for each migrated subcrate's per-crate regression test rebuilder.
11. Pin `assert_eq!(<eunomia::Complex64 as ComplexField>::modulus(z), z.norm_sqr().sqrt())` for kwavers-physics / kwavers-solver migrate sites.
12. Visual: no render / printable output is introduced by these migrations (they are pure Cargo.toml + import + method-dispatch swaps).

## Failure modes / risks

- **Layout drift between `num_complex::Complex64` and `eunomia::Complex<f64>`**: zero drift. Both are `#[repr(C)] { re: f64, im: f64 }` (eunomia's layout is documented at `crates/eunomia/src/types/complex/mod.rs:25-27`; the apollo rustfft reference at `crates/apollo-validation/src/infrastructure/rustfft_reference.rs:13-25` cites both layouts). Downstream `Pod` / `Zeroable` `unsafe impl<T: bytemuck::Pod> bytemuck::Pod for Complex<T>` at `crates/eunomia/src/types/mod.rs:10-11` confirms bytemuck compatibility. Bit-cast cross-walk stays valid pre/post migration.
- **`eunomia::Complex::default()` precision**: `Complex::<f64>::default()` derives `Complex::new(<f64 as Default>::default(), <f64 as Default>::default())`. `Default for f64 == 0.0_rust_f64`, so `default` resolves to `Complex::new(0.0, 0.0)`. Identical to `num_complex::Complex64::default()`. Differential: bitwise-equivalent post migration. Already pinned at `crates/eunomia/src/impls/field.rs:236-263` (`eunomia_complex64_default_is_zero`, `eunomia_complex32_default_is_zero`, `eunomia_complex64_default_has_zero_modulus`).
- **`ComplexField::modulus()` performance**: per-step `modulus_squared` vs `modulus` — the implementation at `crates/eunomia/src/impls/field.rs:103` (real case) returns `NumericElement::abs(self)`; at `:148-149` (complex case) returns `self.norm()` (which is `sqrt(norm_sqr())`). For inner-product loops, prefer `modulus_squared` to skip the `sqrt`. The kwavers-solver Krylov tolerance check sequence already migrates from `.norm_sqr()` / `.norm()` to `modulus_squared` / `modulus` per §1.
- **Cycle constraint on kwavers-diagnostics**: confirmed pre-decision — kwavers-diagnostics already depends on `kwavers-solver` in `crates/kwavers-diagnostics/Cargo.toml`; the §4 acyclic constraint is satisfied by the existing dep direction.
- **`kwavers-medium` k-space residual scope**: if `rg -n "num_complex" crates/kwavers-medium/src | wc -l` returns > 100 sites on first audit pre-migration, file a follow-up ADR §7.5 (a Phase-1B-3 split) and gate this ADR's `kwavers-medium` commit until §7.5 is authored. Rationale: a >100-site sweep warrants its own Definition-of-Ready + checklist, not a tail-end bulk commit.
- **`kwavers-python` PyO3-bound complex types**: the Python bindings crate (`crates/kwavers-python`) re-exports `num_complex::Complex64` only via the legacy path; ADR 0007 §7 (kwavers-boundary) covers the FEM/BEM Python-side, but `kwavers-python` itself is not in scope here — the bindings crate's `pyo3::exceptions` exceptions may have edge-case complex types that need a follow-up ADR (§7.6).

## Alternatives considered

### Rejected Variant A — Unseal `eunomia::NumericElement` (or add a non-sealed `Scalar` supertrait)

The user's `_TODO` Atlas extension memo verbatim offers this alternative. ADR 0005 §Decision is binding:

> `eunomia::NumericElement` is sealed via `private::Sealed` (only the `eunomia` crate can add impls). The `private::Sealed` supertrait is the SSOT defensibility mechanism ADR 0005 deliberately preserves — it prevents Atlas downstream crates from declaring their own `impl NumericElement` for `nalgebra::Complex<f64>`, `num_complex::Complex<f64>`, etc., restoring the alias-driven architecture pattern ADR 0005 explicitly forbids under `compatibility_soup` / `fake_generics` / `alias_driven_architecture`.

The weaker "non-sealed `Scalar` supertrait" variant in the same memo is rejected for the same reason — re-bifurcates Atlas trait vocabulary. ADR 0006 §"Why not the alternatives" makes the rejection ledger explicit: Path B was chosen specifically to avoid re-adding a consumer-implable surface; ADR 0007 inherits that path.

### Rejected Variant B — Build a new native `eunomia::Complex64` API distinct from `eunomia::Complex<T>`

Mentioned only to be explicit that no new wrapper is needed. `eunomia::Complex<T>` is already `#[repr(C)] { re, im }` with `Complex32 = Complex<f32>` / `Complex64 = Complex<f64>` aliases at `crates/eunomia/src/types/complex/mod.rs:25-46` and re-exported at the crate root via `crates/eunomia/src/lib.rs:21-24`. A new API would re-introduce the alias-driven architecture Variant A above. Rejected.

### Rejected Variant C — Per-subcrate seaborn-bridge trait re-declaration (`kwavers::Complex<T>`, `kwavers::ComplexField`)

Sweeping the consumer-side cross-walk beneath a `kwavers`-internal `ComplexField` trait would let `kwavers-solver` / `kwavers-physics` consume that trait uniformly. Rejected because:

- It moves the SSOT into kwavers (away from eunomia) — re-bifurcates the Atlas numeric stack.
- It forfeits the eunomia blanket-impl path that §1 just established: `impl<T: RealField> ComplexField for T` + `impl<T: RealField> ComplexField for Complex<T>`. A kwavers-local trait would require the same blanket impls in `kwavers-solver`, duplicating them.
- Per ADR 0005 consolidation discipline: the second occurrence of the trait body is the trigger for drift; consolidating on eunomia is the chosen path.

### Rejected Variant D — Direct method translation table (`norm` → `modulus`, `norm_sqr` → `modulus_squared`, etc., via a private macro)

`num_complex::Complex<T>` exposes ~30 method names (`arg`, `l1_norm`, `fract`, `is_nan`, `is_infinite`, etc.) that `eunomia::Complex<T>` does NOT expose. A private macro translating them would either:

- Extend `eunomia::Complex` with the missing surface (out of scope; that's a separate eunomia-side proposal), or
- Add a kwavers-local leaf module that wraps `eunomia::Complex` (alias-driven architecture; see Variant C).

Neither is acceptable. The migration is therefore **bounded**: only the methods used by kwavers-* code get migrated; `num_complex`-only methods that have no eunomia equivalent are kept as kwavers-local utility helpers (e.g. a private `kwavers_math::compat::complex::l1_norm(z: eunomia::Complex<f64>) -> f64` if any direct consumer uses `num_complex::Complex64::l1_norm`).

## Out of scope

- `kwavers-python` PyO3-bound complex generators for non-`ComplexField`-shaped PODs (e.g. dictionary-of-arrays complex types). Filed as follow-up ADR §7.6.
- `kwavers-receiver/spectra` modules pinned on third-party / non-Atlas spectral crates not present in the workspace.
- `kwavers-analysis/stochastic` substack depending on `rt-stochastic-*` types (out of Atlas scope).
- The `kwavers-physics/legacy` crate subgroup targeting legacy MAT-file artifact compatibility.
- `apollo-ghostcell` decommissioning (CR-1) and `#[global_allocator]` consolidation (CR-2): independent Atlas milestones, sequenced after the kwavers-complex migration per the Atlas token-batch ordering.
- The kwavers-* Rayon/ndarray-parallel manifest edges: those are independently closed per CHANGELOG entries 2026-07-01 / 2026-07-03 / 2026-07-04. No reliance on this migration for the nd-array-parallel cleanup.
- Hephaestus / hephaestus-CUDA / hephaestus-WGPU backend work (CR-1 successor). Independent Atlas scope.
- A real CUDA-custom FFT path. Apollo/Hephaestus own GPU-FFT; this ADR touches no FFT path directly.
