<a id="atlas-gate-lease-hold-001"></a>
## ATLAS-GATE-LEASE-HOLD-001 - Release dependency leases before the gate command runs [patch] - todo
- **outcome:** a pre-push identity step holds exclusive leases only while it cleans; the clippy/nextest/rustdoc command then runs under shared leases, so a peer push that shares a first-party dependency no longer waits out the whole command.
- **evidence (2026-09-28, basis `7b14277be`):** four gaia pushes refused after the 900 s lease wait; holders were kwavers/apollo gates holding `aequitas` and `gaia-mesh` leases. gaia-mesh's clean closure is 24 first-party crates. `run_build` re-acquires exclusive on the full closure for any unmatched record and keeps it through `_run_checked(command)`.
- **not this item:** per-step re-clean (#372, shared command key); per-package narrowing (#361). Registry content walk is 0.8 s of a 1.1 s snapshot but is a tested contract (`03aee53b0`); not a lever.
- **acceptance:** a test holding a shared lease on a dependency while a second run executes its command proves the second run proceeds; a timed gaia push after #372/#361 records per-step lease hold.
- **priority:** tightening
- **needs:** #372, #361
- **scope:** `scripts/atlas_build_identity.py`, `scripts/atlas_build_lease.py`, `scripts/tests/test_atlas_build_identity.py`
- **next:** after #361 lands, split `run_build` into clean (exclusive) and command (shared) phases with a re-check of the record between them.
