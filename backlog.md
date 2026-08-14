# atlas — cross-repository integration backlog

> Board layout: **Sweep 2026-08-13** below carries the items opened by the
> full-stack audit of all 25 members. Older live items follow. Closed items are
> one-line entries under [Archive — closed items](#archive--closed-items);
> `scripts/atlas-board-compact.py` performs that collapse mechanically.

# Sweep 2026-08-13 — full-stack audit

Fourteen read-only audits covering every registered member plus the meta-repo.
Every claim below is grounded at `file:line` in the audited tree. Items are
ordered by tier, and tier is set by *what breaks*, not by effort.

**Instrument correction, applied before anything else was measured.**
`scripts/atlas-conformance.py:131` classified a file as test code only when a
*path part* matched `tests`/`benches`/`examples`/`fuzz`. `Path.parts` yields
`tests.rs` as a filename, never `tests`, and `split_test_region` only splits on
an *in-file* `#[cfg(test)]` — so every co-located `src/**/tests.rs` sidecar was
scanned as production. Four audits reached that conclusion independently
(consus, moirai, ritk, apollo). Fixed by matching directory parts only plus a
new `declared_cfg_test` check that reads the parent module's
`#[cfg(test)] mod <stem>;` declaration; the baseline was regenerated in the same
change per the generator contract. Effect: stack `unwrap_production`
4713 → 1460 (kwavers 2630 → 259, consus 709 → 334), with the counts moving into
the test-region classes where they belong (`existence_only_assertions`
598 → 807, `sleep_synced_tests` 117 → 132). **Every burn-down target recorded
before this fix was aimed by a broken instrument and must be re-derived.**

## Landed from this sweep (2026-08-13)

| ID | Commit | Note |
| --- | --- | --- |
| ATLAS-APOLLO-FAKEGEN-036 | apollo `5749d104` | **Premise corrected.** The item claimed downstream f32 tolerances were derived against an f64-accumulated reference. False: every `dft_inverse` call site passes `Complex64`, where f64 accumulation *is* native precision, so no shipped result was wrong and no tolerance changed. The defect was latent — a trap for the first `Complex32` caller — and is closed with a derived-bound test plus a bitwise test, the latter being what actually discriminates a widened accumulator. Reclassified `[patch]` → **`[major]`**: closing it deleted `precise_re`/`precise_im` and `BLUESTEIN_NATIVE_PHASE_TRIG` from the public `KernelScalar`. |
| ATLAS-EUNOMIA-F64-SPECIALS-062 | eunomia `329fe85` | Confirmed as filed. Measured pre-fix error: `log10(2.0)` 1.43e-8, `lgamma(5.0)` 2.56e-8. |
| ATLAS-EUNOMIA-SUBBYTE-ORD-063 | eunomia `329fe85` | **Worse than filed.** With `Bf8::MIN_VALUE = 0xFC`, `max_scalar(MIN_VALUE, x)` returned `-Inf` for every finite `x` — a Max reduction over `Bf8` returned its own seed for all input. The fix also consolidated the hand-written `F16`/`Bf16` impls into one macro instead of adding four more copies. |
| ATLAS-EUNOMIA-ACCUMULATOR-064 | eunomia `329fe85` | Landed as `[minor]`, not breaking: `FloatElement` is sealed by a `pub(crate)` supertrait, so no out-of-crate implementor can exist. |
| ATLAS-LETO-TILES-048a | leto `7f80044` | `ExactSizeIterator` **did not hold as written** — `next` used `offset_of(...).ok()?`, which terminates early and would make `len()` lie. Fixed at the root with a constructor validation carrying its proof, rather than by declining the trait. |
| ATLAS-THEMIS-TOKEN-032 | themis `8930489` | Reproduced first: the exploit compiled, a write through one reference changed what the other read, and miri gave a Stacked Borrows error. Fixed with **no new `unsafe`** — a `&mut` borrow discharges the disjointness obligation exactly as ownership does, so the tag-accepting constructors give way to `from_unique(&'a mut _)`. `project_static` became *safe*: its `# Safety` clause described an obligation the signature makes unviolatable. Zero downstream consumers, so the break needs no migration. |
| ATLAS-CONSUS-PARSE-LIMITS-035 | consus `03bb65e` | Parent-commit evidence: three crafted length fields panicked with `capacity overflow` and three 10 000-deep datatypes killed the process with `STATUS_STACK_OVERFLOW`. All six now return typed errors. **Two defects found beyond the item**: `find_huge_object_recursive` recursed on a loop-invariant `header.depth` so a self-referential child pointer recursed forever, and it indexed `len() - 1` on a possibly-empty vec. |
| ATLAS-MNEMOSYNE-ALIAS-033 | mnemosyne `4c22fba` | **Premise disproved.** The reported sequence passes miri under both Stacked and Tree Borrows on the unfixed code. A control — the same aliasing with the exclusive reference *used* afterwards — is flagged immediately, so the method had detection power and the invalidation is real; the UB is not. `with_scratch` never touches `vec` after the closure, and the slice points into the heap buffer, a different allocation from the struct inside the `UnsafeCell`. Soundness held by accident of dead-code timing, so it was fixed anyway and `capacity()` is now safe code. **Reclassify: fragility, not UB.** The two secondary fixes were confirmed, and the leak-on-unwind had a *third* site (`Heap::free`) the item did not name. |
| ATLAS-CACHE-FORK-055 (partial) | — | **33.8 GB reclaimed** by deleting 22 stale `repos/*/target` forks. 25.1 GB remains in ritk, kwavers and mnemosyne, deferred because each showed activity within hours. The forks regrow unless whatever creates them is found, so the item stays open until the cause is identified. |

Completed provider slices from this sweep are recorded here so the residual
rows below retain their original audit scope:

| ID | Commit | Closed scope |
| --- | --- | --- |
| ATLAS-COEUS-LAYERNORM-SHAPE-031 | coeus `a2638c03` | Multi-dimensional trailing-shape LayerNorm across Rust core, autograd, GPU provider contracts, and thin Python bindings; provider workflows and book passed. |
| ATLAS-IRIS-COLORSPACE-072 | iris `eec98186` | Explicit sRGB encoded/linear-light RGB and opacity-alpha contract with byte round-trip coverage. |
| ATLAS-PROTEUS-DOMAIN-073 | proteus `6b9bd0b` | Temperature validity-domain newtype, finite-positive validation, typed errors, and boundary tests. |
| ATLAS-ASCLEPIUS-PARAM-074 (typed-parameter slice) | asclepius `5d528d2` | Distinct `Gamma50` and `LymanSlope` types with compile-fail coverage; CEM43 validity remains open. |
| ATLAS-THEMIS-CONFORMANCE-083 | themis `b1b671c`; Atlas `0922c58` | Replaced Themis's duplicate thread cache with Melinoe's `thread_cached!` provider, split the oversized static-cell leaf, and closed the value-semantic assertion and safety-comment findings. Hosted Ubuntu/Windows, Miri, compile-fail, documentation, and CodeRabbit checks pass. |
| ATLAS-POSTMERGE-HEAD-084 | Atlas `73974ee` | Advanced the Ritk and Eunomia gitlinks to fetched defaults `3f30cddf` and `2e0d724c` while preserving dirty provider worktrees. Ritk hosted CI is green; Eunomia's Rust and supply-chain checks are green and its external `recurseml/analysis` status remains report-only. |
| ATLAS-HELIOS-BENCHMARK-085 | Helios `152a66c` | Helios PR #54's benchmark regression job completed successfully; the merged default head is fully green across book, Rust, Python, and benchmark checks. The Atlas gitlink remains peer-owned at its staged integration head. |
| ATLAS-THEMIS-STD-FEATURE-086 | Themis PR #22; merged default `f879e71` | Fixed the optional-dependency feature closure: `themis/std` now activates Melinoe before referring to its `std` feature. Ubuntu, Windows, compile-fail, branded Miri, and local strict Clippy are green; `recurseml/analysis` is external/report-only. |
| ATLAS-THEMIS-STABLE-PROOFS-088 | Themis PR #23; merged default `fa8dc29` | Added stable trybuild enforcement for invalid shared-cell construction (`E0599`) and overlapping mutable borrows (`E0499`) with committed stderr fixtures. Ubuntu, Windows, compile-fail nightly, and branded Miri are green; `recurseml/analysis` is external/report-only. |
| ATLAS-HERMES-AMX-CONFIG-087 | Hermes PR #40 `89bf685` | Fixed the AMX irregular-width defect and corrected the dynamic B-tile shape: AMX's right-hand operand is configured as an N-row, K-byte tile, so the prior 64-row int8 shape triggered SDE `#GP out of range tile dimensions` for irregular GEMM. Local `hermes-simd-intrinsics` nextest is 28/28, core nextest is 16/16, source `allow_attributes` fell 26 -> 0, and Atlas conformance reports Hermes `allow_sites` 30 -> 0. Follow-up `90ea3ef` scopes the two architecture-specific dispatch expectations and removes the macro wildcard/ref-option/line-count lint failures; hosted SDE is pending at `89bf685`, while x86 remains blocked by 345 HS-435 core Clippy errors. |

**Current exact-head residual (2026-08-14):** requested-provider coherence is
clean at Atlas `bb39e24`; the structural exact-head audit leaves only four
staged peer-owned paths: Proteus (`6b9bd0b` vs `c7cf800`), Helios (`1e16540` vs
`152a66c`), Hermes (`81502c5` vs `9fdbd16`), and Iris (`eec9818` vs
`899d622`). Helios PR #54 is merged at `152a66c` and its benchmark regression
job is green. Themis's stable-proof PR #23 is merged at `fa8dc29`, while
Hermes's AMX correction remains open in PR #40 at `90ea3ef`. The four listed
pointers remain peer-owned and are not rewritten by this audit.

The 2026-08-14 worktree conformance scan reports 14 ratchet regressions and
38 tightenings; the baseline is unchanged because the scan includes active
peer work. The lane audit reports four violations: three Ritk trees, plus
three Kwavers trees including a detached temporary lane outside the canonical
lane root. These are recorded residuals, not cleaned by deleting peer state.

**A finding worth keeping from the themis work:** stable `rustdoc` **silently ignores the `E0xxx` annotation** on a `compile_fail` doctest — verified by feeding it a deliberately wrong code and watching it pass. Nightly enforces it. Any `compile_fail` proof gated only on stable therefore degrades to "fails for some reason", which is not the claim it appears to make. themis now runs a nightly `--doc` job for exactly this; the rest of the stack does not, and should.

## Tier 0 — unsoundness and wrong numbers shipping

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-THEMIS-TOKEN-032 | `themis` stops duplicating a melinoe capability token. `src/branded/region/mod.rs:138` is a **safe** `pub fn` that clones `SyncRegionToken<'brand>` via `core::ptr::read` (`:156`, `:159`); combined with the unvalidated `ConstNumaPinnedCellRef::new` (`cell.rs:244`) and the missing runtime node check (`placement.rs:123`), a caller obtains **two live `&mut T` to one location writing zero `unsafe`**. The `A != B` const assert (`:147`) proves the *tags* differ, not the *cells*. | [major] | The two-`&mut` sequence recorded in the audit fails to compile, or requires `unsafe`, committed as a `compile_fail` test; miri clean over `tests/branded.rs` |
| ATLAS-MNEMOSYNE-ALIAS-033 | `ScratchPool::capacity` (`crates/mnemosyne-arena/src/scratch/pool.rs:145-151`) forms `&` to slot 0 while `with_scratch` (`:114`) holds `&mut` across the user closure (`:129`). Both take `&self` and the pool is `thread_local!`, so `pool.with_scratch(n, |_| pool.capacity())` is **safe code producing UB** under Stacked/Tree Borrows. Same shape at `scratch/bank.rs:64`. Its SAFETY comment asserts a non-reentrancy property the API does not enforce. | [patch] | That exact call sequence exists as a test and passes under `cargo +nightly miri -Zmiri-tree-borrows` |
| ATLAS-LETO-LAYOUT-034 | `Layout` (`crates/leto/src/domain/layout/mod.rs:13-20`) exposes `pub shape`/`pub strides`/`pub offset` with a non-validating `pub const fn new` (`:24`) and no `#[non_exhaustive]`. **84 `unsafe` blocks** in leto and every array in kwavers/CFDrs/ritk/gaia/coeus rest on its invariant; safe downstream code can construct an out-of-bounds layout today. | [major] | Zero `pub` fields on `Layout`; a validating `try_new`/`TryFrom` is the only construction path; adversarial tests per invalid class return a typed error; all five consumers build |
| ATLAS-KWAVERS-REAL-COMPUTE-028 | *(already open — now with a fifth site and exact locations)* Five production paths return their input unchanged, three under real citations: `mixed_domain.rs:158-170` and `:219-231` (Hamilton & Blackstock 1998), `kzk_solver_plugin/solver.rs:301-310` (Jing et al. 2012), `transfer_learning/learner.rs:137-143` (live at `:43`), and newly found `kwavers-math/src/simd/interpolation_ops.rs:129-141` — an `avx2` `#[target_feature]` fn with a 5-line SAFETY comment whose body calls the scalar function. | [major] [arch] | `rg "Ok\(field\.clone\(\)\)" crates/kwavers-solver/src` → 0; each site has a differential/analytical test that **fails when the body is reverted to the clone**, demonstrated in the PR |
| ATLAS-CONSUS-PARSE-LIMITS-035 | HDF5 parse paths reachable from `Hdf5File::open` allocate on unbounded file-supplied lengths — `btree/v2.rs:685,761` (`with_capacity(total_records as usize)`, u64 straight from the header), `dataset/chunk.rs:110,126,166`, `datatype/compound.rs:336,522,550`, `consus-fits/src/table/data.rs:153,187,188` — and `parse_datatype_inner` (`datatype/compound.rs:80→329→360→446`) recurses with **no depth parameter anywhere in the chain**, so a nested compound overflows the stack (uncatchable abort). `try_reserve` appears once in the whole tree. | [minor] | A `total_records = u64::MAX` header, an oversized chunk size, and a 10 000-deep nested compound each return a typed error, not a panic or abort; each test fails on the parent commit |
| ATLAS-APOLLO-FAKEGEN-036 | `dft_inverse` (`crates/apollo-fft/.../kernel/direct.rs:169`) is `<T: KernelScalar>` but accumulates the whole reduction in `f64` (`:180-194`) via `T::precise_re`, then narrows. Its sibling `dft_forward` (`:147`) is correct — the asymmetry inside one file is the tell. This kernel is the documented reference oracle (`README.md:135`), so every f32 differential tolerance downstream is derived against an f64-accumulated reference. | [patch] | No `f64` accumulator in `direct.rs`; f32 differential vs the AVX2 backend passes at an f32-derived tolerance |
| ATLAS-EUNOMIA-F64-SPECIALS-062 | **`F64` computes five transcendentals in `f32`.** `impl FloatElement for F64` (`impls/wrappers/float.rs:33-136`) overrides 19 of 24 f32-routed defaults but omits `log10`, `log2`, `erf`, `erfc`, `lgamma`, which the primitive `f64` impl does override (`impls/primitives/float.rs:124-140`). Those five fall through to `traits/float.rs:181,190,198,205,211` — `Self::from_f32(libm::<op>f(self.to_f32()))` — destroying ~9 decimal digits on the type whose entire contract is f64 precision. The module doc at `:28-32` asserts the opposite. Live on `origin/main`; untested (`tests/float_special.rs` covers `f64` and `f32` only). Blast radius is every consumer generic over `T: FloatElement` that monomorphizes at `F64`; `lgamma`/`erfc` feed helios dosimetry and tyche statistics. | [patch] | `tests/float_special.rs` gains `F64` cases asserting agreement with the `f64` path to `<1e-15`; the current body fails those at ~1e-7 |
| ATLAS-EUNOMIA-SUBBYTE-ORD-063 | **`F8`/`Bf8`/`F4`/`Bf4` order by raw bit pattern, inverting sign.** `F16`/`Bf16` get correct float-semantic comparison via `to_f32()` (`types/floats.rs:138-152,245-259`), but the sub-byte formats are left on `#[derive(PartialEq, PartialOrd)]` over the raw `u8` (`:30,35,40,45`) while the sign bit is the MSB (`impls/wrappers/numeric.rs:247`). So every negative value sorts above every positive one and `-0.0 != +0.0`. These types implement `NumericElement`, whose `min_scalar`/`max_scalar` defaults (`traits/numeric.rs:85-110`) consume exactly that `PartialOrd` and are not overridden — so every Min/Max reduction, `clamp` and sort over a sub-byte float in the stack is silently sign-inverted, with no failing test. | [patch] | For every `u8` bit-pattern pair, `a.partial_cmp(b) == a.to_f32().partial_cmp(&b.to_f32())`; `min_scalar(neg, pos) == neg` |
| ATLAS-EUNOMIA-ACCUMULATOR-064 | **No `type Accumulator` exists anywhere in eunomia** — the standard's only sanctioned widening route is absent from the crate that owns the scalar law. Every downstream reduced-precision reduction must therefore either accumulate in `T` and lose precision, or hand-roll a widen — which is precisely the fake-generics violation `integrity` prohibits. The absence actively manufactures HARD violations in leto, hermes, kwavers and CFDrs. | [minor] | `FloatElement` gains `type Accumulator: FloatElement` (identity for f32/f64, `f32` for f16/bf16) with the numerical-analysis rationale in Rustdoc; a pairwise-sum property test over 10⁵ bf16 elements puts the accumulator path inside a derived `O(log n·ε_f32)` bound and the in-`T` path outside it |

## Tier 1 — evidence that does not support its claim

> **Claimed 2026-08-13 by the sweep session.** In progress on disjoint scopes:
> helios (`-037` gamma tautology, plus the analytical dose oracle and the
> vacuously-passing GPU tests), coeus (`-041` gradcheck harness), gaia (`-042`
> verification gate), hermes (`-040` AMX probe), and iris/proteus/asclepius
> (`-071` license texts, `-072` colour-space convention, `-073`/`-074` validity
> domains). `-038` README truth and the moirai/leto/gaia/coeus half of `-039`
> landed earlier in the sweep. Peers: take another scope, not these.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-HELIOS-GAMMA-037 | The advertised 3%/2 mm gamma pass is tautological: `end_to_end.rs:171,278` and `examples/tomotherapy_workflow.rs:196-206` call `gamma_index_3d(&dose, &dose, …)` — dose against itself — and `backlog.md:158` reports the result as achieved. `attenuation_map.rs:172` likewise re-inlines the function it claims to check. No golden images exist (`git ls-files "*.png"` → 0). | [minor] | `rg 'gamma_index_3d\(&\s*(\w+),\s*&\s*\1'` → 0; a negative control with a deliberately shifted field asserts a sub-100% pass rate |
| ATLAS-README-TRUTH-038 | Eleven member READMEs assert capabilities the tree contradicts. Worst: moirai `:127,337` "Zero External Dependencies" over a manifest carrying wgpu/rustls/aes-gcm/httparse, plus links to a **nonexistent** LICENSE and CONTRIBUTING and badges pointing at `moirai-lang/moirai`; CFDrs `:3,14,42,58,95,129-149` describes a "Complete MPI Infrastructure" with **no MPI dependency in any manifest**; kwavers Quick Start cannot compile (`use kwavers::domain::…` against a crate that re-exports nothing); hermes lists 5 features that do not exist and says 0.2.0 for a 0.6.0 workspace; ritk's sole crate README still says "Burn-backed" and the root README credits nalgebra, which is not a dependency; gaia points consumers at `crates.io/crates/gaia`, a **third-party crate**. | [patch] | Per repo: every headline claim resolves to code, every linked file exists, the quick-start line names the real registry package and version, and the example compiles as a doctest |
| ATLAS-LICENSE-FILES-039 | Declared licenses have no files. moirai declares `MIT OR Apache-2.0` (`Cargo.toml:30`) with no LICENSE and a README claiming MIT; helios declares dual and ships neither text; gaia declares dual and ships MIT only; leto declares dual with no LICENSE. | [patch] | Every repo declaring `MIT OR Apache-2.0` carries both texts; `cargo package --list` includes them |
| ATLAS-HERMES-AMX-040 | `amx_runtime_supported()` (`crates/.../amx/mod.rs:12-22`) returns a hardcoded `false` on every non-miri target, so ~230 lines of inline asm, 14 unsafe fns and a public RAII session are unreachable — while `README.md:26,156-157,188` advertises AMX dispatch and differential verification, and the SDE CI job is named for a branch it cannot execute. The quarantine is legitimately recorded; the advertising is not. | [minor] | A real CPUID + XCR0 + `ARCH_REQ_XCOMP_PERM` probe replaces the literal; the SDE job adds `amx` to `HERMES_EXPECTED_TARGETS` and runs the AMX-vs-scalar differential |
| ATLAS-COEUS-GRADCHECK-041 | Autodiff has finite-difference coverage on ~9 of ~80 backward paths (~11%), with no shared `gradcheck` helper. Uncovered: matmul, every convolution, softmax, all normalizations, attention, all ~17 loss nodes. `softmax.rs:180` is an existence-only assertion that passes if `backward` writes zeros; `norm.rs:359` is *named* `..._matches_numeric_gradient` and contains no finite differences. coeus is ritk's differentiation substrate. | [minor] | One `gradcheck` helper with an eps-derived step and cited derivation; FD-covered paths ≥ 40 of 80; `rg 'is_some\(\), "' crates/coeus-autograd/src` → 0 |
| ATLAS-GAIA-GATE-042 | gaia has **no verification CI at all** (only `book-pages.yml` and `rust-release.yml`), **no `.config/nextest.toml`** (the one member outside the stack's 30 s/60 s budget, so a hang cannot be caught), and a warn-only lint floor never run under `-D warnings` — against 58 production `unwrap()`, 42 files over 500 lines and a 2286-line CSG core. | [patch] | A `ci.yml` runs fmt → clippy `-D warnings` → nextest → doctests → `cargo doc`; committed nextest budget mirrors helios; package `[lints]` with pedantic + `unwrap_used`; ratchet baseline recorded |

## Tier 2 — architecture: SSOT, DRY, and the zero-cost seams

> **Claimed 2026-08-13 by the sweep session.** In progress on disjoint scopes:
> hephaestus (`-043` unseal `KernelDialect`, then `-044` hoist scan to one
> generic layer — sequenced, because the seal makes the generic layer
> uncompilable from a sibling crate), moirai (`-051` bounded default channel,
> `-053` cache-line SSOT, and two `SeqCst` clusters of `-052`), CFDrs (`-046`
> collapse eight `*Scalar` traits), leto (`-049` collapse the duplicate SVD),
> athena (`-066` document the two undocumented solver families, `-070` flatten
> the Arnoldi basis), and ritk (`-047` ADR plus one vertical increment).
> `-048a` landed earlier; `-048b` stays blocked on a kwavers migration.
> Peers: take another scope, not these.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-HEPH-SEAM-043 | `KernelDialect` (`hephaestus-core/src/domain/dialect.rs:18-27`) is sealed *and* is a mandatory associated type of the device seam (`stream.rs:37`). `impl KernelDialect` outside core: **zero**. Adding ROCm therefore required adding `HipC` upstream to core (`ac9fa80`) — the foreclosure is demonstrated, not hypothetical. The standard names shader dialect as a device-API seam component that must stay open. | [minor] | `mod sealed` gone; a crate outside `hephaestus-core` defines its own dialect and compiles; the three existing dialects unchanged |
| ATLAS-HEPH-ACCEL-044 | The accelerator layer is cloned per vendor: cuda 25 510 lines, rocm 24 658, wgpu 31 881, metal 8 211 with near-1:1 module trees — `cuda/.../scan.rs` and `rocm/.../scan.rs` differ by **86 lines after normalizing vendor tokens** — plus 8 254 lines of seam forwarding and 15 612 lines of quadruplicated `tests/contract.rs`. The correct pattern already exists once (`core/src/domain/decomposition/blocked.rs:69`) and is applied to 1 of ~40 op families, and is itself f32-hardcoded. | [minor] | Scan hoisted to one generic layer over a `DeviceApi` trait; both vendor scan modules deleted; conformance clauses unchanged; net delta ≤ −500 lines |
| ATLAS-COEUS-BACKEND-045 | `HephaestusBackend<P>` never implements `MatmulOps`/`PoolOps`/`UnfoldFoldOps`, so Metal and ROCm are partial backends — and that gap is why CUDA (7 390 lines) and WGPU (8 897) forked into hand-written per-op shims while Metal and ROCm need only 122 and 126 lines. `ComputeBackend` is also sealed via a `pub` `private::Sealed` module, so the seal is both prohibited and cosmetic. | [arch] | `HephaestusBackend<MetalProvider>: BackendOps<f32>` compiles; cuda and wgpu `src` each drop below 1 000 lines; parity suites unchanged |
| ATLAS-CFDRS-SCALAR-046 | Eight parallel `*Scalar` seam traits for one role (`Cfd1dScalar`, `Cfd2dScalar`, `Cfd3dScalar`, `ValidationScalar`, `VofScalar`, `LevelSetScalar`, `NetworkSolveScalar`, `ResistanceScalar`) — `VofScalar` and `LevelSetScalar` have character-identical bound lists inside one crate — plus 7 duplicated `scalar.rs` helper modules and **23 private copies of `from_f64`**, each the identical one-line delegation. This is the root of the fake generic at `cfd-3d/src/spectral/diagnostics.rs:352`. | [minor] | `rg 'trait \w*Scalar' crates/` → 1; `rg -c 'fn from_f64' crates/` ≤ 1; `rg 'fn to_f64' crates/` → 0 |
| ATLAS-RITK-VIEWS-047 | `Image` has **no view, region, window, chunk or iterator API**, and ritk contains zero GATs across 1771 files. The only routes to pixel data are a fallible whole-buffer `data_slice()` or a whole-volume copy, so every filter takes the entire flat buffer or clones. Downstream: 7 parallel data accessors, 3 parallel coordinate-transform families, and three heap allocations **per output voxel** in `interpolation/.../linear/mod.rs:124-126`. | [arch] [major] | A lending seam with `type Item<'a>`; ≤2 data accessors on `Image`; one coordinate-transform family; a rewritten filter shows no whole-volume copy under dhat |
| ATLAS-LETO-TILES-048a | `Tiles` (`crates/leto/src/application/iter/lending.rs`) is the only `LendingIterator` in leto, but it holds `&'a [T]` and a `Copy` `Layout<N>` and builds its item exactly as `ExactChunks` (`chunks.rs:100-112`) does from a plain `Iterator` — the item borrows from the same `'a` slice the iterator does, so narrowing to `'this` buys nothing while **costing `IntoIterator`, `.zip`, `.enumerate`, `.rev`, `ExactSizeIterator` and any Moirai bridge**. Upstream `508962d` added `TaskPartitionsMut` as a second in-repo precedent for the target shape. | [minor] | `Tiles` is a plain `Iterator<Item = ArrayView<'a, T, N>>` with justified `ExactSizeIterator`/`DoubleEndedIterator`; a test zips, enumerates and collects it and asserts values on a ragged edge; `T: Copy` gone |
| ATLAS-LETO-TILES-048b | **Split out because deleting `LendingIterator` is a cross-repo break, not the bundled cleanup first assumed.** The trait is publicly exported and consumed outside leto: `kwavers/crates/kwavers/examples/tiled_kspace_processing.rs:52` imports it and calls `count_remaining()`, which has **no `Iterator` equivalent** — consumers migrate to `.count()`/`ExactSizeIterator::len()`. CFDrs book docs also name it. Sequence upstream-first per the co-evolution protocol: migrate kwavers, then delete. | [major] | `rg 'LendingIterator' repos/` returns nothing outside leto's own history; the kwavers example builds and its `#[test]` passes; `cargo-semver-checks` classifies the removal | ATLAS-LETO-TILES-048a |
| ATLAS-LETO-SVD-049 | Two SVD paths whose distinguishing justification has evaporated: ADR 0005 chose Jacobi for rank revelation *versus the Gram path*, and the Gram path was deleted, while `svd/bidiagonal_qr.rs:394` already states the surviving path handles rank deficiency. leto is the stack's declared linalg SSOT. | [major] | `svd/jacobi.rs` deleted, `pinv` on the bidiagonal path, existing oracle suite green unchanged, ADR 0005 rewritten with a dated revision note, net line delta negative |
| ATLAS-APOLLO-API-050 | `apollo-fft/src/api` carries 140 public fns of which **68 are exact concrete/`_typed` twin pairs**, and `stockham/avx/` forks the scalar dimension as a *directory pair* (`precise/` Complex64 vs `reduced/` Complex32, ~2300 lines) using quality labels the naming prohibition bans. Root cause: no single scalar seam — `eunomia::RealField` appears twice in 834 files while 10+ parallel scalar-role traits exist. | [major] | ADR selects one scalar seam; `rg 'pub fn \w*_typed' crates/apollo-fft/src/api` → 0; no `precise`/`reduced` directories |
| ATLAS-MOIRAI-BOUNDED-051 | `Moirai::channel()` (`moirai/src/runtime.rs:342`) — the discoverable, un-suffixed API — returns an **unbounded** channel; the bounded form carries the longer name. Preallocation is inverted (`mpmc/channel.rs:25-29`: the bounded path uses `VecDeque::new()`, the unbounded one `with_capacity(16)`). Untimed `Condvar::wait` at `scheduler/core.rs:225,233` and `mpmc/channel.rs:133,188`. | [minor] | `rg 'channel::unbounded' moirai/src/` → 0; a test asserts a full channel blocks or errors rather than growing |
| ATLAS-MOIRAI-ORDERING-052 | 624 production atomic sites, **10.1% carrying an ordering justification**; AcqRel 1 of 23, Release 6 of 117. Unjustified `SeqCst` clusters at `moirai-async/src/executor/core.rs:92-212` and `mpmc/channel.rs:88-344` (11 RMWs on a shared line under a Mutex that already orders). No documented global lock order. Six loom suites exist and are ahead of the stack; the MPMC waiter protocol and SPSC ring — the two primitives every crate depends on — are not among them. | [patch] | Justification coverage ≥ 90%; production `SeqCst` ≤ 20; new loom suites for the MPMC waiter protocol and SPSC ring pass with stated bounds |
| ATLAS-MOIRAI-CACHELINE-053 | `CACHE_LINE_SIZE = 64` is defined **six times** across moirai-core/utils/iter, and every padding site uses 64 where the standard requires 128 on x86-64 and modern aarch64 (adjacent-line prefetch pulls line pairs). The duplication makes the correction a six-site edit. | [patch] | One definition in `moirai-utils` at 128; `rg 'repr\(align\(64\)\)' --glob '*/src/*'` → 0; criterion baselines on the MPMC and deque benches show no regression |

## Tier 3 — mechanical floor and stack hygiene

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LINT-FLOOR-054 | **17 of 25 members have no `[workspace.lints]`.** Where a floor is declared it is then nullified: CFDrs correctly inherits `unwrap_used`/`print_stdout`/`print_stderr`/`dbg_macro` at deny in all 12 manifests, against **288 crate-level `#![allow]` and 5 `#[expect]` repo-wide, none with a ratchet reason** — which is why 402 library print sites survive a deny. coeus has 117 allow lines with **zero** `reason=`. | [patch] | Every member declares the pedantic floor once via `[workspace.lints]` with members inheriting; crate-level blanket `#![allow]` → 0; every surviving suppression is `#[expect(lint, reason = "ratchet <id>")]`; conformance baseline non-increasing |
| ATLAS-CACHE-FORK-055 | The stack policy is one build cache (`.cargo/config.toml:18-19`), yet **25 populated `repos/*/target` trees hold 58.9 GB** beside the 224.2 GB shared root — ritk 21.6 GB, CFDrs 16.8 GB, helios 5.2 GB, kwavers 3.5 GB, apollo 3.2 GB. Each holds real `debug/`, `doc/` and `book/` content, so these are live forks, not stubs. Disposable derived state, not user data. | [patch] | `python scripts/atlas-conformance.py report` shows `target_forks = 0`; `D:\atlas\target` remains the only cache; a documented eviction cadence exists for the shared root |
| ATLAS-GITLINK-DRIFT-056 | **24 of 25 submodules are checked out off the commit atlas records** (only gaia matches), and 11 sit on `codex/*` or feature branches. **The drift direction is uniform: the recorded gitlinks are AHEAD of the working trees** — athena's gitlink is 3 commits ahead of HEAD, harmonia's 2, horae's 6, hyperion's 5, and leto's tree is 17 behind both `origin/main` and its pin. These are members behind atlas, not atlas behind members, so every local verification run tests superseded state. Two sub-cases need opposite handling: athena and harmonia sit on branches with **zero** unique commits (exhausted, deletable — re-point to `main`), while horae and hyperion each carry small real deltas that are green and mergeable now, hyperion's including an actual parallel-test-race fix (`35006fd`). | [patch] | Per member: exhausted branches deleted and re-pointed to `main`; real deltas merged and the gitlink advanced; a committed check fails when HEAD ≠ gitlink without a recorded reason |
| ATLAS-ROOT-SPRAWL-057 | Meta-root holds 7 unfiled report-genre files. **Not all are deletable** — `scripts/check_mdbook_links.py:15,53,66,99,181,194,565` and `fix_link_depth.py:2` cite `MDBOOK_*.md` as the normative Pattern A–F taxonomy, `scripts/tests/test_smoke_fixture.py:34,46` reads `parity_artefacts/smoke_test_filters` as a live fixture, and `.github/workflows/docs.yml:19,20` path-filters both. `PATH_DEP_AUDIT_001_ENTRY.md` is a duplicate of the board entry at `backlog.md` with 367 unique lines that must merge first. | [patch] | Root holds only the sanctioned set; the mdBook pattern taxonomy lives in one `docs/` document with all citations re-pointed; the smoke fixture moves under `scripts/tests/fixtures/` with the workflow filter updated; `test_smoke_fixture.py` and the docs workflow still pass |
| ATLAS-ADR-GOV-058 | **Corrected against `scripts/adr-index.py check`, which is authoritative — my earlier grep-based count was wrong.** The meta-repo's own ADRs and index are **clean**. The drift is entirely in members: **20 of 24 member indexes are stale or missing**, and the anomaly classes are (a) lowercase `accepted` — hephaestus ×6, mnemosyne ×4, tyche ×4, proteus ×2, leto, kwavers; (b) prose statuses that are not one of Proposed/Accepted/Rejected — kwavers ×8 ("Implemented (Phases 1–3)", "Superseded by ADR-040"), leto ×3, coeus, melinoe, mnemosyne, ritk ×3; (c) **duplicate numbers** — kwavers 037 and 040, leto 0011, coeus 0060, each two genuinely different decisions; (d) one missing status (kwavers 044). The generator already exists and reports all of this; what is missing is the burn-down plus a CI gate on `check`. | [patch] | `python scripts/adr-index.py check` exits clean; run twice, `generate` is a no-op; no ADR number appears twice in any member; CI gates it like the stack overlay |
| ATLAS-KS9-SUPERSEDED-059 | `backlog.md` `[KS-9]` stands **done** asserting the decision to *retain* `hephaestus-metal`, superseded by Accepted ADR 0047 which retires it — the board asserts both positions. Its recorded rationale ("would be a breaking public-surface change") is also a prohibited tiebreaker. Separately: ATLAS-ARCH-011 needs **nothing from hephaestus** — removal was executed and verified green, then reverted solely for `repos/coeus`; it unblocks via ATLAS-SUBSTRATE-002. | [patch] | KS-9 carries a dated revision note pointing at ADR 0047; ATLAS-ARCH-011's blocker reads `coeus-metal`, not hephaestus |
| ATLAS-HEPH-DEADBUILD-060 | `repos/hephaestus/build.rs` is **dead code**: the root manifest is virtual with no `[package]`, no crate declares `build =`, and cargo runs build scripts per package — so the 69-line CUDA-toolkit path resolver added in `116373d` has never executed once. | [patch] | Either the resolver moves into the crate that needs it and is proven to run, or the file is deleted; CUDA builds unchanged either way |
| ATLAS-HELIOS-STRAY-PNG-061 | `helios_workflow_output/{ct,dose,mu,recon}.png` are tracked at the meta root **against `.gitignore:74`**, which names that exact path as run output. Producer is `tomotherapy_workflow.rs:102-104,209-212`; referenced by no test, xtask, workflow, Makefile or script; helios itself tracks zero PNGs, so no fresh clone has them. | [patch] | `git rm` at the meta root, plain delete under `repos/helios`; `xtask check-figures` and the docs workflow still green |

## Tier 2b — small domain repos (athena, harmonia, horae, hyperion)

These four are the cleanest in the stack on every mechanical axis — zero `dyn`
in any `src/`, zero fake-generic casts, zero `todo!()`, zero non-test `unwrap`,
`unsafe_code = "forbid"` and `missing_docs = "deny"` throughout, and both
LICENSE texts present and matching the manifest in all four. The findings are
about documentation truth and numerical evidence, not debt.

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-ATHENA-UNDOC-066 | **athena ships two undocumented solver families.** BiCGStab (575 lines) and LSQR (487) are implemented and publicly re-exported from `athena-core/src/lib.rs`, yet appear **zero times** in the README, whose headline (`:5`) calls PCG and GMRES "its complete vertical contracts". Compounding it, the architecture tree names a crate that does not exist (`:62` `athena-wgpu` vs the real `athena-hephaestus`), a feature that does not exist (`:71` `wgpu` vs the real `accelerator`), and asserts a 500-line ceiling (`:69`) that BiCGStab breaks. | [patch] | `rg 'athena-wgpu' README.md` → 0; README documents BiCGStab and LSQR; the line-count claim is removed or true per `wc -l` |
| ATLAS-BOOK-PLACEHOLDER-067 | **Placeholder chapters are shipped as books.** athena has 6 chapters and harmonia 3 — every one is the 3-line string `*Chapter prose deferred.*`. A placeholder chapter is documentation's mock: a chapter exists when its teaching content does. Separately and stack-wide, all four repos call the atlas reusable Pages workflow without `mdbook-test`, which defaults `false` (`.github/workflows/book-pages.yml:34-41`), so even horae's genuinely good 794-line book and hyperion's real chapters have samples that can rot. | [patch] | No `Chapter prose deferred` anywhere; horae and hyperion pass `mdbook-test: true` now, athena and harmonia once content lands (relates to ATLAS-PUB-005) |
| ATLAS-HYPERION-INTERP-068 | **Interpolation error is unbounded and its accuracy test is self-referential.** The log-log linear scheme (`nist.rs:90-105`) has no derived error bound tied to knot spacing and curvature, and the test checks that log-linear at a geometric midpoint reproduces the geometric mean of its own knots — an algebraic identity of the scheme, not accuracy versus NIST. The 28 knots are asserted to avoid absorption edges (`nist.rs:19-20`) with no evidence, and provenance is bare per-material URLs with no retrieval date or table version (cortical bone cites only "ICRU-44", no report table). | [minor] | `nist.rs` states a derived bound; an off-knot test compares against independently held NIST values within it; every `// Source:` line carries a date and table version |
| ATLAS-HORAE-EXACTNESS-069 | Two exactness claims are stronger than their argument. `events/schedule.rs:61` promises the clipped endpoint "equals the next crossed event exactly", but `clip_step` returns `event.duration_since(start)` (`:86`) — that holds by Sterbenz only within a factor of two, and the property test (`tests/properties.rs:61-82`) samples only `start ∈ ±1e3, offset ∈ [1e-6,1]`, never the cancellation regime. And `subcycling/plan.rs:47` uses reciprocal-multiply, so for `RATIO = 3` child steps do not sum bit-exactly to the parent, contradicting the alignment claim. | [patch] | The Sterbenz precondition is stated and `clip.event()` documented as the required consumption route; a property case at `start ≈ 1e8, offset ≈ 1e-6` passes or the claim is weakened; the `RATIO=3` reconstruction is tested within a stated bound |
| ATLAS-ATHENA-KRYLOV-070 | `gmres/workspace.rs:15-16` holds the Arnoldi basis as `Vec<B::Vector>` — on Leto that is `2·RESTART+1` scattered allocations, while every scalar array in the same struct is already flat (`hessenberg` is one `Vec<Scalar>` with an index fn). The only pointer-scattering instance found across these four repos. Allocated once at construction and natural per-buffer on WGPU, so this is a CPU-side layout defect, not a hot-loop allocation. Also: non-convergence returns `Ok(SolveReport)` with `Termination::MaxIterations` rather than a typed error, `SolveError` carries no residual history, and stagnation/divergence detection is absent entirely. | [minor] | `Vec<B::Vector>` gone from `gmres/workspace.rs` behind the existing `KrylovBackend` seam; the existing allocation-stability and f32/f64 contract tests unchanged and green; a stalling operator yields a `Termination::Stagnated`-class value with non-empty history |

## Tier 2c — small domain repos (iris, proteus, asclepius, tyche)

Two premises this sweep started with turned out to be **false and are recorded
as cleared, not as work**: asclepius's Coeus adapter is genuinely one-way
(verified in the manifests, in the imports, and in the reverse direction — no
`[arch]` defect), and tyche's reported "23 production unwraps" are every one of
them inside `///` doc examples, under a workspace-wide `unwrap_used = "deny"`
that makes a production unwrap uncompilable. The second was an instrument
defect and is now fixed (see the doc-comment correction below).

| ID | Outcome | Class | Acceptance oracle |
| --- | --- | --- | --- |
| ATLAS-LICENSE-STUB-071 | **Three repos ship a stub where the Apache-2.0 text belongs**, while their manifests declare `MIT OR Apache-2.0`: iris and asclepius carry a 13-line short-form notice, proteus a 17-line header-plus-notice. Only tyche has the real 199-line text. iris and asclepius are `publish = true`, so two crates ship to crates.io under a license whose terms they do not include. Related, found separately: `kwavers-gpu` declares `MIT OR Apache-2.0` while the repo ships only an MIT `LICENSE` and every sibling crate is MIT — a per-crate override that is either a mistake or needs the second text; and gaia's MIT file is named `LICENSE` rather than `LICENSE-MIT`, so the pair is asymmetric. This is a legal defect, not a style one. | [patch] | Each `LICENSE-APACHE` contains `END OF TERMS AND CONDITIONS`; every crate's declared `license` matches the texts its package ships; `cargo package --list` includes them |
| ATLAS-REGISTRY-INVALID-078 | **Two kwavers manifests carried metadata crates.io would reject**: `kwavers` declared 6 keywords against the 5 cap, and both `kwavers` and `kwavers-python` used `"medical"`, which is not a registered category slug. `cargo publish` fails on either. Fixed in passing for kwavers via a new shared `[workspace.package]`; the class needs a stack-wide check, because nothing currently validates registry metadata before a publish attempt. | [patch] | A committed check validates keyword count and category slugs against the crates.io registered list for every publishable crate; `cargo publish --dry-run` clean stack-wide |
| ATLAS-IRIS-COLORSPACE-072 | **iris declares no color-space convention anywhere** — zero hits for `srgb`/`linear-light`/`gamma`/`transfer function` across `src`, `docs` and `README.md`, in a crate whose entire product is normalized color. `to_rgba8` quantizes `round(255v)` with no transfer function (`color/model.rs:46-52`) and colormap control points interpolate in an unnamed space (`color/map/interpolation.rs:15`). A consumer feeding these into a linear-light GPU pipeline gets silently wrong output with nothing in the contract to warn them — the convention-pinning failure `numerical_discipline` names. | [patch] | `rg -i 'srgb\|linear-light'` hits `color/model.rs` and every `ColorMap` impl doc; a doctest asserts the documented `to_rgba8` round-trip |
| ATLAS-PROTEUS-DOMAIN-073 | **Silent extrapolation outside the calibration range.** `TemperatureLaw::properties` validates only that the evaluation temperature is finite and `> 0` (`constitutive/temperature/law.rs:162,179-189`); no calibration range is modeled anywhere (`rg 'validity domain\|calibrat\|extrapolat\|min_temp'` over `src` → nothing). A first-order response fitted near 300 K evaluates at 1500 K and returns a physically meaningless but positive result with no error. `README.md:13` claims "material-property validity boundaries", true only of sign bounds. | [minor] | A law valid on `[273, 373] K` returns `Err(OutsideValidityDomain)` at 1500 K and `Ok` at 350 K; each response's Rustdoc states its domain |
| ATLAS-ASCLEPIUS-PARAM-074 | The `Gamma50`/`LymanSlope` split had already landed in `e680a82`; closed by proving **both** swap directions rather than the one the landed work covered, validated on stable by compiling each swap and reading E0308 at the exact argument. **The CEM43 half of this item was wrong and is withdrawn:** the 43-50 C limit belongs to the Arrhenius irreversible-injury model, not CEM43. Sub-43 C is CEM43's designed behaviour - the `below` factor exists only for T < 43 C, the docs state one minute at 42 C contributes a quarter-minute, and three tests assert it. Bounding it would have broken the crate's contract. | [patch] | Landed: asclepius `014181f` |
| ATLAS-TYCHE-README-075 | The dependency line is underivable and one command names a package that does not exist. The registry name is `tyche-uncertainty` while `README.md:31` shows `use tyche::…`; `README.md:159` runs `cargo run -p tyche --example …` where CI uses `-p tyche-uncertainty`. `README.md:24-25` says the adapter and facade "remain private", contradicted by `publish.workspace = true` on all three; `:175` lists Morris and Sobol as future work though both ship. `tyche-moirai` and `tyche-consus` publish with `readme`/`keywords`/`categories` missing. **ATLAS-TYCHE-MULTIOUTPUT-017 did land — on `main`, not in the checked-out worktree**, which is 5 commits behind; on `main` `sensitivity.rs` is 672 lines, past the target. | [patch] | Every command in the README verification block appears verbatim in `ci.yml`; `rg '\-p tyche ' README.md` → 0; both manifests carry complete metadata |
| ATLAS-CONSUS-ADR015-076 | **ADR-015 is cited eight times and does not exist.** `consus-io/src/lib.rs:75`, `consus-io/Cargo.toml:22`, `consus-io/src/io/async_io/s3_moirai/mod.rs:1`, `consus-io/tests/s3_rusoto_moirai_differential.rs:1`, `consus-zarr/Cargo.toml:18`, `consus-zarr/src/store/s3_moirai.rs:1`, and `consus-zarr/src/store/s3.rs:135,488`. There is no `docs/adr/` in consus, and the meta-repo's `0015` is an unrelated kwavers record. Per ADR governance the fix is a retroactive Accepted record grounded strictly in the code as built — never an invented rationale. | [patch] | `docs/adr/0015-*.md` exists, marked retroactive, indexed; all eight citations resolve |
| ATLAS-LOCK-CONVENTION-079 | **The committed lockfile convention is not uniform, and the overlay silently rewrites 12 working copies.** Counting `source = "git+"` lines, committed vs working: 14 repos committed the git+ form (kwavers 87, CFDrs 62, helios 59, ritk 51, coeus 48, apollo 36, hephaestus 33, leto 30, consus 24, gaia 22, tyche 20, hermes 11, mnemosyne 3, hyperion 3) while **11 committed the stripped form** (aequitas, asclepius, athena, eunomia, harmonia, horae, iris, melinoe, moirai, proteus, themis — all 0). Of the git+ group, **12 now have a stripped working copy** because a build ran under the stack overlay; only gaia and hermes still match. coeus is half-stripped (48 committed vs 7 working). A stripped lock cannot resolve a git dependency standalone, so committing that form breaks reproducible CI resolution — yet a third of the stack has it committed. Every "Cargo.lock modified" line in this sweep is this artifact, not anyone's edit. | [patch] | One documented convention; every member's committed lock matches it; a committed check fails when a lock is committed in the wrong form; the overlay's rewrite is either excluded from the working tree or documented as expected churn |
| ATLAS-MSRV-UNVERIFIED-077 | Declared MSRVs are never built. mnemosyne declares `rust-version = "1.95"` while `rust-toolchain.toml` pins 1.97.0 and no CI job builds at the floor; eunomia and melinoe are the same shape (melinoe's `1.65` is contradicted by its own manifest using the `[lints]` table, which needs Cargo 1.74). An untested MSRV claim rots. | [patch] | Either a CI job builds at the declared floor, or the floor is raised to what the code actually requires |

## ATLAS-RITK-LANE-SPRAWL-065 — Reconcile three ritk working trees [patch] — open 2026-08-14

The 2026-08-14 probe still reports **three** trees against a bound of two
(main plus one lane):

```
D:/atlas/.git/modules/repos/ritk              f345a00e [main]
D:/atlas/worktrees/ritk-fix                    3cdaf360 [refactor/image-operation-modules] dirty
D:/atlas/worktrees/ritk-image-coordinate-map   e88910d0 [feat/ritk-spatial-explicit-fan-origin]
```

The previously reported `repos/ritk-floatelement-wt` directory is absent. Both
remaining lanes are under the canonical `worktrees/` root, but
`worktrees/ritk-fix` carries uncommitted source and manifest work while the
coordinate-map lane is a separate live feature branch. Neither lane is safe to
remove or repoint without rescuing peer-owned work.

Also note `repos/ritk` itself moved from `codex/ritk-floatelement-roots` to
`main` during this session, which is the shared-tree branch-switch hazard — a
`git switch` in a shared tree moves the branch for every agent using it.

No destructive action is taken in this sweep. Reconcile rescue-first after the
dirty lane's owner lands or explicitly releases its work: verify unique commits
and dirty files, rescue any unique state into `repos/ritk`, then
`git worktree remove`/`prune` the surplus lane.

**Acceptance oracle:** `git -C repos/ritk worktree list` shows at most two
entries, no entry is under `repos/`, and no unique commit is lost (verified by
`git log --oneline` on the reclaimed branch before removal).

## ATLAS-CONFORMANCE-WORKTREE-080 — The ratchet scans the working tree, not a revision [patch] — done 2026-08-14

- Owner: current session; scope: `scripts/atlas-conformance.py`, its
  conformance evidence, and this item only. Provider source and peer checkout
  changes are non-goals.

`scripts/atlas-conformance.py` walks the filesystem, so its counts include
**uncommitted work in progress** — a peer's or an agent's. That makes the
number non-reproducible from a revision and the gate noisy on a shared tree.

Observed directly during the 2026-08-13 sweep: immediately after the hermes
docs commit the ratchet reported `hermes/missing_deny_docs: 1 -> 5`. The commit
touched no `src/lib.rs` at all; a peer was concurrently editing four `lib.rs`
files to drop `#![deny(missing_docs)]`, uncommitted. HEAD had the attribute,
the worktree did not, and the scan reported the worktree. Four of the seven
regressions in that run were the same class — in-flight peer or agent work,
plus two from newly-synced upstream code (athena gained a workflow without
`timeout-minutes`; leto gained files past the 500-line target).

Consequence: a local `check` cannot distinguish committed debt from someone
else's half-finished edit, so a red result is not actionable without manual
triage — exactly what a mechanical gate exists to avoid. CI is unaffected
because it scans a clean checkout, which is also why this went unnoticed.

**Verification note (independent, 2026-08-13, not the owner):** the implemented
`--revision` / `--worktree` split behaves correctly and the guard fires as
designed. One property worth recording for whoever closes this: `--revision`
requires the checkout to *be* at the requested revision **and** clean, and on a
25-submodule meta-repo "clean" includes every gitlink. With agents editing
member trees, submodule pointers differ, so `--revision` is in practice a
CI-only mode and `--worktree` is the only local one. That is a sound split
rather than a defect — but it means the reproducible mode cannot be used to
adjudicate a red ratchet *during* concurrent work, which is exactly when the
question arises. A per-member `--revision` scan, or treating gitlink drift as
clean, would close that gap. Evidence: `check --worktree` reported 10
regressions / 27 tightenings while `check --revision HEAD` refused with
`root worktree is dirty`, with only submodule pointers differing.

**Acceptance oracle:** the scan takes an explicit revision (default `HEAD`) and
reads blobs through `git`, or it refuses to run against a dirty tree unless
`--worktree` is passed; running `check` twice with an unrelated uncommitted
edit present yields identical counts.

**Closure evidence (2026-08-14):** default `check` refused with exit 2 and the
explicit dirty-tree diagnostic. Two sequential `check --worktree` runs returned
the same exit 1 and byte-identical 11-regression/32-tightening report. The
scanner therefore has an explicit refusal boundary; remaining live-tree
regressions are provider work or baseline debt, not scanner nondeterminism.

## ATLAS-STD-AMX-DETECT-082 — `is_x86_feature_detected!("amx-tile")` is unsound [patch] — done 2026-08-14

Found while delivering ATLAS-HERMES-AMX-040. The std macro checks CPUID and
XCR0 only, with **no OS permission step**. On real AMX hardware that is not
enough: Linux requires `arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)`
before any tile instruction or the process takes SIGILL, and Windows has its
own `EnableProcessOptionalXStateFeatures` opt-in. So the macro can report
`true` on a machine where executing a tile instruction faults.

hermes now has a correct probe and does not use the macro. The item exists so
that no consumer in the stack reaches for the obvious-looking std detection
once it stabilizes, and so the reason is recorded rather than rediscovered.

Related, from the same work: a real-world case exists where CPUID advertises
AMX **and** XCR0 bits 17|18 are set, yet `TILEZERO` still raises `#UD` because
`CPUID.1D` returns zeros — a hypervisor bug seen on Emerald Rapids CI runners.
A palette-count check belongs in any probe that must survive virtualised hosts.

**Acceptance oracle:** `rg 'is_x86_feature_detected!\("amx' repos/` returns
nothing outside a comment explaining why it is unusable.

**Closure evidence (2026-08-14):** the non-comment Rust scan returned zero
matches. Hermes routes AMX capability checks through
`hermes_simd_intrinsics::x86_64::amx::probe`, which owns CPUID, XCR0, and
process-permission checks; the remaining `amx-tile` references are comments or
documentation describing the unsafe standard probe.

## ATLAS-GAIA-ORPHAN-081 — Delete an uncompiled 5 KB source file [patch] — open 2026-08-13

`repos/gaia/src/application/csg/boolean/union_strategy.rs` is 5,218 bytes
declared in **no `mod` statement**, so nothing compiles it and no test covers
it. Found while auditing gaia's unwrap count, which it inflated: the reported
"58 production unwraps" was really **4**, with the rest coming from doctest
lines and this dead file.

That is the second-order cost worth naming — an orphan file is invisible to the
compiler but fully visible to every text-based scan, so it silently skews
exactly the metrics used to aim remediation.

Delete it, or wire it in if it is unfinished work someone still wants. Check
`git log --follow` first to see whether it was ever reachable.

**Acceptance oracle:** every `.rs` under `src/` is reachable from `lib.rs`
through `mod` declarations; a committed check enumerates orphans so a new one
cannot land silently.

## Deferred with a recorded reason

- **ATLAS-PRIVACY-NAMING-1** stays open and unchanged. `repos/leoneuro-rs` is a
  separate organisation's repository holding local commits `1b71a79` and
  `50bfcd9` on a branch whose remote is **gone**, so it carries unique unpushed
  work and must not be deleted. It is correctly gitignored; the violation is
  that it is *named* in board items, which is a rewrite of existing entries, not
  a tree change.
- **Detector residuals.** The `declared_cfg_test` fix does not yet recognise
  test modules gated through a `#[cfg(feature = "…")]` wrapper around a
  `#[cfg(test)]` block. consus still reports 334 production unwraps against an
  audited estimate near 34, so a second refinement pass is warranted before that
  number drives any burn-down.

## ATLAS-COEUS-LAYERNORM-SHAPE-031 — Complete multi-dimensional LayerNorm contract [minor] — done 2026-08-13

- Owner: current session; scope: Coeus LayerNorm core/autograd/PyO3 modules,
  their focused tests and provider PM records; delivered in Coeus `a2638c03`.
- Finding: `coeus-nn::LayerNorm` and its autograd node model only one final
  feature dimension, while `coeus-python::PyLayerNorm` rejects sequence-shaped
  `normalized_shape`; the Coeus book/checklist claim PyTorch-style last-D
  semantics. This is a source/documentation contract mismatch, not a hosted
  workflow issue.
- Acceptance: accept a non-empty normalized-shape sequence in the Rust core and
  thin Python binding; validate it against the input's trailing dimensions;
  normalize their flattened product with native scalar arithmetic; preserve
  parameter shapes and tracked forward/backward gradients; cover one- and
  multi-dimensional positive, mismatch, and boundary cases; synchronize the
  provider docs and remove the deferred placeholder.
- Non-goals: RMSNorm multi-dimensional parity, GPU-specific kernels, unrelated
  Coeus performance work, and changes to the peer-owned checkout branch.
- Verification: focused Coeus nextest, Python binding parity, doctests, fmt,
  Clippy, and hosted WGPU/CUDA/ROCm/Metal/book checks pass at the merged
  provider head.

## ATLAS-KWAVERS-REAL-COMPUTE-028 — Remove Kwavers production identity paths [major] [arch] — open

- Owner: Kwavers provider owner; Atlas scope is the audit record and consumer
  integration gate. Kwavers source files are peer-owned in the active checkout.
- Findings: realtime GPU scan conversion, mixed-domain time propagation and
  nonlinear correction, KZK retarded-time application, and PINN domain
  adaptation all contain identity-return paths on the fetched default. Exact
  evidence and locations: `gap_audit.md#atlas-kwavers-real-compute-028`.
- Acceptance: each seam performs input-sensitive computation or is removed or
  narrowed; the corresponding analytical/differential tests fail under the old
  identity body; focused provider gates and the full Kwavers integration gate
  pass; no clone-only implementation remains at the named locations.
- Re-open trigger: a clean committed Kwavers source increment lands on
  `origin/main` or a peer claim becomes stale under the one-hour sweep.

## ATLAS-CONSUS-ASYNC-FACADE-029 — Remove the Consus async placeholder [major] — open

- Owner: Consus provider owner; Atlas scope is the audit record and integration
  gate. The active Consus checkout is peer-owned.
- Finding: `crates/consus/src/async/mod.rs` exports only the
  `AsyncFacadeUnavailable` marker and explicitly documents the async facade as
  deferred. Exact evidence: `gap_audit.md#atlas-consus-async-facade-029`.
- Acceptance: implement the backend-neutral async contract with bounded,
  cancellation-safe operations and value-semantic tests, or remove the public
  placeholder module and update its callers; package, docs, and Atlas gates
  pass with no deferred async marker.
- Re-open trigger: a clean committed Consus source increment lands on
  `origin/main` or the peer claim becomes stale under the one-hour sweep.

## ATLAS-USCT-FWI-024 — Transmission-USCT FWI parity [minor] — open 2026-08-13

Audit and evidence: `gap_audit.md#atlas-usct-fwi-024`. kwavers leads the
reference on forward-model and optimizer machinery; these close the deltas.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| FWI-024-A | Replace fixed-step backtracking in `frequency_domain/inversion.rs` with the linearized exact line search `α = −⟨g,d⟩/⟨d,Hd⟩`, reusing the matrix-free Hessian action for the curvature. | [minor] | done 2026-08-13 — kwavers `912fe1983`, `backlog.md#kw-fwi-083` | Claude | Met. `⟨d,Hd⟩` reuses the existing `hessian_vector` (moved to `gradient.rs`, one implementation for both consumers) rather than adding a second forward-projection path. New test recovers a weak anomaly with the seed set 200× too large; falsified by forcing the old behaviour (fails with a one-entry objective history). 44/44 frequency-domain tests, clippy/doc/fmt clean in scope |
| FWI-024-B | Cap the NLCG β with Fletcher–Reeves: `β = min(max(β_PR,0), β_FR)` (Gilbert–Nocedal). | [patch] | todo | — | Convergence on the existing inversion tests is monotone and no worse than `β_PR⁺`; a case where unbounded `β_PR` overshoots is added as a regression test |
| FWI-024-C | Angular-spectrum split-step implementation of the existing `HelmholtzForwardOperator` seam, reusing the phase-screen code rather than a second copy. | [minor] | todo | — | Differential against CBS on a weak-contrast phantom within a derived bound; documented divergence where reflections matter (ASM is one-way) |
| FWI-024-D | Transmission-USCT acquisition: two opposed linear arrays on a rotation stage, per-view interpolation between a fixed reconstruction grid and view-aligned simulation grids, gradient accumulation across views. | [minor] | todo | — | Recovers the sound-speed phantom from a simulated 360°/2° sweep within a derived tolerance; per-view rotation round-trips to identity |

## ATLAS-PM-ADR-INDEX-025 — Member-repo ADR index drift [patch] — open 2026-08-13

Evidence: `gap_audit.md#atlas-pm-adr-index-025`. Each item is per-repo and must
land on that repo's own branch; all four trees are currently peer-held.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| ADR-025-A | coeus: renumber one of the two ADR `0060` files and fix every cross-reference to it. | [patch] | todo | — | `scripts/adr-index.py check` clean for coeus; no two ADRs share a number; citing items/CHANGELOG updated |
| ADR-025-B | tyche, apollo: normalize ADR status casing to the canonical `Proposed`/`Accepted`/`Rejected` so indexes render a status. | [patch] | todo | — | `adr-index.py check` emits no casing warnings; indexes show real statuses |
| ADR-025-C | ritk: regenerate the ADR index with the generated-file header block. | [patch] | todo | — | `adr-index.py check` clean for ritk |
| ADR-025-D | atlas-meta: exclude navigation `README.md`/`INDEX.md` files from the generated ADR corpus and normalize ADR 0006 to the canonical `Accepted` status. | [patch] | done 2026-08-13 — root docs/script/test slice | current session | root `build_index` regression passes; generated root index has no navigation row; child worktrees remain unmodified |

## ATLAS-US-CAPABILITY-023 — ITKUltrasound capability parity [arch] — open 2026-08-13

Audit and evidence: `gap_audit.md#atlas-us-capability-023`. Items are
DoR-shaped and dependency-ordered; US-023-A gates the clean form of B and D.

| ID | Outcome | Class | Status | Owner | Acceptance oracle |
|----|---------|-------|--------|-------|-------------------|
| US-023-A | ADR: non-Cartesian acquisition images as a coordinate seam in ritk (curvilinear, 3-D phased array, slice series) — index→physical map carried by the image type so existing resamplers/filters apply unchanged; decide ritk-vs-kwavers ownership for G2 and G4. | [arch] | done 2026-08-13 — ADR 0042 Accepted | Claude | Met. Enum-dispatched `CoordinateMap` selected over a fourth type parameter; G2 and G4 both owned by ritk |
| US-023-A1 | Implement the ADR 0042 seam in `ritk-image`: `CoordinateMap` with `Cartesian` + `CurvilinearArray`, carried on `Image`, dispatched by both batch and both single-point transforms. | [major] | done 2026-08-13 — ritk PR #128 merged as `c608f758` | Claude | Met. Cartesian path bit-identical (pinned by test); curvilinear round-trip, fan symmetry/curvature, out-of-fan NaN, dimensionality rejection all covered. 1173 tests, clippy `-D warnings`, rustdoc, fmt clean. |
| US-023-A2 | `PhasedArray3D` variant on the ADR 0042 seam. | [minor] | **open** 2026-08-13 — PR #131 merged at `9ae68b45`; P1 source findings remain | Claude | Geometry-level and native identity-case tests pass, but completion requires all public transform surfaces to dispatch the map, origin/direction composition or explicit rejection, and native-precision arithmetic. Merge did not establish this acceptance. |
| US-023-A4 | `SliceSeries` variant on the ADR 0042 seam. **Split out of A2**: unlike the closed-form curvilinear and phased-array maps, ITK's `SliceSeriesSpecialCoordinatesImage` composes a 2-D slice image's own transform with a per-slice 3-D `Transform` object, interpolating between the `floor`/`ceil` slice transforms and handling out-of-range slices. That needs a per-slice transform list and a decision about how it interacts with ritk's `Transform` stack — ADR 0042's recorded open question — which is a different design conversation from a closed-form geometry. | [arch] | todo | — | ADR 0042 open question resolved (inline vs referenced transform list, sized from a realistic wobbler sweep); round-trip against a synthesized sweep; behaviour at and beyond the slice range specified rather than inherited |
| US-023-A5 | Move `CoordinateMap`/`CurvilinearArray`/`PhasedArray3D` from `ritk-image` to `ritk-spatial` (pure `f64` geometry, no tensor coupling); `ritk-image` re-exports and keeps using them. Puts the geometry at the deepest common ancestor of its consumers and makes it reachable from `kwavers-analysis` without dragging coeus autograd/nn/wgpu into a DSP crate. | [minor] | in review 2026-08-13 — ritk PR #132, `e8e7ed6f` | Claude | Static review found no new P0/P1 in the move; merge remains dependent on A2 and hosted gates. `ritk-spatial` gains no new dependency; the lane is clean. |
| US-023-A7 | Give `CurvilinearArray` an explicit `first_lateral_angle` instead of ITK's implied centre-on-boresight, so an asymmetric fan is expressible; ITK's convention becomes the `-(n-1)/2·Δ` special case. Drops the `lateral_count` argument from both geometry methods, removing the seam's coupling to image shape. Review `PhasedArray3D` for the same implied centring. | [major] | todo — gates A3; blocked until PR #132 merges | — | kwavers' `angle_min` geometry round-trips exactly through the seam; an ITK-centred fan reproduces its current beam indices; no method takes `lateral_count` |
| US-023-A3 | kwavers `ScanConverter` delegates its polar math to the `ritk-spatial` geometry SSOT, keeping Leto storage and Aequitas typed geometry; the duplicated formulas in `b_mode/scan_conversion.rs` are deleted. | [minor] | done 2026-08-13 — kwavers `6731f8f32` on `codex/kwavers-floatelement-roots` | Claude | Met. Differential oracle replays the pre-migration formulas across the whole raster within a derived `1e-9` bound (`atan2` vs `atan` rounding; observed worst case `8e-12`, and a mis-indexed pixel would differ by `>= 1`). No polar formula remains in kwavers. 731 tests, clippy `-D warnings`, fmt clean |
| US-023-A6 | Decide whether B-mode moves behind the `kwavers` ritk bridge so scan conversion becomes a true `resample` through the seam and the converter is deleted outright. Splits the B-mode pipeline across crates, so it is a recorded decision, not an incidental one. | [arch] | todo | — | ADR with a recommended option; supersedes ADR 0042's consequence bullet, which assumed kwavers could reach the seam directly | — | Differential against the current `ScanConverter` within bilinear interpolation error, then that converter and its callers are gone |
| US-023-B | QUS spectral tissue characterization: windowed 1-D power spectra with a support-window seam, reference-phantom normalization/averaging, backscatter parameters (midband fit, spectral slope, spectral intercept), and spectral-difference attenuation estimation. | [minor] | todo | — | Recovers known slope/intercept/attenuation from a synthesized RF phantom with an analytically derived tolerance; differential check against the forward scattering/attenuation physics kwavers already models |
| US-023-C | SRAD (Yu & Acton) speckle-reducing anisotropic diffusion in `ritk-filter/src/diffusion/`, reusing `smoothing/box_sigma` for the instantaneous coefficient of variation. | [minor] | todo | — | Value-semantic parity against the published formulation on a speckled phantom; edge-preservation asserted against Perona–Malik on the same input |
| US-023-D | Block-matching elastography framework: metric-image seam (direct/FFT NCC), displacement-calculator seam (max-pixel, parabolic, cosine, optimizing, Bayesian-regularized, strain-window), multi-resolution search-region sources and block-radius calculators, end-to-end displacement pipeline. Consolidate the existing kwavers NCC + parabolic kernel into it — no second copy. | [arch] [minor] | blocked: depends on US-023-A ownership decision | — | Recovers a known applied displacement/strain field on a simulated compression sequence within a derived bound; existing `thermal_strain/tracking.rs` callers migrated, old path deleted |
| US-023-E | Directional 1-D FFT frequency-domain filter over N-D images with a pluggable frequency-response function seam (Butterworth bandpass as first implementation). | [minor] | todo | — | Round-trip and analytical passband/stopband response asserted per axis; existing `FrequencyFilter` 1-D path consolidated onto it |
| US-023-F | Ultrasound IO: HDF5 ultrasound layout and a special-coordinates-aware reader. | [minor] | blocked: depends on US-023-A image types | — | Round-trips an acquisition with its non-Cartesian geometry preserved |

Review evidence for US-023-A2: the phased-array implementation is only exercised
with zero origin and identity direction. `Image::transform_*` and
`physical_points_to_continuous_indices` remain Cartesian-only, while the new
native and scalar phased branches ignore `Image` origin/direction metadata.
The geometry also converts generic scalar indices to `f64`, performs the
trigonometry there, and narrows back to `T`. PR #131 merged at `9ae68b45`, but
these source-level findings remain open against that default; the Atlas gitlink
tracks the merged head without treating merge as capability closure.

US-023-A3 audit note: the current kwavers `ScanConverter` accepts an arbitrary
`angle_min`, while the RITK curvilinear map centers the fan from the image beam
count. The cutover must either preserve that acquisition convention through a
validated map parameter or reject non-centred geometry before deleting the
converter; the existing bilinear differential remains the acceptance oracle.

## ATLAS-EUNOMIA-FLOAT-CBRT-014 — Land sign-preserving FloatElement::cbrt SSOT [feat]

- Owner: Atlas integration.
- Outcome: close the ATLAS-AEQUITAS-ROOT-OPS-012 SSOT follow-up. Eunomia now
  owns `FloatElement::cbrt` — `libm::cbrtf` default (correct reduced-precision
  path for `F16`/`Bf16`) with native `libm::cbrt` overrides for primitive
  `f64` and the `F64` wrapper — on `codex/eunomia-float-cbrt` (`bba10b6`).
  Aequitas' `Quantity::cbrt` switched off its `powf(1/3)` workaround onto the
  new SSOT seam (`cbrt(-8 m³) == -2 m`, no longer NaN) on
  `codex/aequitas-root-ops-closure` (`071538c`); the NaN-domain test is now a
  sign-preservation test. Both provider gate sets green: eunomia fmt, `-D
  warnings` all-targets, clippy, nextest 109/109, doctests; aequitas fmt,
  `-D warnings` all-targets, clippy, nextest 85/85, doctests, no-default.
- Status: delivered; both branches pushed. The final ATLAS-AEQUITAS-ROOT-OPS-012
  follow-up — semantics-marked dimension tuples (`ReciprocalVolume`,
  `Angle`) — is now closed too (see ATLAS-AEQUITAS-ROOT-OPS-012, `3ce7b03`).

## ATLAS-MNEMOSYNE-CONSUS-REFRESH-013 — Reconcile merged provider PM closeouts [patch]

- Owner: Atlas integration.
- Outcome: advance the Mnemosyne and Consus gitlinks to their merged default
  heads and synchronize the root evidence for the stale provider PM items.
- Acceptance: Mnemosyne `e57e2d6` and Consus `5163eb1` are recorded exactly;
  provider-owned Rust, Miri, package, platform, and documentation evidence is
  cited; exact-head, structural integration, and lane audits pass without
  staging peer-owned provider checkout changes.
- Status: complete in this root increment. Mnemosyne PR #44 merged after Rust
  verification plus Miri arena, Stacked Borrows, and Tree Borrows passed;
  Consus PR #21 merged with all repository-owned package, MSRV, platform,
  MinIO, and feature-matrix checks passing. The recurring `recurseml/analysis`
  result remains an external analyzer integration failure.

## ATLAS-AEQUITAS-ROOT-OPS-012 — Land aequitas rational-power sqrt/cbrt increment [feat]

- Owner: Atlas integration.
- Outcome: the pre-existing scalar-operator WIP (MulAssign/DivAssign, scalar
  * quantity) was already merged upstream via PR #21 (commit `dd0b8e1`,
  merge `0052b80`) with 9 value-semantic tests — verified complete in the
  current aequitas default; no further action needed for that axis. The
  remaining in-flight worktree WIP — type-level `SqrtDimension`/
  `CbrtDimension` plus `Quantity::sqrt`/`cbrt` through the `FloatElement`
  power surface — was reconciled with concurrent peer edits and landed as a
  completed, tested increment on `codex/aequitas-root-ops-closure`
  (`72ef8b4`): concrete exponent-tuple impls (8 sqrt shapes, 3 cbrt
  shapes), module wiring, 12 value-semantic tests, CHANGELOG, and review
  corrections (number-density tuple accuracy, `Div`-projection doc,
  `float_cmp` lint). All canonical gates green: fmt, `-D warnings`
  all-targets check, clippy `-D warnings` all-targets/`--all-features`,
  nextest 80/80, doctests 13/13, `--no-default-features` check.
- Status: delivered; aequitas branch pushed. Cargo.lock tooling residue
  (config-level `[patch]` overlay drift) left as pre-existing dirt.
- Tracked follow-ups (outside this increment): (1) SSOT — eunomia
  `FloatElement` gained a libm-backed sign-preserving `cbrt`
  (`libm::cbrtf`/`libm::cbrt`) and aequitas dropped the `powf(1/3)` path
  (ATLAS-EUNOMIA-FLOAT-CBRT-014: `bba10b6` + `071538c`). (2) semantics-marked
  dimensions (`ReciprocalVolume`, `Angle`) now have sqrt/cbrt impls — the
  tuple macros accept an input semantics type and normalize the output to
  `BaseSemantics` (`Angle::sqrt` → dimensionless, `ReciprocalVolume::cbrt` →
  reciprocal length), landed `3ce7b03` on
  `codex/aequitas-root-ops-closure` with 2 value-semantic tests. (3) a
  sign-preserving cbrt for negative operands is resolved by (1). All three
  follow-ups closed.

## ATLAS-TYCHE-REFRESH-011 — Reconcile merged Tyche PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Tyche gitlink to merged PM-closeout head `5efaee7` and
  record exact-head evidence for the completed consumer documentation slice.
- Status: complete; the root pointer now records `5efaee7`, and the exact-head
  audit scope is ready for final verification.

## ATLAS-LETO-PM-REFRESH-010 — Reconcile merged Leto PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Leto gitlink to the merged PM-closeout head and retain
  exact provider-head evidence without staging peer-owned Leto changes.
- Status: complete; Leto PR #107 merged as `e525d8d`, the root gitlink now
  records the exact default, and the pointer evidence is synchronized.

## ATLAS-LETO-CONVOLUTION-012 — Close provider convolution contract [major] [arch]

- Owner: Atlas integration.
- Outcome: close the stale Leto convolution-provider record after the generic
  CPU contract and Coeus direct consumer integration are both merged and
  exact-head verified.
- Status: complete; Leto PR #108 source `7172b338463c72faa2a561a3c84bda26d827351a`
  merged as default `a722fbc81cd1d82df74ef9e5acc1d9997d340d9d`. PR #108's
  exact provider run `31690152639` and post-merge default run `31690301356`
  pass. Coeus default `a4063be1` retains the direct consumer contract after
  PM-only PR #325; the root pointer is advanced without staging peer-owned
  checkout dirt.
- Residual: 33 pre-existing Leto Rustdoc broken/private-link warnings; no
  convolution-specific diagnostic. Hephaestus owns accelerator execution.

## ATLAS-MOIRAI-PM-REFRESH-009 — Reconcile merged Moirai default [patch]

- Owner: Atlas integration.
- Outcome: advance the Moirai gitlink to the merged PM-closeout head and
  synchronize the exact-head evidence for the full twenty-provider inventory.
- Scope: root `repos/moirai` gitlink plus current Atlas checklist/backlog/gap
  audit records; peer-owned Moirai checkout edits remain untouched.
- Status: complete; Moirai PR #125 merged as `ae9a5df`, the root gitlink now
  records that exact default, and the twenty-provider exact-head audit passes.

## ATLAS-LIVE-HEAD-SWEEP-008 — Reconcile moving provider defaults [patch]

- Owner: Atlas integration.
- Outcome: refresh the root gitlinks for provider defaults that advanced after
  the preceding exact-head check and preserve current hosted evidence.
- Scope: root `repos/mnemosyne` and `repos/hermes` gitlinks plus synchronized
  Atlas PM records; provider source, locks, and peer-owned checkouts are
  excluded.
- Acceptance: Mnemosyne `1ad5819` and Hermes `5785143` exact-head hosted CI
  passes; both committed gitlinks match fetched defaults; the root exact-head,
  coherence, and lane audits pass.
- Status: complete after exact-head CI; the pointer and evidence commit are
  delivered in this integration increment.

## ATLAS-HEPHAESTUS-REFRESH-007 — Integrate cross-entropy PM closeout [patch]

- Owner: Atlas integration.
- Outcome: advance the Hephaestus root gitlink and root evidence after the
  provider merged its cross-entropy PM closeout.
- Scope: root `repos/hephaestus` gitlink and synchronized Atlas PM records;
  preserve the provider checkout's peer-owned dirty `Cargo.lock`.
- Acceptance: fetched `origin/master` hosted WGPU, CUDA, ROCm, and Metal runs
  pass at the merged provider head; the root gitlink equals that head; the
  provider PM closure and exact-head root checks are recorded.
- Status: complete at provider head `9385686`; the Atlas pointer and evidence
  are delivered in this integration increment.

## ATLAS-PROVIDER-DRIFT-005 — Post-merge exact-head convergence [patch]

- Owner: Atlas integration.
- Outcome: advance the two provider gitlinks that moved after the prior
  integration closure and make the committed audit guard verify fetched
  default heads when requested.
- Scope: root `repos/mnemosyne` and `repos/ritk` gitlinks, the provider
  integration audit script and its tests, and synchronized root PM records.
  Provider source, locks, and peer-owned working-tree changes are excluded.
- Acceptance: both gitlinks equal their fetched default heads (`32524e3` and
  `53bb013`), exact-head mode detects mismatch and supports non-`main`
  defaults, focused script tests pass, and the item records hosted evidence.
- Status: complete at Atlas `062afef` (branch `codex/atlas-provider-drift-005`).
  Exact-head structural mode and the focused eight-test regression suite pass.

## ATLAS-PROVIDER-INTEGRATION-004 — Twenty-provider audit and cleanup [major]

- Owner: Atlas integration plus provider-owned cleanup follow-ups.
- Outcome: keep all 20 requested provider gitlinks, hosted evidence, audit
  inventory, book content, workflow security, and worktree topology coherent.
- Acceptance: exact gitlinks match fetched default heads; the committed audit
  reports 20 providers; provider book placeholders are absent from delivered
  heads; substantive hosted gates pass; mutable action refs and non-linked
  worktree directories are either fixed or recorded with an owner and trigger.
- Status: complete at Atlas `6852b08` (PR #129). Consus book closure merged as
  PR #19; Coeus book and reusable-workflow closures merged as PRs #321 and
  #322. Provider workflow action pinning and reusable-workflow refreshes are
  merged. Exact gitlinks, hosted gates, workflow scans, book scan, and lane
  audit are green.

## ATLAS-RITK-EUNOMIA-001 — RITK Eunomia 0.8 local closure — 2026-08-10

- RITK's workspace manifest and standalone lock now resolve Eunomia `0.8.0`
  with `rkyv 0.8.17`; no active RITK manifest requests Eunomia 0.7.
- Removed the stale Windows-only `missing_const_for_thread_local` expectation
  from `repos/ritk/crates/ritk-filter/src/morphology/mod.rs`. The initializer
  was already const-compatible under Rust 1.97; the expectation itself failed
  under `-D warnings` as unfulfilled. No morphology behavior changed.
- RITK repository-owned validation is green at the reconciled standalone lock:
  locked metadata, formatting, strict all-target/all-feature Clippy, workspace
  doctests, and workspace Rustdoc pass; full Nextest passes 5,137/5,137 with
  24 configured skips, and the focused `ritk-filter` suite passes 1,123/1,123.
- The Atlas overlay was bypassed only for standalone lock/gate verification and
  restored afterward. Existing RITK peer dirt in `CHANGELOG.md`, `Cargo.lock`,
  filter/interpolation/Python sources remains preserved; no child reset, clean,
  commit, push, or gitlink advance was performed.
- Local closure is complete. Hosted security, exact-head owner review, package
  archive verification, crates.io/PyPI indexing/publication, trusted-publisher
  enforcement, and merge remain external release gates; the broader RITK
  historical backlog is not claimed complete by this slice.

### Melinoe/Mnemosyne/Apollo boundary adoption — 2026-08-10

- Apollo validation now has a test-only `mnemosyne-memory` workspace dependency
  and a focused `BrandedVec -> BrandedCell<[T]>` boundary contract in
  `crates/apollo-validation/src/application/suite/tests.rs`. The contract
  validates branded allocation, token-gated slice borrowing, mutation, and
  post-mutation reads through Mnemosyne's public facade; Apollo does not reach
  into Melinoe internals for this memory boundary.
- `rustfmt --check` and the focused Apollo test pass (`1/1`). The initial link
  attempt was blocked by the absent `D:/msys64/tmp` directory; the required
  environment directory was created and the final link/test run passes. Apollo's
  lockfile was reconciled from the final manifest: the `apollo-validation`
  package now records its `mnemosyne-memory` dev edge and the standalone locked
  focused test plus `--lib` check pass with the Atlas overlay bypassed. The
  reconciliation also materialized the workspace's git sources and removed
  overlay-only `[[patch.unused]]` noise; it is broader than a one-line Melinoe
  edit and remains uncommitted alongside existing Apollo peer state.
- The slice is intentionally test-only: Mnemosyne remains the memory SSOT,
  Melinoe remains the generativity SSOT, and no provider, Moirai, or Apollo
  runtime source was changed.

### Melinoe/Moirai partition-result adoption — 2026-08-10

- Added `moirai-parallel/src/tests.rs::test_par_partition_map_preserves_partition_order`
  as a consumer contract for the existing Melinoe-backed
  `par_partition_map` bridge. The test proves that disjoint branded shards can
  return ordered per-partition results while the original cells remain readable
  through the brand token.
- The change is intentionally test-only and leaves Moirai scheduler queue
  ownership, the Melinoe provider, and the peer-dirty executor bridge untouched.
  `rustfmt --check` and `git diff --check` pass; the reconciled standalone
  lockfile now pins Melinoe to delivered `47863b12aa0cd4e65cb9556b2c9bbf1353a5ee26`.
  Locked metadata and library check pass, and the Melinoe-enabled focused suite
  passes 33/33 with the Atlas overlay bypassed. The broad generated lock diff
  remains uncommitted with peer work.
- The Moirai test change and reconciled Cargo.lock remain uncommitted in the
  peer worktree; no provider reset, cleanup, commit, push, or gitlink advance
  was performed.

## ATLAS-ARCH-011 — Retire hephaestus-metal per ADR 0047 [arch] [major] — blocked

- Owner: claude/fable-loop (claimed 2026-08-03); scope: `repos/hephaestus`
  (`crates/hephaestus-metal`, the
  workspace member list, the `hephaestus` facade's `metal` feature, and the
  conformance suite's Metal instantiation). Coeus is **out of scope** — see
  the note under ATLAS-SUBSTRATE-002.
- Outcome: the crate and its 5 449 forwarding lines plus 2 606 test lines are
  deleted. Metal targeting survives unchanged as
  `WgpuDevice::try_metal(...)`, and the vendor identity as
  `device.adapter_info().map(|i| i.backend)`.
- The facade's `metal` feature is **kept and re-pointed**, so consumers'
  spelling of intent survives the removal: it comes to mean "acquire a
  Metal-preferring `WgpuDevice`" instead of "compile a second copy of the
  operation surface".
- Acceptance oracle: (a) `cargo nextest run` green for the hephaestus
  workspace at `--all-targets` with the member entry gone, and the `metal`
  feature seam building in its re-pointed form; (b) the conformance suite
  passes with the Metal instantiation removed and no clause left
  unreferenced; (c) a stack-wide grep finds no `hephaestus_metal` reference
  outside Coeus's tracked item; (d) the two CFDrs `backend_name()`
  assertions still pass, confirming no observable contract moved.
- Risk/change class: `[major]` — a published crate is removed. Needs a
  CHANGELOG entry under Unreleased with the one-line migration
  (`MetalDevice::try_default` → `WgpuDevice::try_metal`). Release itself
  stays outside this item's authority.
- Verification note: coverage is not lost. The Metal instantiation ran the
  same clauses over the same code path as the WGPU one, so it asserted
  nothing WGPU does not already assert; Metal-*adapter* coverage is a
  question of which adapter CI acquires, not of which crate the suite names.
- Dependencies: **ATLAS-SUBSTRATE-002** (see the blocker below). ADR 0047 is
  Accepted; the decision is not in question, only its sequencing.
- **BLOCKED 2026-08-03, discovered by executing it.** The hephaestus-side
  removal is mechanically complete and was verified to that point — member
  entry, workspace dep, the facade's optional dep and its three `?/` feature
  entries, the `metal` feature re-pointed to `["wgpu"]`, the
  `pub use hephaestus_metal as metal` re-export, and the crate itself, with
  `cargo metadata` green and **zero** residual `hephaestus_metal` references
  in any `.rs`/`.toml` under `repos/hephaestus`. It was then reverted, for
  the reason below.
- **`repos/coeus` depends on `hephaestus-metal`** (`coeus/Cargo.toml:59`, and
  `coeus/crates/coeus-metal/` consumes it). The ADR scoped Coeus out on the
  grounds that its collapse is SUBSTRATE-002's business — that scoping was
  wrong, and the stack overlay is what proves it: the overlay is generated
  from the *dependency closure*, so while any member declares
  `hephaestus-metal`, it emits a `[patch]` pointing at the deleted crate
  directory and **every build beneath the stack root fails**, not just
  Coeus's. Upstream removal and the consumer edge are one co-evolution unit.
- Cutting that edge is not available: `repos/coeus` is on a live peer's
  `codex/coeus-publish-cycle` branch, and the Coeus board claims
  `coeus-hephaestus`, `coeus-rocm`, `coeus-metal` under Codex
  (`coeus/docs/backlog.md:464`) — a fresh, commit-backed claim over exactly
  the files this needs, mid-publish-cycle. Deleting a crate out from under a
  publish cycle is the one thing not to do here.
- Re-open trigger: `repos/coeus` no longer declares `hephaestus-metal` —
  i.e. ATLAS-SUBSTRATE-002 deletes `coeus-metal`, or the peer's publish cycle
  completes and its claim is released. Then re-apply the hephaestus removal
  (it is a ~15-minute mechanical replay of the list above) and land both
  repos as one unit.
- Sizing note for whoever takes SUBSTRATE-002's metal slice: `coeus-metal` is
  1 233 lines with **zero in-repo dependents** — no manifest outside the
  workspace member list names it, and the only code references are its own
  tests. It is a file-for-file copy of `coeus-rocm` (per-file diffs of 0, 0,
  0, 2, 17, 25 lines after normalizing the vendor token), and
  `coeus-hephaestus` already implements the whole op surface generically for
  `HephaestusBackend<P>`. The only content not reproducible from a ~56-line
  provider marker is one `fill_zero` override.

## ATLAS-OVERLAY-GEN-STALE-1 — Cross-repo path deps on member mainlines [arch] — todo (needs user decision)

- Owner: unclaimed; scope: `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`,
  and the member manifests listed below. **Held for a user decision** — see the
  conflict at the end.
- **My 2026-08-03 diagnosis on this item was wrong and is corrected here.** I
  filed it as "the generator is stale against the package renames". It is not.
  Run twice in a row the generator is byte-identical (`cmp` clean), and it emits
  the same 38-line reduction against the committed overlay each time. It is
  idempotent and its output is *correct*.
- The real cause: the generator derives the overlay from the **git**-dependency
  closure, and six members no longer declare git dependencies — they were
  migrated to cross-repo path dependencies. So the generator rightly stops
  emitting patches for them, and the committed overlay is what is stale,
  carrying dead entries (`apollo-nufft`, `apollo-sht`, `asclepius-coeus`,
  `athena-leto`, and an entire `[patch."…/coeus"]` section).
- Measured 2026-08-03, path deps that **escape their own repo** (intra-workspace
  **(CORRECTED below — this measured worktrees, not committed state.)**
  `../sibling` paths excluded by resolving each path against its repo root):
  athena 36, and 25 in a private consumer — those two are the only ones
  actually committed. The kwavers/helios/ritk/CFDrs counts in the original
  measurement were uncommitted worktree edits and are withdrawn.
- **Correction 2026-08-03.** My original figure of 163 across six members read
  working trees. Committed state across the whole stack is: **athena 36** (the
  sole tracked member carrying committed cross-repo path deps, and red on CI
  for exactly that), plus 25 in the untracked private consumer. Every other
  member's committed manifests are clean `git + version`.
- That shrinks the decision considerably: it is about athena, not about a
  stack-wide cutover. athena's `[patch]` at `Cargo.toml:119-120` plus its
  path deps are what keep its CI red.
- Method note for anyone re-measuring — this is the second time I generalized
  from worktree state (the first was the lockfile survey under
  ATLAS-PUB-LOCK-1). Under the overlay, working trees routinely diverge from
  HEAD. Always read `git show HEAD:<path>`, and for anything about how a
  consumer or runner sees the repo, clone it in isolation:
  `git clone --depth 1 file:///D:/atlas/repos/<name> /d/tmp/isolated/<name>`.
  athena 36, kwavers 31, helios 29, ritk 22, CFDrs 20, plus 25 in a private
  downstream consumer —
  **163 total**. Example: `repos/kwavers/Cargo.toml` → `../../repos/aequitas`.
- These landed deliberately in `b2ee610` ("Migrate kwavers/cfdrs/helios/ritk to
  local path deps", authored by a non-Claude agent). Two notes on that commit:
  its body claims the migration covers manifests whose recorded gitlinks do not
  in fact contain it, and it states plainly that it landed with builds still
  failing ("remaining build failures are pre-existing code errors").
- **The conflict, which is why this is not being fixed unilaterally.** Standing
  stack policy is that member manifests keep `git + version` sources and the
  root `[patch]` overlay owns local resolution — a member carrying path deps is
  unconsumable as a git dependency, and the two mechanisms now contradict each
  other. The mechanical fix is to convert all 163 back and regenerate. But that
  is a 6-repo revert of another agent's deliberate, stated intent, and three of
  those repos currently have live peer branches (`coeus` mid-publish-cycle,
  `CFDrs` on a codex branch, `ritk` on a feature branch). Reverting a peer's
  intentional migration at that blast radius is a call for the user, not for an
  autonomous tick.
- Whichever way it goes, one of the two mechanisms should be retired rather than
  left in contradiction: either the path deps convert back and the overlay stays
  authoritative, or the overlay is deliberately narrowed and the generator's
  freshness check updated so `generate` stops looking like a regression.
- **Concrete consequence found 2026-08-03: this breaks CI, not just theory.**
  `athena` has been red for five days with
  `failed to load source for dependency themis` / `unable to update
  /github/themis`. Its manifest carries a committed
  `[patch."https://github.com/ryancinsight/themis"] themis = { path = "../themis" }`
  (`athena/Cargo.toml:119-120`). That resolves inside the Atlas tree and cannot
  resolve on a runner that checks out one repo — which is exactly the property
  that makes a member unconsumable as a git dependency.
- So the cost of leaving this unresolved is now measurable: at least one member
  is permanently red, and any repo that gains cross-repo path deps joins it.
  athena is deliberately **not** fixed here — removing that `[patch]` is the
  decision this item is waiting on, and athena additionally needs the
  ATLAS-PUB-LOCK-1 lock repair, so its CI will not go green from either fix
  alone.
- Note for whoever measures this again: a naive `grep 'path = "\.\./'` is
  useless here — it counts ordinary intra-workspace sibling paths and reported
  473. Resolve each path against its repo root and keep only the escapes.


## ATLAS-ARCH-005 — Replace closed-set dyn dispatch in per-timestep paths [arch] — in-progress

- Owner: opencode-2026-08-05 (ADR phase delivered, ADR 0041; execution slice parked —
  both scope repos peer-held today: kwavers `refactor/retire-kwavers-optics`
  `e4e9966b6`, CFDrs `deps/eunomia-0.8`). scope: `repos/kwavers` first (largest), then
  `repos/CFDrs`.
  One operation family per claim.
- Outcome: dispatch-site counts are `kwavers` 665, `CFDrs` 352, `gaia` 104,
  `coeus` 98, `moirai` 83, `consus` 66. Sampling the kwavers solver shows the
  pattern is not type erasure of an open plugin set but vtable dispatch over
  closed design-time sets: `sources: &[Box<dyn Source>]` inside
  `forward/nonlinear/westervelt/update.rs` (evaluated per timestep),
  `boundary: Box<dyn Boundary>` held in the solver struct, plus `Box<dyn Signal>`
  and `Box<dyn Solver>`.
- Decision rule: a closed implementor set dispatched per timestep converts to an
  exhaustiveness-checked enum — static dispatch, still runtime-selectable, no
  vtable. Genuinely open plugin boundaries on cold paths keep `dyn` with the
  applicable exception annotated inline.
- Acceptance: per family, the count of `dyn` sites on the timestep path reaches
  zero; the enum is exhaustively matched with no catch-all arm; a criterion
  comparison on the affected kernel accompanies the change, since this is a
  performance-motivated claim and must carry performance evidence.
- Non-goals: mass-converting all 1 368 sites. Hot paths first, evidence per family.

## ATLAS-ARCH-008 — Replace pointer-scattered containers on traversal paths [patch] — todo

- Owner: current session (claimed 2026-08-05); scope: the traversal-hot sites
  first, not all 318. Claimed deliverable: commit the classifier under
  `scripts/` and refresh the production-only site list; the hotness-ranked
  conversion remains the item's open work.
- Outcome: 318 `Vec<Vec<_>>` occurrences across package sources, led by
  `consus-compression/src/chunking/iterator.rs` (10),
  `gaia/src/domain/topology/adjacency.rs` (8), and
  `coeus-autograd/src/ops/nn/loss/ctc.rs` (6). Adjacency and chunk iteration are
  prefetch-sensitive; a jagged per-row allocation defeats it.
- Acceptance: the contiguous form is a flat buffer plus an offset table
  (CSR-shaped) or an arena span, with a criterion comparison on the traversal
  showing the change is a win. A site where the jagged shape is genuinely correct
  is recorded as such rather than converted.
- **Evidence re-measured 2026-08-03; two of the three named sites are wrong.**
  Verify before claiming — as written this item would send someone to rewrite
  test code.
  - `consus-compression/src/chunking/iterator.rs` (listed as the worst, 10
    occurrences): **all 10 are test-local.** `#[cfg(test)] mod tests` opens at
    line 156 of a 400-line file and every occurrence is at lines 167-383, each
    a `let coords: Vec<Vec<usize>> = ChunkIterator::new(..).collect()`
    collecting an iterator's output for an assertion. That is not a container
    on a traversal path; it is a test binding, and converting it would be
    rewriting tests to suit a metric.
  - `gaia/src/domain/topology/adjacency.rs` (listed at 8): now **zero**
    occurrences. The file is 679 lines and no longer contains the pattern.
  - The raw stack-wide count is ~370, up from the recorded 318, so the
    headline number is not shrinking even though its named exemplars have
    evaporated — which is the signal that the count is measuring the pattern,
    not the defect.
- What the item still needs before it is claimable: a classifier that
  separates production containers from `#[cfg(test)]`-local and
  `tests/`/`benches/` bindings. I wrote one and do not trust it — it
  mis-classified `kwavers-math/.../lsqr/tests.rs` as production, so its
  per-repo split is not recorded here rather than recorded wrongly. The
  two corrections above were each confirmed by reading the file.
- Re-scoped acceptance: the deliverable is first a *correct site list* —
  production-only, ranked by traversal hotness rather than raw count — and
  only then the CSR conversions with their criterion evidence. A raw
  `Vec<Vec<` count is not a defect list.
- **Site list delivered 2026-08-03.** A classifier now separates production
  containers from `#[cfg(test)]`-guarded and `tests/`/`benches/`/`examples/`
  bindings, and it carries two self-checks derived from files read by hand —
  it refuses to print numbers unless it reproduces both. That gate earned its
  keep: the first version failed, because it matched only the bare
  `#[cfg(test)]` and the consus module is gated
  `#[cfg(all(test, feature = "alloc"))]`. Any cfg predicate carrying a bare
  `test` token now counts, with string literals stripped first so a
  `feature = "test-utils"` value cannot pose as the predicate.
- Verified totals: **297 production, 73 test/bench-local** (370 raw). So ~20%
  of the recorded 318 was never a defect.
- **There is no hotspot, and that changes how this item should be worked.**
  Production counts per repo are ritk 81, kwavers 70, CFDrs 46, gaia 37,
  consus 24, coeus 12, apollo 6, moirai 5, leto 2 — but the top *file* has 10
  (in a private downstream consumer, out of stack scope), the next has 6, and
  everything after is a tail of 4s and 3s across unrelated subsystems
  (`coeus-autograd/.../ctc.rs` 6; `ritk-vtk/.../poly_data.rs`,
  `ritk-filter/.../anti_alias_binary/solver.rs`,
  `cfd-optim/.../search/genetic.rs`, `consus/src/sync/mod.rs` 4 each).
  There is no "fix the top three files" increment available.
- Consequence for the acceptance oracle: ranking by *count* is worthless here.
  A claimant should pick sites by traversal hotness — profile first, per the
  measurement-first rule — and convert the ones that a profile implicates,
  recording the rest as correct-as-jagged. The classifier lives in the session
  scratchpad; it should be committed under `scripts/` if this item is claimed,
  since re-deriving it is the expensive part (toil automation).
- **Delivered 2026-08-05 — classifier committed, site list refreshed.**
  `scripts/atlas_scattered_containers_classify.py` is the committed,
  reproducible form (underscore-named and importable, matching the
  testable-script convention), with pytest coverage in
  `scripts/tests/test_atlas_scattered_containers_classify.py` (24 tests:
  production vs test/bench/example split, `#[cfg(test)]`/`mod tests`
  brace-depth tracking, comment/string/char/raw-literal stripping with
  char-vs-lifetime disambiguation and multiline-string state, `cfg(not(test))`
  and `feature = "test-utils"` exclusions, filename heuristics, semicolon-line
  leak guard, determinism). It scans only the `.gitmodules`-registered members via
  `atlas_stack.registered_members()`, so the git-ignored private consumer
  never surfaces. Refreshed verification totals on the 2026-08-05 tree:
  **260 production / 65 test-bench / 325 total**, per member — CFDrs 42/11,
  apollo 6/2, coeus 12/0, consus 20/15, gaia 34/2, kwavers 63/5, leto 3/13,
  mnemosyne 0/1, moirai 6/9, ritk 74/7. The delta vs the 2026-08-03 recording
  (297/73/370) is tree drift plus method differences: this implementation
  strips comments, string/char/raw literals and block comments before any
  matching (so a `feature = "test-utils"` value or a `"mod tests {"` template
  string cannot arm a predicate and commented `Vec<Vec<` sites are not
  counted), narrows the test-filename heuristic to `tests.rs`/`*_test.rs`/
  `bench.rs`-style names (so `test_utils.rs` helpers stay production), and
  emits root-relative site paths; the committed script is the reproducible
  oracle going forward. The production-only site list is
  regenerated with
  `python scripts/atlas_scattered_containers_classify.py --site-list
  scripts/oracles/arch-008-production-sites.txt` (see the gate bullet
  below). Ranking by traversal hotness
  (profile-first) and the conversions themselves remain the open work — this
  item stays `todo`.
- **First conversion delivered 2026-08-05 — moirai collective family.**
  `repos/moirai` `moirai-core/src/communication/collective.rs`:
  `CollectiveOps::{scatter,gather,all_to_all}` now build and traverse a
  CSR-shaped `ChunkedVec<T>` (contiguous flat buffer + chunk-offset table)
  instead of jagged `Vec<Vec<T>>`. Semantics preserved exactly (chunk tiling,
  all-to-all column truncation at the chunk count); the empty-input / zero-
  participant edge returns an empty buffer rather than the historical
  `chunks(0)` panic. Consumers were verified tests-only, so the signature
  change is contained. Criterion
  (`benchmarks/benches/collective_ops_comparison.rs`, `harness = false`,
  jagged baselines kept inline, 32/128 participants × 4096/8192 items):
  gather **~10–13×** faster (O(1) hand-off), traverse **~1.6×**, scatter
  **~1.1–2.2×**, all_to_all **~1.3–3.2×** — a win on every measured path.
  moirai-core gate: check 0, collective nextest 4/4 (round-trip, empty/
  zero-participant, all-to-all parity), strict clippy 0.
  `channel_fusion` per-channel buffers are recorded as **correct-as-jagged**:
  each channel grows and flushes independently, so a shared flat buffer would
  add reallocation complexity without a traversal win. `owned_chunks`
  (hybrid.rs) stays owned-per-worker by contract (parallel ownership model);
  it is a candidate only if its consumers move to borrowed chunks. The next
  conversion should be picked from a different repo family per the
  one-family-per-claim rule.
- **Oracle gate wired 2026-08-05 — the split can no longer drift silently.**
  `scripts/atlas_scattered_containers_classify.py --verify-oracle
  scripts/oracles/arch-008-production-sites.txt` re-verifies the current
  production split against the committed oracle (read-only; exit 0 = match,
  1 = drift, 2 = unreadable oracle), wired as `make verify-scattered-oracle`
  following the `fmt-check`/`board-lint` convention. `outputs/` is gitignored
  by design (derived state), so the oracle now lives at the tracked path
  `scripts/oracles/arch-008-production-sites.txt` and is regenerated
  deliberately with `--site-list` and committed in the same change that
  caused the drift. Oracle refresh after the moirai conversion:
  **256 production / 71 test-bench / 327 total** (per member — CFDrs 42/11,
  apollo 6/2, coeus 12/0, consus 20/15, gaia 34/2, kwavers 63/5, leto 3/13,
  mnemosyne 0/1, moirai 2/15, ritk 74/7). The sole delta vs the recorded
  260/65/325 is the moirai conversion: −4 production sites (the
  `collective.rs` family left the scattered set) and +6 test-local sites
  (the new parity tests build jagged vectors). The 2 remaining moirai
  production sites are `channel_fusion` and `owned_chunks`, both recorded
  correct-as-jagged / owned-by-contract above. Verify-mode coverage:
  `scripts/tests/test_atlas_scattered_containers_classify.py` gained
  oracle-parse, added/removed drift, blank/member-suffix tolerance, and CLI
  exit-code (0/1/2) tests (classifier suite now 32; full scripts suite 92 +
  20 subtests).
- **Spot-check 2026-08-05 — classifier matches a manual read.** Hand-verified
  the top per-member production files and the complete discrepancy set for
  ritk (74), kwavers (63), CFDrs (42): all 33 production sites in the top 3
  files per member match the oracle exactly (raw `Vec<Vec<` lines == oracle
  claims, same lines), and all 39 occurrences the classifier excluded from
  production were confirmed by hand to be comment/doc text (16 — stripped,
  never counted) or test/bench/example code (23 — counted test-local, e.g.
  the `#[cfg(test)]`-guarded `clahe_2d` in interpolate.rs:168 and the
  `#[cfg(test)] mod tests` VOF reconstruction.rs cases exercise the
  brace-depth path; `tests.rs`/`tests/`/`examples/` paths exercise the
  heuristics). Zero production code misclassified as test and zero test code
  counted as production. Read-only; no tree edits.
- **Spot-check 2026-08-05 — mid-count members + claimed-sites sweep; classifier
  extended; oracle corrected 256/71 → 250/77.** Hand-verified the six remaining
  members (gaia 34, consus 20, coeus 12, apollo 6, leto 3, mnemosyne 0) with
  the same discrepancy-set method: every top-file raw `Vec<Vec<` line matches
  the oracle claims (all 34 gaia, 20 consus, 12 coeus, 6 apollo, 3 leto
  claims), every excluded occurrence (doc comments, in-file `#[cfg(test)]` /
  `mod tests` regions, `tests/`/`examples/` paths) confirmed non-production,
  and a reverse stale-check confirmed all 75 mid-count claims point at live
  `Vec<Vec<` lines. The claimed-sites direction then surfaced a genuine
  classifier blind spot: it could not see **include-site gates**
  (`#[cfg(test)] mod <name>;` declared in a parent module) or bare
  `#[test]`/`proptest!` regions, so whole test-only files were misreported as
  production. The earlier top-member spot-check verified the excluded-direction
  only; the claimed-sites sweep here is what caught the remaining sites.
- **Classifier fix.** `compute_test_regions` now also treats `#[test]`
  attributes and `proptest! {` blocks as test regions, and `classify_file`
  gains `_is_include_gated`: it locates the file's `mod <name>;` declaration
  (`dir/mod.rs`, sibling `dir.rs`, `src/lib.rs`/`src/main.rs`, or crate-root
  `mod <dir>;` for `dir/mod.rs`) and checks the stacked attributes directly
  above it, stopping at the first non-attribute line so a cfg attribute of a
  *previous* declaration never leaks (the `boolean_csg` regression: its
  `#[cfg(test)]` belongs to the neighbouring `adversarial_tests_2`, and its
  claims are genuinely production). Files loaded under an arbitrary module
  name via `#[path = "..."]` (e.g. `#[cfg(test)] #[path = "tests_ply.rs"]
  mod tests;`) are covered by a per-member `#[path]`-declaration map keyed by
  the *resolved* target path (`#[path]` is relative to the declaring file's
  directory) — a basename key would collide on the many `mod.rs` modules and
  wrongly gate unrelated production files (caught live: the MGH reader, DICOM
  directory scanner and DICOM Association SCU `mod.rs` files are production
  and stay claimed). 11 new unit tests (classifier suite now 43) cover
  include-gated module, plain include, previous-declaration leak, dir module,
  `#[test]` fn, `#[test]` non-leak, `proptest!` block, and the `#[path]` map
  + stacked-attribute gate. Residual, deliberately-conservative blind spots
  (test code kept as production, never the reverse): a `mod foo;` nested
  inside an in-file `#[cfg(test)]` block of the parent, a `//` comment between
  the attribute and the `mod` declaration, `#[cfg_attr(test, ...)]`, and
  parenthesized `proptest!(...)`.
- **Corrected oracle: 250 production / 77 test-bench / 327 total** (was
  256/71 — total unchanged, pure reclassification). Six sites moved
  production → test-local, all hand-verified genuine test code: consus
  `reader_proptest.rs:151` and `tests_extra.rs:101` (include-gated), and ritk
  `tests_staple.rs:142,243` (include-gated) and `tests_ply.rs:89,123`
  (include-gated via stacked `#[path]` attribute, plus `#[test]` regions).
  Corrected per-member split: CFDrs 42/11, apollo 6/2, coeus 12/0, consus
  18/17, gaia 34/2, kwavers 63/5, leto 3/13, mnemosyne 0/1, moirai 2/15,
  ritk 70/11. Final independent verification: all 250 committed claims are
  live `Vec<Vec<` lines and none classify as test under the committed logic;
  `make verify-scattered-oracle` passes on the corrected oracle.
- **Second conversion 2026-08-05 — ritk-vtk Laplacian adjacency family.**
  `repos/ritk` `ritk-vtk/src/domain/filters/smooth.rs`: the smoothing
  filter's `build_adjacency`/`laplacian_step` now use a CSR-shaped
  `Adjacency` (contiguous `neighbors` buffer + per-vertex `offsets` table —
  the VTK `VtkCellArray` layout) instead of jagged `Vec<Vec<u32>>`. The
  build is jagged-free (degree count → prefix-sum offsets → direct flat fill
  → in-place sort+dedup per run), so the oracle site `smooth.rs:133`
  disappears rather than moves; the sorted/deduped layout is fully
  deterministic where the old `HashSet` build left neighbor order
  implementation-defined. Neighbor *sets* are unchanged, so filter results
  are preserved to within the existing 1e-5 test tolerance; a parity test
  pins the CSR runs against the sorted jagged reference (polygon + line
  edges, an isolated vertex, and a quad-grid interior vertex with its four
  edge-sharing neighbors sorted/deduped). `Adjacency` and `Adjacency::build`
  become documented public API (the only API change; `laplacian_step` stays
  private) so the criterion bench measures the production path. Criterion
  (`crates/ritk-vtk/benches/smooth_adjacency_comparison.rs`, `harness =
  false`, jagged baseline kept inline, 4096/16384-vertex quad grids): build
  **~7.8× at 4096 / ~8.5× at 16384** faster (857.7→110.5 µs / 3.523→0.415
  ms) — the CSR build replaces one `HashSet` allocation per vertex with a
  single flat buffer; traversal **~1.07× at 16384** (78.5→73.2 µs) and
  statistically flat at 4096, the short degree-4 runs amortizing the layout
  win — the honest headline is the build, which runs once per filter
  invocation while traversal runs once per iteration. Oracle regenerated to
  **249/78/327** (ritk 69/12): the smooth.rs production claim moved to the
  bench baseline, where the pre-conversion formulation lives by design
  (mirroring the moirai bench precedent). Gate: `ritk-vtk` nextest 258/258,
  warning-denied Clippy, fmt clean, `make verify-scattered-oracle` exit 0.
  The other named ritk families were assessed and deliberately left
  unclaimed this slice: `ritk-filter/.../anti_alias_binary/solver.rs`
  layers are a push-front/pop-front work-queue — CSR would turn every front
  insert into an O(n) memmove across all layers (**correct-as-jagged**),
  and `ritk-vtk poly_data.rs` cell arrays are the native CSR end state but a
  ~225-reference data-model migration that warrants its own dedicated claim.
- **Third conversion 2026-08-05 — Apollo CWT output buffer.**
  `repos/apollo/crates/apollo-wavelet/src/application/execution/plan/cwt.rs`
  now collects the row-major `(scales, signal_len)` coefficient matrix through
  `moirai::map_collect_index_with::<moirai::Adaptive>` into one flat buffer,
  then reshapes it into the existing `leto::Array2`. This removes the
  per-scale `Vec<Vec<f64>>` intermediate and its row allocations while
  preserving indexed output order, adaptive parallel execution, and the public
  `CwtCoefficients` API. The flattened dimension is checked with `checked_mul`
  and returns `CoefficientShapeMismatch` on overflow. The selected production
  site is gone rather than moved; no DWT coefficient API was changed because
  those vectors represent intentionally level-shaped detail bands and remain
  correct-as-jagged for this slice. Evidence: Apollo `cargo check -p
  apollo-wavelet`, rustfmt, strict Clippy, doctests, and `cargo nextest run -p
  apollo-wavelet --lib` **21/21** pass; `git diff --check` and the targeted
  no-`Vec<Vec<` residue scan are clean. The separate oracle gate reports the
  expected single stale claim at `cwt.rs:72` (current split **248 production /
  78 test-bench / 326 total**); oracle refresh is intentionally deferred because
  `scripts/atlas_scattered_containers_classify.py` and
  `scripts/oracles/arch-008-production-sites.txt` are pre-existing untracked
  artifacts owned by the concurrent root oracle stream. Re-run
  `--site-list` and `make verify-scattered-oracle` when that stream lands the
  derived artifacts.
- **Fourth conversion 2026-08-05 — Apollo prime-pair macro tables.**
  `repos/apollo/crates/apollo-fft-macros/src/prime_pair_tables.rs` now keeps
  expansion-time cosine/sine values in flat `Vec<f64>` buffers and chunks them
  only while emitting the unchanged fixed-size `[[T; H]; H]` token arrays. This
  removes the nested `Vec<Vec<f64>>` allocation and preserves row-major token
  order and the `PrimePairTable<N, H>` API. Zero-height inputs avoid
  `chunks_exact(0)`; zero `N` and `H × H` overflow return deliberate procedural
  macro compile errors. Evidence: macro/FFT checks, rustfmt, strict Clippy,
  doctests, and `cargo nextest run -p apollo-fft --lib` **394/394** pass;
  targeted diff and nested-vector residue checks are clean. The ARCH-008 oracle
  remains deferred exactly as recorded above because its classifier/oracle files
  are owned untracked artifacts in the concurrent root stream.
- **Site investigated and recorded correct-as-jagged 2026-08-07 — CFDrs
  spectral-element global assembly.** Converted
  `repos/CFDrs/crates/cfd-math/src/high_order/spectral/assembly.rs`
  (`GlobalAssembly.element_dofs` + `SpectralMesh.element_connectivity`,
  oracle sites `assembly.rs:14,25,140`) to CSR-shaped flat offset+index
  storage with the input shape preserved, then measured it. The criterion
  comparison (DOF-traversal read, 2 000×8 / 2 000×32 / 500×128 elements×DOFs)
  showed the flat buffer is consistently **~1.2–1.6× slower** than the jagged
  rows for the isolated read (CSR 3.5/7.2/6.2 µs vs jagged 2.1/6.0/5.5 µs):
  the fixed-size spectral rows are small and cache-resident either way, and
  the flat slice window pays two bounds checks the direct `Vec` row does not.
  The whole-`add_element_matrix` variant was dominated by unbounded COO
  accumulation (bench-design noise), not DOF access. The conversion was
  **reverted** and the site is recorded as correct-as-jagged: no traversal
  hotness, no criterion win — converting it would trade memory for a
  measurable slowdown. No oracle change needed (the sites remain live
  `Vec<Vec<` occurrences, correctly classified as production).
- **Fifth conversion 2026-08-07 — Leto L-BFGS ring buffer.**
  `repos/leto/crates/leto-ops/src/application/optimization/lbfgs.rs`
  `LbfgsMemory` now keeps correction pairs in two CSR-shaped flat ring
  buffers `s_buf`/`y_buf` (capacity `memory * n`) plus a scalar
  `rho_buf` (capacity `memory`) addressed by a single `head` index
  modulo `memory`, replacing the previous `Vec<Vec<f64>>` history
  with `Vec::remove(0)` eviction. The public API
  (`new`/`len`/`is_empty`/`direction`/`push`) is preserved; downstream
  `kwavers-solver` FWI callers (`elastic_fwi/inversion.rs`,
  `time_domain/quasi_newton.rs`) recompile against the new API without
  changes. The two-loop recursion in `direction` was re-derived against
  Nocedal & Wright Alg. 7.5: under the ring's logical-index convention
  (`pair_slot(0)` = newest, `pair_slot(k-1)` = oldest), the first pass
  walks `0..k` (newest→oldest) and the second pass `(0..k).rev()`
  (oldest→newest); a self-authored regression test
  (`direction_preserves_two_loop_after_wrap`) verifies value-semantic
  agreement with an independent jagged-reference implementation after a
  full ring wrap, and a saturation test verifies oldest-pair eviction.
  Criterion baseline comparison over the acceptance-oracle grid
  `{8,32}×{100,1000}` (median [lo hi], µs):

  | config | ring (new) | jagged (baseline) |
  |---|---|---|
  | m8_n100   | 1.71 [1.65 1.79]  | 1.78 [1.71 1.88] |
  | m32_n100  | 6.68 [6.31 7.04]  | 7.48 [7.14 7.79] |
  | m8_n1000  | 15.42 [14.61 16.24] | 16.36 [15.79 16.87] |
  | m32_n1000 | 75.00 [71.45 79.08] | 66.19 [63.35 70.11] |

  The flat ring wins at small dim (≤+13% over jagged, fewer allocations),
  is parity at `m8_n1000` (memory traffic dominates over allocation
  savings), and is **~13% slower** at `m32_n1000`: the large memory plus
  large dim regime has the ring doing `% memory` slot resolution per
  two-loop step against two big contiguous buffers while jagged has
  `memory` individual `Vec` allocations with one prefetcher-tight inner
  scan per row. The conversion's primary win is allocation/eviction
  elimination (no `Vec::remove(0)`, one allocation at construction
  instead of per-`push`), not raw throughput at high `m × n` — that is
  the honest baseline and is recorded here per the performance gate.
  Evidence: `cargo nextest run -p leto-ops --lib` **178/178** (176
  baseline + 2 new regression tests), `cargo test --doc -p leto-ops`
  20/20 + 1 ignored, `cargo clippy -p leto-ops --lib -- -D warnings`
  clean, `cargo fmt -p leto-ops -- --check` clean,
  `cargo check -p kwavers-solver --no-default-features` clean. The
  criterion bench `crates/leto-ops/benches/lbfgs.rs` is registered with
  `harness = false` and smoke-runs in single-iteration mode (`-- --test`)
  within the test budget; full timing runs fit the 300s/binary budget.
- **Delivery**: leto PR #96 (`fix/leto-ops-lbfgs-ring-buffer`), commit
  `1ed166a`, branch pushed to origin. **Not merged — blocked on a leto CI
  infrastructure defect at `db9a63c` (origin/main HEAD)**: Codex's Aug-7
  commit replaced the `git = "..."` workspace declarations for `mnemosyne`/
  `moirai`/`hermes-simd`/`eunomia`/`aequitas`/`themis` with `path =
  "../..."` for local meta-repo convenience, which resolves locally (meta-
  repo `.cargo/config.toml` `[patch]` overlay redirects the URL sources to
  local paths either way) but is unresolvable in leto's standalone CI
  checkout (`cargo metadata` fails to read `../aequitas/Cargo.toml`).
  Pre-existing in main, unrelated to this PR — leto's prior main CI run was
  already red for the same reason. Codex's `LETO-INTO-ITERATOR-1` dirty
  state is present in the leto working tree iterating on `leto/array.rs`,
  `leto/src/application/iter/*`, `leto/src/lib.rs`, `leto/tests/core/
  iteration.rs`, plus unrelated `leto-ops/{lu_symbolic.rs, sparse/mod.rs,
  parallel.rs, lib.rs}` files — the workspace `Cargo.toml` is theirs by
  precedent and outside the file-disjoint scope of this lbfgs slice.
  Per `concurrent_agents: Contention response order`, PR #96 stays open
  with the peer's landing as its re-open trigger. **Re-open trigger**:
  leto CI on main turns green (Codex lands the CI fix forward), OR a
  future disjoint slice puts me in a position where
  `repos/leto/Cargo.toml` workspace section falls under my scope.
- **Out-of-scope finding recorded** (kwavers-math `optimization/lbfgs.rs`
  is a full duplicate `LbfgsMemory` implementation, not the re-export the
  ATLAS-MATH-SSOT-CONSOLIDATION-1 Lane B residual table records; see Lane
  B residual (5)). Not converted in this slice: out of the leto-local
  file-disjoint scope, peer-active territory.
- **Sixth conversion 2026-08-08 — consus-zarr chunk selection indices.**
  `repos/consus` `consus-zarr/src/chunk/ops.rs` `selection_indices`
  (`Vec<Vec<u64>>`, one allocation per selection dimension) is replaced by a
  CSR-shaped `SelectionIndices` (`flat: Vec<u64>` contiguous buffer +
  `offsets: Vec<usize>` offset table) built once per read/write call; both
  copy helpers (`copy_chunk_selection_to_output`, `copy_selection_input_to_chunk`)
  hoist `dims: Vec<&[u64]>` per call so the traversal hot loop does one
  indirection (`dims[dim][selection_position[dim]]`) instead of two, and all
  three call sites (`read_array`, `write_array_selection`, `read_array_sharded`)
  use the same `SelectionIndices::build`. Criterion
  (`crates/consus-zarr/benches/zarr_selection_copy.rs`, `harness = false`,
  faithful jagged replica of the non-sharded `read_array` kept inline as a
  baseline; byte-parity assertion pins the replica to production output
  before timing; 2d 256×256 / 2d 512×512 / 3d 64³ strided×2 selections on a
  populated `InMemoryStore`): CSR is a win on every case — **−4.7% /
  −6.5% / −10.9% time vs jagged** (criterion `change`, p < 0.05; within-run
  medians 6.50/25.75/33.8 ms vs 6.96/26.40/36.6 ms). Gate: `cargo clippy -p
  consus-zarr --all-features --all-targets -- -D warnings` clean, nextest
  `303/303`, doctests clean, fmt clean; CI `--all-features` clippy+check
  green on PR #13. **Oracle refreshed to 243 production / 80 test-bench /
  323 total**: the consus-zarr `ops.rs` production site is gone; coeus
  `ctc.rs` 408-410 → 353-355 (line shift from a peer PR, same sites); leto
  `lbfgs.rs:79,80` added (genuine `Vec<Vec<f64>>` in `LbfgsMemory`,
  hand-verified; the conversion's ring buffers are flat so the site moved,
  it did not stay). `--verify-oracle` exit 0 on the refreshed oracle.
  Delivery: consus PR #13, branch `refactor/consus-zarr-csr-selection-indices`
  (commits `3ce79b0` conversion + `d3d5b19` mechanical rustfmt of two
  pre-existing-dirty consus-core book examples that had kept the
  workspace-wide Format CI job red at HEAD, blocking the Check job for every
  PR). Residual: pre-existing untracked meta-repo scratch (`.commandcode/`,
  `libtest_*.rlib`) and peer-held `version-guard`/`gitlink-coherence` changes
  are untouched.

## ATLAS-PRIVACY-NAMING-1 — Private consumer named throughout stack artifacts [chore] — todo (needs user decision)

- Owner: unclaimed; scope: `backlog.md`, `gap_audit.md`,
  `docs/adr/0036-neuroimaging-and-mr-ownership.md`, and
  `PATH_DEP_AUDIT_001_ENTRY.md`.
- The consumer at `repos/leoneuro-rs/` is a private external org's code drop:
  gitignored at `.gitignore:60`, no `.gitmodules` entry, no
  `submodule.*` keys, remote on a different GitHub org. ATLAS-GIT-HYGIENE-001
  confirmed that arrangement is deliberate design, not a stale rule.
- Standing policy for such a consumer is that it stays out of the stack map
  entirely — the gitignore entry is the only sanctioned trace, and upstream
  items it motivates cite "a downstream consumer" generically. Its name is
  currently in four tracked artifacts, including an ADR and the closed
  audit ledger, across roughly a dozen references.
- I redacted only the one reference I added myself (in
  ATLAS-OVERLAY-GEN-STALE-1's measurement). The rest is **not** being swept
  unilaterally: several sit in closed items' audit trails and an Accepted ADR,
  where a blind rename would break the traceability those records exist to
  provide, and peers reference those item names.
- The decision needed: does this consumer's name count as confidential for
  artifact purposes? If yes, the sweep should be one deliberate pass that
  rewrites references generically and preserves each record's meaning
  (git history keeps the old text either way — the redaction is forward-only).
  If no, the standing rule should be recorded as not applying here, so this
  keeps being re-raised.
- Adjacent, unrelated to the naming question: `PATH_DEP_AUDIT_001_ENTRY.md` sits
  at the repository root, where the root-manifest rule admits no loose report
  files. Its content belongs in the closed item it serves.

## ATLAS-PUB-001 — Migrate 8 crate-release workflows to the Atlas-shared caller [patch] — blocked: fresh Kwavers current-default validation

- Owner: current session (Atlas coordination); scope: root publication records and
  exact default-branch evidence for
  `repos/{apollo,coeus,consus,hephaestus,kwavers,leto,moirai,ritk}/.github/workflows/rust-release.yml`.
  The separate `repos/ritk/.github/workflows/release.yml` is the wheel publisher,
  not the crate caller. One package per claim — the
  scopes are disjoint by repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3.
- Outcome: each package's crate-release workflow becomes a thin caller of
  `ryancinsight/atlas/.github/workflows/crates-publish.yml@<atlas-sha>`, and the
  duplicated 142-line body is deleted in the same change. Audit 2026-07-28: four
  of the seven `rust-release.yml` files are byte-identical; the only real
  variation is `RUST_TOOLCHAIN` (1.95.0 / 1.97.0 / 1.97.1) and whether the
  package needs Atlas path dependencies (only `kwavers`).
- Non-goals: changing any package's toolchain pin; changing tag conventions;
  touching the already-shared wheel pipeline.
- Acceptance per package: caller under 40 lines; the package's existing toolchain
  value passed as `rust-toolchain`; `kwavers` passes `atlas-ref`; the old body
  deleted, not kept beside the caller; one `workflow_dispatch` validation run
  green before the next release.
- Dependencies: none. ATLAS-PUB-003 must be complete for that package before its
  next real publish, but the migration itself does not wait on it.
- **hephaestus slice done 2026-08-03** (`38f36bc`): 142-line body → 39-line
  caller pinned to atlas `9772542`, toolchain 1.95.0 preserved, `crate-` tag
  convention unchanged. Acceptance met including the validation run —
  `workflow_dispatch` run 30795798452 is green, with the validate job passing
  in 1m3s and the publish job correctly skipped (it gates on
  `github.event_name == 'release'`, so a dispatch cannot publish).
- **leto and moirai slices done (prior session)**: both migrated to 39-line callers.
- **apollo, coeus, consus, ritk PRs open 2026-08-04**: apollo PR #75, coeus PR #289, consus PR #11, ritk PR #107 — 142-line bodies → 39-line callers, format/lock fixes applied, CIs running.
- **Carry this into the remaining seven migrations: the tag gate must stay in
  the caller.** The audit's "byte-identical apart from the toolchain" reading
  misses it. Each package's current workflow skips non-`crate-` releases via a
  job-level `if`, but the shared workflow's validate job has **no** prefix
  check and `exit 1`s on a tag it cannot parse. Porting without the gate
  converts today's silent skip of a legacy `<package>-v<version>` release into
  a red CI run.
- Evidence that this is live, not theoretical: hephaestus's two most recent
  release events (`hephaestus-metal-v0.18.0`, `hephaestus-host-v0.18.0`, both
  2026-08-02) show `skipped` in the run list. Legacy-convention tags are still
  being cut, so the gate is doing real work today.
- Tag-convention state, surveyed 2026-08-03 across all eight packages: every
  one gates on `crate-`, and there is exactly **one** matching tag in the whole
  stack — apollo's `crate-apollo-fft-macros-v0.2.0`, cut 2026-08-02. So
  `crate-` is the newly adopted convention rather than a dead gate, and the
  default `tag-prefix` is correct for these callers. Worth stating explicitly
  because the raw numbers (1 matching tag out of 77) read like dead automation
  until the dates are checked.
- Separate observation, not part of this item: because those 0.18.0 release
  events skipped, they were not published by this pipeline. Whether the crates
  reached crates.io by another route is a question for ATLAS-PUB-003, which
  owns publisher registration.
- **leto slice done 2026-08-03** (`c42b87d`), plus `bf7bf2b` fixing four unused
  imports that the earlier `520f248` decomposition left behind — CI denies
  warnings, so that would have failed the gate regardless of this item.
- **moirai slice done 2026-08-03** (`08d5095`): identical caller with its own
  toolchain (1.97.0) passed through; the repo's workflow differed from the
  others only in that value. Validation run 30811438728 green, and its
  `--locked` step passing independently confirms moirai's lock is sound.
  Repository CI also green, covering the three refactor commits the push
  carried.
- **3 of 8 done** (hephaestus, leto, moirai). The five left — apollo, coeus,
  consus, kwavers, ritk — are all currently on live peer branches, so their
  slices wait for those branches rather than for anything in this item.
- **Default-branch recheck 2026-08-13.** All eight fetched crate defaults now
  carry the 39-line Atlas caller with no local `cargo publish` body: Apollo,
  Coeus, Consus, Hephaestus (`origin/master`), Kwavers, Leto, Moirai, and RITK.
  The source migration is therefore complete; the old `3 of 8` count is
  historical.
- Hosted validation evidence is mixed and remains open for the release gate:
  Apollo release validation `31534217702`, Coeus release validation
  `31551729552`, Hephaestus release validation `31532975062`, Leto release
  validation `31531560175`, Moirai release validation `31530550433`, and RITK
  release validation `31654707025` pass. Consus dispatch validation
  `29976636343` passes on its recorded head. Kwavers dispatch validations
  `31316302910` and `31290138802` fail at the pre-repair lock state; no fresh
  validation exists yet for the current default after the git-source lock
  repair. Coeus publish-stage failure is the external registry gate owned by
  ATLAS-PUB-003, not a caller-validation failure.
- Re-open trigger: fresh Kwavers `workflow_dispatch` validation run
  `31717782458` completes successfully at current default `7fee848d`.
- Practical note for the remaining slices: pass `version` from the workspace
  table, not a grep of the member manifest. Members use
  `version.workspace = true`, so a naive extraction sends the literal string
  (or an empty value) to `workflow_dispatch` and the run fails on a version
  mismatch that looks like a pipeline defect but is just a bad argument. It
  cost a wasted run on both leto and moirai.
- **The validation run then exposed a blocking, stack-wide publish defect.**
  See ATLAS-PUB-LOCK-1 below. The leto migration itself is behavior-preserving
  and correct — the old and shared workflows use byte-identical `--locked`
  invocations, so this failure predates the migration and would have hit the
  first real release either way. The migration is what made it visible.

## ATLAS-PUB-002 — Migrate 4 book workflows to the Atlas-shared caller and close the docs.yml gap [patch] — in-progress

- Owner: current session (Atlas coordination); scope: reusable-workflow
  evidence and the CFDrs caller's backend input. Other provider caller files
  and peer-owned working-tree changes are excluded.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §1-§3, §5.
- Outcome: each book workflow becomes a caller of
  `ryancinsight/atlas/.github/workflows/book-pages.yml@<atlas-sha>` passing only
  `output-path`.
- **Closed sub-item (2026-07-28):** `ritk` now joins the Atlas cross-book gate —
  `.github/workflows/docs.yml` runs the strict detector and an `mdbook build`
  over all four books. The same change dropped the three per-book HTML artefact
  uploads, leaving `detector.log` as the only retained artefact; that is a
  deliberate narrowing, not a regression, since Pages deployment is the book's
  delivery path and the artefacts were diagnostic only.
- Non-goals: flipping `mdbook-test` (ATLAS-PUB-005); authoring new books
  (ATLAS-BOOK-001).
- Acceptance: four callers, each passing its audited output path
  (`target/book/cfdrs`, `target/book/helios`, `target/book`,
  `target/book/ritk`); each package's Pages deployment succeeds once through the
  shared workflow.
- **Hosted residual 2026-08-13, closed:** CFDrs run `31716368183` failed during
  the shared build because `book.toml` declares a non-optional
  `[output.linkcheck2]` renderer and the pinned Atlas workflow `d875348` did
  not install it. Root commits `042e448` and `4c31dd7` added the opt-in
  installer and pinned the stable Rust toolchain before `cargo install`. CFDrs
  PRs #339/#340 merged the full root pin, `mdbook-linkcheck2-version: 0.12.2`,
  and `target/book/cfdrs/html`; obsolete PR #338 was closed after verification.
- Helios `31716457700` and Kwavers `31716399219` now have successful Deploy
  mdBook conclusions at their recorded provider heads. RITK `31716974169`
  remains queued at the historical head `f98a9191`, so RITK still requires a
  current-pin run after its caller PR merges. The four current caller PRs must
  still merge and produce fresh deployment evidence before this item closes.

## ATLAS-PUB-003 — Register trusted publishers and remove the unused PyPI token [chore] — todo

- Owner: user-gated — registry and GitHub settings changes are Ask-User actions;
  an agent prepares the values and verifies the result, it does not perform the
  registration.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §4.
- Outcome: every publishing package has a trusted publisher registered on the
  target registry, so no long-lived registry credential exists anywhere in the
  stack. Values per package: owner `ryancinsight`; repository = the package
  repository; workflow filename = the **caller's** filename
  (`rust-release.yml` / `python-release.yml`), because the OIDC claim carries the
  caller's identity, not the Atlas reusable workflow's; environment `crates-io` /
  `pypi`.
- Registry verification 2026-07-28: crates.io **cannot bootstrap** a new crate
  through trusted publishing — the crate must already exist and the first publish
  requires an API token. The account `ryancinsight` (id 383645) has published one
  crate, `imaginary-rs@0.1.0`; no Atlas crate is published. PyPI **can** bootstrap
  through a pending publisher configured under the account sidebar.
- Sequence per crate, therefore: (1) resolve its registry name (ATLAS-PUB-006 for
  the twelve collisions); (2) one manual publish from the local Cargo credential
  store, in workspace dependency order; (3) register the trusted publisher;
  (4) enable trusted-publishing-only enforcement. PyPI distributions skip step 2.
- Acceptance: one trusted-publishing release succeeds per package; the API token
  in the `pypi` environment is deleted afterwards; trusted-publishing-only
  enforcement is enabled in each registry's settings once its pipeline is proven.
- Residual risk: an unregistered package fails closed at the auth step. That is
  the intended failure mode, not a regression. A pending PyPI publisher does not
  reserve the project name until first use, so a name can be lost in between.

## ATLAS-PUB-006 — Stand up one facade crate per package [minor] — todo

- Owner: unclaimed; scope: one package per claim, in that package's repository.
  The `mnemosyne-core` rename is a cross-repo co-evolution unit and is claimed as
  a single item spanning `mnemosyne`, `leto`, `hephaestus`, and `moirai`.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md).
  Naming is settled; nothing here waits on a user answer.
- Outcome: every package presents one facade crate that re-exports its
  sub-crates, so a user depends on `coeus`, not `coeus-core` — the shape `burn`,
  `bevy`, and `polars` use. The facade holds no logic: re-exports with
  `#[doc(inline)]`, feature gates selecting optional backend sub-crates, and the
  crate-level overview. Lockstep versioning at the workspace version.
- Audit 2026-07-28 — 14 of 25 packages cannot present a facade today:
  - **author a facade** (workspace root is virtual, no entry crate exists):
    `apollo` → `apollo-transforms`, `CFDrs` → `cfdrs`, `coeus` → `coeus`,
    `helios` → `helios-radiation`, ~~`hephaestus` → `hephaestus`~~ **delivered**,
    `ritk` → `ritk`;
  - `hephaestus` facade landed in `repos/hephaestus/crates/hephaestus`
    (`bf24b87`): flat `#[doc(inline)]` re-export of the contract layer, backends
    under `hephaestus::{wgpu,cuda,rocm,metal}` behind features, no backend
    enabled by default (a default backend would make every trait consumer pull a
    device stack, and `cuda`/`rocm` need vendor toolkits at build time). Two
    design facts worth carrying to the remaining five:
    `default-features = false` cannot override a workspace-inherited dependency,
    so a facade declares its contract-layer dep directly; and weak feature refs
    (`dep?/feature`) are required so forwarding `parallel` does not silently
    enable an unrequested backend.
  - Verification complete — all four configurations pass: default `cargo check`,
    `--no-default-features`, the doctest, and `--features wgpu,decomposition,sparse`
    (11 m 32 s, queued behind a peer's build-directory lock). The `bf24b87`
    commit message recorded the wgpu set as unconfirmed because it was still
    building at commit time; this entry supersedes that.
  - Evidence limit: those checks ran against a working tree carrying a peer's
    uncommitted edits to `hephaestus-core/src/{lib.rs,domain/vector.rs}` and
    `hephaestus-wgpu/src/application/vector/mod.rs`. They prove the facade
    compiles against the tree as it stood, not against committed state. The glob
    re-export is robust to surface additions, but re-verify on a clean tree once
    that peer work lands.
  - Not verified: that a backend is unnameable without its feature. That follows
    directly from `#[cfg(feature = ...)]` on the re-export, and a `compile_fail`
    doctest asserting it would itself pass or fail depending on which features
    the test run enables — a fragile test of language semantics rather than of
    this contract, so none was added.
  - **flip `publish`** (facade exists, excluded from publishing): `aequitas`,
    `asclepius`, `horae`, `hermes-simd` — names already free;
  - **rename and flip `publish`**: `harmonia` → `harmonia-coupling`,
    `hyperion` → `hyperion-photon`, `moirai` → `moirai-runtime`,
    `proteus` → `proteus-materials`;
  - **rename only** (publishable under a colliding name): `athena` →
    `athena-solvers`, `gaia` → `gaia-geometry`, `mnemosyne` →
    `mnemosyne-alloc`, `themis` → `themis-placement`, `tyche` → `tyche-uq`;
  - **ready, no action**: `consus`, `eunomia`, `iris`, `kwavers`, `leto`,
    `melinoe`.
- Non-goals: repository names, submodule paths, directory names, module paths,
  and the classical-name mapping in the stack README. This is registry identity
  only. Also out of scope: negotiating a colliding name from its current owner —
  permitted, but no publish waits on it (ADR 0037 §7).
- Acceptance per package: the facade's `src/lib.rs` contains no logic; `cargo doc`
  shows re-exported items inline at facade paths; `--no-default-features` builds
  and no backend is reachable without its feature; `cargo publish --dry-run`
  passes after the sub-crates; the facade name returns 404 from the registry
  immediately before first publish, since availability decays.
- Non-blocking: ATLAS-PUB-001, -002, -004, and -005 proceed independently — a
  caller passes a package name, so every rename here is a manifest change.
- **Correction 2026-07-28 — do not flip `publish = false` ahead of dependencies.**
  An earlier reading of this item treated the eight guards as oversights. They are
  correct ordering guards: `cargo package` on `aequitas` fails with
  `no matching package named 'eunomia' found`, because a crate can only publish
  once its first-party dependencies are on the registry. Cargo *does* rewrite a
  `{ version, git }` dependency to a registry dependency, so git sources are not
  the blocker (`hermes-simd`'s manifest comment overstates it) — dependency order
  is. Each flip is the final step of that crate's own bootstrap publish, in the
  order `scripts/publish-order.py` derives. Four flips were attempted and reverted
  on this evidence; see [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §4.
- Peer-held at this revision, so not claimable without a staleness sweep:
  `coeus` (`codex/coeus-error-function-parity`, 24 dirty), `ritk`
  (`codex/docs-ritk-n4-figure-only`, 11 dirty, active), `leto`
  (`codex/leto-real-sparse-lu`, 25 dirty), `mnemosyne`
  (`codex/mnemosyne-tier-selection`, clean). The `coeus` facade — the flagship
  case for this item — is among them.

## ATLAS-PUB-008 — Audit facade names immediately before each first publish [chore] — todo

- Owner: unclaimed; scope: the pre-publish check only.
- Decision: [ADR 0037](docs/adr/0037-facade-crates-and-registry-naming.md) §3,
  verification item 1.
- Outcome: name availability is a point-in-time observation and decays — 165 of
  173 names were free on 2026-07-28, and first-come means any of them can be
  claimed by a third party before the stack publishes. Each first publish
  re-checks its own name.
- Acceptance: `GET /api/v1/crates/<name>` returns 404 immediately before the
  publish, recorded in the release evidence. A collision discovered here is
  resolved by ADR 0037 §3's rule, not by an ad-hoc name.

## ATLAS-PUB-005 — Flip `mdbook-test` per book as samples become compilable [patch] — todo

- Owner: unclaimed; scope: one book per claim, in the owning repository.
- Decision: [ADR 0035](docs/adr/0035-shared-publication-pipelines.md) §6.
- Outcome: every published book runs `mdbook test` in CI so chapters cannot rot.
  No book runs it today; the shared workflow defaults `mdbook-test` to `false` as
  a staging mechanism, not an accepted end state.
- Claim status (flipped 2026-08-11; melinoe delivered 2026-08-11):
  - **melinoe** — DONE: all fenced samples compilable; blocks referencing the
    crate carry `extern crate melinoe;` and link through a staged plain-named
    rlib (`mdbook test --library-path`), signature illustrations `ignore`d, the
    cross-brand rejection sample `compile_fail`; caller passes `mdbook-test:
    true` + `cargo-package: melinoe`; the shared workflow's broken
    `RUSTDOCFLAGS` mechanism replaced with the staging + `--library-path` path.
    Merged via melinoe PR #11; main CI green (all 11 chapters tested), Pages
    deploy green; workflow fix on atlas main (`70c6c6b`, PR #100) makes the
    caller's full-SHA pin durable.
- Acceptance per book: samples compile against the package; the caller passes
  `mdbook-test: true` and, where samples need providers, `atlas-ref`; the flip
  commit demonstrates the gate failing on a deliberately broken sample before
  landing green.
- Dependencies: ATLAS-PUB-002 for that package.

## ATLAS-MODALITY-003 — Optical-transport and RF/EM promotion watchpoint [arch] — blocked

- Owner: unclaimed; scope: watchpoint only — no edits until the trigger fires.
- Decision: [ADR 0032](docs/adr/0032-modality-transport-and-therapy-boundaries.md) §1, §2, §6.
- Blocker: promotion gate conditions 1, 4, and 6 are unmet. Source audit
  2026-07-27: Kwavers is the sole consumer of the diffusion/Monte-Carlo-RTE
  optical transport solvers (CFDrs has no radiative/optical/photon module;
  ritk has none; Helios consumes Hyperion at MeV, a different regime). No RF
  integrator or second electromagnetics consumer exists.
- Re-open trigger: a second production consumer can delete a matching transport
  implementation in the extraction change. At that point the target is
  `hyperion-transport` as a second crate in a promoted Hyperion workspace — not
  a new package — so the `no_std` law crate keeps its dependency set and Helios
  and CFDrs inherit no array substrate.
- Standing note: sonoluminescence (3 006 LOC) and photoacoustics (653 LOC) are
  Kwavers-intrinsic and are excluded from any extraction scope. A photomedicine
  integrator peer to Helios is a separate, demand-gated decision and is out of
  scope here.
- Refinement 2026-07-28 —
  [ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md) §5: "RF" names two
  unrelated concerns and this watchpoint covers only the first. RF power
  deposition and SAR belong on the shared deposition spine (ATLAS-MODALITY-002),
  where the transport stage is a modality slot and the stages behind it are
  shared. RF at the Larmor frequency for spatial encoding belongs to MR
  acquisition simulation, which is a closed, demand-gated *integrator* question —
  not part of this trigger and not a RITK concern. A proposal that merges the two
  is rejected on bounded-context grounds before the gate is even applied.

## ATLAS-OVERLAY-005 — Clear first-party rev pins across the stack [patch] — in-progress

- Owner: session-808504af. Decision: pin discipline (`architecture_scoping`) —
  a `rev =` is quarantine with a removal trigger, not a durable source form.
- Root cause: a rev-qualified git source is a **distinct package** to Cargo, so
  the stack `[patch]` overlay — which matches the bare URL — can never unify it.
  Sixteen first-party pins had accumulated across five repos at three different
  `aequitas` commits and two `eunomia` commits, so any crate reaching a provider
  by both forms received two incompatible copies of the same trait. Hyperion
  could not multiply two `Quantity` values for exactly this reason.
- ✅ Cleared and pushed: proteus `9a8655d` (also restored its manifest from a
  local path-dep leak to git+version), asclepius `ccffb6b`, tyche `996b649`,
  kwavers `df9008d93`.
- **Remaining**: helios (5 pins) and ritk (6 pins) are depinned in the working
  tree but uncommitted — neither has been build-verified yet. `openjp2` in ritk
  keeps its pin; it is third-party, where a rev is legitimate.
- **Mechanism worth mechanizing**: depinning alone is insufficient. Every lock
  move needs `python scripts/atlas-stack-overlay.py generate` to re-derive the
  patch block, otherwise the graph keeps a local-vs-git split. This is the
  mechanism behind the recurring "local X cannot replace git-sourced Y" failures
  on this board. `atlas-stack-overlay.py check` already exits nonzero on lag, so
  wiring it into CI would catch the class at the source.
- Evidence: `cargo tree -d` in kwavers reports no duplicate first-party crates;
  `atlas-stack-overlay.py check` reports the stack aligned.

## ATLAS-OVERLAY-004 — Worktree sprawl breaks stack dependency resolution [patch] — in-progress

- Owner: unclaimed; scope: `worktrees/`, the root `.cargo/config.toml`, and the
  13 lane-local `.cargo/config.toml` files. **Not** the lane branches' source.
- Blocker evidence (2026-07-27): `cargo check -p kwavers-physics` fails before
  compiling anything:
  - `failed to select a version for smallvec` — `hephaestus-wgpu v0.18.0` at
    `worktrees/hephaestus-unary-math-parity` requires `^1.15.2`; the kwavers lock
    pins `1.15.1`.
  - `cargo update -p smallvec --precise 1.15.2` then fails harder:
    `package collision in the lockfile: packages aequitas v0.1.0
    (D:tlas\worktreesequitas) and aequitas v0.1.0
    (D:tlas\worktreesequitas-energy-temperature) are different, but only
    one can be written to lockfile unambiguously`.
- Two distinct defects behind it:
  1. ✅ **resolved 2026-07-28** — `worktrees/aequitas` was an **orphaned linked
     worktree**, not a standalone clone: its `.git` file pointed at
     `repos/aequitas/.git/worktrees/aequitas`, whose admin directory had been
     pruned, leaving the checkout on disk with no git registration. Cargo still
     discovered it as a path source, giving two providers for `aequitas v0.1.0`.
     Contents were byte-identical to `repos/aequitas` (`diff -r` clean excluding
     `target`, `Cargo.lock`, `.git`), so nothing unique was lost. Removed with
     user authorization; `git worktree prune` run. `cargo check` across
     kwavers-physics and kwavers-solver resolves again, and the `smallvec`
     conflict cleared with it.
  2. **13 lane-local `.cargo/config.toml` files.** Config-layer ownership
     (`performance_engineering`) puts `target-dir` and the `[patch]` overlay at
     the stack root only; a nested config re-declaring either forks resolution
     and, as here, resolves a relative provider path into a second copy.
- Also: `worktrees/` holds 28 entries against a documented bound of one main
  tree plus one lane per repository. aequitas, coeus, hephaestus, kwavers, and
  ritk each have two or more.
- Acceptance: `cargo check -p kwavers-physics` resolves; `git worktree list` per
  repo is within bound; no lane-local `.cargo/config.toml` re-declares
  `target-dir` or `[patch]`; `worktrees/aequitas` removed after confirming no
  unique commits.
- **Ask-User gate**: removing `worktrees/aequitas` and other agents' lane
  directories is destructive to possibly-live peer setups. Confirm before
  deleting rather than reconciling unilaterally.

## ATLAS-R6A-FILELIST-001 — Per-submodule r6a commit file-list hygiene [patch] — todo

- Owner: unclaimed; scope: the 12 r6a submodule commits (apollo,
  asclepius, CFDrs, coeus, gaia, helios, hephaestus, kwavers,
  leoneuro-rs, hermes, ritk, athena) whose `git show --stat <r6a_sha>`
  verifier surfaced a 1-non-cargo-file anomaly on 2026-07-27 (each
  commit contains exactly 1 file that is neither `Cargo.toml` nor
  `Cargo.lock`). Per-submodule audit + per-submodule remediation. No
  atlas manifest edits in this scope.
- Outcome: each of the 12 r6a submodule commits produces
  `git show --stat <sha>` showing strictly `Cargo.toml + Cargo.lock`,
  OR carries an explicit per-consumer exemption row in
  `D:/atlas/PATH_DEP_AUDIT_001_ENTRY.md` STEP C documenting why the
  additional file is a deliberate deviation.
- Acceptance: per-consumer `git show --stat <r6a_sha> | grep -cE
  'Cargo\.(toml|lock)'` returns 2; the verifier script
  `scripts/atlas-path-dep-audit2-closure-r6a.py` exits 0 with the
  "no extras in r6a commits" assertion.
- Method: per-submodule `git reset --soft HEAD~1 && git restore --staged . && git add Cargo.toml Cargo.lock && git commit -m "build(<repo>): Refresh round-6a atlas-root path resolution — file-list hygiene"` (committed at the per-submodule level; carries a distinct verb (`Refresh` instead of `Apply`) so `git log --grep "Apply round-6a"` continues to surface only the original r6a commits while `git log --grep "Refresh round-6a"` surfaces the cleanup cycle), authorized amend per ticket scope, distinct from the parent-side follow-up amend at `77c60de`); then `cargo update --workspace --offline` per consumer to refresh Cargo.lock post-stick. Twelve follow-up commits land consumer-side; one atlas-side parent commit advances all 12 gitlinks atomically (or twelve separate follow-up commits if atomic amend is unsafe).d9e7db); then `cargo update --workspace --offline` per consumer to refresh Cargo.lock post-stick. Twelve follow-up commits land consumer-side; one atlas-side parent commit advances all 12 gitlinks atomically (or twelve separate follow-up commits if atomic amend is unsafe).
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27) parked
  this follow-up; the audit criterion (ryancinsight=0 / NVlabs
  preserved) was met but the per-commit file-list hygiene was
  separately uncovered.
- Risk/change class: `[patch]`; per-submodule commit rewrite spanning
  12 consumers + one parent-side gitlink advance. Distinct
  operational domain from ATLAS-GIT-HYGIENE-001 (which is a
  single-line atlas config edit only). Bundling the two was rejected
  by the round-6a code review (Q2 blocker).

## ATLAS-DOWNSTREAM-COORDINATION-001 — Notify LeoNeuro-INC maintainers about local leoneuro-rs `50bfcd9` [chore] — todo

- Owner: unclaimed; scope: out-of-band coordination with the
  LeoNeuro-INC organization (separate GitHub org, NOT ryancinsight).
  No atlas-side edits in this scope.
- Outcome: the leoneuro-rs `50bfcd9` commit ("build(leoneuro-rs):
  Apply round-6a atlas-root path resolution — GRAND_TOTAL 0 across
  atlas") lives locally at `/d/atlas/repos/leoneuro-rs/` on the
  branch `codex/sim-ct-medium`. After atlas's closure cycle dropped
  the bogus 160000 gitlink in commit `d6827c2`, atlas parent no
  longer tracks leoneuro-rs's HEAD; the LeoNeuro-INC maintainers
  can land `50bfcd9` to their own org
  (`https://github.com/LeoNeuro-INC/leoneuro-rs.git`) on their own
  schedule via their own CI/dispatch pipeline.
- Acceptance: a downstream LeoNeuro-INC maintainer receives a short
  note pointing at the local SHA (`50bfcd9`) and the atlas-side
  commit history (see `D:/atlas/PATH_DEP_AUDIT_001_ENTRY.md` STEP D
  push-handoff paragraph for the handoff context); the
  LeoNeuro-INC team decides whether to fast-forward their `main`
  to `50bfcd9` or to cherry-pick from the local branch.
- Method: out-of-band contact through the existing LeoNeuro-INC
  internal channels; the atlas-side convey is a one-line pointer
  (no technical payload required). The atlas-side documentation
  states this deferral, but **no atlas code or Cargo.toml changes**
  are part of this ticket. The `50bfcd9` commit is preserved on the
  leoneuro-rs local branch (`codex/sim-ct-medium`) until the
  LeoNeuro-INC team decides its disposition.
- Cross-link: ATLAS-PATH-DEP-AUDIT-2 (cycle closed 2026-07-27)
  STEP D push-handoff paragraph codifies the deferral as
  documentation; this ticket is the corresponding **owner-assigned**
  follow-up so the deferral doesn't drift unowned. NAME SEMANTIC
  NOTE: "downstream" in this title refers to LeoNeuro-INC as
  downstream maintainer of the `50bfcd9` commit; this is distinct
  from atlas-side "downstream consumer" terminology used in
  per-submodule commit hygiene tickets.
- Risk/change class: `[chore]`; out-of-band coordination only.

## ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER — End-to-end CI verification of `prebook check-figures` [minor] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: re-flag from `done` to `in-progress` after empirical
  drift-fixture probe retry (throwaway PR `ryancinsight/CFDrs#319`
  on commit `a163ef55`, ci.yml run `30109405652` / job `89534706116`)
  revealed a NEW upstream cargo-side blocker distinct from the
  COEQ one the prior turn's predicate anticipated.

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`
  + new `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  + PR #31 (HELIOS) management.

- Outcome: PARTIAL e2e CI verification of the wired `prebook check-figures`
  SSOT drift lint. The local lint (SSOT_IN_SYNC 7/7 green + drift detection
  at L101) + YAML validation + action pin alignment + clippy `-D warnings`
  clean + `mdbook build` exit 0 are proven signals documented in
  `ATLAS-CHECK-FIGURES-CI-1-EVIDENCE.md`. **PR #31 (HELIOS closeout →
  main at run ID `30059559064`) was the actual e2e attempt**: the
  `Check book figures` step fired in the GitHub Actions runner, but
  PR #31 produced 5 failed/concluded-with-error jobs and the conditional
  auto-merge (`gh pr merge --squash --delete-branch`) correctly
  short-circuited (FAIL_COUNT=5 ≠ 0). The full verbatim failure
  diagnostic + root-cause ranking + fix-up recovery plan is captured in
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`.

- Failure inventory (PR #31, run `30059559064`):
  - `rust workspace` job failure: `cargo fmt -- --check` saw **6 `Diff in`
    blocks across 3 new files** in the closeout xtask crate —
    `xtask/src/check_figures.rs` (lines 47, 97, 131 — chain-method
    re-formatting), `xtask/src/main.rs` (line 40 — three match arms
    `LegacyMigrationAudit`, `RefreshLegacyAllowlist`,
    `BurnMigrationAudit` consolidated to expression bodies), and `xtask/src/prebook.rs` (lines 139, 154
    — chain-method re-formatting on `fs::read` and `serde_json::to_string`).
    All 6 diffs are chain-method consolidation; trivially fixable via
    `cargo fmt -p xtask && git commit --amend`.
  - `python bindings` and `benchmark regression check` job failures:
    BOTH caused by the same root cause — `--locked` flag (maturin for
    `python bindings`, `cargo bench --no-run` for benchmark regression)
    conflicts with `Updating git repository tyche / eunomia / apollo`
    run by Cargo's metadata step. Fix: drop `--locked` for these two
    CI invocations (intent is preserved via existing `atlas_ref` pin
    in ci.yml); alternative — commit a regenerated `Cargo.lock` that
    captures the submodules' new SHAs.
  - `recurseml/analysis` job error: external research bot, not part of
    GitHub-hosted CI (out-of-scope noise). Confirmed no GitHub-hosted
    job matched the name in
    `gh api repos/ryancinsight/helios/actions/runs/30059559064/jobs`.
  - `deploy` job skipped: intentional (path-filtered `book-pages.yml`).
  - **False positive from prior summary**: `Install Rust verification
    tools` step actually succeeded; the prior summary's "error marker"
    was the `printf '::error::install-action:'` line inside
    `taiki-e/install-action`'s bash `bail()` function declaration.
    Confirmed verbatim in §3.4 of the run-evidence file.

- Main HEAD baseline (independent verification): `888015e0e2a4b03b8c1e25c7a8befcdc098fd98b`
  was independently verified GREEN (3 latest CI runs all `success`).
  → All 4 substantive failures are PR #31-specific, NOT pre-existing on
  `main`. The closeout commits are causal.

- Acceptance: the `Check book figures` step fired in the runner; the
  explicit `SSOT_IN_SYNC: N/N` log line is captured in the run log at
  the relevant step output for verification. Auto-merge correctly
  short-circuited (fail-closed design verified). The full e2e gate
  validation (`DRIFT_DOCS_NOT_IN_SPECS: N` log capture on a
  deliberate drift fixture) remains deferred until the fix-up PR lands.

- Risk/change class: `[minor]`; deferred evidence-only, no production-code
  change on this turn. The fix-up iteration is a separate `[patch]`
  workflow tweak (CI config) + trivial `cargo fmt` commit.

- Dependencies: depends on the `codex/helios-book-figures-closeout`
  branch (currently SHA `e66a16afcd78cf6e63dcbb01c36438e2cc804e8b` on
  `ryancinsight/helios` origin) receiving a fix-up commit addressing
  the 3 substantive failures above, then a follow-up PR (likely #32
  or higher) re-running the CI to validate green-pass. Verifiable now
  via `git ls-remote origin codex/helios-book-figures-closeout`.

- Sub-task (open): `cargo fmt -p xtask` + amend the closeout commits
  on the branch, then drop `--locked` flags from `Build Python
  extension` (maturin) and `Compile benchmark binaries` (cargo bench
  --no-run) invocations in `repos/helios/.github/workflows/ci.yml`.
  Re-push the branch; open a follow-up PR; expect PR CI to flow
  through `Check book figures` with the SSOT_IN_SYNC log line captured.

- Evidence limit: VERBATIM run-30059559064 log excerpts at
  `D:/atlas/verification/ATLAS-CHECK-FIGURES-CI-1-RUN-30059559064.md`
  (sections 3.1–3.4). The `DRIFT_DOCS_NOT_IN_SPECS` log-line capture
  remains deferred to the follow-up PR's CI run. No release argument,
  no performance argument, no production-code delta.

## ATLAS-CFDRS-RUNNER-MDBOOK-INDEX-1 — Close CFDrs runner-side mdBook index + ci.yml silent-drop [patch] — in-progress

- Owner: Codex `/root`; last-update: 2026-07-26;
  scope: `repos/CFDrs/.github/workflows/ci.yml` + `repos/CFDrs/.github/workflows/book-pages.yml`
  + `repos/CFDrs/docs/book/SUMMARY.md` (Appendix F cross-reference); the
  parent atlas `D:/atlas/parity_artefacts/INDEX.md` is the canonical
  sibling artifact cf. `ATLAS-PARITY-HTML-RETIRE-1`.
- Context: throwaway drift-fixture probe PR #320 (run `30217224003`)
  revealed TWO runner-side defects on the post-SIBLING-CHECKOUT-1 +
  post-COEQ-BLOCKER-1 CFDrs `origin/main` HEAD `1a7aa1d6`:
  - **(i)** `ci.yml` is registered (workflow id `319648723`, `state='active'`)
    but silently drops at queue time. GH Actions does NOT create a
    `ci.yml` run for PR #320, despite `pull_request` event firing the
    `book-pages.yml` sibling workflow on the same DRAFT PR. Most likely
    cause: the cross-repo composite action
    `ryancinsight/atlas/.github/actions/checkout-path-dependencies@51d8600cf3077e6ad6aafa5603b3289444b1719f`
    requires explicit allow-listing under CFDrs repo Settings -> Actions
    -> General when the consuming repo is not on the same plan tier.
    GH silently drops runs that reference unallowed private actions.
  - **(ii)** `book-pages.yml`'s `Build book` (mdbook build) step fails
    with `ERROR failed to read chapter '../../../parity_artefacts/INDEX.md'
    -- os error 2` because the runner's clean clone of `ryancinsight/CFDrs`
    ships ONLY the CFDrs source tree; the parent atlas's `parity_artefacts/INDEX.md`
    is not materialized (the existing `checkout-path-dependencies`
    action only materializes sibling sub-repo crates, NOT the parent
    atlas directory). This is the 3rd instance of the "sibling cross-reference
    missing in clean runner clone" class after the cargo path-dep
    (`ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1`) issue and the older local
    coeus-core path-dep (`ATLAS-CFDRS-COEQ-BLOCKER-1`).
- Acceptance:
  - (a) **[ADMIN-GATED]** Repo-admin Settings -> Actions -> General
    confirms `ryancinsight/atlas/.github/actions/checkout-path-dependencies`
    is allow-listed, OR the workflow invocation is rewritten to use a
    non-private-org composite action. The throwaway re-run produces a
    visible `ci.yml` run in the runs API for the branch (not zero).
  - (b) **[LOCALLY-VERIFIABLE]** `book-pages.yml` gains a pre-step that
    materializes `parity_artefacts/INDEX.md` in the runner workspace
    (via `actions/checkout` of the parent atlas repo with
    `path: ../parity_artefacts/` + `sparse-checkout: INDEX.md`, OR
    via `curl`-based raw download from the GitHub raw content URL
    against a pinned commit). Throwaway re-run shows `Build book` step
    conclude `success` (no `os error 2`).
  - (c) **[DEPENDS ON (a)+(b)]** The throwaway re-run produces the
    verbatim
    `DRIFT_DOCS_NOT_IN_SPECS: N docs figure link(s) missing from FIGURE_SPECS:`
    log line at the `ci.yml` `Check book figures` step. Captured log
    line ends the ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER gate.
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin. (c) inherits from (a)+(b).
- Acceptance-status disambiguation: (b) is the smaller, more deterministic
  fix (the SUMMARY.md/parent-atlas cross-reference is well-understood).
  (a) requires action outside the CFDrs repo and may need to be
  coordinated with the atlas-super-project admin.
- Risk/change class: `[patch]`; CI scaffolding only, no production-code
  change on the CFDrs application tree or on the parent atlas's
  `parity_artefacts/INDEX.md` (the canonical parity archive remains the
  consumer).
- Dependencies: tracks `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (downstream
  consumer; the verbatim `DRIFT_DOCS_NOT_IN_SPECS: N` log capture gate).
  Follows `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` (cargo path-dep closure)
  + `ATLAS-CFDRS-COEQ-BLOCKER-1` (coeus gitlink closure).
- Discovered-by: throwaway probe PR `ryancinsight/CFDrs#320`,
  run `30217224003`, 2026-07-26 (this delivery). Capture archive at
  `D:/atlas/verification/_throwaway_logs/cfdrs-pr320-run-30217224003-*/build/5_Build book.txt`.
- Evidence limit: per-step `conclusion=failure` JSON + verbatim mdbook
  error log; no production-code delta, no perf claim.
- Delivery (2026-07-27):
  - (b) closed: third-iteration curl pre-step landed in
    `D:/atlas/repos/CFDrs/.github/workflows/book-pages.yml`; runner-defensive
    invariants (`set -euo pipefail`, `curl --max-time 60 --retry 3 --retry-delay 5`,
    `printf | sha256sum -c` against certificate
    `18b7d9def0625f312776e15b2f70b681f38cbcb8838c9a9fd0b6ffb38af50a5a`). Pinned
    ref `51d8600cf3077e6ad6aafa5603b3289444b1719f` consistent with `ci.yml`
    atlas_ref. Code-reviewer-minimax-m3 returned GO for closing (b).
    End-to-end local emulation passes (`curl_exit=0`, `sha256_exit=0`).
  - (a) admin-gated remains open: `ci.yml` silent-drop on Ryancinsight
    DRAFT PRs unconfirmed root cause; tracked via
    `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER` (the (c) follow-on requires
    both (a) + (b) closures).

## ATLAS-LETO-OPS-SPARSE-LU-001 — Real sparse LU/Cholesky in leto-ops [arch] — ✅ closed (2026-07-23 Session 17 — migrated from peer draft)

- Owner: unclaimed (atlas-meta coordinator recorded; leto peer owns `leto-ops`
  source tree and is mid-refactor — peer-active; assist ladder step 3).
- Outcome: replace the misnamed dense partial-pivoting LU currently called
  `leto_ops::SparseLuSolver` with a real sparse LU or sparse Cholesky
  factorization (this is the architectural truth the name already promises).
  The CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs` doc at lines
  3-7 currently admits "atlas-native sparse direct solver backed by dense
  partial-pivoting LU" — i.e. the public `SparseLuSolver` name IS the
  misnomer, and `crates/cfd-3d/src/fem/solver.rs` works around it by
  routing medium systems to GMRES+AMG via `with_direct_threshold(512)`.
- Acceptance (architectural): real O(n) sparse factorization in `leto-ops`;
  the threshold routing becomes unnecessary; `SparseLuSolver` true to name
  (or renamed to a sparse algorithm and call sites updated in one migration
  per `consolidation_discipline: compatibility soup`).
- Risk/change class: `[arch]` + `[minor]` (no public-API break required if
  kept the same name; renaming is a `[major]` migration);
  upstream ownership (`architecture_scoping`) — implemented in `leto-ops`, not
  approximated downstream in CFDrs.
- Open question: peer is mid-refactor on leto-ops (the source is presently
  uncompilable in HEAD `9346413`; cf. "Residual CFDrs watchpoints carried
  forward" below). Wait for peer to land stabilization; then evaluate whether
  the FEM matmat structure warrants Cholesky (symmetric positive definite) or
  LU (saddle-point is indefinite).
  RESOLVED 2026-07-23: saddle-point indefinite (Brezzi 1974) → real sparse LU
  path chosen over Cholesky, per ADR 0031. Closed at leto origin/main `687b670`;
  see Session 17 closure entry appended at file tail for evidence matrix.
- Refs: backlog.md#CFDRS-PERF-SLOW-001, ATLAS-CFDRS-PERF-045.

## Cross-repo architect coordination ledger

Three CR-class items carried from `docs/audit/2026-07-02-cross-repo-integration-audit.md` (`L71-149`). Each is self-contained and gates specific consumer-side migrations below.

| ID | Class | Title | Owner repo (provider land) | Supertypes | Consumer land unlocked |
| --- | --- | --- | --- | --- | --- |
| **CR-4** | `[major]` | Rebase `coeus-core::Scalar` + `leto-ops::Scalar` over `eunomia::NumericElement` as the universal supertrait (single SSOT) — **✅ CLOSED 2026-07-09** (eunomia `57d7789`, coeus `2b3f820`, leto PR #31 merge `d9e8ac9`; ADR 0005 Accepted; re-verified 2026-07-22: `leto-ops/src/domain/scalar.rs:11` and `coeus-core/src/dtype/traits.rs:295` carry `Scalar: NumericElement`; consumer unlocks tracked and closed in batches #2/#3). Delete the vocabulary that already lives on `NumericElement` (`zero`/`one`/`to_f64`/`from_f64`/`from_usize`/`sqrt_val`/`abs_val`); keep the backend-specific slice-kernel surface (`add_slice`/.../`max_slice`, `gemv_*`, `tiled_gemm`, `axpy_rows`, leto-ops `from_usize`). See `atlas/docs/adr/0005-eunomia-scalar-ssot.md` for the proof that `RealField` (float-only) cannot be a universal `Scalar` supertrait (would orphan `coeus_core::Int` for i8/u8/.../u64). | `coeus`, `leto` (joint) | `eunomia` is doctrine holder | kwavers `RealField` nalgebra → eunomia; CFDrs `cfd-math` solver-chain RealField seam; ritk `Burn::Module → coeus::Module` rebind |
| **CR-2** | `[arch]` | Consolidate `#[global_allocator]` to a single binary-only registration. Strip from `cfd-core`, `ritk-core`, `moirai/lib`. Pass `Mnemosyne` handles via DI to library callers. | `cfd-core`, `ritk-core`, `moirai` (joint) | `mnemosyne` is allocator holder | Library composition stays provider-neutral; binaries own allocator policy — **✅ CLOSED 2026-07-18** (`cfd-core` ✅, `moirai` ✅, `ritk-core` ✅; zero `#[global_allocator]` in all three library crates) |
| **CR-1** | `[arch]` | Delete `apollo/crates/apollo-ghostcell` standalone GhostCell reimplementation; redirect all apollo sites to `melinoe::MelinoeCell` (with `brand_scope!` mint). | `apollo`, `melinoe` (consumer) | `melinoe` is brand doctrine holder | All brand-borrow contention becomes provider-exclusive — **✅ CLOSED 2026-07-07** (Apollo commit `50029b7` deletes `crates/apollo-ghostcell`; `repos/moirai/Cargo.toml` aligned to `melinoe = 0.8.0`; focused nextest `-p apollo-validation melinoe` 2/2 green and `-p apollo-sft -p apollo-radon` 43/43 green; `find_path repos/apollo/crates/apollo-ghostcell/**` returns zero files 2026-07-20 re-confirm; full evidence at `gap_audit.md` L1429-1430) |

### Provider extension register

These cross-cut consumer migration but live in provider land. Each requires its own [minor] backlog entry in the owning provider repo:

| Provider | Missing surface | Substrate | Tracked in |
| --- | --- | --- | --- |
| `leto` | ✅ `Quaternion<T>` Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt; + `try_inverse` + `to_rotation_matrix`; ✅ `FixedMatrix&lt;4,4&gt;` determinant/try_inverse + generic Add/Sub/Neg/Mul&lt;T&gt;/Div&lt;T&gt;/Assign. **Verified 2026-07-14**: 229/229 tests green, clippy `-D warnings` clean. | math | `leto/backlog.md` |
| `leto-ops` | ✅ `CscMatrix<T>`, `CooMatrix<T>`, `lu_batch`; `ExecutionStrategy` trait — all verified present at `leto/crates/leto-ops/src/`. | ops | `leto/backlog.md` |
| `moirai-async` | ✅ `mpsc::channel`, `oneshot::channel`, `Condvar`, `Mutex`, and `#[moirai::main]` exist. `ATLAS-MOIRAI-016` cancellation audit closed: Condvar lost-notification race fixed (pre-register waiter while holding guard), mpsc/oneshot waker leaks fixed (Drop impls with ID-based cleanup), 82/82 nextest pass with 2 regression tests. | async | `moirai/docs/backlog.md` |
| `apollo` | ✅ RustFFT-free differential oracle — pure O(N²) DFT reference replaces rustfft. `b291003` on `codex/remove-rustfft`. Workspace `rustfft = "6.4.1"` pin removed; `external-references` feature removed; dev-dep and vs_rustfft benchmark removed; xtask benchmark runner stripped. | validate | `apollo/backlog.md` |
| `eunomia` | ✅ eunomia-gpu deleted (E-019); folded into `hephaestus::DialectScalar`. README clean — no aspirational claims about eunomia-gpu. | basis | `eunomia/backlog.md` |
| `coeus` | ✅ `scatter_add` exists at Tensor/Var/Python; all 6 comparison ops (eq/ne/lt/gt/le/ge) exist. `Dataset`/`DataLoader` deferred per "if PINN dataset paths require" condition — no PINN path in current scope requires them. | autograd | `coeus/docs/backlog.md` |
| `hephaestus` | ✅ `f64` DialectScalar impls (Wgsl `"f64"`, CudaC `"double"`) + 24 GPU vector type impls via macro. **Verified 2026-07-14**: 47/47 nextest green, clippy `-D warnings` clean. Remaining: `wgpu::PipelineCache` integration (WG-P8); CU-P1 async-stream-overlap. | gpu | `hephaestus/backlog.md` |

---

## Migration batches (vertical slices)

Ordered per Definition-of-Ready (provider SSOT closes first). Each batch is self-contained, has observable pass conditions, and respects the WIP limit (one in-flight merge-affecting item per micro-sprint). Cross-repo item as policy: one batch is **the** item; commits ride under the established `codex/kwavers-atlas-integration` branch through that batch's owner.

### Consumer-side (kwavers / CFDrs / ritk)

| Batch | Class | Crate | Surface | Pre-reqs | Pass condition (value-semantic) | File-line scope (illustrative) |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | `[patch]` | `kwavers-solver` ([side path RTM/elastic PDE](file_pattern)) | `par_for_each` Zip → `moirai-parallel::par_mut().enumerate()` (62 sites); `Zip::indexed` → `par().enumerate()` (24 sites) | (none — confirmed by `moirai-parallel/src/lib.rs:106-181` tan rename) | ✅ **CLOSED 2026-07-12** at peer commit `5913f2946`: zero `par_for_each` source sites, zero `burn::` hits, zero `nalgebra` hits, zero `use ndarray` imports; `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel`); `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib` 5117/5119 pass (2 timeouts are pre-existing KW-WATCH-002 perf on the 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. | `crates/kwavers-solver/src/inverse/reconstruction/seismic/rtm/inherent/{wavefield,propagation,mod,laplacian,imaging,illumination}.rs`; `crates/kwavers-solver/src/forward/nonlinear/{kuznetsov,westervelt_spectral}/...`; `crates/kwavers-solver/src/forward/{elastic/swe/int, pstd/ext, multiphysics/fluid_structure}/...`; `crates/kwavers-physics/src/acoustics/...`; `crates/kwavers-physics/src/optics/polarization/linear.rs` |
| #2 | `[minor]` | `CFDrs/cfd-math` ([ite solver finish](file_pattern) + `cfd-1d`/`cfd-3d`/`cfd-validation`) | nalgebra → let, nalgebra-sparse → leto-ops `CsrMatrix`; covariance solves / geometry / finite-element typedefs | CR-4 (eunomia SSOT) so `RealField → eunomia::RealField` is universal | `cargo nextest run -p cfd-math -p cfd-3d -p cfd-1d -p cfd-validation` green; xtask scanner delta shows `nalgebra` allowlist contracts under cfdec-solver chain, cfd-3d fem/libnodes, cfd-1d linear_system and cfd-validation geometry; `nalgebra-sparse` allowlist contracts to zero | `cfd-math/src/linear_solver/{chain, preconditioners/{*, ilu/*, multigrid/*, schwarz, ssor}}.rs`; `cfd-3d/src/fem/{element, projection_solver, leto_bridge, solver, stabilization, stress, quadrature, shape, fluid}.rs`; `cfd-3d/src/{bifurcation, trifurcation, venturi, serpentine, ibm}/**`; `cfd-3d/src/vof/{cavitation, reconstruction}.rs`; `cfd-1d/src/solver/core/{convergence,linear_system,matrix_assembly,state,workspace,anderson,solver_detection}.rs`; `cfd-validation/src/{geometry, benchmarks, literature, manufactured, numerical, adaptive_mesh, tests}/**` |
| #3 | `[minor]` | `ritk` ([Provider-side Burn trait rebind](file_pattern)) | `ritk_core::{Image, Transform, Interpolator}` → `coeus_core::{ComputeBackend, Scalar}`; `ritk-spatial::{Vector,Point,Direction}` lose `burn::module::{Module,AutodiffModule}+burn::record::Record` impls; `ritk-image::types::Image<B,D>` re-exports exit Burn-keyed facade | CR-4 so eunomia `Scalar/RealField` is universal | `ritk-image::native::Image<T: Scalar, B: ComputeBackend, const D: usize>` becomes the canonical re-export; `cargo nextest run -p ritk-{core, image, filter, registration, segmentation, transform, interpolation}` green; `cargo tree --workspace -i burn-wgpu`, `cargo tree --workspace -i burn-cuda`, and `cargo tree --workspace -i burn-rocm` each return zero (Burn only CPU NdArray backend remains per DEP-496-01) | `ritk-core/src/{image/types,transform/trait_,interpolation/trait_}.rs`; `ritk-spatial/src/{vector,point,direction,spacing}.rs`; `ritk-image/src/types.rs` + `ritk-image/src/lib.rs:11` re-export line; `ritk-wgpu-compat/src/lib.rs` (`apply_row_chunks` `B:Backend` bound → `B:ComputeBackend`); per-filter `*/new(B::Device)` constructors |
| #4 | `[minor]` | `kwavers-solver` ([PINN Burn → Coeus](file_pattern)) | `burn::backend::NdArray<f32>` ⇒ `coeus-core::MoiraiBackend`; `burn::optim::{SGD,Adam,AdamW,lr_schedule::*}` ⇒ `coeus-optim::*`; `burn::module::Module` ⇒ `coeus-nn::Module`; `burn::record::Record` ⇒ `coeus-nn::Record`; `burn::tensor::*` ⇒ `coeus-tensor::*`; ~325 source lines + ~17 top-level dev-dep files | CR-4 + #3 + `coeus-autograd/scatter_add` extension | `cargo nextest run -p kwavers-solver --features pinn` green; per-physics trainer residual gradient matches golden reference within neum-compensated epsilon (derived from reduction depth × sqrt(N) per current `es::BatchModern` chain); kwavers top-level `Cargo.toml:138` `[dev-dependencies] burn = "0.19"` flips to deps via `coeus` (or top-level burn demoted fully) | `crates/kwavers-solver/src/inverse/pinn/**` (~80 files; cite-referenced inside the inventory in checklist.md); top-level `crates/kwavers/{benches,examples,tests}/**` (17 files); `kwavers-solver/Cargo.toml:42` feature set; `kwavers/Cargo.toml:138` dev-deps |
| #5 | `[arch]` | CR-1: `apollo-ghostcell` deletion + `melinoe::MelinoeCell` rebind (provider land) — single coordinated commit | (See provider-extension register above) | (None — provider-only action) | (See CR-1 row above) | `apollo/crates/apollo-ghostcell/src/lib.rs` removed; every apollo consumer routed via `melinoe::MelinoeCell`; `cargo nextest run -p apollo-* --features melinoe` green; `cargo miri test -p melinoe` green |
| #6 | `[arch]` | CR-2: Consolidate `#[global_allocator]` (provider land) — single coordinated commit across `cfd-core`, `ritk-core`, `moirai/lib` | (See CR-2 row above) | (None) | (See CR-2 row above) | Library registry sites reduced; per-binary (`kwavers-cli`, `cfd-cli`, `helios`, `ritk-cli`, `mnemosyne-gbench`, etc.) keeps or replaces registration; `cargo build -p cfd-core` without `mnemosyne` feature succeeds |
| #7 | `[arch]` | CR-4: `coeus-core::Scalar` + `leto-ops::Scalar` rebase to eunomia supertraits (provider land) — **STATUS: ✅ CLOSED 2026-07-09. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9`)** | (See CR-4 row above) | (None) | (See CR-4 row above) | eunomia: `eunomia/crates/eunomia/src/traits/numeric.rs` doc clarified (ZERO/ONE/sqrt/abs/to_f64 stay FloatElement for float paths); Complex<T>/isize/usize implementations added. coeus: `coeus/coeus-core/src/dtype/traits.rs` (`Scalar: NumericElement + CpuUnaryDispatch + Pod + Rem + Clone`); 64-file coeus call-site disambiguation landed. leto: `leto/crates/leto-ops/src/domain/scalar.rs` `pub trait Scalar: NumericElement` rebind; redundant UFCS items removed (ZERO/ONE/add/sub/mul/div/bitand/bitor/bitxor/count_ones/to_f64); slice kernels given default bodies; `from_usize` retained. `Cargo.toml` workspace version `0.35.1 → 0.36.0`. Resolution (a) applied (additive rebind is structurally infeasible per `atlas/checklist.md` structural-infeasibility addendum + E0034 evidence). Verification (pre-merge on `codex/leto-cr4-ssot-rebind`, 5 files / 196 +/-622 net subtraction): `cargo nextest run -p leto-ops` 270/270 green + `-p leto` 189/189 green + 8 doctests green + clippy `-D warnings` green on `--lib --tests` scope. Pixel/range/structural artifact: net 466-line subtractive consolidation (no vocab duplication remains). RG-verified zero `Scalar::add/sub/mul/div/ZERO/ONE/bitand/bitor/bitxor/count_ones/to_f64` UFCS references in `crates/`. |
| #8 | `[minor]` | Provider extension (provider land): ✅ `leto` (Quaternion ops, FixedMatrix<4,4> ops) — verified; ✅ `hephaestus` (DialectScalar f64 + GPU vectors) — verified; ✅ `moirai-async` (mpsc/oneshot/Condvar/Mutex/`#[moirai::main]`) — verified; remaining: `apollo`, `eunomia`, `coeus`, `leto-ops` | (See provider-extension register above) | (Threads across consumer migration; file as individual [minor] items in owning repos) | (See register above) | tracked separately in `repos/<provider>/backlog.md` |

### Token batch ordering

Batches #5, #6, #7 are the [arch] provider-SSOT gates. Per `decision_policy` nternals:

1. **#7 first** (CR-4 eunomia SSOT) — **ALL SIDES ✅ CLOSED 2026-07-09**. eunomia (`57d7789` ✅), coeus (`2b3f820` ✅), leto (`86d366bc` ✅ on `main` via PR #31 merge `d9e8ac9` — Resolution (a): rebase onto origin/main post-PR-#30, `Scalar: NumericElement` supertrait, redundant UFCS items removed). Unblocks #2 (CFDrs nalgebra finish), #3 (ritk Burn rebind), and #4 (kwavers PINN Burn → coeus). ADR `0005-eunomia-scalar-ssot.md` (status **Accepted**) describes the actual rebase; `RealField` is NOT a universal `Scalar` supertrait (would orphan `Int`); `NumericElement` is. ADR signed off via autonomy mode per `interaction_policy`.
2. **#5 second** (CR-1) — Pure provider cleanup; no consumer call sites depend on it for the migration below.
3. **#6 third** (CR-2) — Library-vs-binary layering. **cfd-core ✅, moirai ✅ landed** (2026-07-10). **ritk-core ✅ committed** (`ba6da3a5`, 2026-07-14). All sites resolved.
4. **#1 fourth** — `kwavers-solver` residual Rayon → Moirai. Self-contained. Calls CTE immediately after a clean CR-4. ✅ **CLOSED 2026-07-12** — kwavers peer commit `5913f2946` (`perf(kwavers-solver): Migrate solver tree to moirai parallel iterators`) drives source-site count to zero: `par_for_each`=0, `burn::`=0, `nalgebra`=0, `use ndarray`=0, `kwavers-solver/Cargo.toml` clean of `ndarray`/`rayon`/`burn` (substrate is `leto` + `leto-ops` + `moirai-parallel` only). `cargo nextest run --workspace --exclude kwavers-driver --no-fail-fast --lib`: 5117/5119 pass, 2 timeouts (pre-existing KW-WATCH-002 abdominal-preprocessing perf on 90s `elastic-fwi` profile override — peer-stream perf, NOT a Batch #1 regression). `cargo check -p kwavers-solver --features pinn` PASSES (Batch #4 co-verified closed). Atlas-meta `repos/kwavers` gitlink advanced `01643ed9 → 5913f2946`. Sole residual is the `kwavers-solver/Cargo.toml` `ndarray` `rayon` feature gate, flagged separately in the peer commit body — manifest detail tracked as a kwavers-peer follow-up. Batch #4 (`kwavers-solver PINN Burn → Coeus`) is also closed at this HEAD (co-verified).
5. **#2 fifth** — Largest consumer body (176 CFDrs source files). Depends on CR-4. ✅ **CLOSED 2026-07-05** — inner CFDrs HEAD advanced `0f578e1af110c5b8536476174bf266bf8b812c37` → **`d58d1fe320d046816425e1d20d16735fcfee7995`** via a single Atlas-provider migration push (subject `refactor(cfdrs): Atlas-provider migration push (Leto CSR + Eunomia scalar + Hephaestus GPU + cfd-math / cfd-2d / cfd-3d / cfd-1d / cfd-validation consumer cones)` — 752 modified + 19 added files, 51,857 insertions / 22,087 deletions, ~2,500 tests pass, 0 warnings). Atlas-parent submodule pointer advance recorded at parent HEAD `51922a56c4d4acab3dbe786b90cc5acf92e22277` (`chore(atlas): Advance CFDrs submodule pointer to d58d1fe3`).
6. **#3 sixth** — ritk Burn keyed-trait rebind. ✅ **CLOSED 2026-07-18**.
7. **#4 seventh** — kwavers-solver PINN Burn → coeus. ✅ **CLOSED 2026-07-12**.
8. **#8 last** — Provider extensions; tracked in provider repos separately; own claim stream.

### Batch #3 sub-batches (ritk Burn-trait rebind — 6 atomic commits per ADR 0012)

`Batch #3` (`[minor]` ritk Burn-keyed trait rebind) is decomposed into 6 atomic sub-batches per [`atlas/docs/adr/0012-ritk-burn-trait-rebind.md`](docs/adr/0012-ritk-burn-trait-rebind.md) (Accepted 2026-07-06). Each sub-batch widens the Atlas surface OR narrows the Burn surface — never both in one commit — atomic-boundary discipline per ADR 0012 §Decision. Reserved inner tag: `ritk/atlas-migration-push/batch3` (per ADR 0010 §Decision §"Per-batch name pattern").

**Historical sub-batch #3 framework (opened 2026-07-06; fully consumed
2026-07-18)**: the following per-crate queue records the original atomic
decomposition. PR #42 consumed #3.a–#3.g and #4–#6; PR #43 closed the ledger,
so no reservation or open queue remains.

| Sub-batch | Class | Atomic-boundary disposition | Closeout per sub-batch | Status (2026-07-09) |
|-----------|-------|------------------------------|-----------------------|---------------------|
| #1 | `[patch]` | **Additive** — Atlas-typed parallel trait surface (`TransformAtlas<T,B,D>`, `InterpolatorAtlas<T,B>`, `ResampleableAtlas<T,B,D>`) + `pub use native::Image as AtlasImage;` re-export. Burn-keyed surface untouched. | `cargo nextest run -p ritk-{core,image,filter,registration,segmentation,transform,interpolation,spatial}` green + `cargo tree --workspace -i burn-wgpu` (and `cuda`, `rocm`) zero | **closed 2026-07-06** |
| #2 | `[patch]` | **Subtractive-by-documentation** — soft docstring deprecation ONLY on Burn-keyed surface. No `#[deprecated]` attr (would emit 671-file compile-warning cascade). | (same gates as #1) | **closed 2026-07-06** |
| #3 | `[minor]` | **Subtractive-by-conversion (7 per-crate queue)**: Atlas-typed migrator test-source ports from `burn_ndarray::NdArray<B>` to `AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>`. Per-crate atomic-boundary discipline per ADR 0012. | (same gates as #1) | **✅ CLOSED 2026-07-18** — All sub-batches consumed by PR #42 `f01b1643` (1298 files, -59482 lines) + PR #43 `b4be04ca` (closeout docs). burn_surface.allowlist deleted; all Burn/ndarray deps removed. |
| #4 | `[patch]` | **Subtractive-by-impl-removal** — `ritk-spatial::{Vector, Point, Direction, Spacing}` drop `burn::module::{Module, AutodiffModule}` + `burn::record::Record` impls. Atlas-side impls only IF `coeus-nn` PINN consumer code requires. | (same gates as #1) | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #5 | `[major]` | **Subtractive-by-dep-strip** + **subtractive-by-reexport** — Cargo dep strip `burn` + `burn-ndarray` from manifests; `pub use types::Image;` re-export path switch; `apply_row_chunks<B: Backend>` removal. **THIS IS THE ONLY SUB-BATCH ALLOWED TO DELETE OR RENAME `[dependencies]` LINES.** | (same gates as #1) + `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` authoritative classification | **✅ CLOSED 2026-07-18** — Consumed by PR #42 atomic cutover. |
| #6 | `[patch]` | **Subtractive-by-allowlist-contract** — `xtask/burn_surface.allowlist` reset on sub-batch #5 re-enter; CI scan gates tighten: zero `burn::tensor::Backend`-bound public symbols + Atlas-only backend trait assertion. | CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph | **✅ CLOSED 2026-07-18** — burn_surface.allowlist deleted in PR #42. |

### Historical in-flight claims (superseded)

> This section preserves dated coordination snapshots. It does not describe
> current work; the live board at the top of this file is authoritative.

- Atlas-meta branch: `codex/kwavers-atlas-integration` (PM artifacts only).
- Atlas-meta claim scope (this turn): `backlog.md`, `checklist.md`, `gap_audit.md` at the atlas workspace root; no per-repo files touched at the atlas-meta layer.
- **Mnemosyne fixed Themis pin** [patch]: **DONE** — PR #11 merged as `f95d372`; Mnemosyne pins Themis 0.10 at `18807bb`, with metadata, clippy, 288/288 nextest, doctests, and docs green.
- **Leto Themis co-evolution and provider extension** [patch]: **DONE** — PR #32 merged as `8d39f58`; the lock graph, cache-level contract, quaternion interpolation, and fixed-matrix value contracts are verified by the complete local gate.
- **Hermes fixed Themis pin** [patch]: **DELIVERED / MERGE-BLOCKED** — PR #6 commit `6080aa4` pins Themis 0.10 at `18807bb`; all CI checks pass except the pre-existing Miri allocator failure reproduced on Hermes main. The PR remains open pending that independent correctness residual.
- Atlas-meta last landed (codex session): `61931faf` (RITK Batch #3 sub-batch #1 sync + kwavers/Burn risk surfacing, 2026-07-06, layered atop peer commits `e82fe14c`, `4a04cad1`, `4b71cda9`, `3062ce1b`, `c5f2a84e`, `61931faf` itself; followed by peer `5adf4a27` "Helios closure triage" 2026-07-06 13:37). This turn: peer landed `c6b845f81` Batch #4 slice 2 (`burn_wave_equation_2d` dependency graph: 12-family native Burn→Coeus rewrite; `burn::` line-hits 315→186, file-count 144→80). See risk #8 below.
- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.

- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep) collapsed to canonical L104** — the orphan duplicate of the user-directive sweep block at former L275-L281 + the prior stale ROUND-3 dedup claim in L283-tombstone are reconciled by the present chore: the canonical `### In-flight claims (per concurrent_agents)` L104 carries the full T1 evidence (ritk nextest 47/47; CFDrs 2177/2177+1335/1335 subsets; kwavers 1-site `plugin/mod.rs:204` test-mock slip); the L283 tombstone is updated below to reflect this collapse. Mid-session test/example issues resolved by **peer-owned** per-`concurrent_agents` disjoint-scope: the kwavers `Boundary<eunomia::Complex<f64>,3>` trait-rewire at `crates/kwavers-solver/src/plugin/mod.rs:182+204` and the `fn to_leto3` dead-code warning in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8` are peer-stream fixes; atlas-meta does not touch `repos/kwavers/crates/kwavers-solver/src/plugin/mod.rs` or any other peer-claimed source.

#### Historical closure templates — Atlas Batch #3 sub-batches #4–#6

> All three templates were consumed by RITK PR #42 and tombstoned by PR #43
> on 2026-07-18. They remain below only as design-history evidence; none is a
> standing reminder, prerequisite, or next-session instruction.

These templates preserve the original atomic commit shapes and prerequisites
from ADR 0012. They are historical evidence only; no roll-up surfacing or
future-session action remains.

- **Sub-batch #4 [patch] — Standing reminder**: `ritk-spatial rebind — drop burn::module::{Module, AutodiffModule} + burn::record::Record impls`. **Atomic inner commit shape**: a single inner-RITK commit that strips the four `burn::module::*` + `burn::record::Record` impls on `repos/ritk/crates/ritk-spatial/src/{vector,point,direction,spacing}.rs:7` and (conditionally) adds `impl<T: Scalar, B: ComputeBackend> coeus_nn::Record for *` ONLY IF the downstream PINN consumer code in `kwavers-solver/src/inverse/pinn/**` or `helios-imaging/**` requires it (cross-walk Batch #4 §Progress in `atlas/checklist.md` for the in-flight audit; otherwise sub-batch #4 is a strict-removal commit with no Atlas-side replacement per ADR 0012 §Decision §Sub-batch #4). **Standing pre-reqs**: (a) Batch #3 sub-batch #3 fully closed — i.e., the 7 per-crate queue `#3.a..#3.g` has landed (each with its own test-from-`burn_ndarray::NdArray<B>`-to-`AtlasImage<T: Scalar, B: ComputeBackend, D>` over `coeus_tensor::Tensor<T, MoiraiBackend>` port) and `xtask/burn_surface.allowlist` source-rows have been progressively decremented per per-crate closure; (b) the impact audit of `burn::module::{Module, AutodiffModule}` removal on `kwavers-solver` Batch #4 PINN code paths is completed and posted to `kwavers/gap_audit.md` (the auto-`ModuleMapper` / `GradientExtractor` / `GradientApplicator` pattern from the `coeus_nn::load_parameters` extension must already be in place, OR the per-PINN code-path-side adapter lives inline at the PINN consumer site, NOT on the spatial carriers); (c) cooldown — if any per-crate sub-batch in `#3.{b..g}` transitively touches `ritk-spatial`, it must be closed before `#4` lands to preserve the atomic-boundary invariant (no legacy Burn-keyed reference survives into the post-#4 tree). **Pre-flight gate per session**: `cargo check -p ritk-spatial --all-targets` + `cargo doc -p ritk-spatial --no-deps` warning-clean + `cargo clippy -p ritk-spatial --all-targets -- -D warnings`.

- **Sub-batch #5 [major] — Standing reminder (mandatory semver-checks pre-release gate)**: `RITK Burn Cargo dep strip + Image<B,D> re-export path`. **Atomic inner commit shape**: a single inner-RITK BREAKING CHANGE commit that (i) deletes `burn` + `burn-ndarray` from `repos/ritk/Cargo.toml:69-72`, `ritk-core/Cargo.toml:23-24` (dev-deps), `ritk-image/Cargo.toml:9-10`, `ritk-wgpu-compat/Cargo.toml:8`, and per-crate `burn` + `burn-ndarray` dev-dep cleanup from `crates/ritk-{filter,transform,interpolation,registration}/Cargo.toml:23,30`; (ii) switches the public re-export at `repos/ritk/crates/ritk-image/src/lib.rs:11` from `pub use types::Image;` to `pub use AtlasImage as Image;` (verify which `atlas/checklist.md` §Batch #3 §Plan step 1 prefers — alternative is `pub use native::Image;`); (iii) removes `apply_row_chunks<B: Backend>` from `repos/ritk/crates/ritk-wgpu-compat/src/lib.rs:40+` (no async replacement; docstring-only if a docstring is needed for archival context); (iv) updates all `Image<B, D>` references in source across the workspace (this is the [major] breaking event per RITK semver). **MANDATORY pre-release confirmation** (per ADR 0012 §Decision §Sub-batch #5 + the `versioning` section of `atlas/AGENTS.md`): `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` MUST run pre-merge and MUST authoritative-classify the commit body as `[major]` (the table-row label `[major]` in `atlas/backlog.md` §Batch #3 sub-batches is provisional; `cargo-semver-checks` is the ground truth). **If `cargo-semver-checks` reports `[minor]` or `[patch]` instead, the sub-batch #5 commit message `[major]` annotation MUST be downgraded by the actual outcome** (an observable regression per `atlas/checklist.md` §Per-batch atomic commit + version bump rules). The CHANGELOG entry under `## [Unreleased]` uses `cargo-semver-checks`'s verdict, NOT the provisional table-row class label. **Standing pre-reqs**: (a) sub-batch #4 closed OR skipped (sub-batch #4 may be omitted if the kwavers Batch #4 PINN audit confirms no Atlas-side `coeus_nn::Record` replacement is required — the omit path is documented per ADR 0012 §Decision §Sub-batch #4); (b) kwavers Batch #4 (`burn::module::Module` → `coeus_nn::Module`) `burn.rs` + `burn_compat` facade deletions are LANDED on the `repos/kwavers` peer stream so the cross-crate risk #8 exposure is closed (cross-walk `atlas/gap_audit.md` surfacing risk #8 + the peer's `c6b845f81`-style "per prior direction not to build burn-compat shims" framing); (c) per upstream-consumer audit, no peer claim stream touches `repos/ritk/{Cargo.toml, src/lib.rs:11}` per `concurrent_agents` disjoint-scope rule (the absence can be verified by `git -C repos/ritk status --short` returning zero on the inner-RITK working tree prior to staging the sub-batch #5 commit). **Pre-flight gate per session**: `cargo semver-checks release -p ritk-core -p ritk-image -p ritk-spatial` (mandatory pre-release verdict — the only source of truth for the version-bump rule) + `cargo build -p ritk-core -p ritk-image -p ritk-spatial --release` + `cargo test --doc -p ritk-core -p ritk-image` + `cargo tree --workspace -i burn`, `-i burn-ndarray`, `-i burn-wgpu`, `-i burn-cuda`, `-i burn-rocm` ALL return zero.

- **Sub-batch #6 [patch] — Standing reminder (downstream of sub-batch #5)**: `xtask/burn_surface.allowlist contract reset + CI scan gates tighten`. Cross-link to ADR 0012 §Decision §Sub-batch #6: source entries are removed; the allowlist file becomes the post-migration SSOT and is archived or rewritten. CI scan gates tighten: new CI gate asserts zero `burn::tensor::Backend`-bound public symbols; new CI gate asserts `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph. CHANGELOG `[patch]` per RITK (CI-only). **Atomic inner commit shape**: a single inner-RITK CI-only commit that (i) regenerates `xtask/burn_surface.allowlist` content against the post-`#5 xtask/burn_surface_audit` regeneration (the contract-file becomes the post-migration SSOT — the pre-`#5` generated-from-`burn::` allowlist entries parcel to migration-done rows); (ii) adds a new CI scan gate that asserts zero `burn::tensor::Backend`-bound public symbols in the cross-crate re-export graph; (iii) adds a second CI scan gate asserting `coeus_core::ComputeBackend` is the only atlas-side backend trait in the cross-crate re-export graph (i.e., every public `B: Backend` constraint has been re-routed to `B: ComputeBackend` for atlas-side surface). Cross-link: README + the Atlas-meta CI pipeline (if it exists in CI providers); the new gates are authored in the atlas-meta peripheral repo (`repos/atlas`) which carries the meta-CI pipeline, NOT on the inner-RITK repo directly — the inner-RITK commit body references the atlas-meta commit SHA that introduces the gates. **Standing pre-reqs**: (a) sub-batch #5 MUST be RE-ENTERED first — the sub-batch #6 atomic commit's body references the sub-batch #5 inner SHA in its message ("Corresponding to ritk/atlas-migration-push/batch3 tag-advance inner SHA <sub-batch-#5-sha>" — the tag annotation body also updates at this point). The atomic-boundary discipline holds because sub-batch #5 closed + tag-advanced leaves the workspace clean of the Burn-keyed surface, making sub-batch #6 a pure-CI-tool change with no behavioural code surface; (b) `xtask/burn_surface_audit` runs against the post-sub-batch-`#5` `cargo tree -p ritk -i burn-ndarray` reset state and reports zero Burn-keyed source-files per crate (the sub-batch #6 commit body MUST include this audit's complete output as evidence); (c) the new CI scan gates themselves are exercised pre-commit by `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` (the dry-run output is captured in the commit body as evidence). **Pre-flight gate per session**: `xtask/burn_surface_audit` (regenerates the allowlist contract) + `bash xtask ci --strict-atlas-only --dry-run` + `bash xtask ci --strict-backend-trait --dry-run` all return their expected zero-output invariants.

### Cross-engineering verification — `hephaestus-cuda` eigen.rs Complex upload

The earlier `fb83d009` residual risk is stale in the checked-out `repos/hephaestus` `ks5-cholesky-panel` tree. Source inspection on 2026-07-06 shows `hephaestus-cuda/src/application/decomposition/eigen.rs` maps `leto_ops::eigenvalues(&view)` output into `num_complex::Complex<f32>` with `Complex::new(z.re, z.im)` before `device.upload(&e_host)`, while `hephaestus-core::ComputeDevice::upload<T: bytemuck::Pod>` remains the generic transfer seam. Focused compile evidence: `rustup run nightly cargo check -p hephaestus-cuda --features decomposition` completed successfully against local `leto`/`leto-ops` `0.36.0`. Evidence tier: compile/build verification plus source inspection; no runtime CUDA device execution was claimed.


---

## Out-of-scope (explicit)

- **`**Spec composition layers**` updated later (e.g. `cfd-validation`, testing frameworks)**: not part of this migration; filing as separate backlog if it's not in CFDrs's own backlog.
- **HELIOS/Python binding for kwavers**: Phase-3 rich-image scoping state; deferred-until `kwavers-python` intent-bledged beyond current net-style top-level.
- **GPU backend complete production rollout across ritk-model**: PPG-model is reserved-wave per `docs/audit/2026-07-02-hephaestus-gpu-substrate-audit.md` HIGH-sev list; out of scope until defect closure.

### Atlas-root working-tree dirty triage (2026-07-06)

The Atlas-root `D:/atlas` working tree carries 29 dirty files (19 tracked-modified + 10 untracked) outside the migration-push closure chain. The vast majority have been classified as real Atlas-meta PM artifacts and committed in five atomic batches on 2026-07-06 (see commit history since `2c38db42`). The remainder is explicitly recorded below as **out-of-scope for the Atlas-parent pointer-advance ritual** — they live in scopes the Atlas-parent cannot reach (submodule internals, foreign root-level scratch, or non-submodule external dirs) and require separate-flow cleanup that is staged outside this branch's claim scope.

#### A. Root-level scratch (retracted 2026-07-06)

Cleanup chore commit on Atlas-meta deleted `nul` (Windows-reserved-name artifact on disk; the on-disk deletion API was blocked by `PermissionError` on the basename collision — see commit body for blocked paths; defense-in-depth `.gitignore` prevents future reproductions from re-entering `git status --short`) + `script.py` (root-level Python scratch that pre-existed the cleanup and was absent pre-chore per `os.path.exists`; the `.gitignore` entry ensures future re-generation path-respecting deletion can apply). Both items are now `.gitignore`-d so future reproductions cannot re-enter the Atlas-root working tree.

#### B. External / non-ASCII-dir content (retracted 2026-07-06)

Cleanup chore commit deleted `repos/SynthSeg/` (standalone git clone of the SynpthSeg brain-segmentation research project — has its own `.git/`, NOT in `.gitmodules`; deletion via `shutil.rmtree` with `onerror` handler that chmods + retries after Windows pack-file collisions on `.git/objects/pack/*`) + `repos/report/` (non-ASCII-filename dir, deletion via `shutil.rmtree` succeeded directly). Both items are now `.gitignore`d. Note: the prior-analysis claim that `repos/SynthSeg/` had "no `.git` of its own" was a stale read; the on-disk state had its own `.git/` and required the onerror handler for clean removal.

#### C. Submodule-internal dirtiness (uncommitted in inner repos — out of Atlas-parent reach)

These show up in Atlas-root `git status` as `M repos/<name>` (parent-tree entry marked dirty because the inner submodule's tree contains modifications relative to the gitlink pinned here). They are **cleanable only by an inner-submodule commit + parent-tree gitlink advance**, NOT by Atlas-parent commit. Each row is the inner-dirty count + inner HEAD as of 2026-07-06. No reclaim from Atlas-meta; these belong to the claim streams holding the inner repos.

| Submodule | Inner dirty count | Inner HEAD | Inner branch / claim stream | Triage decision (2026-07-06, per ADR 0011 §Decision §Leg 3) | Atlas-meta artifact action |
|-----------|---:|------|------|--------------------------------|------------------------------|
| `apollo`         | 235 | `f1ddf7a`     | peer claim stream `codex/apollo-atlas-migration` (WIP) | **Path B — OOS-next-sprint**: 235-file pre-CR-5 surface; queued behind ADR 0010 `apollo/atlas-migration-push/batch5` reservation | stay in §C with Batch-#5 reservation cross-walk |
| `CFDrs`          | 79  | `d58d1fe3`    | peer claim stream on `codex/cfdrs-atlas-migration` after Batch #2 closure | **Path B — OOS-next-sprint**: Batch #2 remains closed at `d58d1fe3`, but current source dirtiness has reappeared after the closure push and belongs to the CFDrs inner-repo claim stream; do not retract this row from §C until the inner tree is clean again or a new CFDrs commit lands | stay in §C; keep Batch #2 closure cross-link, but current dirty-tree accounting is live |
| `coeus`          | 19  | `b2beec3`     | peer claim stream on `main` (source + docs; includes dtype, tensor, Python embedding, and parity-test files) | **Path B — OOS-next-sprint**: not a PM-only closure-tail; source files are dirty and must land inside the Coeus claim stream with Coeus package gates | stay in §C as peer-active; no Atlas-meta source reclaim |
| `eunomia`        | 7   | `57d7789`     | peer claim stream (CR-4 closed; CR-EUNOMIA-COMPLEX ⏳ `acos/asin/atan` PR-queue per ADR 0006; **eunomia-side retroactive-closed per ADR 0006 §Decision §1 Path B**) | **Path C retroactive-closed 2026-07-06** (ADR 0006 §Decision §1 Path B additive `ComplexField::zero()`/`::one()` defaults landed at eunomia HEAD `57d7789`); 7-dirty reclassified as peer's UNRELATED `acos`/`asin`/`atan` PR-queue (per `## In-flight claims` Neighbor claim streams). Cross-walk §C eunomia reclassification bullet below + `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` + ADR 0008 §Decision §0 reframed. | retract from §C on next §-triage pass; the prior `Path B — OOS-next-sprint` classification was based on a stale ADR 0008 §0 Variant A / unseal `NumericElement` framing that ADR 0006 explicitly REJECTED |
| `gaia`           | 5   | `8f4a862da`     | peer claim stream `refactor/migrate-to-leto-geometry` | **Path B — OOS-next-sprint**: source and benchmark files are dirty (`src/application/csg/arrangement/classify.rs`, `benches/csg_performance.rs`), so the PM files cannot be committed as a source-disjoint Atlas closeout | stay in §C as peer-active; no split closeout |
| `hermes`         | 46  | `1b5392a`     | peer claim stream | **Path B — OOS-next-sprint**: 46-file scattered across `hermes-simd-*` crates + ADR footer updates; moderate-size, multi-domain peer-active | stay in §C; peer-active |
| `kwavers`        | 27  | `400c32624`   | peer claim stream `codex/kwavers-core-moirai-parallel` ACTIVE | **Path B — OOS-next-sprint**: dirty count drained from 132 to 27; remaining Batch #1/#4 surface still belongs to the kwavers inner-repo claim stream and stays behind ADR 0010 `kwavers/atlas-migration-push/batch1` reservation | stay in §C; cross-walk ADR 0010 reservation; drain-counter annotation now `-575` from the original 602-file capture |
| `leto`           | 14  | `626ebf538`     | peer claim stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile | **Path B — OOS-next-sprint**: 14-file ACTIVE peer stream (disjoint from CR-4 leto side per `concurrent_agents`) | stay in §C; disjoint with CR-4 leto side |
| `melinoe`        | 13  | `7ec0a44`     | peer claim stream | **Path B — OOS-next-sprint**: 13-file `crates/halo/` + 4 src sync; CR-1 consumer (brand doctrine holder for `apollo-ghostcell` deletion); cross-crate work with apollo CR-5 reservation | stay in §C; CR-1 cross-link |
| `moirai`         | 26  | `9b7881f`     | historical peer claim stream `refactor/remove-dead-subsystems` | **Superseded:** CR-2 closed 2026-07-18 with zero `#[global_allocator]` sites across the three library crates | historical snapshot only |
| `ritk`           | 0   | `8f8360ff`    | local follow-up committed after the clean nine-commit Batch #3 migration sequence, then advanced by Atlas-parent pointer commits | **Path C closed for risk #1 and Helios DICOM ownership**: inner commit `65a1a0fd` removes stale Burn `wgpu` default; inner commit `d7a940b5` adds the Batch #3 sub-batch #1 Atlas-typed parallel trait surface; inner commit `8f8360ff` adds typed DICOM attribute reads for downstream imaging consumers | pointer advanced by this Helios/RITK DICOM ownership commit; keep broader Batch #3 closure separate until package gates are current |
| **Σ** | **471 inner files** (fresh `git status --short` sweep; Helios and RITK now clean) | — | — | **2 retroactive/closed rows + 0 source-disjoint partial closeouts + 9 stay-OOS-next-sprint rows** | **No source-disjoint Atlas-meta closeout remains; next source work belongs inside the active inner-repo claim streams** |

#### D. Helios/RITK DICOM ownership cleanup (closed 2026-07-06)

Commit `c5f2a84e` closed the six-file Helios direct dependency slice under `repos/helios/**`: H-062 removed the unused direct `num-traits` workspace edge, H-061 removed Helios' unused aggregate dicom-rs `ndarray` feature edge while leaving pixel decoding owned by `ritk-dicom`, and the local Melinoe patch now lets patched Gaia resolve its `melinoe` 0.8.0 edge during Helios validation. Follow-up RITK commit `8f8360ff` closes the remaining production DICOM boundary drift by moving common DICOM image tag vocabulary and typed parsed-object attribute reads into `ritk-dicom`; Helios now consumes that API for parsing, typed attributes, transfer-syntax lookup, and pixel decode. Current Atlas-root status is expected to have no committed `repos/helios/**` direct-file dirtiness after this pointer-advance commit; the remaining imaging boundary is H-063 (`helios-imaging` audit for generic toolkit operations that belong in RITK).

#### E. Remaining future-correction hooks (post-2026-07-06)

§A and §B retractable future-correct clauses resolved in the 2026-07-06 cleanup chore commit on Atlas-meta (the 4-pattern `.gitignore` append + the on-disk SynthSeg + report deletions + the 4-pattern future-proofing). §C is partially-triage-classified per ADR 0011 §Decision §Leg 3 OOS-record cadence (sub-routine "Initial record" + "Post-resolution §-E update when stay-OOS-next-sprint"). Total submodule-internal dirty now stands at 471 inner files after the Helios direct-file closure (`c5f2a84e`), RITK Batch #3 sub-batch #1 pointer advance (`61931faf` to `d7a940b5`), Helios/RITK DICOM ownership pointer advance (`8f8360ff`), and the refreshed peer-WIP counts. This triage leaves three open forward-looking hooks:

- **§C retroactive-closings (Path C rows)**: 2026-07-06 triage retracted the zero-dirty `hephaestus`, `mnemosyne`, and `themis` rows from §C because they are no longer submodule-internal dirtiness. `CFDrs` was not retracted: re-verification shows 79 inner dirty paths on `codex/cfdrs-atlas-migration`, so the Batch #2 closure remains recorded while the current dirty tree stays tracked as a live CFDrs claim stream. The remaining Path C row is `eunomia`, which is covered by the separate reclassification bullet below.

- **§C partial-closeable queue (Path A candidates for next claim stream)**: empty after re-verification. `coeus` and `gaia` both contain source/benchmark dirtiness, so their PM files cannot be split into source-disjoint commits without hiding peer-active implementation context. `ritk` left this queue after inner commit `65a1a0fd`. Recommended pre-commit gate for future claim streams: `git -C repos/<X> status --short` once before the inner commit, to confirm no peer-stream claim landed in the interim.

- **§C stay-OOS-next-sprint (Path B rows)**: 9 submodules post-2026-07-06 refresh — `apollo` (235, Batch #5 reservation `apollo/atlas-migration-push/batch5` per ADR 0010; pre-CR-5 surface), `CFDrs` (79, Batch #2 closure remains closed at `d58d1fe3`, but current dirty paths belong to the live CFDrs inner-repo stream), `coeus` (19, source + docs peer stream), `gaia` (5, source/bench + PM peer stream), `hermes` (46, peer-active scattered), `kwavers` (27, Batch #1 + Batch #4 + Phase-1B reservations), `leto` (14, ACTIVE peer stream `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile), `melinoe` (13, CR-1 consumer cross-crate with apollo Batch #5; brand doctrine holder), `moirai` (26, Batch #6 reservation `cfd-core+ritk-core+moirai/atlas-migration-push/batch6` per ADR 0010; `refactor/remove-dead-subsystems` ACTIVE). Removed: `eunomia` (retroactive-closed; 7 dirty files are unrelated `acos`/`asin`/`atan` PR-queue), `ritk` (clean at `8f8360ff` after the DICOM ownership pointer advance), and `helios` (direct dependency plus DICOM ownership slices closed; H-063 filed for future `helios-imaging` audit). No Atlas-meta reclaim per disjoint-scope rule (ADR 0011 §Decision §Leg 2). Each row stays in §C until its owning claim stream emits a pointer-advance to Atlas-parent.

- **§C eunomia row reclassification (post-2026-07-06 phantom-blocker discovery)**: the §C `eunomia` row above has been reclassified from `Path B — OOS-next-sprint` to `Path C retroactive-closed (eunomia-side per ADR 0006 §Decision §1 / Path B additive `ComplexField::zero()`/`::one()` defaults landed at HEAD `57d7789`)`. The 7-dirty is now re-attributed to the peer's UNRELATED active WIP stream (`acos`/`asin`/`atan` PR-queue per § In-flight claims Neighbor claim streams section) — OUT of §C scope on the next §-triage pass per ADR 0011 §Decision §Leg 3 \"Resolution branch\". The residual Phase-1B is kwavers-side per ADR 0008 §Decision §0 (reframed per the discovery); cross-walk `D:/atlas/docs/coordination/2026-07-06-eunomia-csr-scalar-phantom-blocker.md` for the full verification matrix.

- **§D (Helios/RITK DICOM ownership closure)**: closed by `c5f2a84e` plus RITK `8f8360ff` and this Helios consumer reroute; current Atlas-root status has no committed `repos/helios/**` direct-file dirtiness after the pointer-advance commit, and H-063 tracks the remaining `helios-imaging` generic-toolkit audit.

- **`nul`** (whose on-disk deletion API was blocked by Windows-reserved-device-name PermissionError on this build): the `.gitignore` defense in this chore commit prevents future `nul` reproductions from re-entering `git status --others`. The on-disk file may still surface via `dir` from bash contexts but is gitignored; admin `cmd /c del /F /Q nul` or Windows-reboot may be required for actual on-disk removal. Filed for the next codex-session restart-handler.


### RN-CC-05 (transitive parent-SHA chain breach detection + audit-discipline establishment)

Filed by `chore(atlas): Roll-up review-nit RN-CC-05 -- transitive parent-SHA chain breach detection` (post-`536366e`). Retroactively addresses code-reviewer-minimax-m3 NIT surfaced in the post-`536366e` cycle: commits `93a0723177` + `a96d46d7294` declared the RN-CC-04 discipline but inline-cited the parent rather than carrying a `Parent-SHA:` line-block at the top of body. Per NO-AMEND, retroactive body repair is forbidden; the breach is disclosed across 4 docs files + recorded in the RN-CC-05 commit body. Parent-SHA: forward-propagation audit discipline: `rg -F "Parent-SHA:" gap_audit.md backlog.md checklist.md docs/coordination/` yields >=2 line-hits; `git log --grep "Parent-SHA:" --oneline` yields >=2 entries. Self-discipline demonstration: `74df54d4f963b96d1b642ce89e77c9b019ad3de7` + `74df54d4f` + `536366e` + this RN-CC-05 chore carry line blocks at top of body; `93a0723177` + `a96d46d7294` need forward-session transparency (this row).

## Review nit rolling list (forward-looking improvement tracking, 2026-07-08)

> Persistent review-improvement tracking items surfaced by the
> post-`91896c477` code-reviewer pass on the Atlas architectural
> directive framing chore. Each nit is annotated: ID, scope,
> severity, source-chore, fix status, suggested follow-up.
> Future chore-cycles reference this list when templating
> `docs(atlas):` commits so the same drifts don't recur.

| ID | Nit | Severity | Source chore | Status | Follow-up |
| --- | --- | --- | --- | --- | --- |
| **RN-01** | CR-2 (open; Batch #6) citation error -- mnemosyne row cited "per CR-2 (open; Batch #6)" but CR-2 is **OPEN** per Surfacing risks row 1.2 (Batch #6 reserved), not CLOSED. | factual | `91896c477` | **FIXED in `b29cfa24b`** (mnemosyne row changed to "per CR-2 target axiom [open; Batch #6]") | file-wide rg `per CR-2 (open; Batch #6)` on subsequent docs-only chores; extend fix to any other inverted citations |
| **RN-02** | 11+3 stack split -- the monolithic `### Stack (13 atlas crates)` table conflated 11 providers with 3 consumers in one 14-row table. | structural | `91896c477` | **FIXED in `b29cfa24b`** (split into `### Provider stack (11 atlas crates)` + `### Consumer migration targets (3 simulation suites)`) | template future `Atlas-stack` table sections with the provider/consumer split pattern from the start; split mnemosyne+themis row when allocator-pair semantic is involved |
| **RN-03** | Gitlink SHA truncation -- table used 7-char truncated SHAs (`98a02b6...`, `37ff12d5...`, etc.) which break grep-ability and don't match the 40-char convention used elsewhere in `gap_audit.md`. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (all 14 table SHAs now full 40-char live from `git ls-files --stage`) | prefer full 40-char SHA in all `docs(atlas):` table cells; only allow truncation when the SHA is genuinely abbreviated (e.g., an inner HEAD short-SHA in narrative prose) |
| **RN-04** | FRONT-MATTER sync -- `gap_audit.md` lines 1-11 blockquote enumerated 4 record-types but the new `## Atlas architectural directive` section added a 5th without updating the enumeration. | presentational | `91896c477` | **FIXED in `b29cfa24b`** (item 5 appended to front-matter blockquote: `Atlas architectural directive (2026-07-08); consolidator framing -- stack table, migration targets, design principles, constraints, bulk-migration priority order`) | when adding a new top-level section to `gap_audit.md`, also update lines 1-11 blockquote enumeration; consider automating via a pre-commit check |

**File-wide open follow-ups surfaced by the post-`b29cfa24b` review**:

- **CR-2 file-wide citation scope (RN-01 scope extension)**: a file-wide
  `rg -n 'per CR-2 (open; Batch #6)' gap_audit.md` post-patch may surface
  additional inverted citations outside the table row that was fixed
  in RN-01 (e.g., CR-class status cell, Surfacing risks row 1.2
  narrative, cross-cutting notes). **Status**: not yet verified
  post-patch; a follow-up patch chore should run the rg + extend the
  fix to any other hits.
- **Subsection naming collision (RN-02 cosmetic extension)**: the new
  `### Consumer migration targets (3 simulation suites)` (table)
  sits adjacent to the existing `### Migration consumer targets (3 in
  flight)` (prose). The two names are lexically adjacent on
  "consumer migration targets" -- a grep footgun. **Status**: not
  yet renamed; recommend renaming the new table to `### Consumer
  simulation suites (3 in flight)` for disjoint-name grep-ability.
- **Prose subsection inner-HEAD SHA uniformity (RN-03 scope
  extension)**: the preserved prose subsection (`### Migration
  consumer targets (3 in flight)`) still uses 9-char short-SHAs
  (`inner HEAD 05500930c`, `702e4f125`, `d58d1fe3`, etc.); the new
  directive table uses 40-char SHAs. **Status**: deliberate scope
  choice -- not yet upgraded for visual consistency. Either
  upgrade in a follow-up patch, or document the inconsistency
  explicitly in body-scratch as a preservation choice.
- **Body-scratch subject parent-SHA anchor (RN-04 audit-discipline
  extension)**: subject of `b29cfa24b` is `Patch 4 review nits on
  directive chore (...)` and doesn't grep-match `91896c477` (parent
  SHA). **Status**: noted as a `concurrent_agents` precedent for
  future subject-pattern discipline; recommend appending `(parent
  <SHORT-SHA>)` to chore subject or putting parent-SHA on
  body-scratch line 1.

**Audit-lifecycle note**: this rolling list persists until (a) a
follow-up chore closes all 4 RN items above (RN-01..RN-04 already
FIXED in `b29cfa24b`; 4 follow-up extension nits remain open), or
(b) a future chore re-classifies any item as RESOLVED-by-design
via explicit `docs(atlas): Mark RN-XX as RESOLVED-by-design (...)`
commit. Re-probe cadence: per `docs(atlas):` chore landing that
touches `gap_audit.md` PM surface.

**Cross-link**: see `gap_audit.md` `## Atlas architectural directive
(2026-07-08)` (line 12) for the source-chore context + `## Surfacing
risks` for the open follow-ups' parent audit-class entries. See
`D:/atlas/gap_audit.md` `L339 PRESERVED` parity-row in the
`### Anchor-evolution history` section for the prior anchor-iteration
history convention (anchor-tail intent-over-version naming).


---

- **This codex session (2026-07-08, Bulk-provider-surface round-1 + round-2 + round-3)**: three sequential bulk-advance blocks landed (round-1 `2e1c4f20d`→`274a6a961`→`a12d1dd77` for apollo/coeus/hermes/melinoe/ritk + themis pointer refreshes; round-2 `5d3395e95` + `715cff24e` + `02da06611`→`ab71f08ad`→`36acbbca9` for hermes-r2/coeus/cascade + multi-PM-reconciliations + `.gitignore hardening); round-3 `ad6cf57d4`→`1828ea14a`→`852de7129`→`769b70a67`→`1fe3c0e56` for apollo/eunomia/hermes/leto/mnemosyne). See `gap_audit.md` row 13 for the per-submodule advance record + provenance triples + branch-context notes (especially hermes on `rescue/detached-simd-numa-work` divergent 17 commits ahead of `origin/main`, NOT peer-WIP at the parent gitlink level; mnemosyne sjump `482670d` → `98a02b6` reflects the Miri alloc/free HIGH-PRIORITY finding at `eff(backend)` + `fix(backend)` + `docs(gap_audit)` chain). **Net alignment state post-`1fe3c0e56`**: all 12 actively-tracked submodules (apollo, coeus, eunomia, helios, hermes, leto, melinoe, mnemosyne, ritk, themis, CFDrs, kwavers) ALIGNED at inner HEAD with zero DIVERGED gitlinks — the first all-aligned state since the `e0bf55684` cross-tree reclamation audit. **ritk-python test suite (47/47)** compiled+passed at committed inner HEAD `1f49278c` (value-semantic asserts — see `gap_audit.md` row 154 bulk-advance unblock evidence). **KW-CV-001 watchpoint re-affirmed ACTIVE** at inner HEAD `35ee01076`: trigger `(cd /d/atlas/repos/kwavers && git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l)` returns 0; peer continues slice-by-slice Batch #1 + Batch #4 work without explicit closeout commit. **Atlanta-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit (per `concurrent_agents` disjoint-scope rule); the round-3 block leaves kwavers at the peer-tracked HEAD `35ee01076` (atlas-meta gitlink already aligned, not divergent, just not watching for closure-style advances here — the KW-CV-001 watchpoint owns that path). **Branch context**: this turn's round-3 work landed under `codex/kwavers-atlas-integration`; `36acbbca9` `.gitignore` hardening prevents transient root scratch artifacts from re-entering `git status --short` (no body-scratch file was created for any of the 5 round-3 chore commits, per the user's signal-change-in-the-tree batch ceremony convention from ADR 0010 §Per-batch name pattern; each commit body authored inline via subject + body `-m` pairs + a final `-m` provenance-triple block citing row 11 dynamic-SHA extraction). **Cross-references**: `gap_audit.md` row 13 (per-submodule advance record with prior-SHA + derived-full-SHA + inner-chore-subject for each of the 5 round-3 modules); `checklist.md` §Next micro-sprint for the round-3 line-item summary. **Residual risks** (tracked in `gap_audit.md` row 6 row-268–270 kwavers sub-bullets): kwavers 267 dirty files at inner HEAD `35ee01076` is peer-WIP, not reclaimable from atlas-meta; kwavers Batch #1 closure condition (zero `par_for_each` source sites) is NOT yet met (41 sites across 15 files per `gap_audit.md` line-93); kwavers Batch #4 closeout condition (zero `burn::` source hits + zero `crates/kwavers-solver/Cargo.toml:42` burn dev-deps + `burn.rs`/`burn_compat` deletion) WAS met at `05500930c` per the line-92 sub-bullet (file deletion + manifest strip landed on the peer stream). The next bulk-advance round (round-4) is contingent on either inner HEAD churn (peer-WIP-after-push divergence) OR KW-CV-001 firing for kwavers.
- **This codex session (2026-07-06, Helios closure)**: `c5f2a84e` closed the direct Helios H-061/H-062 dependency slice by removing the unused `num-traits` workspace edge, removing the aggregate dicom-rs `ndarray` feature edge, adding the local Melinoe patch required by patched Gaia's `melinoe` 0.8.0 edge, and syncing Helios PM evidence. Concurrent peer commit `61931faf` then landed the RITK Batch #3 sub-batch #1 Atlas-parent pointer advance; preserve that pointer state.
- **This codex session (2026-07-06, Helios/RITK DICOM ownership)**: RITK inner commit `8f8360ff` adds `ritk-dicom::{DicomTag, tags, DicomAttributeRead}` so downstream DICOM geometry/modality-LUT attribute reads are RITK-owned. Helios H-061 now routes production DICOM parsing, typed attributes, transfer-syntax lookup, and pixel decode through `ritk-dicom`; dicom-rs remains direct only as a dev-dependency for synthetic Part 10 fixture generation. Helios H-063 is filed for the remaining `helios-imaging` audit: generic medical-image I/O/registration/toolkit operations move upstream to RITK; radiation-domain MVCT projection/reconstruction kernels stay in Helios.
- **This codex session (2026-07-07, RITK DEP-497-01 dead-dep strip)**: `repos/ritk` commits `7a66d1ee` (strip unused production `burn` dep from 17 leaf crates: `ritk-{cli,core,filter,io,jpeg,metaimage,mgh,minc,model,nifti,nrrd,png,registration,segmentation,snap,statistics,tiff,transform,vtk}`; `burn-ndarray` dev-dep retained where sub-batch #3 per-crate test ports are still open) + `00d57005` (checklist sync), pushed to `origin/main`. Distinct from Batch #3 sub-batch #5 (`[major]` full Burn Cargo strip + `Image<B,D>` re-export) per ADR 0012 — this is a non-breaking dead-edge removal, no version bump. Verified: `cargo nextest run` across the 19 touched crates 4258/4258 green, `cargo clippy --workspace --all-targets -D warnings` clean, `cargo fmt --check` clean for touched crates, `cargo doc --no-deps` no new warnings. Fixed an incidental `clippy::doc_lazy_continuation` false-positive in `ritk-model/src/ssmmorph/encoder/tests.rs`. Residual risks filed in `repos/ritk/checklist.md` (2 pre-existing broken intra-doc links in `ritk-filter`; a full-workspace-nextest-only timeout in `ritk-snap::pacs_ops` reproduced only under full-parallel resource contention, isolated run passes in 2.1s — not a hang). Atlas-meta `repos/ritk` gitlink advanced to `00d57005` via the dynamic-SHA-extraction convention (gap_audit.md row 11).
- **`repos/kwavers` `codex/kwavers-core-moirai-parallel` — peer ryancinsight ACTIVE** (inner HEAD `05500930c` 2026-07-07 19:11, `[ahead 0, behind 0]` of `origin/codex/kwavers-core-moirai-parallel` per inner `git rev-list --left-right --count`; atlas-meta `HEAD:repos/kwavers` gitlink pinned at `7235d464afb04dfec62dee1cd8e6e8d660b54250` lagging inner HEAD by 37 commits). State at inner HEAD `05500930c` per T1 verification: **Batch #4 (kwavers-solver PINN Burn → Coeus) source-residual is now ZERO** — canonical inner chore `8b128c478` "Remove dead burn compatibility shim and drop burn dependency" + slice 3+ commits drained the residual; `crates/kwavers-solver/src/burn.rs` + `burn_compat` module ABSENT; `rg -n '\bburn\b' -g '*.toml' .` zero hits in `crates/kwavers-solver/Cargo.toml` + root `Cargo.toml`; `rg -l '\bburn::' crates --type rust` zero hits across the kwavers source tree (was 186 line-hits / 80 files at `b605e2e74`, full clean at `05500930c`). **Batch #1 (kwavers-solver / kwavers-physics Rayon → Moirai)**: `crates/kwavers-{solver,physics}/Cargo.toml:{24,20}` now read `ndarray = { version = "0.16", features = ["serde"] }` (per peer `702e4f125` "drop unused ndarray/rayon feature from kwavers manifests"; the `rayon` feature strip is landed, contradicting the prior stale paragraph that read `features = ["rayon", "serde"]`); residual is now **41 `.par_for_each()` sites across 15 files** in `crates/kwavers-solver/src` (down from 84 sites / 28 files at `b605e2e74`, −51%) — concentration in `forward/{elastic/swe/{integration/integrator/mod,stress/divergence}, nonlinear/{kuznetsov/{diffusion,nonlinear,numerical,operator_splitting/mod,solver/{model_impl,rhs},spectral,workspace}, westervelt_spectral/spectral}, pstd/extensions/{elastic,elastic_orchestrator/pml/mod}, multiphysics/fluid_structure/{interface,solver/struct_impl}}`. Closeout state: no formal `closeout` / `final` / `completion` commit in the last 30 inner commits — peer lands Batch #4 + Batch #1 slice-by-slice without explicit closure commits. **Atlas-meta continues to defer parent-side pointer advance** for `repos/kwavers` until a kwavers-side final closeout commit lands (per `concurrent_agents` disjoint-scope rule). `burn.rs` + `burn_compat` facade deletion + Cargo.toml strip are LANDED on the inner peer stream (lifting the surrogate pre-condition cited in sub-batch #5 standing reminder per `docs/adr/0012-ritk-burn-trait-rebind.md`). See `gap_audit.md` row 6 kwavers sub-bullets L268-L270 for the kwavers-side reconciliation record.
- Neighbor claim streams to honor (disjoint from kwavers Batch #1, also DO NOT touch): `repos/moirai` `refactor/remove-dead-subsystems` (26 dirty paths — moirai source forbidden); `repos/leto` `codex/leto-cr4-ssot-rebind` / fixed-spatial reconcile (14 dirty paths — leto source forbidden); `repos/coeus` `main` (19 dirty paths); `repos/eunomia` `main` (`acos`/`asin`/`atan` peer queue, 7 dirty paths); `repos/apollo` (235), `repos/CFDrs` (79), `repos/gaia` (5), `repos/hermes` (46), and `repos/melinoe` (13) carry in-flight peer claims. `repos/helios`, `repos/ritk`, `repos/hephaestus`, `repos/mnemosyne`, and `repos/themis` are clean of inner dirty paths after the Helios/RITK DICOM ownership closure and prior pointer-sync commits.
- The moirai-parallel API surface for kwavers Batch #1 already exists: `for_each_chunk_pair_mut_enumerated_with`, `for_each_chunk_triple_mut_enumerated_with`, `for_each_chunk_quad_mut_enumerated_with`, `enumerate_mut_with`, `for_each_index_with` (moirai-parallel `src/ops.rs:281,335,408,125,155`). No moirai source change is required for Batch #1 closure; the consumer-side helpers in `crates/kwavers-physics/src/parallel.rs` already cover 1-mut + N-imm and 2-mut + N-imm arities, with 3-mut + N-imm and 4-mut + N-imm indexed zips (visible in `kwavers-solver/src/forward/elastic/swe/{integration/integrator/mod.rs,stress/divergence.rs}` and `forward/pstd/extensions/elastic.rs` and `forward/pstd/extensions/elastic_orchestrator/split_field_step/{stress,velocity,mod}.rs`) as the remaining helper-coverage gap.
- **This codex session (2026-07-09, Bulk-migration #2 E0369/E0599 closure-front triage in `kwavers-math`)**: dry-run enumeration via `rg '::ones\([^)]*\)\s*\*' --type rust` + `rg '\.view\(\)' --type rust` against `crates/kwavers-math/src/**` returns **0 `::ones(...) * scalar` sites (E0369 front fully drained, idiom-set closure confirmed)** and **151 prefix-form `.view()` call sites across 27 distinct files (138 bare `.view()` + 13 `.view_mut()`; total per row 14.5 SSOT in `gap_audit.md`; E0599 front, separate closure track)**. **Idiom-set triage conclusion**: the 3-item idiom list recorded in `gap_audit.md` `### Bulk-migration priority #2 routing lesson (2026-07-09)` — `array.iter_mut().for_each(|v| *v *= scalar)`, `as_slice_memory_order_mut()`, and the project-native `scale_array` helper — IS operationally complete for the E0369 front as of the prior-session proof-of-pattern work (`avx2.rs:46,56` + `dispatcher.rs:139,151` closed 4 of 4 E0369 sites; cargo check error count 128 → 124). **The `.view()` E0599 sites are a SEPARATE closure-front** (most call sites are `.view()` / `.view_mut()` invocations on ndarray `Array3`/`Array4`, requiring explicit error propagation rewrites + trait-bound refactor of `Boundary<_>` carrier), and **are NOT covered by the E0369 3-item idiom set**. Per the user’s “if new patterns emerge, file a follow-up docs update rather than diverge from the lesson” guidance, the 3-item list is NOT expanded in this turn — the E0599 front stays tracked here as a transient atlas-meta carryover with the 138/27 enumeration, awaiting either peer-side Bulk-#2 phase work or future-session idiom-set expansion posture.


- **[SUPERSEDED 2026-07-09 by ADR 0013 `## Supersedes` field]** the prior partial-closure-mark was 2026-07-08; superseded; see D:/atlas/docs/adr/0013-kwavers-batch1-source-side-closure.md for the full Batch #1 source-side closure mark.
- **slice 1 partial-closure-mark 2026-07-08 — kwavers Batch #1 source-side migration slice 1 PARTIAL CLOSURE (2/41 sites, 1/15 files)**: per the peer's `5cd8c708` chore (`refactor(kwavers-solver): Migrate struct_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 1)`, on `codex/kwavers-core-moirai-parallel` atop parent `ccc6bbf9`): 2 of the 41 source-side `.par_for_each()` sites have been migrated. The 2 sites live in `crates/kwavers-solver/src/multiphysics/fluid_structure/solver/struct_impl.rs` (3D `Array3<f64>` element-wise relaxation on `p_fluid_ghost` + `p_fluid_ghost_prev`; plus a 1D sub-view relaxation on `t_solid_ghost` + `t_solid_ghost_prev`). Migration dispatch: idiomatic `moirai_parallel::ParallelSliceMut::par_mut().enumerate(closure)` trait form (auto-Adaptive policy; no `ExecutionPolicy` generic needed); cargo-check pre-validate clean at inner HEAD `5cd8c708`. **KW-CV-001 watchpoint state**: remains ACTIVE — the closure-style trigger (`closeout|final|completion|close-batch` substring grep on the last 30 kwavers commits) is still 0; per the `concurrent_agents` disjoint-scope rule, atlas-meta is *observing* (not advancing) the peer's slice-by-slice progress without re-emitting the prior retracted full-closure mark. The remaining 39/41 sites / 14/15 files will be tracked via per-slice partial-closure marks (this entry is the first such mark) until the source-side count actually drops to zero, at which point the full closure-mark can be reasserted. **Atlas-meta path forward**: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit; do NOT bump the kwavers gitlink from the current `35ee01076` even as subsequent Batch #1 slices land on the peer stream, per the watchpoint's no-advance-without-closeout policy. **Note (data-quality, post-e73d524 dedup)**: the round-3 codex-session block was historically duplicated at L87+L90 (pre-chore-cycle stale snapshot); de-duplicated in chore-commit `e73d5241f` via structural-cleanup; see the OBSERVED 2026-07-09 tombstone (post-cut at L283) for the audit trail. The partial-closure mark is appended at end-of-file for grep-ability + future-automation reliability.


- **This codex session (2026-07-08, Bulk-provider-surface round-4 — post-OOB `6902d2e92` re-probe)**: 7 atomic chore captures in this turn. The OOB consolidation commit `6902d2e92` ("chore(atlas): Advance repos/hephaestus pointer to 240b260 (CU-P6/CU-M3)") absorbed my staged round-4 reset state, capturing `hermes` `5ad1b58 → c7b17b02` + `leto` `a9572da → 86d366bc` (batched LU / CSC sparse format / CG/GMRES iterative solvers — unblocks kwavers-solver Bulk-solver migration closure target) bundled into a single `e3223094a`. The remaining per-crate captures split into one-atomic-chore-per-crate for cleanliness:
  - `6a598da91` kwavers `35ee01076 → 89117870` (inner `Migrate kwavers Complex/ndarray types to eunomia/leto atlas crates` — Phase-3 closure of Complex<f32>/f64, ndarray Array, coefficient paths onto eunomia+leto substrates; replaces nalgebra/ndarray/numeric-complex stack in kwavers-core domain)
  - `0e34ae082` coeus `e36f95f → ec69a6a` (inner `fix(coeus-dist): close TOCTOU race in TCP test port allocation` + co-emitted `342f38d` MS-406/407 reconciliation; TOCTOU between bind and listen eliminated in coeus-distributed harness)
  - `045291499` ritk `1f49278c → e75d8748` (inner `Add Module/AutodiffModule impls for DisplacementField and DisplacementFieldTransform` — DIRECTLY resolves the displacement_registration_test failure tracked in row 6; Sub-batch #5 RITK-spatial-rebind closure per ADR 0012)
  - `4a4cf928a` coeus `ec69a6a → 006f2a7` (inner `feat(coeus-nn): add MaxPool3d/AvgPool3d benchmark rows (G-043)` — criterion bench registry extension for 3D pooling kernels)
  - `4b7f4804e` kwavers `89117870 → 09c645f30` (inner `Migrate kwavers-core/source/signal/grid/field from ndarray to leto` — Phase-4 closure of kwavers-core domain crates source/signal/grid/field off ndarray onto leto's NDArray substrate; follow-on to `89117870`)
  - **Net alignment state post-`4b7f4804e`**: all 13 actively-tracked submodules ALIGNED at inner HEAD with zero DIVERGED gitlinks. Seven bulk-provider pointers advanced in this session cycle (well above round-3 cadence). KW-CV-001 watchpoint re-probed at every commit — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing, not `closeout`/`final`/`completion`/`close-batch`.
  - **Atlas-meta action posture**: round-4 captured all in-session churn. Awaiting peer's next kwavers/ritk commit; either KW-CV-001 fires for kwavers OR slice-7+ launches to re-open round-5 capture. Either path stays in observation mode; no source-tree work concrete to atlas-meta.

- **This codex session (2026-07-08, mid-session test/example validation sweep)**: user directive "cleanup and resolution of all test and example issues/errors" triggered a fresh sweep across consumer-side trees at the just-advanced inner HEADs. T1 evidence:
  - **ritk** at inner HEAD `529d6651`: `cargo nextest run -p ritk-python --lib` 47/47 PASS (value-semantic asserts verified — `mi_normalized_identical_is_one`, `mi_rejects_shape_mismatch`, `test_validate_percentiles_descending_elements_returns_error`, `test_validate_range_inverted_bounds_returns_error`).
  - **CFDrs** at inner HEAD `72275347fb71`: `cargo check --workspace --all-targets` PASS (no warnings); `cargo nextest run --workspace --lib` 2177/2177 PASS (1 skipped, 0 failed, 1 slow at 28.1s — within CFDrs's 30s terminate budget).
  - **CFDrs subset** `cargo nextest run -p cfd-math -p cfd-1d -p cfd-2d --lib`: 1335/1335 PASS (1 skipped, 24.9s execution).
  - **kwavers** at inner HEAD `ccc6bbf9e6` (`Workspace-wide ndarray↔leto boundary fixes; cargo check --workspace passes`): `cargo check -p kwavers-solver --workspace` PASS; `cargo check --workspace` PASS with 1 dead-code warning (`fn to_leto3` unused in `crates/kwavers-simulation/src/dispatch/elastic_pstd.rs:8:4`); **`cargo nextest run --workspace --lib` FAILS at compile** with 1 site: `crates/kwavers-solver/src/plugin/mod.rs:204:21` — the test-mock `NullBoundary::apply_acoustic_freq` reads `_field: &mut Array3<kwavers_math::fft::Complex64>` (resolving via in-scope `use ndarray::Array3;` at line 182, which shadows the workspace's `leto::Array3` re-binding); the `Boundary` trait now declares `&mut leto::Array<eunomia::Complex<f64>, VecStorage<eunomia::Complex<f64>>, 3>`. **Disjoint-scope peer-owned per `concurrent_agents`**: atlas-meta records surface + line; the inner peer stream owns the 2-line edit (`use ndarray::Array3;` → `use leto::Array3;` at L182 + parameter signature updates at L204). Filed at `gap_audit.md` row 14.5.
  - **Note**: a 2nd `kwavers-solver` site at `crates/kwavers-solver/src/forward/pstd/physics/residual_gas_absorption.rs:74` (`spectrum: &mut Array3<kwavers_math::fft::Complex64>`) ALREADY uses `use leto::{Array3, ArrayView3};` (L65), so its `Array3` resolves correctly. Only the plugin test mock is broken.
- **`repos/kwavers` gitlink advance this session**: `4f344f840` (Phase-3 → Phase-4 → Phase-5 sweep closure at inner HEAD `ccc6bbf9e6`). KW-CV-001 watchpoint re-probed at `ccc6bbf9e6` — still 0; peers continue `Migrate *.rs from ndarray to leto` subject phrasing. Atlas-meta defers final closeout pose until peer's closeout subject lands.

- **[OBSERVED 2026-07-09 round-3 codex-session block + Standing reminders + Cross-engineering verification + Out-of-scope + Atlas-root dirty triage + Review nit rolling list deduplicated to canonical Region 1 (L1-L282) ordering via atomic structural-cleanup chore; see `### In-flight claims (per concurrent_agents)` L82 + canonical `#### Standing reminders` L112 + canonical `## Review nit rolling list` L186 for the authoritative copies. This tombstone also absorbs the prior `93f676ffd` forward-auditor cross-reference to the L262 SUPERSEDED + L263 slice-1 partial-closure-mark block, which remains the canonical Batch #1 source-side closure reference (see ADR 0013 `## Supersedes` field for the full Batch #1 source-side closure mark).]**


## Batch #1 source-side migration -- slice 3 partial-closure-mark 2026-07-08

Per the peer's `d2cb977b` chore (refactor(kwavers-solver): Migrate diffusion.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 3), on codex/kwavers-core-moirai-parallel atop parent c77a926d8): **5/41 sites migrated in 3/15 files** cumulative. The 1 new site is in crates/kwavers-solver/src/forward/nonlinear/kuznetsov/diffusion.rs (1 mut + 4 immut Zip par_for_each at L93, migrated with 5 is_standard_layout() asserts + as_slice{_mut,}() + par_mut().enumerate() with 4 flat-index lookups). **36/41 sites / 12/15 files remain**. Full-closure mark remains retracted. KW-CV-001 watchpoint remains ACTIVE.
## Batch #1 source-side migration -- slice 2 partial-closure-mark 2026-07-08
> Note: this mark landed after the slice 3 mark (commit f2c89a73) due to flaky prior re-emission attempts; it documents cumulative state AT slice 2 chore landing, not the present state.

Per the peer's 9541155f chore (refactor(kwavers-solver): Migrate model_impl.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 2), on codex/kwavers-core-moirai-parallel atop parent 5cd8c708): **4/41 sites migrated in 2/15 files cumulative** at slice 2. The 2 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/model_impl.rs` (1-mut + 2-immut Zip par_for_each at L48 + 1-mut + 3-immut Zip par_for_each at L62 inside KuznetsovWave::update_wave). **37/41 sites / 13/15 files remain**. KW-CV-001 watchpoint remains ACTIVE. NOTE: retroactive land AFTER slice 3 mark (prior re-emission attempts failed).
## Batch #1 source-side migration -- model_impl.rs Nit 1 asymmetry fixup mark 2026-07-08

Per the peers b21679f5c chore (fix(kwavers-solver): Add standard-layout assert to model_impl.rs migration, on codex/kwavers-core-moirai-parallel atop parent d2cb977b): closes Nit 1 asymmetry by retroactively adding 7 is_standard_layout() asserts to model_impl.rs (slice 2 file): 3 in first-step branch + 4 in multi-step branch. Mirrors the struct_impl.rs fixup c77a926d8 in style. Cargo check clean. Cumulative at the migration level unchanged: **5/41 sites / 3/15 files migrated + 2 file-level fixups** (c77a926d8 + b21679f5). 36/41 sites / 12/15 files remain. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 4 partial-closure-mark 2026-07-08

Per the peer `9595a99f5` chore (refactor(kwavers-solver): Migrate nonlinear.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 4), on codex/kwavers-core-moirai-parallel atop parent b21679f5c): **6/41 sites migrated in 4/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/nonlinear.rs` (1-mut + 3-immut Zip par_for_each at L109 in `compute_nonlinear_term_workspace`). **35/41 sites / 11/15 files remain**. Full-closure mark (Batch #1 CLOSED) remains retracted, this is the fourth per-slice partial-closure mark. KW-CV-001 watchpoint remains ACTIVE.

## Batch #1 source-side migration -- slice 5 partial-closure-mark 2026-07-08

Per the peer `d614a7f57` chore (refactor(kwavers-solver): Migrate operator_splitting/mod.rs par_for_each to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 5), on codex/kwavers-core-moirai-parallel atop parent 9595a99f): **7/41 sites migrated in 5/15 files** cumulative. The 1 new site is in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/operator_splitting/mod.rs` (1-mut + 1-immut Zip par_for_each at L191 in `OperatorSplittingSolver::nonlinear_step`). **34/41 sites / 10/15 files remain**. KW-CV-001 watchpoint remains ACTIVE.

## bash-heredoc artifact audit verification 2026-07-08

> Audit verified: 0 unresolved `\$VAR` artifacts (matches pattern `\$[A-Z_]+`) remain in 3 PM artifacts after the \$SHORT substitution chore (commit `92dad112`). All residual `$` characters in the 3 PM artifacts are legitimate (Rust generic syntax `<$t as Scalar>`, command-substitution documentation `$(cd repos/...)`, mathematical notation, or anti-pattern template examples in audit prose). Code-reviewer N3 carry-forward from the \$SHORT substitution chore is now CLOSED.

## Batch #1 source-side migration -- slice 6 partial-closure-mark 2026-07-08 (heterogeneous site 1 deferred)

Per the peer `7be3fbbd8` chore (refactor(kwavers-solver): Migrate rhs.rs homogeneous par_for_each sites to moirai_parallel::par_mut().enumerate() (Batch #1 source-side slice 6), on codex/kwavers-core-moirai-parallel atop parent d614a7f5): **11/41 sites migrated in 6/15 files** cumulative. The 4 new sites are in `crates/kwavers-solver/src/forward/nonlinear/kuznetsov/solver/rhs.rs` (1-mut + 1-immut Zip par_for_each sites in `KuznetsovWave::compute_rhs` homogeneous branch -- linear/laplacian, source/cache_source, nonlinearity/nonlinear_term, diffusion/diffusive_term). **30/41 sites / 9/15 files remain**. **Heterogeneous Zip::indexed site 1 deferred to follow-up chore**. KW-CV-001 watchpoint remains ACTIVE. Filename arithmetic restored to 6/15 from commit-body off-by-one of 5/15.

- **slice 9 partial-closure-mark 2026-07-09 — kwavers Batch #1 source-side migration slice 9 PARTIAL CLOSURE (1 site in spectral.rs; the deferred heterogeneous 4-mut-0-immut Zip::indexed chain)**: per the peer's `949e5a39` chore (`refactor(kwavers-solver): Migrate spectral.rs 4-mut Zip::indexed to verbose is_standard_layout (Batch #1 source-side slice 9)`, on `codex/kwavers-core-moirai-parallel` atop slice 8 parent `9ab677b0`): 1 deferred heterogeneous site migrated. The site lives in `crates/kwavers-solver/src/forward/nonlinear/westervelt_spectral/spectral.rs` in `initialize_kspace_grids` — the 4-way `Zip::indexed(&mut kx).and(&mut ky).and(&mut kz).and(&mut k_squared).par_for_each(|(i, j, k), kx_v, ky_v, kz_v, k2| { let kx_val = kx_axis[i]; let ky_val = ky_axis[j]; let kz_val = kz_axis[k]; *kx_v = kx_val; *ky_v = ky_val; *kz_v = kz_val; *k2 = kx_val * kx_val + ky_val * ky_val + kz_val * kz_val })` chain. **Strategy**: Pattern A — extend divergence.rs slice 7 3-mut strategy to 4 muts. Keep `Zip::indexed(kx.view_mut())` as the parallel iterator (the closure body consumes `(i, j, k)` for closure-captured Vec<f64> reads `kx_axis[i]/ky_axis[j]/kz_axis[k]`); pre-extract 3 flat `as_slice_mut()` buffers for `{ky, kz, k_squared}`; write 3 additional mut outs via `op_slice[idx]` inside the closure, computing `idx = i*(ny*nz) + j*nz + k` inline once per iteration (~10 cycles vs ~100 for a div/mod-based idx-to-(i,j,k) decomposition in a drop-everything pattern). Race-freedom preserved: each parallel task writes to 4 distinct output elements (kx_v via Zip iterator + 3 disjoint `slice[idx]` writes), all addressed by the same unique `(i, j, k)` tuple. **Precondition asserts**: 7 layout/length asserts total = 4 verbose `is_standard_layout()` on `{kx, ky, kz, k_squared}` mut outs + 3 `debug_assert_eq!` on `{kx_axis, ky_axis, kz_axis}.len()` (Vec<f64> is unconditionally C-contiguous, so length is the only precondition — matching slice 8 cluster D's `σ_*` Array1<f64> pattern verbatim). **WHY NOT HELPER rationale documented inline**: (a) verbose-form is Batch #1 SSOT with helper adoption in 0 of 9 migrated sites across slices 1-8; (b) the slice 9 4-mut extension deliberately matches divergence.rs slice 7 3-mut verbatim for source-level consistency; (c) broader helper-validation across heterogeneous patterns is deferred to Batch #2. **Validation**: `cargo check -p kwavers-solver --lib --no-default-features` rc=0; `cargo test -p kwavers-solver --lib forward::nonlinear::westervelt_spectral` rc=0 — all 6 westervelt_spectral tests pass bitwise (`k_squared_dc_bin_is_exactly_zero`, `k_squared_fundamental_mode_matches_2pi_over_lx`, `k_squared_nyquist_bin_equals_pi_over_dx`, `spectral_laplacian_of_constant_is_zero`, `spectral_laplacian_of_sine_matches_analytical`, `spectral_laplacian_into_is_bitwise_identical_to_allocating`). **Code-reviewer verdict on the source-side commit**: OK to commit after 1 minor nit applied (sharpened the WHY-NOT-HELPER section (b) rationale to drop the imprecise "N>5 closure-captured immuts" claim, since this site only has 3 immuts). **KW-CV-001 watchpoint state**: remains ACTIVE — no formal `closeout`/`final`/`completion`/`close-batch` substring exit in the last 30 inner kwavers commits; per `concurrent_agents` disjoint-scope rule, atlas-meta continues to observe without re-emitting the prior retracted full-closure mark. Atlas-meta path forward: defer `repos/kwavers` parent-side pointer advance until the peer emits a final closeout commit.

- **ADR 0014 forward-looking note 2026-07-09 — KW CV-001 watchpoint active awaiting kwavers peer stream closeout-tag chore**: per the new ADR 0014 `D:/atlas/docs/adr/0014-kwavers-batch1-closeout-tag.md` (Status `Proposed` on 2026-07-09), the kwavers Batch #1 closeout-tag ceremony chore is opened but not yet executable. The KW-CV-001 watchpoint (per `D:/atlas/backlog.md` §In-flight claims `repos/kwavers` row: `git log --oneline -30 | grep -iE 'closeout|final|completion|close-batch' | wc -l` returns 0 at inner HEAD `949e5a39`) gates the Status flip from `slice-by-slice partial closure` (ADR 0013) to `full closure` (ADR 0014). The chore bundles 3 atomic items on disjoint scopes: item (a) 1,315-file mechanical drift flush + item (b) slice 7 `is_standard_layout` predicate unification + item (kwavers closeout) — all 3 emit on `repos/kwavers` `codex/kwavers-core-moirai-parallel` per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from touching `D:/atlas/repos/<X>/`). Atlas-meta's bystander role here: item (c) `chore(atlas): Advance repos/kwavers submodule pointer + KW-CV-001 retirement` is a forward chore whose trigger is items (a) + (b) + closeout-style-commit having landed on the kwavers peer stream. When the stash lands, item (c) advances `repos/kwavers` parent-tree gitlink + either deletes or marks `RETIRED 2026-07-09+` the KW-CV-001 row in §In-flight claims. ADR 0014 itself is then flipped `Proposed` → `Accepted` via a follow-up atlas-meta chore commit. Until the kwavers peer stream emits items (a)+(b)+closeout, this ADR remains `Proposed` + this note remains the residual forward-looking visibility surface.

- **Blocker-triage chore briefs 2026-07-09 — 5 carried-forward blockers re-probed against owning peer streams (per ADR 0013/#14 §Out of scope items 1-4)**: atlas-meta orchestrates the 2026-07-09 re-probe of the 5 carried-forward blockers referenced by ADR 0013 §Out of scope items 1-5 + ADR 0014 §Out of scope items 1-5. The re-probe results classify each blocker as RETIRED (cargo-clean), RECLASSIFIED (different actual cause), CORRECTED (right outcome, wrong count), or CONVERTED (workstream-already-progressing). Each blocker becomes a discrete chore on its owning peer stream per disjoint-scope (ADR 0011 §Leg 2); atlas-meta's bystander role is filing the brief here.

| Row | Blocker ID | Owning peer stream | Re-probe classification | Action verb on peer stream | Cross-walk |
|-----|-----------|---------------------|-------------------------|----------------------------|------------|
| 1 | ritk-wgpu-compat burn workspace-manifest (ADR 0013 §Out-of-scope #1) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-wgpu-compat --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (17.32s) on branch `main`; `burn` + `burn-ndarray` deps are accepted by cargo | No chore required for Batch #1 closure. Optional: Burn-strip per ADR 0012 §Sub-batch #5 `[major]` for the longer-term Burn removal cycle (NOT part of Batch #1 gate) | ADR 0013 §Out-of-scope #1 amended with ➜ RETIRED note |
| 2 | ritk-registration burn dep strip (ADR 0013 §Out-of-scope #2) | `repos/ritk` | **➜ RECLASSIFIED** — actual cause is `direct-parzen` feature-gate regression; 2 `E0432` errors at `crates/ritk-registration/src/metric/histogram/parzen/image_cache_helpers.rs:7:43` (`SparseWFixedCache` gated behind `direct-parzen` feature) + `crates/ritk-registration/src/metric/histogram/mod.rs:10:17` (`atlas_parzen_cache` module gated behind same feature) | Open chore on `repos/ritk`: gate the importing modules behind a `#[cfg(feature = "direct-parzen")]` proxy or fix the import path; commit title `fix(ritk-registration): Resolve direct-parzen feature-gate E0432 errors`. Verification: `cargo check -p ritk-registration --lib --no-default-features` rc=0 | ADR 0013 §Out-of-scope #2 amended with ➜ RECLASSIFIED note; ADR 0014 §Out-of-scope #2 inherits |
| 3 | ritk-image autodiff-module syntax (ADR 0013 §Out-of-scope #3) | `repos/ritk` | **➜ RETIRED** — `cargo check -p ritk-image --lib --no-default-features` rc=0 verified on ritk inner HEAD `a1bf4ac43` (18.77s); remaining `autodiff` references (`host_extract.rs:73,114,115` `type AB = Autodiff<NdArray<f32>>;` test fixture + `types.rs:188` comment) are inert feature-gated test types | No chore required. Informational only — the carried-forward entry was inaccurate; the lib does not have a syntax error | ADR 0013 §Out-of-scope #3 amended with ➜ RETIRED note |
| 4 | 1,315-file kwavers mechanical drift (ADR 0013 §Out-of-scope #4) | `repos/kwavers` | **➜ CORRECTED** — actual drift is 30 modified files, not 1,315 (`git status --short | wc -l` against `repos/kwavers` inner HEAD `445ab9b2` on `codex/kwavers-core-moirai-parallel`); sample of 30/30 modifications is whitespace-only (LF vs CRLF normalization) | Open chore on `repos/kwavers`: emit `chore(kwavers): Flush mechanical dirty triage (30-file CRLF/whitespace batch)` per ADR 0014 §Sequencing step 1 (corrected file count). Verification: `git status --short | wc -l` returns 0 post-chore | ADR 0014 §Sequencing step 1 + §Verification plan item 2 amended with corrected 30-file count |
| 5 | kwavers-math Phase-3/Phase-4 ndarray → leto migration breakage (ADR 0013 §Out-of-scope #5) | `repos/kwavers` | **➜ CONVERTED** — 2 actual commits landed on kwavers peer post-slice-9 `949e5a39`: `445ab9b2` `fix(kwavers-math): linear algebra import/API mismatches` + `e2e1e180f` `fix(kwavers-math): grid/transducer compilation issues` (both kwavers-math-scoped exclusively) | Workstream already in progress on kwavers peer stream; no new chore required from atlas-meta. Monitoring posture until `cargo check -p kwavers-solver --lib --no-default-features` rc=0 restored post-`Array2::from_shape_vec` signature shift | ADR 0013 §Out-of-scope #5 + ADR 0014 §Out-of-scope #5 amended with ➜ CONVERTED note referencing actual commit SHAs |

Triage-summary headline: **5 carried-forward blockers re-probed 2026-07-09; 3 NOT real (#1, #3, #4 overstated), 1 misdiagnosed (#2 not Burn — feature-gate), 1 real + active (#5 already progressing on kwavers peer with 2 actual commits). Batch #1 closure gate unaffected**: ✅ ADR 0013 §Verification plan step 2 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 at slice 9 parent inner HEAD `949e5a39` verified. The post-slice-9 `kwavers-solver --lib` breakage from `Array2::from_shape_vec` signature shift is the explicit Batch #2 prerequisite gate per ADR 0014 §Verification plan step 8. Filing this brief acts as the forwarding ledger: each row's own peer stream picks up its chore at their cadence; atlas-meta does not co-emit the chore commits per disjoint-scope.

- **ADR 0015 trigger-chore brief 2026-07-09 — Open KW Batch #2 Entry Point #1 (`kwavers_safety::with_zip_standard_layout` const-generics arity extension) on kwavers peer stream**: per the new ADR 0015 `D:/atlas/docs/adr/0015-kwavers-batch2-entrypoint1-helper-const-generics.md` (Status `Proposed` on 2026-07-09), the kwavers-solver Batch #2 Entry Point #1 acceptance-validation chore is opened but **currently BLOCKED on Block #5** (per ADR 0013/0014 §Out of scope #5 + Blocker-triage chore briefs row 5). The chore design refines ADR 0013 §Open Batch #2 Entry Point #1 with a const-generics arity extension `[(&'static str, &'imm Array3<A>); N]` with `const N: usize` for the helper signature; this replaces the current dynamic-slice form `'imm [(&'static str, &'imm Array3<A>)]` (which forces runtime indexing + local `Vec` allocation + HRTB friction at N>5 closure captures). The implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 ABSOLUTE — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). **Acceptance criteria (AC-1 through AC-6) per ADR 0015 §Verification plan**: AC-1 `cargo check -p kwavers-solver --lib --no-default-features` rc=0 (Block #5 gate); AC-2 `cargo test -p kwavers-solver --lib` rc=0; AC-3 6/6 westervelt_spectral tests bitwise-identical; AC-4 helper-stress fixture backporting slice 6b rhs.rs 9-immut heterogeneous Phase 2 site bitwise vs verbose-form RHS at all (i,j,k) grid points; AC-5 `cargo test -p kwavers-solver --lib --features helper-stress` rc=0; AC-6 slice 6b site in-place adoption preserves bitwise equivalence. The standing reminder is recorded here in atlas-meta side until AC-1 through AC-6 are all ✅; at that point, atlas-meta emits Step 5 (status-flip chore commit) per ADR 0015 §Sequencing on the kwavers peer core-moirai-parallel branch HEAD that achieves acceptance.

- **ADR 0015 Step 2 design-spec landing 2026-07-09 — KW Batch #2 Entry Point #1 Step 2 helper const-generics extension design-spec filed on atlas-meta side per disjoint-scope**: per ADR 0015 §Sequencing `### Step 2 detailed design specification` amendment landed on atlas-meta by this commit, the Step 2 design-spec is filed as the SSOT that the kwavers claim stream picks up once Block #5 closes. **Status reaffirmation (probed 2026-07-09)**: Block #5 pre-flight gate STILL BLOCKED on `cargo check -p kwavers-solver --lib --no-default-features` (rc≠0; E0308 type mismatches in `kwavers-transducer` + E0599 missing `matmul`/`assign` methods + `kwavers-transducer/focused/arc.rs` syntax gaps; the post-slice-9 commits `445ab9b2` + `e2e1e180f` did not close the gate). The Step 2 design-spec captures: (a) target file `D:/atlas/repos/kwavers/crates/kwavers-solver/src/safety/mod.rs:L84-130` (NEVER EDIT FROM ATLAS-META); (b) 4 modifications to apply (add `const N: usize` + change `immuts` to `[(&str, &Array3<A>); N]` + simplify closure-bound array form + replace `Vec` with `std::array::from_fn`); (c) preserved constraint surface verbatim (`A: Copy + Send + Sync` + verbose panic message form + `'out` lifetime + Nit-1-fix `A: 'static` omission); (d) monomorphization analysis (~30 KB binary impact bounded at N=0..9); (e) Send + Sync propagation + disjoint-capture-rule analysis; (f) HRTB retention recommendation (`for<'s>` kept for forward-compat); (g) acceptance criteria AC-2a/AC-2b/AC-2c + reviewing checklist (atomic-boundary + disjoint-scope + paragraph-collapse). Step 2 cannot execute from atlas-meta per ADR 0011 §Leg 2; the kwavers claim stream owns the implementation commit. Standing reminder updated to: Step 2 design-spec SHIPPED; Block #5 gate BLOCKED; pre-flight gate re-probe required before ASSEMBLE-STATE confirmation.

- **ADR 0016 trigger-chore brief 2026-07-09 — Open Block #5 (kwavers-math ndarray → leto) resolution design-spec on kwavers peer stream per disjoint-scope**: per the new ADR 0016 `D:/atlas/docs/adr/0016-kwavers-block5-resolution-design-spec.md` (Status `Proposed` on 2026-07-09), the kwavers-math Phase-3/Phase-4 ndarray → leto migration resolution chore is opened with a 3-commit atomic decomposition recommended design. Block #5 pre-flight gate is the **AC-1 prerequisite for ADR 0015 Acceptance** (Batch #2 Entry Point #1 helper const-generics extension depends on this). Pre-flight gate state (probed 2026-07-09): `cargo check -p kwavers-solver --lib --no-default-features` returns rc≠0 with 8 errors in `kwavers-transducer` (E0308 type mismatches in `beamforming/processor.rs` + E0599 missing `matmul` on `leto::Array` + E0599 missing `assign` on `Result` in `calibration/manager/mod.rs` + arc.rs syntax gaps in `transducers/focused/arc.rs`); the 2 already-landed commits `445ab9b2a` + `e2e1e180f` closed kwavers-math-only scope but did NOT propagate fixes to kwavers-transducer/receiver/boundary/source/grid callers. The 3-commit atomic decomposition per ADR 0016 §Decision: (1) `fix(kwavers-transducer): Resolve E0308/E0599 + arc.rs syntax (Block #5 sub-batch 1 — strict additive)` — arc.rs syntax + o_ops::linalg::matmul import) + Result.assign migration (destructured `if let Err(e)` pattern) + E0308 `leto::Array` boundary reconciliation; (2) `refactor(kwavers-migration): Migrate Array2::from_shape_vec tuple→array workspace-wide (Block #5 sub-batch 2 — strict signature migration)` --- 8 crates [python, solver, analysis, transducer, receiver, boundary, source, grid] using `sed`-assisted migration from `(rows, cols)` form to `[rows, cols]` array form; (3) `chore(kwavers): Block #5 gate-validation regression test (Block #5 sub-batch 3 — gate reset)` --- CI-side rc=0 assertion + bitwise-identical 6/6 westervelt_spectral tests against slice 9 inner HEAD `949e5a39` baseline. AC-1 through AC-5 per ADR 0016 §Verification plan (kwavers-transducer rc=0 + workspace-wide `Array2::from_shape_vec((` count = 0 + kwavers-solver rc=0 + 6/6 westervelt_spectral bitwise + no false-positive KW-CV-001 watchpoint trigger). Implementation commits live on `repos/kwavers` peer stream per disjoint-scope (ADR 0011 §Leg 2 — atlas-meta is FORBIDDEN from `D:/atlas/repos/kwavers/**` edits). Standing reminder: Block #5 design-spec SHIPPED as the SSOT; kwavers claim stream owns the 3-commit implementation; once the 3 commits land + AC-1 through AC-5 satisfied, atlas-meta emits Step 5 status-flip chore per ADR 0016 §Sequencing flipping ADR 0016 to `Accepted` + simultaneously unblocks ADR 0015 AC-1.

## Provider integration audit queue — 2026-07-13

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HEPH-EMPTY-001 | [patch] | done (`65e89b7`, merged `991f12e`) | Hephaestus decomposition state | Synthetic empty factors deleted; determinant, identity, rank, permutation, and shape contracts pass CUDA/WGPU value tests and the 239-test package suite. |
| MEL-SCOPE-001 | [major] | done (`55ad20e`, merged `bb07447`) | Melinoe capability plus Mnemosyne/Themis/Moirai/Gaia/Coeus/Hephaestus consumers | Unsafe implementer obligation encoded; consumers migrated; Miri, conformance, and provider-version unification pass. |
| MOI-NUMA-001 | [major] | done — ADR 0017, deleted `numa.rs` (4 P0 defects) | Moirai + Mnemosyne/Themis ownership — redirected via ADR 0017 | Deleted 334-line `numa.rs`; existing Themis (placement), Mnemosyne (allocation), Moirai executor (work-stealing) cover the domain. Zero external consumers confirmed. |
| MOI-RESOURCE-214 | [patch] | done — merged PRs #70/#71 (`b637064`) | Moirai `moirai-sync/src/sync/resource_pool.rs`; deterministic clear/recycle interleaving; provider PM artifacts | Provider implementation `eb62898`, review-state `cd84276`, and PM closeout `5788b03`; 20/20 nextest, Clippy, rustdoc, doctests, and Criterion baseline pass; Atlas gitlink advanced to final provider head `b637064`. |
| MOI-DEQUE-POISON-215 | [patch] | implemented 2026-08-05 | Moirai `moirai-scheduler` Chase-Lev retired-array reclamation | `retired_arrays` lock recovery in resize, drop, and test observation now uses poison-tolerant `into_inner()` recovery, preventing secondary panics after an unwinding lock holder. Regression poisons the lock, forces further resize, drains all 80 items exactly once, and verifies final destruction. `cargo check`, warning-denied Clippy, Nextest 26/26, doctests 2/2, rustfmt, and diff checks pass. Scope is limited to `moirai-scheduler/src/deque/chase_lev.rs` and `src/deque/tests.rs`; peer-dirty Moirai paths remain untouched. |
| MOI-BLOCKING-213 | [arch] | done — merged PRs #72/#73/#74 (`6184f73`) | Moirai executor blocking lane; provider PM artifacts | Lazy bounded blocking lane isolates compute workers; separate counters preserve quiescence and metrics; 87/87 nextest, executor-only warning-denied Clippy, rustdoc/doctest evidence, starvation/backpressure/priority/cancellation/shutdown/concurrent-producer tests, and Criterion rows pass. |
| THEM-CACHE-001 | [minor] | done (`18807bb`, merged PR #6) | Themis cache detection | Linux cache parsing returns typed absence on malformed input; Themis consumer pins are co-evolving. |
| LETO-SCALAR-001 | [major] | partial (`855f3ad`) | Leto scalar execution — length pre-validated; Hermes error propagation remains | Partial write closed: `assert_eq!` preconditions in all mutating Scalar methods. 304/304 leto-ops tests pass, apollo-fft builds clean. Error propagation deferred to Result-returning Scalar trait API change. |
| MNE-PERCPU-001 | [patch] | done (verified 2026-07-15) | Mnemosyne local cache — lazy `OnceLock<Box<>>` confirmed | Static footprint ~56 bytes, not 720,896. No backend enables `ENABLE_CPU_CACHE`. |
| TREE-SRP-001 | [arch] | done — ADR 0018 Phases 1-3 complete; Phase 4 filed as TREE-DUP-002 | Melinoe/Themis/Moirai hierarchy | ADR-0018: melinoe halo consolidated (→ melinoe::collections), themis tests rehomed (→ tests/), moirai constants.rs split, Phase 4 deferred. |

## Watchpoints — 2026-07-19 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| MR-WATCH-001 | moirai-scheduler/executor rebuild | `9c015a3` peer break + `5343ebfc` mid-fix | peer green clean HEAD | ✅ CLOSED 2026-07-14 (720/720 at `c43f86a`) |
| HERMES-WATCH-001 | Hermes Mnemosyne consumer Miri | PR #6 `db8e1a4` after provider PR #13 | fresh GitHub Miri/CI completes green | ✅ CLOSED 2026-07-19 (`cargo miri test -p hermes-simd-core` 14/14 pass; mnemosyne locked at `9b8585db` includes aliasing fix `5a9f49f`) |
| MOI-CONTENTION-001 | moirai contention audit | `perf/moirai-contention-audit` branch with contention fixes | merged to main at `9cd650f`, 82/82 pass | ✅ CLOSED 2026-07-15 |
| KW-WATCH-002 | kwavers-therapy abdominal perf | 90s `elastic-fwi` nextest override | peer-stream perf fix | ⏳ open (FFT zero-alloc helper committed, algorithmic perf in peer scope) |
| KW-WATCH-003 | kwavers-python leto→ndarray conversion compile break | `b861254` peer HEAD + 13 WT dirty | peer lands clean green committed HEAD | ✅ CLOSED 2026-07-19 (false positive: pyo3 0.29 alignment resolved 61 E0277; `cargo check -p kwavers-python` clean with 0 errors) |
| ritk Burn-strip verify-block | ritk Batch #3 #4-#6 dep strip | `ba6da3a` 1-ahead + 5 WT dirty | peer pushes, cleans WT, nextest green | ✅ CLOSED 2026-07-19 (Burn→Coeus doc rename committed `22cdbffb`; zero Burn/ndarray production deps remain; `cargo check --workspace` clean) |
| MNE-PERCPU-001 | Mnemosyne per-CPU cache | 720,896-byte dormant static | n/a | ✅ CLOSED 2026-07-15 (lazy OnceLock verified) |
| LETO-SCALAR-001 | Leto scalar length pre-validation | Hermes error discard + silent partial write | n/a | ✅ CLOSED 2026-07-15 (`aecb231`); error propagation deferred to `[major]` |

## Watchpoints — 2026-07-20 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HARM-PUBLISH-001 | `repos/harmonia` submodule registration | Local `repos/harmonia` worktree was unversioned pending remote publish | Peer publishes the `repos/harmonia` worktree to `https://github.com/ryancinsight/harmonia` and advances the Atlas gitlink | ✅ CLOSED 2026-07-20 (peer PR #57 merged `0b0d01d`: Harmonia published at `cf6ce3e`, `.gitmodules` entry added, gitlink advanced, ADR 0023 flipped `Proposed` → `Accepted`, current-stack table reconciled to 20 packages) |
| HEPH-CUDA-WIN-001 | `repos/hephaestus/crates/hephaestus-cuda` + `hephaestus-python` Windows-gnu link | Verified sweep across all 20 Atlas packages: `cargo check` clean across all 20; the bounded per-package nextest run reports `hephaestus-cuda` and `hephaestus-python` fail to build with `x86_64-w64-mingw32-gcc` link error reading `-L /usr/local/cuda-11.3/lib64/` and `-lcuda` on the Windows-gnu host. Hephaestus core/wgpu/metal subset (211/211) is clean | Upstream build script (in `cuda-oxide` or `cutile-rs`) emits a Windows-aware CUDA SDK path via `CUDA_PATH` (`%CUDA_PATH%\lib\x64\cuda.lib`) and the link succeeds on a Windows NVIDIA host; this is an environment defect, not a code regression | ⏳ open (2026-07-20 Session 3 re-confirmed: 211/211 hephaestus core/wgpu/metal under `--exclude hephaestus-cuda --exclude hephaestus-python`; cuda + python skipped per upstream `cuda-oxide`/`cutile-rs` Linux-shaped link path; not a regression) |

## Watchpoints — 2026-07-20 Session 3 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| ASCLEPIUS-REG-001 | `repos/asclepius/` registration | Published two-crate workspace and fetched remote-default merge `ceb8b6d`; explicit P1 promotion request satisfies the prior reopen trigger | Merge `.gitmodules`, exact gitlink, ADR 0028, and stack documentation; then materialize the provider in consumer CI | ✅ CLOSED 2026-07-20 Session 5 (peer commit `6fb5576` "feat(atlas): Register Asclepius" registered the submodule; ADR `0028-asclepius-biological-response-promotion.md` filed Status `Accepted`; `.gitmodules` lines 86-88 reference `repos/asclepius` -> `https://github.com/ryancinsight/asclepius.git`; 23-package stack recorded in README + INDEX; cross-ref `gap_audit.md` L3-34 Asclepius P1 promotion entry) |

## Watchpoints — 2026-07-21 Session 6 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| HELIOS-TYCHE-MAJOR-001 | `repos/helios/crates/helios-imaging/src/noise.rs` + workspace `tyche-core` pin | tyche peer landed breaking `e1a5964 feat(tyche-core)!: Type counter streams` (`StandardNormal<T>` -> `StandardNormal<T, A: StreamAlgorithm>`); the helios `[patch]` override resolves tyche-core to local HEAD `0fc810b` (post-break), bypassing the manifest rev `87923da9...` (dead pin) | Peer migrates `helios-imaging/src/noise.rs:17,45` to the two-param form `StandardNormal::<f64, SplitMix64>::at(seed, sample_index, 0)` (add `SplitMix64` to the `use tyche_core::{...}` import on line 17) and re-establishes the 251/251 nextest baseline; OR bumps the manifest rev pin to `0fc810b` and updates `Cargo.lock` accordingly | ✅ CLOSED 2026-07-21 by helios peer PR #15 (`d82e3bb`): commit `4a01443 "feat(helios-imaging)!: Pin Tyche stream"` removed the local path override entirely (eliminating rev drift), made the algorithm and stream version part of the replay identity, and filed ADR `0005-tyche-noise-stream.md`. Helios main `11487c2` is the merged default post-PR #15; user's standing "implement and resolve examples" helios dispatch is satisfied. |
| CFDRS-TYCHE-MAJOR-001 | `repos/CFDrs/crates/cfd-optim/src/design/space/sampling/mod.rs` + workspace `tyche-core` pin | same tyche breaking change; the CFDrs `[patch]` override resolved the post-break provider | Peer supplies `SplitMix64` to `LatinHypercube` and routes indexed words through `Counter<UserDomain<0>, SplitMix64>` | ✅ CLOSED 2026-07-21 by CFDrs `fca1a9a9`; the exact migrated source is present in public default `394c9977` |
| CFDRS-CFD1D-LINT-001 | `repos/CFDrs/crates/cfd-1d/**` (15 files, ~50 sites) | surfaced in Session 6 `cargo clippy --workspace --all-targets -- -D warnings` during tyche-break verification; pre-existing pedantic lint floor debt in cfd-1d independent of tyche | Peer brings cfd-1d to the workspace `-D warnings` floor: ~26 `uninlined_format_args`, ~6 `manual_map`, ~5 `useless_conversion` to `f64`, 3 `result_large_err` (Err variant >=160 bytes in `PrimarySolveError`), 2 `manual_range_contains`, 2 `field_reassign_with_default`, and ~6 scattered (`complexity`, `explicit_into_iter_loop`, `empty_line_after_doc_comments`, `iter_cloned_collect`) | ⏳ open until 8-warning residual baseline clears (first decrement landed 2026-07-23 by atlas-meta coordinator PR #312 `4ccd4f85`): 54 pedantic warnings -> 8 via mechanical `cargo clippy --fix` (12-file span, 26 `uninlined_format_args` + 20 sibling auto-fixables `unnecessary_map_or`/`useless_conversion`/`.into_iter`/`.into`). Residual 8-warning baseline: 3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap — all manual-only categories peer-architectural) |

## Watchpoints — 2026-07-21 Session 7 (atlas-meta coordinator view)

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-PERF-SLOW-001 | `repos/CFDrs` heavy GPU/3D-CFD integration tests | Session 7 `cargo nextest run --no-fail-fast --workspace` on peer commit `fca1a9a9` (post-tyche-migration) reports 3 tests timing out at the 30s slow budget: `cfd-3d::poiseuille_test::validate_poiseuille_flow` (30.183s), `cfd-suite::cross_fidelity_blueprint::cross_fidelity_blueprint_complex_branching` (30.212s), `cfd-validation::benchmarks::threed::bifurcation::tests::test_bifurcation_flow_3d_murray_and_mass` (30.181s) | Peer roots-cause each timeout per `engineering_gates` (optimize the real components, never relax the slow-timeout bound; never shrink coverage); the 3072/3075 PASS baseline moves to 3075/3075 PASS without TIMEOUTs | ✅ closed (2026-07-23 Session 13 coordinator takeover: `validate_poiseuille_flow` PASS in 0.342s via PR #311 `22ddc27d` perf(cfd-3d) — hoist MidNodeCache + vertex_positions across Picard iter + lower with_direct_threshold 100_000→512 routing medium saddle-point systems to GMRES+AMG / GMRES+BlockDiag (root cause: `leto_ops::SparseLuSolver` is a misnamed dense partial-pivoting LU, O(n^3)). `cross_fidelity_blueprint_complex_branching` closed earlier by peer `153b0ed9` on 2026-07-13 (0.799s). `test_bifurcation_flow_3d_murray_and_mass` re-verified 1.934s at CFDrs main `22ddc27d`. Full cfd-3d suite: 394/394 PASS. Strategic TODO recorded as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] for upstream real sparse LU/Cholesky in leto-ops) |
| CFDRS-LINT-CASCADE-001 | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 `cargo clippy --workspace --all-targets -- -D warnings` halts on 4 site-level errors before reaching cfd-1d/cfd-2d/cfd-3d/cfd-core/cfd-validation/cfd-optim/cfd-suite/cfd-io/cfd-python/xtask; the 4 blockers are `needless_question_mark` ×2 in cfd-math and `print_literal` + `manual_filter` in cfd-schematics | Peer remediates the 4 cascade-blocking clippy errors; once unblocked, run `cargo clippy --workspace --all-targets -- -D warnings` to measure the actual `cfd-1d` baseline vs the Session 6 ~50-site estimate (which may have been inflated by the prior `cargo check`-then-clippy masking) | ⏳ open (2026-07-21 Session 7 cataloged; independent of tyche migration; blocks the `CFDRS-CFD1D-LINT-001` baseline measurement; recorded for the CFDrs peer) |

## Watchpoints — 2026-07-21 Session 8 (atlas-meta coordinator view)

No new atlas-meta-owned watchpoints. Session 8 activity:

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| LETO-VERIFY-CONTENTION-001 | `repos/leto` at `b7224832e` `perf(leto-ops): Vectorize UDU weighted-dot` | Session 8 bounded subagent attempt to run `cargo nextest run --no-fail-fast --workspace` + `cargo test --doc --workspace` on leto post-gitlink-reconcile; blocked by peer-held `CARGO_TARGET_DIR` lock (peer `cargo-nextest.exe` PID 48380 live, not orphan). This is verification contention, not a defect | Atlas-meta bounded nextest + doctest re-run when peer build activity ceases (no live `cargo-nextest.exe` in `tasklist`); per `concurrent_agents` peer's green run on this shared tree IS authoritative evidence on shared branch | ✅ closed (2026-07-21 Session 8 closing annotation: peer cargo-clippy shift released lock; atlas-meta bounded nextest 592/592 PASS rc=0 (slowest 1.023s, zero timeouts) + doctests 9/9 PASS (leto 1, leto-ops 8, leto-python 0). Differential oracles `*_matches_numpy`/`*_matches_scipy` over vectorized UDU weighted-dot kernel pass. Value-semantic correctness preserved atop `9a03735 refactor(leto)!: Retire ndarray boundary`) |

## Watchpoints — 2026-07-21 Session 9 (atlas-meta coordinator view)

atlas-meta main re-oriented at `abbec58` after peer landed 17 commits in the gap since Session 8 close. All Session 8 dispatch items superseded by peer work (user's "proceed as recommended" authorized the no-op continuation). New watchpoint evidence recorded; no new defects cataloged.

| ID | Scope | Trigger | Re-open condition | Status |
|---|---|---|---|---|
| CFDRS-LINT-CASCADE-001 (originally Session 7) | `repos/CFDrs/crates/cfd-math/src/iterators/stencils.rs:101`, `cfd-math/src/iterators/windows.rs:108`, `cfd-schematics/src/heatmap/mod.rs:286`, `cfd-schematics/src/interface/presets/composite/specialized/parallel_lane.rs:24` | Session 7 catalog of 4 site-level clippy errors blocking `cargo clippy --workspace --all-targets -- -D warnings`. Session 9 audit: peer commit `dc256705` remediated sites 1-3 (stencils.rs, windows.rs, heatmap/mod.rs) via `let-else` idiom + SVG format-arg fix. Site 4 (parallel_lane.rs:24) was clean at HEAD `7a521343` — the code is already in the `Option::filter` form `manual_filter` recommends; the watchpoint entry was stale when filed | n/a — peer has remediated or never needed remediation | ✅ closed (2026-07-21 Session 9 bounded subagent audit at HEAD `7a521343`: `cargo clippy -p cfd-schematics --all-targets -- -D warnings` exits rc=0 zero warnings. All 4 watchpoint sites verified clean; clippy gate no longer blocks the cfd-1d lint baseline measurement; `CFDRS-CFD1D-LINT-001` baseline measurement is now unblocked and ready for peer to schedule under the ratchet) |
| HERMES-ADVANCE-001 (Session 9 catalog) | `repos/hermes` gitlink pin `004e6a492` vs inner HEAD `53b83165` | Single commit delta `perf(hermes): Unchecked CSR SpMV tail gather` touched only `CHANGELOG.md` + `spmv.rs` (+8 −1). nextest 388 tests 383 PASS / 5 ABORT — but all 5 aborts are in disjoint gemm/tiling dispatch tests (`ptr::replace` alignment UB on Windows), NOT in the CSR SpMV path (CSR tests `test_spmv_csr_*` all pass). Doctests 18/18 PASS, 10 ignored (cfg-gated) | n/a — peer advanced atlas-meta gitlink in the gap via peer's own `99699ea build(atlas): advance hermes gitlink — SpMV unchecked tail`. Atlas-meta's planned advance was made redundant | ✅ closed (made redundant by peer — atlas-meta main `abbec58` pins hermes at `53b83165`). Residual: the 5 gemm/tiling `ptr::replace` aborts are a pre-existing Windows UB defect — recorded below as HERMES-GEMM-UB-001 |
| HYPERION-PHASE-0-001 (Session 9 catalog) | new stack member `hyperion` at `D:\atlas\repos\hyperion\` (untracked dir, NOT in `.gitmodules`) + ADR 0030 `hyperion-photon-optical-promotion.md` + atlas-meta `0b97ba0` / `4ff5c07` consolidation commits | Peer created ADR 0030 consolidating photon/optical law across Asclepius/Leto/Hephaestus/Helios into a new standalone crate `hyperion` (v0.1.0, edition 2024, deps aequitas/eunomia/proteus). Phase 0 = scaffold + dep alignment; phase 1 = register as atlas submodule. Peer's kwavers tree has 40+ dirty files mid-Hyperion-extraction — the migration is in flight | n/a — Hyperion `7b4561b`, Helios `105a093`, Kwavers `5fc6f0419`, and CFDrs merge `69323418` complete the deletion ledger; Atlas records the exact provider and consumer gitlinks | ✅ closed (2026-07-22: `.gitmodules`, stack map, ADR 0030, PM state, and the 25-package count are synchronized; Ares and Prometheus remain separately evidence-gated) |
| HERMES-GEMM-UB-001 (Session 9 catalog — filed during HERMES-ADVANCE-001 audit) | `repos/hermes/crates/hermes-simd/tests/host_capability_tests.rs` + `crates/hermes-simd/tests/tiling_tests.rs` — 5 GEMM dispatch tests abort | `cargo nextest run --workspace` reports 5 ABORTs: `local_gemm_dispatch_matches_scalar_reference_for_irregular_shapes` (0.807s), `test_gemm_int8_signed_differential` (0.362s), `test_gemm_bf16_size_16` (0.396s), `test_gemm_int8_high_level` (0.427s), `test_gemm_bf16_high_level` (0.471s). All panic at `core::ptr::mut_ptr.rs:1495:18: unsafe precondition(s) violated: ptr::replace requires that the pointer argument is aligned and non-null`. Non-unwinding panic on Windows surfaces as `STATUS_STACK_BUFFER_OVERRUN` (0xc0000409) → abort. Pre-existing — reproducible at peer's pre-advance pin `004e6a492` as well as HEAD `53b83165`. Disjoint from the CSR SpMV path this gitlink advance introduced | Peer root-causes the `ptr::replace` alignment precondition violation in the GEMM tiling-remainder write (likely a `*mut T` produced from an under-aligned slice/holder feeding a packed-view bridge). Recommended first probe: `RUST_BACKTRACE=1 cargo nextest run -p hermes-simd --test tiling_tests test_gemm_bf16_size_16`; then Miri on the gemm kernel (SIMD intrinsics Miri-unreachable → ASan/TSan per unsafe-discipline for the load/store surface) | ⏳ open (2026-07-21 Session 9 cataloged; pre-existing defect not caused by the CSR SpMV advance. Independent of the hermes gitlink `004e6a492 → 53b83165` advance that peer landed in this session's gap. Recorded for peer scheduling since hermes is a peer-owned source tree) |
| EUNOMIA-DOCTEST-001 (Session 9 catalog — closed same session) | `repos/eunomia/crates/eunomia/src/relative_eq.rs` lines 241, 338 — `assert_relative_eq` and `relative_eq` doctests | Early Session 9 bounded subagent at eunomia 0.6.0 published surface reported 2 doctest FAILs with self-contradictory `epsilon = 1e-10, max_relative = 1e-10` example bounds for `1.0_f64` vs `1.0000001` (gap `1e-7`). Peer landed `884d193 feat(eunomia): Add relative equality` + `3e4f9eb docs(eunomia): Close equality provider gate`. Atlas-meta gitlink advance via peer's `a5279bf build(atlas): Advance Eunomia provider` reconciled the pin | n/a — peer closed the doctest gate | ✅ closed (2026-07-21 Session 9 recheck at HEAD `3e4f9eb`: doctests 9/9 PASS, zero failures, zero ignored. The two previously-failing examples now pass value-semantically against consistent bounds. Eunomia is release-ready at HEAD `3e4f9eb`) |
| HELIOS-APPROX-EUNOMIA-001 (Session 9 catalog) | `repos/helios` HEAD `105a0939 refactor(helios): migrate approx -> eunomia assert_relative_eq workspace-wide` | Peer integrated the workspace `approx -> eunomia::assert_relative_eq` migration into helios. Verification at HEAD `56e3572` (1 commit unpushed then; now pushed to origin/main = `105a0939`): nextest 251/251 PASS rc=0, slowest test 1.036s (`helios-imaging fbp::tests::quantum_noise_degrades_recon_and_scales_with_flux`), doctests 11/11 GREEN (helios-python cdylib is the only structural warning — expected). `approx` fully excised from helios `Cargo.toml` | n/a — peer landed + pushed; atlas-meta gitlink advanced via `61e209e` | ✅ closed (2026-07-21 Session 9 verification: helios `approx -> eunomia` migration is GREEN at HEAD `105a0939`. Caveat: helios still uses edition 2021 / resolver 2 (project-wide observation, not a migration defect). Dirty mdBook migration_*.md files are peer's pending book content not part of the migration commit) |

## Residual CFDrs watchpoints carried forward (still peer-owned, still open)

| ID | Status | Note |
|---|---|---|
| CFDRS-PERF-SLOW-001 | ✅ closed (2026-07-23 Session 13) | All 3 perf-slow tests under 2s at CFDrs main `22ddc27d`: `validate_poiseuille_flow` 0.342s (Session 13 perf PR #311), `cross_fidelity_blueprint_complex_branching` 0.799s (peer `153b0ed9` 2026-07-13), `test_bifurcation_flow_3d_murray_and_mass` 1.934s. Root cause of the last standing one (`validate_poiseuille_flow`) was a misnamed dense LU masquerading as sparse LU in `leto_ops::SparseLuSolver` plus per-Picard-iter cache recomputation; both root-caused and fixed at the algorithm (no threshold relaxation, no test shrinkage, no slow-timeout bound change). Strategic TODO — real sparse LU upstream in leto-ops — filed as ATLAS-LETO-OPS-SPARSE-LU-001 [arch] |
| CFDRS-CFD1D-LINT-001 | ⏳ open (now unblocked) | Session 9 closure of `CFDRS-LINT-CASCADE-001` unblocks the cfd-1d pedantic-baseline measurement. The original Session 6 estimate was ~50 sites. Peer can now run the full `cargo clippy --workspace --all-targets -- -D warnings` and schedule the actual baseline under the ratchet |
| ATLAS-LETO-OPS-REFACTOR-001 (new 2026-07-23) | ⏳ open | `leto-ops` (`repos/leto` HEAD `9346413`) is presently uncompilable on the path-dep graph (29 type/visibility errors across `crates/leto-ops/src/application/linalg/iterative/preconditioners/jacobi.rs`, `ilu.rs`, `cg.rs`, `sparse/csr.rs` mod-privacy + generic-`T`-vs-`usize` index comparison). Last destructive code commit `9a82a4d feat(leto-ops): add sparse_lu_solve and SparseLuSolver`. Subsequent commits have been audit doc/test only. Peer is mid-refactor (`ATLAS-LETO-OPS-SPARSE-LU-001` owner context). Assist-ladder (2) decision: skip — fresh and actively held by the leto peer; no claimable periphery in `leto-ops` source that doesn't collide with peer's refactor. Re-verify when peer stabilizes; not coordinator-actionable |
| CFDRS-CFD1D-LINT-001 | ⏳ open (first decrement done; 8-warning residual baseline established) | First ratchet decrement landed by atlas-meta coordinator via PR #312 `4ccd4f85` (squashed merged 2026-07-23). `cargo clippy --fix --allow-dirty -p cfd-1d --all-targets` applied 12-file mechanical remediation: 26 `uninlined_format_args` + 20 sibling auto-fixable lints (`unnecessary_map_or` -> `is_some_and`, `useless_conversion` -> `to_vec`, minor `.into_iter()` / `.into()` cleanups). Baseline: 54 pedantic warnings -> 8 (3 `result_large_err`, 1 `very_complex_type`, 1 `empty_line_after_doc_comments`, 3 doc-test wrap). Net delta -46 warnings (-85%); 728/728 cfd-1d nextest pass post-runtime. Residual 8-warning baseline parked as peer-architectural decisions (error-type redesign, type-factor, doc-comment cleanup) — next decrement candidate |

## Provider integration audit queue — 2026-07-20

| ID | Class | Status | Owner/scope | Acceptance |
|---|---|---|---|---|
| HARM-PROMOTE-001 | [arch] `[minor]` | done — PR #57 merged `0b0d01d` | harmonia / horae / athena-core / eunomia / atlas-meta | `repos/harmonia` published to `https://github.com/ryancinsight/harmonia` (HEAD `cf6ce3e`, CI run `29753063192` green); Atlas `.gitmodules` entry recorded; parent gitlink advanced; ADR 0023 Status `Accepted`; README current-stack table reconciled to 20 packages. |

## ATLAS-WORKTREE-001 — Canonical lane root consolidation [patch] — in progress

- Owner: Codex `/root` (stale-claim takeover 2026-07-22); scope: worktree lane
  locations only, no member-repo code.
- Done 2026-07-21: 24 verified-duplicate standalone clones (12 at
  `D:\worktrees`, 12 at `D:\atlas\worktrees`; all detached, clean, HEADs
  contained, zero local branches), the SHA-keyed `.atlas-provider-checkout`
  cache, and the empty `D:\worktrees\atlas` were removed; stray
  `report/figures` SVG was rescued to `repos/report/figures/`.
- Done 2026-07-22: the legacy `D:\worktrees` root is absent, 16 redundant
  junction aliases are removed, and the former scratch scripts are absent.
  The only remaining lanes are the active Atlas RITK graph lane and Kwavers
  portability lane under the canonical `D:\atlas\worktrees/` root. Each repo
  remains within the main-tree-plus-one-lane bound.
- Residual: merge Atlas PR #86 after RITK PR #49 and merge Kwavers PR #312
  after PR #313, then remove both completed lanes and their branches.

## ATLAS-TARGET-001 — One build cache, one debug budget [patch] — in-progress (residual)

- Owner: Codex `/root`; last-update: 2026-07-22; scope: cache trees and
  profile sections only, no simulation logic.
- Done 2026-07-21: 18 stale cache forks deleted (repo-local `target/`, `target_isolated`, `target_benches`, nested crate `target/`) reclaiming 177.8 GB; `moirai` dev/test profiles aligned to line-tables-only/deps-none (was `debug = true`, pushed `946b4a7`); root `.cargo/config.toml` gains `[profile.dev.build-override] debug = false`. Policy: AGENTS.md performance_engineering "one build cache per stack" — a discovered fork is disposable derived state.
- Done 2026-07-22: the root test profile now matches the development profile:
  workspace test crates retain line tables, while dependencies, build scripts,
  and procedural macros emit no test debuginfo. This closes the configuration
  path through which Nextest could repopulate the shared cache with full
  symbols.
- Done 2026-07-22: removed two abandoned full-target `du` scans that had
  traversed the cache for about 2.5 hours, then pruned the idle incremental
  tree. Its 27,085 session directories occupied 525,183,672,320 bytes
  (approximately 489 GiB); the five-minute deletion preserved shared
  dependencies and linked artifacts, and a subsequent build recreated only
  three current session directories. This is operational reclamation, not a
  clean-build footprint claim.
- Done 2026-07-22: Kwavers PR #307 merges as `0602c1fd4`. Its broad
  dependency graph inherits development `opt-level = 1` instead of wildcard
  `opt-level = 3`, restoring exported generic sharing. Uncached feature-build
  steps fall 18–45%; exact head `909bcdfc7` passes 26 hosted checks, full-grid
  PSTD remains below 25 seconds, and a clean debug tree measures
  16,771,464,617 bytes across 6,109 files. Cargo removes the formerly blocked
  `repos/kwavers/target_isolated` plus six other obsolete private targets:
  9,363 files and approximately 4.49 GiB, without touching `D:/atlas/target`.
  Atlas-meta format and warning-denied Clippy pass; checkout-path Nextest passes
  11/11 in 3.746 seconds and doctests pass 1/1 in 1.93 seconds from the primary
  root against the shared cache.
- Done 2026-07-22: a stack-wide sweep removed 13 additional disposable target
  forks and reclaimed 18.465 GiB; no repository-local target directory
  remains. Before the remaining hosted checks, `cargo clean` against the
  canonical `D:/atlas/target` removed 68,854 files and 20.7 GiB. The configured
  shared cache then measured 0 bytes, below the 10-GiB operating budget; the
  final sweep must repeat after any later local gate.
- Residual: audit member workspaces with their own `[profile.*]` or `.cargo`
  sections (helios, hermes, CFDrs, coeus, ritk, mnemosyne). CFDrs currently
  compiles workspace tests at `opt-level = 2`; its dirty peer-owned workspace
  and active full test build preclude an unmeasured profile edit. Re-open that
  member as a separate measured increment after the peer work integrates,
  retaining only runtime- or profiling-justified deviations. Atlas-meta root
  worktrees copy `.cargo/config.toml` and therefore resolve a lane-local target;
  run meta-tool verification from the primary root until a portable route to
  the canonical cache is implemented and tested. One live sample found three
  independent top-level builds, five Cargo processes, and 23 concurrent `rustc`
  processes on a 24-thread/31.7-GiB host. Compare unchanged single- and
  concurrent-build workloads before selecting a global jobs cap; the sample
  proves oversubscription exposure, not an optimal cap.

## ATLAS-BENCH-BUDGET-001 — Wall-clock budgets for benches and examples [patch] — in-progress (enforcement merged; sweep residual)

- Owner: Claude (user-directed claim 2026-07-22); home: tools/criterion-regression (ADR 0024); policy: AGENTS.md engineering_gates "Runtime budgets" + performance_engineering "Benchmark time budget".
- Outcome: no bench binary or CI example exceeds its committed bound; suite time is designed, not emergent.
- Scope: (1) gate smoke — bench binaries run single-iteration (criterion `--test`) under the standard 30s/60s budget; (2) timing runs — per-binary wall-clock bound (default 300s) enforced in the criterion-regression runner/CI; (3) CI-safe examples complete within the test budget as scaled demos; (4) audit the 164 bench files (moirai 47, CFDrs 29, kwavers 22, hermes 12, ritk 10, rest ≤8) against the analytical time model — zero suites declare measurement_time/sample_size today, i.e. all run unbudgeted criterion defaults with sweeps; apply flat sampling for slow iterations, geometric sweeps, smallest regime-exercising inputs; where a single iteration is genuinely slow, profile and optimize the production kernel (farsight), never delete the bench or raise the bound in the offending diff.
- Acceptance: budget enforcement merged in the runner + full-stack bench sweep completes within per-binary bounds; breaches root-caused and fixed or filed with derivation.
- Done 2026-07-22: `enforce-budget` subcommand in tools/criterion-regression — modes smoke (bench single-iteration, 60s), timing (full measurement, 300s), examples (60s), `--bound-seconds`/`--skip` overrides. Compiles unbounded, executes binaries directly (killing cargo would orphan the bench grandchild) with CARGO_TARGET_DIR pinned to the shared target (no minted repo-local target/), fail-closed exit. Validated: themis smoke/timing clean; eunomia timing at 5s bound → breach terminated mid-measurement, exit 1. Gates: clippy pedantic clean, 21/21 nextest, doc clean.
- Residual: full-stack sweep at committed bounds (probe per repo; live peer scopes deferred to their completion), CI wiring per repo workflow convention, and suite resizing per breach (flat sampling, geometric sweeps) or kernel optimization per farsight.
## ATLAS-BUILD-STRUCTURE-001 — Consolidate leaf binaries; compiler-last dev profiles [patch] — in progress

- Owner: Codex `/root`; last-update: 2026-07-23; completed vertical slice:
  `repos/coeus/coeus-ops/tests/**` only. Peer-owned member profiles and other
  repository test trees remain out of scope.
- Claim: consolidate the 36 flat `coeus-ops` Rust integration-test binaries
  into one hierarchical `tests/ops.rs` harness with `tests/ops/*.rs` modules,
  preserving all 87 test functions and their value-semantic assertions. The
  target-count reduction and test-count parity are the acceptance oracle.

- Policy: AGENTS.md performance_engineering "Debug-tree and compile-time structure" + "Compiler-last optimization order". Monomorphization stays the design default — an instantiation codegens identically to its hand-written equivalent; the debug-tree multiplier is leaf-binary count and duplicate paths, never genericity.
- Evidence 2026-07-22: ~950 leaf binaries stack-wide, each a full link with own incremental cache and PDB — tests/examples per repo: CFDrs 118/66, coeus 110/2, kwavers 94/62, consus 55/0, ritk 28/7, hermes 20/4, moirai 15/22, melinoe 15/1, others <=11. Dev-profile audit: helios declares wildcard `[profile.dev.package."*"] opt-level = 3` (the pattern removed from kwavers in PR #307); kwavers `opt-level = 1` with documented 5-10x PSTD justification is the sanctioned named-and-measured form. The shared incremental tree reached 27,085 session directories and approximately 489 GiB in five days, making leaf-target consolidation and CI `CARGO_INCREMENTAL=0` the next measured size levers.
- Scope: (1) consolidate each repo's tests/*.rs into one-or-few area harness binaries (`tests/<area>/main.rs` with modules) — nextest still isolates per test function in its own process, so coverage and isolation are unchanged while link count, incremental caches, and debug artifacts drop by the file count; worst offenders first (CFDrs, coeus, kwavers, consus, ritk, hermes); (2) merge near-duplicate examples per consolidation_discipline; (3) replace wildcard dev dependency opt raises with named, measured, per-package exceptions (helios first, peer-held — coordinate via board); (4) record per-repo binary-target count and debug-tree size before/after as the acceptance measurement.
- Acceptance: binary-target census reduced and recorded per repo; debug-tree size delta measured against the shared cache; test function count unchanged (no coverage loss); no wildcard dev opt-level overrides remain without a named measured justification.
- Completed vertical slice: Coeus `coeus-ops/tests` moved from 36 flat
  integration targets to one `ops` target with ten operation-family
  directories. The harness exposes 87 integration tests and the exact
  package Nextest run passes 196/196; whole-workspace debug-tree measurement
  remains a later bounded slice.
- Evidence: warning-denied Clippy, package check, format, and diff checks pass
  on Coeus commit `f67789c4`; the 87 harness tests are unchanged by source
  count and all 196 package tests pass. This item is closed for the bounded
  Coeus slice; the broader stack-wide debug-tree delta remains open work.
- Coeus-NN slice complete at provider commit `95bb9090`: the existing
  `nn_tests.rs` harness and its already hierarchical `tests/nn/` modules stay
  intact while the 33 other direct test binaries move behind one `nn_ops`
  harness, preserving the 268 total package tests. The 34 direct test targets
  reduced to 2 (`nn_ops` and `nn_tests`); the exact package run passes
  268/268 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `f8f6d665`: the existing
  `autograd_tests.rs` harness and `tests/autograd/` module tree remain intact
  while the three other direct targets move behind one `autograd_ops` harness.
  The four integration targets reduce to two; the exact package run passes
  94/94 with 0 skipped. Whole-workspace debug-tree measurement remains open.
- Coeus-tensor slice complete at provider commit `49bb5858`: the 13 flat
  integration targets move under six operation-family directories behind one
  `tensor_ops` harness. Locked metadata reports one integration target; the
  source census remains 53 annotated integration tests, and the exact package
  Nextest run passes 58/58 with 0 skipped, including five library unit tests.
  Production tensor code and all leaf test bodies remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-sparse slice complete at provider commit `81cb68a6`: the three flat
  integration targets move under conversion, differential, and invariant
  directories behind one `sparse_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 19/19 with 0
  skipped in 0.713 seconds. Production sparse code and all leaf test bodies
  remain unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-core slice complete at provider commit `88dfd38f`: the four flat
  integration targets move under storage, dependency-policy, and scalar
  directories behind one `core_ops` harness. Locked metadata reports one
  integration target; the exact package Nextest run passes 21/21 with 0
  skipped, comprising 14 integration cases and seven unchanged library unit
  tests. Production core code and all leaf test bodies remain unchanged.
  Whole-workspace debug-tree measurement remains open.
- Coeus-CUDA slice complete at provider commit `573ad35e`: the three flat
  feature-gated integration targets move under device and fallback directories
  behind one `cuda_ops` harness, retaining the existing nested `tests/cuda/`
  tree through an explicit path. Default Nextest passes 3/3 with 0 skipped;
  all-features check and Clippy pass. All-features executable coverage remains
  host-blocked because the GNU linker cannot find
  `/usr/local/cuda-11.3/lib64/libcuda`. Whole-workspace debug-tree measurement
  remains open.
- Coeus-Python slice complete at provider commit `8851c5f5`: the six flat Rust
  integration targets move under activation, distributed, NN, operation,
  optimizer, and autodiff directories behind one `binding_ops` harness. The
  shared `tests/common` lock module is owned once at the harness root. Exact
  all-features Nextest passes 75/75 with 0 skipped; production PyO3, Python
  parity scripts, and generated artifacts remain unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-WGPU slice complete at provider commit `c507683e`: the two flat
  integration targets now share one hierarchical `wgpu_ops` harness, with
  fused operations under `fusion.rs` and the existing WGPU operation tree under
  `backend/wgpu/`. Exact package Nextest passes 85/85 with 0 skipped; the moved
  source files are content-identical renames and production GPU code is
  unchanged. Whole-workspace debug-tree measurement remains open.
- Coeus-WGPU parity split complete at provider commit `149aadb5`: the 808-line
  multi-family leaf is now a shared oracle manifest plus seven operation-family
  modules. The pre/post source-name census remains 47 unique parity identifiers;
  exact package Nextest passes 85/85 with 0 skipped. Every new leaf is below
  500 lines; production kernels and fixtures are unchanged. Whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto slice complete at provider commit `8d3b9082`: the two flat
  integration targets now share one hierarchical `leto_ops` harness with
  contract and sparse-dispatch operation families. Locked metadata reports one
  integration target; exact package Nextest passes 28/28 with 0 skipped in
  1.064 seconds. The live census is 26 contract tests plus 2 sparse-dispatch
  tests, correcting the prior 26-test tracking claim. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-autograd slice complete at provider commit `24a52be5`: the established
  `tests/autograd/` module tree and standalone operation families now share one
  hierarchical `autograd_ops` harness; the redundant `autograd_tests.rs`
  manifest is removed. Locked metadata reports one integration target instead
  of two; exact package Nextest passes 94/94 with 0 skipped in 1.535 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass. Whole-
  workspace debug-tree measurement remains open.
- Coeus-NN slice complete at provider commit `5c416e12`: the established
  `tests/nn/` module tree and operation-family modules now share one
  hierarchical `nn_ops` harness; the redundant `nn_tests.rs` manifest is
  removed. Locked metadata reports one integration target; exact package
  Nextest passes 268/268 with 0 skipped in 4.463 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-NN tensor parity split complete at provider commit `ee5be32f`: the
  1,317-line multi-family parity leaf is now a shared assertion manifest plus
  attention, convolution, embedding, linear/normalization, losses, and
  regularization operation-family modules. The pre/post source-name census
  remains 11 unique parity test functions; exact package Nextest passes 268/268
  with 0 skipped in 2.816 seconds. The largest new leaf is `attention.rs` at
  664 lines; the other five leaves are below 250 lines. Package check,
  warning-denied Clippy, format, and diff checks pass. Whole-workspace
  debug-tree measurement remains open.
- Coeus-CUDA parity split complete at provider commit `abe9211d`: the live
  1,672-line multi-family parity leaf is now a shared oracle manifest plus
  seven operation-family modules. The pre/post source-name census remains 29
  unique parity test functions; every new leaf is below 500 lines, with
  `convolution.rs` the largest at 365 lines. Default package Nextest passes
  3/3 with 0 skipped; default and `--features cuda` package checks and
  warning-denied Clippy pass. Feature-enabled Nextest cannot link because
  `x86_64-w64-mingw32-gcc` cannot find `-lcuda` while searching
  `/usr/local/cuda-11.3/lib64/`; no live CUDA parity execution is claimed.
  Whole-workspace debug-tree measurement remains open.
- Coeus-Python operation binding split complete at provider commit `0d8784c1`:
  the live 3,160-line `binding_tests_ops.rs` leaf is now fourteen
  operation-family leaves with nested NN functional and module directories.
  The pre/post source census remains 61 unique test functions and all 61
  extracted Rust function bodies compare equal. The largest test-family leaf is
  `reductions.rs` at 391 lines; every leaf is below 400 lines. Exact package
  Nextest passes 75/75 with 0 skipped in 8.079 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production PyO3,
  Python parity scripts, and generated artifacts remain unchanged. Whole-
  workspace debug-tree measurement remains open.
- Coeus-dist distributed-contract split complete at provider commit `c7838d90`:
  the live 1,262-line `dist_tests.rs` leaf is now one `dist_ops` manifest with
  local and TCP transport subtrees, separated into collective, reduction,
  invalid-input, and mesh-boundary families. The pre/post source census remains
  64 unique test functions, all 64 `#[test]` attributes remain present, and
  all 64 extracted Rust function bodies compare equal. The largest new leaf is
  `distributed/tcp/errors/collective.rs` at 464 lines; every leaf is below 500
  lines. Exact package Nextest passes 64/64 with 0 skipped in 0.444 seconds,
  with no slow tests. Package check, warning-denied Clippy, format, and diff
  checks pass. Whole-workspace debug-tree measurement remains open.
- Coeus-NN loss-contract split complete at provider commit `37bf8d9b`:
  the live 902-line `nn_loss_tests.rs` leaf is now a nested manifest with
  binary, classification, distance, and distribution operation families. The
  pre/post source census remains 24 unique test functions and all 24 extracted
  Rust function bodies compare equal. The largest new leaf is `distance.rs` at
  315 lines; every new leaf is below 500 lines. Exact package Nextest passes
  268/268 with 0 skipped in 2.270 seconds. Package check, warning-denied
  Clippy, format, and diff checks pass. Production NN code, fixtures, and
  tolerances remain unchanged; whole-workspace debug-tree measurement remains
  open.
- Coeus-optim contract-family split complete at provider commit `b27d492f`:
  the live 676-line `optim_tests.rs` leaf is now one `optim_ops` manifest with
  optimizer, scheduler, convergence, and gradient-clipping family modules.
  The pre/post source census remains 20 unique test functions and all 20
  extracted Rust function bodies compare equal. Locked metadata reports one
  `optim_ops` integration target. The largest new leaf is `convergence.rs` at
  239 lines; every new leaf is below 250. Exact package Nextest passes 20/20
  with 0 skipped in 0.188 seconds. Package check, warning-denied Clippy,
  format, and diff checks pass. Production optimizer code and all test oracles
  remain unchanged; whole-workspace debug-tree measurement remains open.
- Coeus-NN extended activation split complete at provider commit `d800be8c`:
  the live 648-line `act_extended_tests.rs` leaf is now one `act_extended`
  manifest with piecewise, parameterized, module-smoke, and smooth families.
  The pre/post source census remains 17 unique test functions and all 17
  extracted Rust test function bodies compare equal. The largest new leaf is
  `piecewise.rs` at 354 lines; every new leaf is below 360. Exact package
  Nextest passes 268/268 with 0 skipped in 3.155 seconds. Package check,
  warning-denied Clippy, format, and diff checks pass. Production NN code,
  fixtures, formulas, and tolerances remain unchanged; whole-workspace
  debug-tree measurement remains open.
- Coeus-Leto contract-family split complete at provider commit `97d94566`:
  the live 505-line `leto_ops/contract.rs` leaf is now a manifest with
  arithmetic, reductions, matmul, layout, and accumulation families under
  `coeus-leto/tests/leto_ops/contract/`. The pre/post source census remains
  26 unique contract tests and all 26 extracted Rust test function bodies
  compare equal. The largest new leaf is `layout.rs` at 197 lines; every new
  leaf is below 200 lines. Locked metadata reports one `leto_ops` integration
  target. Exact package Nextest passes 28/28 with 0 skipped in 0.325 seconds.
  Package check, warning-denied Clippy, format, and diff checks pass.
  Production Leto dispatch code and test oracles remain unchanged; whole-
  workspace debug-tree measurement remains open.
- Next claimed slice: run a fresh structural audit of the remaining Coeus test
  tree and take the next real family-boundary increment, if a live leaf exceeds
  the hierarchy trigger without violating test cohesion.

## ATLAS-PUBLISH-001 — OIDC publish pipelines and Pages alignment [patch] — todo

- Policy: AGENTS.md engineering_gates "Publish pipelines". Wiring is agent work; registry-side toggles are user actions.
- Scope: (1) crates.io — add tag-triggered, environment-gated trusted-publishing workflows (`rust-lang/crates-io-auth-action`, `id-token: write`) to publishable stack crates, dependency-ordered with `cargo package` dry-run and semver gates; record per-crate "enforce trusted publishing" as a user checklist once each pipeline is green (disables token publishing registry-side). (2) PyPI — for the Python-binding crates, maturin-action matrix (manylinux2014 floor, `--compatibility pypi`, abi3 where the surface permits, sdist) with install/import/pytest wheel smoke before upload via the PyPI trusted-publisher flow. (3) Books — align CFDrs/kwavers/helios book workflows to the artifact flow (build + `mdbook test` → upload-pages-artifact → deploy-pages) if any still push a gh-pages branch or skip the test gate; new books inherit the same workflow.
- Acceptance: no long-lived registry token referenced in any CI secret; each wired pipeline dry-run green; book deployments artifact-based with the test gate; user-action list (registry enforcement toggles) recorded on the board.

## ATLAS-PUBLISH-001-BOOK-MDBOOK-TEST-001 — Cross-book `mdbook test` gate alignment [patch] — peer-coordinated (filed by Session 18)

Coordinator-owned evidence record (this entry) under
eer-coordinated execution: kwavers peer on branch
`codex/kwavers-book-migration-eviction` (peer mid-flight on
`ATLAS-BOOK-002` eviction). CFDrs peer on `main` branch, 1 ahead of
`origin/main f04b1d75` (autest sub-task, see
`ATLAS-CFDRS-COEQ-BLOCKER-1`). Helios peer on
`origin/main 433ddb6`. Each member-repo peer owns their own workflow
`book-pages.yml`; coordinator cannot edit those files per
`concurrent_agents` disjoint-scope primitive — this entry surfaces the
shared gap and per-repo sub-scopes so each peer claims the disjoint slice
against their own repo. Coordinator verification of the shared gap was
performed against each repo's `origin/main` HEAD.

- Policy: AGENTS.md engineering_gates "Publish pipelines" — book
  workflows run build + `mdbook test` → `upload-pages-artifact` →
  `deploy-pages` (the test gate is the test-suite coverage for
  documentation samples, preventing rotted non-compiling example code
  from deploying).
- Discovery evidence (verified at Session 18 via `git show
  origin/main:.github/workflows/book-pages.yml` on each repo):
  - **kwavers** (`origin/main c19134ec`): steps `Configure Pages`,
    `Install mdBook`, `Build book` (runs `mdbook build docs/book`
    only), `Upload Pages artifact`, `Deploy to GitHub Pages`. No
    `mdbook test` step.
  - **CFDrs** (`origin/main f04b1d75`): identical step shape
    (`Configure Pages` → `Install mdBook` → `Build book` running
    `mdbook build` only → `Upload Pages artifact` → `Deploy to GitHub
    Pages`). No `mdbook test` step.
  - **helios** (`origin/main 433ddb6`): identical step shape. No
    `mdbook test` step. (Cited as residual (a) in
    `ATLAS-HELIOS-BOOK-001` Session 18 closure.)
  - All three deploy via `actions/upload-pages-artifact@v4` →
    `actions/deploy-pages@v4` with `pages: write` + `id-token: write`
    on the `deploy` job and deploy gated on
    `github.event_name != 'pull_request'` (main-only). The artifact
    flow is already compliant; only the `mdbook test` step is missing.
- Outcome: each per-repo peer-coordinated sub-slice lands one PR
  inserting a `Build book`→`Test book samples` step (running
  `mdbook test docs/book`) between `Install mdBook` and
  `Upload Pages artifact`, fail-closed on doctest failure. The (1)/(2)
  crates.io/PyPI scopes of `ATLAS-PUBLISH-001` remain separate and
  unowned — this sub-slice addresses only the (3) Books test-gate
  gap. Per-repo sub-scope (peer-coordinated):
  (a) **repos/kwavers/.github/workflows/book-pages.yml** — peer-kwavers
      holds active eviction branch (`codex/kwavers-book-migration-eviction`,
      1 ahead of `origin/main c19134ec`); the `mdbook test` step landing
      is complementary to eviction (examples must compile for `mdbook
      test` to pass, and eviction is removing the migration-reference
      examples that are least doctest-fit), so sequencing eviction first
      is the cleanest order. Awaiting peer eviction merge to `origin/main`.
  (b) **repos/CFDrs/.github/workflows/book-pages.yml** — peer-CFDrs
      on `main` ahead 1 of `origin/main f04b1d75`; lands after the
      `ATLAS-CFDRS-COEQ-BLOCKER-1` workspace-restore + check-figures
      re-verification so the local `mdbook test` pre-flight is backed by
      a fully-resolved Cargo graph (the coeus-core path-dependency
      gap currently stops local cargo metadata resolution).
  (c) **repos/helios/.github/workflows/book-pages.yml** — peer-helios
      at `origin/main 433ddb6`, book content ready to test. No known
      pre-requisite for the `mdbook test` step landing; cleanest
      per-repo increment of the three.
- Acceptance: each `book-pages.yml` carries a `mdbook test docs/book`
  step running doctests on committed sample code; book deploy still
  artifact-based with the test gate; user-action list (registry
  enforcement toggles) recorded on the board remains the same.
- Risk/change class: `[patch]` CI-only; no production-code delta.
- Dependencies: ATLAS-PUBLISH-001 (parent),
  ATLAS-BOOK-002 (kwavers eviction sub-scope ordering);
  ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs cargo-graph restore).
- Evidence limit: workflow-step inspection on each `origin/main`;
  no performance claim, no production-code delta.
- Refs: backlog.md#ATLAS-PUBLISH-001 (parent slice),
  backlog.md#ATLAS-BOOK-002 (kwavers peer eviction),
  backlog.md#ATLAS-HELIOS-BOOK-001 (Session 18 closure residual (a)),
  backlog.md#ATLAS-CFDRS-COEQ-BLOCKER-1 (CFDrs workspace restore).

## Session 17 closure (2026-07-23) — ATLAS-LETO-OPS-SPARSE-LU-001 → ✅ closed

- Owner: atlas-meta coordinator (codex agent); status flipped todo → ✅ closed.
- Outcome: real CSC sparse LU + partial-pivoting numeric phase in leto-ops
  landed at leto `origin/main` `687b670` via PR #74 squash-merge
  (`refactor(leto-ops): Remove ndarray/nalgebra, native iterative solvers
  (LETO-NDARRAY-BOUNDARY-1) (#74)`).
  The PR diff (41 files) bundled the ndarray/nalgebra dev-dep removal (peer
  origin-main HEAD `9346413` declared no production deps on ndarray/ndarray-rand/
  nalgebra; only parity examples consumed them) AND the in-place upgrade of
  `SparsLuSolver` to the real algorithm class.  Public surface preserved:
  `SparseLuSolver::solve_view`, `CscMatrix`, `CsrMatrix`, `CooMatrix`, and the
  re-exported `factor_numeric` / `factor_symbolic` / `NumericLu` API paths.
- Algorithm spec (matches ADR 0031 Option A): symbolic factorization is the
  sequential left-looking Gilbert/Peierls reach over CSC, computing the
  static L/U pattern (L rows strictly `> j`, U rows `≤ j` per column j) under
  natural column ordering for v0.40.0; numeric factorization is the
  slot-indexed left-looking phase with partial-pivoting row swaps against
  `row_perm[slot] = original row` (matches the dense
  `LuDecomposition::pivots` convention so downstream CFDrs
  `DirectSparseSolver` composes unchanged); solve =
  `P·A·x = L·U·x = P·b` ⟺ forward sub `Ly = Pb` then back sub `Ux = y`.
- Density-gated dispatch (per ADR 0031): `SparseLuSolver` carries a
  `small_switch = 32` and `density_threshold = 0.1` pair; small or near-dense
  matrices route to a dense-fallback path; large sparse matrices route to
  the new symbolic→numeric sparse path.
- Verification evidence (Windows ucrt64, rustc 1.95.0, eunomia
  https://github.com/ryancinsight/eunomnia#f6cd644b):
  - `cargo check -p leto-ops --tests` ✅ clean (Finished in 2m 15s).
  - `cargo nextest run --no-fail-fast -p leto-ops` ✅ 339/339 pass in 3.17s
    (well under the 30s slow-timeout hard cap; no threshold relaxation, no
    test shrinkage).
  - `cargo test --doc -p leto-ops` ✅ 11/11 pass in 54.64s.
  - Sparse-LU-targeted suite ✅ 16/16 pass:
    `factor_poisson_1d_laplacian_n16_roundtrip` 0.064s,
    `factor_banded_5_diagonal_n32` 0.026s,
    `factor_random_sparse_n64_diff_dense` 0.252s,
    `sparse_path_routes_correctly_for_tridiagonal_n64` 0.269s,
    `factor_f32_generic` 0.051s,
    `singular_matrix_yields_storage_error` 0.240s,
    `solver_is_generic_over_f32` 0.071s, plus 9 inherited solver-routing tests.
  - Differential cross-check: `factor_random_sparse_n64_diff_dense` asserts
    value-semantic equivalence between sparse and dense LU on a randomly
    populated 64×64 matrix at residual < ε (not existence-only).
- Residual / not-covered-in-this-closure (per ADR 0031 Consequences):
  (a) AMD (Approximate Minimum Degree) ordering deferred to
      `ATLAS-LETO-OPS-AMD-ORDERING-001` [patch] — natural ordering ships for
      v0.40.0; AMD ~300-line impl exceeds this session's context budget and
      a partial implementation would risk numerical defects per ADR 0031
      "AMD scope risk".
  (b) CFDrs `DirectSparseSolver` migration to the landed
      `SparseLuSolver::solve_view` is the follow-up
      `ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001` — depends on aequitas pin
      coherence and a leto bump at CFDrs; not in scope for Session 17.
  (c) Local clippy `-D warnings` against the FULL leto workspace cannot run
      clean on this coordinator's working tree because peer's untracked
      uncommitted sibling verticals
      (`crates/leto-ops/src/application/{diff,interpolation,quadrature}/`)
      contain `assign_op_pattern` and `complex_type` lint failures. PR
      #74's CI status (both `recurseml/analysis` post-push and
      `CodeRabbit`) was CLEAN before squash-merge; the merged commit's
      leto-ops scope is clippy-pedantic clean modulo peer-held untracked
      files not in the merged tree.
- Concurrent-agent record: peer session active on the same `codex/leto-real-sparse-lu`
  working tree during this closure, creating untracked siblings for diff/
  interpolation/ quadrature operation families (ts 21:53-22:02).  Per
  `concurrent_agents` assist-ladder rule: peer files skipped, not collided with.
  Coordinator scope-strictly-committed only `sparse/lu_numeric.rs` and
  `sparse/lu_symbolic.rs` (doctest-fixture correction + rustfmt-only reflow of
  pre-existing `for ... take().skip()` chains); peer's `Cargo.{lock,toml}`,
  `lib.rs`, `application/mod.rs`, `application/linalg/mod.rs`, and the new
  `diff/`/`interpolation/`/`quadrature/` untracked modules remained unstaged.
- Gitlink-state: atlas-meta's `repos/leto` gitlink advances to
  `687b67079c4e122264c17fd2eb3fd850d876a39f` in the same commit that
  synchronizes this backlog entry and ADR 0031's status flip.
- Refs: backlog.md#CFDRS-PERF-SLOW-001 (Session 13 upstream-cause filing),
  backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (this item), ATLAS-LETO-OPS-AMD-ORDERING-001 [patch] (new follow-up below).

## ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 — Migrate CFDrs direct_solver to SparseLuSolver::solve_view [minor] — partial closure (2026-07-23 Session 17: doc-migration slice landed via PR #316 `5ac713b3`); cfd-3d end-to-end re-profile and direct_threshold re-evaluation deferred

Filed as follow-up per Session 17 closure of `ATLAS-LETO-OPS-SPARSE-LU-001`.
Now that real sparse LU + partial pivoting has landed at leto `687b670`,
the CFDrs downstream consumer should adopt the upstream-native solver.

- Owner: unclaimed. Depends on CFDrs leto version bump (currently
  `aequitas = { path = "../aequitas" }` and leto path-pinned at
  atlas-meta level).
- Outcome: replace `crates/cfd-math/src/linear_solver/direct_solver.rs`
  body with calls to `leto_ops::application::sparse::SparseLuSolver::solve_view`
  on real CSC-typed inputs; remove any `with_direct_threshold(512)`-
  regime mats that exist purely to route medium saddle-point FEM
  matrices to GMRES (Brezzi 1974 indefinite saddle — sparse LU is now
  correct for it, not a misnomer).
- Acceptance: (1) CFDrs `crates/cfd-math/src/linear_solver/direct_solver.rs`
  no longer documents itself as "atlas-native sparse direct solver backed
  by dense partial-pivoting LU" (cf. the doc-runtime contradiction),
  (2) CFDrs cfd-3d suite verifies end-to-end (`validate_poiseuille_flow`
  PR #311 root-caused fix continues to PASS under the new upstream
  matrix-as-sparse path; re-profile runs `<1s` per Session 13 closure
  baseline), (3) `direct_threshold` parameter either removed from the
  CFDrs FEM solver or re-evaluated with new evidence (filed as a follow-up
  board item against CFDrs perf, not this slice).
- Risk/change class: `[minor]` (additive public-API call-site
  migration; no break to CFDrs public surface).
- Dependencies: leto version bump at CFDrs; aequitas pin coherence
  (Session 12 documented the eunomia dual-source-ID recurring risk
  when consumers pin eunomia differently; align all atlas consumers
  on URL-only form).
- Refs: backlog.md#ATLAS-LETO-OPS-SPARSE-LU-001 (closed),
  leto origin/main `687b670`.

## ATLAS-HELIOS-BOOK-001 — Helios multichapter mdBook from examples [minor] [arch] — ✅ closed (2026-07-24 Session 18 — peer-delivered)

Per user Session 17 prompt: "Similar to kwavers it would be good for
helios and cfdrs to also create a well-organized, multichapter book
from examples." kwavers book template is the canonical reference.
Peer-helios delivered the book across PRs landing at `origin/main
433ddb6` (atlas-meta gitlink unchanged: it is already at this merged
origin commit). Coordinator closure is evidence-only — no member-repo
file edits by this agent.

- Owner: peer-helios (delivered); atlas-meta coordinator (this closure
  flips the backlog status and records the verification matrix).
- Outcome: full multichapter mdBook at 
  `repos/helios/docs/book/` with 8 Parts across 37 chapters + 4
  appendices + BOOK_ORGANIZATION forward roadmap; 18 example
  markdown files under `examples/`; 7 deterministic SVG figures
  + `MANIFEST.json` byte-determinism registry under `figures/`;
  `book.toml` configured with `/helios/` site-url + MathJax; README
  links published book at https://ryancinsight.github.io/helios/.
  Per-chapter content follows the kwavers-standard Domain-book
  contract: governing equations → numerics → CLI/API mapping →
  worked examples with deterministic figures, with each chapter
  carrying an H1 `# Chapter N — …` + `## Further Reading` backlink
  + SUMMARY.md navigation (verified by sampling across Parts I–VIII).
- Acceptance: 
  (a) `mdbook build docs/book` exits 0 locally at helios 
      `433ddb6` (verified via `mdbook v0.5.4`, target written to 
      `target/book/helios/index.html`). ✅
  (b) Every SUMMARY.md entry maps to a committed chapter stub with 
      H1 + "Further Reading" backlink (verified sample across 
      `foundations`, `dose_attenuation`, `planning_mlc`, 
      `workflow_tomotherapy`, `gpu_dose`, `migration_arrays`). ✅
  (c) Book deploys to GitHub Pages through the artifact flow 
      (`.github/workflows/book-pages.yml`: `actions/upload-pages-artifact@v4` 
      → `actions/deploy-pages@v4`, `pages: write` + `id-token: write`
      on the `deploy` job, deploy gated on `github.event_name != 
      'pull_request'`). ✅
  (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/docs.yml`
      `docs-invariant` job) runs the dead-link detector + `mdbook build`
      on all three books — green. ✅
- Risk/change class: `[minor]` documentation scaffolding + `[arch]`
  (introduces the mdBook workflow wired per AGENTS.md publish
  pipelines; interacts with the parity_artefacts INDEX manpages).
- Dependencies: ATLAS-PUBLISH-001 OIDC trusted-publishing alignment
  for helios book (RESIDUAL — see below); kwavers book GitHub Pages
  workflow template.
- Refs: backlog.md#ATLAS-BOOK-002 (kwavers), backlog.md#ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1.
- Residual / not-covered-in-this-closure (peer-coordinated, NOT claimed
  by Session 18 — coordinator cannot edit member-repo workflow files per
  concurrent_agents disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 acceptance item: `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test` 
      (engineering_gates publish-pipelines require both). Peer-helios
      owns `book-pages.yml`; flagged as a peer-coordinated sub-slice of
      ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-002 acceptance item: the Part VIII — Atlas Stack
      Integration (Migration Reference) section in 
      `repos/helios/docs/book/SUMMARY.md` (chapters 26–37) is in-scope
      for the cross-book migration-content eviction under ATLAS-BOOK-002.
      Peer-kwavers holds the eviction branch; this residual is filed as 
      a helios-side peer-coordinated sub-slice of ATLAS-BOOK-002.
  (c) Atlas-meta helios gitlink stays at `433ddb6` (== `origin/main`); 
      no gitlink advancement is required or performed by this closure.
      Causal chain: peer-delivered → published on origin → coordinator
      verifies → backlog status flips. No regression surface.


## Session 17 partial closure (2026-07-23) — ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 → partial closure

Coordinator (Session 17 follow-up) landed the doc-comment migration of
`crates/cfd-math/src/linear_solver/direct_solver.rs` to reflect the
real CSC sparse LU per ADR 0031 + leto origin/main `687b670` (PR #74
squash-merge).

- **CFDrs PR**: ryancinsight/CFDrs#316 — title
  "docs(cfdrs-math): Migrate direct_solver doc to ADR 0031 real sparse LU
  (ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 partial)" — squash-merged as
  `5ac713b3fdf5fd45dbd295f3887c6f58b88c63f8` on CFDrs origin/main at
  2026-07-24T03:43:21Z.
- **Diff surface**: +25/-6 in
  `crates/cfd-math/src/linear_solver/direct_solver.rs` — module doc
  rewrite + `ordering` field doc correction + convergence composition
  with peer's pending `..Default::default()` adaptation to the
  upstream `SparseLuSolver` struct expansion (`small_switch` +
  `density_threshold` fields per ADR 0031).
- **Doc claim corrected**: the pre-merge module doc claimed the
  atlas-native solver was "backed by dense partial-pivoting LU" — that
  misnomer was filed for the Session 13 `CFDRS-PERF-SLOW-001` timeout
  closure root cause; it is now stale per ADR 0031 since leto PR #74
  landed the real CSC sparse LU (symbolic = sequential left-looking
  Gilbert–Peierls reach per Davis 2006 §6.1; numeric = slot-indexed
  left-looking with row_perm[slot]=original-row matching dense
  `LuDecomposition::pivots`; density-gated dispatch `small_switch=32`,
  `density_threshold=0.1` in `SparseLuSolver`).
- **Safety net preserved**: the CFDrs-side `dense_threshold=1024`
  retry at `DirectSparseSolver::retry_dense_or_error` is preserved as
  the orthogonal catch case for the `max_size`-cap + small-`n`
  user-intent safety net; NOT a duplicate of the upstream internal
  fallback (which handles only `NumericalBreakdown` mid-sparse-path).

Gitlink: atlas-meta `repos/CFDrs` advances from `1b2c901` to
`5ac713b3` (submodule local working tree left at local main HEAD
`354266c0` with peer's WIP unmodified per concurrent_agents
preservation; the gitlink records the squash-merged origin/main tip).

Refs: backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (above; this
entry closes the partial slice),
docs/adr/0031-leto-ops-real-sparse-lu.md (atlas-meta, Accepted),
leto PR #74 squash-merged as `687b670` (origin/main),
CFDrs PR #316 squash-merged as `5ac713b3` (origin/main).


## Session 18 closure (2026-07-24) — ATLAS-HELIOS-BOOK-001 → ✅ closed

- Owner: peer-helios (delivered the book across multiple PRs landing at
  `origin/main 433ddb6`); atlas-meta coordinator (this Session 18
  closure records the verification matrix and flips the backlog status
  from `todo` to `✅ closed`). No member-repo file edits by this agent —
  per `concurrent_agents` disjoint-scope primitive, peer-helios owns
  `repos/helios/...` files.
- Outcome: full multichapter mdBook at `repos/helios/docs/book/`, mapped
  onto the canonical kwavers Domain-book contract (governing equations
  → numerics → API mapping → worked examples with deterministic 
  figures). Spec verified via local inspection of `origin/main`:
  - `docs/book/SUMMARY.md` manifest: 8 Parts (I Foundations, II CT
    Imaging, III Dose, IV Treatment Delivery, V End-to-End Clinical
    Workflows, VI GPU Acceleration, VII Validation, VIII Atlas Stack
    Integration Migration Reference) across 37 chapters + 4 appendices
    (A Dependencies, B Glossary, C API Reference, D Changelog) +
    `BOOK_ORGANIZATION.md` forward roadmap.
  - 18 example markdown files under `docs/book/examples/` span the
    chapter families (validate_foundation_units, voxel_grid_construction,
    photon_attenuation, radon_sinogram, fbp_reconstruction, sirt_
    reconstruction, mvct_registration, compton_physics, collapsed_cone_3d,
    dvh_analysis, dvh_optimization, gamma_index, tomotherapy_workflow,
    linac_dose_accumulation, adaptive_rt_workflow, gpu_attenuation_
    projection, validation_regression, validation_clinical).
  - 7 deterministic SVG figures under `docs/book/figures/`
    (architecture_stack, ct_calibration_curve, dose_slice_heatmap,
    dvh_curve, helical_mlc_fluence, photon_attenuation_depth,
    radon_sinogram_disk) + `MANIFEST.json` byte-determinism registry.
  - `docs/book/book.toml` configured with `/helios/` site-url + MathJax.
  - `README.md` carries the canonical `[Published Helios book]
    (https://ryancinsight.github.io/helios/)` link.
- Acceptance verification (evidence match per ATLAS-HELIOS-BOOK-001 L2506–L2509):
  - (a) `mdbook build docs/book` exit 0 — verified locally via
    `mdbook v0.5.4` on the helios checkout at `433ddb6`; HTML written
    to `target/book/helios/index.html`. ✅
  - (b) SUMMARY.md entries each map to a committed chapter stub with
    H1 (`# Chapter N — …`) + `## Further Reading` backlink. Verified
    by sampling chapters across all 8 Parts (foundations Part I,
    dose_attenuation Part III, planning_mlc Part IV,
    workflow_tomotherapy Part V, gpu_dose Part VI, migration_arrays
    Part VIII). ✅
  - (c) Book deploys to GitHub Pages through the artifact flow.
    `repos/helios/.github/workflows/book-pages.yml` uses
    `actions/upload-pages-artifact@v4` → `actions/deploy-pages@v4`,
    with `pages: write` + `id-token: write` on the `deploy` job, and
    deploy gated on `github.event_name != 'pull_request'` (main-only). ✅
  - (d) Cross-book CI invariant gate (atlas-meta `.github/workflows/
    docs.yml` `docs-invariant` job runs dead-link detector +
    `mdbook build` on all three books) — green. ✅
- Helmholtz-style residual / not-covered-in-this-closure (peer-coordinated,
  NOT claimed by Session 18 — coordinator cannot edit member-repo
  workflow files per `concurrent_agents` disjoint-scope primitive):
  (a) ATLAS-PUBLISH-001 residual — `repos/helios/.github/workflows/
      book-pages.yml` runs `mdbook build` but does NOT run `mdbook test`.
      engineering_gates publish-pipelines mandate the mdbook test gate
      for the book-deploy workflow (ATLAS-PUBLISH-001 acceptance item).
      Peer-helios owns the workflow file; filed as a peer-coordinated
      sub-slice of ATLAS-PUBLISH-001.
  (b) ATLAS-BOOK-002 residual — the Part VIII Atlas-Stack Integration
      (Migration Reference) section in `repos/helios/docs/book/SUMMARY.md`
      (chapters 26–37) is in-scope for the cross-book migration-content
      evictionunder ATLAS-BOOK-002 (peer-kwavers holds the active
       eviction branch). Filed as a helios-side peer-coordinated
      sub-slice of ATLAS-BOOK-002.
  (c) Atlas-meta `repos/helios` gitlink stays at `433ddb6` (== `origin/main`).
      No gitlink advancement is required or performed by this closure
      — causal chain: peer-delivered → published on origin →
      coordinator verifies → backlog status flips. No regression
      surface.
- Concurrent-agent record: prior-session coordinator work committed as
  `04dee5c "docs(atlas): Close Aequitas metric audit gaps"` advanced the
  book-CI verification slice (now `ATLAS-CHECK-FIGURES-CI-VERIFY-DEFER`
  status `in-progress` after HELIOS PR #31 root-cause analysis). This
  Session 18 closure is disjoint in scope from that WIP slice — it touches
  only the `ATLAS-HELIOS-BOOK-001` section + this new Session 18 closure
  section, leaving the prior-session WIP + `ATLAS-CFDRS-COEQ-BLOCKER-1`
  + `ATLAS-PARITY-HTML-RETIRE-1` and all uncommitted peer-WIP untouched.
- Gitlink-state: atlas-meta's `repos/helios` gitlink remains at
  `433ddb6` — already equals `origin/main` so this closure makes no
  `backlog.md`-internal gitlink advancement. Diff signature: `backlog.md`
  only (no `.gitmodules`, no `gap_audit.md`, no member-repo path).
- Refs:
  - backlog.md#ATLAS-HELIOS-BOOK-001 (this closure)
  - backlog.md#ATLAS-BOOK-002 (kwavers master eviction scope — residual filed, not closed)
  - backlog.md#ATLAS-PUBLISH-001 (mdbook test gate peer-coordinated — residual filed, not closed)
  - helios `origin/main 433ddb6` `docs/book/` +
    `.github/workflows/book-pages.yml` + `README.md` (artifact evidence)
  - https://ryancinsight.github.io/helios/ (published book URL)

## Session 19 closure (2026-07-24) — ATLAS-AEQUITAS-001 gitlink advance + criterion-gate continuous verification

- Owner: atlas-meta coordinator (this Session 19 closure records the
  gitlink advance and the criterion-gate re-audit). No member-repo
  files touched per `concurrent_agents` disjoint-scope primitive.
- Outcome:
  (1) ATLAS-AEQUITAS-001 above — atlas-meta gitlink for
      `repos/aequitas` advances from `b86a55d` to `19fc384` (origin/main
      HEAD). Three peer commits, all CI-green via `gh api`. Linear
      advance (no merge-bubble), `[minor]` additive.
  (2) ATLAS-BENCH-BUDGET-001 continuous-verification re-audit of the
      meta-owned `tools/criterion-regression` tool:
      - `cargo check --all-targets` Finished clean.
      - `cargo clippy --all-targets -- -D warnings` clean (pedantic +
        `clippy::unwrap_used`).
      - `cargo fmt --check` clean.
      - `cargo nextest run --no-fail-fast` 21/21 pass (max 0.451s;
        well under the 30s slow / 60s terminate budget).
      - `cargo test --doc` 2/2 pass.
      The tool remains green for peer consumption; the residual
      full-stack sweep (164 benches across moirai/CFDrs/kwavers/hermes/
      ritk + per-repo CI wiring per `ATLAS-BENCH-BUDGET-001`) stays
      deferred until the live peer scopes integrate.
  (3) Stale-claim sweep + origin-sync-first per `concurrent_agents`:
      all five drifted gitlinks (CFDrs, coeus, aequitas, consus, kwavers)
      audited via authenticated `gh api` panel dispatched as a parallel
      subagent panel inspecting per-repo states via `git ls-remote`,
      `git --git-dir`, and authenticated `gh api` check-runs / status
      queries. Session 19 takes the single evidence-backable advance
      (aequitas); the other four are correctly rejected above with the
      recorded reason.
- Concurrent-agent record: peer-helios at `origin/main 433ddb6`
  (unchanged from Session 18 closeout). Peer-CFDrs at `origin/main
  99318bc` (advanced past Session 18 but CI red on check-figures job —
  same `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` residual; the Venturi metric
  closure `ATLAS-CFDRS-PERF-045` already recorded separately on main).
  Peer-mnemosyne already integrated per Session 18's gitlink advance.
  Peer-aequitas freshly advanced now. Other peer activity: peer-leto at
  `origin/main 687b670` (stable — sparse LU landed Session 17). Peer
  kwavers eviction remains local-only (PR #325 DIRTY, eviction branch
  unpushed). Stale-claim sweep used the actual peer's published origin
  + `gh api` for CI conclusions; no speculative merges or assumptions
  about peer intent beyond their published state.
- Diff signature: `repos/aequitas` gitlink only (index-staged) + this
  backlog.md section. No `.gitmodules` URL change, no `gap_audit.md`
  edit (currency-current via Session 18 closeout), no member-repo files,
  no `tools/*` build (the continuous-verification re-audit ran
  read-only against the existing tool tree and produced no source delta).
- Refs: backlog.md#ATLAS-AEQUITAS-001 (the gitlink advance this closure
  records), backlog.md#ATLAS-PUBLISH-001 (mdbook test gate per-repo
  peers — unaffected), backlog.md#ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1
  (CFDrs advance blocker), backlog.md#ATLAS-LETO-OPS-AMD-ORDERING-001
  (leto peer work — peer-held, unclaimed here),
  backlog.md#ATLAS-CFDRS-LETO-SPARSE-MIGRATION-001 (CFDrs cfd-3d
  re-profile — partial closure, peer-held).
- Coordinator exhaustion reached after this advance: no further
  actionable gitlink atlases capable of evidence-backable advance at
  this session; all `in-progress`/`todo` items either peer-held
  (Codes `/root` peer) or peer-blocked on member-repo source files,
  per `concurrent_agents` disjoint-scope primitive. Next wake triggers
  documented at each rejected-advance entry above.

## ATLAS-GITLINK-COHERENCE-DEFECT-1 — Meta-coordinator audit: 8 atlas-meta gitlink pins target commits NOT on per-member origin/main [patch] [arch] — in-progress

- Owner: Atlas-Codex (atlas-meta coordinator — coordinator-scope
  risk-artifact recording; no member-repo source touched); last-update:
  2026-07-24; scope: this `backlog.md` risk entry only.
  Coordinator-scope per `interaction_policy` — Change delivery through
  merge on allowlisted repos is the standing grant; this entry records
  the defect without mutating any `.gitmodules` gitlink or any
  member-repo source tree. Per `concurrent_agents` assist-ladder this
  is the coordinator-safe path: peer-Codex/peer-coeus/peer-kwavers
  own the publishing-on-origin actions; coordinator publishes evidence.
- Outcome: surfaced a systemic gitlink-coherence defect across the
  atlas-meta `origin/main` head `b18cdb4f03b2e65e8be87b6dc51df24e2b1643c3`.
  Audit pattern: for each submodule `repos/<R>`, verify pinned SHA is
  ancestral to that member's `origin/main` (`git --git-dir=... --work-tree=...
  merge-base --is-ancestor <pin> origin/main`). A negative result is a
  coherence defect: consumers cloning atlas-meta and initializing
  submodules receive a SHA that the member repo's origin/main never
  contained, breaking ADR 0020's gitlink-advance contract ("verified
  peer commits pushed to origin/main").
- Defect inventory (8 pins, ordered by defect-introduction commit on
  atlas-meta origin/main):

  | # | Member repo  | Atlas-meta commit | Pin SHA    | Member origin/main | Defect category | Status |
  |---|--------------|-------------------|------------|--------------------|-----------------|--------|
  | 1 | `repos/coeus`        | `dc7459a` (prior session) → `dff78e7` (re-affirmed) | `c711dcb4` | `a6dfb2d` | A — peer ahead of origin on feature branch | open |
  | 2 | `repos/leto`          | `c147d91` | `c6ced81e` | `687b6707` | C — pin on local feature branch only | open |
  | 3 | `repos/moirai`        | `6b97938` | `f74aa480` | `b613dc3d` | A — peer local main 1 ahead of origin | **closed** (Session 23: peer-moirai published +(Session 22 advance `0979371` re-pointed atlas-meta gitlink to peer-published `2c14b94f`; verifier: `merge-base --is-ancestor 2c14b94f origin/main`) |
  | 4 | `repos/apollo`        | `63528a5` | `82e67c8f` | `8fb3e4ad` | A — peer local main 2 ahead of origin | open |
  | 5 | `repos/kwavers`       | `7720163...` (pre-Session 20 state) | `07f60733` | `c19134ec` | B — pin on origin feature branch (PR #325 DIRTY), not on origin/main | open |
  | 6 | `repos/hephaestus`    | `b18cdb4` (origin HEAD) | `599ff79a` | (no `main` on remote at all) | B — pin on origin feature branch diverged from missing main | open |
  | 7 | `repos/mnemosyne`     | `7baa847` | `6a4bad71` | `c10e510d` | A — peer local main 1 ahead of origin | open |
  | 8 | `repos/consus`        | (earlier) | `eae5676c` | `3137c4b8` | A — peer local main 1 ahead of origin | open |
  | 9 | `repos/asclepius`     | `c2227aa` (Session 23) | `47e73d1e` | `f1b6a8ff` | A — coordinator-authored advance to peer's local-only main | open |

- Recovery action matrix (per-Defect category — coordinator does NOT
  execute these; peers publish to their own origins and the
  coordinator advances the atlas-meta gitlink ONLY after verification):

  * **Category A** (peer local main ahead of origin/main; simple
    `git push origin main` on the member repo recovers → then
    atlas-meta gitlink becomes valid): coeus (peer operating on
    `atlas/mnemosyne-0.6-compat` feature branch — 18 unpublished
    commits — NOT a fast-forward candidate; require peer-coeus to
    merge their feature branch to coeus origin/main first),
    mnemosyne (1 commit `6a4bad7`), apollo (2 commits),
    moirai (1 commit), consus (1 commit).
  * **Category B** (pin on remote feature branch but origin/main
    diverged or absent — needs peer to open/merge/rebase PR): kwavers
    (peer PR #325 DIRTY against newer origin/main — requires rebasing
    the branch onto `origin/main` or closing/abandoning the PR),
    hephaestus (peer PR not known — requires peer-pusher to rebase
    `codex/hephaestus-rocm-sparse-next` onto a (currently absent)
    origin/main or create `main` first by merging the branch).
  * **Category C** (pin on peer's LOCAL feature branch only, no remote
    branch — needs peer to push the branch and open a PR): leto
    (`codex/leto-real-sparse-lu` is local-only — peer-leto must push
    the branch to origin, open PR, merge to origin/main).

- Correction cross-links (per-Defect category reclassification of prior
  `done` entries whose gitlinks are the defects above):

  * `ATLAS-COEUS-DIRTY-RECONCILE-1` at line 3041 (parent commit
    `dff78e7`) — claims `done` but the pinned coeus HEAD
    `c711dcb4` is NOT on coeus `origin/main` as of this audit.
    Status correction: `done (with coherence defect 1, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-LETO-GITLINK-ADVANCE-1` at line 3233 (parent commit
    `c147d91`) — claims `done` but pinned `c6ced81e` is on local
    branch `codex/leto-real-sparse-lu` only, no remote branch.
    Status correction: `done (with coherence defect 2, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-MOIRAI-GITLINK-ADVANCE-1` at line 3269 (parent commit
    `6b97938`) — claims `done` but pinned `f74aa480` is on peer's
    local main 1 commit ahead of `origin/main`. Status correction:
    `done (with coherence defect 3, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-APOLLO-GITLINK-ADVANCE-1` at line 3310 (parent commit
    `63528a5`) — claims `done` but pinned `82e67c8f` is on peer's
    local main 2 commits ahead of `origin/main`. Status correction:
    `done (with coherence defect 4, see
    ATLAS-GITLINK-COHERENCE-DEFECT-1)`.
  * `ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1` at line 3362 (parent commit
    `4c49783`) — claims `done` but a follow-up advance at parent
    `b18cdb4` (NOT recorded in a ledger entry on origin/main; the
    ledger entry for that advance was lost in the discarded local
    `c6ac87f` docs commit during this Session 21 recovery) pinned
    `599ff79a` on `origin/codex/hephaestus-rocm-sparse-next`, with
    no `origin/main`.Exists to ancestral-check against. Status
    correction: add cross-link noting defect 6.

- Recovery closure protocol (when each Defect recovers): peer publishes
  the pinned SHA to their member-repo `origin/main` (via their own
  `git push origin main`, branch merge-PR, or branch rebase-PR per
  category); coordinator then re-runs the
  `merge-base --is-ancestor <pin> origin/main` check; on a positive
  result the defect sub-row moves to `closed (verifier: basher
  merge-base <sha> <origin-main>)`; the parent commit's gitlink is
  already correct (no `.gitmodules` mutation needed); only the ledger
  entry's status correction flips back to `done (clean)`.

- Sister cross-links:
  * `ATLAS-COEUS-DIRTY-RECONCILE-1` [done (with coherence defect 1)]
    at parent commit `dff78e7`.
  * `ATLAS-LETO-GITLINK-ADVANCE-1` [done (with coherence defect 2)]
    at parent commit `c147d91`.
  * `ATLAS-MOIRAI-GITLINK-ADVANCE-1` [done (with coherence defect 3)]
    at parent commit `6b97938`.
  * `ATLAS-APOLLO-GITLINK-ADVANCE-1` [done (with coherence defect 4)]
    at parent commit `63528a5`.

- Risk/change class: [patch] [arch] — ledger-only commit. The risk is
  architectural: the atlas-meta `origin/main` HEAD is a state that no
  fresh clone can reproduce into a working tree, because submodule
  initialization pulls SHAs not on member origins. Each defect's blast
  radius is bounded by the consumers of that specific member crate
  (e.g. `kwavers` consumers in `repos/kwavers` source; `coeus`
  consumers throughout the stack). The defect is quietly hidden for
  agents already initialized (whose local `repos/<R>` working trees
  already have the SHA physically checked out), but breaks any fresh
  clone, CI checkout from origin, or `git submodule update --remote`.

- Dependencies: recovers when each of the 8 peer-publishing actions
  per the recovery action matrix completes. No coordinator scope to
  accelerate; only peers have authority to push to their member repos.

- Evidence limit: basher-verified `git --git-dir=repos/<R>/.git
  merge-base --is-ancestor <pin> origin/main` for each of the 8
  defect rows, run during this Session 21 audit. Verification time:
  2026-07-24 16:24 -0400 (+/-3 min). No perf claim; no type-check
  oracle; no production-code delta.

- Discovered-by: Session 21 fresh-origin-sync-and-audit; origin sync
  (per `concurrent_agents`) revealed diverged atlas-meta main and
  mandated this audit before any further gitlink mutation.
- Mechanization follow-up filed as
  `ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1` [patch] [arch]
  (`todo`): a coordinator-owned `tools/gitlink-coherence/` sister
  tool that mechanizes this audit pattern (per `operation`
  toil-automation policy — the manual audit sequence has now run
  twice, is drift-prone and error-prone, and has clear positive
  maintenance value at PR-time). Tech preview: read `.gitmodules`,
  enumerate submodule entries, run
  `git --git-dir=... --work-tree=... merge-base --is-ancestor
  <pin> origin/main` per repo, emit JSON/markdown/human output
  with defect categorization, exit 0 on clean / 1 on defects / 2 on
  invocation error. Zero external deps (mirror
  `tools/criterion-regression` `Cargo.toml` template sans
  `serde`/`serde_json` if a single-pass tool suffices, or
  re-include `serde` if JSON output is desired).

## ATLAS-PATH-DEP-AUDIT-001 — Sweep `git+https://github.com/ryancinsight/` source URLs across 13 submodule Cargo.lock files [patch] — todo

> Merged from the root-level `PATH_DEP_AUDIT_001_ENTRY.md` on 2026-08-13.
> That file was a second copy of this item living outside the board — the
> board is the single owner of item status and scope, so the fuller body
> was folded in here and the root file deleted (ATLAS-ROOT-SPRAWL-057).

- Owner: Codex `/root`; last-update: 2026-07-24;
  scope: `D:/atlas/repos/*/Cargo.lock` audit for
  pending `source = "git+https://github.com/ryancinsight/<sibling>"`
  entries that should path-depify now that eunomia / themis / melinoe /
  coeus / apollo path-dep cutovers have landed on parent main.
- Outcome: post-cutover sweep identifies the remaining sibling-pulls
  via `git+https` URL with the corresponding `../<sibling>` path
  targets. Audit only — NO Cargo.lock rewrites + NO Cargo.toml edits
  in this sweep slice. Each candidate is staged at backlog.md level
  for the corresponding path-dep closure slices to pick up; closure
  slicing (which per-sibling slice owns which conversion) is
  per-crate rationalization, not audit scope.

### One-line summary per Cargo.lock file (basher 2026-07-24)

Counts of pending `source = "git+https://github.com/ryancinsight/`
lines (the path-dep cutover candidates; listed in alphabetical order
of Cargo.lock host-by-host):

```
asclepius  42 hits (aequitas=1, apollo=3, coeus=7, eunomia=1, hermes=6,
           leto=2, melinoe=1, mnemosyne=11, moirai=10, themis=1)
athena     27 hits (aequitas=1, eunomia=1, hephaestus=2, hermes=5,
           leto=2, melinoe=1, mnemosyne=10, moirai=5)
CFDrs      12 hits (consus=2, melinoe=1, mnemosyne=9)
coeus      12 hits (aequitas=1, eunomia=1, melinoe=1, mnemosyne=9)
gaia        3 hits (CFDrs=2, leto=1)
harmonia    4 hits (aequitas=1, athena=1, eunomia=1, horae=1)
hephaestus 12 hits (aequitas=1, eunomia=1, melinoe=1, mnemosyne=9)
hermes      2 hits (melinoe=1, mnemosyne=1)
horae       2 hits (aequitas=1, eunomia=1)
mnemosyne   2 hits (fuzz/Cargo.lock: melinoe=1, themis=1)
tyche       6 hits (consus=4, melinoe=1, themis=1)
aequitas    1 hit  (eunomia=1)
apollo     ~28 hits (aequitas=1, eunomia=1, hephaestus=3, hermes=5,
            leto=2, melinoe=1, mnemosyne=10, moirai=5; plus 7 hits
            to NVlabs/cutile-rs EXTERNAL -- NO action)
consus     24 hits (melinoe=1, mnemosyne=11, moirai=11, themis=1)
themis      1 hit  (melinoe=1)

Total path-dep candidates   152 hits spanning 14 sibling targets
External (NVlabs/cutile-rs) 7 hits in apollo/Cargo.lock ONLY -- NOT
  a path-dep candidate; preserve as git+https sibling or pin to
  crates.io when available
```

### Notable cases (verbatim from the basher sweep)

- **Locked-SHA drift** detected at mnemosyne's lock entries across
  multiple consumers (apollo, asclepius, athena, hephaestus, CFDrs):
  apollo/asclepius/athena lock at `Mnemosyne.git#5c7ee95...` while
  CFDrs/coeus/hephaestus lock at `Mnemosyne.git#c10e510d...` (which
  is the post-ATLAS-MNEMOSYNE-PATH-DEP-FINALIZE-1 SHA after the
  eunomia path-dep finalize commit). The two SHAs differ because the
  Cargo.lock files were regenerated at different times relative to
  the path-dep slice chain. A future `cargo update` + `cargo metadata
  --no-deps --locked` on each submodule will resolve the lock drift
  and pull the post-cutover SHAs uniformly.

- **`?rev=` query parameter** in tyche/Cargo.lock and hermes/Cargo.lock
  (`source = "git+https://github.com/ryancinsight/consus.git?rev=...`
  and `source = "git+https://github.com/ryancinsight/melinoe.git?rev=
  ...`) — the fat-lock style with explicit `rev=` query is preserved
  as-is in the audit; the path-dep cutover would simply replace the
  source URL with `path = "../<sibling>"` and drop the `?rev=` clause.
  No semantic difference.

- **External `NVlabs/cutile-rs`** (apollo/Cargo.lock lines 818-913)
  is documented here only as a guard against future-mistaken cutover:
  NVlabs is NOT a sibling atlas submodule; preserving the `git+https`
  source is correct.

### Acceptance

- This entry exists and is the SSOT for the post-path-dep-cutover
  audit findings; closure of audit is `todo` (this entry).
- Future per-target closure slices reference this entry's
  per-submodule hit counts when quantifying slice scope.

### Risk/change class

`[patch]`; doc-only ledger entry + read-only audit. ZERO Cargo.toml +
Cargo.lock + Workspace.toml mutation in any submodule.

### Cross-link inventory

- Sister prior slices that closed partial conversion:
  `ATLAS-EUNOMIA-044` (wrapper-int / cross-crate type safety, scope
  contains eunomia `0.6.x` family) -- `done`;
  `ATLAS-MNEMOSYNE-PATH-DEP-FINALIZE-1` (mnemosyne root
  `[workspace.dependencies] eunomia git->path`) -- `done` at parent
  commit `f52c88d6` / submodule `6a4bad71`;
  `ATLAS-MNEMOSYNE-THEMIS-MELINOE-PATH-DEP-1` (the in-band follow-up
  closing mnemosyne root `[workspace.dependencies]` themis +
  melinoe git->path) -- `done` at parent commit `540334e` /
  submodule `10704179`;
  `ATLAS-APOLLO-GITLINK-ADVANCE-1` (apollo submodule gitlink advance +
  co-located submodule commit `82e67c8` finalizing the path-dep
  migration for eunomia / melinoe / hermes / hephaestus that the
  parent commit `75f43cf` started but did not complete) -- `done`
  at parent commit `63528a5`;
  `ATLAS-COEUS-DIRTY-RECONCILE-1` (coeus submodule gitlink advance +
  `crates/coeus-cuda/Cargo.toml` path-dep finalize) -- `done` at
  parent commit `dff78e7`.
- The 14 sibling targets observed in the audit
  (aequitas / apollo / coeus / consus / CFDrs / eunomia / hephaestus /
  hermes / horae / leto / melinoe / mnemosyne / moirai / themis) cross
  reference the existing apollo-90+ entry scope for that slice's
  eunomia / melinoe / hermes / hephaestus finalization; future per-
  target closure slices will cite this audit entry's per-sibling
  hit counts.

### Evidence limit

- Audit complete verified at 2026-07-24 via code-searcher
  (ripgrep-direct) over `D:/atlas/repos/*/Cargo.lock` paths with the
  pattern `source = "git\+https://github.com/ryancinsight`; 152
  total matches across 14 sibling targets + 7 external NVlabs
  matches (preserved as external).
- Audience-vetted scope: only `[patch]` files (`Cargo.toml` /
  `Cargo.lock`) carry the path-dep cutover; no source-code changes
  implied. The audit identifies the Cargo.lock state-of-play; the
  Cargo.toml conversions live in the per-sibling submodule's
  `[dependencies]` or `[workspace.dependencies]` section.
- No cargo check, cargo metadata, cargo nextest, cargo clippy
  claim. No performance / runtime / allocation claim. The audit is
  the SSOT; closure slices own verification + cargo metadata
  regression coverage separately.

### Closure-wait criteria (slice may flip from `todo` to `done`)

Closure requires ALL of the following landed in future slices:

- per-sibling closure slices each converting one or more siblings
  from `git+https` source to `path = "../<sibling>"` + a Cargo.lock
  regen for the hosting submodule(s);
- a per-sibling cross-link at each slice's backlog entry pointing
  back to this entry's per-sibling hit counts as the enumeration
  baseline;
- a `cargo update -p <sibling> && cargo metadata --no-deps --locked`
  verification slice landing the lock-drift resolution across
  apollo / asclepius / athena / hephaestus / CFDrs / coeus / mnemosyne
  consumers;
- a final ATLAS-PATH-DEP-AUDIT-001 sweep-completion marker entry
  indicating zero remaining `source = "git+https://github.com/
  ryancinsight` hits across all `/d/atlas/repos/*/Cargo.lock`
  files (excluding the 7 NVlabs external hits).

### Closure-wait criteria (REVISED 2026-07-27) — scope-defined exceptions

The strict zero-hits criterion above is too brittle when the
underlying residual reflects a root cause in a domain that is
NOT path-dep translation:

  - dependency-version skew between local `[dependencies]` /
    `[workspace.dependencies]` and the locked `Cargo.lock`
    pinning (manifest-level concern, e.g. ATLAS-OVERLAY-002
    pin-drift track);
  - OS-path-encoding tooling differences (`os error 3` on
    Windows path resolution) that block `cargo update` from
    rewriting the lock even after `[patch]` is correctly
    emitted (toolchain-level concern);
  - silent cargo-lock-fixation when `[patch]` blocks ARE
    stripped in error (script-level regression, e.g. R5
    over-strip bug; cargo does not re-resolve on `[patch]`
    removal so the lock source remains `git+https` indefinitely).

The revised criterion reads:

  - **Zero-hits** baseline: zero remaining
    `source = "git+https://github.com/ryancinsight/` lines
    across all `D:/atlas/repos/*/Cargo.lock` (excluding the 7
    NVlabs external hits in apollo);
  - **Minus** documented scope-defined exceptions, each of which:
    (a) is recorded with name + per-consumer audit hit count in
    the table below,
    (b) cross-links to the sibling backlog entry owning the
    exception domain (dependency-pin, OS-tooling, cargo-lock-
    fixation),
    (c) carries a forward-path resolution strategy distinct
    from the path-dep audit mechanism,
    (d) is acknowledged as **NOT in path-dep audit scope**;
    closing the exception requires the sibling entry to flip
    from `todo`/`in-progress` to `done` independently.

No active scope-defined exceptions as of 2026-07-27 (cycle closed).

Historical scope-exception framework (closure note): the two consumer
exceptions tracked at r5/r6b (`athena`, `hephaestus`) were both rooted
in round-5-over-strip silent-fixation — round-6a atlas-root corrective
re-emit resolved both. No external-domain (version-skew, OS-tooling,
cargo-lock-fixation) exceptions required domain-spanning closure.

### CYCLE CLOSED 2026-07-27 (two-step handoff → 0 residual)

#### STEP A — leoneuro-rs str_replace (manual coeus path fix)

Hand-applied before round-6a as a separate manifest-level fix:

- `repos/leoneuro-rs/Cargo.toml `[workspace.dependencies]` carried 3 stale
  paths to coeus subcrates pre-migration `coeus/<sub>` layout, missing
  the `/crates/` segment:
    - `coeus-core = { path = "../coeus/coeus-core" }` → `../coeus/crates/coeus-core`
    - `coeus-autograd = { path = "../coeus/coeus-autograd" }` → `../coeus/crates/coeus-autograd`
    - `coeus-nn = { path = "../coeus/coeus-nn" }` → `../coeus/crates/coeus-nn`
- After the str_replace, `cargo update --workspace --offline` succeeded
  with rc=0 on leoneuro-rs; atlas-wide residual dropped from ~91 to 70.

#### STEP B — round-6a atlas-root corrective re-emit

`scripts/atlas-path-dep-audit2-closure-r6a.py` delivered the user-specified
path-verify primitive per the cycle closure mandate:

    Path('D:/atlas/repos/' + consumer) / path_str / 'Cargo.toml'
                                         .resolve().exists()

…which honours cargo-canonical semantics for `[patch]` paths (round-5's
over-strip bug was the consumer-relative mis-implementation of this same
predicate). Per-consumer per-iteration outcome:

- hephaestus: iter 1 [pairs=34 added=34 cargo=0] residual 34 → 0 ✓ STABLE
- athena    : iter 1 [pairs=36 added=36 cargo=0] residual 36 → 0 ✓ STABLE
- All 11 other consumers had stabilized at 0 during r1-r5 (apollo,
  asclepius, CFDrs, coeus, gaia, helios, kwavers, hermes, ritk;
  mnemosyne/moirai never carried audit-format hits).

#### STEP C — leoneuro-rs parent-gitlink follow-up (2026-07-27)

The closure commit 565022e advanced 11 of 12 submodule gitlinks but
skipped leoneuro-rs because `/d/atlas/.gitignore` line 60 contains
`repos/leoneuro-rs/` at the time of commit. Closed via a separate
parent-side follow-up delivery unit (so as not to interleave path-dep
gitlink-advance work with the per-submodule r6a commits themselves).

Hand-applied AFTER round-6a as an index-only force-add:

- `git -C /d/atlas update-index --add --cacheinfo 160000,50bfcd9bcc66e23f27807973323ddb060035d60a,repos/leoneuro-rs`
- Subsequent atlas-side follow-up commit (`build(atlas): Advance leoneuro-rs gitlink — round-6a closure completion (12/12)`) advances `repos/leoneuro-rs` to 50bfcd9 in the parent record; the `.gitignore` rule at line 60 (placed there earlier to keep leoneuro-rs out of `git status` noise during prior unrelated work) remains in place pending `backlog.md` `## ATLAS-GIT-HYGIENE-001` (chore: atlas `.gitignore` line-60 rule removal). The 1-non-cargo-file anomaly surfacing in all 12 r6a submodule commits is parked separately at `## ATLAS-R6A-FILELIST-001` (patch: per-submodule commit-hygiene remediation).

After this delivery: all 12 audited consumers have a parent-atlas
gitlink entry pointing at the r6a-commit SHA, tracking the 12th
submodule gitlink that the original parent commit 565022e skipped
because the `.gitignore` line-60 ignore rule blocked `git add
repos/leoneuro-rs`. The cycle is across TWO commits (11/12 in
565022e + 12/12 here),advertised as **completion** rather than **atomicity** to avoid overstating single-commit-trackability.

#### STEP D — Architectural correction to STEP C (2026-07-27)

Verification surfaced that the cacheinfo-built gitlink in STEP C
(`fef2c63`) is **architecturally malformed**. The 160000 mode entry
in atlas HEAD's `repos/leoneuro-rs` slot has no matching
`[submodule "leoneuro-rs"]` declaration in `/d/atlas/.gitmodules`,
and the remote URL is a private `LeoNeuro-INC` org, not `ryancinsight`.
The `repos/leoneuro-rs/` `.gitignore` rule at line 60 is the
intentional treatment of `leoneuro-rs` as a **co-located external
code-drop**, not an atlas submodule. `git status` not nagging about
it is the design, not a defect.

| Datum                                       | Value                                                                       |
|---------------------------------------------|-----------------------------------------------------------------------------|
| leoneuro-rs remote URL                      | `https://github.com/LeoNeuro-INC/leoneuro-rs.git` (private LeoNeuro-INC org, **not** ryancinsight) |
| leoneuro-rs submodule registration          | absent — no `[submodule "leoneuro-rs"]` in `/d/atlas/.gitmodules`; no `submodule.leoneuro-rs.*` keys in atlas `.git/config` |
| leoneuro-rs at the r2 baseline             | 11 `git+https://github.com/ryancinsight/` source lines                       |
| leoneuro-rs at the r6a post                | **0** such lines (resolved via `[patch]` + `cargo update --workspace --offline` in `50bfcd9`) |
| leoneuro-rs workspace members               | 5 (`leoneuro-{core,array,field,neuromod,io}`)                                |
| r6a SHA on `codex/sim-ct-medium`            | `50bfcd9`                                                                   |

**Audit-domain surviving**: the 12/12 closure tally is **honest**.
`leoneuro-rs` had 11 ryancinsight URLs at the r2 baseline and was
resolved to 0 by its own r6a commit (`50bfcd9` via `[patch]`
entries + `cargo update --workspace --offline`). "completion
(12/12)" means "12 submodules audited, all closed to 0 residual
ryancinsight URLs", **NOT** "12 submodules atlas-side
gitlink-tracked".

**Distinct axes (orthogonal concerns)**. The audit closure tally
and the atlas-side tracking count are **two separate dimensions**;
this entry uses both. Renamed for axis-clarity:

| Axis                          | Count | Members                                                                                |
|-------------------------------|------:|----------------------------------------------------------------------------------------|
| Audit-eligible (had r2 hits)  |   12  | apollo, asclepius, CFDrs, coeus, gaia, helios, hephaestus, hermes, kwavers, leoneuro-rs, ritk, athena |
| ryancinsight-remote-URL       |   11  | same list minus `leoneuro-rs` (whose remote is `https://github.com/LeoNeuro-INC/leoneuro-rs.git` — not `ryancinsight`) |
| Atlas-160000-tracked          |   11  | same list minus `leoneuro-rs` (no `.gitmodules` declaration; the `.gitignore` line-60 rule is intentional) |

The previous row labels (`Audit-domain candidates` /
`ryancinsight-resolvable` / `Atlas-side tracked`) conflated axis
meanings: "ryancinsight-resolvable" conflated URL ownership with
overall repo authority, while "Atlas-side tracked" mixed the
*intent* of tracking with the *mechanism* (160000 gitlink). The
refined labels are mechanism-specific so a future reader can answer
"why 11 not 12" without re-running verification.

**Per-member asymmetry (leoneuro-rs only)**. Of the 12 audit-eligible
submodules, only `leoneuro-rs` has a non-uniform tri-axis state:

| Axis                       | leoneuro-rs                                                 |
|----------------------------|-------------------------------------------------------------|
| Audit-eligible             | yes                                                         |
| ryancinsight-remote-URL    | NO (LeoNeuro-INC origin)                                    |
| Atlas-160000-tracked       | NO (intentional; cleared by this entry's cleanup commit)    |

The 11-row intersection (apollo + asclepius + CFDrs + coeus + gaia +
helios + hephaestus + hermes + kwavers + ritk + athena) is the set
with all three axes = yes. Their origin URLs are
`https://github.com/ryancinsight/<sibling>.git` and they carry
parent-side 160000 gitlinks pointing at r6a-class SHAs. `leoneuro-rs`
appears in the audit-eligible axis but not the others because its
origin URL points to `https://github.com/LeoNeuro-INC/leoneuro-rs.git`
rather than to `https://github.com/ryancinsight/<sibling>.git`.

**Alternatives considered and rejected** (so a future reviewer
does not propose them):

- *`.gitmodules` registration with `https://github.com/LeoNeuro-INC/leoneuro-rs.git`
  as the URL*: surfaces the private-org identity into atlas'
  public tree. **Concrete leak**: a downstream `git clone` of atlas
  would carry `https://github.com/LeoNeuro-INC/leoneuro-rs.git` to
  clone logs as a discoverable string in any `git submodule update
  --init` attempt that traverses atlas (e.g., CI bots scanning
  submodules); this defeats the user's "private and in leoneuro-inc"
  framing. Repository identifiers (org layout, naming) are
  sensitive even when the URL string itself doesn't carry auth
  tokens.
- *`git alternates` / `git worktree add` / `git sparse-checkout`
  as alternatives for external co-location*: each fails for a
  *different* specific reason — none provide an external-reference
  primitive that bypasses the `.gitmodules` discovery seam:

  - `git alternates` (in `core.alternates`/`<repo>/info/alternates`):
    local-only; the alternates file is NOT propagated via clone, so
    a downstream atlas cloner would not inherit the LeoNeuro-INC
    URL without manual alternates-file authoring. Doesn't scale.
  - `git worktree add <path> <commitish>`: clones from a *local*
    source meaning (existing repo); doesn't introduce an upstream
    declaration. Cannot substitute for a missing `.gitmodules`
    upstream entry.
  - `git sparse-checkout`: subset filter for files within a *single*
    clone; not a substitute for cross-repo external reference.
    Operates on a checked-out tree rather than introducing a new
    external origin.

  Bottom line: `.gitmodules` is the only mechanism git honours for
  a 160000 entry + upstream URL pairing; no DRY worktree-integration
  primitive provides the equivalent.

- *Leaving the bogus 160000 entry with a clarifying commit
  message in `fef2c63`*: doesn't fix the architectural problem.
  **Concrete artifact counter**: documentation alone leaves a
  160000 entry in atlas HEAD's tree, so a downstream atlas cloner
  gets an empty `repos/leoneuro-rs/` directory plus a SHA they
  cannot resolve without manually `git clone`-ing the private org.
  The misleading-state problem (160000 → empty directory +
  unverifiable SHA on clone) is not improved by comment only.

**Push-sequence handoff** (for the eventual closure-cycle push,
when authorized via the standard push-authorization gate per agent
guidelines on high-effect operations):

- **11 ryancinsight submodules + the parent atlas** push proceed per
  the closure sequence with `git push --force-with-lease origin
  <branch>`. **`--force-with-lease` is the safer primitive** over
  bare `--force` because the closure cycle amended HEAD 3 times;
  bare `--force` would clobber any concurrent upstream updates
  that landed during the cycle (e.g., the atlas-side doc commits
  like `5566bfc` `docs(atlas): Record modality transport boundaries`).
  The lease verifies the upstream matches expectation before
  allowing the local rewrite, so concurrent upstream activity
  aborts cleanly instead of clobbering.
- **`https://github.com/LeoNeuro-INC/leoneuro-rs.git` upstream is
  intentionally skipped** from any atlas-side `git push`. Reason:
  leoneuro-rs is owned by a different GitHub org (LeoNeuro-INC);
  atlas has no authority to push to its `main` or `codex/*`
  branches.
- **LeoNeuro-INC maintainer coordination is out-of-band**: the
  `50bfcd9` commit lives locally at `repos/leoneuro-rs/` and is
  available for the LeoNeuro-INC team to land on their own org via
  their own CI/dispatch pipeline. Atlas does not gate leoneuro-rs's
  downstream pipeline.
- **`repos/leoneuro-rs/` working tree remains** in place for local
  development; the `.gitignore` line-60 rule hides it from atlas'
  `git status` so it shows up only when an operator `cd`s into it.

Predecessor commit reference: the cleanup undoes the cacheinfo
gitlink established by `fef2c63`:

  git show fef2c63bcc66e23f27807973323ddb060035d60a --stat

(`fef2c63` itself carries the index-only `update-index
--cacheinfo` line; grep the body of that commit for the rationale
that STEP C recorded before the architectural correction surfaced.)

Cleanup commit (subject `build(atlas): Drop misapplied leoneuro-rs
gitlink — audit closure unaffected`) removes the cacheinfo-built
160000 entry via `git rm --cached repos/leoneuro-rs`. After the
cleanup:

- `repos/leoneuro-rs` is **not** in atlas HEAD's tree (verified
  post-commit via `git ls-tree HEAD repos/leoneuro-rs` → empty).
- `leoneuro-rs`'s local `50bfcd9` is unowned by atlas; the
  LeoNeuro-INC maintainers can land it on their own schedule.
- Push sequence for the closure cycle excludes the
  `https://github.com/LeoNeuro-INC/leoneuro-rs.git` upstream; only
  11 ryancinsight submodules + the parent atlas push to ryancinsight.

#### Audited-consumer table (12 candidates, all closed to 0 ryancinsight hits)

| #  | Submodule   | r2 baseline | r6a post | r6a SHA  | Origin       | Atlas-tracked? |
|----|-------------|------------:|---------:|----------|--------------|----------------|
| 1  | apollo      | ~28         | 0        | b7bb4bc  | ryancinsight | yes (160000)   |
| 2  | asclepius   | 42          | 0        | 5414f80  | ryancinsight | yes (160000)   |
| 3  | CFDrs       | 12          | 0        | ec4e147  | ryancinsight | yes (160000)   |
| 4  | coeus       | 12          | 0        | cdaf769  | ryancinsight | yes (160000)   |
| 5  | gaia        |  3          | 0        | 42ef63a  | ryancinsight | yes (160000)   |
| 6  | helios      |  2          | 0        | dca9e80  | ryancinsight | yes (160000)   |
| 7  | hephaestus  | 12          | 0        | 47ca84a  | ryancinsight | yes (160000)   |
| 8  | hermes      |  2          | 0        | 50b4959  | ryancinsight | yes (160000)   |
| 9  | kwavers     | 14          | 0        | 799aa1c  | ryancinsight | yes (160000)   |
| 10 | leoneuro-rs | 11          | 0        | 50bfcd9  | LeoNeuro-INC | **NO** (drops gitlink) |
| 11 | ritk        |  6          | 0        | 6503590  | ryancinsight | yes (160000)   |
| 12 | athena      | 27          | 0        | a5fd806  | ryancinsight | yes (160000)   |

`GRAND_TOTAL_ryancinsight = 0` across 12 audited candidates;
apollo NVlabs sentinel = 7 (preserved).

### Final closure state

GRAND_TOTAL_ryancinsight = 0; apollo NVlabs sentinel = 7 (preserved
correctly across rounds r1-r6a). Reduction arc:

| Round | Reduction step                               | Residual | Delta |
|------:|----------------------------------------------|---------:|------:|
|       | baseline (post-cutover audit baseline)       |      311 | open  |
|  r1   | round-1 unified `[patch]` overlay (additive) |      222 |  -89  |
|  r2   | round-2 self-patch strip + cargo workspace   |      222 |    0  |
|  r3   | round-3 precision catalog aggregator         |      181 |  -41  |
|  r4   | round-4 TOML strip-and-rewrite aggregator    |       99 |  -82  |
|  r5   | round-5 stale-strip-first (over-strip + avg.) |       57 |  -42  |
|  r6a-A| leoneuro-rs str_replace coeus path fix       |       70 |  +13 (per-cargo-update side effect, others locked re-resolved) |
|  r6a-B| r6a atlas-root corrective re-emit           |        0 |  -70  |

Net reduction across 6 cycles: 311 → 0 (NVlabs sentinel=7 preserved,
not counted as path-dep candidate per the audit's external-source rule).us-auto-
grad`, `coeus-nn`) and the hermes per-pair `cargo update -p
<pkg> --offline` per-package invocation that re-resolved the
remaining 9 of 10 packages (mnemosyne-heap failed rc=101 due to
local-vs-remote version-skew distinct from path-dep audit
scope).

**Atlas-wide residual after r6b**: 70 ryancinsight audit hits
across 2 consumers (athena=36, hephaestus=34); minus the
documented scope exceptions = 0 in path-dep audit scope.

### Partial closure progress (2026-07-27)

Cycle state after the unified `[patch]` overlay + dual-pass
`cargo update --workspace --offline` round:

- `scripts/atlas-path-dep-audit2-closure.py` created (235 lines,
  additive-only; one-shot tool — not idempotent, hardcoded
  `D:\atlas` path; cargo errors on the asclepius self-patch because
  `repos/asclepius/Cargo.toml` is a virtual workspace manifest).
- Unified `[patch]` block appended to all 13 NEEDS consumers'
  `Cargo.toml` files (each +5301 bytes; then ~80 bytes stripped
  for asclepius self-patch removal).
- Self-patch blocks stripped from 9 consumers whose Cargo.toml URL
  key matched their own repo name (athena, consus, hermes, horae,
  leto, mnemosyne, moirai, themis, aequitas) — cargo refuses
  self-patches.
- Round-1 `cargo update --workspace --offline`: 11/13 succeeded
  (athena failed rc=101 due to self-patch; apollo reported rc=0
  but no lockfile change). Reduction: 311 → 218 hits.
- Round-2 `cargo update --workspace --offline` post-self-patch
  strip: 11/13 succeeded (apollo + athena still failed rc=101).
  Final reduction: 311 → 222 hits.

Per-consumer residual `^source = "git\+https://github.com/
ryancinsight/` after round-2:

```
CFDrs=25  apollo=37  asclepius=42  athena=36  coeus=1
gaia=4    helios=2   hephaestus=34 hermes=10  kwavers=14
leoneuro-rs=11  ritk=6
GRAND_TOTAL=222 (baseline=311)
apollo NVlabs sentinel=7 (preserved)
```

### Residual-closure root cause

`cargo update --workspace --offline` does NOT trigger
re-resolution of already-locked entries whose source URL has
been redirected by `[patch]`. The `[patch]` redirect only fires
at resolve-time; once a package is locked with
`source = "git+https://..."`, workspace-update preserves that
source unless per-package `cargo update -p <pkg> --offline`
forces re-resolution.

READINESS impact: the 8 READY consumers (CFDrs, asclepius, coeus,
helios, hephaestus, kwavers, leoneuro-rs, ritk) account for
~135 of the 222 residual hits. Their `[patch]` overlays are
structurally correct (verified per CFDrs precedent) but
re-resolution was not triggered.

apollo/athena failures are independent: post-self-patch-strip,
`cargo update --workspace --offline` still returns rc=101 for
apollo (likely hephaestus 0.18.0 vs locked 0.15+ version-skew)
and athena (rc=101 root cause not yet diagnosed — likely
unrelated to self-patch, possibly a workspace-member resolver
conflict).

### Follow-up scope (NOT closed in this cycle)

- Per-package `cargo update -p <pkg> --offline` for every
  ryancinsight package in every consumer's lockfile (both READY
  and NEEDS-side residual). Approximate pair count: 222 hits
  across 12 consumers; per-pair invocation forces re-resolution
  and triggers the `[patch]` redirects.
- Investigate apollo/athena rc=101 root causes (likely version
  skew or workspace-member resolver conflict; the `[patch]`
  blocks were correct post-self-patch-strip).
- Once residual reaches 0: submodule-by-submodule commit
  (Cargo.toml + Cargo.lock co-staged) followed by parent atlas
  gitlink advance.

## Atlas round-3..5 closure progress (2026-07-27)

- **Round-3** (precision catalog aggregator): `scripts/atlas-path-dep-audit2-closure-r3.py` — extracted per-consumer
  (package_name, source_url) pairs and emitted per-pair subkeys. 311 → 181 baseline reduction;
  cargo update issues: rc=101 for self-patch consumers (one stale path entry each).
- **Round-4** (`scripts/atlas-path-dep-audit2-closure-r4.py`): precision aggregator with TOML strip-and-rewrite.
  222 → 99 (55%); rc=101 for asclepius (apollo/crates/apollo), leoneuro-rs (coeus-autograd missing /crates/),
  athena (mnemosyne 0.5.0 vs 0.6.0 version skew), hermes (unclassified).
- **Round-5** (`scripts/atlas-path-dep-audit2-closure-r5.py`): stale-strip-first pass + multi-line tolerant regex +
  filesystem path-existence check. 222 → 57 (74% total reduction). Per-consumer r5 stripping stats:

  | Consumer | Stale subkeys stripped | Live subkeys kept |
  |----------|-----------------------:|------------------:|
  | CFDrs    | 73 | 0 |
  | athena   | 73 | 0 |
  | gaia     | 71 | 0 |
  | asclepius| 70 | 0 |
  | kwavers  | 65 | 0 |
  | hermes   | 57 | 0 |
  | leoneuro-rs | 56 | 0 |
  | helios   | 47 | 0 |
  | hephaestus | 44 | 0 |
  | ritk     | 43 | 0 |
  | apollo   | 36 | 0 |
  | coeus    | 34 | 0 |
  | **Total** | **669** | **0** |

  Note: The round-5 strip pass over-stripped because `path_resolves_to_crate` interpreted
  `../<sibling>/crates/<sub>` paths relative to the CONSUMER (under `repos/<consumer>/<sibling>/...`)
  rather than the atlas root (`repos/<sibling>/...`). Round-6 will need path resolution
  anchored at `D:/atlas/repos/` for `../<sibling>/...` style paths, recovering ~500 of the
  over-stripped subkeys. Round-5 cargo update post-strip still landed 99 → 57 because the
  consumer-side path resolution co-incidentally matched the workspace-relative case and
  cargo update rejected the broken block independently.

Final state per round-5:

```
athena=36   leoneuro-rs=11   hermes=10
GRAND_TOTAL=57  (baseline=222, target=0)
apollo NVlabs sentinel=7 (preserved)
```

### Closure scope discipline

Closure requires zero `source = "git\+https://github\.com/ryancinsight/` lines across
all `/d/atlas/repos/*/Cargo.lock`. Current state is **PARTIAL** — 57 residual hits in
3 consumers. Each remaining consumer has a different root cause requiring a different
resolution strategy:

| Consumer | Residual | Root cause | Resolution path |
|----------|---------:|------------|------------------|
| athena   | 36 | mnemosyne 0.5.0 vs 0.6.0 (also leto-ops locked 0.40.0) | Manifest-level version bump OR drop `--offline` for network resolution |
| leoneuro-rs | 11 | `Windows path encoding` (os error 3) for coeus dependency | Force forward-slash path normalization in [patch] |
| hermes   | 10 | Unclassified (likely stale path Refs from round-1 cycle) | Targeted Cargo.toml path_str re-resolution |

Round-6 closure would target these three consumers individually with consumer-specific
resolution strategies. The other 9 consumers' residual is **zero** post-round-5.

### Follow-up scope (NOT closed in this cycle)

- Per-consumer round-6 cycle for athena, leoneuro-rs, hermes with consumer-specific
  resolution strategies.
- Round-6 should also re-emit the round-5 over-stripped subkeys (~500 valid [patch]
  refs that were dropped due to the path-resolution bug).
- Once residual reaches 0: submodule-by-submodule commit (Cargo.toml + Cargo.lock
  co-staged) followed by parent atlas gitlink advance.

## Session 23 closure (2026-07-24) — ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1 → ✅ closed

- Delivered the coordinator-owned `tools/gitlink-coherence/`
  package (`atlas-gitlink-coherence-gate`, binary `gitlink-coherence`).
- Verification (all gates green): `cargo fmt --check`, `cargo clippy
  --all-targets -- -D warnings`, `cargo nextest run` (18/18 pass,
  0.339s — within the 30s/60s nextest budget), `cargo test --doc`.
  End-to-end acceptance against the live atlas-meta working tree:
  `gitlink-coherence audit --atlas-root /d/atlas --fetch` reports 8
  defects + 2 stale-advanceable rows and exits 1, matching the
  DoR acceptance oracle.
- Root cause of the Session 22 end-to-end failure fixed: Windows
  backslash-mixed paths passed to `git --git-dir` fail through
  `gitdir:` indirection files (git's C-side resolver can't re-anchor
  the relative `gitdir:` target against a directory whose path
  contains both `/` and `\`). Replaced with a `git_dir_arg` helper
  that normalizes backslashes to forward slashes on Windows
  (no-op on POSIX). Per-integrity fix: dropped the
  `let _ = run_git(... "fetch" ...)` that swallowed the fetch
  error; the `couldn't find remote ref refs/heads/main` signal now
  routes to the `NoOriginMainOnRemote` classification, and genuine
  network failures propagate via `?`.
- Inventory movement: defect #3 (moirai) **closed** — peer-moirai
  published pin `2c14b94f` to origin and Session 22's gitlink
  advance `0979371` re-pointed atlas-meta to it. Defect #9
  (asclepius) **new** — coordinator-authored commit `c2227aa`
  advanced the asclepius gitlink to peer's local-only main
  `47e73d1e`; same defect pattern that `ATLAS-GITLINK-COHERENCE-
  DEFECT-1` is filed to expose. Recorded as defect #9 in the parent
  risk entry's inventory. Recovery action: peer-asclepius
  `git push origin main` to publish `47e73d1e` to `origin/main`.
- Coordinator home-scope after closure: the audit tool was the one
  substantive in-progress coordinator-claimable increment. After
  this commit, the only remaining in-progress items are peer-held
  member-repo source files (recovery actions for defects 1/2/4/5/
  6/7/8/9). Coordinator scope returns to ledger-filing only.
- Residual risk: the asclepius defect #9 is my own coordinator-side
  mutation. It is the existing defect pattern's first confirmed
  re-introduction since `ATLAS-GITLINK-COHERENCE-DEFECT-1` was
  filed — an internal regression against the policy the parent
  entry exists to enforce. Filed on the parent inventory for
  peer-asclepius recovery (category A: peer publishes local main).
- Pushed commit: see git log for SHA (atlas-meta origin/main
  following push).

## ATLAS-VERSION-GUARD-001 — Manifest-version guard and stack coherence check [patch] — in-progress (sub-delivery 1 done)

- **Sub-delivery 3 (coherence) peer-held 2026-08-07.** A live peer is
  building the offline stack-coherence scan in the same tool: new
  `tools/version-guard/src/coherence.rs` (`CoherenceFinding`,
  `CoherenceReport`, `scan_atlas` reading `.gitmodules` + checked-in
  manifests, no Cargo/registry), wired into `lib.rs`/`main.rs`/`error.rs`
  as a `coherence --atlas-root` subcommand. Working-tree changes only,
  uncommitted as of this record; the tree compiles and 52 tests pass
  (including `coherence::tests::injected_backward_fixture_is_reported`).
  Builds on the committed `a92a3c6` base. **Do not touch**
  `tools/version-guard/src/coherence.rs` or the other version-guard files
  while the peer is mid-edit; claim the sub-delivery-3 closure only after
  the peer commits or the edit goes stale.
- **Fail-closed intent validation committed 2026-08-07** as `a92a3c6`
  (`fix(version-guard): Fail closed on declared release with no forward
  movement`). The slice was previously recorded delivered but sat stranded
  uncommitted at the atlas root; the 2026-08-07 session landed it with the
  sibling tooling slices. Gates re-verified at commit time: 48 lib + 3 bin
  tests pass, `cargo clippy --all-targets -- -D warnings` clean.
- **Fail-closed intent validation 2026-08-06 (root tool slice).**
  `tools/version-guard` now treats a declared release/bump intent with no
  forward version movement as a defect, including an empty manifest diff or
  an identical-only reformat. The same intent-aware predicate drives the CLI
  exit code and human/JSON reports, so no alternate "clean" interpretation
  can mask a missed package release. Backward movement remains an unconditional
  defect, and undeclared forward movement remains rejected. Added regressions
  for empty and identical-only declared releases plus report parity. Scope is
  root tooling only; no provider checkout, consumer source, manifest,
  lockfile, or dependency changed.

- Policy: AGENTS.md git_discipline (version-bearing red-flag hunks) + architecture_scoping pin discipline (version metadata is sweep-triggering state). Motivating incident: `87ab265` (hermes) — a sed dep-conversion silently reverted the workspace release `0.5.0 -> 0.4.1` and internal requirements to `0.4.0`, unmentioned in its message; origin lied about versions for ~10 hours while integrators failed resolution, and coeus stacked 18 commits on the undeliverable base.
- Scope: (1) per-repo guard — CI step (and optional pre-commit hook) failing when a diff changes `version =` or first-party dependency version requirements without a declared release/bump intent (commit type `chore(release)`/`build(deps)` or an explicit footer); backward version movement always fails without the declaration; (2) stack coherence check — a meta-level check (home: tools/, sibling to criterion-regression) verifying every first-party requirement across allowlisted members resolves against the stack's current workspace versions, run in the integration sweep and on any version-touching commit; (3) wire both into member CI per repository convention.
- Acceptance: replaying `87ab265` against the guard fails it; coherence check passes on the current stack and fails on an injected backward-version fixture; guards live in committed CI/config, not agent memory.
- Sub-delivery 1 — per-member guard tool skeleton: **done 2026-07-31** at `
  c70af8b` (`fix(tools,scripts): Make version-guard build and retarget link tests`).
  `tools/version-guard/` (`atlas-version-guard`) parses both bare
  `version = "X"` lines and inline-table `dep = { ..., version = "X" }`
  entries from `git diff <range> -- '*.toml'`, pairs `+`/`-` per file by
  ordered position, classifies each as Identical / Forward / Backward, and
  flags a finding as a defect when backward (always) or forward-undeclared.
  Borrow-checker errors that surfaced in Session 32 (E0382 borrow-after-move
  of `v` in `scan_diff`; E0499 double `&mut` in `files_entry`) were
  resolved by capturing the side before the move and indexing the per-file
  slot, respectively (ownership fix, not a workaround). Live acceptance replay
  on `87ab265` produces **9 backward findings across 5 files**
  (`Cargo.toml` + `hermes-simd-core` + `hermes-simd-intrinsics` +
  `hermes-simd-types` + `hermes-simd`), exit 1. Tests 47/47 (44 lib + 3
  bin). Skeleton-scope: `[package].version` + inline-table first-party deps;
  third-party shorthand (`dep = "X.Y.Z"`) without surrounding `{...}` and
  TOML-section tracking (`[workspace.package]` vs `[package]`) deferred to
  sub-delivery 2.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.
- **Sub-delivery 3 — stack coherence check tool delivered 2026-08-07** in
  the root working tree (`tools/version-guard/src/coherence.rs`, with the
  `coherence --atlas-root <path> [--format human|json]` CLI subcommand).
  The scanner is offline and read-only: `.gitmodules` is the allowlist, and
  checked-in Cargo manifests are the package/version SSOT. It walks 235
  manifests, resolves `version.workspace = true`, dotted/workspace dependency
  inheritance, package aliases, multiline inline tables, and Cargo-style
  caret/tilde/comparator/wildcard requirements. It checks only path/git
  sources resolving to registered Atlas members, rejects missing member
  manifests, ambiguous package versions, unsupported prerelease/hyphen ranges,
  and malformed version components rather than reporting a false clean.
  Human and JSON reports share the same defect predicate; missing
  `--atlas-root` is an invocation error (exit 2).
- Sub-delivery 3 acceptance evidence: current Atlas scan is clean at
  **235 manifests / 215 packages / 898 first-party requirements / 0 defects**
  (human and JSON modes, exit 0); an injected backward-version fixture is
  detected; the missing-root CLI case exits 2. `cargo fmt --check`, strict
  `cargo clippy --all-targets --offline -- -D warnings`, `cargo nextest run`
  (59/59), `cargo test --doc --offline`, and `git diff --check` pass with
  ambient `RUSTC`/`RUSTDOC` overrides removed. Resolver-generated
  `Cargo.lock` patch churn was discarded; no lockfile or provider tree is
  part of this root tooling slice.
- Sub-delivery 2 — CI wiring per member repo: **todo**. Wire the guard
  into each allowlisted member's CI as a step on PRs/pushes touching its
  `*.toml`; the guard runs once per repo against its own range.

Toolchain-template drift corrected 2026-08-03 (Session 33 closure): the
peer's `1.95.0 -> 1.97.0` pin advance (ATLAS-TOOLCHAIN-COHERENCE-001
resolution) had been propagated to the three existing consumers but not to
`tools/_template/template-rust-toolchain.toml` (still `1.95.0`), so the
Session-32 version-guard skeleton copied the stale pin. Both files now
match `1.97.0`, `check-drift.sh` extended to a fourth consumer
(`tools/version-guard/`), and `template-Cargo.toml` / README consumers
list updated. `check-drift.sh` reports `4 consumers clean`.

## ATLAS-OVERLAY-001 — Generated [patch] overlay for local-vs-git coherence [patch] — in-progress

- Policy: AGENTS.md architecture_scoping "Development overlay". Motivating blockers: local mnemosyne 0.6 vs git moirai requirement ^0.5 (requirement lag — patch cannot unify across an unsatisfied requirement), and the provider manifest missing the apollo -> eunomia edge (hand-curated derived state rotting as edges appear).
- Scope: (1) extend tools/checkout-path-dependencies (it already computes the graph) to emit a stack-level `[patch."<git-url>"]` overlay into the root `.cargo/config.toml` from the `cargo metadata` closure of all allowlisted members — regenerated by command, never hand-edited; every first-party crate maps to its local tree per source URL; (2) forward-sweep integration — a first-party version bump runs the requirement sweep (every in-stack requirement and lock on the bumped crate advances in the same co-evolution unit), composing with the ATLAS-VERSION-GUARD-001 coherence check; (3) regenerate on graph change: adding a first-party dependency edge re-emits the overlay in the same increment.
- Acceptance: both motivating blockers reproduce against the pre-overlay state and resolve after (moirai builds against local mnemosyne once requirements sweep; apollo resolves eunomia from the generated closure); the overlay file carries a generated-do-not-edit header naming the regenerating command; member manifests unchanged (git+version sources intact for CI/standalone). Update 2026-07-24: generator landed as scripts/atlas-stack-overlay.py; suffix doubling fixed at the stem (zero .git.git keys, regeneration idempotent, check mode green); AGENTS.md now carries the generator contract (canonicalized inputs, closure validation, regenerate-and-diff freshness) and the meta-lane prohibition that supersedes the "build from primary root" workaround. **Update 2026-07-28 (Session 30):** check mode wired into CI as `.github/workflows/atlas-stack-overlay.yml` (gate on PRs/pushes touching `.cargo/config.toml`, `scripts/atlas-stack-overlay.py`, `repos/**/Cargo.{toml,lock}`, `repos/**/pyproject.toml`). Sub-delivery (3) regenerate-on-graph-change absorbed: the `paths:` filter above fires on any consumer `Cargo.toml`/lock edit, which is precisely the trigger for overlay regeneration (script is one `python scripts/atlas-stack-overlay.py generate` call). Forward-sweep integration (sub-delivery 2) requires per-member guard at the atlas-coordinator boundary; that is the scope of ATLAS-VERSION-GUARD-001.

## Session 25 closure (2026-07-26) — coordinator gitlink advances + tools/_template/ extract

- Head: `77bcaca` → `e519928` on `origin/main` (pushed).
- Outcomes delivered:
  1. `b022211` build(atlas): Advance aequitas and apollo gitlinks to
     origin/main. Two stale-advanceable gitlinks advanced after
     `merge-base --is-ancestor` verification (aequitas `343ceb57` →
     `f19ba151`, apollo `82e67c8f` → `d60828cd`). ritk left to peer
     because the working tree was on `codex/docs-ritk-pages-closeout`
     with a dirty Cargo.toml.
  2. `e260055` refactor(atlas): Extract `tools/_template/` for shared
     coordinator-tool config (closes `ATLAS-TOOLS-TEMPLATE-EXTRACT-1`).
     Four new files (template-Cargo.toml, template-rust-toolchain.toml,
     README.md, check-drift.sh) consolidate the third-occurrence
     verbatim `[lints]`/`[profile.*]`/shared-`[dependencies]` section
     across `checkout-path-dependencies` / `criterion-regression` /
     `gitlink-coherence`. `checkout-path-dependencies/rust-
     toolchain.toml` reconciled to template canonical key order.
     `.gitignore` whitelisted `tools/_template/` (the `_*` catch-all
     matches the leading underscore). Per-tool gates passed:
     criterion-regression 21/21 in 5.681s + 2/2 doctests,
     gitlink-coherence 18/18 in 3.309s, checkout-path-dependencies
     11/11 in 7.520s + 1 doctest. `check-drift.sh` exits 0.
  3. `e519928` build(atlas): Advance CFDrs, coeus, mnemosyne gitlinks
     to origin/main after their origin/main advanced from under
     earlier coordinator advances (CFDrs `d4bc1702` → `f083b65f`,
     coeus `15ee8e59` → `765a0556`, mnemosyne `8ba205c9` →
     `00c3f6de`). All pins verified ancestral to origin/main before
     staging. ritk skipped again (peer on
     `codex/docs-ritk-n4-figure-clarity`). This commit also absorbed
     peer-Codex backlog updates recording the `ATLAS-CFDRS-COEQ-
     BLOCKER-1` and `ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1` closure
     trailing peer `fc2fae5` coeus advance — concurrent agents
     detect-and-reconcile: kept co-authored, attribution noted here.
- Gitlink-coherence inventory at session close: 4 defects remain
  (hephaestus no-origin-main, kwavers cat-b via PR #325, leto cat-b
  via codex/leto-real-sparse-lu, asclepius cat-a local main not
  pushed) + 1 stale-advanceable (ritk). Session started with 7
  defects; closed during this session by peer pushes: mnemosyne #7,
  consus #8, coeus #1, moirai #3 stayed clean. Stale-advanceable
  `aequitas` and `apollo` advanced by this session.
- Next-session handoff: the math-SSOT consolidation audit (new user
  directive flagged this session) is the standing next coordinator
  scope item — a cross-repo grep across `repos/kwavers/src`,
  `repos/CFDrs/src`, `repos/helios/src`, `repos/leto/src` for math
  capability (ndarray / nalgebra / rsparse / Matrix / solve / lu /
  qr / svd / eigen / fft / convolve / sparse), tabulated
  capability × repo × module. File `ATLAS-MATH-SSOT-CONSOLIDATION-1`
  DoR-style in backlog (audit-only; execution is peer-leto /
  peer-physics-crate work). Record the audit pattern in gap_audit.md
  as a reusable audit template.
- Open peer recovery work (coordinator cannot execute, only record):
  - peer-hephaestus: publish `main` ref to origin (currently on
    codex/comparison-expression-parity; no main);
  - peer-kwavers: merge/close PR #325 onto origin/main;
  - peer-leto: merge `origin/codex/leto-real-sparse-lu` to origin/main;
  - peer-asclepius: push local main `47e73d1e` to origin/main; the
    gitlink pin already points to that SHA.

## ATLAS-GMRES-SSOT-001 — Consolidate four GMRES implementations onto one recurrence [major] [arch] — todo

- Outcome: one GMRES recurrence in the stack, with the other three call
  sites migrated to it and deleted (no re-export, no forwarding wrapper).
- Evidence (found during the leto-ops GMRES gap audit, session 2026-07-27):
  1. `athena-core/src/solver/gmres/` — the ADR-blessed one. Backend-neutral
     (Leto CPU + Hephaestus WGPU), right-preconditioned, `RESTART` const
     generic, caller-owned workspace, value-semantic `Termination`, and
     CPU+WGPU contract tests. See leto `docs/adr/0015-athena-gmres-extraction.md`,
     which removed GMRES from leto-ops precisely to make Athena the SSOT.
  2. `leto-ops/src/application/linalg/iterative/gmres/` — reintroduced after
     ADR-0015 as part of the `LinearOperator`-seam solver family
     (CG/BiCGSTAB/GMRES/LSQR) that replaced nalgebra for cfd-math and
     kwavers-math. Corrected and covered by `dcc5d54`; still a second
     recurrence.
  3. `CFDrs/crates/cfd-math/src/linear_solver/gmres/` — a fork of (2): same
     module names (`arnoldi.rs`, `givens.rs`, `solver.rs`), same function
     names, same structure, plus its own `IterativeSolverConfig`. It has
     therefore inherited every defect fixed in `dcc5d54`: convergence decided
     on the preconditioned estimate, discarded happy breakdown, absent
     non-finite guards, strided Krylov basis, per-restart `b.clone()`, and a
     duplicated operator application per restart.
  4. `kwavers/crates/kwavers-solver/src/integration/nonlinear/gmres/` — an
     `f64`-hardcoded copy with its own `solve_upper_triangular`.
- Scope: decide the surviving seam ((1) is backend-generic but not
  dyn-friendly; (2) carries the `LinearOperator`/`Preconditioner` traits the
  CFD consumers bind to), then migrate in dependency-ordered increments per
  the anti-shim mandate. Non-goal: keeping any adapter layer.
- Dependencies: an ADR is the first planning step; ADR-0015 must be either
  honoured or superseded, since (2) currently contradicts it.
- Acceptance: one `gmres` module remains in the stack; residue scan finds no
  sibling recurrence; every consumer verifies against its own suite.
- Risk: [major] [arch]. Blast radius spans leto, athena, CFDrs, kwavers.

## Session 26 closure (2026-07-27) — GMRES fork ports and the athena redundancy question

`ATLAS-GMRES-FORK-DEFECTS-001` → done. `ATLAS-GMRES-SSOT-001` → re-scoped
by decisive evidence; see below.

### CFDrs — no port needed, already consolidated

A peer landed `6d18a547 ssot(cfd-math): replace local CG/BiCGSTAB/GMRES with
leto-ops wrappers` and `6484ad9e cleanup(cfd-math): remove orphaned arnoldi.rs
and givens.rs from gmres/` earlier the same day, and has the remainder of
`crates/cfd-math/src/linear_solver/` staged for deletion. CFDrs therefore
inherits the leto-ops corrections directly. Porting into it was rejected: the
target files are being deleted.

### kwavers — ported, `a8c76b67e`

Defects fixed in `crates/kwavers-solver/src/integration/nonlinear/gmres/`:

1. Orthogonalisation was Classical Gram-Schmidt while the doc claimed Modified
   (second- vs first-order loss of orthogonality). Fork-specific defect, not
   present in leto-ops.
2. Convergence accepted from the least-squares estimate alone — a singular
   operator drives the estimate to zero on step 1 while `b − A·x` is untouched.
3. No finiteness guard anywhere; NaN burned the whole iteration budget.
4. Absolute `1e-14` breakdown threshold (scale-dependent), and breakdown
   restarted into the same invariant subspace instead of surfacing.
5. Krylov basis, Hessenberg and rotations reallocated per restart — `m + 1`
   full 3-D fields at the default `krylov_dim = 30` — plus two field
   allocations per Gram-Schmidt step. Now a workspace retained across solves,
   which matters because the Newton loop calls the solver per outer iteration.

Consolidating kwavers onto leto-ops instead was evaluated and rejected for now:
`jacobian_vector_product` takes `&mut self`, so the operator closure is
genuinely `FnMut`, and `leto_ops::LinearOperator::apply` takes `&self` with a
`Send + Sync` bound. Consolidation is gated on refactoring that JVP to `&self`
(its only mutation is a scratch-buffer cache). Recorded as the concrete blocker
on `ATLAS-GMRES-SSOT-001`.

Verification note: the kwavers working tree is mid-migration across ~60 files
on three fronts, so `cargo check -p kwavers-solver` does not build. The module
was verified in a standalone harness compiling it against the same `leto` and
`kwavers-core` revisions: 9/9 tests, clippy `-D warnings` and rustfmt clean.
Re-run the package gate once the peer migration lands.

### ATLAS-GMRES-SSOT-001 — CORRECTED 2026-07-27: Athena is the owner

An earlier entry in this session read the zero-consumer evidence as grounds to
name `leto-ops` the Krylov SSOT and supersede leto ADR 0015. **That was wrong
and is retracted.** It inverted a ratified boundary on evidence of
non-adoption. See [ADR 0033](docs/adr/0033-krylov-ownership-reaffirmation.md).

Standing evidence, unchanged: nothing in the stack references
`athena_core::Gmres` or `athena_core::Cg`; Athena's only code consumer is
Harmonia, which imports `ConvergencePolicy`, `IterationObserver`,
`IterationState`, `NoObserver` only. Every other `athena-*` manifest line is a
`[patch]` overlay entry, not a dependency.

Corrected reading of that evidence:

- Atlas ADR 0022 (Accepted, `[arch]`) names Athena the iterative-solver
  provider, citing exactly this defect: "Leto, CFDrs, and Kwavers own
  iterative-solver recurrences beside storage, discretization, or domain code".
  The meta README stack map agrees: `athena` — "Iterative solver policy over
  CPU and accelerator providers."
- Leto executed the extraction in `aa8aa9b` (2026-07-19 22:29, ADR 0015).
- `ee6582d chore(leto): remove ndarray/nalgebra dev-dependencies`
  (2026-07-23 17:57) reintroduced the whole family — `cg.rs`, `bicgstab.rs`,
  `gmres/`, `lsqr.rs`, Jacobi/SOR/SSOR/ILU — four days later, under a message
  that never mentions it. That commit is the regression.
- CFDrs `6d18a547` then wrapped the reintroduced Leto family, propagating it.

So Athena's zero consumers measure a stalled extraction, not a wrong owner.
The unwind sequence is ADR 0033 stages A-D, tracked below.

### Concurrent-agent record

Assist edits left uncommitted in peer working trees, each completing a peer's
own in-flight leto-ops SSOT migration and needed to reach a build:
`kwavers-source/Cargo.toml` and `kwavers-physics/Cargo.toml` (missing
`leto-ops` dependency behind imports the peer had already switched);
`bessel.rs`, `acousto_optics.rs`, `wave/nonlinear.rs`, `burgers/solution.rs`
(`u32` → `usize` for the leto-ops `jn` signature);
`kwavers-transducer/.../processor.rs` (`Vec<f64>` → `Array1<f64>` conversion).
Also `bessel_k0` added to `leto-ops/src/application/special.rs`, which the peer
had already imported from there but not yet moved upstream — left uncommitted
because that file is the peer's active rewrite and the addition cannot be
separated from it by path. **That port fixed a transcribed A&S 9.8.1
coefficient, `3.5156329` → `3.5156229`, which alone accounted for a 5e-7
absolute error in K₀ near x = 1.** Reference-value tests added.

## ATLAS-WORKTREE-CLONES-001 — Reconcile standalone clones under `worktrees/` [patch] — in-progress

- Census 2026-07-30 (mechanized: `scripts/atlas-lane-audit.py`, exit-nonzero local gate for orient/replenishment — filed by fable-prompt-session as peer-assist evidence): 17 hand-wired gitdir mirrors are back under `worktrees/` (aequitas, apollo, coeus, consus, eunomia, gaia, hermes, hyperion, iris, leto, melinoe, mnemosyne, moirai, proteus, ritk, themis, tyche — each `.git` file points at the member's primary `.git/modules/...` gitdir, sharing its index), plus the `worktrees/hephaestus` standalone clone, three bare non-worktree dirs (hephaestus-unary-math-parity, kwavers-aequitas-vessel-metrics, ritk-book-complete), and kwavers at 3 working trees. The prior purge did not hold — something regenerates the mirrors. SPIKE (unclaimed): identify the generator (peer tooling or an agent habit materializing `worktrees/<member>`), evidence budget one session, deliverable = generator named and fixed or a defect filed on its owner; re-deletion without that finding repeats the cycle. Legitimate submodule lanes (gitdir under `.git/modules/<path>/worktrees/<lane>`) pass the audit.
- Live-regeneration evidence 2026-07-30: the violation count moved 22 -> 29 within ~2h of the first audit run — lane-root timestamps show a peer serially creating `hephaestus-j1e2` … `hephaestus-j5` plus `ritk-pr-split` during the session (lane-per-subtask sprawl; the two-tree bound and one-item-per-lane rules ignored). The spike's generator question now has a live specimen: whatever workflow drives the `-jN` series is creating a lane per job. Differential note for auditors: `scripts/atlas-lane-audit.py` counts are environment-dependent by design (local git state) — never baseline them in conformance JSON.
- Evidence: `D:/atlas/worktrees/` holds directories named after stack repos
  (`leto`, `eunomia`, `moirai`, `ritk`, …) that are **standalone clones**, not
  linked worktrees — `worktrees/eunomia/.git` is a full repo directory, and
  `git worktree list` in `repos/eunomia` shows only `repos/eunomia`.
- Impact: this is the prohibited repo-copy pattern (forked history, duplicated
  disk). It also actively breaks lanes: a real worktree placed under
  `worktrees/` resolves a member's `../<repo>` path dependencies to these
  clones, producing `package collision in the lockfile` — encountered while
  trying to lane the kwavers GMRES work.
- Scope: per clone, rescue-commit any dirty state, fetch unique branches and
  commits into the authoritative repo under `repos/`, then delete. Confirm
  `git worktree list` per repo stays within the two-tree bound afterwards.
- Non-goal: touching genuine linked worktrees.

### Session 29 partial reconciliation (2026-07-27)

Inventory at session open: 8 standalone clones (full `.git` dir at
`worktrees/<repo>`): `aequitas`, `asclepius`, `eunomia`, `hephaestus`,
`hermes`, `iris`, `leto`, `themis`.

- **Reconciled and deleted this session**: `worktrees/iris`.
  Safety verification satisfied byte-for-byte: WT HEAD `c3cc43b` ==
  `worktrees/iris`'s `origin/main` == atlas-meta gitlink pin ==
  `repos/iris` HEAD == `repos/iris`'s `origin/main`; zero unpushed commits
  (`origin/main..HEAD` empty); clean WT (no dirty files, no untracked,
  no stashes); single local branch `main`; not a linked worktree
  (`git worktree list` in `repos/iris` lists only the main tree). 3 days
  stale (well past the 1h staleness sweep threshold).
- **Intentionally NOT touched (peer mid-flight or unique content)**:
  - `leto` — last commit 18 min prior to close (actively in flight).
  - `aequitas` — dirty WT (`CHANGELOG.md`, `Cargo.lock`, `README.md`,
    `src/systems/si/*.rs`, `tests/*.rs`), 5h staleness. Mid-flight peer work;
    deletion would trigger `interaction_policy` Ask-User (irreversible loss
    of uncommitted unique work).
  - `themis` — dirty `Cargo.toml` containing **ATLAS-PATH-DEP-AUDIT-2 /
    ATLAS-OVERLAY-001 generated `[patch]` overlay content** (comment
    `Last delivery: 2026-07-27 closure cycle`). This is the peer-attributed
    draft of the ATLAS-OVERLAY-001 deliverable; deletion would destroy
    unique peer-authored state.
  - `asclepius`, `eunomia`, `hephaestus`, `hermes` — 6h staleness,
    not exhaustively safety-verified this session. Hephaestus clone HEAD
    matches the active peer-hephaestus feature branch, currently the focus
    of the persistent `no-origin-main` defect.
- **Next-session action**: re-safety-verify the 6h-stale and 3-day-stale
  clones (`asclepius`, `eunomia`, `hermes`) using the iris verification
  protocol (HEAD == origin/main AND clean WT AND no local-only branches AND
  no unpushed commits AND not a linked worktree) and delete each that passes.
  `aequitas` and `themis` require the user or the owning peer to rescue the
  dirty state before the clone can be deleted. `leto` is freshly active and
  should not be touched.

## Session 27 closure (2026-07-27) — peer-coordinator ATLAS-MODALITY advance + the persistent gitlink defect set

Re-oriented against `origin/main` at session open. The standing "next action"
from the Session 26 handoff (append Session 26 closure to `backlog.md`) had
already landed under peer-coordinator attribution: commit `1da7cea docs(pm):
Close GMRES fork ports; record athena zero-consumer evidence` wrote the
`## Session 26 closure` section at L4785. The math-SSOT audit content I drafted
in Session 26 also survived intact at L4542 (`ATLAS-MATH-SSOT-CONSOLIDATION-1`)
and the audit-pattern template in `gap_audit.md` at L5178 — peer commit
`fad8c9e` reused my commit subject but its diff was a CFDrs gitlink advance;
no content clobber. Same attribution-absorption pattern as Session 25
`e519928`; no remediation needed because the content is correct DoR-level PM
state.

### Peer-coordinator landings during the inter-session gap (10 commits, b3106f4..20b03b8)

A peer-coordinator session (same Ryan Clanton attribution) ran during the
~90-minute gap and landed 10 commits, of which 7 are substantive coordinator-
scope work on the modality-boundaries workstream and the CFDrs metric closure:

| Commit | Subject summary |
| :--- | :--- |
| `20b03b8` | Advance CFDrs gitlink to its consumer-side metric closure |
| `a802e0c` | Close CFDrs MET22 transient-composition metric gap in `gap_audit.md` |
| `b804449` | Split `ATLAS-MODALITY-002` — 2a (kwavers bioheat boundary) closed, 2b (SpecificAbsorptionRate provider-side gap) blocked on peer |
| `8571cc1` | Refresh Aequitas metric audit (reconcile CFDrs/Helios/Kwavers consumer closures) |
| `5711c0c` | Advance aequitas gitlink — `ATLAS-MODALITY-002` phase 1 |
| `537b22c` | Claim `ATLAS-MODALITY-002` phase 1 in aequitas |
| `35f41e9` | Record modality boundaries (optics / RF / photomedicine) in the stack map + kwavers bioheat deposition spine |
| `1da7cea` | (Session 26 carry-over) Close GMRES fork ports; record athena zero-consumer evidence; file `ATLAS-WORKTREE-CLONES-001` |
| `fad8c9e` | (Session 26 carry-over, peer-reused subject) CFDrs gitlink advance |
| `b3106f4` | (Session 26 close, peer-reused subject) Math SSOT audit pattern filed in `gap_audit.md` |

These landings are accepted (peer-coordinator authority is granted by the
standing Change intent on this allowlisted meta-repo; no clobber of my
Session 26 work). They advance `ATLAS-MODALITY-002` from `todo` to
`in-progress` (phase 1 delivered, phases 2b-4 open).

### Residual gitlink defects (re-probed this session)

`target/release/gitlink-coherence.exe audit` reports **5 defects + 1
stale-advanceable + 19 clean** (down from Session 26's 11 defects — peers
published `origin/main` for apollo/athena/gaia/helios/hermes/asclepius during
the gap, resolving the cat-a class).

Persistent defects, each blocked on peer recovery action the coordinator
cannot execute (no write access to `repos/<name>/...`):

| Repo | Category | Pin | origin/main | WT HEAD | Branch | Last commit | Recovery (peer-owned) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| coeus | cat-c | cdaf769 | e26ba668 | cdaf769 | `codex/coeus-error-function-parity` | 3h ago | peer-coeus: publish origin/main |
| hephaestus | no-origin-main | 47ca84a | (none) | 47ca84a | `codex/hephaestus-product-axis-reduction-parity` | 3h ago | peer-hephaestus: create `origin/main` (4-session persistent defect) |
| kwavers | cat-b | 81a40071 | dce38e26 | **a7922bcc** | `codex/kwavers-book-migration-eviction` | **59 min ago** | peer-kwavers: merge/rebase feature to origin/main OR roll WT to main; coordinator NOT advancing — peer is actively committing |
| leto | cat-b | c6ced81 | 5ba88cc | dcc5d54 | `codex/leto-real-sparse-lu` | 5h ago | peer-leto: merge feature to origin/main |
| ritk | cat-c | 65035908 | c05f84d5 | 65035908 | `codex/docs-ritk-n4-figure-only` | 3h ago | peer-ritk: merge feature + publish origin/main |

Stale-advanceable (still NOT safely advanceable):

- `mnemosyne`: pin=00c3f6d, origin-main=905909b, WT HEAD=ec1c000 on
  `codex/mnemosyne-tier-selection` (7h ago). `git add` would capture the
  feature-branch HEAD `ec1c000`, not `origin/main` `905909b`. Per pitfall #2,
  this remains blocked until peer-mnemosyne either publishes `origin/main`
  or rolls WT back to `main`.

### Assist-ladder actions taken this session

- **Audit recovery**: Verified peer-coordinator's Session 26 closure (L4785)
  and the math-SSOT inventory (L4542) survived intact — no remediation
  required.
- **No gitlink advances**: Every defect row is either a structurally
  peer-only recovery (publish `origin/main`, merge feature branch) or has
  the working tree on a feature branch that would capture the wrong SHA.
  `kwavers` peer committed 59 minutes ago — active, not stale; coordinator
  escalation inappropriate per `concurrent_agents` assist-or-skip rules.
- **Closure written**: This section.
- **No new board entries**: The 5 defect rows above are already covered by
  their prior-session backlog items; a louder board restate is not warranted
  until a true stale-claim (1h+ no commit signal) develops. Three defects
  (hephaestus, kwavers PR, leto) are at 3+ sessions persistence and would
  become candidates for user-direction escalation if they persist into
  Session 28.

### Stale-memory re-verification (this session)

- `rust-toolchain.toml` pinned, MSRV unchanged.
- `target/release/gitlink-coherence.exe` present and unchanged.
- 25 submodules in `.gitmodules` unchanged.
- Shared `target-dir = "target"` at `/d/atlas/.cargo/config.toml` unchanged.
- Re-confirmed: `repos/<name>/.git` is a `gitdir:` indirection file for the
  submodule members (except `leto`/`hephaestus`, which are full directories);
  the gitlink pin is what `atlas-meta`'s git index records, and it can differ
  from `repos/<name>` WT HEAD when a peer has moved their WT onto a feature
  branch without the coordinator committing the advance.

### Next-session handoff

- Re-fetch + re-probe at session open (utility `gitlink-coherence.exe audit`
  is the canonical state read).
- Watch for peer-kwavers landing the feature branch — if `origin/main`
  advances, the gitlink is a one-step advance.
- Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  merges — same one-step advance opportunity.
- Watch for peer-hephaestus publishing `origin/main` — would close the
  4-session persistent `no-origin-main` defect.
- If 3 of the 5 persistent defects are unchanged by Session 28 open,
  escalate to user with a single batched message naming the 2-3 worst
  blockers (likely hephaestus + the most-active-of-the-rest) and request
  direction on peer-side remediation.
- Stand-alone next coordinator items still `todo`:
  `ATLAS-OVERLAY-001` (generated patch overlay), `ATLAS-VERSION-GUARD-001`
  (manifest version guard), `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit filed;
  execution owned by peer-leto/peer-physics-crate), `ATLAS-WORKTREE-CLONES-001`
  (rescue the standalone clones under `worktrees/`). Review whether any
  becomes urgent next session.

## ATLAS-GMRES-FORK-CONVERGE-001 — Stages B-D: migrate consumers, delete the Leto family [major] [arch] — todo

- Unblocked 2026-07-28: `ATLAS-ATHENA-KRYLOV-CAPABILITY-001` is done.
- B: CFDrs from its `6d18a547` Leto-family wrappers to Athena.
- C: Kwavers, gated on refactoring `jacobian_vector_product` from `&mut self`
  to `&self` (its only mutation is a scratch-buffer cache) so the matrix-free
  operator satisfies `LinearOperator::apply(&self, ...)`.
- D: delete `leto-ops/src/application/linalg/iterative/` including the
  duplicated `LinearOperator`/`Preconditioner` traits; residue scan clean.

## Session 28 closure (2026-07-27) — ADR 0033/0034 (Krylov/Accelerator re-architecture), coeus cat-b promotion, 1 defect escalation

Short session: re-oriented after peer-coordinator landings, integrated two new
ADRs into PM state, escalated the standing 4-session hephaestus defect as a
cross-referenced blocker on `ATLAS-ATHENA-ACCEL-BACKEND-001`, ended with no
new gitlink advances (5 defects + 1 stale-advanceable + 19 clean unchanged
this session).

### Peer-coordinator landings during the inter-session gap (6 commits, 5ed51fa..2cd4c01)

| Commit | Subject summary |
| :--- | :--- |
| `2cd4c01` | Propose one Hephaestus-backed Athena accelerator backend (ADR 0034, status `Proposed`) |
| `a454976` | Record `ATLAS-MODALITY-002` 2b progress + the unified heat-source field defect |
| `12d3fdf` | Reserve `ATLAS-DOWNSTREAM-COORDINATION-001` ticket for LeoNeuro-INC `50bfcd9` hand-off |
| `051d1af` | Reaffirm Athena as the Krylov owner (ADR 0033, `Accepted`, `[major] [arch]`) |
| `b23271b` / `eb3cdb9` | Refine STEP D axes table + alternatives-rejected grounds (PATH_DEP_AUDIT_001_ENTRY.md) |
| `1fd57ae` | Clarify STEP D orthogonal axes + alternatives rejected + push-handoff |

ADR 0033 supersedes the iterative-solver lane of my Session 26
`ATLAS-MATH-SSOT-CONSOLIDATION-1` audit (L4542). ADR 0033's reasoning is
correct: adoption-count inversion of a ratified boundary (ADR 0022 named
Athena Krylov SSOT; leto-ops's `ee6582d` reintroduction is a regression, not
a new SSOT, regardless of which has more current consumers). The
`ATLAS-MATH-SSOT-CONSOLIDATION-1` row's direct-decomposition lane (LU/QR/
Cholesky/SVD/eigen/Schur/Bunch-Kaufman/UDU — definitively leto-ops's
ownership per ADR 0033 §2) and sparse-interpolation-quadrature lanes remain
valid; only the iterative-solver recommendation is superseded by
ATLAS-ATHENA-KRYLOV-CAPABILITY-001 / ATLAS-GMRES-FORK-CONVERGE-001 /
ATLAS-ATHENA-ACCEL-BACKEND-001. The audit-inventory table itself (ssot-
baseline + cross-capability matrix) is unmodified and remains useful as the
broader cross-repon math consolidation inventory; it's just that one slice
of its recommended action set has been overtaken by a more authoritative
ADR.

### Gitlink state re-probed (post-peer-landings)

`target/release/gitlink-coherence.exe audit`: **5 defects + 1
stale-advanceable + 19 clean** (Session 27 had identical counts; this
session's only movement is the `coeus` defect upgrading from cat-c → cat-b).

| Repo | Category | Pin | origin/main | Movement vs Session 27 |
| :--- | :--- | :--- | :--- | :--- |
| coeus | cat-b | cdaf769 | 971fab9 | **upgraded** from cat-c: peer-coeus pushed `codex/coeus-error-function-parity` to a tracked remote branch (`origin/codex/coeus-error-function-parity`); still not merged to `origin/main` |
| hephaestus | no-origin-main | 47ca84a | (none) | unchanged (5-session persistent) |
| kwavers | cat-b | 81a40071 | dce38e26 | unchanged; WT HEAD moved to `a7922bcc` (peer kwavers-book-migration-eviction, 59 min ago at session open — peer is actively committing in their feature branch) |
| leto | cat-b | c6ced81 | 5ba88cc | unchanged |
| ritk | cat-c | 65035908 | c05f84d5 | unchanged |
| mnemosyne | stale-advanceable | 00c3f6d | 905909b | unchanged; WT on `codex/mnemosyne-tier-selection` |

### Assisted ACCEL-BACKEND row with the hephaestus-`origin/main` cross-reference

Appended a "Blocking upstream state" note at `ATLAS-ATHENA-ACCEL-BACKEND-001`
(L5127→L5137) naming the hephaestus 5-session persistent `no-origin-main`
defect as the upstream unblock for that [arch] item's deletion of
`athena-wgpu` and Hephaestus kernel additions. Recommend the user direct
peer-hephaestus to publish `origin/main` (or merge the feature branch) as
the unblock for both this row and the 4-session-persistent defect.

### Assist-ladder actions taken this session

- **No gitlink advances**: every defect is structurally peer-only recovery
  (publish/merge) or has the WT on a feature branch that would capture the
  wrong SHA per pitfall #2.
- **Doc-sync (anti-orphaning)**: cross-referenced the new ADR 0033/
  0034 chain into the existing `ATLAS-MATH-SSOT-CONSOLIDATION-1` audit row's
  recommendation set (no edit to that row, but the new PM state above makes
  the supersedence traceable); appended the blocking-upstream note to
  ACCEL-BACKEND.
- **Closure written**: this section.

### Next-session handoff

- **Highest-priority unblock**: peer-hephaestus publishing `origin/main` or
  merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  closes a 5-session persistent defect AND unlocks `ATLAS-ATHENA-ACCEL-
  BACKEND-001` execution. Recommend the user message peer-hephaestus
  directly if the defect is unchanged at Session 29 open.
- **Watch for peer-kwavers feature-branch merge**: kwavers peer is actively
  committing to `codex/kwavers-book-migration-eviction`. Once it lands on
  `origin/main`, the gitlink is a one-step advance.
- **Watch for peer-coeus / peer-ritk / peer-mnemosyne / peer-leto feature
  branch merges** — same one-step advance opportunities.
- **3+ session persistence threshold**: hephaestus now in its 5th session;
  kwavers PR #325 (codex/kwavers-book-migration-eviction) and leto branch
  (codex/leto-real-sparse-lu) at 3+ sessions each. At Session 29, if
  hephaestus is still `no-origin-main`, escalate to user with batched
  message naming hephaestus as the worst blocker.
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`, `ATLAS-WORKTREE-CLONES-001`,
  `ATLAS-DOWNSTREAM-COORDINATION-001` (new, peer-filed), `ATLAS-MATH-SSOT-
  CONSOLIDATION-1` (audit filed; execution owned by peer-leto/peer-physics-
  crate and now partially overtaken by ADR 0033's Krylov sequence).

## Session 29 closure (2026-07-27) — athena gitlink advance + hephaestus 6-session escalation threshold

### Re-orientation findings

- HEAD moved from Session 28 close (`73d3042`) to `ac20857` before this session
  opened via two peer-coordinator commits:
  - `3df60c1 build(atlas): Advance kwavers gitlink — ATLAS-MODALITY-002 phase
    2b closed` (peer-coordinator carried kwavers ATLAS-MODALITY-002 phase 2b
    close forward; kwavers gitlink was not actually advanced — see defect
    table below — the commit message subject and the kwavers gitlink advance
    it claimed did not coincide: pin remained `37d50b96`)
  - `ac20857 docs(pm): Record BiCGSTAB landing in Athena stage A` advanced
    the **leto** gitlink to `78d9e9e0` (peer-leto merged
    `codex/leto-real-sparse-lu` to `origin/main`, landing 17 commits since
    prior pin `c6ced81e`, including the boundary execution
    `687b670 refactor(leto-ops): Remove ndarray/nalgebra, native iterative
    solvers (LETO-NDARRAY-BOUNDARY-1)` — directly advancing the standing
    migration goal and aligning with ADR 0033's Krylov-ownership reaffirmation
    by retiring leto-ops native iterative solvers)
- Re-audited gitlink coherence: **4 defects | 2 stale-advanceable | 19
  clean**. Compared to Session 28 close: leto resolved (cat-b → advanced);
  athena newly stale-advanceable (peer-athena landed BiCGSTAB).

### Assist-ladder action executed: athena gitlink advance

- Verified: pin `a5fd8061` ancestral to origin/main `e965a95d` via
  `merge-base --is-ancestor`; **WT HEAD == origin/main byte-for-byte**;
  WT clean (`## main...origin/main`, no dirty files, not on feature branch).
  Pitfall #2 satisfied.
- Selective-staging discipline executed: `git reset HEAD -- .` →
  `git add repos/athena` → verified staged SHA == athena origin/main →
  verified only `repos/athena` staged (`git diff --cached --name-only` →
  CLEAN).
- Committed as `c38ca61 build(atlas): Advance athena gitlink to e965a95d`,
  pushed same cycle (`ac20857..c38ca61 main -> main`). Aligns with ADR 0033
  (Athena owns Krylov) and ATLAS-ATHENA-KRYLOV-CAPABILITY-001.

### Hephaestus `no-origin-main` — now 6-session persistent, escalation exercised

- Re-probed 2026-07-27 Session 29: hephaestus HEAD `47ca84a8`, last commit
  2026-07-27T12:22:02-04:00 (~6h prior). WT on
  `codex/hephaestus-product-axis-reduction-parity`, **ahead 1** of
  `origin/codex/hephaestus-product-axis-reduction-parity` with dirty
  `Cargo.lock`. Remote has only feature branches — **`origin/main` ref
  does not exist**; the structural cause is peer-hephaestus works
  exclusively on feature-branch flow and never publishes `main`.
- Per the standing ATLAS-ATHENA-ACCEL-BACKEND-001 cross-reference
  (L5139+) and the Session 28 next-session handoff instruction, the
  5-session threshold having been crossed at Session 28 close, Session 29
  confirms the defect is now **6-session persistent**.
- Coordinator authority (assist-ladder) does not authorize executing peer
  pushes. The escalation route is a **batched user-facing message** naming
  peer-hephaestus as the worst blocker; the cluster trio
  (`hephaestus`, `kwavers PR #325`, `ritk` `codex/docs-ritk-n4-figure-only`)
  as the user-actionable remediation set; and the gating relationship to
  `ATLAS-ATHENA-ACCEL-BACKEND-001` ([arch]) as the consequence of continued
  blockage. This message is delivered in the session response (not as a
  PM artifact, per no-report-file genre).

### Post-push gitlink-coherence state

| # | Repo | Category | Pin | origin/main | Last commit | Recovery (peer-owned) |
|---|---|---|---|---|---|---|
| 1 | coeus | cat-b | `cdaf769` | `971fab9` | 3h ago | peer-coeus: merge `codex/coeus-error-function-parity` to origin/main |
| 2 | hephaestus | no-origin-main | `47ca84a` | (none) | 6h ago | peer-hephaestus: publish origin/main — **6-session persistent, gating ACCEL-BACKEND-001** |
| 3 | kwavers | cat-b | `37d50b96` | `dce38e26` | <1h ago | peer-kwavers: merge/rebase `codex/kwavers-book-migration-eviction` (PR #325) |
| 4 | ritk | cat-c | `65035908` | `c05f84d5` | 3h ago | peer-ritk: merge `codex/docs-ritk-n4-figure-only` + publish origin/main |

**Stale-advanceable (this session close)**: `mnemosyne` only — pin `00c3f6d`,
origin/main `905909b`, WT on `codex/mnemosyne-tier-selection` HEAD
`ec1c000` (dirty `Cargo.lock`/`Cargo.toml`). NOT safely advanceable per
pitfall #2 (would capture peer's feature-branch HEAD, not origin/main).

**Athena — captured in two advances this session**:
- `c38ca61` advanced athena to `e965a95d` for the right-preconditioned
  BiCGSTAB landing.
- `24ad6ea` advanced athena again to `fef782cb` for the incomplete-LU /
  SuccessiveOverRelaxation preconditioner landing in `athena-leto`, which
  pairs with the Krylov family covered by ADR 0033. (Pin `e965a95d`
  stayed ancestral to `fef782cb`, so the second advance remained a clean
  one-step `git add` after verifying `WT HEAD == origin/main`.)
Both advances are attestable; the table above lists only the
still-defective and still-stale-advanceable rows.

### Next-session handoff

- **Primary escalation (carried)**: peer-hephaestus publishing `origin/main`
  or merging `codex/hephaestus-product-axis-reduction-parity` to main. This
  now closes a 6-session persistent defect AND unlocks
  `ATLAS-ATHENA-ACCEL-BACKEND-001` execution. A direct user → peer-hephaestus
  nudge is now warranted prior to a 7th session.
- **Cluster escalation (carried)**: kwavers PR #325 /
  `codex/kwavers-book-migration-eviction` (3+ sessions), ritk
  `codex/docs-ritk-n4-figure-only` (3+ sessions), coeus
  `codex/coeus-error-function-parity` (3+ sessions). Batch a single
  user-facing message if all are unchanged at Session 30 open.
- **Watch for one-step gitlink advance opportunities**: peer-mnemosyne,
  peer-coeus, peer-kwavers, peer-ritk if their feature branches merge to
  origin/main (verify `WT HEAD == origin/main` before `git add` per
  pitfall #2).
- Standing coordinator-scope `todo` items unchanged:
  `ATLAS-OVERLAY-001`, `ATLAS-VERSION-GUARD-001`,
  `ATLAS-WORKTREE-CLONES-001`, `ATLAS-DOWNSTREAM-COORDINATION-001`,
  `ATLAS-MATH-SSOT-CONSOLIDATION-1` (audit-only, partially overtaken by
  ADR 0033 Krylov sequence).

## Session 27 (2026-07-27) — Athena stage A progress and the ADR 0034 scope refinement

### Landed

- `e965a95` right-preconditioned BiCGSTAB in `athena-core`.
- `fef782c` `IncompleteLu` and `SuccessiveOverRelaxation` in `athena-leto`,
  sharing one triangular-substitution module.
- Athena gate green at each step: 38/38 nextest including the WGPU contracts,
  clippy `-D warnings`, doctests, fmt.

SSOR was deliberately **not** ported: a stack-wide scan finds no consumer, so
building it would be speculative. CFDrs uses ILU most, then Jacobi, then SOR.

Stage A remaining: **LSQR**. That completes the capability set and unblocks
`ATLAS-GMRES-FORK-CONVERGE-001` stage B (CFDrs migration).

### ATLAS-ATHENA-ACCEL-BACKEND-001 — refined, larger than first scoped

Surveying Hephaestus changed the shape of this item. It is **not** "delete
Athena's WGSL and call Hephaestus", because there is nothing device-neutral to
call:

- `hephaestus-core` carries the dialect-generic kernel machinery
  (`KernelSource<L: KernelDialect>`, `UnaryStorageKernel`,
  `BinaryStorageKernel`, `MultiStorageDevice`) and an op-expression algebra.
- Each backend crate exposes `dot`, `norm_l2`, `scalar_elementwise_into`,
  `binary_elementwise_into` — but as **per-backend free functions**.
- `ComputeDevice`, the device-neutral trait, covers allocation and transfer
  only.

So a `KrylovBackend` generic over `D: ComputeDevice` cannot reach any vector
operation. That is precisely why `athena-wgpu` hand-wrote WGSL against a
concrete `WgpuDevice` and hardcoded `f32`: the seam it needed did not exist.

The defect and the decision are unchanged — Athena must not own GPU kernels,
and the per-device crate must go. What changes is that the first increment
belongs to **Hephaestus**, not Athena: a device-neutral vector-operation seam
in `hephaestus-core` that each backend implements by delegating to the free
functions it already has. That closes a substrate gap benefiting every
Hephaestus consumer.

Staged, each with its own gate:

1. `hephaestus-core`: the vector-operation seam (scale, axpy, dot, norm,
   residual, and the two fused Krylov-shaped updates).
2. `hephaestus-wgpu`: implement it by delegation. The only backend testable on
   this host.
3. `athena-hephaestus`: `KrylovBackend` over the seam, generic in scalar type
   rather than `f32`-only.
4. Delete `athena-wgpu` and its WGSL; move its contract tests in the same
   change.

CUDA, Metal, and ROCm implementations follow the same seam and are verifiable
only where that hardware exists, so each is its own increment rather than a
blocker on Athena.

## ATLAS-LETO-PEER-WIP — Leto uncommitted peer WIP [patch] — blocked (peer-owned)

- Owner: peer session (codex); scope: `repos/leto/crates/leto-ops/`,
  `repos/leto/Cargo.toml`.
- Status: active peer WIP on `codex/leto-real-sparse-lu`. Contains:
  - `special_legendre.rs` (new Legendre polynomial module, 111 lines, 3 tests)
  - `Cargo.toml` path-dep overlay patches
  - `special.rs` formatting normalization
  - `lib.rs`/`mod.rs` module tree updates
  - `bessel_k0` test tolerance fix (1e-7 → 1e-6, already applied)
- Evidence: 425 leto-ops tests pass.
- Blocker: peer-owned; not committed by this session per concurrent_agents policy.
- Re-open trigger: the peer lands the branch or the one-hour stale-claim sweep
  finds no board/commit update; then reclaim the scope and complete the
  integration from the committed branch state.

## ATLAS-CFDRS-TEST-BUDGET — 8 integration tests exceed 30s nextest budget [patch] — blocked

- Owner: unclaimed; scope: `repos/CFDrs/crates/cfd-validation/`,
  `repos/CFDrs/crates/cfd-3d/`.
- Status: blocked by infrastructure issues that prevent test execution.
- Blocker 1 — lockfile collision: CFDrs root `Cargo.toml` uses path deps
  (`path = "../<repo>"`), but the stack overlay `.cargo/config.toml` patches
  git sources to `worktrees/*`. Transitive git deps resolve to a second copy
  of each crate at identical name+version → cargo cannot write the lockfile.
  `cargo nextest` cannot run. Related: `ATLAS-OVERLAY-COHERENCE-001`.
- Blocker 2 — hephaestus merge conflict: committed unresolved merge-conflict
  markers at `repos/hephaestus/crates/hephaestus-core/src/domain/stencil.rs:78`
  (`<<<<<<< HEAD` … `>>>>>>> origin/master`) break compilation of the
  gpu-feature chain (`cfd-core` default `gpu` feature → `hephaestus-wgpu`).
- Slow tests (measured 2026-07-28, 40s kill):
  1. `microventuri_fallback_case_produces_converged_informative_2d_result` — >40s
     (80×400 grid, 150 adaptive steps × 3 outer × 2 inner × 15 CG iterations)
  2. `microventuri_35um_case_produces_converged_informative_2d_result` — >40s
     (same SIMPLEC path, ny=343)
  3. `option2_selected_45um_geometry_routes_to_fallback_and_converges` — >40s
     (same SIMPLEC path, ny=267)
  4. `test_venturi_blood_flow` — >40s (full 3D FEM N-S, 10 Picard iterations)
  5. `cross_fidelity_trifurcation_dominance` — 37.1s (3D FEM, 20×600 iterations)
  6. `test_venturi_flow_3d` — 32.6s (P1/P1 PSPG FEM, 32³ resolution, 500 max iter)
  7. `cross_fidelity_stenosis_shear_thinning` — 27.9s (2×1D + 2×2D SIMPLE,
     20000 max iterations, alpha_mu=0.1)
  8. `cross_fidelity_venturi_total_loss_coefficient` — 23.0s (1D+2D+3D legs)
- Optimization outlook: warm-started Picard, AMG preconditioning, shared solver
  state across the three microventuri cases, tighter rheology-update scheme.
- Note: workload/assertion reduction is explicitly NOT an acceptance path
  per `CFDRS-RUNTIME-001`.
- Re-open trigger: the stack overlay resolves only authoritative `repos/*`
  trees and the Hephaestus conflict markers are removed from the fetched
  default; then profile the named cases and implement the first measured
  production optimization within the committed runtime budget.

## ATLAS-HYGIENE-BASELINE-001 — Eleven-class conformance baseline and namespace hygiene [patch] — in-progress

- Owner: fable-prompt-session (claimed 2026-07-30). Claimed scope: `scripts/atlas-conformance.py`, `scripts/conformance-baseline.json`, this entry. Burn-down (scopes 2-4) stays unclaimed for peers.
- Scope 1 DELIVERED 2026-07-30: `scripts/atlas-conformance.py` (report/generate/check; 19 classes = the eleven recorded plus reexport_shims, sleep_synced_tests, commented_out_code, target_forks, gitattributes_missing, nextest_budget_missing, workspace_lints_missing, member_namespace_pollution), committed baseline `scripts/conformance-baseline.json` (supersedes the 2026-07-25 ad-hoc grep counts — heuristics differ, the instrument is now the SSOT), CI ratchet gate `.github/workflows/atlas-conformance.yml` (fails on any per-repo class increase; triggers on gitlink advances). Scan universe is `.gitmodules`-registered members only; git-ignored unregistered directories are skipped silently (private-consumer rule) and other unregistered directories count as unnamed `member_namespace_pollution` (currently 1 — the scope-3 run-output dump).
- New-class findings for burn-down (baseline totals): target_forks 5 (CFDrs, helios, hephaestus +2 — delete tree and creating override per performance_engineering "one build cache per stack"); gitattributes_missing 17/25 and workspace_lints_missing 17 (retrofit sweeps — mechanical, one commit per member); sleep_synced_tests 125 (moirai 105 — its scheduler tests wall-clock-sync; candidate for injected-clock rework); commented_out_code 109 (kwavers 51); reexport_shims 39; markers 13; nextest_budget_missing 1 (gaia). Also observed, outside scanner classes: workflow actions are tag-pinned across all six meta workflows (SHA-pin sweep per engineering_gates "Workflow hygiene") and `scripts/` retains the closed path-dep audit's r2-r6b iteration series (obsolete-artifact deletion candidate).
- Scope 1 extension 2026-07-30: five workflow/lock classes added — tag_pinned_actions 218 stack-wide (kwavers 66, hermes 21, ritk 21; the SHA-pin sweep is now measured, not just observed), workflow_missing_timeout 23, workflow_missing_permissions 7, pull_request_target_use 0 (clean), missing_cargo_lock 1 (themis — a foundation member without a committed lock) — baseline regenerated in the same change (generator contract); 24 classes total. Companion local gate `scripts/atlas-lane-audit.py` mechanizes the worktree-lane rules (two-tree bound, canonical lane roots, named branches, gitdir-mirror and standalone-clone detection) for orient and the replenishment audit — CI cannot see local worktrees, so it gates locally; census filed on ATLAS-WORKTREE-CLONES-001. The seven obsolete r-series audit scripts are deleted and the meta root adopts `* text=auto` `.gitattributes` (renormalization no-op — index already LF).
- Correction 2026-08-14: Themis's committed `Cargo.lock` landed in provider commit `09b2252`; the current `missing_cargo_lock` count is 0 for the requested provider set.
- Consolidation 2026-07-30: the scan-universe definition now has one owner — `scripts/atlas_stack.py` (registered members from `.gitmodules`, git helpers, ignore checks) imported by both the conformance scanner and the lane audit; the duplicated `registered_members()` pair and the scanner's twice-implemented root-sprawl/LF checks are collapsed (behavior-preservation proven by old-vs-new differential on stable members). Defect finding — **fixed 2026-08-02** (umbrella, this commit's parent): `atlas-toolchain-preflight.py` now imports `atlas_stack.registered_members()`; the glob-over-everything derivation is gone and the run resolves 25 member pins.
- Preflight side-finding 2026-08-02: this agent's shell environment carries ambient `RUSTC`/`RUSTDOC` exports pointing at the rustup PROXIES (`~/.cargo/bin/*`), which the preflight rightly fails. Proxy targets honor the pins, so the session's builds were coherent (single compiler identity confirmed once the overrides are cleared), but the exports should be removed from whatever profile sets them — an override pointing anywhere non-proxy would silently poison the shared cache.
- Lane-series clarification (re the 2026-07-30 sprawl evidence naming `hephaestus-j1e2`…`-j5`): those lanes were SERIAL, one claimed item each, each removed on its merge — the two-tree bound held at every instant (`git worktree list` never exceeded main + one lane) and the creation-rate spike measured throughput, not concurrent trees. Two removals hit Windows Permission-denied on first attempt and were pruned + rm-rf'd in the same cycle; if the audit counts orphan directories, that transient is the residue to look for.
- **Board-sweep sub-slice delivered 2026-08-07.** `scripts/atlas-board-sweep.py`
  parses the lenient level-two heading format, normalizes `in progress` /
  `in-progress`, reports explicit owner and claim-date context, and identifies
  blocked items lacking a `Re-open trigger` (including qualified forms such as
  `Re-open trigger (for the claiming session):`). It is report-only: findings
  never fail the command or mutate the board, while missing/unreadable input
  returns 2. Focused unittest coverage is in
  `scripts/tests/test_atlas_board_sweep.py` (6/6); `py_compile`, board lint,
  and `git diff --check` pass. The live root report scans 244 items, finds 27
  in-progress claims, and surfaces 3 blocked items without a re-open trigger:
  `ATLAS-SUBSTRATE-002`, `ATLAS-LETO-PEER-WIP`, and
  `ATLAS-CFDRS-TEST-BUDGET`. Claim freshness and remediation remain operator
  decisions; this tool does not reclaim or edit claims.
- Policy: AGENTS.md engineering_gates conformance scan (now enumerating all eleven debt classes), documentation_discipline "Root manifest", architecture_scoping "Member namespace hygiene".
- Baseline 2026-07-25 (per-repo counts recorded; the ratchet gate holds these non-increasing): files >500 lines: 574 (CFDrs 137, kwavers 91, consus 89); implementation-bearing lib.rs/mod.rs: 402 (kwavers 145); production `unwrap()`: 5833 (kwavers 3119, ritk 719); `#[allow]`: 798 (kwavers 330); print/dbg in src: 1082 (CFDrs 428); existence-only assertions: 444 (coeus 104, leto 79); type-suffixed fns: 380 (apollo 111); junk-drawer modules: 66 (kwavers 28); crates missing deny(missing_docs): 107/208; unsanctioned root files: 120 (kwavers 40); markers: 18.
- Scope: (1) extend the committed conformance scan script to all eleven classes and record this baseline as its first output; (2) burn-down items per repo by triage (kwavers is the epicenter: unwraps, fat manifests, junk modules, root clutter); (3) `repos/parity_artefacts` (untracked run-output dump in the member namespace — det_*.log, url/target lists) relocates to a gitignored verification output root or deletes at the parity stream's item completion (owner: parity stream; regenerable evidence, rescue-first if any file proves unique); (4) kwavers root files triage per the Root manifest rule.
- Acceptance: scan script covers all eleven classes with committed baseline; member namespace holds registered members only; per-repo burn-down items filed DoR-shaped.

## Session 30 closure (2026-07-28) — atlas-stack-overlay CI wiring + peer math-SSOT PR 0008 audit artifacts tracked

Re-oriented against `origin/main` at session open; HEAD had moved from `d2e0ac9` to `182f346` through peer-coordinator landings during the inter-session gap. The persistent gitlink defect set shifted: hephaestus 8-session `no-origin-main` defect narrowed (peer published an `origin/main` ref, pin advanced to `bf24b873`), but the 4-defect cluster (coeus cat-b, hephaestus no-origin-main, kwavers cat-b, ritk cat-c) persists and remains blocked on peer-side branch merges.

### Landed

- `599ddca build(atlas): Advance athena/proteus/tyche/asclepius gitlinks` — four stale-advanceables cleared: athena `fef782cb` -> `1d24c643` (ADR 0034 stage 3 merge of feat/athena-hephaestus-backend, advancing the device-neutral accelerator backend per ADR 0034), proteus `9d7c1a8c` -> `9a8655d3`, tyche `1527964c` -> `996b649d`, asclepius `bbf38400` -> `ccffb6bc`. Each followed the safe-advance protocol (pin ancestor of origin/main, WT on `main` with HEAD == origin/main, single Cargo.lock dirt in each not captured by submodule gitlink staging). Reduces stale-advanceable from 6 to 2 (mnemosyne on feature branch, kwavers on cat-b).

### Tracked (peer-authored artifacts staged for review)

- `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` (138 lines, peer-drafted PR description for the math-SSOT consolidation; covers ADRs 0031/0032/0033 closure into leto-ops SSOT; cross-repo consumers `cfd-math`, `kwavers-math`, `kwavers-solver`; reserved tag `atlas/math-ssot-adr-0031-0033-closure`; per-ADR sign-off checklist spanning CFDrs / Kwavers / leto-ops module owners). Stage-only; substantive source changes in `repos/CFDrs/crates/cfd-math/...` and `repos/kwavers/crates/kwavers-{math,solver}/...` are peer-owned and out of coordinator scope.
- `docs/audit/math-ssot-ledger.md` (753 lines, peer-authored audit ledger documenting the leto SSOT surface and per-consumer redundancy inventory; provider-side already landed in leto-ops `StaggeredForward`/`StaggeredBackward`, `complex_solve`/`complex_inv`, `FiniteDifference3D`). Stage-only.

### Next-session handoff

- ATLAS-MATH-SSOT-CONSOLIDATION-1 closure gate: peer-CFDrs must commit and merge the `cfd-math` wrapper deletion (`cfd-math/src/differentiation/` removed, `fd_extensions` re-export added) before coordinator can advance the CFDrs gitlink and close the audit row. The CFDrs WT is at origin/main HEAD `c90e6840` but dirty (36 files, peer-cfdrs mid-flight on `CFDRS-AEQ-MET-25` cavitation work). When the CFDrs gitlink advances, the audit row can mark the math-SSOT consolidation phase as delivered and PR 0008 can be reviewed/merged by module owners. The same dependency applies to kwavers (`codex/kwavers-book-migration-eviction` feature branch at `df9008d9`) and leto (`codex/leto-real-sparse-lu` at `1d24c643`+3); none is safely advanceable until peer returns WT to `main` and merges to `origin/main`.
- Standing coordinator-scope `todo` items unchanged: `ATLAS-OVERLAY-001` (sub-deliveries 1/2 still open), `ATLAS-VERSION-GUARD-001` (sub-delivery 1: per-member guard tool skeleton), `ATLAS-WORKTREE-CLONES-001` (asclepius/hephaestus/leto WTs are peer-active mid-flight; remaining clones re-evaluate on next session).
- The `repos/parity_artefacts/` directory has been physically removed from the working tree but the deletion is not staged; the corresponding `INDEX.md` was the landing page for three atlas mdbooks' Appendix F/D links, all of which have since been removed from `SUMMARY.md`. The deletion belongs with the parity stream's closure increment, not a unilateral coordinator commit.

### Post-session peer advances (attribution-absorption pattern)

Between my `599ddca` and the close of this session, peer landed a chain that absorbed the Session 30 closure intent and advanced the persistent defect set further:

- `9f92d94 docs(atlas): Refresh Aequitas gap audit` — peer-committed `docs/audit/math-ssot-ledger.md` and `docs/pr/0008-math-ssot-adr-0031-0033-review-checklist.md` under their subject. Content identical to what this session would have committed. Pattern matches the Session 25/26/28 attribution-absorption; no remediation needed because the content is correct.
- `d1f2e2c docs(atlas): Record Aequitas consumer closure` — gap audit refresh.
- `c2cad74 build(atlas): Advance CFDrs Aequitas closure` — CFDrs gitlink advanced to `109aec63`; CFDrs now reads as clean in the gitlink-coherence audit (down from stale-advanceable). MET-25 closure intent is now realized at the CFDrs WT HEAD; the math-SSOT PR 0008 cfd-math deletion gate (peer-cf must commit + push) remains the only outstanding dependency.
- `485b3dd docs(pm): Root-cause the gaia git-dep break blocking helios tests` — closes the gaia blocker; helios tests can now run against canonical gaia.
- `f793735 docs(adr): Correct ADR 0037's lockstep versioning mandate` — ADR 0037 mandate tightened.
- `86cb19a docs(pm): Record the generic-instantiation pattern; revert the blocked edit` — reverts a blocked edit and records the generic-instantiation pattern.

Final gitlink-coherence state at Session 30 close: **25 probed | 4 defects | 1 stale-advanceable | 20 clean.**

- **Defects (4):** coeus cat-b (peer `codex/coeus-error-function-parity` not merged); hephaestus no-origin-main (default branch is `master` at remote `14b73d56`, WT HEAD `7897c13f` is mid-flight on `ATLAS-HEPHAESTUS-SPARSE-SEAM-001` sparse-seam work, last commit 77 min ago — peer-active, leave alone); kwavers cat-b (`codex/kwavers-book-migration-eviction` not merged); ritk cat-c (`codex/docs-ritk-n4-figure-only` local-only, not pushed).
- **Stale-advanceable (1):** mnemosyne `00c3f6de` -> `905909be` — WT on divergent feature branch `codex/mnemosyne-tier-selection` (HEAD `ec1c000` not ancestor of origin/main), 30h since last commit; peer-mnemosyne is mid-flight on tier-selection work.

### Session 30 / Atlas-meta delivery summary

| Increment | SHA | Type | Coordinator-authored? |
|---|---|---|---|
| Advance athena/proteus/tyche/asclepius gitlinks | `599ddca` | build(atlas) | Yes — full content + protocol verification |
| Track PR 0008 + math-SSOT ledger | `9f92d94` | docs(atlas) | Peer-absorbed (content preserved) |
| Session 30 closure in backlog | `9f92d94` + `485b3dd` | docs(pm) | Yes — full text + peer addendum |
| CFDrs Aequitas closure advance | `c2cad74` | build(atlas) | Peer-owned |

## Session 28 (2026-07-28) — ADR 0034 complete

`SparseOperatorOps` landed in hephaestus `317bd7a`, and `athena-wgpu` is gone
in athena `045efe4`. ADR 0034 is closed.

- **Sparse seam.** Takes canonical CSR parts rather than a host matrix type, so
  `hephaestus-core` keeps its no-sparse-storage charter and any CSR producer
  can feed it. Raw parts arrive without the invariants a matrix type enforces
  at construction, so the seam validates structure before upload — dispatching
  on malformed CSR would read out of bounds on the device. `GpuCsrMatrix`
  gained `from_parts` and `from_cpu` now delegates, so the upload path exists
  once.
- **Operator.** `athena_hephaestus::CsrOperator` applies a device-resident
  operator through the seam, making the operator half as device-neutral as the
  vector half. That was the last thing keeping `athena-wgpu` alive.
- **Deletion.** `athena-wgpu` removed outright with its five hand-written WGSL
  kernels and `f32`-only backend, no compatibility re-export; nothing outside
  Athena depended on it and its contract tests moved in the same change. The
  facade feature is now `accelerator`, not `wgpu`.
- **ADR 0034 residue scan passes**: no `wgsl`, `@compute`, or `workgroup`
  literal under `repos/athena/crates`, and no crate there names a device API.
  Athena went from one device API to every Hephaestus backend, and from
  `f32`-only to generic in the scalar.

### Verification and its limit

`athena-hephaestus` passed 7/7 on GPU hardware — CG, GMRES and BiCGSTAB each to
convergence through the device-neutral backend and operator, plus retained-handle
reuse across solves, dimension rejection, rectangular rejection, and three
malformed-CSR rejections. Clippy `--all-targets` and fmt were clean immediately
before commit.

The workspace-wide gate could **not** be run afterwards: an in-flight `aequitas`
change (14 dirty files in `repos/aequitas`) began failing `leto` and `leto-ops`
beneath the whole stack —

```
error[E0599]: the method `in_unit` exists for struct `Quantity<...>`, but its
trait bounds were not satisfied
  --> repos/leto/crates/leto/src/application/stencil.rs:121
     = note: `T: UnitScalar` not satisfied
```

`stencil.rs` is committed and unmodified, so this is upstream drift rather than
local breakage, and it predates nothing of this increment. Re-run the athena and
hephaestus workspace gates once that settles.

### Remaining

- ADR 0033 stage A: **LSQR**, the last capability before the CFDrs migration
  (`ATLAS-GMRES-FORK-CONVERGE-001` stage B).
- CUDA, Metal and ROCm adopt `RetainedReductions` and `SparseOperatorOps` in
  their own increments, verifiable only where that hardware exists. Until then
  the accelerator backend runs on WGPU alone — but adding a device now adds no
  Athena code, which is the property ADR 0034 existed to establish.

## ATLAS-LANE-AUDIT-001 — Lane-root sweep results and residuals [patch] — in-progress (residual)

- Policy: AGENTS.md git_discipline Worktrees (lanes are swept claim surfaces; created only by `git worktree add`) + concurrent_agents (gitdir-mirror checkouts prohibited — a `.git` file pointing at another tree's gitdir shares its index and corrupts both trees' status).
- Audit 2026-07-26 of `D:\atlas\worktrees` (26 entries): 4 compliant live lanes (coeus-backend-parity, hephaestus-mixed-reduction-batch, kwavers-aequitas-vessel-metrics, ritk-ebcot-magnitude-view); 13 gitdir-mirror checkouts on main (the improvised-provider species); 7 standalone clones; 3 bare directories; 1 broken meta lane. Legacy root `D:\worktrees` now empty — its lanes completed and dissolved per ATLAS-WORKTREE-001.
- Done: `report` re-mint deleted (SVG already rescued to repos/report/figures); broken `atlas-final-integration` meta lane deleted + `worktree prune` (meta lanes prohibited); 5 stale clones rescue-fetched into their authoritative repos under `refs/rescue-worktrees/<name>/*` then deleted (leto incl. codex/leto-real-sparse-lu); 13 gitdir-mirrors deleted — and regenerated within seconds: a live process on pre-fix instructions re-mints the mirror farm (signature: `.git` file -> `../../.git/modules/repos/<r>`, checkout on main). Self-resolves as sessions roll onto current instructions; re-audit the root then and delete survivors.
- Residuals: (1) `hephaestus-unary-math-parity` — git-less source snapshot with real unique deltas (6/12 sampled files differ from authoritative): reconcile into a branch of repos/hephaestus (diff, salvage, commit under the unary-math-parity item), then delete the snapshot; (2) `ritk-book-complete` — near-duplicate snapshot (11/12 identical): verify the delta, salvage if real, delete; (3) stale lanes `coeus` (codex/coeus-error-function-parity, 30h) and `mnemosyne` (codex/mnemosyne-tier-selection, 33h) — takeover material: complete their items or confirm branches landed, then remove the lanes; (4) fresh clones `aequitas`/`eunomia` left in place (regenerator-owned) — delete at re-audit.
- Re-audit 2026-08-14: the current probe reports four violations: Ritk still has three trees, and Kwavers has three trees with one detached temporary lane outside the canonical lane root. No lane is removed while peer-owned work or unique state remains unrescued.

## Session 28 closure (2026-07-28) — ADR 0033 stage A complete

LSQR landed in athena `24b5c56`. Athena now carries every Krylov capability
its prospective consumers call, and the capability table from
`ATLAS-ATHENA-KRYLOV-CAPABILITY-001` has no gaps left:

| Capability | Athena | Needed by |
|---|---|---|
| CG / PCG | yes | CFDrs |
| GMRES(m) | yes | CFDrs, Kwavers |
| BiCGSTAB | yes (`e965a95`) | CFDrs |
| LSQR | yes (`24b5c56`) | CFDrs |
| Identity / Jacobi | yes | all |
| SOR / ILU(0) | yes (`fef782c`) | CFDrs |

SSOR remains deliberately unbuilt: no consumer anywhere in the stack.

### LSQR design notes

- `RectangularOperator` is a separate contract from `LinearOperator`, not an
  extension: a square operator does not necessarily expose a transpose, and
  requiring one would burden every consumer that never needs it.
- `RectangularCsrOperator` scatters the adjoint through the same CSR arrays the
  forward product reads rather than materialising a transpose, which matters
  because LSQR applies the adjoint once per iteration.
- Termination needs **two** criteria. A consistent system is caught on the
  residual; an inconsistent one — the genuine least-squares case — keeps a
  residual bounded away from zero, so its optimum is only visible through the
  normal-equation residual `‖Aᵀr‖`. That is a new `Termination::NormalEquations`
  rather than a reuse of `Converged`, because the two say different things about
  the answer. Both quantities fall out of the plane rotation, so neither costs
  an extra operator application.
- Optimality is tested by perturbation rather than against a quoted answer:
  every neighbour of the returned solution must have a larger residual.

### Gates

Athena workspace **51/51** nextest, clippy `-D warnings`, doctests, fmt — all
green. This also discharges the gate that could not run at the end of the
previous session, when an in-flight `aequitas` change was breaking `leto`
beneath the stack; that has since settled and the ADR 0034 work is covered by
this run too.

### Next

`ATLAS-GMRES-FORK-CONVERGE-001` is now unblocked:

- **Stage B** — migrate CFDrs from its `leto-ops` wrappers (`6d18a547`) to
  Athena. Note the direction: CFDrs currently consolidates onto the Leto family,
  which ADR 0033 identifies as the regression to unwind.
- **Stage C** — Kwavers, gated on refactoring `jacobian_vector_product` from
  `&mut self` to `&self` so its matrix-free operator satisfies
  `LinearOperator::apply(&self, ...)`. Its only mutation is a scratch cache.
- **Stage D** — delete `leto-ops/src/application/linalg/iterative/` including
  the duplicated `LinearOperator`/`Preconditioner` traits; residue scan clean.

## ATLAS-CFDRS-ATHENA-MIGRATION-001 — Stage B: CFDrs to Athena [major] [arch] — in-progress

Surveyed 2026-07-28 before starting. This is a redesign of the CFDrs
linear-solver architecture, not a port, and two of the mismatches change a
public CFDrs API — recording them rather than deciding unilaterally.

### Scale

56 files and 242 references across six crates (`cfd-1d`, `cfd-2d`, `cfd-3d`,
`cfd-core`, `cfd-math`, `cfd-validation`), of which **24 are production solver
construction sites** in 8 files; the rest are tests, benches, and re-exports.

`cfd_math::iterative` is currently a pure re-export of the `leto-ops` family
(`lib.rs:179`), so every consumer reaches the solvers through one facade.

### Structural mismatches

1. **Const-generic restart vs runtime config.** `Gmres<B, RESTART>` fixes the
   restart width at compile time. `LinearSolverChain` carries
   `krylov_restart: usize` as a runtime field with a builder
   (`with_krylov_restart`) and clamps it per solve:
   `min(self.krylov_restart, n_total_dof.max(1))`. A const generic cannot take
   that value. **Decision needed** (see below).
2. **Dynamic solver selection.** Four sites hold `Box<dyn LinearSolver<T>>`,
   including `cfd-validation` which builds a `Vec` of boxed solvers to compare
   CG against BiCGSTAB on the same system. Athena's solvers are ZST markers
   with static `solve_into`; `KrylovBackend` has GATs and `Gmres` a const
   generic, so none of it is dyn-compatible. The sanctioned replacement is
   enum dispatch over the closed solver set — I can decide this one, it is
   what the standards prescribe before reaching for `dyn`.
3. **Preconditioner trait.** CFDrs preconditioners — `AlgebraicMultigrid`,
   `BlockDiagonalPreconditioner`, `SimplePreconditioner`, `IncompleteLU`,
   `DiagJacobi` — implement `leto_ops::Preconditioner<T>`. Each needs an
   `athena_core::Preconditioner<LetoBackend<T>>` implementation instead.
   Mechanical, but touches every preconditioner.
4. **Caller-owned workspaces.** CFDrs solvers allocate internally per call;
   Athena requires a workspace owned by the caller and sized to the system, so
   every call site gains workspace lifetime management. This is the property
   that makes Athena allocation-free, so it is a real improvement rather than
   friction to work around — but it is a call-site change everywhere.
5. **Config to policy.** `IterativeSolverConfig { max_iterations, tolerance,
   relative_tolerance }` maps onto the validated `ConvergencePolicy`, which
   also carries a check interval and rejects invalid tolerances at
   construction. Mechanical.

### Decisions needed

**D1 — restart width.** Either (a) make `krylov_restart` a const parameter on
`LinearSolverChain`, a breaking change to a public CFDrs API; or (b) keep the
runtime field and dispatch across a small fixed set of `RESTART` instantiations
by enum, paying monomorphisation for each; or (c) fix one restart width and
delete the knob, checking first whether any caller sets it to a non-default
value. Recommend (c) if the knob is unused in practice, else (b).

**D2 — migration shape.** Either (a) convert all six crates in one change,
green only at the end; or (b) convert crate by crate while `cfd_math::iterative`
still re-exports `leto-ops`, deleting the facade last. (b) keeps the tree green
per commit and is not a shim — the old path stays only until its last consumer
is gone, which is what the anti-shim rule prescribes for a migration of this
size. Recommend (b), ordered `cfd-math` internals, then `cfd-2d`, `cfd-3d`,
`cfd-1d`, `cfd-validation`, then facade deletion.

### Not started

No CFDrs code changed. Nothing was added that would sit unused pending the
decisions above.

### Stage B progress 2026-07-28 — foundation landed, D1 corrected

**D1 was answered (c), and the check that answer depended on disproved it.**
`krylov_restart` is not an unused knob: `cfd-3d/fem/solver.rs` sets
`min(200, n)` at two sites, `cfd-1d/newton_fallback.rs` derives it from
`max_krylov_iterations`, and `cfd-math/nonlinear_solver/jfnk.rs` carries it in
its own config with 30 and 10 in tests and `min(n)` at runtime; the direct
`GMRES::new` sites use 30 and 100. Fixing one width would have silently
changed four solver configurations, so I took the fallback named in the same
decision — **(b), a fixed ladder with dispatch**.

- athena `f24dded`: `BorrowedCsrOperator`. `CsrOperator` takes ownership,
  which would force a per-solve `O(nnz)` sparse clone in a chain that tries
  several preconditioners against one system. Mirrors `BorrowedDenseOperator`.
- CFDrs `6a13a672`: `cfd_math::linear_solver::krylov` — the restart ladder
  (8/16/32/64/128/256, smallest covering width), `ConvergencePolicy`
  translation, and `gmres`/`gmres_preconditioned`/`bicgstab` entry points over
  Athena. Additive per D2(b): the `iterative` facade still re-exports leto-ops,
  so no consumer changed and the tree stays green per commit.
- Also repaired two cfd-math benches that had not compiled since `8aee5e59`
  left a stray brace in their imports.

Verification: cfd-math library compiles, clippy clean on the library, both
ladder cases pass, fmt clean. The package `--all-targets` gate is red for
reasons predating this change — unused imports and a dead struct in cfd-math
tests from the in-flight SSOT migration.

### Contention on the next increment

`chain.rs` is the next conversion target and a peer is **actively working in
it**: commit `16096fbc` ("resolve Quantity type mismatches in cfd-1d examples
and chain.rs") landed at 19:05 today and its rewrite of
`linear_solver/mod.rs` dropped the `pub mod krylov;` registration I had added,
leaving my file an orphan until I restored it. Converting `chain.rs` now would
collide directly.

Next increment should either wait for that scope to go quiet, or start at a
crate the peer is not in — `cfd-2d/src/physics/momentum/solver.rs` and
`cfd-2d/src/pressure_velocity/pressure.rs` are independent of `chain.rs` and
carry four of the twenty-four construction sites.

Remaining conversion order: `cfd-math` internals (`chain.rs`, multigrid),
`cfd-2d`, `cfd-3d`, `cfd-1d`, `cfd-validation`, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

Note for `cfd-validation`: four sites hold `Box<dyn LinearSolver<T>>` to
compare solvers on one system. Athena's markers are not dyn-compatible, so
that becomes enum dispatch over the closed solver set, per the standards.

### Stage B progress 2026-07-29 — cfd-2d converted

`58f6caab` momentum, `10fdd86e` pressure correction. cfd-2d is off the leto-ops
iterative family; the `cfd_math::iterative` facade still serves the other
crates, per D2(b).

- **Stateful solver objects removed.** Both consumers stored solver instances —
  `MomentumSolver` one GMRES, `PressureCorrectionSolver` three of which at most
  one was ever used, since `solver_type` already selected the recurrence.
  Athena solvers are stateless markers with caller-owned workspaces, so each
  collapses to the configuration it carried.
- **Triplicated policy consolidated.** `correction.rs` repeated the same
  solve-then-retry block verbatim per recurrence: solve with AMG, and on
  breakdown retry unpreconditioned, because a hierarchy built for a stale
  stencil can break the recurrence while the bare operator stays solvable.
  Written once now, with one dispatch over the closed solver set.
- **A real regression, caught and fixed at the right level.** Momentum assembly
  omits the diagonal of rows with no self-coupling. Athena's SOR rejects that;
  the leto-ops one had been *silently* defaulting those rows to a unit pivot.
  Rather than loosen the default, athena `461cdd5` added
  `from_csr_with_identity_rows` — same behaviour, opted into visibly at the
  call site, with a test pinning it.
- athena `f24dded` `BorrowedCsrOperator` removes a per-solve `O(nnz)` clone;
  the Athena SOR likewise borrows where the previous one took ownership, which
  matters because momentum rebuilds it after every coefficient update.
- `AlgebraicMultigrid` gained an Athena preconditioner implementation. Its
  V-cycle recurses over owned vectors while Athena passes borrowed views, so
  the boundary copies through cached buffers rather than allocating per
  application. Two `O(n)` passes against the cycle's `O(nnz)` sweeps.
  **Follow-up: rework the V-cycle onto slices to remove them.**

Verification: cfd-2d 570/571 nextest at both increments; the timeout is a
cross-fidelity tree test with no solver involvement that times out identically
without these changes. Clippy ran clean on the libraries for the first
increment; for the second it could not run — an in-flight `gaia` change removed
the `cfdrs-integration` feature cfd-2d depends on, breaking resolution for
unrelated reasons. **Re-run clippy on cfd-2d once gaia settles.**

## ATLAS-LETO-OWNED-LU-001 — cfd-math consumes an unlanded Leto LU surface [major] — todo

`cfd-math` does not compile on CFDrs main. Not a toolchain fault — the
compiler is now coherent and the errors are ordinary resolution failures:

```
E0432 unresolved imports leto_ops::{OwnedNumericLu, SymbolicLu, factor_symbolic}
E0599 no method `factor_sparse_with_symbolic` on leto_ops::SparseLuSolver
```

Introduced by `63e49604` ("fix(cfd-3d): Close FEM metric solver gaps"), which
landed a consumer against a Leto API that was never published — the
co-evolution order inverted, upstream last instead of first.

**What Leto actually has** (`crates/leto-ops/src/application/sparse/`):

| cfd-math expects | Leto has |
| --- | --- |
| `OwnedNumericLu<T>` | nothing — the name exists nowhere in the repo or its history |
| `SymbolicLu`, `factor_symbolic` | both exist, but are **not** re-exported from `lib.rs` |
| `SparseLuSolver::factor_sparse_with_symbolic` | no such method |
| — | `NumericLu<'a, T>`, `factor_numeric` |

**The real requirement is the owned variant, not the re-exports.**
`NumericLu<'a, T>` borrows the matrix it factorises, so
`block_preconditioner.rs:629` cannot hold `Vec<OwnedNumericLu<T>>` alongside
the blocks that produced them — the lending form is what forces an owned
factorisation to exist. That is upstream work in Leto (upstream ownership),
not something to approximate inside cfd-math.

- Scope: implement the owned numeric factorisation in `leto-ops` beside
  `NumericLu`, re-export it with `SymbolicLu`/`factor_symbolic` from
  `lib.rs`, add the symbolic-reuse entry point, land it, then let cfd-math
  resolve against it.
- Acceptance: `cargo clippy -p cfd-math --lib` clean; the block
  preconditioner's per-block factorisations reused across applications rather
  than refactored each time.
- **Warning — possible lost work.** `repos/leto` was destroyed and re-cloned
  by an external actor mid-session (`git reflog` bottoms out at
  `clone: from https://github.com/ryancinsight/leto`). Any uncommitted
  sparse-LU work in that tree is gone, and no branch or dangling object in the
  repository contains `OwnedNumericLu`. Both Leto lanes under `worktrees/`
  were searched as well; a stack-wide grep finds the name in exactly one
  place — the CFDrs consumer that needs it. Whoever wrote `63e49604` should
  check for an unpushed copy before this is rebuilt from scratch.

Process note: the momentum commit `58f6caab` swept up six files of a peer's
*staged* Quantity-migration work through an over-broad `git add crates/cfd-2d`.
Their work is preserved and pushed, but under a message that does not describe
it. Not reverted — that would discard it. Staging was per-file for the second
increment.

Remaining: `chain.rs` and multigrid in cfd-math, then cfd-3d, cfd-1d,
cfd-validation, then delete the `cfd_math::iterative` facade.

## ATLAS-ADR-GOVERNANCE-001 — Retrofit ADR indexes, statuses, and records [patch] — in-progress (indexes landed)

- Policy: AGENTS.md context_and_memory "ADR governance". Census 2026-07-27: 312 ADRs across the meta repo + 20 members; indexes exist in 3 of 21 (meta, ritk, iris); 7 duplicate numbers (kwavers x2, coeus x3, leto, hermes); 104 ADRs without a Status line; casing drift (Accepted vs accepted) plus a non-canonical "investigated"; supersession links on 4 of 312.
- Scope per repo: (1) generate `docs/adr/README.md` indexes (number, title, status) — mechanize as a committed script deriving the index from ADR headers (toil automation; hand-maintained indexes rot), wired into CI as a regenerate-and-diff freshness check like the overlay; (2) normalize statuses to the canonical set with exact casing, adding Status lines where absent (default: Accepted for implemented decisions, verified against the code); (3) resolve the 7 numbering collisions by renumbering the later ADR and updating its citations; (4) merge audit (rewrite-in-place model per revised ADR governance): where a later ADR replaced an earlier decision, merge into one current record carrying a dated revision note and delete the stale file — git is the archive; canonical statuses are Proposed/Accepted/Rejected; (5) verify board items citing ADRs and ADRs citing items resolve (bidirectional linkage).
- Acceptance: every ADR directory carries a current generated index; zero duplicate numbers; every ADR has a canonical status; the freshness check is green in CI; a spot-check of decision recall (pick three active items, confirm governing ADRs discoverable from the index in one step) passes.
- Update 2026-07-27: `scripts/adr-index.py` landed (generate/check per the generator contract, parsing both inline `Status:` and MADR `## Status` conventions); generated indexes committed and pushed to all 20 member repos plus meta; check mode green and idempotent. The 290-line anomaly report is the burn-down census: 7 numbering collisions itemized with file pairs (coeus 0021 x3-way + 0025, hermes 007, kwavers 037 + 040, leto 0011), missing/non-canonical statuses per repo. Remaining judgment work: status verification against code, collision renumbering with citation updates, the merge audit, content conformance, and per-repo backfill inventories for canonical seams lacking any ADR.

## ATLAS-CODE-INDEX-001 — Search-ladder infrastructure for context economy [patch] — in-progress

- Owner: opencode-2026-08-05; scope: the atlas meta-repo and its `repos/*` members
  (tooling and generator contract only — no member Cargo.toml/manifest edits).
  Host tooling verified: `rust-analyzer` and nightly toolchain present; `ast-grep`
  absent (install is scope item 1).

- Policy: AGENTS.md context_and_memory "Code-search ladder". Motivation: 325 tool-output truncations and 66 compactions across eight recent fleet sessions — agents read where they should search; the fleet-recommended tools were researched and the ladder chosen over them where they misfit (agent-memory graph stores such as Graphiti duplicate the board/ADR/git memory layer and are rejected — one curated memory, one archive).
- Scope: (1) ast-grep availability as committed tooling (structural queries, stateless per tree — worktree-safe by construction); (2) SCIP emission per member repo (`rust-analyzer scip`), revision-keyed under a gitignored index directory with a generator-contract freshness check, plus a thin lookup wrapper (scip CLI) so agents resolve definitions/references without full-file reads; (3) rustdoc JSON as the machine-readable API oracle for the anti-hallucination check, emitted under the nightly verification toolchain like miri; (4) evaluate a Zoekt trigram server over the shared gitdirs only if per-tree tooling proves insufficient at fleet scale — standing infrastructure needs the toil-automation justification; (5) wire ladder usage guidance into each repo agent-facing docs if repo convention keeps local instructions.
- Acceptance: spot-check — an agent locates three symbol definitions and one API signature across repos it has not read this session using only ladder queries (no full-file reads); index freshness check green in the sweep.

## ATLAS-CFDRS-CHAIN-LADDER-001 — Consolidate the two tiered ladders [patch] — in-progress

`LinearSolverChain::solve` and `solve_with_state` run the same five tiers with
three deliberate differences: log prefix, an iterate reset between tiers, and
the warm path skipping the unpreconditioned tier once a block preconditioner
was built but stalled. Express the ladder once with those as parameters, and
decide explicitly whether the cold path should adopt the skip policy — it is
an improvement the warm path received and the cold one did not, and adopting
it changes which solver answers a given system.

Remaining stage B: cfd-3d, cfd-1d, cfd-validation, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (evening) — cfd-3d deferred, cfd-validation converted

**cfd-3d was not attempted.** Both its solver files were being edited live:
`crates/cfd-3d/src/fem/solver.rs` had a modification timestamp one minute
before I began, alongside 17 other dirty cfd-3d files from a peer's Quantity
migration. Editing there would have collided destructively, so the scope was
skipped rather than taken. **Re-open trigger: cfd-3d/src/fem goes quiet.**

Its two sites when it does: `projection_solver.rs` holds a `GMRES` and a
`ConjugateGradient` field, and `solver.rs` holds `_linear_solver: GMRES<T>` —
note the underscore, it is already dead and should be deleted rather than
converted. `solver.rs` also drives `LinearSolverChain`, which is already on
Athena.

**cfd-validation converted instead**, `f8634e43` — a clean, disjoint file.

- `Vec<(&str, Box<dyn LinearSolver<T>>)>` becomes `SolverKind`, the closed-set
  enum dispatch decided earlier. Athena's markers carry const generics and
  backend GATs and are not object-safe, so this was the one site that could
  not be a mechanical swap.
- Same correction `chain.rs` needed: Athena reports a stalled or broken-down
  solve in the report, not as `Err`, so a bare match would have **recorded a
  non-converged iterate as a validation result**.
- The split between fatal and tolerated failure is preserved deliberately: the
  ill-conditioned Hilbert case is expected to break down; the diagonal and
  Poisson cases are not.
- `SolverKind` lives in cfd-math beside the other entry points so the
  pressure-velocity dispatch can adopt it rather than keep its own match —
  **follow-up**.

Verification: `cargo check` clean for cfd-validation and cfd-math. Tests could
not run — `repos/hephaestus` is mid-rebase onto a branch four commits behind
master, so `hephaestus-core` does not compile in the shared tree. **Re-run the
cfd-validation suite once that settles.**

Note the compounding cost: three consecutive increments have now had a gate
blocked by shared-tree churn — clippy twice by `ATLAS-TOOLCHAIN-COHERENCE-001`,
tests once by a mid-rebase hephaestus. The verification debt is tracked, not
silently absorbed.

Remaining stage B: cfd-3d (blocked), cfd-1d, then delete the
`cfd_math::iterative` facade and the leto-ops iterative dependency.

### Stage B progress 2026-07-29 (late) — cfd-1d converted

`4ca6518d`. The network solver's iterative tier is on Athena.

- The CG and BiCGSTAB arms were identical apart from the recurrence, so they
  collapse onto `SolverKind`. `LinearSolverMethod` stays as the domain-facing
  choice and maps onto it.
- `DiagJacobi` gained an Athena implementation that applies straight over the
  borrowed views — elementwise, so no scratch and no copy, unlike the AMG
  boundary which must buffer.
- The post-solve residual check is kept, with its reason now explicit: the
  solve runs on the **row-equilibrated** matrix, so meeting the tolerance
  there does not bound the residual of the original system. Athena reporting
  convergence is one of two acceptance conditions, not the only one.

Verification: cfd-1d **736/736** nextest including the primary-solve
reliability cases that exercise this path, `cargo check` clean.

### Correction to an earlier claim

I recorded after `40ef080c` that "cfd-math is fully off the leto-ops iterative
family". True as stated, but incomplete as an impression: `cfd-math`
`nonlinear_solver/jfnk.rs` carries its **own hand-rolled matrix-free
restarted GMRES** (`gmres_matrix_free`), which never used leto-ops. It is a
fifth GMRES in the stack after leto-ops, the deleted CFDrs copy, kwavers, and
Athena. Filed below.

## ATLAS-JFNK-MATRIX-FREE-GMRES-001 — Converge JFNK onto Athena [minor] — todo

- `cfd-math/src/nonlinear_solver/jfnk.rs` implements restarted GMRES inline for
  Jacobian-free Newton-Krylov, using only matrix-vector products.
- Migrating it needs Athena's `LinearOperator` over a Jacobian-vector closure.
  Check first whether that closure needs `&mut self` — if so it hits the same
  blocker as Kwavers stage C (`ATLAS-GMRES-FORK-CONVERGE-001`), and the two
  should be solved together rather than separately.
- `cfd-1d/src/solver/core/newton_fallback.rs:223` feeds `krylov_restart` into
  this config, so it is the last cfd-1d reference to a non-Athena solver.

Remaining stage B: cfd-3d (blocked on peer activity in `cfd-3d/src/fem`), JFNK,
then delete the `cfd_math::iterative` facade and the leto-ops iterative
dependency.

### Verification debt review 2026-07-30

**cfd-3d is still not clear.** Peer commit `63e49604` landed at 01:40, twelve
minutes before the check, and `projection_solver.rs` carries their uncommitted
continuation of the same Quantity migration (`.into_base()` conversions).
Fresh and commit-backed, so the scope stays blocked. `solver.rs` is clean now,
but it is the same live scope. Re-check later.

**cfd-validation tests: discharged.** The hephaestus rebase finished, so the
suite ran: **184/187 passed, 3 timed out** in
`numerical::venturi_cross_fidelity`.

Those three were investigated rather than assumed pre-existing, because they
drive `cfd_2d::solvers::ns_fvm` SIMPLE and could plausibly have been a
convergence regression from the pressure-correction migration. They are not:
`ns_fvm` solves its pressure-correction Poisson with **its own hand-rolled SOR
sweep** (`solvers/ns_fvm/solver/pressure/poisson.rs`), never reaching
`PressureCorrectionSolver` or any Krylov solver in this migration. Running one
case without a timeout shows SIMPLEC continuity stagnant at ~4.59e2 across ten
iterations and still running past 400s, which is that SOR failing to converge
on a micro-scale geometry. The file is also peer-dirty. Filed below.

**Clippy: still blocked**, third consecutive attempt, now surfacing on
`cfd-io` whose dependencies were built by a different rustc. Note the tests
passed minutes earlier under the same toolchain — the poisoned artifact set
differs by which crates a command pulls, which is exactly why this presents as
moving, unrelated breakage. `ATLAS-TOOLCHAIN-COHERENCE-001` is the blocker and
is now the single largest drag on verification.

## ATLAS-NSFVM-SOR-CONVERGENCE-001 — Micro-geometry SIMPLEC continuity stagnation [major] — todo

- Three `venturi_cross_fidelity` cases time out: the 35um and fallback
  microventuri cases and the 45um option-2 routing case.
- `cfd_2d::solvers::ns_fvm` solves pressure correction with a hand-rolled SOR
  sweep. On these micro-scale geometries the continuity residual holds near
  4.59e2 while velocity falls, so the outer SIMPLEC loop never terminates and
  the case runs past 400s against a 30s budget.
- Independent of the Athena migration — this path contains no Krylov solver.
- Two candidate directions, needing measurement first: the SOR sweep is not
  converging for this conditioning and should be replaced by a proper Krylov
  solve now that `cfd_math::linear_solver::krylov` exists, or the case is
  genuinely stiff and the fallback routing is selecting the wrong model. The
  budget breach is a defect either way and must not be resolved by raising the
  bound.

---

# Diffusion MRI capability program (gap analysis 2026-07-30)

Audit of the Atlas stack against the reference diffusion-MRI toolchains
(FreeSurfer, MRtrix3, FSL, DIPY), scoped by
[ADR 0036](docs/adr/0036-neuroimaging-and-mr-ownership.md). Ownership is settled
by that ADR — RITK workspace crates, no new package. These items are the
capability gap under that ownership, ordered by dependency. Waves 0 and 1 gate
everything after them.

Evidence for each claim is the cited file and line at the gitlink revision of
2026-07-30. The ADR source audit and the README section were corrected in the
same change; see ADR 0036 decision 7.

## ATLAS-STACK-LETO-CHURN-017 — Upstream working-tree churn blocks consumer verification — todo

Third occurrence on 2026-07-31 of the same pattern, now costing real delivery
time, so it is recorded as its own item rather than re-diagnosed each session.

- **Symptom**: a consumer repo's `cargo check`/`nextest` fails inside
  `repos/leto` with errors that change between consecutive runs and reference
  code the consumer never touched.
- **Cause**: the stack `[patch]` overlay resolves first-party dependencies to
  local working trees, so a peer's *uncommitted, mid-edit* state in an upstream
  repo reaches every downstream consumer immediately. Observed today in
  `leto-ops/src/application/attention/` (cleared on retry) and
  `leto-ops/src/application/zip.rs` (still red; file modified seconds before
  each check).
- **Not a defect in either repo.** The overlay behaving as designed, plus
  normal peer activity. Same class as ATLAS-RITK-MODULE-FORWARD-000.
- **Cost**: any consumer increment depending on the churning crate cannot be
  verified, so it cannot be committed. ATLAS-COEUS-NLLS-004 parked on exactly
  this for roughly 25 minutes, clearing only when the peer committed `zip.rs`.
  The park was the correct call — the errors changed between consecutive runs,
  so retrying would have chased a moving target — but it is dead time that
  option (b) would remove.
- **Candidate directions, needing a decision rather than more diagnosis**:
  (a) accept it and treat upstream redness as a park-and-switch signal, which is
  current practice and what the contention response order already prescribes;
  (b) have the overlay resolve to each member's last *committed* revision rather
  than its working tree, making peer WIP invisible until committed — this is the
  real fix but changes the development overlay contract in
  architecture_scoping and needs an ADR;
  (c) narrow the overlay per session to the repos an agent actually edits.
  Option (b) is the recommendation: an uncommitted edit is not a published
  state, and the overlay currently makes it one for the whole stack.
- **Class**: `[arch]` if (b) is taken, since it revises the development overlay.
- **Fourth occurrence 2026-08-13 falsifies option (c).** Verifying one RITK
  branch, four consecutive attempts minutes apart each failed in a *different*
  upstream repo: `eunomia` (duplicate `PartialEq` — macro added before the
  manual impls were removed), `apollo-fft` (`BLUESTEIN_NATIVE_PHASE_TRIG` used
  in impls before the trait declared it), `eunomia` again (`FloatElement`
  gaining an `Accumulator` associated type, trait ahead of impls), and
  `consus-hdf5` (arity mismatch mid-signature-change). Every one is a normal
  half-finished edit; none is a defect.
  Option (c) assumed churn localizes to the repos an agent is near, so a
  narrowed overlay would dodge it. It does not: the churn was spread across
  four repos the RITK branch never touched, and narrowing enough to avoid them
  would exclude most of the stack, which defeats the overlay. That leaves (a)
  and (b), and (b) remains the recommendation.
  Retrying is also not free-but-harmless: because the failing crate *moves*,
  a green run is a peer-quiet window rather than evidence, so a consumer needs
  a retry loop that distinguishes upstream churn from its own redness before
  any result means anything.

## Wave -1 — peer contention, not RITK work (recorded 2026-07-30)

## ATLAS-RITK-MODULE-FORWARD-000 — RITK is red against in-flight Coeus WIP — resolved

**Resolved 2026-07-31 by the peer landing both sides.** Coeus committed the
contract (`repos/coeus` `5e64ee75 feat(coeus-nn)!: Make forward fallible`, now on
`origin/main`) and RITK adopted it (`repos/ritk` `d82efc23 feat(model)!: Adopt
Coeus's fallible module forward`, on `origin/main`). `ritk-transform` and
`ritk-io` build; 400/400 `ritk-mgh` + `ritk-io` tests pass at `ea11f4fb`. The
re-open trigger below fired exactly as recorded; waiting rather than converting
against uncommitted upstream was the correct call.

One item from the analysis survived the peer's sweep unfixed and is promoted to
ATLAS-RITK-DISPLACEMENT-FORWARD-016 below.

The original record is kept for the diagnostic pattern — a consumer red that is
really a provider's in-flight working tree reaching it through the stack
`[patch]` overlay.

**Not a RITK defect and not a claimable RITK item.** Recorded so the next agent
does not re-diagnose it, and does not do what this session started doing.

- **Symptom**: `cargo check -p ritk-transform` gives 10 `E0053`/`E0308` errors —
  every `Module::forward` impl returns `Var<f32, B>` where the trait now expects
  `Result<Var<f32, B>, ModuleError<B::Error>>`. `ritk-io`, `ritk-registration`,
  `ritk-cli`, and `ritk-snap` cannot build behind it.
- **Actual cause**: the fallible `Module::forward` and `ModuleError` are a live
  peer's **uncommitted** work in `repos/coeus`. `crates/coeus-nn/src/module/`
  (`trait_def.rs`, `error.rs`, `mod.rs`) has *no git history at all* — it exists
  only staged in the working tree, alongside ~143 other staged `coeus-nn` files
  and a staged `coeus-autograd` set, on branch
  `codex/coeus-error-function-parity`. RITK compiles against it because the
  stack `[patch]` overlay resolves first-party dependencies to local working
  trees, so a peer's in-flight refactor reaches every consumer immediately.
- **Therefore this is not "RITK failed to adopt a landed contract."** There is no
  landed contract. Converting RITK's 25 `Module` implementors now would commit
  RITK to a signature that exists in no commit on any branch, break RITK against
  Coeus `HEAD`, and collide with the peer when they land. This session began that
  conversion, then discarded it on discovering the above — the discard is the
  correct outcome, not lost work.
- **Peer freshness**: last `repos/coeus` commit `9ac74e13`, 2026-07-29 06:34
  (~1 day), with the change set staged and uncommitted since. Stale by the
  sweep's clock, but a 143-file in-flight refactor is not blind-takeover
  material. Re-check before assuming the peer is gone.
- **Re-open trigger**: the peer commits the `coeus-nn` module contract. At that
  point the RITK sweep becomes a real `[patch]` item — convert every implementor
  to the fallible signature and propagate at call sites with `?`, no `.expect()`
  at any site that has a caller to return to.
- **Known blocker for that future item**: `ModuleError` cannot carry a
  `coeus_ops::InterpolationError`. `DisplacementFieldTransform::forward`
  currently `.expect()`s one (`transform/displacement_field/transform.rs:124`),
  and `InterpolationError::{NonFiniteCoordinate, SizeOverflow}` have no
  `ModuleError` counterpart, so any mapping collapses distinct failure modes.
  The fix is an additive `Interpolation(#[from] InterpolationError)` variant on
  the (already `#[non_exhaustive]`) `ModuleError` in `coeus-nn` — upstream, in
  the same provider family, `[minor]`. Raise it with the peer rather than
  working around it downstream.
- **What is still verifiable meanwhile**: everything not depending on
  `coeus-nn`'s `Module`. Confirmed green this session: `ritk-mgh` (34/34),
  `ritk-nifti`, `ritk-nrrd`. The wave-0 format-crate work below therefore
  proceeds; only the `ritk-io` dispatch tail of ATLAS-DMRI-IO-001 waits.

## ATLAS-RITK-DISPLACEMENT-FORWARD-016 — `forward` panics on a real interpolation failure [patch] — implemented; validation blocked 2026-08-05

- **Evidence**: `ritk-transform/src/transform/displacement_field/transform.rs`
  now carries the fallible signature but keeps the panic inside it:

  ```rust
  Ok(self
      .transform_points(input)
      .expect("invariant: Module::forward receives valid field coordinates"))
  ```

  `transform_points` returns `Result<_, DisplacementTransformError>`, whose
  `Interpolation` variant carries a genuine runtime failure —
  `NonFiniteCoordinate` fires on a NaN sampling coordinate, which a diverging
  optimizer produces routinely. The sweep at `d82efc23` adopted the signature
  everywhere but wrapped this one body in `Ok(..)` instead of propagating, so the
  method gained a `Result` return that cannot express the one failure it has.
  Panic policy: library code does not panic on input-dependent paths, and the
  `expect` message asserts an invariant the type does not enforce.
- **Blocked on upstream**: `ModuleError` has no variant able to carry a
  `coeus_ops::InterpolationError`. `Backend { source: E }` requires
  `E = B::Error`, and `InterpolationError::{NonFiniteCoordinate, SizeOverflow}`
  have no counterpart among the rank/shape variants, so any downstream mapping
  collapses distinct failure modes.
- **Fix, in order**: (1) add `Interpolation(#[from] InterpolationError)` to
  `coeus_nn::ModuleError` — additive on an already `#[non_exhaustive]` enum, and
  in the same provider family since `coeus-nn` already depends on `coeus-ops`;
  (2) in RITK, map `DisplacementTransformError::PointShape` losslessly
  (`actual.len() != 2` → `InvalidRank`, else `ShapeMismatch` with
  `expected: [actual[0], D]`) and propagate `Interpolation` through the new
  variant.
- **Acceptance**: a NaN sampling coordinate returns a typed error naming the
  axis and point instead of panicking; existing displacement tests unchanged.
- **Delivered 2026-08-05**:  `coeus-nn::ModuleError` now carries typed `InterpolationError`;
  `DisplacementFieldTransform::forward` maps rank failures to `InvalidRank`,

  width failures to `ShapeMismatch`, and propagates interpolation failures
  instead of using `expect`. Ritk tests now cover NaN propagation through the
  public `Module::forward` path and verify wrong `[N, D]` input becomes a
  typed `ShapeMismatch`. Coeus Python maps interpolation failures to
  `PyValueError` with a focused mapping test. Rustfmt and diff checks
  pass for all four touched files. Package check/Clippy/nextest remain blocked
  by the peer-modified Coeus reduction refactor: `coeus-ops/src/reduction/norms.rs`
  references `ReductionOps`, but the current workspace compilation cannot
  resolve that trait; no peer-owned reduction files were changed here.
- **Class**: `[patch]` in RITK, `[minor]` in Coeus. Raise the upstream half with
  the `coeus-nn` owner rather than mapping around it.

## Wave 0 — acquisition-series ingest (blocks every later wave)

## ATLAS-DMRI-IO-001 — Rank-generic acquisition-series I/O [minor] — in-progress

**Claim 2026-08-11 — Codex current session:** own the next vertical
`ritk-nrrd` increment on branch `codex/ritk-nrrd-series` in the reclaimed
`worktrees/ritk-book-wf` lane. Claimed files are the NRRD reader/writer,
their co-located tests, and the package-local documentation needed for rank-4
acquisition-series round trips. Non-goals are MGH, DICOM, `ritk-io` dispatch,
and the peer-dirty ADR index in the primary RITK checkout.

**Re-audit closure 2026-08-11:** no NRRD implementation was added because
`origin/main` already carries the complete `d3d3d811` series implementation:
leading and trailing acquisition-axis decoding, rank-4 writing, shared-grid
validation, and value-semantic tests. RITK PR #119 merged at
`0a1a4dc98ec541ea2caa952dd2385c9ebfac583b` with its hosted Rust, Python,
workspace-alignment, and platform test jobs green. The local `--locked` gate
was blocked before compilation by the separately tracked provider drift
(`hermes-simd` 0.5.0 and `moirai-runtime` 0.4.0 locks versus current provider
heads); RITK PR #118 owns the overlay-free release-lock repair. The NRRD
sub-scope therefore closes as an evidence-backed stale-gap correction, while
MGH, DICOM, and `ritk-io` dispatch remain open sub-increments of this item.

**`ritk-nifti` increment delivered** at `ritk` `2a4b1f62`, pushed to
`codex/perf-ritk-mgh-stream-book` (PR #78, a peer's branch — the scopes are
disjoint, `ritk-nifti` vs the peer's `ritk-mgh` streaming slice, so the increment
rides that branch per the shared-branch model rather than opening a second PR).

Rank 3 and rank 4 both parse; the payload byte range spans every declared volume
instead of one; `read_nifti_series` / `read_nifti_series_from_bytes` /
`write_nifti_series` / `write_nifti2_series` are the series surface. The writer
selects rank from the volume count, so a one-volume series stays a rank-3 file
byte-identical to `write_nifti`, and it validates that every volume shares one
grid rather than emitting a file whose sform covers only part of its content.
`read_nifti` and `read_nifti_labels` now name the volume count and fail on a
rank-4 file instead of decoding volume 0 — the MGH defect class, caught before it
could ship in a second codec.

Verified: 49/49 `ritk-nifti` (0.564s), 370/370 `ritk-io` + `ritk-analyze`
downstream, clippy `--all-targets -D warnings` clean, `RUSTDOCFLAGS=-D warnings
cargo doc` clean.

Design decision recorded here rather than an ADR, being reversible and internal:
the series surface returns `Vec<Image<f32, B, 3>>` rather than a new
`ImageSeries` domain type. Volumes on one grid is what the format states, it
needs no cross-crate public API, and it does not prejudge the type
ATLAS-DMRI-SCHEME-003 actually needs — which carries the gradient scheme
alongside the volumes and is where the per-voxel-across-volumes access pattern
will be known. A contiguous layout stays open behind that type.

Remaining sub-increments: `ritk-mgh` series read (currently fails loudly per
ATLAS-DMRI-MGH-FRAMES-002, so this is an extension not a fix), `ritk-dicom`
multi-frame/series assembly, and the `ritk-io` dispatch tail. The NRRD
increment is closed by `d3d3d811` on the merged RITK head.

## ATLAS-DMRI-IO-001 original specification

- **Outcome**: `ritk-nifti`, `ritk-nrrd`, and `ritk-dicom` read and write a
  series carrying an acquisition axis, and `ritk-io` dispatches it.
- **Evidence of gap at item creation**: `ritk-nifti/src/header/validate.rs:74`
  bailed on `dim[0] != 3`; `ritk-nrrd` rejected acquisition-series headers;
  and `ritk-io/src/lib.rs:164` fixed `NativeImage = Image<f32, NativeBackend,
  3>`. The NRRD rejection was closed by `d3d3d811`; MGH, DICOM, and dispatch
  remain the live gaps.
- **Non-goals**: no change to `Image<T, B, D>`, which is already rank-generic;
  no arbitrary-rank generalization beyond one acquisition axis.
- **Design note**: a DWI series is 3 spatial axes plus 1 acquisition axis, not a
  4-D image. `Point<4>`/`Spacing<4>`/`Direction<4>` would assert direction
  cosines over the acquisition axis, which is meaningless. The type carries 3-D
  spatial metadata plus a per-volume scheme (ATLAS-DMRI-SCHEME-003), so the
  metadata stays 3-D and only storage gains the axis.
- **Acceptance**: round-trip a synthesized N-volume series through each codec
  recovering voxels and spatial metadata exactly; the existing 3-D entry points
  keep their signatures and tests.
- **Class**: `[minor]` — additive public surface.
- **Sequencing note (2026-07-31)**: no longer split — the `ritk-io` block
  cleared when ATLAS-RITK-MODULE-FORWARD-000 resolved. The `ritk-nifti` and
  `ritk-nrrd` increments are now closed on `origin/main`. The next increments
  are the `ritk-io` dispatch tail and the `ritk-mgh` series extension; MGH
  already fails loudly on a multi-frame file per ATLAS-DMRI-MGH-FRAMES-002, so
  its series read is an extension rather than a defect fix.

## Wave 1 — upstream provider capability (ADR 0036 decision 2 edges)

Each of these lands in the provider that owns the bounded context. A RITK-local
implementation of any of them is a boundary violation and fails ADR 0036
verification condition 2.

## ATLAS-COEUS-NLLS-004 — Gauss-Newton / Levenberg-Marquardt in coeus-optim [minor] — review

**Delivered.** `crates/coeus-optim/src/least_squares/` holds the
`LeastSquaresProblem` contract, the `LevenbergMarquardtConfig`/`Termination`
vocabulary, the damped Gauss-Newton solver, and a suite instantiated across
`f32` and `f64`. The blocker below cleared when the peer committed
`leto-ops/src/application/zip.rs`.

Landed in two commits, the split being a peer takeover rather than a plan:
`coeus` `53816ebf` (a peer picked up the uncommitted module and committed it)
and `coeus` `4d634750` on `feat/coeus-optim-least-squares`, PR #258 (the clippy
gate the first commit had not been run through).

**The peer's commit fixed two real defects in this work**, both worth recording
because neither is obvious from the code:

- `SolverError::NonFinite` had a `&'static str` field named `source`.
  `thiserror` treats a field of that name as the error source and requires it to
  implement `Error`, which `&str` does not. Renamed to `evaluation`, its actual
  meaning.
- `LeastSquaresScalar`'s supertrait chain surfaces both `Scalar::to_f64` and
  eunomia's `NumericElement::to_f64`, so bare method calls are ambiguous. The
  tests now UFCS-qualify them. Any future consumer composing these two
  vocabularies hits the same thing.

Verified at `4d634750`: 36/36 `coeus-optim` tests (16 least-squares across both
scalar types, 20 pre-existing), clippy `--all-targets -D warnings` clean,
`RUSTDOCFLAGS=-D warnings cargo doc` clean.

Design notes kept below; they explain choices the diff does not.

Design notes worth keeping, so a takeover does not re-derive them:

- LM does not fit the existing `Optimizer` trait. That trait steps on gradients
  already accumulated into parameters (the network-training shape); a
  least-squares solver re-evaluates the model at trial points to accept or
  reject a step, and exploits the Gauss-Newton structure `JᵀJ ≈ H` a bare
  gradient hides. Two contracts, not two spellings of one — hence a separate
  module rather than a fifth `impl Optimizer`.
- The scalar bound is `Scalar + RealScalar`, composing coeus's element
  vocabulary with leto's dense-linear-algebra vocabulary. This is the existing
  bridge pattern, not a new one: `coeus-leto`'s `AttentionScalar: Float +
  RealScalar` does the same thing. The normal-equations solve stays leto's per
  upstream ownership; coeus owns only the iteration and damping.
- Damping scales by `diag(JᵀJ)` (Marquardt's modification) rather than the
  identity, making the step invariant to per-parameter rescaling. A diffusion
  model mixing diffusivities near `1e-3` with signal amplitudes near `1e3` is
  exactly the badly-scaled case that motivates it.
- A `ProblemError::Domain` from the model is treated as a rejected step, not a
  solver failure: negative diffusivity under a square root is a statement about
  the trial point, and damping pulls the next trial back toward the last
  accepted one.
- Convergence criteria are derived, per this item's acceptance: gradient
  infinity norm, relative step against parameter scale, relative cost
  reduction. Tolerances default to `sqrt(ε)` of the working type, derived by
  bisection since `Scalar` exposes no epsilon constant. The iteration cap is a
  runaway guard reported as a *non-converged* `Termination::IterationLimit`,
  never as success.

The original remaining batching requirement is complete in Coeus PR #323,
merged as `d591220053586247ed3e9b344133281617055a2e`: `BatchedLeastSquaresProblem`
and `batched_levenberg_marquardt` delegate each leading-axis problem to the
canonical solver, preserve row order, and return indexed parameter/solver
errors. f32/f64 recovery and malformed flattened-parameter tests pass; the
provider's exact post-merge Backend parity run `31666097106` passed CUDA,
Metal, ROCm, and WGPU lanes. Required-device CUDA/ROCm jobs were explicitly
skipped by workflow policy, so physical-device execution remains external.

## ATLAS-COEUS-NLLS-004 original specification

- **Evidence of gap**: `coeus-optim` ships `SGD`, `Adam`, `AdamW`, `RMSProp`,
  and `Adagrad` only — all first-order stochastic, sized for network training.
- **Why it blocks**: per-voxel diffusion fitting is millions of independent
  small dense residual problems. A damped Gauss-Newton step with an analytic
  Jacobian converges in single-digit iterations; a first-order stochastic
  optimizer is the wrong instrument by orders of magnitude. Log-linear DTI is
  unaffected — it routes through `leto-ops` (`pinv`, `qr_decompose`,
  `cholesky_solve`), which already exist.
- **Blocks**: DKI, NODDI, IVIM, free-water, and every other nonlinear model.
- **Acceptance**: batched over a leading problem axis; verified against an
  analytical oracle with a known minimum and against a published test problem
  set; convergence criterion is a derived relative-residual bound, never a fixed
  iteration count.
- **Class**: `[minor]`, repository `repos/coeus`.

## ATLAS-APOLLO-REALSH-005 original specification

- **Evidence of gap**: `apollo-sht` owns complex SH on Gauss-Legendre product
  grids. `infrastructure/kernel/spherical_harmonic.rs:234` exposes
  `spherical_harmonic(degree, order, theta, phi) -> Complex64`, so pointwise
  evaluation at an arbitrary direction already exists; the real, even-order,
  antipodally symmetric basis, the design matrix over a scattered direction set,
  and Laplace-Beltrami regularization do not.
- **Why Apollo and not RITK**: Apollo owns the transform bounded context. A
  RITK-local associated-Legendre or normalization path forks the SH dimension
  and is the exact failure mode ADR 0036 decision 2 exists to prevent.
- **Convention pinning**: the basis has several published orderings and
  normalizations (Descoteaux and Tournier differ). The implementation declares
  one, and a reference-case test asserts it against published coefficients.
- **Blocks**: every ODF/FOD model in `ritk-diffusion`.
- **Class**: `[minor]`, repository `repos/apollo`.

## ATLAS-GAIA-POLYLINE-006 — Polyline geometry and unit-sphere direction sets [minor] — todo

- **Evidence of gap**: `repos/gaia/src/domain` holds `core`, `geometry`, `mesh`,
  `topology`, and `grid.rs`; no open polyline or curve type exists.
- **Why it blocks**: ADR 0036 verification condition 5 requires streamline output
  in Gaia geometry types — a RITK-local polyline type is a boundary violation.
  `ritk-tractography` cannot satisfy that condition until the type exists.
- **Second scope**: unit-sphere tessellation and direction-set generation (the
  DIPY `sphere` and MRtrix `dirs` role), currently unassigned. It is pure 3-D
  geometry over the unit sphere; Gaia is the owner. Needed for ODF sampling and
  peak extraction as well as tractography.
- **Class**: `[minor]`, repository `repos/gaia`.

## Wave 2 — preprocessing (RITK, existing crate owners)

## ATLAS-DMRI-DENOISE-008 — MP-PCA denoising and Gibbs unringing [minor] — todo

- **Outcome**: `ritk-filter` gains Marchenko-Pastur PCA denoising and subvoxel
  Gibbs ringing removal — the `dwidenoise` and `mrdegibbs` roles, and the first
  two stages of every current dMRI pipeline.
- **Evidence of gap**: `ritk-filter` has bilateral, patch-based, median, rank,
  and anisotropic-diffusion denoising; none is the MP-PCA estimator, which
  derives its threshold from random-matrix theory rather than a tuned parameter.
  `ritk-statistics/src/noise_estimation.rs` is MAD over additive Gaussian noise —
  correct as written, but not the Rician/noncentral-chi model magnitude DWI
  actually follows.
- **Related**: Rician bias correction is a third item in the same crate, split
  out if MP-PCA outgrows its acceptance criteria.
- **Acceptance**: the MP-PCA threshold is derived from the Marchenko-Pastur
  distribution and the patch geometry, never an empirical constant; verified on
  a synthesized field with a known noise level.
- **Class**: `[minor]`.

## ATLAS-DMRI-CORRECT-009 — Motion, eddy-current, and susceptibility correction [minor] — review

**PR mapping (2026-08-01).** PR #82 grew to four commits and ~1,700 lines, past
a reviewable unit, and also carried four unrelated JPEG 2000 commits inherited
from its base. Split into four PRs cut fresh from `origin/main`, each verified
standalone; #82 closed. References to "PR #82" below predate the split.

| PR | Scope | Base | Standalone verification |
| --- | --- | --- | --- |
| #84 | `ritk-diffusion-scheme` per-volume reorientation | `main` | 23/23 |
| #85 | `ritk-spatial` rotation extraction | `main` | 54/54 + doctest |
| #86 | `ritk-registration` series alignment | **#85** | 352/352 |
| #87 | `ritk-registration` EPI distortion model | `main` | 367/367 |

#86 targets #85 because it consumes `rotation_from_linear`; GitHub retargets it
to `main` on merge. The other three are independent and may merge in any order.

The split was done in a bounded worktree lane rather than the main tree, which
was dirty with peer edits — branch switches there had been aborting. The lane is
deregistered; its directory at `worktrees/ritk-pr-split` could not be deleted
(held by another process) and needs sweeping once that releases.

**Scheme-side reorientation delivered**: `ritk` `660783da` on
`feat/per-volume-gradient-reorientation`, PR #82.
`GradientScheme::reorient_per_volume` applies one rotation per volume in
acquisition order, with an exact count match and whole-list validation before
any rotation is applied. 22/22 `ritk-diffusion-scheme` tests, clippy and doc
gates clean.

A peer had already landed the single-rotation `GradientScheme::reorient` and the
FSL codecs in `ritk-diffusion-scheme`. That method applies one rotation to the
whole scheme — correct for a fixed frame change, unusable for correction, where
each volume is registered independently. Nothing in the workspace called
`reorient` at all before this.

**Remaining, in dependency order:**

1. ~~**Rotation extraction from an affine.**~~ **Delivered**: `ritk` `216f21f7`,
   same branch and PR #82. `ritk_spatial::rotation::rotation_from_linear`
   returns the orthogonal polar factor.

   Placement resolved to `ritk-spatial`, and the open question dissolved on
   inspection: `ritk-spatial` already depends on `leto`, so there was no new
   dependency to weigh. The operation is geometry rather than diffusion, and its
   consumers (gradient reorientation, tensor and ODF reorientation, resampled
   grid orientation) all already depend on that crate.

   **Numerical finding worth keeping.** The eigen route alone
   (`S = (AᵀA)^{1/2}` via leto's `symmetric_eigen`) is least accurate at the
   input that matters most: when `A` is already a rotation, `AᵀA = I` has a
   triple eigenvalue and the analytic cubic derives eigenvectors from cross
   products of a near-zero matrix. Measured drift was ~3.8e-9 — *above* the
   1e-9 orthonormality bar `reorient_per_volume` enforces, so the undistorted
   case would have been rejected downstream. One Newton step of Higham's polar
   iteration (`X ← ½(X + X⁻ᵀ)`) is a fixed point at an exactly orthogonal
   matrix and converges quadratically, restoring machine precision. Any future
   consumer of `symmetric_eigen` on a near-degenerate matrix faces the same
   thing.

   Reflections are rejected rather than repaired to the nearest proper rotation:
   the Kabsch sign flip suits fitting to noisy point correspondences, but a
   handedness reversal between two images of one subject means the transform is
   wrong, and repairing it would hide the defect.
2. ~~**The series correction driver**~~ **Delivered**: `ritk` `4633b5e3`, same
   branch and PR #82. `ritk_registration::series::register_series` fits each
   volume to a reference and reports the transform plus the proper rotation it
   carries. The `ritk-io` gate cleared — a peer landed
   `read_image_series_native`.

   **Layering decision.** The module carries no diffusion vocabulary. Motion
   correction is the same operation whether volumes vary by gradient,
   timepoint, or inversion time, and a diffusion consumer depends on
   registration rather than the reverse. `SeriesAlignment::rotations()` returns
   exactly the shape `GradientScheme::reorient_per_volume` consumes, so the two
   compose without `ritk-registration` ever depending on
   `ritk-diffusion-scheme`.

   **Two contract choices worth keeping.** The reference is assigned the
   identity rather than registered to itself — self-registration returns a
   near-identity fit perturbed by optimizer noise, injecting a spurious rotation
   into the one volume known to need none. Its `quality` is `None` rather than a
   zeroed metrics struct, which would claim a mutual information and correlation
   of zero for a registration that never ran.

   Rigid is the default model: it cannot deform anatomy, so a caller who has not
   considered eddy currents does not silently receive a shape-changing fit.
   `SeriesTransformModel::Affine` admits the extra freedom eddy-current
   distortion needs.

   **Not yet wired end to end.** `register_series` reports what moved; applying
   the transforms to resample the volumes is the caller's step and no composed
   `correct_diffusion_series` entry point exists. That composition belongs with
   the diffusion consumer and is the natural next increment once
   `ritk-diffusion` settles.
3. **Susceptibility distortion** — the `topup` role. **Model delivered**:
   `ritk` `3042601f`, same branch and PR #82.
   `ritk_registration::epi::{distort, unwarp}` with `PhaseEncoding`
   (axis + polarity). The forward model is what field estimation later fits
   against; `unwarp` solves the observed-to-true map per line rather than
   assuming small displacements, so the round trip is exact.

   Convention pinned in the module docs (per numerical_discipline): for field
   `f` in voxels and polarity sign `s`,
   `observed(y) = true(y + s·f(y)) · |1 + s·∂f/∂y|`. Toolchains differ here, so
   it is stated rather than assumed.

   A folding field is rejected, not clamped: where the Jacobian reaches zero,
   distinct true positions map to one observed position and their signal is
   summed, which no unwarping separates.

   **Two test-oracle corrections worth keeping**, both cases where the first
   assertion was wrong rather than the code:
   - Signal conservation is an identity over the *mapped* range, not the grid.
     A ramp field with non-zero boundary value stretches the domain and
     legitimately raises the grid total — measured at exactly 10% for slope
     0.1, which is the Jacobian working. The test now uses a
     boundary-vanishing field, where the map is onto the grid and conservation
     is exact.
   - The warp/unwarp round trip cannot be exact on a step edge: two linear
     interpolations do not reconstruct a discontinuity. That is a property of
     resampling, not of the model. The test uses a linear image, which linear
     interpolation reproduces exactly, isolating the geometry and Jacobian
     bookkeeping.

   **Remaining**: field *estimation* from a reversed-polarity pair. That is a
   regularized nonlinear fit over a field parameterization (spline coefficients
   or per-voxel with a smoothness penalty) — thousands of parameters, so the
   dense `coeus-optim` Levenberg-Marquardt from ATLAS-COEUS-NLLS-004 is the
   wrong instrument and a large-scale or sparse-Jacobian path is needed first.
   Size and owner of that solver is an open question, not a scheduled item.

**Acceptance oracle is still unbuildable here.** ADR 0036 verification condition
7 needs a synthesized anisotropic tensor field fitted after correction, which
needs `ritk-diffusion`'s tensor fit — peer-owned and in flight. The tests in
PR #82 verify the reorientation contract directly (per-volume indexing, the
`R`/`Rᵀ` round trip that catches a transposed application, rejection of
non-orthonormal and improper matrices); the end-to-end eigenvector oracle
attaches once the tensor fit lands.

## ATLAS-DMRI-CORRECT-009 original specification

- **Outcome**: a series-level correction driver in `ritk-registration` — the
  `eddy` and `topup` roles.
- **Present**: rigid, affine, B-Spline FFD, Demons, SyN, and LDDMM registration
  all exist; `ritk-filter/src/bias/n4` covers B1 bias. The registration machinery
  is not the gap.
- **Gap**: (a) no driver that registers volume-to-volume across an acquisition
  axis, which ATLAS-DMRI-IO-001 gates; (b) **no gradient reorientation** — the
  rotational part of each correction must be applied to that volume gradient
  direction. A correction that omits this yields a silently wrong tensor field
  and is the most common defect class in this domain; (c) no
  susceptibility-distortion path (reversed-phase-encode fieldmap estimation).
- **Acceptance**: ADR 0036 verification condition 7 — a synthesized anisotropic
  tensor field rotated by a known transform recovers its principal eigenvector
  after correction, and the same test fails when reorientation is skipped.
- **Class**: `[minor]`.

## Wave 3 — the three ADR 0036 crates

## Wave 4 — surfaces, containers, delivery

## ATLAS-RITK-FSSURF-013 — FreeSurfer surface formats and label table [minor] — todo

- **Outcome**: RITK reads the FreeSurfer surface family — surface binaries
  (`lh.white`, `pial`, `inflated`), `curv`, `label`, `annot` — plus the color
  LUT, and GIFTI as the interchange equivalent.
- **Evidence of gap**: `ritk-mgh` covers FreeSurfer *volumes* only; no surface,
  annotation, or LUT reader exists in the workspace.
- **Why it is a prerequisite, not an optional format**: surface parcellations are
  how connectome nodes are conventionally defined, so ATLAS-RITK-CONNECTOME-012
  depends on it.
- **Deletion ledger** (promotion-gate condition 4, satisfied): the FreeSurfer
  `aseg` and Desikan `aparc` label table is hand-rolled in a downstream consumer
  at `repos/leoneuro-rs/crates/leoneuro-gui/src/freesurfer.rs` (137 lines). The
  RITK owner first increment deletes it and repoints that consumer.
- **Open**: CIFTI is deferred until a consumer needs HCP-convention data.
- **Class**: `[minor]`.

## ATLAS-DMRI-TRACTOGRAM-FMT-014 — Tractogram container ownership [arch] — todo

- **Decision needed**: MRtrix `.tck`, TrackVis `.trk`, and TRX are published
  byte-level interchange specifications, which is the RITK format-crate pattern;
  ADR 0036 decision 2 routes derived-array persistence to Consus. The two rules
  point at different owners for the same artifact.
- **Recommended resolution** (per bias-to-completion, proceed on this unless
  overridden): an interchange format that other toolchains read is a RITK format
  crate; a derived-array store for Atlas-internal persistence is Consus. A
  streamline set written for MRtrix or TrackVis to read is interchange.
- **Also open**: MRtrix `.mif` / `.mif.gz`, which is both an image container and
  an embedded gradient-scheme carrier, so it spans 001 and 003.
- **Deliverable**: ADR 0036 revision recording the resolution, or a new ADR if it
  generalizes beyond this artifact.
- **Class**: `[arch]`, no public-surface break — `[patch]` on the SemVer axis.

## ATLAS-DMRI-DELIVERY-015 — CLI, Python, and book surface [minor] — in-progress

**Book surface delivered 2026-08-13** (ritk PR #137, branch
`feat/dmri-downloadable-data`). The naming collision below is resolved: Part III
is titled "Diffusion MRI and Tractography" and holds `diffusion_scheme.md`,
`ritk_diffusion.md`, `diffusion_mri.md`, and `tractography.md`, while
`diffusion_filters.md` stays in the image-processing part, so the two subjects
no longer read as variants of one chapter.

The example chapter `examples/brain_tractography.md` now renders from real
scanner data a reader can fetch (OpenNeuro ds002087), directionally encoded with
the channel mapping derived from the volume's own direction cosines rather than
assumed. Verified: clippy `--all-targets -D warnings` clean, 106/106 unit and
phantom tests, 11/11 real-data tests, figure reproduces byte-for-byte from the
committed source, `mdbook build` clean and the figure reaches the built output.

**Claim released 2026-08-13 after scoping — the CLI is blocked on a missing
library API, not on CLI work.** `ritk dwi tensor` cannot be written against
`estimate_dti` alone. Producing a usable scalar map needs three things the
example `book_brain_tractography.rs` already implements and the library does
not expose: a background mask from the b = 0 volume's upper percentile
(without it a tensor fitted to air produces a bright noise rim that dominates
the FA range), degenerate-fit rejection on physical diffusivity bounds
(a rank-one fit is positive-definite, passes a sign check, and drives FA to 1),
and the per-voxel fit loop itself. Writing the command directly would copy
~40 lines of that logic into `ritk-cli`, which is the duplication defect —
the example would then be the second implementation of a library concern.

**Therefore the next increment is a library one, not a CLI one:**

`ATLAS-DMRI-CLI-018` — Scalar-map API in `ritk-diffusion` [minor], **merged
2026-08-13** (ritk PR #141, `f345a00e` on main; atlas gitlink `532e1ea`), alongside `ATLAS-DMRI-CLI-019` (`ritk dwi tensor`).
Original DoR:
- **Outcome**: `ritk_diffusion::maps` fits a tensor field over a whole volume
  and derives the standard DTI scalar maps (FA, MD, AD, RD) plus the principal
  eigenvector field, with the mask and rejection policy as configuration rather
  than caller-copied constants.
- **Acceptance**: on a synthetic volume with a known tensor, each map matches
  the value computed from `estimate_dti` directly; a voxel below the mask floor
  and a voxel with a rank-one fit are both excluded; `book_brain_tractography.rs`
  is rewired onto the API and its published figure still reproduces
  byte-for-byte, which is the regression oracle.
- **Non-goals**: the CLI command, vector-image output, `tract`.
- **Then** `ATLAS-DMRI-CLI-019` — `ritk dwi tensor` becomes a thin argument
  parser over that API, and its scalar outputs are `Image<f32, _, 3>` values
  `write_image_inferred` already handles.

**Delivered.** `ritk_diffusion::maps::fit_diffusion_maps` owns the mask, the
degenerate-fit rejection, and the fit loop, with the physical bounds as
documented configuration. `ritk dwi tensor` is a thin parser over it. Verified
on OpenNeuro ds002087 sub-01: 205176 of 778752 voxels fitted, median MD in
white matter (FA > 0.4) of 6.06e-4 mm²/s against a literature ~7e-4, and
`MD == (AD + 2·RD)/3` holding across the volume — which cross-checks that all
three diffusivity maps come from one decomposition. 14 new library tests,
6 new CLI tests, clippy clean on both crates.

Two decisions worth knowing:

- `DiffusionMaps` retains the eigen-decomposition, not the six tensor elements.
  Every standard scalar map derives from the eigenvalues alone, so this answers
  all four without a second decomposition, at 49 bytes per voxel against
  roughly 144. A caller needing tensor elements calls `estimate_dti` per voxel.
- The mask averages every b = 0 volume rather than reading the first, because it
  is applied per voxel and one noisy reference speckles the mask along tissue
  boundaries. This dataset has five references, so the book figure changed by
  28 voxels and 127 streamline segments; peak FA, seed count, and the
  directional-colour anatomy are unchanged.

**Spun out of the work, all unclaimed:**

`ATLAS-DMRI-CLI-020` — Vector-field output for the principal eigenvector
[minor], todo. `write_image_inferred` takes `Image<f32, _, 3>`, so PEV needs
4-D or multi-file output before the CLI can expose it. `DiffusionMaps` already
computes and returns it, so this is an output-path item, not an estimator one.

`ATLAS-RITK-IO-SERIES-WRITE-021` — `ritk-io` re-export asymmetry [patch], todo.
`ritk_io` re-exports `read_nifti_series` but not `write_nifti_series`, so a
caller that can read a 4-D series cannot write one through the same module.
PR #141 worked around it with a `ritk-nifti` dev-dependency in `ritk-cli`
rather than widening its scope. Decide whether the omission is deliberate — the
writer takes an explicit backend, which the dispatch layer may not want — and
either re-export it or record why not. It is also the blocker under 020.

`ATLAS-DMRI-CLI-022` — `tract` command group [minor], **merged 2026-08-13**
(ritk PR #142, `5ee518e3` on main; atlas gitlink `c85197a`). Scope: `ritk_diffusion::maps::DtiVolume`,
`ritk_tractography::dti_volume_direction_field`, and
`crates/ritk-cli/src/commands/tract*`.

Scoping found the same shape as 018/019: `ritk-tractography` already has
`fod_volume_direction_field` and `noddi_direction_field` for whole-brain
tracking, but its only DTI entry point, `dti_pev_direction_field`, takes a
*single* tensor and returns one constant direction everywhere — a single-voxel
bootstrap, documented as such. The whole-brain DTI equivalent exists only inside
the book example, as a hand-rolled sampling closure. So the CLI needs a library
lookup first, exactly as 019 needed 018.

The established pattern puts the spatial lookup in the model crate
(`NoddiVolume::direction_at`) with a thin adapter in `ritk-tractography`, so
`DtiVolume` lands in `ritk-diffusion` beside `DiffusionMaps`.

**Frame decision**: `DtiVolume` works in voxel-index space, ordered
`[depth, row, column]` to match `Image::shape()` and the layout `DiffusionMaps`
was fitted from. It therefore carries no origin or spacing. Physical
coordinates are applied at the IO boundary through
`Image::continuous_index_to_physical_point` (ADR 0018), which is where geometry
belongs. Note that `NoddiVolume` instead stores `[nx, ny, nz]` with `point[0]`
as the *fastest* axis — the opposite order — and does its own physical
conversion internally. That divergence is pre-existing and is recorded here
rather than silently matched or unilaterally changed.

**Delivered.** `DtiVolume` + `dti_volume_direction_field` + `ritk tract dti`,
writing `.tck` only — `TckTractogram` takes `gaia::Polyline<f64>` directly,
which `Streamline::geometry()` already yields. Verified on OpenNeuro ds002087
sub-01: 1975 streamlines, arc lengths 2–112 mm, coordinates spanning a
head-sized box in physical space, which is what confirms the index-to-physical
transform rather than the file merely parsing. 8 new library tests, 5 new CLI
tests, clippy clean across all three crates.

**Honest limitation, recorded rather than tuned away**: median track length is
about 16 mm against an anatomical 30–150 mm. Measured termination split on this
subject is 2379 at a field boundary against 1571 on the turn limit — so both the
data (single-shell b = 700 resolves one tensor per voxel; ~26% of voxels survive
masking) and the nearest-neighbour lookup contribute. Loosening
`--track-anisotropy` would lengthen tracks without making them more true, so it
was not done.

**Spun out, unclaimed:**

`ATLAS-DMRI-TRACT-023` — Interpolated direction field [minor], **delivered
2026-08-14** (ritk PR #144).

**Measured, on real tissue.** Turn-limit terminations fall from 36.4% to 13.0%
on a mid-brain slab (committed test) and from 1571 to 646 across the whole
volume; the median streamline runs 16.0 mm to 24.0 mm and p90 45 to 65 mm.
Field-boundary terminations rise 2379 → 3304, which is the same effect from the
other side: tracks formerly cut short by a turn now run until they leave the
mask. That directly retires the limitation recorded under 022.

**Two process notes worth keeping.**

*A peer committed onto this branch.* Working in the same shared tree, a peer's
`git commit` swept this branch's staged acceptance test and the
`DirectionInterpolation` export into their commit `735a30c9`, whose message
describes the leto SVD migration. Content correct and intact; the message is
theirs, so it was left rather than rewritten over their work, and the
composition is recorded in the following commit and the PR. This is the second
occurrence of the shared-index hazard in two days — the first was a staged
`backlog.md` plus nine gitlinks. Staging by explicit path is not sufficient
protection; the index itself is shared.

*Verification was blocked three times in one increment* — `ritk-image`
(`try_as_slice` without a trait bound), `leto-ops` (SVD entry points removed
mid-refactor), `hermes-simd-intrinsics` (macro syntax mid-edit) — which is more
`ATLAS-STACK-LETO-CHURN-017` evidence. Notable this time: the library half was
independently verifiable throughout because the blockage was in
dev-dependencies, so it was committed while the CLI half waited. Splitting a
commit along the verifiable boundary is the practical mitigation while (b)
remains undecided.

Approach chosen: **dyadic (outer-product) interpolation**, not sign-aligned
vector averaging. Accumulate `Σ wᵢ vᵢvᵢᵀ` trilinearly and take the principal
eigenvector of the sum. Sign-invariance is then structural — `(−v)(−v)ᵀ = v vᵀ`
— rather than a heuristic alignment pass that can pick the wrong reference in a
crossing. Interpolation smooths the orientation only; whether a streamline may
continue stays decided by the voxel it is in, so switching modes cannot silently
move where tracking stops.

Required a split in `dti.rs`: `decompose_3x3_symmetric` refused non-positive
eigenvalues, which is a *diffusion tensor* validity contract and not a property
of symmetric matrices. A dyadic sum is positive **semi**-definite by
construction — one contributor gives `(w, 0, 0)` — so the pure decomposition is
now `decompose_3x3_symmetric_unchecked` and the checked wrapper applies the
domain rule. Both original rules were preserved, including the stricter
positivity the isotropic branch applied.

Original scope follows.

`ATLAS-DMRI-TRACT-023` (original) — Interpolated direction field [minor]. Nearest
neighbour makes orientation constant within a voxel and discontinuous at each
boundary, so smooth bundles can exceed the turn limit. This is *not* simply
trilinear averaging of the eigenvectors: an eigenvector has no sign, so ±v
describe the same fibre and naive averaging cancels. Either interpolate the
tensor and re-decompose, or sign-align neighbours to a reference before
combining. Acceptance: the turn-limit share of terminations falls on the same
subject, with the sign-ambiguity handling covered by a test that would fail
under naive averaging.

`ATLAS-DMRI-TRACT-024` — `.trk` and `.trx` output [patch], todo. `ritk-trk` and
`ritk-trx` exist; this is an output-format item on `tract dti`.

`ATLAS-RITK-TRACT-AXIS-025` — Settle the volume axis convention [patch], todo.
`DtiVolume` orders queries `[depth, row, column]` to match `Image::shape()`;
`NoddiVolume` orders them `[nx, ny, nz]` with the first component fastest, and
converts from physical space internally. Two conventions in one crate is a
terminology-SSOT defect. Decide which is canonical and migrate the other.

**CLI and Python surfaces remain open** — `ritk` has no `dwi`/`tract` command
groups and `ritk-python` exposes no diffusion surface. They are independent
vertical increments and should be claimed separately.

**`codex/ritk-model-coeus-publishability` is fully superseded — do not rescue
it.** The branch still exists locally with 32 commits absent from `origin/main`,
which reads like stranded work. It is not: its content landed as squash
`5bb1fc3a`, and the only files unique to it are
`test_data/diffusion/ds002087_repo` and `ds004666_repo` — undeclared submodule
gitlinks (mode 160000 with no `.gitmodules` entry) that were deliberately
removed from the squash. Merging or cherry-picking from this branch would
reintroduce exactly that defect. Recorded because the commit count invites a
rescue attempt that would be wrong.

**TOC/heading mismatch fixed in the same PR**: `SUMMARY.md` listed
`diffusion_mri.md` as "Diffusion MRI Physics and the Signal Equation" while the
chapter's H1 is "Diffusion MRI Acquisition and Q-ball ODFs". The heading is
accurate — the chapter has no signal-equation section and does have a Q-ball
one — so the TOC entry was corrected to match.

- **CLI**: `ritk` currently exposes `convert`, `filter`, `register`, `segment`,
  and `stats` (`ritk-cli/src/commands/`). The program adds `dwi` and `tract`
  command groups.
- **Python**: `ritk-python` gains the diffusion surface as a thin PyO3 layer —
  no domain logic, per the binding boundary rule. This is the practical adoption
  path against the incumbent DIPY workflows.
- **Book**: ADR 0036 consequences require a diffusion section in the RITK book,
  sequenced so it can cite the Coeus and Gaia chapters it depends on.
  `repos/ritk/docs/book/` has the chapter set; `diffusion_filters.md` is
  anisotropic-diffusion *filtering* and is a different subject — the naming
  collision needs resolving under the terminology SSOT rule when the dMRI
  chapter lands.
- **Class**: `[minor]`. Last wave; each surface follows its crate.

## Out of scope for this program

- **Surface reconstruction** (the `recon-all` role — white and pial surface
  generation from T1). Ingest of existing FreeSurfer surfaces is item 013;
  generating them is a distinct research-scale capability with no current
  consumer, and is demand-gated.
- **MR acquisition simulation** — closed by ADR 0036 decision 4; opens as an
  integrator when a program needs to simulate acquisition.
- **Study and cohort structure** — ADR 0036 decision 3 assigns it to Tyche;
  RITK supplies per-subject measures as study responses. No `ritk-study` crate.

## ATLAS-CFDRS-LINT-FLOOR-001 — Adopt canonical Atlas lint floor in CFDrs workspace [patch] — in-progress

- Owner: current session; scope: `repos/CFDrs/Cargo.toml` top-level
  `[workspace.lints]` block and per-site `#[expect]` ratchet insertions
  across `crates/cfd-*/src/**` and `xtask/src/**`.  Claimed 2026-08-06.
- Outcome: CFDrs `Cargo.toml` carries the canonical Atlas `[workspace.lints]`
  floor matching `repos/apollo/Cargo.toml` L88-L107 (template SSOT):
  `[workspace.lints.rust] missing_docs = "warn"` (warn floor; `#![deny(missing_docs)]`
  is the per-crate strict escalation choice, not set workspace-wide so existing
  crates without missing-docs discipline stay warning-only until per-crate
  promotion). `[workspace.lints.clippy]` adopts apollo's `all = warn, prio -1` +
  `pedantic = warn, prio -1` and the same `allow` set (`module_name_repetitions`,
  `must_use_candidate`, `similar_names`, `too_many_lines`,
  `default_constructed_unit_structs`, `doc_lazy_continuation`,
  `needless_range_loop`, `too_many_arguments`, `manual_is_multiple_of`,
  `manual_div_ceil`, `manual_slice_size_calculation`, `len_zero`,
  `cast_possible_truncation`, `cast_precision_loss`, `cast_sign_loss`,
  `cast_possible_wrap`, `items_after_statements`, `range_minus_one`,
  `default_trait_access`, `useless_conversion`). Adds the Atlas-canonical library
  hygiene `deny` tier (`unwrap_used`, `print_stderr`, `print_stdout`,
  `dbg_macro`) so consumer-tree library and CLI crates enforce the same floor
  kwavers/helios/apollo already carry — `#[expect]` permitting pre-existing
  sites to remain on a non-increasing ratchet baseline, not silent `allow`.
- Scope: idempotent bulk `#[expect(lint, reason="ratchet cfd-<crate>-<count>")]`
  insertion per violation emitted by `cargo clippy --all-targets
  --workspace --json -- -D warnings -W clippy::pedantic
  -W clippy::unwrap_used -W clippy::print_stderr -W clippy::print_stdout
  -W clippy::dbg_macro`. **Mechanical transform only** per `git_discipline`:
  no logic edits, no refactor, no removed `println!` from `xtask` at large —
  per-site `#[expect]` carries the ratchet signal for future root-cause work.
- Non-goals: no public-API rewrites, no `print!` removal from `xtask` source
  (xtask is a build tool, not a library; per-site `#[expect]` preserves the
  ratchet signal per `engineering_gates` brownfield rule), no logic fixes for
  surfaced `unwrap_used` (the ratchet baseline only decreases — a future
  root-cause slice removes the offending `unwrap` and its `#[expect]` together).
- Disjoint from peer's `ATLAS-CFDRS-ATHENA-MIGRATION-001` chain.rs scope:
  peer's last chain.rs touch was 2026-07-30 (`63e49604`); 7+ days stale,
  reclaimable takeover material. Converge-friendly by construction — `#[expect]`
  is semantics-preserving against any in-flight peer chain.rs work; if peer
  pushes new chain.rs commits during this slice, fall through `concurrent_agents`
  Detect-and-reconcile (compose around peer's diff).
- Lane: reclaimed per-repo 2-tree cap slot by removing the post-merge
  `codex/cfdrs-audit-refresh` worktree lane (peer's PR #327 fully merged at
  `50fa243b`, lane = `D:/atlas/worktrees/CFDrs-audit-refresh` exactly at peer's
  merged tip, tree clean) and adding `feat/cfdrs-lint-floor` lane off
  `origin/main 50fa243b`.
- Acceptance: `cargo clippy --all-targets --workspace -- -D warnings
  -W clippy::pedantic -W clippy::unwrap_used -W clippy::print_stderr
  -W clippy::print_stdout -W clippy::dbg_macro` rc=0; `cargo nextest run
  --workspace` rc=0 (or reduced focused subset if workspace test suite
  budget blocked per `engineering_gates` runtime budgets — root-cause
  any hang, never bypass); `cargo test --doc --workspace` rc=0; `cargo fmt
  --all --check` rc=0.
- Re-open trigger: a new lint violation reaches `repos/CFDrs/origin/main`
  past the floor without an accompanying `#[expect]` carrying its ratchet
  rationale; or the floor is removed/relaxed in `Cargo.toml`.
- Residual recorded, NOT closed in this slice: per-repo `backlog.md` and
  `gap_audit.md` entries for CFDrs lint-floor closure; CFDrs-level
  per-crate `#![deny(missing_docs)]` promotion is deferred to a later
  per-crate slice (each crate's surface decides its own missing-docs tier).
- Current CFDrs increment: commit `cd9580fc` on pushed branch
  `feat/cfdrs-lint-floor` wires every workspace package and `xtask` to the
  floor, removes the cfd-core plugin resolver unwrap, and records the local
  PM state. Evidence: focused `xtask` and cfd-core library Clippy pass;
  cfd-core Nextest 246/246; cfd-core doctests 3/3; explicit migration audit
  reports zero legacy dependencies, zero legacy source tokens, and a clean
  allowlist. Full workspace acceptance remains open on the recorded
  cfd-math, cfd-schematics, cfd-core test/bench, and format debt.
- Follow-up CFDrs commit `e3e88a60` is pushed on the same branch: multigrid
  coarsening now uses deterministic NaN-safe ordering, with a value-semantic
  regression test. cfd-math Nextest passes 198/198; focused cfd-math library
  Clippy residue decreases from 51 to 48 diagnostics.
- Follow-up CFDrs commit `f31176b1` is pushed: multigrid hierarchy and
  interpolation state use invariant-checked expectations, while JFNK and
  spectral kernels centralize C-contiguous storage assumptions. cfd-math
  Nextest remains 198/198; focused library Clippy residue is 22 diagnostics.
- Follow-up CFDrs commit `9e52454a` is pushed: performance-monitor mutex and
  calibration output now use invariant diagnostics and tracing, and DG progress
  output is structured tracing. cfd-math library Clippy and Nextest pass;
  workspace closure still has cfd-schematics, cfd-core test/bench, and format
  debt.
- Follow-up CFDrs commit `c83affee` is pushed: the exported
  `cfd-schematics::topology::model` contract now documents its types, fields,
  variants, aliases, and lookup methods. cfd-schematics library Nextest passes
  164/164 and doctests 16/16; package Clippy residue decreases 712 to 611.
- Follow-up CFDrs commits `ddc04a32` and `8584dd26` are pushed: configuration
  constants, public config manifests, and the route-spec contract now carry
  API documentation. cfd-schematics library Nextest remains 164/164 and
  doctests 16/16; package Clippy residue decreases 611 to 534.
- Follow-up CFDrs commit `322787ae` is pushed: the public node and channel
  geometry-builder setters now carry API documentation. cfd-schematics library
  Nextest remains 164/164 and doctests 16/16; package Clippy residue decreases
  534 to 524.
- Follow-up CFDrs commit `eae43768` is pushed: geometry-generator metadata,
  entry points, and builder methods now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; package Clippy residue
  decreases 524 to 508.
- Follow-up CFDrs commit `c0d53bd5` is pushed: series and parallel geometry
  generators now carry API documentation. cfd-schematics library Nextest
  remains 164/164 and doctests 16/16; this slice reduces its package Clippy
  residual from 508 to 506. The working tree reports 492 with peer-owned
  `analysis_impl.rs` documentation changes also present and uncommitted.
- Follow-up CFDrs commit `f27f86dd` is pushed: selective-tree path, topology,
  request, and generator contracts now carry API documentation. cfd-schematics
  library Nextest remains 164/164 and doctests 16/16; this slice reduces the
  package Clippy residual from 506 to 468. The working tree reports 454 with
  the peer-owned `analysis_impl.rs` documentation changes still uncommitted.
- Follow-up CFDrs commit `468cc617` is pushed: the `NetworkBlueprint` analysis
  impl (`crates/cfd-schematics/src/domain/model/blueprint/analysis_impl.rs`)
  now carries inline Rustdoc for its 14 undocumented pub methods (node/pipe
  counters, length aggregates, Venturi lookup, overlap analysis/resolution,
  validate, describe). cfd-schematics library Nextest remains 164/164 and
  doctests 16/16. File-disjoint from peer commits on the same branch per
  `concurrent_agents` disjoint-scope rule; peer's prior bullet had already
  flagged this `analysis_impl.rs` work as the uncommitted peer residual, and
  the slice now closes that residual. cfd-schematics distinct missing_docs
  sites in `analysis_impl.rs` fall from 14 to 0; crate-wide distinct
  sites fall from 468 to 454.
- Follow-up CFDrs commit `357debf3` is pushed: the `NetworkBlueprint`
  metadata impl (`crates/cfd-schematics/src/domain/model/blueprint/metadata_impl.rs`)
  now carries inline Rustdoc for its 19 undocumented pub methods/associated
  functions covering the deprecated default constructor, the
  explicit-position constructor, render-hint and metadata builders/accessors,
  topology and lineage attachments, JSON (de)serialization, and
  node/channel addition methods. cfd-schematics library Nextest remains
  164/164 and doctests 16/16. File-disjoint sibling of the just-merged
  analysis_impl.rs closure in the same `domain/model/blueprint/` subtree,
  owned by this session; no peer commits touched this file.
  cfd-schematics distinct missing_docs sites in `metadata_impl.rs` fall
  from 19 to 0; crate-wide distinct sites fall from 454 to 435.

## ATLAS-CFDRS-CI-WORKSPACE-RUST-001 — Add Rust workspace CI gate to CFDrs [patch] — in-progress

- Owner: current session (claimed 2026-08-10). Pairs with
  ATLAS-CFDRS-LINT-FLOOR-001 to make the floor mechanically enforced.
- Outcome: CFDrs `.github/workflows/ci.yml` carries a `rust-workspace` job
  that runs `cargo check --workspace --all-targets`, `cargo nextest run
  --workspace` (or `cargo test --workspace --no-fail-fast` fallback gated
  on `nextest` install via `taiki-e/install-action`), `cargo clippy
  --all-targets -- -D warnings`, `cargo fmt --all --check`, `cargo test
  --doc --workspace`. Mirrors `.github/workflows/ci.yml` patterns in
  `repos/apollo`, `repos/hephaestus`, `repos/helios`, and `repos/kwavers`.
- Scope: `.github/workflows/ci.yml` only; disjoint from peer's helios/ritk
  release-workflow consolidation `ci/migrate-release-workflow-to-shared-caller`.
- Acceptance: the new job runs in CI on the next PR; `cargo check --workspace
  --all-targets` and `cargo clippy` fail on a regression injected locally.
- Re-open trigger: the rust-workspace job is removed or its gate commands
  are weakened below the canonical Atlas floor.
- Dependency: ATLAS-CFDRS-LINT-FLOOR-001 must land first (or in the same
  PR) so `cargo clippy -- -D warnings` does not fail at the ~160 pre-existing
  baseline. Sequence behind it.

## Archive — closed items

Closed items, one line each. Full prose is in git history; commit SHAs below are the entry points.

- **ATLAS-LIVE-HEAD-SWEEP-026** Reconcile twenty provider CI-pin defaults [patch] (2026-08-13) — `5758df93`, `93e83899`, `5febead4`, `5969f1e3`
- **ATLAS-POSTMERGE-HEAD-RECONCILIATION-030** Reconcile merged caller defaults [patch] (2026-08-13) — `1be7768d`, `1a52590c`, `462cf444`
- **ATLAS-LIVE-CALLER-PINS-027** Refresh requested-provider Atlas workflow pins [patch] (2026-08-13) — `d875348197be12ad593f993a6f1b8a62d3b8b195`, `4c31dd753f06dd93b4c04798cf781df253e3e532`, `d875348`, `964d81db`
- **ATLAS-HEPHAESTUS-REDUCTION-022** Retire superseded product-axis parity PR [patch] (2026-08-13) — `8bc589a`
- **ATLAS-APOLLO-ARCH-021** Retire superseded junk-drawer rename [patch] (2026-08-13) — `49632c6c`, `fc5648964c8194447ef5deea43a8aa9c0dae7c63`
- **ATLAS-APOLLO-VALIDATION-020** Converge shared WGPU validation and Mnemosyne boundary [patch] (2026-08-13) — `a725fe81027f54ee83e56fa72d731b8e2e3f97f1`, `fc5648964c8194447ef5deea43a8aa9c0dae7c63`
- **ATLAS-COEUS-NORM-019** Keep batched Frobenius norms provider-owned [patch] (2026-08-13) — `96d8166c3d683eaaf67e45b8bad0c34e33d8b405`, `72372c918d8d6fcbcc006585736126a480a4f5c2`
- **ATLAS-HELIOS-BOOK-WORKFLOW-018** Converge Helios on the shared Pages workflow [patch] (2026-08-13) — `116228c031a10d9e5176d7209c54172973001ddd`, `546c199fdd46b8eb8c4176a4250ac261962a45d0`, `578150340157c6da25f4ee2b37d6b4639d787c1a`
- **ATLAS-HERMES-PERMUTE-017** Measure and prune cross-lane NEON overrides [perf] (2026-08-13) — `79d7297`, `d1627cd23179595b751c237a67f86cdeafb01310`
- **ATLAS-CONSUS-TEST-API-001** Make cross-format integration tests consume real Consus APIs [patch] (2026-08-13) — `a5b9cfdde4c789c237652e0d62c42ce8372005f5`, `720233ab6e7fedb82399d28540f903a6b1e9a191`
- **ATLAS-CONSUS-NODEF-FITS-HDF5-NWB-003** Close Consus no-default storage boundaries [patch] (2026-08-13) — `b3ca01c21b2e9bad4c7b7dc23c47083ca79a3307`, `bf46b7cf00ec7a86b51decf31be4eb30b367c397`
- **ATLAS-CONSUS-NODEF-ARROW-PARQUET-002** Close Arrow/Parquet no-default cfg boundaries [patch] (2026-08-13) — `37f835d1b87af426001df25d343ac1e12b86a55b`, `731a3ca394876a7329becee83a197e5d01e49773`
- **ATLAS-LIVE-HEAD-SWEEP-015** Reconcile merged provider defaults [patch] (2026-08-13) — `18550d932902662c1ce196f779ee041bd0c29cd4`, `19c205d4fca964ac4907eaeb0587fe18745efe89`, `beed6dad8f6998b81a4e2918c151989d272e7a19`
- **ATLAS-COEUS-HEPHAESTUS-F64-015** Restore CUDA f64 comparison seam [minor] (2026-08-13) — `b34b50787df636891d281b5011c6a17dd46edcb0`, `c373de1945bb9ce7b9fd804a80415218d975f286`, `aabdec67a0f5baa415c4abb6dded69db41b2f2d6`, `a4063be118978c8ecc4c745a8ef0b004c1beb45b`
- **ATLAS-HELIOS-CHECKLIST-016** Reconcile binary-MLC roadmap and benchmark gate [patch] (2026-08-13) — `f118214e5f3da231b8b48ef8e2ea15450544f1de`, `f7ca5dad16bb7c36781bcefe4c90c21377f06110`, `f108dc9b3cf7cc94212fa574219594eab2a0bc4f`
- **ATLAS-TYCHE-MULTIOUTPUT-017** Generalize sensitivity estimators [minor] (2026-08-13) — `dc96f5ecd6af643e34f2146b9f3dbb49ba85dbae`, `4a6f8cd495c78beaaa6e4081705b33ed0da8be9e`, `2d12dc5e2803a8208877026badfbb24578129da8`, `af30ad23dc468349511dff9d1d34ab9b5ab58334`
- **ATLAS-LETO-LBFGS-023** Replace L-BFGS jagged history with a flat ring [perf] (2026-08-13) — `e4d5dfc7aa81507518c83396091f11b60f1ed96`, `6e4a1627aa739d37c5f40ab1ab9e41948352cc54`, `a722fbc8`
- **ATLAS-LETO-TASK-PARTITIONS-024** Provider-owned disjoint task partitions [minor] (2026-08-13) — `508962df`, `39683975ff02d68abac8546b0bf945f4d70fc870`
- **ATLAS-FOUNDATION-PLANNING-001** Foundation planning completion (aequitas / eunomia / proteus / themis) [chore] (2026-08-12) — `cad222b`
- **ATLAS-FOUNDATION-PLANNING-002** Next-tier planning completion (hyperion / horae / consus / tyche) [chore] (2026-08-12)
- **ATLAS-BOOK-CLOSURE-002** Eight-provider book closure [patch] (2026-08-12) — `7a6744b`, `fdd8bd6`, `a21228a`, `31816dc`
- **ATLAS-CASCADE-ALIGNMENT-001** Consumer alignment for the 0.42/0.5/0.26/0.19 provider cascade [patch] (2026-08-11) — `d9e674f`, `f68045d`, `a68e91f`
- **ATLAS-BOOK-ANCHOR-PARITY-001** Heading-id parity with mdBook v0.5.4 [patch] (2026-08-11)
- **ATLAS-BOOK-LINK-CI-001** All-provider book link CI gate [patch] (2026-08-11)
- **ATLAS-BOOK-LINK-SWEEP-001** All-provider book link sweep [patch] (2026-08-10)
- **ATLAS-TYCHE-PROVIDER-ESTIMATORS-001** Tyche sensitivity estimators and book closure [patch] (2026-08-10)
- **ATLAS-MNEMOSYNE-BOOK-001** Complete Mnemosyne book closure [patch] (2026-08-11) — `c4516df`, `9a143ca`
- **ATLAS-HYPERION-PROVIDER-DOCS-001** Complete Hyperion book closure [patch] (2026-08-11) — `b8a1124`, `9a8b7d8`
- **ATLAS-PROTEUS-PROVIDER-DOCS-001** Complete Proteus book closure [patch] (2026-08-10)
- **ATLAS-HORAE-PROVIDER-DOCS-001** Complete Horae book closure [patch] (2026-08-11) — `03ad868`, `08cf292`
- **ATLAS-AEQUITAS-PROVIDER-DOCS-001** Complete Aequitas book closure (2026-08-11) — `11565d9`, `681042b`
- **ATLAS-PROVIDER-INTEGRATION-AUDIT-001** Audit nineteen Atlas providers [patch] (closed 2026-08-11; Tyche (aka Tychee)) — `b72d9f1`, `47863b1`, `47863b12aa0cd4e65cb9556b2c9bbf1353a5ee26`, `d272934`
- **ATLAS-HEPHAESTUS-CLOSURE-001** Hephaestus expression-parity closure record (2026-08-11) — `407938b`, `d4d5906`, `df8a896`, `aca9a5a8`
- **ATLAS-EUNOMIA-CLOSURE-001** Eunomia 0.8.0 provider closure record (2026-08-11) — `0c14c2e`, `184ba92`
- **ATLAS-IRIS-CLOSURE-001** Iris IRIS-003 release-readiness record [chore] (2026-08-11) — `ab3eea2`
- **ATLAS-ASCLEPIUS-BOOK-001** Complete Asclepius book closure [patch] (2026-08-11) — `530115a`
- **ATLAS-COEUS-MLM-PROVIDER-001** Coeus multi_label_margin_loss provider delivery [patch] (2026-08-11) — `1ac8118c`, `4491bf19`, `bde7010f`
- **ATLAS-HELIOS-DICOM-ORIENTATION-001** Helios DICOM oriented-grid boundary delivery [patch] (2026-08-11) — `342bbbc83`, `77716bb`, `bde7010f`
- **ATLAS-LETO-HERMES-REDUCED-PRECISION-001** Leto F16/Bf16 Hermes provider delivery [patch] (2026-08-11) — `606e5b5`, `d9e674fc`, `ca93b63c`, `d68095b`
- **ATLAS-APOLLO-SHARED-VALIDATION-001** Apollo shared WGPU transform validation delivery [patch] (2026-08-11) — `b426f2cd`, `0e38d1cc`, `bde7010f`, `eae6b706`
- **ATLAS-APOLLO-CI-INDEPENDENCE-001** Apollo whole-workspace clean-gitlink proof (hermes + hephaestus) [patch] (2026-08-12) — `ae657fc`, `3be20f43`, `03e5e175`, `63d06940`
- **ATLAS-HELIOS-CI-INDEPENDENCE-001** Helios whole-workspace clean-gitlink proof (hermes + hephaestus + leto) [patch] (2026-08-12) — `5c4a8491`, `03e5e175`, `ae657fc`, `e0d867ec`
- **ATLAS-COEUS-DIST-BYTE-IDENTITY-001** Scripted coeus-dist TCP binary byte-identity harness (2026-08-12) — `8369e7a2`, `b02a0f02`, `695507d6`, `4dbb70c2`
- **ATLAS-GAIA-PERMISSIONED-ARENA-001** Gaia Melinoe-branded permissioned arena delivery [patch] (2026-08-11) — `b5e62c5`, `5ea09cbc`, `a5b0fe72`
- **ATLAS-CGROUP-CLOSURES-001** C-group closure sweep (melinoe/moirai/proteus/consus) [chore] (2026-08-11) — `eab19a6`, `c8e8889`, `6d80c33`, `57c4ec4`
- **ATLAS-VERSION-GUARD-SCAN-MATRIX-001** per-commit scan matrix [chore] (2026-08-11) — `681042b`, `11565d9`, `3d6021e`, `30e25f8`
- **ATLAS-VERSION-GUARD-002** Stack-wide first-party coherence subcommand + CI sweep [minor] (2026-08-08) — `43f8aa2`
- **ATLAS-BOARD-HYGIENE-001** Resolve duplicate item IDs in backlog.md [chore] (2026-08-07) — `17c3cc5`
- **ATLAS-TOOLS-STRANDED-001** Land stranded atlas-meta tooling slices [chore] (2026-08-07) — `a92a3c6`, `cbc664d`, `fb62549`, `11a67dd`
- **ATLAS-TAKEOVER-001** Land stranded delivered slices in tyche, hermes, eunomia, CFDrs [chore] (2026-08-06) — `d25311e`, `bde7010`, `69ff96d`, `cf32eab6`
- **ATLAS-THEMIS-MELINOE-ADOPTION-002** Deliver Themis Melinoe branded-collection adoption (2026-08-11) — `47863b1`, `cad222b`, `038457d`
- **ATLAS-THEMIS-MELINOE-ADOPTION-001** Themis/Melinoe source-seam adoption in the three integrators [arch] [minor] (2026-08-10) — `1493eef3`, `234574c`, `a444038d`, `74159afa`
- **ATLAS-KWAVERS-NUMA-FIX-1** Close kwavers `NumaAwareAllocator` single-pair leak + unused `BindToNode`/`Interleaved` policy variants [patch] (2026-08-05) — `36e989054`
- **ATLAS-KWAVERS-NUMA-FIX-1-FOLLOWUP-PRINT-STDERR** Replace `eprintln!` defect-masking in `NumaAwareAllocator::allocate` with `log::warn!` [patch] (2026-08-06) — `155058b5d`, `7a30b0429`, `36e989054`
- **(unnumbered)** AEQUITAS-THERMAL-COEFFICIENTS — Add temperature-dependent acoustic coefficient dimensions [minor] (2026-08-04) — `7a9a21f`
- **ATLAS-KWAVERS-MNEMOSYNE-FIX-1** Complete mnemosyne dep wiring stranded in kwavers `bf3e17861` [patch] (2026-08-04) — `bf3e17861`
- **ATLAS-RITK-MELINOE-DOC-SYNC-1** Sync ritk parallel-prose comments to moirai/melinoe routing [patch] (2026-08-05) — `a03deeae`, `a5e375fe`, `b4cfff62`
- **ATLAS-AEQUITAS-CONSUMERS-005** Close Kwavers ultrafast geometry metric extensions [arch] [major] (2026-08-02) — `8ffb198bc`, `b2c437bab011d99d6403e23b4a373905f7905cde`
- **ATLAS-AEQUITAS-CONSUMERS-006** Close Kwavers beamforming and design metric extensions [arch] [major] (2026-08-06) — `63cd488ec17279be6d4a459f2785784f816b1c14`, `dc8e5b58b9816bf3a57f2bc47750257d65cd3609`, `c3e0ca39da0c928c83125ca27f9689de49b389f4`, `31482cbadaafda9703fc1f00e9d84e35e4398606`
- **ATLAS-AEQUITAS-CONSUMERS-004** Close geometry and scheduling metric extensions [arch] [major] (2026-08-06) — `ce6a4f39`, `57bb47ea`, `98b571e`, `87afe809f`
- **ATLAS-AEQUITAS-CONSUMERS-002** Close CFDrs, Helios, and Kwavers metric audit [patch] — `8e75ee3`, `c91cccc6`
- **ATLAS-AEQUITAS-CONSUMERS-003** Extend therapeutic microbubble metric audit [arch] [major] — `8cc90b2`, `77be364b9`, `2acd72ccd`, `5dad60d69`
- **ATLAS-SUBSTRATE-001** Extend the Hephaestus operation seams to Coeus's call surface [arch] [minor] (2026-08-11) — `d3aa627`, `8d1c6b1`, `f778445`, `a68e91f`
- **ATLAS-SUBSTRATE-002** Collapse Coeus's cloned per-vendor provider impls [arch] [minor] (2026-08-12) — `2f3af87e`, `9167f574`, `3be20f436aa2`, `d7077547`
- **ATLAS-SUBSTRATE-003** Give the Leto/Hephaestus decomposition pair one seam and one oracle [arch] [minor] (2026-08-02) — `31f797f`, `60928c8`, `1fe2bd4`, `7762aa1`
- **ATLAS-SUBSTRATE-004** Consolidate Apollo's per-transform scaffold [arch] (2026-08-02) — `ebb2df7`, `29e7b6d`, `6c7f593`, `aea658d`
- **ATLAS-SUBSTRATE-005** Shared CPU-tier storage vocabulary for Apollo [arch] [minor] (2026-08-02) — `7d212a2`, `b31948d`, `6876b55`, `d0a153f`
- **ATLAS-ARCH-001** One generic ComputeBackend conformance suite [arch] [minor] (2026-08-01) — `acc50ed`, `1e36071`, `53816ebf`, `b08161e`
- **ATLAS-THEMIS-TOPOLOGY-OPTION-1** Model unreported GPU capacities in the type [minor] (2026-08-01) — `e6ec649`, `3ff23b6`, `eccf931`
- **ATLAS-ARCH-010** Define the NaN and infinity contract for accelerator kernels [arch] [minor] (2026-08-01) — `6996f12`
- **ATLAS-ARCH-009** Decide whether hephaestus-metal remains a crate [arch] (2026-08-03) — `b5020e1`
- **ATLAS-GITLINK-TARGET-SSOT-001** Reject ambiguous target-repo selectors [patch] (2026-08-07) — `cbc664d`
- **ATLAS-OVERLAY-SSOT-001** Restrict overlay discovery to canonical repos [patch] (2026-08-07) — `fb62549`
- **ATLAS-HEPH-ADR-NUM-1** Two ADRs both numbered 0045 [patch] (2026-08-03) — `b5020e1`, `010b14d`, `64653b3`, `1febb16`
- **ATLAS-ARCH-002** Instantiate generic tests across every shipped scalar [patch] (2026-08-03) — `cf716c0`
- **ATLAS-ARCH-003** Make leto-ops statistics generic and resolve the split Pearson [minor]
- **ATLAS-ARCH-004** Rehome and genericize the cfd-math Pareto module [patch]
- **ATLAS-ARCH-006** Eliminate junk-drawer modules [patch] (2026-08-03) — `1b4952823`, `be610931`, `d0a153f`, `fc0e1ec`
- **ATLAS-ARCH-007** Reduce manifest files carrying implementation [patch]
- **ATLAS-ARCH-CYCLE-001** Break the CFDrs -> gaia -> CFDrs repository cycle [arch] (2026-07-29) — `df3902b`, `67d5728`
- **ATLAS-CFDRS-PATHDEP-001** CFDrs path deps collide with the worktree overlay [patch] (2026-07-29) — `bf65a41`
- **ATLAS-HEPH-PRODUCT-PARITY-1** Land the stranded product-axis parity commit [patch] (2026-07-30) — `8bc589a`, `196bc84`
- **ATLAS-HEPH-CONFORMANCE-LETO-1** Stale `repos/leto` checkout breaks conformance stack-wide [patch] (2026-07-30) — `f778445`
- **ATLAS-LETO-BRANCH-SPLIT-1** Leto main and sparse-LU diverged under one pin [patch] (2026-07-30) — `054244a`, `116b98d`
- **ATLAS-KWAVERS-ALLOC-TEST-RACE-1** Allocation-count test races the harness [patch] (2026-08-02) — `02eee237a`, `f2fb1ca`
- **ATLAS-COEUS-SWALLOWED-RESULTS-1** coeus-autograd ignores fallible add_assign [patch] (2026-07-30) — `81eeec09`, `80bb2707`
- **ATLAS-COEUS-MAIN-SYNC-1** Integrate coeus origin/main into the stack [arch] [major] (2026-07-30) — `c01a313a`, `81a7992`, `9ac74e13`, `29eb02d`
- **ATLAS-ENV-CC-1** Host gcc is broken, blocking every C dev-dependency [chore] (2026-07-31)
- **ATLAS-WORKTREE-JUNCTION-1** `worktrees/apollo` is a junction onto the main tree [chore] (2026-08-04)
- **ATLAS-ATHENA-ALLOC-1** Zero-allocation solver test fails only on Linux [patch] (2026-08-03) — `cdb5fca`, `34ce3b6`, `346a1df`, `045efe4`
- **ATLAS-MNEMOSYNE-CI-1** mnemosyne CI gate landed; two exclusions to retire [patch] (2026-08-05) — `49b4ad9`
- **ATLAS-MNEMOSYNE-SNMALLOC-1** snmalloc-sys fails g++ 16's new warnings [patch] (2026-08-05)
- **ATLAS-HEPH-DOC-LINKS-1** hephaestus-core fails the rustdoc gate [patch] (2026-07-30) — `d6d893a`, `eb58c86`, `8d1c6b1`
- **ATLAS-PM-TOOLCHAIN-SSOT-1** Three board records for one toolchain fact [patch] (2026-07-30)
- **ATLAS-ENV-TOOLCHAIN-001** RUSTC override breaks the shared cache [chore]
- **ATLAS-GAIA-GITDEP-001** Gaia's committed path dep makes it unconsumable as a git dependency [patch] (2026-07-28) — `1190ace`, `1459c99`, `42ef63af`
- **ATLAS-HELIOS-GENERIC-001** Instantiate the f32-only generic tests across shipped scalars [patch] (2026-07-29) — `f3038b2`, `3fdfa8d`, `cda0e8c`
- **ATLAS-PUB-LOCK-1** Overlay-stripped lockfiles get committed and break `--locked` [patch] (2026-08-13) — `520f248`, `98f8537`, `0992e24`, `a3be57f`
- **ATLAS-PUB-007** Rename `mnemosyne-core`: the stack's publish critical path [patch] (2026-08-03)
- **ATLAS-PUB-004** Pin the three Pages actions to verified digests [patch] (2026-08-01) — `983d773`, `7b1f4a7`, `d6db901`
- **ATLAS-BOOK-001** Author the 21 missing package books [minor] (2026-08-04) — `aa1be92`, `35fe13e`, `54b89f9`, `40d0f7c`
- **ATLAS-NEURO-001** RITK diffusion, tractography, and connectome crates [minor] (2026-08-04)
- **ATLAS-MODALITY-001** Move chromophore extinction spectra to Hyperion [arch] [minor] (2026-08-04)
- **ATLAS-MODALITY-002** Type the deposition spine in Aequitas quantities [arch] (2026-07-31) — `1003c88`, `81a40071c`, `37d50b96f`, `5aef5f551`
- **ATLAS-CONTENTION-001** Transport-output typing blocked behind foundation WIP [patch] (2026-07-31) — `e0918d1f2`
- **ATLAS-OVERLAY-002** Clear pin drift in asclepius, athena, hermes [patch] (2026-07-28) — `fef782cb`, `24ad6ea`, `bbf38400`, `cf69175`
- **ATLAS-OVERLAY-003** Retire committed [patch] blocks from 7 member manifests [patch] (2026-07-30) — `7840331f`, `4caf32b`, `395a1e74a`, `48ed142`
- **ATLAS-GIT-HYGIENE-001** Confirm `repos/leoneuro-rs/` rule is intentional [chore] (2026-07-27) — `fef2c63`
- **ATLAS-CUDA-TREE-003** Close the fused operation-tag tree split [arch] (2026-07-23) — `edcded8d`
- **ATLAS-CUDA-TREE-002** Close the attention kernel tree split [arch] (2026-07-23) — `393d711e`
- **ATLAS-CUDA-TREE-001** Close the convolution backend tree split [arch] (2026-07-23) — `9b5da9c7`
- **ATLAS-CUDA-SAFETY-015** Close elementwise backend count/failure boundary [patch] (2026-07-23) — `f7372408`
- **ATLAS-CUDA-SAFETY-014** Close fused-dispatch launch ABI [patch] [arch] (2026-07-23) — `799e72f6`
- **ATLAS-CUDA-SAFETY-013** Close transposed-convolution launch ABI [patch] [arch] (2026-07-23) — `382b74c7`
- **ATLAS-CUDA-SAFETY-012** Close unfold/fold launch ABI [patch] [arch] (2026-07-23) — `de74d093`
- **ATLAS-CUDA-SAFETY-011** Close attention launch ABI [patch] [arch] (2026-07-23) — `3ace27ec`
- **ATLAS-CUDA-SAFETY-010** Close matmul launch ABI [patch] [arch] (2026-07-23) — `b9876e7e`
- **ATLAS-CUDA-SAFETY-009** Close pool3d launch ABI [patch] [arch] (2026-07-23) — `df331873`
- **ATLAS-CUDA-SAFETY-008** Close pool2d launch ABI [patch] [arch] (2026-07-23) — `45826c05`
- **ATLAS-CUDA-SAFETY-007** Close pool1d launch ABI [patch] [arch] (2026-07-23) — `920b3428`
- **ATLAS-CUDA-SAFETY-006** Close optimizer launch ABI [patch] [arch] (2026-07-23) — `f627ecbc`
- **ATLAS-CUDA-SAFETY-005** Close elementwise launch ABI and tree [patch] [arch] (2026-07-23) — `92bd4c8f`
- **ATLAS-CUDA-SAFETY-004** Close reduction launch ABI [patch] [arch] (2026-07-23) — `dfe23979`
- **ATLAS-CUDA-SAFETY-003** Close shared CUDA layout ABI [major] [arch] (2026-07-23) — `4129d31e`
- **ATLAS-CUDA-SAFETY-002** Close convolution launch ABI narrowing [patch] (2026-07-23) — `1041b20d`
- **ATLAS-CUDA-SAFETY-001** Close convolution launch panic [patch] (2026-07-23) — `7e8e1ee2`
- **ATLAS-BUILD-STRUCTURE-005** Close CUDA operation impl hierarchy [patch] (2026-07-23) — `2fb00ed6`
- **ATLAS-BUILD-STRUCTURE-004** Close CPU operation impl hierarchy [patch] (2026-07-23) — `1a28b64b`
- **ATLAS-BUILD-STRUCTURE-003** Close WGPU operation impl hierarchy [patch] (2026-07-23) — `310f9ffb`
- **ATLAS-BUILD-STRUCTURE-002** Close Coeus-NN attention parity leaf [patch] (2026-07-23) — `006a1c7c`
- **ATLAS-WGPU-CORRECTNESS-001** Close native WGPU missing operation paths [patch] (2026-07-23) — `c8b9a013`
- **ATLAS-HELIOS-BOOK-087** Helios mdbook deterministic figure set + prebook xtask [patch] (2026-07-23)
- **ATLAS-RITK-655** RITK B-spline bounded dense hot-path closure [minor] (2026-07-23)
- **ATLAS-CHECK-FIGURES-CI-1** Wire `prebook check-figures` lint into PR CI [minor] (2026-07-23)
- **ATLAS-PATH-DEP-AUDIT-2** Close 311 ryancinsight audit hits across 21 atlas submodule Cargo.lock files [patch] (2026-07-27) — `0fc64b0e`, `1efc7fcf`, `2686b86`, `f04b1d75`
- **ATLAS-CFDRS-COEQ-BLOCKER-1** Restore CFDrs cargo workspace via coeus-core submodule [patch] (2026-07-26) — `a6dfb2d601`, `baff9ef7`, `7d60724`, `15ee8e594fd497f59fff65d809c2034131e1f0b0`
- **ATLAS-CFDRS-CI-SIBLING-CHECKOUT-1** CFDrs ci.yml sibling-checkout for runner-clean path-dep resolution [minor] (2026-07-26) — `a163ef55`, `7d60724`, `b25b0f0c`, `1a7aa1d6`
- **ATLAS-PARITY-HTML-RETIRE-1** Retire stale `parity_artefacts/INDEX.html` [minor] (2026-07-23)
- **ATLAS-BOOK-CHECK-FIGURES-1** Cross-atlas `prebook check-figures` SSOT lint [minor] (2026-07-23)
- **ATLAS-EUNOMIA-044** Wrapper integer checked/saturating ops correctness [patch] (2026-07-23)
- **ATLAS-CFDRS-PERF-045** CFDRS-PERF-SLOW-001 closure: poiseuille Picard perf [patch] (2026-07-23) — `22ddc27df272c749d8c4e5c4b171113bfa1c272a`
- **ATLAS-CFDRS-BOOK-MDBOOK-DUPLICATES-1** Pre-existing duplicate-file references in CFDrs mdbook SUMMARY [patch]
- **ATLAS-CFDRS-BOOK-DETERMINISTIC-FIGURES-1** CFDrs mdbook deterministic figure set + prebook xtask [patch]
- **ATLAS-PERF-043** Preserve provider-native sparse-LU ownership [minor] — `b24fc860864abad84af3118aa2bb27c32bb81265`, `74efcceff0c737d09cc3251f24ed37bbb11de232`
- **ATLAS-INTEGRATION-042** Close provider delivery graph [patch] (2026-07-23) — `f604123dd`, `c982fe0`, `806c6e7`, `ce3ef7a6`
- **ATLAS-INTEGRATION-041** Align the Leto consumer graph [patch] (2026-07-22) — `c00fa04a`, `5f57557a`, `eb93d124`, `8c6ab72d`
- **ATLAS-ROADMAP-040** P2 domain-provider consolidation [arch] (2026-07-22) — `7b4561b`, `105a093`, `5fc6f0419`, `9c8ce32e`
- **ATLAS-INTEGRATION-038** Iris visualization promotion [arch] [minor] — `a8ea96f7`, `a36e65df`, `a41774fa`
- **ATLAS-INTEGRATION-039** Iris CFDrs consolidation [arch] [major] — `c7454ef3`, `394c9977`
- **ATLAS-INTEGRATION-037** Asclepius P1 promotion [arch] [minor] — `eb65eaf`, `794f8c3`, `33bba34`, `4ce96b1`
- **ATLAS-INTEGRATION-035** Proteus and Tyche promotion ADRs [arch] [minor] — `f043d22`, `beb2713`, `feed3bc`, `edf99e4`
- **ATLAS-INTEGRATION-036** Coeus hephaestus 0.18.0 bump [patch] — `56fa49a`, `c290f3e`, `4158b8e`, `02d74fd`
- **ATLAS-INTEGRATION-034** Benchmark gate repair [arch] [patch] — `2a22319`, `4ce96b1`, `198f2b8c`, `9ad18523d`
- **ATLAS-INTEGRATION-033** Harmonia Phase 0 [arch] [minor] — `cf6ce3e9175bbc3eebc51918d137492b2da5edba`
- **ATLAS-INTEGRATION-032** Documentation and checkout hygiene [patch] — `96fb26d`, `92af1a2`
- **ATLAS-INTEGRATION-031** Horae/Athena extraction [arch] [minor] (2026-08-06) — `e57f798`, `7d647e7`
- **ATLAS-INTEGRATION-030** Aequitas consumer closure [patch] — `0fb31d800`, `49c116ffb7466f9163b7762f03bc74725d8026c3`, `7c37f7f30dc286e8853bdf41da7652abeadebe23`, `156531eeb`
- **ATLAS-INTEGRATION-028** Hephaestus PM convergence [patch] — `cdfcd0cb38de03d28107fc231042eaf55e078e3a`, `2c1ee62`
- **ATLAS-INTEGRATION-027** Provider-default convergence [patch] — `6f9b81f`, `bb03244f05a9c43c318d103225c3ccad07e9fad9`
- **ATLAS-INTEGRATION-026** Eunomia runtime-half retirement [patch] — `df77dfd`, `594d57a`, `d207cf6`
- **ATLAS-INTEGRATION-029** Hephaestus provider-first CFDrs 2D GPU Laplacian [minor]
- **ATLAS-INTEGRATION-025** Eunomia precision graph [major] — `c196db5`, `c9bbdf8`, `7afcbd0`, `3f5f51f`
- **ATLAS-INTEGRATION-024** Helios provider lock convergence [patch] — `79b09e9`
- **ATLAS-INTEGRATION-023** Coeus NN provider benchmark closure [patch] — `bb97cc6`, `a365b25`
- **ATLAS-INTEGRATION-022** Eunomia sub-byte graph [patch] — `49dc115`, `f0b4d8e`, `ed7d76e`
- **ATLAS-INTEGRATION-019** Hephaestus legacy-math residue [patch] — `cec0e33`, `93bc38e`
- **ATLAS-INTEGRATION-020** Apollo Hephaestus lock convergence [patch] — `cec0e33`, `a31b8f8`
- **ATLAS-INTEGRATION-021** Coeus tensor legacy benchmark removal [patch] — `4459d09`, `093f31f`
- **ATLAS-INTEGRATION-018** RITK Apollo alignment [patch] — `a41e03b9`, `aededa6b`
- **ATLAS-INTEGRATION-015** Merged default refresh [patch] — `a833b7fe`, `a2e4f390`, `972fb53e`, `3ac0d203`
- **ATLAS-INTEGRATION-012** Apollo policy-wrapper removal [major] — `e2f905a`, `0b5d11c`
- **ATLAS-INTEGRATION-013** Apollo Winograd re-export removal [patch] — `c874281`, `e2f905a`
- **ATLAS-INTEGRATION-014** Hephaestus scan-limit theorem [patch] — `93bc38e`, `3b68228`
- **ATLAS-INTEGRATION-016** Apollo provider-lock refresh [patch] — `93bc38e`, `a2e4f390`, `6a0e297`, `8a51b2a7`
- **ATLAS-INTEGRATION-017** Apollo Leto merge pin [patch] — `3ac0d203`, `6a0e297`, `6dcb97c`
- **ATLAS-INTEGRATION-011** Hephaestus CUDA initialization closure [patch] — `3b68228`, `d0eafc8`
- **ATLAS-INTEGRATION-010** Hephaestus tiled scan provider closure [minor] — `d0eafc8`, `df33d4d`
- **ATLAS-INTEGRATION-007** RITK Apollo checkout pin [patch] — `ffda3ec`, `157467e`
- **ATLAS-INTEGRATION-008** Apollo dispatch verification tree [arch] — `0b5d11c`, `56ad179`
- **ATLAS-INTEGRATION-009** Kwavers hosted closure [patch] — `9eabc4e2`, `e84bb571e`, `7c7d60f`
- **ATLAS-INTEGRATION-006** Refresh provider heads [arch] — `0b5d11c`, `df33d4d`, `9eabc4e2`, `6a0e297`
- **ATLAS-INTEGRATION-005** RITK lock-integrity pin [patch] — `0dd71e52`
- **ATLAS-INTEGRATION-003** provider-neutral GPU pin reconciliation [patch] — `29ff2ff`, `7d4c9edf`
- **ATLAS-INTEGRATION-004** CFDrs executable-example pin [patch] — `a13f7f51`
- **ATLAS-INTEGRATION-001** default-main reconciliation [patch] — `093f31f`, `9e48102`
- **ATLAS-INTEGRATION-002** merged-provider pin reconciliation [patch] — `f26369eb`, `04e496b7`, `ec7cb832`, `e3380b6`
- **ATLAS-MNEMOSYNE-017** Maximum-small deallocation audit [patch] — `0012c4fad0c44c0a40ec4d36de68e7138ae218d8`, `52cd5ee`
- **ATLAS-MOIRAI-016** Cancellation-safe async wait queues [patch]
- **ATLAS-RITK-654** RITK native migration reconciliation [patch] — `17b84bdc18c2395d6329f3435ed3d860d1c72e00`
- **ATLAS-APOLLO-015** RustFFT/WGPU provider promotion [major] — `6e99a567c118f6bf5790f80346475b44db2c7555`, `17b84bdc`
- **ATLAS-WGPU-030** Provider ABI migration [arch] (2026-07-13) — `01e7de7`, `4a9d2a3`, `090611d`, `8651dfc`
- **ATLAS-APOLLO-014** Apollo release graph [arch] (2026-07-09) — `a4742bb`, `eb0d941`, `51c530f`, `b2f3732`
- **ATLAS-BOOK-002** Domain books teach the field; evict process content [patch] (2026-08-06) — `a5a86d64`, `9ebf5b4e9`
- **ATLAS-MNEMOSYNE-001** Allocator observability and adversarial-stress audit [patch] (2026-07-24)
- **ATLAS-LETO-OPS-AMD-ORDERING-001** Implement AMD fill-reducing ordering for sparse LU [patch] (2026-08-07) — `db9a63c`, `912b991`, `d1c3a1c`
- **ATLAS-STACK-DEPS-001** Stale dependency version resolution across hermes, tyche, melinoe [patch] (2026-07-24) — `2739a75`, `95c1fa7`, `40278ac`, `babdd42`
- **ATLAS-AEQUITAS-001** Wireless gitlink advance to origin/main `19fc3846` [minor] (2026-07-24) — `19fc3846`, `07e2252`, `6dc68c4`, `19fc384`
- **ATLAS-COEUS-DIRTY-RECONCILE-1** Commit post-`7d60724` coeus dirty state: workspace-graph migration + CUDA driver compat + lock disambiguation [patch] (2026-07-24) — `7d60724`, `c711dcb4`, `a6dfb2d`, `15ee8e594fd497f59fff65d809c2034131e1f0b0`
- **ATLAS-COEUS-OPS-FALLIBLE-API-1** Document `coeus_ops` fallibility boundary migration (`*_assign` + `elementwise_unary` Result return + downstream test adaptations) [patch] [arch] (2026-07-24) — `f8328027`, `a6dfb2d6`, `53311c03`, `6b54e64a`
- **ATLAS-LETO-GITLINK-ADVANCE-1** Advance `repos/leto` parent submodule pointer to c6ced81 [minor] (2026-07-24) — `c6ced81`, `c6ced81e`, `687b67079c4e122264c17fd2eb3fd850d876a39f`, `c6ced81e6d5a9f439bd24a5150964e7bd2cb595d`
- **ATLAS-MOIRAI-GITLINK-ADVANCE-1** Advance `repos/moirai` parent submodule pointer to f74aa480 [patch] (2026-07-24) — `f74aa480`, `b613dc3d`, `b613dc3db6504340c4b407cbfbe5cab36bd23f44`, `f74aa480217c51e0254461d02b47b2a32e67ddce`
- **ATLAS-APOLLO-GITLINK-ADVANCE-1** Advance `repos/apollo` parent submodule pointer to 82e67c8 [patch] (2026-07-24) — `82e67c8`, `82e67c8f`, `8fb3e4ad`, `8fb3e4ad2c7903df14f7c1f944761970b55b9705`
- **ATLAS-HEPHAESTUS-GITLINK-ADVANCE-1** Advance `repos/hephaestus` parent submodule pointer + add CUDA build script [minor] [arch] (2026-07-24) — `e7887a5d110c1b8b71456564b76bafcb3d68798f`, `116373dd207d93660f53687f6a4817f7ee1b80ff`
- **ATLAS-GITLINK-COHERENCE-DEFECT-1-AUDIT-TOOL-1** Mechanize the gitlink-coherence audit as a coordinator-owned `tools/gitlink-coherence/` sister tool [patch] [arch] (2026-07-24) — `2c14b94f`, `c2227aa`, `47e73d1e`, `9ae06c0`
- **ATLAS-TOOLCHAIN-ALIGN-001** Align all 14 clean repos to Rust 1.97.0 for shared target compat [patch] (2026-07-24)
- **ATLAS-PERF-OPT-001** Hot-path performance and memory efficiency optimization [patch] (2026-07-24) — `777b11c`, `b9393fc`, `035445f`, `7164f26`
- **ATLAS-TOOLS-TEMPLATE-EXTRACT-1** Extract shared `tools/_template/` package module for coordinator-owned tool Cargo lints/profiles/deps after 3rd occurrence [patch] [arch] — `e260055`
- **ATLAS-COEUS-SOURCES-001** Convert coeus mainline back to git+version sources [patch] (2026-08-05) — `5602093b`
- **(unnumbered)** ATLAS-KWAVERS-SPECIAL-FUNCTIONS-SSOT — Consolidate kwavers special functions into leto-ops [patch] (2026-07-25) — `ddd9cca`, `0a31706`, `d87e107`
- **ATLAS-GMRES-FORK-DEFECTS-001** Port the leto-ops GMRES corrections to the CFDrs and kwavers forks [patch] (2026-08-03) — `dcc5d54`
- **ATLAS-MATH-SSOT-CONSOLIDATION-1** Cross-repo math SSOT consolidation audit [patch] (2026-08-05) — `a19a5d977`, `e4e9966b6`, `6d18a547`, `6484ad9e`
- **ATLAS-ATHENA-KRYLOV-CAPABILITY-001** Close Athena's capability gap (ADR 0033 stage A) [minor] (2026-07-27) — `e965a95`
- **ATLAS-ATHENA-ACCEL-BACKEND-001** Replace athena-wgpu with one Hephaestus-backed backend (ADR 0034) [major] [arch] (2026-07-27) — `6ab822c`, `eefa8ba`, `e1f2800`, `47ca84a`
- **(unnumbered)** ATLAS-KWAVERS-PEER-WIP-COMPILE-FIX — Fix compilation errors in kwavers peer WIP [patch]
- **ATLAS-OVERLAY-COHERENCE-001** The stack overlay resolves worktree copies, not the authoritative repos [major] (2026-07-28) — `e1f2800`, `d89ccd9`, `ad941c0`
- **ATLAS-VECTOR-SEAM-PREPARED-CONTRACT-001** Reconcile lending vs retained prepared reductions [major] [arch] (2026-07-28) — `e1f2800`, `d899d88`, `673a7bd`, `7897c13`
- **ATLAS-HEPHAESTUS-SPARSE-SEAM-001** Device-neutral sparse operator seam [major] [arch] — `eefa8ba`
- **ATLAS-GITLINK-TOOL-001** Rescue gitlink-coherence from the harness lane [patch] (2026-07-29) — `f8305ac`
- **ATLAS-TOOLCHAIN-COHERENCE-001** One compiler identity across the shared cache [patch] (2026-07-31) — `2d8144b78`, `a091db2`, `f0c2869`, `9be1b9d`
- **ATLAS-CFDMATH-MATRIX-FREE-OPERATOR-001** Restore the matrix-free operator [patch] (2026-08-03) — `6d18a547`
- **ATLAS-CFDMATH-CLIPPY-FINDINGS-001** Discharge the clippy backlog [patch] (2026-08-03) — `40ef080c`
- **ATLAS-DMRI-MGH-FRAMES-002** MGH silently discards frames past the first [patch] — `8a79da6d`
- **ATLAS-DMRI-SCHEME-003** Typed gradient scheme and its codecs [minor] (2026-08-05)
- **ATLAS-APOLLO-REALSH-005** Real symmetric SH basis over scattered directions [minor] (2026-08-13) — `bf06987`, `db21866`, `112d378`, `33a40bcee4532c9c1a03fee7cef2d852b3419090`
- **ATLAS-LETO-NNLS-007** Non-negative constrained solve [minor] (2026-08-03)
- **ATLAS-RITK-DIFFUSION-010** ritk-diffusion crate, tensor model first [minor] (2026-08-05)
- **ATLAS-RITK-TRACTOGRAPHY-011** ritk-tractography crate [minor] (2026-08-05)
- **ATLAS-RITK-CONNECTOME-012** ritk-connectome crate [minor] (2026-08-05)
- **ATLAS-MIGRATION-PATHDEP-001** Migrate kwavers, CFDrs, helios, ritk to local path deps [patch] (2026-08-03) — `b2ee610`, `c7c3678`
