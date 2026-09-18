<a id="atlas-helios-radon-oracle-2026-08-20"></a>
## ATLAS-HELIOS-RADON-ORACLE-2026-08-20 — Remove existence-only sinogram assertion [patch] — in-progress

- outcome: `helios-imaging/src/radon.rs`'s existence-only
  `Sinogram::from_readings(...).is_ok()` assertion becomes an
  invariant-preserving typed extraction; the negative-length case and
  value-semantic map/geometry assertions are retained.
- delivered: published as [Helios PR #69](https://github.com/ryancinsight/helios/pull/69)
  (head `7a97333158bcaa134054eef9b254798d64c394de`) on merged default
  `7ff72e378895`. Local evidence: conformance scan
  `existence_only_assertions: 0` (was 1); locked check/format/Clippy/nextest
  (262/262)/doctests/Rustdoc pass.
- next: PR #69's Rust, Python, benchmark, and mdBook checks are queued —
  confirm terminal green before advancing the Helios gitlink; the dirty
  detached primary Helios checkout stays untouched until then.
