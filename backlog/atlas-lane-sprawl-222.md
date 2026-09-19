<a id="atlas-lane-sprawl-222"></a>
## ATLAS-LANE-SPRAWL-222 — 26 lane directories against a two-per-repo bound [patch] — in-progress

- **outcome:** a committed lane tool enforces the two-tree precondition,
  canonical root, and naming convention on create/re-point/close; every
  member at or under two trees; misplaced consus lane consolidated.
- **delivered:** `count_excess_worktrees` conformance class landed
  (deduplicated `febe7d5`, bound from `WORKTREE_BOUND`), with behavioural
  tests asserting the count crosses at the third tree.
- **open:** kwavers still holds 5 trees against a bound of 2. The clean
  detached lane at `D:/tmp/kw-verify` is outside the canonical root but
  an external checkout whose ownership Atlas doesn't establish —
  recorded residual, not a deletion target.
- **not a blocker:** at cap the existing lane is the next work (as `-221`
  proceeded, re-pointing a stale merged lane instead of a 4th tree).
