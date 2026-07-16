# Atlas backlog

## Completed

- **META-001** [patch] — Align public Atlas submodule pins with fetched default
  branches. Acceptance: every public gitlink matches its repository's fetched
  `origin/HEAD`; the integration commit passes structural verification.
- **META-002** [patch] — Advance the Apollo gitlink after its provider-boundary
  merge landed during META-001 integration. Acceptance: the public Apollo pin
  matches its fetched `origin/HEAD` and all other public gitlinks remain
  aligned.
- **META-003** [patch] — Register Kwavers and Helios at their fetched default
  commits, then align the root documentation and shared build-artifact policy.
  Acceptance: all sixteen public gitlinks match their resolved `origin/HEAD`
  and cross-stack test commands use `cargo nextest run` or `cargo test --doc`.

## Ready

- No unclaimed meta-repository item is ready after META-001. The next item is
  created by the next provider-default change or by a recorded integration
  failure.
