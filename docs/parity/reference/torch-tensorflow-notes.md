# PyTorch and TensorFlow reference extraction — 2026-10-26

This is source-enumeration evidence for the Atlas full-parity program. Every
reference declaration remains **unmapped** until an owner reviews its semantic
contract and supplies implementation and verification evidence. The files do
not assert API compatibility, runtime compatibility, stability, implementation,
correctness, performance qualification, or release availability.

## Frozen baselines and extraction coverage

| Reference | Selected stable release | Exact source revision | Extracted source coverage | Declaration counts |
| --- | --- | --- | --- | --- |
| PyTorch | [2.14.1](https://github.com/pytorch/pytorch/releases/tag/v2.14.1) | `5c4886908584029761b579af026dcfb627c84070` | All entries from the [published 2.14 Sphinx inventory](https://docs.pytorch.org/docs/2.14/objects.inv?raw=1); header declares the minor series, so patch reconciliation remains open. | 9,066 Python objects, all uniquely named; 8,944 additional document/label entries; 18,010 total inventory entries. |
| TensorFlow | [2.21.0](https://github.com/tensorflow/tensorflow/releases/tag/v2.21.0) | `a481b10260dfdf833a1b16007eead49c1d7febf3` | All 585 v1 and 600 v2 [API golden files](https://github.com/tensorflow/tensorflow/tree/a481b10260dfdf833a1b16007eead49c1d7febf3/tensorflow/tools/api/golden). Legacy v1 names are represented under `tf.compat.v1`. | 22,857 source declarations before the Keras supplement. |
| Keras companion for `tf.keras` | [3.15.1](https://github.com/keras-team/keras/releases/tag/v3.15.1) | `250b42181ce9f37df68319d8f4753ec89a349a43` | All 67 generated [TensorFlow Keras export modules](https://github.com/keras-team/keras/tree/250b42181ce9f37df68319d8f4753ec89a349a43/keras/api/_tf_keras/keras). TensorFlow's release metadata requires `keras>=3.12.0`; current stable 3.15.1 is an explicit companion selection, with runtime compatibility unverified. | 1,732 declarations, including 67 modules and 1,665 exports; targets preserve aliases. |

The combined TensorFlow file contains **24,589 declarations / 23,379 distinct
symbols**. A module can declare a class-valued attribute while a second golden
file defines that class. Those are separate source declarations with one symbol,
not two independent capabilities. No `(symbol, kind)` pair is duplicated.

Current stable selection is corroborated by the package owners' [torch
metadata](https://pypi.org/pypi/torch/json), [TensorFlow
metadata](https://pypi.org/pypi/tensorflow/json), and [Keras
metadata](https://pypi.org/pypi/keras/json). The generated files preserve observed
versions, upload dates, dependencies, and metadata hashes. These mutable URLs
describe the observation date; release tags and recorded content hashes fix the
baseline.

## Files and reproducibility

- [pytorch.json](pytorch.json) retains all inventory Python declarations and all
  documentation/label entries in a separate array, with their source and resolved
  documentation URI.
- [tensorflow.json](tensorflow.json) retains v1/v2 modules, classes, functions,
  methods, attributes, protocol messages and fields, argument specifications and
  protocol descriptors where the goldens provide them. Keras exports preserve
  the fully qualified alias target and companion package version.
- [The extractor](../../../scripts/parity/reference/extract_torch_tensorflow.py)
  uses only the Python standard library and never imports the framework runtime.
  Each TensorFlow/Keras source file is checked against the Git tree's blob SHA,
  then recorded with its SHA-256, size and extracted declaration count. The tree
  requests must be nontruncated. PyTorch inventory parsing rejects an unparsed
  line instead of silently dropping it.

From the Atlas root:

```sh
python3 scripts/parity/reference/extract_torch_tensorflow.py pytorch
python3 scripts/parity/reference/extract_torch_tensorflow.py tensorflow
```

Inputs cache under `/tmp/atlas-framework-references`; use `--cache` to select a
different location and `--offline` to regenerate without network access. Sources
remain outside the repository; source URLs and hashes remain in the committed
inventory. Re-extraction against an already cached input is deterministic.

Verification executes four extractor tests (legacy signatures, protocol field
schemas, unknown-syntax rejection and modified-source rejection). Both inventories
regenerate byte for byte offline. All 1,252 TensorFlow/Keras source blobs match
their Git tree identities. Keras's 67 modules contain 1,665 import declarations
and 67 docstring expressions, with no wildcard imports or unhandled top-level
export forms.

`complete_for_source` means the enumerated input files and their declarations
were parsed. Both inventories set **`public_surface_complete: false`**. Source
enumeration does not close the broader reference-scope gate.

## Semantic work that must accompany symbol mapping

The following are contract-extraction obligations. Namespace routing is a
mechanical hint; it cannot settle owner, semantics or acceptance status. In
particular, `tf.raw_ops` spans numeric, string, resource, random, distributed,
storage and execution domains.

| Family | Reference surfaces already enumerated | Contract and acceptance distinctions that must survive deduplication |
| --- | --- | --- |
| Storage, views and mutation | `torch.Tensor`, `torch.Storage`, `torch.as_strided`, `tf.Tensor`, `tf.Variable`, `tf.TensorArray` | Shape/strides/storage offset, overlapping and zero-stride views, alias lifetime and mutation, resource ordering, copy versus view, memory format and contiguous layout; tensor values and mutation effects require separate evidence. |
| Dtypes and numerics | `torch` tensor attributes, `torch.amp`, `tf.dtypes`, `tf.quantization`, raw operators | Exact dtype inventory, promotion and casting, precision and accumulator rules, rounding, overflow, NaN/Inf, signed zero, real/complex conventions, reduced-precision and quantized storage/arithmetic; distinguish an unsupported target from verified execution. |
| Indexing and reductions | Tensor methods, top-level numeric functions, `tf.math`, `tf.raw_ops` | Basic/advanced indexing, gather/scatter repeated indices, negative/bounds behavior, empty axes and zero-length arrays, reduction identity/dtype/order, broadcasting and keep-dimensions rules; gradient accumulation on aliased/repeated selections. |
| Autodiff and transforms | `torch.autograd`, `torch.autograd.forward_ad`, `torch.func`, `tf.GradientTape`, `tf.autodiff.ForwardAccumulator`, `tf.custom_gradient` | Reverse/forward and nested higher derivatives, Jacobian/Hessian construction, batching/composition, complex conjugate conventions, nonsmooth points, nondifferentiable arguments, unconnected gradients, custom derivatives, stateful operations and mutation/version checks. Analytical derivatives precede differential checks. |
| Compilation and graphs | `torch.compile`, `torch.compiler`, `torch.export`, `torch.fx`, `torch.jit`, `tf.function`, `tf.autograph`, `tf.xla` | Capture and tracing boundaries, recompilation/guards, dynamic/symbolic shapes, state/control flow, graph breaks and graph execution errors, custom operators, differentiation through compiled code, export constraints and serialization. Functional equivalents must preserve contracts through Atlas's own compiler/execution architecture. |
| Neural networks and training | `torch.nn`, functional NN, initializers, losses; `tf.nn`, Keras layers/models/losses/metrics | Training/evaluation state, running statistics, padding/dilation/groups, parameter and buffer ownership, masking, recurrent/attention state, stochastic layers, reduction semantics, sparse gradients, mixed precision and all optimizer state/resume semantics. A family test count cannot establish every documented variant. |
| Randomness and distributions | `torch.random`, `torch.Generator`, `torch.distributions`, `tf.random`, stateless raw operators | Seed/state/splitting semantics, algorithm choice, device stream state and reproducibility, distribution support/parameterization, sample versus reparameterized gradients, statistical tests and exact-sequence contracts where promised. Different framework sequences must remain distinct obligations where specified. |
| Distributed and devices | `torch.distributed`, DTensor/FSDP/DDP/checkpoint, accelerator namespaces; `tf.distribute`, DTensor/config | Placement, rank and collective ordering, sharding/layout, process groups, asynchronous completion and synchronization, stream lifetime, multi-host transport, failure/cancellation, deterministic gradients, distributed checkpoint/resume. Require actual recorded hardware and prohibit silent CPU fallback. |
| Sparse, nested and structured tensors | `torch.sparse`, `torch.nested`, `torch.masked`, quantization; `tf.sparse`, `tf.RaggedTensor`, resource/string/raw operators | Formats and invariants, sparse duplicates/coalescing, missing-value interpretation, ragged row partitions, batch semantics, supported operations/dtypes/layouts and gradient contracts; conversion paths are capabilities, not evidence for native support. |
| Interoperability and persistence | NumPy/DLPack/custom-op APIs, `torch.save/load`, ONNX/package; `tf.saved_model`, checkpoints, Keras saving, `tf.lite` | Device/stream ownership and zero-copy lifetime, dtype/stride fidelity, archive schemas and safe-loading behavior, graph signatures/assets/resources, training state restoration, format compatibility and independent consumer round trips. Deployment runtime ownership remains first-party. |
| Data and tooling | `torch.utils.data`, profiler/testing/benchmark/environment docs; `tf.data`, IO, image/audio, summaries/profiler/debugging/Keras callbacks | Deterministic pipelines, ordering/shuffle/repeat/batch/prefetch, cancellation and backpressure, distributed data partitioning, codecs and transforms, trace correctness, instrumentation overhead and repeatable benchmark procedures. |

## Remaining extraction gates

1. Reconcile PyTorch 2.14's published API inventory with exact 2.14.1 tagged
   declarations and release changes. Its release specifically fixes numerical
   correctness for MPS linear algebra; the patch distinction affects evidence.
2. Reconcile TensorFlow 2.21.0 API goldens with export decorators, generated
   documentation and raw-op overloads. The [live API
   root](https://www.tensorflow.org/api_docs/python/tf) identifies **2.16.1** at
   observation, so those pages are navigation aids, not accepted 2.21 semantics.
3. Extract Keras inherited class methods and signature/documentation contracts;
   generated exports alone are not a complete Keras API inventory. Verify the
   selected 3.15.1 companion against the exact TensorFlow 2.21.0 runtime.
4. Review stability and deprecation per API. Experimental, private-spelling and
   legacy compatibility entries remain present. The absence of an experimental
   namespace is not a verified stable designation.
5. Enumerate separate public language and ecosystem surfaces: LibTorch C++ and
   operator schemas; TensorFlow C/C++, Java/JavaScript, Serving, TensorBoard,
   standalone LiteRT and other relevant packages. Version selection and
   inclusion decisions are required; these are unresolved program scope, not
   accepted exclusions or completed parity.
6. Extract environment variables, tutorial/guide-only behaviors, deployment and
   debugging contracts not represented by Python object records. Existing
   documentation records provide traceable starting points for PyTorch.
7. Bind every accepted semantic obligation to one canonical provider owner,
   exact implementation revision, dtype/device/layout/gradient combinations,
   analytical and differential tests, measured benchmarks and required hardware.

No framework runtimes or heavy builds execute during this extraction. No test
skip, fallback, release publication, registry availability or performance result
is credited by these files.
