<a id="atlas-prepush-hook-forked-across-members-2026-09-09"></a>
## ATLAS-PREPUSH-HOOK-FORKED-ACROSS-MEMBERS-2026-09-09 — One gate, twenty-three copies, six versions [patch] [ci] — in-progress

outcome: the member `pre-push` gate has one stack-level owner in the meta-repo's `scripts/git-hooks/pre-push`, consumed by every member, so a fix reaches all repos instead of one. Two defects fixed at the source: the lockfile-guard base was vacuous on every new-branch push (six hook versions), and the gate half assumed `origin/main` and failed open on a non-`main` default (hephaestus's is `master`) — both closed via a shared `default_branch_base` helper.

acceptance: `member_gate_versions` (the conformance scan's distinct-hook-content count) reaches 1, including coeus.

status (measured 2026-09-21T16:23Z, canonical blob `0fc89348`): six distinct contents across the members that carry the file. At the canonical revision: CFDrs, ares, asclepius, athena, consus, gaia, harmonia, helios, hermes, horae, iris, melinoe, mnemosyne, ritk. One revision behind (`fab87b29`): aequitas, eunomia, hephaestus, kwavers, leto, moirai. Two behind (`d1068cf4`): hyperion, prometheus, proteus, themis, tyche. Apollo at `68ec5bba`; report at `d6f804ef`; coeus at its own `c6a5f49e`. Canonical requests open: apollo#528, coeus#385, kwavers#815, leto#213, metis#325.

open:
- the publish is idempotent now: `publish-hooks` lost its `--branch` argument and treats an already-open request as the re-run case rather than a failure. Eighteen duplicate requests on `ci/sync-stack-hooks-20260921` — a 14:47 sweep's self-named branch, deploying `fab87b29` onto members whose default already carried `0fc89348`, which would have reverted the hook on twelve of them — are closed and their branches deleted. Re-run `publish-hooks --push` to put the current hook on `ci/sync-stack-hooks` for every member still behind.
- leoneuro-rs and metis carry no `.githooks/pre-push` on their default branch; metis#325 adds it.
- coeus: PR closed unmerged — needs a decision, not a sync: coeus adopts the owned hook (retiring its own shared `.githooks/lockfile.sh` entry + `test_hooks.py`), or the owned hook absorbs coeus's shared-entry design (the only member that tests its hooks at all, and the only one that caught the guard failing open).
- eunomia: owned `pre-commit` fails closed without `scripts/lockfile.py`, which eunomia lacks and cannot receive by copy (member copies of `lockfile.py` aren't stack-synced); needs a member-appropriate checker first.
