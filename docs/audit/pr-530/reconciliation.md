# Atlas PR 530 fleet reconciliation

Date: 2026-10-13 (America/New_York). The cited failure runs report October 14 in UTC.
Status: reviewable corrections; fleet coherence remains a merge gate.

## Contract and evidence

For every first-party dependency edge, the selected provider version must satisfy
its consumer requirement. Every canonical lock must resolve outside the Atlas
path overlay, retain first-party Git identities and match the selected provider
versions. Every Atlas gitlink must be published on its member default, stay within
the unchanged one-commit threshold or carry an existing justified waiver, and
pass the unchanged conformance baseline. An unmerged branch cannot satisfy the
published-default condition. No check, baseline, timeout or drift threshold changes.

The [overlay run](https://github.com/ryancinsight/atlas/actions/runs/38487605633)
reports 66 direct declaration lags and 17 lock-drift repositories. The
[version guard](https://github.com/ryancinsight/atlas/actions/runs/38487605641)
expands workspace inheritance; an immutable fetched-default scan reports 198
findings. The [pin scan](https://github.com/ryancinsight/atlas/actions/runs/38487605644)
reports 16 failing members and two waivers. These counts measure different views.
The fetched identities, full dependency graph, 66 declaration locations, compiler
outcomes and proposed revisions are in [revisions.json](revisions.json).

## Dependency order

The graph comes from every registered member's fetched default manifests,
including inherited, build, development and target-specific first-party edges.
A layer may advance only after its selected providers resolve and pass validation:

1. `eunomia`, `iris`, `melinoe`.
2. `aequitas`, `themis`.
3. `mnemosyne`.
4. `hermes`, `horae`, `moirai`, `proteus`.
5. `hyperion`, `leto`.
6. `gaia`, `hephaestus`, `prometheus`.
7. `apollo`, `athena`.
8. `coeus`, `consus`, `harmonia`.
9. `ares`, `asclepius`, `metis`, `tyche`.
10. `ritk`.
11. `CFDrs`, `helios`, `kwavers`.

Within each repository: update incompatible requirements against approved
provider versions; apply the required patch version; resolve each owned lock
outside the overlay; validate metadata, all supported features, computed values
and diagnostics; obtain hosted review; then advance its Atlas gitlink. A provider
lock correction does not make its branch a default dependency before merge.
Re-resolve downstream locks after the final provider merge revision is known.

## Completed corrections against approved defaults

| Repository | Review | Correction | Native verification |
| --- | --- | --- | --- |
| Horae | [PR 98](https://github.com/ryancinsight/horae/pull/98) | Aequitas 0.2.2 and Eunomia 0.9.1 lock identities | 42 tests, 2 doctests |
| Hyperion | [PR 82](https://github.com/ryancinsight/hyperion/pull/82) | Aequitas 0.2.2 and Eunomia 0.9.1 lock identities | 24 tests, 1 doctest |
| Consus | [PR 172](https://github.com/ryancinsight/consus/pull/172) | Moirai 0.9 requirements and lock; patch 0.2.1 | 2,697 tests, 14 doctests, one existing ignored example |
| Tyche | [PR 109](https://github.com/ryancinsight/tyche/pull/109) | Consus 0.2/Moirai 0.9 requirements and lock; patch 0.3.1 | 51 tests, 18 doctests |

All 2,814 native tests pass with zero skips. All four corrections pass locked
standalone metadata, all-feature compilation, warning-denying Clippy and the
unchanged conformance baseline. Registry package/version/source/checksum tuples
remain identical. Tyche extends its existing branch and preserves its earlier
Eunomia upgrade. Source, numerical assertions and test budgets remain unchanged.
The ignored Consus documentation example is pre-existing. Hosted checks and
review remain prerequisites; these proposal commits are excluded from Atlas pins.

## Provider boundary and unresolved consumers

Approved Moirai main already declares 0.9.0 through merged page-provider work.
Its adoption does not require [Moirai PR 618](https://github.com/ryancinsight/Moirai/pull/618)
or [Metis PR 503](https://github.com/ryancinsight/metis/pull/503). Both QUIC
branches remain unmerged. The provider's controlled gate retains three failures
among 108 process pairs for the 16-stream, 65,560-byte, 1% loss case at the
unchanged 60-second deadline. No QUIC dependency enters this reconciliation.

A new independent blocker precedes the Leto/Hephaestus chain: Eunomia's approved
default removes `CastFrom`, but Hermes default still exports/imports it in
`crates/hermes-simd-core/src/scalar.rs`. Exact standalone lock updates compile
until rustc reports E0432 on that import. Restoring an obsolete trait, widening
generic kernels or pinning an unmerged replacement is not a compatible fix.
Hermes must migrate its actual conversion contract and callers under separate
provider review, then pass value and native-backend equivalence tests.

| Consumer | Actual rejection after direct requirement edits |
| --- | --- |
| Hermes | Updated Eunomia removes the imported `CastFrom` trait. |
| Leto | Moirai 0.9 lock resolves; compilation reaches the Hermes/Eunomia E0432. |
| Hephaestus | Moirai 0.9 lock resolves; compilation reaches the same E0432. |
| Apollo | Its locked Hephaestus requires moirai-sync 0.8.2. |
| Coeus | Its locked leto-ops requires moirai-runtime 0.8.2. |
| Metis | Advancing Gaia removes its <0.9 requirement; compilation then reaches E0432. |
| RITK | Its selected Apollo requires moirai-runtime 0.8.2; its own 19 declaration lags also require adoption. |
| Ares | Advancing Harmonia removes its Athena 0.2 constraint; resolution then reaches leto-ops 0.8.2. |
| Kwavers | Its locked Apollo requires moirai-runtime 0.8.2; the explicit RITK quarantine revision stays intact. |
| Helios | Its selected RITK requires Consus 0.1 despite current Consus 0.2. |
| CFDrs | Its locked Hephaestus requires moirai-sync 0.7.0. |

No failing manifest-only candidate is published as a completed correction.
After the conversion migration, Leto precedes Hephaestus, then Apollo, Coeus,
Metis and RITK before the scientific integrators. Consus and Tyche's verified
independent corrections can be reviewed without that migration or QUIC approval.

## Atlas selection and holds

Thirteen gitlinks advance from their recorded commits to verified forward
ancestors on fetched defaults: CFDrs, Aequitas, Asclepius, Coeus, Consus, Gaia,
Harmonia, Helios, Hermes, Kwavers, Mnemosyne, Prometheus and Proteus. Every one
passes the unchanged debt baseline. Pointer and board commits stay separate.
Concurrent primary component trees and the concurrent Atlas CLI audit survive.

Eunomia remains at its recorded revision until the Hermes conversion migration
passes. Moirai remains held until consumers adopt 0.9. Apollo's current default
raises two board classes, and Athena's adds a checklist-class regression; their
recorded pins stay unchanged. These unwaived holds remain visible to the drift
check where they exceed its threshold.

The two existing Leto/Hephaestus waiver entries and held gitlinks remain. Their
previous regressions are fixed on current defaults, so their reasons now record
the measured remaining regressions: Leto manifest_implementation 19 -> 21;
Hephaestus allow_sites 8 -> 12, junk_drawer_modules 0 -> 1, invalid board status
17 -> 21, missing board anchors 15 -> 16 and checklist files 0 -> 1. Their reopen
conditions require clean conformance and a verified provider closure. No new
waiver conceals Eunomia, Moirai, Apollo or Athena.

The root development overlay is regenerated by the unchanged generator from
the immutable approved-default graph. Freshness correction does not close its
requirement or lock findings. The strict gate continues to report those failures.

## Verification disposition

The published-default graph remains at 66 declaration lags and 17 lock-drift
repositories until reviewed corrections merge. The staged proposal graph is a
separate diagnostic view, not a published-default pass. The final root check
results and exact revisions are recorded in revisions.json and the owning
[reconciliation checklist](checklist.md).

The unchanged rechecks report 66 declaration lags, 17 lock-drift repositories
and 198 version-guard findings on approved defaults. The separate four-PR
proposal view reports 60 declaration lags, 14 lock-drift repositories and 190
version findings. Consus's patch release creates downstream lock work, including
four Tyche Consus identities; this proposal view is still a failing graph.
The exact Atlas selection reports four failing drift members (Apollo, Athena,
Eunomia, Moirai), two existing waivers and zero malformed waivers. No OFF-DEFAULT
revision is selected. Forty-two overlay/pin/version-wrapper tests pass.

The next independent increment is the Hermes conversion migration. Provider
review, consumer closure and unchanged fleet checks precede Atlas promotion.
QUIC recovery performance, QUIC provider approval, Metis QUIC adoption and
physical Apple-device acceptance retain their own review boundaries.
