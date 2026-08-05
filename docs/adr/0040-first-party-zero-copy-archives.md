# ADR 0040 — Zero-copy archival is first-party, and Consus owns it

- Status: Proposed
- Date: 2026-08-04
- Refs: atlas `backlog.md#atlas-sec-rkyv-1` (the advisory that forced the
  question); ADR 0039 (compute-substrate topology, the same first-party
  ownership argument applied to compute).

## Context

Zero-copy archival is currently third-party and, worse, **optional**. Eunomia
declares `rkyv` behind a feature (`crates/eunomia/Cargo.toml:14`), so the
stack's serialization story is a compile-time toggle rather than a capability.
For a performance-first stack that is backwards: archival is how tensors reach
disk and how typed messages cross a boundary, and a `serde`/JSON path is not an
acceptable default at these sizes.

Three facts sharpen the timing.

**The dependency is a live liability.** `cargo audit` reports
RUSTSEC-2026-0235 against `rkyv 0.7.46` — insufficient archive validation,
out-of-bounds. `cargo tree -p eunomia` from Kwavers confirms it is in the
compiled graph, reached as
`kwavers -> hermes-simd-core -> eunomia[rkyv] -> rkyv 0.7.46`. It currently
blocks every Kwavers merge, and 20 repositories declare eunomia.

**The surface is already small and already ours.** Across the stack rkyv
appears in 17 files, and the substantive part is four hand-written `Archive`
implementations for our own containers:

| Crate | Archived type | Size |
| --- | --- | --- |
| `eunomia` | `ArchivedPacked4Cow` for `Packed4Cow` | 200 LOC |
| `hermes-simd-core` | `ArchivedSimdCow`, `SimdCowResolver` | ~51 refs |
| `coeus-tensor` | checkpoint archives | 2 files |
| `moirai-transport` | typed cross-boundary messages | 4 files |

We are not using rkyv's derive ergonomics across a wide type surface. We are
using its trait vocabulary to hand-roll four archives.

**The pattern is already proven first-party.** `moirai-transport` depends on
**no** rkyv at all: `safe_channel` implements "rkyv-style archives: validate
once, then read through a borrowed view" itself. The stack has already written
this once without the dependency.

## Decision (recommended)

1. **Zero-copy archival stops being a feature.** It is a first-class capability
   of the stack, on by default wherever a type is archivable. `serde` remains
   only for genuinely interchange-shaped boundaries (config, human-facing
   manifests), never for bulk numeric payloads.

2. **Consus owns the archival layer.** Consus is the registered storage owner —
   arrow, parquet, hdf5, nwb, npy, netcdf, fits — and first-party supremacy
   says the capability belongs in the owning repository rather than being
   re-derived per consumer. Today Consus has *zero* rkyv usage, which is the
   anomaly this corrects: the storage repo does not own the storage primitive.

3. **The layer is Atlas-specific by design.** A general archival crate must
   support arbitrary user types; ours must support *our* containers over
   `T: Scalar`. That admits a tighter contract — const-known element widths,
   our alignment and placement rules, our endianness policy fixed rather than
   parameterised — and lets each archive monomorphize to the concrete layout
   instead of resolving through generic machinery.

4. **The security advisory is handled separately and first.** This ADR is a
   direction, not an incident response. Whichever short-term route closes
   RUSTSEC-2026-0235 (see the alternatives) must land on its own, because a
   new archival format is not a thing to rush behind a CVE.

## Alternatives considered

- **Stay on rkyv, upgrade to 0.8.** The advisory's own remedy. Cheapest and
  should almost certainly be the short-term move regardless of this ADR. It
  does not address the feature-gating, the ownership anomaly, or the next
  advisory.
- **Drop the `rkyv` feature where unused.** Worth checking as an immediate
  mitigation — if nothing archives a `SimdCow` today, removing the edge fixes
  20 graphs for free. It is a mitigation, not a direction.
- **Keep hand-rolled archives per repository.** The status quo, and the reason
  the same code exists four times. Rejected: it is the duplication that
  consolidation discipline exists to prevent.

## Consequences and the honest risk

The strongest argument *against* this decision is safety, and it should be
stated plainly: **a zero-copy archive reader is a parser of untrusted bytes,
and a bug in it is undefined behaviour, not a wrong answer.** RUSTSEC-2026-0235
is itself an archive-validation flaw — in a widely-used, fuzzed, reviewed
crate. Ours would start with none of that scrutiny.

That risk is acceptable only if the layer is built to the standard the stack
already requires of parsers:

- Validation is mandatory and typed, never optional: an archive from an
  untrusted source is checked before any borrowed view is handed out, with
  length and offset fields bounded against the actual buffer.
- Every `unsafe` block carries its `// SAFETY:` obligation, and the reader is
  covered by `cargo miri` plus a `cargo-fuzz` target over a malformed corpus.
  A parser panic or OOM on adversarial input is a defect, not a limit.
- Layout invariants are pinned by const assertions, so a field reorder breaks
  the build rather than the data.
- Archives carry a version discriminant from the first commit; a format
  without one cannot be evolved safely.

If those cannot be met, the correct decision is to stay on a maintained
third-party crate and take its advisories as the cost of not owning it.

## Verification plan

1. Differential: every migrated container round-trips identically to its
   current rkyv archive, asserted value-semantically over generated inputs.
2. Adversarial: fuzz the reader against truncated, overlong, misaligned and
   offset-corrupted buffers; miri over the unsafe paths.
3. Performance: criterion baselines before migration, on a quiet host, showing
   archive and read-back throughput at least matching rkyv — the whole premise
   is that an Atlas-specific layout monomorphizes better, so that claim needs
   evidence, not assertion.
4. No consumer keeps a `serde` path for bulk numeric data once migrated.

## Staging

Sequenced so nothing depends on the whole thing landing:

1. Close the advisory by the cheapest correct route (upgrade or drop the edge).
2. Land the Consus layer with one container — `Packed4Cow` is the smallest
   real archive — behind its own differential and fuzz tests.
3. Migrate `SimdCow`, then `coeus-tensor` checkpoints.
4. Fold `moirai-transport`'s hand-rolled archives onto the shared layer, which
   is the consolidation that proves the abstraction.
5. Remove the rkyv dependency and the `rkyv` feature flag together.
