<a id="atlas-arch-005"></a>
## ATLAS-ARCH-005 — Replace closed-set dyn dispatch in per-timestep paths [arch] — in-progress

- **outcome:** per-timestep `dyn` dispatch sites (`sources`, `boundary`,
  `Signal`, `Solver` in kwavers; similar in CFDrs) convert to exhaustively
  matched enums — static dispatch, no vtable — with criterion evidence per
  family since the change is performance-motivated.
- **owner:** opencode-2026-08-05. ADR 0041 delivered; execution slice
  parked — both scope repos peer-held (kwavers
  `refactor/retire-kwavers-optics` `e4e9966b6`, CFDrs `deps/eunomia-0.8`).
- **scope order:** `repos/kwavers` first (665 sites), then `repos/CFDrs`
  (352). Non-goal: mass-converting all 1,368 sites stack-wide.
- **next:** re-claim kwavers or CFDrs once its tree frees, convert the
  per-timestep dyn sites to an enum, verify zero remain on that path with
  no catch-all arm, and attach a criterion comparison.
