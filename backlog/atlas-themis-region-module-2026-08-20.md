<a id="atlas-themis-region-module-2026-08-20"></a>
## ATLAS-THEMIS-REGION-MODULE-2026-08-20 — Split branded region implementation [arch][patch] — in-progress

Themis `src/branded/region/mod.rs` is a 481-line implementation file. It
contains the `SyncRegionPlacement` capability, its NUMA-tag proof helper, scope
construction, and tests, so the module manifest is not a manifest and the
conformance scan records one `manifest_implementation` violation.

**Scope:** Themis `src/branded/region/` only, plus the provider ADR/index and
owner-local PM records. Move the existing implementation into a focused leaf
module, retain `region/mod.rs` as the module manifest, and preserve every
public path and safety argument. Do not touch the peer-owned primary checkout
or unrelated platform/book changes.

**Acceptance:** public exports and behavior remain unchanged; the region
module manifest contains only module declarations and curated re-exports; the
provider ADR index is synchronized; format, locked all-target check, warning-
denied Clippy, nextest, doctests, and Rustdoc pass; the conformance scan drops
Themis `manifest_implementation` by one without raising any class.

**Owner:** current Atlas session. **Claimed files:** Themis
`src/branded/region/`, provider ADR/index, and root `backlog.md`/`checklist.md`.
The clean lane must be based on fetched Themis `origin/main` after the primary
checkout's five-commit lag is reconciled by using a new lane, not by editing
the dirty primary.

**Implementation evidence (2026-08-20):** clean lane branch
`fix/themis-region-module` is based on `origin/main`
`c76a55e5eb9988b48bba69e67d6e07ce5fe55ea8` and publishes commits `7b30088`
and `32c40a7`. `region/mod.rs` is now a manifest with curated re-exports and
the implementation/tests are in `region/scope.rs`; ADR 0003 and the provider
backlog/gap audit are synchronized. Locked all-target check, format,
warning-denied Clippy, nextest (`25/25`), doctests (`5/5`), and Rustdoc pass.
The lane conformance scan reports `manifest_implementation: 1` versus `2` on
the fetched provider default, with every other Themis class unchanged.

The implementation was published as PR
[#29](https://github.com/ryancinsight/themis/pull/29) at exact head
`32c40a7b21fd9a6e81505e8741d54884ab1d2e59`, based on merged default
`c441acffc71ebeb24b77dd2d23a90856352d2f48`, and merged with the expected-head
guard at default merge commit `2c0749873c4860257ba912ff8494937021a79aa1`.
The PR's Ubuntu, Windows, MSRV, Miri, compile-fail, Clippy, Nextest, doctest,
and Rustdoc checks are terminal-successful. Post-merge default runs are
queued: MSRV `32473974344`, CI `32473974353`, and Pages
`32473973059`. The dirty primary Themis checkout and Atlas gitlink remain
unchanged until those runs and the live-page check are terminal. The merged
clean lane and its local branch were removed after the PR merge.

