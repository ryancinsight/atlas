<a id="atlas-hook-scrub-list-ssot"></a>
## ATLAS-HOOK-SCRUB-LIST-SSOT — One source for the git variables the hooks scrub [patch] — todo
- Outcome: one source generates or feeds every hook-side list of inherited git repository variables, so a variable added to the scrub reaches all of them.
- Evidence: `REPOSITORY_ENVIRONMENT` in `scripts/atlas_git_process.py` is pinned to `git rev-parse --local-env-vars` by `test_atlas_stack.py` (ryancinsight/atlas#461). Bash cannot import it, so four hand lists remain, each a different subset: `.githooks/pre-commit` lines 78 (`unset GIT_DIR GIT_WORK_TREE`) and 157 (`unset GIT_INDEX_FILE`), `.githooks/pre-push` line 444, `scripts/git-hooks/pre-push` line 88, and the `env -u` list in the shim template (`HOOK_SHIM` in `scripts/atlas-lock-form.py`). An inherited `GIT_COMMON_DIR` was missing from the first three until the #428 review found the installer's scrub lacked it.
- Oracle: `git grep -nE "unset GIT_|env -u GIT_" -- .githooks scripts/git-hooks scripts/atlas-lock-form.py` finds no hand-written variable list, and a test compares what each hook scrubs with `git rev-parse --local-env-vars` minus the settings entries.
- priority: tightening
- needs: ryancinsight/atlas#461 merged
- scope: .githooks/pre-commit, .githooks/pre-push, scripts/git-hooks/pre-push, scripts/atlas-lock-form.py, scripts/atlas_git_process.py, scripts/tests/test_root_hook_guards.py, scripts/tests/test_atlas_lock_form.py
- Next step: for each of the four sites record which variables it must keep (pre-commit line 157 unsets only the index on purpose), then choose between a generated include with regenerate-and-diff and a hook-side call that prints the list.
