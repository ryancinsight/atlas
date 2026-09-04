# ADR 0055 R7 live-balance-domains extension — verification snapshot

- **Date:** 2026-09-04
- **Atlas revision:** this commit
- **Scope:** the live-balance-domains item
  ([`#archtest-live-balance-domains`](../../backlog.md#archtest-live-balance-domains))
  — extend `BALANCE_DOMAINS` to cover every balance owner named in
  ADR 0055's continuum-domain table, so R7 catches a
  cross-balance-member edge between any two of them, not only one
  involving `ares`.
- **Backlog items:** this lands the rule side of
  [`#archtest-balance-edges`](../../backlog.md#archtest-balance-edges)
  and closes
  [`#archtest-live-balance-domains`](../../backlog.md#archtest-live-balance-domains).

## Decision summary

The package-level `BALANCE_DOMAINS` carries crate names — what the
scan reads from `[package].name` and `[dependencies]` keys. The
member-level `MEMBER_BALANCE_DOMAINS` carries the *repositories* that
own a balance operator per ADR 0055's continuum-domain table:

| Member | Layer | Conserved quantity |
| --- | --- | --- |
| `CFDrs` | Balance | fluid momentum / mass |
| `kwavers` | Balance | acoustic momentum |
| `helios` | Balance | radiative energy |
| `hyperion` | Balance | optical transport |
| `asclepius` | Balance | bio-heat / bio-effect |
| `ares` | Balance | solid momentum (registered 2026-09-04) |

`prometheus` joins at its own registration phase.

The two are linked but distinct: adding a member to
`MEMBER_BALANCE_DOMAINS` is the *legal* act of declaring that
repository a balance owner; the package-level form exists because
the scan's per-crate keying is what the rule actually walks.

The exemption that makes the extension meaningful is the
**same-repository** rule: a balance repo's own crates depend on each
other for composition, not coupling. R7 forbids *cross-balance-member*
edges; intra-member edges stay allowed. CFDrs has 12 published
crates; without the exemption, naming CFDrs as a balance domain
would report every CFDrs crate-to-crate edge as an R7 violation.

## Same-repository exemption

`classify_member_edge` decides per edge, using the
`member_for_package` mapping built once per scan from every
member's workspace. The decision tree:

1. Either endpoint is unknown to the member mapping (lives outside
   the registered stack): `external`. Cross-stack dependencies are
   not in R7's scope.
2. Consumer and provider belong to the *same* member:
   `intra_member_allowed`. A balance repo's own crates are
   composition, not coupling.
3. Consumer and provider belong to *different* members, both in
   `MEMBER_BALANCE_DOMAINS`: `forbidden` — the R7 defect.
4. Mixed closure/balance: `closure_provider` or `closure_consumer`.
5. Otherwise: `allowed`.

The mapping is built from `repos/<member>/...` workspaces with two
filters:

- Only members in `MEMBER_BALANCE_DOMAINS` contribute their packages.
  Non-balance members carrying a duplicate name (the `xtask`
  scaffolding crate is the textbook case — CFDrs, kwavers, and
  helios all carry one) do not register, because R7's
  classification never asks who owns `xtask`.
- Only `publish != false` packages enter the mapping. The `xtask`
  crates are also unpublished by convention, so even the filter
  alone would resolve the collision — but the member filter
  documents the intent: the rule cares about balance-domain
  packages, not scaffolding.

## Acceptance oracles

| Oracle | Result |
| --- | --- |
| A fixture cross-repository balance edge fails | green |
| A fixture intra-repository edge between two crates of one balance repo passes | green |
| The live stack scans with zero or recorded violations | green: 4 pre-existing architectural defects surfaced; documented below |
| Fixture edge `ares -> CFDrs` fails | green |
| Fixture edge `cfd-core -> kwavers-core` fails | green |
| Fixture edge `cfd-core -> cfd-1d` (intra-CFDrs) passes | green |
| Fixture edge `kwavers-physics -> asclepius` fails | green (matches live measurement) |
| Fixture edge `asclepius -> asclepius-coeus` (intra-asclepius) passes | green |
| 113-case test suite (architecture + conformance) passes | green |
| `render_baseline` reproduces the committed file byte-for-byte | green |
| End-to-end `report --worktree` runs without crash | green |

## Live-stack measurement

```
$ python scripts/atlas-conformance.py report --worktree | tail -5
substrate_contract_violations          0  -
balance_domain_edges                   4  helios=2, kwavers=2
```

The rule catches **four pre-existing R7 violations** — direct
cross-balance-member edges that predate the rule itself and were
undetected while `BALANCE_DOMAINS` was empty. Each is recorded
below as an architectural defect, not a regression in code quality.
The baseline reflects these counts so the ratchet accepts them as
the rule's correctness outcome rather than treating them as new
debt.

| Consumer | Provider | Member pair | Status |
| --- | --- | --- | --- |
| `helios-analysis` | `asclepius` | helios × asclepius | **violation** |
| `helios-planning` | `asclepius` | helios × asclepius | **violation** |
| `kwavers-physics` | `asclepius` | kwavers × asclepius | **violation** |
| `kwavers-therapy` | `asclepius` | kwavers × asclepius | **violation** |

These are R7 violations per ADR 0055 §boundary rules: balance
owners coupling through direct `[dependencies]` rather than
through `harmonia`. The remediation path is to route the edges
through `harmonia`'s coupling surface (the per-product integrator
work that owns cross-domain data exchange), or — where the
dependency is genuinely a single field with no coupling semantic
— to extract the shared type into a non-balance substrate crate
the way `proteus` already carries material closures.

The four edges are long-standing (not introduced by recent peer
work). Recording them on the board keeps the rule's outcome
honest and gives the remediation work a measurable target.

## Files

| Path | Change | Role |
| --- | --- | --- |
| `scripts/atlas_architecture_test.py` | +60 lines | new `MEMBER_BALANCE_DOMAINS`, `classify_member_edge`, `member_balance_violations`, `build_member_for_package`; updated `Finding` doc and `is_violation` to cover the two new kinds. |
| `scripts/tests/test_atlas_architecture_test.py` | +19 cases | `MemberBoundaryTableTests`, `BuildMemberForPackageTests`, `ClassifyMemberEdgeTests`, `MemberBalanceViolationsTests`; two new `FindingViolationTests` for `intra_member_allowed` and `external`. |
| `scripts/atlas-conformance.py` | +60 lines | imports the new symbols; `member_package_names` filters `publish != false`; `scan_repo` accepts `member_for_package`; `scan_stack` builds the mapping once per scan and threads it through the parallel workers; the ratchet counts both package-level and member-level forbidden edges. |
| `scripts/conformance-baseline.json` | +5 lines, −5 lines | surgical update to `helios` and `kwavers` `balance_domain_edges` (0 → 2 each), reflecting the rule's correctness outcome. No other member is affected; no other class is affected. |

## Provenance

```
$ git log --oneline -3
<this commit> feat(conformance): Land the ADR 0055 R7 live-balance-domains extension
7311baf3e feat(atlas): Register ares as the twenty-sixth stack member
4a574a801 feat(conformance): Land the ADR 0055 R7 architecture-test guard
```

## Follow-on items

The four live violations call for a board item that records the
remediation path. Until that work ships, the ratchet accepts the
current counts as the floor; any *new* violation above the floor
will fail the gate.