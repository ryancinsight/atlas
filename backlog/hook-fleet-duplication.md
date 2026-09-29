<a id="hook-fleet-duplication"></a>
## ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06 - Stack-owned git hooks [patch] - todo
- **outcome:** `scripts/git-hooks/` is the single source deployed by `atlas-lock-form.py`; member copies remain executable but are never authored independently.
- **rollout:** 19 sync PRs merged, seven are enqueued, and `consus`/`ritk` already match canonical hook blob `0fc8934833d79075ed4b123819a98c5fc0d6e1b8`.
- **open:** `kwavers` #815 remains dirty; a fresh-default retry reached the canonical 90-second command deadline while a peer release build held the shared cache, and the timed-out hook process tree required cleanup.
- **risk:** hook `Cargo.lock` snapshot/restore remains unsynchronized, so concurrent hooks can restore over each other. The selector and publisher fixes do not serialize it. Members whose stale hook refuses or times out the sync push are published through the git data API with the same bytes.
- **risk:** 25 members set `core.hooksPath=.githooks`, so the hook version follows the checked-out branch: `repos/CFDrs` on 2026-09-28 sat 80 commits behind and its pre-push failed on the `python3` Store stub until a peer switched the tree. Only one member points at `D:/atlas/scripts/git-hooks`.
- **acceptance:** close when canonical hooks are current fleet-wide, `sync-hooks --check` exits zero, and named publisher reruns are idempotent and bounded.
