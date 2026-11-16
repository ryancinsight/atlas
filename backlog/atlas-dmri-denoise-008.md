<a id="atlas-dmri-denoise-008"></a>
## ATLAS-DMRI-DENOISE-008 — MP-PCA denoising and Gibbs unringing [minor] — todo
- outcome: MP-PCA denoising (`ritk_filter::mppca::MpPcaDenoiser`, ritk#623) and subvoxel Gibbs unringing (`ritk_filter::gibbs_unringing::GibbsUnringer`, ritk#625), the `dwidenoise`/`mrdegibbs` roles, run both single-threaded sweeps on the stack's parallel provider and are compared against MRtrix `dwidenoise`/`mrdegibbs` output on real DWI.
