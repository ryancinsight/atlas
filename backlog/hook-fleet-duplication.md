<a id="hook-fleet-duplication"></a>
## ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06 - Stack-owned git hooks [patch] - todo
- **outcome:** `scripts/git-hooks/` is the single source deployed by `atlas-lock-form.py`; member copies remain executable but are never authored independently.
- **rollout:** 19 sync PRs merged, seven are enqueued, and `consus`/`ritk` already match canonical hook blob `0fc8934833d79075ed4b123819a98c5fc0d6e1b8`.
- **open:** `kwavers` #815 remains dirty; a fresh-default retry reached the canonical 90-second command deadline while a peer release build held the shared cache, and the timed-out hook process tree required cleanup.
- **risk:** hook `Cargo.lock` snapshot/restore remains unsynchronized, so concurrent hooks can restore over each other. The selector and publisher fixes do not serialize it. Members whose stale hook refuses or times out the sync push are published through the git data API with the same bytes.
- **risk:** all 28 members now use `core.hooksPath=D:/atlas/scripts/git-hooks` (#391, applied 2026-09-29), so hook freshness follows the umbrella checkout. On 2026-09-29 that tree's `main` had been moved by message-less ref updates while its index stayed at `1106b55a6` (rescued as #392). Candidate cure: `install-hooks` writes shims that exec `origin/main:scripts/git-hooks/<hook>`, as `publish-hooks` already does.
- **acceptance:** close when canonical hooks are current fleet-wide, `sync-hooks --check` exits zero, and named publisher reruns are idempotent and bounded.
