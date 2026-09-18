<a id="atlas-cfdrs-format-gate-2026-08-20"></a>
## ATLAS-CFDRS-FORMAT-GATE-2026-08-20 — Restore exact-default formatting gate [patch] — in-progress

The exact CFDrs default `aa54f5cdcdc4e406df0c60ea6c3cb507e968fc97` has a red
hosted CI run `32323543129`; the failure is formatting-only in
`crates/cfd-2d/src/solvers/cell_tracking/tracker.rs`,
`crates/cfd-core/src/management/aggregates/parameters.rs`, and
`crates/cfd-core/src/physics/cavitation/number.rs`. The canonical checkout is
peer-owned and dirty, so the bounded lane owns those three source files plus
the provider validation caller required to repair the hosted runtime failure.

**Acceptance:** the exact three-file format correction and the provider-side
validation repair are committed and pushed; the provider's exact-head Rust and
Pages gates are terminal green, with no peer source or lockfile state included.
This slice does not claim broader CFDrs closure until those gates pass.

The current Atlas session owns the bounded lane
`D:\\atlas\\worktrees\\CFDrs-format-gate`, PR
[#361](https://github.com/ryancinsight/CFDrs/pull/361). The exact-head provider
CI run `32408413904` at the formatting-only head is terminal failure. The
provider repair now has local exact nine-test numerical-fidelity evidence.

**Timeout increment (2026-08-22, head `c993b906`):** the replacement hosted run
`32449587886` at `c1e4fdcf` failed on the committed 30s nextest termination
bound — `cross_fidelity_trifurcation_dominance` terminated at 30.008s. Local
instrumentation attributes the cost to the Picard assembly/Krylov path (~9s)
plus SDF meshing (~1s) spread across first-party FEM code and provider-external
numeric crates (`gaia-mesh`, `leto`, `nalgebra`), so named-package opt-level
raises measured no effect. Raising the test profile to `opt-level = 2`
measures 11.4s → 2.0s locally (5.5×), restoring hosted headroom; dev/debug
profiles are unchanged and no test or workload was reduced. Local evidence at
`c993b906`: `cfd-validation` nextest 435/435 (10.3s total), doctests 4 passed,
`cargo fmt --all --check` clean. **Closed (2026-08-23):** replacement hosted run
`32588697868` terminal success at `c993b906`; PR #361 merged with the
expected-head guard at default `a70faea6`; default CI run `32589906080`
terminal success; live Pages HTTP 200 (the merge touched no book content, so
no Pages deployment is expected). The Atlas gitlink advanced to `a70faea6`
(commit `43fe895`).

