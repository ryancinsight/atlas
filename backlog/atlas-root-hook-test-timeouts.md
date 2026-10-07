<a id="atlas-root-hook-test-timeouts"></a>
## ATLAS-ROOT-HOOK-TEST-TIMEOUTS — Root hook tests time out under host load [patch] — todo
- Outcome: `scripts/tests/test_root_hook_guards.py` passes with the stack's usual concurrent gates running, and each hook stage it runs fits a bound derived from its work.
- Evidence (2026-10-02, full exports of origin/main 09ac02467 and of ryancinsight/atlas#396): `test_linked_lane_uses_the_canonical_member_checkout_for_gitlinks` and `test_separate_git_dir_resolves_the_canonical_worktree_root` fail on the fixture's fixed 30 s timeout around a `git commit` (pre-commit hook) or the pre-push hook. Alone, the first takes 41 s on main. A fixture commit spending over 30 s in `.githooks/pre-commit` is the slow component.
- Oracle: profile which pre-commit/pre-push stage spends the time in these fixtures and fix that stage. Timeouts are derived from the operation, or the test synchronizes on events. Ten consecutive full runs beside a concurrent cargo build pass.
- priority: verification
- needs: none
- scope: .githooks/pre-commit, .githooks/pre-push, scripts/tests/test_root_hook_guards.py
- Next step: run the slow test once with each hook stage timed (the hooks' own timing output, or `bash -x` with timestamps) and attribute the 41 s.
