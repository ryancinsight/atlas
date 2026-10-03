<a id="atlas-root-hook-tip-controlled"></a>
## ATLAS-ROOT-HOOK-TIP-CONTROLLED — A pushed tip can replace the root hook that gates it [correctness] — todo
- priority: correctness
- outcome: the hook git runs for a push from the atlas root comes from a ref the pushed tip cannot alter.
- evidence: the atlas root sets `core.hooksPath=.githooks`, so git runs the checked-out tip's own `.githooks/pre-push`. The trampoline corrects only a copy that still contains the trampoline, so a tip can replace the hook that gates it. Reported as N6 of the judge verdict on ryancinsight/atlas#369 (https://github.com/ryancinsight/atlas/pull/369#issuecomment-5964871266, pre-existing, outside that diff). The member half (members run the umbrella working tree's hook) is addressed by draft ryancinsight/atlas#468, which points members at origin/main shims.
- oracle: a test where the tip edits `.githooks/pre-push` shows the gate that runs is main's hook and refuses the push the edited hook would allow; the root's `core.hooksPath` resolves to a shim that executes origin/main's hook by blob, as the member shims do.
- needs: none
- scope: .githooks/pre-push, .githooks/pre-commit, .githooks/stack-root.sh, scripts/atlas-lock-form.py (hook installation), scripts/tests/test_atlas_hook_trampoline.py, scripts/tests/test_root_hook_guards.py
- next: read how #468 builds the member shim and reuse that generator for the root rather than writing a second one; both root hooks source `.githooks/stack-root.sh` (ryancinsight/atlas#447), which the shim must load from the same ref as the hook.
- links: [ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06](hook-fleet-duplication.md) records the same shim cure for members.
- basis: 3ea1f062969718a419bceac2dca48d4437878513
