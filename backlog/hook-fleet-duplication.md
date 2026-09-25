<a id="hook-fleet-duplication"></a>
## ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06 - Stack-owned git hooks [patch] - in-progress
- **outcome:** `scripts/git-hooks/` is the single source deployed by `atlas-lock-form.py`; member copies remain executable but are never authored independently.
- **rollout:** 19 sync PRs merged, seven are enqueued, and `consus`/`ritk` already match canonical hook blob `0fc8934833d79075ed4b123819a98c5fc0d6e1b8`.
- **open:** `kwavers` #815 remains dirty; a fresh-default retry reached the canonical 90-second command deadline while a peer release build held the shared cache, and the timed-out hook process tree required cleanup.
- **risk:** hook `Cargo.lock` snapshot/restore remains unsynchronized, so concurrent hooks can restore over each other. The selector and publisher fixes do not serialize it. Members whose stale hook refuses or times out the sync push are published through the git data API with the same bytes.
- **acceptance:** close when canonical hooks are current fleet-wide, `sync-hooks --check` exits zero, and named publisher reruns are idempotent and bounded.
