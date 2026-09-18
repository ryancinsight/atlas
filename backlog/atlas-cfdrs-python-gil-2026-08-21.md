<a id="atlas-cfdrs-python-gil-2026-08-21"></a>
## ATLAS-CFDRS-PYTHON-GIL-2026-08-21 — Complete PyO3 solver GIL boundaries [minor] — in-progress

delivered: `Python::detach` around every remaining input-sensitive cfd-python solver computation, NumPy conversion kept under the GIL, bounded Python-thread regression coverage added. Local format/check/Clippy/Rustdoc, abi3 wheel build, and the new concurrency test pass; full wheel tests 4/4. Merged as PR [#365](https://github.com/ryancinsight/CFDrs/pull/365).

Open: PR #365 is `mergeable=false`/`dirty`, no Actions runs at the exact head; `recurseml/analysis` errored, CodeRabbit rate-limited. A pre-existing dirty-main test-expectation mismatch (Casson/Newtonian constant `0.0035` vs peer-expected `0.00345`) and an unrelated existing Clippy blocker remain provider-side. crates.io/PyPI release identity for `cfd-python` is unresolved (name taken by an unrelated package).

Verification residual: the new Python-thread test uses bounded waits plus a large deterministic workload rather than event/barrier-only synchronization. Re-open on a clean CFDrs lane without displacing PR #361's restored format lane (`fix/cfdrs-format-gate` at `c1e4fdcf`).
