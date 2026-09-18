<a id="atlas-lane-sprawl-222"></a>
## ATLAS-LANE-SPRAWL-222 — 26 lane directories against a two-per-repo bound [patch] — in-progress

Found while needing one lane for `-221`. `git_discipline: Worktrees` bounds a
repository to **two** working trees (main plus one lane), and the bound is a
creation precondition, not an aspiration.

| repo | trees | bound |
|---|---|---|
| kwavers | 5 | 2 |

`worktrees/` currently holds **16 directories**, including the sanctioned
`.archive` metadata directory. The former empty Consus lane directory and
two empty root Consus husks were removed after confirming zero children. The
remaining structural violation is the clean detached Kwavers lane at
`D:/tmp/kw-verify`, outside the single canonical lane root; it remains
unremoved because it is an external checkout whose ownership is not
established by this tree.

The remaining external lane is clean, but its owning process and intended
lifecycle are not established from Atlas. It remains a recorded residual,
not a deletion target.

The rule already names the cause: "sprawl is friction's product", and the
prescribed fix is a committed lane tool making create/re-point/close one
command each, with the tree-count precondition enforced in `create`. Without
it the compliant path is more work than the workaround, which is exactly the
state here.

- Acceptance: a committed lane tool enforcing the two-tree precondition, the
  canonical root, and the naming convention; every member at or under two
  trees; the misplaced consus lane consolidated (`git worktree move`); the
  husks cleared once their holders exit. ~~A conformance class counting trees
  per member so the bound is measured rather than remembered.~~

**Measurement half done 2026-08-19 — and built twice.** A peer landed
`count_excess_worktrees` in `dbb1a4e` while I was writing the same class, and
their commit swept my uncommitted definition in alongside theirs, so HEAD
briefly carried **two definitions**, the second shadowing the first. Nothing
failed, because both were correct and produced identical counts
(consus 1, kwavers 2, ritk 3). Deduplicated in `febe7d5`, keeping theirs and
porting two fixes: the bound now comes from `WORKTREE_BOUND` rather than a
bare literal, and the docstring's claim to read "the packed-refs mechanism"
is corrected to what it does read — `.git/worktrees/` entries, one per linked
worktree, which is why the bound is reduced by one before subtracting.

Behavioural tests cover whichever implementation survives: they build a real
repository, add lanes one at a time, and assert the count crosses at the third
tree. The ratchet now refuses a third tree exactly as it refuses any other
debt increase, so the bound is enforced rather than remembered.

The collision is itself the lesson worth keeping — two agents built the same
detector within an hour because neither claim was visible to the other until
it landed.
- **Not** a blocker for anything: at cap the existing lane is the next work,
  which is how `-221` proceeded — the stale `consus-zarr-fix` lane held a
  branch already merged as PR #47, so it was re-pointed rather than adding a
  fourth tree.

