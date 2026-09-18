<a id="ritk-shared-tree-stale-basis-213"></a>
## RITK-SHARED-TREE-STALE-BASIS-213 — ritk's shared tree is checked out 58 commits behind origin [patch] — in-progress

- Mid-session a peer switched `repos/ritk` off `refactor/ritk-two-accessors-047`
  onto a local `main` sitting **58 behind `origin/main` and 2 ahead**. In a
  shared tree a branch switch moves the branch for everyone, so this landed
  under an in-flight verification without warning.
- **This is the mechanism behind the stale-basis reverts seen repeatedly this
  sweep.** Any commit authored from this checkout is built on a 58-commit-old
  base; a whole-file write or artefact regeneration from it silently reverts
  everything landed since, passes the author's own gates, and surfaces later
  as unrelated deletions. Filing rather than fixing: the two local commits are
  safe (both mine, 4 days old, preserved on
  `origin/feat/tract-output-formats`), so nothing is stranded, but moving a
  branch a peer just checked out is not mine to do while they may be mid-work.
- It also produced two false readings in this session, both corrected below
  under `-210`.
- Acceptance: the tree is on a branch at or ahead of `origin/main`, and the
  2 local commits are confirmed merged or dropped. Re-open trigger: any
  commit lands in ritk from a base more than one sweep behind origin.

