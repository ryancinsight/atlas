<a id="atlas-push-lock-stale-reclaim"></a>
## ATLAS-PUSH-LOCK-STALE-RECLAIM — Serialize stale push-lock reclamation [patch] — todo
- Outcome: competing stale-owner reclaimers cannot remove a newly published live push lock.
- Basis: `scripts/git-hooks/pre-push` at `6c0d319ced74677527ccdee4944c0ee915d70495` reads the owner, checks `kill -0`, then removes the path without serializing reclamation. A second reclaimer can act on its earlier stale-owner observation after the first has replaced the lock.
- Scope: stale-owner recovery and ownership-safe cleanup, separate from portable atomic publication of a populated lock directory.
- Acceptance: a deterministic two-reclaimer regression forces the first reclaimer to publish a live incumbent before the second resumes; the second preserves that incumbent and cannot enter the protected gate concurrently. Run on supported native platforms.
- State: source-level interleaving identified; not yet reproduced or fixed. The macOS `mv -T` portability repair does not close this item.
- Priority: correctness; no active locks may be deleted or gates bypassed during investigation.
