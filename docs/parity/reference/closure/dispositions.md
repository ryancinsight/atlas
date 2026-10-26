# Bounded source dispositions

Program 2026-10-26.4. These source findings refine WP-001/WP-003. No full public
surface, whole-API semantic closure, implementation, runtime test, external
verification, native hardware, performance or release status advances. The
admitted set remains 38,096 candidates: two source-specified, 59 partial and
38,035 unmapped. Other overlapping candidate tables remain explicit obligations.

## NumPy generated ufunc member surface

The [bounded declaration table](numpy-ufunc/bounded-completeness.json) preserves
all 133 original rows: 130 literal generator objects and three native aliases.
It records 22 native/stub/slot member candidates, 642 source bindings and 123
public root/string spellings. The complete declared cross-products contain
2,860 object/member and 2,706 spelling/member rows. These overlapping source
tables add no API-denominator or verified-capability count.

All 130 generated doc payloads remain, including eight explicitly empty ones.
All 123 public spellings have exact frozen-source doc/alias traces; 104 selectors
on the ufunc reference page are dispositioned. The older official 2.5.0 index is
supplemental, with no relabelling as rendered 2.5.4. Twenty private generator
names and the documented public C-user methods `_resolve_dtypes_and_context`
and `_get_strided_loop` remain retained despite underscores and unstable status.

The [workflow templates](numpy-ufunc/ufunc-expansions.json) preserve real guard
differences: native `outer` checks binary, non-generalized inputs without a
single-output guard, so multi-output cases remain candidates. Dtype resolution's
`reduction=True` checks arity without the actual reduction workflow's gufunc
restriction. Conditional metadata, writable doc/state fields, alias spellings,
wrapper shadows and source/stub/doc contradictions remain separate. Delegated
protocol outputs may retain their own graphs; source NumPy's lack of native AD
does not authorize detaching them.

Thirty frozen source blobs, 597 source-line citations and 17 static/negative
checks pass. Nine workflow templates remain partial. Instantiated dtype loops,
promoters/ABI/ISA, runtime attribute availability, errors, AD, benchmarks, other
native modules/factories and exact rendered selection remain unqualified. The
workspace must define these public workflows through approved functional
interfaces; a NumPy runtime or raw pointer architecture is not adopted by this
inventory. Concrete provider designs remain WP-004 obligations.

## JAX requested members

The [22 retained candidate payloads](jax-selection/selection-dispositions.json)
reconcile as 15 selector-eligible through their own docs, two through documented
inherited `Stage.in_tree` properties, one conditional metaclass-documentation
fallback (`Compiled.__call__`) and four filtered by stock undocumented-member
rules (`Traced.jaxpr/out_info`, `Lowered.out_tree`, `Compiled.out_tree`). Filtered
names remain scope obligations. Source selection does not prove rendered
inclusion, callable semantics or workflow equivalence.

The frozen JAX build requests Python 3.12 and Sphinx `>=7.3.2,<8.0`; it does not
record an exact resolved transitive lock. Relevant [Sphinx filter/helper source](https://github.com/sphinx-doc/sphinx/blob/v7.4.7/sphinx/ext/autodoc/__init__.py#L643-L806)
ASTs match across the 14 compatible published releases in the captured metadata.
The source study checks 74 tooling inputs and eight frozen JAX files. Generic
metaclass docs supply no operation contract. Extension event handlers and the
actual rendering environment remain unqualified.

Three [official versioned-page GETs](jax-selection/versioned-docs-access.json)
returned HTTP 403 and produced no HTML. That rendered-output check is denied;
it has not been retried or bypassed. Source evidence and ten source/selection
regressions are completed; exact rendered receipts remain unavailable.

## PyTorch `Tensor.new_tensor`

The [corrected partial contract](torch-new-tensor/contract.json) supersedes the
active mapping's earlier universal copy/layout summary; the historical capture
is preserved. The [manual parser](https://github.com/pytorch/pytorch/blob/5c4886908584029761b579af026dcfb627c84070/torch/csrc/utils/tensor_new.cpp#L1510)
accepts `data`, `dtype`, `device` and `requires_grad` after possible receiver
`__torch_function__` interception. Documented `layout` and `pin_memory` keywords
are rejected on the ordinary built-in route and remain reference discrepancies.

Tensor, NumPy, CUDA-array-interface, DLPack, Storage, scalar and sequence routes
must retain their ordering, errors and ownership behavior. The source Storage
route uses `set_` and a matching `.to(copy=False)` fast path; Tensor input can
preserve its layout. These prevent a universal fresh-storage/strided assertion.
They are source-derived counterexample candidates; admitted input/alias cases
still require runtime confirmation. Legacy `torch.Tensor`, `torch.tensor` and
`new_tensor` remain separate contracts.

The study verifies 26 source blobs and nine source regressions. All
[26 acceptance cases](torch-new-tensor/acceptance-cases.json) remain unrun,
including protocol admission, backend/layout conversion, AD, transforms and
compiler behavior. No source-only correction grants whole-API qualification.

## Keras saving package and lookup workflows

All [14 retained names](keras-saving/saving-endpoint-resolution.json) remain in
scope: one module and 13 export names targeting 12 definitions. The official
Keras 3.15.1 wheel has SHA-256
`836460e480930acbd19bb7a17e62f9ecad40e8a9af9a651fc8d0586a96d27e20`.
All 908 hashed RECORD entries verify (909 entries including RECORD itself),
and 904 Python files match selected release Git blobs.

Both saving submodules are packaged with identical exports. The ordinary
`keras` root reexports `saving`; the selected TensorFlow-facing root initializer
does not. Fresh attribute lookup, explicit concrete submodule import, subsequent
process import state and TensorFlow lazy aliases are separate workflows.
Package presence and import targets establish no runtime availability or
serialization equivalence. Method adapters such as `Model.save` remain distinct
from free functions and direct-import aliases.

Five official Keras3 pages are captured; four API pages, including
[whole-model saving](https://keras.io/api/models/model_saving_apis/model_saving_and_loading/),
link `v3.15.1` sources matching the selected commit. Their page URLs remain
mutable. Signature/prose discrepancies are retained, including `safe_mode=True`;
no setting changes. Eleven static checks pass; all
[ten runtime probes](keras-saving/saving-acceptance-specifications.json) are
unexecuted. TensorFlow wheel aliases, exact dependencies/backend context, legacy
companions and real serialization/editor/registry behavior remain open.

## Cached reproduction

```sh
python3 scripts/parity/dispositions/reproduce.py jax-selection
python3 scripts/parity/dispositions/reproduce.py torch-new-tensor
python3 scripts/parity/dispositions/reproduce.py keras-saving
python3 scripts/parity/dispositions/reproduce.py numpy-ufunc
```

This driver performs no network request or framework import. It copies captured
primary inputs and adapted analysis code into a separate external work directory,
checks versioned input hashes, then compares stable source outputs byte for byte.
`--capture-cache`, `--source-cache` and `--work` select input/output locations;
missing inputs are blockers, never fabricated or silently downloaded. Primary
source/wheel/HTML bytes remain external, with receipts and acquisition URLs in
the versioned JSON. Original capture manifests retain original generator hashes;
the adapted driver reproduces named source facts, not those historical script
bytes or a full documentation build. NumPy's captured `verification-report.json`
is historical metadata; it is not counted as a regenerated output. The driver
regenerates its six named source tables and runs the 17 checks separately.
Canonical CI validates the metadata,
identities, count conservation and zero-credit distinctions without requiring
external caches. All provider designs and exact-revision execution gates remain.
