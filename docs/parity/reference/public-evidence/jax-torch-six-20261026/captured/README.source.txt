# Six unresolved JAX/PyTorch bindings: frozen source audit

This packet audits exactly six raw bindings captured from Atlas `20ae8d85f6c3aa6a6712e4f0b823b5f066bdc008`. It changes no canonical file, owner, reference ID, public denominator, implementation stage or product version. All six raw visibility classifications remain **publicness unresolved**. The snapshot is anchored by the pinned commit/tree/path/blob proof and semantic receipts in [canonical-anchors.json](canonical-anchors.json). Every functionality obligation remains required; source documentation/filtering and implementation support cannot remove one.

| Binding | Frozen-source result | Required functionality route |
| --- | --- | --- |
| `jax.stages.Traced.out_info` | Public class export and explicit member request; undocumented property getter; stock cached autodoc filters it | Coeus `GRAPH-COMPILE`, after `GRAPH-TRACE` and `DEV-COMPILE` |
| `jax.stages.Lowered.out_tree` | Public class export and explicit request; own annotated list-slot descriptor; no inherited target documentation | Same |
| `jax.stages.Compiled.out_tree` | Public class export and explicit request; own annotated list-slot descriptor; no inherited target documentation | Same |
| `torch.overrides.get_ignored_functions` | Literal export, own docstring, dedicated API directive and cached published minor inventory entry; guide explicitly calls the coverage API private | Coeus `INTEROP-TENSOR`, after `INTEROP-ARRAY`, `GRAPH-EXPORT`, `IO-CHECKPOINT` |
| `torch.overrides.get_overridable_functions` | Same contradictory documentation/export/stability axes; public wrapper projects the private helper's tuple element 0, not an alias | Same |
| `torch.overrides.get_testing_overrides` | Same contradictory axes; returned callable catalogue is prescribed introspection/coverage tooling | Same |

These are planned functionality routes from the frozen20ae capability records, not a claim about later live canonical mappings. All six actual canonical API mapping associations remain explicitly **unmapped**. No implementation ownership or source-semantic closure follows from routing.

The three Torch functions are documented tooling functionality required by the user's full-parity instruction even where the guide describes private stability. That ordinary resolution does not require a scope choice from the user. It does not establish a stable public API guarantee or silently override the guide. The canonical schema should retain separate documentation, export, stability and required-functionality axes; publicness stays unresolved pending source/schema review.

## Exact sources and selection limits

JAX is frozen at `0.12.0.1`, commit `dc4af684446e65ee98eee8090e1ff6f8211473fb`; PyTorch at `2.14.1`, commit `5c4886908584029761b579af026dcfb627c84070`. Fifteen complete framework blobs have Git-blob and SHA-256 receipts; every source span has exact line bounds, span SHA-256 and a commit-addressed official URL in [source-receipts.json](source-receipts.json). There is no selected frozen source-blob dependency missing from this packet.

The JAX three are requested in [the frozen stage API source](https://github.com/jax-ml/jax/blob/dc4af684446e65ee98eee8090e1ff6f8211473fb/docs/jax.stages.rst#L15-L23). Their own declarations, getter, constructors, slot generation and direct `Stage` inheritance are recorded without executing JAX. `Traced.out_info` constructs and unflattens output metadata. The `out_tree` declarations store a `PyTreeDef`; source storage does not prove immutable/read-only semantics.

The frozen docs requirement selects a Sphinx range, `>=7.3.2,<8.0`, and Python 3.12 minor, not an exact resolved docs environment. Seventy-four cached primary tooling files support 56 AST method fingerprints across 14 observed compatible Sphinx releases. In these sources explicit `members` does not override `has_doc or undoc_members`. The configured local source audit finds no literal local skip-member callback or doc-inheritance/default-members override. Installed external callbacks and the actual resolved environment remain unknown. **No Sphinx helper, framework module, docs configuration or extension is executed.** No actual rendered visibility is proven. The prior JAX rendered-docs 403 route remains stopped without retry or bypass; its original outcomes remain in the packet.

For Torch the [dedicated reference source](https://github.com/pytorch/pytorch/blob/5c4886908584029761b579af026dcfb627c84070/docs/source/torch.overrides.md#L12-L29), [literal exports](https://github.com/pytorch/pytorch/blob/5c4886908584029761b579af026dcfb627c84070/torch/overrides.py#L50-L62), and [guide's private warning and public examples](https://github.com/pytorch/pytorch/blob/5c4886908584029761b579af026dcfb627c84070/docs/source/notes/extending.md#L1021-L1077) are preserved together. The guide also uses stale underscore spellings; a missing top-level source binding does not prove runtime nonexistence. `get_ignored_functions` has a set annotation/constructed set while its prose says tuple; this is a retained semantic contradiction. The cached `2.14` Sphinx inventory proves published minor membership of all three, not correspondence to an exact `2.14.1` rendered build.

[returned-tooling-views.json](returned-tooling-views.json) preserves all 974 lambda declarations inside `get_testing_overrides`, including source key expressions, parameter variants and the prescribed `-1` return. These are coverage-testing callable views, **zero new public API IDs and zero numerical operator verification**. Runtime catalogue construction, conditional namespaces, aliases and effective wrapper signatures remain unrun; the 974 source declarations do not establish the runtime returned dictionary's completeness.

## Reproduction and acceptance

Use Python's standard library only:

```sh
python3 -B build.py
python3 -B verify.py
python3 -B seal.py
python3 -B test_manifest.py
python3 -B seal.py --check
```

[six-dispositions.json](six-dispositions.json) preserves the six exact original IDs, binding positions, source-artifact/source-row joins, original rows, signatures and source certificates. [configuration-selection-evidence.json](configuration-selection-evidence.json), [tooling-selection-evidence.json](tooling-selection-evidence.json) and [published-inventory-evidence.json](published-inventory-evidence.json) separate source policy from unavailable rendering. [remaining-evidence.json](remaining-evidence.json) retains the four evidence/semantic gaps and stopped route history. Existing raw classifications and protected source packet/review bytes remain immutable.

`verify.py` blocks framework/Sphinx imports, validates finite conservation and source/owner joins, runs copied-artifact malformed/no-credit adversaries, and compares seven generated JSON outputs byte for byte in a disposable replay. Lossless table reindexing and reformatting are accepted controls. Tests do not execute framework functionality and grant no API, numerical, AD, compiler, device, layout, runtime, performance or release credit. Independent acceptance of this new packet remains pending the root's exact sealed-packet review. Broader public denominator and per-framework semantic closure remain open.

## Canonical provenance repair

This successor preserves the initial127 artifacts and root manifest byte for byte
under [history/predecessor-d3de6c5e](history/predecessor-d3de6c5e/README.md). The
[initial independent review](history/initial-independent-review/review-d3de6c5e.json)
found that neighboring capture hashes and derived routes could be co-mutated to
invent canonical facts. The repair binds all six canonical inputs plus both
codec/schema sources through the exact Atlas20ae Git commit, directory trees,
paths and blobs. The validator pins that proof independently of capture metadata.
Current input semantics must match the frozen semantic receipts; Boolean/float
distinctions, metadata, record order and all fields survive normalization. JSON
reformatting and lossless value-table reindexing remain valid encodings. A new
neighboring content hash cannot authorize changing a canonical mapping or owner.

`validate.py`, `seal.py --check` and `replay.py` all enforce those anchors, including
after a physical manifest reindex. Protected original source/review bytes are
bundled; validation, sealing and replay read no live canonical checkout or source
checker state. `record_canonical_anchors.py` is the one-time local Git-object
capture tool and is never invoked by portable replay. The original absolute
paths remain immutable historical provenance, not runtime dependencies.

The later live canonical mapping is a separate integration-time join. Frozen
source associations here remain six unmapped rows and six unresolved visibility
classifications. All seven source outputs,15 framework blobs,1,010 spans,74
tooling sources,56 method fingerprints and974 callable source views are retained;
the callable views contribute zero public API IDs and zero numerical/runtime
evidence. The new copied-file corruption tests exercise both reported attacks,
capability-prerequisite/contract/mapping analogues and false capture/proof claims
through actual validate, seal-check and replay entry points. Valid reformat/table
reindex and portable-read controls remain accepted. New exact-seal independent
review remains pending; no source-semantic, runtime or release stage is promoted.
