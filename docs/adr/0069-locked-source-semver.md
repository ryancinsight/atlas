# ADR 0069: Compare committed APIs with their locked source dependencies

- Status: Accepted
- Date: 2026-10-14
- Item: ATLAS-SEMVER-LOCKED-SOURCES

## Context

The local-project generator in cargo-semver-checks deletes its temporary lock
and runs `cargo update`. Apollo's committed lock still supplies Moirai 0.8.2,
but the Git provider's default branch supplies 0.9.0. Its `^0.8.2` requirement
therefore fails during API extraction before any comparison takes place. An
informational job can report success even though no API verdict was produced.

## Decision

Add an opt-in `dependency-contract: locked` PR comparison. Export the exact
base and head commits outside Atlas's path overlays, document each selected
library with `cargo rustdoc --locked --all-features`, and pass the complete
private and hidden item JSON to cargo-semver-checks' supported prebuilt inputs.
Both arms use the caller's recorded toolchain. The helper checks crate identity,
version, private-item inclusion and unchanged workspace lock hashes. Its report
records commit SHAs and content hashes. Builds, invalid selections, unsupported
targets and incomplete comparisons fail the job. Nothing interprets an extraction
failure as an API verdict.

The manifest version determines the permitted release class, including major
changes on a pre-1.0 minor increment. A same-version comparison permits patch
changes only. The workflow requires a reviewed helper revision and validates the
dependency-contract input. Existing callers retain the latest-resolution policy;
registry release comparisons retain their existing policy.

The contract currently documents the native target only. A cross-target API
comparison requires a separately specified target matrix. This change neither
upgrades providers beyond their consumers' requirements nor publishes packages.

## Validation

Real temporary Git repositories reproduce a provider's 0.1 to 0.2 advance.
The ordinary local-project comparison fails resolution while the unchanged
locked consumer comparison passes. Removing a real public operation without a
version bump still fails the locked comparison. The slow Python CI installs the
same toolchain and comparison tool and executes both regressions. Apollo's
native repair also passes an actual locked patch API comparison.
