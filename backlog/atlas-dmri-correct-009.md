<a id="atlas-dmri-correct-009"></a>
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

