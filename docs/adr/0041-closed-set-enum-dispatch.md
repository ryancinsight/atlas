# ADR 0041: Closed-set per-timestep `dyn` dispatch converts to exhaustive enum dispatch

- Status: Proposed
- Date: 2026-08-05
- Class: `[arch]`
- Refs: atlas `backlog.md#atlas-arch-005` (the mandating item); ADR 0004
  (hephaestus-kernel-seam, the plugin boundary that stays `dyn`); ADR 0038
  (one conformance suite, the acceptance harness for the converted kernels).

## Context

Stack-wide dispatch-site counts are kwavers 665, CFDrs 352, gaia 104, coeus
98, moirai 83, consus 66. Sampling the kwavers solver shows the dominant
pattern is not type erasure of an open plugin set but vtable dispatch over
closed design-time implementor sets, evaluated per timestep:

- `sources: &[Box<dyn Source>]` in
  `crates/kwavers-solver/src/forward/nonlinear/westervelt/update.rs:64,66`,
  the Westervelt leapfrog update body.
- `boundary: Box<dyn Boundary>` held in the solver struct, plus
  `Box<dyn Signal>` and `Box<dyn Solver>`.

Every one of these traits has a closed, in-repo implementor set, verified
2026-08-05 against the kwavers tree:

| Trait | Implementors | Surface |
| --- | --- | --- |
| `Source` | 19 (`kwavers-source` 9, `kwavers-transducer` 8, `kwavers-source::types` 1, `kwavers-source::custom` 2) | closed |
| `Boundary` | 3 (`DomainPMLBoundary`, `CPMLBoundary`, `NullBoundary`) | closed |
| `Signal` | ~19 (`kwavers-signal` 16, `kwavers-source` 1, `kwavers-transducer` 1, kwavers-python 2, test-local) | closed |
| `Solver` | 3 (`GenericFdtdSolver`, `DgSimulationSolver`, `GpuPstdSimulationAdapter`) | closed |
| `Medium` | blanket `impl<T> Medium for T where T: CoreMedium` (`kwavers-medium/src/traits.rs:41`) | open by construction |

The performance motivation is structural: a vtable indirect call on a
per-timestep path is a branch predictor miss the CPU cannot amortize, and the
field layouts (`Box<dyn ...>`) prevent the compiler from seeing the concrete
type at all. Enum dispatch monomorphizes the per-variant kernel body.

## Decision (recommended)

1. A closed implementor set dispatched per timestep converts to an
   exhaustiveness-checked enum: static dispatch, still runtime-selectable, no
   vtable. The enum is exhaustively matched with no catch-all arm, so adding
   an implementor is a compile error at every match site rather than a silent
   fall-through.
2. Genuinely open plugin boundaries on cold paths keep `dyn` with the
   applicable exception annotated inline. `Medium` is such a boundary by
   construction (blanket impl) and stays on the trait path; it is not a
   conversion target.
3. Conversion proceeds one operation family per claim, kwavers first (largest
   site count), then CFDrs. Each family carries a criterion comparison on the
   affected kernel, since the claim is performance-motivated and must show
   measured evidence. The conversion is complete per family: the enum replaces
   the `Box<dyn ...>`/`&[Box<dyn ...>]` at the dispatch sites, all constructors
   and callers update in the same change, and no compat shim retains the dyn
   form.

## Alternatives considered

- **Keep `dyn` and rely on devirtualization.** LLVM can devirtualize only when
  it can prove the concrete type; `Box<dyn ...>` crossing a function boundary
  or held in a struct defeats the analysis. Unverifiable, and no stored
  baseline exists to assert it.
- **Generics at every call site.** A `<S: Source>` solver family would
  monomorphize correctly, but the sites collect heterogeneous sources into one
  `&[...]` slice; a generic bound cannot express a slice of distinct concrete
  types. Enum dispatch is the only static-dispatch form that preserves the
  heterogeneous collection shape.
- **Mass conversion of all 1 368 sites in one change.** Rejected: the hot
  timestep path is the measured motivation; converting cold construction-path
  sites adds churn without evidence. Non-goal, recorded in the item.

## Failure modes

- A new implementor fails to compile at the match sites (desired — this is the
  point, and it redirects the author to the enum variant).
- Enum growth past branch-predictor limits: mitigated by the bounded closed
  sets above (max 19 variants) and by keeping dispatch at the operation
  boundary (once per timestep per site, not per element).

## Verification plan

Per family: criterion comparison on the affected kernel against a stored
baseline (median + confidence interval, machine class in the header); the
enum's match arms exhaust the implementor set with no catch-all; differential
test against the dyn path where a reference output exists.
