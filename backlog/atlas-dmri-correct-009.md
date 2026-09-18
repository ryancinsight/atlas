<a id="atlas-dmri-correct-009"></a>
## ATLAS-DMRI-CORRECT-009 — Motion, eddy-current, and susceptibility correction [minor] — review

outcome: a series-level correction driver in `ritk-registration` covering the `eddy`/`topup` roles — per-volume gradient reorientation, series registration, and susceptibility (EPI) distortion correction — satisfying ADR 0036 verification condition 7.

Split from closed PR #82 into four standalone PRs, each cut fresh from `main` and independently verified: #84 per-volume gradient reorientation (main, 23/23); #85 rotation extraction from an affine (main, 54/54+doctest); #86 series alignment, consumes #85 (352/352); #87 EPI distortion model (main, 367/367).

next: (1) merge #84/#85/#86/#87 (#86 retargets to `main` on merge); (2) wire `register_series`'s reported transforms into a composed `correct_diffusion_series` entry point (no caller applies them yet); (3) implement susceptibility field *estimation* from a reversed-polarity pair — a regularized nonlinear fit over thousands of parameters; dense Coeus LM is the wrong instrument, and solver size/owner is still an open question.

Acceptance oracle still unbuildable: ADR 0036 condition 7 needs a synthesized anisotropic tensor field fitted after correction, which needs `ritk-diffusion`'s tensor fit (peer-owned, in flight); PR #82's tests cover the reorientation contract directly meanwhile.

Residual: `worktrees/ritk-pr-split` is deregistered but its directory could not be deleted (held by another process) — sweep once released.
