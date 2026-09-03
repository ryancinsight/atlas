# ADR 0056: A new-construction path through the promotion gate

- Status: Accepted
- Date: 2026-09-03
- Class: `[arch]`
- Relates to: [ADR 0030](0030-hyperion-photon-optical-promotion.md),
  [ADR 0055](0055-continuum-domain-decomposition.md)

## Context

The promotion gate in the stack map has seven conditions. Read together they
describe one kind of promotion: **consolidation**. Condition 1 wants two
packages that already need the capability, condition 4 wants a deletion ledger
naming superseded types in every first-wave consumer, and condition 5 wants the
first change to migrate callers and delete superseded implementations. Hyperion
passed exactly that way — three consumers deleted parallel optical laws.

That gate is correct for extraction and it has held the package count down.
It cannot, however, be satisfied by a capability the stack does not yet have.
`ares` and `prometheus` are the standing examples: no consumer implements solid
momentum balance or a reaction network, so no deletion ledger can exist, and
condition 4 rejects the proposal on the grounds that nothing is being deleted —
which is true, and is the point.

The result is a gate that cannot say yes to new physics. Every audit re-derives
the same deferral and records it again. Four rounds of that are in the history,
and a fifth produced an external review that proposed the wrong package
entirely, because a permanently-deferred candidate accumulates description
without acquiring a decision.

The suite target makes this a live problem rather than a theoretical one.
Reaching a general multiphysics suite requires solid mechanics and species
transport. Neither arrives by consolidation.

## Decision

Add a second path through the gate. The consolidation path is unchanged and
remains the default. The new path applies only when a candidate is new
construction, and it substitutes different evidence for the deletion ledger it
cannot produce.

A candidate qualifies for the new-construction path when **all** hold:

1. **The bounded context is unowned and stated.** A source audit proves no
   current provider owns it, and [ADR 0055](0055-continuum-domain-decomposition.md)
   or a successor states which layer it occupies and what its boundary is
   against every adjacent owner. A candidate without a stated decomposition
   position is refused.
2. **A named product driver.** A specific deliverable requires the capability.
   "The suite would be more complete" is not a driver; a named study, device,
   or analysis is.
3. **A first consumer is identified before the first commit**, with the
   integration surface written down. The consumer need not exist yet, but its
   boundary must, and it is named in the ADR.
4. **Phase 0 is a complete vertical slice of real computation**, not a
   scaffold. It carries an analytical or independently-derived oracle, and it
   satisfies the same standards as any shipped code: generic over the scalar
   dimension, typed physical quantities, no mocks, no placeholder bodies.
5. **The verification oracle is analytical, not differential.** Consolidation
   promotions verify by differencing against the implementation they replace.
   New construction has nothing to difference, so it verifies against closed
   forms, conservation laws, manufactured solutions, or published benchmark
   values, each cited. This condition is stricter than the consolidation path,
   deliberately: the usual safety net is absent.
6. **Dependency direction is inward and acyclic** on the day of registration,
   asserted by the committed architecture test, not by review.
7. **The same delivery unit moves** `.gitmodules`, the stack table, the naming
   table, the roadmap entry, and cross-package verification — unchanged from
   the consolidation path's condition 7.

Conditions 4 and 5 replace the deletion ledger. They are not weaker: a
consolidation promotion may lean on the code it deletes as a reference oracle,
while new construction must prove correctness against mathematics.

### What does not change

- The gate still refuses empty repositories. Condition 4 means the first commit
  computes something real and verified.
- The gate still refuses speculative generality. Condition 2 requires a named
  driver, and condition 3 a named first consumer.
- A capability that *could* be consolidated must be, and takes the
  consolidation path. The new-construction path is not an escape from
  extracting duplicated code.
- Package count remains an outcome, never a target.

### Consequence for the deferred candidates

`ares` and `prometheus` are re-evaluated under the new path in
[ADR 0057](0057-ares-phase-0-charter.md) and
[ADR 0058](0058-prometheus-phase-0-charter.md). Their prior deferral was
correct under the consolidation path and is superseded, not overturned: the
finding was always that no deletion ledger exists, and that finding still
stands. What changes is that a missing deletion ledger is no longer
automatically disqualifying.

The elastic-property consolidation recorded as the Ares prerequisite proceeds
regardless. It is real duplication and takes the consolidation path on its own
merits, independent of whether Ares is ever promoted.

## Registry names

Both candidates collide on crates.io. `prometheus` is the widely used metrics
client; `ares` is likewise unavailable. The stack already has the convention —
`proteus-mat`, `gaia-mesh`, `moirai-runtime`, `mnemosyne-memory`,
`themis-topology`, `iris-viz` — where the registry name is qualified and the
import path is restored through `[lib] name`. New packages follow it, and
availability is verified before the repository is created, never after.

## Consequences

- The stack can add physics it does not already have, under evidence that is
  stricter in the dimension that matters for new code.
- A permanently-deferred candidate is no longer a stable state. Either a driver
  and consumer exist and it proceeds, or they do not and it is closed rather
  than re-audited each cycle.
- The risk this accepts is real: new construction has no reference
  implementation, so a defect in Phase 0 is caught by the analytical oracle or
  not at all. Condition 5 is the mitigation, and it is why the oracle
  requirement is stricter here than anywhere else in the gate.

## Non-goals

- Relaxing the consolidation path.
- Promoting anything by this ADR. It defines a path; the charters walk it.
- Admitting a candidate without a driver. `astrape` and `daedalus` remain
  recorded gaps with no consumer, and this path does not advance them.
