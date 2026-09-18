<a id="atlas-crate-level-allows-217"></a>
## ATLAS-CRATE-LEVEL-ALLOWS-217 — 502 blanket suppressions the ratchet never counted [major] — in-progress

- **outcome:** every crate-level `#![allow(...)]` fixes its lint or
  converts to a self-expiring `#[expect(lint, reason)]`; `allow_sites`
  (fixed `d9c8c60`) ratchets to zero.
- **done (MERGEABLE PRs):** moirai `0746861`; CFDrs
  [#372](https://github.com/ryancinsight/CFDrs/pull/372); kwavers
  [#646](https://github.com/ryancinsight/kwavers/pull/646); consus
  [#55](https://github.com/ryancinsight/consus/pull/55).
- **open:** CFDrs step 3 (~105 per-crate escalations, separate PR);
  coeus 18 (peer branch claims it), ritk 8, gaia 4, mnemosyne 2,
  hermes 1, leto 1.
- **apollo residual:** three `thread_local!` sites lack the
  const-for-thread-local expect; `twiddle.rs` is its own design question.
