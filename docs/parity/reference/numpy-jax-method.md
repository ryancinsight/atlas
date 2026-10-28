# NumPy and JAX reference extraction — 2026-10-26

This is a release-pinned **candidate-symbol extraction**, not an exhaustive
public capability inventory and not implementation or parity evidence.

| Reference | Stable release observed on PyPI | Exact source revision | Source files hash-verified | Candidate records | Declaration occurrences | Explicit expansion/name gaps |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| NumPy | 2.5.4 | `a3d0ef1df045b858e68115001fdabc930bb3b68c` | 362 | 2,718 | 2,928 | 65 |
| JAX | 0.12.0.1 | `dc4af684446e65ee98eee8090e1ff6f8211473fb` | 338 | 1,678 | 1,694 | 119 |

Stable release selection uses the primary
[NumPy PyPI metadata](https://pypi.org/pypi/numpy/json) and
[JAX PyPI metadata](https://pypi.org/pypi/jax/json). Each JSON records the observed
version, observation date, response SHA-256, exact release metadata SHA-256,
source commit, root tree, every scanned Git blob SHA and source SHA-256.
NumPy release files were uploaded 2026-10-10. JAX files were uploaded 2026-10-21;
the official JAX changelog labels the release 2026-10-23. Upload and changelog
dates are separate observations.

The [extractor](../../../scripts/parity/reference/numpy_jax.py) downloads all
348 NumPy and 246 JAX `.rst`/`.md` documentation source files from exact release
trees. It excludes seven NumPy Sphinx templates because they contain template
variables rather than concrete declarations, and records each exclusion.
It also reads module docstrings from the 14 NumPy and 92 JAX Python modules
directly referenced by `automodule` when their source is present. Downloaded
content must match the release tree's Git blob SHA before parsing. Extraction
preserves source occurrences, C API declarations, experimental APIs, extension
APIs, example-library APIs, and aliases; shared semantics are not inferred from
matching names. Domains are a mechanical routing aid requiring review.

Direct requests for NumPy/JAX `objects.inv` returned HTTP 403 on this host.
NumPy's stable documentation URL identifies the 2.5 line rather than an exact
patch. JAX's moving `latest` documentation includes an Unreleased section.
Neither moving site is used as the extraction revision. The tagged source is
the authority for the generated records.

Reproduce from a source cache without framework installation:

```sh
python3 scripts/parity/reference/numpy_jax.py --cache /tmp/atlas-numpy-jax-parity
python3 -m unittest discover -s scripts/parity/reference -p test_numpy_jax.py -v
```

The first command fetches missing source files; `--refresh` redownloads the
same pinned sources. Repeated generation with an unchanged verified cache is
byte-identical. The test suite covers module qualification, relative JAX NumPy
names, NumPy's explicit module separator, native declarations, directive
boundaries, experimental/private classification, and failed declaration
parsing.

Independent review identified a native identity error in the initial extraction:
function-pointer members were assigned their last parameter's name, and bare
member names merged unrelated structures. The corrected extractor reads the
declarator name and qualifies native members/enumerators by the enclosing
RST native type/struct/union/enum. An unresolved container retains a unique
source-occurrence identity and an explicit extraction gap rather than claiming
equivalence. Current source resolves all native members. The correction restores
48 distinct member identities and five callback typedef identities, increasing
NumPy's candidate count from 2,665 to 2,718 without changing its 2,928 source
occurrences. Thirteen tests include release-derived fixtures for all 16 affected
`PyArray_ArrFuncs` callbacks, distinct structures' `flags`/`base` fields, callback
typedefs, pointer/array declarators, scope termination, unresolved-scope
rejection, and a regression over the generated inventory.

## Definition gaps that block completeness

The files set `extraction.complete=false`. NumPy lists 59 unexpanded autodoc
directives and six source-unqualified protocol/function names. JAX lists 119
unexpanded autodoc directives. The latter includes member-generated APIs such
as `jax.example_libraries.optimizers` and `stax`; the module record does not
establish member completeness. Some directives overlap an explicit autosummary
list, so these counts are gaps to reconcile rather than estimates of missing
unique symbols.

The extractor does not import frameworks or build Sphinx. Generated/imported
members, notebook-only material, implicit APIs, signatures/overloads/defaults,
exception contracts, prose-only tooling, individual deprecation status and the
dtype/device/layout/gradient product are not exhausted. A source declaration
can describe a protocol or tutorial concept rather than a framework-owned
public object. Those candidates require resolution before the public API
denominator is frozen. No private or experimental name is silently removed.

Completion requires: expand autodoc from the pinned releases; reconcile every
member and reference page against the generated public API index; classify
public/deprecated/experimental/example/protocol status; extract signatures and
semantic distinctions; audit notebook and prose capability coverage; assign
each comparator semantic to a canonical capability and acceptance matrix;
independently review residual and namespace coverage; and retain explicit
decision records for any conflict with workspace architecture. These gaps are
release blockers, not an approved scope reduction.

## Framework semantics that must remain distinct

| Domain | NumPy obligation | JAX obligation and implications |
| --- | --- | --- |
| Arrays, indexing, layouts | Writable views, copy/alias semantics, C/F orders, strides including negative/zero strides, broadcasting, advanced indexing, `out`/`where`, overlapping writes and array protocols | Immutable functional updates; `.at` indexing/scatter conflict, bounds and fill/drop behavior; traced indices and static output-shape requirements; sharded global versus addressable arrays; physical layout and donation/alias lifetime |
| Dtypes and numerics | Exact promotion/casting and scalar rules; integer overflow; IEEE exceptional values/signed zero; object, structured, string, datetime/timedelta, endian and masked-array behavior; ufunc/gufunc contracts | Weak types, default 32-bit policy and `enable_x64`, promotion differences, reduced precision and algorithm precision controls; output dtype versus accumulator dtype; transformed behavior at discontinuities and complex differentiation |
| Transforms and differentiation | FFT length/axes/order/normalization; real/Hermitian layouts; NumPy FFT's documented precision promotion; no native autodiff denominator | Forward/reverse AD, JVP/VJP, higher derivatives, Jacobians/Hessians, custom derivative/batching/rematerialization rules, checkpoint policies, transform composition and control-flow differentiability; preserve NumPy/JAX FFT dtype differences |
| Compiler and effects | Eager array operation contracts, extension C/Fortran APIs and build/ABI tooling | `jit` staging/cache/static arguments, shape polymorphism, lowering/compilation, abstract evaluation, pytrees, callbacks/effect sequencing, refs/state, FFI, Pallas and extension stability; functional equivalence does not authorize adopting XLA as Atlas runtime architecture |
| NN and optimization | Statistical/numerical building blocks rather than an invented NumPy NN suite | `jax.nn` activations/initializers/scaled dot; example `optimizers`/`stax` are documented but have example-library status; do not substitute Optax/Flax for JAX scope without separately versioning those comparators |
| Randomness | `Generator`, `BitGenerator`, `SeedSequence`, streams/jump/advance/state, legacy `RandomState`, distributions and parameter/broadcast/error contracts | Typed keys and legacy keys, split/fold-in, pluggable RNG algorithms, key reuse/stateful randomness, distribution shape/dtype and transformations; a matching distribution does not imply identical seeded streams |
| Distributed/device | NumPy's host semantics and public interoperability boundaries; its absence of accelerator execution is not a waiver for other comparators | Explicit/automatic sharding, meshes, collectives, shard maps, multi-host initialization, placement/transfers, synchronization/asynchrony, addressable/global shards, supported vendor/TPU behavior and failure modes; no silent CPU fallback |
| Interoperability/deployment/tooling | DLPack, buffer/array interfaces, C API/ABI, F2PY, typing/testing, memory maps and NPY/NPZ/text I/O; unsafe object persistence constraints | DLPack versions/ownership/stream handoff, NumPy conversion, FFI, exported program serialization/calling conventions, compiled executable lifetime/portability, profiler/debug/checkify/cache/environment controls |

Primary release-source anchors for the semantic audit include
[NumPy indexing](https://github.com/numpy/numpy/blob/a3d0ef1df045b858e68115001fdabc930bb3b68c/doc/source/user/basics.indexing.rst),
[NumPy promotion](https://github.com/numpy/numpy/blob/a3d0ef1df045b858e68115001fdabc930bb3b68c/doc/source/reference/arrays.promotion.rst),
[NumPy FFT module documentation](https://github.com/numpy/numpy/blob/a3d0ef1df045b858e68115001fdabc930bb3b68c/numpy/fft/__init__.py),
[JAX NumPy differences](https://github.com/jax-ml/jax/blob/dc4af684446e65ee98eee8090e1ff6f8211473fb/docs/jax.numpy.rst),
[JAX transformation API](https://github.com/jax-ml/jax/blob/dc4af684446e65ee98eee8090e1ff6f8211473fb/docs/jax.rst),
[JAX export API](https://github.com/jax-ml/jax/blob/dc4af684446e65ee98eee8090e1ff6f8211473fb/docs/jax.export.rst), and
[JAX compatibility policy](https://github.com/jax-ml/jax/blob/dc4af684446e65ee98eee8090e1ff6f8211473fb/docs/api_compatibility.md).
