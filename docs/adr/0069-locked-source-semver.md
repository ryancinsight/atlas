# ADR 0069: Treat locked-resolution API coverage as unsupported

- Status: Accepted
- Date: 2026-10-30
- Item: ATLAS-SEMVER-LOCKED-SOURCES
- Revision: 2026-11-10 — Separate completed-major admission from reviewed
  disposition of recognized unsupported historical reconstruction.

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
`--baseline-rev` and patch-level discovery. Patch exit 0 requires patch impact.
Patch exit 100 means only that patch impact is insufficient, so the same inputs
run again at minor level: minor exit 0 requires minor impact and remains
compatible, while minor exit 100 requires major impact and is breaking. Exit
101, timeout, cleanup failure, or an unknown result in either run is unverified.
The report records both native runs and separates required impact and native
compatibility from declared impact, phase, manifest release admissibility, and
the final gate verdict.

Development analysis does not require a manifest bump. A breaking development
result has two separately typed development dispositions:

1. Completed-major admission starts only from patch exit 100 followed by minor
   exit 100 on identical inputs. The native findings remain major and breaking;
   admission never relabels them compatible.
2. Recognized-unsupported historical reconstruction starts only from native exit
   101 carrying every locked-resolution diagnostic identified above. It binds the
   exact native failure, supplemental locked compiler-artifact identities and lock
   hashes, source analysis naming the unresolved API facts, value-semantic consumer
   contract evidence, and explicit coverage limits. It produces no compatibility
   or required-impact verdict and remains unsupported and non-green. An unknown
   exit 101, other execution error, timeout, cleanup failure, malformed report, or
   omitted comparison has no disposition path.

Both dispositions are reviewed pull-request compositions, not helper inputs. The
review binds the exact candidate, complete baseline set and report digests, an
Accepted ADR and migration, inventory-derived consumer preparation at the exact
provider revision, configured consumer results, and an independent `judge` status
on the exact integration head. A stale review, wrong consumer revision, omitted
baseline or consumer, or arbitrary approval boolean has no authority. This helper
currently has no committed pre-push or CI caller; until a separately reviewed
mechanism lands, the composition is manual and its limits stay explicit in the
integrating pull request.

Release ignores development dispositions. It admits a completed major-required
result only when both declared impact and the Cargo-compatible manifest boundary
are major. Minor-required changes remain compatible and pass only when declared
impact and manifest boundary cover minor. An unchanged-version major release,
version rollback, unsupported comparison, timeout, cleanup failure, or native
execution error is never green. Publication authority remains separate. This
helper establishes only local classification and version boundary; it does not
establish migration, ADR, consumer-policy, review, or release completion.

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
- Allowing development breaks or unsupported reconstruction through a local flag,
  allowlist, or approval boolean would not authenticate an exact-head review or
  prove consumer preparation.

## Consequences

Known resolution failures now provide reviewable source and compilation
evidence without a fabricated SemVer verdict. Callers must still fail until a
supported API comparison completes or a reviewed disposition addresses the
strictly recognized unsupported coverage with the exact evidence and limits above.
Completed breaking admission retains its findings and classification. Development
integration can therefore proceed only through the reviewed composite, while the
local report remains non-green. Major release policy can admit a completed
breaking finding without relabeling it compatible; it cannot consume an unsupported
reconstruction. The locked-resolution decision changes when the native tool
preserves the committed lock, or when the dedicated nightly Rustdoc path satisfies
the stated schema and identity requirements.

## Validation

A real provider repository advances from 0.1 to 0.2 while two consumer commits
retain a `^0.1` requirement and the old provider revision in `Cargo.lock`.
Locked artifacts identify the old revision for both commits; a workspace case
excludes another root's optional dependency and retains the selected root's
helper. Native 0.51.0 remains nonzero with API comparison unsupported. Real Git
fixtures also cover compatible same-version analysis, same-version breaking
development and release decisions, an admitted major release that retains its
breaking classification, a deprecation that requires minor but remains
compatible, rollback, native failure, and process-tree timeout.

Admission review must falsify these cases: completed major findings remain present
and breaking; recognized exit 101 remains unsupported and is accepted only with the
specified diagnostic, exact identities, source analysis, value-semantic consumer
contracts, and stated limits; an unknown failure or omitted comparison has no
disposition. Missing or stale exact-head review, an inventory omission, or a
consumer lock at the wrong provider revision fails the composite. An arbitrary
approval boolean changes nothing. Development disposition cannot admit the same
unchanged version for release, a rollback, or publication.
