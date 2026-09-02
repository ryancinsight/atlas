# Conformance green-ratchet snapshot — 2026-09-02

- **Revision:** atlas `dc0135e10d77` — every member scanned at the gitlink this revision records
- **Gate verdict:** 0 regressions, 0 tightenings (`python scripts/atlas-conformance.py check` and `check --json` agree)
- **Members:** 25 of the stack's registered providers
- **Captured:** 2026-09-02 22:47 UTC

This is the first fully green ratchet snapshot for ATLAS-RATCHET-REGRESSIONS-2026-09-02:
every regression raised that day is burned down with evidence or re-attributed to its
owner's board, and the baseline records only honest, measured floors (one phantom floor,
mnemosyne `oversized_files: 6`, was corrected to its measured value before tightening).

## Stack-wide totals (top classes)

| class | total | worst members |
| --- | --- | --- |
| unwrap_production | 779 | kwavers=261, apollo=132, moirai=128 |
| manifest_implementation | 664 | kwavers=286, ritk=105, CFDrs=82 |
| oversized_files | 614 | CFDrs=140, kwavers=107, consus=81 |
| existence_only_assertions | 601 | kwavers=171, ritk=156, CFDrs=123 |
| allow_sites | 510 | kwavers=322, CFDrs=91, moirai=32 |
| type_suffixed_fns | 390 | eunomia=75, ritk=72, apollo=49 |
| sleep_synced_tests | 113 | moirai=98, kwavers=12, CFDrs=2 |
| missing_deny_docs | 107 | ritk=33, apollo=21, kwavers=20 |

## Provenance

```
python scripts/atlas-conformance.py check --json   # at dc0135e10d77
```

The raw scan output is the sibling `.json` file; this summary is derived from it.
Two transient `target_forks` flags (coeus, hephaestus — live peer build caches)
were cleared before capture; the detector counts only registered members' recorded
gitlinks, so such caches never enter the recorded history.

🤖 Generated with Freebuff
