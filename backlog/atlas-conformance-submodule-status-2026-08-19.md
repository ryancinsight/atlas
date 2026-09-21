<a id="atlas-conformance-submodule-status-2026-08-19"></a>
## ATLAS-CONFORMANCE-SUBMODULE-STATUS-2026-08-19 — classify provider dirt after root status [patch] — in-progress
- Hosted conformance runs `32247752034` and `32248848495` failed before the ratchet scan with the generic `root worktree is dirty` error, while the hosted checkout was clean at the root revision. The scanner's root status query included nested submodule summaries and therefore hid the provider boundary that its next checks own.
- `scripts/atlas-conformance.py` now uses `--ignore-submodules=all` for the root status query and retains the per-provider status checks. Its focused regression suite passes 18/18, including the provider-dirt classification.
- The next exact-head hosted run must pass the scanner and lock-form gates; local execution remains intentionally blocked by peer-dirty provider trees.
