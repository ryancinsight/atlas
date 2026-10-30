# NumPy native dtype policy: bounded source definition

Frozen reference: **NumPy 2.5.4**, commit **`a3d0ef1df045b858e68115001fdabc930bb3b68c`**. This packet advances the `G02-DTYPE-DOMAIN` gap from the prior accepted core packet (`7c169acf…`), whose inputs and history remain unchanged. It changes no canonical/provider files and no package versions.

The three existing public entry IDs are `numpy.result_type`, `numpy.promote_types` and `numpy.can_cast`. `native-contracts.json` retains their exact identity/provenance and five supporting admitted C/Python IDs, with **10 reusable contract families**. The scope includes native argument/error order, descriptor conversion versus DType classes, weak scalar values versus types, common-class/instance callbacks, numeric/byteorder, temporal, fixed/managed string, object, structured/subarray and custom dtype distinctions. These functions/source declarations are not new API denominator capabilities.

The finite cache audit covered 50 frozen dependency paths: **12 exact local sources**, **38 missing loose-source matches** in the declared roots. A further local audit checked **59 Git indexes / 225,683 indexed objects** and **66 ZIP/TAR archives / 2,333 members** without finding those requested blobs. The 241 measurement/image gzip containers were not source-archive scans; no whole-machine absence claim is made. Additional support sources, including `ctors.c` and `npy_2_compat.h`, were recovered from other existing caches rather than treated as unavailable merely because they were omitted from an earlier packet.

Under the parent's subsequent bounded authorization, **38 + 5 + 4 official GitHub Git-blob reads** completed through the existing `gh` CLI session, at most four concurrently. Every SHA was already bound to its exact frozen-tree path. All **47** reads verified content SHA256, Git-blob SHA and size; zero denials, uncertain outcomes, retries, alternate routes or credential/settings changes occurred. Acquisition logs preserve both the historical cache audit and the new receipts. The packet now contains **78 exact sources**: 31 reused cached and 47 acquired. Per-file equality with the frozen 2.5.0 tree is recorded explicitly; matching bytes support the 2.5.4 path without relabeling 2.5.0 semantics or claiming a current default build.

`policy-tables.json` expands every **24×24 = 576** legacy safe-cast initializer cell into an expression over ABI-size parameters. It also captures the scalar-kind/next-larger initialization used to build the legacy class promotion table. The two computed ABI profiles are analytical examples only, not observations of this machine or a NumPy build. Neither table is the final arbitrary-descriptor cast/promotion relation: parametric, object, temporal, structured and custom callbacks add further behavior.

`source-witnesses.json` contains **131 portable line excerpts** and **129 selected C/Python function-body hashes**. The control-site catalog is lexical (if/for/while/switch); it is not C preprocessing, a complete CFG, formal semantic path coverage or runtime verification. Exact bodies retain the remaining conditions, template/preprocessor details, callbacks and failure paths for review. Complete source capture is distinguished from semantic completeness.

Material refinements are explicit:

- Native keyword mapping and duplicate/unknown-name errors occur before converters. Converters run in declaration order, then missing-required checks run.
- `__array_function__` **type-object lookup** can clear any lookup error and act absent; present noncallables fail on invocation. Invocation errors propagate. Native cast-resolution errors projected to `False` form a separate later boundary.
- `can_cast` may accept advertised cast safety without invoking descriptor resolution; a `True` query does not guarantee later payload conversion or exact value preservation. Unsized S/U targets and resolver failures retain their source behavior.
- A **single-input** `result_type` canonicalizes the discovered descriptor, which can depend on Python integer range. The **multi-input** path replaces exact Python scalar temporary descriptors with abstract kind tags. Bool/subclasses and scalar type objects are distinct.
- Identical native legacy descriptors can preserve metadata in `promote_types`; other nonparametric promotion paths return the default descriptor. Structured names/titles, padding/alignment, subarray shape, temporal multipliers and managed-string state remain observable.
- Temporal metadata helper predicates differ from the registered cast resolver. Its metric-prefix branch uses integer quotient tests (for example2001ms versus2s), retained as an explicit source/documentation question pending exact binary comparison.
- ctypes probe errors can be cleared as “not ctypes,” while actual conversion failures have different behavior. Exact cached/fetched bodies define array/pointer/struct/union/scalar branches; ABI sizes and alignment remain parameters.

Two earlier provenance assumptions are corrected rather than erased: the promotion table lives in the already cached `scalartypes.c.src`, not `npy_static_data.c`; and the frozen template is `templ_common.h.src`, not an absent `templ_common.h` source path.

`acceptance-cases.json` supplies **47 unrun** concrete/parameterized reference and first-party case specifications. `ownership-plan.json` recommends Eunomia numeric policy, Leto coercion/interop, Mnemosyne ownership, Melinoe layout proof, Coeus explicit AD consumption and Hephaestus device execution. These are planning assignments; no implementation ABI/ADR or code-owner approval is implied. Internal typed diagnostics plus a reference-facing query projection are recommended without blanket suppression in provider internals. No foreign NumPy runtime may substitute for first-party computation.

`remaining-gaps.json` keeps actual build/ABI receipts, arbitrary valid callback programs/registration/lifetime, the full descriptor-parameter matrix, payload casts, transitive/compiler interpretation, actual reference/provider/device tests and release gates open. NumPy supplies no AD contract; discrete dtype policy does not justify detaching custom/object graph payload. **Whole-API semantics and runtime parity are not claimed.** Ordinary missing evidence is not a user architecture decision.

Offline replay (never rerun acquisition for replay):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/seal.py --check
```

The **29 static/analytical/negative tests** cover source/identity/acquisition conservation, symbolic table expansion and policy edges, illustrative ABI distinction, scalar and metadata branches, lookup/invocation/resolver phase separation, C lexical extraction, and rejection of mutated IDs, source witnesses/body hashes, acquisition outcomes, runtime statuses and missing table cells. They execute only stdlib analysis; **no framework import, C/Rust/framework build, reference/provider runtime test, canonical edit or provider edit occurs**. Independent semantic review is pending parent assignment.
