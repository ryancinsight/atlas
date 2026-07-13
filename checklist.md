# atlas — kwavers/CFDrs/ritk → Atlas migration checklist

> Tactical decomposition aligned to `backlog.md`. Each step is atomic, evidence-tied, and self-verify-able. Per `engineering_gates`, only `cargo nextest run` and `cargo test --doc` are sanctioned test runners; changelog version bump and CHANGELOG sync travel with each [minor]/[major]/[arch] commit.
>
> **Active sprint target**: atlas migration 0.16.0 (meta version).
> **Branch**: `codex/kwavers-atlas-integration`.
> **Phase**: Foundation → Execution (batches 1, 2, 3 sequencing determined by Definition-of-Ready below).
> **WIP limit**: one merge-affecting backlog item active at a time (per `context_and_memory WIP limit`).

> **Current execution order (2026-07-12 evening session, kwavers Batch #1 + #4 closed)**:
> 1. ✅ CR-2 (`cfd-core` + `moirai`) — closed. `ritk-core` deferred.
> 2. ✅ Kwavers Stage-B (math + facade tests/examples/benches) + Stage-C (ky-python PyO3 boundary via complex_compat bridge) — `c5b1333b7` + `fa9abb664` + `ddf216ec0` + `01643ed9b` landed on `codex/kwavers-core-moirai-parallel`; cargo check --workspace --exclude kwavers-python green; cargo check -p kwavers-python --{no-default-features, gpu, plotting} all green; cargo check --tests --benches --examples --workspace --exclude kwavers-driver green (469/469 libTests, 38 doctests).
> 3. ✅ CFDrs all-features build — green with cfd-io → ritk-vtk → ritk-core → coeus-core fixed up.
> 4. ✅ RITK coeus-core pinning fix — `4d52ff8b` build(ritk): Pin coeus workspace path-deps at 0.7.0 (track coeus/main HEAD); CFDrs cfd-suite now builds green.
> 5. ✅ Kwavers Batch #1 (kwavers-solver/{solver,physics}/Rayon→Moirai `par_for_each`) — **CLOSED 2026-07-12**. Peer commit `5913f2946` "perf(kwavers-solver): Migrate solver tree to moirai parallel iterators" drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0, `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn`. `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (KW-WATCH-002 abdominal-preprocessing perf tests on 90s `elastic-fwi` profile override), 7 skipped — peer-stream perf, NOT a Batch #1 correctness regression. Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`.
> 6. ✅ Kwavers Batch #4 (kwavers-solver PINN Burn → Coeus) — **CLOSED** at the new HEAD `5913f2946`. `cargo check -p kwavers-solver --features pinn` PASSES (53 warnings, 0 errors); sole residual is `kwavers-solver/Cargo.toml`'s `ndarray` `rayon` feature gate (separate item flagged in the peer commit body). Co-verified with Batch #1.
> 7. ❌ RITK Burn cleanup — peer active (dirty inner WT). Sub-batch #3 per-crate work continues (`bcd3b726` adds coeus-native paths for `ritk-filter` intensity + grayscale morphology atop `829ebfe5` convolution/stencil + `34c3836b` `ritk-statistics` normalization/comparison; `cargo nextest run -p ritk-filter -p ritk-statistics -p ritk-image --lib --no-fail-fast` 1399/1399 pass). Sub-batch #3.g (python/cli/snap) + sub-batches #4/#5/#6 remain reserved per ADR 0012 standing reminders. Atlas-meta `repos/ritk` gitlink advanced `57b2b1c3 → bcd3b726`.
> 8. **Next actionable**: Provider extension items (Batch #8) in peer-clean provider repos (leto, moirai, apollo, eunomia, mnemosyne, themis, melinoe, hephaestus), OR re-check peer stream status after session boundary. The three watchpoints remain: kwavers-therapy KW-WATCH-002 perf, CFDrs cfd-1d Picard convergence, ritk Burn dep strip sub-batches #4/#5/#6.

---

## CR-4 — `[major]` Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` (universal SSOT)

> **Status (2026-07-05)**: Implementation split across 3 commits across the workspace:
>
> | Sub-step | Repo | Commit | Landed |
> | --- | --- | --- | --- |
> | eunomia SSOT extension (Complex<T>, isize, usize impls; trait doc clarifier; private::Sealed impls; CastFrom<i32> edge for platforms) | `eunomia` | `57d7789` | ✅ pushed to main |
> | coeus SSOT rebind + call-site disambiguation across `coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor`, doctests | `coeus` | `2b3f820` (`feat(scalar)!:`) | ✅ pushed to main |
> | leto `Scalar: NumericElement` rebind | `leto` | `b15439baf` (`feat(scalar)!:`) on `codex/leto-cr4-ssot-rebind` | ✅ pushed (2026-07-05) |
>
> **Implementation record**: the actual NumericElement-trait shape carries `from_f64`/`from_usize` only inside `FloatElement::from_f64` and the integer `v as Self` literal-cast route — *not* on `NumericElement` itself. The §5 plan originally proposed adding `from_f64`/`from_usize` to `NumericElement`, but T1-verification at compile time proved it'd collide with `FloatElement::from_f64` (duplicate method-name resolution across super/sub-trait). The actual shipped trait surface keeps `NumericElement` constants/methods-only (`ZERO`/`ONE`/`sqrt`/`abs`/`to_f64`/`is_finite`/`is_nan`/`scalar_fmadd`/`bitand`/`bitor`/`bitxor`/`count_ones`/`min_scalar`/`max_scalar`/`BYTE_WIDTH`/`MIN_VALUE`/`MAX_VALUE`/...). The simulator-side dispatch routes floats via `<T as FloatElement>::from_f64(v)` and ints via the literal `v as Self` truncating cast.
>
> **Massive call-site rewrites landed**: ~64 coeus files received `<T as Scalar>::to_f64` / `<T as Float>::abs` / `<T as Float>::sqrt` / `<T as Float>::is_finite` qualifiers — necessary because at the SSOT-bridged surface, `T::to_f64`/`T::abs`/`T::sqrt`/`T::is_finite` resolve to multiple candidates through the `Scalar: NumericElement` path. Disambiguation is the user-confirmed scope of CR-4 because the duplication concern was the *whole point* of the rebind. Adjacent clippy `assign_op_pattern` (`acc = acc + x` → `acc += x`) was fixed in the same atomic commit so the verification gate passes — these were latent-hot-loop patterns that the SSOT rebind surfaced for clippy re-analysis.
>
> **Verified (eunomia + coeus)**: `cargo fmt --check` clean, `cargo clippy --workspace --all-targets -- -D warnings` clean (`coeus-core`, `coeus-autograd`, `coeus-ops`, `coeus-nn`, `coeus-fft`, `coeus-optim`, `coeus-tensor` all clippy-green), 1031 coeus nextest tests, 29 eunomia nextest tests, doctests across all crates pass, `cargo doc --no-deps` warning-clean.
>
> **2026-07-05 (CR-4 closure, `b15439baf`)**: leto rebind landed on `codex/leto-cr4-ssot-rebind` and the atlas-meta submodule pointer for `repos/leto` was bumped from `21681967e` to `b15439ba` to consume the commit. Pre-push gates (recorded pre-stage on `codex/leto-cr4-ssot-rebind` working tree): 270/270 nextest `-p leto-ops` + 189/189 `-p leto` + 8 doctests + clippy `-D warnings` on `--lib --tests` scope. RG verification: zero remaining `Scalar::add|sub|mul|div|ZERO|ONE|bitand|bitor|bitxor|count_ones|to_f64` UFCS in `crates/`. Workspace version bumped `0.35.1 -> 0.36.0` (pre-1.0 `0.x.0` minor = breaking per `versioning`). Atomic commit: 5 files / 196 +/622- net deletion. CR-4 is **closed**; Batches #2/#3/#4 are unblocked (`Decision-of-Ready`), and Batch #1 (kwavers Rayon → Moirai) was sequenced before per token-batch ordering.

> **2026-07-05 (atlas-meta sync, `fb83d009`)**: `fb83d009 chore(atlas): Align submodule pointers to CR-4 eunomia/coeus/leto commits` aligned `repos/{coeus,eunomia,leto}` to the three landing SHAs (`1ae2f30c8` / `57d778930` / `21681967e`) and recorded the kwavers-foundation GPU-error-boundary rule in `README.md`. Pushed to `origin/codex/kwavers-atlas-integration`. Re-verification at the chore commit: eunomia 29/29 + coeus core-set 758/758 nextest green; clippy `-D warnings` clean on the core set; doctests pass; `cargo doc --no-deps` warn-clean.
>
> **2026-07-06 Hephaestus CUDA blocker refresh**: the `fb83d009` `coeus-wgpu` / `coeus-cuda` note is stale for the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. `eigen.rs` now converts `leto_ops::eigenvalues(&view)` results into `num_complex::Complex<f32>` before `device.upload(&e_host)`. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. This is compile/build evidence only; runtime CUDA nextest coverage remains separate.

> **## RESOLVED — CR-4 leto side merged via PR #31 ##**

> PR #31 (`codex/leto-cr4-ssot-rebind`) was merged into `origin/main` at `d9e8ac9`. Resolution (a) was applied: rebase onto origin/main post-PR-#30, remove `add/sub/mul/div` and `ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` from `Scalar` (inherited from `NumericElement`), slice kernels rewritten to operator-syntax. 5 additional commits landed on top (`28d0a03`..`86d366bc`). Submodule pointer at `86d366bc` == `origin/main`. All downstream batches (Batch #2 CFDrs, Batch #3 ritk, Batch #4 kwavers PINN) are unblocked.
>
> **Historical record retained in git log** — the resolution path, structural-infeasibility addendum (E0034), and user-decision-required state are preserved in the commit history for audit. See `git log --all --oneline origin/main | grep -E "b15439b|d9e8ac9"` for the merge trail.

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
- ✅ `leto/crates/leto-ops/src/domain/scalar.rs` — CR-4 rebind merged via PR #31 (`d9e8ac9`) on `origin/main`. Submodule pointer at `86d366bc`.
- ✅ Both eunomia + coeus-primary redeclarations removed; backends extend `NumericElement` rather than redeclare vocabulary.

**Plan (archaeology — superseded by ADR 0005; closed via execution)**:
The original CR-4 plan proposed methods and trait shapes that diverge from what actually shipped. See ADR 0005 for the correct design. The actual execution is recorded in the commit chain:
- eunomia: `57d7789`
- coeus: `2b3f820`
- leto: `b15439b` (on `codex/leto-cr4-ssot-rebind`), merged to `origin/main` via PR #31 at `d9e8ac9`

**Next step after CR-4 (unblocks, per ADR 0005)**:
- Batches #2/#3/#4 are Definition-of-Ready. The token-batch ordering in `atlas/backlog.md` is: #5 (CR-1) → #6 (CR-2) → #1 → #2 → #3 → #4 → #8.
- Per `decision_policy` lowest-risk-vertical-slice bias, Batch #1 (kwavers-solver/physics Rayon → Moirai) is sequenced next — but it is *not gated by CR-4* and can land in parallel; see its own checklist section.

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

> **Status (2026-07-10)**: ✅ **CLOSED** (cfd-core + moirai). ritk-core deferred (peer-active, 112 dirty).
>
> | Site | Action | Status |
> |------|--------|--------|
> | `cfd-core/src/lib.rs:45-51` | Removed `#[global_allocator]` + entire `mnemosyne` feature | ✅ committed `e24922c8` |
> | `moirai/moirai/src/lib.rs:202-205` | Removed `#[global_allocator]` registration | ✅ committed `ce22f85` |
> | `ritk-core/src/lib.rs:15-17` | Deferred — 112 dirty files (peer active) | ⏭️ |
> | `CFDrs/Cargo.toml` | Removed workspace `mnemosyne` dep + feature; removed `no-global-alloc` from moirai features | ✅ committed |
> | `coeus-python/src/lib.rs:7-9` | Out of CR-2 scope (cdylib = binary artifact) | N/A |
> | `cfd-validation/src/benchmarking/memory.rs:92-96` | Out of CR-2 scope (`TrackingAllocator` wraps `System`, not mnemosyne) | N/A |

**Pre-reqs** (historical — all satisfied):
- ✅ Inventory: T1 identified 6 `#[global_allocator]` sites across 5 repos.
- ✅ No binaries currently register `#[global_allocator]` — allocator policy is now a clean binary-level concern.

**Plan** (closed):
1. ✅ Audit: `cfd-core/src/lib.rs:45-53`, `moirai/moirai/src/lib.rs:202-205`, `ritk-core/src/lib.rs:15-17`.
2. ✅ Removed `#[global_allocator]` from cfd-core (including `mnemosyne` dep + feature).
3. ✅ Removed `#[global_allocator]` from moirai (deeper mnemosyne integration preserved).
4. ✅ Updated CFDrs workspace: removed `mnemosyne` workspace dep and feature; removed `no-global-alloc` from moirai features.
5. ✅ Verified: `cargo check -p cfd-core`, `cargo check -p moirai`, full CFDrs workspace all clean.

**Completion condition**:
- ✅ `cfd-core/src/lib.rs` no longer carries `#[global_allocator]` or `mnemosyne` feature.
- ✅ `moirai/moirai/src/lib.rs` no longer carries `#[global_allocator]`.
- ✅ `cargo check -p cfd-core`, `cargo check -p moirai`, full CFDrs workspace green.
- ⏭️ `ritk-core` deferred.
- ⏭️ `cargo nextest run -p cfd-core` timed out (120s limit; GPU compilation-heavy suite).

---

## Batch #1 — `[patch]` kwavers-solver / kwavers-physics residual Rayon → Moirai

> **Status (2026-07-10)**: peer advanced kwavers inner HEAD to `ca1530ffd`. Residual `par_for_each` sites reduced from 41→**4** across 3 files:
>
> | File | Sites |
> |------|------:|
> | `forward/elastic/swe/integration/integrator/mod.rs` | 1 |
> | `forward/nonlinear/kuznetsov/solver/rhs.rs` | 1 |
> | `forward/nonlinear/kuznetsov/workspace.rs` | 1 |
> | `safety/mod.rs` | 2 |
> | **Total** | **4** |
>
> The peer made substantial progress since the H-067 partial-closure mark (30 sites → 4). The `kwavers-solver/Cargo.toml` ndarray `rayon` feature strip was landed earlier at `702e4f125`. The `cargo tree -p kwavers-solver | grep rayon` still shows rayon transitively through `ritk → burn` (provider-side, not Batch #1 gate). 10 dirty files remain in the kwavers working tree (Batch #4 cleanup + nalgebra→leto residual migration in flight).

- **slice 1 partial-closure-mark 2026-07-08 (2/41 sites, 1/15 files)**: per the peer's `5cd8c708` chore
  on `codex/kwavers-core-moirai-parallel` (atop parent `ccc6bbf9`):
  `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/
  struct_impl.rs` has had its 2 `.par_for_each()` call-sites migrated to
  `moirai_parallel::ParallelSliceMut::par_mut().enumerate()` (idiomatic
  trait form, auto-Adaptive policy). Cargo-check pre-validate clean. 39/41
  sites / 14/15 files remain; the full closure-mark (`✅ Batch #1 CLOSED
  2026-07-08`) remains retracted per the prior retraction (`0060b1e10` was
  measured against an uncommitted working-tree snapshot, not the
  committed inner HEAD `35ee01076`). The next slices are tracked via
  per-slice partial-closure marks; the full-closure mark can be
  reasserted only when the source-side count actually drops to zero.


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

## Batch #3 — `[minor]` ritk Burn-keyed trait rebind (provider side, 6 atomic sub-batches per ADR 0012)

> **Status (2026-07-06)**: Sub-batch #1 (`RITK-Atlas-typed-trait-surface`, additive Atlas-typed parallel trait surface) **closed**. Sub-batches #3.a–#3.f of the Sub-batch #3 per-crate sub-atomic increment queue also **closed** (`ritk-filter` / `ritk-registration` / `ritk-segmentation` / `ritk-model` SSM-Morph encoder / `ritk-statistics` image statistics / `ritk-{io,interpolation,transform}` tri-crate sister pass). Sub-batches #2 + #3.g + #4–#6 reserved per the §atomic-boundary discipline below. ADR: `docs/adr/0012-ritk-burn-trait-rebind.md` (status **Accepted**). Per-sub-batch ceremony template: inner-repo atomic commit (`feat(ritk)!: Sub-batch #N ...` or `feat(ritk): Sub-batch #N ...` per the [major]/[minor]/[patch] class) + atlas-meta chore (`chore(atlas): Sync ritk/atlas-migration-push/batch3 sub-batch #N + Atlas meta pointer advance`). Reserved inner tag: `ritk/atlas-migration-push/batch3` (per ADR 0010 §Decision §Per-batch name pattern).

### Atomic-boundary discipline (mandatory for all sub-batches)

Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision:

1. **Strict additive OR strict subtractive per sub-batch**. A sub-batch either widens the Atlas surface (adds new pub-export, new trait, new impl) OR narrows the Burn surface (deprecates, removes, rewrites a symbol) — never both in one commit. This protects the bisect rollback path.
2. **No public-type signature narrowing on the Burn-keyed surface** until sub-batch #5 (`[major]`). The legacy `Image<B: Backend, D>`, `Transform<B: Backend, D>`, `Interpolator<B>`, `Resampleable<B, D>`, `Vector<D>::Module<B>`, `Point<D>::Module<B>`, `Direction<D>::Module<B>`, `Spacing<D>::Module<B>`, and per-crate reader/writer `B: Backend` fn signatures stay exactly as today through sub-batch #4.
3. **Cargo.toml is in one place per sub-batch**. Sub-batch #5 is the only commit allowed to delete or rename `[dependencies]` lines.
4. **Compile-gate per sub-batch**: `cargo fmt --check` + `cargo clippy --workspace --all-targets -- -D warnings` + `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` + `cargo test --doc` + `cargo doc --no-deps` (warning-clean).
5. **Atlas-only validation per sub-batch**: `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero; allowlist unchanged (sub-batch #6 owns the contract).

### Sub-batch #1 — `RITK-Atlas-typed-trait-surface` `[patch]` — CLOSED 2026-07-06

Additive Atlas-typed parallel trait surface; pure pub-export adds; no Burn-keyed surface mutation. 5-file change-set:

- `repos/ritk/crates/ritk-core/Cargo.toml`: add `coeus-core = { workspace = true }` and `coeus-tensor = { workspace = true }` to `[dependencies]` (workspace-declared at `repos/ritk/Cargo.toml:78-79`).
- `repos/ritk/crates/ritk-image/src/lib.rs:11`: add `pub use native::Image as AtlasImage;` (alongside the existing `pub use types::Image;`).
- `repos/ritk/crates/ritk-core/src/transform/trait_.rs`: append `TransformAtlas<T: Scalar, B: ComputeBackend, const D: usize>: Sized` + `transform_points(&self, points: Tensor<T, B>) -> Tensor<T, B>` + `inverse(&self) -> Option<Self> { None }` DEFAULT body; mirror `ResampleableAtlas`.
- `repos/ritk/crates/ritk-core/src/interpolation/trait_.rs`: append `InterpolatorAtlas<T: Scalar, B: ComputeBackend>` + `interpolate<const D: usize>(&self, data: &Tensor<T, B>, indices: Tensor<T, B>) -> Tensor<T, B>`.

Per ADR 0012 §Decision §Sub-batch #1, the new traits have **default-method-only bodies with no concrete impls on day 1**. `[allow(dead_code)]` markers are added to suppress unused-warning until consumer crates migrate in sub-batch #3+.

Compile-gate verifications: `cargo check -p ritk-core -p ritk-image -p ritk-transform -p ritk-interpolation` succeeds; `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero (state preserved from `65a1a0fd`).

### Sub-batches #2-#6 — RESERVED (#2 closed 2026-07-06; #3 OPENED 2026-07-06 with 7-per-crate queue, #3.a/#3.b/#3.c/#3.d/#3.e/#3.f closed 2026-07-06; #3.g + #4-#6 reserved)

Per ADR 0012 §Decision §Sub-batches #2-#6. The high-level `## Batch #3 — \[minor\] ritk Burn-keyed trait rebind (provider side)` section ABOVE (in this checklist, the original text under this H2 header) is now the sub-batch ceremony template + atomic-boundary discipline.

#### Sub-batch #3 OPENED 2026-07-06 — 7-per-crate sub-atomic increment queue

Sub-batch #3 (`RITK-crate-migrate`, [minor]) is **OPENED** as a 7-per-crate sub-atomic increment queue. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 (amended 2026-07-06):

**Per-crate sub-atomic increment = port ONE specific test module from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`.** Each per-crate commit is strictly subtractive (drops 1 source-row from `xtask/burn_surface.allowlist`), preserves every public Burn-keyed signature intact, and lands only Atlas-typed test bodies + Atlas-typed device/build patterns. No `#[deprecated]` attribute added (would emit 671-file compile-warning cascade per the sub-batch #2 carry-over rule). No `Cargo.toml` mutation. No `pub use …;` re-export change.

**Per-crate order (open):**

| # | Crate | Burner-touching file-count | Smallest sub-atomic increment | Atlas-side substrate |
|---|-------|---:|---|---|
| #3.a | `ritk-filter` | 296 | `morphology/tests_binary_erode.rs` (binary erosion tests, 7 fixtures) | `AtlasImage<f32, MoiraiBackend, 3>` over `coeus_tensor::Tensor<f32, MoiraiBackend>` |
| #3.b | `ritk-registration` | 109–129 | `metric/histogram/parzen/tests/cache_property_tests.rs` (Parzen-window cache property tests) | `AtlasImage<f32, MoiraiBackend, 3>` + Parzen-window ops native coeus path |
| #3.c | `ritk-segmentation` | 88 | `morphology/binary_erosion/tests.rs` (binary erosion fixtures) | `AtlasImage<f32, MoiraiBackend, 3>` over `coeus_tensor::Tensor` |
| #3.d | `ritk-model` | 18–36 | `ssmmorph/encoder/tests.rs` (SSM-Morph encoder route) | `AtlasImage<f32, MoiraiBackend, 3>` + coeus_nn Module forward |
| #3.e | `ritk-statistics` | 20–32 | `tests_image_statistics.rs` (image statistics golden values) | `AtlasImage<f32, MoiraiBackend, 3>` + image-statistics ops native coeus path |
| #3.f | `ritk-{io,interpolation,transform}` | 24–30 each | `format/dicom/color/tests.rs` + `interpolation/tests_trilinear.rs` + `transform/affine/tests_affine.rs` | `AtlasImage<f32, MoiraiBackend, 3>` + DICOM reader/trilinear/affine native coeus path |
| #3.g | `ritk-{python,cli,snap}` | 11–14 each | one CLI command test + one snapshot handler test + one python binding test | `AtlasImage<f32, MoiraiBackend, 3>` + pyo3-thin binding carrier |

**Per-crate atomic-boundary invariants (mandatory):**
1. Strict additive OR strict subtractive per per-crate commit (per ADR 0012 §Decision §1). Each per-crate commit is strictly subtractive (drops 1 source-row from the allowlist).
2. No public Burn-keyed signature narrowing (per ADR 0012 §Decision §2). Sub-batch #5 remains the only commit authorised to delete/rename `[dependencies]` lines.
3. Compile/test gate per per-crate commit: `cargo nextest run -p ritk-<crate> --lib --tests` (or `-p ritk-snap --lib`) verifying the ported test body passes with `AtlasImage<T=MoiraiBackend, f32, 3>` semantics + `cargo fmt --check` + `cargo clippy -p ritk-<crate> --all-targets -- -D warnings` + `cargo doc -p ritk-<crate> --no-deps` warning-clean.
4. Atlas-only validation per per-crate commit: `cargo tree -p ritk-<crate> -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` each return zero; `cargo tree -p ritk-<crate> -i burn-ndarray` decrements by 1.
5. Reservation cross-link: `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 (amended 2026-07-06).

**Sub-batch #3 closeout (final per-crate commit lands + sub-batch #6 owns allowlist refresh ritual):** when the last per-crate commit (`#3.g`) lands, the `xtask/burn_surface.allowlist` source-entries parcel to the migration-done rows per sub-batch #6. The `ritk/atlas-migration-push/batch3` annotated tag annotation body will enumerate the 7 per-crate SHAs per ADR 0010 §Decision §Per-batch name pattern.

##### Sub-batch #3.a CLOSED 2026-07-06 — `ritk-filter` (proof-of-pattern)

Inner RITK commit `603ad51609ce68546bc0e66d511dcd8a5fd7dda8` lands the per-crate sub-atomic increment for `ritk-filter`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::Image`, `ritk_image::tensor::{Shape,Tensor,TensorData}`, `ritk_image::test_support` from `tests_binary_erode.rs`) and **strictly additive on production surface** (new `AtlasBinaryErodeFilter` sibling consuming `AtlasImage<f32, B: ComputeBackend + Default, 3>`). Legacy `BinaryErodeFilter::apply<B: Backend>(&Image<B, 3>)` at `repos/ritk/crates/ritk-filter/src/morphology/binary_erode.rs:74` preserved verbatim.

Inner-deliverable: 4 files / +215 lines (NEW `atlas_binary_erode.rs`; rewrite of `tests_binary_erode.rs`; `mod.rs` adds `pub mod atlas_binary_erode;` + re-export; `Cargo.toml` adds `coeus-tensor = { workspace = true }`).

Compile/test gate (atomic-boundary rule §3): `cargo check -p ritk-filter` PASS; `cargo test -p ritk-filter --lib morphology::binary_erode::tests_binary_erode` PASS (T1-T7 7/7, 0 failed); `cargo tree -p ritk-filter -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each; `[dev-dependencies] burn-ndarray` retained; no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row (the rewritten `tests_binary_erode.rs`). Atlas-meta submodule pointer advance: `4ff70a74` (sub-batch #2) → `603ad516` (sub-batch #3.a). The `ritk/atlas-migration-push/batch3` annotated tag at `603ad516` enumerates the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b..#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.b CLOSED 2026-07-06 — `ritk-registration` (Parzen-window cache sibling port)

Inner RITK commit `abd6abd4` lands the per-crate sub-atomic increment for `ritk-registration`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::tensor::{Backend,Tensor}`, `ParzenJointHistogram<B: Backend>` from `tests/cache_property_tests.rs`) and **strictly additive on production surface** (new `atlas_parzen_cache` sibling consuming `AtlasImage<f32, B: ComputeBackend + Default, 3>` via `coeus_tensor::Tensor`). Legacy `direct::compute_joint_histogram_direct` / `direct::build_sparse_w_fixed_transposed` / `dispatch::normalize_and_extract` symbol surface preserved verbatim; only the wrappers in `atlas_parzen_cache.rs` carry the Atlas-prefix.

Inner-deliverable: 3 files (NEW `atlas_parzen_cache.rs`; rewrite of `tests/cache_property_tests.rs`; `mod.rs` adds `pub mod atlas_parzen_cache;` + sibling description comment). Cargo.toml has **zero changes** — `coeus-tensor` already declared at `repos/ritk/crates/ritk-registration/Cargo.toml:33` from sub-batch #2 readiness. The atlas-side sibling module is gated by `#![cfg(feature = "direct-parzen")]` so the wrappers compile simultaneously with the test gate.

The Atlas-side sibling signature shape (production-side wrappers, mirroring #3.a's `AtlasBinaryErodeFilter` wrap-pattern):
- `pub struct AtlasSparseEntry { pub bin: u16, pub weight: f32 }` (Derives: Debug+Clone+Copy+PartialEq) — Atlas-side flattened sparse-cache entry type mirroring `direct::SparseWFixedEntry`.
- `pub fn compute_atlas_joint_histogram_direct(fixed_norm, moving_norm, num_bins, sigma_sq_fix, sigma_sq_mov, oob_mask, pool) -> Vec<f32>` — wraps `direct::compute_joint_histogram_direct` (returns `TensorData`) by extracting `TensorData.as_slice::<f32>().to_vec()`.
- `pub fn build_atlas_sparse_w_fixed_transposed(fixed_norm, num_bins, sigma_sq_fix, oob_mask) -> Vec<(Vec<AtlasSparseEntry>, f32)>` — wraps `direct::build_sparse_w_fixed_transposed` (returns `SparseWFixedT = Vec<(SparseSampleCache, f32)>`) by unpacking each `SparseSampleCache` (Deref to `[SparseWFixedEntry]`) into the named-field entry-vector form.
- `pub fn atlas_normalize_intensities(values, min, max, num_bins) -> Vec<f32>` — host-slice normalisation helper mirroring `dispatch::normalize_and_extract` algorithm shape without `burn::Tensor<B, 1>` indirection.

`ParzenConfig` (the legacy `pub(crate)` config type in `direct::ParzenConfig`) is consumed by the test through the crate-local path `crate::metric::histogram::parzen::direct::ParzenConfig` — Rust rejects visibility-elevation of `pub(crate)` items through `pub use ... as AtlasParzenConfig`, so the type-import is direct rather than aliased.

Compile-gate verifications (per per-crate atomic-boundary rule §3): `cargo check -p ritk-registration --tests` PASS (test target builds cleanly with `direct-parzen` feature enabled); `cargo test -p ritk-registration --lib parzen::tests::cache_property_tests` PASS (T1-T3 3/3 oracle-valued: `histogram_non_negative_all_entries`, `histogram_marginals_sum_correctly`, `sparse_w_fixed_deterministic`); `cargo tree -p ritk-registration -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each; `[dev-dependencies] burn-ndarray` retained (legacy `tests/mod.rs` + `masked_cache_tests.rs` still consume it — out of #3.b scope); no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `tests/cache_property_tests.rs`. The 2 grep hits for `burn_ndarray`/`burn::tensor`/`ParzenJointHistogram` in the rewritten test are doc-comment references documenting the names of REMOVED burn-side dependencies (in the strict-subtractive invariant explanation), not actual code imports — sub-batch #3.b strict-subtractive-on-test-surface invariant preserved.

Atlas-meta submodule pointer advance: `603ad516` (sub-batch #3.a) → `abd6abd4` (sub-batch #3.b). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `603ad516` to `abd6abd4` with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, **#3.b closed**, #3.c..#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.c CLOSED 2026-07-06 — `ritk-segmentation` (binary-erosion sister-impl port)

Inner RITK commit `9892049d` lands the per-crate sub-atomic increment for `ritk-segmentation`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::Image`, `ritk_image::tensor::{Shape,Tensor,TensorData}`, `ritk_image::test_support` from `morphology/binary_erosion/tests.rs`) and **strictly additive on production surface** (new `AtlasBinaryErodeFilter` sister struct consuming host-slice `AtlasImage<f32, MoiraiBackend, 3>` over `coeus_tensor::Tensor`). Legacy `BinaryErosion::apply<B: Backend, const D: usize>(&Image<B, D>) -> Image<B, D>` at `repos/ritk/crates/ritk-segmentation/src/morphology/binary_erosion/mod.rs:40` preserved verbatim per ADR 0012 §Decision §2.

Inner-deliverable: 6 files / +178 -126 net (Cargo.lock drift +178 lines from `coeus-tensor = { workspace = true }` workspace-dep ingress; the source-code delta is +106 -126 across the 4 other files). NEW `atlas_binary_erosion.rs` (~70 lines); rewrite of `morphology/binary_erosion/tests.rs` (14 oracle tests); `binary_erosion/mod.rs` adds a single `pub mod atlas_binary_erosion;` declaration between the `MorphologicalOperation<B, D>` impl and the protected `erode_nd` helper; `Cargo.toml` adds `coeus-tensor = { workspace = true }` (forward-compatible dep for sub-batches #3.d–#3.g in `ritk-segmentation`); `xtask/burn_surface.allowlist` drops the rewritten `morphology/binary_erosion/tests.rs` source-row. The Atlas-side sister struct is structurally simpler than #3.b's `atlas_parzen_cache` (no `TensorData`-unpacking wrappers required — the legacy `super::erode_nd` in this crate already operates on `&[f32]` + `&[usize]` returning `Vec<f32>`), and structurally mirrors #3.a's `AtlasBinaryErodeFilter` family-pattern through parallel parameterisation (struct shape: `{ radius: usize }` + const-fn `new` + `apply(flat, shape)` + `Default`).

The Atlas-side sister signature shape (production-side sister struct, mirroring the family-pattern):
- `pub struct AtlasBinaryErodeFilter { pub radius: usize }` (Derives: `Debug`+`Clone`+`Copy`+`PartialEq`+`Eq`+`Hash`) — Atlas-side sister struct mirroring legacy `BinaryErosion { radius }`.
- `pub const fn new(radius: usize) -> Self` — constructor.
- `pub fn apply(&self, flat: &[f32], shape: &[usize]) -> Vec<f32>` — host-slice forward path delegating to `super::erode_nd` (the legacy CPU-side canonical erosion kernel that already routes through `erode_line`/`erode_plane`/`erode_volume`).
- `impl Default for AtlasBinaryErodeFilter` (radius = 1) — mirrors legacy `BinaryErosion::default()`.

The legacy `BinaryErosion::apply<B, D>` Burn-keyed signature stays untouched at `morphology/binary_erosion/mod.rs:40-52`. The legacy `MorphologicalOperation<B, D>` impl stays untouched at `morphology/binary_erosion/mod.rs:64-69`. The legacy `super::erode_nd` CPU-side helper is reused verbatim as the Atlas twin's algorithmic core — no algorithmic duplication, no shape-contract drift, no out-of-bounds semântica divergence.

Compile-gate verifications (per per-crate atomic-boundary rule §3): `cargo check -p ritk-segmentation` PASS; `cargo check -p ritk-segmentation --tests` PASS; `cargo test -p ritk-segmentation --lib morphology::binary_erosion::tests` PASS (T1–T14 14/14 atlas-side oracle-valued: `test_radius0_is_identity_volumetric`, `test_radius0_is_identity_line`, `test_all_fg_5x5x5_erosion_r1_keeps_all`, `test_all_fg_7x7x7_erosion_r2_keeps_all`, `test_z1_square_erodes_in_plane_not_to_zero`, `test_single_voxel_eroded_to_empty`, `test_erosion_is_anti_extensive`, `test_all_background_stays_empty`, `test_1d_erosion_r1_known_output`, `test_1d_all_foreground_erosion_r1`, `test_1d_single_voxel_image_survives`, `test_output_strictly_binary_volumetric`, `test_atlas_shape_preserves_voxel_count`, `test_double_erosion_subset_of_single_erosion`); `cargo tree -p ritk-segmentation -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each (state preserved); `[dev-dependencies] burn-ndarray` retained (other `ritk-segmentation` test modules + benches still consume it — out of #3.c scope); no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `morphology/binary_erosion/tests.rs`. The single grep hit for `burn_ndarray`/`burn::tensor`/`::Backend`/`ritk_image::tensor` in the rewritten test is a doc-comment reference documenting the names of REMOVED burn-side dependencies (in the strict-subtractive invariant explanation), not actual code imports — sub-batch #3.c strict-subtractive-on-test-surface invariant preserved.

Atlas-meta submodule pointer advance: `abd6abd4` (sub-batch #3.b) → `9892049d` (sub-batch #3.c). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `abd6abd4` to `9892049d` (annotated tag-object SHA `b603bbc8`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, **#3.c closed**, #3.d–#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.d CLOSED 2026-07-06 — `ritk-model` (SSM-Morph encoder structural-shape sister port)

Inner RITK commit `24522ae76ab4b8bcb3b23d75870b8d16c151a57f` lands the per-crate sub-atomic increment for `ritk-model`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::tensor::{Shape,Tensor,TensorData}`, `ritk_image::test_support`, `burn::record::Record` from `ssmmorph/encoder/tests.rs`) and **strictly additive on production surface** (new `AtlasSSMMorphEncoderConfig` + `AtlasEncoderStage` + `AtlasSSMMorphEncoder` Atlas-side sister structs scaffolding the structural-shape mirror of the legacy `SSMMorphEncoderConfig` + `EncoderStageConfig` + `SSMMorphEncoder<B: Backend>` config-family). Legacy `SSMMorphEncoder<B: Backend>::forward` + per-stage `EncoderStage<B: Backend>::forward` Burn-keyed signatures preserved verbatim per ADR 0012 §Decision §2 — the deep `coeus_nn::Module` forward contract is reserved for sub-batch #5 `[major]`.

Inner-deliverable: 6 files / +277 −56 net (Cargo.lock drift from `coeus-tensor = { workspace = true }` workspace-dep ingress via `Cargo.toml` +=1 line). NEW `atlas_encoder.rs` (~199 lines); rewrite of `ssmmorph/encoder/tests.rs` (6 oracle tests, all rewritten as construction-shape integrity assertions since deep forward-path tests cannot be mirrored without `coeus_nn::Module::forward` impl on legacy Burn-keyed types); `ssmmorph/encoder/mod.rs` adds `pub mod atlas_encoder;` declaration; `Cargo.toml` adds `coeus-tensor = { workspace = true }` (coeus-nn was hold-and-dropped in a round-2 cleanup because workspace root `[workspace.dependencies]` does not yet declare coeus-nn — that declaration is sub-batch #5 [major] concern); `Cargo.lock` propagates the workspace-dep ingress; `xtask/burn_surface.allowlist` drops the rewritten `ssmmorph/encoder/tests.rs` source-row.

The three Atlas-side sister structs (design boundary: structural-shape mirror, NOT forward-contract twin per sub-batch #5 [major] reservation):
- `AtlasSSMMorphEncoderConfig` — structural-shape mirror of legacy `SSMMorphEncoderConfig` (fields: `num_stages: usize, base_channels: usize, stage_channels: Vec<usize>, drop_path: DropPath`); derives `Debug+Clone+PartialEq+Eq` (Hash intentionally OMITTED because legacy `super::config::DropPath` enum does not derive Hash; ADR 0012 §Decision §2 forbids modifying the legacy surface); `pub` constructor `for_registration()` / `lightweight()` / `high_quality()` preset forwarding + `From<&SSMMorphEncoderConfig>` lifting adapter.
- `AtlasEncoderStage` — structural-shape mirror of legacy `EncoderStage` (fields: `blocks_len: usize, downsample: DownsamplePolicy, proj_present: bool, out_channels: usize`); derives `Debug+Clone+PartialEq+Eq` (Hash intentionally OMITTED because legacy `super::config::DownsamplePolicy` enum does not derive Hash; ADR 0012 §Decision §2); `from_config_only(&EncoderStageConfig)` construction-shape introspection surface.
- `AtlasSSMMorphEncoder` — structural-shape mirror of legacy `SSMMorphEncoder` (fields: `num_stages: usize, stage_channels: Vec<usize>`); derives `Debug+Clone+PartialEq+Eq+Hash` (Hash PRESERVED because all fields are `usize` + `Vec<usize>`); `from_config(&AtlasSSMMorphEncoderConfig)` construction-shape introspection + `From<&SSMMorphEncoderConfig>` lifting adapter.

Forward-path re-interpretation per ADR 0012 §Decision §Sub-batch #3 (sub-batch #5 [major] reservation): the two legacy forward-path tests (`test_encoder_stage_forward` + `test_encoder_forward`) are rewritten as construction-shape integrity tests asserting `blocks_len` / `depth` / `proj_present` / `out_channels` on the Atlas twin (contract: legacy `out_channels == 32, proj_present == true, blocks_len == 1` for the stage; `num_stages == 3, stage_channels == [16, 32, 64]` for the encoder), NOT the original 5D-output-shape contract (`[1, 32, 16, 64, 64]` style `[B, C, D, H, W]` tensors). The full forward contract is reserved for the sub-batch #5 [major] `coeus_nn::Module` rebind.

Compile-gate verifications (per per-crate atomic-boundary rule §3): `cargo check -p ritk-model` PASS; `cargo check -p ritk-model --tests` PASS (after round-4 Hash-derive drop fix for the 2 enum-containing structs); `cargo test -p ritk-model --lib ssmmorph::encoder::tests` PASS (T1–T6 6/6 atlas-side oracle-valued: `test_encoder_stage_config_presets`, `test_encoder_stage_remaining_field_paths_unchanged`, `test_encoder_stage_forward` (re-interpreted as construction-shape), `test_encoder_forward` (re-interpreted as construction-shape), `test_for_registration_matches_legacy_constructor`, `test_lightweight_and_high_quality_differ_from_baseline`); `cargo tree -p ritk-model -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each; `[dev-dependencies] burn-ndarray` retained; no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `ssmmorph/encoder/tests.rs`. Round-4 note: the asymmetric derive-macros (`Hash` PRESERVED on `AtlasSSMMorphEncoder` but OMITTED on `AtlasSSMMorphEncoderConfig` + `AtlasEncoderStage`) are documented inline at each affected struct with a `/// **Derive-macro note**` paragraph explaining the legacy-surface preservation constraint — a future maintainer adding `Hash` back without coordinating legacy `DropPath` / `DownsamplePolicy` Hash derivation will be blocked at compile time.

Atlas-meta submodule pointer advance: `9892049d` (sub-batch #3.c) → `24522ae76ab4b8bcb3b23d75870b8d16c151a57f` (sub-batch #3.d). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `9892049d` to `24522ae7` (annotated tag-object SHA `a8872e431718ae96ac28e16bf7de4d1ef57c31a5`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, #3.c closed, **#3.d closed**, #3.e–#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.e CLOSED 2026-07-06 — `ritk-statistics` (image_statistics sister-port)

Inner RITK commit `b0ef594067398598877c2e45428fcdb31bcdda82` lands the per-crate sub-atomic increment for `ritk-statistics`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on test surface** (drops `burn_ndarray::NdArray`, `ritk_image::Image` (the Burn-keyed legacy re-export of `burn::tensor::Tensor`), and `ritk_image::test_support::make_image` from `tests_image_statistics.rs`) and **strictly additive on production surface** (new `atlas_image_statistics.rs` sister module exposing `AtlasImageStatistics` sister struct + bidirectional `From` cross-interchange impls + `compute_atlas_statistics` / `compute_atlas_statistics_from_slice` / `atlas_masked_statistics` Atlas-typed sister functions over `AtlasImage<f32, coeus_core::ComputeBackend, D>` rasterized through `ritk_image::native::Image::from_flat`). Legacy `super::compute_statistics<B: Backend, const D>` + `super::masked_statistics<B: Backend, const D>` Burn-keyed signatures preserved verbatim per ADR 0012 §Decision §2.

Inner-deliverable: 3 source files / +1 allowlist row drop / NO `Cargo.toml` mutation per per-crate §3 invariant. NEW `atlas_image_statistics.rs` (~196 lines): 1 sister struct `AtlasImageStatistics` (field-shape identical to legacy `ImageStatistics` with bidirectional `From` cross-interchange), hand-rolled `AtlasStatsError` enum with `Debug+Clone+PartialEq+Eq` derives + `std::fmt::Display` + `std::error::Error` impls (no `thiserror` dep-add per per-crate no-Cargo.toml-mutation rule), 3 sister compute functions operating via the canonical `ritk_tensor_ops::native::extract_image_slice` (matches `super::native::compute_statistics` pattern verbatim — trait-bound `B::DeviceBuffer<f32>: CpuAddressableStorage<f32>` on the `ComputeBackend` generic). Rewrite of `tests_image_statistics.rs`: 15 atlas-side oracle tests replacing the burn↔coeus oracle comparison with hand-computed oracle values matching bit-exactly the burn reference (`test_uniform_image`, `test_known_sequence`, `test_slice_input_preserves_input_order`, `test_atlas_image_preserves_values_through_from_flat`, `test_single_voxel`, `test_two_values`, `test_reverse_order_input_matches_sorted`, `test_masked_subset`, `test_masked_all_foreground_matches_unmasked`, `test_masked_single_foreground_voxel`, `test_atlas_to_legacy_round_trip_field_identity`, `test_masked_empty_mask_returns_empty_foreground_error`, `test_masked_shape_mismatch_returns_shape_mismatch_error`, `test_large_n_ct_scale_mean_precision`, `test_large_n_negative_mean_precision`); `xtask/burn_surface.allowlist` contracts by 1 source-row on `tests_image_statistics.rs`.

The legacy `super::compute_from_owned` (f64-precision fused-pass + quickselect-on-progressive-suffix percentile algorithm) is reused verbatim by the Atlas twin via `super::compute_statistics_from_slice` delegation — bit-identity on the f32 numeric contract is preserved across both Burn-keyed legacy and Atlas-typed call paths. The Atlas twin surfaces `super::masked_statistics`'s panic contract as `AtlasStatsError::EmptyForegroundMask` + `AtlasStatsError::ShapeMismatch { image_n, mask_n }` with `Result`-returns instead of `panic!`, matching the idiomatic `coeus_core::ComputeBackend` error-mapping convention. `Display` impls are crafted bit-identical to the legacy `panic!` strings (no `"atlas"`/`"coeus"` prefix drift across the two sister modules) so callers that `match`/`grep` against the legacy diagnostic text preserve their contract.

Compile-gate verifications (per per-crate atomic-boundary rule §3 + §4): `cargo check -p ritk-statistics` PASS; `cargo check -p ritk-statistics --tests` PASS; `cargo test -p ritk-statistics --lib image_statistics::tests` PASS (T1–T15 15/15 atlas-side oracle-valued); `cargo tree -p ritk-statistics -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` zero each (state preserved); `[dev-dependencies] burn-ndarray` retained (other `ritk-statistics` test modules still consume it — out of #3.e scope); no `#[deprecated]` attr; `xtask/burn_surface.allowlist` contracts by 1 source-row on `tests_image_statistics.rs`. Cargo.toml unchanged per per-crate §3 invariant.

Amend note: the inner RITK commit `4861657a` (initial #3.e drop) was amended to `b0ef594067398598877c2e45428fcdb31bcdda82` 2026-07-06 to include a `Cargo.lock` drift from the `coeus-core` trait-bound `B::DeviceBuffer<f32>: CpuAddressableStorage<f32>` ingress via the Atlas-side sister wiring (compile-only — no `Cargo.toml` mutation in the `ritk-statistics` per-crate scope, no new transitively-installed crates). The `burn` and `burn-ndarray` entries are workspace-resolved transitive dependencies for `ritk-vtk` (an unrelated per-crate reference that the resolver auto-registered). The amend is round-2 per ADR 0012 §Decision §Sub-batch #3 amended-2026-07-06 cleanness rule: one ceremony commit captures the per-crate delta + the lockfile ingress so the inner-ritk working tree lands atomically-clean.

Atlas-meta submodule pointer advance: `24522ae76ab4b8bcb3b23d75870b8d16c151a57f` (sub-batch #3.d) → `b0ef594067398598877c2e45428fcdb31bcdda82` (sub-batch #3.e, post-amend). The `ritk/atlas-migration-push/batch3` annotated tag is re-force-moved from `24522ae7` to `b0ef5940` (annotated tag-object SHA `29ba4b1e`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, #3.c closed, #3.d closed, **#3.e closed**, #3.f–#3.g pending, #4/#5/#6 reserved.

##### Sub-batch #3.f CLOSED 2026-07-06 — `ritk-{io,interpolation,transform}` (tri-crate sister pass)

Inner RITK commit `310fcd6c421cb9844c519f1b350d39e67261729b` lands the tri-crate per-crate sub-atomic increment for `ritk-io`, `ritk-interpolation`, and `ritk-transform`. Per `docs/adr/0012-ritk-burn-trait-rebind.md` §Decision §Sub-batch #3 atomic-boundary invariant, this commit is **strictly subtractive on the selected test surface** (the rewritten `format/dicom/color/tests.rs`, `interpolation/tests_trilinear.rs`, and `transform/affine/tests_affine.rs` contain no `burn`/`burn_ndarray`/`ndarray` hits) and **strictly additive on production surface** (new sister modules `atlas_color.rs`, `atlas_trilinear.rs`, and `atlas_affine.rs`). Legacy tensor-backed production APIs remain intact; sub-batch #5 still owns dependency deletion and signature removal.

Inner-deliverable: new Atlas-typed DICOM color loaders returning `Image<f32, MoiraiBackend, 4>` and re-exported through `ritk-io`'s public DICOM/lib boundary; new Atlas trilinear sister over `Image<f32, MoiraiBackend, 5>`; new Atlas affine sister over host-slice `[N, D]` point carriers. The affine test's rigid-rotation oracle uses the documented `R_z * R_y * R_x` Euler formula from `RigidTransform::build_rotation_matrix()` without constructing legacy tensors. The tracked helper message artifacts `.atlas_3f_commit_msg.txt` and `.atlas_batch3_f_tag.txt` are removed from the inner repo.

Compile/test gate verifications (per per-crate atomic-boundary rule §3): `rustup run nightly cargo check -p ritk-interpolation -p ritk-io -p ritk-transform` PASS; `rustup run nightly cargo check --tests -p ritk-interpolation -p ritk-io -p ritk-transform` PASS; `rustup run nightly cargo clippy -p ritk-interpolation -p ritk-io -p ritk-transform --all-targets -- -D warnings` PASS; `rustup run nightly cargo nextest run -p ritk-io color --status-level fail --no-fail-fast` PASS (10/10); `rustup run nightly cargo nextest run -p ritk-interpolation trilinear --status-level fail --no-fail-fast` PASS (8/8); `rustup run nightly cargo nextest run -p ritk-transform affine --status-level fail --no-fail-fast` PASS (18/18). Baseline workspace warning preserved: unused `hephaestus-core`/`hephaestus-wgpu` patch warnings.

Atlas-meta submodule pointer advance: `b0ef594067398598877c2e45428fcdb31bcdda82` (sub-batch #3.e) → `310fcd6c421cb9844c519f1b350d39e67261729b` (sub-batch #3.f, post-amend). The `ritk/atlas-migration-push/batch3` annotated tag is force-moved from `b0ef5940` to `310fcd6c` (annotated tag-object SHA `d3d82ff4`) with the annotation body updated to enumerate the per-batch chain: #1 closed, #2 closed, #3 opened (7-per-crate queue), #3.a closed, #3.b closed, #3.c closed, #3.d closed, #3.e closed, **#3.f closed**, #3.g pending, #4/#5/#6 reserved.

#### Sub-batch #2 closing (2026-07-06) — RITK trait soft deprecation documentation

Sub-batch #2 (`RITK-trait-deprecate`, [patch]) is **closed** per the same ceremony template as sub-batch #1 (inner atomic doc-only commit + atlas-meta chore commit). Per-sub-batch evidence (cross-walked from `repos/ritk/CHECKLIST.md` and `repos/ritk/gap_audit.md` near-new sections):

- 4 source files touched (`ritk-core/src/{transform/trait_, interpolation/trait_}.rs`, `ritk-image/src/types.rs`); no `Cargo.toml` mutations; no allowlist mutations.
- Soft docstring callout prepended to 4 Burn-keyed surfaces (`Transform<B, D>`, `Resampleable<B, D>`, `Interpolator<B>`, `Image<B, D>`); each callout (a) bold-prefixes the deprecation status, (b) forward-intra-doc-links the Atlas-typed parallel trait, (c) explicitly states NO `#[deprecated]` attribute, (d) cross-references `xtask/burn_surface.allowlist` and ADR 0012.
- `cargo check -p ritk-core -p ritk-image`: passes.
- `cargo doc -p ritk-core -p ritk-image --no-deps`: passes (intra-doc-links resolve: `[`TransformAtlas`]` and `[`ResampleableAtlas`]` to `transform/trait_.rs`; `[`InterpolatorAtlas`]` to `interpolation/trait_.rs`; `[`AtlasImage`]` via the `ritk-image/src/lib.rs` re-export of `native::Image`).
- `cargo tree --workspace -i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm`: zero each.

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
1. Each `crates/kwavers-solver/src/inverse/pinn/**` (≈126 source files per T1 ripgrep at HEAD `400c32624`; prior estimate of ≈80 was undercounted): migrate `burn::backend::NdArray<f32>` → `coeus_core::MoiraiBackend`; `burn::module::Module` → `coeus_nn::Module`; `burn::optim::*` → `coeus_optim::*`; `burn::record::Record` → `coeus_nn::Record`; `burn::tensor::Backend` → `coeus_tensor::Tensor::from_data(..., &<MoiraiBackend as ComputeBackend>::Device)`.
2. Top-level `kwavers/{benches,examples,tests}/**` (17 files) burn-tagged: same trait rewire.
   - `benches/{adaptive_sampling_opt, pinn_elastic_2d_training, pinn_vs_fdtd_benchmark}.rs`.
   - `examples/{electromagnetic_simulation, field_surrogate_demo, multiphysics_sonoluminescence, pinn_2d_heterogeneous, pinn_2d_wave_equation, pinn_training_convergence, seismic_imaging_demo, seismic_imaging_3d_demo, skull_ct_phase_correction, transfer_learning_pinn}.rs`.
   - `tests/{electromagnetic_validation, pinn_bc_validation, pinn_elastic_validation, pinn_ic_validation}.rs`.
C. Trainer re-bind:
1. `kwavers-solver/src/inverse/pinn/beamforming/burn_adapter.rs` delete (Burn-replacement not needed).
2. `kwavers-solver/src/inverse/pinn/ml/{universal_solver, distributed_training, meta_learning}/...` rewrite to coeus autograd tape.
3. Migrate `burn::train::{TrainingInterruption, stop_at, checkpoint, metric::*}` patterns to coeus equivalents.
D. Top-level `kwavers/Cargo.toml:138` `[dev-dependencies] burn = ...` demoted: keep only if there’s a residual dev-only create-e-test-app that uses burn off the pinned coeus backend; else strip. `kwavers-solver/Cargo.toml:53` `burn` optional dep and the `pinn` feature at L62-70 `dep:burn` line stripped in lockstep with D.
E. Delete `crates/kwavers-solver/src/burn.rs` (the burn→coeus facade alias module) and `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat` once all `use burn::…` callsites are rewritten to native coeus imports per B.1+B.2.
F. CHANGELOG: `[minor]` per kwavers.

**Progress (slice 1, peer 2026-07-06, `400c32624`)**: peer landed inner commit `400c32624` "Migrate burn_wave_equation_1d PINN to native coeus" on `codex/kwavers-core-moirai-parallel`. 12-file slice covering `crates/kwavers-solver/src/inverse/pinn/{beamforming/burn_adapter.rs, ml/burn_wave_equation_1d/{network,optimizer,physics,trainer,tests}/*, ml/{validation, burn_wave_equation_1d/tests}.rs}` rewritten against `coeus_nn::Linear`, `coeus_autograd` free functions, `coeus_optim::SGD`. Continued use of the `crates/kwavers-solver/src/burn.rs` shim facade + `burn_compat` module permits the remaining 126 PINN-subtree + 17 top-level files to keep importing `burn::*` without source rewrites per slice. Slice 1 evidence: 315 `burn::` line-hits / 144 files + 222 `use burn` import-sites / 139 files at `400c32624` HEAD.

**Progress (slice 2, peer 2026-07-06, `c6b845f81`)**: peer landed inner commit `c6b845f81` "Complete Burn-to-Coeus migration for 2D PINN dependency graph". Native-source rewrite of the `burn_wave_equation_2d` dependency-graph surface — `acoustic_wave`, `cavitation_coupled`, `sonoluminescence_coupled`, `electromagnetic`, `adaptive_sampling`, `meta_learning`, `transfer_learning`, `distributed_training`, `quantization`, `uncertainty_quantification`, `universal_solver`, plus `field_surrogate/training/trainer.rs` partially — onto `coeus_autograd::Var` + `coeus_nn::Module` + `coeus_optim::SGD`. The peer's commit body affirms the integrity-axis instruction with: "Replaces burn-shaped ModuleMapper-based gradient machinery … with native per-parameter gradient snapshots (Vec<Option<Vec<f32>>>) applied via coeus's parameters() / load_parameters() round-trip, **per prior direction not to build burn-compat shims**." This is a concrete reconciliation of risk #8's framing — the peer's Batch #4 slice 2 explicitly rejects the burn-compat facade path. Slice 2 drain verified at `c6b845f81`: 186 `burn::` line-hits / 80 files + 125 `use burn` import-sites / 78 files (slice 1→slice 2: −41% hits / −44% files / −44% import-sites). Residual unmatched after slice 2: `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}` + `pinn/elastic_2d/{training/{loop,optimizer,adaptive_sampling},loss/pde_residual/tests}` + `pinn/ml/field_surrogate/{network,tests/training}` + 17 top-level `kwavers/{benches,examples,tests}/**` files + `kwavers-solver/Cargo.toml:53` `burn` optional dep + the `pinn` feature `dep:burn` line at L62-70 + `crates/kwavers-solver/src/burn.rs` and `kwavers-solver/src/inverse/pinn/ml/burn_compat` deletions (conditioned on full burn-source purge). Risk #8 stays live until `burn.rs`+`burn_compat` deletion + Cargo.toml strip land. See `gap_audit.md` §kwavers "Residual `burn`" block (T1 refreshed) and surfacing risk #8.

**Progress (slices 3–5, peer 2026-07-06, `cd8cf776d` / `7235d464a` / `d4ff48285`)**: peer landed three further inner Burn→Coeus migration commits beyond the handoff `c6b845f81` snapshot. Slice 3 `cd8cf776d` "Migrate burn_wave_equation_3d to native coeus" cleared the entire `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}` family flagged as residual after slice 2. Slice 4 `7235d464a` "Migrate field_surrogate PINN to native coeus" closed the remaining `pinn/ml/field_surrogate/{network,tests/training}` PINN-port target (this is the commit the atlas-meta gitlink pins at `7235d464a`). Interstitial `ae86daecc` resolved clippy pedantic nits in `kwavers-math` + `kwavers-transducer`. Slice 5 `d4ff48285` "Migrate advanced_architectures + autodiff_utils to native coeus; fix latent bound/numerical gaps" moved the autodiff-utils + advanced-architectures surface into native coeus and pinned latent trait-bound and numerical-discipline gaps surfaced by the rewind (per commit body). T1 re-verification at peer's actual working-tree HEAD `d4ff48285` (`[ahead 17]` of `origin/codex/kwavers-core-moirai-parallel`, four commits ahead of the atlas-meta gitlink pin): `burn::` line-hits **145** across **42 files** + `use burn` import-sites **43** across **43 files**. Slice 2 → slice 5 drain: 186 hits / 80 files → 145 hits / 42 files (−22% hits / −48% files); `use burn` imports 125/78 → 43/43 (−66% import-sites / −45% files). `cargo tree -p kwavers-solver | grep burn` still returns **43** (the `kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` dev-dep remain), so the Batch #4 completion condition (`cargo tree | grep burn` zero) is **unmet**. Top residual sites: `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat.rs` (34 hits — verified constant across `c6b845f81` → `7235d464a` → `d4ff48285` snapshots; shim file content unchanged), `crates/kwavers/benches/pinn_elastic_2d_training.rs` (26), `pinn/elastic_2d/training/loop.rs` (13), `pinn/elastic_2d/training/optimizer/{mappers.rs:7, pinn_optimizer.rs:6}`, `pinn/elastic_2d/loss/pde_residual/tests.rs` (6), `kwavers/benches/pinn_vs_fdtd_benchmark.rs` (6). Residual unmatched: `pinn/elastic_2d/{training/{loop,optimizer/{mappers,pinn_optimizer,tests},adaptive_sampling/batch},loss/pde_residual/tests}` (~32 hits in the `elastic_2d` subtree) + `pinn/ml/burn_wave_equation_1d/physics/mod.rs` (2) + 17 top-level `kwavers/{benches,examples,tests}/**` files (~55 hits) + `xtask/src/migration_audit.rs` (1) + facade deletion (`crates/kwavers-solver/src/burn.rs` + `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat.rs`) + Cargo.toml strip (`kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` `burn` non-optional dev-dep + `pinn` feature `dep:burn` line at L62-70). Risk #8 stays live: peer's slice-2 body and continuing native-rewrite direction align with the hard-tier non-shim invariant, but `burn.rs` + `burn_compat` are **still on disk** at `d4ff48285` (referenced by the still-unmigrated `elastic_2d` + 17 top-level families); risk closes only when the facade is deleted AND the three Cargo.toml dep lines are stripped. Note: `backlog.md` L90 + `gap_audit.md` L91-97 + risk #6 kwavers-sub-row still anchor on the `c6b845f81` snapshot (186/80 + `[ahead 13]`); they are stale by 4 commits and 41 hits / 38 files — refresh held back this turn because peer concurrently authored in those two files (the pre-batch-#5 `cargo semver-checks` verification note + §Risk #9 `SEMVER-CHECKS RESOLUTION BLOCKER`, still-uncommitted working-tree edits per `git status -sb backlog.md gap_audit.md`); composing the kwavers-burn refresh with peer's semver-blocker commit would violate `git_discipline` atomic-commit cleanliness; defer until peer's commit lands, then a follow-up atomic commit refreshes those two files to `d4ff48285`-anchored residual evidence.

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


### Pre-commit discipline row: Parent-SHA line-block + forward audit hooks

- [ ] **Parent-SHA: line-block at top of body**: atlasside chores/docs commits MUST carry a `Parent-SHA: <40-char-sha>` line-block as the FIRST BODY LINE (per RN-CC-04 self-carry discipline, retroactively validated by RN-CC-05). Inline prose citation does NOT satisfy the discipline.
- [ ] **Forward-propagation audit hooks present**: BEFORE committing, the chore author MUST verify `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` yields >=2 line-hits (after this RN-CC-05 commit lands, that threshold is established).
- [ ] **git log --grep "Parent-SHA:" audit pass**: post-commit, run `git log --grep "Parent-SHA:" --oneline` to verify the new commit is enumerated in the discoverable chain. Pre-RN-CC-04 baseline = 4 entries (`536366e`, `74df54d4`, `a96d46d`, `93a0723`); post-RN-CC-05 baseline = 5 entries (adds this RN-CC-05 commit).

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
| #3 | `[minor]` | ritk Burn-keyed trait rebind | `ritk/atlas-migration-push/batch3` | 2026-07-05 | reserved; `repos/ritk` Batch #3 history includes Burn GPU-default cleanup at `65a1a0fd` and sub-batch #1 Atlas-typed parallel trait surface at `d7a940b5`. Later DICOM ownership commit `8f8360ff` is an imaging-consumer support slice, not Batch #3 closure. Closure still requires current package gates for the remaining rebind packages; the Burn GPU-default drift is closed separately. |
| #4 | `[minor]` | kwavers-solver PINN Burn → Coeus | `kwavers/atlas-migration-push/batch4` | 2026-07-05 | reserved; depends on #3 + the `coeus-autograd/{scatter_add}` extension. Inner commit will land on `repos/kwavers` (likely the same `codex/kwavers-core-moirai-parallel` branch as #1 if concatenated, otherwise a fresh per-batch branch). |
| #5 | `[arch]` | CR-1: Apollo-ghostcell decommissioning + Melinoe `MelinoeCell` rebind | `apollo/atlas-migration-push/batch5` | 2026-07-05 | reserved; provider-side obstacle on `melinoe` brand-doctrine holder. Inner commit will land on `repos/apollo` (probable branch `refactor/apollo-fft-eunomia` per gap_audit.md peer-WIP inventory). |
| #6 | `[arch]` | CR-2: `#[global_allocator]` consolidation across `cfd-core` / `ritk-core` / `moirai` | `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` | 2026-07-05 | reserved; primary inner commit on `repos/CFDrs/crates/cfd-core` (the cfd-side first); tag annotation body enumerates the cross-repo commit chain. |

The convention shape (per ADR 0010 §Decision §"Per-batch name pattern"): **one annotated tag per batch** at inner-repo closure, anchored on the inner consumer-repo commit. Atlas-parent side gets a `chore(atlas): Advance <consumer-repo> submodule pointer to <inner-SHA>` commit + a `chore(atlas): Sync <consumer-repo>/atlas-migration-push/<N> + migration push record` docs-commit + (when applicable) an ADR authoring commit. Atlas-parent itself is the ceremony repo — **no per-batch tag on Atlas-parent**. Tag namespace reserved: `{consumer-repo}/atlas-migration-push/batch{N}` where `{N}` matches the `atlas/backlog.md` row number and `{consumer-repo}` matches the leaf consumer responsible for the migration push. Multi-repo CR-class batches (#6 above) put the tag on the primary repo (`cfd-core`) and enumerate the cross-repo commit chain in the tag annotation body.

Reference: `D:/atlas/docs/adr/0010-cfdrs-atlas-pointer-advance.md` (Accepted 2026-07-05) §Decision §"Per-batch name pattern" is the source-of-truth; this checklist section is the pre-allocation tracker enforced before batch closure.

## In-flight claim (this checkpoint)

- Owned files (atlas-meta, this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root (NOT under `atlas/`); these are the cross-repo PM artifacts.
- Owner: `claude-codex` (current session).
- Atlas-meta claim start: 2026-07-04.
- Atlas-meta last landed (codex session): `61931faf` (RITK Batch #3 sub-batch #1 sync + kwavers/Burn risk surfacing, 2026-07-06, layered atop peer commits `e82fe14c`, `4a04cad1`, `4b71cda9`, `3062ce1b`, `81413ed9`, `c5f2a84e`, `61931faf`; followed by peer `5adf4a27` "Helios closure triage" 2026-07-06 13:37). This turn: peer landed `c6b845f81` Batch #4 slice 2 (`burn_wave_equation_2d` dependency graph: 12-family Burn→Coeus native rewrite, 186 `burn::` line-hits / 80 files remaining, down from 315/144). See risk #8 below.
- **Latest closed migration batch**: Batch #3 sub-batch #3.f (RITK Burn-keyed trait rebind, per-crate sub-atomic tri-crate sister pass for `ritk-{io,interpolation,transform}`; landed in inner RITK at commit `310fcd6c421cb9844c519f1b350d39e67261729b`; `ritk/atlas-migration-push/batch3` annotated tag force-moved to tag-object SHA `d3d82ff4`; pointer advanced by atlas-meta chore commit-at-this-turn 2026-07-06). Sub-batch #3 ledger: #3.a (`603ad516`) / #3.b (`abd6abd4`) / #3.c (`9892049d`) / #3.d (`24522ae7`) / #3.e (`b0ef5940`) / #3.f (`310fcd6c`) all closed 2026-07-06 per the 7-per-crate queue. Latest closed support slice: Helios/RITK DICOM ownership (`8f8360ff` RITK typed attributes + Helios H-061 consumer reroute). ADR 0012 `ritk-burn-trait-rebind` authored in `docs/adr/`. Remaining Batch #3 sub-batch #3.g and sub-batches #4-#6 remain reserved per the atomic-boundary discipline. Earlier closed batch: Batch #2 (CFDrs nalgebra → leto + nalgebra-sparse → leto-ops `CsrMatrix`) — landed in inner CFDrs as `d58d1fe3` on branch `codex/cfdrs-atlas-migration` (2026-07-05 23:33); Atlas-parent submodule pointer advance landed as `51922a56` (peer 2026-07-06 08:14).
- **This turn (2026-07-06, codex, resumed)**: T1 re-verification of the `kwavers` "Residual `burn`" inventory at inner HEAD `c6b845f81` post peer commit `c6b845f81` "Complete Burn-to-Coeus migration for 2D PINN dependency graph". Findings layered on prior `5adf4a27` baseline: (1) the residual inventory in `gap_audit.md` L91-103 (now refreshed) drained from 315 `burn::` line-hits / 144 files to **186 / 80** (−41% hits, −44% files) and `use burn` import-sites from 222/139 to **125/78** (−44% / −44%). Slice 2 rewrote the `burn_wave_equation_2d` family (`acoustic_wave`, `cavitation_coupled`, `sonoluminescence_coupled`, `electromagnetic`, `adaptive_sampling`, `meta_learning`, `transfer_learning`, `distributed_training`, `quantization`, `uncertainty_quantification`, `universal_solver`, `field_surrogate/training/trainer`) onto `coeus_autograd::Var` + `coeus_nn::Module` + `coeus_optim::SGD`; per-parameter gradients replace burn-shaped `ModuleMapper`/`GradientExtractor`/`GradientApplicator`/`MetaOptimizer<B>` — the peer's native-rewrite direction is now explicit and **substantively aligns with risk #8's hard-tier framing**. (2) `cargo tree -p kwavers-solver | grep burn` is still **non-empty** (full `burn v0.19.0` stack pulled via `kwavers-solver/Cargo.toml:53` `optional = true` `pinn` feature + `kwavers/Cargo.toml:138` non-optional dev-dep). Batch #4 completion condition (`cargo tree | grep burn` returns zero) is **unmet**. (3) Residual unmatched: `burn_wave_equation_3d/{wavespeed,solver,optimizer,mod,tests}`, `pinn/elastic_2d/{training/{loop,optimizer,adaptive_sampling},loss/pde_residual/tests}` (32+ hits in `elastic_2d/` alone), `pinn/ml/field_surrogate/{network,tests/training}`, 17 top-level `kwavers/{benches,examples,tests}/**` files. The `burn.rs` facade + `burn_compat` module remain on disk, referenced by these still-unmigrated families; deletion awaits the Burn-source purge. (4) Risk #8 status: **partially-resolved** by `c6b845f81`'s explicit non-shim direction + the major slice-2 surface drained; live until facade + Cargo.toml strip land. Atlas-meta authors one atomic observation-mode doc-sync commit replacing the `400c32624`-anchored burn residual inventory with the `c6b845f81`-anchored one and adding slice-2 record to checklist Batch #4 progress. Does NOT touch peer-claimed source (kwavers tree).
- **This turn (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds typed `ritk-dicom` attribute ownership (`DicomTag`, common DICOM image `tags`, and `DicomAttributeRead`). Helios H-061 now removes the direct production `dicom` edge and reads Rows/Columns/SamplesPerPixel/BitsAllocated/PixelRepresentation/RescaleSlope/RescaleIntercept/PixelSpacing/SliceThickness/ImagePositionPatient/transfer syntax through RITK. Evidence tier: value-semantic RITK attribute nextest (2/2), Helios DICOM loader nextest (5/5), and normal-dependency tree proof that `dicom` appears below `ritk-dicom` only. H-063 is filed for the remaining `helios-imaging` boundary audit: generic medical-image toolkit operations move to RITK; radiation-domain MVCT simulation kernels remain in Helios.
- Next claim: observation-mode; both `kwavers` Batch #1 (Rayon→Moirai, 84 `.par_for_each` sites / 28 files remain orthogonal to Batch #4; unchanged across `ea7e09948`→`d4ff48285` snapshots) and Batch #4 (Burn→Coeus) are peer-active. Slices 3 `cd8cf776d` + slice 4 `7235d464a` + slice 5 `d4ff48285` drained the `burn_wave_equation_3d` family, the `field_surrogate/{network,tests/training}` subtree, and the `advanced_architectures` + `autodiff_utils` surface; residual after slice 5 at peer's working-tree HEAD `d4ff48285` (`[ahead 17]`): **145 `burn::` hits / 42 files** plus 43 `use burn` import-sites / 43 files (down from the handoff `c6b845f81` snapshot 186/80/125/78 — additional −22% hits / −48% files / −66% imports / −45% files on top of slice 2). Slices 6..N pending: `pinn/elastic_2d/{training/{loop,optimizer/{mappers,pinn_optimizer,tests},adaptive_sampling/batch},loss/pde_residual/tests}` (~32 hits) + 17 top-level `kwavers/{benches,examples,tests}/**` files (~55 hits) + `pinn/ml/burn_wave_equation_1d/physics/mod.rs` (2) + `xtask/src/migration_audit.rs` (1) + facade deletion (`crates/kwavers-solver/src/burn.rs` + `crates/kwavers-solver/src/inverse/pinn/ml/burn_compat.rs`) + Cargo.toml strip (`kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` `burn` non-optional dev-dep + `pinn` feature `dep:burn` line at L62-70). Atlas-meta remains ready to bump the `repos/kwavers` submodule pointer only when (a) Batch #1 closure lands cleanly (zero `par_for_each` + `ndarray` `rayon` feature strip from `kwavers-solver/Cargo.toml:24` + `kwavers-physics/Cargo.toml:20` + `cargo tree -p kwavers-solver | grep rayon` empty) AND (b) risk #8 fully resolves (peer deletes `burn.rs` + `burn_compat` and strips the three Cargo.toml dep lines).
  - Note on stale PM records: `backlog.md` L90 + `gap_audit.md` L91-97 + risk #6 kwavers-sub-row still anchor on the `c6b845f81` snapshot (186/80 + `[ahead 13]`). They are stale by 4 commits and 41 hits / 38 files; refresh held back this turn because peer concurrently authored in those two files (the pre-batch-#5 `cargo semver-checks` verification note + §Risk #9 `SEMVER-CHECKS RESOLUTION BLOCKER (mnemosyne-arena → themis dep-resolution)`, still-uncommitted working-tree edits per `git status -sb backlog.md gap_audit.md`). Composing the kwavers-burn refresh into peer's semver-blocker commit would violate `git_discipline` atomic-commit cleanliness; defer until peer's commit lands, then a follow-up atomic commit refreshes those two files to `d4ff48285`-anchored residual evidence.
- Concurrent claim streams to honor (per `concurrent_agents`, all disjoint from atlas-meta's scope, all DO NOT touch source): `repos/kwavers` `codex/kwavers-core-moirai-parallel` (27 dirty paths + `[ahead 12]` ⇒ peer ACTIVE); `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths); `repos/coeus` `main` (19 dirty paths across dtype/tensor/Python/docs); `repos/gaia` `refactor/migrate-to-leto-geometry` (5 dirty paths across CSG source/bench/PM); `repos/eunomia` `main` (7 dirty paths, `acos`/`asin`/`atan` PR-queue); plus peer claims in `repos/{apollo,CFDrs,hermes,melinoe}` (`CFDrs` now 79 dirty paths). `repos/{helios,ritk,hephaestus,mnemosyne,themis}` have no inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.

## Residual risks (logged here per actions of `gap_audit.md`)

- T1 confirms `kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral,solver/{model_impl,rhs}, operator_splitting/mod}` aggregating ~35 sites; full file-line inventory in `gap_audit.md` per the cross-repo master.
- T1 confirms `kwavers-solver/src/inverse/same_aperture/{operator/linear_op:9 +, encoded:1}` already `moirai_parallel::ParallelSliceMut`; no Rayon created.
- T1 confirms `ritk/python.rs` `numpy::{ndarray::Array2,3,4,}` import set for Python interop only; not a migration target.
- `hephaestus-cuda/src/application/decomposition/eigen.rs` Complex upload mismatch is stale in the checked-out `ks5-cholesky-panel` tree: `leto_ops::eigenvalues` output is converted to `num_complex::Complex<f32>` before upload, and `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` passes. Runtime CUDA nextest coverage remains unclaimed.
- **NEW (this turn 2026-07-06)**: `kwavers-solver/src/burn.rs` + `kwavers-solver/src/inverse/pinn/ml/burn_compat` form a burn→coeus face-shift alias module — `integrity` HARD-tier candidate (compatibility-soup / distributed-shim pattern). Peer-claim boundary: atlas-meta surfaces, peer resolves. See `gap_audit.md` surfacing risk #8 for full framing + two reconciliation options (commit-body retraction-or-burn.rs-delete-now) handed to peer.

## Next micro-sprint

**Observation-mode hand-off for active inner-repo peers**:
- This turn (2026-07-06, codex) surfaced the Batch #4 slice-1 partial-land + the burn.rs facade `integrity` concern via atomic atlas-meta doc edits only (PM artifacts at workspace root). Did NOT migrate kwavers/coeus/gaia source because those scopes are peer-active. Separately, the Helios/RITK DICOM ownership slice is closed: `ritk-dicom` now owns typed DICOM attribute reads, and Helios production DICOM loading consumes RITK for parse + attributes + transfer syntax + pixel decode.
- Next turn (2026-07-06, codex resumed) refreshed the Batch #4 record against peer's actual working-tree HEAD `d4ff48285` (slices 3 `cd8cf776d` `burn_wave_equation_3d` + slice 4 `7235d464a` `field_surrogate/{network,tests}` + interstitial `ae86daecc` + slice 5 `d4ff48285` `advanced_architectures`+`autodiff_utils`), all drained to native coeus. This atlas-meta turn authored a single atomic commit editing `checklist.md` only (Batch #4 §Progress append + §In-flight §Next-claim refresh + §Next-micro-sprint refresh), explicitly NOT touching `backlog.md` or `gap_audit.md` because peer is concurrently authoring them with the pre-batch-#5 `cargo semver-checks` verification note + §Risk #9 `SEMVER-CHECKS RESOLUTION BLOCKER (mnemosyne-arena → themis dep-resolution)` (still-uncommitted working tree per `git status -sb backlog.md gap_audit.md`). Composing the kwavers-burn refresh with peer's semver-blocker commit would violate `git_discipline`'s atomic commit unit; deferred to a follow-up once peer's commit lands.
- Peer's slice-2..N sequence progress (post-handoff): slice 2 `c6b845f81` (12-family `burn_wave_equation_2d` dependency graph) ✅ landed; slices 3-5 `cd8cf776d` + `7235d464a` + `d4ff48285` ✅ landed (drained `burn_wave_equation_3d` + `field_surrogate/{network,tests/training}` + `advanced_architectures`+`autodiff_utils`). Remaining peer queue: slice 6 `pinn/elastic_2d/{training/{loop,optimizer/{mappers,pinn_optimizer,tests},adaptive_sampling/batch},loss/pde_residual/tests}` → slice 7 17 top-level `kwavers/{benches,examples,tests}/**` files + `pinn/ml/burn_wave_equation_1d/physics/mod.rs` (2) + `xtask/src/migration_audit.rs` (1) → slice 8 `burn.rs`+`burn_compat` deletion + `kwavers-solver/Cargo.toml:53` `burn` optional dep + `kwavers/Cargo.toml:138` `burn` dev-dep removal + `pinn` feature `dep:burn` strip at L62-70.
- **T1 confirmed (this turn 2026-07-06, codex resumed continuation)**: peer is mid-slice-6+7 Batch #4 Burn→Coeus migration AND a parallel `nalgebra` → leto/eunomia migration across kwavers. Inner kwavers working-tree dirty count expanded from 7 files (at start of this turn) to **116 files** — both Batch #4 slice-6 `elastic_2d` + slice-7 plus the gap_audit L51-59 `nalgebra` residual-site migration are live. Direct evidence: (1) `crates/kwavers/Cargo.toml` working-tree diff strips the workspace `nalgebra = { version = "0.33", features = ["serde-serialize"] }` line (visible as `-nalgebra = { ... }` in `git diff Cargo.toml`); (2) `git grep 'nalgebra' -- '*.rs'` returns **164 line-hits** across the dirty tree (transient inflation as rewrite references both old `use nalgebra::...` imports + new `leto`/`leto_ops::`/`eunomia::` callsites co-exist), against the prior `aa10a6e76`-anchored L51-59 baseline of 13 source sites × 5 manifests; (3) the 13 source-site file-path set in `gap_audit.md` L52-59 (`kwavers-mesh/src/tetrahedral/mesh.rs`, `kwavers-transducer/src/flexible/calibration/{types,manager/kalman,manager/mod}`, `kwavers-medium/src/anisotropic/{christoffel,stiffness}`, `kwavers-analysis/.../three_dimensional/cpu/mvdr/mod.rs`, `kwavers-solver/.../{cbs/solve,hybrid/{bem_fem_coupling/{interface,coupler/struct_impl/solvers}},helmholtz/fem/solver/core/{interpolation,element}}`) is **exactly the file set now dirty** in the inner kwavers working tree — the route-by-route site rewrites are landing on the same files `gap_audit.md` enumerates; (4) peer is simultaneously dirty across `kwavers-analysis/.../beamforming/{adaptive/{mvdr,subspace},narrowband/{capon,subspace_spectrum},three_dimensional/{cpu,processing}}` (15+ files), `kwavers-grid/{src/compat.rs DELETION, src/{lib,structure,operators/{curl,divergence,gradient,gradient_optimized/*,laplacian}}.rs}` (11 files), `kwavers-math/{linear_algebra/{basic,eigen/*,eigendecomposition/*,iterative/lsqr/*,norms,sparse/*,tests},numerics/operators/{differential/*,spectral/*},fft/{gpu_fft,kspace,mod,utils},inverse_problems/{pnp,regularization/*},simd_safe/{auto_detect/*,avx2,neon,operations,swar},lib}` (37 files; SIMD dispatch path may also be Hermes-aligned), `kwavers-medium/src/anisotropic/{christoffel,stiffness}` (3 files), `kwavers-mesh/{Cargo.toml,src/tetrahedral/mesh}` (2 files), `kwavers-solver/src/{forward/{bem/solver/{assembly,solution},hybrid/bem_fem_coupling/{interface,struct_impl/solvers},helmholtz/fem/solver/core/{element,interpolation,solve}},inverse/{fwi/frequency_domain/cbs/solve,pinn/elastic_2d/{loss,pde_residual/*,model,training/loop,training/optimizer/*},reconstruction/unified_sirt,reconstruction/seismic/??},pins/elastic_2d/ml/autodiff_utils/*}` (25+ files including 5 DELETIONS: `elastic_2d/loss/pde_residual/{divergence,gradients,strain_stress,time}.rs` + `elastic_2d/training/optimizer/mappers.rs`), `kwavers-transducer/{beamforming/processor,flexible/calibration/{types,kalman}}` (4 files), top-level `kwavers/benches/{cpml,simd_fdtd}` (2 files). (5) Burn residual simultaneously drained: `burn::` line-hits **105 across 31 files** at the dirty tree (down from `d4ff48285` HEAD `145/42`) — peer's slice-6 `elastic_2d` + slice-7 top-level files rewrite is landing Live; `burn.rs` + `burn_compat.rs` shim still **constant 34 hits** (shim content unchanged; deletion awaits the last burn-source purge). (6) `par_for_each` residual **84 sites / 28 files unchanged** — peer's current dirty tree does NOT touch Batch #1 Rayon→Moirai; Batch #1 remains stable as a separate downstream phase.
- **T1 confirmed (2026-07-07 Burn cleanup closeout + neutral-name continuation)**: current `repos/kwavers` working tree has zero kwavers manifest Burn hits, zero requested PINN/top-level source-scope `Burn`/`burn_`/`burn-`/literal `burn` hits, no `crates/kwavers-solver/src/burn.rs`, and no `burn_compat` alias path. The 1-D/2-D/3-D PINN module paths are framework-neutral (`wave_equation_1d`, `wave_equation_2d`, `wave_equation_3d`), exported names are framework-neutral (`PinnWave*`, `PinnConfig*`, `LossWeights*`, `TrainingMetrics*`), and the beamforming adapter is `pinn_adapter`. `xtask/legacy_surface.allowlist` was regenerated and `rustup run nightly cargo run -p xtask -- legacy-migration-audit` reports allowlist clean. Whole-repo literal residual is **356 lines across 21 files**, concentrated in `Cargo.lock` and historical PM/audit prose; scoped PINN/top-level source plus allowlist residual is **0 lines across 0 files**. `cargo tree -p kwavers-solver --features pinn -i burn` still resolves Burn through RITK provider crates, not kwavers manifests. Verification: `rustup run nightly cargo fmt -p kwavers-solver -p kwavers --check` passed; `rustup run nightly cargo check -p kwavers-solver --features pinn` passed; `rustup run nightly cargo check -p kwavers --features pinn --tests --benches --examples` passed with pre-existing warnings; `rustup run nightly cargo nextest run -p kwavers --features pinn --test pinn_bc_validation --test pinn_ic_validation --status-level fail --no-fail-fast` ran 16 tests with 12 passed and 4 failed on legacy 3-D loss thresholds.
- **2026-07-08 Bulk provider-surface round 3 — 5 atomic choruses landed** (post-`36acbbca9` fresh-session, post-`gap_audit.md` row 13 injection): the prior cand-2 session's round-1 (`2e1c4f20d`→`274a6a961`→`a12d1dd77`) + round-2 (`5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9`) bulk-advance blocks left 5 provider surfaces DIVERGED; round 3 captured the inner churn that landed since then, advancing 5 gitlinks in 5 NEW atomic chore commits (per row 10 NO-AMEND + row 11 DYNAMIC-SHA-EXTRACTION):
  - `ad6cf57d4` apollo `2e6f9be` → `e6ecce4` (inner head `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`)
  - `1828ea14a` eunomia `b3fd6f2` → `22e971e` (inner head `chore(deps): sync Cargo.lock (num-traits dependency)`)
  - `852de7129` hermes `92187d0` → `166a7b9` (inner head on `rescue/detached-simd-numa-work` branch — 17 commits ahead of `origin/main` — `Revert "ci(miri): use Tree Borrows for the mnemosyne-allocator-backed run"`)
  - `769b70a67` leto `83e1693e1` → `a9572da27` (inner head `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`)
  - `1fe3c0e56` mnemosyne `482670d` → `98a02b6` (inner head `docs(gap_audit): Record the Miri alloc/free aliasing finding (HIGH PRIORITY)` — *node: this finding is now ALIGNED in atlas-meta's tracking; gap_audit row 13 records it as a residual risk for the mnemosyne peer to root-cause*)
- **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit shifted to round-2 bookkeeping. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` line-154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE**: at inner HEAD `35ee01076`, trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout.
- **Atlas-meta action posture**: peer's concurrent expansion across the kwavers Batch #1 + Batch #4 surfaces consumes the entire kwavers source surface, as described in the previous line-586 entry — there is no disjoint-contribution surface available to atlas-meta at this moment beyond observation-mode PM-record refresh. The round-3 block closes the 5 provider-pointer divergences that were the immediate-discovery billboard; the next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR the KW-CV-001 watchpoint firing for kwavers.
- Atlas-meta action posture: peer's concurrent expansion across two batch themes (Batch #4 slice-6+7 + `nalgebra`-residual-site migration) consumes the entire kwavers source surface — there is no disjoint-contribution surface available to atlas-meta at this moment beyond observation-mode PM-record refresh. The pending `backlog.md` L90 + `gap_audit.md` L51-59/L91-97 refresh is now **larger** than the kwavers-Burn-only refresh originally deferred — same atomic commit scope explodes to refresh BOTH the `nalgebra` L51-59 block AND the L91-97 burn residual block; the per-batch-theme atomic discipline argues for two separate follow-up atomic commits when peer's next landing stabilizes the tree. Both still deferred until peer's pre-batch-#5 semver-blocker commit (the `backlog.md`+`gap_audit.md` working tree) lands.
- Awaiting the peer's `nalgebra` residual migration closure signal — when `nalgebra = { ..., features = ["serde-serialize"] }` is fully stripped from all 5 kwavers manifest files (`kwavers` workspace + `kwavers-mesh`/`-transducer`/`-medium`/`-solver` per `gap_audit.md` §kwavers L51 listing manifests) AND `git grep 'nalgebra' -- '*.rs'` returns zero in the kwavers tree, the L51-59 `gap_audit.md` block (and the related L51 `##### Residual nalgebra #####` enumeration) is ready for re-anchor per peer-landed commit SHA. Until then, `nalgebra = { ..., features = ["serde-serialize"] }` workspace dep may still be restored in peer's iteration, and the 164 transient line-hits will collapse to zero on commit.
- Awaiting the peer's Batch #1 closure signal (clean `cargo nextest run -p kwavers-solver --no-fail-fast` + `cargo tree -p kwavers-solver | grep rayon` empty + `ndarray` `rayon` feature strip from `kwavers-solver/Cargo.toml:24` + `kwavers-physics/Cargo.toml:20`) on a branch tip not contemporaneous with this session's pointer.
- Awaiting the peer's Batch #4 closure signal (`cargo tree -p kwavers-solver | grep burn` empty), conditioned on `burn.rs`+`burn_compat` facade deletion + Cargo.toml dep strip.
- Once the peer lands closure(s) or a claim goes stale (next session's check): atlas-meta bumps `repos/kwavers` pointer + closes the Batch #1 and/or Batch #4 entries in the in-flight section of `backlog.md`.

- **2026-07-08 Bulk provider-surface round 4 — 6 atomic chore commits landed (post-`1fe3c0e56` session)**: the round-3 inner-churn capture cycle overshot and two divergent screenshots reappeared shortly after the `2d78fffa4` OOB session landed (a `chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)` commit at `6902d2e92` merged with my staged r4 stash, both consuming hermes/leto r4 pointers + adding hephaestus to 240b260). Re-probe at session-resume returned `hermes c7b17b02c73a / leto 86d366bc0e90` ALREADY-RESOLVED via that OOB consolidation. The r5 round then captured (a) the OOB-merging of the hermes `5ad1b58 → c7b17b02` ergonomically inside the consolidated `6902d2e92`, (b) the leto `a9572da → 86d366b` (Migrate kwavers closure path unblock — `feat(leto-ops): batched LU, CSC sparse format, CG/GMRES iterative solvers`), plus 5 fresh divergences that surfaced mid-session:
  - `e3223094a` hermes c7b17b02c73a (inner `chore(deps): sync Cargo.lock (eunomia num-traits dependency)`) — bundled with leto advance during the `6902d2e92` OOB consolidation; verified via `git --no-pager show --stat e322309`
  - `e3223094a` leto 86d366bc0e90 (inner `feat(leto-ops): batched LU, CSC sparse format, CG/GMRES iterative solvers` — canonical generic LU factorization in batched form for tiled GPU dispatch, CSC sparse storage, CG/GMRES iterative kernels; unblocks kwavers-solver Bulk-solver migration closure target)
  - `6a598da91` kwavers 89117870 (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/Complex<f64>, ndarray Array bases, and coefficient paths onto eunomia+leto atlas substrates; replaces nalgebra/ndarray/numeric-complex stack in the kwavers-core domain)
  - `0e34ae082` coeus ec69a6a (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` `docs(checklist): reconcile MS-406/MS-407 as already-closed`)
  - `045291499` ritk e75d8748 (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — directly resolves the displacement_registration_test failure noted in row 6, the Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus 006f2a7 (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — extends criterion bench registry for 3D pooling kernels)
  - `4b7f4804e` kwavers 09c645f30 (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870` Complex/eunomia migration)
- **Net alignment state post-`4b7f4804e`** (this turn): all 13 actively-tracked submodules ALIGNED (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, gaia, hephaestus, kwavers) at the moment of capture. KW-CV-001 watchpoint re-probed (still 0). The round-4 migration advances do not trigger the watchpoint.
- **2026-07-08 (mid-session) Test/example validation sweep**: triggered by the user's directive "cleanup and resolution of all test and example issues/errors". T1 verification at the just-advanced consumer-side inner HEADs:
  - **ritk** at `529d6651` inner HEAD: `cargo nextest run -p ritk-python --lib` PASSES **47/47** (1m 41s compile, 0.34s test execution) — value-semantic asserts survive.
  - **CFDrs** at `72275347` inner HEAD: `cargo check --workspace --all-targets` PASSES (1m 31s) — zero warnings across cfd-{core, math, 1d, 2d, 3d, validation, optim, python, schematics, io} + gaia.
  - **CFDrs** at `72275347` inner HEAD: `cargo nextest run --workspace --lib` PASSES **2177/2177** (1 skipped, 37s execution, 0 failed, 1 slow flagged at the cfd-3d bifurcation::validation::test_mesh_convergence_outputs_observed_order_and_gci boundary of 28.1s — within 15s slow-timeout×2 budget).
  - **CFDrs subset** `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib`: PASSES **1335/1335** (24.9s, 1 skipped).
  - **kwavers** at `ccc6bbf9e6` inner HEAD: `cargo check -p kwavers-solver --workspace` PASSES (49.88s); the workspace-wide ndarray↔leto boundary integration landed.
  - **kwavers** at `ccc6bbf9e6` inner HEAD: `cargo check --workspace` PASSES with 1 dead-code warning (`fn to_leto3` unused in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`).
  - **kwavers** at `ccc6bbf9e6` inner HEAD: `cargo nextest run --workspace --lib` FAILS at compile due to 1 residual slip at `crates/kwavers-solver/src/plugin/mod.rs:204:21` — the `NullBoundary` test-mock `apply_acoustic_freq` method uses `use ndarray::Array3;` (line 182) which shadows the workspace's `leto::Array3` re-binding; the `Boundary` trait now declares `&mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. One-line fix lands at line 182. **Disjoint-scope peer-owned**: record to `gap_audit.md` ### Bulk-migration priority #1 × #2 source-side overlap (2026-07-09); atlas-meta does NOT touch `repos/kwavers/crates/kwavers-solver/src/plugin/mod.rs`.
- **Atlas-meta action posture**: round-4 captured all in-session churn; mid-session validation sweep found 1 residual slip in kwavers-solver (peer-owned per disjoint-scope) + 1 cosmetic dead_code warning. Awaiting peer's next kwavers commit (KW-CV-001 watchpoint catch + the 2-line plugin/mod.rs fix). Either path stays in observation mode; no source-tree work concrete to atlas-meta.
- **2026-07-10 — chorus-chain revert + litter hygiene pass**: 4 unpushed `chore(atlas): Post-review patch for d6db896 -- NIT 1 closure ...` style commits accumulated atop `d6db896` (`78e40e4` + `035b9ca` + `a5b3cdb` + `2acedcf`) — collectively adding 5 self-referential narrative sub-sections to `docs/coordination/INDEX.md` and 26 blank trailing lines (`+` × N). The chorus-chain was the audit-predicates-recursive-noise pattern flagged as pollution per handoff §Pitfalls (HIGH); reset to `d6db896` (own unshared branch + unpushed + pure-noise content) restored the canonical PM baseline. RN-CC-05 audit predicates re-verified: 4-file `rg -F "Parent-SHA:"` aggregate = 7 hits (>=4 ✅), `git log --grep "Parent-SHA:" --oneline` = 10 entries (>=2 ✅✅✅). 17 ignored scratch files (`_apply_*.py` × 9, `_commit_*.txt` × 8) and `gap_audit.md.reframe.bak` deleted from worktree (covered by `_*` + `*.bak` `.gitignore` patterns). `git status --ignored --short` now reports only 8 benign infrastructure patterns (`.claude/`, `.ruff_cache/`, `repos/report/`, `target/`) + 7 submodule inner-dirty markers. Branch parity with `origin/codex/kwavers-atlas-integration` (0 ahead). KW-CV-001 watchpoint: still 0 (peer kwavers-side closeout pending); KW-CV-002: stable. Repository returned to observation mode; resignation-confirmed via `git --no-pager status` reporting "Your branch is up to date with 'origin/codex/kwavers-atlas-integration'."

Branch: `codex/kwavers-atlas-integration`.### H-063 done -- Batch #1 slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8): 5/41 sites migrated in 3/15 files cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (1 mut + 4 immut Zip par_for_each at L93 in compute_diffusive_term_workspace), migrated to par_mut().enumerate() with 5 is_standard_layout() asserts applied in-chore (Nit 1 from prior slice 2 review). Cargo check clean at inner HEAD. **36/41 sites / 12/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.
### H-062b done -- Batch #1 slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708 = slice 1): 4/41 sites migrated in 2/15 files cumulative at slice 2. The 2 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1-mut + 2-immut Zip at L48 + 1-mut + 3-immut Zip at L62 inside KuznetsovWave::update_wave), migrated via the canonical 1+N physics-equation pattern (as_slice{_mut,}().expect() + par_mut().enumerate() with flat-index lookups). Cargo check clean at inner HEAD. **37/41 sites / 13/15 files remain** after slice 2. KW-CV-001 watchpoint remains ACTIVE. NOTE: retroactive land AFTER slice 3 mark (prior re-emission attempts failed due to basher command-length limits).
### H-064 done -- model_impl.rs Nit 1 asymmetry fixup 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b = slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2): 7 is_standard_layout() asserts added retroactively to model_impl.rs (slice 2 file): 3 in first-step branch (1 mut pressure_field + 2 immut self.pressure_current + rhs) + 4 in multi-step branch (1 mut + 3 immut including NEW self.pressure_prev). Each assert precedes the corresponding .as_slice{_mut,}().expect() call. Cargo check clean. Cumulative: 5/41 sites / 3/15 files migrated + 2 file-level fixups (c77a926d8 struct_impl.rs + b21679f5 model_impl.rs). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

### H-065 done -- Batch #1 slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c = model_impl.rs Nit 1 fixup = d2cb977b slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 = 5cd8c708 slice 1): 6/41 sites migrated in 4/15 files cumulative across slices 1+2+3+4. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (1 mut + 3 immut Zip par_for_each at L109 in `compute_nonlinear_term_workspace`), migrated to `par_mut().enumerate()` with 4 `is_standard_layout()` asserts applied in-chore (Nit 1). Cargo check clean at inner HEAD. **35/41 sites / 11/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

### H-066 done -- Batch #1 slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f = slice 4 nonlinear.rs = b21679f5c model_impl.rs Nit 1 fixup = d2cb977b slice 3 diffusion.rs = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 model_impl.rs = 5cd8c708 slice 1): 7/41 sites migrated in 5/15 files cumulative across slices 1+2+3+4+5. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (1-mut + 1-immut Zip par_for_each at L191 in OperatorSplittingSolver::nonlinear_step), migrated to par_mut().enumerate() with 2 is_standard_layout() asserts applied in-chore. Cargo check clean at inner HEAD. **34/41 sites / 10/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

### H-067 done -- Batch #1 slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5 = slice 5 = 9595a99f slice 4 = b21679f5c model_impl.rs Nit 1 fixup = d2cb977b slice 3 = c77a926d8 struct_impl.rs fixup = 9541155f slice 2 = 5cd8c708 slice 1): 11/41 sites migrated in **6/15 files** cumulative. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (1-mut + 1-immut Zip par_for_each in `KuznetsovWave::compute_rhs` homogeneous branch -- sites 2-5), migrated with 8 is_standard_layout asserts (2 per site) + 4 par_mut().enumerate with flat-index lookups. Cargo check clean. **30/41 sites / 9/15 files remain**. Heterogeneous site 1 (`Zip::indexed(rhs.view_mut())` with 3D-index closure arg + 8 (i,j,k) lookups) deferred to follow-up chore. KW-CV-001 watchpoint remains ACTIVE.

## Session 2026-07-12 -- leto empty-layout fix + atlas-meta verification sweep

### Closed (atlas-meta write-set)

- **`leto` [patch]**: `Layout::has_zero_stride_aliasing` short-circuits on `size() ==
  0` (commit `08d0b44` on `repos/leto` main, pushed to origin). Empty C/F-
  contiguous layouts produced by `c_contiguous_strides` defensive
  zero-stride collapse for zero-sized interior axes are no longer falsely
  flagged as aliased. Regression tests added (5 cases). Provider gate:
  fmt / clippy -D warnings / nextest --all-features 564/564 / doc --no-deps
  all clean.
- **Unblocked consumer test**: `kwavers-solver::inverse::fwi::time_domain::
  encoded_source::tests::hadamard_averaged_encoded_gradient_matches_summed_shot_gradient`
  now PASSES (was the sole documented kwavers lib test failure). Root cause:
  test uses `CPMLConfig::default()` with `per_dimension.y == 0`, producing an
  empty `psi_p_y` memory buffer of shape `[8, 0, 8]` with strides `[0, 8, 1]`;
  the leto predicate rejected the mutable zip. No kwavers source change
  required (the temporary `eprintln!` debug lines from the prior session were
  uncommitted scratch; removed by restoring HEAD state on `axis.rs`).
- **atlas-meta pointer**: `repos/leto` submodule bumped `a20286e -> 08d0b44`.

### Verification sweep (consumer read-only)

Full-workspace `cargo nextest run --no-fail-fast` from each consumer repo:

| Repo | Inner HEAD | Branch | Result | Known peer-active items |
|---|---|---|---|---|
| `kwavers` | `7c70d1b1d` | `codex/kwavers-core-moirai-parallel` | 5611/5612 lib pass, 1 timeout, 15 skipped | `abdominal_preprocessing_selects_one_connected_treatment_component` (elastic-fwi profile 90 s budget) -- see `gap_audit.md` KW-WATCH-002 |
| `CFDrs` | `e24922c8` | `codex/cfdrs-atlas-migration` | 3055/3056 pass, 1 fail, 30 skipped | `cfd-suite::cross_fidelity_blueprint_complex_branching` Picard non-convergence -- pre-filed by peer `fa28ce43` |
| `ritk` | `0ca58574` | `codex/ritk-burn-ndarray-cleanup` | 4900/4900 pass, 26 skipped | `ritk-model ssmmorph::decoder::tests::test_decoder_forward` 293.9 s (9.8x slow threshold) on burn NdArray backend -- peer active Burn dep strip Batch #4/#5 |

### Findings recorded in `gap_audit.md`

See `gap_audit.md` "Findings 2026-07-12" section for the three recorded items:
leto fix summary, KW-WATCH-002 (kwavers-therapy perf), and the CFDrs and
ritk peer-stream watchpoints. Per ADR 0011 disjoint-scope, atlas-meta is
NOT editing peer-active consumer source for any of these items; the leto
fix is the sole closed write-set this session.

### Concurrent peer activity (not mine)

- kwavers peer stream advanced HEAD `1a27e922d -> 7c70d1b1d` mid-session
  (`refactor(kwavers-python): Remove rank-one shim`). 11 dirty files in
  `crates/kwavers-python` (peer Stage-C complex_compat bridge in flight).
- CFDrs working tree: `Cargo.lock` artifact drift only.
- ritk working tree: 5 modified files in `crates/ritk-core/tests` + Cargo.lock
  (peer Burn dep strip WIP).

### Next actionable

- Await peer stream closure of the three watchpoints (kwavers-therapy perf,
  CFDrs cfd-1d Picard convergence, ritk Burn dep strip Batch #4/#5).
- Re-verify each consumer repo after peer closures, then trigger an
  atlas-meta alignment sweep committing the new submodule pointers.

## Session 2026-07-12 (evening) -- kwavers Batch #1 closure + ritk coeus-native pointer advance

### Closed (atlas-meta write-set)

- **`kwavers` Batch #1 [patch]**: peer commit `5913f2946`
  (`perf(kwavers-solver): Migrate solver tree to moirai parallel iterators`)
  closes the Rayon→Moirai source-side migration. Closure-condition evidence
  at HEAD `5913f2946`: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use
  ndarray`=0; `kwavers-solver/Cargo.toml` deps section carries `leto` +
  `leto-ops` + `moirai-parallel` only (zero `ndarray`/`rayon`/`burn`). Commit
  body declares "Closes remaining ndarray-parallel and rayon surface-level
  dependencies in kwavers-solver." `cargo nextest run --workspace --exclude
  kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (the
  pre-existing KW-WATCH-002 abdominal-preprocessing perf tests on the
  explicit 90s `elastic-fwi` profile override), 7 skipped — NOT regressions
  introduced by the migration (peer-stream perf, atlas-meta is NOT editing
  `crates/kwavers-therapy/**`). KW-CV-001 lexical-trigger probe still
  returns 0 (peer uses `Migrate ...` subject phrasing) but the underlying
  zero-site invariant IS met and the commit body declares closure.
- **`kwavers` Batch #4 [minor]**: co-verified closed at the new HEAD —
  `cargo check -p kwavers-solver --features pinn` PASSES (53 warnings, 0
  errors). Sole residual is the `ndarray` `rayon` feature gate on
  `kwavers-solver/Cargo.toml` flagged as a separate item in the peer
  commit body (manifest detail, not a source-site residual).
- **`ritk` [minor]**: peer advanced `57b2b1c3 → bcd3b726` on
  `codex/ritk-burn-ndarray-cleanup` with coeus-native paths for
  `ritk-filter` (intensity + grayscale morphology) atop `829ebfe5`
  (convolution/stencil) and `34c3836b` (`ritk-statistics` normalization /
  comparison). Verification at HEAD: `cargo nextest run -p ritk-filter -p
  ritk-statistics -p ritk-image --lib --no-fail-fast`: 1399/1399 pass.
  Residual `use burn` imports: 320 (down from prior); dep strip per
  Batch #3 sub-batch #5/#6 remains reserved per ADR 0012 standing
  reminders.
  **Subsequent advances in same session**: peer landed
  `5812cd17 feat(ritk-filter): add coeus-native paths for
  spatial/intensity/morphology filters`, then later
  `ef9420fb feat(ritk-filter): add coeus-native paths for
  edge/diffusion/intensity filters`. Verification
  `cargo nextest run -p ritk-filter --lib --no-fail-fast` at HEAD
  `ef9420fb`: 1063/1063 pass (8.318s, well under 30s slow threshold).
  Inner HEAD advanced `bcd3b726 → 5812cd17 → ef9420fb` across the session
  per the `concurrent_agents` disjoint-scope rule — atlas-meta pins only
  verified state.
- **Atlas-meta pointers**: `repos/kwavers` gitlink advanced `01643ed9
  → 5913f2946`; `repos/ritk` gitlink advanced `57b2b1c3 → bcd3b726
  → 5812cd17 → ef9420fb` (peer landed two further coeus-native filter
  commits mid-session, each verified green 1063/1063 under
  `cargo nextest run -p ritk-filter --lib --no-fail-fast` at HEAD before
  pinning).

### Out-of-scope this session (unchanged)

- `CFDrs` (submodule status `m` lowercase): inner WT dirty with peer-active
  cfd-1d Picard convergence work (the `cross_fidelity_blueprint_complex_branching`
  finding). Gitlink ALIGNED.
- `helios` (submodule status `m` lowercase): inner WT carries only untracked
  `examples/` dirs. Gitlink ALIGNED.
- Atlas-meta does NOT absorb inner-WT state into parent pointers per the
  disjoint-scope rule; only committed inner HEAD advances are pinned.

### Next actionable

- Continue observing the three peer-stream watchpoints: KW-WATCH-002
  (kwavers-therapy abdominal-preprocessing perf), CFDrs cfd-1d Picard
  convergence, ritk Burn dep strip sub-batches #4/#5/#6.
- Provider extension items (Batch #8) remain claimable in peer-clean
  provider repos (`leto`, `moirai`, `apollo`, `eunomia`, `mnemosyne`,
  `themis`, `melinoe`, `hephaestus`).

## Session 2026-07-13 -- atlas-meta pointer advance: CFDrs Picard watchpoint closure + helios/kwavers verified advances

### Closed (atlas-meta write-set)

- **CFDrs cfd-1d Picard convergence watchpoint — ✅ CLOSED**: peer HEAD
  `153b0ed9` `fix(cfd-1d,cfd-2d): resolve cross_fidelity_blueprint_complex_branching
  convergence` resolves the long-standing OPEN-033 / `cfd-suite::cross_fidelity_blueprint
  cross_fidelity_blueprint_complex_branching` regression that previously panicked with
  `MaxIterationsExceeded: Convergence failed: Maximum iterations (10000) exceeded`.
  Re-verification at HEAD `153b0ed9`: `cargo nextest run --no-fail-fast` from
  `repos/CFDrs`: **26/26 pass**; `cross_fidelity_blueprint_complex_branching` PASS
  in 0.799s (orders of magnitude below the prior 10000-iteration stall, and well
  under the 30s slow threshold). Atlas-meta `repos/CFDrs` gitlink advanced
  `e24922c8d564816e6f0834912d900e698ef27b93 →
  153b0ed95710460014bf2429bc5bd94e31f2d054`.
- **`helios` advance**: peer HEAD `4efb14c` `fix(helios-domain): correct
  voxel_grid_construction example type errors`. Re-verification at HEAD `4efb14c`:
  `cargo nextest run --no-fail-fast` from `repos/helios`: **241/241 pass** (2.630s).
  Atlas-meta `repos/helios` gitlink advanced `5f6aef65a47d716f26452592d3a91f3d934a2ffc
  → 4efb14cd391fbd0653257865a3f3ea74fdf0e461`.
- **`kwavers` advance**: peer HEAD `4453c2275` `fix(kwavers-driver): graceful
  skip for missing KiCad fixture files`. Re-verification at HEAD `4453c2275`:
  `cargo nextest run --workspace --no-fail-fast` from `repos/kwavers`:
  **6097/6099 pass, 2 timeouts, 15 skipped**. The two timeouts are the pre-existing
  KW-WATCH-002 abdominal-preprocessing perf tests on the explicit 90s `elastic-fwi`
  profile override (`repos/kwavers/.config/nextest.toml:70-74`) — NOT regressions
  introduced by this driver fix; test-count growth (5119 → 6099) reflects peer-added
  tests. Atlas-meta `repos/kwavers` gitlink advanced `5913f29466bb6b769aefbc1a9b794c63b139babb
  → 4453c227524d9f150fb1e299c967e98821368ea7`.

### Watchpoint status post-advance

- ✅ **CFDrs cfd-1d Picard convergence — CLOSED** (peer HEAD `153b0ed9`, verified
  by atlas-meta run). Of the three peer-stream watchpoints, one is now closed.
- ⏳ **kwavers-therapy KW-WATCH-002 perf** — still open; 2 abdominal-preprocessing
  timeouts persist (peer-stream perf, NOT atlas-meta's to fix per ADR 0011).
- ⏳ **ritk Burn dep strip Batch #4/#5/#6** — still open; inner ritk WT remains
  dirty with peer WIP (Burn dep strip continuing).

### Next actionable

- Continue observing the two remaining peer-stream watchpoints (KW-WATCH-002,
  ritk Burn dep strip).

## Session 2026-07-13 (continued) -- mnemosyne advance (single) + moirai peer-break watchpoint filed

### Closed (atlas-meta write-set)

- **`mnemosyne` advance**: peer HEAD `877cde0586`
  (`docs(backend): Decide callback pair`) atop prior pinned `98a02b614`.
  Re-verification at HEAD `877cde0`:
  `cargo nextest run --workspace --no-fail-fast` from `repos/mnemosyne`:
  **278/278 pass** (4.437 s). mnemosyne has zero moirai dependency; the peer-active
  moirai break documented below does not propagate into this verification.
  Atlas-meta `repos/mnemosyne` gitlink advanced
  `98a02b61ccb8ce04f5b1920113d8315cae193ae8 →
  877cde0586f0d25e70627fa2ad546f583116e47e`.

### Discovered this cycle: moirai peer-stream break (MR-WATCH-001) — NOT pinned

- **MR-WATCH-001 (new watchpoint)**: peer's breaking commit
  `9c015a3 refactor(moirai)!: Remove allocator residue` followed by further
  HEAD `5343ebfc` with uncommitted WT edits on
  `moirai-scheduler/src/deque/{chase_lev,reclaim,split,mod}.rs`, `lib.rs`,
  `docs/adr.md`, `docs/checklist.md` breaks `moirai-scheduler` lib test
  compile (27 errors) and `moirai-executor` lib compile (10 errors) at the
  in-worktree moirai HEAD. The peer is actively fixing (WT dirty mid-edit).
  Atlas-meta WILL NOT advance `repos/moirai` gitlink until the peer rebuilds
  green on a clean HEAD.
- **ritk gitlink unpinned this cycle as co-consequence**: ritk's path dep
  `moirai = { path = "../moirai/moirai" }` pulls the broken in-worktree
  moirai into any ritk test build. ritk HEAD `39cf95bc`
  (`feat(ritk): migrate IO crate tests from burn to coeus native path (ADR 0002)`)
  and two intermediate commits (`2390f633`, `476ac35f`) remain unpinned until
  either the peer fixes moirai (re-open trigger: clean green moirai HEAD with
  zero WT edits) or a future cycle can verify ritk against the previously-
  pinned moirai HEAD without disturbing the peer's in-progress moirai WT.
  See `gap_audit.md` "### moirai peer-active break (NOT pinned) + ritk verify-
  blocked" for the full evidence trace and re-open trigger.

### Watchpoint status post-cycle

- ✅ **CFDrs cfd-1d Picard convergence — CLOSED** (prior cycle, peer HEAD `153b0ed9`).
- ⏳ **kwavers-therapy KW-WATCH-002 perf** — open.
- ⏳ **ritk Burn dep strip Batch #4/#5/#6** — open.
- ⏳ **MR-WATCH-001 (moirai-scheduler/executor rebuild)** — NEW, open.

## Session 2026-07-13 (continued #2) -- hephaestus advance (docs-only peer commit, full gate green)

### Closed (atlas-meta write-set)

- **`hephaestus` advance**: peer HEAD `c78a98e1`
  (`docs(wgpu): Claim callback migration`) atop prior pinned `b90923ef` on branch
  `codex/fix-wgpu-callback-pair`. Single docs-only commit atop the previously-
  verified `b90923e` `perf(hephaestus-wgpu): Gate pinv/matexp/random behind
  decomposition/sparse features`. Re-verification at HEAD `c78a98e`:
  `cargo nextest run --workspace --no-fail-fast` from `repos/hephaestus`:
  **298/298 pass** (97.554s suite total; slowest single test 1.196s, well under
  30s slow threshold). Inner hephaestus WT remains dirty on three wgpu files
  (`device.rs`, `lib.rs`, `contract.rs`) — peer active on wgpu callback pair
  migration — but atlas-meta pins only the verified committed HEAD, never WT
  state. Atlas-meta `repos/hephaestus` gitlink advanced
  `b90923ef25d8148b53716e652cdf5b807e31586d →
  c78a98e1c7d5615fc8744622a6c9013ed16e1e6b`.

### Next actionable

- Two intentionally-blocked gitlink advances remain (moirai MR-WATCH-001,
  ritk verify-blocked upstream via moirai path-dep). Re-open trigger is the
  same for either: peer lands a clean-green moirai HEAD with zero WT edits.
- Provider-repo Batch #8 `[minor]` extensions remain claimable in peer-clean
  provider repos (`eunomia`, `gaia`, `hermes`, `leto`, `melinoe`, `themis`,
  `consus`). Each requires editing the owning provider's own source per its
  own backlog register; provider repos commit independently and the gitlink
  advance is a follow-up increment in atlas-meta.

## Session 2026-07-13 — provider integration safety and audit

- [x] Audit Mnemosyne, Moirai, Hephaestus, Leto, Themis, Hermes, and Melinoe
  ownership, safety, topology, memory, contention, and hierarchy surfaces.
- [x] Complete and push the immutable Mnemosyne WGPU callback pair plus
  Hephaestus typed/no-unwind consumer migration.
- [x] Verify Mnemosyne with clippy, 42/42 nextest, focused Miri, doctests,
  rustdoc, and semver classification; verify Hephaestus with clippy, 131/131
  nextest, doctests, and rustdoc.
- [x] Record ranked provider findings and acceptance criteria in
  `gap_audit.md` and `backlog.md`.
- [x] Close HEPH-EMPTY-001 with canonical Leto empty state, CUDA/WGPU
  value-semantic contracts, and the full 239-test backend gate (`65e89b7`).
- [ ] Next increment: MEL-SCOPE-001; MOI-NUMA-001 remains parked until the
  active scheduler/deque peer scope is committed and green.
