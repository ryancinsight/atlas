<a id="atlas-identity-lease-starvation"></a>
## ATLAS-IDENTITY-LEASE-STARVATION - Gated pushes starve on the 900 s identity-lease wait [verification] - todo
- priority: verification
- outcome: a gated member push under fleet load waits at most one peer gate step for a source-identity lease. It is never refused for a lease another push holds through a whole gate.
- evidence (2026-09-30, hook checker at the merge of #388, after #361 and #385): eight serial pushes were refused after the 900 s wait. These were helios, ritk, hephaestus, kwavers, metis and CFDrs, plus four atlas pushes of PR #408. Holders were peer gates for metis-perf, moirai, kwavers and mnemosyne. Two pre-push gates of one mnemosyne lane ran at once from separate exports (`pg-2ab412cdc4`, `pg.7Z3wYu`), and each queued behind the other.
- acceptance: (1) a test with two runs on one closure records the second run's wait as bounded by the first run's hold of that step; (2) the pre-push hook refuses a second concurrent push of the same ref and repository; (3) a timed fleet push records per-step lease hold.
- needs: none
- scope: `scripts/atlas_build_identity.py`, `scripts/atlas_build_lease.py`, `scripts/git-hooks/pre-push`, `scripts/tests/`
- next: measure per-step exclusive hold under the #385 downgrade. A lease is held from clippy through rustdoc of every changed package, so a multi-package gate outlasts 900 s.
