<a id="atlas-hook-stack-root-ssot"></a>
## ATLAS-HOOK-STACK-ROOT-SSOT — One stack-root resolver for both root hooks [patch] — todo
- Outcome: `.githooks/pre-commit` and `.githooks/pre-push` resolve the canonical stack root through one definition, so a fix to the resolver reaches both hooks.
- Evidence: both hooks carry the same `canonical_stack_root`/`scan_candidate` body (pre-commit around line 88, pre-push around line 151); ryancinsight/atlas#447 had to apply each process-count fix to both copies.
- Oracle: `git grep -c 'scan_candidate()' -- .githooks` totals 1; test_root_hook_guards.py's separate-git-dir and linked-lane tests pass through both hooks unchanged.
- priority: tightening
- needs: ryancinsight/atlas#447 merged
- scope: .githooks/pre-commit, .githooks/pre-push, a sourced file under .githooks/, scripts/tests/test_root_hook_guards.py
- Next step: check how the pre-push trampoline re-execs the hook body (process substitution) and source the shared file by the path it resolves, not by `BASH_SOURCE`.
