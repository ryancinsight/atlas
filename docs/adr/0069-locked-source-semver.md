# ADR 0069: Treat locked-resolution API coverage as unsupported

- Status: Accepted
- Date: 2026-10-30
- Item: ATLAS-SEMVER-LOCKED-SOURCES
- Revision: 2026-11-10 — Separate completed-major admission from reviewed
  disposition of recognized unsupported historical reconstruction.
- Revision: 2026-11-11 — Bind separate locked registry reconstruction for development.
- Revision: 2026-11-14 (atlas PRs 708, 709) — The informational pull-request job
  compares locked rustdoc with no native run or disposition authority. Why: native
  `--baseline-rev` reruns `cargo update` in a placeholder, so a git dependency past
  the base requirement fails it. Evidence: hephaestus PR 537, job 132284946092,
  `MovedGitDependencyTests`; member rustdoc moves to `nightly-2026-08-01`.

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

Every Git comparison, except the informational pull-request job (see the revision
note), first invokes the pinned native tool with `--baseline-rev` and patch-level
discovery. Patch exit 0 requires patch impact. Patch exit 100 means only that patch
impact is insufficient, so the same inputs run again at minor level: minor exit 0
requires minor impact and remains compatible, while minor exit 100 requires major
impact and is breaking. Exit 101, timeout, cleanup failure, or an unknown result in
either run is unverified.
The report records both native runs and separates their required impact and
compatibility from declared impact, phase, release admission and gate verdict.

Development analysis does not require a manifest bump. The following reviewed
development dispositions keep native findings and separate evidence distinct:

1. Completed-major admission starts only from patch exit 100 followed by minor
   exit 100 on identical inputs. The native findings remain major and breaking;
   admission never relabels them compatible.
2. Recognized-unsupported historical reconstruction starts only from native exit
   101 carrying every locked-resolution diagnostic identified above. It binds the
   exact native failure, supplemental locked compiler-artifact identities and lock
   hashes, source analysis naming the unresolved API facts, value-semantic consumer
   contract evidence, and explicit coverage limits. It produces no compatibility
   or required-impact verdict and remains unsupported and non-green.
3. A historical registry graph may use a separate locked-artifact comparison
   after native exit 101 only when the recorded registry reconstruction and
   the authenticated release's bundled lock select different dependencies and
   matched stable compiler controls reproduce the named failure only on the
   captured reconstruction. Bind the causal compiler unit, its dependency
   identities and features, both source inputs and target, and raw diagnostics.
   If the published and generated manifests have different root roles, show
   why that difference does not account for the failure in the dependency
   unit; unresolved causes remain unsupported. The native result stays
   non-green. Only the independently reviewed development composition can
   use the separate comparison for a disposition.

Unknown failures, timeout, cleanup failure, malformed evidence, and omitted
comparisons have no disposition path. All dispositions are reviewed pull request
compositions, not helper inputs. The review binds the exact candidate, complete
baseline set and report digests, an Accepted ADR and migration, inventory-derived
consumer preparation at the exact provider revision, configured consumer results,
and an independent `judge` status on the exact integration head. A stale review,
wrong consumer revision, omitted baseline or consumer, or arbitrary approval boolean
has no authority. This helper currently has no committed pre-push or CI caller;
until a separately reviewed mechanism lands, the composition is manual and its
limits stay explicit in the integrating pull request.

Release ignores development dispositions. It admits a completed major-required
result only when both declared impact and the Cargo-compatible manifest boundary
are major. Minor-required changes remain compatible and pass only when declared
impact and manifest boundary cover minor. An unchanged-version major release,
version rollback, unsupported comparison, timeout, cleanup failure, or native
execution error is never green. Publication authority remains separate. This
helper establishes only local classification and version boundary; it does not
establish migration, ADR, consumer-policy, review, or release completion.

For the exact recognized locked-resolution diagnostic, the report records from both
committed consumer revisions `cargo check --locked` under the declared feature
policy and target, compiler-artifact IDs mapped to Cargo metadata versions and
sources (Cargo packages only, not the C or operating-system input graph), and
unchanged baseline and candidate lockfile hashes; missing identities, malformed
messages, or unavailable evidence fail. The report sets `api_comparison` to
`unsupported`. It does not replace the native result, waive exit 101, or claim ready
coverage. Unknown errors, timeouts, schema and compilation failures fail.

Atlas never injects `RUSTC_BOOTSTRAP`. Outside the informational pull-request job it
does not substitute artifacts for native discovery. For separate development
evidence use fresh `--locked` Rustdoc JSON from `nightly-2026-08-01`, schema 61.
Bind each artifact to its tools, manifest, lock, graph, features, target and
configuration. Authenticate source by exact commit/tree or by archive checksum and
bundled lock. Verify identities and acquired digests before and after comparison.
Real API removal must fail; graph or artifact substitution, missing/stale output and
schema mismatch must refuse. Compare every applicable baseline and configuration,
and exercise real consumer contracts where the checker cannot see a dependency
surface. Retain all native results. Release cannot use this evidence. The
informational job records no bindings or digests, refuses missing output, and leaves
schema refusal to the checker (`trustfall_rustdoc` 0.41.0 `src/parser.rs`).

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

Local native failures stay non-green. Development can proceed only through
a supported comparison or the independently judged composition above.
Release applies its version rule and cannot use this reconstruction.
Revisit this distinction when native discovery preserves committed locks.

## Validation

A real provider repository advances from 0.1 to 0.2 while two consumer commits
retain a `^0.1` requirement and the old provider revision in `Cargo.lock`: locked
artifacts identify the old revision for both commits, a workspace case excludes
another root's optional dependency and keeps the selected root's helper, and native
0.51.0 stays nonzero with API comparison unsupported. Real Git fixtures cover
same-version compatible and breaking analysis for development and release, an
admitted major release that stays breaking, a deprecation that requires minor but
stays compatible, rollback, native failure and timeout.

Admission review must falsify these cases: completed major findings remain present
and breaking; recognized exit 101 remains unsupported, accepted only with the
diagnostic, identities, analysis, consumer contracts, limits and (for registries)
matched stable controls that items 2 and 3 name. A missing or stale exact-head
review, an inventory omission, a consumer lock at the wrong provider revision, or an
approval boolean admits nothing, and development disposition never admits an
unchanged version for release, rollback, or publication.
