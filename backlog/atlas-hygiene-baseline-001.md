<a id="atlas-hygiene-baseline-001"></a>
## ATLAS-HYGIENE-BASELINE-001 — Eleven-class conformance baseline and namespace hygiene [patch] — in-progress
- owner: fable-prompt-session. scope: `scripts/atlas-conformance.py`, `scripts/conformance-baseline.json`; per-repo burn-down stays unclaimed.
- outcome: the committed scanner covers all debt classes with a non-increasing per-repo baseline; fleet check reports zero violations.
- state (2026-09-08): 6 violations remain (down from 26): `ritk` and part of `kwavers/oversized_files` are proven-stale baseline rows; `kwavers`'s remainder is a live peer's build/lane; `apollo/{manifest_implementation, existence_only_assertions}` is skipped — apollo is at its two-tree bound.
- next: (1) `check` compares the working-copy baseline to itself post-`generate` — read the committed blob or refuse a dirty baseline; (2) `generate` prints no diff on a raised row — add previous-value output; (3) `reexport_shims` double-counts `cfg`-gated alias arms — count each group once.
