<a id="atlas-harmonia-field-exchange-050-2026-08-21"></a>
## ATLAS-HARMONIA-FIELD-EXCHANGE-050-2026-08-21 — Add typed physical-field exchange [major] [arch] — in-progress

The current Harmonia boundary exchanges scalar slices with only runtime
dimension and time checks. That permits CFDrs, Kwavers, and Helios adapters to
connect fields with incompatible physical quantities or grid frames.

**Scope:** a clean Harmonia lane based on `origin/main`; add a no-unsafe,
zero-copy field envelope whose values are `aequitas::Quantity<T, D>`, validated
grid shape/spacing/origin/orientation metadata, and transfer validation tests.
The first slice owns the contract only; consumer adapters and numerical source
terms follow as dependency-ordered items. **Non-goals:** changing solver
algorithms, inventing unit conversions, or editing peer-dirty provider trees.

**Acceptance:** the public constructor rejects zero dimensions, non-finite or
non-positive spacing, non-finite origins/directions, non-orthonormal direction
cosines, and value-count mismatches; a valid envelope borrows the caller's
quantity slice without allocation; compile-time quantity dimensions prevent an
`Intensity`/`VolumetricPowerDensity` interchange; property and boundary tests
cover the validation partitions and orientation identity/round-trip laws.

**ADR claim:** `docs/adr/0050-typed-physical-field-exchange.md` is reserved for
this decision. The ADR must record Harmonia as the orchestration owner,
Aequitas as quantity SSOT, and the later CFDrs/Kwavers/Helios adapter path.

**Owner:** current Atlas session. **Claimed files:** this root item and the
Harmonia clean lane only. The Apollo hosted-gate monitor remains separate.

**Current increment:** Harmonia commit `5b1bc28` (on top of
`944eafebb5045a24b8353964d1a0700a2cb62098`) implemented the contract and
merged through [PR #9](https://github.com/ryancinsight/harmonia/pull/9) with
the expected-head guard at default commit
`542b80b65628d8c4a16fdfd4113a2ff029116a96`. The follow-up adds negative and
non-finite spacing cases, a valid rotated-frame round-trip assertion, and
exact shape/origin/direction compatibility failures. The clean lane passed
`cargo clippy --all-targets --all-features --locked -- -D warnings`,
`cargo nextest run --locked` (31 passed, 0 skipped),
`cargo test --doc --locked`, `cargo doc --no-deps --locked`, and
`cargo check --release --locked`. The root ADR and generated index are in
`c39f12a`; the root commit is pushed. Post-merge CI `32474562236` and Pages
`32474560873` are queued. No consumer adapter or Atlas pointer advance is
authorized until those default runs and the live-page check are terminal.
The merged clean provider lane and its local branch were removed after the PR
merge; the dirty primary checkout remains untouched.
An independent exact-head review found no implementation or ADR blocker. It
also records a verification limit: the provider CI omits `--locked` and does
not run MSRV, release, or SemVer checks; those limits are not replaced by the
local locked gates or by the queued default runs.

