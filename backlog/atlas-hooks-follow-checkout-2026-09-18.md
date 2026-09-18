<a id="atlas-hooks-follow-checkout-2026-09-18"></a>
## ATLAS-HOOKS-FOLLOW-CHECKOUT-2026-09-18 — The installed atlas hooks are whatever branch the shared tree holds [patch] — todo
- Evidence: `core.hooksPath=.githooks` resolves in the working tree, so the atlas pre-push gate that runs is the checked-out branch's copy. On 2026-09-18 the tree held a peer branch whose `.githooks/pre-push` predated the pushed-range fix; three pushes of main-based branches were refused for a moirai pin they did not touch, and were pushed through origin/main's hook via a transient `-c core.hooksPath`.
- Acceptance: the gate that runs on any push is the default branch's committed hook (for example a tracked trampoline that executes `git show origin/<default>:.githooks/pre-push`, or hooks installed outside the tree by the setup path), with a fixture test where the checked-out branch carries an older hook.
- Dependencies: none. Risk: a stale gate refuses valid pushes (bypass pressure) or passes invalid ones.
- Last-update: 2026-09-18.

