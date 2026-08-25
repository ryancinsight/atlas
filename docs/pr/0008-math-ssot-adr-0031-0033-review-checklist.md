# PR 0008 — Math/Linalg SSOT ADRs 0031-0033 Review & Merge Checklist

- **Atlas-parent change**: Yes — this PR advances `repos/leto`, `repos/CFDrs`, and `repos/kwavers` gitlinks and updates Atlas-parent PM artifacts (`gap_audit.md`, `docs/audit/math-ssot-ledger.md`, ADR status lines).
- **Sprint class**: `[arch]` (SSOT boundary + cross-repo consumer migration).
- **Depends on**: ADR 0031, ADR 0032, ADR 0033 already accepted/implemented.
- **Cross-repo consumers**: `cfd-math` (CFDrs), `kwavers-math`, `kwavers-solver` (Kwavers).
- **Reserved Atlas tag**: `atlas/math-ssot-adr-0031-0033-closure` (annotated).
- **Circulation**: CFDrs module owner / claim stream; Kwavers module owner / claim stream; leto-ops provider owner (SSOT provider).

## Purpose

This PR closes the review loop for the first three math/linalg SSOT ADRs:

| ADR | Title | Consumer | Provider SSOT |
|-----|-------|----------|---------------|
| ADR 0031 | Remove CFDrs `cfd-math` finite-difference/iterative wrapper | CFDrs `cfd-math` | `leto_ops::FiniteDifference` / iterative solvers |
| ADR 0032 | Close Kwavers `kwavers-math` `linear_algebra::{ext, complex}` trivial wrappers | Kwavers `kwavers-math` | `leto_ops::{solve, inv, eig, complex_solve, complex_inv}` |
| ADR 0033 | Complete Kwavers 3-D finite-difference staggered-grid migration to `leto-ops` | Kwavers `kwavers-math` / `kwavers-solver` | `leto_ops::FiniteDifference3D` |

This checklist is the PR description. Reviewers from CFDrs and Kwavers should sign off before the merge.

## Files changed

| File | Type | Substance |
|------|------|-----------|
| `repos/leto/docs/adr/0031-cfdrs-cfd-math-fd-iterative-ssot-consolidation.md` | Status bump | `Status: Accepted / Implemented` |
| `repos/leto/docs/adr/0032-kwavers-linear-algebra-wrapper-closure.md` | Status bump | `Status: Accepted / Implemented` |
| `repos/leto/docs/adr/0033-kwavers-3d-finite-difference-staggered-completion.md` | Status bump | `Status: Accepted / Implemented` |
| `docs/audit/math-ssot-ledger.md` | Status bump | ADR 0031-0033 status lines `Drafted` → `Accepted` |
| `gap_audit.md` | Audit section | New “Math/Linalg SSOT ADRs accepted (2026-07-27)” section |
| `repos/CFDrs/crates/cfd-math/src/lib.rs` | Source | Removed `differentiation` module; added `fd_extensions` re-export; updated prelude |
| `repos/CFDrs/crates/cfd-math/src/differentiation/*` | Deletion | Legacy wrapper directory removed |
| `repos/CFDrs/crates/cfd-math/src/fd_extensions.rs` | Addition | CFD-specific FD SIMD + gradient helpers |
| `repos/kwavers/crates/kwavers-math/src/linear_algebra/ext.rs` | Deletion | Trivial `LinearAlgebraExt` wrapper removed |
| `repos/kwavers/crates/kwavers-math/src/linear_algebra/complex.rs` | Deletion | Trivial `ComplexLinearAlgebra` wrapper removed |
| `repos/kwavers/crates/kwavers-math/src/numerics/operators/differential/staggered_grid/*` | Deletion | Redundant `StaggeredGridOperator` removed |
| `repos/kwavers/crates/kwavers-solver/src/forward/fdtd/solver/*` | Source | `StaggeredGridOperator` → `leto_ops::FiniteDifference3D<f64>` |
| `repos/kwavers/crates/kwavers-solver/src/forward/fdtd/velocity_updater.rs` | Source | Uses `self.grid.dx/dy/dz` instead of operator spacings |
| `repos/kwavers/crates/kwavers-solver/src/forward/fdtd/pressure_updater/divergence.rs` | Source | Uses `apply_x_into/y_into/z_into` on backward-configured operator |
| `repos/kwavers/crates/kwavers-solver/src/forward/fdtd/pressure_updater/tests.rs` | Source | Pre-allocated output arrays for leto-ops API |
| `repos/leto/crates/leto-ops/src/application/diff/three_dimensional.rs` | Provider enabler (gitlink advance) | `StaggeredForward` / `StaggeredBackward` branches already landed in leto-ops; this PR advances the leto gitlink |

## Per-ADR review checklist

### ADR 0031 — CFDrs `cfd-math` wrapper deletion

- [ ] `cfd-math/src/differentiation/` directory is fully removed.
- [ ] `cfd-math/src/lib.rs` no longer declares `pub mod differentiation;`.
- [ ] `cfd-math` exposes SSOT surface through `pub mod fd`, `pub mod interp`, `pub mod quadrature_rules`, and `pub mod iterative` (leto-ops re-exports).
- [ ] `cfd-math::prelude` no longer imports the deleted `differentiation::FiniteDifference`.
- [ ] `cargo check -p cfd-math` passes with no new warnings.
- [ ] `cargo test -p cfd-math --lib` passes.
- [ ] Any cfd-1d / cfd-3d / cfd-validation consumer that previously imported `cfd_math::differentiation::FiniteDifference` is updated to `cfd_math::fd::FiniteDifference`.
- [ ] `cfd-math::linear_solver` domain-specific pieces (multigrid, block preconditioners, solver chain, direct solver bridge) are **not** deleted or relocated.
- [ ] `fd_extensions::first_derivative_simd` retains its f32-only unit test and matches the generic `FiniteDifference` output to ≤1 ULP.

### ADR 0032 — Kwavers `linear_algebra::{ext, complex}` closure

- [ ] `kwavers-math/src/linear_algebra/ext.rs` is removed.
- [ ] `kwavers-math/src/linear_algebra/complex.rs` is removed.
- [ ] No source file in `repos/kwavers` references `LinearAlgebraExt` or `ComplexLinearAlgebra`.
- [ ] Call sites import `solve`, `inv`, `symmetric_eigen_jacobi`, `hermitian_eigen_jacobi`, `complex_solve`, and `complex_inv` directly from `leto_ops`.
- [ ] `KwaversError` conversion from `leto::LetoError` is preserved at all consumer boundaries.
- [ ] `cargo check -p kwavers-math` passes with no errors.
- [ ] `cargo check -p kwavers-analysis` passes (MVDR beamforming uses `leto_ops::complex_solve`).
- [ ] `kwavers-math::linear_algebra::sparse::eigenvalue` inverse-power iteration is left intact (domain-specific, not part of this ADR).

### ADR 0033 — Kwavers 3-D FD staggered migration

- [ ] `leto_ops::FiniteDifference3DScheme::StaggeredForward` / `StaggeredBackward` exist and are documented.
- [ ] `kwavers-math/src/numerics/operators/differential/staggered_grid/` directory is fully removed.
- [ ] `kwavers-math/src/numerics/operators/differential/traversal.rs` is removed (helper used only by staggered half).
- [ ] `kwavers-math/src/numerics/operators/differential/mod.rs` only re-exports leto-ops types; `DifferentialOperator` trait shim is removed.
- [ ] `kwavers-math/src/numerics/operators/mod.rs` keeps only `pub use leto_ops::{FiniteDifference3D, FiniteDifference3DScheme};`.
- [ ] `kwavers-solver` stores `staggered_operator: FiniteDifference3D<f64>` configured as `StaggeredBackward`.
- [ ] `kwavers-solver` velocity updater uses `self.grid.dx/dy/dz` directly (decoupled from operator).
- [ ] `kwavers-solver` pressure updater uses `apply_x_into/y_into/z_into` on the backward-configured operator.
- [ ] `cargo check -p kwavers-math -p kwavers-solver` passes.
- [ ] `cargo test -p kwavers-solver --lib` passes.
- [ ] No remaining references to `StaggeredGridOperator` in compiled code.

## Cross-cutting review checklist

- [ ] `docs/audit/math-ssot-ledger.md` status lines for ADR 0031/0032/0033 read `Status: Accepted`.
- [ ] `gap_audit.md` contains the “Math/Linalg SSOT ADRs accepted (2026-07-27)” section with correct ADR titles.
- [ ] All three ADR files in `repos/leto/docs/adr/` have consistent status wording (`Accepted / Implemented`).
- [ ] No stale `Proposed`, `Drafted`, or `Closed` references for these ADRs.
- [ ] Atlas-parent gitlinks for `repos/leto`, `repos/CFDrs`, and `repos/kwavers` are updated to the merge commits implementing these ADRs.
- [ ] `repos/CFDrs/CHANGELOG.md` and `repos/kwavers/CHANGELOG.md` (if applicable) contain entries for the wrapper deletions / migrations.

## Verification commands

```bash
# ADR 0031
(cd repos/CFDrs && cargo check -p cfd-math --offline)
(cd repos/CFDrs && cargo test -p cfd-math --lib --offline)

# ADR 0032
(cd repos/kwavers && cargo check -p kwavers-math --offline)
(cd repos/kwavers && cargo check -p kwavers-analysis --offline)

# ADR 0033
(cd repos/kwavers && cargo check -p kwavers-math -p kwavers-solver --offline)
(cd repos/kwavers && cargo test -p kwavers-solver --lib --offline)

# Cross-cutting stale-reference scan
rg -g '*.rs' 'StaggeredGridOperator|LinearAlgebraExt|ComplexLinearAlgebra' repos/kwavers repos/CFDrs
rg -g '*.md' 'Status:\s*(Proposed|Drafted)' repos/leto/docs/adr docs/audit/math-ssot-ledger.md
```

## Sign-off

| Module | Owner / Claim Stream | Sign-off | Date |
|--------|----------------------|----------|------|
| CFDrs (`cfd-math`) | CFDrs module owner / claim stream | [ ] | |
| Kwavers (`kwavers-math`) | Kwavers module owner / claim stream | [ ] | |
| Kwavers (`kwavers-solver`) | Kwavers solver owner / claim stream | [ ] | |
| leto-ops (provider SSOT) | Leto-ops provider owner / claim stream | [ ] | |
| Atlas-meta PM artifacts | Atlas-meta owner / claim stream | [ ] | |

## Merge ceremony

1. Confirm all sign-offs above are checked.
2. Run the verification commands; all must pass.
3. Advance `repos/leto`, `repos/CFDrs`, and `repos/kwavers` gitlinks to the implementation merge commits.
4. Commit Atlas-parent PM artifact updates (`gap_audit.md`, `docs/audit/math-ssot-ledger.md`, ADR status lines).
5. Annotated tag: `atlas/math-ssot-adr-0031-0033-closure` on the Atlas-parent merge commit.
6. Push the tag and merge commit.

## References

- [ADR 0031](../../repos/leto/docs/adr/0031-cfdrs-cfd-math-fd-iterative-ssot-consolidation.md)
- [ADR 0032](../../repos/leto/docs/adr/0032-kwavers-linear-algebra-wrapper-closure.md)
- [ADR 0033](../../repos/leto/docs/adr/0033-kwavers-3d-finite-difference-staggered-completion.md)
- `docs/audit/math-ssot-ledger.md` §7.1-7.3
- `gap_audit.md` §“Math/Linalg SSOT ADRs accepted (2026-07-27)”
- ADR 0010 — Atlas-parent pointer advance + tag ritual
- ADR 0011 — Atlas-root working-tree hygiene ritual
