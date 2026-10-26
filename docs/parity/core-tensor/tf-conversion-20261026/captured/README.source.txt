# TensorFlow conversion boundary numerical successor

**Proposal only; independent review is pending.** The primary endpoint is the
existing, currently **unmapped** identity
`tensorflow@2.21.0|function|tf.convert_to_tensor|a128953132f05570`.
No public identity, mapping-stage, implementation, runtime, performance or release
credit is added. All 30 future cases are **UNRUN**. The primary canonical inventory
and its denominator are unchanged and are not recounted by this packet.

The observed Atlas planning snapshot is
`fd0efd9007235bede364fc6a4f26036a3bbe5204`, tree
`3ec069926a406cbf3e22bf5fb9dac1108c36bded`. This packet does not modify it.
The accepted core source packet `875d1411...` already defines partial TF
cast/add/shape/broadcast/reshape/index/resource/AD contracts. Its own cast and add
contracts identify weak and automatic conversion as remaining work. The JAX and
NumPy dtype policy indexes remain source-specific. The active Torch author
confirms no overlapping TF semantic packet or active TF author in that lane.

This selects one missing input boundary rather than another publicness classifier
or a full TensorFlow dtype table. It has 11 source clauses, five supporting
distinctions, 10 existing identities, 21 cached official source files, 63 exact
line excerpts, 30 future cases and 10 open gap groups. There are 22 primary cases,
six supporting cases and two auxiliary source controls. Existing partial
API mappings stay partial; existing unmapped APIs stay unmapped. Source-exported
experimental NumPy names absent from this primary inventory remain explicit
source obligations without invented identities or an exclusion decision.

The original unaccepted manifest `856a65a0...`, all 42 artifacts and its manifest
are preserved byte-for-byte under `history/predecessor-856a65a0/`. The initial
independent review has **changes requested**, not clearance, and is retained
under `review-history/856a65a0/`. [Correction history](correction-history.json)
records all six original finding groups and numerical groups007/008. The exact
e075 predecessor manifest and all 125 artifacts are additionally preserved under
`history/predecessor-e0759917/`, with the sealed 68-file independent review
evidence under `review-history/e0759917/`. That review confirms the original six
repairs and requests the two numerical corrections; it grants no acceptance.
This successor still requires the **same
reviewer's exact-manifest review**; local guards do not grant that review.

## Selected semantics

The [proposal](proposal.json) distinguishes public API dispatch, dtype parsing,
hook precedence, registry order, soft hints, return validation and native Tensor
identity. The public selected v2 native route normalizes `dtype`, then the hint,
before looking up `__tf_tensor__`. The hook receives dtype/name and bypasses the
registry. A soft hint is tried only when hard dtype is absent. Its TypeError or
ValueError allows an unhinted retry; NotImplemented selects the next converter.
Wrong hinted dtype and other exceptions do not receive that retry.

A converter's **normal hinted return of None** raises `AttributeError` while
loading `ret.dtype` in the try-else, outside that exception handler. An unhinted
None return instead fails `accepted_result_types` with `RuntimeError`. These are
separate from a caught converter exception and NotImplemented. The exact public
registration exclusion/internal priority-zero tuple is `int`, `float`,
`np.generic`, `np.ndarray`, including subclasses. `bool` is excluded through int;
Python `complex` is not. List/tuple conversion has priority 100 and object
fallback 200. Python complex reaches the object fallback absent another matching
registration; NumPy complex scalar classes remain distinct.

The native eager Tensor path preserves object, value, shape and device when dtype
is compatible; it rejects an incompatible hard dtype rather than adding a cast.
An EagerTensor crossing into a building-function graph returns
`graph.capture(self, name=name)` without forwarding dtype or invoking the
superclass branch. Capture's own dtype validation and alias behavior require
their own source/runtime evidence; this does not assert success with an
incompatible requested dtype.
The selected eager ndarray constructor copies host memory; it does not establish
a Tensor stride or accelerator zero-copy contract.

Raw `tf.cast` can infer a Python value's dtype before its requested cast. Direct
conversion with a hard dtype has a different sequence. A binary64 Python value
near pi distinguishes binary32 construction then widening from direct binary64
construction. Raw `tf.add`, the legacy NumPy-enabled Tensor operator, and SAFE/ALL
weak wrappers remain separate paths. Three selected flexible-table cells are
read from the source AST; no all-pairs promotion, native dtype legality or kernel
support is inferred.

For the mixed-add analytical cases18/19, each operand is converted into inferred
float32 **before** addition. Exact rational round-to-nearest/ties-even models
both operand conversion and the target addition. Thus `16777217` first becomes
`16777216`, and adding float32 `-16777216` yields `0`, not the unrounded rational
sum `1`. Opposite tie and post-add rounding controls are retained. The conversion
order is source-backed; IEEE nearest-even is an analytical premise, not an
observed native TensorFlow/kernel/device rounding result. Native execution,
subnormal/flush rules, all modes and nonfinite behavior remain open.

Protocol case09 checks every generated cotangent in its declared dtype as well
as primal outputs and loss intermediates. Zero primal values cannot hide an
impossible finite float32 cotangent `2 * max_float32`. That input is rejected by
the finite analytical fixture model; it is not a TensorFlow error prediction or
a public-domain exclusion. The valid half-maximum-weight control has finite
cotangent `max_float32`. Nonfinite/overflow/inexact AD and protocol obligations
remain unrun. Signed-negative-zero input fixtures remain unmaterialized in this
value-only model; sign-sensitive API obligations remain open, and typed float
comparison preserves sign when comparing represented values.

Keras 3.15.1 input autocast and compute/variable policies remain separate from raw
TF conversion. Keras' TF backend also deliberately uses conversion followed by
cast for integer/bool targets. The helper source control is not a newly admitted
public operation or an automatic equivalence to `tf.convert_to_tensor`.

## Ownership and execution readiness

[Implementation planning](implementation-plan.json) proposes Coeus/TEN-CORE as the
single Tensor facade owner. **Actual implementation owner remains null.** Eunomia
supplies NUM-PROMOTE/NUM-REP policy; Leto supplies interchange and shape/layout;
Mnemosyne supplies buffers; Melinoe supplies access proof; Themis supplies
placement; Hephaestus supplies actual device conversion. Coeus composes AD after
the primal contract. The copied transitive capability DAG preserves canonical
owners and prerequisites. None of these proposal roles approves an ADR, changes
an API mapping or adopts protected owner work.

The recommended native design uses one generic first-party conversion operation
with distinct hard-target and soft-preference types and explicit policy,
weakness, shape and execution-context parameters. Source-observable callback
semantics require a typed native extension contract; they do not require adopting
TensorFlow's Python registry/runtime architecture. Implicit widening and silent
CPU fallback cannot satisfy a native precision/device contract. Keras' documented
wider internal precision remains an explicit functional-equivalence design
question requiring associated accumulator/numerical evidence, not a waiver.

Conditional effort, with low confidence and **after dependencies are met**, is
2–4 engineer-days for selected source review/definition, 1–2 for canonical
integration/guards, 3–7 for an approved first CPU primal implementation, and 2–5
for selected CPU mode/protocol/AD acceptance. These are sequential work allowances
with separately stated prerequisites. They are not deadlines or a total program
estimate. Native dtype domains, traced/device profiles, performance and release
remain unestimated until artifacts, architecture, ownership and hardware are
known. The current proposal is not execution-ready.

## Evidence and open work

[Receipts](source-receipts.json) bind TensorFlow **2.21.0** at
`a481b10260dfdf833a1b16007eead49c1d7febf3` and Keras **3.15.1** at
`250b42181ce9f37df68319d8f4753ec89a349a43`. Each source matches both its earlier
cache receipt and frozen Git-tree blob. [Witnesses](source-witnesses.json) preserve
exact excerpts with line URLs and hashes. The earlier cache manifest/tree hashes
and source selection are recorded; there are no new network requests. These pins
do not prove any installed wheel, ABI, NumPy/ml_dtypes companion, compiler,
plugin, driver or hardware configuration.

Actual source bytes/coordinates are anchored to the immutable original manifest
and the independently fixed initial source audit, rather than trusting editable
receipt fields to authenticate one another. The repaired immutable source
specification fixes each clause's selected witness coordinates. AST inspection
separately reconstructs the reviewed hint branches, registration tuple/priorities,
capture return and selected promotion cells. No framework source executes.

Thirteen full canonical files, including the four actual mapping source contracts,
are preserved under `frozen-canonical/`. Their contents prove Git-blob membership
through ten preserved raw tree objects and the fixed `fd0efd9` commit object.
The ten IDs, exact selectors/signatures, **full four existing mappings**, six
unmapped associations and full transitive owner/prerequisite rows derive from
those files. [Canonical joins](canonical-joins.json) keep API ownership separate
from scalar-policy supply. No current checkout or network is needed for replay.

[Cases](acceptance-cases.json) specify represented inputs, dtypes/shapes, values,
object identity, error phases, weak flags and selected AD targets. Public binding
to patched mode wrappers, actual native construction and exact referenced
artifact compatibility must be proven before any mode case qualifies. Cases with
unresolved native error classes explicitly retain that obligation. Tests must
observe actual device and execution context; host transfer/fallback and skipped
cases never count as verification.

[Remaining gaps](remaining-gaps.json) retain custom dispatch/protocols,
Composite/Ragged/Sparse/IndexedSlices/resources, full dtype/shape admissibility,
native parser and kernel error order, graph capture, nonnumeric/extended types,
all AD/transforms, Keras policy effects, companions and hardware. None is excluded
from eventual parity. Source public/export evidence is distinct from a currently
admitted API identity. No grouping, shared name or helper table proves semantic
equivalence between frameworks.

## Offline checks and reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verify_proposal.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_proposal
PYTHONDONTWRITEBYTECODE=1 python3 replay_proposal.py
PYTHONDONTWRITEBYTECODE=1 python3 seal_proposal.py --check
```

The verifier checks frozen blob/hash/span bindings, exact existing identity
joins, no-credit stages, real input-sensitive analytical designs, selected source
table cells and the owner/prerequisite DAG. Its stdlib checks are **not** TF or
provider tests. Complete typed projections cover every case/error/call-order/
identity/shape field, all ten gaps, source-only evidence headers, null/unapproved
actual ownership and conditional effort/readiness prerequisites. Analytical
inputs vary within explicit finite fixture domains. Native inputs are represented
in their stated dtype; mixed-add target conversions may round, explicitly in the
oracle. Other selected dot products/cotangents require finite exact declared-dtype
representation. These domains do not
reduce the eventual public dtype/shape/AD obligations. Negative guards reject
promoted credit, bool/int count or shape confusion, wrong cotangents/precision/
snapshots, forged source/canonical attestations and unknown prerequisites. Valid
reformatting and an analytically recomputed input edit remain positive controls.
The replay copies this packet privately, regenerates fourteen JSON projections
without the original cache or canonical checkout, checks values and bytes, then
runs the same source-only checks. All fourteen are byte-identical for the sealed
canonical formatting; valid JSON reformatting is separately recorded without a
false semantic failure. `build_proposal.py` has no capture/network mode.
`mutation_checks.py` exercises actual disposable copies with physical reindexing;
the semantic validator and semantic sealer must still reject invalid claims.
`verification.json`, `mutation-results.json` and `replay.json` are author source
checks with exact source-only headers, never framework/runtime qualification.
Root owns independent review, canonical integration and all later delivery gates.
