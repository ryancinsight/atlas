<a id="atlas-unwired-gates-224"></a>
## ATLAS-UNWIRED-GATES-224 — Instruments that exist, pass, and are never run [patch] — in-progress

**`atlas-registry-metadata.py` had never been invoked by any workflow.** It
was written, committed, and green — and on the single day it was run by hand
it found kwavers declaring six keywords against a cap of five, plus the
category slug `medical`, which does not exist in the crates.io taxonomy.
crates.io enforces both **at upload**, after the version number is spent, so
the rejection is not retryable under that version. Wired in `572a585`; the
defect it found is fixed in kwavers `1aa24beb7`.

An unreachable taxonomy degrades to `UNVERIFIED` at exit 0 and the slug
snapshot is committed, so it cannot flake on crates.io availability.

**`atlas-lane-audit.py` is deliberately left unwired.** It already implements
`-222`'s whole audit half — tree bound, canonical lane root, named branch,
prune freshness, standalone-clone detection — and currently reports the same
four violations. But a CI clone has one working tree, so in CI it would pass
unconditionally and prove nothing. It is an orient-time and
replenishment-time check by its own contract; its findings belong on the
board, which is where `-222` now carries them.

- Residual: `atlas_scattered_containers_classify.py` is also unwired. Assess
  whether it is CI-valid (like the registry check) or inherently local (like
  the lane audit) before deciding — those are the only two answers, and
  "wire everything" is the wrong one.
- The pattern, worth keeping: **a gate that has never failed may never have
  run.** Three instruments were built during this sweep; one was silently
  inert. Checking `grep -ohE "scripts/[a-z-]+\.py" .github/workflows/*.yml`
  against `ls scripts/*.py` is the ten-second version of that audit.

