<a id="atlas-hook-stack-root-ssot"></a>
## ATLAS-HOOK-STACK-ROOT-SSOT — One stack-root resolver for both root hooks [patch] — todo
- Outcome: `.githooks/pre-commit` and `.githooks/pre-push` resolve the canonical stack root through one definition, so a fix to the resolver reaches both hooks.
- Evidence: both hooks carry the same `canonical_stack_root`/`scan_candidate` body (pre-commit around line 88, pre-push around line 151); ryancinsight/atlas#447 had to apply each process-count fix to both copies.
- Oracle: `git grep -c 'scan_candidate()' -- .githooks` totals 1; test_root_hook_guards.py's separate-git-dir and linked-lane tests pass through both hooks unchanged.
- basis: 2b000c51b; priority: tightening; needs: none; scope: .githooks/pre-commit, .githooks/pre-push, a sourced file under .githooks/, scripts/tests/test_root_hook_guards.py
- Next step: check how the pre-push trampoline re-execs the hook body (process substitution) and source the shared file by the path it resolves, not by `BASH_SOURCE`. Held work (basis b334401f2fcf): `refs/pull/784/head` ([commit](https://github.com/ryancinsight/atlas/commit/9c8c1b3b2b51e9bda6234b230dba33921bba240e)) adds `.githooks/stack-root.sh` (79 lines, one `canonical_stack_root` holding the single `scan_candidate`); at that head neither hook sources it, so each keeps its own `scan_candidate()` and the grep counts 3.
