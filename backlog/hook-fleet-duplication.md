<a id="hook-fleet-duplication"></a>
## ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06 - Twenty-two hand-maintained copies of two git hooks [patch] - in-progress

- **outcome:** `scripts/git-hooks/` is the one source for member-side
  `pre-commit`/`pre-push`, deployed by `atlas-lock-form.py sync-hooks`
  (`--check` fails CI on drift); copies stay but stop being authored.
- **delivered:** canonical source rewritten with hephaestus's
  `safe.directory` fix and the commit-time lockfile guard; `pre-push`
  reads git's stdin revision range, skipping non-manifest pushes. 23
  members synced, 3 new given hooks.
- **open:** `apollo`, `coeus`, `hephaestus` enqueued behind required
  checks; `metis`/`prometheus` unregistered and out of scope
  (`#metis-unregistered-member`, `161354f`).
- **acceptance:** `atlas-lock-form.py sync-hooks --check` exits zero
  fleet-wide and runs in CI.
