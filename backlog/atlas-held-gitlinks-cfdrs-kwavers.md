<a id="atlas-held-gitlinks-cfdrs-kwavers"></a>
## ATLAS-HELD-GITLINKS-CFDRS-KWAVERS — The CFDrs and kwavers gitlinks trail member defaults that raise baseline rows [verification] [patch] — todo
- outcome: the `repos/CFDrs` and `repos/kwavers` gitlinks advance to their member defaults with no baseline row raised, so the scheduled "Gitlink pins at their members' default branches" job passes.
- evidence (basis b334401f2fcf; scheduled run 45939392672 failed at ddf18d670ace): `atlas-conformance.py check --repo <M> --member-path <checkout> --member-revision <default>` exits 1. CFDrs `b76f00a72132`
  (gitlink `40021147e365`, 14 behind) raises three board rows 0 -> 1 (`CFDRS-CIVIL-TIME`); kwavers `eb91da65678b` (gitlink `bee13af7268b`, 79 behind) raises 11 rows (`allow_sites` 297 -> 305 and ten more).
- oracle: both `check` commands exit 0 printing `0 regression(s)` (`--accept-raises` is not an option), and `python scripts/atlas-pin-drift.py --rev <revision with both advanced>` prints no `PIN DRIFT`.
- basis: b334401f2fcf; priority: verification; needs: ATLAS-MEMBER-BOARD-SCHEMA, ATLAS-DEPENDENCY-COHORT-20261127; scope: the two gitlinks; next step: fix the kwavers rows in kwavers, then advance both gitlinks together.
