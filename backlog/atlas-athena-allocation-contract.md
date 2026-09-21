<a id="atlas-athena-allocation-contract"></a>
## ATLAS-ATHENA-ALLOCATION-CONTRACT — warm solves allocate 4-6 small buffers per call on Linux [patch] — in-progress
- outcome: the three `repeated_*_solves_allocate_nothing_...` tests pass on hosted Linux with 0/0/0 allocations, mechanically distinguished from noise.
- audit (2026-08-31) exonerates the solver path end-to-end: the 4-6 allocs/17 deallocs signature is glibc per-thread arena churn, not solver traffic.
- next: `MALLOC_ARENA_MAX=1` added to the CI job — if strict zero-traffic passes under it, arena churn is confirmed and strict GMRES unblocks for re-enable; if not, reopen with a named non-arena source.
- blocked: shares the `verify` job with ryancinsight/athena#18 (unrelated).
