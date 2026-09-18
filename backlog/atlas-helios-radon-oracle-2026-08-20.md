<a id="atlas-helios-radon-oracle-2026-08-20"></a>
## ATLAS-HELIOS-RADON-ORACLE-2026-08-20 — Remove existence-only sinogram assertion [patch] — in-progress

`helios-imaging/src/radon.rs` asserts only `Sinogram::from_readings(...).is_ok()`
and then unwraps the same result. This is an existence-only assertion and does
not verify the constructed value; the later mapped-reading assertions are the
actual geometry/value oracle.

**Scope:** Helios `crates/helios-imaging/src/radon.rs` and provider PM records
on a clean lane based on fetched `origin/main`. Replace the vacuous assertion
with an invariant-preserving typed extraction, retain the existing negative
length case and value-semantic map/geometry assertions, and do not touch the
peer-owned Helios primary checkout or unrelated Python/workflow/book files.

**Acceptance:** the test contains no existence-only assertion for this path;
the valid construction is consumed with a precise invariant message, the
invalid length remains asserted as a typed failure, provider format/locked
all-target check/Clippy/nextest/doctest/Rustdoc pass, and the conformance scan
reduces `existence_only_assertions` by one without another class increasing.

**Owner:** current Atlas session. **Claimed files:** Helios
`crates/helios-imaging/src/radon.rs`, provider PM, and root PM. The branch is
published separately from the provider's dirty primary checkout.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/helios-radon-assertion` is based on `origin/main`
`7ff72e37889594b6592e1f8b8b169834765f7851` and publishes `fdfe61a`. The
success path now consumes the validated `Sinogram`; the error path matches
`HeliosError::InvalidDomainValue` and checks its field, rejected value, and
reason. The lane conformance scan reports `existence_only_assertions: 0`
versus `1` on the fetched provider default. Locked workspace all-target check,
format, warning-denied Clippy, nextest (`262/262`, 9 skipped), doctests, and
Rustdoc pass.

The implementation was published as PR
[#69](https://github.com/ryancinsight/helios/pull/69), initially at
`fdfe61aa61a92493e643b76033a7ba72e8fda68c` and now at stacked head
`7a97333158bcaa134054eef9b254798d64c394de`, based on merged default
`7ff72e37889594b6592e1f8b8b169834765f7851`. The current stack also carries
the typed Python metadata and one executable Compton book oracle; its Rust,
Python, benchmark, and mdBook checks are queued. The dirty detached primary
Helios checkout and Atlas gitlink remain unchanged until the current PR head's
checks are terminal.

