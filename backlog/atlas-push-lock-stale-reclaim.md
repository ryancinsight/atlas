<a id="atlas-push-lock-stale-reclaim"></a>
## ATLAS-PUSH-LOCK-STALE-RECLAIM — Serialize stale push-lock reclamation [patch] — blocked
- Outcome: competing stale-owner reclaimers cannot remove a newly published live push lock.
- Basis: `scripts/git-hooks/pre-push` at `6c0d319ced74677527ccdee4944c0ee915d70495` reads the owner, checks `kill -0`, then removes the path without serializing reclamation. A second reclaimer can act on its earlier stale-owner observation after the first has replaced the lock.
- Scope: stale-owner recovery and ownership-safe cleanup, separate from portable atomic publication of a populated lock directory.
- Acceptance: a deterministic two-reclaimer regression forces the first reclaimer to publish a live incumbent before the second resumes; the second preserves that incumbent and cannot enter the protected gate concurrently. Run on supported native platforms.
- State: deterministic extracted-hook regression against the preserved portability-only predecessor admits two live claimants; local guarded ref-lock candidate rejects the delayed observer. Acquisition and ownership-checked EXIT release share one guard; only ESRCH permits stale removal.
- Blocked: final independent review and normal delivery gates; installed-hook/service holds remain. No installed hook or real lock is changed by these tests.
- Residual: an abandoned guard is deliberately not auto-reaped. Recovery remains unavailable until its owner investigates; do not delete a potentially live guard. Native Windows/Linux validation remains outstanding.
- Compatibility: serialization requires cooperating updated hooks. Mixed old unguarded versions remain outside this guarantee; preserve the existing deployment hold.
- Windows: the hook probes the owner's MSYS pid with the shell's own `kill -0` and `/proc`, reclaims only a definite absence or a different recorded start time (`start` beside `pid`), and retains every ambiguity, a legacy lock without `start` included. The bounded runner releases the lock of the tree it retires at its deadline.
- Separate unresolved scope: reusable-export reclamation and its weekly age sweep still use unguarded observations and path deletion. This ref-lock repair does not establish safety for that lifecycle.
- Priority: correctness; no active locks may be deleted or gates bypassed during investigation.
