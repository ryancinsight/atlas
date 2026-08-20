# ADR 0049: Metadata-only book figures are conceptual, not numerical evidence

- Status: Accepted
- Date: 2026-08-20
- Class: `[arch]`
- Refs: `backlog.md#atlas-figure-provenance-2026-08-20` (the mandating item)

## Context

The root `generate_book_figures` tool receives only a chapter title, extracted
keywords, page kind, and caption. It has no measured series, analytical
reference, provenance manifest, or tolerance contract. Three templates
nevertheless rendered numerical-looking content from constants embedded in the
template: benchmark bars labelled "Reference" and "Computed", a validation
plot labelled "Analytical" and "Simulated", and a Pareto front with fixed
points. A figure produced by that interface could therefore look like a
validation result while depending on no computation or input data.

That violates the Atlas evidence rule: figures that claim a numerical result
need executable provenance and an independent oracle. The current generator is
a metadata-only book illustration tool, not a numerical experiment runner.

## Decision

Remove the benchmark, validation, and optimization templates from the
metadata-only generator and remove their routing entries. Titles containing
those concepts use the generic hub diagram, which communicates chapter
structure without asserting values or comparisons. The remaining templates
are schematic diagrams whose geometry is structural and whose labels derive
from the page metadata or fixed domain topology.

A future quantitative figure producer is a separate change. Its input contract
must carry the computed series, source/provenance identity, independent oracle,
and an error bound derived from the numerical method before it can emit a
figure labelled as analytical, simulated, benchmark, or optimized. This ADR
does not invent that schema because no current producer or consumer requires
it.

## Alternatives considered

1. **Keep the fixed series and label them illustrative.** Rejected: the
   geometry and data would still be indistinguishable from a result in a
   rendered book, and the generator would continue to encode fake values.
2. **Add a provenance string parameter while retaining constants.** Rejected:
   metadata is not provenance, and a caller cannot make a hard-coded series
   truthful by naming a source after the fact.
3. **Introduce a full numerical figure data model now.** Rejected as
   speculative: the root tool has no current data producer, reference dataset,
   oracle, or tolerance owner. The acceptance boundary is recorded for the
   next item instead.

## Verification

- Routing tests assert the three quantitative concepts resolve to the
  conceptual hub.
- SVG regression tests assert the metadata-only output contains no removed
  quantitative series labels or chart primitives for those titles.
- The existing idempotence tests continue to cover page insertion and
  regeneration behavior.

## Consequences

The generator cannot accidentally publish fabricated quantitative evidence.
Books that need measured plots must add a data-backed producer with its own
acceptance oracle; a title-only invocation will produce a conceptual diagram
until then.
