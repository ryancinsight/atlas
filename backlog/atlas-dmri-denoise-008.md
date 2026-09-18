<a id="atlas-dmri-denoise-008"></a>
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

