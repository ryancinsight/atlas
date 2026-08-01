# ComputeBackend conformance triage (2026-07-28)

First increment of `ATLAS-ARCH-001` and the triage
[ADR 0038](../adr/0038-compute-backend-conformance-crate.md) §2 requires before
any conformance crate is written. Read-only pass: no source file was modified.

> **Correction, 2026-07-28 (same day).** The coverage figures first published in
> this ledger were computed by scanning only each backend's `tests/contract.rs`.
> Every backend also carries sibling test files (`strided.rs`,
> `volume_ray_integral.rs`, `dense_vector.rs`, `stencil_laplacian.rs`,
> `topology.rs`, `concurrency.rs`), so every per-backend number was understated
> and three entry points were wrongly listed as unverified. The corrected
> figures below supersede them; the superseded numbers are named inline so the
> error is traceable rather than silently overwritten.

## Method, and a correction to the basis

The initial framing triaged the **union of test-function names** (221). That
basis is wrong, and following it would have produced a conformance suite shaped
by whichever backend's author wrote the most tests.

Two facts falsified it:

1. Of the 354 functions in the four `tests/contract.rs` files, **52 are helpers,
   not tests**. The real test counts are wgpu 113, cuda 100, rocm 59, metal 30 —
   not the 130/114/70/40 first reported.
2. The backends differ in test **granularity**, not only coverage. `rocm`
   aggregates several contract clauses per test function where `cuda` and `wgpu`
   split them one clause per function. Verified by reading
   `cholesky_factorization_and_common_host_contracts_match_values`, which asserts
   factor values, determinant, *and* solve — three clauses that cuda/wgpu carry as
   `cholesky_decomposition_matches_leto_reference`,
   `cholesky_solve_known_system_accurate`, and their siblings. Most of rocm's "53
   unique tests" are therefore naming and granularity divergence, not behaviour
   no other backend checks.

The correct basis is the **public API surface**: what every backend promises.
This ledger is derived from the union of `pub fn` declarations across the four
backend crates, cross-referenced against test invocation (matching both `name(`
and turbofish `name::<` call forms).

## The topology is three backends and one delegation layer

`hephaestus-metal` is not an independent backend. Its own crate documentation
states it "implements the `hephaestus-core` `ComputeDevice` seam by delegating to
`hephaestus-wgpu` configured to use the native Metal API", and the source agrees:

- `MetalDevice` wraps a `WgpuDevice` obtained from `WgpuDevice::try_metal(...)`;
- every `application/*` module forwards to `wgpu_backend` — `decomposition.rs`
  (268 lines, 23 forwarding references), `reduction.rs` (521/25), `linalg.rs`
  (246/18), `sparse.rs` (252/23), and so on;
- the crate depends on `hephaestus-wgpu` and `wgpu` directly;
- **no native Metal API usage exists** — no `metal::` crate, no `objc`, no
  `MTLDevice`, no MSL shader source.

This corrects an earlier reading in this audit. Metal's low test count is not
primarily a correctness hole in Metal kernels, because there are no Metal
kernels; the delegated paths are covered by wgpu's suite. It also explains the
28 result accessors (`lower`, `q`, `r`, `u`, `v`, `pivots`, `permutation`,
`rank`, `solve`, `solve_least_squares`, …) that appear in three backend crates
and not in metal: metal re-exports wgpu's result types rather than declaring its
own, so those accessors are available to metal users. That is not an API gap.

| | wgpu | cuda | rocm | metal |
| --- | --- | --- | --- | --- |
| Independent kernels | yes | yes | yes | **no — delegates to wgpu** |
| Public fns declared | 173 | 157 | 141 | 114 |
| Tests | 113 | 100 | 59 | 30 |
| `contract.rs` lines | 5 287 | 4 381 | 4 657 | 1 614 |

## Contract surface: 112 shared entry points

Of 188 distinct public functions across the four crates:

| Present in | Count | Class |
| --- | --- | --- |
| all 4 backends | **112** | **contract** |
| 3 backends | 28 | not a class — all are wgpu result-type accessors metal re-exports (see above) |
| 2 backends | 5 | **capability-gated** — `download_sub_buffer`, `write_sub_buffer`, `raw`, `values`, `try_with_ordinal` |
| 1 backend | 43 | **backend-intrinsic** (with one exception, below) |

### Coverage of the 112 shared entry points

Measured across **all** test files per backend (the corrected basis):

| Backend | Covered | Share | (superseded contract.rs-only figure) |
| --- | --- | --- | --- |
| wgpu | 101 | 90% | 94 |
| rocm | 95 | 84% | 93 |
| cuda | 84 | 75% | 78 |
| metal | 53 | 47% | 50 |

46 of the 112 are exercised by all four backends. The remainder are verified
unevenly, which is the condition the shared suite removes: one clause written
once is executed by every backend automatically.

Eight entry points are exercised by exactly one backend — `cumsum_into`,
`max_axis_into`, `min_axis_into`, `spmv_into`, and `scalar_elementwise_strided`
(wgpu); `reduce_axis` (cuda); `scan_axis_into` (rocm); `reduce_axis_into`
(metal). Each is a single-backend assumption about a four-backend promise.

### Six shared entry points were tested by no backend at all

Every backend promises them; nothing verified any of them:

```text
binary_elementwise_typed              binary_elementwise_typed_into
binary_elementwise_strided_typed      binary_elementwise_strided_typed_into
prod_axis_into                        prepare_reduce_axis_into
```

**Not nine.** `ray_line_integrals` is covered by all four backends and
`ray_line_integrals_into` by three, in `tests/volume_ray_integral.rs`;
`scalar_elementwise_strided` is covered by wgpu in `tests/strided.rs`. The
earlier claim that these three were unverified — and the recommendation to
prioritise `ray_line_integrals` on the strength of its Helios consumer — was an
artifact of the contract.rs-only scan and is withdrawn.

The six are the `TypedBinaryExpr` comparison dispatch paths and the two
axis-reduction entry points. That they were the gap is not incidental:
comparisons are the only operators with per-scalar-type codegen, so they are the
newest and least-travelled path in the elementwise family.

### Closed by this increment (wgpu)

`hephaestus-wgpu/tests/typed_elementwise.rs` and
`hephaestus-wgpu/tests/axis_reduction_contracts.rs` add 13 tests covering all six
on wgpu; wgpu coverage rises 101 → 107 of 112. Oracles are exact equalities, not
epsilon bounds: `u32`/`i32` comparisons are integer-exact, and the `f32` cases use
dyadic operands and integer-valued products below `2^24`, where the expected value
is representable without rounding. `cuda`, `rocm`, and `metal` remain uncovered
for all six — closing those is the shared-suite work, not a per-backend copy.

### A contract boundary surfaced by writing them: NaN and infinity

The first `f32` comparison test asserted IEEE-754 semantics (`NaN != NaN` is
true, all other NaN comparisons false). It **failed** on wgpu: the device returned
`NaN != NaN` as false.

That is not a backend defect. The WGSL specification states that
"implementations may assume that overflow, infinities, and NaNs are not present
during shader execution", and that an expression yielding one produces "an
indeterminate value of the target type". The assertion demanded a guarantee the
specification explicitly withholds, so the assertion was wrong — corrected by
removing NaN and infinity operands from the contract case, not by relaxing the
expected values to match observed output.

The consequence for ADR 0038 is concrete: **NaN and infinity behaviour is a
capability-gated clause, not a universal one.** CUDA and HIP provide IEEE
semantics; WGSL does not promise them. A shared suite that asserted IEEE NaN
ordering uniformly would fail on wgpu forever, and one that dropped the assertion
entirely would leave CUDA's real semantics unverified. Filed as
`ATLAS-ARCH-010`.

## Triage classification

### Class 1 — contract (112 entry points)

Every clause below is required of every `ComputeBackend`. Grouped by the
conformance-crate module that will own it (ADR 0038 §1):

| Module | Entry points | Count |
| --- | --- | --- |
| `transfer.rs` | `from_cpu`, `to_cpu`, `new`, `try_default`, `output`, `shape`, `dispatch` | 7 |
| `elementwise.rs` | `unary_elementwise{,_into,_strided,_strided_into}`, `binary_elementwise{,_into,_typed,_typed_into,_strided,_strided_into,_strided_typed,_strided_typed_into}`, `scalar_elementwise{,_into,_strided,_strided_into}` | 16 |
| `reduction.rs` | `reduction{,_with_width}`, `reduce_axis{,_into}`, `sum_axis{,_into}`, `prod_axis{,_into}`, `mean_axis{,_into}`, `min_axis{,_into}`, `max_axis{,_into}`, `norm_l1`, `norm_l2`, `norm_max`, `dot`, `trace` | 19 |
| `scan.rs` | `scan_axis{,_into}`, `cumsum{,_into}`, `cumprod{,_into}`, `suffix_sum{,_into}`, `suffix_prod{,_into}` | 10 |
| `prepared.rs` | `prepare_dot`, `prepare_norm_l2`, `prepare_reduction{,_with_width}`, `prepare_reduce_axis_into`, `prepare_{sum,mean,min,max}_axis_into`, `prepare_spmv{,_many}`, `prepare_spmm`, `submit_prepared_{reduction,axis_reduction,sparse}_batch` | 15 |
| `sparse.rs` | `spmv{,_into}`, `spmv_many{,_into}`, `spmm{,_into}`, `nnz` | 7 |
| `linalg.rs` | `matmul{,_into}`, `batched_matmul{,_into}`, `kron{,_into}`, `matexp`, `matpow`, `det`, `pinv`, `matrix_rank{,_with_tolerance}` | 12 |
| `decomposition.rs` | `cholesky_decompose{,_blocked}`, `lu_decompose{,_blocked}`, `qr_decompose{,_blocked}`, `col_piv_qr{,_blocked}`, `full_piv_lu{,_blocked}`, `bunch_kaufman`, `udu_decompose`, `hessenberg`, `bidiagonalize`, `schur`, `svd_decompose`, `svd_rank_revealing`, `singular_values`, `eigenvalues`, `symmetric_eigen_jacobi`, `symmetric_eigenvalues_jacobi` | 21 |
| `volume.rs` | `ray_line_integrals{,_into}` | 2 |
| `random.rs` | `uniform_with_seed`, `normal_with_seed` | 2 |
| `device.rs` | `topology` | 1 |

Per-clause assertions are drawn from the existing suites: the union already
contains a value-semantic assertion, a rejection assertion, or both, for most of
these. Where the union contains only one backend's version, that version becomes
the clause; where it contains none (the nine above), the clause is authored.

### Class 2 — capability-gated (5 entry points)

`download_sub_buffer`, `write_sub_buffer`, `raw`, `values`, `try_with_ordinal` —
each present in exactly two backends. Each moves into the suite behind an
associated-const capability predicate so a backend advertising the capability
cannot skip its clause, and one lacking it skips by construction rather than by
omission. Whether each asymmetry is deliberate is a question for the
implementation increment; sub-buffer transfer in particular looks like an
unfinished surface rather than a capability boundary.

### Class 3 — backend-intrinsic (43 entry points)

**wgpu, 29** — device and adapter acquisition and pooling: `adapter_info`,
`adapter_limits`, `limits`, `features`, `device_limits`,
`supports_device_feature`, the `try_default_with_*` / `try_with_*` family,
`try_metal`, and the staging/uniform buffer recycling pair. Correctly intrinsic:
these are WGPU-API shapes with no cross-backend meaning.

**cuda, 12** — `compile_cuda_to_ptx`, `grid_size`, `bind`, `row_ptr`,
`col_indices`, `get`, the `*_strided_dyn_*` variants, and
`gemm_trailing_update`, `hh_trailing_update`, `syrk_trailing_update`.

The three `*_trailing_update` functions are flagged, not classified. They are
inner steps of blocked decompositions exposed as public API in one backend only,
which reads as surface-minimization erosion rather than an intentional contract.
Confirm and demote to `pub(crate)` in the implementation increment, or justify
the public surface.

**metal, 2** — `wgpu_device`, `wgpu_buffer`. Honest escape hatches onto the
delegated implementation; intrinsic by construction.

## Consequences for ADR 0038

1. **The suite is written against the 112-entry-point contract surface**, not the
   196 distinct test names. Test names are an artifact of four authors; the API is
   the promise.
2. **Metal's instantiation verifies delegation fidelity and Metal adapter
   acquisition**, not independent kernel correctness. It stays in the suite —
   running it is nearly free once the suite exists, and it does catch delegation
   regressions — but the expectation set in ADR 0038's Consequences ("raising
   Metal's coverage will surface real failures") should be tempered: failures
   there indicate a broken delegation or adapter path, not an unverified kernel.
3. **`hephaestus-metal`'s 1 614-line `contract.rs` is the most redundant of the
   four** and should reduce furthest — to the suite instantiation plus a small
   file covering device acquisition and the two escape hatches.
4. **The six untested shared entry points are authored first** (count corrected
   with the entry-point re-basis above). They are the only part of this work
   that adds coverage nothing currently provides.
5. **A prior question is now answered**: whether `hephaestus-metal` should exist as
   a crate at all, given it contains no Metal code, is a separate architectural
   question. It is *not* resolved here and is not in ARCH-001's scope. Recorded as
   a follow-up so the conformance work does not silently decide it.

## Follow-up filed

- `ATLAS-ARCH-009` — decide whether `hephaestus-metal` remains a crate or becomes
  a device-selection path inside `hephaestus-wgpu`.
- Tolerance derivation: the assertions read during this pass use magic tolerance
  arguments (`assert_near(lower[0], 2.0, 64.0)`). The conformance suite must carry
  derived tolerances per `numerical_discipline`; migrating an undocumented
  constant into the shared suite would propagate it to every backend. Folded into
  the ARCH-001 acceptance criteria rather than filed separately.
