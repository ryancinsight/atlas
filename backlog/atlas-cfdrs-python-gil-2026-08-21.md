<a id="atlas-cfdrs-python-gil-2026-08-21"></a>
## ATLAS-CFDRS-PYTHON-GIL-2026-08-21 — Complete PyO3 solver GIL boundaries [minor] — in-progress

- Provider commit `575375e85ef0e4344461e3eb2635d28d10ad5997` adds
  `Python::detach` around every remaining input-sensitive cfd-python solver
  computation, keeps NumPy conversion under the GIL, and adds bounded
  Python-thread regression coverage. Local formatting, locked check, warning
  denied Clippy, Rustdoc, abi3 wheel build, and the new concurrency test pass.
- Full wheel tests pass `4`; one pre-existing dirty-main mismatch remains at
  the Casson/Newtonian branch constant (`0.0035` versus a peer expectation of
  `0.00345`). Mypy is unavailable and cdylib doctests are unsupported.
- PR [#365](https://github.com/ryancinsight/CFDrs/pull/365) is published at
  that exact head. The worker temporarily reused the clean CFDrs format lane;
  after publishing, the lane was restored to `fix/cfdrs-format-gate` at
  `c1e4fdcf`, preserving PR #361's scope. Atlas's CFDrs pointer is unchanged.
- **Hosted hold:** PR #365 is `mergeable=false`/`dirty` with no Actions runs
  returned for the exact head; `recurseml/analysis` is errored and CodeRabbit
  is rate-limited. The live Pages book is HTTP 200, but docs.rs/crates.io have
  no `cfd-python` artifact and the existing PyPI name belongs to an unrelated
  package, so release identity remains unresolved. The stale `0.0035` versus
  `0.00345` test expectation and an unrelated existing Clippy blocker remain
  provider-side residuals.
- **Verification residual:** the new Python-thread test detects progress with
  bounded waits and a large deterministic workload, but does not yet meet the
  repository's event/barrier-only synchronization preference. Re-open on a
  clean CFDrs lane; do not displace PR #361's restored format lane.

