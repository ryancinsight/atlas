<a id="atlas-dmri-denoise-008"></a>
## ATLAS-DMRI-DENOISE-008 — MP-PCA denoising and Gibbs unringing [minor] — todo

- outcome: `ritk-filter` gains Marchenko-Pastur PCA denoising and subvoxel
  Gibbs ringing removal — the `dwidenoise`/`mrdegibbs` roles, the first two
  stages of every dMRI pipeline. Neither exists today: current denoisers
  (bilateral, patch, median, rank, anisotropic-diffusion) are not the MP-PCA
  estimator, and `noise_estimation.rs` is MAD over Gaussian noise, not the
  Rician/noncentral-chi model magnitude DWI follows.
- next: implement MP-PCA with the threshold derived from the
  Marchenko-Pastur distribution and patch geometry, never an empirical
  constant; verify on a synthesized field with a known noise level.
- related: Rician bias correction splits out as its own item if MP-PCA
  outgrows its acceptance criteria.

