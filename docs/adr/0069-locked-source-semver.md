# ADR 0069: Treat locked-resolution API coverage as unsupported

- Status: Accepted
- Date: 2026-10-30
- Item: ATLAS-SEMVER-LOCKED-SOURCES

## Context

`cargo-semver-checks` 0.51.0 constructs a `LocalProject` baseline by running
`cargo update` unconditionally and deleting its temporary lockfile. Its
`GitRevision` baseline also maps to that project form. The relevant upstream
source is `src/data_generation/generate.rs:134-170,855-878,899-900` and
`src/rustdoc_gen.rs:288-297,630-664,683-704` at tag `v0.51.0`.

A consumer can therefore compile from a committed lock while native baseline
generation selects a newer provider revision that no longer satisfies the
consumer's requirement. Native analysis then exits 101 before producing an API
verdict. Compilation of the locked graph establishes only that the selected
source builds; it does not establish API compatibility.

The native checker's release type also combines discovery with release policy.
Selecting `major` permits breaking queries and can return success without
reporting the compatibility fact that development and consumer preparation need.
Manifest release admissibility is a separate question from whether an API breaks.

## Decision

Every Git comparison first invokes the pinned native tool with
`--baseline-rev` and patch-level discovery. Exit 0 means compatible, exit 100
means breaking, and exit 101 or any other execution failure means unverified.
The report schema records that native compatibility independently from the
declared impact, the `development` or `release` phase, manifest release
admissibility, and the final gate verdict.

Development analysis does not require a manifest bump. A breaking development
result remains denied until a separate reviewed admission mechanism binds its
findings and consumer preparation; this decision defines no approval flag or
allowlist. A release admits a breaking result only when both its declared impact
and its Cargo-compatible manifest boundary are major. The report still calls
that API breaking rather than compatible. An unchanged-version major release,
version rollback, timeout, cleanup failure, or native execution error is never
green. This helper establishes only the local SemVer classification and version
boundary; it does not establish migration, ADR, or consumer-policy completion.

For the exact recognized locked-resolution diagnostic, the report records
supplemental evidence from both committed consumer revisions:

- `cargo check --locked` under the declared feature policy and target;
- compiler-artifact IDs mapped to Cargo metadata versions and sources, limited
  to Cargo packages rather than the complete C or operating-system input graph;
- failure on missing identities, malformed messages, or unavailable evidence; and
- unchanged baseline and candidate lockfile hashes.

The report sets `api_comparison` to `unsupported`. It does not replace the
native result, waive exit 101, or claim full ready coverage. Unknown execution
errors, timeouts, schema failures, and compilation failures remain failures.

Atlas does not inject `RUSTC_BOOTSTRAP` and does not compare self-generated
prebuilt Rustdoc as a native substitute. A future prebuilt-Rustdoc path requires
a separately reviewed pinned nightly whose Rustdoc schema is supported by the
pinned checker, plus explicit graph-identity and consumer-contract validation.

## Rejected alternatives

- Supplying the baseline export as a native baseline root misstates the
  `--baseline-rev` contract and hides the unsupported path.
- Injecting bootstrap into stable Rust bypasses the toolchain contract and
  leaves Rustdoc schema and dependency-graph identity unverified.
- Treating successful locked compilation as API compatibility conflates two
  distinct evidence categories.
- Running native discovery with the declared major impact suppresses the
  breaking findings needed for development review.
- Allowing development breaks through a local flag would not authenticate a
  review or prove consumer preparation.

## Consequences

Known resolution failures now provide reviewable source and compilation
evidence without a fabricated SemVer verdict. Callers must still fail until a
supported API comparison completes or a reviewed disposition addresses the
unsupported coverage. Major release policy can admit a completed breaking
finding without relabeling it as compatible. The locked-resolution decision
changes when the native tool preserves the committed lock, or when the dedicated
nightly Rustdoc path satisfies the stated schema and identity requirements.

## Validation

A real provider repository advances from 0.1 to 0.2 while two consumer commits
retain a `^0.1` requirement and the old provider revision in `Cargo.lock`.
Locked artifacts identify the old revision for both commits; a workspace case
excludes another root's optional dependency and retains the selected root's
helper. Native 0.51.0 remains nonzero with API comparison unsupported. Real Git
fixtures also cover compatible same-version analysis, same-version breaking
development and release decisions, an admitted major release that retains its
breaking classification, rollback, native failure, and process-tree timeout.
