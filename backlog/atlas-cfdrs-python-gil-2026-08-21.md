<a id="atlas-cfdrs-python-gil-2026-08-21"></a>
## ATLAS-CFDRS-PYTHON-GIL-2026-08-21 — Complete PyO3 solver GIL boundaries [minor] — todo
outcome: `Python::detach` wraps every input-sensitive cfd-python solver computation (NumPy conversion stays under the GIL), proven by a Python-thread overlap test synchronized on events or barriers and by value-semantic result checks.
basis: 2b000c51b; state: PR [#365](https://github.com/ryancinsight/CFDrs/pull/365) closed unmerged; at CFDrs origin/main `detach` appears only in `crates/cfd-python/src/bifurcation.rs` and `poiseuille_2d.rs`, and `solver_2d/`, `solver_3d/` and `womersley.rs` carry none. next: `git fetch origin pull/365/head`, port its detach sites to current main, and replace its bounded-wait test with an event-synchronized one.
