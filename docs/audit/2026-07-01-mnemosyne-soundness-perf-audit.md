# 2026-07-01 mnemosyne audit cycle — soundness, contention, memory, structure

Four-agent read-only fan-out over all 11 mnemosyne crates + workspace config
(dimensions: performance, memory efficiency, contention, safety, and the
structural lens: monomorphization, const generics, GATs, ZSTs, Cow/zero-copy,
DRY/SSOT/SoC/SRP/DIP, file-tree depth). High-severity findings fixed in the
same cycle on `mnemosyne` branch `fix/audit-2026-07-soundness-perf` (eleven
atomic commits, pushed). Detail lives in mnemosyne's checklist.md /
CHANGELOG.md / gap_audit.md; deferred items are backlog `AR-1..AR-12`.

Fixed highlights: orphan-adoption free-list re-keying corruption (hardened
policies) with differentially-verified regression tests; two safe-code UB
holes in the branded heap API (`BrandedCell` covariance, safe
`BrandedBlock::cast`); a `Relaxed`→`Acquire` CAS-retry data race in the shared
tagged segment stack; CUDA init `static mut` races, a permanent
device-allocation leak in registry unregister, and the process-wide VEH that
converted crashes into silent exit-0; profiler hasher/drain/flag-race
defects; decay purger lost-wakeup; huge-pool over-provision (fit cap) and dead
buckets.

## Cross-repo coordination items (owner: mnemosyne; consumers named)

- **AR-2 [major]**: replace the pub `WGPU_{ALLOCATE,DEALLOCATE}_CALLBACK`
  `AtomicPtr<c_void>` statics (safe-code soundness hole) with a typed
  `register_wgpu_callbacks` API. Consumer to migrate in the same unit:
  `hephaestus-wgpu` `src/infrastructure/device.rs:177-184` (stores the statics
  directly). One coordinated change per the co-evolution protocol.
- Consumers pinning mnemosyne by rev (e.g. apollo pins `938d0c2`) are
  unaffected until they bump; the branded-heap breaking change
  (`BrandedBlock::cast` now `unsafe`, `BrandedCell` invariant in `T`) has a
  migration note in mnemosyne's CHANGELOG.

Verified clean (do not re-chase): melinoe's brand cells are variance-sound
(payload inline in invariant `UnsafeCell`); the mnemosyne unsafe surface
outside the fixed sites; benchmark instruments except the filed statistics
weakness (AR-4). Residual: CUDA runtime paths are compile-time/unit-test tier
only — no NVIDIA driver on the audit machine.
