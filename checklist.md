# atlas — kwavers/CFDrs/ritk → Atlas migration checklist

> Tactical decomposition aligned to `backlog.md`. Each step is atomic, evidence-tied, and self-verify-able. Per `engineering_gates`, only `cargo nextest run` and `cargo test --doc` are sanctioned test runners; changelog version bump and CHANGELOG sync travel with each [minor]/[major]/[arch] commit.
>
> **Active sprint target**: atlas migration 0.16.0 (meta version).
> **Branch**: `codex/kwavers-atlas-integration`.
> **Phase**: Foundation → Execution (batches 1, 2, 3 sequencing determined by Definition-of-Ready below).
> **WIP limit**: one merge-affecting backlog item active at a time (per `context_and_memory WIP limit`).

---

## CR-4 — `[major]` Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` (universal SSOT)

> **Status (2026-07-05)**: Implementation split across 3 commits across the workspace:
>
> | Sub-step | Repo | Commit | Landed |
> | --- | --- | --- | --- |
> | eunomia SSOT extension (Complex<T>, isize, usize impls; trait doc clarifier; private::Sealed impls; CastFrom<i32> edge for platforms) | `eunomia` | `57d7789` | ✅ pushed to main |
> | coeus SSOT rebind + call-site disambiguation across `coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor`, doctests | `coeus` | `2b3f820` (`feat(scalar)!:`) | ✅ pushed to main |
> | leto `Scalar: NumericElement` rebind | `leto` | (BLOCKED — see `## blocker ##` below) | 🔴 parked in working tree |
>
> **Implementation record**: the actual NumericElement-trait shape carries `from_f64`/`from_usize` only inside `FloatElement::from_f64` and the integer `v as Self` literal-cast route — *not* on `NumericElement` itself. The §5 plan originally proposed adding `from_f64`/`from_usize` to `NumericElement`, but T1-verification at compile time proved it'd collide with `FloatElement::from_f64` (duplicate method-name resolution across super/sub-trait). The actual shipped trait surface keeps `NumericElement` constants/methods-only (`ZERO`/`ONE`/`sqrt`/`abs`/`to_f64`/`is_finite`/`is_nan`/`scalar_fmadd`/`bitand`/`bitor`/`bitxor`/`count_ones`/`min_scalar`/`max_scalar`/`BYTE_WIDTH`/`MIN_VALUE`/`MAX_VALUE`/...). The simulator-side dispatch routes floats via `<T as FloatElement>::from_f64(v)` and ints via the literal `v as Self` truncating cast.
>
> **Massive call-site rewrites landed**: ~64 coeus files received `<T as Scalar>::to_f64` / `<T as Float>::abs` / `<T as Float>::sqrt` / `<T as Float>::is_finite` qualifiers — necessary because at the SSOT-bridged surface, `T::to_f64`/`T::abs`/`T::sqrt`/`T::is_finite` resolve to multiple candidates through the `Scalar: NumericElement` path. Disambiguation is the user-confirmed scope of CR-4 because the duplication concern was the *whole point* of the rebind. Adjacent clippy `assign_op_pattern` (`acc = acc + x` → `acc += x`) was fixed in the same atomic commit so the verification gate passes — these were latent-hot-loop patterns that the SSOT rebind surfaced for clippy re-analysis.
>
> **Verified (eunomia + coeus)**: `cargo fmt --check` clean, `cargo clippy --workspace --all-targets -- -D warnings` clean (`coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor` all clippy-green), 1031 coeus nextest tests, 29 eunomia nextest tests, doctests across all crates pass, `cargo doc --no-deps` warning-clean.

> **## blocker ##**

> The leto `Scalar` rebind was concurrently developed in `repos/leto` working tree, but at push time `repos/leto origin/main` had diverted 47 commits ahead of the local maintainer branch (the `leto` project advanced independently through `feat/array-to-vec` PR #30 which has its own independent declaration of `Scalar` traits without the eunomia NumericElement supertrait binding). The local CR-4 `Scalar: NumericElement` rebind conflicts with that pre-published origin design — the divergent declaration of `Scalar` shapes makes a clean merge impossible at the file-`crates/leto-ops/src/domain/scalar.rs` boundary without coordination.
>
> **Resolution path** (user-decision required, NOT blocking eunomia/coeus consumer migration):
> 1. Coordinate with the author of PR #30 / `leto origin/main` — reconcile whether the SSOT-bound vs origin's stable-by-additive-change `Scalar` design wins.
> 2. If SSOT-bound: rebase leto local onto `origin/main` with a recorded migration plan for every `Scalar::add/sub/mul/div` → `NumericElement::+ operator` rewrite (the origin design declares those as required methods of `Scalar`).
> 3. If origin stable: pivot leto's CR-4 contribution to a smaller surface — re-bind only the `from_usize` constructor (the §5 original intent of `leto_ops::Scalar`) and leave the existing `add/sub/mul/div` surface as-is, with `NumericElement` added as an *additional* supertrait rather than a replacement.
>
> Filed for explicit user sign-off per `atlas/backlog.md` Item #7 (`[arch] CR-4: leto ...`).

> **Design SSOT**: `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (status: **Proposed**, awaiting user sign-off pre-implementation per `versioning` policy).
>
> **Correction note**: this section's earlier text proposed `Scalar: NumericElement + RealField` as the binding. The ADR's pre-implementation T1 read disproves that — `eunomia::RealField: FloatElement` is **float-only** (per `eunomia/src/traits/field.rs:17`), and `coeus_core::Int: Scalar` (`coeus-core/src/dtype/traits.rs:551-569`) is implemented for `i8`/`i16`/`i32`/`i64`/`u8`/`u16`/`u32`/`u64`. Binding `Scalar: RealField` would orphan every integer `Int` impl and is a HARD integrity defect (fake-generic / alias-driven architecture). The correct binding is `NumericElement` only — the universal element vocabulary whose impl set covers `{f32, f64, f16, bf16}` ∪ signed+unsigned ints (verified at `eunomia/src/impls/primitives/{numeric,float}.rs`). An empty-body `Scalar {}` supertrait is ALSO rejected — it would silently strip the legitimate backend extension surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `leto_ops::Scalar::from_usize`) which belongs on the backend `Scalar`, NOT on `NumericElement`.

**Pre-reqs** (Definition-of-Ready):
- User signs off on `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (✅ entry on 2026-07-04).

**Plan** (ordered, atomic commits per increment):
1. **[arch] coeus-core** + eunomia SSOT enlargement (atomic commit touching 3 crates):
   - `eunomia/crates/eunomia/src/traits/numeric.rs:7-110`: add `fn from_f64(v: f64) -> Self { v as Self }` and `fn from_usize(v: usize) -> Self { v as Self }` to `NumericElement`. (See ADR 0005 §5 for rationale; the §5 "no change" non-decision in the original ADR was overconfident.)
   - `coeus/coeus-core/src/dtype/traits.rs:277-450` (`pub trait Scalar`):
     - Supertrait set: `pub trait Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem<Output=Self> + Clone`. Drop redundant `Copy/Send/Sync/Debug/PartialOrd/Add/Sub/Mul/Div/'static` (all on `NumericElement`). Drop `private::Sealed` (eunomia's seal covers this).
     - Delete required methods: `zero`, `one`, `to_f64`, `from_f64`, `from_usize`, `sqrt_val`, `abs_val` (each duplicates `NumericElement::ZERO`/`::ONE`/`::to_f64`/`::from_f64`/`::from_usize`/`::sqrt`/`::abs` post-§5).
     - Keep default-bodies slice-kernel surface (`add_slice`/`sub_slice`/`mul_slice`/`div_slice`/`dot_slice`/`scale_slice`/`axpy_slice`/`sum_slice`/`min_slice`/`max_slice`) — these are the `hermes-simd` per-type seam, NOT duplicated on `NumericElement`.
   - `coeus/coeus-core/src/dtype/float/native.rs:5-37` (`impl_scalar_float_native` macro for `f32`/`f64`): delete the 7 redundant methods from `Scalar` impl; the slice-kernel surface stays as `coeus_core::Scalar` trait bodies. Float `Float`/`FloatOps`/`CpuUnaryDispatch` impls outside `Scalar` are unaffected.
   - `coeus/coeus-core/src/dtype/float/half.rs:6-37` (`impl_scalar_float_half` macro for `f16`/`bf16`): same — empty the Scalar impl.
   - `coeus/coeus-core/src/dtype/int.rs:9-108` (int orig/uint orig macros for `i8..u64`): empty the Scalar impl.
   - `coeus/coeus-core/src/dtype/float/cpu_unary.rs` (`impl_cpu_unary_dispatch_float` macro):
     - `Self::zero()` → `<Self as eunomia::NumericElement>::ZERO`
     - `Self::one()` → `<Self as eunomia::NumericElement>::ONE`
     - `Self::from_f64(v)` → `<Self as eunomia::FloatElement>::from_f64(v)`
     - `x.sqrt_val()` → `eunomia::NumericElement::sqrt(x)` (call form: `x.sqrt()`)
     - `x.abs_val()` → `eunomia::NumericElement::abs(x)` (call form: `x.abs()`)
   - `coeus/coeus-core/src/dtype/int.rs:155-225` (`impl_cpu_unary_dispatch_int` macro):
     - `Self::zero()` → `<Self as eunomia::NumericElement>::ZERO`
     - `Self::one()` → `<Self as eunomia::NumericElement>::ONE`
     - `Self::from_f64(v)` → `v as Self` (literal truncating cast; no `FloatElement::from_f64` for ints)
     - `x.abs_val()` → `eunomia::NumericElement::abs(x)`
     - `x.sqrt_val()` → `eunomia::NumericElement::sqrt(x)`
   - `coeus/coeus-core/src/dtype/float/native.rs:198-203` (`impl_scalar_float_native: gelu_op`): `<$t as Scalar>::from_f64(0.5)` → `<$t as eunomia::NumericElement>::from_f64(0.5)` (now resolves through SSOT).
   - `coeus/coeus-core/src/dtype/complex.rs:161-220` (`impl<T: Float> Scalar for Complex<T>`): becomes an empty impl block (the trait requires no methods post-rebase; slice kernels inherit defaults). Delete the whole impl body. Any caller of `Scalar::zero()/one()/etc.` on `Complex<T>` must migrate per caller-rewrite below in §5 of this checklist.
   - `coeus/coeus-core/src/dtype/complex.rs:222-281` (`impl<T: Float> CpuUnaryDispatch for Complex<T>`): within the dispatch macro body, replace `Self::zero()`/`Self::one()` with `<Self as eunomia::NumericElement>::ZERO/::ONE`, `T::zero()`/`T::one()` with `<T as eunomia::NumericElement>::ZERO/::ONE`, `x.sqrt_val()` becomes `eunomia::ComplexField::sqrt(x)` (delegation: field.rs:158-160), `x.abs_val()` becomes `eunomia::ComplexField::from_real(eunomia::ComplexField::modulus(x))`.
   - `coeus/coeus-core/src/dtype/float/native.rs` and half's `gelu_op/erf_op/lgamma_op` etc.: any `<$t as Scalar>::from_f64(...)` becomes `<$t as eunomia::NumericElement>::from_f64(...)` (post-§5).
   - Cargo: no Cargo.toml change required (`coeus-core/Cargo.toml` already declares `eunomia = { workspace = true }`).
   - Verify: `cargo nextest run -p coeus-core -p eunomia`, `cargo test --doc -p coeus-core -p eunomia`, `cargo doc --no-deps -p coeus-core -p eunomia`, `cargo semver-checks release -p coeus-core -p eunomia`. Atomic commit; bump per `cargo-semver-checks` output (`eunomia` `[minor]` additive; `coeus-core` `[major]` removal).
2. **[patch or minor] leto-ops** (`leto/crates/leto-ops/src/domain/scalar.rs:12-177`):
   - `pub trait Scalar: NumericElement { fn from_usize(value: usize) -> Self; /* default-bodies slice kernels */ }`. Only `from_usize` remains required.
   - `impl_scalar_simd!` and `impl_scalar_plain!` macros unchanged in body (they only set `from_usize` and override default slice kernels).
   - Verify `leto-ops`'s `eunomia` dep (`Cargo.toml:22`, already present) covers the new supertrait; no Cargo change.
   - Optional follow-on [patch] (separate commit, separate batch entry): strip `num-traits` from `leto-ops/Cargo.toml:18` if `rg "num_traits" repos/leto/crates/leto-ops/src` returns zero after this change.
   - Verify: `cargo nextest run -p leto -p leto-ops`, `cargo test --doc -p leto-ops`, `cargo doc --no-deps -p leto-ops`, `cargo semver-checks release -p leto-ops`. Atomic commit.
3. **(verify-only) gaia** — `gaia/src/domain/core/scalar.rs:54-106` already bound over `eunomia::RealField`; no change. Verify `cargo nextest run -p gaia` green after #1+#2 land.
4. **(verify-only) eunomia** — `NumericElement::ZERO`/`::ONE` already at `eunomia/src/traits/numeric.rs:27-29`; no source change. Verify `cargo doc --no-deps -p eunomia` warning-clean.
5. **Consumer-repo verification** — `cargo nextest run` for downstream packages that consume `coeus-core::Scalar` or `leto-ops::Scalar`: `-p kwavers-math -p cfd-math -p ritk-registration` at minimum.
6. **PM sync** (in the same commit as #1): mark CR-4 done here, mark `atlas/gap_audit.md` CR-4 row CLOSED, resequence Batches #2/#3/#4 as Definition-of-Ready in `atlas/backlog.md`, write provider-local backlog entries per `architecture_scoping` PM scope isolation.
7. **CHANGELOG**: under `Breaking` in `repos/coeus/CHANGELOG.md` and `repos/leto/CHANGELOG.md` (subject to `cargo-semver-checks` final classification).

**Leak-check (investigate during implementation; not blocking the ADR)**:
- `Complex<T>::from_usize` post-rebase: if `T` is bounded only on `coeus_core::Scalar` (which after rebase is `NumericElement`, not `leto_ops::Scalar`), there is no `from_usize` on `T`. Two resolutions: (a) make `Complex<T>::from_usize` an inherent helper that delegates to `v as T` for floats (requires `T: FloatElement`) — works because `Complex<T>` is bounded on `Float` already, which inherits the f32/f64-only `as`-cast surface; or (b) require `Complex<T>: Scalar` impls also bound `T: leto_ops::Scalar` — unlikely. Resolution (a) is cleanest; investigate at impl time.

**Completion condition (evidence)**:
- `cargo nextest run -p eunomia -p coeus-core -p coeus-autograd -p coeus-ops -p leto -p leto-ops -p gaia -p kwavers-math -p cfd-math -p ritk-core -p ritk-registration` green.
- `cargo test --doc -p coeus-core -p leto-ops -p eunomia` green.
- `cargo semver-checks release -p coeus-core -p leto-ops` reports the §7-predicted classification (`[major]` for coeus-core; `[minor]` or `[patch]` for leto-ops).
- `rg -n "<.+ as Scalar>::(zero|one|to_f64|from_f64|from_usize|sqrt_val|abs_val)\b" repos` returns zero matches (every duplicated call site migrated to `NumericElement`/`FloatElement`/inherent).
- `rg -n "trait Scalar" repos/{coeus,leto,gaia,eunomia}` returns exactly 3 matches (the 3 backend `Scalar` traits); zero new redeclarations.
- `Complex<T>` tests (wherever they live in `repos/coeus`) value-semantically green; principal `sqrt`/`abs`/`from_f64`/`to_f64` results bitwise-identical pre/post.

**Next step after CR-4 (unblocks)**:
- Batches #2 (CFDrs nalgebra finish), #3 (ritk Burn trait rebind), #4 (kwavers-solver PINN → Coeus) become Definition-of-Ready.
- Per `decision_policy` lowest-risk-vertical-slice bias, Batch #1 (kwavers-solver/physics Rayon → Moirai) is sequenced next — but it is *not gated by CR-4* and can land in parallel; see its own checklist section.

**Pre-reqs** (Definition-of-Ready):
- ✅ `coeus/coeus-core/src/dtype/traits.rs` current shape T1-read by owner (2026-07-04).
- 🟡 `leto/crates/leto-ops/src/domain/scalar.rs` — *local* branch rebind T1-read, but origin/main diverged 47 commits; SSOT integration pending user decision per `## blocker ##` above.
- ✅ Both eunomia + coeus-primary redeclarations removed; backends extend `NumericElement` rather than redeclare vocabulary.

**Plan** (the old CR-4 plan, now superseded by ADR 0005 — left for archaeology; do NOT execute this version):
1. Author `eunomia::NumericElement::zero() -> Self` and `::one() -> Self` directly (today only via `Default`). File: `eunomia/crates/eunomia/src/traits/numeric.rs:7-17` body. Owner: `eunomia`.
2. Rebase `Scalar` in `coeus-core/src/dtype/traits.rs:1-11` as `pub trait Scalar: eunomia::NumericElement + eunomia::RealField {}`. Empty-body trait (no methods). File-line: `coeus/coeus-core/src/dtype/traits.rs`.
3. Rebase `Scalar` in `let''o-ops/src/domain/scalar.rs:1-21` same shape.
4. Update kwavers consumers:
   - `crates/kwavers/Cargo.toml:52` already imports `eunomia`; pass-through fine.
   - `crates/kwavers-math/Cargo.toml:18` still declares `num-traits = "0.2"`; strip it (verify no source uses `use num_traits::*`).
   - Confirm `cfd-math/src/linear_solver/conjugate_gradient/mod.rs:6,7` `use nalgebra::RealField` → `use eunomia::RealField`. Same for `cwit-stub/mod.rs:6,7` etc.
5. Update CFDrs consumers (parallel):
   - `CFDrs/Cargo.toml:41` `num-traits = "0.2"` strip after all `nalgebra::RealField` refs replaced.
   - `let''ops::Scalar` callers patched through `RealField` import migration.
6. Update ritk consumers (parallel):
   - `crates/ritk-registration/src/classical/spatial/kabsch.rs:11` `use eunomia::FloatElement` (existing) stays; verify SVD result type routes leto's `RealField`.
   - `RITK/Cargo.toml:112 num-traits` strip.
7. Changelog: `[major]` bump in `atlas` meta-version; CHANGELOG entry for `eunomia SSOT inheritance`.

**Completion condition (evidence)** (the old CR-4 completion condition, now superseded by ADR 0005 — use the new CR-4 completion condition above):
- `cargo nextest run -p eunomia -p coeus-core -p leto-ops -p kwavers-math -p cfd-math -p ritk-registration` green.
- `cargo tree -i num-traits -p kwavers` returns zero.
- `cargo tree -i num-traits -p CFDrs` returns zero (or shows only `[dev-dependencies]` of an `apollo-validation` dev-crate).
- `rg -n "Scalar = ..." crates/kwavers crates/CFDrs crates/ritk` returns zero matches outside the three SSOT sites.
- `cargo clippy --all-targets -- -D warnings` green across the touched repos.

**Next step after CR-4 (unblocks, per ADR 0005)**:
- Batches #2/#3/#4 become Definition-of-Ready. The token-batch ordering in `atlas/backlog.md` is: #5 (CR-1) → #6 (CR-2) → #1 → #2 → #3 → #4 → #8.

---

## Batch #5 — CR-1 (Apollo-ghostcell → Melinoe) `[arch]`

> Dependency-only — no Atlas-migration unblock, but the cleanup intrinsic to this branch goal.

**Pre-reqs**:
- `apollo/crates/apollo-ghostcell/src/lib.rs` inventoried: full source-read by owner.
- `melinoe::MelinoeCell` reachable (confirmed at `melinoe/src/lib.rs:18-24, 65-115, 233`).
- Apollo's consumers via `apollo-ghostcell` cited: T1 cross-grep `rg -l "apollo_ghostcell\|ghostcell" repos/apollo/crates`.

**Plan**:
1. List every consumer of `apollo_ghostcell` across `apollo` workspace via cross-grep (T1: `rg -nl "ghostcell" repos/apollo`).
2. For each: replace `apollo_ghostcell::*` with `melinoe::*`; patch the `brand_scope!` mint call to `melinoe::brand_scope!(|mut token| ...)`.
3. Delete `apollo/crates/apollo-ghostcell` from `apollo/Cargo.toml` workspace `members`.
4. Update `apollo/docs/adr/*` (if any IDR exists) referencing `apollo-ghostcell`; cross-link to `melinoe` as the SSOT.
5. Changelog: `[arch]` bump `apollo` per templating (`repos/apollo/release.toml`), with `BREAKING CHANGE:` footer.

**Completion condition**:
- `repoS/apollo` no longer carries `apollo-ghostcell` member.
- `rg -l ghostcell` returns zero matches across `apollo` (only `melinoe` mentions kept).
- `cargo nextest run -p apollo-* --features melinoe` green.
- `cargo miri test -p melinoe` green.
- `cargo clippy --all-targets -- -D warnings` green.

---

## Batch #6 — CR-2 (Consolidate `#[global_allocator]`) `[arch]`

**Pre-reqs**:
- Inventory of every library-side `#[global_allocator]` registration: `rg -n "global_allocator" --type rust crates repos/CFDrs/crates repos/CFDrs/xtask repos/coeus/coeus-python` T1.
- Mnemosyne handle signature ready in DI shape (audit `docs/audit/2026-07-02-cross-repo-integration-audit.md:L76-95`).
- Binaries that need registration published: per-binary list `kwavers-cli`, `cfd-cli`, `helios`, `helios-python`, `ritk-cli`, `coeus-python`, etc.

**Plan**:
1. Audit: T1 list each library site (provisional): `cfd-core/src/lib.rs:45-53`, `ritk-core/src/lib.rs:15-17` (dead config gate — confirm), `moirai/moirai/src/lib.rs` (TBD), `coeus/coeus-python/src/lib.rs:7-9`.
2. Replace each library registration with a Mnemosyne handle carrier struct: `pub struct MnemosyneHandle { … }` re-exported via `mnemosyne::Handle`.
3. Update each library `Cargo.toml` to drop the `mnemosyne` feature implication; pass the handle in main.
4. Each binary in the integration workspace (kwavers-rs binary, cfdsuite-cli, helios, ritk-cli, etc.) keeps the registration.
5. Changelog: `[arch]` bump individual binaries; cross-link to a new ADR `atlas/docs/adr/0004-allocator-handle-pattern.md`.

**Completion condition**:
- Library `crates/*/src/lib.rs` no longer carries `#[global_allocator]`.
- Binaries successfully link `mnemosyne` and resolve handle through DI.
- `cargo build -p cfd-core --no-default-features` green (no allocator requirement leaks into crate library).
- `cargo nextest run` green for the four repos.
- `cargo clippy --all-targets -- -D warnings` green.

---

## Batch #1 — `[patch]` kwavers-solver / kwavers-physics residual Rayon → Moirai

**Pre-reqs**:
- `moirai-parallel/src/lib.rs:106-181` confirms `par()` / `par_mut()` rebind (T1 verification by owner).
- `crates/kwavers-solver/src/{inverse/reconstruction/seismic/rtm/inherent, inverse/same_aperture}/...` and `crates/kwavers-physics/src/acoustics/...` source-read in inventory.
- Migration pattern noted: `Zip::indexed(arr).par_for_each(...)` → `auto_moirai_for_each(arr, |i, _| ...)`. Helper macro or `par().enumerate()` direct.

**Plan**:
1. Add the helper `let''o::par_for_each_indexed` if not present (or use `moirai-parallel::par_mut().enumerate()` directly). Cite library file.
2. For each `.par_for_each` site in `kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{...}.rs` (23 sites) and `kwavers-solver/src/forward/nonlinear/kuznetsov/{...}.rs` (19 sites), patch to replace.
3. For each `.par_for_each` site in `kwavers-solver/src/forward/elastic/swe/{integration,stress}/...` (13 sites).
4. For each `.par_for_each` site in `kwavers-solver/src/forward/pstd/extensions/elastic.rs` (4 sites).
5. For each `.par_for_each` site in `kwavers-solver/src/multiphysics/fluid_structure/{interface,solver}.rs` (3 sites).
6. For each `.par_for_each` site in `kwavers-physics/src/acoustics/...` and `kwavers-physics/src/optics/polarization/linear.rs` (24 sites).
7. Strip `ndarray = { ..., features = ["rayon"] }` from `kwavers-solver/Cargo.toml:24` and `kwavers-physics/Cargo.toml:20`.
8. Confirm `cargo tree -p kwavers-solver | grep ndarray` shows no `rayon` feature.
9. CHANGELOG: `[patch]` per `kwavers/CHANGELOG.md` with Replaced fence data citing each module.

**Progress this slice**:
- Replaced `Zip::indexed(...).par_for_each(...)` with `crate::parallel` helpers in:
  - `crates/kwavers-physics/src/acoustics/skull/heterogeneous/mask.rs`
  - `crates/kwavers-physics/src/acoustics/therapy/sonogenetics/membrane.rs`
  - `crates/kwavers-physics/src/acoustics/mechanics/cavitation/damage/erosion.rs`
- Remaining `par_for_each` sites in `kwavers-physics` and `kwavers-solver` are still open per Batch #1 schedule.

**Completion condition**:
- `cargo nextest run -p kwavers-solver -p kwavers-physics` green.
- `cargo nextest run -p kwavers-solver -p kwavers-physics fast_tests/medium_tests/slow_tests` green with no skip.
- `cargo tree -p kwavers-solver | grep rayon` returns zero.
- `cargo clippy --all-targets -- -D warnings -p kwavers-solver -p kwavers-physics` green.
- Spatial norm conservation: each migrated module's spatial-step norm within `O(N·ε)` bounded derived epsilon (reduction order). FFT/PSTD residual reductions derive Kahan-compensated epsilon per `numerical_discipline`.

---

## Batch #2 — `[minor]` CFDrs nalgebra → leto completion; nalgebra-sparse → leto-ops

**Pre-reqs** (post-CR-4):
- `eunomia::RealField` reachable; consumers routed.
- `let''o::Array1/2/3<T>` publicly exposed (confirmed T1).
- `let''o-ops::CsrMatrix` reachable (CFDrs `crates/cfd-math/src/sparse/operations.rs:37` already consumes).
- `let''o::FixedMatrix<T,3,3>` and `FixedVector<T,3>` reachable (confirmed T1).

**Plan** — two passes:
A. **Trait surface rebind** (per `LetoRealScalar` chain):
   - `cfd-math/src/linear_solver/chain.rs:62-72` rebind to eunomia `RealField`. Update BiCGSTAB fallback.
   - Every `RealField` mention in `cfd-math/src/linear_solver/{conjugate_gradient, bicgstab, gmres, preconditioners, matrix_free}/...`. File-line inventory per part-A row.
   - `cfd-math/src/dense_bridge.rs:4-5` already a Leto boundary; rebind internals.
B. **Body migration** (per-file):
   - `cfd-math/src/linear_solver/preconditioners/{basic, cholesky, deflation, ilu/{ilu0, iluk, triangular, types}, multigrid/{amg, coarsening/{mod, algorithms, quality}, interpolation, smoothers, mod}, schwarz, ssor}.rs` — `nla_sparse::CsrMatrix` → `let''o_ops::CsrMatrix`.
   - `cfd-3d/src/fem/{element:35, projection_solver:446+, leto_bridge, mesh_utils, mid_node_cache, quadrature, shape_functions, solution, solver, stabilization, stress, fluid}.rs` — `nalgebra::{DMatrix,DVector,Matrix3,Vector3}` → `let''::{Array2,Array1,FixedMatrix<T,3,3>,FixedVector<T,3>}`.
   - `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**` — same.
   - `cfd-3d/src/vof/{cavitation_solver, reconstruction}.rs` — `DMatrix` → `let''::Array2`.
   - `cfd-1d/src/solver/core/{convergence:63,214, linear_system:36,37,364, matrix_assembly:63,64, state:20, workspace:2, anderson_acceleration, mod, solver_detection}.rs`, `cfd-1d/src/domain/network/wrapper.rs:13`, `cfd-1d/src/scalar.rs` — drop `nalgebra_sparse` storage.
   - `cfd-validation/src/geometry/{annular, bifurcation_2d, circular, rectangular, trifurcation_2d, threed/bifurcation}.rs` — geometry `DMatrix/DVector` → leto.
   - `cfd-validation/src/benchmarks/{cavity, cylinder, poiseuille_bifurcation:60, runner, step, threed/nufft_coupling, mod}.rs` — solver vector Realmigration.
   - `cfd-validation/src/{adaptive_mesh, numerical, manufactured, literature, tests, benches}/**` — `DMatrix` reservoir.
   - `xdtests 176-file allowlist` — drop after closure, `xtask migrate-audit -- --strict-context` reports zero legacy residual.
3. Strip `CFDrs/Cargo.toml:38-41` (`nalgebra`, `nalgebra-sparse`, `num-traits`, `serde-serialize` feature) and the per-crate `Cargo.toml` entries.
4. Adopt `[patch]` for `nalgebra*` workspace-level = not needed (unconditional drop).
5. CHANGELOG: `[minor]` per CFDrs policy.

**Completion condition**:
- `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation -p cfd-2d -p cfd-core` green.
- `cargo xtask migrate-audit --strict` returns no legacy tokens across CFDrs.
- `cargo tree -p CFDrs \| grep nalgebra` returns zero production ops.
- Numerical regression: each module's spatial-step norm/par criteria remain within pre-migration baseline per analytics-child false-__________ epsilon budget (criterion baseline).

---

## Batch #3 — `[minor]` ritk Burn-keyed trait rebind (provider side)

**Pre-reqs** (post-CR-4 + `coeus-core::ComputeBackend`):
- Reference: `ritk-image/src/native.rs:10-11` already exposes `Image<T: Scalar, B: ComputeBackend, const D: usize>`.
- `coeus-core/src/backend/moirai.rs` exposes `MoiraiBackend` ZST as `ComputeBackend`.

**Plan**:
1. Audit existing public API surface for `B: Backend`:
   - `ritk-core/src/image/types.rs:18` (`Image<B,D>`)
   - `ritk-core/src/transform/trait_:19` (`Transform<B,D>`)
   - `ritk-core/src/interpolation/trait_:20` (`Interpolator<B>`)
   - `ritk-spatial/src/{vector,point,direction,spacing}:7` (`burn::module::{Module,AutodiffModule} + burn::record::Record`)
   - `ritk-wgpu-compat/src/lib.rs:40+` `apply_row_chunks<B: Backend>`
2. Migrate signatures:
   - `Image<B: ComputeBackend, const D: usize>` where `B: coeus_core::ComputeBackend` (re-export).
   - `Transform<B: ComputeBackend, const D: usize>` same.
   - `Interpolator<B: ComputeBackend>` same.
   - Drop `burn::record::Record` impls on `ritk-spatial::Vector/Point/Direction/Spacing`; replace with `coeus_nn::Record` if necessary (determine by migration for downstream consumers).
3. Audit downstream consumers (kwavers-imaging, helios-imaging, ritk-cli, ritk-python) for `B: Backend` patterns; templatize through `B: ComputeBackend`. Provide `type Bn = burn::backend::NdArray<f32>` alias compat shader for legacy consumers for one sprint (compat-only).
4. Strip `RITK/Cargo.toml:69` `burn-wgpu` feature (already in backlog narrative — verify file state; literal or narrative drift).
5. CHANGELOG: `[minor]` per RITK; cross-link the [major] `burn remove` plan in next sprint.

**Completion condition**:
- `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation, io, model}` green.
- `cargo tree -p ritk -i burn-wgpu -i burn-cuda -i burn-rocm` returns zero; `cargo tree -p ritk -i burn-ndarray` reports only NdArray backend (`burn::backend::NdArray`) which remains a CPU reference.
- `cargo clippy --all-targets -- -D warnings -p ritk` green.

---

## Batch #4 — `[minor]` kwavers-solver PINN Burn → Coeus

**Pre-reqs** (post-CR-4 + #3 + Coeus extension `scatter_add`):
- `coeus-core/src/backend/moirai.rs:56-89` confirms `MoiraiBackend` as CPU `ComputeBackend`.
- `coeus-autograd::{Var, backward, grad_buffer}` reachable.
- `coeus-optim::{SGD, Adam, AdamW, LrScheduler}` reachable.

**Plan**:
A. Manifest bridge:
1. `kwavers-solver/Cargo.toml` add `coeus-core`, `coeus-autograd`, `coeus-tensor`, `coeus-ops`, `coeus-nn`, `coeus-optim`.
2. Reuse `pinm / pinn-rs/...` paths with `burn::prelude::*` → `coeus::{core,nn,optim,tensor,autograd}::*`.
B. Module refactoring:
1. Each `crates/kwavers-solver/src/inverse/pinn/**` (≈80 files): migrate `burn::backend::NdArray<f32>` → `coeus_core::MoiraiBackend`; `burn::module::Module` → `coeus_nn::Module`; `burn::optim::*` → `coeus_optim::*`; `burn::record::Record` → `coeus_nn::Record`; `burn::tensor::Backend` → `coeus_tensor::Tensor::from_data(..., &<MoiraiBackend as ComputeBackend>::Device)`.
2. Top-level `kwavers/{benches,examples,tests}/**` (17 files) burn-tagged: same trait rewire.
   - `benches/{adaptive_sampling_opt, pinn_elastic_2d_training, pinn_vs_fdtd_benchmark}.rs`.
   - `examples/{electromagnetic_simulation, field_surrogate_demo, multiphysics_sonoluminescence, pinn_2d_heterogeneous, pinn_2d_wave_equation, pinn_training_convergence, seismic_imaging_demo, seismic_imaging_3d_demo, skull_ct_phase_correction, transfer_learning_pinn}.rs`.
   - `tests/{electromagnetic_validation, pinn_bc_validation, pinn_elastic_validation, pinn_ic_validation}.rs`.
C. Trainer re-bind:
1. `krners-solver/src/inverse/pinn/beamforming/burn_adapter.rs` delete (Phaseburn-replacement not needed).
2. `kwavers-solvers/src/inverse/pinn/ml/{universal_solver, distributed_training, meta_learning}/...` rewrite to coeus autograd tape.
3. Migrate `burn::train::{TrainingInterruption, stop_at, checkpoint, metric::*}` patterns to coeus equivalents.
D. Top-level `kwavers/Cargo.toml:138` `[dev-dependencies] burn = ...` demoted: keep only if there’s a residual dev-only create-e-test-app that uses burn off the pinned coeus backend; else strip.
E. CHANGELOG: `[minor]` per kwavers.

**Completion condition**:
- `cargo nextest run -p kwavers-solver --features pinn` green.
- `cargo nextest run -p kwavers-solver backward` green for adjoint/PDE-residual test pipelines.
- `cargo nextest run -p kwavers top_level_pinn_examples` green for the 10 example benchhmark + 4 test slice.
- PINN trainer residual = right shape; checked against manufactured-solution PINN canonical within neum-compensated epsilon.
- `cargo tree -p kwavers-solver \| grep burn` returns zero (Burn removed from production tree).
- `cargo clippy --all-targets -- -D warnings -p kwavers-solver` green.

---

## Batch #8 — provider extension register `[minor]`

Row-by-row per `provider-extension register` in `backlog.md`:
- `lwavers` beyond scope.
- `let''O` + `let''o-ops`: lives in `repos/let''O/backlog.md`; track there.
- `moirai-async`: lives in `repos/moirai/docs/backlog.md`.
- `apollo`: lives in `repos/apollo/backlog.md`.
- `eunomia` + `eunomia-gpu`: lives in `repos/eunomia/backlog.md`.
- `coeus` + `coeus-autograd/scatter_add` etc.: lives in `repos/coeus/docs/backlog.md`.
- `hephaestus` HIGH-sev defect closure: lives in `repos/hephaestus/backlog.md`.

These are **not** a single meta-migration item; they're provider-own claims, claimable per-provider as the upstream work piece-by-piece.

---

## Per-batch atomic commit + version bump rules

Each batch follows the atomic-commit rule:
- One commit per batch (organised under the `codex/kwavers-atlas-integration` branch).
- Pre-flight gates run per `engineering_gates`:
  - `cargo fmt --check`
  - `cargo clippy --all-targets --all-features -- -D warnings`
  - `cargo nextest run`
  - `cargo test --doc`
  - `cargo doc --no-deps`
- Bump per the batch's change-class. Charged with the commit.

## In-flight claim (this checkpoint)

- Owned files (this turn): `atlas/docs/adr/0005-eunomia-scalar-ssot.md` (newly authored), `atlas/backlog.md`, `atlas/checklist.md`, `atlas/gap_audit.md` (corrected per the ADR's evidence-finding).
- Owner: `claude-codex` (current session).
- Claim start: 2026-07-04.
- Claim end: pending user sign-off on the ADR (per `versioning` policy, `[major]`/`[arch]` items require ADR sign-off pre-implementation).
- Next claim: open Batch #7 implementation checklist item (CR-4 §1 coeus-core increment) after sign-off.
- Concurrent claim stream to honor: `codex/kwavers-core-moirai-parallel` in `repos/kwavers` — disjoint scope (kwavers source); no collision.

## Residual risks (logged here per actions of `gap_audit.md`)

- T1 confirms `kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral,solver/{model_impl,rhs}, operator_splitting/mod}` aggregating ~35 sites; full file-line inventory in `gap_audit.md` per the cross-repo master.
- T1 confirms `kwavers-solver/src/inverse/same-aperture/{operator/linear_op:9 +, encoded:1}` already `moirai_parallel::ParallelSliceMut`; no Rayon created.
- T1 confirms `ritk/python.rs` `numpy::{ndarray::Array2,3,4,}` import set for Python interop only; not a migration target.

## Next micro-sprint

**Await user sign-off on `atlas/docs/adr/0005-eunomia-scalar-ssot.md`** (status **Proposed**). Once accepted, the next micro-sprint opens Batch #7 increment §1 (coeus-core `Scalar` rebase + `Complex<T>` migration per ADR §1+§2).

Branch: `codex/kwavers-atlas-integration`. Single coordinated commit for §1;#2 is a separate atomic commit; consumer-side verification (#5) and PM sync (#6) travel with their respective commits.
