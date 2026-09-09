# ADR 0055 R7 architecture-test guard — verification snapshot

- **Date:** 2026-09-04
- **Atlas revision:** `4a574a801`
- **Scope:** the R7 boundary rule of
  [ADR 0055](../adr/0055-continuum-domain-decomposition.md)
  (no direct balance-to-balance dependency edge; coupling routes through
  `harmonia`), mechanized as a preventive guard before the balance
  packages it governs exist.
- **Backlog item:** [`#archtest-balance-edges`](../../backlog.md#archtest-balance-edges)

## Decision summary

The prior deferral of R7 was a recommendation, not a prohibition; the
substrate-contract delivery (`f15418551`) proved the preventive pattern
— a guard that fails fixture violations while the live stack still
passes earns its keep when the first violation lands, not at its own
landing. R7 lands before `ares` and `prometheus` exist for exactly
that reason.

The check lives in `scripts/atlas_architecture_test.py` alongside the
substrate scan and is exposed as a new ratchet class
(`balance_domain_edges`) inside `scripts/atlas-conformance.py`. The
boundary tables are encoded directly from ADR 0055's continuum-domain
table: `BALANCE_DOMAINS` (empty today, grows at registration),
`COUPLING_LAYERS` (`harmonia`), `CLOSURE_DOMAINS` (`proteus`).

## Acceptance oracles

| Oracle | Result |
| --- | --- |
| A fixture `ares -> CFDrs` edge fails the rule | green |
| The live stack (no balance packages exist yet) passes vacuously | green |
| The coupling-routing assertion forbids any direct cross-balance edge | green |
| `cargo fmt --check` analogue (`python -m py_compile`) on every changed Python file | green |
| `atlas-conformance` existing 64-test suite still passes | green |
| `atlas-architecture-test` new 27-test fixture suite passes | green |
| `atlas-conformance report --worktree` end-to-end run | green (0 violations across 25 members) |
| `atlas-conformance check --worktree --json` | green (0 regressions, 0 tightenings) |
| `render_baseline` reproduces the committed file byte-for-byte | green |

## Test coverage

```
$ python -m unittest scripts.tests.test_atlas_architecture_test scripts.tests.test_atlas_conformance
...........................................................................................
Ran 91 tests in 2.342s
OK
```

The 27 architecture-test cases break down:

- **5** BoundaryTableTests — the boundary tables are frozensets and
  encode ADR 0055 directly; drift here is an ADR break.
- **4** EdgeClassificationTests — every `classify_edge` call returns
  one of the four documented kinds; the function is total.
- **5** FindingViolationTests — only `forbidden` findings fail the
  test; the other three classifications are recorded but never raise.
- **3** ForbiddenEdgesTests — the live stack passes vacuously with
  `BALANCE_DOMAINS` empty; an empty provider set yields no edges.
- **3** ScanMemberManifestTests — every finding carries the
  documented type and the providers sort deterministically (so CI
  output does not shuffle).
- **7** FutureBoundarySimulationTests — with `BALANCE_DOMAINS`
  simulated to include `ares`, `prometheus`, `CFDrs`, `kwavers`:
  - direct `ares -> CFDrs`, `prometheus -> ares`, and
    `kwavers -> CFDrs` edges classify as `forbidden`;
  - `CFDrs -> harmonia` and `harmonia -> ares` edges classify as
    `allowed` (the coupling layer is not a balance domain);
  - `CFDrs -> proteus` classifies as `closure_provider`,
    `proteus -> CFDrs` as `closure_consumer`;
  - the multi-edge set produces exactly the two `forbidden` edges
    the rule must reject.

## Live-stack measurement

```
$ python scripts/atlas-conformance.py report --worktree | grep balance_domain_edges
balance_domain_edges                   0  -

$ python scripts/atlas-conformance.py check --worktree --json | tail -5
  "results": { ... },
  "regressions": [],
  "tightenings": []
}
```

Zero violations across 25 members at the recorded gitlinks. The check
runs alongside the substrate-contract check; both share the manifest
parsing machinery in `atlas-conformance.py`.

## Files

| Path | Lines | Role |
| --- | --- | --- |
| `scripts/atlas_architecture_test.py` | new, 208 lines | the rule module — boundary tables, `Edge`/`Finding` types, `classify_edge`, `forbidden_edges`, `scan_member_manifest`. |
| `scripts/tests/test_atlas_architecture_test.py` | new, 297 lines | the test suite — 27 cases covering boundary tables, classification totality, finding violations, vacuous live-stack pass, and the simulated post-promotion rule. |
| `scripts/atlas-conformance.py` | +41 lines | the ratchet integration — `member_package_name` helper, the new class `balance_domain_edges`, and the per-manifest increment that calls `classify_edge` on each `BALANCE_DOMAINS` runtime dependency. |
| `scripts/conformance-baseline.json` | +61 lines, −9 lines | the regenerated baseline — every member carries `balance_domain_edges: 0`. |

## Provenance

```
$ git log --oneline -2
4a574a801 feat(conformance): Land the ADR 0055 R7 architecture-test guard
a91ed9220 chore(atlas): Claim R7 architecture-test increment

$ git show --stat 4a574a801 | tail -7
 scripts/atlas-conformance.py                  |  41 ++++
 scripts/atlas_architecture_test.py            | 208 ++++++++++++++++++
 scripts/conformance-baseline.json             |  70 +++++-
 scripts/tests/test_atlas_architecture_test.py | 297 ++++++++++++++++++++++++++
 4 files changed, 607 insertions(+), 9 deletions(-)
```

## Future boundary additions

When `ares` lands, add its `[package] name` (registry name `ares-solid`,
import path `ares` per ADR 0057) to `BALANCE_DOMAINS` in
`scripts/atlas_architecture_test.py`. The change is one line; the rule
already discriminates a forbidden edge from a sanctioned coupling
route, as the `FutureBoundarySimulationTests` class proves in
isolation. The same pattern applies when `prometheus` lands.

R1 and R2 stay grep-shaped and live in `scripts/atlas-conformance.py`
as documented in ADR 0055's verification section; the architecture test
holds only the rules whose implementation needs the module's table.