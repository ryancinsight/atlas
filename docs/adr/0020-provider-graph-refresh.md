# ADR 0020: Refresh the Atlas provider graph

- **Status:** Accepted
- **Date:** 2026-07-17
- **Class:** [arch]

## Context

The Kwavers CI checkout action resolves sibling providers from the fixed
`codex/kwavers-atlas-integration` Atlas branch. That branch had pinned an
obsolete RITK batch commit (`b1850302`) and older Apollo, Hephaestus, Kwavers,
and Leto heads. The stale RITK source failed before Kwavers tests compiled.

## Decision

The initial ATLAS-INTEGRATION-006 graph advanced the Atlas provider gitlinks
to merged or explicitly published heads:

| Provider | Commit |
|---|---|
| Apollo | `157467e` |
| Hephaestus | `cf4df20` |
| Kwavers | `2fb8661` |
| Leto | `37968f7` |
| RITK | `a5e375f` |

Apollo remains a consumer of `hephaestus-wgpu`; no Apollo crate owns a direct
`wgpu` dependency. RITK `a5e375f` is the merged PR #39 head and removes the
non-compiling batch source from the reproducible graph.

The follow-up RITK default-branch head `ffda3ec` corrects the composite
checkout action to select Apollo `157467e`, matching `apollo-fft` 0.24. That
source correction is pinned separately by ATLAS-INTEGRATION-007 after its
cross-platform hosted matrix passes.

## Follow-up graph status (2026-07-17)

Apollo PR #46, PM closure PR #47, and canonical-export documentation PR #48
are now merged at `0b5d11c`. Their deep verification-tree change
does not alter the provider boundary: Apollo consumes Hephaestus/Leto and
still owns no direct raw WGPU implementation. The current parent-side
follow-up is therefore:

| Provider | Current or pending commit |
|---|---|
| Apollo | `a31b8f8` (PR #53 merged; Hephaestus lock convergence) |
| Coeus | `bb97cc6` (PR #212 merged; NN provider benchmark closure) |
| CFDrs | `a833b7f` (PR #297 merged; sparse-direct contract retained) |
| Eunomia | `49dc115` (PR #39 merged; canonical sub-byte conversion) |
| Hephaestus | `ed7d76e` (PR #50 merged; Eunomia 0.4.0 lock) |
| Helios | `79b09e9` (PR #7 merged; provider lock convergence) |
| Kwavers | `9eabc4e2` (parent current) |
| Leto | `f0b4d8e` (PR #44 merged; Eunomia 0.4.0 lock) |
| RITK | `a41e03b` (PR #41 merged; Apollo 0.25 alignment) |

Hephaestus PR #44 adds the provider-owned order-preserving tiled scan slice
for WGPU and CUDA. Its theorem/spec is ADR 0009 in the provider repository.
PR #45 then memoizes CUDA driver initialization and serializes only the
process-global context-creation boundary on Windows; the provider's full
109/109 CUDA nextest suite now includes the concurrent-acquisition contract.
The parent pin advances only after each provider merge and its
consumer-independent gates complete.

Apollo PR #49 then removed the duplicate execution-policy wrapper at
`e2f905a`; PR #50 removes the internal Winograd compatibility re-export and
rewrites every caller to `components::winograd::ShortWinogradScalar`, merged at
`c874281`. The canonical-module theorem is structural: the Apollo caller graph
contains one trait definition path, so no forwarding alias can diverge from
the codelet contract. Local 402/402 Nextest and the hosted Python, Rust, and
CodeRabbit checks are green; the external analyzer error is non-required.

Hephaestus PR #46 records the scan-limit theorem at `93bc38e`: with `W` lanes,
the provider stores `W` partials and each lane folds at most `ceil(L/W)`
values, so `shared_bytes = W * size_of(T)` does not grow with line length.
The existing `L=513`, `W=256` WGPU/CUDA contracts provide the `L > W`
witness; KS-5b reopens only after a measured device budget failure. PR #47
then removes obsolete CPU reference dependencies and makes Leto/Leto Ops the
sole host-side differential vocabulary; its merged provider head is `cec0e33`.

Apollo PR #51 then refreshed its consumer lockfile to the Hephaestus head
(`93bc38e`) and the current Eunomia, Leto, and Moirai default commits. After
Hephaestus PR #47 moved the provider to `cec0e33`, Apollo PR #53 refreshed all
three Hephaestus lock entries to that merged head. The lockfile theorem is
direct: committed Cargo source revisions are the only provider selectors, so
the consumer cannot silently resolve the former heads or a local compatibility
path.

Apollo PR #52 aligns both Leto lock entries with the Atlas merge object
`3ac0d203`, closing the one-parent drift left by PR #51. The provider tree is
PM-only between `6a0e297` and `3ac0d203`, so the preceding package evidence
remains valid; hosted Rust/Python checks provide the fresh lock-only compile.

RITK PR #41 then aligns its lockfile and composite provider checkout with
Apollo 0.25 at `a41e03b`. All 22 repository and review checks pass across the
cross-platform Rust, Python 3.9–3.13, wheel, lint, dependency-alignment, and
migration-audit lanes.

PR #294 merged at `9eabc4e2` after Architecture Validation `29614208770`,
CI/CD `29614208862`, and Legacy Migration Audit `29614208769` passed. Its
source gate retains tarpaulin `cobertura.xml` generation, while the external
tokenless Codecov upload is non-blocking after HTTP 429 rate limiting. The
MVDR timing contract now lives in Criterion, leaving correctness tests
value-semantic and instrumentation-independent. The parent advances to the
merged default-branch commit in this increment.

The 2026-07-17 default refresh also advances CFDrs, Eunomia, Helios, Leto, and
RITK only to fetched remote-default commits. Active Apollo, Kwavers, and RITK
feature work remains outside `G(P)`: a dirty working tree cannot enter the
graph unless its commit is first reviewed and merged to that repository's
default branch.

The 2026-07-18 Eunomia sub-byte refresh advances Eunomia to PR #39 merge
`49dc115`, Leto to PR #44 merge `f0b4d8e`, and Hephaestus to PR #50 merge
`ed7d76e`. Leto and Hephaestus both commit Eunomia 0.4.0 at `49dc115`; the
parent therefore records one provider identity from foundation through both
consumers without a compatibility path.

Coeus PR #212 then removes the Burn comparison dimension without removing the
NN provider-performance instrument. Its merged default `bb97cc6` retains 211
operation groups and 424 Sequential/Moirai rows while its lock selects Eunomia
0.4.0, Leto 0.38.2, and Hephaestus 0.17.0. The parent advances only after that
consumer graph and hosted review are green.

Helios PR #7 then replaces an invalid partial Apollo lock edit with a complete
Cargo resolution at `79b09e9`. Its consumer graph selects Apollo 0.25.0,
Eunomia 0.4.0, Leto 0.38.2, and Hephaestus 0.17.0 and removes the
`num-complex` package without a consumer compatibility path.

## Theorem (provider-graph closure)

Let `G` be the directed graph materialized by the Atlas gitlinks, and let `P`
be the provider set above. If every first-party edge resolves to its recorded
commit in `P`, and each commit is reachable from its provider remote branch,
then the checkout action materializes one reproducible graph `G(P)`. A
consumer cannot silently select an older provider revision because the action
fetches the exact gitlink object.

This is a structural Git proof obligation; compile and test results remain the
behavioral obligation of each consumer pull request.

## Rejected alternatives

- Keep the stale RITK batch pin: rejected because it fails before consumer
  tests compile.
- Add consumer-local compatibility wrappers: rejected by provider-first
  ownership and the no-shim constraint.
- Float provider defaults in CI: rejected because it removes graph
  reproducibility.
