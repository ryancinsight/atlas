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
> | leto `Scalar: NumericElement` rebind | `leto` | `b15439b` (`feat(scalar)!:`) on `codex/leto-cr4-ssot-rebind` | ✅ pushed (2026-07-05) |
>
> **Implementation record**: the actual NumericElement-trait shape carries `from_f64`/`from_usize` only inside `FloatElement::from_f64` and the integer `v as Self` literal-cast route — *not* on `NumericElement` itself. The §5 plan originally proposed adding `from_f64`/`from_usize` to `NumericElement`, but T1-verification at compile time proved it'd collide with `FloatElement::from_f64` (duplicate method-name resolution across super/sub-trait). The actual shipped trait surface keeps `NumericElement` constants/methods-only (`ZERO`/`ONE`/`sqrt`/`abs`/`to_f64`/`is_finite`/`is_nan`/`scalar_fmadd`/`bitand`/`bitor`/`bitxor`/`count_ones`/`min_scalar`/`max_scalar`/`BYTE_WIDTH`/`MIN_VALUE`/`MAX_VALUE`/...). The simulator-side dispatch routes floats via `<T as FloatElement>::from_f64(v)` and ints via the literal `v as Self` truncating cast.
>
> **Massive call-site rewrites landed**: ~64 coeus files received `<T as Scalar>::to_f64` / `<T as Float>::abs` / `<T as Float>::sqrt` / `<T as Float>::is_finite` qualifiers — necessary because at the SSOT-bridged surface, `T::to_f64`/`T::abs`/`T::sqrt`/`T::is_finite` resolve to multiple candidates through the `Scalar: NumericElement` path. Disambiguation is the user-confirmed scope of CR-4 because the duplication concern was the *whole point* of the rebind. Adjacent clippy `assign_op_pattern` (`acc = acc + x` → `acc += x`) was fixed in the same atomic commit so the verification gate passes — these were latent-hot-loop patterns that the SSOT rebind surfaced for clippy re-analysis.
>
> **Verified (eunomia + coeus)**: `cargo fmt --check` clean, `cargo clippy --workspace --all-targets -- -D warnings` clean (`coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor` all clippy-green), 1031 coeus nextest tests, 29 eunomia nextest tests, doctests across all crates pass, `cargo doc --no-deps` warning-clean.
>
> **2026-07-05 (CR-4 closure, `b15439b`)**: leto rebind landed on `codex/leto-cr4-ssot-rebind` and the atlas-meta submodule pointer for `repos/leto` was bumped from `21681967e` to `b15439ba` to consume the commit. Pre-push gates (recorded pre-stage on `codex/leto-cr4-ssot-rebind` working tree): 270/270 nextest `-p leto-ops` + 189/189 `-p leto` + 8 doctests + clippy `-D warnings` on `--lib --tests` scope. RG verification: zero remaining `Scalar::add|sub|mul|div|ZERO|ONE|bitand|bitor|bitxor|count_ones|to_f64` UFCS in `crates/`. Workspace version bumped `0.35.1 -> 0.36.0` (pre-1.0 `0.x.0` minor = breaking per `versioning`). Atomic commit: 5 files / 196 +/622- net deletion. CR-4 is **closed**; Batches #2/#3/#4 are unblocked (`Decision-of-Ready`), and Batch #1 (kwavers Rayon → Moirai) was sequenced before per token-batch ordering.

> **2026-07-05 (atlas-meta sync, `fb83d009`)**: `fb83d009 chore(atlas): Align submodule pointers to CR-4 eunomia/coeus/leto commits` aligned `repos/{coeus,eunomia,leto}` to the three landing SHAs (`1ae2f30c8` / `57d778930` / `21681967e`) and recorded the kwavers-foundation GPU-error-boundary rule in `README.md`. Pushed to `origin/codex/kwavers-atlas-integration`. Re-verification at the chore commit: eunomia 29/29 + coeus core-set 758/758 nextest green; clippy `-D warnings` clean on the core set; doctests pass; `cargo doc --no-deps` warn-clean.
>
> **2026-07-06 Hephaestus CUDA blocker refresh**: the `fb83d009` `coeus-wgpu` / `coeus-cuda` note is stale for the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. `eigen.rs` now converts `leto_ops::eigenvalues(&view)` results into `num_complex::Complex<f32>` before `device.upload(&e_host)`. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. This is compile/build evidence only; runtime CUDA nextest coverage remains separate.

> **## blocker ##**

> The leto `Scalar` rebind was concurrently developed in `repos/leto` working tree, but at push time `repos/leto origin/main` had diverted 47 commits ahead of the local maintainer branch (the `leto` project advanced independently through `feat/array-to-vec` PR #30 which has its own independent declaration of `Scalar` traits without the eunomia NumericElement supertrait binding). The local CR-4 `Scalar: NumericElement` rebind conflicts with that pre-published origin design — the divergent declaration of `Scalar` shapes makes a clean merge impossible at the file-`crates/leto-ops/src/domain/scalar.rs` boundary without coordination.
>
> **Resolution path** (user-decision required, NOT blocking eunomia/coeus consumer migration):
> 1. Coordinate with the author of PR #30 / `leto origin/main` — reconcile whether the SSOT-bound vs origin's stable-by-additive-change `Scalar` design wins.
> 2. If SSOT-bound: rebase leto local onto `origin/main` with a recorded migration plan for every `Scalar::add/sub/mul/div` → `NumericElement::+ operator` rewrite (the origin design declares those as required methods of `Scalar`).
> 3. If origin stable: pivot leto's CR-4 contribution to a smaller surface — re-bind only the `from_usize` constructor (the §5 original intent of `leto_ops::Scalar`) and leave the existing `add/sub/mul/div` surface as-is, with `NumericElement` added as an *additional* supertrait rather than a replacement.
>
> Filed for explicit user sign-off per `atlas/backlog.md` Item #7 (`[arch] CR-4: leto ...`).
>
> **Structural-infeasibility addendum (2026-07-05)**: T1-verified at the local session that **additive SSOT** (option (b) above) **is not rustc-acceptable**. `Scalar: NumericElement` + PR #30's pre-existing `Scalar { const ZERO: Self; const ONE: Self; fn add(); fn sub(); fn mul(); fn div(); fn from_usize(); ... }` triggers **rustc E0034 ('multiple applicable items in scope')** because `eunomia::NumericElement::ZERO`/`ONE` shadow `Scalar::ZERO`/`ONE` from the supertrait, plus `Scalar::add/sub/mul/div` and `<Self as Add<Output=Self>>::add` collide. Origin/main's trait declares those constant and method names without NumericElement in scope, so any `: NumericElement` supertrait binding concretely requires renaming either the origin/constants OR splitting `Scalar` into two traits (e.g. `Scalar: NumericElement + scalar_arith!`). Pivoting the rebind to the additive design without coordinate changes fails to compile; the resolution options (a) rebase-onto-origin and rebind with a migration plan for every `add/sub/mul/div`, OR (a-prime) propose a rename/breaking-change to PR #30's `Scalar` shape and coordinate with its author+merge. **Verify reproducible**: cargo snippet `pub trait A { const X: i32; } pub trait B: A { const X: i32; } impl A for S { const X: i32 = 1; } impl B for S { const X: i32 = 2; }` produces `error[E0034]: multiple applicable items in scope` for `Self::X` resolution inside `B`.
>
> **Resolution (a) applied 2026-07-05** (commit `b15439b` on `codex/leto-cr4-ssot-rebind`): rebind rebased onto `origin/main` post-PR-#30; `add/sub/mul/div` and `ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` removed from `Scalar` (now inherited from `NumericElement`); slice kernels rewritten to operator-syntax over `NumericElement`'s `Add`/`Sub`/`Mul`/`Div` items (`x + y`, `acc += x`, etc.); reductions converge to `<Self as NumericElement>::ZERO/abs`; `Cargo.toml` workspace version `0.35.1 -> 0.36.0`. Leto side closed; pull request ready for `ryancinsight/leto` review.

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

**Progress this slice** (resumed 2026-07-05 after CR-4 closure unblocks):
- Prior slice (2026-07-01, peer ryancinsight commits `e9f426d38`–`1f320cfe6`): replaced `Zip::indexed(...).par_for_each(...)` with `crate::parallel` helpers in:
  - `crates/kwavers-physics/src/acoustics/skull/heterogeneous/mask.rs`
  - `crates/kwavers-physics/src/acoustics/therapy/sonogenetics/membrane.rs`
  - `crates/kwavers-physics/src/acoustics/mechanics/cavitation/damage/erosion.rs`
  - `crates/kwavers-physics/src/chemistry/{reaction_kinetics,ros_plasma/ros_species}/**`, `thermal/diffusion/{bioheat,hyperbolic}.rs`, `optics/sonoluminescence/{blackbody,bremsstrahlung,cherenkov}/**`, `field_surrogate/{cube,resample}.rs` — `crate::parallel::for_each_indexed_mut` / `for_each_indexed_pair_mut` / `zip_mut_two_refs` / `zip_mut_three_refs` / `zip_mut_four_refs` / `zip_two_mut_two_refs` family.
  - `crates/kwavers-transducer/src/basic/{linear_array,matrix_array}.rs`, `transducers/focused/{arc,bowl,multi_bowl}.rs`, `transducers/phased_array/transducer.rs` — `enumerate_mut_with::<Adaptive, _, _>` direct.
  - `kwavers-core` direct Rayon edge — full Moirai migration landed in `e9f426d38`.
- **Session-window work (peer, 2026-07-05 22:16+22:19)**: `1dc47028a refactor(kwavers-math)!: Port to eunomia/leto/moirai-parallel, drop nalgebra` (8416 +/- 3734 across 131 files, includes `crates/kwavers-math` CSR + tensor + differential + simd-safe rewrite); `f36995162 refactor(kwavers-gpu, kwavers-solver)!: Generic GPU provider seam over Hephaestus`. These commits close the **`kwavers-math` migration** (separate from Batch #1) and add the GPU backend seam; they do NOT migrate `kwavers-solver`/`kwavers-physics` Rayon sites or strip the `rayon` feature from `Cargo.toml`. The peer is **actively landing adjacent scope** — Batch #1 is not stale/reclaimable; this meta layer does not initiate kwavers-source edits.
- **Baseline (reclaim verification 2026-07-05, branch tip `1f320cfe6`)**: `cargo check -p kwavers-solver --lib` finishes green in 3m09s with all Atlas dependencies (eunomia, leto, moirai-parallel, hermes, coeus, apollo-fft, ritk) resolving via submodule path; CR-4 `leto 0.36.0` (`b15439ba`) integrates cleanly. No CR-4 fallout; auto-resolution via `eunomia::NumericElement` operator items. (Newer branch tip `f36995162` adds the GPU seam and the math port; full verification on that tip is the peer's responsibility.)
- **Residual inventory (re-measured at branch tip)**: 107 `Zip::indexed(...).par_for_each(...)` / `Zip::from(...).par_for_each(...)` sites across 40 files — 31 in `kwavers-solver/src/{forward,inverse,integration,multiphysics,pstd}/**` and 9 in `kwavers-physics/src/{acoustics,optics,thermal}/**`. `kwavers-math` and `kwavers-core` are Rayon-free (zero residual). Top-density residual files: `inverse/reconstruction/seismic/rtm/inherent/imaging.rs`, `forward/elastic/swe/integration/integrator/mod.rs`, `forward/viscoacoustic/solver.rs`, `kwavers-physics/src/acoustics/mechanics/acoustic_wave/nonlinear/numerical_methods/spectral/mod.rs`, `forward/pstd/extensions/elastic_orchestrator/split_field_step/stress.rs`, `forward/nonlinear/kuznetsov/solver/rhs.rs`.
- Arities present in residual set: 1-mut + N-imm (covered by existing `zip_mut_*_refs`); 2-mut + N-imm (covered by existing `zip_two_mut_two_refs`); **3-mut + N-imm (helper gap); 4-mut + N-imm (helper gap); 6-arity mixed mut/imm indexed (helper gap)**.
- **Planned increment (peer-owned; tracked here for hand-off)**: extend `crates/kwavers-physics/src/parallel.rs` and add a parallel sibling helper module in `kwavers-solver` with `for_each_indexed_three_mut_*` / `for_each_indexed_four_mut_*` + indexed variants using `moirai-parallel::for_each_chunk_triple_mut_enumerated_with` / `for_each_chunk_quad_mut_enumerated_with` (already exposed at `src/ops.rs:335,408`). Disjoint-mut-pointer slice safety reused from existing helpers; contiguous-slice fast path + ndarray `Zip` fallback preserved as in existing patterns. Then migrate the 40 residual files mechanically. Then strip `rayon` feature from `Cargo.toml:43`, `crates/kwavers-solver/Cargo.toml:24`, `crates/kwavers-physics/Cargo.toml:20`.

**Completion condition**:

**Completion condition**:
- `cargo nextest run -p kwavers-solver -p kwavers-physics` green.
- `cargo nextest run -p kwavers-solver -p kwavers-physics fast_tests/medium_tests/slow_tests` green with no skip.
- `cargo tree -p kwavers-solver | grep rayon` returns zero.
- `cargo clippy --all-targets -- -D warnings -p kwavers-solver -p kwavers-physics` green.
- Spatial norm conservation: each migrated module's spatial-step norm within `O(N·ε)` bounded derived epsilon (reduction order). FFT/PSTD residual reductions derive Kahan-compensated epsilon per `numerical_discipline`.

---

## Batch #2 — `[minor]` CFDrs nalgebra → leto completion; nalgebra-sparse → leto-ops

> **Status (2026-07-05)**: ✅ **CLOSED**. Inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). The 185-line xtask `legacy_surface.allowlist` + 176 source files + 7 manifests of legacy `nalgebra 0.33 [serde-serialize]` / `nalgebra-sparse 0.10` / `num-traits 0.2` / `num-complex 0.4` are consumed in this commit; post-push `cargo tree -p CFDrs | grep nalgebra` returns zero production ops. Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`). See `repos/CFDrs/CHANGELOG.md` `## Unreleased` Atlas-provider migration push section.

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
3. Audit downstream consumers (kwavers-imaging, helios-imaging, ritk-cli, ritk-python) for `B: Backend` patterns; convert each bounded scope directly to `B: ComputeBackend` with no compatibility alias or Burn-shaped local wrapper.
4. Strip `RITK/Cargo.toml:69` `burn-wgpu` feature. **Closed 2026-07-06**: `repos/ritk/Cargo.toml` now keeps Burn on `std`, `ndarray`, and `autodiff` only.
5. CHANGELOG: `[minor]` per RITK; cross-link the [major] `burn remove` plan in next sprint.

**Completion condition**:
- `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation, io, model}` green.
- `cargo tree --workspace -i burn-wgpu`, `cargo tree --workspace -i burn-cuda`, and `cargo tree --workspace -i burn-rocm` each return zero; `cargo tree -p ritk -i burn-ndarray` reports only NdArray backend (`burn::backend::NdArray`) which remains a CPU reference.
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

## Per-batch Atlas-provider tag reservations (from ADR 0010 §Per-batch name pattern)

Pre-allocating the per-batch inner-repo tag names at checklist level enforces the convention shape at the time of inner-repo closure, so no per-batch re-discovers its tag-name string. Each `git tag -a <reserved-name> <inner-SHA> -m <annotation>` invocation at the batch's inner-repo closure event binds to the row below; the Atlas-parent-side pointer advance + docs-rounding + ADR-authoring commits are then stampable in lockstep.

| Batch | Class | Title | Reserved inner tag | Reserved-at | Closure status (2026-07-05) |
|-------|-------|-------|--------------------|-------------|------------------------------|
| **#2** | `[minor]` | CFDrs nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix` | `cfdrs/atlas-migration-push/batch2` | 2026-07-05 | ✅ **CLOSED** — inner commit `d58d1fe3...` on branch `codex/cfdrs-atlas-migration`; annotated tag-object SHA `8b55e6ef...` on inner CFDrs remote. Atlas-parent pointer advance `51922a56...`; docs-rounding `dd676d13`; ADR authoring `92511912`; ADR 0007 lint fix `4038a576`. |
| #1 | `[patch]` | kwavers-solver / kwavers-physics residual Rayon → Moirai | `kwavers/atlas-migration-push/batch1` | 2026-07-05 | reserved; peer-active on `repos/kwavers` `codex/kwavers-core-moirai-parallel` (last inner commit `f36995162...`). Closure still blocked on the peer's 107-Rayon-site residual inventory (`kwavers-solver` 62 sites + `kwavers-physics` 24 sites + 21 sites across forward-multiphysics) per `atlas/backlog.md` Batch #1 status line. |
| #3 | `[minor]` | ritk Burn-keyed trait rebind | `ritk/atlas-migration-push/batch3` | 2026-07-05 | reserved; `repos/ritk` `main` is now a ten-commit sequence ending at `65a1a0fd`, with this session's five-file manifest/audit-artifact follow-up closed. Closure still requires current package gates for the rebind packages; the Burn GPU-default drift is closed separately. |
| #4 | `[minor]` | kwavers-solver PINN Burn → Coeus | `kwavers/atlas-migration-push/batch4` | 2026-07-05 | reserved; depends on #3 + the `coeus-autograd/{scatter_add}` extension. Inner commit will land on `repos/kwavers` (likely the same `codex/kwavers-core-moirai-parallel` branch as #1 if concatenated, otherwise a fresh per-batch branch). |
| #5 | `[arch]` | CR-1: Apollo-ghostcell decommissioning + Melinoe `MelinoeCell` rebind | `apollo/atlas-migration-push/batch5` | 2026-07-05 | reserved; provider-side obstacle on `melinoe` brand-doctrine holder. Inner commit will land on `repos/apollo` (probable branch `refactor/apollo-fft-eunomia` per gap_audit.md peer-WIP inventory). |
| #6 | `[arch]` | CR-2: `#[global_allocator]` consolidation across `cfd-core` / `ritk-core` / `moirai` | `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` | 2026-07-05 | reserved; primary inner commit on `repos/CFDrs/crates/cfd-core` (the cfd-side first); tag annotation body enumerates the cross-repo commit chain. |

The convention shape (per ADR 0010 §Decision §"Per-batch name pattern"): **one annotated tag per batch** at inner-repo closure, anchored on the inner consumer-repo commit. Atlas-parent side gets a `chore(atlas): Advance <consumer-repo> submodule pointer to <inner-SHA>` commit + a `chore(atlas): Sync <consumer-repo>/atlas-migration-push/<N> + migration push record` docs-commit + (when applicable) an ADR authoring commit. Atlas-parent itself is the ceremony repo — **no per-batch tag on Atlas-parent**. Tag namespace reserved: `{consumer-repo}/atlas-migration-push/batch{N}` where `{N}` matches the `atlas/backlog.md` row number and `{consumer-repo}` matches the leaf consumer responsible for the migration push. Multi-repo CR-class batches (#6 above) put the tag on the primary repo (`cfd-core`) and enumerate the cross-repo commit chain in the tag annotation body.

Reference: `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` (Accepted 2026-07-05) §Decision §"Per-batch name pattern" is the source-of-truth; this checklist section is the pre-allocation tracker enforced before batch closure.

## In-flight claim (this checkpoint)

- Owned files (atlas-meta, this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root (NOT under `atlas/`); these are the cross-repo PM artifacts.
- Owner: `claude-codex` (current session).
- Atlas-meta claim start: 2026-07-04.
- Atlas-meta last landed (codex session): `5328de1c` (CR-4 closure 2026-07-05 20:27). Peer (ryancinsight) landed the Batch #2 pointer advance + sync as `51922a56` / `dd676d13` / `7a046c13` early 2026-07-06 08:14–08:21 — parent HEAD now at `dd676d13` (these were the peer's own atlas-meta commits, not codex's, recorded here for cross-session attribution). **Latest closed migration batch**: Batch #2 (CFDrs nalgebra → leto + nalgebra-sparse → leto-ops CsrMatrix) — landed in inner CFDrs as **`d58d1fe3`** on branch `codex/cfdrs-atlas-migration` (2026-07-05 23:33); Atlas-parent submodule pointer advance landed as `51922a56`.
- **This session (2026-07-06, codex):** Path C atlas-meta cleanups — (1) deleted stray 0-byte `nul` junk file at workspace root (Windows-reserved-name shell-redirect artifact, untracked, not a `target/` cache member); (2) T1 re-verification of gap_audit surfacing risks #2 and #3, both retracted as stale-memory misreads — `ritk-core` `mnemosyne-alloc` feature exists at `Cargo.toml:8`, and no `rust-toolchain*` file exists at `repos/kwavers/`; (3) closed surfacing risk #7 (ADR 0005 status bump done in `b66ec228`); (4) closed surfacing risk #1 in inner RITK commit `65a1a0fd` by removing `wgpu` from the RITK workspace Burn dependency, refreshing `xtask/burn_surface.allowlist`, and verifying the RITK dependency graph contains no `burn-wgpu`, `burn-cuda`, or `burn-rocm` package. `docs/adr/0005-eunomia-scalar-ssot.md` already at status "Accepted — implementation closed 2026-07-05"; no further doc work. `repos/themis` triaged: peripheral provider-cache single-crate, no migration relevance, left alone.
- Next claim: observation-mode; **the kwavers Batch #1 surface is peer-active** (peer ryancinsight landed `f36995162` + `1dc47028a` on 2026-07-05 22:19/22:16), so atlas-meta does not initiate kwavers-source edits. This layer remains ready to bump the `repos/kwavers` submodule pointer and sync cross-repo PM once the peer lands the Batch #1 closure.
- Concurrent claim streams to honor (per `concurrent_agents`, all disjoint from atlas-meta's scope, all DO NOT touch source): `repos/kwavers` `codex/kwavers-core-moirai-parallel` (peer ryancinsight ACTIVE — see In-flight claims in `backlog.md`); `repos/moirai` `refactor/remove-dead-subsystems` (peer, 20+ WIP files — moirai source forbidden); `repos/leto` `codex/leto-fixed-spatial-reconcile` (peer, 2 stashes + ~41 unstaged + `Cargo.toml:39` serde_json workspace-dep placeholder still breaks leto's `cargo` parse — leto source forbidden); `repos/coeus` `crates/coeus-ops/Cargo.toml` melinoe 0.7.0 → 0.8.0 uncommitted; `repos/eunomia` `crates/eunomia/src/{traits,impls/primitives,impls/wrappers}/float.rs` `acos/asin/atan` uncommitted; plus various peer claims in `repos/{apollo,CFDrs,gaia,hermes,helios,melinoe,mnemosyne,ritk,themis}`.

## Residual risks (logged here per actions of `gap_audit.md`)

- T1 confirms `kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral,solver/{model_impl,rhs}, operator_splitting/mod}` aggregating ~35 sites; full file-line inventory in `gap_audit.md` per the cross-repo master.
- T1 confirms `kwavers-solver/src/inverse/same_aperture/{operator/linear_op:9 +, encoded:1}` already `moirai_parallel::ParallelSliceMut`; no Rayon created.
- T1 confirms `ritk/python.rs` `numpy::{ndarray::Array2,3,4,}` import set for Python interop only; not a migration target.
- `hephaestus-cuda/src/application/decomposition/eigen.rs` Complex upload mismatch is stale in the checked-out `ks5-cholesky-panel` tree: `leto_ops::eigenvalues` output is converted to `num_complex::Complex<f32>` before upload, and `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` passes. Runtime CUDA nextest coverage remains unclaimed.
- Session 2026-07-05 22:19 tree-shift: peer ryancinsight landed two commits on `repos/kwavers codex/kwavers-core-moirai-parallel` while the prior atlas-meta commit (`5328de1c`) was being authored. Consequence: atlas-meta's kwavers submodule pointer (`1f320cfe6`) is now one commit behind the peer's latest (`f36995162`). Reconciliation deferred to the next Batch #1 increment commit on the kwavers side, after which the atlas-meta pointer bumps in lockstep.

## Next micro-sprint

**Observation-mode hand-off for the kwavers peer**:
- This session (2026-07-06, codex) performed Path C atlas-meta cleanups only: deleted stray `nul` artifact, retracted stale surfacing risks #2/#3, closed #7. Did NOT migrate kwavers source (peer is active) and so did NOT bump the `repos/kwavers` submodule pointer. The peer's next atomic commits to `codex/kwavers-core-moirai-parallel` continue the Batch #1 surface (help gap + 40 residual files + 3 Cargo.toml rayon strips).
- Awaiting the peer's Batch #1 closure signal (clean `cargo nextest run -p kwavers-solver --no-fail-fast` + `cargo tree -p kwavers-solver | grep rayon` empty) on a branch tip not contemporaneous with this session's pointer.
- Once the peer lands the closure or the claim goes stale (next session's check): atlas-meta bumps `repos/kwavers` pointer + closes Batch #1 entry in the in-flight section of `backlog.md`.

Branch: `codex/kwavers-atlas-integration`.
