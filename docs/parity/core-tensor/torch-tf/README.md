# Bounded PyTorch/TensorFlow core-tensor source contracts

Pinned PyTorch2.14.1 `5c4886908584029761b579af026dcfb627c84070` and
TensorFlow2.21.0 `a481b10260dfdf833a1b16007eead49c1d7febf3`, with admitted
identities pinned to Atlas `da03f4ea2b134539f4f26343510f0e41e8e43568`.
No Keras behavior is required for this selected core slice.

The packet has10 exact admitted public endpoints per framework,20 partial
contract records,58 source line witnesses,32 full-file byte/line/SHA/Git receipts,
43 concrete analytical **specified-not-run** cases and11 named native/generated
source gaps. No whole API is fully specified or implementation/runtime qualified.

The original80cfe packet is preserved with all52 artifact hashes under
`/tmp/atlas-core-model-torch-tf-history/80cfe34a3ca83c163ffdc6a6501cae72001df232a0033e7f0c5167912d7468c6`.
`correction-history.json` retains the independent findings and exact before/after
records. Only two contract records change, three prior cases are corrected, and
two cases are added; the other18 contracts and38 prior cases remain unchanged.

PyTorch endpoints: Tensor.dim, broadcast_shapes, promote_types, can_cast,
Tensor.to, reshape, Tensor.view, index_select, Tensor.index_put_, autograd.grad.
TensorFlow endpoints: rank, shape, broadcast_dynamic_shape, cast, add, reshape,
gather, tensor_scatter_nd_update, Variable.assign, GradientTape.gradient.

`contracts.json` retains source signatures, exact admitted api_identity and
historical source-view ID separately; each record supplies concrete slice domain,
validation order known in the source, named delegated/native gaps, alias/effect/AD
distinctions, planned first-party supplier prerequisites and actual coverage axes.
Source clauses are partial obligations, never full closure by analogy.

`broadcast-law.json` defines concrete right-aligned nonnegative extent joining,
including0 joined with1 equals0. The PyTorch note's componentwise-max prose is
preserved as a discrepancy; missing cached _refs bytes are not invented. TF
static unknown-shape assumptions differ from dynamic BroadcastArgs validation.

Tensor.to's native no-op guard requires compatible dtype, layout, device and
memory_format plus copy=False. Memory format must be Preserve or equal to
self.suggest_memory_format(); same dtype/device alone is insufficient. A concrete
NCHW-contiguous rank4 channels_last conversion now explicitly selects _to_copy
despite copy=False. The recovered native source is already cached and Git-verified.
TF cast also has a real no-op alias branch; reshape does not license an
always-copy or always-alias rule. Torch shape view, dtype reinterpretation,
advanced read/copy, in-place update and TF functional scatter/resource assignment
remain distinct. Integer shape/index cotangents are absent where source registers
that boundary; requested materialized zeros and sparse IndexedSlices remain
separate policies. TF trainability includes resource/variant and optional
quantized cases, which are retained and unqualified rather than blanket excluded.
The GradientTape wrapper sequence now separates target normalization/trainability
logging before source flattening. The transposed-view fixture is explicitly
noncontiguous, and a grad-bearing floating-to-floating dtype-view fixture isolates
its registered nondifferentiable boundary from integer dtype restrictions.

For portable canonical integration, copy the ten JSON files listed in
`portable_files` in the manifest. `source-provenance-registry.json` gives full line
count and byte size per source. Every line witness also embeds these bounds,
exact excerpt, excerpt SHA, full-file SHA and Git blob/revision/path. A canonical
validator can check line bounds without vendoring raw source files; raw copies
remain here solely for local exact-byte replay and independent review.

Case JSON shape: `{case_id, contract_refs, inputs, expected,
independent_oracle, actual_axis_values, status, framework_execution,
tolerance_policy, qualification_rule}`. All43 have status specified-not-run and
framework_execution=false. Undefined/ambiguous/negative-domain cases remain
required pending policy or exact native evidence, not skipped verification.

Planned Coeus framework accountability composes Eunomia promotion/casting,
Leto layout/indexing, Mnemosyne ownership and Hephaestus device seams. Source
Variable.assign is a selected resource implementation variant; root may map its
canonical framework capability to TEN-RESOURCE while preserving this proposal.
No actual implementation owner or status is promoted. Sparse/nested/ragged,
resource, device, symbolic, forward/higher AD and other public variants remain
required; the dense concrete domain does not exclude them.

Replay uses only bundled inputs and standard-library research code:

```sh
python3 build_packet.py
python3 build_cases.py
python3 validate_packet.py
python3 finalize_packet.py
```

Eight checks pass: source/Git provenance, portable anchor bounds, exact admitted
identities/status,43 unrun case records,441 independent finite abstract-law
symmetry cases,11 rejected adverse fixtures (including five review regressions),
bounded before/after correction history and no framework import/promotion.
The abstract-law checks test our mathematical specification, not comparator code.
No framework imports/builds, external network/access probes, canonical/provider
edits or prior packet changes occurred. Native validation order, exact dtype/
device/layout/AD closure and all numerical/runtime/performance/release gates
remain open. No irreconcilable architecture choice was identified in this slice.
