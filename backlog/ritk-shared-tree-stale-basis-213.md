<a id="ritk-shared-tree-stale-basis-213"></a>
## RITK-SHARED-TREE-STALE-BASIS-213 — ritk's shared tree is checked out 58 commits behind origin [patch] — in-progress
- **outcome:** the shared ritk tree sits on a branch at or ahead of `origin/main`, with no commit landing from a stale basis.
- Mid-session a peer switched `repos/ritk` off `refactor/ritk-two-accessors-047` onto a local `main` 58 behind `origin/main` (2 ahead) — in a shared tree a branch switch moves the branch for everyone. This is the mechanism behind the stale-basis reverts seen repeatedly this sweep: a whole-file write from this base silently reverts everything landed since, passing the author's own gates.
- The 2 local commits are safe (mine, preserved on `origin/feat/tract-output-formats`); not fixing the branch switch unilaterally since a peer may be mid-work on it.
- **next:** confirm the 2 local commits are merged or dropped, and that the tree is moved to a branch at or ahead of origin.
- **Re-open trigger:** any commit lands in ritk from a base more than one sweep behind origin.
