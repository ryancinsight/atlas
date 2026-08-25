# ADR 0031 — Real sparse LU factorization for `leto-ops::SparseLuSolver`

- **Status**: Accepted (2026-07-23; SparsLU landed at leto `687b670`) — was Proposed
- **Date**: 2026-07-23
- **Class**: `[arch]` `[minor]`
- **Driver**: ATLAS-LETO-OPS-SPARSE-LU-001
- **Topic tag**: `upstream-algorithm`
- **Relates to**:
  - ADR 0005 (Eunomia numeric-element SSOT — `Scalar`/`RealScalar` rebind at the seam)
  - ADR 0022 (Athena Krylov policy over Leto CPU + Hephaestus WGPU — complement, not substitute, for the direct path)
  - CFDRS-PERF-SLOW-001 (Session 13 closure — root cause was dense-backed LU masquerading as sparse)
  - ATLAS-PERF-043 (provider-native sparse-LU ownership — public surface contract this ADR preserves)

## Context

`leto_ops::SparseLuSolver` is, as of leto HEAD `9346413`, a **misnamed dense
partial-pivoting LU**. The module doc at
`crates/leto-ops/src/application/sparse/lu_sparse.rs:1-20` states this honestly:

> For systems of order `n ≤ DENSE_LIMIT` the implementation expands the
> `CsrMatrix` to a dense `n × n` row-major buffer and delegates to the
> existing `lu_decompose` / `LuDecomposition::solve` path … A fully
> symbolic+numeric sparse LU with Markowitz/AMD ordering is the long-term
> path (tracked as a `leto-ops` enhancement).

Algorithmic cost: `O(n²)` memory + `O(n³)` time, regardless of `nnz`. This
defect was the root cause of the Session 13 `CFDRS-PERF-SLOW-001` timeout —
`validate_poiseuille_flow` exceeded the committed 30s nextest budget at
pre-PR-#311 CFDrs. The tactical workaround PR #311 (`22ddc27d`) hoisted
per-Picard-iteration caches and lowered `with_direct_threshold(100_000 → 512)`
so medium saddle-point systems route to GMRES+AMG instead of the dense-backed
"fake sparse" path. The strategic fix — **a real sparse LU** — was filed as
`ATLAS-LETO-OPS-SPARSE-LU-001 [arch]`.

### CFD problem-class fingerprint

CFDrs `crates/cfd-3d/src/fem/solver.rs` solves discrete saddle-point systems
arising from Taylor-Hood Stokes FEM with Lagrangian multipliers
(velocity + pressure). The problem class is **indefinite saddle-point**,
not symmetric positive definite — see Brezzi 1974 RAIRO (cited in the
`cfd-3d` solver.rs:23 header) and the projection-solver note at
`crates/cfd-3d/src/fem/projection_solver.rs:5` (the projection operator
exists *to avoid* the ill-conditioned saddle-point system).

**Corollary**: sparse Cholesky is forbidden — it requires SPD input. The
strategic upstream fix must be a real **nonsymmetric sparse LU** with
partial pivoting (which the existing dense `lu_decompose` already uses; we
preserve that convention). Symmetry-exploiting factorizations are a
different problem class and would silently misfactor saddle-point matrices.

### Existing infrastructure

`crates/leto-ops/src/application/sparse/` already provides:

- `CsrMatrix<T>` — `transpose()`, `to_dense()`, `from_dense()`, `as_parts()`,
  `row()`, `get()`, `diagonal()`, `values_mut()`. Generic over `Scalar`.
- `CscMatrix<T>` — column-major analogue with `column(j)`, `col_ptr()`,
  `row_indices()`, `values()`, `from_csr()`, `to_csr()`, `transpose()`,
  `to_dense()`. **CSC is the native format for the factorization phase**
  (column-major suits LU pivot search and the L/U column-by-column fill-in).
- `CooMatrix<T>` — assembly phase; `to_csr()` / `to_csc()`.
- Existing dense `lu_decompose` at `application/linalg/lu.rs` — partial
  pivoting LU with `LuDecomposition::solve` / `solve_into`. The current
  `SparseLuSolver::solve_validated` path calls this on a dense expansion.
- Existing `sparse_lu_solve` convenience function + `DENSE_LIMIT_DEFAULT =
  2048`.

### Public API surface to preserve

`crates/leto-ops/src/lib.rs:64-68` re-exports:

```rust
pub use application::sparse::{
    csc_spmv, csc_spmv_into, csr_to_dense, sparse_lu_solve, spgemm, spmm, spmm_into, spmv,
    spmv_into, CooMatrix, CscColumn, CscMatrix, CsrMatrix, CsrRow, SparseLuSolver,
    DENSE_LIMIT_DEFAULT,
};
```

Consumer seam: `crates/cfd-math/src/linear_solver/direct_solver.rs` imports
`SparseLuSolver as LetoCsrLuSolver` and calls `.solve_view(matrix, &rhs.view())`
with a `retry_dense_or_error` fallback. `crates/cfd-3d/src/fem/solver.rs:157`
and `:239` invoke `.with_direct_threshold(512)`.

**Naming policy per AGENTS.md `consolidation_discipline` + `integrity:
compatibility soup`**: a replacement takes the original's name. The peer
(owning the leto-ops tree) has explicitly committed to keeping the public
name `SparseLuSolver` despite the dense-backed stub. The clean path is
**in-place upgrade** — the new real-sparse factorization becomes the new
`SparseLuSolver`; the existing dense path becomes a size/density-gated
fallback *inside the same type*, preserved as a private `DenseLuFallback`
path for cases where dense-storage actually wins on small/dense matrices.

## Options

### Option A — In-place upgrade with size/density-gated path (recommended)

Replace the body of `SparseLuSolver::solve_validated` with a **dispatcher**:

- Convert the input `CsrMatrix<T>` to CSC via `CscMatrix::from_csr`.
- Compute the density `nnz / n²`. If `n ≤ SMALL_SWITCH` (default 32 — small
  enough that the dense path's constant factor wins) OR `density ≥
  DENSITY_THRESHOLD` (default `0.1` from sparse-LU literature), use the
  existing dense `csr_to_dense` + `lu_decompose` path. The dense path is
  still correct — just not asymptotically optimal. For small matrices the
  dense path is also faster (no symbolic-factorization overhead). For
  near-dense matrices the sparse path's `O(nnz)` savings vanish and its
  constant factor becomes a tax.
- Otherwise (large + sparse): factor via **symbolic LU + numeric LU** over
  the CSC pattern, with **partial pivoting** at each elimination step and
  **natural column ordering** for v0.40.0 (RCM/AMD tracked as follow-up).

**Pros**:

- Preserves the public surface (`SparseLuSolver`, `sparse_lu_solve`,
  `DENSE_LIMIT_DEFAULT`, `csr_to_dense` all retain their types and names).
- Resolves the algorithmic defect at root (`O(nnz·k)` factorization where
  `k` is fill-in, vs `O(n³)` dense).
- No `[major]` consumer migration — `cfd-math/direct_solver.rs` keeps
  working without source changes.
- The existing 6 tests in `lu_sparse.rs` keep passing (small matrices route
  to the dense path they already exercised).
- Reuses existing `CscMatrix` infrastructure (no second CSC impl).

**Cons**:

- The dense path stays as a fallback path inside the same type — slight
  conceptual folding, but justified by the real crossover at small `n`.
- AMD ordering deferred (see Consequences).

### Option B — Separate `RealSparseLuSolver` + deprecate `SparseLuSolver`

Forbidden by `consolidation_discipline` (`integrity: compatibility soup`):
a rename/delete + new variant forecloses seamless consumer migration, and
the public surface already promised "sparse" — the alias-deprecation
avoidance rule says one authoritative name. Option A absorbs the new
factorization under the existing name, so the dead-name path does not arise.

### Option C — Sparse Cholesky

Rejected: requires SPD input. CFDrs's saddle-point class is indefinite;
Cholesky silently misfactors. (Optional add-on `SparseCholeskySolver` for
SPD-input consumers like thermal-conduction Poisson systems is **not** in
scope for this ADR — would be a separate ADR driven by an SPD-only consumer
if and when one materializes.)

### Option D — Keep current + iterative-only downstream routing

Strategic defect left in place. The CFDrs `with_direct_threshold(512)`
workaround forces medium systems to GMRES+AMG even when a real sparse LU
would be faster and produce a sharper residual. WAF (rejected as
technical-debt expansion).

## Decision (with recommendation)

**Option A.** Implement real sparse LU with partial pivoting over CSC,
size/density-gated dispatch inside the existing `SparseLuSolver`. Use
**natural column ordering for v0.40.0** and track AMD/RCM ordering as the
follow-up board item (see Consequences — the AMD algorithm's ~300-line
implementation surface exceeds the bounded increment's context budget, per
the AGENTS.md AMD-scope-risk caution).

### Algorithm class

**Left-looking** sparse LU with **partial pivoting** over CSC storage:

1. **Symbolic factorization** (`lu_symbolic::factor_symbolic`): given the
   input CSC sparsity pattern, compute the static sparsity patterns of
   `L` (unit lower triangular) and `U` (upper triangular), encoded as
   `l_col_ptr`, `l_row_indices`, `u_col_ptr`, `u_row_indices`. Under
   natural ordering this is a column-by-column reachability computation:
   the nonzero pattern of column `j` of `L` is the union (modulo j) of the
   nonzeros of column `j` of `A` and the patterns of all earlier columns
   of `L` whose pivot row index appears in `A[:, j]`. Storage is allocated
   to these patterns (so numeric factorization is single-pass, no dynamic
   reallocation).
2. **Numeric factorization** (`lu_numeric::factor_numeric`): fill the
   symbolic L/U buffers with computed values, doing partial-pivoting row
   permutation at each step. For column `j`: gather the column entries,
   eliminate each row index `> j` already accounted for by prior columns,
   then pick the pivot (largest |entry| in the surviving column, subject
   to `pivot_tolerance`). The pivot row permutation `P` is recorded so that
   `P · A = L · U`.
3. **Solve**: with `b` RHS, compute `Pb`, triangular solve `L · y = Pb`,
   then `U · x = y`. Return `x`.

### Pivot tolerance and singular detection

A pivot candidate with `|pivot| < pivot_tolerance * |max_col_entry|` is
treated as zero (matching the existing `SparseLuSolver` field semantics).
Singularity surfaces as `LetoError::StorageError` with a "matrix singular
to working precision" reason, matching the existing dense path's failure
mode (so consumers' error handling logic is unchanged).

### Dispatch thresholds

- `SMALL_SWITCH_DEFAULT: usize = 32` — matrices up to this order always take
  the dense path (constant-factor wins).
- `DENSITY_THRESHOLD_DEFAULT: f64 = 0.1` — `nnz / n² ≥ 0.1` takes the dense
  path (sparse-path savings vanish; sparse-path constant factor becomes a
  tax).
- The existing `max_size: usize` (default `DENSE_LIMIT_DEFAULT = 2048`) is
  preserved as the absolute ceiling — above it, return the same
  `LetoError::StorageError` pointing consumers at iterative solvers (unchanged
  behavior).
- These three constants live in `lu_sparse.rs` as `pub const`s, defaulting
  into the `SparseLuSolver` struct as the dense-limit does today. They are
  `pub` so callers like CFDrs `with_direct_threshold(N)` can pin them
  explicitly if desired (no immediate CFDrs change required — the defaults
  route small saddle-point systems through dense LU with no algorithmic
  regression, and large sparse saddle-point systems through real sparse LU).

### Files

New (split for SRP, deep vertical hierarchy per AGENTS.md
`architecture_scoping`):

- `crates/leto-ops/src/application/sparse/lu_symbolic.rs` — symbolic
  factorization + ordering entry point. ~250-350 lines. Public:
  `pub struct SymbolicLu { … }` and `pub fn factor_symbolic<T: RealScalar>(
  csc: &CscMatrix<T>) -> SymbolicLu`.
- `crates/leto-ops/src/application/sparse/lu_numeric.rs` — numeric
  factorization + solve. ~350-500 lines. Public: `pub struct NumericLu<T> {
  … }`, `pub fn factor_numeric<T: RealScalar>(csc: &CscMatrix<T>,
  symbolic: &SymbolicLu, pivot_tolerance: f64) -> Result<NumericLu<T>>`.

Upgraded:

- `crates/leto-ops/src/application/sparse/lu_sparse.rs` —
  `SparseLuSolver::solve_validated` becomes a dispatcher; struct gains
  `small_switch` + `density_threshold` fields with defaults; the previous
  dense-path body becomes a private `fn solve_dense_fallback`. Public
  `SparseLuSolver` API + `sparse_lu_solve` + `csr_to_dense` +
  `DENSE_LIMIT_DEFAULT` preserved. ~150-200 lines (down from 357).
- `crates/leto-ops/src/application/sparse/mod.rs` — register the two new
  modules + re-export `SymbolicLu`, `NumericLu` for callers wanting
  reusable factorizations across multiple RHS (Krylov preconditioner use,
  future work). The lib.rs re-export surface grows by exactly these two
  names (additive, `[minor]`).

### Tests

Existing 6 `mod tests` in `lu_sparse.rs` continue to pass (small matrices
route dense — same exact bytes of behavior).

New tests in `lu_numeric.rs` mod `tests`:

1. `factor_poisson_1d_laplacian_n16_roundtrip` — n=16 banded tridiagonal
   Laplacian; assert `‖A·x − b‖∞ < 1e-12` with closed-form `b = (1, …, 1)`
   solution `x = solve_laplacian_1d(b)`.
2. `factor_banded_5_diagonal_n32` — n=32, bandwidth 5; assert
   `‖A·x − b‖∞ < 1e-12` against a manufactured non-trivial `x`.
3. `factor_random_sparse_n64` — n=64, density ~0.05; round-trip against
   precomputed dense-LU solution as the oracle (so we verify differential
   equivalence between sparse-LU and the existing dense LU).
4. `density_threshold_routes_to_dense_path` — confirm a near-dense matrix
   goes through `solve_dense_fallback` (assert by observing the dispatch
   decision via a test-only hook OR by behavior — for matrices at the
   threshold boundary with randomly permuted entries, sparse LU and dense
   LU produce `‖x_sparse − x_dense‖∞ < 1e-12`).

All factorization tests must complete within the 30s nextest slow budget.
For matrices up to n=512, factorization completes in milliseconds; even
n=1024 Poisson-class systems finish well under 1s. The arithmetic is
`RealScalar` so the tests cover `f64` (and one `f32` parity smoke so
generic instantiation stays verified).

### Doctests

New public items ship standard Rustdoc sections (`# Errors`, `# Panics`
where reachable, `# Examples` runnable) per AGENTS.md `documentation`

## Consequences

### Positive

- `ATLAS-LETO-OPS-SPARSE-LU-001 [arch]` closes at the algorithmic level.
- CFDrs `with_direct_threshold(512)` becomes eligible for re-evaluation:
  once `Cargo.lock` pins the new leto-ops, re-benchmark
  `validate_poiseuille_flow` and consider raising the threshold back
  toward `4 096` or higher. **The threshold revert lives in the CFDrs
  repo as a separate refactor** — out of scope for this ADR; tracked as a
  follow-up board item.
- The CFDrs perf improvement flows through to other CFDrs saddle-point
  benchmarks that currently detour to iterative solvers at smaller sizes
  than necessary.

### Negative / acknowledged limits

- **AMD ordering deferred.** The AGENTS.md session-15 pitfalls caution
  explicitly warns: AMD has a ~300-line implementation surface; if it
  exceeds the bounded-increment context budget, ship natural ordering and
  track AMD as a follow-up. **This ADR ships natural ordering** — fill-in
  is not actively minimized for v0.40.0. For CFDrs's banded 2-D pressure
  systems, natural ordering is already near-optimal (bandwidth small); for
  unstructured 3-D systems the fill-in cost is real but bounded (worst case
  still `O(n²)` storage, not worse than the dense path being replaced). The
  follow-up AMD item is recorded on the board.
- Dense fallback path stays — slight conceptual non-minimalism, but the
  crossover at small `n` is a real measurement (symbolic factorization
  overhead exceeds dense-matrix constant factor around `n ≤ 32`), and
  unifying under one `SparseLuSolver` type preserves the public surface
  per the naming policy.
- No sparse QR / sparse Cholesky / sparse LDL^T variants shipped. SPD-only
  and rank-deficient classes are separate ADRs driven by consumers needing
  them, per `architecture_scoping: seam-first` (no seam without a present
  requirement).

### Migration

In-repo: none required. The leto-ops public surface is additive (`SymbolicLu`
and `NumericLu` are new). `SparseLuSolver` field gains `small_switch` and
`density_threshold` — these have `Default::default()`-equivalent values, and
the struct already had user-facing constructor-style fields (`max_size`,
`pivot_tolerance`), so existing field-literal constructions at consumer
sites continue to compile (`#[non_exhaustive]` is **not** introduced on
`SparseLuSolver` because that would break existing literal constructions —
the addition is `[minor]`-compatible by standard semver rules). Consumer
construction sites (CFDrs `direct_solver.rs`) inherit the new defaults
without source changes.

External: the test suite continues to verify the dense-path behavior on
small matrices byte-for-byte. The new sparse-path tests verify
differential equivalence against the dense path on medium matrices.
Performance claims (`O(nnz·k)` factorization) live in the module-level
Rustdoc, supported by the test timing budget assertion (each factorization
test must finish in well under 30s — verified by nextest's `slow-timeout`).

### Test-budget invariant

Per AGENTS.md `engineering_gates` + `performance_engineering`: the nextest
profile's 30s slow-timeout is the hard gate. Sparse LU factorization for
n ≤ 512 must complete in well under 30s (empirically milliseconds). If a
test approaches the bound, the production code is profiled and optimized
per farsight — **never** the bound raised or the workload shrunk.

## Verification plan

1. **Build**: `cargo check -p leto-ops --tests` finishes green (≤90s).
2. **Tests**: `cargo nextest run --no-fail-fast -p leto-ops` finishes green
   with all existing 6 + new 4 tests passing; the new sparse-path tests
   must each complete in <1s observed.
3. **Doctests**: `cargo test --doc -p leto-ops` green, new public items
   carry runnable examples.
4. **Lint**: `cargo clippy -p leto-ops --all-targets -- -D warnings` clean
   (incl. the workspace `clippy::pedantic` floor and `clippy::unwrap_used`
   deny — tests exempt from `unwrap_used`).
5. **Format**: `cargo fmt -p leto-ops --check` clean.
6. **Public API surface**: `cargo doc -p leto-ops --no-deps` clean — new
   public items carry `# Errors`/`# Examples` Rustdoc sections.
7. **Crossover assertion**: one test explicitly verifies the density
   threshold dispatch boundary — confirming the routing logic, not just one
   path's correctness.
8. **Cross-repo evidence**: after merge + leto sub/gitlink advance, CFDrs
   `cargo check -p cfd-math` succeeds without source changes (the public
   surface is preserved). The `with_direct_threshold` re-evaluation is a
   separate downstream follow-up.

## References

- Brezzi, F. (1974). *On the existence, uniqueness and approximation of
  saddle-point problems arising from Lagrangian multipliers*. RAIRO
  Analyse Numérique **8** (R-2), 129–151. The saddle-point citation already
  in `crates/cfd-3d/src/fem/solver.rs:23`.
- Davis, T. A. (2006). *Direct Methods for Sparse Linear Systems*. SIAM,
  Series on the Fundamentals of Algorithms. Chapter 8 (LU factorization,
  partial pivoting, symbolic + numeric phases); Chapter 7 (AMD reference
  implementation, deferred per Consequences).
- Amestoy, P. R., Davis, T. A., Duff, I. S. (1996). *An approximate minimum
  degree ordering algorithm*. SIAM J. Matrix Anal. Appl. **17** (4),
  886–905. Reserved for the follow-up AMD board item — explicitly not
  implemented in v0.40.0.
