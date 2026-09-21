<a id="atlas-hosted-recheck-2026-08-19-2"></a>
## ATLAS-HOSTED-RECHECK-2026-08-19-2 — current provider state [patch] — in-progress
outcome: a verified, current record of each provider's hosted/package gate state so Atlas gitlink advances only follow terminal exact-head evidence.
- Moirai PR #143 open, mergeable; Ubuntu wheel smoke (`32328186717`) pending — gitlink holds until it completes and merges.
- RITK package blocked: `apollo-fft ^0.27.0` has no matching crates.io release (release-order blocker on Apollo 0.27 publication).
- Hyperion package blocked: registry Proteus lacks the `std` feature the git provider exposes.
- Moirai package gate blocked: `benchmarks/Cargo.toml` path deps carry no version (provider packaging defect).
- Helios draft PyPI PR #67 open at `f31f2619`, checks pass, Pages skipped.
- Apollo PR #107 open; benchmark regression localized to the four const twiddle-cache initializers (`apollo-fft/.../twiddle.rs:26-29`).
