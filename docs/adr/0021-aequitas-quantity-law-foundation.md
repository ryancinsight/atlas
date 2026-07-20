# ADR 0021: Promote Aequitas to the quantity-law foundation

- **Status:** Accepted
- **Date:** 2026-07-19
- **Class:** [arch]

## Context

The Atlas roadmap identified repeated physical-unit ownership in CFDrs,
Helios, and Kwavers. A source comparison against `uom` 0.38.0 narrowed the
actual provider gap: `uom` supplies mature dimensional analysis and broad unit
coverage, but its closed storage-type generation cannot admit Atlas's sealed
Eunomia wrapper types from a downstream crate.

The promotion gate now has a concrete vertical implementation:

- the public `ryancinsight/aequitas` repository contains a `no_std` quantity
  core, type-level SI dimension algebra, and zero-sized linear unit markers;
- `Quantity<T, D>` is transparent over `T: eunomia::FloatElement`;
- generic tests instantiate every Eunomia floating-point implementation;
- `uom` remains a development-only differential oracle;
- Hephaestus accepts typed Aequitas length at the two-dimensional stencil
  boundary and performs the only quantity-to-POD conversion;
- CFDrs carries typed spacing from its public Laplacian facade to Hephaestus;
- Helios retains validated domain newtypes while delegating energy and length
  representation to Aequitas; and
- Kwavers replaces its bubble-energy `uom` dependency and removes the
  superseded call sites in PR #295.

The detailed package decision and comparison evidence live in
[Aequitas ADR 0001](https://github.com/ryancinsight/aequitas/blob/49ee8004e008a480ac871c3782d00d921ba41c01/docs/adr/0001-aequitas-quantity-law.md).
The public consumer migration is specified by
[Kwavers ADR 040](https://github.com/ryancinsight/kwavers/blob/49c116ffb7466f9163b7762f03bc74725d8026c3/docs/ADR/040-aequitas-quantity-provider.md).

## Decision

Promote Aequitas from a roadmap candidate to the Atlas foundation layer and
pin merge commit `eeff191f9b7caecf4f161b2fe832bf170f43c6ac` in the
meta-repository. Advance the integrated Hephaestus, CFDrs, Helios, and Kwavers
pointers with the same provider-graph unit.

Provider ownership is:

- Eunomia owns scalar representations, conversion, and numeric traits.
- Aequitas owns physical dimensions, transparent quantities, and linear-unit
  conversion over Eunomia scalars.
- Domain packages own validity constraints and physical models.

Aequitas remains one crate until an independent artifact or infrastructure
boundary triggers workspace promotion. Its vertical module tree separates
dimension algebra, quantity representation and operations, SI vocabulary, and
unit conversion without parallel implementations.

## Rejected alternatives

### Keep Aequitas on the roadmap

Rejected because a public implementation and real consumer migration now
satisfy the promotion gate. Leaving it listed as provisional would make the
stack map false.

### Assign quantity law to Eunomia

Rejected because numeric representation and physical dimensional semantics are
separate bounded contexts. Coupling them would make every scalar consumer
inherit a physical-units API.

### Retain `uom` beside Aequitas in migrated consumers

Rejected because dual providers preserve conversion and scalar-law
duplication. `uom` is retained only as Aequitas test-oracle evidence.

## Consequences

- The recorded stack contains 17 public packages.
- Future shared quantity or unit gaps are implemented in Aequitas.
- Aequitas depends on Eunomia; Eunomia does not depend on Aequitas.
- Hephaestus owns device-representation conversion; consumers retain domain
  validation and pass typed quantities to its provider boundary.
- `proteus` and other future domain providers may consume Aequitas quantities
  without defining another scalar or unit vocabulary.

## Verification

- Aequitas CI at bootstrap commit `5057bcc` passed source, tests, doctests,
  documentation, and supply-chain gates.
- Aequitas PRs #1 and #2 passed `verify` and `supply-chain`; PR #2 removed the
  duplicate Eunomia source identity and merged as `eeff191`.
- Hephaestus PR #53 passes typed spacing through a live 4/4 GPU boundary suite
  and merged as `1ab1d6b`.
- CFDrs PR #298 passes warning-denied GPU Clippy and 13/13 focused Laplacian
  tests and merged as `7c37f7f`; Atlas pins that remote default instead of the
  unpublished `a34a01d` compatibility-alias follow-up.
- Helios PR #9 passes warning-denied Clippy, 17/17 native tests, doctests,
  rustdoc, and a Git-baseline SemVer check and merged as `71f565e`.
- Release codegen for typed velocity arithmetic contains the same single
  scalar division body as the raw implementation.
- Kwavers PR #295 passed all 24 hosted checks, including stable/beta/nightly,
  feature combinations, CUDA compilation, 1,554 native tests, doctests,
  Miri, security, coverage, and Criterion benchmarks, then merged as
  `49c116ffb`.
- `.gitmodules`, the current-stack table, provider ownership, naming table,
  layer diagram, roadmap, and ADR index agree on Aequitas's current role.
