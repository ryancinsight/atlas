# ADR 0039: Compute-substrate topology across Apollo, Leto, Hephaestus, and Coeus

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]`
- Relates to: [ADR 0001](0001-gpu-accelerator-substrate.md),
  [ADR 0004](0004-hephaestus-kernel-seam.md),
  [ADR 0034](0034-athena-single-accelerator-backend.md),
  [ADR 0038](0038-compute-backend-conformance-crate.md)

## Context

Four packages form the compute substrate: `apollo` (transforms), `leto` (host
arrays and CPU linear algebra), `hephaestus` (accelerator devices and kernels),
and `coeus` (tensors and autodiff, consuming all three). They are the densest
dependency cluster in the stack, and the place where a duplicated variation
dimension is most expensive because every domain package inherits it.

This ADR records where the boundaries are, which duplication is real, and the
sequence that removes it. It exists because three of the four carry structural
repetition that is invisible from inside any one repository.

### Source audit (2026-07-28)

**Coeus re-forks the vendor dimension — but not by choice.** `coeus-rocm` and
`coeus-metal` have identical file trees and identical per-file line counts. After
normalizing the vendor token, **1 185 of 1 247 lines are the same crate written
twice**; only 62 lines genuinely differ:

| File | Lines | Differ after normalization |
| --- | --- | --- |
| `src/backend/elementwise.rs` | 462 | 2 |
| `src/backend/reduction.rs` | 109 | 0 |
| `src/backend/runtime.rs` | 153 | 4 |
| `src/backend/provider.rs` | 19 | 8 |
| `tests/elementwise.rs` | 360 | 24 |
| `tests/reduction.rs` | 124 | 16 |

`coeus-wgpu` (15 696 lines) and `coeus-cuda` (17 047 lines) carry the same shape
at larger scale.

The cause is not a design failure in Coeus. `coeus-hephaestus` already owns the
generic half correctly — its own crate documentation states it "owns storage,
transfer, layout validation, and the Coeus reduction/scan dispatch contract once.
Vendor crates implement `HephaestusProvider` and the scalar-specific
`ReductionProvider` seam; they do not copy the consumer-side operation
orchestration." That intent is right.

What forces the duplication is the shape of Hephaestus's surface. Operations are
**free functions in per-vendor crates** — `hephaestus_rocm::sum_axis_into`,
`hephaestus_metal::sum_axis_into` — so a provider impl cannot be written once
over a device parameter. Coeus clones the impl per vendor because there is
nothing to be generic over. The diff is literally a module-path substitution:

```rust
// coeus-rocm                              // coeus-metal
hephaestus_rocm::sum_axis_into::<$scalar>  hephaestus_metal::sum_axis_into::<$scalar>
```

Coeus consumes `ComputeDevice` at 43 sites but **none** of the operation seams
(`DenseVectorOps`, `SparseOperatorOps`, `AxisReductionOps`) — the first two
because they postdate the integration, the third because it landed today.

**Apollo repeats a per-transform scaffold 19 times.** Of 23 crates, 19 carry the
identical `application/execution/plan/<transform>/` shape alongside
`domain/contracts`. The transform mathematics genuinely differ; the plan,
execution, and dispatch scaffolding around them does not. Apollo also holds the
stack's largest concentration of junk-drawer modules (`mod helpers` / `mod utils`
in 7+ crates, including `apollo-fft/src/api/mod.rs` on a public path) and 35
files above the 500-line target.

**Leto and Hephaestus are a substrate pair without the pair's obligations.**
They share **14 decomposition entry points** — `cholesky_decompose`,
`lu_decompose`, `qr_decompose`, `svd_decompose`, `svd_rank_revealing`, `schur`,
`hessenberg`, `bunch_kaufman`, `udu_decompose`, `bidiagonalize`, `col_piv_qr`,
`full_piv_lu`, `eigenvalues`, `singular_values`. That is the sanctioned CPU/GPU
drop-in relationship, and it carries three requirements: one role trait, one
shared generic conformance suite, and differential tests between the two. None of
the three exists. Hephaestus's tests reach for Leto as an ad-hoc oracle by name
(`matches_leto_reference`), which is the differential test in spirit, written
per backend and per operation.

**Non-finding.** `coeus-fft` is 567 lines and depends on `apollo-fft`. Coeus
consumes Apollo's transforms and adds differentiation rather than reimplementing
them, exactly as the stack README describes. No action.

## Decision

### 1. Hephaestus owns the vendor dimension; no consumer re-forks it

A consumer binds a device-generic seam and monomorphizes. It does not carry one
crate per vendor for operations Hephaestus already provides. Per-vendor code in a
consumer is limited to **device acquisition** — `coeus-rocm`'s 19-line
`HephaestusProvider` impl selecting `RocmDevice` is correct and stays.

This is not a new rule; it is the existing one made enforceable. It was
unenforceable while operations were free functions, which is why the audit found
what it found rather than a review catching it.

### 2. Seam coverage in Hephaestus precedes collapse in Coeus

The sequence is fixed by the dependency direction, and reversing it would mean
Coeus inventing its own abstraction over Hephaestus — a second seam for the same
concern:

```text
1. Hephaestus: extend the operation seams to cover what Coeus calls
   (elementwise, reduction, scan) alongside the existing vector/sparse/axis seams
2. Hephaestus: every backend instantiates the shared conformance suite (ADR 0038)
3. Coeus: coeus-hephaestus writes ONE generic provider impl over the seams
4. Coeus: per-vendor crates shrink to device acquisition; the cloned
   elementwise/reduction/runtime/test files are deleted
```

Step 4 is the deletion ledger: roughly 1 200 lines per vendor crate across four
crates, plus the corresponding share of `coeus-wgpu` and `coeus-cuda`.

### 3. The Leto–Hephaestus pair gets one role trait and one conformance suite

The 14 shared decomposition entry points become one role trait owned in the
deepest consumer-facing crate, with Leto and each Hephaestus backend as
implementors. The shared conformance suite from ADR 0038 gains a decomposition
module, and the per-operation `matches_leto_reference` tests become instantiations
of one differential clause parameterized by the operation.

Tolerances are derived per `numerical_discipline` — decomposition error bounds
follow from the condition number and the algorithm's growth factor, not from the
constants currently written at the assertion sites.

### 4. Apollo separates the transform scaffold from the transform mathematics

The repeated `application/execution/plan/<transform>/` scaffold is one bounded
concern appearing 19 times. It consolidates into a generic plan/execution layer
parameterized by the transform, leaving each transform crate holding its kernel
and its mathematical contract — which is what actually varies.

This is the largest single consolidation available in the substrate and also the
riskiest, because 19 crates change. It is sequenced last and decomposed per
crate, with the generic layer landing first and crates adopting it one at a time.

### 5. Junk-drawer modules are not deferred cleanup

`mod helpers` and `mod utils` are removed as each crate is touched by the work
above, not batched into a separate pass. A module named for its lack of a concern
cannot be reasoned about when deciding what belongs where, which is precisely the
decision every step here requires.

## Consequences

- Coeus loses roughly 3 700 lines of cloned vendor code (rocm + metal, plus the
  cloned share of wgpu and cuda) and gains one generic provider impl.
- A new accelerator vendor costs Hephaestus one backend crate and Coeus one
  device-acquisition impl, instead of a cloned 1 200-line provider.
- The Leto–Hephaestus pair becomes verifiable as a pair rather than as two
  independently tested implementations that happen to agree today.
- Apollo's per-transform crates become small enough to read, and adding a
  transform stops meaning copying a scaffold.
- No new repository and no new package. Every change is inside an existing
  workspace; `.gitmodules` and the stack table are untouched.

## Alternatives rejected

**Collapse Coeus's vendor crates first.** Would require Coeus to define its own
device abstraction over Hephaestus's free functions — a second seam for a concern
Hephaestus owns, and one that would have to be deleted when the real seam landed.

**Leave the vendor clones and enforce by review.** The audit is what review
produced: the clones are individually plausible, and only a normalized diff makes
the 95% overlap visible. The seam removes the ability to introduce them.

**One `hephaestus-ops` mega-trait.** Would bundle elementwise, reduction, scan,
sparse, vector, and decomposition into one contract every backend must satisfy
whole, against interface segregation. The existing per-family split
(`DenseVectorOps`, `SparseOperatorOps`, `AxisReductionOps`) is the right grain and
is extended, not replaced.

**Merge Leto's CPU linear algebra into Hephaestus.** They are the CPU and
accelerator halves of one seam, not one implementation. Merging would put a
GPU dependency under every host-array consumer.

**Flatten Apollo's 23 crates into one.** Solves the scaffold repetition by
discarding the feature-gating and compile-time isolation that per-transform crates
provide. The scaffold is the duplication, not the crate split.

## Verification

1. `coeus-rocm` and `coeus-metal` contain only device acquisition; a normalized
   diff between them returns no shared operation code.
2. Adding a hypothetical fifth vendor touches one Hephaestus crate and one Coeus
   impl — demonstrated by the diff of the change that collapses the four.
3. Every Hephaestus backend instantiates the shared conformance suite, and the
   suite covers the operations Coeus binds.
4. The Leto–Hephaestus differential clause is one parameterized test, and each
   tolerance cites its derivation.
5. No `mod helpers` or `mod utils` remains in any crate touched by this work.
6. Apollo's generic plan/execution layer is depended on by every adopting crate,
   and each adopting crate's file count falls.

## References

- [ADR 0038](0038-compute-backend-conformance-crate.md) — the conformance suite
  this ADR extends to decompositions and to the operations Coeus binds.
- [ADR 0001](0001-gpu-accelerator-substrate.md) — Hephaestus's charter as the
  shared accelerator substrate, which decision 1 restates as enforceable.
- [Structural and abstraction audit](../../gap_audit.md) — the file-length,
  junk-drawer, and dispatch findings this ADR sequences.
- [Substrate composition](../../README.md#substrate-composition) — the
  stack-facing description of these four packages.
