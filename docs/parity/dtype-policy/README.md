# Frozen dtype source policies

Program **2026-10-26.10** consumes independent source-specific policy indexes.
Their introduction versions are immutable provenance, not a requirement to
rewrite prior sources whenever the enclosing program advances. All source
policies remain partial definitions with no runtime or mapping-stage credit.

## JAX source policy

Policy **2026-10-26.1**, introduced in program **2026-10-26.8**. This source definition slice
preserves all **38,096** admitted candidates and their mapping stages. It adds
no public identity, complete API mapping, runtime, performance or release credit.

The [versioned index](jax-20261026/index.json) binds the independently accepted
source packet `72206a73ecad553b819b42af2f45fc35efcdf4b6a3dea45de86e96af9fc3befe`
and [review](jax-20261026/independent-review.json)
`364896a26a94ba037ed6895c072e9dd3211c2faa5e0298a411328d3db87f995f`.
That review covers the original source packet; this integrated candidate still
requires its own exact-head review and normal delivery gates.

| Artifact | Boundary |
| --- | --- |
| [Lossless capture](jax-20261026/capture.json) | Original hashes and roles; compact JSON reconstructs the original bytes |
| [Source graph](jax-20261026/graph.json) and [pair table](jax-20261026/pairs.json) | Eight graph/config views and 9,256 finite source-symbol joins |
| [Source clauses](jax-20261026/captured/policy-contracts.json) and [canonical joins](jax-20261026/joins.json) | 18 clauses, nine IDs, policy suppliers, actual API mapping associations, source spans and acceptance links |
| [Acceptance targets](jax-20261026/captured/acceptance-targets.json) | 18 targets, all unrun |
| [CP02 disposition](jax-20261026/companion-disposition.json) | Derived evidence-required state; immutable raw workflow record retained |
| [Remaining gaps](jax-20261026/captured/remaining-gaps.json) | Ten open definition/execution groups |
| [Source witnesses](jax-20261026/source-witnesses.json) | 63 hashed excerpts across 17 frozen Git blobs |

JAX remains **0.12.0.1**, commit
`dc4af684446e65ee98eee8090e1ff6f8211473fb`. Supporting NumPy source remains
**2.5.4**, commit `a3d0ef1df045b858e68115001fdabc930bb3b68c`. These source pins
do not identify installed companion artifacts. Full third-party source files are
not vendored; portable excerpts, hashes and original review preserve provenance.
The [opaque original README](jax-20261026/captured/README.source.txt) and replay
receipts describe the original packet, preserving its exact bytes and historical
relative paths. Canonical navigation uses the [graph](jax-20261026/graph.json),
[pair table](jax-20261026/pairs.json) and other artifacts above. Canonical
reproduction uses the Atlas checker and tests below.

The finite graph has 33 nodes when both `ml_dtypes.int1` and `uint1` are absent,
35 when both are present, and source initialization rejections for the two
one-sided profiles. Removing Python assertions changes the signed-only exception
site but still leaves an arity mismatch. No released artifact or executed import
is inferred from a symbolic attribute profile. Never downgrade a companion or
fabricate one to force branch coverage.

Standard/strict policy and X64 config views remain separate. Strict graph shapes
coincide across X64 settings, while input canonicalization and trace state still
differ. Standard X64-off changes the `uint32` edge to `int32`; it does not remove
already-formed x64 nodes. Weak `int/float/complex`, strong bool, low-precision
formats, defaults, explicit-X64 WARN/ERROR/ALLOW, preserved JAX-array dtypes and
registered scalar behavior retain distinct clauses. Column storage deduplicates
JSON values, never symbols or semantics; all 9,256 ordered pairs survive lossless
reconstruction, including explicit null joins.

`jax.numpy.can_cast` delegates to companion NumPy's casting predicate. JAX's
internal `safe_to_cast` uses promotion-result equality with a strongly typed
output. It is not a newly admitted public API or an all-values-exactness proof.
The integer `2**24+1` cannot be represented exactly by binary32, even though the
source graph joins int64 and float32 at float32. A graph LUB is not a final API
dtype, native conversion result, kernel-support matrix or numerical guarantee.

`float0`, strings and PRNG/custom extended dtypes are not silently excluded from
parity because they lie outside the finite ordinary numeric graph. Category sets,
native-valid sets, trivial result-type branches, representation conversions and
custom primal/tangent rules differ. AD tangent dtype and Ref accumulation follow
Coeus contracts, independently of ordinary promotion. Actual casting, coercion,
warnings/errors, shape/layout/device rules and higher transforms remain unrun.

The NUM-PROMOTE policy supplier remains **Eunomia**, prerequisite **NUM-REP**.
Each endpoint separately records its policy supplier and its association with
the actual canonical API mapping. Four endpoints have existing partial mappings:
`result_type`, `promote_types` and `can_cast` join Eunomia/NUM-PROMOTE; `astype`
joins Coeus/TEN-OPS while retaining Eunomia as its scalar policy supplier. The
other five endpoints remain explicitly unmapped. These joins never reassign
canonical API ownership or create a mapping. Source clauses retain Eunomia scalar
and Coeus AD policy suppliers with their existing prerequisites. One generic native policy
encodes dtype/weak/config/format variation; no foreign production runtime,
precision-cloned algorithm or silent CPU fallback is authorized.

CP02 retains its original `decision_required_no_resolved_artifact_set` record in
the sealed workflow capture. The derived state is
`evidence_required_no_resolved_artifact_set`: eight ordinary artifact,
environment, configuration, compatibility and scope-inventory gaps, with no
demonstrated irreconcilable user decision. Exact jaxlib/ml_dtypes/NumPy/SciPy/
opt_einsum artifacts, ABI/platform and native/device compatibility remain open.
No artifact selection or full companion matrix is claimed.

```sh
python3 scripts/atlas-parity.py check
python3 scripts/atlas-parity.py report
PYTHONPATH=scripts python3 -m unittest scripts/tests/test_parity_dtype.py -v
```

The actual checker conserves graph/profile/pair counts, independently recomputes
joins and expected source edges, verifies lossless source/review hashes and exact
source spans, and checks every ID/supplier/API-mapping/prerequisite/clause/case link. It consumes
all captured artifacts as committed qualification inputs. Exact span bytes bind
source bodies; original AST-render digests remain immutable provenance across
Python versions. No framework import/build or hardware execution occurs.

The original packet's 24 source/analytical checks, 22 expected join fixtures and
byte-identical replay are historical source evidence, not executed acceptance
targets. All 18 targets, ten wider gaps and eight CP02 evidence gaps remain open.
The rendered JAX documentation 403 route remains stopped.

Canonical review found and corrected the earlier supplier/API-owner ambiguity
and a reindexed source-witness header that could claim runtime credit. Exact
typed wrapper schemas now bind source-only credit, original review scope,
17-source/44-file counts, structured replay provenance and eight unique CP02 gap
IDs. Copied-artifact tests reindex changed files and exercise the full program
loader; reformat/reindex remains a valid positive control. The accepted source
packet/review and raw workflow history remain immutable. This correction still
requires exact-head clearance before delivery.


## NumPy native dtype source policy

The [NumPy index](numpy-20261026/index.json), introduced in program
**2026-10-26.9**, binds source packet
`04e6d40cd363a27e7169916a1c68e6716c2ed658bd7746f1c9f93ec977265a97` and
[independent source review](numpy-20261026/independent-review.json)
`710b8e1d629ceb370bf70ff8866f593688f591738c44613d6072252937ddf33b`.
NumPy remains **2.5.4**, commit `a3d0ef1df045b858e68115001fdabc930bb3b68c`.
The accepted review covers 29 source tests, zero skips, and 211 byte-identical
replayed artifacts. It does not review this canonical candidate or execute an
API, provider or installed companion artifact.

| Artifact | Boundary |
| --- | --- |
| [Lossless capture](numpy-20261026/capture.json) | Sixteen selected original roles reconstruct exact accepted bytes; original manifest/review pins remain strict |
| [Source families](numpy-20261026/captured/native-contracts.json) and [role joins](numpy-20261026/joins.json) | Ten partial source families, three primary IDs, five supporting IDs, policy suppliers and actual canonical API mapping associations |
| [Table policy](numpy-20261026/table-policy.json) and [symbolic cells](numpy-20261026/safe-pairs.json) | All 576 relations, including ABI expressions and nonnumeric kinds; two illustrative ABI profiles remain unobserved |
| [Source receipts](numpy-20261026/captured/source-receipts.json), [quotes](numpy-20261026/captured/source-witnesses.json) and [bindings](numpy-20261026/source-bindings.json) | 78 file receipts, 129 exact selected function hashes/signatures, 131 bounded spans and six named registered-resolver phases |
| [Acceptance cases](numpy-20261026/captured/acceptance-cases.json) and [benchmarks](numpy-20261026/captured/benchmarks.json) | All 47 comparator/provider specifications and every performance family remain unrun |
| [Open gaps](numpy-20261026/captured/remaining-gaps.json) and [ownership proposal](numpy-20261026/captured/ownership-plan.json) | Descriptor/callback/payload/ABI/device/AD/source-closure obligations; no implementation owner or ADR approval |
| [Correction disposition](numpy-20261026/correction-disposition.json) | Source-backed annotation of earlier result_type wording; historical contract/mapping bytes remain unchanged |

The capture preserves symbolic relations, not a universal dtype lattice or a
payload-representability theorem. The checker expands the pinned safe-table
macros into all 576 cells, parses their closed comparison/boolean grammar,
reconstructs the promotion initializer metadata and independently computes both
illustrative profile matrices. It does not trust precomputed cells as an oracle.
Object, structured, subarray, fixed/managed string, temporal, custom and legacy
user descriptor callbacks retain distinct semantics outside that finite table.
The exact observed ABI, extension callback programs, conversion kernels and all
legal descriptor parameter combinations remain open.

Registered casting implementation lookup, advertised-safety bypass, resolver
invocation, source/target descriptor adjustment, cleanup and query-local error
projection remain distinct phases. The registered temporal slot and its integer
quotient branch are source-bound: same-byteorder **2001ms to 2s** satisfies
`2001 // 2 == 1000` in the selected branch, while the durations differ. This is
an unresolved exact-binary comparison question. It grants neither a reference
bug waiver nor a scope exclusion, and no observed divergence is claimed.

The three existing query mappings remain partial Eunomia/NUM-PROMOTE mappings.
`numpy.dtype` and the four supporting C APIs remain explicitly unmapped.
Descriptor/coercion and custom-dtype component planning retains Leto ownership,
with Eunomia supplying NUM-REP policy. The source-plan label `INTEROP-NATIVE`
is not one of the 67 registered capabilities; two families retain it explicitly
as an unresolved prerequisite. This is ordinary provider/capability ABI design
work, with no demonstrated irreconcilable user architecture choice. It is not
silently reassigned to dispatch-only
ownership. All actual implementation owners remain unresolved. One native
generic policy encodes the representation/ABI/descriptor variation; no hidden
widen-compute-narrow or foreign runtime architecture is authorized.

The earlier result_type wording is narrower than a blanket no-value-inspection
law: single-input descriptor discovery can depend on Python integer range;
multi-input exact Python scalar temporaries use abstract weak kinds. The new
annotation records this correction without rewriting the accepted core source
or granting mapping completion.

The [opaque original README](numpy-20261026/captured/README.source.txt) and source
scope retain their original historical paths and pending-review label as exact
source metadata. Canonical navigation uses the functional links above; the
separate accepted review records the later source-only acceptance. Historical
acquisition receipts describe 31 reused sources and 47 verified reads, with no
denial or retry. This integration performs no access or network operation and
makes no new current-access claim. Full foreign source files are not vendored;
selected source excerpts and a frozen Git tree/receipt index preserve provenance.
JAX's index, source, review, mappings and raw CP02 record remain unchanged.

```sh
PYTHONPATH=scripts python3 -m unittest scripts/tests/test_parity_numpy_dtype.py -v
python3 scripts/atlas-parity.py check
python3 scripts/atlas-parity.py report
```

The 38 NumPy integration tests include physical-file corruption followed by
reindexing, strict status/provenance/count/role checks, source/body/phase joins,
independent symbolic reconstruction and a valid reformatted/reindexed control.
The current candidate still requires independent exact-head review and normal
local/hosted delivery checks. Source checks grant no framework execution,
performance, registry, release or whole-API qualification.


## Repaired Torch native dtype source policy

The [Torch source index](pytorch-20261026/index.json), introduced in program
**2026-10-26.10**, binds repaired packet
`a34fc711c04e087985c8835b933bcfae275493fdeb0b72455523ee7e1618fcb0` and the
[same-reviewer successor assessment](pytorch-20261026/independent-review.json)
`013862e7a4bff259a08aaa1cf31531f0c5e67f0069e91d764f482124dd6b94c6`.
PyTorch remains **2.14.1**, source commit
`5c4886908584029761b579af026dcfb627c84070`. The source identity inventory is
minor-series 2.14; exact patch semantics are bound separately to selected source.
Neither an installed artifact nor complete public extraction is established.

| Artifact | Boundary |
| --- | --- |
| [Lossless capture](pytorch-20261026/capture.json) | Selected source artifacts and initial review reconstruct accepted bytes; no full foreign source/history bundle is vendored |
| [Partial contracts](pytorch-20261026/captured/contracts.json) and [canonical roles](pytorch-20261026/joins.json) | Ten admitted IDs retain actual API associations independently of the Coeus facade proposal and Eunomia supplier |
| [Model metadata](pytorch-20261026/model.json), [core cells](pytorch-20261026/core_lookup_cells.json), [promotion pairs](pytorch-20261026/native_promotion_pairs.json) and [cast permissions](pytorch-20261026/native_cast_permission_pairs.json) | All 47 native enums, 196 core cells and 2,209 ordered pairs per relation; native enums are not a public kernel registry |
| [Receipts](pytorch-20261026/captured/source-registry.json), [quotes](pytorch-20261026/captured/source-witnesses.json) and [portable proof](pytorch-20261026/source-proof.json) | 45 full-file receipts and 88 exact bounded excerpts; original review checks full bytes, canonical validation checks selected receipt/quote bindings |
| [Computation policies](pytorch-20261026/captured/computation-policies.json) | Storage, common, computation, accumulator and result types remain separate, per source path and operation |
| [Acceptance cases](pytorch-20261026/captured/acceptance-cases.json) and [conditional plan](pytorch-20261026/acceptance-plan.json) | All 66 framework/provider specifications remain UNRUN; three bounded subordinate packages are evidence-required, with null actual implementation owners |
| [Repair history](pytorch-20261026/captured/correction-history.json), [source-review proof](pytorch-20261026/review-proof.json) and [open gaps](pytorch-20261026/captured/remaining-gaps.json) | Original findings/history remain intact; 14 named gaps and exact-head canonical review remain open |

The initial `697b0c74` packet and `3ac30501` review remain preserved externally
and through selected immutable history receipts. The initial material findings
were an ambiguous complex/list fixture and aggregate wrappers capable of false
scope/runtime credit. The repaired packet uses rank-zero native complex64
Tensors, a Python complex Number alpha, real float32 scalar loss/cotangent and
conjugate gradients, plus strict aggregate/status types. The same reviewer
clears those two source findings. Its 156-file replay, 28 source tests/zero skips,
18 physical-file reindexed probes, 58 independent negative probes and six
independent real-coordinate controls are original source evidence only; they do
not approve this canonical candidate or execute any of the 66 framework cases.

Canonical validation reconstructs native classifiers, the 14-axis table and all
ordered promotion/cast outcomes from pinned excerpts. Equal dtype, quantized,
Bits, Float8 and extended-unsigned mixed rules preserve source order. A
permitted metadata cast is not value preservation, conversion availability or a
whole shell/quantized/extended dtype capability. Rank-zero, dimensioned,
wrapped/Python scalar and default contexts remain distinct. The nine bounded
rank/default analytical fixtures do not close symbolic or generated binding
semantics.

The concrete CPU sum cascade uses `acc_type<scalar_t,true>` despite running in
the CPU source. Native and Python accumulator helpers differ; source opmath
specializations do not qualify all kernel/device paths. Tensor.to aliasing also
requires compatible memory format, layout and copy=False. Visible CPU integer
trunc division checks zero then performs C++ division; no universal signed
minimum/-1 result or exception is invented. Full generated arithmetic,
conversion/rounding/overflow, reduction scheduling, default-context and
layout/device/AD/error domains remain among the 14 gaps.

Three selected APIs have existing partial Coeus/TEN-OPS associations; seven are
explicitly unmapped at this source revision. The canonical validator joins the
actual mapping records and never assumes every facade endpoint belongs to
Coeus: an actual Eunomia association, when supplied by the canonical map, remains
Eunomia. The Coeus facade is a proposal, while Eunomia NUM-PROMOTE supplies scalar
policy. All actual implementation owners remain unresolved. Source-side text
that says Coeus ownership is retained is interpreted within that proposal role,
not used to reassign canonical owners or create mappings.

Six separately tagged exact-rational complex controls verify the canonical
oracle's input sensitivity and conjugation convention. Native Tensor shape,
dtype/device, Python Number alpha and requires_grad leaves are checked before
algebra. Changing inputs or cotangent while retaining stale outputs/gradients
rejects; a correctly changed analytical control and a reformatted/reindexed
capture remain valid. Every component and intermediate in these controls is
binary32-exact. This finite precondition is an analytical check domain, not a
restriction on admitted API scope or a qualification of generated arithmetic.

The [conditional native plan](pytorch-20261026/acceptance-plan.json) links
WP-001/003/004 to definition closure, Eunomia typed policy and proposed Coeus
tensor integration. It retains all selected case obligations and gap IDs,
explicit Storage/Promoted/Compute/Accumulator/Result policy types and real
hardware/AD/error/release evidence requirements. Ordinary native design direction
is authorized; it grants no concrete ADR approval, hidden widen-compute-narrow
substitute, unsupported-capability exclusion or new user scope decision.

The [opaque original README](pytorch-20261026/captured/README.source.txt) and
history metadata retain their historical paths and pending-review labels.
Canonical navigation uses the links above. JAX and NumPy indexes, captures,
reviews, mappings and raw CP02 remain unchanged at introduction versions .8/.9.
The inherited CI setup fix and protected #551 handoff remain intact; no prepared
shared tool is adopted and no provider/build/import/network/auth action occurs.
After the NumPy selector successor is merged locally, Torch endpoint/case/receipt
paths use the shared typed source resolver, exact expected positions and selected
object identities. The local duplicate resolver is removed. This tooling repair
preserves captured source bytes, actual API ownership and every unrun obligation.

```sh
PYTHONPATH=scripts python3 -m unittest scripts/tests/test_parity_torch_dtype.py -v
python3 scripts/atlas-parity.py check
python3 scripts/atlas-parity.py report
```

These checks grant no implementation, external API, performance, registry or
release credit. Definition and release qualification remain blocked. Independent
review of the final canonical head and normal delivery gates remain mandatory.
