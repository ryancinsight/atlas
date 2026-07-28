# ADR 0038: One generic conformance suite owns the ComputeBackend contract

- Status: Proposed
- Date: 2026-07-28
- Class: `[arch]` `[minor]`
- Relates to: [ADR 0001](0001-gpu-accelerator-substrate.md),
  [ADR 0004](0004-hephaestus-kernel-seam.md),
  [ADR 0034](0034-athena-single-accelerator-backend.md)
- Amended 2026-07-28 by the
  [conformance triage](../audit/2026-07-28-computebackend-conformance-triage.md),
  which corrects the contract basis and the Metal characterization below.

## Context

`ComputeBackend` is the stack's central substitution seam: Leto is the CPU
backend, Hephaestus the accelerator backend, and Coeus binds both through
zero-cost generic dispatch. The standing rule for such a seam is that every
implementation runs **one shared generic conformance suite** plus differential
tests against its siblings.

That suite does not exist.

### Source audit (2026-07-28)

Each accelerator backend carries a hand-written `tests/contract.rs`:

| Backend | Lines | Test fns | Unique to it |
| --- | --- | --- | --- |
| `hephaestus-wgpu` | 5 287 | 130 | 41 |
| `hephaestus-rocm` | 4 657 | 70 | 53 |
| `hephaestus-cuda` | 4 381 | 114 | 20 |
| `hephaestus-metal` | 1 614 | 40 | 12 |
| **Total** | **15 939** | | |

Pairwise overlap by test-function name:

| Pair | Shared |
| --- | --- |
| `cuda` / `wgpu` | 87 |
| `metal` / `wgpu` | 19 |
| `cuda` / `metal` | 22 |
| `cuda` / `rocm` | 13 |
| `metal` / `rocm` | 13 |
| `rocm` / `wgpu` | 7 |

**Five test-function names are present in all four.** The union is 221 distinct
names. `ls crates/` confirms no conformance or test-support crate:
`hephaestus-core`, `-cuda`, `-metal`, `-python`, `-rocm`, `-wgpu`.

Two failures follow from one cause. The `cuda`/`wgpu` pair shares 87 tests by
copy-paste lineage, so those assertions are maintained in two places and drift
independently — the duplication half. And 53 of rocm's 70 behaviours are
verified for no other backend, while Metal is held to 40 assertions where WGPU is
held to 130 — the coverage half. The seam's contract is not defined by the trait;
it is defined by whichever backend's author wrote the most tests.

This is the exact condition the seam abstraction exists to prevent. A consumer
generic over `<B: ComputeBackend>` is entitled to assume every backend satisfies
the same contract, and today nothing establishes that.

## Decision

### 1. A new workspace-level crate owns the conformance suite

`crates/hephaestus-conformance` holds one generic suite parameterized over the
backend:

```text
crates/hephaestus-conformance
├── src/
│   ├── allocation.rs      buffer lifetime, alignment, uninitialized-read rejection
│   ├── transfer.rs        host↔device copy, mismatch rejection, aliasing
│   ├── dispatch.rs        kernel launch ABI, workgroup bounds, error propagation
│   ├── elementwise.rs     value semantics against the CPU reference
│   ├── reduction.rs       reduction-order tolerance per numerical_discipline
│   └── linalg.rs          decomposition and strided-operand contracts
```

Each module exposes generic entry points; a backend crate's `tests/contract.rs`
becomes an instantiation, not a suite:

```rust
// crates/hephaestus-wgpu/tests/contract.rs
hephaestus_conformance::assert_backend_contract::<WgpuBackend>();
```

The crate is a normal published member of the workspace, not a dev-only artifact,
because Leto and any future backend outside this repository must run the same
suite (decision 3).

This satisfies the module → crate promotion trigger directly: four sibling crates
need to consume it, and it needs independent feature gating so a backend compiles
the suite without pulling in its siblings.

### 2. The union is triaged, not merged wholesale

**Amended by the triage.** The contract basis is the **public API surface**, not
the union of test names: 112 entry points are declared by all four backends, and
those are the contract. Test names proved to be an artifact of four authors'
granularity — `rocm` bundles several clauses per test function where `cuda` and
`wgpu` split them — so triaging names would have shaped the suite around whoever
wrote the most tests. The classification below is applied to API entry points.

The triage also establishes that `hephaestus-metal` declares no native Metal code
and delegates wholly to `hephaestus-wgpu`; the consequences section is amended
accordingly. Full evidence and the per-module clause assignment are in the
[triage ledger](../audit/2026-07-28-computebackend-conformance-triage.md).

Each entry point is classified in the migration:

- **contract** — a behaviour every `ComputeBackend` must exhibit. Moves into the
  generic suite. The 5 universal names and most of the `cuda`/`wgpu` 87 land here.
- **capability-gated contract** — required only of backends advertising a
  capability (f64 support, unified memory, subgroup ops). Moves into the suite
  behind an associated-const capability predicate, so a backend lacking the
  capability skips it by construction rather than by omission.
- **backend-intrinsic** — genuinely specific to one implementation (a CUDA
  managed-memory behaviour, a WGSL validation rule). Stays in that backend's
  crate, in a file named for the concern rather than `contract.rs`.

Classification is recorded per test in the migration change. A test that cannot
be classified is a contract that was never specified, and specifying it is the
work.

### 3. Leto runs the same suite

Leto is the CPU backend of the same seam. Once the suite is generic it applies to
Leto unchanged, and Leto becomes the differential reference the accelerator
backends compare against — the CPU-reference oracle several backend tests already
reach for informally (`matches_cpu`, `cpu_reference` appear across the Hephaestus
test tree).

Cross-backend differential tolerances follow the reduction-order rule: bitwise
equality only where evaluation order provably matches, otherwise an epsilon
derived from reduction depth and width, never an empirical constant.

### 4. The suite is generic over scalar type, not only over backend

Backend genericity without scalar genericity would rebuild half the problem.
Entry points are `<B: ComputeBackend, T: Scalar>` and each backend instantiates
across every scalar type it ships, which is also the fix for the stack-wide
single-type instantiation gap recorded as `ATLAS-ARCH-002`.

## Consequences

- 15 939 lines of divergent per-backend tests collapse toward one suite plus four
  thin instantiations, and the 87 duplicated `cuda`/`wgpu` assertions are
  maintained once.
- Metal's coverage rises from 50 of the 112 shared entry points to the full
  contract. **Amended by the triage:** because `hephaestus-metal` delegates to
  `hephaestus-wgpu` rather than implementing kernels, a failure there indicates a
  broken delegation or Metal adapter path, not an unverified kernel — the
  original expectation of widespread Metal kernel failures was wrong. The
  instantiation stays because it is nearly free once the suite exists and it does
  catch delegation regressions.
- Nine shared entry points are currently tested by **no** backend
  (`binary_elementwise_typed` and its three siblings, `scalar_elementwise_strided`,
  `prod_axis_into`, `prepare_reduce_axis_into`, `ray_line_integrals{,_into}`).
  Authoring those clauses is the part of this work that adds coverage nothing
  provides today. `ray_line_integrals` is the priority: Helios depends on the
  substrate for radiographic projection.
- Where a real backend fails a clause it never ran before, that remains a defect
  to fix in the backend — never a weakened test, and never a clause reclassified
  as backend-intrinsic to make the suite pass.
- A new backend costs one instantiation instead of authoring a suite, which is
  what makes the seam genuinely open.
- Adding a contract clause is one edit that every backend is immediately held to.
- The crate is a Hephaestus workspace member, so no new repository, no new pin,
  and no `.gitmodules` change. The Atlas package count stays 25.

## Alternatives rejected

**A shared `#[macro_export]` test macro.** Generates the same assertions without a
crate boundary, but macro-expanded tests degrade IDE support and error messages,
and the macro policy makes declarative macros the last resort — const-generic and
trait-parameterized designs come first. A generic function over `<B, T>` is the
direct expression.

**A `dev-dependency`-only test-support crate.** Cannot be consumed by Leto or any
out-of-repo backend, which decision 3 requires. Publishing it costs nothing and
makes the contract available to any implementor.

**Keep per-backend suites, add a checklist.** A document asserting that four
suites cover the same behaviours is a second source of truth about the first, and
it drifts the moment a backend adds a test. The audit is what a checklist looks
like after two years.

**Merge all 221 tests into the suite.** Would force every backend to satisfy
assertions that are genuinely implementation-specific, and the pressure to make
that pass would push real contract clauses back out into backend files. Triage
(decision 2) is the load-bearing step.

## Verification

1. Each backend's `tests/contract.rs` is reduced to instantiation calls; no
   assertion logic remains in a backend crate except classified
   backend-intrinsic files.
2. The union of assertions executed per backend is a superset of what that
   backend executed before the migration — the suite adds coverage and removes
   none. Demonstrated by test-name count per backend, before and after.
3. Every generic entry point is instantiated across every scalar type the backend
   ships, not one.
4. A deliberately broken backend method fails the suite for that backend and only
   that backend, proving the parameterization is real.
5. Capability-gated clauses skip by an associated-const predicate, and a backend
   advertising a capability cannot skip its clauses.
6. Cross-backend differential tolerances cite their derivation at the assertion
   site; no empirical epsilon is introduced.

## References

- [ADR 0001](0001-gpu-accelerator-substrate.md) — the Hephaestus substrate whose
  contract this suite specifies.
- [ADR 0004](0004-hephaestus-kernel-seam.md) — the kernel-authoring seam whose
  per-dialect implementations the suite holds to one contract.
- [ADR 0034](0034-athena-single-accelerator-backend.md) — the precedent that one
  backend abstraction beats per-device crates.
- Structural and abstraction audit, `gap_audit.md` (2026-07-28) — finding A, with
  the per-backend line, test-count, and pairwise-overlap evidence.
