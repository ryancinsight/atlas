<a id="atlas-hook-merge-range"></a>
## ATLAS-HOOK-MERGE-RANGE — A pushed merge of the default branch gates the default branch's own commits [patch] — todo
- Outcome: a branch update whose range contains `git merge origin/<default>` gates only commits not reachable from the fetched `origin/<default>`, so a manifest change that landed on main does not make the push gate the whole workspace.
- Evidence (origin/main 12708acf3ae4892d4443627f0d6d5016ddeb29d7, `scripts/git-hooks/pre-push`): for a remote tip that is an ancestor of the local tip the base is the remote tip (lines 558-561), so the range `<remote sha>..<local sha>` includes every main commit the merge brought in. `base-triggers` over that range (lines 2057-2065) then prints "cast counts are compared with the pushed base (...)" for a main commit that changed `Cargo.toml`.
- Reported, not re-run here: the 2026-11-13 push of kwavers#963's branch printed "cast counts are compared with the pushed base (Cargo.toml changed)" and was BLOCKED at the 600 s deadline.
- Oracle: a hook test builds a branch pushed at tip R, merges a main whose new commit changes `Cargo.toml`, and pushes: the gate range lists none of main's commits and prints no cast-base line. A control push whose own commit changes `Cargo.toml` still prints it.
- basis: 12708acf3ae4892d4443627f0d6d5016ddeb29d7; priority: verification; needs: none
- scope: `scripts/git-hooks/pre-push`, `scripts/tests/test_root_hook_guards.py`. Member copies follow through [ATLAS-HOOK-FLEET-BLOB-DRIFT](../backlog.md#atlas-hook-fleet-blob-drift).
- Next step: write the failing control and merge pair, then exclude commits reachable from `origin/<default>` when forming the range base.
