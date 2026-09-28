<a id="atlas-lockfile-checker-single-source"></a>
## ATLAS-LOCKFILE-CHECKER-SINGLE-SOURCE — Run the stack-owned lockfile checker, not member copies [patch] — todo
- priority: tightening
- outcome: the member pre-commit and pre-push hooks run atlas `scripts/lockfile.py` from the stack scripts they already extract from the fetched default (as they do for the budget, secret, ratchet and identity tools), and the per-member `scripts/lockfile.py` copies are deleted.
- evidence (2026-09-27, each member's fetched default): 20 members carry one identical copy, 5 carry distinct variants, 3 lack the file (iris, melinoe, prometheus), and atlas's own `scripts/lockfile.py` matches none of them. The hooks call the member copy, so the missing ones refuse every commit or push: melinoe cannot commit, and iris and prometheus vendored a copy to deliver.
- acceptance: a member without `scripts/lockfile.py` commits and pushes under the synced hooks; `git grep -l lockfile.py` over member defaults finds no copies; the conformance scan counts member copies as a class that may only decrease.
- needs: atlas#328 (open; rewrites the same hook) landed first.
- scope: `scripts/git-hooks/pre-push`, `scripts/git-hooks/pre-commit`, `scripts/tests/test_atlas_pre_push_gate.py`, member `scripts/lockfile.py` (deleted per member through publish-hooks).
- next step: after #328 merges, route the lockfile check through `$stack_scripts/lockfile.py` with an export-relative `--manifest-path`, then publish-hooks and delete the copies.
