# End-to-end functional acceptance contracts

This is a partial, source-backed design inventory: **24 workflows, 58 unrun
scenarios and 29 export route profiles**. It neither closes the complete public
workflow denominator nor qualifies an implementation. Fourteen exact analytical
fixtures and twelve deliberately wrong-fixture probes check the mathematics of
the proposed witnesses; they do not execute NumPy, JAX, PyTorch, TensorFlow or an
Atlas backend. All native and reference adapters remain unbound.

The [workflow contracts](workflow-contracts.json) and [acceptance language](acceptance-language.json)
cover array/dtype/layout/dispatch, indexing and state, AD/transforms/compiler,
NN/training/optimizers, RNG, distribution/device execution, persistence and
interchange, serving/export targets, native extensions and tooling. They retain
framework-specific signatures, effects, precision, rejection and target behavior.
The [source manifest](source-manifest.json) and [citations](source-citations.json)
bind 206 frozen source blobs and 217 anchors. Independent source/cache and replay
receipts are preserved in [the review](independent-review/final-review.json).
The normal gate verifies stored hashes and traceability; it does not claim to
download or re-execute every captured source on each invocation.

The [export matrix](export-acceptance-matrix.json) separates all 25 Keras
backend/format cells and four native root export surfaces. Static shape
specialization, supported source rejection, state mutation and actual target
execution have different outcomes. In particular, Keras JAX-to-OpenVINO flags
do not establish a working non-XLA path: frozen JAX2TF ignores those flags and
selects native serialization. Compatibility is unrun, and the frozen versions
remain unchanged. A reference's CPU-copy adapter does not establish Atlas native
device execution.

Mutable Ref AD includes returned gradient markers and accumulation effects.
Asynchronous training histories retain their selected read/commit ordering;
synchronous sum/mean fixtures are not universal asynchronous results. Quantized
workflows retain AWQ calibration, scaling, packing and serialization as well as
other source-supported modes. Train/checkpoint/export/restore chains include
model, optimizer, RNG, data, graph/effect and repeated-call state.

## Direction and remaining gates

The [planning dispositions](planning-dispositions.json) apply the existing
DEC-001 through DEC-009 policies to all eight captured architectural directions.
First-party generic numeric/array kernels, typed state/effect AD, native graph
and target lowering, provider-owned collectives, versioned data schemas and
explicit RNG policies follow the user's existing instruction. They require no
new scope-reduction decision. Each concrete provider interface still requires
its existing ADR/design/code approval; no such approval is granted here.

The [companion inventory](companion-inventory.json) retains 30 unresolved
scope/version/ABI/opset/build decisions. Root runtime dependencies, optional
documented workflow targets and adjacent ecosystems remain distinguishable.
Resolve coherent supported tool/artifact hashes before running each route;
never downgrade the frozen roots to make an adapter pass. Public companion API
and workflow extraction remains open. Hardware absence and the stopped JAX
rendered-documentation HTTP403 route grant no verification or scope exclusion.

The gate reports workflow counts separately from public API semantic coverage.
Every signature still needs source-valid dtype/device/layout/gradient/domain
classes and native/oracle bindings. Analytical, differential, failure,
performance, platform, registry and fresh-consumer acceptance must run at exact
revisions before any implementation or release state changes.
