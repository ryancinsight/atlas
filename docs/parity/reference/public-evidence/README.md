# Accepted public-surface source evidence

Introduced in parity program **2026-10-26.11**. This slice admits two independently
reviewed packets as source evidence. It applies **zero public-scope admission
certificates** and changes no raw identity, visibility classification, API mapping
stage, required functionality, verified owner, or execution/release status.
The [index](index.json) and [live joins](joins.json) are consumed by the parity
validator. The [existing public-scope ledger](../public-scope/README.md) remains
the authority for candidate classifications and reusable family routes.

| Accepted packet | Source capture | Retained scope |
| --- | --- | --- |
| TensorFlow 2.21.0 / Keras 3.15.1 | [Manifest](tensorflow-492-20261026/source-manifest.json), [independent review](tensorflow-492-20261026/independent-review.json), [capture index](tensorflow-492-20261026/index.json) | 492 existing IDs, 155 source receipts, 747 quoted spans, 281 rows with AST views / 225 distinct definitions, 24 companion contexts and 19 partial workflow groups |
| JAX 0.12.0.1 / PyTorch 2.14.1 | [Manifest](jax-torch-six-20261026/source-manifest.json), [independent review](jax-torch-six-20261026/independent-review.json), [capture index](jax-torch-six-20261026/index.json) | Six existing IDs, 15 framework receipts / 1,010 span identities, 74 tooling receipts / 56 AST fingerprints, 974 testing-callable source views adding zero APIs |

The accepted original packet manifests are respectively `ac452a11…` and
`67ed2377…`; review digests are `47d7cb36…` and `29c75bc9…`. The validator pins
those full digests independently of mutable capture indexes. Selected original
JSON, including signatures, raw bindings, history, proposals and retained
workflow relations, roundtrips to its exact manifest bytes. Reformatting the
canonical storage or reindexing a column value table cannot change its meaning.
Independent original-source reviews certify the original packets only; the
canonical change still requires its own exact-head review and hosted gates.

## Evidence and scope remain separate

The TF source supports six literal internally-used SavedModelBuilder base
identity proposals, five required operator/protocol views, one required grouping
namespace and 480 unresolved publicness rows. **All 492 canonical visibility
classifications remain `publicness_unresolved`.** The public v1 Builder facades
and their twelve source views remain required: public override signatures and
asset/init behavior differ from the base, and `save` is inherited. A class
identity or facade relationship does not prove semantic equivalence.

The three JAX members remain explicitly source-requested but individually
unresolved under the cached stock selection rules. The actual resolved docs
environment, external callbacks and rendered selection are unavailable; the
prior rendered-documentation HTTP403 route remains stopped. The three PyTorch
introspection functions retain documented export/use evidence and the separate
private-stability guidance conflict. The public wrapper's projection from its
helper result is not an alias. None of the 974 returned lambda declarations is
admitted as a new numerical API, runtime-returned dictionary, effective runtime
signature, kernel, or execution result.

Every join preserves the source packet's frozen Atlas `20ae8d85…` binding and
planned route in separate fields from the live canonical binding, contract route,
capability suppliers and actual API mapping association. The latter are derived
from current authoritative tables; the former are bound to the independently
accepted manifest and its original offline Git/source proofs. A proposed Coeus
facade or workflow role cannot reassign a live API owner. Actual implementation
owners remain null and route verification remains zero.

The [reviewed admission interface design](admission-design/admission-interface-recommendation.json)
is preserved as nonoperative context, with its [review](admission-design/REVIEW.md)
and [manifest](admission-design/manifest.json). A future scope certificate needs
exact candidate/signature/occurrence/corpus binding, independent review and
preserved functionality targets before it can affect a gate. Leading underscores,
doc suppression, private stability, or unsupported implementations are not such
certificates. The existing three uncertified NumPy internal proposals continue
to be requirements; this slice introduces no denominator subtraction or gate
relief. Required reference views and required workflows are different kinds of
obligation, rather than interchangeable counts.

## Portable verification and replay

[Portable witnesses](six-portable-witnesses.json) retain 1,006 exact partial
framework spans and 56 canonical tooling AST payloads. Four complete local JAX
configuration/extension-file spans retain certified digests and bounds only;
standalone foreign source files and packet history are not vendored. Thirteen
TF golden-declaration quotes equal their complete seven- or eight-line input
files; they are retained as source identity/signature evidence, without
vendoring the original source tree. TF quotes retain
their accepted line bounds, file SHA-256, Git blob and immutable source URLs.
The original packet reviews establish full-file/path/blob provenance; this
canonical reader verifies its lossless certificate lineage, selected bytes,
source joins and AST/signature relations without requiring those caches or
executing source. It does not newly recompute an omitted full file's Git hash
from a partial quote or claim complete source/AST/control-flow coverage.

```sh
python3 scripts/atlas-parity.py check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -m unittest discover \
  -s scripts/tests -p test_parity_public_evidence.py -v
```

For a byte-identical producer replay, `scripts/parity/capture_public_evidence.py`
accepts explicit local paths for the two exact packets/reviews, the reviewed
admission-design directory and an Atlas checkout. It first verifies every
original sealed artifact, including source bytes, then writes the selected
captures and live joins. It performs no acquisition, network operation,
framework/Sphinx import, source evaluation or native build. Ordinary canonical
validation needs only committed inputs. Copied-file tests recompute all affected
indexes and reject source/output co-mutations, ownership substitutions, malformed
typed selectors and certificate rebinding; legitimate formatting controls pass.

This evidence leaves 480 TF publicness questions, 211 inherited/generated/native
member selectors, all six JAX/Torch membership/stability questions and complete
signature-specific semantics open. The whole four-framework public denominator
and semantic definition flags remain false. Full dtype/device/layout/AD/effect,
error ordering, implementation, numerical differential, hardware, performance,
and release qualification still require their own acceptance evidence.
