<a id="atlas-provider-closure-2026-08-20"></a>
## ATLAS-PROVIDER-CLOSURE-2026-08-20 — Complete active provider slices [major][arch] — in-progress

- **outcome:** each provider's executable-book gate and named
  integration slice is hosted-verified at its merged default, gitlink
  advanced to that default without touching dirty primary checkouts.
- **delivered (hosted-terminal, gitlinks advanced):** Themis, RITK,
  Apollo, Hephaestus, Coeus, Kwavers, Hermes, Tyche, Consus P4, Helios
  lock sweep.
- **open — Hyperion:** PR [#21](https://github.com/ryancinsight/hyperion/pull/21)
  merged (`4df62f63`); post-merge CI/mdBook/Pages still queued. Pointer
  holds at `e2dbc9b` until terminal and page verified.
- **open — live-tree conformance:** sweep at `72cc6eb` exits 1, 13
  regressions/27 tightening classes (CFDrs oversized files + 42
  unformatted peer files; stale Consus/RITK behind origin; Moirai `SeqCst`).
