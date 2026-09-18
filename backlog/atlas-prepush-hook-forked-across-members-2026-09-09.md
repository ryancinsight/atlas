<a id="atlas-prepush-hook-forked-across-members-2026-09-09"></a>
## ATLAS-PREPUSH-HOOK-FORKED-ACROSS-MEMBERS-2026-09-09 — One gate, twenty-three copies, six versions [patch] [ci] — in-progress

outcome: the member `pre-push` gate has one stack-level owner in the meta-repo's `scripts/git-hooks/pre-push`, consumed by every member, so a fix reaches all repos instead of one. Two defects fixed at the source: the lockfile-guard base was vacuous on every new-branch push (six hook versions), and the gate half assumed `origin/main` and failed open on a non-`main` default (hephaestus's is `master`) — both closed via a shared `default_branch_base` helper.

acceptance: `member_gate_versions` (the conformance scan's distinct-hook-content count) reaches 1, including coeus.

status: rollout landed for 8 members (asclepius, athena, consus, gaia, leto, aequitas, apollo, ares); 10 more enqueued on auto-merge behind pending checks (harmonia, helios, hephaestus, hermes, horae, hyperion, proteus, ritk, themis, tyche).

open — 9 members not yet deployable:
- eunomia: blocked — owned `pre-commit` fails closed without `scripts/lockfile.py`, which eunomia lacks and cannot receive by copy (member copies of `lockfile.py` aren't stack-synced); needs a member-appropriate checker first.
- iris, melinoe, prometheus: same — no `.githooks/` directory and no `lockfile.py`.
- CFDrs, kwavers, metis, mnemosyne, moirai: uncommitted peer work in the tree when the rollout ran; re-run the sync once clean.
- coeus: PR closed unmerged — needs a decision, not a sync: coeus adopts the owned hook (retiring its own shared `.githooks/lockfile.sh` entry + `test_hooks.py`), or the owned hook absorbs coeus's shared-entry design (the only member that tests its hooks at all, and the only one that caught the guard failing open).
