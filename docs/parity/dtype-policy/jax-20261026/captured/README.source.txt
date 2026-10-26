# JAX promotion and casting policy prerequisite

This packet defines a bounded source prerequisite for Atlas `NUM-PROMOTE`.
It changes no canonical/provider files, admissions, implementations or versions.
The existing accountable owner is **eunomia**, with prerequisite **NUM-REP**;
AD/resource composition remains with the existing Coeus contracts.

The reference is JAX **0.12.0.1** at
[`dc4af684446e65ee98eee8090e1ff6f8211473fb`](https://github.com/jax-ml/jax/tree/dc4af684446e65ee98eee8090e1ff6f8211473fb).
Inputs include the independently reviewed core packet manifest
`7c169acfcb711c3714701f6fde84fea2fe14508c30d3d8148b7e2aca1cee1ea0`.
All **17** selected full source files match their frozen Git tree blobs and
SHA-256 receipts; **63** source spans have exact hashes and line URLs.
NumPy source used to characterize the companion casting alias is frozen
**2.5.4** at `a3d0ef1df045b858e68115001fdabc930bb3b68c`. No installed companion
artifact is inferred from those source versions.

## Finite source graph

[promotion-graph.json](promotion-graph.json) extracts the literal weak/strong
DAG with a restricted AST table evaluator. It never imports or evaluates a
framework function. [dtype-catalog.json](dtype-catalog.json) preserves valid
native dtype sets, category sets, weak types and the X64 canonical map.

| Conditional companion profile | Source graph disposition |
| --- | --- |
| Neither `int1` nor `uint1` | 33 nodes; standard/strict × X64 off/on |
| Both `int1` and `uint1` | 35 nodes; standard/strict × X64 off/on |
| Only `int1` | Source assertion rejects; with Python assertions removed, subsequent unpack still rejects |
| Only `uint1` | Source unpack rejects |

The eight constructible graph/config views contain **9,256 ordered binary
source-symbol pairs**. Every pair has a unique source-symbol least upper bound
or no common upper bound. This finite pair table is complete for these exact
graphs. It does **not** establish complete public API dtype legality or a final
runtime dtype result. The weak-node output of `promote_types` is subsequently
interpreted by companion `np.dtype`; `result_type` has additional input/default
and weak-result rules. Named formats are source-symbol identities here; installed
companion dtype identity/equality and registration remain CP02 obligations.

Strict topologies are identical across X64 flags; their config views remain
separate because argument canonicalization, explicit dtype requests and trace
state still differ. In standard mode the X64 graph difference is precisely
`uint32 -> [int32,uint64]` versus `uint32 -> [int64,uint64]`. The source comment's
`u4xi4` byte-width notation must not be confused with the tiny `uint4/int4`
formats. Existing x64 graph nodes remain present when X64 is off.

Each conditional profile is a source alternative, not evidence that a released
artifact with that exact profile exists. Select latest coherent companions and
record actual metadata; never downgrade or fabricate one to force a branch.
No source-model rejection is counted as an executed JAX import test.

## Policy distinctions retained

[policy-contracts.json](policy-contracts.json) contains **18** source rules and
links **nine existing admitted identities**, including unchanged
`jax.numpy.result_type`, `promote_types` and `can_cast` IDs. It adds no public ID.

- `jax.numpy.can_cast` is the companion `numpy.can_cast` alias, through JAX
  dtypes. The extracted NumPy Python function is a native C dispatcher/signature;
  its native casting matrix remains a separate obligation. Internal JAX
  `safe_to_cast` instead compares JAX `result_type` against a strongly typed
  target and may raise `TypePromotionError`. It has no newly asserted public
  import path here. `jax.numpy.dtype` also comes directly from NumPy.
- Weak `int/float/complex` nodes, strong bool, registered scalar types and
  `aval.weak_type` remain distinct. Standard all-weak result typing and category
  defaulting are preserved; they are not inferred from names or rank alone.
- Default integer/float/complex widths and the four X64-off canonical mappings
  remain separate from explicit-X64 `WARN/ERROR/ALLOW`. Already-formed JAX x64
  arrays preserve their dtype in the supporting `dtype()` branch even when
  global X64 is off. Source documentation summaries about downcasting do not
  replace these conditional branches.
- Tiny integers and float4/6/8 formats have source-specific disconnected nodes;
  weak scalar reachability does not imply promotion between different strong
  formats. `float0` and `StringDType` belong to the valid dtype set but not the
  promotion/category sets. Identical/single result-type bypasses and extended
  PRNG/custom dtype protocols remain explicit obligations outside the graph.
- Scalar integer overflow, constructor fast paths, list weakness, protocol
  coercion, inferred `lattice_result_type`, operation-specific numeric/inexact/
  complex helpers, copy/device/sharding and actual conversion remain separate
  clauses. Float/int conversion values and complex deprecation behavior need
  the selected backend and transitive policy receipts.
- AD tangent dtype comes from `primal_dtype_to_tangent_dtype`, extended dtype
  rules and cast JVP/transpose rules. It is not ordinary promotion LUB.
  `float0`, real/complex/holomorphic restrictions, `allow_int`, exact trees/shapes
  and Ref accumulation retain their separate contracts.

## CP02 disposition

[CP02-evidence-audit.json](CP02-evidence-audit.json) preserves the canonical row
observed at checkout `fb95a32833b673a5ff8f1bdf5e39e93afe447001`. Its current
`decision_required_no_resolved_artifact_set` label denotes missing evidence;
no irreconcilable user scope or architecture choice has been demonstrated.
The proposed label is **`evidence_required_no_resolved_artifact_set`**.

Eight named ordinary gaps cover exact jaxlib/ml_dtypes/NumPy/SciPy/opt_einsum
artifacts, Python/ABI/platform/optimization state, dtype configuration and
registrations, native/device compatibility and companion scope traceability.
The source ranges/minima are verified, but selected versions, wheel/source
hashes and compatibility runs remain unresolved. The source minimum
`ml_dtypes>=0.5.0` does not establish all unconditionally referenced format
attributes or native kernel support. No request for scope reduction is needed.

The native implementation recommendation uses one trait-driven policy with
explicit dtype/weak/configuration/format variants and the existing owner DAG.
It does not adopt a third-party runtime or clone algorithms per precision.
Escalation is appropriate only if future evidence demonstrates a conflict that
cannot be resolved within the frozen baselines and authorized native design.

## Acceptance and remaining work

[acceptance-targets.json](acceptance-targets.json) defines **18 unrun targets**,
covering public API representation variants, three explicit-X64 modes, weak/
strong and custom types, errors/warnings, coercion, casts, AD, JIT/vmap and real
device/layout/ISA behavior. It includes benchmark evidence requirements without
inventing a numerical budget. [remaining-gaps.json](remaining-gaps.json) names
ten wider definition/execution gaps. The complete companion/artifact matrix,
per-API legality, extended protocol domain, numerical conversion semantics,
hardware, performance and releases remain open.

The analytical witness for integer `2^24+1` uses exact integer arithmetic:
binary32 precision24 has spacing2 in `[2^24,2^25)`, so this odd integer is not
exactly representable. The source graph still admits `int64,float32->float32`.
Thus a source promotion-based “safe” predicate cannot establish all-values
exact conversion. This is a mathematical format witness, not an installed
dtype or kernel receipt.

## Verification and reproduction

```sh
python3 build.py
python3 verify.py
python3 validate.py
```

[verification.json](verification.json) records **24 passing checks, zero skips**.
An independent bitset transitive-closure/join calculation checks every source
pair against the extractor's traversal result. Additional checks cover **22**
explicit expected joins, integer boundary proofs, conditional profiles,
X64/strict differences, alias and AD source clauses, exact existing IDs and
source spans, rejection mutations and byte-identical cached-source replay.
All nine generated JSON outputs replay byte-identically.

Framework/provider cases executed: **zero**. Network/auth/protection probes,
framework imports/builds and PR actions: **zero**. The rendered JAX documentation
403 route remains stopped. Previously sealed source, public-scope and workflow
packets remain unchanged. No whole inventory, API semantics, runtime, external,
performance or release qualification is claimed.
