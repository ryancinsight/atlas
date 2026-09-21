<a id="atlas-helios-radon-oracle-2026-08-20"></a>
## ATLAS-HELIOS-RADON-ORACLE-2026-08-20 — Remove existence-only sinogram assertion [patch] — in-progress
- outcome: `helios-imaging/src/radon.rs`'s existence-only `Sinogram::from_readings(...).is_ok()` assertion becomes an invariant-preserving typed extraction; the negative-length case and value-semantic map/geometry assertions are retained.
- next: PR #69's Rust, Python, benchmark, and mdBook checks are queued — confirm terminal green before advancing the Helios gitlink; the dirty detached primary Helios checkout stays untouched until then.
