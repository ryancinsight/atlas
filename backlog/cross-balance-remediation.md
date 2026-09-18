<a id="cross-balance-remediation"></a>
## ATLAS-CROSS-BALANCE-EDGE-REMEDIATION-2026-09-04 - Route the four cross-balance edges through harmonia [minor] - todo

Parent: `#archtest-live-balance-domains`.

- **outcome:** the four cross-balance edges surfaced by ADR 0055 R7
  route through `harmonia`'s coupling surface — or, where the shared
  type is genuinely a single-field dependency, the shared type moves
  to a non-balance substrate crate the way `proteus` already carries
  material closures. After remediation the live stack reports
  `balance_domain_edges = 0` and the ratchet tightens to that floor.
- **surfaced by:** `#archtest-live-balance-domains`
  at `9e9dbe785` on 2026-09-04. The current counts are baseline (the
  rule's correctness outcome); any *new* violation above the floor
  fails the gate.
- **the four edges:**

  | Consumer | Provider | Member pair | Notes |
  | --- | --- | --- | --- |
  | `helios-analysis` | `asclepius` | helios × asclepius | bio-effect scoring in therapy plan evaluation |
  | `helios-planning` | `asclepius` | helios × asclepius | bio-effect scoring in dose planning |
  | `kwavers-physics` | `asclepius` | kwavers × asclepius | bio-thermal acoustic coupling |
  | `kwavers-therapy` | `asclepius` | kwavers × asclepius | bio-effect scoring in therapy protocols |

- **two remediation paths are admissible** per ADR 0055:
  1. **Route through harmonia** — the dependency becomes a
     `harmonia::Partition` consumer; the field exchange routes through
     typed field envelopes per [ADR 0050](docs/adr/0050-typed-physical-field-exchange.md).
     This is the canonical path for true coupling.
  2. **Extract the shared type** — if `asclepius` is only being used
     for one type (e.g. an effect-score quantity), the type moves to
     `aequitas` (the shared quantities layer ADR 0055 places alongside
     the balance owners) and the edge disappears. This is the path
     for *non*-coupling dependencies that were routed through
     `asclepius` for convenience.

- **decision per edge** belongs to the *consumer* repository's owner:
  helios's `helios-analysis` and `helios-planning` edits live on
  helios's tree (lane `perf/helios-ci-concurrency` per the latest
  sync, or a fresh branch); kwavers's `kwavers-physics` and
  `kwavers-therapy` edits live on kwavers's tree (lane
  `refactor/elastic-ssot-consumer` per the latest sync). The asclepius
  side is unaffected — asclepius publishes the coupling surface the
  consumer reads, and ADR 0055 R5 names `harmonia` as the route.

- **acceptance:** the live conformance scan reports `balance_domain_edges = 0`
  across all 26 members; the four edges are removed; the ratchet baseline
  reflects the new floor; kwavers's elastic SSOT work (in flight under
  `[#proteus-elastic-ssot](backlog.md#proteus-elastic-ssot)`) and
  the kwavers→ares→athena first-consumer path remain green.
- **class:** `[minor]` (architectural cleanup; not blocking publish).
  **risk:** low — the existing `kwavers-analysis -> asclepius` and
  `kwavers-simulation -> asclepius` edges (dev-dependency-only) are
  outside R7's scope and unaffected. **depends on:** nothing.

