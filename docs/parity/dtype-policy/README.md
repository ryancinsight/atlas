# Frozen JAX promotion and casting policy

Policy **2026-10-26.1**, program **2026-10-26.8**. This source definition slice
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
| [Source clauses](jax-20261026/captured/policy-contracts.json) and [canonical joins](jax-20261026/joins.json) | 18 clauses, nine existing IDs, owners, prerequisites, source spans and acceptance links |
| [Acceptance targets](jax-20261026/captured/acceptance-targets.json) | 18 targets, all unrun |
| [CP02 disposition](jax-20261026/companion-disposition.json) | Derived evidence-required state; immutable raw workflow record retained |
| [Remaining gaps](jax-20261026/captured/remaining-gaps.json) | Ten open definition/execution groups |
| [Source witnesses](jax-20261026/source-witnesses.json) | 63 hashed excerpts across 17 frozen Git blobs |

JAX remains **0.12.0.1**, commit
`dc4af684446e65ee98eee8090e1ff6f8211473fb`. Supporting NumPy source remains
**2.5.4**, commit `a3d0ef1df045b858e68115001fdabc930bb3b68c`. These source pins
do not identify installed companion artifacts. Full third-party source files are
not vendored; portable excerpts, hashes and original review preserve provenance.
Captured research documentation and replay receipts describe the original packet.
Canonical reproduction uses the Atlas checker and tests below.

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

The canonical NUM-PROMOTE owner remains **Eunomia**, prerequisite **NUM-REP**.
The joins reuse Coeus AD owners and prerequisites. One generic native policy
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
source spans, and checks every ID/owner/prerequisite/clause/case link. It consumes
all captured artifacts as committed qualification inputs. Exact span bytes bind
source bodies; original AST-render digests remain immutable provenance across
Python versions. No framework import/build or hardware execution occurs.

The original packet's 24 source/analytical checks, 22 expected join fixtures and
byte-identical replay are historical source evidence, not executed acceptance
targets. All 18 targets, ten wider gaps and eight CP02 evidence gaps remain open.
The rendered JAX documentation 403 route remains stopped.
