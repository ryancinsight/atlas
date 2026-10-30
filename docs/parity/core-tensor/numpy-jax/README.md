# NumPy/JAX bounded core-array source contract

This offline research packet defines 19 existing admitted reference endpoints against NumPy **2.5.4** (`a3d0ef1df045b858e68115001fdabc930bb3b68c`) and JAX **0.12.0.1** (`dc4af684446e65ee98eee8090e1ff6f8211473fb`). It adds no denominator identities and gives no provider/runtime/semantic-completion credit. Canonical Atlas integration belongs to the parent task; the pushed `f09`/`da03` snapshots and existing handoffs are untouched.

The selected NumPy endpoints are `shape`, `ndim`, `broadcast_shapes`, `result_type`, `promote_types`, `can_cast`, `astype`, `reshape`, `ndarray.__getitem__`, and `ndarray.__setitem__`. The selected JAX endpoints are `jax.numpy.shape`, `ndim`, `broadcast_shapes`, `result_type`, `promote_types`, `can_cast`, `astype`, `reshape`, and `jax.Array.at` (get/set/add workflows; other methods retained as open scope). Exact source-derived signatures and immutable existing public IDs appear in the framework contract files and `reference-links.json`.

Five reusable laws cover finite concrete host shapes/rank, broadcasting, fixed-shape reshape values, fixed basic-index coordinate maps, and the discrete metadata/AD boundary. A zero extent is a non-unit broadcast extent: `(0,)` with `(1,)` yields `(0,)`; `(0,)` with `(2,)` is incompatible. The abstract tuple law does not define framework input coercion, platform limits, constructors, symbolic/dynamic shapes, arbitrary casting, full indexing, layout/sharding or runtime execution.

`contracts/numpy.json` and `contracts/jax.json` retain validation/error ordering, custom protocol/delegation phases, payload dtype/layout/alias/device/AD modifiers and remaining whole-API gaps. Single planned owners and prerequisite components are definition assignments, without implementation ADR or verified code-owner claims. `source-receipts.json` verifies all **44** bundled source files against their exact frozen Git trees and SHA256 bytes. `source-witnesses.json` contains the **80** exact cited line excerpts, their byte hashes and immutable URLs, so canonical validators can retain portable witnesses without depending on preexisting `/tmp` caches. Input snapshots, history and extraction gaps remain immutable.

Positive Array.at case inputs explicitly tag native JAX caller arrays and integer index arrays with dtype/shape. A separate bare-Python-list case records reference rejection. NumPy getter result semantics are separated from assignment coordinate/effect semantics; object/managed/custom dtype scalar extraction remains open.

The source conflicts and implementation distinctions are deliberate:

- NumPy `astype` docs specify ndarray, while its default guard accepts `isscalar`; missing scalar `astype` can raise after device validation.
- JAX shape/ndim docs promise collection TypeError, while ordinary lists/tuples warn then delegate under the default warning policy. Custom metadata can be fetched twice and returned unchanged.
- JAX reshape can delegate to NumPy/custom reshape and return a view or arbitrary result. Native no-op reshape can retain object identity. Native JAX values have no NumPy mutable-view guarantee.
- JAX `can_cast` directly binds companion NumPy; it is distinct from JAX promotion-lattice `safe_to_cast`. Explicit X64 policy and already formed JAX Array dtypes prevent a universal “64 becomes32” rule.
- JAX `.at` negative/OOB, normalized uniqueness/sortedness, duplicate updates, empty-selection short-circuit, strategy fallback, sharding and gradient rules are separate branches. `apply` retains the reference's unsupported AD rejection.

`acceptance-cases.json` contains **75 unrun** analytical/negative/protocol/differential specifications covering the selected branches. All are future reference/provider acceptance targets, not execution evidence. `benchmarks.json` supplies future complexity, workload, hardware and synchronization obligations. `gaps.json` names **14 open areas**, including unavailable native shape/index/promotion/cast source, conditional dtype/companion dependencies, symbolic/dynamic shapes, full indexing/AD, backend layout/sharding, source conflicts, cast deprecation lifecycle and coercion. Public unsupported cases are retained; none is an approved exclusion or waiver.

Reproduce generated JSON offline using only bundled inputs:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/seal.py --check
```

The 25 static/analytical tests execute only stdlib laws, AST witnesses and receipt validation. They include finite-domain broadcast compatibility/commutativity/associativity, rank0/zero-dimension boundaries, reshape inference rejection, slice affine indices, immutable identity conservation and negative status-promotion/no-framework-import checks. **No NumPy/JAX import, framework build, runtime test, network request, provider edit or canonical write occurs.** `prepare_cached.py` is the historical one-time offline selection helper; portable replay starts at `build.py` and never needs its original absolute cache paths.
