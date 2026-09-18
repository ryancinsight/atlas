<a id="atlas-stale-checkout-findings-223"></a>
## ATLAS-STALE-CHECKOUT-FINDINGS-223 — Gates measure the checkout, and 8 of 25 members are behind [patch] — in-progress

**Four false findings this session trace to one cause.** Gates read whichever
revision happens to be checked out. A survey today found **8 of 25 members
behind their origin**: CFDrs 5, coeus 6, consus 3, gaia 2, themis 2,
aequitas 1, apollo 1, tyche 1.

The four, all reported as defects before being traced:

1. ritk's `apollo-fft` requirement read as lagging at `^0.26` with my bump
   orphaned — I was reading a `main` 58 commits behind (`-213`).
2. The `hermes-simd-core ^0.6` resolver failure attributed to that lag; it
   was the stale base.
3. Three ADRs reported untracked — that one was the *index* rather than the
   checkout, but the same shape (`-219`).
4. coeus reporting a drifted ADR index, where `origin/main` had carried the
   missing row for six commits. I regenerated it and nearly committed the
   redundant change before checking upstream.

Fixed in `7481561` for the ADR gate: findings now state how far behind the
checkout is. The fallback to `origin/main` is the case that matters, not an
edge — a detached HEAD has no `@{upstream}`, and detached checkouts are
exactly the stale ones.

- Residual: `atlas-conformance.py --worktree` has the same exposure. It does
  guard the default path (`check_clean_revision` requires a clean tree with
  matching gitlinks), but `--worktree` bypasses that and is what gets run
  while peers hold dirty trees — every conformance number in this session
  came from it.
- Acceptance: any gate reporting against a checkout states that checkout's
  distance from its upstream, or refuses to report; and the members above are
  brought current, which is `-213`'s territory.

