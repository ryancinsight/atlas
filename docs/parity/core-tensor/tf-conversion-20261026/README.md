# TensorFlow conversion boundary

Source definition **2026-10-26.1**, introduced in program **2026-10-26.12**.
The existing `tf.convert_to_tensor` identity stays **unmapped**. Ten existing
identities retain four partial and six unmapped associations; `mappings.json`
is unchanged. All **30** future cases are **UNRUN**, all **ten** gap groups stay
open, and actual implementation/kernel owners remain null. No public identity,
classification, exemption, implementation, runtime, performance or release credit
is added. The four complete public inventories and whole-API semantics stay open.

| Artifact | Scope |
| --- | --- |
| [Index](index.json) | Exact roles, source/review pins, counts and no-credit status |
| [Lossless capture](capture.json) | 24 selected roles from the immutable 320-artifact packet |
| [Original source proposal](captured/proposal.json) | Eleven clauses and five supporting distinctions |
| [Source proof](source-proof.json) | 21 source receipts, 63 portable excerpts, typed clause links and inspected AST branches |
| [Current joins](joins.json) | Ten exact IDs, signatures/selectors, full four actual mappings and separately named suppliers/facade proposals |
| [Analytical cases](cases.json) | Editable input-sensitive values, dtypes/shapes, errors, call order, identity and AD targets; all unrun |
| [Conditional plan](plan.json) | Current owner/DAG/revision joins, evidence prerequisites, low-confidence allowances and no execution readiness |
| [Original gaps](captured/remaining-gaps.json) | Ten open groups with no public-scope exclusions |
| [Independent source review](independent-review.json) | Accepted original source/model/guards; canonical candidate review is still required |

The frozen references remain TensorFlow **2.21.0**, commit
`a481b10260dfdf833a1b16007eead49c1d7febf3`, and Keras **3.15.1**, commit
`250b42181ce9f37df68319d8f4753ec89a349a43`. Source packet
`67e6c982b00ed38936c66a65d0c192790c59db4da7b1337291c727022c2bc3a7`
and same-reviewer acceptance
`c4de4542b6254a7ed1a056bd6b2f73c5b55fca7868a752492c39207a221de57d`
are fixed independently of editable artifact indexes. Compact JSON reconstructs
each selected original byte stream, including the full manifest. Full foreign
sources, runtime architecture and whole research histories are not vendored.
The original 320 artifacts and rejected predecessors remain immutable in the
reviewed source packet. Captured rejected-review/manifest metadata is inert
history; it never supplies an active contract, approval or execution result.

The source packet proves canonical context at Atlas
`fd0efd9007235bede364fc6a4f26036a3bbe5204`, tree
`3ec069926a406cbf3e22bf5fb9dac1108c36bded`. That historical context is provenance,
not current task ownership or implementation authority. The current reader joins
actual references, full mapping records, capability owners/prerequisites,
supplier revisions and work packages. Reviewed architecture/status conservation
does not adopt old task records. Current SAME-PR #551 ownership remains in the
existing program records; this slice does not contact or take over that work.

The selected native v2 route parses hard dtype and hint, then tries
`__tf_tensor__` before the registry. A normal hinted `None` return raises
`AttributeError` in the try-else dtype access. A converter's caught TypeError or
ValueError permits an unhinted retry; NotImplemented skips to the next converter;
unhinted None fails the accepted-result check. Public registration excludes
exactly int, float, NumPy generic/ndarray classes and their subclasses. Python
complex, bool and NumPy complex scalars therefore have different source routes.
Non-eager building-function conversion returns graph capture without forwarding
dtype or invoking the superclass branch; capture's own validation stays open.

Raw `tf.cast` conversion order, normal `tf.add`, legacy NumPy-enabled Tensor
operators, safe/all weak conversion and Keras input autocast/compute-variable
policy remain separate. Tensor identity, eager ndarray snapshot copying,
TensorShape metadata, runtime shape, resources and physical/device layout do not
share a blanket equivalence rule. Custom dispatch, Composite/Ragged/Sparse/
IndexedSlices/resource protocols and eager/traced/context branches remain open.

The source-parametric mathematical model converts each mixed-add operand into
inferred float32 before target addition. Exact rational nearest-even arithmetic
predicts `16777217 -> 16777216`, then cancellation with float32 `-16777216` gives
zero. This is an **unrun analytical premise**, not verified TensorFlow cast,
construction, kernel, subnormal/flush or device rounding. Protocol case09 checks
every output/loss intermediate and generated cotangent in its declared finite
dtype. Zero primal values cannot hide an impossible finite `2 * max_float32`
cotangent; the half-maximum-weight control remains valid. Finite-model rejection
does not predict a TensorFlow error or exclude inexact/nonfinite/overflow,
signed-zero, full dtype/mode, AD/protocol or device behavior from eventual parity.

Coeus/TEN-CORE is the proposed primary tensor facade, without ADR approval or an
actual implementation owner. Eunomia supplies scalar representation/promotion
policy; that supply does not confer the whole public API or Keras autocast role.
Leto supplies shape/interchange, Mnemosyne buffers, Melinoe access proofs, Themis
placement and Hephaestus device execution, with Coeus composing AD after primal
contracts. One typed/generic native design must preserve functional behavior;
foreign runtime adoption, hidden widening or CPU fallback is not authorized.

Conditional low-confidence engineer-day allowances stay source-only: definition
2–4, canonical integration 1–2, approved first CPU primal work 3–7, and selected
CPU protocol/mode/AD acceptance 2–5, each **after** its listed dependencies.
They are not deadlines or a total-program bound. Actual owners/design approval,
coherent resolved artifacts, native errors, all hardware/tracing, full AD,
performance and release/fresh-consumer evidence remain required and unestimated
where the source plan says so.

```sh
python3 scripts/atlas-parity.py check
python3 scripts/atlas-parity.py report
PYTHONPATH=scripts python3 -m unittest scripts/tests/test_parity_tf_conversion.py -v
```

The checker consumes every indexed artifact as a committed qualification input.
It reconstructs immutable captures, binds original review proofs, inspects
portable source branches, resolves exact typed selectors and recomputes active
case projections. Copied/reindexed/co-mutated full-loader tests challenge source
forgery,001–008, owner/DAG/plan/status claims and wrong float32/VJP targets.
Changed analytical inputs, JSON reformatting and cache-free loading remain valid
controls. No stdlib/source guard or skipped case counts as framework execution.
