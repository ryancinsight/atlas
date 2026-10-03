<a id="atlas-hook-deadline-enforced"></a>
## ATLAS-HOOK-DEADLINE-ENFORCED - The pre-push hook enforces no deadline of its own [verification] - todo
- priority: verification
- basis: f5d478142
- outcome: a pre-push run that passes the hook's committed ten-minute budget is ended by the hook with a verdict naming the stage it was in, and the budget is the one the identity lease wait and the gate steps are sized against.
- evidence (2026-10-02): the hook has no deadline, only the caller's. A 12-package metis gate ran three identity steps of about 12 minutes each, about 36 minutes, so the committed ten-minute hook budget (engineering_gates: process budgets) is breached by a gate that passes. A metis push observed before step batching ran from 00:17 to 01:53. The 900 s identity lease wait bounds one wait, not the gate, and a gate of that size leaves the next run about one step of it.
- acceptance: (1) a test with a stub step that outlives the budget ends the hook with a verdict naming the step and the elapsed time, and leaves no lock; (2) the budget is a committed value the gate and the lease wait both read, with a reviewed per-member entry for gates whose measured steps exceed it (metis); (3) the metis gate's steps, measured per step with the claim records (`claims.jsonl`), are within the entry.
- needs: none
- scope: `scripts/git-hooks/pre-push`, `scripts/atlas_build_identity.py`, `scripts/tests/test_atlas_pre_push_gate.py`
- next: measure the per-step hold of the 12-package metis gate from `claims.jsonl`, then derive the member entry.
