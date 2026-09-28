<a id="atlas-lane-sprawl-222"></a>
## ATLAS-LANE-SPRAWL-222 — 26 lane directories against a two-per-repo bound [patch] — in-progress
- **outcome:** a committed lane tool enforces the two-tree precondition, canonical root, and naming convention on create/re-point/close; every member at or under two trees; misplaced consus lane consolidated.
- **open:** the lane tool (`scripts/atlas-lane.py`, ADR 0066) and the `worktrees_outside_lane_root`/`detached_lanes` host-state classes close the generators. Live residue on 2026-09-27 (the new classes): `D:/{apollo,kwavers,ritk}-audit` trees outside the root, leto and ritk at 3 trees, one detached metis lane, and non-lane `worktrees/kwavers-log` and `worktrees/report`; each closes with `atlas-lane.py close` once clean and landed or pushed.
- **not a blocker:** at cap the existing lane is the next work (as `-221` proceeded, re-pointing a stale merged lane instead of a 4th tree).
