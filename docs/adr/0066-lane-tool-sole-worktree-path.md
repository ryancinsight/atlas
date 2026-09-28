# ADR 0066: The lane tool is the only way to create a worktree

- Status: Accepted
- Date: 2026-09-27
- Item: [ATLAS-LANE-SPRAWL-222](../../backlog.md#atlas-lane-sprawl-222)

## Context

The lane rules (AGENTS.md `git_discipline`: Worktrees) bound each repository to its main tree plus one linked lane under `worktrees/`, named `<repo>-<branch-slug>`, on a named branch; the umbrella repository opens no lanes. They were enforced only after the fact by `scripts/atlas-lane-audit.py`, and nothing in `scripts/` ran `git worktree add`. A sweep on 2026-09-26 removed ten stale trees, all from two generators: an A/B calibration run that made one detached tree per baseline revision under `tmp/cal*-<member>`, and an audit that made one `D:/<member>-audit` tree per member even at the cap.

## Decision

`scripts/atlas-lane.py` is the only sanctioned way to create, re-point, or close a worktree, and to materialize an A/B baseline:

- `create` refuses at two trees (naming the held lane and its branch), refuses a lane root that resolves outside the stack root, and refuses revision-shaped or `HEAD` targets that would leave the lane detached. The lane path is derived, never supplied.
- `repoint` and `close` require a clean lane whose work passes the landed-work proof (`merge-tree --write-tree` against the fetched default with an empty attribute tree). `close` also accepts a clean lane whose branch is pushed. `repoint --unlanded` overrides the proof only; a dirty lane is never re-pointed, since switching would carry its dirt onto another branch.
- `export` writes `git archive <rev>^{tree}` outside the lane root. An A/B baseline is a tree, not a checkout.

The conformance scan counts, per repository, `excess_worktrees`, `worktrees_outside_lane_root` (a harness-managed `.claude/worktrees/` lane counts as canonical, as the lane audit already treats it), and `detached_lanes`. These classes read `.git/worktrees/` registrations on the live checkout, so they are host-observed: reported as `HOST STATE` rows, recorded as zero by `generate`, and not gating a `--member-revision` check.

## Alternatives rejected

- Audit only: the audit found the sprawl after both generators had run; a precondition prevents the tree.
- A pre-command git hook: git has no hook on `worktree add`.
- Gating the classes as repository debt: a CI checkout has no lanes, so the count would describe the machine, not the revision, and flap pushes that changed nothing.

## Consequences

A caller that needs a second concurrent branch at the cap works in the existing lane or closes it. Evidence tools that compare revisions export trees instead of checking them out.

Overturning evidence: a workflow that needs two concurrent linked trees of one repository and cannot be served by an export.
